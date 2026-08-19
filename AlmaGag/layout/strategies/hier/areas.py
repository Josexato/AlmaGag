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
from AlmaGag.utils import extract_item_id
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
              'hub': 2,                  # al MEDIO: conecta con todo
              'external': 3, 'overlay': 4}
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
    """Cajas de etiqueta (centradas bajo cada icono) para incluir en el bbox.
    Los contenedores no llevan etiqueta inferior — su label vive en el header
    de la caja (ARCH-009)."""
    boxes = []
    for e in members:
        if 'x' not in e or not e.get('label') or e.get('contains'):
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


# ---------------------------------------------------------------------------
# WISH-ARCH-009: contenedores como miembros de área — «zonas para la
# escenografía, contenedores para la profundidad» (el autor, 18-ago-2026).
# El contenedor se MIDE primero (sub-layout de sus hijos, bottom-up) y entra
# a la grilla del área como un nodo gordo; su caja dibujada = la reservada
# (se fijan x/y/width/height + _is_container_calculated, el mismo contrato
# que ContainerCalculator le da a draw_container).
# ---------------------------------------------------------------------------
_CONT_PAD = 10.0        # espejo de container.get('padding', 10)
_FAT_GAP_X = 60.0       # aire horizontal entre nodos gordos
_FAT_GAP_Y = 46.0       # aire vertical entre filas de nodos gordos


def _container_header_h(cont):
    """Alto del header (icono+label) — espejo de ContainerCalculator."""
    if not cont.get('label'):
        return 0.0
    return float(max(50, len(cont['label'].split('\n')) * 18))


def _measure_container(cont, by_id, conns, cont_of):
    """Sub-layout local de los hijos y footprint del contenedor. Deja en el
    dict: _cw/_ch (caja completa), _koff (offset del contenido dentro de la
    caja), _kids/_kconns (para trasladar junto con la caja). Sólo cuentan
    los hijos cuya pertenencia sigue en `cont_of` (un hijo con área propia
    declarada ya no es de este contenedor para el layout)."""
    kid_ids = [k for k in (extract_item_id(i)
                           for i in cont.get('contains', []))
               if cont_of.get(k) == cont['id']]
    kids = [by_id[k] for k in kid_ids if k in by_id]
    kset = set(kid_ids)
    kconns = [c for c in conns
              if c.get('from') in kset and c.get('to') in kset]
    cw, ch = _sub_layout(kids, kconns)
    pad = float(cont.get('padding', _CONT_PAD))
    head = _container_header_h(cont)
    fw = cw + 2 * pad
    if cont.get('label'):
        # mínimo para que el label del header quepa (BUGS-AUTO-007)
        lw = max(len(ln) for ln in cont['label'].split('\n')) * 10
        fw = max(fw, 10 + ICON_WIDTH + 10 + lw + 10)
    fh = ch + 2 * pad + head
    cont['_cw'], cont['_ch'] = fw, fh
    cont['_koff'] = ((fw - cw) / 2, head + pad)
    cont['_kids'], cont['_kconns'] = kids, kconns
    return fw, fh


def _node_dims(e):
    """(w, h) del miembro como unidad de empaque: contenedor medido o
    icono + bloque de etiqueta."""
    if e.get('_cw'):
        return e['_cw'], e['_ch']
    lines = e['label'].count('\n') + 1 if e.get('label') else 0
    h = ICON_HEIGHT + (LABEL_GAP + lines * LABEL_LINE_H if lines else 0.0)
    return max(ICON_WIDTH, 2 * _label_halfwidth(e)), h


def _fat_sub_layout(members, conns, cont_of):
    """ARCH-009: sub-layout de un área con contenedores entre sus miembros.
    Niveles sobre el grafo CONDENSADO (cada hijo cuenta como su contenedor),
    filas por nivel, empaque horizontal por anchos reales. Muta members (y
    los hijos de cada contenedor) a coords locales del área; rutea las
    conexiones que cruzan de un miembro a otro. Devuelve (w, h)."""
    mset = {e['id'] for e in members}
    synth, seen = [], set()
    for c in conns:
        f = cont_of.get(c.get('from'), c.get('from'))
        t = cont_of.get(c.get('to'), c.get('to'))
        if f in mset and t in mset and f != t and (f, t) not in seen:
            seen.add((f, t))
            synth.append({'from': f, 'to': t})
    lv = compute_levels(members, synth)
    cols, _wp = compute_columns(lv, members, synth)
    # Los medios-niveles (tomas laterales) comparten FILA con su nivel
    # entero: un contenedor a nivel 0.5 en fila propia apila la cadena en
    # columna 1×N (zona alta y flaca) — como caja gorda, convive mejor al
    # lado que a medio nivel.
    rows = {}
    for e in sorted(members, key=lambda e: (lv.level.get(e['id'], 0),
                                            cols.get(e['id'], 0))):
        rows.setdefault(int(lv.level.get(e['id'], 0)), []).append(e)
    y = 0.0
    for lvl in sorted(rows):
        row = rows[lvl]
        row_h = max(_node_dims(e)[1] for e in row)
        x = 0.0
        for i, e in enumerate(row):
            w, _h = _node_dims(e)
            # bordes de fila: el canal lateral del área sólo sirve a
            # miembros que tocan ese borde (el pasillo queda libre por
            # construcción del empaque por filas).
            e['_edge'] = ('L' if i == 0 else '') + \
                ('R' if i == len(row) - 1 else '')
            if e.get('_cw'):
                e['x'], e['y'] = x, y
                e['width'], e['height'] = e['_cw'], e['_ch']
                e['_is_container_calculated'] = True
                ox, oy = e['_koff']
                _shift(e['_kids'], e['_kconns'], x + ox, y + oy)
            else:
                e['x'] = x + (w - ICON_WIDTH) / 2
                e['y'] = y
                e['label_position'] = 'bottom'
            x += w + _FAT_GAP_X
        y += row_h + _FAT_GAP_Y

    lvl_of = {e['id']: int(lv.level.get(e['id'], 0)) for e in members}
    _route_fat_conns(members, conns, cont_of, mset, lvl_of,
                     lane=_make_lanes())

    # bbox local: cajas gordas + iconos/etiquetas sueltos + paths.
    maxx = maxy = 0.0
    for e in members:
        w, h = _node_dims(e)
        ex = e['x'] if e.get('_cw') else e['x'] - (w - ICON_WIDTH) / 2
        maxx = max(maxx, ex + w)
        maxy = max(maxy, e['y'] + h)
    for b in _label_boxes([e for e in members if not e.get('_cw')]):
        maxx = max(maxx, b[2])
        maxy = max(maxy, b[3])
    for c in conns:
        for px, py in _all_points([], [c]):
            maxx = max(maxx, px)
            maxy = max(maxy, py)
    return maxx, maxy


def _route_fat_conns(members, conns, cont_of, mset, lvl_of=None, lane=None):
    """Conexiones que cruzan de un miembro gordo a otro DENTRO del área:
    puertos en el borde del hijo real, corredor ortogonal a mitad de camino
    entre las cajas enfrentadas (T71 en miniatura). Los enlaces LARGOS
    (saltan ≥2 filas) entre miembros que tocan un mismo borde van por el
    CANAL LATERAL del área — el pasillo central es de los que entran, no
    de los que pasan (ARCH-009 v3: r_a1→r_a5 causaba 7 de los 13 cruces
    del showcase atravesando el medio)."""
    lvl_of = lvl_of or {}
    by_local = {e['id']: e for e in members}
    for e in members:
        for k in e.get('_kids', []):
            by_local[k['id']] = k
    box_of = {}
    for e in members:
        w, h = _node_dims(e)
        ex = e['x'] if e.get('_cw') else e['x'] - (w - ICON_WIDTH) / 2
        box_of[e['id']] = (ex, e['y'], w, h)
    maxx_all = max((b[0] + b[2] for b in box_of.values()), default=0.0)
    side_used = {'L': 0, 'R': 0}
    for c in conns:
        f, t = c.get('from'), c.get('to')
        cf, ct = cont_of.get(f, f), cont_of.get(t, t)
        if cf not in mset or ct not in mset or cf == ct:
            continue
        s, d = by_local.get(f), by_local.get(t)
        if s is None or d is None or 'x' not in s or 'x' not in d:
            continue
        fx, fy, fw, fh = box_of[cf]
        tx, ty, tw, th = box_of[ct]
        key = ('fan', f)               # abanico por origen, como el bus X92
        ln_f = (lambda kind, idx: lane(kind, idx, key)) if lane else \
            (lambda kind, idx: 0.0)

        if abs(lvl_of.get(cf, 0) - lvl_of.get(ct, 0)) >= 2:
            ef = by_local[cf].get('_edge', '')
            et = by_local[ct].get('_edge', '')
            side = 'L' if ('L' in ef and 'L' in et) else \
                ('R' if ('R' in ef and 'R' in et) else None)
            if side:
                side_used[side] += 1
                if side == 'L':
                    chx = -(16.0 + 8.0 * (side_used['L'] - 1))
                    a = _node_border_port(s, 'L')
                    b = _node_border_port(d, 'L')
                else:
                    chx = maxx_all + 16.0 + 8.0 * (side_used['R'] - 1)
                    a = _node_border_port(s, 'R')
                    b = _node_border_port(d, 'R')
                pts = [a, (chx, a[1]), (chx, b[1]), b]
                c['computed_path'] = {'type': 'polyline',
                                      'points': _dedupe(pts),
                                      'corner_radius': _CURVE_R}
                c['_from_port'] = a
                c['_to_port'] = b
                continue
        dxc = (tx + tw / 2) - (fx + fw / 2)
        dyc = (ty + th / 2) - (fy + fh / 2)
        if abs(dyc) >= abs(dxc):
            pa = max(-30.0, min(30.0, ln_f('p', f)))
            pb = max(-30.0, min(30.0, ln_f('p', t)))
            if dyc >= 0:
                a = _node_border_port(s, 'B')
                b = _node_border_port(d, 'T')
                corr = ((fy + fh) + ty) / 2
            else:
                a = _node_border_port(s, 'T')
                b = _node_border_port(d, 'B')
                corr = (fy + (ty + th)) / 2
            a = (a[0] + pa, a[1])
            b = (b[0] + pb, b[1])
            corr += ln_f('fc', round(corr))
            pts = [a, (a[0], corr), (b[0], corr), b]
        else:
            pa = max(-18.0, min(18.0, ln_f('p', f)))
            pb = max(-18.0, min(18.0, ln_f('p', t)))
            if dxc >= 0:
                a = _node_border_port(s, 'R')
                b = _node_border_port(d, 'L')
                corr = ((fx + fw) + tx) / 2
            else:
                a = _node_border_port(s, 'L')
                b = _node_border_port(d, 'R')
                corr = (fx + (tx + tw)) / 2
            a = (a[0], a[1] + pa)
            b = (b[0], b[1] + pb)
            corr += ln_f('fc', round(corr))
            pts = [a, (corr, a[1]), (corr, b[1]), b]
        c['computed_path'] = {'type': 'polyline', 'points': _dedupe(pts),
                              'corner_radius': _CURVE_R}
        c['_from_port'] = a
        c['_to_port'] = b


def layout_by_areas(layout, areas_spec):
    """Posiciona `layout` por áreas (§I27) y rutea inter-área (§I29).
    Devuelve la lista de cajas [{id,label,color,x,y,w,h}]. Muta layout."""
    by_id = {e['id']: e for e in layout.elements}
    conns = layout.connections

    # ARCH-009: mapa hijo → contenedor (un nivel; un contenedor anidado
    # dentro de otro se nombra y se trata como icono normal en v1).
    containers = {e['id']: e for e in layout.elements if e.get('contains')}
    cont_of: Dict[str, str] = {}
    for cid, cont in containers.items():
        for item in cont.get('contains', []):
            kid = extract_item_id(item)
            if kid in containers:
                logger.warning(f"[areas] contenedor '{kid}' anidado dentro "
                               f"de '{cid}' — ARCH-009 v1 soporta UN nivel; "
                               f"se coloca como icono")
                continue
            if kid in by_id:
                cont_of[kid] = cid

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
    # conflicto: un hijo de contenedor que ADEMÁS declara área propia — la
    # membresía declarada gana y el contenedor lo pierde para el layout
    # (nunca dos dueños, nunca silencio).
    for kid in list(cont_of):
        if kid in area_of:
            logger.warning(f"[areas] '{kid}' es hijo del contenedor "
                           f"'{cont_of[kid]}' pero declara área propia — la "
                           f"membresía declarada gana (ARCH-009)")
            del cont_of[kid]
    for e in layout.elements:
        if e['id'] in area_of or e['id'] in cont_of:
            continue        # los hijos viajan con su contenedor (ARCH-009)
        aid = f"__solo_{e['id']}"
        spec_by_id[aid] = {'id': aid, 'label': '', 'members': [e['id']]}
        area_of[e['id']] = aid
        order.append(aid)
    # los hijos heredan el área de su contenedor (para el ruteo inter-área);
    # una membresía declarada explícita del hijo gana.
    for kid, cid in cont_of.items():
        if cid in area_of:
            area_of.setdefault(kid, area_of[cid])

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
        fat = [m for m in members if m.get('contains')]
        if fat:
            # ARCH-009: la clausura del área incluye a los hijos de sus
            # contenedores; las conexiones internas del contenedor viajan
            # con él y las miembro-a-miembro se rutean a nivel de área.
            closure = set(spec['members'])
            for cont in fat:
                closure.update(k for k, c in cont_of.items()
                               if c == cont['id'])
            sub_conns = [c for c in conns
                         if c.get('from') in closure
                         and c.get('to') in closure]
            for cont in fat:
                _measure_container(cont, by_id, conns, cont_of)
            w, h = _fat_sub_layout(members, sub_conns, cont_of)
            movers = members + [k for cont in fat for k in cont['_kids']]
            dims.append({'aid': aid, 'spec': spec, 'members': movers,
                         'conns': sub_conns,
                         'w': w + 2 * AREA_PAD,
                         'h': h + 2 * AREA_PAD + AREA_HEAD})
            continue
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

    # ARCH-009 v2: desvío de contenedores ajenos — un segmento que cruza
    # una caja de lado a lado se desvía por su borde; el que ENTRA a una
    # caja (para llegar a su hijo) se respeta.
    cont_boxes = [(c['x'], c['y'], c['x'] + c['width'], c['y'] + c['height'])
                  for c in containers.values()
                  if c.get('_is_container_calculated')]
    if cont_boxes:
        dodge_reg = {}          # ROUTE-008: desvíos escalonados por caja+lado
        for c in conns:
            cp = c.get('computed_path')
            if cp and cp.get('type') == 'polyline':
                cp['points'] = _dodge_boxes(list(cp['points']), cont_boxes,
                                            reg=dodge_reg)

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
    # ARCH-009: si el nodo es un contenedor medido, el puerto va en el borde
    # de su caja real, no en un icono imaginario de 80×50.
    w = e.get('width', ICON_WIDTH) if e.get('contains') else ICON_WIDTH
    h = e.get('height', ICON_HEIGHT) if e.get('contains') else ICON_HEIGHT
    cx, cy = e['x'] + w / 2, e['y'] + h / 2
    if side == 'R':
        return (e['x'] + w, cy)
    if side == 'L':
        return (e['x'], cy)
    if side == 'T':
        return (cx, e['y'])
    return (cx, e['y'] + h)


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


_DODGE_M = 12.0     # holgura del desvío alrededor de un contenedor ajeno


def _dodge_boxes(pts, boxes, reg=None):
    """ARCH-009 v2: ninguna ruta atraviesa un contenedor AJENO — cada
    segmento ortogonal que corta una caja se desvía por el borde más
    cercano (rectángulo + holgura). Se repite hasta limpiar o agotar el
    presupuesto (los desvíos nuevos pueden cortar otra caja).

    `reg` (ROUTE-008): registro COMPARTIDO entre rutas — dos rutas que
    rodean la misma caja por el mismo lado se escalonan (+7px cada una)
    en vez de montarse en la misma línea de desvío."""
    def _m(box, side):
        if reg is None:
            return _DODGE_M
        n = reg.get((box, side), 0)
        reg[(box, side)] = n + 1
        return _DODGE_M + 7.0 * n
    for _ in range(24):
        changed = False
        for i in range(len(pts) - 1):
            p, q = pts[i], pts[i + 1]
            hit = None
            if abs(p[1] - q[1]) < 0.01:                      # horizontal
                y = p[1]
                a, b = sorted((p[0], q[0]))
                for x0, y0, x1, y1 in boxes:
                    if y0 < y < y1 and min(b, x1) - max(a, x0) > 0.01 \
                            and a < x0 and b > x1:
                        hit = ('h', (x0, y0, x1, y1))
                        break
            elif abs(p[0] - q[0]) < 0.01:                    # vertical
                x = p[0]
                a, b = sorted((p[1], q[1]))
                for x0, y0, x1, y1 in boxes:
                    if x0 < x < x1 and min(b, y1) - max(a, y0) > 0.01 \
                            and a < y0 and b > y1:
                        hit = ('v', (x0, y0, x1, y1))
                        break
            if not hit:
                continue
            axis, (x0, y0, x1, y1) = hit
            box = (x0, y0, x1, y1)
            if axis == 'h':
                y = p[1]
                top = y - y0 <= y1 - y
                m = _m(box, 'T' if top else 'B')
                yd = y0 - m if top else y1 + m
                if p[0] < q[0]:
                    xa, xb = x0 - _DODGE_M, x1 + _DODGE_M
                else:
                    xa, xb = x1 + _DODGE_M, x0 - _DODGE_M
                detour = [(xa, y), (xa, yd), (xb, yd), (xb, y)]
            else:
                x = p[0]
                left = x - x0 <= x1 - x
                m = _m(box, 'L' if left else 'R')
                xd = x0 - m if left else x1 + m
                if p[1] < q[1]:
                    ya, yb = y0 - _DODGE_M, y1 + _DODGE_M
                else:
                    ya, yb = y1 + _DODGE_M, y0 - _DODGE_M
                detour = [(x, ya), (xd, ya), (xd, yb), (x, yb)]
            pts = pts[:i + 1] + detour + pts[i + 1:]
            changed = True
            break
        if not changed:
            return _dedupe(pts)
    return _dedupe(pts)


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


def _exit_to_corridor(node, box, siblings, corr_y, ln=None):
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
    # WISH-ROUTE-007 v2: la vertical lateral también lleva carril propio
    sx += ln('s', (box['id'], 'L' if left else 'R')) if ln else 0.0
    return a, [a, (sx, a[1]), (sx, corr_y)], sx


def _enter_from_corridor(node, box, siblings, corr_y, ln=None):
    """Espejo de _exit_to_corridor: puntos desde el corredor corr_y hasta
    `node` sin atravesar hermanos. Devuelve (puerto, pts_previos).

    BUGS-ROUTE-005 (hallazgo del Skiller, v3.16): las entradas a un mismo
    hijo se reparten en el borde del icono TAMBIÉN en la vía por
    corredores — ROUTE-008 sólo cubría la vía directa y dos orígenes
    distintos llegaban al punto idéntico."""
    from_above = corr_y < node['y']
    cx = node['x'] + ICON_WIDTH / 2
    ny0, ny1 = node['y'], node['y'] + ICON_HEIGHT
    blocked = any(
        abs((sib['x'] + ICON_WIDTH / 2) - cx) < ICON_WIDTH * 0.9
        and ((from_above and sib['y'] + ICON_HEIGHT <= ny0 + 1)
             or (not from_above and sib['y'] >= ny1 - 1))
        for sib in siblings if sib is not node and 'x' in sib)
    if not blocked:
        off = max(-30.0, min(30.0, ln('p', node['id']))) if ln else 0.0
        b = _node_border_port(node, 'T' if from_above else 'B')
        b = (b[0] + off, b[1])
        return b, [(b[0], corr_y)]
    left = (cx - box['x']) <= (box['x'] + box['w'] - cx)
    b = _node_border_port(node, 'L' if left else 'R')
    off = max(-18.0, min(18.0, ln('p', node['id']))) if ln else 0.0
    b = (b[0], b[1] + off)
    sx = box['x'] - AREA_GAP / 2 if left else box['x'] + box['w'] + AREA_GAP / 2
    sx += ln('s', (box['id'], 'L' if left else 'R')) if ln else 0.0
    return b, [(sx, corr_y), (sx, b[1])]


# WISH-ROUTE-007: carriles dentro del corredor — rutas independientes que
# comparten un pasillo van en carriles paralelos (paso _LANE_STEP), no
# montadas en la línea central; sólo los ramales de un MISMO bus comparten
# carril (la troncal superpuesta es adrede, X92).
_LANE_STEP = 9.0
_CURVE_R = 12.0        # quiebres curvos: la curva dice «doblo», el cruce seco dice «cruzo»
_LANE_MAX = AREA_GAP / 2 - 8.0


def _make_lanes():
    """Registro de carriles: (tipo, índice) → {clave_de_ruta: offset}.
    El primero va al centro (0); los siguientes alternan ±paso."""
    reg = {}

    def lane(kind, idx, key):
        d = reg.setdefault((kind, idx), {})
        if key not in d:
            n = len(d)
            k = (n + 1) // 2
            off = 0.0 if n == 0 else k * _LANE_STEP * (1 if n % 2 else -1)
            d[key] = max(-_LANE_MAX, min(_LANE_MAX, off))
        return d[key]
    return lane


def _corridor_route(x0, c0, tb, tx, rows, corr_ys, row_of, lane=None,
                    key=None):
    """WISH-ROUTE-006: waypoints desde (x0, corr del índice c0) hasta el
    corredor ADYACENTE a la caja destino tb, cruzando las filas intermedias
    por sus huecos (jamás a través de una caja ajena). Devuelve
    (pts, entra_por), con entra_por 'T'|'B' según el corredor de llegada.
    Con `lane`/`key`, cada corredor y cada hueco usados llevan el offset
    del carril de ESTA ruta (WISH-ROUTE-007)."""
    ln = (lambda kind, idx: lane(kind, idx, key)) if lane else \
        (lambda kind, idx: 0.0)
    ti = row_of[tb['id']]
    pts = []
    c_cur = c0
    if c_cur <= ti:
        # bajando: cruzar filas c_cur .. ti-1; llegar al corredor de ti
        for r in range(c_cur, ti):
            gx = _row_gap_x(rows[r], tx) + ln('v', r)
            pts += [(gx, corr_ys[r] + ln('h', r)),
                    (gx, corr_ys[r + 1] + ln('h', r + 1))]
        pts.append((tx, corr_ys[ti] + ln('h', ti)))
        return pts, 'T'
    # subiendo: cruzar filas c_cur-1 .. ti+1; llegar al corredor bajo ti
    for r in range(c_cur - 1, ti, -1):
        gx = _row_gap_x(rows[r], tx) + ln('v', r)
        pts += [(gx, corr_ys[r + 1] + ln('h', r + 1)),
                (gx, corr_ys[r] + ln('h', r))]
    pts.append((tx, corr_ys[ti + 1] + ln('h', ti + 1)))
    return pts, 'B'


def _route_bus(src_id, conns, area_of, box_by_area, by_id, grid=None,
               lane=None):
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
            if eid in by_id and not by_id[eid].get('contains'):
                members.setdefault(aid, []).append(by_id[eid])
    # WISH-ROUTE-007: todos los ramales del bus comparten CLAVE de carril —
    # la troncal superpuesta es adrede; contra otras rutas, carril propio.
    key = ('bus', src_id)
    ln = (lambda kind, idx: lane(kind, idx, key)) if (grid and lane) else \
        (lambda kind, idx: 0.0)
    if ups >= len(conns) / 2:              # mayoría arriba → troncal superior
        a = _node_border_port(s, 'T')
        c_trunk = si if grid else None
        trunk_y = corr_ys[si] + ln('h', si) if grid \
            else sb['y'] - AREA_GAP / 2
    else:                                  # mayoría abajo → troncal inferior
        a = _node_border_port(s, 'B')
        c_trunk = si + 1 if grid else None
        trunk_y = corr_ys[si + 1] + ln('h', si + 1) if grid \
            else sb['y'] + sb['h'] + AREA_GAP / 2
    if grid:
        # salida del hub SIN atravesar hermanos (WISH-ROUTE-006)
        a, head, x_out = _exit_to_corridor(
            s, sb, members.get(area_of[src_id], []), trunk_y, ln=ln)
    for c in conns:
        d = by_id[c['to']]
        tb = box_by_area[area_of[c['to']]]
        tx = d['x'] + ICON_WIDTH / 2
        if grid:
            ti = row_of[tb['id']]
            mid, side = _corridor_route(x_out, c_trunk, tb, tx,
                                        rows, corr_ys, row_of,
                                        lane=lane, key=key)
            c_idx = ti if side == 'T' else ti + 1
            c_in = corr_ys[c_idx] + ln('h', c_idx)
            b, tail = _enter_from_corridor(
                d, tb, members.get(area_of[c['to']], []), c_in, ln=ln)
            pts = _dedupe(head + mid + tail + [b])
            c['computed_path'] = {'type': 'polyline', 'points': pts,
                                  'corner_radius': _CURVE_R}
        else:
            b_side = 'B' if tb['y'] + tb['h'] / 2 < trunk_y else 'T'
            b = _node_border_port(d, b_side)
            entry = tb['y'] + tb['h'] if b_side == 'B' else tb['y']
            pts = [a, (a[0], trunk_y), (b[0], trunk_y), (b[0], entry), b]
        c['computed_path'] = {'type': 'polyline', 'points': pts,
                              'corner_radius': _CURVE_R}
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
    lane = _make_lanes() if grid else None   # WISH-ROUTE-007
    if grid:
        for eid, aid in area_of.items():
            # ARCH-009: los contenedores no entran como hermanos-obstáculo
            # (la guarda de columna asume dimensiones de icono).
            if eid in by_id and not by_id[eid].get('contains'):
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
            _route_bus(src, cs, area_of, box_by_area, by_id, grid=grid,
                       lane=lane)
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
                key = (f, t)                 # WISH-ROUTE-007: carril propio
                ln_c = lambda kind, idx: lane(kind, idx, key)
                a, head, x_out = _exit_to_corridor(
                    s, sb, members.get(area_of[f], []),
                    corr_ys[c0] + lane('h', c0, key), ln=ln_c)
                mid, side = _corridor_route(x_out, c0, tb, tx,
                                            rows, corr_ys, row_of,
                                            lane=lane, key=key)
                c_idx = ti if side == 'T' else ti + 1
                c_in = corr_ys[c_idx] + lane('h', c_idx, key)
                b, tail = _enter_from_corridor(
                    d, tb, members.get(area_of[t], []), c_in, ln=ln_c)
                pts = _dedupe(head + mid + tail + [b])
                c['computed_path'] = {'type': 'polyline', 'points': pts,
                                      'corner_radius': _CURVE_R}
                c['_from_port'] = a
                c['_to_port'] = b
                c['_inter_area'] = True
                continue

        dx = (tb['x'] + tb['w'] / 2) - (sb['x'] + sb['w'] / 2)
        dy = (tb['y'] + tb['h'] / 2) - (sb['y'] + sb['h'] / 2)
        # ROUTE-008: la vía directa entre cajas enfrentadas (misma fila /
        # sin grilla) era ANTERIOR a los carriles — todas las rutas de un
        # mismo par de zonas se montaban en la vertical del corredor y en
        # los puertos. Política de ABANICO por origen (la del bus X92):
        # las rutas de un MISMO origen comparten troncal en el corredor
        # (superposición adrede: una línea que se ramifica — carriles
        # por-ruta las trenzaban, medido 0→19 cruces); orígenes distintos
        # van en carriles distintos, y las entradas a un mismo destino se
        # reparten por origen en el borde del icono (T72 en miniatura).
        key = ('fan', f)
        ln_d = (lambda kind, idx: lane(kind, idx, key)) if lane else \
            (lambda kind, idx: 0.0)
        if abs(dx) >= abs(dy):
            if dx >= 0:                    # destino a la derecha
                a = _node_border_port(s, 'R')
                b = _node_border_port(d, 'L')
                ex, en = sb['x'] + sb['w'], tb['x']
            else:                          # destino a la izquierda
                a = _node_border_port(s, 'L')
                b = _node_border_port(d, 'R')
                ex, en = sb['x'], tb['x'] + tb['w']
            pa = max(-18.0, min(18.0, ln_d('p', f)))
            pb = max(-18.0, min(18.0, ln_d('p', t)))
            a = (a[0], a[1] + pa)
            b = (b[0], b[1] + pb)
            corr = (ex + en) / 2 + ln_d('c', (sb['id'], tb['id']))
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
            pa = max(-30.0, min(30.0, ln_d('p', f)))
            pb = max(-30.0, min(30.0, ln_d('p', t)))
            a = (a[0] + pa, a[1])
            b = (b[0] + pb, b[1])
            corr = (ex + en) / 2 + ln_d('c', (sb['id'], tb['id']))
            pts = [a, (a[0], ex), (a[0], corr), (b[0], corr), (b[0], en), b]
        c['computed_path'] = {'type': 'polyline', 'points': pts,
                              'corner_radius': _CURVE_R}
        c['_from_port'] = a
        c['_to_port'] = b
        c['_inter_area'] = True
