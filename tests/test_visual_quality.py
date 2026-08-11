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


def test_validate_gag_without_canvas_uses_defaults(tmp_path):
    """BUGS-VAL-004: `canvas` es opcional en el formato — validate_gag debe
    poner los mismos defaults que el CLI, no reventar con KeyError."""
    import json
    from AlmaGag.validation.visual_quality import validate_gag
    src = tmp_path / 'sin_canvas.sdjf'
    src.write_text(json.dumps({
        'elements': [
            {'id': 'a', 'type': 'server', 'label': 'A'},
            {'id': 'b', 'type': 'database', 'label': 'B'},
        ],
        'connections': [{'from': 'a', 'to': 'b'}],
    }))
    report = validate_gag(str(src))
    assert report.n_icons >= 2


def test_small_container_is_not_an_icon_for_r1(tmp_path):
    """BUGS-VAL-005 (GAG Skiller): un contenedor CHICO (bajo el umbral de
    300×200) contaba como icono y todo texto interior daba R1 falso —
    zona de 2 miembros: 3×R1 contra 0 con 3-4 miembros. El rect del
    contenedor ahora viaja con class="ag-container" (contrato del
    renderer) y el validador lo excluye; un R1 real sigue saltando."""
    import json
    from AlmaGag.generator import generate_diagram
    d = {'elements': [
            {'id': 'z', 'type': 'area', 'label': 'ZONA',
             'contains': [{'id': 'e0', 'scope': 'full'},
                          {'id': 'e1', 'scope': 'full'}]},
            {'id': 'e0', 'type': 'server', 'label': 'Equipo 0'},
            {'id': 'e1', 'type': 'server', 'label': 'Equipo 1'},
            {'id': 'x', 'type': 'router', 'label': 'Externo'}],
         'connections': [{'from': 'e0', 'to': 'x',
                          'direction': 'bidirectional'}]}
    src = tmp_path / 'zon2.sdjf'
    src.write_text(json.dumps(d))
    out = tmp_path / 'zon2.svg'
    generate_diagram(str(src), output_file=str(out),
                     layout_algorithm='select')
    report = validate_svg(str(out))
    r1 = [v for v in report.violations if v.rule == 'R1_label_over_icon']
    assert not r1, f'falsos positivos R1 en zona de 2 miembros: {r1}'

    # control positivo: texto ENCIMA de un icono con gradiente sí es R1
    svg = ('<?xml version="1.0"?>'
           '<svg xmlns="http://www.w3.org/2000/svg" width="400" height="300">'
           '<defs><linearGradient id="gradient-a">'
           '<stop offset="0" stop-color="#888"/></linearGradient></defs>'
           '<rect fill="url(#gradient-a)" x="80" y="80" width="80" height="50"/>'
           '<text x="120" y="110" text-anchor="middle" font-size="14px">'
           'encima del icono</text></svg>')
    ctrl = tmp_path / 'ctrl.svg'
    ctrl.write_text(svg)
    report2 = validate_svg(str(ctrl))
    assert any(v.rule == 'R1_label_over_icon' for v in report2.violations), \
        'el fix apagó la detección de R1 reales'


def test_normalizing_scale_does_not_inflate_icon_bbox(tmp_path):
    """BUGS-VAL-006 (GAG Skiller): el scale del transform normaliza el
    viewBox intrínseco del icono a la ranura 80×50 (firewall: 51×43 →
    ×1.57/×1.16) — ningún emisor magnifica más allá de la ranura. El
    validador multiplicaba la ranura por el scale: bbox de 125×58 y R1
    falso de 512px² del FortiGate contra su PROPIO label lateral."""
    import json
    from AlmaGag.generator import generate_diagram
    d = {'elements': [
            {'id': 'i', 'type': 'cloud', 'label': 'Internet'},
            {'id': 'fw', 'type': 'firewall', 'label': 'FortiGate'},
            {'id': 'sw', 'type': 'router', 'label': 'Switch'},
            {'id': 's', 'type': 'server', 'label': 'Servidor'}],
         'connections': [
            {'from': 'i', 'to': 'fw', 'direction': 'bidirectional'},
            {'from': 'fw', 'to': 'sw', 'direction': 'none'},
            {'from': 'sw', 'to': 's', 'direction': 'none'}]}
    src = tmp_path / 't6fw.sdjf'
    src.write_text(json.dumps(d))
    out = tmp_path / 't6fw.svg'
    generate_diagram(str(src), output_file=str(out),
                     layout_algorithm='select')
    report = validate_svg(str(out))
    r1 = [v for v in report.violations if v.rule == 'R1_label_over_icon']
    assert not r1, f'bbox inflado por scale normalizador: {r1}'
    # el clamp no debe apagar la detección de conexiones (R3)
    assert report.n_connections == 3

    # control positivo: un <g> escalado con texto ENCIMA sí es R1
    svg = ('<?xml version="1.0"?>'
           '<svg xmlns="http://www.w3.org/2000/svg" width="400" height="300">'
           '<g id="fw2" transform="translate(80,80) '
           'scale(1.5686274509803921,1.1627906976744187)">'
           '<path d="M0 0 L51 0 L51 43 L0 43 Z" fill="#a90000"/></g>'
           '<text x="120" y="110" text-anchor="middle" font-size="14px">'
           'encima del icono</text></svg>')
    ctrl = tmp_path / 'ctrl6.svg'
    ctrl.write_text(svg)
    report2 = validate_svg(str(ctrl))
    assert any(v.rule == 'R1_label_over_icon' for v in report2.violations), \
        'el clamp apagó la detección de R1 reales dentro de la ranura'
