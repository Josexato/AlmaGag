"""
Tests para el container 'contract band' (WISH-LAYOUT-005).
"""

import json
import tempfile
import os

from AlmaGag.layout import Layout
from AlmaGag.layout.auto.optimizer import AutoLayoutOptimizer
from AlmaGag.layout.container_calculator import is_band, band_label_margin


def _band_gag():
    return {
        'canvas': {'width': 900, 'height': 600},
        'elements': [
            {'id': 'entry', 'type': 'server', 'label': 'Entry', 'x': 400, 'y': 60},
            {'id': 'band', 'shape': 'band', 'type': 'building', 'label': 'Contract',
             'x': 120, 'y': 240, 'contains': ['a', 'mid', 'b']},
            {'id': 'a', 'type': 'server', 'label': 'A', 'x': 200, 'y': 260},
            {'id': 'mid', 'type': 'diamond', 'label': 'I', 'x': 420, 'y': 260},
            {'id': 'b', 'type': 'server', 'label': 'B', 'x': 640, 'y': 260},
        ],
        'connections': [
            {'from': 'entry', 'to': 'a', 'direction': 'forward'},
            {'from': 'a', 'to': 'mid', 'direction': 'forward'},
            {'from': 'b', 'to': 'mid', 'direction': 'forward'},
        ],
    }


def _optimize(data):
    layout = Layout(elements=data['elements'], connections=data['connections'],
                    canvas=data['canvas'])
    layout._diagram_name = 'test'
    return AutoLayoutOptimizer(verbose=False).optimize(layout, max_iterations=10)


def test_is_band_detection():
    assert is_band({'shape': 'band'})
    assert not is_band({'shape': 'box'})
    assert not is_band({})


def test_band_label_margin_scales_with_lines():
    one = band_label_margin({'label': 'Contract'})
    two = band_label_margin({'label': 'Contract\nLayer'})
    assert two > one


def test_band_children_in_single_row():
    """Los hijos de una band quedan en una sola fila (misma Y, X creciente)."""
    r = _optimize(_band_gag())
    ys = [r.elements_by_id[c]['y'] for c in ('a', 'mid', 'b')]
    xs = [r.elements_by_id[c]['x'] for c in ('a', 'mid', 'b')]
    # Misma fila
    assert max(ys) - min(ys) < 1.0
    # X estrictamente creciente
    assert xs[0] < xs[1] < xs[2]


def test_band_wraps_all_children():
    """El rect de la band cubre a todos sus hijos sin overflow horizontal."""
    r = _optimize(_band_gag())
    band = r.elements_by_id['band']
    left, right = band['x'], band['x'] + band['width']
    for c in ('a', 'mid', 'b'):
        e = r.elements_by_id[c]
        assert e['x'] >= left - 0.5
        assert e['x'] + 80 <= right + 0.5


def test_band_renders_rotated_label():
    """El SVG de una band contiene el título rotado -90."""
    data = _band_gag()
    tmp = tempfile.NamedTemporaryFile(suffix='.gag', delete=False, mode='w')
    json.dump(data, tmp)
    tmp.close()
    out = tmp.name.replace('.gag', '.svg')
    from AlmaGag.generator import generate_diagram
    generate_diagram(tmp.name, output_file=out)
    with open(out) as f:
        svg = f.read()
    os.unlink(tmp.name)
    os.unlink(out)
    assert 'rotate(-90' in svg
    assert 'Contract' in svg
