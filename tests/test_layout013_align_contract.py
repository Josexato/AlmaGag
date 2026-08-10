"""WISH-LAYOUT-013 (V79) — align[] es contrato, como near.

El align de eje x entre rangos distintos (columna de tronco) se honra en
el positioner (mediana, con hueco label-aware); toda violación restante
se NOMBRA en el audit final (`[align] grupo N ...`) — nunca silencio.
"""

import json
import logging

import pytest

from AlmaGag.generator import select_strategy
from AlmaGag.layout import Layout
from AlmaGag.layout.considerations import extract_considerations
from AlmaGag.layout.engine import LayoutEngine

PPTO = 'docs/diagrams/gags/mina-presupuesto.sdjf'


def _optimize(d):
    L = Layout(elements=d['elements'], connections=d['connections'],
               canvas={'width': 1400, 'height': 900})
    L._strategy = select_strategy(d, None)
    L._considerations = extract_considerations(d)
    return LayoutEngine(verbose=False, strategy=None).optimize(L)


def _center(e, axis):
    return (e['x'] + e.get('width', 80) / 2.0 if axis == 'x'
            else e['y'] + e.get('height', 50) / 2.0)


def test_presupuesto_all_aligns_fulfilled():
    """Las 5 alineaciones declaradas se cumplen (desviación ≤1px por
    centros de icono) — incluida la de eje x del tronco, que la vía
    blanda no podía honrar (el artefacto midió 2/5; hoy 5/5)."""
    d = json.load(open(PPTO))
    out = _optimize(d)
    for cons in d['considerations']:
        ids, axis = cons['align'], cons['axis']
        vals = [_center(out.elements_by_id[i], axis) for i in ids]
        assert max(vals) - min(vals) <= 1.0, \
            f'align {axis} {ids} violada: {[round(v) for v in vals]}'


def test_unfulfillable_align_is_named_by_audit(caplog):
    """Un align imposible (misma columna para dos elementos del MISMO
    rango) no se cumple — y el audit lo NOMBRA, nunca silencio."""
    d = {'elements': [{'id': 'a', 'type': 'server', 'label': 'A'},
                      {'id': 'b', 'type': 'server', 'label': 'B'},
                      {'id': 'c', 'type': 'server', 'label': 'C'}],
         'connections': [{'from': 'a', 'to': 'c'}, {'from': 'b', 'to': 'c'}],
         'considerations': [{'align': ['a', 'b'], 'axis': 'x'}]}
    with caplog.at_level(logging.WARNING, logger='AlmaGag'):
        out = _optimize(d)
    va = _center(out.elements_by_id['a'], 'x')
    vb = _center(out.elements_by_id['b'], 'x')
    if abs(va - vb) > 1.0:
        assert '[align]' in caplog.text, \
            'align violada sin aviso del audit'
    else:
        pytest.skip('el motor la cumplió — nada que auditar')
