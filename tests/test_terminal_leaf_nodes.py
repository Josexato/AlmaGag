#!/usr/bin/env python3
"""
Tests for leaf and terminal leaf detection in StructureAnalyzer.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from AlmaGag.layout.laf.structure_analyzer import StructureAnalyzer


class MockLayout:
    """Minimal layout mock for testing StructureAnalyzer."""

    def __init__(self, elements, connections):
        self.elements = elements
        self.connections = connections
        self.elements_by_id = {e['id']: e for e in elements}


def _analyze(elements, connections):
    analyzer = StructureAnalyzer(debug=False)
    layout = MockLayout(elements=elements, connections=connections)
    return analyzer.analyze(layout)


def test_terminal_leaf_chain():
    """A -> B -> C: C is a terminal leaf."""
    info = _analyze(
        elements=[{'id': 'A'}, {'id': 'B'}, {'id': 'C'}],
        connections=[
            {'from': 'A', 'to': 'B'},
            {'from': 'B', 'to': 'C'},
        ],
    )

    assert info.leaf_nodes == {'C'}
    assert info.terminal_leaf_nodes == {'C'}


def test_leaf_not_terminal_when_parent_has_non_leaf_sibling():
    """P -> L and P -> X -> Y: L is leaf but NOT terminal (X is non-leaf sibling)."""
    info = _analyze(
        elements=[{'id': 'P'}, {'id': 'L'}, {'id': 'X'}, {'id': 'Y'}],
        connections=[
            {'from': 'P', 'to': 'L'},
            {'from': 'P', 'to': 'X'},
            {'from': 'X', 'to': 'Y'},
        ],
    )

    assert 'L' in info.leaf_nodes
    assert 'L' not in info.terminal_leaf_nodes


def test_terminal_leaf_with_multiple_parents_no_active_siblings():
    """P1 -> L and P2 -> L with no active sibling branches: L is terminal."""
    info = _analyze(
        elements=[{'id': 'P1'}, {'id': 'P2'}, {'id': 'L'}, {'id': 'A'}, {'id': 'B'}],
        connections=[
            {'from': 'P1', 'to': 'L'},
            {'from': 'P2', 'to': 'L'},
            {'from': 'P1', 'to': 'A'},
            {'from': 'P2', 'to': 'B'},
        ],
    )

    # A and B are leaves, so L remains terminal
    assert 'L' in info.leaf_nodes
    assert 'L' in info.terminal_leaf_nodes


def test_leaf_not_terminal_with_multiple_parents_and_active_branch():
    """One predecessor has an alternate non-leaf branch, so leaf is not terminal."""
    info = _analyze(
        elements=[
            {'id': 'P1'}, {'id': 'P2'}, {'id': 'L'}, {'id': 'X'}, {'id': 'Y'}, {'id': 'Z'}
        ],
        connections=[
            {'from': 'P1', 'to': 'L'},
            {'from': 'P2', 'to': 'L'},
            {'from': 'P1', 'to': 'X'},
            {'from': 'X', 'to': 'Y'},
            {'from': 'P2', 'to': 'Z'},
        ],
    )

    assert 'L' in info.leaf_nodes
    assert 'L' not in info.terminal_leaf_nodes
