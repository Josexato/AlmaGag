"""WISH-LAYOUT-014 (V81) — contenedor-feeder = carril lateral.

Un contenedor cuya única relación con el grafo es UNA arista hacia un
nodo primario no ocupa un rango propio del tronco: va al costado del
rango de su destino, con arista corta (≤2 codos). El tronco no se estira.
"""

import json

from AlmaGag.generator import select_strategy
from AlmaGag.layout import Layout
from AlmaGag.layout.engine import LayoutEngine

PPTO = 'docs/diagrams/gags/mina-presupuesto.sdjf'


def _optimize(d, strategy='auto'):
    L = Layout(elements=d['elements'], connections=d['connections'],
               canvas={'width': 1400, 'height': 900})
    L._strategy = strategy if strategy else select_strategy(d, None)
    return LayoutEngine(verbose=False, strategy=strategy).optimize(L)


def _v_overlap(a, b):
    return a['y'] < b['y'] + b.get('height', 50) and \
        b['y'] < a['y'] + a.get('height', 50)


def test_synthetic_feeder_keeps_trunk_pitch():
    """Tronco a→b→c con feeder F→b: el pitch del tronco no cambia y F
    queda al costado del rango de b (solape vertical), no en un rango."""
    d = {'elements': [
            {'id': 'a', 'type': 'server', 'label': 'A'},
            {'id': 'b', 'type': 'server', 'label': 'B'},
            {'id': 'c', 'type': 'server', 'label': 'C'},
            {'id': 'F', 'type': 'building', 'label': 'Feeder',
             'contains': ['f1', 'f2']},
            {'id': 'f1', 'type': 'server', 'label': 'F1'},
            {'id': 'f2', 'type': 'server', 'label': 'F2'}],
         'connections': [
            {'from': 'a', 'to': 'b', 'direction': 'forward'},
            {'from': 'b', 'to': 'c', 'direction': 'forward'},
            {'from': 'F', 'to': 'b', 'direction': 'forward'}]}
    out = _optimize(d)
    E = out.elements_by_id
    pitch_ab = E['b']['y'] - E['a']['y']
    pitch_bc = E['c']['y'] - E['b']['y']
    assert abs(pitch_ab - pitch_bc) < 2, \
        f'el feeder estiró el tronco: {pitch_ab:.0f} vs {pitch_bc:.0f}'
    assert _v_overlap(E['F'], E['b']), 'el feeder no está al costado de b'
    # fuera de la columna del tronco
    trunk_x = {E[i]['x'] for i in 'abc'}
    assert E['F']['x'] > max(trunk_x) + 40 or \
        E['F']['x'] + E['F']['width'] < min(trunk_x) - 40


def test_presupuesto_trunk_not_stretched():
    """Caso real: dppto→ppto vuelve al pitch normal (era 635px con el
    contenedor en medio) e `indir` queda al costado del rango de constr
    con arista de ≤2 codos."""
    d = json.load(open(PPTO))
    out = _optimize(d, strategy=None)
    E = out.elements_by_id
    sep = E['ppto']['y'] - E['dppto']['y']
    assert sep <= 350, f'tronco estirado: dppto→ppto a {sep:.0f}px'
    assert _v_overlap(E['indir'], E['constr']), \
        'indir no está al costado del rango de constr'
    for conn in out.connections:
        if conn['from'] == 'indir' or conn['to'] == 'indir':
            cp = conn.get('computed_path') or {}
            pts = cp.get('points') or []
            assert len(pts) - 2 <= 2, f'arista del feeder con {len(pts)-2} codos'
