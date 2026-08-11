"""§P61 — pasada anticolisión GLOBAL post-layout sobre el árbol completo.

Dos piezas: (a) el detector mide las etiquetas donde se DIBUJAN (posición
almacenada, `_measure_stored_labels`) en la etapa final; (b) la pasada
global reubica etiquetas a toda profundidad (contenidas y, desde
WISH-LAYOUT-008, también libres) y desliza etiquetas de conexión por su
polilínea, con separación texto↔texto ≥8px. El renderer dibuja el
resultado tal cual (tests en test_layout008_unified_labels.py).
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
    # It10-4: el detector mide con las MISMAS constantes que el renderer
    # (TEXT_CHAR_WIDTH/TEXT_LINE_HEIGHT) — los 8/18 rancios escondían
    # solapes reales tras la recalibracion tipografica de la iteracion 9.
    from AlmaGag.config import TEXT_CHAR_WIDTH, TEXT_LINE_HEIGHT
    w = len('lineas de texto') * TEXT_CHAR_WIDTH
    assert bb == (500 - w // 2, 700 - 14, 500 + w // 2,
                  700 - 14 + 2 * TEXT_LINE_HEIGHT)
    # anclas start/end desplazan el rango x
    st = geo.get_label_bbox_stored(e, (500.0, 700.0, 'start', 'bottom'))
    en = geo.get_label_bbox_stored(e, (500.0, 700.0, 'end', 'bottom'))
    assert st[0] == 500 and en[2] == 500


def test_detector_measures_stored_positions():
    """WISH-LAYOUT-008 (medición veraz total): el detector mide SIEMPRE la
    posición ALMACENADA — un escalón anti-fusión cuenta, sin flag alguno."""
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
    boxes = {bid: bb for bb, kind, bid in det._collect_all_bboxes(L)
             if kind == 'icon_label'}
    # el bbox de b arranca en su y desplazada (escalón) — verdad almacenada
    assert boxes['b'][1] == 214 - 14


def test_mina_labels_below_baseline(result):
    """El contador VERAZ del fixture minero queda muy por debajo de la línea
    base (55 pares): la pasada global deshace los racimos."""
    pairs = [p for p in (result._collision_pairs or []) if 'label' in p[2]]
    assert len(pairs) <= 26, f'{len(pairs)} pares con etiqueta (base: 55)'
    fusions = [p for p in pairs if p[2] == 'icon_label_vs_icon_label']
    # tope 3→5 (It10-4): con el detector veraz (char 9.2 / linea 20.6)
    # aparecen 2 fusiones que el estimador rancio de 8/18 no veia —
    # existian visualmente desde la tipografia 16px; mirado en PNG.
    assert len(fusions) <= 5, \
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


def test_auto_renderer_does_not_reoptimize():
    """WISH-LAYOUT-008: el AutoSVGRenderer ya no usa LabelPositionOptimizer —
    la única optimización de etiquetas es la pasada global."""
    import inspect
    from AlmaGag.layout.strategies.auto import auto_renderer
    src = inspect.getsource(auto_renderer)
    assert 'LabelPositionOptimizer' not in src
