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

import logging
from typing import Dict, List
from AlmaGag.layout.layout import Layout
from AlmaGag.layout.strategies.hier.leveling import compute_levels
from AlmaGag.layout.strategies.hier.columns import compute_columns
from AlmaGag.layout.strategies.hier.routing import route_connections
from AlmaGag.layout.strategies.hier.arcs import route_cycle_arcs
from AlmaGag.layout.strategies.hier.labels import assign_label_sides, assign_connection_label_anchors
from AlmaGag.config import ICON_WIDTH, ICON_HEIGHT

logger = logging.getLogger('AlmaGag')

COL_SPACING = 200.0
LEVEL_SPACING = ICON_HEIGHT + 42.0     # §J30
AREA_PAD = 22.0
AREA_HEAD = 30.0                        # banda superior para el rótulo de fase
AREA_GAP = 70.0                         # corredor entre cajas de área
MARGIN_X = 40.0
MARGIN_Y = 40.0
ASPECT_TARGET = 1.5                     # X91: objetivo de la envoltura 2D

# WISH-LAYOUT-020 (X91): `area.role` orienta la banda de la macro-grilla —
# control/feeder arriba (gobiernan/alimentan), chain al centro (la cadena se
# lee), external abajo (sale de la lámina), overlay al fondo (banda de bus).
_ROLE_BAND = {'feeder': 0, 'control': 0, 'chain': 1,
              'external': 2, 'overlay': 3}
_BAND_DEFAULT = 1
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

    # PASO 1 — sub-layout local por área (contenido en 0,0) y dimensiones.
    dims = []
    for aid in order:
        spec = spec_by_id[aid]
        members = [by_id[m] for m in spec['members'] if m in by_id]
        mset = set(spec['members'])
        sub_conns = [c for c in conns
                     if c.get('from') in mset and c.get('to') in mset]
        w, h = _sub_layout(members, sub_conns)
        dims.append({'aid': aid, 'spec': spec, 'members': members,
                     'conns': sub_conns,
                     'w': w + 2 * AREA_PAD,
                     'h': h + 2 * AREA_PAD + AREA_HEAD})

    # PASO 2 — macro-plano. Precedencia (X91/X91b): `canvas.partition`
    # declarado > `area.role` > derivación por aspecto.
    partition = (layout.canvas or {}).get('partition') \
        if isinstance(layout.canvas, dict) else None
    cells = rows = None
    if partition:
        placed = _place_partition(dims, partition)
        if placed:
            kind, payload = placed
            if kind == 'cells':
                cells = payload
            else:
                rows = payload
    if rows is None and cells is None:
        rows = _macro_rows(dims)

    # PASO 3 — colocar: en su celda declarada (X91b) o fila por fila (X91).
    boxes = []
    if cells is not None:
        for d in dims:
            spec = d['spec']
            bx, by, bw, bh = cells[d['aid']]
            _shift(d['members'], d['conns'],
                   bx + AREA_PAD, by + AREA_HEAD + AREA_PAD)
            boxes.append({'id': d['aid'], 'label': spec.get('label', ''),
                          'color': spec.get('color'), 'x': bx, 'y': by,
                          'w': bw, 'h': bh,
                          'solo': d['aid'].startswith('__solo_')})
    else:
        y_cursor = MARGIN_Y
        for row in rows:
            x_cursor = MARGIN_X
            row_h = max(d['h'] for d in row)
            for d in row:
                spec = d['spec']
                bx, by = x_cursor, y_cursor
                _shift(d['members'], d['conns'],
                       bx + AREA_PAD, by + AREA_HEAD + AREA_PAD)
                boxes.append({'id': d['aid'], 'label': spec.get('label', ''),
                              'color': spec.get('color'), 'x': bx, 'y': by,
                              'w': d['w'], 'h': d['h'],
                              'solo': d['aid'].startswith('__solo_')})
                x_cursor = bx + d['w'] + AREA_GAP
            y_cursor += row_h + AREA_GAP

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


def _place_partition(dims, partition):
    """WISH-LAYOUT-021 (X91b): `canvas.partition` — el macro-plano DECLARADO.

    Schemes enchufables: `bsp` (lista ordenada de colocaciones relativas —
    la primera con anchor "base", las demás con at right_of|below|left_of|
    above de un área YA colocada) y `grid` (filas de ids, azúcar). Los
    tamaños son PROPORCIONES, nunca píxeles: la partición entera se escala
    al contenido real (§P59 — si los miembros no caben en la proporción de
    su celda, toda la grilla crece manteniendo los ratios).

    Devuelve ('cells', {aid: (x, y, w, h)}) para bsp, ('rows', filas) para
    grid, o None si el plan es inválido — el porqué se NOMBRA y la
    precedencia cae a role/derivación (X90: nunca silencio).
    """
    by_aid = {d['aid']: d for d in dims}
    scheme = (partition or {}).get('scheme', 'bsp')
    if scheme == 'grid':
        declared = partition.get('rows') or []
        rows, seen = [], set()
        for r in declared:
            row = []
            for aid in r:
                if aid not in by_aid:
                    logger.warning(f"[partition] área '{aid}' del plan no "
                                   f"existe en areas[] — se ignora")
                    continue
                row.append(by_aid[aid])
                seen.add(aid)
            if row:
                rows.append(row)
        rest = [d for d in dims if d['aid'] not in seen]
        named = [d['aid'] for d in rest if not d['aid'].startswith('__solo_')]
        if named:
            logger.warning(f"[partition] área(s) fuera del plan: "
                           f"{', '.join(named)} — van en fila propia al final")
        if rest:
            rows.append(rest)
        return ('rows', rows) if rows else None
    if scheme != 'bsp':
        logger.warning(f"[partition] scheme '{scheme}' desconocido "
                       f"(bsp | grid) — cae a role/derivación")
        return None

    splits = partition.get('splits') or []
    if not splits:
        logger.warning("[partition] bsp sin splits — cae a role/derivación")
        return None
    units = {}                      # aid -> (ux, uy, uw, uh) en unidades
    for i, s in enumerate(splits):
        aid = s.get('area')
        if aid not in by_aid:
            logger.warning(f"[partition] splits[{i}]: área '{aid}' no existe "
                           f"en areas[] — plan inválido, cae a role/derivación")
            return None
        size = s.get('size') or []
        if len(size) != 2 or not all(
                isinstance(v, (int, float)) and v > 0 for v in size):
            logger.warning(f"[partition] splits[{i}] ('{aid}'): size debe ser "
                           f"[ancho, alto] en proporciones — plan inválido")
            return None
        uw, uh = float(size[0]), float(size[1])
        if i == 0:
            if s.get('anchor') != 'base':
                logger.warning(f"[partition] el primer split debe ser "
                               f"anchor 'base' — plan inválido")
                return None
            units[aid] = (0.0, 0.0, uw, uh)
            continue
        at, of = s.get('at'), s.get('of')
        if of not in units:
            logger.warning(f"[partition] splits[{i}] ('{aid}'): of='{of}' "
                           f"aún no está colocado — plan inválido")
            return None
        ox, oy, ow, oh = units[of]
        if at == 'right_of':
            units[aid] = (ox + ow, oy, uw, uh)
        elif at == 'below':
            units[aid] = (ox, oy + oh, uw, uh)
        elif at == 'left_of':
            units[aid] = (ox - uw, oy, uw, uh)
        elif at == 'above':
            units[aid] = (ox, oy - uh, uw, uh)
        else:
            logger.warning(f"[partition] splits[{i}] ('{aid}'): at='{at}' "
                           f"desconocido (right_of|below|left_of|above) — "
                           f"plan inválido")
            return None

    # Escala px/unidad: TODA celda aloja su contenido (+ corredor).
    sx = max((by_aid[a]['w'] + AREA_GAP) / u[2] for a, u in units.items())
    sy = max((by_aid[a]['h'] + AREA_GAP) / u[3] for a, u in units.items())
    minx = min(u[0] for u in units.values())
    miny = min(u[1] for u in units.values())
    cells = {}
    for aid, (ux, uy, uw, uh) in units.items():
        cells[aid] = (MARGIN_X + (ux - minx) * sx + AREA_GAP / 2,
                      MARGIN_Y + (uy - miny) * sy + AREA_GAP / 2,
                      uw * sx - AREA_GAP, uh * sy - AREA_GAP)

    # Áreas fuera del plan: fila propia bajo la grilla, nombradas.
    rest = [d for d in dims if d['aid'] not in units]
    named = [d['aid'] for d in rest if not d['aid'].startswith('__solo_')]
    if named:
        logger.warning(f"[partition] área(s) fuera del plan: "
                       f"{', '.join(named)} — van en fila propia al final")
    if rest:
        base_y = MARGIN_Y + max(
            (u[1] - miny + u[3]) * sy for u in units.values()) + AREA_GAP / 2
        x_cursor = MARGIN_X
        for d in rest:
            cells[d['aid']] = (x_cursor, base_y, d['w'], d['h'])
            x_cursor += d['w'] + AREA_GAP

    ratio = partition.get('ratio')
    if isinstance(ratio, (list, tuple)) and len(ratio) == 2 and all(ratio):
        gw = max(u[0] - minx + u[2] for u in units.values())
        gh = max(u[1] - miny + u[3] for u in units.values())
        want = float(ratio[0]) / float(ratio[1])
        got = gw / gh
        if abs(got - want) / want > 0.02:
            logger.warning(f"[partition] los splits arman {gw:g}×{gh:g} "
                           f"(={got:.2f}) pero ratio declara "
                           f"{ratio[0]}:{ratio[1]} (={want:.2f}) — "
                           f"manda la suma de los splits")
    return ('cells', cells)


def _macro_rows(dims):
    """WISH-LAYOUT-020 (X91): decide las FILAS de la macro-grilla de áreas.

    Precedencia (partition > role > derivación; `canvas.partition` es
    WISH-LAYOUT-021):
    1. `area.role` declarado en ALGUNA área → bandas semánticas
       (_ROLE_BAND); las áreas sin role van a la banda central.
    2. Sin roles: si la fila única respeta el aspecto §O52 se queda tal
       cual (estabilidad de los fixtures sanos); si lo viola, envoltura
       tipo estantería EN ORDEN DECLARADO hacia ASPECT_TARGET — jamás una
       cinta 1×N desproporcionada (tabernero: 9 áreas en 11129×893).
    """
    from AlmaGag.layout.metrics import ASPECT_RANGE
    if not dims:
        return []
    roles = {d['aid']: (d['spec'].get('role') or '') for d in dims}
    if any(r in _ROLE_BAND for r in roles.values()):
        bands = {}
        for d in dims:
            b = _ROLE_BAND.get(roles[d['aid']], _BAND_DEFAULT)
            bands.setdefault(b, []).append(d)
        return [bands[k] for k in sorted(bands)]

    total_w = sum(d['w'] for d in dims) + AREA_GAP * (len(dims) - 1)
    max_h = max(d['h'] for d in dims)
    if total_w / max_h <= ASPECT_RANGE[1] or len(dims) < 2:
        return [dims]
    # Envoltura: ancho objetivo hacia ASPECT_TARGET (nunca más angosto que
    # la caja más ancha).
    area_total = sum(d['w'] * d['h'] for d in dims)
    target_w = max(max(d['w'] for d in dims),
                   (area_total * ASPECT_TARGET) ** 0.5)
    rows, row, roww = [], [], 0.0
    for d in dims:
        w = d['w'] + (AREA_GAP if row else 0.0)
        if row and roww + w > target_w:
            rows.append(row)
            row, roww = [], 0.0
            w = d['w']
        row.append(d)
        roww += w
    if row:
        rows.append(row)
    return rows


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
    """§I29 generalizado (WISH-LAYOUT-020): con la macro-grilla 2D las cajas
    ya no están sólo a la derecha — el lado de salida/entrada se elige por el
    EJE DOMINANTE entre centros de caja (R→L, L→R, B→T o T→B), con el
    corredor a mitad de camino entre los bordes enfrentados."""
    by_id = {e['id']: e for e in layout.elements}
    for c in layout.connections:
        f, t = c.get('from'), c.get('to')
        if f not in area_of or t not in area_of or area_of[f] == area_of[t]:
            continue
        sb = box_by_area[area_of[f]]
        tb = box_by_area[area_of[t]]
        s, d = by_id[f], by_id[t]
        dx = (tb['x'] + tb['w'] / 2) - (sb['x'] + sb['w'] / 2)
        dy = (tb['y'] + tb['h'] / 2) - (sb['y'] + sb['h'] / 2)
        if abs(dx) >= abs(dy):
            if dx >= 0:                    # destino a la derecha
                a = _node_border_port(s, 'R')
                b = _node_border_port(d, 'L')
                ex, en = sb['x'] + sb['w'], tb['x']
            else:                          # destino a la izquierda
                a = _node_border_port(s, 'L')
                b = _node_border_port(d, 'R')
                ex, en = sb['x'], tb['x'] + tb['w']
            corr = (ex + en) / 2
            pts = [a, (ex, a[1]), (corr, a[1]), (corr, b[1]), (en, b[1]), b]
        else:
            if dy >= 0:                    # destino abajo
                a = _node_border_port(s, 'B')
                b = _node_border_port(d, 'T')
                ex, en = sb['y'] + sb['h'], tb['y']
            else:                          # destino arriba
                a = _node_border_port(s, 'T')
                b = _node_border_port(d, 'B')
                ex, en = sb['y'], tb['y'] + tb['h']
            corr = (ex + en) / 2
            pts = [a, (a[0], ex), (a[0], corr), (b[0], corr), (b[0], en), b]
        c['computed_path'] = {'type': 'polyline', 'points': pts}
        c['_from_port'] = a
        c['_to_port'] = b
        c['_inter_area'] = True
