"""
Tests para el validador de calidad visual (3 reglas del usuario).
"""

import os
import tempfile
from AlmaGag.validation import validate_svg, validate_gag, QualityReport


SAMPLE_SVG = '''<?xml version="1.0"?>
<svg xmlns="http://www.w3.org/2000/svg" width="500" height="400">
  <rect x="100" y="100" width="80" height="50" fill="url(#gradient-a)"/>
  <rect x="300" y="100" width="80" height="50" fill="url(#gradient-b)"/>
  <text x="140" y="170" text-anchor="middle" font-size="14">Label A</text>
  <text x="340" y="170" text-anchor="middle" font-size="14">Label B</text>
  <line x1="180" y1="125" x2="300" y2="125" stroke="black" marker-end="url(#arrow)"/>
</svg>'''


SAMPLE_BAD = '''<?xml version="1.0"?>
<svg xmlns="http://www.w3.org/2000/svg" width="500" height="400">
  <rect x="100" y="100" width="80" height="50" fill="url(#gradient-a)"/>
  <rect x="300" y="100" width="80" height="50" fill="url(#gradient-b)"/>
  <!-- R1: label encima de icono -->
  <text x="140" y="130" text-anchor="middle" font-size="14">Over Icon</text>
  <!-- R2: dos labels solapados -->
  <text x="340" y="170" text-anchor="middle" font-size="14">Label B</text>
  <text x="345" y="172" text-anchor="middle" font-size="14">Label C</text>
  <!-- R3: línea sin endpoint cercano a icono -->
  <line x1="50" y1="50" x2="50" y2="350" stroke="black" marker-end="url(#a)"/>
</svg>'''


def _write_tmp(content):
    f = tempfile.NamedTemporaryFile(suffix='.svg', delete=False, mode='w')
    f.write(content)
    f.close()
    return f.name


def test_validate_clean_svg():
    path = _write_tmp(SAMPLE_SVG)
    r = validate_svg(path)
    os.unlink(path)
    assert r.passed
    assert r.n_icons == 2
    assert r.n_labels == 2
    assert r.n_connections == 1


def test_validate_detects_label_over_icon():
    path = _write_tmp(SAMPLE_BAD)
    r = validate_svg(path)
    os.unlink(path)
    r1 = r.by_rule('R1_label_over_icon')
    assert len(r1) >= 1
    assert 'Over Icon' in r1[0].extra['text']


def test_validate_detects_label_overlap():
    path = _write_tmp(SAMPLE_BAD)
    r = validate_svg(path)
    os.unlink(path)
    r2 = r.by_rule('R2_labels_overlap')
    assert len(r2) >= 1


def test_validate_detects_dangling_connection():
    path = _write_tmp(SAMPLE_BAD)
    r = validate_svg(path)
    os.unlink(path)
    r3 = r.by_rule('R3_dangling_connection')
    # La línea de (50,50) a (50,350) no toca ningún icono
    assert len(r3) >= 1


def test_validate_with_explicit_icon_bboxes():
    """Cuando se pasan icon_bboxes explícitos, el validador los usa."""
    path = _write_tmp(SAMPLE_SVG)
    custom_bboxes = [(0, 0, 1000, 1000)]  # un solo icono enorme que cubre todo
    r = validate_svg(path, icon_bboxes=custom_bboxes)
    os.unlink(path)
    # Todos los labels ahora caerán "dentro" del icono enorme → R1 violations
    assert len(r.by_rule('R1_label_over_icon')) >= 2


def test_validate_gag_uses_real_positions():
    """validate_gag debe usar las posiciones reales del optimizer
    (incluso con iconos custom)."""
    import json
    gag_data = {
        'canvas': {'width': 600, 'height': 300},
        'elements': [
            {'id': 'a', 'type': 'server', 'label': 'A', 'x': 100, 'y': 100},
            {'id': 'b', 'type': 'server', 'label': 'B', 'x': 300, 'y': 100},
        ],
        'connections': [{'from': 'a', 'to': 'b'}],
    }
    tmp = tempfile.NamedTemporaryFile(suffix='.gag', delete=False, mode='w')
    json.dump(gag_data, tmp)
    tmp.close()
    r = validate_gag(tmp.name)
    os.unlink(tmp.name)
    # El validador debe haber visto 2 iconos
    assert r.n_icons == 2


# ============================================================================
# BUGS-VAL-001: detección de iconos custom (transform + polygon)
# ============================================================================

CUSTOM_ICON_SVG = '''<?xml version="1.0"?>
<svg xmlns="http://www.w3.org/2000/svg" width="600" height="300">
  <!-- icono custom por transform (factory/gear/embedded) -->
  <g id="gen" transform="translate(100,100) scale(1.0)">
    <rect x="8" y="22" width="64" height="22" fill="currentColor"/>
  </g>
  <!-- icono custom por polygon (diamond) -->
  <g id="dia"><polygon points="420,100 460,125 420,150 380,125" fill="url(#g)"/></g>
  <!-- conexion del transform-icon al diamond -->
  <line x1="180" y1="125" x2="380" y2="125" stroke="black" marker-end="url(#a)"/>
</svg>'''


def test_detects_transform_custom_icon():
    path = _write_tmp(CUSTOM_ICON_SVG)
    r = validate_svg(path)
    os.unlink(path)
    # Debe detectar ambos iconos custom (transform-group + polygon-group)
    assert r.n_icons == 2


def test_no_dangling_with_custom_icons():
    """La conexión entre dos iconos custom NO debe reportarse como dangling
    (BUGS-VAL-001: antes el icono no se detectaba → R3 falso positivo)."""
    path = _write_tmp(CUSTOM_ICON_SVG)
    r = validate_svg(path)
    os.unlink(path)
    assert len(r.by_rule('R3_dangling_connection')) == 0


def test_semantic_colored_connection_is_detected():
    """Una conexión con color semántico (no negro) debe contar como conexión."""
    svg = '''<?xml version="1.0"?>
<svg xmlns="http://www.w3.org/2000/svg" width="500" height="300">
  <g id="a" transform="translate(80,100)"><rect x="0" y="0" width="80" height="50" fill="c"/></g>
  <g id="b" transform="translate(340,100)"><rect x="0" y="0" width="80" height="50" fill="c"/></g>
  <line x1="160" y1="125" x2="340" y2="125" stroke="#e8820c" marker-end="url(#a)"/>
</svg>'''
    path = _write_tmp(svg)
    r = validate_svg(path)
    os.unlink(path)
    assert r.n_connections == 1
    assert len(r.by_rule('R3_dangling_connection')) == 0
