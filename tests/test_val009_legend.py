"""BUGS-VAL-009 — una sola verdad sobre canvas.legend (PY-002).

(a) Los strings VALEN (la spec manda): el audit ya no los llama «no es
    un objeto — se ignora» mientras el drawer los dibuja.
(b) hier reconstruía el dict canvas entero en 5 sitios (areas, lanes,
    matrix, optimizer×2) y la leyenda del autor moría sin aviso: ahora
    width/height son del motor y el resto se conserva.
(c) Un dict con clave desconocida sigue auditado.
"""

import json
import logging

from AlmaGag.generator import generate_diagram

LEGEND = ['Estado al cierre', {'label': 'Prioridad', 'color': '#c62828'}]


def _gen(tmp_path, data, name):
    src = tmp_path / f'{name}.sdjf'
    src.write_text(json.dumps(data), encoding='utf-8')
    out = tmp_path / f'{name}.svg'
    assert generate_diagram(str(src), output_file=str(out),
                            layout_algorithm='select')
    return out.read_text(encoding='utf-8')


def test_strings_validos_sin_aviso_falso_en_auto(tmp_path, caplog):
    data = {'canvas': {'width': 600, 'height': 400, 'legend': LEGEND},
            'elements': [{'id': 'a', 'label': 'A'}, {'id': 'b', 'label': 'B'}],
            'connections': [{'from': 'a', 'to': 'b'}]}
    with caplog.at_level(logging.WARNING, logger='AlmaGag'):
        svg = _gen(tmp_path, data, 'auto')
    assert 'Estado al cierre' in svg and 'Prioridad' in svg
    assert 'no es un objeto' not in caplog.text, \
        'el audit sigue mintiendo sobre strings válidos'


def test_hier_con_areas_conserva_la_leyenda(tmp_path):
    data = {'canvas': {'width': 900, 'height': 600, 'legend': LEGEND},
            'elements': [{'id': 'a', 'label': 'A'}, {'id': 'b', 'label': 'B'}],
            'connections': [{'from': 'a', 'to': 'b'}],
            'areas': [{'id': 'z', 'label': 'Zona', 'members': ['a', 'b']}]}
    svg = _gen(tmp_path, data, 'hier')
    assert 'Estado al cierre' in svg and 'Prioridad' in svg, \
        'hier volvió a perder la leyenda al reconstruir el canvas'


def test_dict_con_clave_desconocida_sigue_auditado(tmp_path, caplog):
    data = {'canvas': {'width': 600, 'height': 400,
                       'legend': [{'label': 'X', 'colr': '#f00'}]},
            'elements': [{'id': 'a', 'label': 'A'}],
            'connections': []}
    with caplog.at_level(logging.WARNING, logger='AlmaGag'):
        _gen(tmp_path, data, 'typo')
    assert "'colr'" in caplog.text, 'la clave desconocida quedó sin nombrar'
