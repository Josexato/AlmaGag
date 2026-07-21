"""
Consideraciones blandas (rescate ④ desde LAF) — `AlmaGag.layout.considerations`.

Cubre el parseo del schema, la geometría de align/near/avoid, y —lo esencial de
su naturaleza blanda— que una consideración que aumentaría las colisiones CEDE
(la guarda la descarta) en vez de romper el diagrama.
"""

import json

from AlmaGag.layout.layout import Layout
from AlmaGag.layout.considerations import (
    extract_considerations, apply_one, apply_considerations)
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
    assert extract_considerations({}) == []
    assert extract_considerations({'considerations': None}) == []


def test_extract_valid():
    data = {'considerations': [
        {'align': ['a', 'b'], 'axis': 'x'},
        {'near': ['c', 'd']},
        {'avoid': ['e', 'f']},
    ]}
    cs = extract_considerations(data)
    assert [c['kind'] for c in cs] == ['align', 'near', 'avoid']
    assert cs[0]['axis'] == 'x'
    assert cs[1]['axis'] == 'x'          # default


def test_extract_accepts_legacy_constraints_alias():
    data = {'constraints': [{'align': ['a', 'b']}]}
    assert len(extract_considerations(data)) == 1


def test_extract_skips_invalid():
    data = {'considerations': [
        {'align': ['solo']},              # <2 ids → descartada
        {'frobnicate': ['a', 'b']},        # tipo inválido → descartada
        {'align': ['a', 'b']},             # válida
    ]}
    assert len(extract_considerations(data)) == 1


# ---- geometría (apply_one) ----

def test_align_x_gives_common_column():
    els = [_el('a', 0, 0), _el('b', 100, 50), _el('c', 200, 100)]
    L = _layout(els)
    apply_one(L, {'kind': 'align', 'ids': ['a', 'b', 'c'], 'axis': 'x'})
    xs = [_cx(e) for e in els]
    assert max(xs) - min(xs) < 0.01


def test_align_y_gives_common_row():
    els = [_el('a', 0, 0), _el('b', 100, 80)]
    L = _layout(els)
    apply_one(L, {'kind': 'align', 'ids': ['a', 'b'], 'axis': 'y'})
    assert abs(_cy(els[0]) - _cy(els[1])) < 0.01


def test_near_reduces_spread():
    els = [_el('a', 0, 0), _el('b', 300, 0), _el('c', 600, 0)]
    L = _layout(els)
    before = max(_cx(e) for e in els) - min(_cx(e) for e in els)
    apply_one(L, {'kind': 'near', 'ids': ['a', 'b', 'c'], 'axis': 'x'})
    after = max(_cx(e) for e in els) - min(_cx(e) for e in els)
    assert after < before


def test_avoid_separates_overlap():
    els = [_el('a', 0, 0), _el('b', 10, 10)]
    L = _layout(els)
    apply_one(L, {'kind': 'avoid', 'ids': ['a', 'b'], 'axis': 'x'})
    a, b = els
    ox = min(a['x'] + ICON_WIDTH, b['x'] + ICON_WIDTH) - max(a['x'], b['x'])
    oy = min(a['y'] + ICON_HEIGHT, b['y'] + ICON_HEIGHT) - max(a['y'], b['y'])
    assert not (ox > 0 and oy > 0)


# ---- naturaleza BLANDA (guarda) ----

def _count_overlaps(layout):
    """Colisiones simples = pares de iconos cuyas cajas se solapan."""
    els = [e for e in layout.elements if 'x' in e]
    n = 0
    for i in range(len(els)):
        for j in range(i + 1, len(els)):
            a, b = els[i], els[j]
            ox = min(a['x'] + ICON_WIDTH, b['x'] + ICON_WIDTH) - max(a['x'], b['x'])
            oy = min(a['y'] + ICON_HEIGHT, b['y'] + ICON_HEIGHT) - max(a['y'], b['y'])
            if ox > 0 and oy > 0:
                n += 1
    return n


def test_guard_keeps_harmless_consideration():
    els = [_el('a', 0, 0), _el('b', 300, 40)]
    L = _layout(els)
    out, unmet = apply_considerations(
        L, [{'kind': 'align', 'ids': ['a', 'b'], 'axis': 'y'}],
        evaluate=lambda lo: _count_overlaps(lo), reroute=lambda lo: None)
    assert unmet == []                    # no colisiona → se aplica
    by = {e['id']: e for e in out.elements}
    assert abs(_cy(by['a']) - _cy(by['b'])) < 0.01


def test_guard_drops_consideration_that_would_collide():
    # a y b lejos; alinearlos en X *y* en Y los apila → colisión → la 2a cede.
    els = [_el('a', 0, 0), _el('b', 400, 0)]
    L = _layout(els)
    cons = [
        {'kind': 'align', 'ids': ['a', 'b'], 'axis': 'y'},   # inofensiva
        {'kind': 'align', 'ids': ['a', 'b'], 'axis': 'x'},   # los apilaría
    ]
    out, unmet = apply_considerations(
        L, cons, evaluate=lambda lo: _count_overlaps(lo), reroute=lambda lo: None)
    assert len(unmet) == 1 and unmet[0]['axis'] == 'x'   # la que apila cedió
    assert _count_overlaps(out) == 0                     # el diagrama no se rompió


# ---- integración por el motor ----

def test_demo_diagram_soft_via_engine():
    from AlmaGag.layout.engine import LayoutEngine
    with open('docs/diagrams/gags/considerations-demo.sdjf') as f:
        data = json.load(f)
    L = Layout(elements=data['elements'], connections=data['connections'],
               canvas=data['canvas'])
    L._diagram_name = 'x'
    L._areas = L._roles = L._lanes = None
    L._layout_view = 'flow'
    L._considerations = extract_considerations(data)
    out = LayoutEngine(strategy='auto').optimize(L)
    by = {e['id']: e for e in out.elements}
    ys = [_cy(by[i]) for i in ('web1', 'web2', 'web3')]
    xs = [_cx(by[i]) for i in ('web1', 'web2', 'web3')]
    assert max(ys) - min(ys) < 0.5        # align y se honra
    assert max(xs) - min(xs) > 1.0        # align x cede (los apilaría)
