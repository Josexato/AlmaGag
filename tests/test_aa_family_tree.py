"""Grupo AA — árboles familiares (AA98 T-joint, AA99 peine, AA100 labels).

Fixture de regresión: docs/diagrams/gags/13-stresstest.gag (la genealogía
de 27 elementos y 6 uniones del veredicto de Claude Design, 20-ago-2026).
"""

import json

from AlmaGag.layout import Layout
from AlmaGag.layout.strategies.auto.optimizer import AutoLayoutOptimizer
from AlmaGag.layout.strategies.auto.genealogy import (apply_family_layout,
                                                      detect_family)
from AlmaGag.config import ICON_WIDTH, ICON_HEIGHT

FIXTURE = 'docs/diagrams/gags/13-stresstest.gag'


def _optimized():
    d = json.load(open(FIXTURE))
    L = Layout(elements=d['elements'], connections=d['connections'],
               canvas=d.get('canvas', {'width': 1400, 'height': 900}))
    return AutoLayoutOptimizer().optimize(L)


def test_deteccion_conservadora():
    """El árbol familiar se detecta; un flujo normal NO."""
    d = json.load(open(FIXTURE))
    L = Layout(elements=d['elements'], connections=d['connections'],
               canvas={'width': 1400, 'height': 900})
    fam = detect_family(L)
    assert fam and len(fam['unions']) == 6
    flow = Layout(
        elements=[{'id': 'a', 'label': 'A'}, {'id': 'b', 'label': 'B'}],
        connections=[{'from': 'a', 'to': 'b'}],
        canvas={'width': 400, 'height': 300})
    assert apply_family_layout(flow) == 0


def test_aa98_union_en_el_carril_de_la_pareja():
    """AA98: |y(unión) − y(pareja)| ≤ ½ fila; cero codos cónyuge—unión."""
    L = _optimized()
    by = {e['id']: e for e in L.elements}
    fam_conns = [c for c in L.connections if c.get('_family_joint') == 'T']
    assert fam_conns, 'sin conexiones cónyuge—unión marcadas'
    for c in fam_conns:
        s, u = by[c['from']], by[c['to']]
        assert abs(u['y'] - s['y']) <= 105, \
            f"unión {c['to']} descolgada de su pareja"
        pts = c['computed_path']['points']
        assert len(pts) == 2 and abs(pts[0][1] - pts[1][1]) < 0.6, \
            f"cónyuge—unión {c['from']}→{c['to']} no es horizontal pura"


def test_aa99_peine_troncal_compartida():
    """AA99: los hijos de una misma unión comparten troncal y bajada."""
    L = _optimized()
    from collections import defaultdict
    combs = defaultdict(list)
    for c in L.connections:
        if c.get('_family_joint') == 'comb':
            combs[c['from']].append(c)
    assert combs
    for uid, cs in combs.items():
        trunks = {round(c['computed_path']['points'][1][1], 1) for c in cs}
        drops = {round(c['computed_path']['points'][0][0], 1) for c in cs}
        assert len(trunks) == 1, f'peine de {uid} sin troncal única'
        assert len(drops) == 1, f'peine de {uid} con varias bajadas del padre'
        for c in cs:
            pts = c['computed_path']['points']
            for a, b in zip(pts, pts[1:]):
                assert abs(a[0] - b[0]) < 0.6 or abs(a[1] - b[1]) < 0.6, \
                    'tramo diagonal en el peine'


def test_aa100_labels_pegados_y_uniformes():
    """AA100: label centrado bajo su icono (≤20px de aire), TODOS abajo."""
    L = _optimized()
    by = {e['id']: e for e in L.elements}
    for eid, pos in L.label_positions.items():
        e = by[eid]
        cx, ly, anchor, side = pos[0], pos[1], pos[2], pos[3]
        assert side == 'bottom', f'{eid}: lado {side} — la fila no es uniforme'
        assert abs(cx - (e['x'] + ICON_WIDTH / 2)) < 1, f'{eid} descentrado'
        gap = ly - (e['y'] + ICON_HEIGHT)
        assert 0 < gap <= 20, f'{eid}: label a {gap:.0f}px del icono'
