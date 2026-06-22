"""
Template 'state' — máquina de estados con transiciones cíclicas
(WISH-LAYOUT-004 Fase 3).

Patrón objetivo:
- Ciclos significativos (estados que se vuelven a alcanzar).
- Self-loops (estados con transiciones a sí mismos — eg. idle waiting).
- Branching moderado (cada estado puede ir a 2-3 siguientes).
- Sin containers o pocos.
- Keywords 'state', 'transition' refuerzan.

Layout: distribución circular — todos los estados en un círculo, las
transiciones se rutean entre ellos. Esto es el layout más limpio para
máquinas de estado sin metadata adicional.
"""

import math
from collections import defaultdict

from AlmaGag.layout.templates.base import BaseTemplate
from AlmaGag.layout.templates.features import GraphFeatures


def _extract_id(ref):
    return ref['id'] if isinstance(ref, dict) else ref


class StateTemplate(BaseTemplate):
    """Máquina de estados: nodos distribuidos en círculo."""

    name = 'state'

    def detect_score(self, features: GraphFeatures) -> float:
        """
        Señales positivas para 'state':
        - has_cycles == True.
        - n_self_loops >= 1.
        - Profundidad topológica baja (los ciclos rompen el orden topológico).
        - Branching moderado.
        - Keywords 'state' / 'transition'.
        """
        score = 0.0

        if features.has_cycles:
            score += 0.30

        if features.n_self_loops >= 1:
            score += 0.20

        # Estados típicamente 3-15
        if 3 <= features.n_root_elements <= 15:
            score += 0.15

        if features.topological_depth <= 3:
            score += 0.10

        if 1.5 <= features.branching_factor <= 4.0:
            score += 0.10

        if features.label_keywords & {'state', 'transition'}:
            score += 0.20

        # Fase 4: bonus por roles declarados como 'state'
        if 'state' in set(features.declared_roles.values()):
            score += 0.20

        # Penalizar si tiene containers (sugiere arch/dashboard)
        if features.n_containers >= 2:
            score -= 0.15

        return max(0.0, min(score, 1.0))

    def apply(self, data: dict) -> None:
        apply_state_template(data)


def apply_state_template(data):
    """Distribuye estados en círculo."""
    RADIUS = 350
    ICON_W_HALF = 40
    ICON_H_HALF = 25
    PADDING = 100

    elements = data.get('elements', [])
    connections = data.get('connections', [])
    if not elements:
        return

    contained_ids = set()
    for e in elements:
        if 'contains' in e:
            for ref in e.get('contains', []):
                contained_ids.add(_extract_id(ref))

    states = [e for e in elements if e['id'] not in contained_ids]
    n = len(states)
    if n == 0:
        return

    canvas_w = 2 * RADIUS + PADDING * 2
    canvas_h = canvas_w
    center_x = canvas_w // 2
    center_y = canvas_h // 2

    if n == 1:
        if 'x' not in states[0]:
            states[0]['x'] = center_x - ICON_W_HALF
        if 'y' not in states[0]:
            states[0]['y'] = center_y - ICON_H_HALF
    else:
        for i, state in enumerate(states):
            angle = 2 * math.pi * i / n - math.pi / 2  # primero arriba
            if 'x' not in state:
                state['x'] = center_x + int(RADIUS * math.cos(angle)) - ICON_W_HALF
            if 'y' not in state:
                state['y'] = center_y + int(RADIUS * math.sin(angle)) - ICON_H_HALF

    canvas = data.setdefault('canvas', {})
    canvas['width'] = canvas_w
    canvas['height'] = canvas_h
