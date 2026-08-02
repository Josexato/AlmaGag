"""§Q65 — afinidad y orden entre áreas (opcional + derivación determinista).

Declarado: `considerations.near` con ids de ÁREAS forma bloques
indivisibles (adyacentes) en su fila — y se consume a nivel de zona, nunca
como cluster de miembros (§N46) ni como empujón blando (rescate ④).
Sin declarar: la banda operativa se encadena por adyacencia de TRANSPORTE
(zonas unidas por enlaces bidirectional/none quedan contiguas) y la
periferia por baricentro; desempate por orden de aparición. Determinista.
"""

import json

import pytest

from AlmaGag.generator import select_strategy
from AlmaGag.layout import Layout
from AlmaGag.layout.engine import LayoutEngine


def _mk(elements, connections, considerations=None):
    d = {'elements': elements, 'connections': connections}
    if considerations:
        d['considerations'] = considerations
    L = Layout(elements=d['elements'], connections=d['connections'],
               canvas={'width': 1600, 'height': 1000})
    L._strategy = select_strategy(d, 'auto')
    if considerations:
        from AlmaGag.layout.considerations import extract_considerations
        L._considerations = extract_considerations(d)
    return LayoutEngine(verbose=False, strategy=None).optimize(L)


def _zone(zid, member):
    return [{'id': zid, 'type': 'area', 'label': zid.upper(),
             'contains': [member]},
            {'id': member, 'type': 'server', 'label': f'srv {member}'}]


def _three_band_one_service(considerations=None):
    """Tres zonas operativas (za, zc, zb en orden de aparición) con
    transporte za–zb y zb–zc, y una zona de servicio."""
    els = (_zone('za', 'a1') + _zone('zc', 'c1') + _zone('zb', 'b1')
           + _zone('zs', 's1'))
    conns = [
        {'from': 'a1', 'to': 'b1', 'direction': 'bidirectional', 'label': 'FO'},
        {'from': 'b1', 'to': 'c1', 'direction': 'bidirectional', 'label': 'FO'},
        {'from': 's1', 'to': 'a1', 'direction': 'forward', 'label': 'soporte'},
    ]
    return _mk(els, conns, considerations)


def test_band_chains_by_transport_adjacency():
    """Sin declarar nada: zb (unida a za y zc por transporte) queda EN MEDIO,
    aunque por aparición iría al final."""
    res = _three_band_one_service()
    by = res.elements_by_id
    xs = sorted(('za', 'zb', 'zc'), key=lambda z: by[z]['x'])
    assert xs[1] == 'zb', f'la cadena de transporte no quedó contigua: {xs}'


def test_declared_affinity_forms_adjacent_block():
    """near [za, zc] declarado: ambas quedan contiguas (bloque indivisible),
    aun rompiendo la cadena de transporte."""
    res = _three_band_one_service(
        considerations=[{'near': ['za', 'zc']}])
    by = res.elements_by_id
    xs = sorted(('za', 'zb', 'zc'), key=lambda z: by[z]['x'])
    ia, ic = xs.index('za'), xs.index('zc')
    assert abs(ia - ic) == 1, f'za y zc no quedaron adyacentes: {xs}'


def test_area_near_not_clustered_as_members():
    """El near de áreas se consume como afinidad: ningún contenedor queda
    marcado `_near_zone` (cluster N46) y la consideración queda marcada."""
    res = _three_band_one_service(
        considerations=[{'near': ['za', 'zc']}])
    for z in ('za', 'zb', 'zc', 'zs'):
        assert res.elements_by_id[z].get('_near_zone') is None
    # los miembros ⊆ su caja siguen intactos (el bloque movió zonas rígidas)
    for z in ('za', 'zb', 'zc', 'zs'):
        zb_ = res.elements_by_id[z]
        for ref in zb_['contains']:
            m = res.elements_by_id[ref if isinstance(ref, str) else ref['id']]
            assert zb_['x'] <= m['x'] and \
                m['x'] + m.get('width', 80) <= zb_['x'] + zb_['width']


def test_periphery_affinity_block():
    """Dos zonas de servicio con baricentros opuestos + near declarado:
    terminan contiguas en la fila periférica."""
    els = (_zone('za', 'a1') + _zone('zb', 'b1')
           + _zone('zs1', 's1') + _zone('zs2', 's2') + _zone('zs3', 's3'))
    conns = [
        {'from': 'a1', 'to': 'b1', 'direction': 'bidirectional', 'label': 'FO'},
        {'from': 's1', 'to': 'a1', 'direction': 'forward', 'label': 'soporte'},
        {'from': 's2', 'to': 'b1', 'direction': 'forward', 'label': 'soporte'},
        {'from': 's3', 'to': 'b1', 'direction': 'forward', 'label': 'soporte'},
    ]
    res = _mk(els, conns, considerations=[{'near': ['zs1', 'zs3']}])
    by = res.elements_by_id
    xs = sorted(('zs1', 'zs2', 'zs3'), key=lambda z: by[z]['x'])
    assert abs(xs.index('zs1') - xs.index('zs3')) == 1, \
        f'zs1 y zs3 no quedaron contiguas: {xs}'


def test_deterministic():
    """Dos corridas idénticas producen exactamente las mismas posiciones."""
    a = _three_band_one_service()
    b = _three_band_one_service()
    pos_a = {e['id']: (e.get('x'), e.get('y')) for e in a.elements}
    pos_b = {e['id']: (e.get('x'), e.get('y')) for e in b.elements}
    assert pos_a == pos_b


def test_mina_fixture_unchanged_by_q65():
    """El fixture minero no declara afinidad: banda de 2 (cadena trivial) y
    periferia por baricentro — mismo orden que P60."""
    d = json.load(open('docs/diagrams/gags/mina-arquitectura-fisica.sdjf'))
    L = Layout(elements=d['elements'], connections=d['connections'],
               canvas={'width': 1400, 'height': 900})
    L._strategy = select_strategy(d, 'auto')
    res = LayoutEngine(verbose=False, strategy=None).optimize(L)
    by = res.elements_by_id
    assert by['z_mina']['x'] < by['z_pila']['x']
    svc = sorted(('z_contratista', 'z_externos', 'z_remoto'),
                 key=lambda z: by[z]['x'])
    assert svc == ['z_contratista', 'z_externos', 'z_remoto']
