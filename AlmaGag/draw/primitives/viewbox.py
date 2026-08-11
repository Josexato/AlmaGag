"""§O51 — viewBox recortado al contenido en la emisión.

El canvas se expande durante el layout pero nunca se contrae: un diagrama
chico sobre un canvas declarado grande emitía láminas casi vacías (1400×900
con <2% de tinta). Al final de emit, el viewBox (y width/height) se recorta
al bbox de todo lo dibujado + margen. Regla: SÓLO contraer, nunca expandir —
las estimaciones de ancho de texto son aproximadas y un sobrestimado no debe
agrandar la lámina.

Las leyendas de la franja inferior (§I30 roles, §N48 tipos de conexión) van
ancladas al borde del canvas, no al contenido: se marcan con la clase
`ag-bottom-anchored`, se excluyen del bbox vertical y se trasladan al nuevo
borde inferior tras el recorte.
"""

import math
import re

SVG_NS = 'http://www.w3.org/2000/svg'

# Clase que marca grupos anclados al borde inferior del canvas (leyendas).
BOTTOM_ANCHORED_CLASS = 'ag-bottom-anchored'

# Margen de aire alrededor del contenido (px) al recortar.
CROP_MARGIN = 40

_NUM = re.compile(r'[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?')

# Ancho promedio de un carácter Arial ≈ 0.6×font-size; algo generoso a
# propósito: sobrestimar sólo hace el recorte menos agresivo (nunca corta).
_CHAR_W = 0.62

_IDENTITY = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)


def _mat_mul(m, n):
    """Composición de afines (a,b,c,d,e,f): primero n, después m."""
    ma, mb, mc, md, me, mf = m
    na, nb, nc, nd, ne, nf = n
    return (ma * na + mc * nb, mb * na + md * nb,
            ma * nc + mc * nd, mb * nc + md * nd,
            ma * ne + mc * nf + me, mb * ne + md * nf + mf)


def _apply(m, x, y):
    a, b, c, d, e, f = m
    return (a * x + c * y + e, b * x + d * y + f)


def parse_transform(s):
    """Parsea un atributo transform SVG a una matriz afín (a,b,c,d,e,f)."""
    m = _IDENTITY
    for name, args in re.findall(r'(\w+)\s*\(([^)]*)\)', s or ''):
        v = [float(n) for n in _NUM.findall(args)]
        if name == 'translate':
            t = (1, 0, 0, 1, v[0], v[1] if len(v) > 1 else 0.0)
        elif name == 'scale':
            t = (v[0], 0, 0, v[1] if len(v) > 1 else v[0], 0, 0)
        elif name == 'rotate':
            a = math.radians(v[0])
            t = (math.cos(a), math.sin(a), -math.sin(a), math.cos(a), 0, 0)
            if len(v) == 3:
                cx, cy = v[1], v[2]
                t = _mat_mul(_mat_mul((1, 0, 0, 1, cx, cy), t),
                             (1, 0, 0, 1, -cx, -cy))
        elif name == 'matrix' and len(v) == 6:
            t = tuple(v)
        elif name == 'skewX':
            t = (1, 0, math.tan(math.radians(v[0])), 1, 0, 0)
        elif name == 'skewY':
            t = (1, math.tan(math.radians(v[0])), 0, 1, 0, 0)
        else:
            continue
        m = _mat_mul(m, t)
    return m


def _arc_points(p0, rx, ry, rot_deg, large_arc, sweep, p1, samples=16):
    """Puntos muestreados de un arco elíptico (comando A/a).

    Parametrización endpoint→centro del spec SVG (F.6.5) y muestreo del
    barrido real: con 16 muestras el error de bbox es <0.5% del radio —
    despreciable frente al margen de recorte. Degenerados (radio 0,
    endpoints coincidentes) caen al punto final, como manda el spec.
    """
    x0, y0 = p0
    x1, y1 = p1
    rx, ry = abs(rx), abs(ry)
    if rx == 0 or ry == 0 or (x0 == x1 and y0 == y1):
        return [p1]
    phi = math.radians(rot_deg % 360)
    cosp, sinp = math.cos(phi), math.sin(phi)
    # (F.6.5.1) al marco de la elipse
    dx, dy = (x0 - x1) / 2.0, (y0 - y1) / 2.0
    x1p = cosp * dx + sinp * dy
    y1p = -sinp * dx + cosp * dy
    # (F.6.6) corregir radios insuficientes
    lam = (x1p / rx) ** 2 + (y1p / ry) ** 2
    if lam > 1:
        s = math.sqrt(lam)
        rx, ry = rx * s, ry * s
    # (F.6.5.2) centro en el marco de la elipse
    num = rx * rx * ry * ry - rx * rx * y1p * y1p - ry * ry * x1p * x1p
    den = rx * rx * y1p * y1p + ry * ry * x1p * x1p
    coef = math.sqrt(max(0.0, num / den)) if den else 0.0
    if large_arc == sweep:
        coef = -coef
    cxp = coef * rx * y1p / ry
    cyp = -coef * ry * x1p / rx
    # (F.6.5.3) centro real
    cx = cosp * cxp - sinp * cyp + (x0 + x1) / 2.0
    cy = sinp * cxp + cosp * cyp + (y0 + y1) / 2.0

    def _angle(ux, uy, vx, vy):
        dot = ux * vx + uy * vy
        norm = math.hypot(ux, uy) * math.hypot(vx, vy)
        a = math.acos(max(-1.0, min(1.0, dot / norm)))
        return -a if ux * vy - uy * vx < 0 else a

    theta1 = _angle(1, 0, (x1p - cxp) / rx, (y1p - cyp) / ry)
    dtheta = _angle((x1p - cxp) / rx, (y1p - cyp) / ry,
                    (-x1p - cxp) / rx, (-y1p - cyp) / ry)
    if not sweep and dtheta > 0:
        dtheta -= 2 * math.pi
    elif sweep and dtheta < 0:
        dtheta += 2 * math.pi

    pts = []
    for k in range(samples + 1):
        t = theta1 + dtheta * k / samples
        ex = rx * math.cos(t)
        ey = ry * math.sin(t)
        pts.append((cosp * ex - sinp * ey + cx, sinp * ex + cosp * ey + cy))
    return pts


def _path_points(d):
    """Puntos de un path (anclas + puntos de control: bbox conservador).

    El bbox de una Bézier está contenido en el casco de sus puntos de
    control, así que incluirlos nunca deja contenido afuera. Los arcos (A/a)
    se muestrean sobre su barrido real (`_arc_points`).
    """
    pts = []
    cur = (0.0, 0.0)
    start = (0.0, 0.0)
    for cmd, args in re.findall(r'([MmLlHhVvCcSsQqTtAaZz])([^MmLlHhVvCcSsQqTtAaZz]*)', d):
        v = [float(n) for n in _NUM.findall(args)]
        rel = cmd.islower()
        c = cmd.upper()
        i = 0

        def pt(dx, dy):
            return (cur[0] + dx, cur[1] + dy) if rel else (dx, dy)

        if c == 'Z':
            cur = start
            continue
        while i < len(v) or (c == 'Z'):
            if c == 'M':
                cur = pt(v[i], v[i + 1]); i += 2
                start = cur
                pts.append(cur)
                c = 'L'                      # pares siguientes: lineto implícito
            elif c == 'L' or c == 'T':
                cur = pt(v[i], v[i + 1]); i += 2
                pts.append(cur)
            elif c == 'H':
                cur = ((cur[0] + v[i]) if rel else v[i], cur[1]); i += 1
                pts.append(cur)
            elif c == 'V':
                cur = (cur[0], (cur[1] + v[i]) if rel else v[i]); i += 1
                pts.append(cur)
            elif c == 'C':
                pts.append(pt(v[i], v[i + 1]))
                pts.append(pt(v[i + 2], v[i + 3]))
                cur = pt(v[i + 4], v[i + 5]); i += 6
                pts.append(cur)
            elif c in ('S', 'Q'):
                pts.append(pt(v[i], v[i + 1]))
                cur = pt(v[i + 2], v[i + 3]); i += 4
                pts.append(cur)
            elif c == 'A':
                end = pt(v[i + 5], v[i + 6])
                pts.extend(_arc_points(cur, v[i], v[i + 1], v[i + 2],
                                       bool(v[i + 3]), bool(v[i + 4]), end))
                cur = end; i += 7
            else:
                break
    return pts


def _text_corners(elem):
    """Esquinas estimadas del bbox local de un <text> (ancla + métrica Arial)."""
    try:
        x = float(elem.get('x', 0))
        y = float(elem.get('y', 0))
    except ValueError:
        return []
    fs = str(elem.get('font-size', '14')).replace('px', '')
    try:
        fs = float(fs)
    except ValueError:
        fs = 14.0
    content = ''.join(elem.itertext())
    w = len(content) * fs * _CHAR_W
    anchor = elem.get('text-anchor', 'start')
    if anchor == 'middle':
        x0 = x - w / 2
    elif anchor == 'end':
        x0 = x - w
    else:
        x0 = x
    # ascent ≈ fs, descent ≈ 0.25×fs
    return [(x0, y - fs), (x0 + w, y - fs), (x0, y + fs * 0.25), (x0 + w, y + fs * 0.25)]


def _element_corners(elem):
    """Puntos locales (sin transformar) que acotan la geometría del elemento."""
    tag = elem.tag.split('}')[-1]
    g = elem.get
    try:
        if tag == 'rect' or tag == 'image':
            x, y = float(g('x', 0)), float(g('y', 0))
            w, h = float(g('width', 0)), float(g('height', 0))
            return [(x, y), (x + w, y + h)]
        if tag == 'circle':
            cx, cy, r = float(g('cx', 0)), float(g('cy', 0)), float(g('r', 0))
            return [(cx - r, cy - r), (cx + r, cy + r)]
        if tag == 'ellipse':
            cx, cy = float(g('cx', 0)), float(g('cy', 0))
            rx, ry = float(g('rx', 0)), float(g('ry', 0))
            return [(cx - rx, cy - ry), (cx + rx, cy + ry)]
        if tag == 'line':
            return [(float(g('x1', 0)), float(g('y1', 0))),
                    (float(g('x2', 0)), float(g('y2', 0)))]
        if tag in ('polyline', 'polygon'):
            v = [float(n) for n in _NUM.findall(g('points', ''))]
            return list(zip(v[0::2], v[1::2]))
        if tag == 'path':
            return _path_points(g('d', ''))
        if tag == 'text':
            return _text_corners(elem)
    except (TypeError, ValueError):
        return []
    return []


_SKIP_TAGS = {'defs', 'title', 'desc', 'metadata', 'style', 'marker',
              'linearGradient', 'radialGradient', 'filter', 'clipPath',
              'mask', 'symbol', 'pattern'}


def _walk_bbox(elem, ctm, bounds, skip_classes):
    tag = elem.tag.split('}')[-1]
    if tag in _SKIP_TAGS:
        return
    classes = (elem.get('class') or '').split()
    if any(c in skip_classes for c in classes):
        return
    m = ctm
    tr = elem.get('transform')
    if tr:
        m = _mat_mul(ctm, parse_transform(tr))
    for (x, y) in _element_corners(elem):
        tx, ty = _apply(m, x, y)
        bounds[0] = min(bounds[0], tx)
        bounds[1] = min(bounds[1], ty)
        bounds[2] = max(bounds[2], tx)
        bounds[3] = max(bounds[3], ty)
    for child in elem:
        _walk_bbox(child, m, bounds, skip_classes)


def content_bbox(root, skip_classes=()):
    """Bbox (minx, miny, maxx, maxy) de lo dibujado, o None si no hay nada."""
    bounds = [math.inf, math.inf, -math.inf, -math.inf]
    _walk_bbox(root, _IDENTITY, bounds, frozenset(skip_classes))
    if bounds[0] is math.inf or bounds[0] > bounds[2]:
        return None
    return tuple(bounds)


def _fmt(x):
    """Número compacto: entero si lo es (mismo estilo que svgwrite)."""
    return str(int(x)) if float(x).is_integer() else f'{x:.1f}'


def crop_viewbox(root, margin=CROP_MARGIN):
    """Recorta viewBox/width/height del root al contenido + margen.

    Sólo contrae (nunca expande) y traslada los grupos `ag-bottom-anchored`
    (leyendas) al nuevo borde inferior, conservando su distancia al borde y
    su margen izquierdo. Devuelve True si hubo recorte.
    """
    vb = root.get('viewBox') or root.get('viewbox')
    try:
        if vb:
            vx, vy, vw, vh = [float(n) for n in _NUM.findall(vb)]
        else:
            vx, vy = 0.0, 0.0
            vw = float(str(root.get('width', 0)).replace('px', ''))
            vh = float(str(root.get('height', 0)).replace('px', ''))
    except (TypeError, ValueError):
        return False
    if vw <= 0 or vh <= 0:
        return False

    bbox = content_bbox(root, skip_classes=(BOTTOM_ANCHORED_CLASS,))
    if bbox is None:
        return False
    minx, miny, maxx, maxy = bbox

    # Las leyendas cuentan para el ancho (no cortarlas a la derecha), pero no
    # para el alto: se van a reanclar al nuevo borde inferior.
    legends = [g for g in root.iter(f'{{{SVG_NS}}}g')
               if BOTTOM_ANCHORED_CLASS in (g.get('class') or '').split()]
    for g in legends:
        sub = content_bbox(g)
        if sub:
            minx = min(minx, sub[0])
            maxx = max(maxx, sub[2])

    x0 = max(vx, minx - margin)
    y0 = max(vy, miny - margin)
    x1 = min(vx + vw, maxx + margin)
    y1 = min(vy + vh, maxy + margin)

    # BUGS-DRAW-005: el reanclaje conserva la distancia de cada leyenda al
    # borde inferior — si el nuevo borde queda a sólo `margin` del
    # contenido, la pila de leyendas cae ENCIMA de la última fila (caso TM:
    # Estados/Recorridos/Enlaces sobre 'Ingeniería'). El borde inferior
    # debe dejar sitio para la pila completa + un respiro.
    if legends:
        dist_max = 0.0
        for g in legends:
            sub = content_bbox(g)
            if sub:
                dist_max = max(dist_max, (vy + vh) - sub[1])
        if dist_max:
            y1 = min(vy + vh, max(y1, maxy + 12.0 + dist_max))

    if x1 - x0 >= vw and y1 - y0 >= vh:
        return False                      # nada que contraer
    if x1 <= x0 or y1 <= y0:
        return False

    root.set('viewBox', f'{_fmt(x0)},{_fmt(y0)},{_fmt(x1 - x0)},{_fmt(y1 - y0)}')
    root.attrib.pop('viewbox', None)
    root.set('width', _fmt(x1 - x0))
    root.set('height', _fmt(y1 - y0))

    dx = x0 - vx                          # conservar margen izquierdo
    dy = (y1 - (vy + vh))                 # nuevo borde inferior
    for g in legends:
        if dx or dy:
            g.set('transform', f'translate({_fmt(dx)},{_fmt(dy)})')
    return True
