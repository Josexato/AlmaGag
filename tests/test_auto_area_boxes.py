"""§O53 mediano plazo — AUTO dibuja cajas de área.

Cuando una señal blanda (considerations/constraints) fuerza AUTO habiendo
`areas`, cada área con 2+ miembros se siembra como zona `near` (§N46): la
caja punteada rotulada, la banda §O54 y la expulsión de intrusos salen de la
maquinaria existente. La señal ya no se pierde — cambia de representación.
Con `contains` no se convierte y el WARNING de anulación se mantiene.
"""

import json
import tempfile
import xml.etree.ElementTree as ET

from AlmaGag.generator import generate_diagram
from AlmaGag.layout.considerations import areas_to_near_seeds

NS = '{http://www.w3.org/2000/svg}'


def _emit(data, tmp_path):
    src = tempfile.NamedTemporaryFile(suffix='.sdjf', delete=False, mode='w')
    json.dump(data, src)
    src.close()
    out = tmp_path / 'o.svg'
    assert generate_diagram(src.name, output_file=str(out),
                            layout_algorithm='select')
    return ET.fromstring(out.read_text(encoding='utf-8'))


def test_seeds_from_areas():
    data = {'areas': [{'id': 'F1', 'label': 'Fase 1', 'members': ['a', 'b']},
                      {'id': 'F2', 'members': ['c']},          # <2 → no
                      {'id': 'F3', 'members': ['c', 'zz']}],   # id fantasma → no
            'considerations': [{'align': ['a', 'c']}],
            'elements': [{'id': 'a'}, {'id': 'b'}, {'id': 'c'}]}
    assert areas_to_near_seeds(data) == 1
    seeds = [c for c in data['considerations'] if 'near' in c]
    assert seeds == [{'near': ['a', 'b'], 'label': 'Fase 1'}]
    # idempotente: re-sembrar no duplica
    assert areas_to_near_seeds(data) == 0


def test_seeds_respect_constraints_alias():
    data = {'areas': [{'id': 'F1', 'members': ['a', 'b']}],
            'constraints': [{'avoid': ['a', 'b']}],
            'elements': [{'id': 'a'}, {'id': 'b'}]}
    assert areas_to_near_seeds(data) == 1
    assert 'considerations' not in data          # no ensombrece el alias
    assert any('near' in c for c in data['constraints'])


def test_auto_renders_area_as_zone_box(tmp_path):
    """Pipeline completo: considerations+areas → AUTO emite la caja punteada
    con el rótulo del área (nivel §O56, color AA §O54)."""
    data = {
        'areas': [{'id': 'F1', 'label': 'Fase de carga', 'members': ['a', 'b']}],
        'considerations': [{'align': ['a', 'c'], 'axis': 'y'}],
        'elements': [{'id': 'a', 'type': 'server', 'label': 'A'},
                     {'id': 'b', 'type': 'server', 'label': 'B'},
                     {'id': 'c', 'type': 'server', 'label': 'C'}],
        'connections': [{'from': 'a', 'to': 'b'}, {'from': 'b', 'to': 'c'}],
    }
    root = _emit(data, tmp_path)
    boxes = [r for r in root.iter(f'{NS}rect')
             if r.get('stroke-dasharray') == '4,4' and r.get('rx')]
    assert boxes, 'sin caja de zona en el render AUTO'
    labels = [t for t in root.iter(f'{NS}text')
              if ''.join(t.itertext()) == 'Fase de carga'
              and t.get('class') != 'ag-text-halo']
    assert labels and labels[0].get('fill') == '#6b6558'


def test_contains_case_keeps_warning(tmp_path, caplog):
    """Con contenedores no hay conversión: el WARNING §O53 sigue avisando."""
    import logging
    data = {
        'areas': [{'id': 'F1', 'label': 'Fase', 'members': ['x', 'y']}],
        'elements': [{'id': 'box', 'type': 'building', 'contains': ['x']},
                     {'id': 'x', 'type': 'server'},
                     {'id': 'y', 'type': 'server'}],
        'connections': [],
    }
    with caplog.at_level(logging.WARNING, logger='AlmaGag'):
        _emit(data, tmp_path)
    text = '\n'.join(r.message for r in caplog.records)
    assert '§O53' in text and 'anulada' in text
