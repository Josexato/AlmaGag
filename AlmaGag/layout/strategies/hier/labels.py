"""
§F18 — Etiqueta al borde menos concurrido (WISH-LAF-002 Fase 3).

Por nodo cuenta los conectores que tocan cada borde (T/B/L/R) — incluidos
extremos de arcos — y elige el borde con menor conteo. Empate: abajo →
arriba → lado exterior (lejos del centro) → lado interior.

Setea `element['label_position']` como preferencia para el renderer.
"""

from AlmaGag.config import ICON_WIDTH, ICON_HEIGHT, TEXT_CHAR_WIDTH


# §J31/§J32 — etiqueta multilínea con ancho máximo.
LABEL_MAX_WIDTH = 180.0        # px — ancho máximo de una etiqueta (§J31)
LABEL_MAX_LINES = 3            # máximo 3 líneas; el resto se trunca con «…»


def wrap_label(text: str, max_width: float = LABEL_MAX_WIDTH) -> str:
    """§J31: parte `text` por palabras en ≤3 líneas que quepan en `max_width`
    (a ~TEXT_CHAR_WIDTH px por carácter). Si no cabe en 3 líneas, trunca la
    última con «…» (§J32). Devuelve el texto con '\\n' entre líneas (el renderer
    ya apila las líneas). Respeta saltos de línea explícitos preexistentes."""
    if not text:
        return text
    if '\n' in text:          # el autor ya definió las líneas → no tocar
        return text
    max_chars = max(6, int(max_width / TEXT_CHAR_WIDTH))
    if len(text) <= max_chars:
        return text
    words, lines, cur = text.split(), [], ''
    for w in words:
        cand = (cur + ' ' + w).strip()
        if len(cand) > max_chars and cur:
            lines.append(cur)
            cur = w
        else:
            cur = cand
    if cur:
        lines.append(cur)
    if len(lines) > LABEL_MAX_LINES:
        keep = lines[:LABEL_MAX_LINES]
        keep[-1] = keep[-1][:max_chars - 1].rstrip() + '…'   # §J32
        lines = keep
    return '\n'.join(lines)


def apply_label_wrapping(layout, max_width: float = LABEL_MAX_WIDTH):
    """Aplica §J31/§J32 a las etiquetas de todos los elementos. No depende de la
    posición (envolver un string no necesita coords): así funciona tanto en el
    flujo normal (llamado tras posicionar) como en áreas/carriles (antes)."""
    for e in layout.elements:
        if e.get('label'):
            e['label'] = wrap_label(e['label'], max_width)


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
