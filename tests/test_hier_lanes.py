"""
Tests de §I28 (carriles por rol) y de la resolución de vista (--view /
layout_view / auto) del algoritmo hier.
"""

import json

from AlmaGag.layout import Layout
from AlmaGag.layout.hier.optimizer import HierLayoutOptimizer
from AlmaGag.config import ICON_WIDTH, ICON_HEIGHT

ADC = 'docs/diagrams/gags/activacion-datacenter.sdjf'


def _data():
    return json.load(open(ADC))


def _optimize(view):
    d = _data()
    L = Layout(elements=[dict(e) for e in d['elements']],
               connections=[dict(c) for c in d['connections']],
               canvas=dict(d['canvas']))
    L._areas = d.get('areas')
    L._roles = d.get('roles')
    L._lanes = d.get('lanes')
    L._layout_view = view
    return HierLayoutOptimizer(verbose=False).optimize(L), d


# ---- §I28 carriles ----

def test_lanes_one_per_used_role():
    r, d = _optimize('lanes')
    used = {e['role'] for e in d['elements'] if e.get('role')}
    assert r.lanes, "debería exponer franjas de carril"
    lane_ids = {s['id'] for s in r.lanes}
    assert used <= lane_ids, f"faltan carriles para roles {used - lane_ids}"


def test_nodes_in_their_role_lane():
    """§I28: cada nodo cae en la banda X del carril de su rol."""
    r, d = _optimize('lanes')
    strip = {s['id']: s for s in r.lanes}
    for e in r.elements:
        if 'x' not in e or not e.get('role'):
            continue
        s = strip[e['role']]
        cx = e['x'] + ICON_WIDTH / 2
        assert s['x'] <= cx <= s['x'] + s['w'], \
            f"{e['id']} (rol {e['role']}) fuera de su carril"


def test_lanes_flow_runs_vertical():
    """§I28: el flujo corre en Y (nivel), los carriles fijan X."""
    r, _ = _optimize('lanes')
    ys = [e['y'] for e in r.elements if 'y' in e]
    assert max(ys) - min(ys) > 500, "el flujo debería desarrollarse en Y"
    # más alto que ancho (vista de responsabilidad)
    assert r.canvas['height'] > r.canvas['width']


def test_lanes_derived_from_role_without_explicit_lanes():
    """Sin `lanes` explícito, los carriles se derivan del campo `role`."""
    r, d = _optimize('lanes')
    assert not d.get('lanes')          # el SDJF no declara lanes
    assert len(r.lanes) >= len({e['role'] for e in d['elements'] if e.get('role')})


# ---- resolución de vista ----

def test_view_dispatch_areas_vs_lanes_vs_flow():
    """La misma data produce 3 layouts según la vista pedida."""
    ra, _ = _optimize('areas')
    rl, _ = _optimize('lanes')
    rf, _ = _optimize('flow')
    assert getattr(ra, 'areas', None) and not getattr(ra, 'lanes', None)
    assert getattr(rl, 'lanes', None) and not getattr(rl, 'areas', None)
    assert not getattr(rf, 'areas', None) and not getattr(rf, 'lanes', None)
    # areas ancha, lanes alta, flow tira
    assert ra.canvas['width'] > ra.canvas['height']
    assert rl.canvas['height'] > rl.canvas['width']


def test_flow_view_ignores_areas():
    """§view 'flow' ignora las `areas` declaradas y hace layout plano."""
    r, _ = _optimize('flow')
    assert getattr(r, 'areas', None) is None
