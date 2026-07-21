"""
Tests para el sesgo de label hacia afuera del container (WISH-LAYOUT-006).

El sesgo es un REORDENAMIENTO del fallback: cuando la posición preferida
('bottom') colisiona, el hijo del extremo de una fila prueba PRIMERO su lado
hacia afuera (izq → 'left', der → 'right') antes que el resto. No fuerza la
preferida, así que no degrada los casos donde 'bottom' ya funciona.
"""

from AlmaGag.layout import Layout
from AlmaGag.layout.strategies.auto.optimizer import AutoLayoutOptimizer


def _layout_with_band():
    elements = [
        {'id': 'band', 'shape': 'band', 'type': 'building', 'label': 'B',
         'x': 100, 'y': 150, 'width': 460, 'height': 90,
         'contains': ['l', 'm', 'r'], '_is_container_calculated': True},
        {'id': 'l', 'type': 'server', 'label': 'Left', 'x': 250, 'y': 170},
        {'id': 'm', 'type': 'server', 'label': 'Mid', 'x': 360, 'y': 170},
        {'id': 'r', 'type': 'server', 'label': 'Right', 'x': 470, 'y': 170},
    ]
    layout = Layout(elements=elements, connections=[],
                    canvas={'width': 900, 'height': 400})
    return layout


def test_outward_preference_leftmost_and_rightmost():
    opt = AutoLayoutOptimizer(verbose=False)
    lay = _layout_with_band()
    band = lay.elements_by_id['band']
    assert opt._outward_label_preference(lay, lay.elements_by_id['l'], band) == 'left'
    assert opt._outward_label_preference(lay, lay.elements_by_id['r'], band) == 'right'


def test_outward_preference_middle_is_none():
    opt = AutoLayoutOptimizer(verbose=False)
    lay = _layout_with_band()
    band = lay.elements_by_id['band']
    assert opt._outward_label_preference(lay, lay.elements_by_id['m'], band) is None


def test_outward_preference_skips_multirow():
    """En containers multi-fila (grid) no se sesga (evita poner label sobre
    vecinos de otra fila)."""
    elements = [
        {'id': 'box', 'type': 'building', 'label': 'Grid',
         'x': 100, 'y': 100, 'width': 300, 'height': 300,
         'contains': ['a', 'b', 'c', 'd'], '_is_container_calculated': True},
        {'id': 'a', 'type': 'server', 'label': 'A', 'x': 150, 'y': 150},
        {'id': 'b', 'type': 'server', 'label': 'B', 'x': 280, 'y': 150},
        {'id': 'c', 'type': 'server', 'label': 'C', 'x': 150, 'y': 300},  # otra fila
        {'id': 'd', 'type': 'server', 'label': 'D', 'x': 280, 'y': 300},
    ]
    lay = Layout(elements=elements, connections=[], canvas={'width': 600, 'height': 600})
    opt = AutoLayoutOptimizer(verbose=False)
    box = lay.elements_by_id['box']
    # 'a' es extremo izquierdo de su fila, pero el container es multi-fila →
    # no se sesga.
    assert opt._outward_label_preference(lay, lay.elements_by_id['a'], box) is None


def test_outward_preference_none_without_container():
    opt = AutoLayoutOptimizer(verbose=False)
    lay = _layout_with_band()
    assert opt._outward_label_preference(lay, lay.elements_by_id['l'], None) is None


def test_band_label_inside_has_no_top_header():
    """En una band, _label_inside_container NO reserva franja superior
    (el título va lateral), así que un label en la parte alta es válido."""
    opt = AutoLayoutOptimizer(verbose=False)
    band = {'id': 'band', 'shape': 'band', 'x': 100, 'y': 150,
            'width': 400, 'height': 90}
    # label pegado al top del band (y=152..170) — válido en band, inválido en
    # un container normal (header_h=40).
    top_label_bbox = (120, 152, 180, 170)
    assert opt._label_inside_container(top_label_bbox, band) is True
    normal = dict(band); normal.pop('shape')
    assert opt._label_inside_container(top_label_bbox, normal) is False
