"""
Tests para WISH-LAYOUT-004 Fase 1 — template 'architecture'.

Verifica:
1. Detección correcta de roles (entry/chain/containers/abstract/terminals).
2. Distribución en T: entry vertical, containers horizontal, abstract debajo,
   terminals al final.
3. Container 'shared' (label con 'shared'/'agnost') va al centro de la fila.
4. Coords manuales se respetan (template solo asigna si falta x/y).
"""

import pytest

from AlmaGag.layout.templates.architecture import (
    _is_shared,
    _categorize,
    _order_containers_with_shared_center,
    apply_architecture_template,
)


def _make_data():
    """Mini-arquitectura: entry → main → AUTO/Shared/LAF → contract → output."""
    return {
        'elements': [
            {'id': 'input', 'type': 'document', 'label': 'archivo.sdjf'},
            {'id': 'main', 'type': 'server', 'label': 'main.py'},
            {'id': 'generator', 'type': 'factory', 'label': 'generator.py'},
            {'id': 'auto_box', 'type': 'building', 'label': 'AUTO',
             'contains': [{'id': 'auto_opt'}]},
            {'id': 'auto_opt', 'type': 'gear', 'label': 'AutoLayoutOptimizer'},
            {'id': 'laf_box', 'type': 'building', 'label': 'LAF',
             'contains': [{'id': 'laf_opt'}]},
            {'id': 'laf_opt', 'type': 'gear', 'label': 'LAFOptimizer'},
            {'id': 'shared_box', 'type': 'firewall',
             'label': 'Shared (algoritmo-agnóstico)',
             'contains': [{'id': 'router_mgr'}]},
            {'id': 'router_mgr', 'type': 'router', 'label': 'Router'},
            {'id': 'contract', 'type': 'contract', 'label': 'LayoutOptimizer'},
            {'id': 'output', 'type': 'document', 'label': 'archivo.svg'},
        ],
        'connections': [
            {'from': 'input', 'to': 'main'},
            {'from': 'main', 'to': 'generator'},
            {'from': 'generator', 'to': 'auto_opt'},
            {'from': 'generator', 'to': 'laf_opt'},
            {'from': 'auto_opt', 'to': 'contract'},
            {'from': 'laf_opt', 'to': 'contract'},
            {'from': 'auto_opt', 'to': 'router_mgr'},
            {'from': 'laf_opt', 'to': 'router_mgr'},
            {'from': 'auto_opt', 'to': 'output'},
            {'from': 'laf_opt', 'to': 'output'},
        ],
    }


def test_is_shared_detects_label():
    assert _is_shared({'label': 'Shared (algoritmo-agnóstico)'})
    assert _is_shared({'label': 'Compartido'})
    assert _is_shared({'label': 'agnostico module'})
    assert not _is_shared({'label': 'AUTO'})
    assert not _is_shared({'label': 'LAF'})
    assert not _is_shared({'label': ''})


def test_categorize_assigns_each_role():
    data = _make_data()
    cats = _categorize(data['elements'], data['connections'])
    assert [e['id'] for e in cats['entry']] == ['input']
    assert {e['id'] for e in cats['chain']} == {'main', 'generator'}
    assert {e['id'] for e in cats['containers']} == {'auto_box', 'shared_box', 'laf_box'}
    assert [e['id'] for e in cats['abstracts']] == ['contract']
    assert [e['id'] for e in cats['terminals']] == ['output']


def test_shared_container_goes_center():
    containers = [
        {'id': 'a', 'label': 'AUTO'},
        {'id': 's', 'label': 'Shared (algoritmo-agnóstico)'},
        {'id': 'l', 'label': 'LAF'},
    ]
    ordered = _order_containers_with_shared_center(containers)
    # Con 2 'other' (a, l) y 1 shared, el shared va al medio.
    assert [c['id'] for c in ordered] == ['a', 's', 'l']


def test_apply_assigns_coords_to_all_elements_without_coords():
    data = _make_data()
    apply_architecture_template(data)
    for e in data['elements']:
        # Hijos contenidos (auto_opt, laf_opt, router_mgr) NO los toca el template.
        if e['id'] in ('auto_opt', 'laf_opt', 'router_mgr'):
            continue
        assert 'x' in e, f"{e['id']} sin x"
        assert 'y' in e, f"{e['id']} sin y"


def test_apply_respects_manual_coords():
    data = _make_data()
    # Coord manual sobre 'generator' — el template debe respetarla.
    next(e for e in data['elements'] if e['id'] == 'generator').update({'x': 99, 'y': 77})
    apply_architecture_template(data)
    gen = next(e for e in data['elements'] if e['id'] == 'generator')
    assert gen['x'] == 99
    assert gen['y'] == 77


def test_apply_creates_canvas():
    data = _make_data()
    apply_architecture_template(data)
    assert 'canvas' in data
    assert data['canvas']['width'] > 0
    assert data['canvas']['height'] > 0


def test_entry_above_containers_above_terminals():
    data = _make_data()
    apply_architecture_template(data)
    by_id = {e['id']: e for e in data['elements']}
    # Entry debe estar arriba (y menor) que containers
    assert by_id['input']['y'] < by_id['auto_box']['y']
    # Containers arriba de contract
    assert by_id['auto_box']['y'] < by_id['contract']['y']
    # Contract arriba de output
    assert by_id['contract']['y'] < by_id['output']['y']


def test_shared_x_is_centered_between_others():
    data = _make_data()
    apply_architecture_template(data)
    by_id = {e['id']: e for e in data['elements']}
    auto_x = by_id['auto_box']['x']
    shared_x = by_id['shared_box']['x']
    laf_x = by_id['laf_box']['x']
    # shared debe estar entre auto y laf
    assert auto_x < shared_x < laf_x
