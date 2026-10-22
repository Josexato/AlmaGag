"""BUGS-DRAW-008 — el viewBox ES el bbox de lo dibujado (§O51 sin clamp).

La regla original («sólo contraer, nunca expandir», clampeado al canvas
declarado) amputaba contenido real: labels laterales en x<0 («Revisar
solicitud» → «sar solicitud», c10) y zonas recolocadas más allá del
canvas. El costo de un sobrestimado de texto son decenas de px de aire;
el costo del clamp era contenido cortado. Hallazgo PY-003 de la fase 0
de almagag-jv, confirmado en PNG.
"""

import xml.etree.ElementTree as ET

from AlmaGag.draw.primitives.viewbox import content_bbox, crop_viewbox
from AlmaGag.generator import generate_diagram

SVG = 'http://www.w3.org/2000/svg'


def test_el_viewbox_cubre_todo_lo_dibujado(tmp_path):
    """c10 (vista columns): ningún bbox de contenido fuera del viewBox —
    los labels laterales en x negativo eran los amputados."""
    out = tmp_path / 'c10.svg'
    assert generate_diagram('docs/diagrams/constructos/c10-columns-decision.sdjf',
                            output_file=str(out), layout_algorithm='select')
    root = ET.parse(out).getroot()
    vx, vy, vw, vh = [float(n) for n in
                      root.get('viewBox').replace(',', ' ').split()]
    bbox = content_bbox(root)
    assert bbox is not None
    minx, miny, maxx, maxy = bbox
    assert minx >= vx - 0.5 and miny >= vy - 0.5, \
        f'contenido amputado arriba/izquierda: bbox {bbox} vs viewBox ' \
        f'({vx},{vy},{vw},{vh})'
    assert maxx <= vx + vw + 0.5 and maxy <= vy + vh + 0.5, \
        f'contenido amputado abajo/derecha: bbox {bbox} vs viewBox ' \
        f'({vx},{vy},{vw},{vh})'


def test_expande_cuando_el_contenido_desborda_el_canvas():
    """Unitario: un rect fuera del canvas declarado (y>alto) EXPANDE el
    viewBox en vez de clamped-cortarse."""
    root = ET.fromstring(
        f'<svg xmlns="{SVG}" width="200" height="100" '
        f'viewBox="0,0,200,100">'
        f'<rect x="10" y="10" width="50" height="40"/>'
        f'<rect x="-80" y="150" width="60" height="30"/>'
        f'</svg>')
    assert crop_viewbox(root, margin=10)
    vx, vy, vw, vh = [float(n) for n in
                      root.get('viewBox').replace(',', ' ').split()]
    assert vx <= -90 and vy + vh >= 190, \
        f'el viewBox ({vx},{vy},{vw},{vh}) no cubre el rect desbordado'


def test_sigue_contrayendo_las_laminas_vacias():
    """La razón de ser original de O51 no se pierde: contenido chico en
    canvas grande → lámina recortada."""
    root = ET.fromstring(
        f'<svg xmlns="{SVG}" width="1400" height="900" '
        f'viewBox="0,0,1400,900">'
        f'<rect x="100" y="100" width="80" height="50"/>'
        f'</svg>')
    assert crop_viewbox(root, margin=40)
    _, _, vw, vh = [float(n) for n in
                    root.get('viewBox').replace(',', ' ').split()]
    assert vw <= 160 + 1 and vh <= 130 + 1
