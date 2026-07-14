"""
Tests de la vista `matrix` (fase × rol) del algoritmo hier.
"""

import json

from AlmaGag.layout import Layout
from AlmaGag.layout.hier.optimizer import HierLayoutOptimizer
from AlmaGag.config import ICON_WIDTH

ADC = 'docs/diagrams/gags/activacion-datacenter.sdjf'


def _optimize():
    d = json.load(open(ADC))
    L = Layout(elements=[dict(e) for e in d['elements']],
               connections=[dict(c) for c in d['connections']],
               canvas=dict(d['canvas']))
    L._areas = d['areas']
    L._roles = d['roles']
    L._lanes = d.get('lanes')
    L._layout_view = 'matrix'
    return HierLayoutOptimizer(verbose=False).optimize(L), d


def test_matrix_grid_dimensions():
    r, d = _optimize()
    assert getattr(r, 'matrix', None), "debería exponer la grilla matrix"
    assert len(r.matrix['cols']) == len(d['areas'])          # 1 columna por fase
    used = {e['role'] for e in d['elements'] if e.get('role')}
    row_ids = {row['id'] for row in r.matrix['rows']}
    assert used <= row_ids                                   # 1 fila por rol usado


def test_each_node_in_its_phase_role_cell():
    """Cada nodo cae en la celda (columna=fase, fila=rol)."""
    r, d = _optimize()
    col = {c['id']: c for c in r.matrix['cols']}
    row = {x['id']: x for x in r.matrix['rows']}
    phase_of = {m: a['id'] for a in d['areas'] for m in a['members']}
    for e in r.elements:
        if 'x' not in e or not e.get('role'):
            continue
        c = col[phase_of[e['id']]]
        rr = row[e['role']]
        cx = e['x'] + ICON_WIDTH / 2
        assert c['x'] <= cx <= c['x'] + c['w'], f"{e['id']} fuera de su columna"
        assert rr['y'] <= e['y'] <= rr['y'] + rr['h'], f"{e['id']} fuera de su fila"


def test_matrix_requires_areas():
    """Sin `areas`, la vista matrix no se activa (cae a flujo)."""
    d = json.load(open(ADC))
    L = Layout(elements=[dict(e) for e in d['elements']],
               connections=[dict(c) for c in d['connections']],
               canvas=dict(d['canvas']))
    L._areas = None
    L._roles = d['roles']
    L._layout_view = 'matrix'
    r = HierLayoutOptimizer(verbose=False).optimize(L)
    assert getattr(r, 'matrix', None) is None
