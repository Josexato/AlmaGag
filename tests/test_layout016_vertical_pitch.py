"""WISH-LAYOUT-016 — gap vertical por corredor medido, no constante.

Hallazgo del caso TM en el visor: pitch fijo de 290px (icono 50 +
LAF_VERTICAL_SPACING 240) regalaba 100-180px de aire puro por corredor —
lámina de 1891px de alto que encogía la letra a ~7px aparentes al ajustar
a pantalla. El gap ahora es el stack real: cada mitad del corredor libra
el label de su lado (+ el label de conexión si un enlace adyacente lo
trae), con piso SPACING_MEDIUM. Incluye el fix acompañante: las pasadas
blandas (align/near/avoid) arrastran el label almacenado junto con el
icono — sin eso, mover el icono dejaba el texto huérfano (label de
'Construcción' ENCIMA de su icono, R1 real).
"""

import json

from AlmaGag.generator import select_strategy
from AlmaGag.layout import Layout
from AlmaGag.layout.considerations import apply_one
from AlmaGag.layout.engine import LayoutEngine


def _optimize(d):
    L = Layout(elements=d['elements'], connections=d['connections'],
               canvas=d.get('canvas', {'width': 1400, 'height': 900}))
    L._strategy = select_strategy(d, None)
    return LayoutEngine(verbose=False, strategy=None).optimize(L)


def _chain(n, label='Nodo\ndos líneas'):
    els = [{'id': f'n{i}', 'type': 'server', 'label': f'{label} {i}'}
           for i in range(n)]
    conns = [{'from': f'n{i}', 'to': f'n{i+1}'} for i in range(n - 1)]
    return els, conns


def test_corridor_gap_is_label_stack_not_constant():
    """Árbol de 3 rangos con labels de 2 líneas: el gap icono-a-icono
    queda muy por debajo de los 240 fijos y por encima del stack del
    label inferior (20 + 2×18 + separación)."""
    d = {'elements': [
            {'id': 'top', 'type': 'server', 'label': 'Raíz\nconsolidada'},
            {'id': 'a', 'type': 'server', 'label': 'Hijo A\nnivel medio'},
            {'id': 'b', 'type': 'server', 'label': 'Hijo B\nnivel medio'},
            {'id': 'a1', 'type': 'server', 'label': 'Nieto A1\nfuente'},
            {'id': 'b1', 'type': 'server', 'label': 'Nieto B1\nfuente'}],
         'connections': [
            {'from': 'a', 'to': 'top'}, {'from': 'b', 'to': 'top'},
            {'from': 'a1', 'to': 'a'}, {'from': 'b1', 'to': 'b'}]}
    out = _optimize(d)
    by = out.elements_by_id
    ys = sorted({round(e['y']) for e in by.values()})
    assert len(ys) == 3, f'esperaba 3 rangos, hay {ys}'
    for y1, y2 in zip(ys, ys[1:]):
        gap = y2 - (y1 + 50)              # borde inferior → techo siguiente
        assert gap < 200, f'gap {gap} sigue en la escala del 240 fijo'
        assert gap >= 56 + 12, f'gap {gap} no libra el stack del label (68)'


def test_corridor_with_connection_label_reserves_more():
    """Un label de conexión entre rangos adyacentes agranda SU corredor."""
    els, conns = _chain(3)
    conns[0]['label'] = 'enlace\ncon dos líneas'
    d = {'elements': els, 'connections': conns}
    out = _optimize(d)
    by = out.elements_by_id
    ys = sorted(round(e['y']) for e in by.values())
    gap_with = abs(ys[1] - ys[0])
    gap_sin = abs(ys[2] - ys[1])
    assert gap_with > gap_sin, \
        f'el corredor con label de conexión ({gap_with}) debería ser mayor ' \
        f'que el corredor sin ({gap_sin})'


def test_soft_pass_drags_stored_label_with_icon():
    """apply_one (align blando) mueve el icono Y su label almacenado —
    el delta del label es el mismo que el del icono."""
    d = {'elements': [{'id': 'a', 'type': 'server', 'label': 'A'},
                      {'id': 'b', 'type': 'server', 'label': 'B'}],
         'connections': [{'from': 'a', 'to': 'b'}]}
    L = Layout(elements=d['elements'], connections=d['connections'],
               canvas={'width': 800, 'height': 600})
    a, b = L.elements_by_id['a'], L.elements_by_id['b']
    a['x'], a['y'] = 100.0, 100.0
    b['x'], b['y'] = 300.0, 300.0
    L.label_positions = {'a': (140.0, 170.0, 'middle', 'bottom'),
                         'b': (340.0, 370.0, 'middle', 'bottom')}
    apply_one(L, {'kind': 'align', 'ids': ['a', 'b'], 'axis': 'x'})
    for eid, x0 in (('a', 100.0), ('b', 300.0)):
        e = L.elements_by_id[eid]
        dx = e['x'] - x0
        assert abs(dx) > 1, 'el align debía mover en x'
        lx = L.label_positions[eid][0]
        expected = (140.0 if eid == 'a' else 340.0) + dx
        assert abs(lx - expected) < 0.5, \
            f'label de {eid} no viajó con su icono (lx={lx}, esperaba {expected})'
