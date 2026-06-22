"""
Template 'hub_and_spoke' — un nodo central + N satélites radiales
(WISH-LAYOUT-004 Fase 2, motivado por inspección SD-WAN del usuario).

Patrón objetivo:
- 1 nodo con degree >> promedio (el hub).
- N nodos con degree bajo y conexiones principalmente al hub.
- Pocas/cero conexiones entre spokes.

Layout: hub en el centro del canvas, spokes distribuidos en círculo
alrededor. Si hay un "hub secundario" (segundo nodo con degree alto)
se posiciona arriba o abajo del hub principal.
"""

import math
from collections import defaultdict

from AlmaGag.layout.templates.base import BaseTemplate
from AlmaGag.layout.templates.features import GraphFeatures


def _extract_id(ref):
    return ref['id'] if isinstance(ref, dict) else ref


class HubAndSpokeTemplate(BaseTemplate):
    """Hub central rodeado de spokes en distribución radial."""

    name = 'hub_and_spoke'

    def detect_score(self, features: GraphFeatures) -> float:
        """
        Señales positivas para 'hub_and_spoke':
        - max_degree_ratio alto (>= 2.5): 1 nodo concentra conexiones.
        - n_root_elements >= 4 (un hub solo no tiene sentido).
        - Pocos ciclos.
        - Profundidad topológica baja (1-2): el hub es el centro de
          todo, no hay encadenamiento profundo.
        - Bonus por keywords ('hub', 'central', 'branch', 'spoke', 'edge').
        """
        score = 0.0

        ratio = features.max_degree_ratio
        if ratio >= 3.0:
            score += 0.40
        elif ratio >= 2.0:
            score += 0.25
        elif ratio >= 1.5:
            score += 0.10

        if features.n_root_elements >= 4:
            score += 0.15

        if features.topological_depth <= 2:
            score += 0.15

        if not features.has_cycles or features.n_self_loops > 0:
            # ciclos self-loops son comunes en hub-spoke (heartbeat),
            # se aceptan; ciclos reales penalizan
            if not features.has_cycles:
                score += 0.10

        if features.label_keywords & {'hub', 'central', 'branch', 'spoke', 'edge'}:
            score += 0.20

        # Fase 4: bonus fuerte si el usuario declaró un `role: hub`
        declared_role_values = set(features.declared_roles.values())
        if 'hub' in declared_role_values:
            score += 0.25
        if 'spoke' in declared_role_values:
            score += 0.10

        # Penalizar si tiene muchos containers (eso sugiere architecture)
        if features.n_containers >= 2:
            score -= 0.15

        return max(0.0, min(score, 1.0))

    def apply(self, data: dict) -> None:
        apply_hub_and_spoke_template(data)


def _find_hub(elements, connections):
    """
    Identifica el hub: nodo root con mayor (in + out) degree, salvo que el
    usuario haya declarado `"role": "hub"` en algún elemento (Fase 4: ese
    override gana sobre la heurística).
    Resuelve endpoints contenidos a sus containers.
    """
    contained_ids = set()
    container_membership = {}
    for e in elements:
        if 'contains' in e:
            for ref in e.get('contains', []):
                cid = _extract_id(ref)
                contained_ids.add(cid)
                container_membership[cid] = e['id']

    root_ids = {e['id'] for e in elements if e['id'] not in contained_ids}

    # Fase 4: si el usuario declara `role: hub`, usar ese
    for e in elements:
        if e.get('role') == 'hub' and e['id'] in root_ids:
            hub_id = e['id']
            spokes = [eid for eid in root_ids if eid != hub_id]
            return hub_id, spokes

    degree = defaultdict(int)
    for c in connections:
        fr = container_membership.get(c.get('from'), c.get('from'))
        to = container_membership.get(c.get('to'), c.get('to'))
        if fr in root_ids:
            degree[fr] += 1
        if to in root_ids:
            degree[to] += 1

    if not degree:
        return None, []

    hub_id = max(degree, key=degree.get)
    spokes = [eid for eid in root_ids if eid != hub_id]
    return hub_id, spokes


def apply_hub_and_spoke_template(data):
    """
    Distribución radial: hub al centro, spokes en círculo alrededor.

    Si hay muchos spokes (>= 8), usa dos columnas (izq/der del hub) para
    diagramas tipo SD-WAN.
    """
    RADIUS = 320
    ICON_W_HALF = 40
    ICON_H_HALF = 25
    HUB_OFFSET_BOOST = 0  # el hub se centra; mantenemos esto en 0
    CANVAS_PADDING = 120

    elements = data.get('elements', [])
    connections = data.get('connections', [])
    if not elements:
        return

    hub_id, spoke_ids = _find_hub(elements, connections)
    if not hub_id:
        return

    by_id = {e['id']: e for e in elements}
    hub = by_id[hub_id]
    spokes = [by_id[sid] for sid in spoke_ids]

    n = len(spokes)
    if n == 0:
        # Sin spokes — solo hub
        canvas_w = 600
        canvas_h = 400
        center_x, center_y = canvas_w // 2, canvas_h // 2
        if 'x' not in hub:
            hub['x'] = center_x - ICON_W_HALF
        if 'y' not in hub:
            hub['y'] = center_y - ICON_H_HALF
        canvas = data.setdefault('canvas', {})
        canvas['width'] = canvas_w
        canvas['height'] = canvas_h
        return

    # Decidir layout: círculo (n<8) o dos columnas (n>=8)
    if n >= 8:
        # Layout estilo SD-WAN: spokes en columnas izquierda y derecha
        canvas_w = 2 * RADIUS + 400 + CANVAS_PADDING * 2
        per_side = math.ceil(n / 2)
        ROW_SPACING = 180
        canvas_h = per_side * ROW_SPACING + CANVAS_PADDING * 2
        center_x = canvas_w // 2
        center_y = canvas_h // 2

        # Hub centro
        if 'x' not in hub:
            hub['x'] = center_x - ICON_W_HALF
        if 'y' not in hub:
            hub['y'] = center_y - ICON_H_HALF

        # Spokes: la mitad izq, la mitad der
        left_count = n // 2
        for i, spoke in enumerate(spokes):
            if i < left_count:
                # Lado izquierdo
                row = i
                x = CANVAS_PADDING
                y = CANVAS_PADDING + row * ROW_SPACING
            else:
                # Lado derecho
                row = i - left_count
                x = canvas_w - CANVAS_PADDING - ICON_W_HALF * 2
                y = CANVAS_PADDING + row * ROW_SPACING
            if 'x' not in spoke:
                spoke['x'] = x
            if 'y' not in spoke:
                spoke['y'] = y
    else:
        # Layout radial circular
        canvas_w = 2 * RADIUS + CANVAS_PADDING * 2
        canvas_h = 2 * RADIUS + CANVAS_PADDING * 2
        center_x = canvas_w // 2
        center_y = canvas_h // 2

        if 'x' not in hub:
            hub['x'] = center_x - ICON_W_HALF
        if 'y' not in hub:
            hub['y'] = center_y - ICON_H_HALF

        for i, spoke in enumerate(spokes):
            angle = 2 * math.pi * i / n - math.pi / 2  # empezar arriba
            x = center_x + int(RADIUS * math.cos(angle)) - ICON_W_HALF
            y = center_y + int(RADIUS * math.sin(angle)) - ICON_H_HALF
            if 'x' not in spoke:
                spoke['x'] = x
            if 'y' not in spoke:
                spoke['y'] = y

    canvas = data.setdefault('canvas', {})
    canvas['width'] = canvas_w
    canvas['height'] = canvas_h
