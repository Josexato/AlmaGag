"""
H6 — tres contadores separados (edge_x_edge / edge_x_node / label_overlap) en
vez de un único 'colisiones' ambiguo; y log con el nombre del motor real.
"""

import json
import logging

from AlmaGag.layout import Layout
from AlmaGag.layout.engine import LayoutEngine
from AlmaGag.layout.metrics import quality_counters, count_edge_node_overlaps
from AlmaGag.generator import select_strategy, generate_diagram


def _render(path):
    data = json.load(open(path))
    tn = data.get('layout_template')
    if tn:
        from AlmaGag.layout.templates import auto_apply_template, apply_template
        (auto_apply_template if tn == 'auto' else lambda d: apply_template(tn, d))(data)
    L = Layout(elements=data['elements'], connections=data['connections'],
               canvas=data.get('canvas', {}))
    L._strategy = select_strategy(data, 'auto')
    return LayoutEngine(verbose=False, strategy=None).optimize(L)


def test_counters_have_three_keys():
    res = _render('docs/diagrams/gags/05-arquitectura-gag.gag')
    q = quality_counters(res)
    assert set(q) == {'edge_x_edge', 'edge_x_node', 'label_overlap'}
    assert all(isinstance(v, int) and v >= 0 for v in q.values())


def test_arquitectura_no_edge_node_overlaps():
    """Tras H2/H3, 05-arquitectura no tiene aristas sobre icono/contenedor ajeno."""
    res = _render('docs/diagrams/gags/05-arquitectura-gag.gag')
    assert count_edge_node_overlaps(res) == 0


def test_log_names_the_engine(caplog):
    """El log de resultados nombra el motor (hier), no 'AutoLayout' fijo."""
    with caplog.at_level(logging.INFO, logger='AlmaGag'):
        generate_diagram('docs/diagrams/gags/14-stresstest.sdjf',
                         output_file='/tmp/_h6.svg', layout_algorithm='select')
    text = '\n'.join(r.message for r in caplog.records)
    assert '[hier]' in text
    assert 'AutoLayout v2.1' not in text
