"""BUGS-LAYOUT-015 — ningún par de iconos montados sobrevive al layout.

Censo del contador BUGS-LOG-004: c21 (satélites gemelos de hier en la
posición EXACTA), 05 y 06 (montajes de AUTO). Dos capas: §A2 escalona
satélites hermanos, y separate_overlapping_icons es la red de seguridad
de AUTO antes del ruteo definitivo.
"""

import logging

from AlmaGag.config import ICON_WIDTH, ICON_HEIGHT
from AlmaGag.layout import Layout
from AlmaGag.layout.strategies.auto.anticollision import (
    separate_overlapping_icons)


def _solape(a, b):
    return (min(a['x'] + ICON_WIDTH, b['x'] + ICON_WIDTH) > max(a['x'], b['x'])
            and min(a['y'] + ICON_HEIGHT, b['y'] + ICON_HEIGHT)
            > max(a['y'], b['y']))


def test_red_de_seguridad_separa_el_montaje_exacto(caplog):
    L = Layout(
        elements=[{'id': 'a', 'label': 'A', 'x': 100, 'y': 50},
                  {'id': 'b', 'label': 'B', 'x': 100, 'y': 50}],
        connections=[{'from': 'a', 'to': 'b'}],
        canvas={'width': 600, 'height': 300})
    with caplog.at_level(logging.WARNING, logger='AlmaGag'):
        assert separate_overlapping_icons(L) >= 1
    a, b = L.elements
    assert not _solape(a, b), 'siguen montados'
    assert 'iconos montados' in caplog.text, 'el empujón no quedó nombrado'


def test_satelites_hermanos_de_hier_no_se_montan():
    """c21 mínimo: dos hojas del mismo padre dentro de un ciclo (hier)."""
    from AlmaGag.layout.strategies.hier.leveling import compute_levels
    from AlmaGag.layout.strategies.hier.columns import compute_columns
    els = [{'id': i, 'label': i} for i in
           ('app', 'cola', 'mon', 'bd', 'cache')]
    conns = [{'from': 'app', 'to': 'cola'}, {'from': 'cola', 'to': 'mon'},
             {'from': 'mon', 'to': 'app'}, {'from': 'app', 'to': 'bd'},
             {'from': 'app', 'to': 'cache'}]
    lv = compute_levels(els, conns)
    assert set(lv.satellites) == {'bd', 'cache'}
    cols, _ = compute_columns(lv, els, conns)
    assert cols['bd'] != cols['cache'], \
        'satélites hermanos en la misma columna otra vez'


def test_contenedores_y_sus_hijos_quedan_fuera():
    """La geometría de contenedores es del container_calculator — la red
    de seguridad no los toca aunque se solapen."""
    L = Layout(
        elements=[{'id': 'c1', 'label': 'C', 'x': 0, 'y': 0,
                   'width': 300, 'height': 200, 'contains': ['h1']},
                  {'id': 'h1', 'label': 'H', 'x': 50, 'y': 50},
                  {'id': 'h2', 'label': 'H2', 'x': 50, 'y': 50,
                   'contains': []}],
        connections=[],
        canvas={'width': 600, 'height': 300})
    L.elements[2].pop('contains')
    h1_antes = dict(L.elements[1])
    separate_overlapping_icons(L)
    assert (L.elements[1]['x'], L.elements[1]['y']) == \
        (h1_antes['x'], h1_antes['y']), 'movió a un hijo de contenedor'
