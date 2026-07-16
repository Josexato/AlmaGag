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
