"""BUGS-VAL-003 — el validador ve iconos dibujados sólo con <path>."""

import xml.etree.ElementTree as ET

from AlmaGag.validation.visual_quality import (
    SVG_NS, _collect_icon_bboxes, _group_transform_bbox)


def test_firewall_detected_in_standalone_svg():
    """El fixture 01 tiene un firewall (100% <path>, id en el envoltorio):
    debe aparecer en los bboxes con su posición y escala reales."""
    root = ET.parse('docs/diagrams/svgs/01-iconos-registrados.svg').getroot()
    bboxes = _collect_icon_bboxes(root)
    fw = [b for b in bboxes if abs(b[0] - 500) < 5 and abs(b[1] - 100) < 5]
    assert fw, 'firewall1 no detectado (falso positivo R3 regresó)'


def test_nonuniform_scale_bbox():
    """BUGS-VAL-006: el scale NORMALIZA el viewBox intrínseco a la ranura
    80×50 — el bbox se acota a la ranura (sx>1 no la infla); sy<1 sí
    reduce (icono más chico que la ranura)."""
    g = ET.fromstring(
        f'<g xmlns="{SVG_NS}" transform="translate(10,20) scale(2,0.5)"/>')
    assert _group_transform_bbox(g) == (10.0, 20.0, 10.0 + 80, 20.0 + 50 * 0.5)
