"""§O51 — viewBox recortado al bbox del contenido + margen en la emisión.

El canvas se expandía pero nunca se contraía: diagramas chicos sobre canvas
declarado grande emitían láminas casi vacías. Verifica: recorte a bbox+40px,
área contenido/viewBox ≥ 0.60, regla sólo-contraer y reanclado de leyendas.
"""

import json
import tempfile
import xml.etree.ElementTree as ET

from AlmaGag.draw.primitives.viewbox import (
    CROP_MARGIN, content_bbox, crop_viewbox, parse_transform, _path_points)
from AlmaGag.generator import generate_diagram

SVG_NS = 'http://www.w3.org/2000/svg'


def _emit(data, tmp_path):
    src = tempfile.NamedTemporaryFile(suffix='.sdjf', delete=False, mode='w')
    json.dump(data, src)
    src.close()
    out = tmp_path / 'out.svg'
    assert generate_diagram(src.name, output_file=str(out), layout_algorithm='auto')
    return ET.fromstring(out.read_text(encoding='utf-8'))


def _viewbox(root):
    import re
    return [float(n) for n in re.findall(r'[-\d.]+', root.get('viewBox'))]


def test_transform_and_path_helpers():
    m = parse_transform('translate(10,20) scale(2)')
    a, b, c, d, e, f = m
    assert (a, d, e, f) == (2, 2, 10, 20)
    pts = _path_points('M 10 10 L 30 10 q 5 5 10 0 z')
    assert (10, 10) in pts and (30, 10) in pts
    assert (40, 10) in pts          # endpoint relativo de la q
    assert (35, 15) in pts          # control de la q (bbox conservador)


def test_crop_shrinks_sparse_canvas():
    src = (f'<svg xmlns="{SVG_NS}" width="1400" height="900" '
           'viewBox="0,0,1400,900">'
           '<rect x="100" y="80" width="600" height="400" fill="red"/></svg>')
    root = ET.fromstring(src)
    assert crop_viewbox(root)
    x0, y0, w, h = _viewbox(root)
    assert (x0, y0) == (100 - CROP_MARGIN, 80 - CROP_MARGIN)
    assert w == 600 + 2 * CROP_MARGIN and h == 400 + 2 * CROP_MARGIN
    assert root.get('width') == str(int(w))
    # área contenido / viewBox ≥ 0.60
    assert (600 * 400) / (w * h) >= 0.60


def test_crop_never_expands():
    """Contenido que ya llena (o desborda) el canvas: no se toca nada."""
    src = (f'<svg xmlns="{SVG_NS}" width="400" height="300" '
           'viewBox="0,0,400,300">'
           '<rect x="-20" y="0" width="500" height="320" fill="red"/></svg>')
    root = ET.fromstring(src)
    assert not crop_viewbox(root)
    assert root.get('viewBox') == '0,0,400,300'


def test_bbox_respects_transforms():
    src = (f'<svg xmlns="{SVG_NS}"><g transform="translate(100,50) scale(2)">'
           '<circle cx="10" cy="10" r="5"/></g></svg>')
    bbox = content_bbox(ET.fromstring(src))
    assert bbox == (110, 60, 130, 80)


def test_pipeline_sparse_diagram_gets_cropped(tmp_path):
    """Diagrama de 2 nodos sobre canvas declarado 1400×900: lámina al bbox."""
    data = {'canvas': {'width': 1400, 'height': 900},
            'elements': [{'id': 'a', 'type': 'server', 'label': 'A'},
                         {'id': 'b', 'type': 'server', 'label': 'B'}],
            'connections': [{'from': 'a', 'to': 'b'}]}
    root = _emit(data, tmp_path)
    x0, y0, w, h = _viewbox(root)
    assert w < 1400 or h < 900, 'el viewBox no se contrajo'
    bbox = content_bbox(root)
    # Nada dibujado queda fuera de la lámina.
    assert bbox[0] >= x0 and bbox[1] >= y0
    assert bbox[2] <= x0 + w and bbox[3] <= y0 + h


def test_fixture_ratio_over_060(tmp_path):
    """Criterio O51 sobre un diagrama real: área contenido/viewBox ≥ 0.60."""
    out = tmp_path / 'fixture.svg'
    assert generate_diagram('docs/diagrams/gags/03-conexiones.sdjf',
                            output_file=str(out), layout_algorithm='select')
    root = ET.fromstring(out.read_text(encoding='utf-8'))
    x0, y0, w, h = _viewbox(root)
    bbox = content_bbox(root)
    ratio = ((bbox[2] - bbox[0]) * (bbox[3] - bbox[1])) / (w * h)
    assert ratio >= 0.60, f'lámina vacía: ratio {ratio:.2f}'


def test_legend_reanchored_to_new_bottom(tmp_path):
    """La leyenda §N48 (anclada al canvas) baja/sube con el recorte."""
    types = ['data_link', 'control_link', 'dependency']
    els = [{'id': f'n{i}', 'type': 'server', 'label': f'N{i}'} for i in range(4)]
    conns = [{'from': f'n{i}', 'to': f'n{i+1}', 'semantic_type': t}
             for i, t in enumerate(types)]
    root = _emit({'canvas': {'width': 1600, 'height': 1200},
                  'elements': els, 'connections': conns}, tmp_path)
    x0, y0, w, h = _viewbox(root)
    legends = [g for g in root.iter(f'{{{SVG_NS}}}g')
               if 'ag-bottom-anchored' in (g.get('class') or '')]
    assert len(legends) == 1
    sub = content_bbox(legends[0])       # ya incluye el transform del grupo
    bottom = sub[3]
    assert y0 < bottom <= y0 + h, 'leyenda fuera de la lámina recortada'
    assert (y0 + h) - bottom < 60, 'leyenda no quedó pegada al borde inferior'


def test_arc_bbox_covers_the_bulge():
    """Los arcos A/a aportan su barrido real al bbox, no sólo el punto final.

    Semicírculo superior de radio 50 entre (0,0) y (100,0): la panza llega a
    y=-50; antes el bbox sólo veía los extremos (y=0).
    """
    pts = _path_points('M 0 0 A 50 50 0 0 1 100 0')
    ys = [p[1] for p in pts]
    xs = [p[0] for p in pts]
    assert min(ys) < -49.5                    # cúspide del semicírculo
    assert -0.5 < min(xs) and max(xs) < 100.5  # sin desborde lateral
    # variante relativa con sweep contrario: panza hacia abajo
    pts = _path_points('M 0 0 a 50 50 0 0 0 100 0')
    assert max(p[1] for p in pts) > 49.5


def test_arc_degenerate_radius_falls_to_endpoint():
    pts = _path_points('M 0 0 A 0 50 0 0 1 100 0')
    assert (100, 0) in pts
