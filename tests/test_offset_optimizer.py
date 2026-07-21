"""
Optimizador de offsets por bisección (rescate ① desde LAF) —
`AlmaGag.layout.offset_optimizer`.

Verifica el óptimo convexo en casos con solución cerrada conocida.
"""

import math

from AlmaGag.layout.offset_optimizer import optimize_group_offsets, _optimal_offset


def test_align_to_single_neighbor():
    # Un nodo en x=0 conectado a un fijo en x=100 (misma Y): óptimo = alinear.
    groups = {'g': ['A'], 'fixed': ['B']}
    pos = {'A': (0.0, 0.0), 'B': (100.0, 0.0)}
    adj = {'A': [('B', 1.0)], 'B': []}
    offs = optimize_group_offsets(groups, pos, adj)
    assert abs(offs['g'] - 100.0) < 0.05


def test_midpoint_between_two_neighbors():
    # Nodo en x=0 con dos vecinos fijos en x=0 y x=100 (misma Y, peso igual):
    # el mínimo de longitud total cae en el punto medio → offset = 50.
    groups = {'g': ['A'], 'f': ['B', 'C']}
    pos = {'A': (0.0, 0.0), 'B': (0.0, 50.0), 'C': (100.0, 50.0)}
    adj = {'A': [('B', 1.0), ('C', 1.0)], 'B': [], 'C': []}
    offs = optimize_group_offsets(groups, pos, adj)
    assert abs(offs['g'] - 50.0) < 0.5


def test_weighted_pull():
    # Peso 3 hacia x=0 y peso 1 hacia x=100 → el óptimo se sesga hacia x=0.
    groups = {'g': ['A'], 'f': ['B', 'C']}
    pos = {'A': (0.0, 0.0), 'B': (0.0, 40.0), 'C': (100.0, 40.0)}
    adj = {'A': [('B', 3.0), ('C', 1.0)], 'B': [], 'C': []}
    offs = optimize_group_offsets(groups, pos, adj)
    assert 0.0 <= offs['g'] < 50.0


def test_no_cross_group_edges_gives_zero():
    groups = {'g': ['A', 'B']}          # todo intra-grupo
    pos = {'A': (0.0, 0.0), 'B': (10.0, 0.0)}
    adj = {'A': [('B', 1.0)], 'B': [('A', 1.0)]}
    offs = optimize_group_offsets(groups, pos, adj)
    assert offs['g'] == 0.0


def test_optimal_offset_is_convex_minimum():
    # La derivada en el óptimo debe ser ~0 (mínimo de una función convexa).
    terms = [(-30.0, 20.0, 1.0), (70.0, 20.0, 1.0)]
    off = _optimal_offset(terms, 0.0, 20.0)
    d = sum(w * (a + off) / math.hypot(a + off, p) for a, p, w in terms)
    assert abs(d) < 1e-3


def test_is_deterministic():
    groups = {'g1': ['A'], 'g2': ['B'], 'f': ['C']}
    pos = {'A': (0.0, 0.0), 'B': (50.0, 50.0), 'C': (100.0, 100.0)}
    adj = {'A': [('C', 1.0)], 'B': [('C', 1.0)], 'C': []}
    a = optimize_group_offsets(groups, pos, adj)
    b = optimize_group_offsets(groups, pos, adj)
    assert a == b
