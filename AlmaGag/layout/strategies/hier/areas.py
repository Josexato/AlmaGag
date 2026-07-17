"""
§I27 + §I29 — "Áreas" por fase para el algoritmo hier.

⚠️ NOTA CONCEPTUAL (WISH-ARCH-004, fase 1): lo que aquí se llama "área/ámbito"
es en realidad un **contenedor con semántica de fase** (una caja 2D que corre el
layout adentro y CRECE hacia su contenido), NO el *ámbito* del modelo "El Mapa"
(terreno de forma arbitraria y fija). La palabra "ámbito" queda RESERVADA para
ese terreno futuro; esto es un contenedor/carril-por-fase. Reetiquetado sólo
conceptual por ahora: la clave del schema (`areas`) no cambia hasta decidir la
migración (§9 del WISH). Ver `docs/architecture/WISH-ARCH-004-el-mapa.md`.

Cada "área" es un sub-lienzo recursivo: los criterios A–H (niveles, columnas,
puertos, ruteo, arcos, etiquetas) corren DENTRO sobre sus miembros; la caja se
dimensiona al contenido + padding y se rotula. Las áreas se ordenan por
el flujo (orden declarado) y se empaquetan de izquierda a derecha como
super-nodos (§J33: usar el ancho). Las conexiones inter-área cruzan por el borde
de las cajas (§I29).

Schema SDJF (top-level, opcional):
    "areas": [{ "id", "label", "members": [ids], "parent"?, "color"? }]
Retrocompatible: sin `areas`, el optimizer usa su pipeline normal.
"""

from typing import Dict, List
from AlmaGag.layout.layout import Layout
from AlmaGag.layout.strategies.hier.leveling import compute_levels
from AlmaGag.layout.strategies.hier.columns import compute_columns
from AlmaGag.layout.strategies.hier.routing import route_connections
from AlmaGag.layout.strategies.hier.arcs import route_cycle_arcs
from AlmaGag.layout.strategies.hier.labels import assign_label_sides, assign_connection_label_anchors
from AlmaGag.config import ICON_WIDTH, ICON_HEIGHT

COL_SPACING = 200.0
LEVEL_SPACING = ICON_HEIGHT + 42.0     # §J30
AREA_PAD = 22.0
AREA_HEAD = 30.0                        # banda superior para el rótulo de fase
AREA_GAP = 70.0                         # corredor entre cajas de área
MARGIN_X = 40.0
MARGIN_Y = 40.0
LEGEND_BAND = 54.0                      # franja inferior para la leyenda de roles
LABEL_LINE_H = 16.0                     # alto por línea de etiqueta (§J31)
LABEL_GAP = 12.0                        # aire entre icono y su etiqueta inferior
LABEL_CHAR_W = 6.6                      # ancho aprox. por carácter (12px)


def _translate_member(e, conns_by_from, dx, dy):
    e['x'] += dx
    e['y'] += dy


def _label_halfwidth(e):
    """Media anchura de la etiqueta (centrada bajo el icono)."""
    lbl = e.get('label')
    if not lbl:
        return ICON_WIDTH / 2
    w = max(len(ln) for ln in lbl.split('\n')) * LABEL_CHAR_W
    return max(ICON_WIDTH, w) / 2


def _label_boxes(members):
    """Cajas de etiqueta (centradas bajo cada icono) para incluir en el bbox."""
    boxes = []
    for e in members:
        if 'x' not in e or not e.get('label'):
            continue
        lines = e['label'].count('\n') + 1
        cx = e['x'] + ICON_WIDTH / 2
        hw = _label_halfwidth(e)
        top = e['y'] + ICON_HEIGHT + LABEL_GAP
        boxes.append((cx - hw, top, cx + hw, top + lines * LABEL_LINE_H))
    return boxes


def _sub_layout(members: List[dict], conns: List[dict]):
    """Corre A–H sobre el subgrafo de un área. Devuelve (bbox_w, bbox_h) en
    coords locales (esquina sup-izq del contenido en 0,0). Muta members/conns
    in-place con x/y/computed_path locales. Las etiquetas van CENTRADAS bajo el
    icono; el paso vertical se amplía para alojarlas (§J30)."""
    lv = compute_levels(members, conns)
    cols, wp_abstract = compute_columns(lv, members, conns)

    all_cols = list(cols.values()) + [cx for chain in wp_abstract.values() for cx, _ in chain]
    min_col = min(all_cols) if all_cols else 0
    min_lvl = min(lv.level.values()) if lv.level else 0

    # §J30: paso vertical = icono + etiqueta multilínea + aire.
    maxlines = max([e['label'].count('\n') + 1 for e in members if e.get('label')] + [1])
    pitch = max(LEVEL_SPACING, ICON_HEIGHT + LABEL_GAP + maxlines * LABEL_LINE_H)

    def to_x(col):
        return (col - min_col) * COL_SPACING

    for e in members:
        eid = e['id']
        if eid not in cols:
            continue
        e['x'] = to_x(cols[eid])
        e['y'] = (lv.level[eid] - min_lvl) * pitch
        e['label_position'] = 'bottom'          # §I27: etiqueta bajo el icono

    icon_half = ICON_WIDTH / 2
    for c in conns:
        key = (c.get('from'), c.get('to'))
        if key in wp_abstract and wp_abstract[key]:
            c['waypoints'] = [
                {'x': to_x(cx) + icon_half,
                 'y': (gl - min_lvl) * pitch + ICON_HEIGHT / 2}
                for cx, gl in wp_abstract[key]
            ]

    subL = Layout(elements=members, connections=conns,
                  canvas={'width': 400, 'height': 300})
    route_connections(subL, lv)
    route_cycle_arcs(subL, lv)
    assign_connection_label_anchors(subL)

    xs = [e['x'] for e in members if 'x' in e]
    if not xs:
        return ICON_WIDTH, ICON_HEIGHT + LABEL_GAP + LABEL_LINE_H
    # normalizar a esquina (0,0) incluyendo paths y cajas de etiqueta.
    pts = _all_points(members, conns)
    lboxes = _label_boxes(members)
    minx = min([min(xs)] + [p[0] for p in pts] + [b[0] for b in lboxes])
    miny = min([e['y'] for e in members if 'y' in e] + [p[1] for p in pts])
    _shift(members, conns, -minx, -miny)
    pts = _all_points(members, conns)
    lboxes = _label_boxes(members)
    maxx = max([e['x'] + ICON_WIDTH for e in members if 'x' in e]
               + [p[0] for p in pts] + [b[2] for b in lboxes])
    maxy = max([e['y'] + ICON_HEIGHT for e in members if 'y' in e]
               + [p[1] for p in pts] + [b[3] for b in lboxes])
    return maxx, maxy


def _all_points(members, conns):
    pts = []
    for c in conns:
        cp = c.get('computed_path')
        if cp:
            pts += list(cp.get('points', [])) + list(cp.get('control_points', []))
        for w in c.get('waypoints', []) or []:
            pts.append((w['x'], w['y']))
        if c.get('_label_anchor'):
            pts.append(c['_label_anchor'])
    return pts


def _shift(members, conns, dx, dy):
    for e in members:
        if 'x' in e:
            e['x'] += dx
            e['y'] += dy
    for c in conns:
        cp = c.get('computed_path')
        if cp:
            if 'points' in cp:
                cp['points'] = [(x + dx, y + dy) for x, y in cp['points']]
            if 'control_points' in cp:
                cp['control_points'] = [(x + dx, y + dy) for x, y in cp['control_points']]
        for w in c.get('waypoints', []) or []:
            w['x'] += dx
            w['y'] += dy
        for k in ('_from_port', '_to_port', '_label_anchor'):
            if c.get(k):
                c[k] = (c[k][0] + dx, c[k][1] + dy)


def layout_by_areas(layout, areas_spec):
    """Posiciona `layout` por áreas (§I27) y rutea inter-área (§I29).
    Devuelve la lista de cajas [{id,label,color,x,y,w,h}]. Muta layout."""
    by_id = {e['id']: e for e in layout.elements}
    conns = layout.connections

    # Miembros por área + área de cada nodo. Los nodos sin área declarada van a
    # un área implícita propia (singleton) para no perderlos.
    area_of: Dict[str, str] = {}
    order: List[str] = []
    spec_by_id = {}
    for a in areas_spec:
        spec_by_id[a['id']] = a
        order.append(a['id'])
        for m in a.get('members', []):
            if m in by_id:
                area_of[m] = a['id']
    for e in layout.elements:
        if e['id'] not in area_of:
            aid = f"__solo_{e['id']}"
            spec_by_id[aid] = {'id': aid, 'label': '', 'members': [e['id']]}
            area_of[e['id']] = aid
            order.append(aid)

    # Sub-layout por área sobre su subgrafo intra-área.
    boxes = []
    x_cursor = MARGIN_X
    for aid in order:
        spec = spec_by_id[aid]
        members = [by_id[m] for m in spec['members'] if m in by_id]
        mset = set(spec['members'])
        sub_conns = [c for c in conns
                     if c.get('from') in mset and c.get('to') in mset]
        w, h = _sub_layout(members, sub_conns)
        bx = x_cursor
        by = MARGIN_Y + AREA_HEAD
        # desplazar el contenido del área a su posición global
        _shift(members, sub_conns, bx + AREA_PAD, by + AREA_PAD)
        box_w = w + 2 * AREA_PAD
        box_h = h + 2 * AREA_PAD
        boxes.append({'id': aid, 'label': spec.get('label', ''),
                      'color': spec.get('color'), 'x': bx, 'y': MARGIN_Y,
                      'w': box_w, 'h': box_h + AREA_HEAD, 'solo': aid.startswith('__solo_')})
        x_cursor = bx + box_w + AREA_GAP

    # §I29: ruteo inter-área — sale por el borde de la caja origen, corredor,
    # entra por el borde de la caja destino.
    box_by_area = {b['id']: b for b in boxes}
    _route_inter_area(layout, area_of, box_by_area)

    # canvas: cajas + banda de leyenda inferior
    max_x = max(b['x'] + b['w'] for b in boxes)
    max_y = max(b['y'] + b['h'] for b in boxes)
    layout.canvas = {'width': max_x + MARGIN_X,
                     'height': max_y + LEGEND_BAND + MARGIN_Y}
    return boxes


def _node_border_port(e, side):
    cx, cy = e['x'] + ICON_WIDTH / 2, e['y'] + ICON_HEIGHT / 2
    if side == 'R':
        return (e['x'] + ICON_WIDTH, cy)
    if side == 'L':
        return (e['x'], cy)
    if side == 'T':
        return (cx, e['y'])
    return (cx, e['y'] + ICON_HEIGHT)


def _route_inter_area(layout, area_of, box_by_area):
    by_id = {e['id']: e for e in layout.elements}
    for c in layout.connections:
        f, t = c.get('from'), c.get('to')
        if f not in area_of or t not in area_of or area_of[f] == area_of[t]:
            continue
        sb = box_by_area[area_of[f]]
        tb = box_by_area[area_of[t]]
        s, d = by_id[f], by_id[t]
        # origen sale a la derecha de su caja, destino entra por la izquierda de
        # la suya (áreas empaquetadas izq→der).
        a = _node_border_port(s, 'R')
        b = _node_border_port(d, 'L')
        ex = sb['x'] + sb['w']            # borde derecho caja origen
        en = tb['x']                       # borde izquierdo caja destino
        corr = (ex + en) / 2               # corredor entre cajas
        pts = [a, (ex, a[1]), (corr, a[1]), (corr, b[1]), (en, b[1]), b]
        c['computed_path'] = {'type': 'polyline', 'points': pts}
        c['_from_port'] = a
        c['_to_port'] = b
        c['_inter_area'] = True
