"""WISH-ROUTE-001 (grupo T) — ruteo hacia contenedores.

T70: destino contenedor → el path termina en su PERÍMETRO y el último
tramo es perpendicular al borde. T71: destino hijo → el cruce del borde es
H/V puro y la punta queda en el borde del hijo. T72: los puertos de un
mismo lado se reparten (≥18px, sin punto de llegada compartido).
"""

import json

import pytest

from AlmaGag.generator import select_strategy
from AlmaGag.layout import Layout
from AlmaGag.layout.engine import LayoutEngine
from AlmaGag.routing.container_ports import PORT_MIN_SEP

HLD = 'docs/diagrams/gags/mina-hld.gag'


def _optimize(d):
    L = Layout(elements=d['elements'], connections=d['connections'],
               canvas={'width': 1400, 'height': 900})
    L._strategy = 'auto'
    return LayoutEngine(verbose=False, strategy='auto').optimize(L)


def _pts(conn):
    cp = conn.get('computed_path') or {}
    return [(p[0], p[1]) if not hasattr(p, 'x') else (p.x, p.y)
            for p in (cp.get('points') or [])]


def _rect(e):
    return (e['x'], e['y'],
            e['x'] + e.get('width', 80), e['y'] + e.get('height', 50))


def _on_border(p, r, eps=2.0):
    x, y = p
    on_v = (abs(x - r[0]) <= eps or abs(x - r[2]) <= eps) and \
        r[1] - eps <= y <= r[3] + eps
    on_h = (abs(y - r[1]) <= eps or abs(y - r[3]) <= eps) and \
        r[0] - eps <= x <= r[2] + eps
    return on_v or on_h


def _axis_aligned(a, b, eps=0.5):
    return abs(a[0] - b[0]) <= eps or abs(a[1] - b[1]) <= eps


def _crossings(pts, r):
    """Segmentos del path que cruzan el borde de r (dentro↔fuera)."""
    def inside(p):
        return r[0] + 0.5 < p[0] < r[2] - 0.5 and r[1] + 0.5 < p[1] < r[3] - 0.5
    out = []
    for i in range(len(pts) - 1):
        a, b = pts[i], pts[i + 1]
        a_in = inside(a) or _on_border(a, r, 0.6)
        b_in = inside(b) or _on_border(b, r, 0.6)
        if a_in != b_in:
            out.append((a, b))
    return out


def test_t70_terminal_port_on_perimeter_perpendicular():
    """Conexión a un CONTENEDOR: termina en su perímetro, llegada H/V."""
    d = {'elements': [
            {'id': 'box', 'type': 'area', 'label': 'Caja',
             'contains': ['a', 'b']},
            {'id': 'a', 'type': 'server', 'label': 'A'},
            {'id': 'b', 'type': 'server', 'label': 'B'},
            {'id': 'ext', 'type': 'cloud', 'label': 'Externo'}],
         'connections': [{'from': 'ext', 'to': 'box',
                          'direction': 'forward'}]}
    out = _optimize(d)
    conn = out.connections[0]
    pts = _pts(conn)
    box = _rect(out.elements_by_id['box'])
    assert len(pts) >= 2
    assert _on_border(pts[-1], box), f'punta {pts[-1]} fuera del perímetro {box}'
    assert _axis_aligned(pts[-2], pts[-1]), 'llegada no perpendicular'


def test_t71_child_crossing_is_axis_aligned_and_ends_on_child():
    """Conexión a un HIJO: el cruce del borde es H/V puro y la punta queda
    en el borde del hijo (nunca su interior)."""
    d = {'elements': [
            {'id': 'box', 'type': 'area', 'label': 'Caja',
             'contains': ['a', 'b']},
            {'id': 'a', 'type': 'server', 'label': 'A'},
            {'id': 'b', 'type': 'server', 'label': 'B'},
            {'id': 'ext', 'type': 'cloud', 'label': 'Externo'}],
         'connections': [{'from': 'ext', 'to': 'a',
                          'direction': 'forward'}]}
    out = _optimize(d)
    conn = out.connections[0]
    pts = _pts(conn)
    box = _rect(out.elements_by_id['box'])
    child = _rect(out.elements_by_id['a'])
    crossings = _crossings(pts, box)
    assert crossings, 'el path no cruza el borde del contenedor'
    for a, b in crossings:
        assert _axis_aligned(a, b), f'cruce diagonal del borde: {a}->{b}'
    assert _on_border(pts[-1], child), \
        f'la punta {pts[-1]} no está en el borde del hijo {child}'


def test_t72_ports_distributed_on_shared_side():
    """Varias conexiones al mismo contenedor: puntos de llegada separados
    (ningún par comparte punto; los del mismo lado, a ≥ PORT_MIN_SEP)."""
    els = [{'id': 'box', 'type': 'area', 'label': 'Caja',
            'contains': ['a']},
           {'id': 'a', 'type': 'server', 'label': 'A'}]
    els += [{'id': f'e{i}', 'type': 'server', 'label': f'E{i}'}
            for i in range(4)]
    conns = [{'from': f'e{i}', 'to': 'box', 'direction': 'forward'}
             for i in range(4)]
    out = _optimize({'elements': els, 'connections': conns})
    box = _rect(out.elements_by_id['box'])
    tips = [_pts(c)[-1] for c in out.connections]
    for t in tips:
        assert _on_border(t, box)
    for i, p in enumerate(tips):
        for q in tips[i + 1:]:
            d = ((p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2) ** 0.5
            assert d > 1.0, f'dos puntas comparten punto: {p} ~ {q}'
            same_side = abs(p[0] - q[0]) <= 1.0 or abs(p[1] - q[1]) <= 1.0
            if same_side:
                assert d >= PORT_MIN_SEP - 0.5, \
                    f'puntas a {d:.1f}px (< {PORT_MIN_SEP})'


def test_hld_perimeter_has_no_diagonal_crossings():
    """Audit del criterio en el caso real (HLD): cruces diagonales de
    perímetro = 0 en todos los contenedores."""
    d = json.load(open(HLD))
    L = Layout(elements=d['elements'], connections=d['connections'],
               canvas={'width': 1400, 'height': 900})
    L._strategy = select_strategy(d, None)
    out = LayoutEngine(verbose=False, strategy=None).optimize(L)
    boxes = [_rect(e) for e in out.elements
             if 'contains' in e and 'x' in e]
    diag = 0
    for conn in out.connections:
        pts = _pts(conn)
        if len(pts) < 2:
            continue
        for r in boxes:
            for a, b in _crossings(pts, r):
                if not _axis_aligned(a, b):
                    diag += 1
    assert diag == 0, f'{diag} cruces diagonales de perímetro'
