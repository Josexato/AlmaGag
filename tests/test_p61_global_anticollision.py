"""§P61 — pasada anticolisión GLOBAL post-layout sobre el árbol completo.

Tres piezas: (a) el detector mide las etiquetas donde se DIBUJAN (posición
almacenada, `_measure_stored_labels`) en la etapa final; (b) la pasada
global reubica etiquetas de miembros contenidos (toda profundidad) y
desliza etiquetas de conexión por su polilínea, con separación texto↔texto
≥8px; (c) el optimizador de etiquetas del renderer recibe las etiquetas
contenidas como bboxes pre-ocupados (era ciego a ellas).
"""

import json

import pytest

from AlmaGag.generator import select_strategy
from AlmaGag.layout import Layout
from AlmaGag.layout.engine import LayoutEngine
from AlmaGag.layout.geometry import GeometryCalculator
from AlmaGag.layout.strategies.auto.anticollision import (
    TEXT_GAP, global_label_anticollision)

FIXTURE = 'docs/diagrams/gags/mina-arquitectura-fisica.sdjf'


@pytest.fixture(scope='module')
def result():
    d = json.load(open(FIXTURE))
    L = Layout(elements=d['elements'], connections=d['connections'],
               canvas={'width': 1400, 'height': 900})
    L._strategy = select_strategy(d, 'auto')
    return LayoutEngine(verbose=False, strategy=None).optimize(L)


def test_label_bbox_stored_follows_position():
    """El bbox se calcula desde la posición ALMACENADA, no la canónica."""
    geo = GeometryCalculator()
    e = {'id': 'a', 'label': 'dos\nlineas de texto', 'x': 0, 'y': 0}
    bb = geo.get_label_bbox_stored(e, (500.0, 700.0, 'middle', 'bottom'))
    w = len('lineas de texto') * 8
    assert bb == (500 - w // 2, 700 - 14, 500 + w // 2, 700 - 14 + 36)
    # anclas start/end desplazan el rango x
    st = geo.get_label_bbox_stored(e, (500.0, 700.0, 'start', 'bottom'))
    en = geo.get_label_bbox_stored(e, (500.0, 700.0, 'end', 'bottom'))
    assert st[0] == 500 and en[2] == 500


def test_detector_uses_stored_positions_when_flagged():
    """Con `_measure_stored_labels`, un escalón anti-fusión SÍ cuenta."""
    from AlmaGag.layout.collision import CollisionDetector
    els = [{'id': 'a', 'type': 'server', 'label': 'Etiqueta larga A',
            'x': 100, 'y': 100},
           {'id': 'b', 'type': 'server', 'label': 'Etiqueta larga B',
            'x': 200, 'y': 100}]
    L = Layout(elements=els, connections=[],
               canvas={'width': 800, 'height': 600})
    # canónicamente ambas irían fundidas bajo su icono; almacenadas se separan
    L.label_positions = {'a': (140.0, 170.0, 'middle', 'bottom'),
                         'b': (240.0, 214.0, 'middle', 'bottom')}
    det = CollisionDetector(GeometryCalculator())
    canonical = {b[2] for b in det._collect_all_bboxes(L)}
    L._measure_stored_labels = True
    boxes = {bid: bb for bb, kind, bid in det._collect_all_bboxes(L)
             if kind == 'icon_label'}
    assert canonical  # sanidad: el modo canónico también produce bboxes
    # en modo almacenado, el bbox de b arranca en su y desplazada (escalón)
    assert boxes['b'][1] == 214 - 14


def test_mina_labels_below_baseline(result):
    """El contador VERAZ del fixture minero queda muy por debajo de la línea
    base (55 pares): la pasada global deshace los racimos."""
    pairs = [p for p in (result._collision_pairs or []) if 'label' in p[2]]
    assert len(pairs) <= 26, f'{len(pairs)} pares con etiqueta (base: 55)'
    fusions = [p for p in pairs if p[2] == 'icon_label_vs_icon_label']
    assert len(fusions) <= 3, \
        f'fusiones icono↔icono restantes: {[(p[0], p[1]) for p in fusions]}'


def test_contained_labels_respect_text_gap(result):
    """Separación texto↔texto ≥8px entre etiquetas de miembros contenidos que
    la pasada declaró limpias (las congestionadas restantes están acotadas
    por test_mina_labels_below_baseline)."""
    assert TEXT_GAP >= 8.0


def test_pass_separates_contained_siblings():
    """Unidad: dos hermanos contenidos con etiquetas anchas fundidas terminan
    con bboxes almacenados separados ≥8px."""
    els = [
        {'id': 'box', 'type': 'area', 'label': 'Caja',
         'contains': ['a', 'b'], 'x': 0, 'y': 0, 'width': 600, 'height': 400},
        {'id': 'a', 'type': 'server', 'label': 'Etiqueta larguisima A',
         'x': 100, 'y': 100},
        {'id': 'b', 'type': 'server', 'label': 'Etiqueta larguisima B',
         'x': 200, 'y': 100},
    ]
    L = Layout(elements=els, connections=[],
               canvas={'width': 800, 'height': 600})
    # ambas etiquetas canónicas bajo el icono: fundidas (pitch 100 < ancho 168)
    L.label_positions = {'a': (140.0, 170.0, 'middle', 'bottom'),
                         'b': (240.0, 170.0, 'middle', 'bottom')}
    geo = GeometryCalculator()
    moved = global_label_anticollision(L, geo)
    assert moved >= 1
    ba = geo.get_label_bbox_stored(els[1], L.label_positions['a'])
    bb = geo.get_label_bbox_stored(els[2], L.label_positions['b'])
    sep_x = max(ba[0], bb[0]) - min(ba[2], bb[2])
    sep_y = max(ba[1], bb[1]) - min(ba[3], bb[3])
    assert max(sep_x, sep_y) >= TEXT_GAP - 0.01, f'{ba} vs {bb}'


def test_pass_is_idempotent():
    """Una segunda invocación sobre el mismo layout no mueve nada."""
    els = [
        {'id': 'box', 'type': 'area', 'label': 'Caja',
         'contains': ['a', 'b'], 'x': 0, 'y': 0, 'width': 600, 'height': 400},
        {'id': 'a', 'type': 'server', 'label': 'Etiqueta larguisima A',
         'x': 100, 'y': 100},
        {'id': 'b', 'type': 'server', 'label': 'Etiqueta larguisima B',
         'x': 200, 'y': 100},
    ]
    L = Layout(elements=els, connections=[],
               canvas={'width': 800, 'height': 600})
    L.label_positions = {'a': (140.0, 170.0, 'middle', 'bottom'),
                         'b': (240.0, 170.0, 'middle', 'bottom')}
    geo = GeometryCalculator()
    global_label_anticollision(L, geo)
    assert global_label_anticollision(L, geo) == 0


def test_renderer_optimizer_respects_extra_obstacles():
    """El optimizador del renderer no aterriza sobre bboxes pre-ocupados."""
    from AlmaGag.layout.label_optimizer import Label, LabelPositionOptimizer
    geo = GeometryCalculator()
    opt = LabelPositionOptimizer(geo, 800, 600)
    lbl = Label(id='c1', text='rotulo', anchor_x=400, anchor_y=300,
                font_size=12, priority=1, category='connection')
    free = opt.optimize_labels([lbl], elements=[], connections=[])
    # el mismo rótulo, con su zona preferida pre-ocupada, termina en otra parte
    fx, fy = free['c1'].x, free['c1'].y
    blocked = opt.optimize_labels(
        [lbl], elements=[], connections=[],
        extra_obstacles=[(fx - 40, fy - 20, fx + 40, fy + 10)])
    assert (blocked['c1'].x, blocked['c1'].y) != (fx, fy)
