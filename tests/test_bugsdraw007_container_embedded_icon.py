"""BUGS-DRAW-007: el header del contenedor no resolvía iconos embebidos.

Un `type` embebido en el archivo (§Q63) que el elemento HIJO dibujaba
perfecto caía, en el header del contenedor, a un rect gris mudo y sin
aviso — doble violación O55 (fallback silencioso + forma muda). El
header ahora sigue la misma precedencia que draw_icon_shape: embebido →
módulo registrado → BWT rotulado con WARNING.
"""

import json
import logging

from AlmaGag.generator import generate_diagram

GIZMO = ('<svg viewBox="0 0 24 24"><circle class="gizmo-marca" cx="12" '
         'cy="12" r="10" fill="currentColor"/></svg>')


def _gag(tmp_path, cont_type):
    data = {
        'spec_version': '2.0',
        'icons': {'gizmo': GIZMO},
        'elements': [
            {'id': 'caja', 'type': cont_type, 'label': 'Caja',
             'color': '#555555', 'contains': ['h1', 'h2']},
            {'id': 'h1', 'type': 'gizmo', 'label': 'Hijo 1'},
            {'id': 'h2', 'type': 'server', 'label': 'Hijo 2'},
        ],
        'connections': [{'from': 'h1', 'to': 'h2'}],
        'canvas': {'width': 800, 'height': 600},
    }
    p = tmp_path / 'caso.gag'
    p.write_text(json.dumps(data), encoding='utf-8')
    return str(p)


def test_header_resuelve_icono_embebido(tmp_path, caplog):
    src = _gag(tmp_path, 'gizmo')
    out = tmp_path / 'caso.svg'
    with caplog.at_level(logging.WARNING, logger='AlmaGag'):
        assert generate_diagram(src, output_file=str(out),
                                layout_algorithm='select')
    svg = out.read_text(encoding='utf-8')
    # el header del contenedor lleva el embebido (grupo caja_icon con la
    # marca del SVG), no el rect gris mudo
    assert 'id="caja_icon"' in svg and svg.count('gizmo-marca') >= 2, \
        'el header no dibujó el icono embebido'
    assert "contenedor 'caja'" not in caplog.text, \
        'un type embebido no debe disparar O55 en el header'


def test_header_sin_icono_avisa_y_rotula(tmp_path, caplog):
    src = _gag(tmp_path, 'artefacto_inexistente')
    out = tmp_path / 'caso.svg'
    with caplog.at_level(logging.WARNING, logger='AlmaGag'):
        assert generate_diagram(src, output_file=str(out),
                                layout_algorithm='select')
    assert "contenedor 'caja' con type 'artefacto_inexistente'" \
        in caplog.text, 'el fallback del header sigue siendo silencioso'
    svg = out.read_text(encoding='utf-8')
    assert '>artefacto_inexistente</text>' in svg, \
        'el BWT del header no rotula su type (§Q64)'
