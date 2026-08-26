"""Z96 (WISH-LAYOUT-030) — presupuesto de cruces para la capa overlay.

Una lámina con aristas overlay declaradas (semantic_type data_link /
control_link / sync / event) tiene presupuesto: cruces ≤ 2×|overlay|.
El excedente se reporta con las aristas culpables NOMBRADAS — un número
solo no le dice al autor qué reencaminar. Sin capa overlay no hay
presupuesto (None). Los cruces son los mismos PARES de count_crossings
(BUGS-LOG-002: trazado real, cruce interior estricto).
"""

from AlmaGag.layout import Layout
from AlmaGag.layout.metrics import (count_crossings, overlay_crossing_report,
                                    OVERLAY_XING_FACTOR)


def _cross_layout():
    """4 diagonales en abanico que se cruzan todas con todas → 6 pares
    cruzados, cada arista participa en 3; 1 sola overlay → presupuesto 2."""
    els = [{'id': f'n{i}', 'label': f'N{i}', 'x': x, 'y': y}
           for i, (x, y) in enumerate(
               [(0, 0), (400, 400), (0, 100), (400, 300),
                (400, 0), (0, 400), (400, 100), (0, 300)])]
    conns = [
        {'from': 'n0', 'to': 'n1', 'semantic_type': 'control_link',
         'computed_path': {'points': [(40, 25), (440, 425)]}},
        {'from': 'n2', 'to': 'n3',
         'computed_path': {'points': [(40, 125), (440, 325)]}},
        {'from': 'n4', 'to': 'n5',
         'computed_path': {'points': [(440, 25), (40, 425)]}},
        {'from': 'n6', 'to': 'n7',
         'computed_path': {'points': [(440, 125), (40, 325)]}},
    ]
    return Layout(elements=els, connections=conns,
                  canvas={'width': 500, 'height': 500})


def test_sin_overlays_no_hay_presupuesto():
    L = _cross_layout()
    for c in L.connections:
        c.pop('semantic_type', None)
    assert overlay_crossing_report(L) is None


def test_excedente_con_culpables_nombrados_y_ordenados():
    L = _cross_layout()
    rep = overlay_crossing_report(L)
    assert rep['overlays'] == 1
    assert rep['budget'] == OVERLAY_XING_FACTOR * 1 == 2
    assert rep['crossings'] == count_crossings(L) == 6
    assert rep['crossings'] > rep['budget']
    # cada arista participa en 3 cruces (contra las otras 3)
    assert rep['offenders'][0][2] == 3
    counts = {(f, t): n for f, t, n in rep['offenders']}
    assert counts[('n0', 'n1')] == 3
    # orden estable: del más cruzado al menos, desempate por nombre
    ns = [n for _, _, n in rep['offenders']]
    assert ns == sorted(ns, reverse=True)


def test_bajo_presupuesto_reporta_sin_exceso():
    """3 overlays (presupuesto 6) y los mismos 6 cruces: al límite, sin
    excedente — el generador sólo advierte con crossings > budget."""
    L = _cross_layout()
    L.connections[1]['semantic_type'] = 'sync'
    L.connections[2]['semantic_type'] = 'data_link'
    rep = overlay_crossing_report(L)
    assert rep['budget'] == 6
    assert not rep['crossings'] > rep['budget']
