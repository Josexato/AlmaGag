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
from AlmaGag.layout.hier.optimizer import HierLayoutOptimizer
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
        if cp['type'] == 'polyline' and len(pts) >= 2:
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
