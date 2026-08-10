"""WISH-LAYOUT-012 (V78) — `canvas.flow`: la orientación cuenta la historia.

`flow: "up"` invierte los rangos (roll-ups: fuentes en la banda inferior,
sumidero arriba, salidas derivadas como remate). Default `down`
(histórico). `left`/`right` avisan con WARNING y emiten como `down`.
"""

import json
import logging

from AlmaGag.generator import select_strategy
from AlmaGag.layout import Layout
from AlmaGag.layout.engine import LayoutEngine

PPTO = 'docs/diagrams/gags/mina-presupuesto.sdjf'


def _optimize(d, flow=None):
    canvas = {'width': 1400, 'height': 900}
    if flow:
        canvas['flow'] = flow
    L = Layout(elements=d['elements'], connections=d['connections'],
               canvas=canvas)
    L._strategy = select_strategy(d, None)
    return LayoutEngine(verbose=False, strategy=None).optimize(L)


def test_flow_up_puts_sources_below_and_sink_above():
    """Presupuesto con flow:'up': fuentes (mo) en la banda inferior,
    consolidado (resumen) arriba, salidas (fza) como remate superior."""
    d = json.load(open(PPTO))
    out = _optimize(d, flow='up')
    E = out.elements_by_id
    assert E['resumen']['y'] < E['mo']['y'], 'el consolidado no subió'
    assert E['fza']['y'] < E['resumen']['y'], 'las salidas no rematan arriba'
    assert E['pulab']['y'] > E['mo']['y'], 'los recursos no son el cimiento'


def test_flow_down_is_the_exact_mirror():
    """Invertir flow produce el espejo: el ORDEN de rangos se invierte
    exactamente (mismos agrupamientos, lectura opuesta)."""
    d = json.load(open(PPTO))
    up = _optimize(d, flow='up').elements_by_id
    down = _optimize(d, flow='down').elements_by_id
    ids = ('fza', 'resumen', 'constr', 'ppto', 'dppto', 'mo', 'pulab')
    order_up = sorted(ids, key=lambda i: up[i]['y'])
    order_down = sorted(ids, key=lambda i: down[i]['y'])
    assert order_up == list(reversed(order_down))


def test_flow_left_warns_and_renders_down(caplog):
    d = json.load(open(PPTO))
    with caplog.at_level(logging.WARNING, logger='AlmaGag.AutoPositioner'):
        out = _optimize(d, flow='left')
    assert 'canvas.flow' in caplog.text and 'left' in caplog.text
    E = out.elements_by_id
    assert E['resumen']['y'] > E['mo']['y']      # emitió down
