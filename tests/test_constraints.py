"""
Constraints declarativas (rescate ④ desde LAF) — `AlmaGag.layout.constraints`.

Cubre el parseo del schema SDJF y la semántica geométrica de align/near/avoid.
"""

import json

from AlmaGag.layout.layout import Layout
from AlmaGag.layout.constraints import extract_constraints, apply_constraints
from AlmaGag.config import ICON_WIDTH, ICON_HEIGHT


def _layout(elements):
    return Layout(elements=elements, connections=[],
                  canvas={'width': 1000, 'height': 1000})


def _el(eid, x, y):
    return {'id': eid, 'x': x, 'y': y}


def _cx(e):
    return e['x'] + e.get('width', ICON_WIDTH) / 2.0


def _cy(e):
    return e['y'] + e.get('height', ICON_HEIGHT) / 2.0


# ---- parseo ----

def test_extract_none_gives_empty():
    assert extract_constraints({}) == []
    assert extract_constraints({'constraints': None}) == []


def test_extract_valid():
    data = {'constraints': [
        {'align': ['a', 'b'], 'axis': 'x'},
        {'near': ['c', 'd']},
        {'avoid': ['e', 'f']},
    ]}
    cs = extract_constraints(data)
    assert [c['kind'] for c in cs] == ['align', 'near', 'avoid']
    assert cs[0]['axis'] == 'x'
    assert cs[1]['axis'] == 'x'          # default


def test_extract_skips_invalid():
    data = {'constraints': [
        {'align': ['solo']},              # <2 ids → descartada
        {'frobnicate': ['a', 'b']},        # tipo inválido → descartada
        {'align': ['a', 'b']},             # válida
    ]}
    assert len(extract_constraints(data)) == 1


# ---- semántica ----

def test_align_x_gives_common_column():
    els = [_el('a', 0, 0), _el('b', 100, 50), _el('c', 200, 100)]
    L = _layout(els)
    apply_constraints(L, [{'kind': 'align', 'ids': ['a', 'b', 'c'], 'axis': 'x'}])
    xs = [_cx(e) for e in els]
    assert max(xs) - min(xs) < 0.01       # misma X


def test_align_y_gives_common_row():
    els = [_el('a', 0, 0), _el('b', 100, 80)]
    L = _layout(els)
    apply_constraints(L, [{'kind': 'align', 'ids': ['a', 'b'], 'axis': 'y'}])
    assert abs(_cy(els[0]) - _cy(els[1])) < 0.01


def test_near_reduces_spread():
    els = [_el('a', 0, 0), _el('b', 300, 0), _el('c', 600, 0)]
    L = _layout(els)
    before = max(_cx(e) for e in els) - min(_cx(e) for e in els)
    apply_constraints(L, [{'kind': 'near', 'ids': ['a', 'b', 'c'], 'axis': 'x'}])
    after = max(_cx(e) for e in els) - min(_cx(e) for e in els)
    assert after < before


def test_avoid_separates_overlap():
    # Dos iconos solapados: tras avoid no deben solaparse (por el eje que sea).
    els = [_el('a', 0, 0), _el('b', 10, 10)]
    L = _layout(els)
    apply_constraints(L, [{'kind': 'avoid', 'ids': ['a', 'b'], 'axis': 'x'}])
    a, b = els
    ox = min(a['x'] + ICON_WIDTH, b['x'] + ICON_WIDTH) - max(a['x'], b['x'])
    oy = min(a['y'] + ICON_HEIGHT, b['y'] + ICON_HEIGHT) - max(a['y'], b['y'])
    assert not (ox > 0 and oy > 0)        # ya no se solapan (algún eje separado)


# ---- integración ----

def test_demo_diagram_aligns_via_engine():
    from AlmaGag.layout.engine import LayoutEngine
    with open('docs/diagrams/gags/constraints-demo.sdjf') as f:
        data = json.load(f)
    L = Layout(elements=data['elements'], connections=data['connections'],
               canvas=data['canvas'])
    L._diagram_name = 'x'
    L._areas = L._roles = L._lanes = None
    L._layout_view = 'flow'
    L._constraints = extract_constraints(data)
    out = LayoutEngine(strategy='auto').optimize(L)
    by = {e['id']: e for e in out.elements}
    ys = [_cy(by[i]) for i in ('web1', 'web2', 'web3')]
    assert max(ys) - min(ys) < 0.5        # align y se mantiene tras el motor
