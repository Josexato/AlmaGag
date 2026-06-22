"""
Template 'dashboard' — N containers paralelos sin conexiones entre sí
(WISH-LAYOUT-004 Fase 3).

Patrón objetivo:
- Múltiples containers (>=3) independientes.
- Pocas o cero conexiones inter-container (cada panel es autocontenido).
- Sin un nodo "entry" ni "output" topológico claro.
- Profundidad topológica baja.

Layout: grid ceil(sqrt(N)) cols × ceil(N/cols) filas.
"""

import math

from AlmaGag.layout.templates.base import BaseTemplate
from AlmaGag.layout.templates.features import GraphFeatures


def _extract_id(ref):
    return ref['id'] if isinstance(ref, dict) else ref


class DashboardTemplate(BaseTemplate):
    """Containers paralelos en grid, sin conexiones inter-container."""

    name = 'dashboard'

    def detect_score(self, features: GraphFeatures) -> float:
        """
        Señales positivas para 'dashboard':
        - n_containers >= 3 (paneles).
        - pct_inter_container_connections <= 0.2 (independientes).
        - Profundidad topológica baja (<= 2).
        - Pocos/cero nodos root sin incoming aislados.
        """
        score = 0.0

        if features.n_containers >= 4:
            score += 0.40
        elif features.n_containers >= 3:
            score += 0.30
        elif features.n_containers == 2:
            score += 0.10

        # Independencia entre containers
        if features.n_containers >= 2:
            if features.pct_inter_container_connections <= 0.1:
                score += 0.30
            elif features.pct_inter_container_connections <= 0.25:
                score += 0.15

        # Baja profundidad topológica
        if features.topological_depth <= 2:
            score += 0.15

        # Sin ciclos
        if not features.has_cycles:
            score += 0.05

        # Penalizar si max_degree_ratio alto (sugeriría hub_and_spoke)
        if features.max_degree_ratio >= 3.0:
            score -= 0.20

        # Penalizar si hay keyword 'shared' (sugiere architecture)
        if 'shared' in features.label_keywords or 'agnost' in features.label_keywords:
            score -= 0.20

        return max(0.0, min(score, 1.0))

    def apply(self, data: dict) -> None:
        apply_dashboard_template(data)


def apply_dashboard_template(data):
    """Distribuye containers en grid + free elements debajo."""
    CONTAINER_W_ESTIMATED = 320
    CONTAINER_H_ESTIMATED = 280
    GRID_GAP_X = 60
    GRID_GAP_Y = 60
    PADDING = 60
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

    containers = [e for e in elements if 'contains' in e]
    # Free elements: no contenidos y no containers
    free_elements = [e for e in elements
                     if 'contains' not in e and e['id'] not in contained_ids]

    n = len(containers)
    if n == 0:
        # Sin containers, layout vertical simple
        y = PADDING
        for e in free_elements:
            if 'x' not in e:
                e['x'] = PADDING
            if 'y' not in e:
                e['y'] = y
            y += 130
        canvas = data.setdefault('canvas', {})
        canvas['width'] = 800
        canvas['height'] = y + PADDING
        return

    # Grid: cols x rows
    cols = math.ceil(math.sqrt(n))
    rows = math.ceil(n / cols)

    # Ordenar containers — preservar orden de aparición en SDJF
    for idx, c in enumerate(containers):
        row = idx // cols
        col = idx % cols
        if 'x' not in c:
            c['x'] = PADDING + col * (CONTAINER_W_ESTIMATED + GRID_GAP_X)
        if 'y' not in c:
            c['y'] = PADDING + row * (CONTAINER_H_ESTIMATED + GRID_GAP_Y)

    grid_w = cols * CONTAINER_W_ESTIMATED + (cols - 1) * GRID_GAP_X
    grid_h = rows * CONTAINER_H_ESTIMATED + (rows - 1) * GRID_GAP_Y

    # Free elements debajo del grid (si los hay)
    free_y = PADDING + grid_h + GRID_GAP_Y
    if free_elements:
        # Distribuir horizontalmente al centro
        free_total_w = len(free_elements) * 100 + (len(free_elements) - 1) * 60
        free_start_x = PADDING + (grid_w - free_total_w) // 2
        for i, e in enumerate(free_elements):
            if 'x' not in e:
                e['x'] = free_start_x + i * 160
            if 'y' not in e:
                e['y'] = free_y
        canvas_h = free_y + 150
    else:
        canvas_h = PADDING + grid_h + PADDING

    canvas = data.setdefault('canvas', {})
    canvas['width'] = PADDING * 2 + grid_w
    canvas['height'] = canvas_h
