"""WISH-ROUTE-002 (V80) — convergencia limpia.

Parte 1: eslabones 1:1 entre rangos consecutivos comparten columna — la
arista es una vertical pura y el label del extremo libre conserva su
posición natural (repro del autor: pulab→mo con 161px de desfase y la
arista barriendo bajo su propio label).
"""

import json

from AlmaGag.generator import select_strategy
from AlmaGag.layout import Layout
from AlmaGag.layout.engine import LayoutEngine

PPTO = 'docs/diagrams/gags/mina-presupuesto.sdjf'


def _optimize_ppto():
    d = json.load(open(PPTO))
    L = Layout(elements=d['elements'], connections=d['connections'],
               canvas={'width': 1400, 'height': 900})
    L._strategy = select_strategy(d, None)
    return LayoutEngine(verbose=False, strategy=None).optimize(L)


def test_chain_links_share_column_and_run_vertical():
    """pulab→mo y tareq→eq: misma columna (desfase ≤1px) y arista
    vertical pura (todos los puntos del path con la misma x)."""
    out = _optimize_ppto()
    E = out.elements_by_id
    for a, b in (('pulab', 'mo'), ('tareq', 'eq')):
        ca = E[a]['x'] + E[a].get('width', 80) / 2
        cb = E[b]['x'] + E[b].get('width', 80) / 2
        assert abs(ca - cb) <= 1.0, f'{a}/{b} desalineados: {ca:.0f} vs {cb:.0f}'
        conn = next(c for c in out.connections
                    if {c['from'], c['to']} == {a, b})
        pts = [(p[0], p[1]) for p in (conn.get('computed_path') or {})
               .get('points', [])]
        assert pts, f'{a}→{b} sin path'
        xs = {round(x) for x, _ in pts}
        assert len(xs) == 1, f'{a}→{b} no es vertical pura: {pts}'


def test_convergence_ports_distributed_and_perpendicular():
    """Parte 2 — T72 en nodos: las tres cadenas entran a `resumen` con
    llegada PERPENDICULAR (tramo final vertical) y puntas repartidas
    ≥ PORT_MIN_SEP; nada de llegadas tangenciales barriendo el borde."""
    from AlmaGag.routing.container_ports import PORT_MIN_SEP
    out = _optimize_ppto()
    tips = []
    for c in out.connections:
        if c['to'] != 'resumen':
            continue
        pts = [(p[0], p[1]) for p in (c.get('computed_path') or {})
               .get('points', [])]
        assert len(pts) >= 2
        a, b = pts[-2], pts[-1]
        assert abs(a[0] - b[0]) < 0.5, \
            f"{c['from']}→resumen llega tangencial: {a}->{b}"
        tips.append(b)
    assert len(tips) == 3
    for i in range(len(tips)):
        for j in range(i + 1, len(tips)):
            d = ((tips[i][0] - tips[j][0]) ** 2
                 + (tips[i][1] - tips[j][1]) ** 2) ** 0.5
            assert d >= PORT_MIN_SEP - 0.5, \
                f'puntas a {d:.1f}px (< {PORT_MIN_SEP})'


def test_convergence_edges_have_no_diagonals():
    """Cero segmentos diagonales en las aristas de convergencia."""
    out = _optimize_ppto()
    for c in out.connections:
        if c['to'] != 'resumen':
            continue
        pts = [(p[0], p[1]) for p in (c.get('computed_path') or {})
               .get('points', [])]
        for a, b in zip(pts, pts[1:]):
            assert abs(a[0] - b[0]) < 0.5 or abs(a[1] - b[1]) < 0.5, \
                f"diagonal en {c['from']}→resumen: {a}->{b}"


def test_free_end_label_stays_natural():
    """El label del extremo libre (pulab) queda en su posición natural
    (bottom, centrado bajo el icono) — sin la arista, el optimizador ya
    no lo empuja a left."""
    out = _optimize_ppto()
    pos = out.label_positions.get('pulab')
    assert pos is not None
    assert pos[3] in ('bottom', 'top'), f'label de pulab empujado a {pos[3]}'
