"""BUGS-VAL-007 (X90) — el schema HABLA.

Constructo declarado = renderizado o error explicable, nunca silencio.
La pasada `audit_schema` corre al cargar y NOMBRA toda clave que el motor
no reconoce (raíz, elements, connections, canvas, areas, journeys, lanes,
legend) y la `spec_version` declarada. Cero falsos positivos: el repo
entero pasa en silencio.
"""

import glob
import json
import logging

import pytest

from AlmaGag.validation.schema import audit_schema


def _audit(data, caplog):
    with caplog.at_level(logging.INFO, logger='AlmaGag'):
        return audit_schema(data)


def test_clean_file_is_silent(caplog):
    d = {'elements': [{'id': 'a', 'type': 'server', 'label': 'A'}],
         'connections': [{'from': 'a', 'to': 'a', 'label': 'x'}],
         'canvas': {'width': 800, 'height': 600, 'flow': 'down',
                    'legend': [{'label': 'ok', 'color': '#333'}]},
         'areas': [{'id': 'z', 'label': 'Z', 'members': ['a']}],
         'journeys': [{'id': 'j', 'label': 'J', 'path': ['a']}]}
    assert _audit(d, caplog) == 0
    assert '[schema]' not in caplog.text


def test_unknown_keys_are_named_everywhere(caplog):
    d = {'sarasa': 1,
         'elements': [{'id': 'a', 'type': 'server', 'priority': 'high'}],
         'connections': [{'from': 'a', 'to': 'a', 'grosor': 3}],
         'canvas': {'background': '#fff'},
         'areas': [{'id': 'z', 'members': ['a'], 'rol': 'chain'}],
         'journeys': [{'id': 'j', 'path': ['a'], 'ancho': 28}]}
    n = _audit(d, caplog)
    assert n == 6, caplog.text
    for frag in ("'sarasa'", "'priority'", "'grosor'", "'background'",
                 "'rol'", "'ancho'"):
        assert frag in caplog.text, f'falta {frag} en el log'
    # cada hallazgo dice DÓNDE
    assert "elements[0] ('a')" in caplog.text
    assert 'a→a' in caplog.text


def test_spec_version_is_acknowledged(caplog):
    d = {'spec_version': '2.0', 'elements': [], 'connections': []}
    assert _audit(d, caplog) == 0          # reconocida, no es hallazgo
    assert "spec_version '2.0'" in caplog.text
    assert 'WISH-ARCH-007' in caplog.text


def test_comment_convention_is_silent(caplog):
    d = {'_comment': 'nota', 'elements': [{'id': 'a', '_nota': 'x'}],
         'connections': []}
    assert _audit(d, caplog) == 0
    assert '[schema]' not in caplog.text


def test_wrong_shapes_are_named(caplog):
    d = {'elements': ['no-un-dict'], 'connections': [],
         'theme': ['deberia', 'ser', 'dict']}
    n = _audit(d, caplog)
    assert n == 2
    assert 'elements[0] no es un objeto' in caplog.text
    assert 'theme' in caplog.text


@pytest.mark.parametrize('path', sorted(
    glob.glob('docs/diagrams/gags/*.sdjf')
    + glob.glob('docs/diagrams/gags/*.gag')))
def test_repo_fixtures_pass_in_silence(path, caplog):
    """Guarda de falsos positivos: TODO fixture del repo se entiende entero.

    Si una clave nueva se implementa, entra a schema.py en el mismo commit
    — este test la reclama."""
    d = json.load(open(path))
    assert _audit(d, caplog) == 0, f'{path}:\n{caplog.text}'


def test_tabernero_case_x90(caplog):
    """El caso que destapó X90: spec_version 2.0 + members se nombran,
    no hay silencio — y members/legend son claves CONOCIDAS."""
    d = {'spec_version': '2.0',
         'elements': [{'id': 'a', 'type': 'server', 'label': 'A',
                       'status': 'confirmado'}],
         'connections': [],
         'canvas': {'flow': 'down',
                    'legend': [{'label': '◉', 'color': '#2E7D32'}]},
         'areas': [{'id': 'z', 'label': 'Z', 'members': ['a'],
                    'color': '#123456'}]}
    assert _audit(d, caplog) == 0
    assert "spec_version '2.0'" in caplog.text
