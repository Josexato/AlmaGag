"""WISH-DRAW-002 — flujos de información resaltados (capa de anotación)."""

import json
import logging

import pytest

from AlmaGag.draw.primitives.journeys import (
    JOURNEY_CLASS, JOURNEY_PALETTE, JOURNEY_WIDTH, build_journey_lanes,
    build_journey_points, draw_journeys)
from AlmaGag.draw.primitives.svg import create_canvas

FIXTURE = 'docs/diagrams/gags/mina-arquitectura-fisica.sdjf'


def _els():
    return {
        'a': {'id': 'a', 'x': 0, 'y': 0},
        'b': {'id': 'b', 'x': 100, 'y': 0},
        'c': {'id': 'c', 'x': 200, 'y': 0},
    }


def test_journey_follows_computed_path_and_reversed():
    conns = [
        {'from': 'a', 'to': 'b',
         'computed_path': {'type': 'polyline',
                           'points': [[40, 25], [40, 90], [140, 90], [140, 25]]}},
        {'from': 'c', 'to': 'b',      # declarada al revés del recorrido
         'computed_path': {'type': 'polyline',
                           'points': [[240, 25], [240, 60], [140, 60]]}},
    ]
    pts = build_journey_points({'id': 'f', 'path': ['a', 'b', 'c']}, _els(), conns)
    assert pts[:4] == [(40, 25), (40, 90), (140, 90), (140, 25)]
    # el tramo b→c usa la conexión c→b INVERTIDA
    assert pts[4:] == [(140, 60), (240, 60), (240, 25)]


def test_u74_pair_without_connection_is_hard_error():
    """U74/U77: un par consecutivo sin conexión declarada es ValueError —
    se acabó la «cinta recta» silenciosa."""
    with pytest.raises(ValueError, match=r'par \(a, c\).*sin conexión'):
        build_journey_points({'id': 'f', 'path': ['a', 'c']}, _els(), [])


def test_u74_declared_connection_without_computed_path_stays_on_edge():
    """Conexión declarada que se dibuja recta (sin computed_path): el
    resaltador sigue esa misma recta — es la arista, no geometría propia."""
    conns = [{'from': 'a', 'to': 'c'}]
    pts = build_journey_points({'id': 'f', 'path': ['a', 'c']}, _els(), conns)
    assert pts == [(40.0, 25.0), (240.0, 25.0)]


def test_u77_unknown_id_is_hard_error():
    with pytest.raises(ValueError, match=r"id 'nope' del recorrido 'f'"):
        build_journey_points({'id': 'f', 'path': ['a', 'nope', 'c']},
                          _els(), [])


def test_u77_label_mandatory_and_color_repeat_warns(tmp_path, caplog):
    conns = [{'from': 'a', 'to': 'b'}, {'from': 'b', 'to': 'c'}]
    dwg = create_canvas(str(tmp_path / 'o.svg'), 400, 200)
    with pytest.raises(ValueError, match=r"'f1' no declara label"):
        draw_journeys(dwg, [{'id': 'f1', 'path': ['a', 'b']}], _els(), conns)
    with caplog.at_level(logging.WARNING, logger='AlmaGag'):
        n = draw_journeys(dwg, [
            {'id': 'f1', 'label': 'uno', 'color': '#123456',
             'path': ['a', 'b']},
            {'id': 'f2', 'label': 'dos', 'color': '#123456',
             'path': ['b', 'c']},
        ], _els(), conns)
    assert n == 2
    assert 'repite el color' in caplog.text


def test_u75_shared_segment_gets_parallel_lanes():
    """Dos flujos sobre el MISMO tramo: carriles lado a lado (paso =
    JOURNEY_WIDTH, ninguno tapado) aunque lo recorran en sentidos opuestos;
    los tramos exclusivos no se mueven."""
    els = dict(_els())
    els['d'] = {'id': 'd', 'x': 300, 'y': 0}
    conns = [{'from': 'a', 'to': 'b'}, {'from': 'b', 'to': 'c'},
             {'from': 'c', 'to': 'd'}]
    lanes = build_journey_lanes([
        {'id': 'f1', 'label': 'uno', 'path': ['a', 'b', 'c']},
        {'id': 'f2', 'label': 'dos', 'path': ['d', 'c', 'b']},
    ], els, conns)
    (f1, p1), (f2, p2) = lanes
    # tramo exclusivo de f1 (a→b) intacto, sobre la línea original y=25
    assert p1[0] == (40.0, 25.0) and p1[1] == (140.0, 25.0)
    # tramo compartido b↔c: f1 y f2 en carriles opuestos, separados
    # exactamente JOURNEY_WIDTH (cero solape del resaltador)
    y1 = p1[-1][1]
    y2 = p2[-1][1]
    assert abs(y1 - y2) == pytest.approx(JOURNEY_WIDTH)
    assert y1 != 25.0 and y2 != 25.0
    # simetría: ±½ ancho alrededor de la línea original
    assert y1 + y2 == pytest.approx(2 * 25.0)
    # tramo exclusivo de f2 (d→c) intacto
    assert p2[0] == (340.0, 25.0) and p2[1] == (240.0, 25.0)


def test_u75_single_journey_stays_on_the_wire():
    """Un flujo solo no se desplaza: sin tramo compartido no hay carril."""
    conns = [{'from': 'a', 'to': 'b'}]
    lanes = build_journey_lanes(
        [{'id': 'f', 'label': 'x', 'path': ['a', 'b']}], _els(), conns)
    assert lanes[0][1] == [(40.0, 25.0), (140.0, 25.0)]


def test_draw_journeys_class_palette_and_declared_color(tmp_path):
    conns = [{'from': 'a', 'to': 'b'}, {'from': 'b', 'to': 'c'}]
    dwg = create_canvas(str(tmp_path / 'o.svg'), 400, 200)
    n = draw_journeys(dwg, [
        {'id': 'f1', 'label': 'uno', 'path': ['a', 'b']},       # paleta[0]
        {'id': 'f2', 'label': 'dos', 'path': ['b', 'c'],
         'color': '#123456'},                                   # declarado
        {'id': 'roto', 'label': 'x', 'path': ['a']},            # no dibujable
    ], _els(), conns)
    assert n == 2
    svg = dwg.tostring()
    assert svg.count(f'class="{JOURNEY_CLASS}"') == 2
    assert JOURNEY_PALETTE[0] in svg and '#123456' in svg
    assert 'stroke-opacity="0.3"' in svg


def test_fixture_minero_emits_journeys_and_legend(tmp_path):
    """El fixture minero declara 2 flujos: trazos ag-flow + leyenda «Flujos:»,
    y la línea [motor] NO cambia (anotación pura)."""
    from AlmaGag.generator import generate_diagram
    out = tmp_path / 'mina.svg'
    generate_diagram(FIXTURE, output_file=str(out), layout_algorithm='select')
    svg = out.read_text()
    assert svg.count(f'class="{JOURNEY_CLASS}"') >= 2
    assert 'Recorridos:' in svg
    assert 'Datos SCADA' in svg


def test_journeys_invisible_for_validator(tmp_path):
    """Diferencial: el conteo de conexiones y las violaciones del audit son
    IDÉNTICOS con y sin flujos — la anotación es invisible para R1-R3."""
    from AlmaGag.generator import generate_diagram
    from AlmaGag.validation.visual_quality import validate_svg
    d = json.load(open(FIXTURE))
    reports = {}
    for tag in ('con', 'sin'):
        if tag == 'sin':
            d.pop('journeys', None)
        src = tmp_path / f'{tag}.sdjf'
        src.write_text(json.dumps(d))
        out = tmp_path / f'{tag}.svg'
        generate_diagram(str(src), output_file=str(out),
                         layout_algorithm='select')
        reports[tag] = validate_svg(str(out))
    assert reports['con'].n_connections == reports['sin'].n_connections
    assert len(reports['con'].violations) == len(reports['sin'].violations)


def test_journeys_work_in_hier_strategy(tmp_path):
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
        'journeys': [{'id': 'w', 'label': 'recorrido', 'path': ['a', 'b', 'c']}],
    }
    src = tmp_path / 'hier.sdjf'
    src.write_text(json.dumps(d))
    out = tmp_path / 'hier.svg'
    generate_diagram(str(src), output_file=str(out), layout_algorithm='select')
    assert f'class="{JOURNEY_CLASS}"' in out.read_text()
