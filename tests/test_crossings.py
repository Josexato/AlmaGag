"""
Métrica de cruces (rescate ③ desde LAF) — `AlmaGag.layout.metrics.count_crossings`.

Cubre la geometría (test de orientación) y el contrato de la métrica: ignora
self-loops, extremos no posicionados y pares que comparten nodo (concurrencia en
un hub NO es cruce). Incluye una prueba de calidad comparativa: para un flujo
dirigido, hier debe cruzar ≤ que AUTO (hier minimiza cruces por diseño).
"""

import subprocess
import sys

import pytest

from AlmaGag.layout.layout import Layout
from AlmaGag.layout.metrics import count_crossings, segments_intersect
from AlmaGag.config import ICON_WIDTH, ICON_HEIGHT


def _elem(eid, x, y):
    return {'id': eid, 'x': x, 'y': y}


def _layout(elements, connections):
    return Layout(elements=elements, connections=connections,
                  canvas={'width': 1000, 'height': 1000})


# ---- geometría ----

def test_segments_cross():
    assert segments_intersect((0, 0), (10, 10), (0, 10), (10, 0))


def test_segments_disjoint():
    assert not segments_intersect((0, 0), (1, 1), (5, 5), (6, 6))


def test_segments_parallel():
    assert not segments_intersect((0, 0), (10, 0), (0, 5), (10, 5))


# ---- count_crossings ----

def test_linear_chain_has_no_crossings():
    # A - B - C alineados: ninguna arista cruza.
    els = [_elem('A', 0, 0), _elem('B', 100, 0), _elem('C', 200, 0)]
    conns = [{'from': 'A', 'to': 'B'}, {'from': 'B', 'to': 'C'}]
    assert count_crossings(_layout(els, conns)) == 0


def test_x_shape_has_one_crossing():
    # A->B y C->D forman una X.
    els = [_elem('A', 0, 0), _elem('B', 200, 200),
           _elem('C', 200, 0), _elem('D', 0, 200)]
    conns = [{'from': 'A', 'to': 'B'}, {'from': 'C', 'to': 'D'}]
    assert count_crossings(_layout(els, conns)) == 1


def test_shared_hub_endpoint_is_not_a_crossing():
    # Abanico desde un hub: aristas que comparten origen se tocan en el nodo.
    els = [_elem('H', 100, 0), _elem('A', 0, 200),
           _elem('B', 100, 200), _elem('C', 200, 200)]
    conns = [{'from': 'H', 'to': 'A'}, {'from': 'H', 'to': 'B'}, {'from': 'H', 'to': 'C'}]
    assert count_crossings(_layout(els, conns)) == 0


def test_self_loop_and_unpositioned_are_ignored():
    els = [_elem('A', 0, 0), _elem('B', 100, 100)]  # C sin posición
    conns = [
        {'from': 'A', 'to': 'A'},        # self-loop → ignorado
        {'from': 'A', 'to': 'C'},        # C no posicionado → ignorado
        {'from': 'A', 'to': 'B'},
    ]
    assert count_crossings(_layout(els, conns)) == 0


def test_is_deterministic():
    els = [_elem('A', 0, 0), _elem('B', 200, 200),
           _elem('C', 200, 0), _elem('D', 0, 200)]
    conns = [{'from': 'A', 'to': 'B'}, {'from': 'C', 'to': 'D'}]
    L = _layout(els, conns)
    assert count_crossings(L) == count_crossings(L)


# ---- calidad comparativa sobre un flujo real ----

def _render_and_count(algorithm):
    """Renderiza 14-stresstest con el algoritmo dado y cuenta cruces del final."""
    from AlmaGag.layout import Layout as _L  # noqa
    import json
    from AlmaGag.layout.engine import LayoutEngine

    with open('docs/diagrams/gags/14-stresstest.sdjf') as f:
        data = json.load(f)
    layout = Layout(elements=data['elements'], connections=data['connections'],
                    canvas=data.get('canvas', {'width': 800, 'height': 600}))
    layout._diagram_name = '14-stresstest'
    layout._areas = data.get('areas')
    layout._roles = data.get('roles')
    layout._lanes = data.get('lanes')
    layout._layout_view = 'flow'
    engine = LayoutEngine(strategy=algorithm)
    out = engine.optimize(layout)
    return count_crossings(out)


def test_hier_crosses_no_more_than_auto_on_flow():
    # hier minimiza cruces por diseño (niveles+columnas); en un flujo dirigido
    # no debería cruzar más que el placement general de AUTO.
    hier = _render_and_count('hier')
    auto = _render_and_count('auto')
    assert hier <= auto, f"hier={hier} debería cruzar ≤ auto={auto}"
