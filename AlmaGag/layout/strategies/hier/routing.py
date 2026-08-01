"""
§C + §D — Puertos y ruteo de conectores (WISH-LAF-002 Fase 2).

Produce `connection['computed_path'] = {'type':'polyline','points':[...]}`
que el renderer dibuja. No usa la política AUTO.

- C9: puertos por proyección del otro extremo sobre el borde (fracción
  acotada), separados sólo lo necesario.
- C10: lado del puerto según el eje de flujo; llegada perpendicular al borde.
- C11: ruteo de tomas laterales (salida por el costado, horizontal, bajada).
- D12: aristas de mismo nivel en recta.
- D13: cruces reales en recta (bifurcaciones/fusiones conservan codo).
- D14: carriles de canal para aristas paralelas (offset por pista).
"""

from collections import defaultdict
from typing import Dict, List, Tuple
from AlmaGag.config import ICON_WIDTH, ICON_HEIGHT
from AlmaGag.layout.strategies.hier.shapes import is_diamond, diamond_port, diamond_vertices

PORT_MIN_FRAC = 0.16
PORT_MAX_FRAC = 0.84
CHANNEL_STEP = 22.0    # separación de pistas en un canal (D14)
PORT_SEP = 14.0        # separación mínima entre puertos del mismo borde


def _center(e):
    return (e['x'] + ICON_WIDTH / 2, e['y'] + ICON_HEIGHT / 2)


def _clampx(e, xv):
    lo = e['x'] + PORT_MIN_FRAC * ICON_WIDTH
    hi = e['x'] + PORT_MAX_FRAC * ICON_WIDTH
    return max(lo, min(hi, xv))


def route_connections(layout, levels):
    """Asigna computed_path a cada conexión (in-place)."""
    by_id = {e['id']: e for e in layout.elements}
    level = levels.level
    back = levels.back_edges
    side_feeders = levels.side_feeders

    def _placed(eid):
        e = by_id.get(eid)
        return e is not None and 'x' in e and 'y' in e

    # Sólo conexiones cuyos DOS extremos tienen posición (hier posiciona
    # elementos root; los contenidos aún no — se dejan al render legacy).
    conns = [c for c in layout.connections
             if _placed(c.get('from')) and _placed(c.get('to'))]

    # --- C9: puertos por proyección, separados por borde ---
    # Agrupar puertos por (elemento, lado) para separarlos.
    # lado: 'bottom'|'top' (flujo vertical) o 'left'|'right' (mismo nivel).
    port_reqs = defaultdict(list)  # (elem_id, side) → [(frac_x, conn_idx, is_source)]

    def flow_sides(f, t):
        # §C11: la toma lateral SALE por el costado (hacia el destino) y ENTRA
        # por arriba del destino → salida horizontal, bajada vertical.
        if f['id'] in side_feeders:
            side = 'right' if _center(t)[0] >= _center(f)[0] else 'left'
            return (side, 'top')
        lf = level.get(f['id'], 0)
        lt = level.get(t['id'], 0)
        if abs(lt - lf) < 0.5:
            # mismo nivel → lado a lado
            return ('right', 'left') if _center(t)[0] >= _center(f)[0] else ('left', 'right')
        if lt > lf:
            return ('bottom', 'top')       # hacia abajo
        return ('top', 'bottom')           # hacia arriba

    # §H26/§G19: lado de salida por rombo considerando TODAS sus aristas
    # salientes (incl. las de ciclo, que §E redibuja pero cuya reserva de
    # vértice importa): la que baja recto (menor |Δx|) toma el vértice INFERIOR
    # (continuación del flujo); las demás salen por el lateral izq/der según su
    # posición. Así el «sí» de una decisión no roba el vértice inferior al «no».
    out_by_src = defaultdict(list)
    for c in conns:
        if (c['from'], c['to']) in back:
            continue
        if is_diamond(by_id[c['from']]):
            out_by_src[c['from']].append(c['to'])
    diamond_out_side: Dict[Tuple[str, str], str] = {}
    for fid, tids in out_by_src.items():
        fc = _center(by_id[fid])
        downs = [tid for tid in tids if _center(by_id[tid])[1] >= fc[1]]
        bottom = min(downs, key=lambda tid: abs(_center(by_id[tid])[0] - fc[0])) \
            if downs else None
        for tid in tids:
            tc = _center(by_id[tid])
            dx = tc[0] - fc[0]
            if tid == bottom and abs(dx) < ICON_WIDTH:
                diamond_out_side[(fid, tid)] = 'bottom'
            elif dx < 0:
                diamond_out_side[(fid, tid)] = 'left'
            elif dx > 0:
                diamond_out_side[(fid, tid)] = 'right'
            else:
                diamond_out_side[(fid, tid)] = 'bottom' if tc[1] >= fc[1] else 'top'

    _vword = {'top': 'T', 'bottom': 'B', 'left': 'L', 'right': 'R'}

    # Puertos ya fijados por forma (§G19: rombos → vértice del polígono).
    port_pos: Dict[Tuple[int, bool], Tuple[float, float]] = {}

    meta = []
    for ci, c in enumerate(conns):
        if (c['from'], c['to']) in back:
            meta.append(None)
            continue
        f, t = by_id[c['from']], by_id[c['to']]
        sf, st = flow_sides(f, t)
        fc, tc = _center(f), _center(t)
        # §G19/§H26: si el origen es rombo, el puerto es el vértice del lado
        # asignado (salida radial); si no, proyección sobre el borde.
        if is_diamond(f):
            sf = diamond_out_side.get((c['from'], c['to']), sf)
            port_pos[(ci, True)] = diamond_vertices(f)[_vword[sf]]
        else:
            port_reqs[(f['id'], sf)].append((tc[0] if sf in ('top', 'bottom') else tc[1], ci, True))
        # §G19: si el destino es rombo, entra por el vértice superior.
        if is_diamond(t):
            pt, st = diamond_port(t, fc, is_source=False)
            port_pos[(ci, False)] = pt
        else:
            port_reqs[(t['id'], st)].append((fc[0] if st in ('top', 'bottom') else fc[1], ci, False))
        meta.append((f, t, sf, st))

    # Resolver posición concreta de los puertos por proyección (no-rombo).
    for (eid, side), reqs in port_reqs.items():
        e = by_id[eid]
        reqs.sort(key=lambda r: r[0])
        n = len(reqs)
        if side in ('top', 'bottom'):
            y = e['y'] if side == 'top' else e['y'] + ICON_HEIGHT
            xs = [_clampx(e, r[0]) for r in reqs]
            xs = _separate(xs, PORT_SEP,
                           e['x'] + PORT_MIN_FRAC * ICON_WIDTH,
                           e['x'] + PORT_MAX_FRAC * ICON_WIDTH)
            for (frac, ci, is_src), px in zip(reqs, xs):
                port_pos[(ci, is_src)] = (px, y)
        else:
            x = e['x'] if side == 'left' else e['x'] + ICON_WIDTH
            lo = e['y'] + PORT_MIN_FRAC * ICON_HEIGHT
            hi = e['y'] + PORT_MAX_FRAC * ICON_HEIGHT
            ys = _separate([max(lo, min(hi, r[0])) for r in reqs], PORT_SEP, lo, hi)
            for (frac, ci, is_src), py in zip(reqs, ys):
                port_pos[(ci, is_src)] = (x, py)

    # --- D14: pistas de canal por (nivel_origen, nivel_destino) ---
    channel_groups = defaultdict(list)
    for ci, m in enumerate(meta):
        if m is None:
            continue
        f, t, sf, st = m
        lf, lt = level.get(f['id'], 0), level.get(t['id'], 0)
        if abs(lt - lf) >= 0.5 and sf in ('top', 'bottom'):
            channel_groups[(round(lf, 1), round(lt, 1))].append(ci)
    channel_offset: Dict[int, float] = {}
    for key, cis in channel_groups.items():
        cis.sort(key=lambda ci: port_pos.get((ci, True), (0, 0))[0])
        n = len(cis)
        for i, ci in enumerate(cis):
            channel_offset[ci] = (i - (n - 1) / 2) * CHANNEL_STEP

    # --- D13: cruces reales en recta ---
    # Dos aristas del mismo canal se cruzan si el orden en X de sus orígenes
    # es OPUESTO al de sus destinos y no comparten origen ni destino
    # (bifurcación/fusión conservan su codo ortogonal).
    straight_cross: set = set()
    for key, cis in channel_groups.items():
        for a in range(len(cis)):
            for b in range(a + 1, len(cis)):
                ci, cj = cis[a], cis[b]
                fa, ta, _, _ = meta[ci]
                fb, tb, _, _ = meta[cj]
                if fa['id'] == fb['id'] or ta['id'] == tb['id']:
                    continue  # bifurcación o fusión → no es cruce
                xfa = port_pos[(ci, True)][0]
                xfb = port_pos[(cj, True)][0]
                xta = port_pos[(ci, False)][0]
                xtb = port_pos[(cj, False)][0]
                if (xfa - xfb) * (xta - xtb) < 0:   # orden opuesto → se cruzan
                    straight_cross.add(ci)
                    straight_cross.add(cj)

    # --- construir paths ---
    for ci, c in enumerate(conns):
        m = meta[ci]
        if m is None:
            continue  # back-edge → §E (Fase 3), se deja sin computed_path
        f, t, sf, st = m
        p_from = port_pos.get((ci, True))
        p_to = port_pos.get((ci, False))
        if not p_from or not p_to:
            continue

        lf, lt = level.get(f['id'], 0), level.get(t['id'], 0)

        if c['from'] in side_feeders:
            # C11: salir por costado, horizontal a la altura de la fuente,
            # bajar vertical al borde superior del destino.
            fx, fy = p_from
            tx, ty = p_to
            pts = [(fx, fy), (tx, fy), (tx, ty)]
        elif abs(lt - lf) < 0.5:
            # D12: mismo nivel → recta directa (puede quedar levemente diagonal
            # si los puertos se separaron; §H24 la admite como recta).
            pts = [p_from, p_to]
            c['_straight'] = True
        elif ci in straight_cross:
            # D13/§M44: cruce real → recta PURA puerto a puerto (se cortan en
            # un punto limpio; única diagonal permitida junto a los arcos de
            # ciclo, §H24). Los extremos se recortan al borde REAL de cada
            # forma A LO LARGO de la recta (sin stubs perpendiculares que la
            # convertían en híbrido codo+diagonal).
            from AlmaGag.layout.strategies.hier.shapes import clip_shape
            cf = (f['x'] + ICON_WIDTH / 2, f['y'] + ICON_HEIGHT / 2)
            ct = (t['x'] + ICON_WIDTH / 2, t['y'] + ICON_HEIGHT / 2)
            pts = [clip_shape(f, *ct), clip_shape(t, *cf)]
            c['_straight'] = True
        else:
            # §H24/§H26: ruteo ortogonal RADIAL — el primer/último tramo sale y
            # entra perpendicular al borde por el lado del puerto (sf/st). Las
            # aristas largas (§B4) también caen aquí: con el sumidero adyacente
            # (§H25) basta un codo en L/S, sin diagonales entre waypoints.
            pts = _ortho_route(p_from, sf, p_to, st, channel_offset.get(ci, 0.0))

        # QA-Q2: refuerzo — garantiza tramo perpendicular en los extremos.
        # §M44: los cruces D13 se EXCLUYEN — un cruce real es recta PURA puerto
        # a puerto (el stub lo convertía en híbrido codo+diagonal de 4 puntos).
        if ci not in straight_cross:
            pts = _perp_stubs(pts, f, t)
        c['computed_path'] = {'type': 'polyline', 'points': pts}
        # Los puertos ya están EXACTAMENTE sobre el borde del icono (§C9/§C10);
        # marcarlos para que el renderer NO aplique su offset de 40px (que
        # dejaba los conectores flotando — QA-Q1/Q3 de Claude Design).
        c['_from_port'] = pts[0]
        c['_to_port'] = pts[-1]


def _ortho_route(p_from, side_f, p_to, side_t, channel=0.0):
    """Ruta ortogonal respetando la dirección radial de cada puerto (§H24/§H26):
    el primer tramo SALE perpendicular al borde por `side_f` y el último ENTRA
    perpendicular por `side_t`. Sin diagonales (solo codos de 90°)."""
    fx, fy = p_from
    tx, ty = p_to
    f_horiz = side_f in ('left', 'right')
    t_horiz = side_t in ('left', 'right')
    if not f_horiz and not t_horiz:
        # ambos verticales (flujo abajo/arriba): recta si alineados, si no S.
        if abs(fx - tx) < 1.0:
            return [p_from, p_to]
        mid = (fy + ty) / 2 + channel
        return [p_from, (fx, mid), (tx, mid), p_to]
    if f_horiz and not t_horiz:
        # sale horizontal (vértice lateral), entra vertical (arriba/abajo) → L.
        return [p_from, (tx, fy), p_to]
    if not f_horiz and t_horiz:
        # sale vertical, entra horizontal → L.
        return [p_from, (fx, ty), p_to]
    # ambos horizontales (mismo nivel, lado a lado): recta si alineados, si no Z.
    if abs(fy - ty) < 1.0:
        return [p_from, p_to]
    mid = (fx + tx) / 2 + channel
    return [p_from, (mid, fy), (mid, ty), p_to]


PERP_STUB = 14.0


def _border_side(pt, e):
    x, y = pt
    d = {'T': abs(y - e['y']), 'B': abs(y - (e['y'] + ICON_HEIGHT)),
         'L': abs(x - e['x']), 'R': abs(x - (e['x'] + ICON_WIDTH))}
    return min(d, key=d.get)


def _stub_point(pt, side):
    x, y = pt
    if side == 'T':
        return (x, y - PERP_STUB)
    if side == 'B':
        return (x, y + PERP_STUB)
    if side == 'L':
        return (x - PERP_STUB, y)
    return (x + PERP_STUB, y)


def _is_perp(a, b, side):
    dx, dy = b[0] - a[0], b[1] - a[1]
    if side in ('T', 'B'):
        return abs(dx) <= 0.5   # segmento vertical
    return abs(dy) <= 0.5       # segmento horizontal


def _perp_stubs(pts, from_elem, to_elem):
    """Garantiza que el primer y último segmento sean perpendiculares al borde
    (QA-Q2). Inserta un tramo recto de PERP_STUB si el segmento extremo llega
    en diagonal."""
    pts = list(pts)
    if len(pts) < 2:
        return pts
    # llegada
    side_t = _border_side(pts[-1], to_elem)
    if not _is_perp(pts[-2], pts[-1], side_t):
        pts.insert(-1, _stub_point(pts[-1], side_t))
    # salida
    side_f = _border_side(pts[0], from_elem)
    if not _is_perp(pts[0], pts[1], side_f):
        pts.insert(1, _stub_point(pts[0], side_f))
    return pts


def _separate(vals, min_sep, lo, hi):
    """Empuja valores ordenados para respetar min_sep, acotado a [lo,hi]."""
    if not vals:
        return vals
    out = list(vals)
    for i in range(1, len(out)):
        if out[i] - out[i - 1] < min_sep:
            out[i] = out[i - 1] + min_sep
    # si se pasó de hi, comprimir hacia abajo
    if out[-1] > hi:
        shift = out[-1] - hi
        out = [v - shift for v in out]
    out = [max(lo, v) for v in out]
    return out
