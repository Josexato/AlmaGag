"""§Q63 — semantic_type declarado; inferencia sólo con el mapa DEL ARCHIVO.

El vocabulario texto→clase NUNCA vive en el código de AlmaGag (§R,
refinado por el autor): viaja declarado en cada conexión (camino 1,
preferido) o en la sección `semantics` embebida en el archivo (camino 2,
como `icons{}`), que el motor aplica mecánicamente con WARNING. Sin match
→ clase neutra; lo declarado jamás se pisa.
"""

import json
import logging

import pytest

from AlmaGag.layout.semantics import apply_embedded_semantics

FIXTURE = 'docs/diagrams/gags/mina-arquitectura-fisica.sdjf'


def test_no_section_is_silent_noop(caplog):
    d = {'connections': [{'from': 'a', 'to': 'b', 'label': 'FO troncal'}]}
    with caplog.at_level(logging.WARNING, logger='AlmaGag'):
        assert apply_embedded_semantics(d) == 0
    assert 'semantic' not in caplog.text
    assert 'semantic_type' not in d['connections'][0]


def test_embedded_map_both_forms_with_warning(caplog):
    """Forma dict (keywords+color) y forma lista; match case-insensitive por
    subcadena; WARNING agregado — nunca en silencio."""
    d = {
        'semantics': {
            'transporte': {'keywords': ['FO', 'MW'], 'color': '#1f6fd0'},
            'soporte': ['reposicion', 'fat/sat'],
        },
        'connections': [
            {'from': 'a', 'to': 'b', 'label': 'enlace fo redundante'},
            {'from': 'c', 'to': 'd', 'label': 'FAT/SAT'},
            {'from': 'e', 'to': 'f', 'label': 'sin señal alguna'},
        ],
    }
    with caplog.at_level(logging.WARNING, logger='AlmaGag'):
        assert apply_embedded_semantics(d) == 2
    a, c, e = d['connections']
    assert a['semantic_type'] == 'transporte' and a['color'] == '#1f6fd0'
    assert c['semantic_type'] == 'soporte' and 'color' not in c
    assert 'semantic_type' not in e          # sin match → neutra, no se adivina
    assert '§Q63' in caplog.text and 'inferido' in caplog.text


def test_declared_semantic_type_never_overridden():
    d = {
        'semantics': {'transporte': ['FO']},
        'connections': [
            {'from': 'a', 'to': 'b', 'label': 'FO', 'semantic_type': 'custom'},
            {'from': 'c', 'to': 'd', 'label': 'FO', 'color': '#123456'},
        ],
    }
    d['semantics']['transporte'] = {'keywords': ['FO'], 'color': '#ffffff'}
    apply_embedded_semantics(d)
    assert d['connections'][0]['semantic_type'] == 'custom'
    assert d['connections'][1]['color'] == '#123456'   # color presente se respeta


def test_engine_ships_no_vocabulary():
    """El módulo del mecanismo no carga NINGUNA palabra clave de dominio —
    el vocabulario viaja en el archivo o lo pone el skill."""
    import inspect
    import AlmaGag.layout.semantics as m
    src = inspect.getsource(m)
    body = src.split('"""', 2)[2]          # sin los docstrings de ejemplo
    for word in ('backhaul', 'energia', 'FAT', 'Mbps', 'data_flow'):
        assert word not in body, f'vocabulario {word!r} embebido en el motor'


def test_mina_fixture_declares_everything():
    """Camino 1 ejemplar: el fixture minero declara semantic_type en TODAS
    sus conexiones (7 clases del dominio) y colorea vía tokens §O57 — sin
    depender de inferencia (log limpio)."""
    d = json.load(open(FIXTURE))
    classes = {c.get('semantic_type') for c in d['connections']}
    assert None not in classes, 'conexión sin semantic_type en el fixture'
    assert len(classes) == 7
    assert all(c.get('color', '').startswith('c-') for c in d['connections'])
    assert set(d['theme']) == {f'c-{s}' for s in classes}


def test_mina_emits_legend_with_domain_classes(tmp_path):
    """≥3 clases declaradas → leyenda §N48 al pie con los nombres de clase."""
    from AlmaGag.generator import generate_diagram
    out = tmp_path / 'mina.svg'
    generate_diagram(FIXTURE, output_file=str(out), layout_algorithm='select')
    svg = out.read_text()
    assert 'Enlaces:' in svg
    for cls in ('backhaul', 'interconexion', 'acceso', 'energia',
                'soporte', 'gestion-remota', 'administrativo'):
        assert f'>{cls}<' in svg, f'clase {cls} ausente de la leyenda'
    assert svg.count('#1f6fd0') >= 8       # backhaul pinta sus 8 enlaces
