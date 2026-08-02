"""§P60 — zonas de servicio a la periferia + troncal por zona destino.

Con zonas-contenedor sin coordenadas del autor, el macro-layout distingue
zonas operativas (enlace inter-zona de transporte: bidirectional/none) de
zonas de servicio (sólo enlaces administrativos dirigidos). Las operativas
van adyacentes en la banda principal; las de servicio, en la fila
periférica bajo la banda. Los enlaces inter-zona de un mismo par
(origen → destino) comparten UNA espina ortogonal en el corredor (§I29)
y no queda ninguna diagonal inter-zona (§H24).
"""

import json

import pytest

from AlmaGag.generator import select_strategy
from AlmaGag.layout import Layout
from AlmaGag.layout.engine import LayoutEngine
from AlmaGag.layout.strategies.auto.zones import (
    TRANSPORT_DIRECTIONS, route_zone_trunks,
    top_level_area_zones, zones_lack_author_coords)

FIXTURE = 'docs/diagrams/gags/mina-arquitectura-fisica.sdjf'
OPERATIONAL = {'z_mina', 'z_pila'}
SERVICE = {'z_contratista', 'z_externos', 'z_remoto'}


def _box(e):
    return (e['x'], e['y'], e['x'] + e.get('width', 80), e['y'] + e.get('height', 50))


@pytest.fixture(scope='module')
def result():
    d = json.load(open(FIXTURE))
    L = Layout(elements=d['elements'], connections=d['connections'],
               canvas={'width': 1400, 'height': 900})
    L._strategy = select_strategy(d, 'auto')
    return LayoutEngine(verbose=False, strategy=None).optimize(L)


def test_service_zones_below_operational_band(result):
    """Las zonas de servicio quedan ENTERAS bajo la banda operativa."""
    by = result.elements_by_id
    band_bottom = max(_box(by[z])[3] for z in OPERATIONAL)
    for z in SERVICE:
        assert _box(by[z])[1] > band_bottom, \
            f'{z} no está en la periferia (top={_box(by[z])[1]} ≤ {band_bottom})'


def test_operational_band_is_horizontal(result):
    """Las operativas comparten banda: sus rangos verticales se solapan."""
    by = result.elements_by_id
    boxes = [_box(by[z]) for z in OPERATIONAL]
    top = max(b[1] for b in boxes)
    bottom = min(b[3] for b in boxes)
    assert top < bottom, 'las zonas operativas no comparten banda horizontal'


def test_inter_zone_paths_are_orthogonal(result):
    """§H24: cero diagonales inter-zona — todo tramo es horizontal o vertical."""
    trunked = [c for c in result.connections if c.get('_zone_trunk')]
    assert trunked, 'ninguna conexión quedó marcada como troncal'
    for c in trunked:
        pts = c['computed_path']['points']
        assert len(pts) >= 2
        for (ax, ay), (bx, by_) in zip(pts, pts[1:]):
            assert abs(ax - bx) < 0.5 or abs(ay - by_) < 0.5, \
                f"tramo diagonal en {c['from']}->{c['to']}: {(ax, ay)}->{(bx, by_)}"


def test_trunk_shares_spine_per_pair(result):
    """§I29: los enlaces de un mismo par (origen→destino) comparten espina."""
    groups = {}
    for c in result.connections:
        tk = c.get('_zone_trunk')
        if tk:
            groups.setdefault((tk['src'], tk['dst']), []).append(c)
    multi = {k: v for k, v in groups.items() if len(v) >= 2}
    assert multi, 'el fixture minero tiene pares con varios enlaces'
    for (src, dst), conns in multi.items():
        # la espina es el tramo intermedio: mismo eje compartido por el grupo
        spines = set()
        for c in conns:
            pts = c['computed_path']['points']
            (ax, ay), (bx, by_) = pts[1], pts[2]
            spines.add(round(ay, 1) if abs(ay - by_) < 0.5 else round(ax, 1))
        assert len(spines) == 1, \
            f'troncal {src}->{dst} con {len(spines)} espinas: {spines}'


def test_classification_gate_requires_transport_contrast():
    """Sin contraste operativa/servicio (todo transporte o todo admin), el
    banding no aplica y el layout general queda como estaba."""
    def _mk(direction):
        d = {'elements': [
            {'id': 'za', 'type': 'area', 'label': 'A', 'contains': ['a']},
            {'id': 'zb', 'type': 'area', 'label': 'B', 'contains': ['b']},
            {'id': 'a', 'type': 'server', 'label': 'a'},
            {'id': 'b', 'type': 'server', 'label': 'b'},
        ], 'connections': [
            {'from': 'a', 'to': 'b', 'direction': direction},
        ]}
        L = Layout(elements=d['elements'], connections=d['connections'],
                   canvas={'width': 800, 'height': 600})
        L._strategy = select_strategy(d, 'auto')
        return LayoutEngine(verbose=False, strategy=None).optimize(L)

    for direction in ('bidirectional', 'forward'):
        res = _mk(direction)
        assert not any(c.get('_zone_trunk') for c in res.connections), \
            f'§P60 no debe aplicar con un solo tipo de enlace ({direction})'


def test_gate_respects_author_coords():
    """Zonas con coordenadas del autor: la geometría es suya, no del motor."""
    els = [
        {'id': 'za', 'type': 'area', 'contains': ['a'], 'x': 10, 'y': 10},
        {'id': 'zb', 'type': 'area', 'contains': ['b']},
        {'id': 'a', 'type': 'server'}, {'id': 'b', 'type': 'server'},
    ]
    assert not zones_lack_author_coords(els)
    for e in els:
        e.pop('x', None), e.pop('y', None)
    assert zones_lack_author_coords(els)


def test_top_level_zones_excludes_nested():
    """Un área contenida por otra no es zona top-level."""
    els = [
        {'id': 'za', 'type': 'area', 'contains': ['zi', 'a']},
        {'id': 'zi', 'type': 'area', 'contains': ['b']},
        {'id': 'zc', 'type': 'area', 'contains': ['c']},
        {'id': 'a', 'type': 'server'}, {'id': 'b', 'type': 'server'},
        {'id': 'c', 'type': 'server'},
    ]
    assert {z['id'] for z in top_level_area_zones(els)} == {'za', 'zc'}


def test_trunk_reroute_is_idempotent(result):
    """route_zone_trunks es estable: re-invocarlo no cambia los paths."""
    before = {id(c): [list(p) for p in c['computed_path']['points']]
              for c in result.connections if c.get('_zone_trunk')}
    route_zone_trunks(result)
    after = {id(c): [list(p) for p in c['computed_path']['points']]
             for c in result.connections if c.get('_zone_trunk')}
    assert before == after


def test_transport_directions_constant():
    """El contrato de clasificación: transporte = bidirectional/none."""
    assert set(TRANSPORT_DIRECTIONS) == {'bidirectional', 'none'}
