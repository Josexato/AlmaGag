"""WISH-AUTO-010 — libre multi-zona a la periferia del baricentro.

Un elemento libre cuyos vecinos viven TODOS dentro de contenedores (en ≥2
distintos) no queda exiliado al fondo del canvas: se coloca fuera de las
cajas, en el lado más cercano al baricentro de sus vecinos.
"""

import json

from AlmaGag.generator import select_strategy
from AlmaGag.layout import Layout
from AlmaGag.layout.engine import LayoutEngine

FISICO = 'docs/diagrams/gags/mina-fisico-v2.gag'


def _center(e):
    return (e['x'] + e.get('width', 80) / 2.0,
            e['y'] + e.get('height', 50) / 2.0)


def _hull(out):
    boxes = [(c['x'], c['y'], c['x'] + c.get('width', 0),
              c['y'] + c.get('height', 0))
             for c in out.elements if 'contains' in c and 'x' in c]
    return (min(b[0] for b in boxes), min(b[1] for b in boxes),
            max(b[2] for b in boxes), max(b[3] for b in boxes))


def _dist(p, q):
    return ((p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2) ** 0.5


def test_multizone_free_element_sits_near_barycenter():
    """Sintético: libre conectado a un miembro de cada una de dos zonas
    queda fuera de las cajas y CERCA del baricentro de sus vecinos."""
    d = {'elements': [
            {'id': 'z1', 'type': 'area', 'label': 'Zona 1',
             'contains': ['a', 'b']},
            {'id': 'z2', 'type': 'area', 'label': 'Zona 2',
             'contains': ['c', 'd']},
            {'id': 'a', 'type': 'server', 'label': 'A'},
            {'id': 'b', 'type': 'server', 'label': 'B'},
            {'id': 'c', 'type': 'server', 'label': 'C'},
            {'id': 'd', 'type': 'server', 'label': 'D'},
            {'id': 'libre', 'type': 'powergrid', 'label': 'Energia'}],
         'connections': [
            {'from': 'a', 'to': 'c', 'direction': 'forward'},
            {'from': 'libre', 'to': 'a', 'direction': 'forward'},
            {'from': 'libre', 'to': 'c', 'direction': 'forward'}]}
    L = Layout(elements=d['elements'], connections=d['connections'],
               canvas={'width': 1400, 'height': 900})
    L._strategy = 'auto'
    out = LayoutEngine(verbose=False, strategy='auto').optimize(L)
    libre = out.elements_by_id['libre']
    x1, y1, x2, y2 = _hull(out)
    lc = _center(libre)
    # fuera de toda caja
    for c in out.elements:
        if 'contains' not in c or 'x' not in c:
            continue
        assert not (c['x'] < lc[0] < c['x'] + c['width']
                    and c['y'] < lc[1] < c['y'] + c['height']), \
            f'libre dentro de {c["id"]}'
    # cerca del baricentro de sus vecinos (a, c)
    bary = ((_center(out.elements_by_id['a'])[0]
             + _center(out.elements_by_id['c'])[0]) / 2,
            (_center(out.elements_by_id['a'])[1]
             + _center(out.elements_by_id['c'])[1]) / 2)
    half_diag = _dist((x1, y1), (x2, y2)) / 2
    assert _dist(lc, bary) <= half_diag, \
        f'libre exiliado: {_dist(lc, bary):.0f}px del baricentro ' \
        f'(tope {half_diag:.0f})'


def test_energia_ext_no_longer_exiled():
    """Caso real: energia_ext (vecinos ge_mina/ge_pila en dos zonas) queda
    a media diagonal o menos de su baricentro — antes: 1.5 diagonales."""
    d = json.load(open(FISICO))
    L = Layout(elements=d['elements'], connections=d['connections'],
               canvas={'width': 1400, 'height': 900})
    L._strategy = select_strategy(d, None)
    out = LayoutEngine(verbose=False, strategy=None).optimize(L)
    lc = _center(out.elements_by_id['energia_ext'])
    bary = ((_center(out.elements_by_id['ge_mina'])[0]
             + _center(out.elements_by_id['ge_pila'])[0]) / 2,
            (_center(out.elements_by_id['ge_mina'])[1]
             + _center(out.elements_by_id['ge_pila'])[1]) / 2)
    x1, y1, x2, y2 = _hull(out)
    half_diag = _dist((x1, y1), (x2, y2)) / 2
    assert _dist(lc, bary) <= half_diag, \
        f'energia_ext sigue exiliado: {_dist(lc, bary):.0f}px ' \
        f'(tope {half_diag:.0f})'
