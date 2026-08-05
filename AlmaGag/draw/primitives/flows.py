"""
WISH-DRAW-002 — Flujos de información resaltados («highlighter»).

Capa de ANOTACIÓN, no de topología: un flujo narra un recorrido sobre el
diagrama ya tendido — el camino de un paquete, un trámite, una cadena de
aprobación — sin agregar aristas ni alterar el layout.

Formato (top-level):

    "flows": [
      {"id": "scada", "label": "Datos SCADA", "color": "#f7e017",
       "path": ["cpe_mina", "est2", "dc_mina", "cco"]}
    ]

Render: trazo ancho semitransparente (puntas redondas) que pasa por los
elementos del `path` EN ORDEN. Entre dos elementos consecutivos, el trazo
SIGUE el `computed_path` de la conexión declarada (en cualquier sentido) —
el resaltador pasa por donde pasan los cables, troncales §P60 incluidas.

Contrato de autoría (U74/U77): un flujo sólo recorre ARISTAS EXISTENTES —
cero geometría propia. Un par consecutivo sin conexión declarada, un id
inexistente o un flujo sin `label` son ERROR DURO (ValueError); dos flujos
con el mismo color o más de 4 flujos por lámina, WARNING. Capa: sobre
fondos/zonas y bajo iconos, líneas y textos.

Todo elemento del flujo lleva `class="ag-flow"`: invisible para métricas,
ruteo y validadores (mismo mecanismo que `ag-text-halo`). Los colores por
defecto son la paleta de resaltador; `color` acepta hex/CSS o token §O57
(resuelto antes por apply_theme).
"""

import logging

from AlmaGag.config import ICON_WIDTH, ICON_HEIGHT

logger = logging.getLogger('AlmaGag')

FLOW_CLASS = 'ag-flow'
FLOW_WIDTH = 28.0          # ancho del trazo (px)
FLOW_OPACITY = 0.30        # transparencia de resaltador
# paleta de resaltador (se cicla si hay más flujos que colores)
FLOW_PALETTE = ('#f7e017', '#7ce07c', '#ff9ad5', '#7cd6e0')


def _center(e):
    return (e['x'] + e.get('width', ICON_WIDTH) / 2.0,
            e['y'] + e.get('height', ICON_HEIGHT) / 2.0)


def _find_conn(connections, a, b):
    """Conexión declarada a→b o b→a. Devuelve (conn, invertida) o None."""
    for c in connections:
        if c.get('from') == a and c.get('to') == b:
            return c, False
        if c.get('from') == b and c.get('to') == a:
            return c, True
    return None


def _conn_points(conn, reverse):
    """Puntos del computed_path de la conexión (invertidos si hace falta)."""
    cp = conn.get('computed_path')
    pts = cp.get('points') if isinstance(cp, dict) else None
    if not pts or len(pts) < 2:
        return None
    xy = [((p[0], p[1]) if not hasattr(p, 'x') else (p.x, p.y)) for p in pts]
    return list(reversed(xy)) if reverse else xy


def build_flow_points(flow, elements_by_id, connections):
    """Polilínea completa de un flujo: concatena los tramos entre elementos
    consecutivos del path siguiendo la conexión declarada de cada par (U74:
    cero geometría propia — sin conexión no hay tramo, es error duro).
    Devuelve la lista de puntos, o None si el flujo no es dibujable."""
    fid = flow.get('id', '?')
    ids = [i for i in flow.get('path', []) if isinstance(i, str)]
    known = []
    for i in ids:
        e = elements_by_id.get(i)
        if e is None:
            raise ValueError(
                f"[flows] id '{i}' del flujo '{fid}' no existe en elements")
        if 'x' not in e:
            logger.warning(f"flows: '{i}' del flujo '{fid}' no tiene "
                           f"posición — se omite del recorrido")
            continue
        known.append(e)
    if len(known) < 2:
        return None

    points = []
    for a, b in zip(known, known[1:]):
        found = _find_conn(connections, a['id'], b['id'])
        if found is None:
            raise ValueError(
                f"[flows] par ({a['id']}, {b['id']}) del flujo '{fid}' sin "
                f"conexión declarada — un flujo sólo recorre aristas "
                f"existentes (U74)")
        conn, reverse = found
        seg = _conn_points(conn, reverse)
        if seg is None:
            # la conexión existe pero se dibuja recta (sin computed_path):
            # el resaltador sigue esa misma recta — nunca geometría propia
            seg = [_center(a), _center(b)]
        if points and abs(points[-1][0] - seg[0][0]) < 0.5 \
                and abs(points[-1][1] - seg[0][1]) < 0.5:
            seg = seg[1:]          # no duplicar el punto de empalme
        points.extend(seg)
    return points if len(points) >= 2 else None


def _seg_key(p, q):
    """Clave canónica de un tramo (independiente del sentido de recorrido)."""
    a = (round(p[0], 1), round(p[1], 1))
    b = (round(q[0], 1), round(q[1], 1))
    return (a, b) if a <= b else (b, a)


def _canonical_normal(key):
    """Normal unitaria del tramo en su orientación canónica: todos los
    flujos que lo comparten se reparten hacia los MISMOS lados del mundo,
    recorran el tramo en el sentido que lo recorran."""
    (ax, ay), (bx, by) = key
    dx, dy = bx - ax, by - ay
    L = (dx * dx + dy * dy) ** 0.5
    if L < 1e-9:
        return None
    return (-dy / L, dx / L)


def build_flow_lanes(flows, elements_by_id, connections):
    """U75: puntos finales de cada flujo con reparto en CARRILES.

    Construye las polilíneas (contrato U74/U77 mediante build_flow_points),
    detecta los tramos compartidos por varios flujos y desplaza cada uno
    perpendicularmente: N flujos sobre un tramo común quedan lado a lado
    (paso = FLOW_WIDTH, carril por orden de aparición), ninguno tapado.
    Devuelve [(flow, points)] sólo con los dibujables."""
    built = []
    for flow in flows:
        points = build_flow_points(flow, elements_by_id, connections)
        built.append((flow, points))

    occupancy = {}            # seg_key -> [índices de flujo, orden estable]
    for fi, (_, pts) in enumerate(built):
        if not pts:
            continue
        for p, q in zip(pts, pts[1:]):
            key = _seg_key(p, q)
            riders = occupancy.setdefault(key, [])
            if fi not in riders:
                riders.append(fi)

    out = []
    for fi, (flow, pts) in enumerate(built):
        if not pts:
            out.append((flow, None))
            continue
        lane_pts = []
        for p, q in zip(pts, pts[1:]):
            key = _seg_key(p, q)
            riders = occupancy.get(key, [fi])
            n = _canonical_normal(key)
            if len(riders) > 1 and n is not None:
                off = (riders.index(fi) - (len(riders) - 1) / 2.0) * FLOW_WIDTH
                pp = (p[0] + n[0] * off, p[1] + n[1] * off)
                qq = (q[0] + n[0] * off, q[1] + n[1] * off)
            else:
                pp, qq = p, q
            for pt in (pp, qq):
                if not lane_pts or abs(lane_pts[-1][0] - pt[0]) > 0.05 \
                        or abs(lane_pts[-1][1] - pt[1]) > 0.05:
                    lane_pts.append(pt)
        out.append((flow, lane_pts if len(lane_pts) >= 2 else None))
    return out


def draw_flows(dwg, flows, elements_by_id, connections) -> int:
    """Dibuja los flujos como trazos de resaltador. Devuelve cuántos se
    dibujaron. No-op silencioso sin sección `flows`."""
    if not flows:
        return 0
    # U77: audit de autoría — label obligatorio, colores sin repetir,
    # recomendación ≤4 flujos por lámina.
    declared = [f for f in flows if isinstance(f, dict)]
    for flow in declared:
        if not flow.get('label'):
            raise ValueError(
                f"[flows] el flujo '{flow.get('id', '?')}' no declara "
                f"label — obligatorio (va a la leyenda «Flujos:»)")
    seen_colors = {}
    for f in declared:
        col = f.get('color')
        if col and col in seen_colors:
            logger.warning(f"flows: '{f.get('id', '?')}' repite el color "
                           f"{col} de '{seen_colors[col]}' — dos flujos "
                           f"iguales no se distinguen")
        elif col:
            seen_colors[col] = f.get('id', '?')
    if len(declared) > 4:
        logger.warning(f"flows: {len(declared)} flujos en una lámina — la "
                       f"recomendación de autoría es ≤4 (el resaltador "
                       f"pierde contraste)")
    n = 0
    for i, (flow, points) in enumerate(
            build_flow_lanes(declared, elements_by_id, connections)):
        if points is None:
            logger.warning(f"flows: el flujo '{flow.get('id', i)}' no tiene "
                           f"≥2 elementos dibujables — no se pinta")
            continue
        color = flow.get('color') or FLOW_PALETTE[n % len(FLOW_PALETTE)]
        dwg.add(dwg.polyline(
            points=[(round(x, 2), round(y, 2)) for x, y in points],
            fill='none', stroke=color,
            stroke_width=FLOW_WIDTH, stroke_opacity=FLOW_OPACITY,
            stroke_linecap='round', stroke_linejoin='round',
            class_=FLOW_CLASS))
        n += 1
    if n:
        logger.info(f"flows: {n} flujo(s) resaltado(s) sobre el diagrama")
    return n


def draw_flow_legend(dwg, flows, canvas_width, canvas_height, y_offset=0):
    """Leyenda «Flujos:» al pie (análoga a §N48). Un swatch de resaltador
    por flujo DIBUJABLE con label; sin labels no hay leyenda."""
    entries = []
    n = 0
    for i, flow in enumerate(flows or []):
        if not isinstance(flow, dict):
            continue
        color = flow.get('color') or FLOW_PALETTE[n % len(FLOW_PALETTE)]
        n += 1
        if flow.get('label'):
            entries.append((str(flow['label']), color))
    if not entries:
        return False

    legend = dwg.g(class_='ag-bottom-anchored')
    y = canvas_height - 30 - y_offset
    x = 24
    legend.add(dwg.text('Flujos:', insert=(x, y + 4),
                        font_size='11px', font_weight='700',
                        font_family='Arial, sans-serif', fill='#5a5648'))
    x += 60
    for label, color in entries:
        legend.add(dwg.line(start=(x, y), end=(x + 26, y), stroke=color,
                            stroke_width=10, stroke_opacity=FLOW_OPACITY,
                            stroke_linecap='round', class_=FLOW_CLASS))
        legend.add(dwg.text(label, insert=(x + 32, y + 4),
                            font_size='11px', font_family='Arial, sans-serif',
                            fill='#3a362c'))
        x += 58 + len(label) * 6.8
    dwg.add(legend)
    return True
