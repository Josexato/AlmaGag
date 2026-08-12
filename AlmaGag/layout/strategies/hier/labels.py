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
CASCADE = 14.0         # WISH-DRAW-007 (X93): paso vertical de la cascada
CASCADE_TRIES = (0, -1, 1, -2, 2, -3, 3,
                 -4, 4, -5, 5, -6, 6)      # base, un lado, el otro, ...


def _intersects(a, b) -> bool:
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def _title_boxes(elements):
    """Bboxes de los títulos ESTRUCTURALES (etiqueta centrada bajo el icono
    — la geometría que dibujan draw_area_node_labels y el default bottom).
    Son los obstáculos que el ancla §G23 no debe pisar (X93)."""
    boxes = []
    for e in elements:
        lbl = e.get('label')
        if not lbl or 'x' not in e or 'y' not in e:
            continue
        lines = lbl.split('\n')
        cx = e['x'] + ICON_WIDTH / 2
        top = e['y'] + ICON_HEIGHT + 14
        w = max(len(ln) for ln in lines) * TEXT_CHAR_WIDTH
        boxes.append((cx - w / 2, top - 14,
                      cx + w / 2, top + (len(lines) - 1) * 16 + 5))
    return boxes


def assign_connection_label_anchors(layout):
    """§G23: fija `connection['_label_anchor']` (x,y) a ~14px del puerto de
    SALIDA, sobre el primer segmento del path, desplazado perpendicular para no
    quedar encima de la línea. Así el rótulo (sí/no/repetir) queda pegado a la
    decisión que lo origina, no en el punto medio de un path largo.

    WISH-DRAW-007 (X93): el ancla ya no pisa en silencio — si su bbox cae
    sobre un título estructural o sobre el ancla de OTRA arista del mismo
    corredor, se apila en CASCADA vertical de a CASCADE px (arriba primero,
    después abajo) hasta el primer lugar limpio; si ninguno lo está, gana el
    menos pisado. Los 28 pares título↔label del tabernero nacían aquí."""
    obstacles = _title_boxes(layout.elements)
    # los ICONOS también son obstáculo (icon_vs_conn_label es la violación
    # más fea — WISH-LAYOUT-010)
    obstacles += [(e['x'], e['y'], e['x'] + ICON_WIDTH, e['y'] + ICON_HEIGHT)
                  for e in layout.elements
                  if 'x' in e and 'y' in e and 'contains' not in e]
    placed = []
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
        bx, by = ax + px * LABEL_OFFSET, ay + py * LABEL_OFFSET
        # cascada X93 en DOS dimensiones: perpendicular del primer segmento
        # (corredor horizontal → apila vertical; vertical → esquiva
        # horizontal) y, si no alcanza, DESLIZARSE a lo largo del segmento
        # (WISH-LAYOUT-022: un título ancho bloquea ±84px perpendiculares,
        # pero el paso label-aware deja aire más adelante sobre la línea).
        # Primer candidato limpio o el menos pisado; k=0 primero conserva
        # el comportamiento previo.
        w = len(c['label']) * 7
        max_along = max(0.0, seg - d - 6.0)
        best = None
        for k in range(0, 4):
            if k * CASCADE > max_along:
                break
            kx, ky = bx + ux * k * CASCADE, by + uy * k * CASCADE
            for j in CASCADE_TRIES:
                cx = kx + px * j * CASCADE
                cy = ky + py * j * CASCADE
                bb = (cx - w / 2, cy - 12, cx + w / 2, cy + 4)
                hits = sum(1 for ob in obstacles if _intersects(bb, ob)) \
                    + sum(1 for ob in placed if _intersects(bb, ob))
                if best is None or hits < best[0]:
                    best = (hits, (cx, cy), bb)
                if hits == 0:
                    break
            if best[0] == 0:
                break
        _, anchor, bb = best
        c['_label_anchor'] = anchor
        placed.append(bb)
