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


def _trunk_y(bus):
    """y de la troncal compartida: la y del primer punto tras el puerto de
    salida en el ramal más largo (los cortos pueden colapsar por dedupe)."""
    longest = max(bus, key=lambda c: len(c['computed_path']['points']))
    return longest['computed_path']['points'][1][1]


def test_hub_with_three_areas_becomes_bus():
    L, spec = _mk_hub(3)
    layout_by_areas(L, spec)
    bus = [c for c in L.connections if c.get('_bus') == 'hub']
    assert len(bus) == 3, 'los 3 ramales deben ser del bus'
    # troncal única: TODOS los ramales tocan la misma y de troncal
    ty = _trunk_y(bus)
    for c in bus:
        pts = c['computed_path']['points']
        # el ramal TOCA la troncal: un vértice en ty o un tramo vertical
        # que la cruza (dedupe colapsa los colineales)
        touches = any(abs(y - ty) < 0.5 for _, y in pts) or any(
            min(y1, y2) - 0.5 <= ty <= max(y1, y2) + 0.5
            for (_, y1), (_, y2) in zip(pts, pts[1:]))
        assert touches, f'ramal sin contacto con la troncal y={ty}: {pts}'
        # ortogonalidad
        for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
            assert abs(x1 - x2) < 0.5 or abs(y1 - y2) < 0.5, 'tramo diagonal'


def test_trunk_lives_in_the_corridor():
    L, spec = _mk_hub(3)
    boxes = layout_by_areas(L, spec)
    bus = [c for c in L.connections if c.get('_bus')]
    ty = _trunk_y(bus)
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
