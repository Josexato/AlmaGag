"""
§P61 — Pasada anticolisión GLOBAL post-layout sobre el árbol completo.

El pipeline reubica etiquetas en varios momentos, pero cada paso mira un
subconjunto (labels bottom de hijos directos, labels con colisiones según
el optimizador…) y ninguno re-verifica el resultado de los demás. Esta
etapa corre AL FINAL, cuando ya nada se mueve, sobre TODAS las etiquetas
a cualquier profundidad de contención:

- etiquetas de icono: candidatos por ancla (posición actual primero —
  estabilidad —, luego bottom con escalones de una línea, top, right,
  left); una etiqueta de miembro no puede salirse de su contenedor.
- etiquetas de conexión: se deslizan por su propia polilínea (fracciones
  de longitud de arco) buscando un punto sin fusión.

Sólo se mueven ETIQUETAS: iconos y paths quedan intactos, así que esta
pasada no puede alterar cruces, arista×nodo, tinta ni aspecto — sólo el
contador `labels`. Determinista: orden (y, x, id) para iconos, orden de
aparición para conexiones. Separación texto↔texto exigida: ≥8px.
"""

import logging
from typing import Dict, List, Optional, Tuple

from AlmaGag.config import ICON_WIDTH
from AlmaGag.utils import extract_item_id

logger = logging.getLogger('AlmaGag')

TEXT_GAP = 8.0            # separación mínima texto↔texto (criterio §P61)
STAGGER_STEP = 18.0       # un renglón (TEXT_LINE_HEIGHT)
LINE_FRACTIONS = (0.5, 0.4, 0.6, 0.3, 0.7, 0.2, 0.8)


def _inflate(b, d):
    return (b[0] - d, b[1] - d, b[2] + d, b[3] + d)


def _intersect(a, b) -> bool:
    return not (a[2] < b[0] or b[2] < a[0] or a[3] < b[1] or b[3] < a[1])


def _seg_hits(bb, segs) -> int:
    x1, y1, x2, y2 = bb
    n = 0
    for (ax, ay, bx, by) in segs:
        if max(ax, bx) < x1 or min(ax, bx) > x2 \
                or max(ay, by) < y1 or min(ay, by) > y2:
            continue
        # muestreo fino: suficiente para tramos ortogonales y diagonales cortas
        for t in (0.0, 0.2, 0.4, 0.5, 0.6, 0.8, 1.0):
            px, py = ax + (bx - ax) * t, ay + (by - ay) * t
            if x1 < px < x2 and y1 < py < y2:
                n += 1
                break
    return n


def _conn_segments(conn, layout, geometry):
    cp = conn.get('computed_path')
    pts = cp.get('points') if isinstance(cp, dict) else None
    if pts and len(pts) >= 2:
        xy = [((p[0], p[1]) if not hasattr(p, 'x') else (p.x, p.y)) for p in pts]
        return [(xy[i][0], xy[i][1], xy[i + 1][0], xy[i + 1][1])
                for i in range(len(xy) - 1)]
    ep = geometry.get_connection_endpoints(layout, conn)
    return [ep] if ep else []


def _parent_boxes(layout) -> Dict[str, Tuple[float, float, float, float]]:
    """id de miembro → bbox de su contenedor directo (si está resuelto)."""
    out = {}
    for c in layout.elements:
        if 'contains' not in c or 'x' not in c:
            continue
        cb = (c['x'], c['y'],
              c['x'] + c.get('width', 0), c['y'] + c.get('height', 0))
        for r in c['contains']:
            out[extract_item_id(r)] = cb
    return out


def _dist_point_segs(px, py, segs) -> float:
    """Distancia mínima de un punto a una lista de segmentos."""
    best = float('inf')
    for (ax, ay, bx, by) in segs:
        vx, vy = bx - ax, by - ay
        L2 = vx * vx + vy * vy
        t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((px - ax) * vx + (py - ay) * vy) / L2))
        qx, qy = ax + t * vx, ay + t * vy
        d = ((px - qx) ** 2 + (py - qy) ** 2) ** 0.5
        if d < best:
            best = d
    return best


# WISH-LAYOUT-008: umbral de rancidez — una posición almacenada más lejos
# que esto de su ancla (icono / polilínea) quedó atrás en algún movimiento
# no rastreado; puntuaría «limpia» en el vacío y se dibujaría huérfana.
STALE_ICON_DIST = 90.0
STALE_CONN_DIST = 60.0


def _conn_label_bbox_at(label: str, cx: float, cy: float):
    """Espejo de geometry.get_connection_label_bbox con centro explícito."""
    w = len(label) * 7
    return (cx - w // 2, cy - 10 - 16, cx + w // 2, cy - 10)


def seed_label_truth(layout, geometry) -> None:
    """WISH-LAYOUT-008: garantiza que el layout CONTIENE la verdad dibujable.

    Todo elemento etiquetado y posicionado sin entrada en `label_positions`
    recibe su posición canónica (respetando `label_position` preferida);
    toda conexión etiquetada sin `_label_anchor` recibe su centro en
    `connection_labels`. El renderer dibuja estos valores TAL CUAL — sin
    esto, una estrategia que no siembra (hier) dejaría etiquetas sin fuente.

    En vistas agrupadas (§I27/§I28: areas/lanes/matrix) las etiquetas de
    nodo son estructurales (centradas bajo el icono, `draw_area_node_labels`)
    y NO viven en `label_positions` — no se siembran ni se reubican.
    """
    grouped = bool(getattr(layout, 'areas', None)
                   or getattr(layout, 'lanes', None)
                   or getattr(layout, 'matrix', None))
    if not grouped:
        for e in layout.elements:
            if ('contains' in e or not e.get('label')
                    or 'x' not in e or 'y' not in e
                    or e['id'] in layout.label_positions):
                continue
            num_lines = len(e['label'].split('\n'))
            preferred = e.get('label_position', 'bottom')
            layout.label_positions[e['id']] = geometry.get_text_coords(
                e, preferred, num_lines)
    for c in layout.connections:
        if not c.get('label') or c.get('_label_anchor'):
            continue
        key = f"{c['from']}->{c['to']}"
        if key not in layout.connection_labels:
            layout.connection_labels[key] = geometry.get_connection_center(
                layout, c)


def global_label_anticollision(layout, geometry) -> int:
    """Reubica etiquetas fundidas sobre el árbol completo. Devuelve cuántas
    etiquetas se movieron. No toca iconos ni paths."""
    seed_label_truth(layout, geometry)     # WISH-LAYOUT-008
    els = [e for e in layout.elements
           if 'contains' not in e and 'x' in e and 'y' in e]
    icon_box = {e['id']: geometry.get_icon_bbox(e) for e in els}
    parent_box = _parent_boxes(layout)
    segs_by_conn = {f"{c['from']}->{c['to']}": _conn_segments(c, layout, geometry)
                    for c in layout.connections}

    zone_labels: List[Tuple[float, float, float, float]] = []
    from AlmaGag.layout.considerations import near_zone_boxes
    for zone in near_zone_boxes(layout.elements):
        if zone.get('label_bbox'):
            zone_labels.append(zone['label_bbox'])
    # el ENCABEZADO de cada contenedor también es texto dibujado: banda
    # superior de la caja (rótulo multilínea) — sin esto, un candidato `top`
    # se monta sobre el título del contenedor y el detector no lo ve.
    # WISH-LAYOUT-010: además de obstáculo blando para terceros, el TÍTULO
    # es ZONA DURA para las etiquetas de los propios miembros. La zona dura
    # NO es la banda completa (expulsaría etiquetas que no pisan nada): sólo
    # icono + texto real del rótulo, espejo de _render_container_labels
    # (anclado a la izquierda, ~8px/carácter en bold).
    header_bands: Dict[str, Tuple[float, float, float, float]] = {}
    for c in layout.elements:
        if 'contains' in c and c.get('label') and 'x' in c:
            lines = c['label'].split('\n')
            header_h = len(lines) * 18 + 10
            band = (c['x'], c['y'],
                    c['x'] + c.get('width', 0), c['y'] + header_h)
            zone_labels.append(band)
            local_x = 10.0 if c.get('type') == 'area' \
                else 10.0 + ICON_WIDTH + 10.0
            text_w = max(len(ln) for ln in lines) * 8.0
            header_bands[c['id']] = (
                c['x'], c['y'],
                min(c['x'] + local_x + text_w, c['x'] + c.get('width', 0)),
                c['y'] + header_h)
    member_header: Dict[str, Tuple[float, float, float, float]] = {}
    for c in layout.elements:
        if 'contains' in c and c['id'] in header_bands:
            for ref in c['contains']:
                member_header[extract_item_id(ref)] = header_bands[c['id']]

    # WISH-LAYOUT-008: TODAS las etiquetas de icono — contenidas a cualquier
    # profundidad Y libres — pasan por esta única pasada; el renderer dibuja
    # label_positions tal cual (ya no re-optimiza nada). Los miembros de zona
    # near y los expulsados conservan su etiqueta estructural (§N46): no se
    # mueven, pero abajo cuentan como obstáculo.
    labeled = [e for e in els
               if e.get('label') and e['id'] in layout.label_positions
               and e.get('_near_zone') is None and not e.get('_evicted')]
    labeled.sort(key=lambda e: (e['y'], e['x'], e['id']))

    # etiquetas estructurales (miembros near/evicted) y rótulos de conexión
    # anclados a puerto (§G23, hier): fijos, pero visibles para el score
    for e in els:
        if (e.get('label') and e['id'] in layout.label_positions
                and (e.get('_near_zone') is not None or e.get('_evicted'))):
            bb = geometry.get_label_bbox_stored(e, layout.label_positions[e['id']])
            if bb:
                zone_labels.append(bb)
    for c in layout.connections:
        anchor = c.get('_label_anchor')
        if c.get('label') and anchor:
            w = len(c['label']) * 7
            zone_labels.append((anchor[0] - w / 2, anchor[1] - 12,
                                anchor[0] + w / 2, anchor[1] + 4))

    # TODAS las etiquetas actuales son obstáculo desde el inicio (al procesar
    # una se quita su propia entrada): el barrido ve también a las que aún no
    # tocan su turno, no sólo a las ya procesadas.
    label_bbox: Dict[str, Tuple[float, float, float, float]] = {}
    for e in labeled:
        bb = geometry.get_label_bbox_stored(e, layout.label_positions[e['id']])
        if bb:
            label_bbox[e['id']] = bb
    conn_bbox: Dict[str, Tuple[float, float, float, float]] = {}
    conn_by_key: Dict[str, dict] = {}
    for c in layout.connections:
        if c.get('label') and not c.get('_label_anchor'):
            key = f"{c['from']}->{c['to']}"
            conn_by_key[key] = c
            cx, cy = layout.connection_labels.get(
                key, geometry.get_connection_center(layout, c))
            conn_bbox[key] = _conn_label_bbox_at(c['label'], cx, cy)

    def _score(bb, own_id, own_conns) -> int:
        # WISH-LAYOUT-010: montarse sobre un ICONO pesa más que rozar otro
        # texto (es la violación R1, la más fea).
        s = 0
        for eid, ib in icon_box.items():
            if eid != own_id and ib and _intersect(bb, ib):
                s += 2
        gb = _inflate(bb, TEXT_GAP / 2)
        for zb in zone_labels:
            if _intersect(gb, _inflate(zb, TEXT_GAP / 2)):
                s += 1
        for eid, lb in label_bbox.items():
            if eid != own_id and _intersect(gb, _inflate(lb, TEXT_GAP / 2)):
                s += 1
        for key, cb in conn_bbox.items():
            if key not in own_conns and _intersect(gb, _inflate(cb, TEXT_GAP / 2)):
                s += 1
        for key, segs in segs_by_conn.items():
            if key in own_conns:
                continue
            s += _seg_hits(bb, segs)
        return s

    moved = 0
    for _sweep in range(2):
        sweep_moved = 0

        # --- Pasada A: etiquetas de icono, a toda profundidad ---------------
        for e in labeled:
            eid = e['id']
            if eid not in label_bbox:
                continue
            own_conns = {f"{c['from']}->{c['to']}" for c in layout.connections
                         if eid in (c['from'], c['to'])}
            cur = layout.label_positions[eid]
            num_lines = len(e['label'].split('\n'))
            pbox = parent_box.get(eid)

            # (posición, escalón, corrimiento horizontal). bottom escalona
            # hasta 3 renglones (una etiqueta de 2 líneas sólo libra a su
            # vecina con 36+8px de descenso) y admite corrimiento ±40px:
            # dos vecinas a 100px de pitch con labels de 152px sólo caben
            # separándose en horizontal, como lo haría un humano.
            candidates: List[Optional[Tuple[str, int, float]]] = [None]
            for p in ('bottom', 'top', 'right', 'left'):
                stags = (0, 1, 2, 3) if p == 'bottom' else (0,)
                dxs = (0.0, -40.0, 40.0) if p in ('bottom', 'top') else (0.0,)
                for stag in stags:
                    for dx in dxs:
                        candidates.append((p, stag, dx))

            own_bb = label_bbox.pop(eid)
            # rancidez: la posición actual sólo es candidata si sigue CERCA
            # de su icono (gap entre bboxes ≤ STALE_ICON_DIST)
            ib = icon_box.get(eid)
            cur_is_stale = False
            if ib and own_bb:
                gx = max(ib[0] - own_bb[2], own_bb[0] - ib[2], 0.0)
                gy = max(ib[1] - own_bb[3], own_bb[1] - ib[3], 0.0)
                cur_is_stale = (gx * gx + gy * gy) ** 0.5 > STALE_ICON_DIST
            best = None      # (score, idx, pos_tuple, bbox)
            for idx, cand in enumerate(candidates):
                if cand is None:
                    if cur_is_stale:
                        continue
                    pos = cur
                    bb = own_bb
                else:
                    p, stag, dx = cand
                    tx, ty, anchor, _ = geometry.get_text_coords(e, p, num_lines)
                    pos = (tx + dx, ty + stag * STAGGER_STEP, anchor, p)
                    bb = geometry.get_label_bbox_stored(e, pos)
                if not bb:
                    break
                if (cand is not None and pbox
                        and not (bb[0] >= pbox[0] - 2 and bb[2] <= pbox[2] + 2
                                 and bb[1] >= pbox[1] - 2 and bb[3] <= pbox[3] + 2)):
                    continue      # un candidato nuevo no saca la etiqueta de su caja
                # WISH-LAYOUT-010: el TÍTULO del contenedor (icono + texto)
                # es zona DURA para las etiquetas de sus miembros — también
                # para la posición actual (un `top` heredado sobre el título
                # se expulsa aunque puntúe limpio).
                hband = member_header.get(eid)
                if hband and _intersect(bb, hband):
                    continue
                s = _score(bb, eid, own_conns)
                if best is None or s < best[0]:
                    best = (s, idx, pos, bb)
                if s == 0:
                    break         # el primer candidato limpio gana (estabilidad)

            if best is None:
                label_bbox[eid] = own_bb
                continue
            _, idx, pos, bb = best
            if idx != 0:
                layout.label_positions[eid] = pos
                sweep_moved += 1
            label_bbox[eid] = bb

        # --- Pasada B: etiquetas de conexión, deslizables por su polilínea --
        for key, c in conn_by_key.items():
            label = c['label']
            segs = segs_by_conn.get(key) or []
            if not segs:
                continue
            own = {key}
            cx, cy = layout.connection_labels.get(
                key, geometry.get_connection_center(layout, c))

            # candidatos: posición actual + puntos por fracción de arco
            lens = [((bx - ax) ** 2 + (by - ay) ** 2) ** 0.5
                    for (ax, ay, bx, by) in segs]
            total = sum(lens) or 1.0
            # rancidez: el centro almacenado sólo es candidato si sigue CERCA
            # de su propia polilínea (el rótulo viaja con su línea)
            if _dist_point_segs(cx, cy, segs) <= STALE_CONN_DIST:
                points = [(cx, cy)]
            else:
                points = []
            for f in LINE_FRACTIONS:
                d = f * total
                for (ax, ay, bx, by), L in zip(segs, lens):
                    if d <= L or L == lens[-1]:
                        t = 0.0 if L == 0 else min(1.0, d / L)
                        px, py = ax + (bx - ax) * t, ay + (by - ay) * t
                        points.append((px, py))
                        # variante bajo la línea (el bbox ancla ARRIBA del
                        # punto): dos rótulos gemelos en polilíneas paralelas
                        # no caben ambos arriba — uno puede colgar debajo
                        points.append((px, py + 30))
                        # WISH-LAYOUT-010: variantes AL COSTADO del conector
                        # (offset perpendicular ±26px) — en zonas congestas
                        # el único hueco suele estar junto a la línea, no
                        # sobre ella
                        if L > 0:
                            ux, uy = (bx - ax) / L, (by - ay) / L
                            for off in (26.0, -26.0):
                                points.append((px - uy * off + 0,
                                               py + ux * off + 13))
                        break
                    d -= L

            del conn_bbox[key]    # no chocar contra mi propia posición vieja
            best = None      # (score, idx, center, bbox)
            for idx, (px, py) in enumerate(points):
                bb = _conn_label_bbox_at(label, px, py)
                s = _score(bb, None, own)
                if best is None or s < best[0]:
                    best = (s, idx, (px, py), bb)
                if s == 0:
                    break

            _, idx, center, bb = best
            # el centro elegido SIEMPRE se almacena: es la fuente única de la
            # que dibuja el renderer (WISH-LAYOUT-008), no sólo una medición
            layout.connection_labels[key] = center
            if idx != 0:
                sweep_moved += 1
            conn_bbox[key] = bb

        moved += sweep_moved
        if not sweep_moved:
            break

    if moved:
        logger.info(f"§P61: pasada global anticolisión — "
                    f"{moved} etiqueta(s) reubicada(s)")
    return moved
