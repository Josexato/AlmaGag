"""WISH-ROUTE-005 (X92) — hub multi-área = bus ortogonal.

Un nodo con destinos inter-área en ≥3 áreas DISTINTAS se rutea como bus:
troncal horizontal única en el corredor pegado a su caja + un ramal
vertical por destino (los tramos compartidos se superponen — la lámina
muestra UNA línea con derivaciones). Bajo el umbral, ruteo par-a-par
normal por eje dominante (LAYOUT-020).
"""

from AlmaGag.layout import Layout
from AlmaGag.layout.strategies.hier.areas import layout_by_areas


def _mk_hub(n_targets):
    """Área 'bus' abajo (overlay) con un hub conectado a n_targets áreas
    de arriba (una por destino)."""
    els = [{'id': 'hub', 'type': 'server', 'label': 'Hub TI'}]
    conns, spec = [], []
    for i in range(n_targets):
        tid = f't{i}'
        els.append({'id': tid, 'type': 'server', 'label': f'Destino {i}'})
        conns.append({'from': 'hub', 'to': tid})
        spec.append({'id': f'z{i}', 'label': f'Área {i}', 'members': [tid],
                     'role': 'chain'})
    spec.append({'id': 'zbus', 'label': 'Bus', 'members': ['hub'],
                 'role': 'overlay'})
    L = Layout(elements=els, connections=conns,
               canvas={'width': 1400, 'height': 900})
    return L, spec


def test_hub_with_three_areas_becomes_bus():
    L, spec = _mk_hub(3)
    layout_by_areas(L, spec)
    bus = [c for c in L.connections if c.get('_bus') == 'hub']
    assert len(bus) == 3, 'los 3 ramales deben ser del bus'
    # troncal única: el tramo horizontal de TODOS comparte la misma y
    trunk_ys = {c['computed_path']['points'][2][1] for c in bus}
    assert len(trunk_ys) == 1, f'troncales distintas: {trunk_ys}'
    # y está en el corredor: fuera de toda caja
    ty = trunk_ys.pop()
    # ramales ortogonales
    for c in bus:
        pts = c['computed_path']['points']
        for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
            assert abs(x1 - x2) < 0.5 or abs(y1 - y2) < 0.5, 'tramo diagonal'
        # el ramal baja/sube perpendicular en la x del destino
        assert abs(pts[3][0] - c['_to_port'][0]) < 0.5


def test_trunk_lives_in_the_corridor():
    L, spec = _mk_hub(3)
    boxes = layout_by_areas(L, spec)
    bus = [c for c in L.connections if c.get('_bus')]
    ty = bus[0]['computed_path']['points'][2][1]
    for b in boxes:
        assert not (b['y'] < ty < b['y'] + b['h']), \
            f"la troncal (y={ty}) atraviesa la caja {b['id']}"


def test_below_threshold_stays_pairwise():
    L, spec = _mk_hub(2)
    layout_by_areas(L, spec)
    assert not any(c.get('_bus') for c in L.connections), \
        'con 2 áreas destino no hay bus'
    assert all(c.get('_inter_area') for c in L.connections), \
        'el ruteo par-a-par sigue cubriendo los enlaces'
