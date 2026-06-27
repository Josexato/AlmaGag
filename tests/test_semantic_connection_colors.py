"""
Tests para color semántico por tipo de conexión (WISH-LAYOUT-007).
"""

import svgwrite

from AlmaGag.draw.primitives.svg import (
    resolve_connection_color,
    setup_arrow_markers,
    SEMANTIC_CONNECTION_COLORS,
)


def test_resolve_color_direct_override():
    assert resolve_connection_color({'color': '#abcdef'}) == '#abcdef'
    assert resolve_connection_color({'color': 'red'}) == 'red'


def test_resolve_color_by_semantic_type():
    assert resolve_connection_color({'semantic_type': 'data_flow'}) == \
        SEMANTIC_CONNECTION_COLORS['data_flow']
    assert resolve_connection_color({'semantic_type': 'sync'}) == \
        SEMANTIC_CONNECTION_COLORS['sync']


def test_resolve_color_precedence_color_over_semantic():
    conn = {'color': 'red', 'semantic_type': 'data_flow'}
    assert resolve_connection_color(conn) == 'red'


def test_resolve_color_none_when_unset():
    assert resolve_connection_color({}) is None
    assert resolve_connection_color({'semantic_type': 'unknown_xyz'}) is None


def test_setup_markers_returns_default_when_no_semantic():
    dwg = svgwrite.Drawing(size=(100, 100))
    conns = [{'from': 'a', 'to': 'b'}]
    result = setup_arrow_markers(dwg, conns, color_connections=False)
    # Sin semantic_type ni color → markers planos (no tupla).
    assert not isinstance(result, tuple)


def test_setup_markers_returns_per_connection_with_semantic():
    dwg = svgwrite.Drawing(size=(100, 100))
    conns = [
        {'from': 'a', 'to': 'b', 'semantic_type': 'data_flow'},
        {'from': 'b', 'to': 'c'},  # sin tipo → negro
    ]
    result = setup_arrow_markers(dwg, conns, color_connections=False)
    assert isinstance(result, tuple)
    _markers, per_conn = result
    assert per_conn[0]['color'] == SEMANTIC_CONNECTION_COLORS['data_flow']
    assert per_conn[1]['color'] == 'black'


def test_color_connections_still_rainbow():
    """El flag --color-connections sigue produciendo paleta arcoíris."""
    dwg = svgwrite.Drawing(size=(100, 100))
    conns = [{'from': 'a', 'to': 'b'}, {'from': 'b', 'to': 'c'}]
    result = setup_arrow_markers(dwg, conns, color_connections=True)
    assert isinstance(result, tuple)
    _markers, per_conn = result
    assert len(per_conn) == 2
    assert per_conn[0]['color'] != per_conn[1]['color']
