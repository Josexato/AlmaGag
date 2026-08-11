"""
WISH-DRAW-002 — Recorridos narrativos resaltados («highlighter»).

Renombrado en v3.9: la sección top-level pasó de `journeys` a `journeys`
(decisión de consistencia: «journey» quedó reservado para canvas.journey, la
dirección de lectura del grafo).

Capa de ANOTACIÓN, no de topología: un recorrido narra un recorrido sobre el
diagrama ya tendido — el camino de un paquete, un trámite, una cadena de
aprobación — sin agregar aristas ni alterar el layout.

Formato (top-level):

    "journeys": [
      {"id": "scada", "label": "Datos SCADA", "color": "#f7e017",
       "path": ["cpe_mina", "est2", "dc_mina", "cco"]}
    ]

Render: trazo ancho semitransparente (puntas redondas) que pasa por los
elementos del `path` EN ORDEN. Entre dos elementos consecutivos, el trazo
SIGUE el `computed_path` de la conexión declarada (en cualquier sentido) —
el resaltador pasa por donde pasan los cables, troncales §P60 incluidas.

Contrato de autoría (U74/U77): un recorrido sólo recorre ARISTAS EXISTENTES —
cero geometría propia. Un par consecutivo sin conexión declarada, un id
inexistente o un recorrido sin `label` son ERROR DURO (ValueError); dos recorridos
con el mismo color o más de 4 recorridos por lámina, WARNING. Capa: sobre
fondos/zonas y bajo iconos, líneas y textos.

Todo elemento del recorrido lleva `class="ag-journey"`: invisible para métricas,
ruteo y validadores (mismo mecanismo que `ag-text-halo`). Los colores por
defecto son la paleta de resaltador; `color` acepta hex/CSS o token §O57
(resuelto antes por apply_theme).
"""

import logging

from AlmaGag.config import ICON_WIDTH, ICON_HEIGHT

logger = logging.getLogger('AlmaGag')

JOURNEY_CLASS = 'ag-journey'
JOURNEY_WIDTH = 28.0          # ancho del trazo (px)
JOURNEY_OPACITY = 0.30        # transparencia de resaltador
# paleta de resaltador (se cicla si hay más recorridos que colores)
JOURNEY_PALETTE = ('#f7e017', '#7ce07c', '#ff9ad5', '#7cd6e0')


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


def build_journey_points(journey, elements_by_id, connections):
    """Polilínea completa de un recorrido: concatena los tramos entre elementos
    consecutivos del path siguiendo la conexión declarada de cada par (U74:
    cero geometría propia — sin conexión no hay tramo, es error duro).
    Devuelve la lista de puntos, o None si el recorrido no es dibujable."""
    fid = journey.get('id', '?')
    ids = [i for i in journey.get('path', []) if isinstance(i, str)]
    known = []
    for i in ids:
        e = elements_by_id.get(i)
        if e is None:
            raise ValueError(
                f"[journeys] id '{i}' del recorrido '{fid}' no existe en elements")
        if 'x' not in e:
            logger.warning(f"journeys: '{i}' del recorrido '{fid}' no tiene "
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
                f"[journeys] par ({a['id']}, {b['id']}) del recorrido '{fid}' sin "
                f"conexión declarada — un recorrido sólo recorre aristas "
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
    recorridos que lo comparten se reparten hacia los MISMOS lados del mundo,
    recorran el tramo en el sentido que lo recorran."""
    (ax, ay), (bx, by) = key
    dx, dy = bx - ax, by - ay
    L = (dx * dx + dy * dy) ** 0.5
    if L < 1e-9:
        return None
    return (-dy / L, dx / L)


def build_journey_lanes(journeys, elements_by_id, connections):
    """U75: puntos finales de cada flujo con reparto en CARRILES.

    Construye las polilíneas (contrato U74/U77 mediante build_journey_points),
    detecta los tramos compartidos por varios recorridos y desplaza cada uno
    perpendicularmente: N recorridos sobre un tramo común quedan lado a lado
    (paso = JOURNEY_WIDTH, carril por orden de aparición), ninguno tapado.
    Devuelve [(journey, points)] sólo con los dibujables."""
    built = []
    for journey in journeys:
        points = build_journey_points(journey, elements_by_id, connections)
        built.append((journey, points))

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
    for fi, (journey, pts) in enumerate(built):
        if not pts:
            out.append((journey, None))
            continue
        lane_pts = []
        for p, q in zip(pts, pts[1:]):
            key = _seg_key(p, q)
            riders = occupancy.get(key, [fi])
            n = _canonical_normal(key)
            if len(riders) > 1 and n is not None:
                off = (riders.index(fi) - (len(riders) - 1) / 2.0) * JOURNEY_WIDTH
                pp = (p[0] + n[0] * off, p[1] + n[1] * off)
                qq = (q[0] + n[0] * off, q[1] + n[1] * off)
            else:
                pp, qq = p, q
            for pt in (pp, qq):
                if not lane_pts or abs(lane_pts[-1][0] - pt[0]) > 0.05 \
                        or abs(lane_pts[-1][1] - pt[1]) > 0.05:
                    lane_pts.append(pt)
        out.append((journey, lane_pts if len(lane_pts) >= 2 else None))
    return out


def draw_journeys(dwg, journeys, elements_by_id, connections) -> int:
    """Dibuja los recorridos como trazos de resaltador. Devuelve cuántos se
    dibujaron. No-op silencioso sin sección `journeys`."""
    if not journeys:
        return 0
    # U77: audit de autoría — label obligatorio, colores sin repetir,
    # recomendación ≤4 recorridos por lámina.
    declared = [f for f in journeys if isinstance(f, dict)]
    for journey in declared:
        if not journey.get('label'):
            raise ValueError(
                f"[journeys] el recorrido '{journey.get('id', '?')}' no declara "
                f"label — obligatorio (va a la leyenda «Recorridos:»)")
    seen_colors = {}
    for f in declared:
        col = f.get('color')
        if col and col in seen_colors:
            logger.warning(f"journeys: '{f.get('id', '?')}' repite el color "
                           f"{col} de '{seen_colors[col]}' — dos recorridos "
                           f"iguales no se distinguen")
        elif col:
            seen_colors[col] = f.get('id', '?')
    if len(declared) > 4:
        logger.warning(f"journeys: {len(declared)} recorridos en una lámina — la "
                       f"recomendación de autoría es ≤4 (el resaltador "
                       f"pierde contraste)")
    n = 0
    for i, (journey, points) in enumerate(
            build_journey_lanes(declared, elements_by_id, connections)):
        if points is None:
            logger.warning(f"journeys: el recorrido '{journey.get('id', i)}' no tiene "
                           f"≥2 elementos dibujables — no se pinta")
            continue
        color = journey.get('color') or JOURNEY_PALETTE[n % len(JOURNEY_PALETTE)]
        dwg.add(dwg.polyline(
            points=[(round(x, 2), round(y, 2)) for x, y in points],
            fill='none', stroke=color,
            stroke_width=JOURNEY_WIDTH, stroke_opacity=JOURNEY_OPACITY,
            stroke_linecap='round', stroke_linejoin='round',
            class_=JOURNEY_CLASS))
        n += 1
    if n:
        logger.info(f"journeys: {n} recorrido(s) resaltado(s) sobre el diagrama")
    return n


def draw_journey_legend(dwg, journeys, canvas_width, canvas_height, y_offset=0):
    """Leyenda «Recorridos:» al pie (análoga a §N48). Un swatch de resaltador
    por recorrido DIBUJABLE con label; sin labels no hay leyenda."""
    entries = []
    n = 0
    for i, journey in enumerate(journeys or []):
        if not isinstance(journey, dict):
            continue
        color = journey.get('color') or JOURNEY_PALETTE[n % len(JOURNEY_PALETTE)]
        n += 1
        if journey.get('label'):
            entries.append((str(journey['label']), color))
    if not entries:
        return False

    legend = dwg.g(class_='ag-bottom-anchored')
    y = canvas_height - 30 - y_offset
    x = 24
    legend.add(dwg.text('Recorridos:', insert=(x, y + 4),
                        font_size='11px', font_weight='700',
                        font_family='Arial, sans-serif', fill='#5a5648'))
    x += 60
    for label, color in entries:
        legend.add(dwg.line(start=(x, y), end=(x + 26, y), stroke=color,
                            stroke_width=10, stroke_opacity=JOURNEY_OPACITY,
                            stroke_linecap='round', class_=JOURNEY_CLASS))
        legend.add(dwg.text(label, insert=(x + 32, y + 4),
                            font_size='11px', font_family='Arial, sans-serif',
                            fill='#3a362c'))
        x += 58 + len(label) * 6.8
    dwg.add(legend)
    return True
