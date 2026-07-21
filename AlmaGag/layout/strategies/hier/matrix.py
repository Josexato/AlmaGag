"""
§I (matriz fase × rol) para el algoritmo hier.

La vista más completa (y la más cara de rutear, por eso el spec la ofrece "solo
bajo petición"): cruza las dos agrupaciones — fase en el eje X (columnas) y rol
en el eje Y (filas). Cada nodo cae en la celda (fase, rol); si varios nodos
comparten celda se apilan por orden de flujo. Es el flowchart transfuncional
clásico (BPMN cross-functional): se lee siguiendo las flechas a través de la
grilla.

Requiere `areas` (fases) y `role` por nodo. Se activa con la vista 'matrix'.
"""

from typing import Dict, List
from AlmaGag.layout.strategies.hier.leveling import compute_levels
from AlmaGag.layout.strategies.hier.routing import route_connections
from AlmaGag.layout.strategies.hier.arcs import route_cycle_arcs
from AlmaGag.layout.strategies.hier.labels import assign_connection_label_anchors
from AlmaGag.layout.strategies.hier.areas import (
    MARGIN_X, MARGIN_Y, LABEL_LINE_H, LABEL_GAP, _all_points)
from AlmaGag.config import ICON_WIDTH, ICON_HEIGHT

CELL_W = 224.0                 # ancho de columna (fase)
HEADER_TOP = 46.0              # banda superior: rótulos de fase
HEADER_LEFT = 158.0            # banda izquierda: rótulos de rol
CELL_PAD = 12.0


def _role_order(elements, roles):
    used = [e['role'] for e in elements if e.get('role')]
    order = []
    for r in list((roles or {}).keys()) + used:
        if r in used and r not in order:
            order.append(r)
    return order


def layout_by_matrix(layout):
    """§I: grilla fase×rol. Devuelve {cols, rows, left, top, w, h}. Muta layout."""
    elements = layout.elements
    connections = layout.connections
    by_id = {e['id']: e for e in elements}
    areas = getattr(layout, '_areas', None) or []
    roles = getattr(layout, '_roles', None) or {}

    phase_order = [a['id'] for a in areas]
    phase_label = {a['id']: a.get('label', a['id']) for a in areas}
    phase_of: Dict[str, str] = {}
    for a in areas:
        for m in a.get('members', []):
            if m in by_id:
                phase_of[m] = a['id']
    role_order = _role_order(elements, roles)
    ci = {p: i for i, p in enumerate(phase_order)}
    ri = {r: i for i, r in enumerate(role_order)}

    # Nivel de flujo para apilar dentro de la celda.
    lv = compute_levels(elements, connections)
    level = lv.level

    # Nodos por celda (col=fase, row=rol). Los que no tengan fase o rol caen en
    # una columna/fila "otros" al final para no perderlos.
    if any(e['id'] not in phase_of for e in elements):
        phase_order.append('__otros'); phase_label['__otros'] = '(otros)'
        ci['__otros'] = len(phase_order) - 1
    if any(not e.get('role') for e in elements):
        role_order.append('__sinrol'); ri['__sinrol'] = len(role_order) - 1

    cells: Dict[tuple, List[str]] = {}
    for e in elements:
        c = ci.get(phase_of.get(e['id'], '__otros'))
        r = ri.get(e.get('role') or '__sinrol')
        cells.setdefault((c, r), []).append(e['id'])

    ncol, nrow = len(phase_order), len(role_order)
    # Alto de fila = mayor pila de esa fila (celdas alineadas para los headers).
    row_stack = [1] * nrow
    for (c, r), ids in cells.items():
        row_stack[r] = max(row_stack[r], len(ids))
    slot = ICON_HEIGHT + LABEL_GAP + 3 * LABEL_LINE_H          # icono + etiqueta
    row_h = [s * slot + 2 * CELL_PAD for s in row_stack]
    row_y0, y = [], HEADER_TOP
    for h in row_h:
        row_y0.append(y); y += h
    total_h = y + MARGIN_Y
    col_x0, x = [], HEADER_LEFT
    for _ in range(ncol):
        col_x0.append(x); x += CELL_W
    total_w = x + MARGIN_X

    for (c, r), ids in cells.items():
        ids.sort(key=lambda n: level.get(n, 0))
        for i, nid in enumerate(ids):
            e = by_id[nid]
            e['x'] = col_x0[c] + CELL_W / 2 - ICON_WIDTH / 2
            e['y'] = row_y0[r] + CELL_PAD + i * slot
            e['label_position'] = 'bottom'

    route_connections(layout, lv)
    route_cycle_arcs(layout, lv)
    assign_connection_label_anchors(layout)

    cols = [{'id': p, 'label': phase_label[p], 'x': col_x0[i], 'w': CELL_W}
            for i, p in enumerate(phase_order)]
    rows = [{'id': r, 'label': roles.get(r, {}).get('label', r),
             'color': roles.get(r, {}).get('color'),
             'y': row_y0[i], 'h': row_h[i]} for i, r in enumerate(role_order)]
    layout.canvas = {'width': total_w, 'height': total_h}
    return {'cols': cols, 'rows': rows, 'left': HEADER_LEFT,
            'top': HEADER_TOP, 'w': total_w, 'h': total_h}
