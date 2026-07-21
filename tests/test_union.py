"""§H7 — tipo semántico `union` (matrimonio): 10 aristas → 5 + barra, 0 cruces."""
import json
from AlmaGag.layout import Layout
from AlmaGag.layout.engine import LayoutEngine
from AlmaGag.generator import select_strategy
from AlmaGag.layout.unions import expand_unions
from AlmaGag.layout.metrics import count_crossings


def test_expand_unions_creates_node_and_bars():
    data = {
        'elements': [{'id': 'a'}, {'id': 'b'}, {'id': 'c'}],
        'unions': [{'id': 'u', 'between': ['a', 'b']}],
        'connections': [{'from': 'u', 'to': 'c'}],
    }
    n = expand_unions(data)
    assert n == 1
    # nodo de union creado
    u = [e for e in data['elements'] if e['id'] == 'u']
    assert u and u[0]['type'] == 'union'
    # dos aristas de barra a→u, b→u
    bars = [c for c in data['connections'] if c.get('_union_bar')]
    assert {c['from'] for c in bars} == {'a', 'b'}
    assert all(c['to'] == 'u' for c in bars)


def test_expand_unions_noop_without_unions():
    data = {'elements': [{'id': 'a'}], 'connections': []}
    assert expand_unions(data) == 0


def test_genealogico_union_zero_crossings():
    data = json.load(open('docs/diagrams/gags/11-stresstest.sdjf'))
    assert 'unions' in data  # ya migrado a union
    expand_unions(data)
    L = Layout(elements=data['elements'], connections=data['connections'],
               canvas=data.get('canvas', {}))
    L._strategy = select_strategy(data, 'auto')
    res = LayoutEngine(verbose=False, strategy=None).optimize(L)
    assert count_crossings(res) == 0
