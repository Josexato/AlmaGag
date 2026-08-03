"""WISH-LAYOUT-009 — pitch label-aware: el espaciado de filas/grillas
considera el ancho de la ETIQUETA, no sólo del icono, en TODA grilla (antes
sólo en las de ≤2 columnas) y en las bandas. Invariantes que el crecimiento
debe respetar: contención P59, contenedores sin solape (aun sin elementos
libres) y rutas ortogonales que no atraviesan iconos ajenos."""

import json

import pytest

from AlmaGag.layout import Layout
from AlmaGag.layout.engine import LayoutEngine
from AlmaGag.layout.geometry import GeometryCalculator
from AlmaGag.utils import extract_item_id

LONG = 'Etiqueta larga de tres palabras'      # ~31 chars ≈ 217px > 80px icono


def _optimize(d):
    L = Layout(elements=d['elements'], connections=d['connections'],
               canvas={'width': 1400, 'height': 900})
    L._strategy = 'auto'
    return LayoutEngine(verbose=False, strategy='auto').optimize(L)


def test_wide_grid_pitch_fits_labels():
    """Grilla ANCHA (3+ columnas): las etiquetas sembradas de hijos vecinos
    no se funden — la celda se ensancha al label (antes sólo en ≤2 cols)."""
    n = 9
    els = [{'id': 'box', 'type': 'area', 'label': 'Caja',
            'contains': [f'e{i}' for i in range(n)]}]
    els += [{'id': f'e{i}', 'type': 'server', 'label': f'{LONG} {i}'}
            for i in range(n)]
    out = _optimize({'elements': els, 'connections': []})
    geo = GeometryCalculator()
    by = out.elements_by_id
    boxes = {}
    for i in range(n):
        e = by[f'e{i}']
        pos = out.label_positions.get(e['id'])
        assert pos is not None
        boxes[e['id']] = geo.get_label_bbox_stored(e, pos)
    ids = sorted(boxes, key=lambda k: (boxes[k][1], boxes[k][0]))
    for i, a in enumerate(ids):
        for b in ids[i + 1:]:
            A, B = boxes[a], boxes[b]
            assert (A[2] <= B[0] or B[2] <= A[0]
                    or A[3] <= B[1] or B[3] <= A[1]), \
                f'{a} y {b} fundidas: {A} vs {B}'


def test_band_children_stay_inside():
    """El avance de una band es por hijo (ancho del label) y la caja cubre
    la extensión REAL — ningún icono se sale (regresión del fixture minero:
    energia_cliente fuera de z_externos)."""
    els = [{'id': 'band', 'type': 'area', 'label': 'Banda', 'shape': 'band',
            'contains': ['a', 'b', 'c']},
           {'id': 'a', 'type': 'server', 'label': LONG},
           {'id': 'b', 'type': 'server', 'label': LONG + ' bis'},
           {'id': 'c', 'type': 'server', 'label': LONG + ' tris'}]
    out = _optimize({'elements': els, 'connections': []})
    band = out.elements_by_id['band']
    bx1, by1 = band['x'], band['y']
    bx2, by2 = bx1 + band['width'], by1 + band['height']
    for cid in ('a', 'b', 'c'):
        e = out.elements_by_id[cid]
        assert bx1 <= e['x'] and e['x'] + e.get('width', 80) <= bx2 + 0.5, \
            f'{cid} fuera de la banda'


def test_container_overlap_resolution_without_free_elements():
    """La resolución contenedor-contenedor corre AUNQUE no haya elementos
    libres (el early-return anterior dejaba montado un diagrama 100%
    seccionado, p. ej. template dashboard)."""
    from AlmaGag.layout.strategies.auto.positioner import AutoLayoutPositioner
    els = [{'id': 'c1', 'type': 'area', 'label': 'Uno', 'contains': ['a'],
            'x': 100, 'y': 100, 'width': 300, 'height': 200},
           {'id': 'c2', 'type': 'area', 'label': 'Dos', 'contains': ['b'],
            'x': 250, 'y': 150, 'width': 300, 'height': 200},
           {'id': 'a', 'type': 'server', 'label': 'A', 'x': 150, 'y': 180},
           {'id': 'b', 'type': 'server', 'label': 'B', 'x': 300, 'y': 220}]
    L = Layout(elements=els, connections=[],
               canvas={'width': 900, 'height': 900})
    pos = AutoLayoutPositioner.__new__(AutoLayoutPositioner)
    from AlmaGag.layout.sizing import SizingCalculator
    pos.sizing = SizingCalculator()
    pos.recalculate_positions_with_expanded_containers(L)
    c1, c2 = L.elements_by_id['c1'], L.elements_by_id['c2']
    ov_x = min(c1['x'] + c1['width'], c2['x'] + c2['width']) - max(c1['x'], c2['x'])
    ov_y = min(c1['y'] + c1['height'], c2['y'] + c2['height']) - max(c1['y'], c2['y'])
    assert ov_x <= 0 or ov_y <= 0, 'contenedores siguen montados'


def test_mina_tower_row_labels_apart():
    """Caso testigo del ticket: la fila de torres del fixture minero — las
    etiquetas de las estaciones ya no se funden en racimo (quedan ≤2 pares
    con solape, antes ~5)."""
    d = json.load(open('docs/diagrams/gags/mina-arquitectura-fisica.sdjf'))
    from AlmaGag.generator import select_strategy
    L = Layout(elements=d['elements'], connections=d['connections'],
               canvas={'width': 1400, 'height': 900})
    L._strategy = select_strategy(d, 'auto')
    out = LayoutEngine(verbose=False, strategy=None).optimize(L)
    geo = GeometryCalculator()
    by = out.elements_by_id
    est = [by[e] for e in by if e.startswith('est') and by[e].get('label')
           and e in out.label_positions]
    boxes = [geo.get_label_bbox_stored(e, out.label_positions[e['id']])
             for e in est]
    fused = 0
    for i, A in enumerate(boxes):
        for B in boxes[i + 1:]:
            if not (A[2] <= B[0] or B[2] <= A[0]
                    or A[3] <= B[1] or B[3] <= A[1]):
                fused += 1
    assert fused <= 2, f'{fused} pares de estaciones fundidos'
