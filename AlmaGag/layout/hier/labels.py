"""
§F18 — Etiqueta al borde menos concurrido (WISH-LAF-002 Fase 3).

Por nodo cuenta los conectores que tocan cada borde (T/B/L/R) — incluidos
extremos de arcos — y elige el borde con menor conteo. Empate: abajo →
arriba → lado exterior (lejos del centro) → lado interior.

Setea `element['label_position']` como preferencia para el renderer.
"""

from AlmaGag.config import ICON_WIDTH, ICON_HEIGHT


def _endpoint_side(elem, px, py):
    """¿En qué borde del elemento cae el punto (px,py)? T/B/L/R."""
    x, y = elem['x'], elem['y']
    cx, cy = x + ICON_WIDTH / 2, y + ICON_HEIGHT / 2
    dx, dy = px - cx, py - cy
    # normalizar por medio-tamaño para comparar proximidad al borde
    if abs(dx) / (ICON_WIDTH / 2) >= abs(dy) / (ICON_HEIGHT / 2):
        return 'R' if dx >= 0 else 'L'
    return 'B' if dy >= 0 else 'T'


def assign_label_sides(layout):
    """Asigna element['label_position'] al borde menos concurrido (§F18)."""
    by_id = {e['id']: e for e in layout.elements}
    placed = {eid for eid, e in by_id.items() if 'x' in e and 'y' in e}
    if not placed:
        return

    cx0 = sum(by_id[e]['x'] + ICON_WIDTH / 2 for e in placed) / len(placed)

    counts = {eid: {'T': 0, 'B': 0, 'L': 0, 'R': 0} for eid in placed}
    for c in layout.connections:
        f, t = c.get('from'), c.get('to')
        if f not in placed or t not in placed:
            continue
        cp = c.get('computed_path')
        pts = cp.get('points') if cp else None
        if pts and len(pts) >= 2:
            fp, tp = pts[0], pts[-1]
        else:
            ff, tt = by_id[f], by_id[t]
            fp = (ff['x'] + ICON_WIDTH / 2, ff['y'] + ICON_HEIGHT / 2)
            tp = (tt['x'] + ICON_WIDTH / 2, tt['y'] + ICON_HEIGHT / 2)
        counts[f][_endpoint_side(by_id[f], *fp)] += 1
        counts[t][_endpoint_side(by_id[t], *tp)] += 1

    side_to_pos = {'B': 'bottom', 'T': 'top', 'L': 'left', 'R': 'right'}
    for eid in placed:
        e = by_id[eid]
        if not e.get('label') or 'label_position' in e:
            continue
        cnt = counts[eid]
        cx = e['x'] + ICON_WIDTH / 2
        outer = 'L' if cx < cx0 else 'R'
        inner = 'R' if outer == 'L' else 'L'
        # orden de preferencia del desempate: abajo→arriba→exterior→interior
        order = ['B', 'T', outer, inner]
        best = min(order, key=lambda s: (cnt[s], order.index(s)))
        e['label_position'] = side_to_pos[best]


# §G23 — etiqueta de conexión anclada junto al puerto de salida.
LABEL_ALONG = 16.0     # avance máximo sobre el primer segmento
LABEL_OFFSET = 9.0     # separación perpendicular a la línea


def assign_connection_label_anchors(layout):
    """§G23: fija `connection['_label_anchor']` (x,y) a ~14px del puerto de
    SALIDA, sobre el primer segmento del path, desplazado perpendicular para no
    quedar encima de la línea. Así el rótulo (sí/no/repetir) queda pegado a la
    decisión que lo origina, no en el punto medio de un path largo."""
    for c in layout.connections:
        if not c.get('label'):
            continue
        cp = c.get('computed_path')
        pts = cp.get('points') if cp else None
        if not pts or len(pts) < 2:
            continue
        (x0, y0), (x1, y1) = pts[0], pts[1]
        dx, dy = x1 - x0, y1 - y0
        seg = (dx * dx + dy * dy) ** 0.5
        if seg < 1e-6:
            continue
        ux, uy = dx / seg, dy / seg
        d = min(LABEL_ALONG, seg * 0.5)
        ax, ay = x0 + ux * d, y0 + uy * d
        # perpendicular unitaria (rota 90°); lado hacia afuera del centro-x.
        px, py = -uy, ux
        c['_label_anchor'] = (ax + px * LABEL_OFFSET, ay + py * LABEL_OFFSET)
