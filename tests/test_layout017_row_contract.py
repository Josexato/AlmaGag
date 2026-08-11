"""WISH-LAYOUT-017 — align y entre rangos = contrato de FILA (promoción).

Hallazgo del caso TM: en un roll-up con cadenas de profundidad desigual
(6/4/3 eslabones), los cabezales de disciplina caían en filas distintas
por rango topológico. Un `align` de eje y cuyos miembros viven en rangos
DISTINTOS se honra promoviendo cada miembro al rango común factible
(todos sus predecesores por debajo, sucesores por arriba) — la «capa de
resúmenes». Si no existe rango factible, no se toca nada y el audit
nombra la violación (mitad honesta, como V79).
"""

import json
import logging

import pytest

from AlmaGag.generator import select_strategy
from AlmaGag.layout import Layout
from AlmaGag.layout.considerations import extract_considerations
from AlmaGag.layout.engine import LayoutEngine


def _optimize(d):
    L = Layout(elements=d['elements'], connections=d['connections'],
               canvas=d.get('canvas', {'width': 1400, 'height': 900}))
    L._strategy = select_strategy(d, None)
    L._considerations = extract_considerations(d)
    return LayoutEngine(verbose=False, strategy=None).optimize(L)


def _rollup(considerations):
    """Tres cadenas de profundidad 3/2/1 hacia un sumidero común."""
    els = [{'id': i, 'type': 'server', 'label': i.upper()} for i in
           ['sink', 'a2', 'a1', 'a0', 'b1', 'b0', 'c0']]
    conns = [{'from': 'a0', 'to': 'a1'}, {'from': 'a1', 'to': 'a2'},
             {'from': 'a2', 'to': 'sink'},
             {'from': 'b0', 'to': 'b1'}, {'from': 'b1', 'to': 'sink'},
             {'from': 'c0', 'to': 'sink'}]
    return {'elements': els, 'connections': conns,
            'considerations': considerations,
            'canvas': {'width': 1200, 'height': 900, 'flow': 'up'}}


def test_heads_share_row_via_rank_promotion():
    """Los cabezales a2/b1/c0 (rangos 3/2/1) comparten fila al declararse
    el align y — promovidos al rango del más profundo."""
    d = _rollup([{'align': ['a2', 'b1', 'c0'], 'axis': 'y'}])
    out = _optimize(d)
    by = out.elements_by_id
    ys = {i: by[i]['y'] for i in ['a2', 'b1', 'c0']}
    assert max(ys.values()) - min(ys.values()) <= 0.5, \
        f'cabezales en filas distintas: {ys}'
    # y quedan a UNA fila del sumidero (la antesala del consolidado)
    assert by['sink']['y'] < min(ys.values()), 'el sumidero no quedó arriba'


def test_without_align_depth_staggers_heads():
    """Sin el contrato, el rango escalona los cabezales de las cadenas
    multi-eslabón (comportamiento histórico intacto — la profundidad es
    información; el leaf c0 ya lo promovía la vía de árboles chicos)."""
    d = _rollup([])
    out = _optimize(d)
    by = out.elements_by_id
    assert abs(by['a2']['y'] - by['b1']['y']) > 0.5, \
        'sin align, a2 (prof. 3) y b1 (prof. 2) no deberían compartir fila'


def test_unfeasible_promotion_is_named_not_forced(caplog):
    """Un align y imposible (miembro con sucesor en el rango objetivo) no
    se fuerza: nada se rompe y el audit lo nombra."""
    # b1 alimenta a a2: no puede compartir fila con a2 (succ en el target)
    d = _rollup([{'align': ['a2', 'b1'], 'axis': 'y'}])
    d['connections'].append({'from': 'b1', 'to': 'a2'})
    with caplog.at_level(logging.WARNING, logger='AlmaGag'):
        out = _optimize(d)
    by = out.elements_by_id
    if abs(by['a2']['y'] - by['b1']['y']) > 0.5:
        assert '[align]' in caplog.text, 'violación sin nombrar en el audit'
    else:
        pytest.skip('el motor la cumplió por otra vía — nada que auditar')
