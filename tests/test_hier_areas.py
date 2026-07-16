"""
Tests de §I27 (áreas por fase), §I29 (conexiones inter-área cruzan el borde) y
§I30 (rol por color + leyenda) del algoritmo hier.
"""

import json

from AlmaGag.layout import Layout
from AlmaGag.layout.strategies.hier.optimizer import HierLayoutOptimizer
from AlmaGag.config import ICON_WIDTH, ICON_HEIGHT

ADC = 'docs/diagrams/gags/activacion-datacenter.sdjf'


def _data():
    return json.load(open(ADC))


def _optimize():
    d = _data()
    L = Layout(elements=d['elements'], connections=d['connections'], canvas=d['canvas'])
    L._diagram_name = 'adc'
    L._areas = d['areas']
    L._roles = d['roles']
    return HierLayoutOptimizer(verbose=False).optimize(L), d


def _area_of(d):
    ao = {}
    for a in d['areas']:
        for m in a['members']:
            ao[m] = a['id']
    return ao


# ---- §I27 áreas ----

def test_one_box_per_declared_area():
    r, d = _optimize()
    labeled = [b for b in r.areas if not b.get('solo')]
    assert len(labeled) == len(d['areas'])
    assert all(b.get('label') for b in labeled)


def test_members_inside_their_box():
    """§I27: cada nodo cae dentro de la caja de su área (con tolerancia)."""
    r, d = _optimize()
    ao = _area_of(d)
    box = {b['id']: b for b in r.areas}
    tol = 2.0
    for e in r.elements:
        if 'x' not in e or e['id'] not in ao:
            continue
        b = box[ao[e['id']]]
        assert b['x'] - tol <= e['x'] and e['x'] + ICON_WIDTH <= b['x'] + b['w'] + tol, \
            f"{e['id']} fuera de {b['id']} en X"
        assert b['y'] - tol <= e['y'] and e['y'] + ICON_HEIGHT <= b['y'] + b['h'] + tol, \
            f"{e['id']} fuera de {b['id']} en Y"


def test_area_order_follows_flow():
    """§I27: las áreas se disponen izquierda→derecha en orden de flujo."""
    r, d = _optimize()
    box = {b['id']: b for b in r.areas}
    xs = [box[a['id']]['x'] for a in d['areas']]
    assert xs == sorted(xs), f"orden de áreas no monótono: {xs}"


# ---- §I29 conexiones inter-área ----

def test_inter_area_edges_marked_and_cross_borders():
    r, d = _optimize()
    ao = _area_of(d)
    inter = [c for c in r.connections
             if ao.get(c['from']) and ao.get(c['to']) and ao[c['from']] != ao[c['to']]]
    assert inter, "debería haber aristas inter-área"
    for c in inter:
        assert c.get('_inter_area'), f"{c['from']}->{c['to']} no marcada inter-área"
        assert c['computed_path']['type'] == 'polyline'


def test_inter_area_edges_dont_cross_third_box():
    """§I29: ningún vértice de una arista inter-área cae DENTRO de una caja que
    no sea la de origen ni la de destino."""
    r, d = _optimize()
    ao = _area_of(d)
    box = {b['id']: b for b in r.areas}
    for c in r.connections:
        if not c.get('_inter_area'):
            continue
        sa, ta = ao[c['from']], ao[c['to']]
        for (px, py) in c['computed_path']['points']:
            for bid, b in box.items():
                if bid in (sa, ta):
                    continue
                inside = (b['x'] < px < b['x'] + b['w'] and b['y'] < py < b['y'] + b['h'])
                assert not inside, f"{c['from']}->{c['to']} cruza la caja {bid}"


# ---- §I30 roles ----

def test_roles_present_and_legend_available():
    r, d = _optimize()
    assert r.roles, "la leyenda de roles debería estar disponible"
    for e in r.elements:
        assert e.get('role') in r.roles, f"{e['id']} sin rol válido"


# ---- §J33 usar el ancho ----

def test_areas_use_width_not_strip():
    r, _ = _optimize()
    assert r.canvas['width'] > r.canvas['height'], "el layout por áreas debe ser ancho"
    assert r.canvas['height'] / r.canvas['width'] <= 3.0
