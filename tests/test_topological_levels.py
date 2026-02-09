#!/usr/bin/env python3
"""
test_topological_levels.py - Tests for topological level calculation

Validates the "leaf stays in parent level" rule:
- Leaf nodes (outdegree=0) stay at their dominant parent's Base level
- Non-leaf nodes get Base = maxBaseParent + 1 (standard rule)
- Source nodes (no parents) get Base = 0
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


def test_case_a_simple_leaf():
    """
    Case A: A -> B, B is a leaf.
    Expected: Base[A]=0, Base[B]=0 (B stays at parent level, does not go to 1)
    """
    layout = MockLayout(
        elements=[
            {'id': 'A', 'type': 'icon'},
            {'id': 'B', 'type': 'icon'},
        ],
        connections=[
            {'from': 'A', 'to': 'B'},
        ],
    )

    analyzer = StructureAnalyzer(debug=False)
    info = analyzer.analyze(layout)

    assert info.topological_levels['A'] == 0, (
        f"A should be level 0, got {info.topological_levels['A']}"
    )
    assert info.topological_levels['B'] == 0, (
        f"B (leaf) should stay at parent level 0, got {info.topological_levels['B']}"
    )
    print("[PASS] Case A: simple leaf stays at parent level")


def test_case_b_chain_with_leaf():
    """
    Case B: A -> B -> C, C is a leaf.
    Expected: Base[A]=0, Base[B]=1, Base[C]=1 (C stays at B's level)
    """
    layout = MockLayout(
        elements=[
            {'id': 'A', 'type': 'icon'},
            {'id': 'B', 'type': 'icon'},
            {'id': 'C', 'type': 'icon'},
        ],
        connections=[
            {'from': 'A', 'to': 'B'},
            {'from': 'B', 'to': 'C'},
        ],
    )

    analyzer = StructureAnalyzer(debug=False)
    info = analyzer.analyze(layout)

    assert info.topological_levels['A'] == 0, (
        f"A should be level 0, got {info.topological_levels['A']}"
    )
    assert info.topological_levels['B'] == 1, (
        f"B (non-leaf) should be level 1, got {info.topological_levels['B']}"
    )
    assert info.topological_levels['C'] == 1, (
        f"C (leaf) should stay at parent level 1, got {info.topological_levels['C']}"
    )
    print("[PASS] Case B: chain leaf stays at parent level")


def test_case_c_merge_with_leaf():
    """
    Case C: P3 -> V, P4 -> V, V is a leaf.
    P3 and P4 at different levels, V stays at the max parent level.
    """
    # P3 is a source, P4 comes after P3 via an intermediate node
    # P3 -> X -> P4 -> V, P3 -> V
    # So P3=0, X=1 (non-leaf), P4=2 (non-leaf because -> V), wait...
    # Actually P4 -> V makes P4 non-leaf. Let me restructure:
    # Source -> P3 (non-leaf, -> V), Source -> X -> P4 (non-leaf, -> V)
    # P3 -> V, P4 -> V
    layout = MockLayout(
        elements=[
            {'id': 'Source', 'type': 'icon'},
            {'id': 'P3', 'type': 'icon'},
            {'id': 'P4', 'type': 'icon'},
            {'id': 'V', 'type': 'icon'},
        ],
        connections=[
            {'from': 'Source', 'to': 'P3'},
            {'from': 'Source', 'to': 'P4'},
            {'from': 'P3', 'to': 'V'},
            {'from': 'P4', 'to': 'V'},
        ],
    )

    analyzer = StructureAnalyzer(debug=False)
    info = analyzer.analyze(layout)

    # Source=0, P3=1 (non-leaf), P4=1 (non-leaf), V should be max(1,1)=1
    assert info.topological_levels['Source'] == 0, (
        f"Source should be level 0, got {info.topological_levels['Source']}"
    )
    assert info.topological_levels['P3'] == 1, (
        f"P3 (non-leaf) should be level 1, got {info.topological_levels['P3']}"
    )
    assert info.topological_levels['P4'] == 1, (
        f"P4 (non-leaf) should be level 1, got {info.topological_levels['P4']}"
    )
    assert info.topological_levels['V'] == 1, (
        f"V (leaf) should stay at max parent level 1, got {info.topological_levels['V']}"
    )
    print("[PASS] Case C: merge leaf stays at max parent level")


def test_case_c_merge_different_depths():
    """
    Case C variant: parents at different depths, leaf stays at max parent level.
    P3 -> V (P3 at level 1)
    P4 -> V (P4 at level 2)
    V is a leaf -> Base[V] = max(1, 2) = 2
    """
    layout = MockLayout(
        elements=[
            {'id': 'S1', 'type': 'icon'},
            {'id': 'S2', 'type': 'icon'},
            {'id': 'P3', 'type': 'icon'},
            {'id': 'X', 'type': 'icon'},
            {'id': 'P4', 'type': 'icon'},
            {'id': 'V', 'type': 'icon'},
        ],
        connections=[
            {'from': 'S1', 'to': 'P3'},
            {'from': 'S2', 'to': 'X'},
            {'from': 'X', 'to': 'P4'},
            {'from': 'P3', 'to': 'V'},
            {'from': 'P4', 'to': 'V'},
        ],
    )

    analyzer = StructureAnalyzer(debug=False)
    info = analyzer.analyze(layout)

    # S1=0, S2=0, P3=1 (non-leaf), X=1 (non-leaf), P4=2 (non-leaf), V=max(1,2)=2
    assert info.topological_levels['V'] == 2, (
        f"V (leaf) should stay at max parent level 2, got {info.topological_levels['V']}"
    )
    print("[PASS] Case C variant: merge leaf stays at max parent level (different depths)")


def test_non_leaf_still_increments():
    """
    Non-leaf nodes should still increment normally.
    A -> B -> C -> D (D is leaf)
    Expected: A=0, B=1, C=2, D=2
    """
    layout = MockLayout(
        elements=[
            {'id': 'A', 'type': 'icon'},
            {'id': 'B', 'type': 'icon'},
            {'id': 'C', 'type': 'icon'},
            {'id': 'D', 'type': 'icon'},
        ],
        connections=[
            {'from': 'A', 'to': 'B'},
            {'from': 'B', 'to': 'C'},
            {'from': 'C', 'to': 'D'},
        ],
    )

    analyzer = StructureAnalyzer(debug=False)
    info = analyzer.analyze(layout)

    assert info.topological_levels['A'] == 0
    assert info.topological_levels['B'] == 1
    assert info.topological_levels['C'] == 2
    assert info.topological_levels['D'] == 2, (
        f"D (leaf) should stay at parent level 2, got {info.topological_levels['D']}"
    )
    print("[PASS] Non-leaf nodes still increment normally")


def test_source_node_is_leaf():
    """
    Isolated source node (no parents, no children) stays at level 0.
    """
    layout = MockLayout(
        elements=[
            {'id': 'Alone', 'type': 'icon'},
        ],
        connections=[],
    )

    analyzer = StructureAnalyzer(debug=False)
    info = analyzer.analyze(layout)

    assert info.topological_levels['Alone'] == 0, (
        f"Isolated node should be level 0, got {info.topological_levels['Alone']}"
    )
    print("[PASS] Isolated source node stays at level 0")


def test_fan_out_multiple_leaves():
    """
    Fan-out: A -> B, A -> C, A -> D (all leaves)
    Expected: A=0, B=0, C=0, D=0 (all leaves stay at parent level)
    """
    layout = MockLayout(
        elements=[
            {'id': 'A', 'type': 'icon'},
            {'id': 'B', 'type': 'icon'},
            {'id': 'C', 'type': 'icon'},
            {'id': 'D', 'type': 'icon'},
        ],
        connections=[
            {'from': 'A', 'to': 'B'},
            {'from': 'A', 'to': 'C'},
            {'from': 'A', 'to': 'D'},
        ],
    )

    analyzer = StructureAnalyzer(debug=False)
    info = analyzer.analyze(layout)

    assert info.topological_levels['A'] == 0
    assert info.topological_levels['B'] == 0
    assert info.topological_levels['C'] == 0
    assert info.topological_levels['D'] == 0
    print("[PASS] Fan-out: all leaves stay at parent level")


def test_mixed_leaf_and_non_leaf_children():
    """
    A -> B (leaf), A -> C -> D (leaf)
    Expected: A=0, B=0 (leaf), C=1 (non-leaf), D=1 (leaf stays at C's level)
    """
    layout = MockLayout(
        elements=[
            {'id': 'A', 'type': 'icon'},
            {'id': 'B', 'type': 'icon'},
            {'id': 'C', 'type': 'icon'},
            {'id': 'D', 'type': 'icon'},
        ],
        connections=[
            {'from': 'A', 'to': 'B'},
            {'from': 'A', 'to': 'C'},
            {'from': 'C', 'to': 'D'},
        ],
    )

    analyzer = StructureAnalyzer(debug=False)
    info = analyzer.analyze(layout)

    assert info.topological_levels['A'] == 0
    assert info.topological_levels['B'] == 0, (
        f"B (leaf) should stay at parent level 0, got {info.topological_levels['B']}"
    )
    assert info.topological_levels['C'] == 1
    assert info.topological_levels['D'] == 1, (
        f"D (leaf) should stay at parent level 1, got {info.topological_levels['D']}"
    )
    print("[PASS] Mixed leaf and non-leaf children")


def main():
    """Run all topological level tests."""
    print("=" * 70)
    print("TESTS: TOPOLOGICAL LEVELS - LEAF STAYS IN PARENT LEVEL")
    print("=" * 70)
    print()

    tests = [
        test_case_a_simple_leaf,
        test_case_b_chain_with_leaf,
        test_case_c_merge_with_leaf,
        test_case_c_merge_different_depths,
        test_non_leaf_still_increments,
        test_source_node_is_leaf,
        test_fan_out_multiple_leaves,
        test_mixed_leaf_and_non_leaf_children,
    ]

    passed = 0
    failed = 0

    for test_func in tests:
        try:
            test_func()
            passed += 1
        except AssertionError as e:
            print(f"[FAIL] {test_func.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"[ERROR] {test_func.__name__}: {e}")
            failed += 1

    print()
    print("=" * 70)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("=" * 70)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
