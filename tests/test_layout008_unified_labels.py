"""WISH-LAYOUT-008 — un solo optimizador de etiquetas: el renderer dibuja
la verdad del layout (label_positions / connection_labels) TAL CUAL; la
única optimización es la pasada global §P61 en la etapa de layout, que
ahora cubre también elementos LIBRES y siembra la verdad que falte."""

import json
import re

import pytest

from AlmaGag.layout import Layout
from AlmaGag.layout.geometry import GeometryCalculator
from AlmaGag.layout.strategies.auto.anticollision import (
    global_label_anticollision, seed_label_truth)
from AlmaGag.layout.strategies.auto.auto_renderer import AutoSVGRenderer


def _render(layout, tmp_path, name='out.svg'):
    out = tmp_path / name
    AutoSVGRenderer(GeometryCalculator()).render(layout, str(out))
    return out.read_text()


def _texts(svg):
    """[(x, y, contenido)] de cada <text> no-halo del SVG."""
    out = []
    for m in re.finditer(r'<text([^>]*)>([^<]*)</text>', svg):
        attrs, content = m.group(1), m.group(2)
        if 'ag-text-halo' in attrs:
            continue
        x = float(re.search(r'x="([-\d.]+)"', attrs).group(1))
        y = float(re.search(r'y="([-\d.]+)"', attrs).group(1))
        out.append((x, y, content))
    return out


def test_renderer_draws_stored_element_position(tmp_path):
    """La posición ALMACENADA (aunque no sea la canónica) es la dibujada."""
    L = Layout(elements=[{'id': 'a', 'type': 'server', 'label': 'Nodo A',
                          'x': 100, 'y': 100}],
               connections=[], canvas={'width': 400, 'height': 300})
    L.label_positions = {'a': (250.0, 77.0, 'start', 'right')}
    svg = _render(L, tmp_path)
    assert any(x == 250.0 and y == 77.0 and t == 'Nodo A'
               for x, y, t in _texts(svg))


def test_renderer_draws_stored_connection_center(tmp_path):
    """El rótulo de conexión se dibuja desde connection_labels (cy-10),
    exactamente donde la pasada global lo midió."""
    els = [{'id': 'a', 'type': 'server', 'label': '', 'x': 0, 'y': 0},
           {'id': 'b', 'type': 'server', 'label': '', 'x': 200, 'y': 0}]
    L = Layout(elements=els,
               connections=[{'from': 'a', 'to': 'b', 'label': 'enlace'}],
               canvas={'width': 400, 'height': 300})
    L.connection_labels = {'a->b': (150.0, 90.0)}
    svg = _render(L, tmp_path)
    assert any(x == 150.0 and y == 80.0 and t == 'enlace'
               for x, y, t in _texts(svg))


def test_global_pass_covers_free_elements():
    """Dos elementos LIBRES con etiquetas fundidas: la pasada global (antes
    sólo miembros contenidos) ahora los separa."""
    geo = GeometryCalculator()
    els = [{'id': 'a', 'type': 'server', 'label': 'Etiqueta larguisima A',
            'x': 100, 'y': 100},
           {'id': 'b', 'type': 'server', 'label': 'Etiqueta larguisima B',
            'x': 190, 'y': 100}]
    L = Layout(elements=els, connections=[],
               canvas={'width': 800, 'height': 600})
    seed_label_truth(L, geo)
    a0 = geo.get_label_bbox_stored(els[0], L.label_positions['a'])
    b0 = geo.get_label_bbox_stored(els[1], L.label_positions['b'])
    assert not (a0[2] < b0[0] or b0[2] < a0[0])      # fundidas al sembrar
    moved = global_label_anticollision(L, geo)
    assert moved > 0
    a1 = geo.get_label_bbox_stored(els[0], L.label_positions['a'])
    b1 = geo.get_label_bbox_stored(els[1], L.label_positions['b'])
    assert (a1[2] < b1[0] or b1[2] < a1[0]
            or a1[3] < b1[1] or b1[3] < a1[1])       # separadas al salir


def test_seed_honors_label_position_preference():
    """La siembra respeta `label_position` (§F18 en hier)."""
    geo = GeometryCalculator()
    e = {'id': 'a', 'type': 'server', 'label': 'X', 'x': 100, 'y': 100,
         'label_position': 'right'}
    L = Layout(elements=[e], connections=[],
               canvas={'width': 400, 'height': 300})
    seed_label_truth(L, geo)
    assert L.label_positions['a'] == geo.get_text_coords(e, 'right', 1)


def test_seed_skips_grouped_views():
    """En vistas agrupadas (§I27/§I28) la etiqueta de nodo es estructural
    (centrada, draw_area_node_labels): no se siembra ni se reubica."""
    L = Layout(elements=[{'id': 'a', 'type': 'server', 'label': 'X',
                          'x': 0, 'y': 0}],
               connections=[], canvas={'width': 400, 'height': 300})
    L.areas = [{'id': 'f1', 'label': 'F1'}]
    seed_label_truth(L, GeometryCalculator())
    assert L.label_positions == {}


def test_hier_flow_ships_label_truth(tmp_path):
    """Un diagrama hier (decision) sale del optimize con la verdad sembrada:
    label_positions para todo elemento etiquetado y medición almacenada."""
    from AlmaGag.generator import select_strategy
    from AlmaGag.layout.engine import LayoutEngine
    d = json.load(open('docs/diagrams/gags/es-primo.gag'))
    L = Layout(elements=d['elements'], connections=d['connections'],
               canvas={'width': 1400, 'height': 900})
    L._strategy = select_strategy(d, None)
    out = LayoutEngine(verbose=False, strategy=None).optimize(L)
    assert getattr(out, '_measure_stored_labels', False)
    for e in out.elements:
        if e.get('label') and 'contains' not in e and 'x' in e:
            assert e['id'] in out.label_positions
