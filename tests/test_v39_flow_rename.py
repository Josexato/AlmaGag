"""v3.9 — consistencia del término «flow» (decisión del autor, 11-ago).

Una palabra = un concepto: «flow» queda SOLO en `canvas.flow` (dirección
de lectura). Renames duros que ENSEÑAN: el nombre viejo no se acepta en
silencio — error/warning que nombra el reemplazo.

| hasta v3.8            | desde v3.9        |
|-----------------------|-------------------|
| flows (top-level)     | journeys          |
| layout_template: flow | steps             |
| --view flow           | --view columns    |
| data_flow/control_flow| data_link/control_link |
"""

import json
import logging

import pytest

from AlmaGag.generator import generate_diagram


def _write(tmp_path, d):
    p = tmp_path / 'f.sdjf'
    p.write_text(json.dumps(d))
    return str(p)


BASE = {'elements': [{'id': 'a', 'type': 'server', 'label': 'A'},
                     {'id': 'b', 'type': 'server', 'label': 'B'}],
        'connections': [{'from': 'a', 'to': 'b'}]}


def test_flows_key_is_hard_error_naming_journeys(tmp_path):
    d = dict(BASE)
    d['flows'] = [{'id': 'x', 'label': 'y', 'path': ['a', 'b']}]
    with pytest.raises(ValueError, match=r"'flows' se renombró a 'journeys'"):
        generate_diagram(_write(tmp_path, d),
                        output_file=str(tmp_path / 'o.svg'),
                        layout_algorithm='select')


def test_template_flow_warns_naming_steps(tmp_path, caplog):
    d = dict(BASE)
    d['layout_template'] = 'flow'
    with caplog.at_level(logging.WARNING, logger='AlmaGag'):
        assert generate_diagram(_write(tmp_path, d),
                                output_file=str(tmp_path / 'o.svg'),
                                layout_algorithm='select')
    assert "se renombró a 'steps'" in caplog.text


def test_semantic_flow_warns_naming_link(tmp_path, caplog):
    d = {'elements': BASE['elements'],
         'connections': [{'from': 'a', 'to': 'b',
                          'semantic_type': 'data_flow'}]}
    with caplog.at_level(logging.WARNING, logger='AlmaGag'):
        assert generate_diagram(_write(tmp_path, d),
                                output_file=str(tmp_path / 'o.svg'),
                                layout_algorithm='select')
    assert "se renombró a 'data_link'" in caplog.text


def test_journeys_renders_with_new_legend(tmp_path):
    d = dict(BASE)
    d['journeys'] = [{'id': 'x', 'label': 'ruta', 'path': ['a', 'b']}]
    out = tmp_path / 'o.svg'
    assert generate_diagram(_write(tmp_path, d), output_file=str(out),
                            layout_algorithm='select')
    svg = out.read_text(encoding='utf-8')
    assert 'ag-journey' in svg and 'Recorridos:' in svg
    assert 'ag-flow"' not in svg


def test_no_stale_flujos_strings_in_journeys_module():
    """Hallazgo del GAG Skiller (11-ago): tras el rename, los mensajes al
    usuario no pueden apuntar a la leyenda vieja «Flujos:»."""
    src = open('AlmaGag/draw/primitives/journeys.py', encoding='utf-8').read()
    assert 'Flujos:' not in src


def test_routing_as_string_is_coerced_with_warning(tmp_path, caplog):
    """BUGS-ARCH-002: `"routing": "orthogonal"` (string) se interpreta como
    {"type": "orthogonal"} con aviso — antes: AttributeError crudo."""
    d = {'elements': [{'id': 'a', 'type': 'server', 'label': 'A'},
                      {'id': 'b', 'type': 'server', 'label': 'B'}],
         'connections': [{'from': 'a', 'to': 'b', 'routing': 'orthogonal'}]}
    p = tmp_path / 'r.sdjf'
    p.write_text(json.dumps(d))
    with caplog.at_level(logging.WARNING, logger='AlmaGag'):
        assert generate_diagram(str(p), output_file=str(tmp_path / 'r.svg'),
                                layout_algorithm='select')
    assert 'routing como string' in caplog.text


def test_roles_as_string_is_coerced_with_warning(tmp_path, caplog):
    """BUGS-ARCH-002: `roles: {"soc": "SOC"}` (string) se interpreta como
    {"label": "SOC"} con aviso — antes: AttributeError crudo."""
    d = {'elements': [{'id': 'a', 'type': 'server', 'label': 'A',
                       'role': 'soc'},
                      {'id': 'b', 'type': 'server', 'label': 'B'}],
         'connections': [{'from': 'a', 'to': 'b'}],
         'areas': [{'id': 'f1', 'label': 'F1', 'members': ['a', 'b']}],
         'roles': {'soc': 'SOC Claro'}}
    p = tmp_path / 'ro.sdjf'
    p.write_text(json.dumps(d))
    with caplog.at_level(logging.WARNING, logger='AlmaGag'):
        assert generate_diagram(str(p), output_file=str(tmp_path / 'ro.svg'),
                                layout_algorithm='select')
    assert "roles['soc'] como string" in caplog.text
