#!/usr/bin/env python3
"""
Tests para Fase 5 (PositionOptimizer): normalizacion y offsets por capa.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from AlmaGag.layout.laf.position_optimizer import PositionOptimizer


def test_normalization_preserves_global_x_alignment():
    """
    Las capas no deben reiniciarse a x=0..N de forma independiente.
    Debe conservarse la alineacion global entre capas.
    """
    optimizer = PositionOptimizer(debug=False)

    positions = {
        "NdPr005": (1.2, 3.0),
        "NdPr006": (0.2, 4.0),
        "NdPr011": (1.1, 4.0),
        "NdPr007": (2.3, 4.0),
    }
    layers = {
        3: ["NdPr005"],
        4: ["NdPr006", "NdPr011", "NdPr007"],
    }

    normalized = optimizer._normalize_positions(positions, layers)

    assert normalized["NdPr005"][0] == 1
    assert normalized["NdPr011"][0] == 1


def test_single_layer_offset_optimizer_moves_layer_horizontally():
    """
    El optimizador por offset de capa debe mover una capa completa.
    """
    optimizer = PositionOptimizer(debug=False)

    layers = {
        0: ["P"],
        1: ["A", "C"],
    }
    base_positions = {
        "P": (8.0, 0.0),
        "A": (4.0, 1.0),
        "C": (7.0, 1.0),
    }
    layer_offsets = {0: 0.0, 1: 0.0}
    current_positions = optimizer._apply_layer_offsets(base_positions, layers, layer_offsets)
    adjacency = {
        "P": [("A", 1)],
        "A": [("P", 1)],
        "C": [],
    }

    changed = optimizer._optimize_layer_offset(
        level=1,
        layers=layers,
        base_positions=base_positions,
        current_positions=current_positions,
        adjacency=adjacency,
        layer_offsets=layer_offsets,
    )

    assert changed is True
    assert layer_offsets[1] > 0.0


def test_apply_layer_offsets_preserves_intralayer_order():
    """
    Al desplazar por capa, debe conservarse el orden relativo de la capa.
    """
    optimizer = PositionOptimizer(debug=False)
    layers = {
        3: ["NdPr005"],
        4: ["NdPr006", "NdPr011", "NdPr007"],
    }
    base_positions = {
        "NdPr005": (4.0, 3.0),
        "NdPr006": (4.0, 4.0),
        "NdPr011": (5.0, 4.0),
        "NdPr007": (6.0, 4.0),
    }

    shifted = optimizer._apply_layer_offsets(
        base_positions=base_positions,
        layers=layers,
        layer_offsets={3: 1.25, 4: -0.5},
    )

    assert shifted["NdPr006"][0] < shifted["NdPr011"][0] < shifted["NdPr007"][0]


def test_layer_offset_uses_parents_only_when_enabled():
    """
    Con optimize_against_parents_only, hijos no deben afectar offset de la capa.
    """
    optimizer = PositionOptimizer(debug=False)
    layers = {
        0: ["P"],
        1: ["N"],
        2: ["C"],
    }
    base_positions = {
        "P": (10.0, 0.0),  # padre muy a la derecha
        "N": (0.0, 1.0),   # nodo de capa a optimizar
        "C": (-10.0, 2.0), # hijo muy a la izquierda (si contara, jalaría al otro lado)
    }
    layer_offsets = {0: 0.0, 1: 0.0, 2: 0.0}
    current_positions = optimizer._apply_layer_offsets(base_positions, layers, layer_offsets)
    adjacency = {
        "P": [("N", 1)],
        "N": [("P", 1), ("C", 1)],
        "C": [("N", 1)],
    }

    changed = optimizer._optimize_layer_offset(
        level=1,
        layers=layers,
        base_positions=base_positions,
        current_positions=current_positions,
        adjacency=adjacency,
        layer_offsets=layer_offsets,
    )

    assert changed is True
    assert layer_offsets[1] > 0.0
