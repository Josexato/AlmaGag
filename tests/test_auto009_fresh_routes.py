"""BUGS-AUTO-009 — el re-ruteo final H3 es incondicional (sin revert viciado).

El guardado antiguo comparaba las rutas frescas contra rutas RANCIAS
(calculadas antes de normalizar/escalonar): si «ganaba» el material viejo,
el layout entregaba paths cuyos extremos ya no tocaban los iconos — el
renderer los re-anclaba dibujando diagonales que ningún evaluador midió.
El criterio ahora: sobre la geometría final sólo existe un estado medible,
el re-ruteado. Invariante observable: TODO computed_path termina anclado a
la geometría VIGENTE de sus extremos.
"""

import json

import pytest

from AlmaGag.config import ICON_HEIGHT, ICON_WIDTH
from AlmaGag.generator import select_strategy
from AlmaGag.layout import Layout
from AlmaGag.layout.engine import LayoutEngine

# fixtures con contenedores/zonas: el camino donde normalizar + escalonar
# movía geometría después del último ruteo del loop
FIXTURES = [
    'docs/diagrams/gags/07-containers.sdjf',
    'docs/diagrams/gags/mina-arquitectura-fisica.sdjf',
]


def _optimized(path):
    d = json.load(open(path))
    L = Layout(elements=d['elements'], connections=d['connections'],
               canvas={'width': 1400, 'height': 900})
    L._strategy = select_strategy(d, 'auto')
    return LayoutEngine(verbose=False, strategy=None).optimize(L)


def _bbox(e, margin=40.0):
    w = e.get('width', ICON_WIDTH)
    h = e.get('height', ICON_HEIGHT)
    return (e['x'] - margin, e['y'] - margin,
            e['x'] + w + margin, e['y'] + h + margin)


def _inside(p, bb):
    return bb[0] <= p[0] <= bb[2] and bb[1] <= p[1] <= bb[3]


@pytest.mark.parametrize('fixture', FIXTURES)
def test_final_routes_are_anchored_to_current_geometry(fixture):
    layout = _optimized(fixture)
    by_id = {e['id']: e for e in layout.elements}
    checked = 0
    for c in layout.connections:
        cp = c.get('computed_path')
        pts = cp.get('points') if isinstance(cp, dict) else None
        if not pts or len(pts) < 2:
            continue
        a, b = by_id.get(c['from']), by_id.get(c['to'])
        if not a or not b or 'x' not in a or 'x' not in b:
            continue
        assert _inside(pts[0], _bbox(a)), (
            f"{fixture}: {c['from']}->{c['to']} arranca en {pts[0]} "
            f"lejos del bbox vigente de {c['from']} — ruta rancia")
        assert _inside(pts[-1], _bbox(b)), (
            f"{fixture}: {c['from']}->{c['to']} termina en {pts[-1]} "
            f"lejos del bbox vigente de {c['to']} — ruta rancia")
        checked += 1
    assert checked > 0
