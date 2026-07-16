"""
§I28 — Carriles por rol (lanes) para el algoritmo hier.

Partición por responsable: cada carril fija la banda X (columna) de sus
miembros y deja correr el flujo en Y (nivel topológico). Se dibuja como franja
rotulada de fondo; cruzar carril = handoff. A diferencia de §I27 (áreas =
sub-lienzo 2D, opcional, anidable), el carril es una restricción de UNA
coordenada, exhaustiva y plana.

Schema SDJF (top-level, opcional):
    "lanes": [{ "id", "label", "members": [ids], "color"? }]
Si no hay `lanes`, se derivan del campo `role` de cada nodo (un carril por rol,
en el orden del mapa `roles`). Se activa con la vista 'lanes'.
"""

from typing import Dict, List
from AlmaGag.layout.layout import Layout
from AlmaGag.layout.strategies.hier.leveling import compute_levels
from AlmaGag.layout.strategies.hier.routing import route_connections
from AlmaGag.layout.strategies.hier.arcs import route_cycle_arcs
from AlmaGag.layout.strategies.hier.labels import assign_connection_label_anchors
from AlmaGag.layout.strategies.hier.areas import (
    LEVEL_SPACING, MARGIN_X, MARGIN_Y, LABEL_LINE_H, LABEL_GAP, _all_points)
from AlmaGag.config import ICON_WIDTH, ICON_HEIGHT

LANE_WIDTH = 210.0                 # ancho mínimo de un carril (icono + etiqueta)
LANE_SLOT = 210.0                  # ancho reservado por nodo dentro de un carril
LANE_HEAD = 30.0                   # banda superior para el rótulo del carril
LANE_TOP = MARGIN_Y + LANE_HEAD


def _lane_defs(layout):
    """Devuelve [(id, label, color)] en orden de dibujo y {node: lane_id}."""
    roles = getattr(layout, '_roles', None) or {}
    lanes = getattr(layout, '_lanes', None)
    lane_of: Dict[str, str] = {}
    defs = []
    if lanes:
        for l in lanes:
            defs.append((l['id'], l.get('label', l['id']), l.get('color')))
            for m in l.get('members', []):
                lane_of[m] = l['id']
    else:
        used = [e['role'] for e in layout.elements if e.get('role')]
        seen = []
        for r in list(roles.keys()) + used:      # orden del mapa roles primero
            if r in used and r not in seen:
                seen.append(r)
        for r in seen:
            spec = roles.get(r, {})
            defs.append((r, spec.get('label', r), spec.get('color')))
        for e in layout.elements:
            if e.get('role'):
                lane_of[e['id']] = e['role']
    # nodos sin carril → un carril implícito al final
    orphan = [e['id'] for e in layout.elements if e['id'] not in lane_of]
    if orphan:
        defs.append(('__nolane', '', None))
        for oid in orphan:
            lane_of[oid] = '__nolane'
    return defs, lane_of


def layout_by_lanes(layout):
    """§I28: posiciona por carriles de rol. Y = nivel de flujo, X = banda del
    carril. Devuelve la lista de franjas [{id,label,color,x,y,w,h}]. Muta
    layout."""
    elements = layout.elements
    connections = layout.connections
    defs, lane_of = _lane_defs(layout)
    lane_index = {lid: i for i, (lid, _, _) in enumerate(defs)}

    # Y por nivel de flujo (reusa §A) + paso compacto ampliado por etiqueta.
    lv = compute_levels(elements, connections)
    level = lv.level
    min_lvl = min(level.values()) if level else 0
    maxlines = max([e['label'].count('\n') + 1 for e in elements if e.get('label')] + [1])
    pitch = max(LEVEL_SPACING, ICON_HEIGHT + LABEL_GAP + maxlines * LABEL_LINE_H)

    # Nodos por (carril, nivel) para repartir horizontalmente si coinciden.
    groups: Dict[tuple, List[str]] = {}
    for e in elements:
        lid = lane_of[e['id']]
        key = (lid, round(level.get(e['id'], 0), 1))
        groups.setdefault(key, []).append(e['id'])

    # Ancho de carril proporcional al máximo de nodos que comparten un nivel:
    # cada nodo reserva un SLOT (icono + su etiqueta) para que dos etiquetas
    # centradas no se solapen (bug de satélites en el mismo carril/nivel).
    lane_maxn = {lid: 1 for lid, _, _ in defs}
    for (lid, _lvl), ids in groups.items():
        lane_maxn[lid] = max(lane_maxn[lid], len(ids))
    lane_w = {lid: max(LANE_WIDTH, lane_maxn[lid] * LANE_SLOT) for lid, _, _ in defs}
    lane_x0, _cur = {}, MARGIN_X
    for lid, _, _ in defs:
        lane_x0[lid] = _cur
        _cur += lane_w[lid]
    total_w = _cur + MARGIN_X

    def band_center(lid):
        return lane_x0[lid] + lane_w[lid] / 2

    by_id = {e['id']: e for e in elements}
    for (lid, lvl), ids in groups.items():
        ids.sort()
        n = len(ids)
        for i, nid in enumerate(ids):
            cx = band_center(lid) + (i - (n - 1) / 2) * LANE_SLOT
            e = by_id[nid]
            e['x'] = cx - ICON_WIDTH / 2
            e['y'] = LANE_TOP + (level.get(nid, 0) - min_lvl) * pitch
            e['label_position'] = 'bottom'

    # Ruteo: reusa §C–§E; cruzar carriles = handoff (arista ortogonal/oblicua).
    route_connections(layout, lv)
    route_cycle_arcs(layout, lv)
    assign_connection_label_anchors(layout)

    # Alto total y franjas de carril (fondo, de arriba a abajo).
    ys = [e['y'] + ICON_HEIGHT for e in elements if 'y' in e]
    pts = _all_points(elements, connections)
    content_bottom = max(ys + [p[1] for p in pts]) if ys else LANE_TOP
    total_h = content_bottom + LABEL_GAP + maxlines * LABEL_LINE_H + MARGIN_Y

    strips = []
    for lid, label, color in defs:
        if lid == '__nolane':
            continue
        strips.append({'id': lid, 'label': label, 'color': color,
                       'x': lane_x0[lid], 'y': MARGIN_Y, 'w': lane_w[lid],
                       'h': total_h - MARGIN_Y})

    layout.canvas = {'width': total_w, 'height': total_h}
    return strips
