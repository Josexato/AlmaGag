"""
Template 'sequence' — diagrama de secuencia con swimlanes
(WISH-LAYOUT-004 Fase 3).

Patrón objetivo:
- Pocos "actores" (~3-6 columnas).
- Muchas conexiones entre los mismos pares (cardinalidad alta entre nodos).
- Las conexiones modelan mensajes/eventos ordenados temporalmente.

Detección complicada sin metadata explícita: muchas veces requiere que el
SDJF indique `"layout_template": "sequence"` manualmente. El scorer es
conservador y solo dispara con señales fuertes.

Layout: actores como columnas verticales (swimlanes) en una fila al tope;
mensajes como flechas horizontales entre lanes a alturas crecientes.

NOTA v1: como el SDJF actual no modela "tiempo" explícitamente, asumimos
que el ORDEN de aparición en `connections` representa el tiempo. Cada
conexión genera una "fila" de mensaje.
"""

from collections import defaultdict, Counter

from AlmaGag.layout.templates.base import BaseTemplate
from AlmaGag.layout.templates.features import GraphFeatures


def _extract_id(ref):
    return ref['id'] if isinstance(ref, dict) else ref


class SequenceTemplate(BaseTemplate):
    """Actores como columnas + mensajes horizontales ordenados."""

    name = 'sequence'

    def detect_score(self, features: GraphFeatures) -> float:
        """
        Señales positivas para 'sequence':
        - Pocos elementos root (3-7 actores).
        - Muchas conexiones (alta ratio conn/nodes).
        - Ciclos / conexiones bidireccionales (request/response).
        - Sin containers.
        - Sin keyword fuerte de otros patrones.

        En la práctica, sin metadata explícita, este detector RARA VEZ
        debería ganar. Es más útil como `layout_template: "sequence"`
        manual.
        """
        score = 0.0

        # Número de actores razonable
        if 3 <= features.n_root_elements <= 7:
            score += 0.20

        # Alta densidad de conexiones (mensajes >> nodos)
        if features.n_root_elements > 0:
            conn_per_node = features.n_connections / features.n_root_elements
            if conn_per_node >= 2.0:
                score += 0.30
            elif conn_per_node >= 1.5:
                score += 0.15

        # Sin containers
        if features.n_containers == 0:
            score += 0.10

        # Ciclos (request/response típico)
        if features.has_cycles:
            score += 0.10

        # Keywords negativos: evitar pisar otros patrones
        if features.label_keywords & {'shared', 'agnost', 'hub', 'spoke', 'branch'}:
            score -= 0.20

        return max(0.0, min(score, 1.0))

    def apply(self, data: dict) -> None:
        apply_sequence_template(data)


def apply_sequence_template(data):
    """
    Actores como columnas en y=top, una fila vertical (lane) bajo cada uno.
    Mensajes (conexiones) ordenados por aparición.
    """
    LANE_X_SPACING = 220
    ACTOR_TOP_Y = 60
    MESSAGE_START_Y = 180
    MESSAGE_SPACING_Y = 60
    PADDING = 80
    ICON_W_HALF = 40

    elements = data.get('elements', [])
    connections = data.get('connections', [])
    if not elements:
        return

    contained_ids = set()
    for e in elements:
        if 'contains' in e:
            for ref in e.get('contains', []):
                contained_ids.add(_extract_id(ref))

    actors = [e for e in elements if e['id'] not in contained_ids and 'contains' not in e]
    n = len(actors)
    if n == 0:
        return

    # Ordenar actores: el más conectado al medio, los demás en orden de aparición
    degree = defaultdict(int)
    for c in connections:
        degree[c.get('from', '')] += 1
        degree[c.get('to', '')] += 1
    # Mantener orden original (estable)
    # No reordenamos: respetamos la declaración del usuario para sequence.

    canvas_w = max(PADDING * 2 + n * LANE_X_SPACING, 600)
    center_x = canvas_w // 2
    total_actors_w = (n - 1) * LANE_X_SPACING
    start_x = center_x - total_actors_w // 2 - ICON_W_HALF

    for i, actor in enumerate(actors):
        if 'x' not in actor:
            actor['x'] = start_x + i * LANE_X_SPACING
        if 'y' not in actor:
            actor['y'] = ACTOR_TOP_Y

    # Canvas height suficiente para todos los mensajes
    n_msg = len([c for c in connections if c.get('label')])
    canvas_h = MESSAGE_START_Y + max(n_msg, 1) * MESSAGE_SPACING_Y + PADDING

    canvas = data.setdefault('canvas', {})
    canvas['width'] = canvas_w
    canvas['height'] = canvas_h
