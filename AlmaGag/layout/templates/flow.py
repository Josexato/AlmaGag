"""
Template 'flow' — secuencia lineal de pasos (WISH-LAYOUT-004 Fase 2).

Patrón objetivo:
- Cadena predominante: cada nodo conecta a uno (o pocos) siguientes.
- Profundidad topológica alta (depth >= 4).
- Branching factor cercano a 1 (poca ramificación).
- Pocos o cero containers.
- Sin ciclos significativos.

Layout: vertical centrado (top-down) o horizontal centrado (left-right)
según orientation. Por ahora solo vertical.
"""

from collections import defaultdict

from AlmaGag.layout.templates.base import BaseTemplate
from AlmaGag.layout.templates.features import GraphFeatures


def _extract_id(ref):
    return ref['id'] if isinstance(ref, dict) else ref


class FlowTemplate(BaseTemplate):
    """Cadena lineal vertical (top-down)."""

    name = 'flow'

    def detect_score(self, features: GraphFeatures) -> float:
        """
        Señales positivas para 'flow':
        - Profundidad >= 4 (cadena larga).
        - Branching factor cercano a 1 (cada nodo continúa a ~1 siguiente).
        - Pocos/cero containers.
        - Sin ciclos.
        - Bonus si hay keywords ('step', 'phase', 'stage', 'pipeline', 'flow').
        """
        score = 0.0

        depth = features.topological_depth
        if depth >= 4:
            score += 0.35
        elif depth == 3:
            score += 0.15

        # Branching cercano a 1 → cadena
        bf = features.branching_factor
        if 0.8 <= bf <= 1.4:
            score += 0.30
        elif 0.6 <= bf <= 1.8:
            score += 0.15

        if features.n_containers == 0:
            score += 0.15
        elif features.n_containers <= 1:
            score += 0.05

        if not features.has_cycles:
            score += 0.10

        if features.label_keywords & {'step', 'phase', 'stage', 'pipeline', 'flow'}:
            score += 0.15

        # Penalizar si el grafo claramente no es cadena (max_degree muy alto)
        if features.max_degree_ratio > 3.0:
            score -= 0.20

        return max(0.0, min(score, 1.0))

    def apply(self, data: dict) -> None:
        apply_flow_template(data)


def _topological_order(elements, connections):
    """
    Devuelve los elementos ROOT (no contenidos) ordenados topológicamente
    en niveles. Cada nivel es una lista de elementos.
    """
    contained_ids = set()
    for e in elements:
        if 'contains' in e:
            for ref in e.get('contains', []):
                contained_ids.add(_extract_id(ref))

    root_elements = [e for e in elements if e['id'] not in contained_ids]
    root_ids = {e['id'] for e in root_elements}

    in_count = {eid: 0 for eid in root_ids}
    adj_out = defaultdict(list)
    for c in connections:
        fr, to = c.get('from'), c.get('to')
        if fr in root_ids and to in root_ids:
            adj_out[fr].append(to)
            in_count[to] += 1

    levels = []
    current = [eid for eid in root_ids if in_count[eid] == 0]
    seen = set()
    while current:
        levels.append(current)
        seen.update(current)
        next_level = []
        for eid in current:
            for nb in adj_out.get(eid, []):
                in_count[nb] -= 1
                if in_count[nb] == 0 and nb not in seen:
                    next_level.append(nb)
        current = next_level

    # Si quedaron nodos sin colocar (ciclos), añadirlos en último nivel
    remaining = [eid for eid in root_ids if eid not in seen]
    if remaining:
        levels.append(remaining)

    by_id = {e['id']: e for e in elements}
    return [[by_id[eid] for eid in lvl] for lvl in levels]


def apply_flow_template(data):
    """Distribuye nodos en cadena vertical centrada."""
    Y_SPACING = 130
    X_SPACING = 200  # cuando un nivel tiene varios nodos
    TOP_MARGIN = 60
    ICON_W_HALF = 40

    elements = data.get('elements', [])
    connections = data.get('connections', [])
    if not elements:
        return

    levels = _topological_order(elements, connections)
    if not levels:
        return

    # Calcular ancho necesario
    max_width = max(len(lvl) for lvl in levels)
    canvas_w = max(max_width * X_SPACING + 200, 600)
    center_x = canvas_w // 2

    y = TOP_MARGIN
    for level in levels:
        n = len(level)
        # Centrar horizontalmente: si n=1 → centro; si n>1 → distribuir
        if n == 1:
            xs = [center_x - ICON_W_HALF]
        else:
            total_w = (n - 1) * X_SPACING
            start_x = center_x - total_w // 2 - ICON_W_HALF
            xs = [start_x + i * X_SPACING for i in range(n)]
        for elem, x in zip(level, xs):
            if 'x' not in elem:
                elem['x'] = x
            if 'y' not in elem:
                elem['y'] = y
        y += Y_SPACING

    canvas = data.setdefault('canvas', {})
    canvas['width'] = canvas_w
    canvas['height'] = y + 100
