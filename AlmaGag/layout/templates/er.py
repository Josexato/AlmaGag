"""
Template 'er' — Entity-Relationship (modelo de datos)
(WISH-LAYOUT-004 Fase 3).

Patrón objetivo:
- Nodos tipo `database`, `table`, `entity` (o keyword 'entity' en label).
- Conexiones múltiples (un nodo conectado con varios — cardinalidad).
- Ratio bipartito alto: entidades centrales (tablas) conectadas a entidades
  satélite (campos, dimensiones).
- Sin ciclos significativos (los ER suelen ser DAG o bipartitos limpios).
- Profundidad topológica baja (1-3 niveles).

Layout: force-directed simplificado — entidades con más conexiones al centro,
las menos conectadas alrededor.
"""

import math
from collections import defaultdict

from AlmaGag.layout.templates.base import BaseTemplate
from AlmaGag.layout.templates.features import GraphFeatures


def _extract_id(ref):
    return ref['id'] if isinstance(ref, dict) else ref


class ERTemplate(BaseTemplate):
    """Entity-Relationship: entidades distribuidas radial-concéntricamente."""

    name = 'er'

    DB_TYPES = {'database', 'table', 'entity', 'queue', 'redis'}

    def detect_score(self, features: GraphFeatures) -> float:
        """
        Señales positivas para 'er' (calibrado v3 — con guardas):

        Cortocircuitos importantes:
        - Sin conexiones → score 0 (no hay "relationships", es un catálogo).
        - Pocas conexiones (< 3) → score muy bajo (no hay modelo de datos).

        Señales positivas:
        - Keywords explícitos: 'entity', 'table', 'database' → señal fuerte.
        - Varios centros relativos (ratio 1.5-2.5) sin dominante.
        - Branching moderado.
        - Profundidad baja, sin containers.
        """
        # Guarda: ER necesita relaciones reales
        if features.n_connections < 3:
            return 0.0

        score = 0.0

        # ER necesita VARIOS centros relativos, no uno dominante
        if 1.5 <= features.max_degree_ratio <= 2.5:
            score += 0.20
        elif features.max_degree_ratio > 3.0:
            score -= 0.25  # claramente hub

        # Branching moderado-alto pero específico (entidades con muchos campos)
        if 2.0 <= features.branching_factor <= 5.0:
            score += 0.15

        # Profundidad baja típica de ER (1-3 niveles)
        if features.topological_depth <= 3:
            score += 0.10

        # Sin containers (ER es plano). Si hay containers, claramente NO
        # es ER puro — es arquitectura/dashboard con alguna entidad dentro.
        if features.n_containers == 0:
            score += 0.10
        else:
            score -= 0.45

        # Keywords explícitos — la señal más confiable
        er_keywords = features.label_keywords & {'entity', 'table', 'database'}
        if er_keywords:
            score += 0.55  # señal muy fuerte

        # Penalizar si hay keywords de otros patrones
        if features.label_keywords & {'shared', 'agnost', 'hub', 'spoke', 'step', 'phase', 'state'}:
            score -= 0.15

        return max(0.0, min(score, 1.0))

    def apply(self, data: dict) -> None:
        apply_er_template(data)


def apply_er_template(data):
    """
    Distribución radial-concéntrica:
    - Entidades con degree alto en el centro.
    - Entidades con degree bajo en el círculo exterior.
    """
    R_INNER = 200
    R_OUTER = 420
    ICON_W_HALF = 40
    ICON_H_HALF = 25
    PADDING = 100

    elements = data.get('elements', [])
    connections = data.get('connections', [])
    if not elements:
        return

    # Calcular degree por elemento root
    contained_ids = set()
    for e in elements:
        if 'contains' in e:
            for ref in e.get('contains', []):
                contained_ids.add(_extract_id(ref))

    root_elements = [e for e in elements if e['id'] not in contained_ids]

    degree = defaultdict(int)
    for c in connections:
        if c.get('from'):
            degree[c['from']] += 1
        if c.get('to'):
            degree[c['to']] += 1

    # Separar en centrales (degree alto) y exteriores
    if not root_elements:
        return

    sorted_elems = sorted(root_elements, key=lambda e: -degree.get(e['id'], 0))
    n_total = len(sorted_elems)
    n_inner = max(1, n_total // 3)
    inner = sorted_elems[:n_inner]
    outer = sorted_elems[n_inner:]

    canvas_w = 2 * R_OUTER + PADDING * 2
    canvas_h = canvas_w
    center_x = canvas_w // 2
    center_y = canvas_h // 2

    # Anillo interior
    n_i = len(inner)
    if n_i == 1:
        e = inner[0]
        if 'x' not in e:
            e['x'] = center_x - ICON_W_HALF
        if 'y' not in e:
            e['y'] = center_y - ICON_H_HALF
    else:
        for i, e in enumerate(inner):
            angle = 2 * math.pi * i / n_i - math.pi / 2
            if 'x' not in e:
                e['x'] = center_x + int(R_INNER * math.cos(angle)) - ICON_W_HALF
            if 'y' not in e:
                e['y'] = center_y + int(R_INNER * math.sin(angle)) - ICON_H_HALF

    # Anillo exterior
    n_o = len(outer)
    for i, e in enumerate(outer):
        if n_o == 0:
            break
        angle = 2 * math.pi * i / n_o - math.pi / 2
        if 'x' not in e:
            e['x'] = center_x + int(R_OUTER * math.cos(angle)) - ICON_W_HALF
        if 'y' not in e:
            e['y'] = center_y + int(R_OUTER * math.sin(angle)) - ICON_H_HALF

    canvas = data.setdefault('canvas', {})
    canvas['width'] = canvas_w
    canvas['height'] = canvas_h
