"""§N48 — leyenda de tipos de conexión al pie cuando hay ≥3 semantic_type."""
import json
import tempfile
import os

from AlmaGag.generator import generate_diagram


def _render(data):
    src = tempfile.NamedTemporaryFile(suffix='.sdjf', delete=False, mode='w')
    json.dump(data, src)
    src.close()
    out = src.name.replace('.sdjf', '.svg')
    assert generate_diagram(src.name, output_file=out, layout_algorithm='auto')
    svg = open(out).read()
    os.unlink(src.name)
    os.unlink(out)
    return svg


def _net(n_types):
    types = ['data_flow', 'control_flow', 'dependency', 'event'][:n_types]
    els = [{'id': f'n{i}', 'type': 'server', 'label': f'N{i}'} for i in range(n_types + 1)]
    conns = [{'from': f'n{i}', 'to': f'n{i+1}', 'semantic_type': t}
             for i, t in enumerate(types)]
    return {'elements': els, 'connections': conns}


def test_legend_with_three_types():
    svg = _render(_net(3))
    assert 'Enlaces:' in svg
    assert '>datos<' in svg and '>control<' in svg and '>dependencia<' in svg


def test_legend_swatches_have_real_geometry():
    """Los swatches son líneas visibles, no puntos en el origen (bug svgwrite:
    Line sobrescribe x1..y2 extra con start/end por defecto)."""
    import xml.etree.ElementTree as ET
    root = ET.fromstring(_render(_net(3)))
    swatches = [ln for ln in root.iter('{http://www.w3.org/2000/svg}line')
                if ln.get('stroke-width') == '2.5']
    assert len(swatches) == 3
    for ln in swatches:
        assert float(ln.get('x2')) - float(ln.get('x1')) == 26
        assert float(ln.get('y1')) > 0


def test_no_legend_with_two_types():
    svg = _render(_net(2))
    assert 'Enlaces:' not in svg
