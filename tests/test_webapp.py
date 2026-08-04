"""Tests del visor web local (AlmaGag/webapp).

Cubre la función de render que usa el endpoint /render: entrada válida
produce SVG, entrada inválida devuelve ok=False con log y sin excepción.
"""

import os

from AlmaGag.webapp.server import render_source

EXAMPLES_DIR = os.path.join(os.path.dirname(__file__), '..', 'examples')


def _leer(nombre):
    with open(os.path.join(EXAMPLES_DIR, nombre), 'r', encoding='utf-8') as f:
        return f.read()


def test_render_source_sdjf_valido():
    contenido = _leer('red-edificios.sdjf')
    ok, svg, log = render_source('red-edificios.sdjf', contenido)
    assert ok, f"render falló, log: {log}"
    assert svg and '<svg' in svg


def test_render_source_json_invalido():
    ok, svg, log = render_source('roto.sdjf', '{esto no es json')
    assert not ok
    assert svg is None
    assert 'ERROR' in log


def test_render_source_extension_desconocida_no_revienta():
    contenido = _leer('red-edificios.sdjf')
    ok, svg, log = render_source('nota.txt', contenido)
    assert ok, f"render falló, log: {log}"
    assert '<svg' in svg
