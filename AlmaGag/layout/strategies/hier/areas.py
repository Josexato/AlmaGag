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


def _sub_layout(members: List[dict], conns: List[dict], aspect_hint=None):
    """Corre A–H sobre el subgrafo de un área. Devuelve (bbox_w, bbox_h) en
    coords locales (esquina sup-izq del contenido en 0,0). Muta members/conns
    in-place con x/y/computed_path locales. Las etiquetas van CENTRADAS bajo el
    icono; el paso vertical se amplía para alojarlas (§J30).

    `aspect_hint` (WISH-LAYOUT-024): proporción ancho/alto de la CELDA
    declarada en `canvas.partition` para esta área. Un bloque-LISTA (sin
    aristas internas) no tiene forma propia — sin la pista sale en fila
    (nivel 0 de A); con ella se envuelve en la grilla que mejor aproxima
    la celda (BMC: celda [2,4] → columna, [5,2] → fila)."""
    lv = compute_levels(members, conns)
    cols, wp_abstract = compute_columns(lv, members, conns)

    all_cols = list(cols.values()) + [cx for chain in wp_abstract.values() for cx, _ in chain]
    min_col = min(all_cols) if all_cols else 0
    min_lvl = min(lv.level.values()) if lv.level else 0

    # §J30: paso vertical = icono + etiqueta multilínea + aire.
    # WISH-LAYOUT-022: si el corredor lleva rótulos de arista, el paso
    # reserva su línea también — el título del nivel N y el rótulo anclado
    # junto al nivel N+1 peleaban el mismo espacio (los ≈70%/≈30% del
    # tabernero montados sobre los títulos del almacén).
    maxlines = max([e['label'].count('\n') + 1 for e in members if e.get('label')] + [1])
    conn_lines = LABEL_LINE_H + 6.0 if any(c.get('label') for c in conns) else 0.0
    pitch = max(LEVEL_SPACING,
                ICON_HEIGHT + LABEL_GAP + maxlines * LABEL_LINE_H + conn_lines)

    def to_x(col):
        return (col - min_col) * COL_SPACING

    if not conns and len(members) > 2 and aspect_hint:
        # WISH-LAYOUT-024: bloque-lista con celda declarada — grilla que
        # aproxima la proporción de la celda (cols candidatas 1..n).
        n = len(members)
        best_cols = min(
            range(1, n + 1),
            key=lambda k: abs((k * COL_SPACING)
                              / ((-(-n // k)) * pitch) - aspect_hint))
        for i, e in enumerate(members):
            e['x'] = (i % best_cols) * COL_SPACING
            e['y'] = (i // best_cols) * pitch
            e['label_position'] = 'bottom'
    else:
        for e in members:
            eid = e['id']
            if eid not in cols:
                continue
            e['x'] = to_x(cols[eid])
            e['y'] = (lv.level[eid] - min_lvl) * pitch
            e['label_position'] = 'bottom'      # §I27: etiqueta bajo el icono

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

    # WISH-LAYOUT-024: si hay partition bsp declarada, la PROPORCIÓN de la
    # celda de cada área se conoce antes del sub-layout — informa la forma
    # de los bloques-lista (celda alta → columna, celda ancha → fila).
    partition_spec = (layout.canvas or {}).get('partition') \
        if isinstance(layout.canvas, dict) else None
    cell_hint = {}
    if partition_spec and partition_spec.get('scheme', 'bsp') == 'bsp':
        for s in partition_spec.get('splits') or []:
            size = s.get('size') or []
            if s.get('area') and len(size) == 2 and all(
                    isinstance(v, (int, float)) and v > 0 for v in size):
                cell_hint[s['area']] = float(size[0]) / float(size[1])

    # PASO 1 — sub-layout local por área (contenido en 0,0) y dimensiones.
    dims = []
    for aid in order:
        spec = spec_by_id[aid]
        members = [by_id[m] for m in spec['members'] if m in by_id]
        mset = set(spec['members'])
        sub_conns = [c for c in conns
                     if c.get('from') in mset and c.get('to') in mset]
        w, h = _sub_layout(members, sub_conns,
                           aspect_hint=cell_hint.get(aid))
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


BUS_MIN_AREAS = 3      # WISH-ROUTE-005 (X92): umbral de destinos en áreas distintas

# WISH-ROUTE-006: holgura mínima para atravesar una fila por un hueco
_GAP_PAD = 8.0


def _corridor_grid(boxes):
    """WISH-ROUTE-006: descompone la macro-grilla en FILAS y corredores.

    Devuelve (rows, corr_ys, row_of) o (None, None, None) si la grilla no
    es descomponible en filas limpias (cajas solapadas — p.ej. un bsp
    irregular): el llamador cae al ruteo directo de LAYOUT-020.

    - rows: [{'y0','y1','boxes':[caja...]}] ordenadas de arriba a abajo.
    - corr_ys[i]: y del corredor ARRIBA de la fila i; corr_ys[n] = debajo
      de la última.
    - row_of: id de caja → índice de fila.
    """
    rows = []
    for b in sorted(boxes, key=lambda b: b['y']):
        for r in rows:
            if b['y'] < r['y1'] and r['y0'] < b['y'] + b['h']:
                r['boxes'].append(b)
                r['y0'] = min(r['y0'], b['y'])
                r['y1'] = max(r['y1'], b['y'] + b['h'])
                break
        else:
            rows.append({'y0': b['y'], 'y1': b['y'] + b['h'], 'boxes': [b]})
    rows.sort(key=lambda r: r['y0'])
    for r1, r2 in zip(rows, rows[1:]):
        if r2['y0'] < r1['y1']:
            return None, None, None
    for r in rows:
        bs = sorted(r['boxes'], key=lambda b: b['x'])
        for a, c in zip(bs, bs[1:]):
            if c['x'] < a['x'] + a['w']:
                return None, None, None
    corr_ys = [rows[0]['y0'] - AREA_GAP / 2]
    for r1, r2 in zip(rows, rows[1:]):
        corr_ys.append((r1['y1'] + r2['y0']) / 2)
    corr_ys.append(rows[-1]['y1'] + AREA_GAP / 2)
    row_of = {}
    for i, r in enumerate(rows):
        for b in r['boxes']:
            row_of[b['id']] = i
    return rows, corr_ys, row_of


def _row_gap_x(row, x_pref):
    """x libre para atravesar la fila verticalmente, lo más cerca posible
    de x_pref (los costados abiertos de la fila también son hueco)."""
    bs = sorted(row['boxes'], key=lambda b: b['x'])
    edges = []
    prev = None
    for b in bs:
        edges.append((prev, b['x']))
        prev = b['x'] + b['w']
    edges.append((prev, None))
    best = None
    for g0, g1 in edges:
        lo = (g0 if g0 is not None else -1e9) + _GAP_PAD
        hi = (g1 if g1 is not None else 1e9) - _GAP_PAD
        if hi < lo:
            continue
        x = min(max(x_pref, lo), hi)
        d = abs(x - x_pref)
        if best is None or d < best[0]:
            best = (d, x)
    return best[1] if best else x_pref


def _dedupe(pts):
    """Quita puntos duplicados y colineales consecutivos."""
    out = []
    for p in pts:
        if out and abs(p[0] - out[-1][0]) < 0.01 and abs(p[1] - out[-1][1]) < 0.01:
            continue
        if len(out) >= 2:
            a, b = out[-2], out[-1]
            if (abs(a[0] - b[0]) < 0.01 and abs(b[0] - p[0]) < 0.01) or \
                    (abs(a[1] - b[1]) < 0.01 and abs(b[1] - p[1]) < 0.01):
                out[-1] = p
                continue
        out.append(p)
    return out


def _exit_to_corridor(node, box, siblings, corr_y):
    """WISH-ROUTE-006: puntos desde `node` hasta el corredor horizontal
    corr_y SIN atravesar hermanos de su propia caja. Si la columna vertical
    está libre, sale por T/B; si un hermano la bloquea, sale por el costado
    de la caja y baja/sube por el hueco lateral (fuera de la caja).
    Devuelve (puerto, pts, x_out)."""
    going_down = corr_y > node['y']
    cx = node['x'] + ICON_WIDTH / 2
    ny0, ny1 = node['y'], node['y'] + ICON_HEIGHT
    blocked = any(
        abs((sib['x'] + ICON_WIDTH / 2) - cx) < ICON_WIDTH * 0.9
        and ((going_down and sib['y'] >= ny1 - 1)
             or (not going_down and sib['y'] + ICON_HEIGHT <= ny0 + 1))
        for sib in siblings if sib is not node and 'x' in sib)
    if not blocked:
        a = _node_border_port(node, 'B' if going_down else 'T')
        return a, [a, (a[0], corr_y)], a[0]
    # costado más cercano de la caja
    left = (cx - box['x']) <= (box['x'] + box['w'] - cx)
    a = _node_border_port(node, 'L' if left else 'R')
    sx = box['x'] - AREA_GAP / 2 if left else box['x'] + box['w'] + AREA_GAP / 2
    return a, [a, (sx, a[1]), (sx, corr_y)], sx


def _enter_from_corridor(node, box, siblings, corr_y):
    """Espejo de _exit_to_corridor: puntos desde el corredor corr_y hasta
    `node` sin atravesar hermanos. Devuelve (puerto, pts_previos)."""
    from_above = corr_y < node['y']
    cx = node['x'] + ICON_WIDTH / 2
    ny0, ny1 = node['y'], node['y'] + ICON_HEIGHT
    blocked = any(
        abs((sib['x'] + ICON_WIDTH / 2) - cx) < ICON_WIDTH * 0.9
        and ((from_above and sib['y'] + ICON_HEIGHT <= ny0 + 1)
             or (not from_above and sib['y'] >= ny1 - 1))
        for sib in siblings if sib is not node and 'x' in sib)
    if not blocked:
        b = _node_border_port(node, 'T' if from_above else 'B')
        return b, [(b[0], corr_y)]
    left = (cx - box['x']) <= (box['x'] + box['w'] - cx)
    b = _node_border_port(node, 'L' if left else 'R')
    sx = box['x'] - AREA_GAP / 2 if left else box['x'] + box['w'] + AREA_GAP / 2
    return b, [(sx, corr_y), (sx, b[1])]


def _corridor_route(x0, c0, tb, tx, rows, corr_ys, row_of):
    """WISH-ROUTE-006: waypoints desde (x0, corr_ys[c0]) hasta el corredor
    ADYACENTE a la caja destino tb, cruzando las filas intermedias por sus
    huecos (jamás a través de una caja ajena). Devuelve (pts, entra_por),
    con entra_por 'T'|'B' según el corredor de llegada."""
    ti = row_of[tb['id']]
    pts = []
    x_cur, c_cur = x0, c0
    if c_cur <= ti:
        # bajando: cruzar filas c_cur .. ti-1; llegar a corr_ys[ti]
        for r in range(c_cur, ti):
            gx = _row_gap_x(rows[r], tx)
            pts += [(gx, corr_ys[r]), (gx, corr_ys[r + 1])]
            x_cur = gx
        pts.append((tx, corr_ys[ti]))
        return pts, 'T'
    # subiendo: cruzar filas c_cur-1 .. ti+1; llegar a corr_ys[ti+1]
    for r in range(c_cur - 1, ti, -1):
        gx = _row_gap_x(rows[r], tx)
        pts += [(gx, corr_ys[r + 1]), (gx, corr_ys[r])]
        x_cur = gx
    pts.append((tx, corr_ys[ti + 1]))
    return pts, 'B'


def _route_bus(src_id, conns, area_of, box_by_area, by_id, grid=None):
    """WISH-ROUTE-005 (X92): un hub con destinos en ≥BUS_MIN_AREAS áreas
    distintas se rutea como BUS — una troncal horizontal en el corredor
    pegado a la caja del hub (arriba o abajo, según la mayoría de destinos)
    y un ramal por destino. Los tramos compartidos de la troncal se
    superponen: la lámina muestra UNA línea con derivaciones, no N rutas
    independientes cruzando el lienzo (tabernero: las ~15 dashed de la capa
    TI). WISH-ROUTE-006: con `grid`, los ramales viajan por los corredores
    de la macro-grilla — cruzan filas por sus huecos, jamás a través de una
    caja ajena."""
    s = by_id[src_id]
    sb = box_by_area[area_of[src_id]]
    scy = sb['y'] + sb['h'] / 2
    ups = sum(1 for c in conns
              if box_by_area[area_of[c['to']]]['y']
              + box_by_area[area_of[c['to']]]['h'] / 2 < scy)
    rows = corr_ys = row_of = None
    members = {}
    if grid:
        rows, corr_ys, row_of = grid
        si = row_of[sb['id']]
        for eid, aid in area_of.items():
            if eid in by_id:
                members.setdefault(aid, []).append(by_id[eid])
    if ups >= len(conns) / 2:              # mayoría arriba → troncal superior
        a = _node_border_port(s, 'T')
        c_trunk = si if grid else None
        trunk_y = corr_ys[si] if grid else sb['y'] - AREA_GAP / 2
    else:                                  # mayoría abajo → troncal inferior
        a = _node_border_port(s, 'B')
        c_trunk = si + 1 if grid else None
        trunk_y = corr_ys[si + 1] if grid else sb['y'] + sb['h'] + AREA_GAP / 2
    if grid:
        # salida del hub SIN atravesar hermanos (WISH-ROUTE-006)
        a, head, x_out = _exit_to_corridor(
            s, sb, members.get(area_of[src_id], []), trunk_y)
    for c in conns:
        d = by_id[c['to']]
        tb = box_by_area[area_of[c['to']]]
        tx = d['x'] + ICON_WIDTH / 2
        if grid:
            ti = row_of[tb['id']]
            mid, side = _corridor_route(x_out, c_trunk, tb, tx,
                                        rows, corr_ys, row_of)
            c_in = corr_ys[ti] if side == 'T' else corr_ys[ti + 1]
            b, tail = _enter_from_corridor(
                d, tb, members.get(area_of[c['to']], []), c_in)
            pts = _dedupe(head + mid + tail + [b])
        else:
            b_side = 'B' if tb['y'] + tb['h'] / 2 < trunk_y else 'T'
            b = _node_border_port(d, b_side)
            entry = tb['y'] + tb['h'] if b_side == 'B' else tb['y']
            pts = [a, (a[0], trunk_y), (b[0], trunk_y), (b[0], entry), b]
        c['computed_path'] = {'type': 'polyline', 'points': pts}
        c['_from_port'] = a
        c['_to_port'] = b
        c['_inter_area'] = True
        c['_bus'] = src_id
    n_areas = len({area_of[c['to']] for c in conns})
    logger.info(f"[bus] hub '{src_id}': troncal + {len(conns)} ramal(es) "
                f"hacia {n_areas} área(s) (X92)")


def _route_inter_area(layout, area_of, box_by_area):
    """§I29 generalizado (WISH-LAYOUT-020): con la macro-grilla 2D las cajas
    ya no están sólo a la derecha — el lado de salida/entrada se elige por el
    EJE DOMINANTE entre centros de caja (R→L, L→R, B→T o T→B), con el
    corredor a mitad de camino entre los bordes enfrentados. Los hubs
    multi-área van aparte como BUS (WISH-ROUTE-005)."""
    by_id = {e['id']: e for e in layout.elements}

    # WISH-ROUTE-006: la macro-grilla como sistema de corredores. Si no es
    # descomponible en filas limpias, grid=None y todo cae al ruteo directo.
    rows, corr_ys, row_of = _corridor_grid(list(box_by_area.values()))
    grid = (rows, corr_ys, row_of) if rows else None
    members: Dict[str, list] = {}
    if grid:
        for eid, aid in area_of.items():
            if eid in by_id:
                members.setdefault(aid, []).append(by_id[eid])

    # WISH-ROUTE-005 (X92): detectar hubs por nodo origen ANTES del ruteo
    # par-a-par.
    inter = [c for c in layout.connections
             if c.get('from') in area_of and c.get('to') in area_of
             and area_of[c.get('from')] != area_of[c.get('to')]]
    by_src: Dict[str, list] = {}
    for c in inter:
        by_src.setdefault(c['from'], []).append(c)
    bussed = set()
    for src, cs in by_src.items():
        if len({area_of[c['to']] for c in cs}) >= BUS_MIN_AREAS:
            _route_bus(src, cs, area_of, box_by_area, by_id, grid=grid)
            bussed.update(id(c) for c in cs)

    for c in layout.connections:
        f, t = c.get('from'), c.get('to')
        if f not in area_of or t not in area_of or area_of[f] == area_of[t]:
            continue
        if id(c) in bussed:
            continue
        sb = box_by_area[area_of[f]]
        tb = box_by_area[area_of[t]]
        s, d = by_id[f], by_id[t]

        if grid:
            si, ti = row_of[sb['id']], row_of[tb['id']]
            same_row_clear = False
            if si == ti:
                lo = min(sb['x'] + sb['w'], tb['x'] + tb['w'])
                hi = max(sb['x'], tb['x'])
                same_row_clear = not any(
                    b['x'] < hi and lo < b['x'] + b['w']
                    for b in rows[si]['boxes']
                    if b['id'] not in (sb['id'], tb['id']))
            if not same_row_clear:
                # WISH-ROUTE-006: por los corredores — sale hacia el
                # corredor que mira al destino (sin atravesar hermanos) y
                # cruza filas por huecos.
                tx = d['x'] + ICON_WIDTH / 2
                c0 = si + 1 if ti > si else si
                a, head, x_out = _exit_to_corridor(
                    s, sb, members.get(area_of[f], []), corr_ys[c0])
                mid, side = _corridor_route(x_out, c0, tb, tx,
                                            rows, corr_ys, row_of)
                c_in = corr_ys[ti] if side == 'T' else corr_ys[ti + 1]
                b, tail = _enter_from_corridor(
                    d, tb, members.get(area_of[t], []), c_in)
                pts = _dedupe(head + mid + tail + [b])
                c['computed_path'] = {'type': 'polyline', 'points': pts}
                c['_from_port'] = a
                c['_to_port'] = b
                c['_inter_area'] = True
                continue

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
