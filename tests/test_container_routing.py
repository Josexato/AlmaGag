"""
H2 — el ruteo trata los contenedores ajenos como obstáculos: ninguna arista
no-relacionada cruza el interior de un contenedor cuando hay canal libre.
"""

import json

from AlmaGag.layout import Layout
from AlmaGag.layout.engine import LayoutEngine
from AlmaGag.generator import select_strategy
from AlmaGag.layout.templates import auto_apply_template, apply_template


def _render(path):
    data = json.load(open(path))
    tn = data.get('layout_template')
    if tn == 'auto':
        auto_apply_template(data)
    elif tn:
        apply_template(tn, data)
    L = Layout(elements=data['elements'], connections=data['connections'],
               canvas=data.get('canvas', {}))
    L._strategy = select_strategy(data, 'auto')
    return LayoutEngine(verbose=False, strategy=None).optimize(L)


def _parent_map(res):
    parent = {}
    for c in res.elements:
        if 'contains' in c:
            for ch in c['contains']:
                cid = ch['id'] if isinstance(ch, dict) else ch
                parent[cid] = c['id']
    return parent


def _seg_in_rect(ax, ay, bx, by, r):
    x1, y1, x2, y2 = r
    if abs(ax - bx) < 0.1:
        return x1 < ax < x2 and min(ay, by) < y2 and max(ay, by) > y1
    if abs(ay - by) < 0.1:
        return y1 < ay < y2 and min(ax, bx) < x2 and max(ax, bx) > x1
    return False


def _container_crossings(res):
    parent = _parent_map(res)
    containers = {
        e['id']: (e['x'], e['y'], e['x'] + e.get('width', 80), e['y'] + e.get('height', 50))
        for e in res.elements if 'contains' in e and 'x' in e
    }
    crosses = 0
    for conn in res.connections:
        cp = conn.get('computed_path')
        if not cp:
            continue
        pts = cp.get('points') or []
        f, t = conn.get('from'), conn.get('to')
        related = {parent.get(f), parent.get(t), f, t}
        for i in range(len(pts) - 1):
            ax, ay = pts[i]
            bx, by = pts[i + 1]
            for cid, r in containers.items():
                if cid in related:
                    continue
                if _seg_in_rect(ax, ay, bx, by, r):
                    crosses += 1
                    break
    return crosses


def test_arquitectura_no_container_crossings():
    """05-arquitectura: 0 aristas ajenas cruzando el interior de un contenedor
    (antes 2; H2 las hace rodear la caja)."""
    res = _render('docs/diagrams/gags/05-arquitectura-gag.gag')
    assert _container_crossings(res) == 0


def test_containers_demo_clean():
    """07-containers: se mantiene en 0 cruces (sin regresión)."""
    res = _render('docs/diagrams/gags/07-containers.sdjf')
    assert _container_crossings(res) == 0
