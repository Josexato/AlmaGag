"""BUGS-DRAW-009 — la leyenda entra entera y no pisa labels (PY-004).

El repro (c21): la leyenda «Enlaces:» montada sobre el label «Monitoreo»
y su último ítem fuera del viewBox. Cayó por la combinación de
BUGS-DRAW-008 (el viewBox ES el bbox — nada queda afuera) y
BUGS-LAYOUT-015 (sin iconos montados la lámina recupera su ancho real).
Este test congela ambas propiedades sobre el repro original.
"""

import xml.etree.ElementTree as ET

from AlmaGag.draw.primitives.viewbox import (BOTTOM_ANCHORED_CLASS,
                                             content_bbox, _text_corners)
from AlmaGag.generator import generate_diagram

SVG = 'http://www.w3.org/2000/svg'


def _render_c21(tmp_path):
    out = tmp_path / 'c21.svg'
    assert generate_diagram(
        'docs/diagrams/constructos/c21-theme-semantica-estilos.sdjf',
        output_file=str(out), layout_algorithm='select')
    return ET.parse(out).getroot()


def test_la_leyenda_entra_entera_al_viewbox(tmp_path):
    root = _render_c21(tmp_path)
    vx, vy, vw, vh = [float(n) for n in
                      root.get('viewBox').replace(',', ' ').split()]
    for g in root.iter(f'{{{SVG}}}g'):
        if BOTTOM_ANCHORED_CLASS not in (g.get('class') or '').split():
            continue
        # content_bbox YA aplica el transform del propio grupo
        bb = content_bbox(g)
        if not bb:
            continue
        x0, y0, x1, y1 = bb
        assert x0 >= vx - 0.5 and x1 <= vx + vw + 0.5, \
            f'leyenda cortada en x: ({x0:.0f}..{x1:.0f}) vs viewBox'
        assert y1 <= vy + vh + 0.5, 'leyenda cortada abajo'


def test_la_leyenda_no_pisa_labels_de_iconos(tmp_path):
    root = _render_c21(tmp_path)
    # bboxes de la leyenda (transformados) y de los <text> fuera de ella
    legend_boxes, label_boxes = [], []
    legend_groups = [g for g in root.iter(f'{{{SVG}}}g')
                     if BOTTOM_ANCHORED_CLASS in (g.get('class') or '').split()]
    legend_texts = {id(t) for g in legend_groups
                    for t in g.iter(f'{{{SVG}}}text')}
    for g in legend_groups:
        bb = content_bbox(g)          # ya incluye el transform del grupo
        if bb:
            legend_boxes.append(bb)
    for t in root.iter(f'{{{SVG}}}text'):
        if id(t) in legend_texts:
            continue
        pts = _text_corners(t)
        if pts:
            xs = [p[0] for p in pts]
            ys = [p[1] for p in pts]
            label_boxes.append((min(xs), min(ys), max(xs), max(ys)))
    for lx0, ly0, lx1, ly1 in legend_boxes:
        for tx0, ty0, tx1, ty1 in label_boxes:
            assert not (lx0 < tx1 and tx0 < lx1
                        and ly0 < ty1 and ty0 < ly1), \
                f'la leyenda ({lx0:.0f},{ly0:.0f})..({lx1:.0f},{ly1:.0f}) ' \
                f'pisa un label en ({tx0:.0f},{ty0:.0f})'
