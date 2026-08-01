"""
Métricas de calidad de layout, agnósticas del motor (WISH-ARCH-002, rescate ③).

`count_crossings` viene del `abstract_placer` de LAF (motor histórico): cuenta los
cruces reales entre conexiones con un test de orientación O(n²). Es una métrica
barata y objetiva de calidad — cuántas aristas se cruzan — que ni AUTO ni hier
tenían. Acá se generaliza para operar sobre cualquier `Layout` ya posicionado
(usa los centros de los iconos), así sirve como:

- criterio de calidad visible en Epifanía (se ve el número bajar por fase),
- métrica de regresión en tests.

Mejora sobre la versión de LAF: dos conexiones que comparten un extremo (p.ej.
el abanico de salidas de un hub) se tocan en el nodo, NO es un cruce; acá se
excluyen esos pares para que la métrica cuente sólo cruces genuinos.
"""

from typing import Dict, List, Tuple

from AlmaGag.config import ICON_WIDTH, ICON_HEIGHT

Point = Tuple[float, float]


def _icon_centers(layout) -> Dict[str, Point]:
    """Centro (x, y) de cada elemento posicionado del layout."""
    centers = {}
    for e in layout.elements:
        if 'x' in e and 'y' in e:
            w = e.get('width', ICON_WIDTH)
            h = e.get('height', ICON_HEIGHT)
            centers[e['id']] = (e['x'] + w / 2.0, e['y'] + h / 2.0)
    return centers


def _orientation(p: Point, q: Point, r: Point) -> int:
    """Orientación del triplete: 0 colineal, 1 horario, 2 antihorario."""
    val = (q[1] - p[1]) * (r[0] - q[0]) - (q[0] - p[0]) * (r[1] - q[1])
    if abs(val) < 1e-9:
        return 0
    return 1 if val > 0 else 2


def _on_segment(p: Point, q: Point, r: Point) -> bool:
    """True si q cae dentro del bbox del segmento pr (asumiendo colinealidad)."""
    return (min(p[0], r[0]) <= q[0] <= max(p[0], r[0]) and
            min(p[1], r[1]) <= q[1] <= max(p[1], r[1]))


def segments_intersect(p1: Point, p2: Point, p3: Point, p4: Point) -> bool:
    """True si el segmento p1p2 cruza el segmento p3p4 (test de orientación)."""
    o1 = _orientation(p1, p2, p3)
    o2 = _orientation(p1, p2, p4)
    o3 = _orientation(p3, p4, p1)
    o4 = _orientation(p3, p4, p2)

    if o1 != o2 and o3 != o4:
        return True
    if o1 == 0 and _on_segment(p1, p3, p2):
        return True
    if o2 == 0 and _on_segment(p1, p4, p2):
        return True
    if o3 == 0 and _on_segment(p3, p1, p4):
        return True
    if o4 == 0 and _on_segment(p3, p2, p4):
        return True
    return False


def count_crossings(layout) -> int:
    """Cuenta cruces entre conexiones del layout (segmentos centro-a-centro).

    O(n²) sobre las conexiones. Usa los centros de los iconos ya posicionados;
    ignora conexiones sin ambos extremos posicionados, self-loops, y pares de
    conexiones que comparten un nodo (se tocan en el nodo, no cruzan).
    """
    centers = _icon_centers(layout)

    edges: List[Tuple[str, str]] = []
    for c in layout.connections:
        a, b = c.get('from'), c.get('to')
        if a in centers and b in centers and a != b:
            edges.append((a, b))

    crossings = 0
    n = len(edges)
    for i in range(n):
        a1, a2 = edges[i]
        p1, p2 = centers[a1], centers[a2]
        for j in range(i + 1, n):
            b1, b2 = edges[j]
            # Comparten un extremo → concurren en el nodo, no es un cruce.
            if a1 == b1 or a1 == b2 or a2 == b1 or a2 == b2:
                continue
            if segments_intersect(p1, p2, centers[b1], centers[b2]):
                crossings += 1
    return crossings


def _elem_bboxes(layout):
    """(icon_bboxes, container_bboxes) por id, usando tamaño real o por defecto."""
    icons, containers = {}, {}
    for e in layout.elements:
        if 'x' not in e or 'y' not in e:
            continue
        w = e.get('width', ICON_WIDTH)
        h = e.get('height', ICON_HEIGHT)
        bbox = (e['x'], e['y'], e['x'] + w, e['y'] + h)
        (containers if 'contains' in e else icons)[e['id']] = bbox
    return icons, containers


def _seg_hits_rect(ax, ay, bx, by, r, inset=3.0):
    x1, y1, x2, y2 = r[0] + inset, r[1] + inset, r[2] - inset, r[3] - inset
    if abs(ax - bx) < 0.1:
        return x1 < ax < x2 and min(ay, by) < y2 and max(ay, by) > y1
    if abs(ay - by) < 0.1:
        return y1 < ay < y2 and min(ax, bx) < x2 and max(ax, bx) > x1
    for t in (0.2, 0.4, 0.6, 0.8):
        px, py = ax + (bx - ax) * t, ay + (by - ay) * t
        if x1 < px < x2 and y1 < py < y2:
            return True
    return False


def _conn_segments(conn, centers):
    cp = conn.get('computed_path')
    if isinstance(cp, dict) and cp.get('points') and len(cp['points']) >= 2:
        pts = [((p[0], p[1]) if not hasattr(p, 'x') else (p.x, p.y)) for p in cp['points']]
        return [(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1]) for i in range(len(pts) - 1)]
    a, b = conn.get('from'), conn.get('to')
    if a in centers and b in centers:
        return [(centers[a][0], centers[a][1], centers[b][0], centers[b][1])]
    return []


def count_edge_node_overlaps(layout) -> int:
    """§H6: nº de conexiones cuyo trazado (computed_path si existe) cruza el
    interior de un ICONO o CONTENEDOR ajeno (que no es su origen/destino ni el
    contenedor padre de éstos). Mide 'arista sobre nodo', distinto de cruces
    arista×arista."""
    centers = _icon_centers(layout)
    icons, containers = _elem_bboxes(layout)
    parent = {}
    for c in layout.elements:
        if 'contains' in c:
            for ch in c['contains']:
                parent[ch['id'] if isinstance(ch, dict) else ch] = c['id']
    count = 0
    for conn in layout.connections:
        f, t = conn.get('from'), conn.get('to')
        related = {f, t, parent.get(f), parent.get(t)}
        segs = _conn_segments(conn, centers)
        hit = False
        for eid, r in list(icons.items()) + list(containers.items()):
            if eid in related:
                continue
            if any(_seg_hits_rect(ax, ay, bx, by, r) for (ax, ay, bx, by) in segs):
                hit = True
                break
        if hit:
            count += 1
    return count


def quality_counters(layout) -> Dict[str, int]:
    """§H6: tres contadores separados de calidad, para que log, epifanía y audit
    reporten lo MISMO sin agregar todo en un ambiguo 'colisiones':

    - edge_x_edge:  cruces arista×arista (count_crossings)
    - edge_x_node:  aristas sobre icono/contenedor ajeno (count_edge_node_overlaps)
    - label_overlap: solapes que involucran etiquetas (del CollisionDetector)
    """
    exe = count_crossings(layout)
    exn = count_edge_node_overlaps(layout)
    label_overlap = 0
    pairs = getattr(layout, '_collision_pairs', None)
    if pairs:
        label_overlap = sum(1 for p in pairs if 'label' in p[2])
    return {
        'edge_x_edge': exe,
        'edge_x_node': exn,
        'label_overlap': label_overlap,
    }


# §O52 — umbrales de la guarda de emisión: por debajo de esta tinta la lámina
# es mayormente aire; fuera de este rango de aspecto es una cinta/columna.
INK_WARN_PCT = 4.0
ASPECT_RANGE = (0.4, 3.0)


def emission_metrics(layout) -> Dict[str, float]:
    """§O52: densidad de tinta y aspecto estimados de la lámina emitida.

    - tinta: Σ áreas de iconos/contenedores + etiquetas estimadas, sobre el
      área de la lámina. La lámina se estima como bbox del contenido + 2×40px
      de margen acotada al canvas — espejo del recorte §O51, así el número
      refleja lo que realmente se emite.
    - aspecto: ancho/alto de esa lámina.
    """
    boxes = []
    for e in layout.elements:
        if 'x' not in e or 'y' not in e:
            continue
        w = e.get('width', ICON_WIDTH)
        h = e.get('height', ICON_HEIGHT)
        boxes.append((e['x'], e['y'], w, h))
        label = e.get('label')
        if label:
            lines = str(label).split('\n')
            lw = max(len(ln) for ln in lines) * 7.0
            lh = len(lines) * 16.0
            boxes.append((e['x'] + w / 2.0 - lw / 2.0, e['y'] + h, lw, lh))
    if not boxes:
        return {'ink_pct': 0.0, 'aspect': 1.0}
    minx = min(b[0] for b in boxes)
    miny = min(b[1] for b in boxes)
    maxx = max(b[0] + b[2] for b in boxes)
    maxy = max(b[1] + b[3] for b in boxes)
    canvas = getattr(layout, 'canvas', None) or {}
    cw = canvas.get('width') or (maxx - minx)
    ch = canvas.get('height') or (maxy - miny)
    sheet_w = max(1.0, min(cw, (maxx - minx) + 80.0))
    sheet_h = max(1.0, min(ch, (maxy - miny) + 80.0))
    ink = sum(b[2] * b[3] for b in boxes)
    return {
        'ink_pct': 100.0 * ink / (sheet_w * sheet_h),
        'aspect': sheet_w / sheet_h,
    }
