"""BUGS-ROUTE-003 — routing.preference se honra hasta el final del pipeline.

Hallazgo del caso TM en el visor: `routing.preference` sólo vivía en el
fallback naive; el grafo de visibilidad (y el simplificador de zigzags)
dejaban el barrido perpendicular PEGADO al borde del icono — el codo
«justo al llegar». Tres piezas:
1. `_reshape_terminal_elbows`: el codo terminal se retira a la MITAD del
   tramo largo (V-H-V), consciente de obstáculos.
2. Preferencia efectiva: la declarada gana; 'auto' toma el eje dominante.
3. Snap casi-alineados: un extremo cuya única arista queda a ≤ media
   ranura de la columna del otro se alinea (con hueco en su fila y
   columna libre en filas intermedias).
"""

import json

from AlmaGag.generator import select_strategy
from AlmaGag.layout import Layout
from AlmaGag.layout.considerations import extract_considerations
from AlmaGag.layout.engine import LayoutEngine
from AlmaGag.routing.orthogonal_router import _reshape_terminal_elbows
from AlmaGag.routing.router_base import Point


def _optimize(d):
    L = Layout(elements=d['elements'], connections=d['connections'],
               canvas=d.get('canvas', {'width': 1400, 'height': 900}))
    L._strategy = select_strategy(d, None)
    L._considerations = extract_considerations(d)
    return LayoutEngine(verbose=False, strategy=None).optimize(L)


def test_reshape_pulls_elbow_to_mid_leg():
    """V…→H pegado al borde se vuelve V-H-V con el codo a mitad del tramo."""
    path = [Point(738, 1136), Point(738, 1000), Point(638, 1000)]
    out = _reshape_terminal_elbows(path, vertical=True)
    assert len(out) == 4
    assert (out[1].x, out[1].y) == (738, 1068)
    assert (out[2].x, out[2].y) == (638, 1068)
    assert (out[3].x, out[3].y) == (638, 1000)   # el puerto no se toca

    # cabeza simétrica: H de salida pegado al borde
    path = [Point(154, 1136), Point(202, 1136), Point(202, 1000)]
    out = _reshape_terminal_elbows(path, vertical=True)
    assert (out[1].x, out[1].y) == (154, 1068)
    assert (out[2].x, out[2].y) == (202, 1068)


def test_reshape_respects_obstacles():
    """Si el corredor de en medio está bloqueado, el codo se queda."""
    class Obst:
        def intersects_segment(self, ax, ay, bx, by):
            # bloquea cualquier tramo que pase por y=1068
            return min(ay, by) <= 1068 <= max(ay, by) or abs(ay - 1068) < 1
    path = [Point(738, 1136), Point(738, 1000), Point(638, 1000)]
    out = _reshape_terminal_elbows(path, vertical=True, obstacles=[Obst()])
    assert [(p.x, p.y) for p in out] == [(738, 1136), (738, 1000), (638, 1000)]


def test_vertical_flow_arrivals_are_vertical():
    """Árbol con preference vertical: ninguna llegada termina con barrido H
    pegado al borde (el codo vive a ≥20px del puerto)."""
    r = {'type': 'orthogonal', 'preference': 'vertical'}
    d = {'elements': [
            {'id': 'top', 'type': 'server', 'label': 'Consolidado\nfinal'},
            {'id': 'a', 'type': 'server', 'label': 'Rama A\nintermedia'},
            {'id': 'b', 'type': 'server', 'label': 'Rama B\nintermedia'},
            {'id': 'a1', 'type': 'server', 'label': 'Fuente A1\nde datos'},
            {'id': 'b1', 'type': 'server', 'label': 'Fuente B1\nde datos'}],
         'connections': [
            {'from': 'a', 'to': 'top', 'routing': dict(r)},
            {'from': 'b', 'to': 'top', 'routing': dict(r)},
            {'from': 'a1', 'to': 'a', 'routing': dict(r)},
            {'from': 'b1', 'to': 'b', 'routing': dict(r)}]}
    out = _optimize(d)
    for c in out.connections:
        pts = (c.get('computed_path') or {}).get('points') or []
        if len(pts) < 2:
            continue
        (ax, ay), (bx, by) = pts[-2], pts[-1]
        horizontal = abs(ay - by) < 0.5 and abs(ax - bx) >= 0.5
        assert not horizontal, \
            f"{c['from']}->{c['to']} llega con barrido H al borde: {pts[-3:]}"


def test_near_miss_end_snaps_to_column():
    """Un extremo con una sola arista a <media ranura de la columna del
    otro (aunque salte rangos) se alinea: la arista sale vertical pura."""
    d = {'elements': [
            {'id': 'sink', 'type': 'server', 'label': 'Sumidero'},
            {'id': 'm1', 'type': 'server', 'label': 'Medio 1'},
            {'id': 'm2', 'type': 'server', 'label': 'Medio 2'},
            {'id': 'src', 'type': 'server', 'label': 'Fuente lejana'},
            {'id': 'x1', 'type': 'server', 'label': 'Vecino'}],
         'connections': [
            {'from': 'm1', 'to': 'sink'}, {'from': 'm2', 'to': 'm1'},
            {'from': 'src', 'to': 'm2'},
            {'from': 'x1', 'to': 'sink'}]}
    out = _optimize(d)
    by = out.elements_by_id
    # la cadena src→m2→m1→sink debería terminar en columnas coherentes:
    # cada eslabón 1:1 con desfase chico queda alineado (dx ≤ 1px) o el
    # desfase original superaba media ranura (no aplica el snap)
    for f, t in [('m1', 'sink'), ('m2', 'm1'), ('src', 'm2')]:
        dx = abs((by[f]['x'] + 40) - (by[t]['x'] + 40))
        assert dx <= 1.0 or dx > 40.0, \
            f'{f}->{t} quedó con jog residual de {dx:.0f}px (ni alineado ni lejos)'
