"""BUGS-AUTO-008 — la compactación horizontal no cizalla contenedores anidados.

Con la membresía directa, un contenedor anidado pertenecía a DOS bloques
(el de su padre y el suyo) y `node_group` resolvía por último-gana: con
offsets distintos por bloque, el anidado se separaba de sus hijos y de su
padre. Ahora cada contenedor TOP-LEVEL forma UN bloque con su subárbol
completo. El test fuerza offsets distintos por bloque (mock) y exige que
la contención sobreviva a la adopción del candidato.
"""

from unittest.mock import patch

from AlmaGag.generator import select_strategy
from AlmaGag.layout import Layout
from AlmaGag.layout.engine import LayoutEngine
from AlmaGag.layout.strategies.auto.optimizer import AutoLayoutOptimizer


def _nested_layout():
    d = {'elements': [
        {'id': 'z', 'type': 'area', 'label': 'Z', 'contains': ['sub', 'a']},
        {'id': 'sub', 'type': 'building', 'label': 'Sub', 'contains': ['x', 'y']},
        {'id': 'x', 'type': 'server', 'label': 'X'},
        {'id': 'y', 'type': 'server', 'label': 'Y'},
        {'id': 'a', 'type': 'server', 'label': 'A'},
        {'id': 'w', 'type': 'server', 'label': 'W'},
    ], 'connections': [{'from': 'w', 'to': 'a', 'direction': 'forward'}]}
    L = Layout(elements=d['elements'], connections=d['connections'],
               canvas={'width': 1200, 'height': 900})
    L._strategy = select_strategy(d, 'auto')
    return LayoutEngine(verbose=False, strategy=None).optimize(L)


def _bbox(e):
    return (e['x'], e['y'], e['x'] + e.get('width', 80), e['y'] + e.get('height', 50))


def _assert_contained(res):
    by = res.elements_by_id
    for cid in ('z', 'sub'):
        c = by[cid]
        cb = _bbox(c)
        for ref in c['contains']:
            m = by[ref if isinstance(ref, str) else ref['id']]
            mb = _bbox(m)
            assert cb[0] <= mb[0] and mb[2] <= cb[2] \
                and cb[1] <= mb[1] and mb[3] <= cb[3], \
                f'{m["id"]} fuera de {cid} tras compactar'


def test_forced_offsets_do_not_shear_nested_containers():
    res = _nested_layout()
    opt = AutoLayoutOptimizer(verbose=False)
    opt.analyze(res)

    def forced_offsets(groups, pos, adj, axis='x'):
        # un offset DISTINTO por bloque: con la doble membresía vieja esto
        # separaba al contenedor anidado de sus hijos
        return {k: 60.0 * i for i, k in enumerate(sorted(groups, key=str))}

    with patch('AlmaGag.layout.strategies.auto.optimizer.optimize_group_offsets',
               side_effect=forced_offsets), \
         patch.object(AutoLayoutOptimizer, 'evaluate', return_value=0), \
         patch('AlmaGag.layout.strategies.auto.optimizer.count_crossings',
               side_effect=[0, 1]):     # candidato 0 < original 1 → se adopta
        out = opt._compact_horizontal(res)

    assert out is not res, 'el candidato debía adoptarse (mock)'
    _assert_contained(out)


def test_membership_is_transitive_single_block():
    """El subárbol entero (z, sub, x, y, a) comparte bloque."""
    res = _nested_layout()
    opt = AutoLayoutOptimizer(verbose=False)
    captured = {}

    def spy(groups, pos, adj, axis='x'):
        captured.update(groups)
        return {k: 0.0 for k in groups}

    with patch('AlmaGag.layout.strategies.auto.optimizer.optimize_group_offsets',
               side_effect=spy):
        opt._compact_horizontal(res)

    blocks = {m: k for k, ms in captured.items() for m in ms}
    assert blocks['sub'] == blocks['z'] == blocks['x'] == blocks['y'] == blocks['a']
    assert ('cont', 'sub') not in captured, 'el anidado no forma bloque propio'
