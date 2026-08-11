"""
§P60 — Zonas de servicio a la periferia + troncal por zona destino.

Cuando el diagrama AUTO se organiza en zonas-contenedor (`type: "area"` con
`contains`, sin coordenadas del autor), el nivel macro distingue dos clases:

- **operativas**: participan de al menos un enlace inter-zona de transporte
  (`direction` bidirectional/none) — van adyacentes en la banda principal;
- **servicio/soporte**: sólo emiten/reciben enlaces administrativos
  dirigidos — van a la periferia (fila bajo la banda).

Los enlaces inter-zona de un mismo par (zona origen → zona destino) se
agrupan en UNA troncal ortogonal que viaja por el corredor y entra por un
único punto del borde de la zona destino (§I29); dentro de la zona se
abren en abanico hasta cada elemento. Cero diagonales inter-zona (§H24).

La troncal se recalcula en cada re-ruteo a partir de la geometría vigente
(marca `_zone_trunk` en la conexión), así sobrevive expansiones de canvas
y movimientos del optimizador.
"""

import logging
from typing import Dict, List, Optional, Tuple

from AlmaGag.config import ICON_WIDTH, ICON_HEIGHT
from AlmaGag.utils import extract_item_id

logger = logging.getLogger('AlmaGag')

ZONE_BAND_GAP = 100        # separación horizontal entre zonas de una fila
ZONE_CORRIDOR = 150        # corredor vertical banda ↔ periferia (troncales)
ZONE_MARGIN = 60           # origen de la banda (se re-normaliza después)
TRUNK_BUMP = 12            # troncales opuestas del mismo par no se pisan

TRANSPORT_DIRECTIONS = ('bidirectional', 'none')


def _box(e) -> Tuple[float, float, float, float]:
    w = e.get('width', ICON_WIDTH)
    h = e.get('height', ICON_HEIGHT)
    return e['x'], e['y'], e['x'] + w, e['y'] + h


def _center(e) -> Tuple[float, float]:
    x1, y1, x2, y2 = _box(e)
    return (x1 + x2) / 2.0, (y1 + y2) / 2.0


def top_level_area_zones(elements: List[dict]) -> List[dict]:
    """Zonas candidatas: contenedores `type: area` que nadie contiene."""
    contained = set()
    for e in elements:
        for r in e.get('contains', []):
            contained.add(extract_item_id(r))
    return [e for e in elements
            if e.get('type') == 'area' and 'contains' in e
            and e['id'] not in contained]


def zones_lack_author_coords(elements: List[dict]) -> bool:
    """Gate temprano (ANTES del posicionamiento): el macro-layout §P60 sólo
    aplica si el autor no fijó coordenadas de las zonas — la geometría es
    del motor (§R)."""
    zones = top_level_area_zones(elements)
    return len(zones) >= 2 and not any('x' in z for z in zones)


def _classify(layout) -> Optional[dict]:
    """Clasifica zonas y enlaces. None si §P60 no aplica."""
    zones = top_level_area_zones(layout.elements)
    if len(zones) < 2:
        return None
    by = layout.elements_by_id
    zone_of: Dict[str, str] = {}
    for z in zones:
        stack = [extract_item_id(r) for r in z['contains']]
        while stack:
            i = stack.pop()
            zone_of[i] = z['id']
            ch = by.get(i)
            if ch and 'contains' in ch:
                stack.extend(extract_item_id(r) for r in ch['contains'])

    inter = [c for c in layout.connections
             if zone_of.get(c.get('from')) and zone_of.get(c.get('to'))
             and zone_of[c['from']] != zone_of[c['to']]]
    if not inter:
        return None

    transported = set()
    linked = set()
    for c in inter:
        zf, zt = zone_of[c['from']], zone_of[c['to']]
        linked.update((zf, zt))
        if c.get('direction') in TRANSPORT_DIRECTIONS:
            transported.update((zf, zt))

    operational = [z for z in zones if z['id'] in transported]
    service = [z for z in zones if z['id'] not in transported]
    if not operational or not service:
        return None            # sin distinción no hay banda/periferia
    return {'zones': zones, 'zone_of': zone_of, 'inter': inter,
            'operational': operational, 'service': service}


def zone_affinity_groups(considerations, zone_ids) -> List[List[str]]:
    """§Q65: consideraciones `near` cuyos ids son TODOS zonas top-level se
    consumen como AFINIDAD entre áreas (adyacencia en su fila), no como
    cluster de miembros. Se marcan `_zone_affinity` para que §N46
    (cluster_near_groups) no intente clusterizar contenedores. NOTA: debe
    recibir la lista ORIGINAL del layout de entrada (Layout.copy() no copia
    `_considerations`) para que la marca la vean los pasos posteriores."""
    groups = []
    for cons in considerations or []:
        if cons.get('kind') != 'near':
            continue
        ids = cons.get('ids') or []
        if len(ids) >= 2 and all(i in zone_ids for i in ids):
            cons['_zone_affinity'] = True
            groups.append(list(ids))
    return groups


def _blocks_for_row(row_zones, affinity) -> List[List[dict]]:
    """Agrupa las zonas de una fila en bloques indivisibles según la afinidad
    declarada (subconjunto de la fila); el resto, bloques unitarios. Orden
    interno y de descubrimiento: aparición (determinista)."""
    by_id = {z['id']: z for z in row_zones}
    joined: Dict[str, set] = {z['id']: {z['id']} for z in row_zones}
    for group in affinity:
        members = [i for i in group if i in by_id]
        if len(members) < 2:
            continue
        merged = set()
        for m in members:
            merged |= joined[m]
        for m in merged:
            joined[m] = merged
    blocks, seen = [], set()
    for z in row_zones:
        if z['id'] in seen:
            continue
        block = [by_id[i] for i in by_id if i in joined[z['id']]]
        seen |= joined[z['id']]
        blocks.append(block)
    return blocks


def apply_zone_banding(layout, shift_subtree, considerations=None) -> int:
    """Reordena las zonas ya resueltas (P59: super-nodos rígidos): banda
    operativa arriba, fila de servicio abajo, corredor entre ambas. Marca
    los enlaces inter-zona con `_zone_trunk` para el ruteo por troncales.

    §Q65 — orden dentro de cada fila: la afinidad declarada
    (`considerations.near` con ids de áreas) forma bloques indivisibles;
    sin declarar, la banda se encadena por adyacencia de TRANSPORTE
    (zonas unidas por enlaces bidirectional/none quedan contiguas) y la
    periferia por baricentro; desempate siempre por orden de aparición.

    `shift_subtree(container, layout, dx, dy)` mueve una zona con todo su
    contenido. Devuelve el número de zonas de servicio movidas (0 = no aplicó).
    """
    info = _classify(layout)
    if info is None:
        return 0
    if any('x' not in z for z in info['zones']):
        return 0

    operational, service = info['operational'], info['service']
    zone_of, inter = info['zone_of'], info['inter']
    affinity = zone_affinity_groups(considerations,
                                    {z['id'] for z in info['zones']})

    # --- banda operativa: bloques de afinidad encadenados por transporte ----
    transport_links: Dict[Tuple[str, str], int] = {}
    for c in inter:
        if c.get('direction') in TRANSPORT_DIRECTIONS:
            zf, zt = zone_of[c['from']], zone_of[c['to']]
            key = (min(zf, zt), max(zf, zt))
            transport_links[key] = transport_links.get(key, 0) + 1

    blocks = _blocks_for_row(operational, affinity)

    def _links_between(a, b) -> int:
        return sum(transport_links.get((min(za['id'], zb['id']),
                                        max(za['id'], zb['id'])), 0)
                   for za in a for zb in b)

    ordered_blocks = [blocks[0]] if blocks else []
    pending = blocks[1:]
    while pending:
        tail = ordered_blocks[-1]
        best = max(pending, key=lambda blk: _links_between(tail, blk))
        if _links_between(tail, best) == 0:
            best = pending[0]          # sin enlace al final: orden de aparición
        pending.remove(best)
        ordered_blocks.append(best)
    band_order = [z for blk in ordered_blocks for z in blk]

    # band_h sigue siendo el alto de la banda: sitúa la fila de periferia.
    band_h = max(_box(z)[3] - _box(z)[1] for z in operational)

    x = ZONE_MARGIN
    band_cx: Dict[str, float] = {}
    for z in band_order:
        x1, y1, x2, y2 = _box(z)
        w, h = x2 - x1, y2 - y1
        # BUGS-LAYOUT-012 (hallazgo GAG Skiller): las cajas se centraban
        # verticalmente en la banda ((band_h - h)/2), así que dos zonas de
        # alto distinto dejaban techos — y con la banda de rótulo constante,
        # PRIMERAS FILAS — desfasados (~9px medidos: cajas de 269 y 287).
        # Alineadas al TECHO de la banda, los miembros equivalentes caen en
        # la misma fila absoluta por construcción y las troncales
        # inter-zona salen rectas.
        shift_subtree(z, layout, x - x1, ZONE_MARGIN - y1)
        band_cx[z['id']] = x + w / 2.0
        x += w + ZONE_BAND_GAP
    band_w = x - ZONE_BAND_GAP - ZONE_MARGIN

    # --- periferia: orden por baricentro de las zonas de banda que enlaza;
    # una zona de servicio que sólo enlaza a otras de servicio hereda el
    # baricentro de éstas (determinista; desempate por orden de aparición).
    svc_ids = {z['id'] for z in service}
    links: Dict[str, List[str]] = {z['id']: [] for z in service}
    for c in inter:
        zf, zt = zone_of[c['from']], zone_of[c['to']]
        if zf in svc_ids:
            links[zf].append(zt)
        if zt in svc_ids:
            links[zt].append(zf)

    bary: Dict[str, float] = {}
    default_cx = ZONE_MARGIN + band_w / 2.0
    for _ in range(len(service) + 1):        # propaga por cadenas svc→svc
        for z in service:
            xs = [band_cx[t] if t in band_cx else bary.get(t)
                  for t in links[z['id']]]
            xs = [v for v in xs if v is not None]
            bary[z['id']] = sum(xs) / len(xs) if xs else default_cx
    order = {z['id']: i for i, z in enumerate(service)}
    svc_blocks = _blocks_for_row(service, affinity)
    svc_blocks.sort(key=lambda blk: (sum(bary[z['id']] for z in blk) / len(blk),
                                     min(order[z['id']] for z in blk)))
    for blk in svc_blocks:
        blk.sort(key=lambda z: order[z['id']])
    service_sorted = [z for blk in svc_blocks for z in blk]

    periph_w = (sum(_box(z)[2] - _box(z)[0] for z in service_sorted)
                + ZONE_BAND_GAP * (len(service_sorted) - 1))
    x = ZONE_MARGIN + max(0.0, (band_w - periph_w) / 2.0)
    y_row = ZONE_MARGIN + band_h + ZONE_CORRIDOR
    for z in service_sorted:
        x1, y1, x2, y2 = _box(z)
        shift_subtree(z, layout, x - x1, y_row - y1)
        x += (x2 - x1) + ZONE_BAND_GAP

    # --- troncales: una por par (origen → destino), recomputadas al rutar
    pairs = set()
    for c in inter:
        zf, zt = zone_of[c['from']], zone_of[c['to']]
        c['_zone_trunk'] = {'src': zf, 'dst': zt}
        pairs.add((zf, zt))

    logger.info(f"§P60: {len(operational)} zona(s) operativas en banda, "
                f"{len(service)} de servicio a periferia, "
                f"{len(pairs)} troncal(es) inter-zona")
    if affinity:
        logger.info(f"§Q65: {len(affinity)} afinidad(es) de área declaradas "
                    f"— bloques adyacentes en su fila")
    return len(service)


def _trim_endpoint(pt, prev, elem):
    """Acorta el último tramo hasta el borde del elemento (la flecha aterriza
    en el borde, no en el centro del icono)."""
    x1, y1, x2, y2 = _box(elem)
    px, py = prev
    tx, ty = pt
    if abs(px - tx) < 0.5:                     # tramo vertical
        return (tx, y1 if py < ty else y2)
    return (x1 if px < tx else x2, ty)         # tramo horizontal


def _dedupe(points):
    out = []
    for p in points:
        if not out or (abs(p[0] - out[-1][0]) > 0.5
                       or abs(p[1] - out[-1][1]) > 0.5):
            out.append(p)
    return out


def route_zone_trunks(layout) -> int:
    """Recalcula el path de toda conexión marcada `_zone_trunk` a partir de
    la geometría VIGENTE: elemento → borde de su zona → espina del corredor
    compartida por el grupo → punto de entrada único en el borde de la zona
    destino → abanico interno hasta el elemento. Idempotente: se invoca en
    cada re-ruteo."""
    by = layout.elements_by_id
    groups: Dict[Tuple[str, str], List[dict]] = {}
    for c in layout.connections:
        tk = c.get('_zone_trunk')
        if tk:
            groups.setdefault((tk['src'], tk['dst']), []).append(c)
    if not groups:
        return 0

    n = 0
    for (src, dst), conns in sorted(groups.items()):
        S, D = by.get(src), by.get(dst)
        if not S or not D or 'x' not in S or 'x' not in D:
            continue
        sx1, sy1, sx2, sy2 = _box(S)
        dx1, dy1, dx2, dy2 = _box(D)
        gap_x = max(dx1 - sx2, sx1 - dx2)
        gap_y = max(dy1 - sy2, sy1 - dy2)
        if max(gap_x, gap_y) <= 0:
            continue                     # zonas solapadas: sin corredor
        bump = -TRUNK_BUMP if src < dst else TRUNK_BUMP

        # La troncal es la ESPINA compartida en el corredor (el «bus» visible
        # hasta el borde de la zona destino); cada conexión sube/baja a la
        # espina por la columna de su origen y entra a la zona destino por la
        # columna/fila de su propio destino — la intrusión interior es la
        # mínima (sólo el tramo perpendicular hacia el elemento).
        if gap_y >= gap_x:               # zonas en filas: espina horizontal
            spine_y = ((sy2 + dy1) / 2.0 if dy1 >= sy2
                       else (sy1 + dy2) / 2.0) + bump
            for c in conns:
                s, t = by.get(c['from']), by.get(c['to'])
                if not s or not t or 'x' not in s or 'x' not in t:
                    continue
                scx, scy = _center(s)
                tcx, tcy = _center(t)
                pts = [(scx, scy), (scx, spine_y), (tcx, spine_y), (tcx, tcy)]
                _apply_trunk_path(c, pts, s, t)
                n += 1
        else:                            # zonas en columnas: espina vertical
            spine_x = ((sx2 + dx1) / 2.0 if dx1 >= sx2
                       else (sx1 + dx2) / 2.0) + bump
            for c in conns:
                s, t = by.get(c['from']), by.get(c['to'])
                if not s or not t or 'x' not in s or 'x' not in t:
                    continue
                scx, scy = _center(s)
                tcx, tcy = _center(t)
                pts = [(scx, scy), (spine_x, scy), (spine_x, tcy), (tcx, tcy)]
                _apply_trunk_path(c, pts, s, t)
                n += 1
    return n


def _apply_trunk_path(conn, pts, s, t):
    pts = _dedupe(pts)
    if len(pts) < 2:
        return
    pts[0] = _trim_endpoint(pts[0], pts[1], s)
    pts[-1] = _trim_endpoint(pts[-1], pts[-2], t)
    pts = _dedupe(pts)
    conn['computed_path'] = {'type': 'polyline',
                             'points': [[p[0], p[1]] for p in pts]}
    conn['_from_port'] = pts[0]
    conn['_to_port'] = pts[-1]
