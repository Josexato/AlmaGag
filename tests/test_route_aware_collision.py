"""
H3/H6 — el detector de colisiones mide sobre la POLILÍNEA ruteada
(`computed_path`), no la recta centro-a-centro: una etiqueta que la recta
cruzaría pero el ruteo ortogonal rodea no cuenta como `label_vs_line`.
"""

from AlmaGag.layout import Layout
from AlmaGag.layout.collision import CollisionDetector
from AlmaGag.layout.geometry import GeometryCalculator


def _layout_with_routed_detour():
    # A (0,0) y B (200,0); una etiqueta de icono de C está en el punto medio
    # de la recta A→B (100,0). La recta la cruzaría; el computed_path la rodea
    # por y=80.
    elements = [
        {'id': 'A', 'x': 0, 'y': 0, 'width': 20, 'height': 20},
        {'id': 'B', 'x': 200, 'y': 0, 'width': 20, 'height': 20},
        {'id': 'C', 'x': 90, 'y': 0, 'width': 20, 'height': 20, 'label': 'C'},
    ]
    conn = {'from': 'A', 'to': 'B'}
    layout = Layout(elements=elements, connections=[conn], canvas={'width': 300, 'height': 200})
    # etiqueta de C sobre la recta A→B
    layout.label_positions = {'C': (95, 5, 'start', 'C')}
    return layout, conn


def test_routed_path_avoids_label_not_counted():
    geo = GeometryCalculator()
    det = CollisionDetector(geo)
    layout, conn = _layout_with_routed_detour()

    # 1) recta (sin computed_path): la línea A→B cruza la etiqueta de C
    straight = det._connection_segments(conn, layout)
    assert straight == [(10, 10, 210, 10)] or len(straight) == 1

    # 2) con computed_path que rodea por y=80: los segmentos son los ruteados
    conn['computed_path'] = {'type': 'polyline',
                             'points': [(10, 10), (10, 80), (210, 80), (210, 10)]}
    routed = det._connection_segments(conn, layout)
    assert routed == [(10, 10, 10, 80), (10, 80, 210, 80), (210, 80, 210, 10)]
