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
