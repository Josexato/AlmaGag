"""WISH-DRAW-002 — flujos de información resaltados (capa de anotación)."""

import json
import logging

import pytest

from AlmaGag.draw.primitives.flows import (
    FLOW_CLASS, FLOW_PALETTE, build_flow_points, draw_flows)
from AlmaGag.draw.primitives.svg import create_canvas

FIXTURE = 'docs/diagrams/gags/mina-arquitectura-fisica.sdjf'


def _els():
    return {
        'a': {'id': 'a', 'x': 0, 'y': 0},
        'b': {'id': 'b', 'x': 100, 'y': 0},
        'c': {'id': 'c', 'x': 200, 'y': 0},
    }


def test_flow_follows_computed_path_and_reversed():
    conns = [
        {'from': 'a', 'to': 'b',
         'computed_path': {'type': 'polyline',
                           'points': [[40, 25], [40, 90], [140, 90], [140, 25]]}},
        {'from': 'c', 'to': 'b',      # declarada al revés del recorrido
         'computed_path': {'type': 'polyline',
                           'points': [[240, 25], [240, 60], [140, 60]]}},
    ]
    pts = build_flow_points({'id': 'f', 'path': ['a', 'b', 'c']}, _els(), conns)
    assert pts[:4] == [(40, 25), (40, 90), (140, 90), (140, 25)]
    # el tramo b→c usa la conexión c→b INVERTIDA
    assert pts[4:] == [(140, 60), (240, 60), (240, 25)]


def test_flow_falls_back_to_straight_segment():
    pts = build_flow_points({'id': 'f', 'path': ['a', 'c']}, _els(), [])
    assert pts == [(40.0, 25.0), (240.0, 25.0)]


def test_unknown_ids_warn_and_skip(caplog):
    with caplog.at_level(logging.WARNING, logger='AlmaGag'):
        pts = build_flow_points({'id': 'f', 'path': ['a', 'nope', 'c']},
                                _els(), [])
    assert 'nope' in caplog.text
    assert pts == [(40.0, 25.0), (240.0, 25.0)]
    # con <2 dibujables no hay flujo
    assert build_flow_points({'id': 'f', 'path': ['a', 'nope']}, _els(), []) is None


def test_draw_flows_class_palette_and_declared_color(tmp_path):
    dwg = create_canvas(str(tmp_path / 'o.svg'), 400, 200)
    n = draw_flows(dwg, [
        {'id': 'f1', 'path': ['a', 'b']},                       # paleta[0]
        {'id': 'f2', 'path': ['b', 'c'], 'color': '#123456'},   # declarado
        {'id': 'roto', 'path': ['a']},                          # no dibujable
    ], _els(), [])
    assert n == 2
    svg = dwg.tostring()
    assert svg.count(f'class="{FLOW_CLASS}"') == 2
    assert FLOW_PALETTE[0] in svg and '#123456' in svg
    assert 'stroke-opacity="0.3"' in svg


def test_fixture_minero_emits_flows_and_legend(tmp_path):
    """El fixture minero declara 2 flujos: trazos ag-flow + leyenda «Flujos:»,
    y la línea [motor] NO cambia (anotación pura)."""
    from AlmaGag.generator import generate_diagram
    out = tmp_path / 'mina.svg'
    generate_diagram(FIXTURE, output_file=str(out), layout_algorithm='select')
    svg = out.read_text()
    assert svg.count(f'class="{FLOW_CLASS}"') >= 2
    assert 'Flujos:' in svg
    assert 'Datos SCADA' in svg


def test_flows_invisible_for_validator(tmp_path):
    """Diferencial: el conteo de conexiones y las violaciones del audit son
    IDÉNTICOS con y sin flujos — la anotación es invisible para R1-R3."""
    from AlmaGag.generator import generate_diagram
    from AlmaGag.validation.visual_quality import validate_svg
    d = json.load(open(FIXTURE))
    reports = {}
    for tag in ('con', 'sin'):
        if tag == 'sin':
            d.pop('flows', None)
        src = tmp_path / f'{tag}.sdjf'
        src.write_text(json.dumps(d))
        out = tmp_path / f'{tag}.svg'
        generate_diagram(str(src), output_file=str(out),
                         layout_algorithm='select')
        reports[tag] = validate_svg(str(out))
    assert reports['con'].n_connections == reports['sin'].n_connections
    assert len(reports['con'].violations) == len(reports['sin'].violations)


def test_flows_work_in_hier_strategy(tmp_path):
    """El renderer es compartido: un diagrama que resuelve a hier (areas)
    también pinta sus flujos."""
    from AlmaGag.generator import generate_diagram
    d = {
        'elements': [{'id': 'a', 'type': 'server', 'label': 'A'},
                     {'id': 'b', 'type': 'server', 'label': 'B'},
                     {'id': 'c', 'type': 'server', 'label': 'C'}],
        'connections': [{'from': 'a', 'to': 'b', 'direction': 'forward'},
                        {'from': 'b', 'to': 'c', 'direction': 'forward'}],
        'areas': [{'id': 'f1', 'label': 'Fase 1', 'members': ['a', 'b']},
                  {'id': 'f2', 'label': 'Fase 2', 'members': ['c']}],
        'flows': [{'id': 'w', 'label': 'recorrido', 'path': ['a', 'b', 'c']}],
    }
    src = tmp_path / 'hier.sdjf'
    src.write_text(json.dumps(d))
    out = tmp_path / 'hier.svg'
    generate_diagram(str(src), output_file=str(out), layout_algorithm='select')
    assert f'class="{FLOW_CLASS}"' in out.read_text()
