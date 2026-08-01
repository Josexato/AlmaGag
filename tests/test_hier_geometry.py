"""
Test de regresión geométrico sobre el trazado hier (QA-Q5 de Claude Design).

Afirma, por conexión, que el path honra los bordes de los iconos:
(a) el primer punto está sobre el borde del origen,
(b) el último punto está sobre el borde del destino,
(c) el último segmento llega perpendicular al borde de llegada (polilíneas),
(d) ningún vértice del path cae DENTRO de un icono ajeno.

Antes del fix del offset de 40/15px, las 17 conexiones del stresstest
fallaban (a)/(b): flotaban 40px del borde.
"""

import json
import glob
import os
import pytest

from AlmaGag.layout import Layout
from AlmaGag.layout.strategies.hier.optimizer import HierLayoutOptimizer
from AlmaGag.config import ICON_WIDTH, ICON_HEIGHT

TOL = 1.0


def _optimize(path):
    d = json.load(open(path))
    L = Layout(elements=d['elements'], connections=d['connections'],
               canvas=d.get('canvas', {'width': 1400, 'height': 900}))
    L._diagram_name = os.path.basename(path)
    return HierLayoutOptimizer(verbose=False).optimize(L)


def _border_dist(pt, e):
    """Distancia del punto al borde del rect del icono (0 si está sobre él)."""
    x, y = pt
    bx1, by1 = e['x'], e['y']
    bx2, by2 = bx1 + ICON_WIDTH, by1 + ICON_HEIGHT
    on_x_span = bx1 - TOL <= x <= bx2 + TOL
    on_y_span = by1 - TOL <= y <= by2 + TOL
    dx = min(abs(x - bx1), abs(x - bx2)) if on_y_span else 1e9
    dy = min(abs(y - by1), abs(y - by2)) if on_x_span else 1e9
    return min(dx, dy)


def _inside(pt, e, margin=-1.0):
    x, y = pt
    return (e['x'] - margin < x < e['x'] + ICON_WIDTH + margin and
            e['y'] - margin < y < e['y'] + ICON_HEIGHT + margin)


def _which_border(pt, e):
    x, y = pt
    d = {'T': abs(y - e['y']), 'B': abs(y - (e['y'] + ICON_HEIGHT)),
         'L': abs(x - e['x']), 'R': abs(x - (e['x'] + ICON_WIDTH))}
    return min(d, key=d.get)


def _check(r, check_obstacles=True):
    """Devuelve la lista de problemas. (a)(b)(c) = el bug de trazado
    (extremos en borde + llegada perpendicular). (d) = evasión de obstáculos,
    opcional (v1 no garantiza evasión en grafos muy densos)."""
    by = {e['id']: e for e in r.elements}
    problems = []
    for c in r.connections:
        cp = c.get('computed_path')
        if not cp:
            continue
        pts = cp['points']
        f, t = by.get(c['from']), by.get(c['to'])
        if not f or not t or 'x' not in f or 'x' not in t:
            continue
        # (a) primer punto sobre el borde del origen
        if _border_dist(pts[0], f) > TOL:
            problems.append(f"{c['from']}->{c['to']}: origen flota ({_border_dist(pts[0], f):.0f}px)")
        # (b) último punto sobre el borde del destino
        if _border_dist(pts[-1], t) > TOL:
            problems.append(f"{c['from']}->{c['to']}: destino flota ({_border_dist(pts[-1], t):.0f}px)")
        # (c) último segmento perpendicular al borde de llegada (sólo polilínea)
        # §M44: los cruces D13 (`_straight`) están EXENTOS — son recta pura
        # puerto a puerto por diseño, la única diagonal permitida (§H24).
        if cp['type'] == 'polyline' and len(pts) >= 2 and not c.get('_straight'):
            side = _which_border(pts[-1], t)
            (px, py), (qx, qy) = pts[-2], pts[-1]
            seg = (qx - px, qy - py)
            if side in ('T', 'B') and abs(seg[0]) > TOL and abs(seg[1]) > TOL:
                problems.append(f"{c['from']}->{c['to']}: llegada no perpendicular a {side}")
        # (d) ningún vértice dentro de un icono ajeno
        if check_obstacles:
            for p in pts:
                for oid, oe in by.items():
                    if oid in (c['from'], c['to']) or 'x' not in oe or 'contains' in oe:
                        continue
                    if _inside(p, oe):
                        problems.append(f"{c['from']}->{c['to']}: vértice dentro de {oid}")
                        break
    return problems


def test_stresstest_paths_touch_borders():
    r = _optimize('docs/diagrams/gags/14-stresstest.sdjf')
    problems = _check(r)
    assert not problems, "Trazado no honra bordes:\n  " + "\n  ".join(problems)


CANON = [p for p in glob.glob('docs/diagrams/gags/*.sdjf') + glob.glob('docs/diagrams/gags/*.gag')]


@pytest.mark.parametrize('path', CANON, ids=[os.path.basename(p) for p in CANON])
def test_all_canonicals_paths_touch_borders(path):
    """QA-Q5: extremos en borde + llegada perpendicular (a·b·c) sobre TODOS
    los canónicos. La evasión de obstáculos (d) se valida sólo en el
    stresstest (v1 no garantiza evasión en grafos muy densos como los árboles
    genealógicos con cruces múltiples)."""
    r = _optimize(path)
    problems = _check(r, check_obstacles=False)
    assert not problems, f"{os.path.basename(path)}:\n  " + "\n  ".join(problems)


def test_esprimo_shared_sink_adjacent_to_parents():
    """§H25: el sumidero compartido not_prime (padres lt2 y divides) se coloca
    en la columna adyacente al tronco, no en el margen opuesto."""
    r = _optimize('docs/diagrams/gags/es-primo.gag')
    xof = {e['id']: e['x'] for e in r.elements}
    trunk = xof['lt2']          # tronco
    assert abs(xof['lt2'] - xof['divides']) < 1.0   # padres en el tronco
    # a lo sumo una columna (COL_SPACING≈200) de separación del tronco
    assert abs(xof['not_prime'] - trunk) <= 320, \
        f"not_prime lejos del tronco: {xof['not_prime']} vs {trunk}"


def test_esprimo_diamond_ports_on_vertices_no_microelbow():
    """§H26/§G19: todo extremo sobre un rombo cae EXACTO en un vértice y el
    primer/último tramo sale/entra radial (sin quiebre a <15px del puerto)."""
    from AlmaGag.layout.strategies.hier.shapes import diamond_vertices, is_diamond
    r = _optimize('docs/diagrams/gags/es-primo.gag')
    by = {e['id']: e for e in r.elements}
    for c in r.connections:
        cp = c.get('computed_path')
        if not cp or cp['type'] != 'polyline':
            continue
        pts = cp['points']
        for eid, pt, seg_pt in ((c['from'], pts[0], pts[1]),
                                (c['to'], pts[-1], pts[-2])):
            e = by[eid]
            if not is_diamond(e):
                continue
            vs = diamond_vertices(e).values()
            assert any(abs(pt[0] - vx) < 1 and abs(pt[1] - vy) < 1 for vx, vy in vs), \
                f"{c['from']}->{c['to']}: puerto {pt} no es vértice de {eid}"
            # primer tramo ≥15px (sin micro-codo espurio pegado al vértice)
            d = ((seg_pt[0] - pt[0]) ** 2 + (seg_pt[1] - pt[1]) ** 2) ** 0.5
            assert d >= 15 - TOL, \
                f"{c['from']}->{c['to']}: micro-codo a {d:.0f}px del vértice de {eid}"


@pytest.mark.parametrize('path', CANON, ids=[os.path.basename(p) for p in CANON])
def test_all_canonicals_no_diagonal_elbows(path):
    """§H24: un ruteo con codos (polyline de ≥3 puntos) es estrictamente
    ortogonal — cada segmento es horizontal o vertical. Las diagonales solo se
    permiten en rectas de 2 puntos (cruces reales §D13 / mismo nivel §D12) y en
    los arcos de ciclo (bezier, §E15)."""
    r = _optimize(path)
    bad = []
    for c in r.connections:
        cp = c.get('computed_path')
        if not cp or cp['type'] != 'polyline':
            continue
        if c.get('_straight'):
            continue  # §D12/§D13: recta directa/cruce real, diagonal permitida
        pts = cp['points']
        if len(pts) < 3:
            continue  # recta de 2 puntos: diagonal permitida (D12/D13)
        for (ax, ay), (bx, by) in zip(pts, pts[1:]):
            if abs(ax - bx) > TOL and abs(ay - by) > TOL:
                bad.append(f"{c['from']}->{c['to']}: diagonal ({ax:.0f},{ay:.0f})→({bx:.0f},{by:.0f})")
    assert not bad, f"{os.path.basename(path)}:\n  " + "\n  ".join(bad)


@pytest.mark.parametrize('path', CANON, ids=[os.path.basename(p) for p in CANON])
def test_all_canonicals_paths_within_viewbox(path):
    """§G22: ningún punto de conector (polyline/waypoints/control-points del
    bezier) se sale del viewBox. bbox(paths) ⊆ [0,w]×[0,h]."""
    r = _optimize(path)
    w, h = r.canvas['width'], r.canvas['height']
    out = []
    for c in r.connections:
        cp = c.get('computed_path')
        if not cp:
            continue
        for px, py in cp.get('points', []) + cp.get('control_points', []):
            if px < -TOL or py < -TOL or px > w + TOL or py > h + TOL:
                out.append(f"{c['from']}->{c['to']}: ({px:.0f},{py:.0f}) fuera de {w:.0f}x{h:.0f}")
    assert not out, f"{os.path.basename(path)}:\n  " + "\n  ".join(out)
