"""BUGS-LOG-003 — los arcos se miden por su CURVA, no por su cuerda.

`_conn_segments` devolvía el segmento recto entre extremos para los
bezier (los control_points se ignoraban): arista×nodo y cruces
evaluaban una línea que no existe en la lámina. Doctrina VAL-008 (lo
dibujado es lo medido): la curva se poligonaliza con sus control_points
y se mide ESA polilínea. Dos clases congeladas: el falso positivo (la
cuerda toca un icono que la comba rodea — E17 en acción, el caso
14-stresstest del reporte) y el falso negativo (la comba entra a un
icono que la cuerda esquiva).
"""

from AlmaGag.config import ICON_WIDTH, ICON_HEIGHT
from AlmaGag.layout.layout import Layout
from AlmaGag.layout.metrics import count_edge_node_overlaps, _conn_segments


def _mk(bulge_y):
    """a → b en la misma fila con el icono j EN MEDIO; el bezier comba
    hacia bulge_y (los control_points a 1/3 y 2/3, como arcs.py)."""
    els = [
        {'id': 'a', 'type': 'server', 'label': 'A', 'x': 0.0, 'y': 200.0},
        {'id': 'j', 'type': 'server', 'label': 'J', 'x': 200.0, 'y': 200.0},
        {'id': 'b', 'type': 'server', 'label': 'B', 'x': 400.0, 'y': 200.0},
    ]
    p0 = (ICON_WIDTH, 200.0 + ICON_HEIGHT / 2)
    p1 = (400.0, 200.0 + ICON_HEIGHT / 2)
    c1 = (p0[0] + (p1[0] - p0[0]) / 3, bulge_y)
    c2 = (p0[0] + 2 * (p1[0] - p0[0]) / 3, bulge_y)
    conn = {'from': 'a', 'to': 'b',
            'computed_path': {'type': 'bezier', 'points': [p0, p1],
                              'control_points': [c1, c2]}}
    return Layout(elements=els, connections=[conn],
                  canvas={'width': 600, 'height': 500})


def test_arc_that_rounds_the_icon_is_clean():
    """La comba rodea a `j` por arriba (E17): la CUERDA lo atraviesa,
    la curva no — arista×nodo debe ser 0 (el falso positivo del ticket)."""
    L = _mk(bulge_y=40.0)                 # comba 190px arriba de la fila
    assert count_edge_node_overlaps(L) == 0


def test_arc_that_dips_into_the_icon_is_counted():
    """La comba plana (control points A LA ALTURA de la fila) mantiene la
    curva dentro de la franja del icono: la travesía REAL se cuenta."""
    L = _mk(bulge_y=200.0 + ICON_HEIGHT / 2)   # curva ≈ recta por la fila
    assert count_edge_node_overlaps(L) == 1


def test_bezier_segments_follow_the_curve():
    """_conn_segments poligonaliza el bezier: varios tramos, y el punto
    medio de la polilínea está a la altura de la comba, no de la cuerda."""
    L = _mk(bulge_y=40.0)
    segs = _conn_segments(L.connections[0], {})
    assert len(segs) >= 4, 'el bezier sigue midiéndose como cuerda'
    mid_y = min(min(s[1], s[3]) for s in segs)
    assert mid_y < 120.0, f'la polilínea no sube con la comba: {mid_y}'
