"""
Higiene de ruta Z96 — «la ruta no atraviesa lo que no es suyo».

Primitivas compartidas por el ruteo con áreas (areas.py, donde nacieron
como ARCH-009 v2 / Z96 fase 2-3) y por el ruteo plano de hier
(routing.py, BUGS-LAYOUT-016): el desvío de travesías completas
(`dodge_boxes`), el recorte de codos dentro de iconos ajenos
(`relocate_corners`) y la geometría de obstáculos icono+etiqueta
(`icon_obstacles`, W87: la travesía se DETECTA con el icono pelado y se
DESVÍA rodeando icono + label).
"""

from AlmaGag.config import ICON_WIDTH, ICON_HEIGHT

DODGE_M = 12.0      # holgura del desvío alrededor de una caja ajena
LABEL_LINE_H = 16.0                     # alto por línea de etiqueta (§J31)
LABEL_GAP = 12.0                        # aire entre icono y su etiqueta inferior
LABEL_CHAR_W = 6.6                      # ancho aprox. por carácter (12px)


def label_halfwidth(e):
    """Media anchura de la etiqueta (centrada bajo el icono)."""
    lbl = e.get('label')
    if not lbl:
        return ICON_WIDTH / 2
    w = max(len(ln) for ln in lbl.split('\n')) * LABEL_CHAR_W
    return max(ICON_WIDTH, w) / 2


def icon_obstacles(elements):
    """Cajas de obstáculo por icono raíz: `core` (icono pelado, para
    DETECTAR travesías) y `outers` (core → icono+etiqueta, para DESVIAR
    sin aterrizar sobre el label — W87). Los contenedores no entran: su
    caja calculada es obstáculo aparte y su label vive en el header."""
    icon_box, icon_outer = {}, {}
    for e in elements:
        if 'x' not in e or e.get('contains'):
            continue
        core = (e['x'], e['y'], e['x'] + ICON_WIDTH, e['y'] + ICON_HEIGHT)
        icon_box[e['id']] = core
        if e.get('label'):
            cx = e['x'] + ICON_WIDTH / 2
            hw = label_halfwidth(e)
            lines = e['label'].count('\n') + 1
            icon_outer[core] = (min(core[0], cx - hw), core[1],
                                max(core[2], cx + hw),
                                core[3] + LABEL_GAP + lines * LABEL_LINE_H)
    return icon_box, icon_outer


def seg_crosses_box(p, q, box):
    """True si el segmento p→q (orto o diagonal) corta el INTERIOR del
    rectángulo con ambos extremos fuera — una travesía, no una llegada.
    Clip paramétrico (Liang-Barsky)."""
    x0, y0, x1, y1 = box
    if (x0 < p[0] < x1 and y0 < p[1] < y1) or (x0 < q[0] < x1 and y0 < q[1] < y1):
        return False                     # un extremo adentro: entra, no atraviesa
    dx, dy = q[0] - p[0], q[1] - p[1]
    t0, t1 = 0.0, 1.0
    for num, den in (((x0 - p[0]), dx), ((p[0] - x1), -dx),
                     ((y0 - p[1]), dy), ((p[1] - y1), -dy)):
        if abs(den) < 1e-12:
            if num > 0:
                return False             # paralelo y fuera de la franja
            continue
        t = num / den
        if den > 0:
            t0 = max(t0, t)
        else:
            t1 = min(t1, t)
        if t0 > t1:
            return False
    return t1 - t0 > 1e-6


def dodge_boxes(pts, boxes, reg=None, outers=None):
    """ARCH-009 v2: ninguna ruta atraviesa un contenedor AJENO — cada
    segmento ortogonal que corta una caja se desvía por el borde más
    cercano (rectángulo + holgura). Se repite hasta limpiar o agotar el
    presupuesto (los desvíos nuevos pueden cortar otra caja).

    `reg` (ROUTE-008): registro COMPARTIDO entre rutas — dos rutas que
    rodean la misma caja por el mismo lado se escalonan (+7px cada una)
    en vez de montarse en la misma línea de desvío.

    `outers` (Z96 fase 2): mapa caja→caja EXTERIOR. La travesía se
    detecta con la caja núcleo (el icono) pero el desvío rodea la
    exterior (icono + su label, W87) — detectar con la inflada esconde
    travesías del icono puro, y desviar con la núcleo aterriza el
    desvío sobre la etiqueta."""
    def _m(box, side):
        if reg is None:
            return DODGE_M
        n = reg.get((box, side), 0)
        reg[(box, side)] = n + 1
        return DODGE_M + 7.0 * n
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
            axis, core = hit
            box = core
            x0, y0, x1, y1 = (outers or {}).get(core, core)
            if axis == 'h':
                y = p[1]
                top = y - y0 <= y1 - y
                m = _m(box, 'T' if top else 'B')
                yd = y0 - m if top else y1 + m
                if p[0] < q[0]:
                    xa, xb = x0 - DODGE_M, x1 + DODGE_M
                else:
                    xa, xb = x1 + DODGE_M, x0 - DODGE_M
                detour = [(xa, y), (xa, yd), (xb, yd), (xb, y)]
            else:
                x = p[0]
                left = x - x0 <= x1 - x
                m = _m(box, 'L' if left else 'R')
                xd = x0 - m if left else x1 + m
                if p[1] < q[1]:
                    ya, yb = y0 - DODGE_M, y1 + DODGE_M
                else:
                    ya, yb = y1 + DODGE_M, y0 - DODGE_M
                detour = [(x, ya), (xd, ya), (xd, yb), (x, yb)]
            pts = pts[:i + 1] + detour + pts[i + 1:]
            changed = True
            break
        if not changed:
            return dedupe(pts)
    return dedupe(pts)


def relocate_corners(pts, boxes, reg=None):
    """Z96 fase 3: el CODO fuera del icono. Un vértice de ruta que cae
    DENTRO de un icono ajeno es la clase que el desvío de travesías no
    ve (cada segmento solo ENTRA o solo SALE — nada lo cruza de lado a
    lado). El codo en L se recorta rodeando la esquina del icono: el
    tramo horizontal se clipea en el borde por el que venía, baja/sube
    por fuera, y retoma la vertical ya pasado el icono — tres puntos
    ortogonales en vez de un vértice adentro.

    Solo se toca el codo cuyos DOS vecinos están fuera de la caja (el
    caso medido); `reg` escalona igual que dodge_boxes."""
    def _m(box, side):
        if reg is None:
            return DODGE_M
        n = reg.get((box, side), 0)
        reg[(box, side)] = n + 1
        return DODGE_M + 7.0 * n

    def _inside(p, b):
        return b[0] < p[0] < b[2] and b[1] < p[1] < b[3]

    for _ in range(8):
        moved = False
        for i in range(1, len(pts) - 1):
            p = pts[i]
            box = next((b for b in boxes if _inside(p, b)), None)
            if box is None:
                continue
            a, b_ = pts[i - 1], pts[i + 1]
            if _inside(a, box) or _inside(b_, box):
                continue                      # vecino adentro: otra clase
            a_h = abs(a[1] - p[1]) < 0.01     # tramo a→p horizontal
            b_h = abs(b_[1] - p[1]) < 0.01
            if a_h == b_h:
                continue                      # no es un codo en L limpio
            qh, qv = (a, b_) if a_h else (b_, a)
            x0, y0, x1, y1 = box
            if qh[0] < p[0]:
                x_esc = x0 - _m(box, 'L')
            else:
                x_esc = x1 + _m(box, 'R')
            if qv[1] > p[1]:
                y_esc = y1 + _m(box, 'B')
            else:
                y_esc = y0 - _m(box, 'T')
            corte = [(x_esc, p[1]), (x_esc, y_esc), (p[0], y_esc)]
            if not a_h:
                corte.reverse()
            pts = pts[:i] + corte + pts[i + 1:]
            moved = True
            break
        if not moved:
            return dedupe(pts)
    return dedupe(pts)


def dedupe(pts):
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
