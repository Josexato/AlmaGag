"""§O54 — rótulo de zona `near` accesible y medido.

- Color #6b6558 (5.1:1, AA) en vez de #8a8577 (3.7:1).
- Banda superior de 18px RESERVADA dentro de la caja: los miembros no la
  pisan por construcción; el rótulo va anclado al borde de SU caja.
- El rótulo entra al contador labels (CollisionDetector → label_overlap).
"""

import xml.etree.ElementTree as ET

from AlmaGag.generator import generate_diagram
from AlmaGag.layout import Layout
from AlmaGag.layout.collision import CollisionDetector
from AlmaGag.layout.considerations import (
    ZONE_BOX_PAD, ZONE_LABEL_BAND, near_zone_boxes)
from AlmaGag.layout.geometry import GeometryCalculator
from AlmaGag.layout.metrics import quality_counters
from AlmaGag.validation.visual_quality import contrast_vs_white

FIXTURE = 'docs/diagrams/gags/red-minera-antes.gag'


def _zone_elements(label='Zona crítica'):
    els = [
        {'id': 'a', 'x': 100, 'y': 100, 'width': 80, 'height': 50,
         '_near_zone': 0, '_near_zone_label': label},
        {'id': 'b', 'x': 220, 'y': 100, 'width': 80, 'height': 50,
         '_near_zone': 0},
    ]
    return els


def test_zone_label_color_is_aa():
    """5.1:1 sobre fondo claro (AA exige 4.5 para 11px)."""
    assert contrast_vs_white('#6b6558') >= 4.5
    assert contrast_vs_white('#8a8577') < 4.5      # el color viejo NO cumplía


def test_rendered_zone_label_uses_aa_color(tmp_path):
    out = tmp_path / 'rm.svg'
    assert generate_diagram(FIXTURE, output_file=str(out),
                            layout_algorithm='select')
    svg = out.read_text(encoding='utf-8')
    assert '#6b6558' in svg
    assert '#8a8577' not in svg


def test_label_band_reserved():
    """Con rótulo, la caja crece 18px hacia arriba: banda sólo del rótulo."""
    with_label = near_zone_boxes(_zone_elements())
    without = near_zone_boxes(_zone_elements(label=None))
    assert len(with_label) == len(without) == 1
    y1_l, y1_s = with_label[0]['bbox'][1], without[0]['bbox'][1]
    assert y1_s - y1_l == ZONE_LABEL_BAND
    # miembros a ≥ banda + pad del borde superior; rótulo dentro de la banda
    lb = with_label[0]['label_bbox']
    assert lb[3] <= y1_l + ZONE_LABEL_BAND
    assert 100 - (y1_l + ZONE_LABEL_BAND) >= ZONE_BOX_PAD - 1e-9


def test_zone_label_anchored_to_its_box(tmp_path):
    """El <text> del rótulo queda en el borde superior-izquierdo de su rect."""
    out = tmp_path / 'rm.svg'
    assert generate_diagram(FIXTURE, output_file=str(out),
                            layout_algorithm='select')
    root = ET.fromstring(out.read_text(encoding='utf-8'))
    ns = '{http://www.w3.org/2000/svg}'
    labels = [t for t in root.iter(f'{ns}text')
              if t.get('fill') == '#6b6558' and t.get('class') != 'ag-text-halo']
    boxes = [r for r in root.iter(f'{ns}rect')
             if r.get('stroke-dasharray') == '4,4' and r.get('rx')]
    assert labels and boxes
    for t in labels:
        tx, ty = float(t.get('x')), float(t.get('y'))
        assert any(abs(tx - (float(r.get('x')) + 10)) < 1e-6 and
                   0 < ty - float(r.get('y')) <= ZONE_LABEL_BAND
                   for r in boxes), 'rótulo sin caja propia en el borde'


def test_zone_label_enters_label_counter():
    """Una línea ajena que cruza el rótulo cuenta en label_overlap (§H6)."""
    els = _zone_elements() + [
        {'id': 'p', 'x': 0, 'y': 40, 'width': 20, 'height': 20},
        {'id': 'q', 'x': 400, 'y': 40, 'width': 20, 'height': 20},
    ]
    # p→q pasa por y=90+10: los bordes superiores… mejor: forzar computed_path
    # que atraviese el label_bbox del rótulo (y≈70-84 tras la banda).
    zone = near_zone_boxes(els)[0]
    lx1, ly1, lx2, ly2 = zone['label_bbox']
    ymid = (ly1 + ly2) / 2
    conn = {'from': 'p', 'to': 'q',
            'computed_path': {'type': 'polyline',
                              'points': [(10, ymid), (410, ymid)]}}
    layout = Layout(elements=els, connections=[conn],
                    canvas={'width': 500, 'height': 300})
    det = CollisionDetector(GeometryCalculator())
    _, pairs = det.detect_all_collisions(layout)
    assert any(a == 'zone:0' and 'label' in kind for (a, b, kind) in pairs)
    layout._collision_pairs = pairs
    assert quality_counters(layout)['label_overlap'] >= 1
