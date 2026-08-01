"""§O57 — tokens de tema: sección `theme` top-level + `"color": "<token>"`.

El token se resuelve a su hex antes de que el pipeline vea el JSON; un hex
literal (o nombre CSS que no es token) sigue válido y gana.
"""

import json
import tempfile

from AlmaGag.generator import generate_diagram
from AlmaGag.layout.theme import apply_theme


def test_tokens_resolved_in_all_sections():
    data = {
        'theme': {'vp': '#663399', 'acento': '#e8820c'},
        'elements': [{'id': 'a', 'color': 'vp'},
                     {'id': 'b', 'color': '#112233'},      # literal: se respeta
                     {'id': 'c', 'color': 'tomato'}],      # CSS no-token: igual
        'connections': [{'from': 'a', 'to': 'b', 'color': 'acento'}],
        'areas': [{'id': 'F1', 'color': 'vp'}],
        'roles': {'ing': {'label': 'Ingeniería', 'color': 'vp'}},
    }
    assert apply_theme(data) == 4
    assert data['elements'][0]['color'] == '#663399'
    assert data['elements'][1]['color'] == '#112233'
    assert data['elements'][2]['color'] == 'tomato'
    assert data['connections'][0]['color'] == '#e8820c'
    assert data['areas'][0]['color'] == '#663399'
    assert data['roles']['ing']['color'] == '#663399'


def test_no_theme_is_noop():
    data = {'elements': [{'id': 'a', 'color': 'vp'}]}
    assert apply_theme(data) == 0
    assert data['elements'][0]['color'] == 'vp'     # sin theme no se toca


def test_pipeline_renders_theme_colors(tmp_path):
    data = {
        'theme': {'corporativo': '#663399'},
        'elements': [{'id': 'a', 'type': 'server', 'label': 'A',
                      'color': 'corporativo'},
                     {'id': 'b', 'type': 'server', 'label': 'B'}],
        'connections': [{'from': 'a', 'to': 'b', 'color': 'corporativo'}],
    }
    src = tempfile.NamedTemporaryFile(suffix='.sdjf', delete=False, mode='w')
    json.dump(data, src)
    src.close()
    out = tmp_path / 'o.svg'
    assert generate_diagram(src.name, output_file=str(out),
                            layout_algorithm='auto')
    svg = out.read_text(encoding='utf-8')
    assert '#663399' in svg          # gradiente del icono + línea temáticos
    assert 'corporativo' not in svg  # el token nunca llega al SVG
