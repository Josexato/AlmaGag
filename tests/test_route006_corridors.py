"""WISH-ROUTE-006 — ruteo por corredores de la macro-grilla.

Toda ruta inter-área (bus incluido) trata las cajas ajenas como
obstáculos: viaja por los pasillos horizontales entre filas y cruza las
filas por los huecos verticales entre cajas — jamás a través de una caja
ajena. La última milla dentro de la caja propia tampoco atraviesa
hermanos: si la columna está bloqueada, sale/entra por el costado.
Tabernero: arista×nodo 33→12, labels 123→51, W83 10→6 (los que quedan
son intra-área, otra causa).
"""

from AlmaGag.config import ICON_HEIGHT, ICON_WIDTH
from AlmaGag.layout import Layout
from AlmaGag.layout.strategies.hier.areas import layout_by_areas


def _mk_three_rows():
    """Tres filas apiladas (roles): un enlace de la fila de abajo a la de
    arriba DEBE rodear la fila del medio, no atravesarla."""
    els, conns, spec = [], [], []
    for a, role in ((0, 'control'), (1, 'chain'), (2, 'external')):
        ids = []
        for i in range(3):
            eid = f'a{a}n{i}'
            els.append({'id': eid, 'type': 'server',
                        'label': f'Nodo {a}.{i} de prueba'})
            ids.append(eid)
        for u, v in zip(ids, ids[1:]):
            conns.append({'from': u, 'to': v})
        spec.append({'id': f'z{a}', 'label': f'Área {a}', 'members': ids,
                     'role': role})
    # el enlace que antes perforaba: fila 2 (abajo) → fila 0 (arriba)
    conns.append({'from': 'a2n1', 'to': 'a0n1', 'label': 'atajo'})
    L = Layout(elements=els, connections=conns,
               canvas={'width': 1400, 'height': 1200})
    return L, spec


def _segments(c):
    pts = c['computed_path']['points']
    return list(zip(pts, pts[1:]))


def _seg_crosses_box(seg, b, pad=1.0):
    (x1, y1), (x2, y2) = seg
    lo_x, hi_x = min(x1, x2), max(x1, x2)
    lo_y, hi_y = min(y1, y2), max(y1, y2)
    return (lo_x < b['x'] + b['w'] - pad and b['x'] + pad < hi_x
            and lo_y < b['y'] + b['h'] - pad and b['y'] + pad < hi_y)


def test_inter_area_route_avoids_foreign_boxes():
    L, spec = _mk_three_rows()
    boxes = layout_by_areas(L, spec)
    c = next(c for c in L.connections if c.get('label') == 'atajo')
    assert c.get('_inter_area')
    own = {'z2', 'z0'}
    for seg in _segments(c):
        for b in boxes:
            if b['id'] in own:
                continue
            assert not _seg_crosses_box(seg, b), \
                f"el tramo {seg} atraviesa la caja ajena {b['id']}"
    # y es ortogonal
    for (x1, y1), (x2, y2) in _segments(c):
        assert abs(x1 - x2) < 0.5 or abs(y1 - y2) < 0.5, 'tramo diagonal'


def test_last_mile_avoids_siblings():
    """La salida/entrada no atraviesa hermanos de la propia caja: ningún
    tramo del enlace pisa el icono de un nodo que no sea sus extremos."""
    L, spec = _mk_three_rows()
    layout_by_areas(L, spec)
    by = {e['id']: e for e in L.elements}
    c = next(c for c in L.connections if c.get('label') == 'atajo')
    ends = {c['from'], c['to']}
    for seg in _segments(c):
        for e in L.elements:
            if e['id'] in ends or 'x' not in e:
                continue
            nb = {'x': e['x'], 'y': e['y'], 'w': ICON_WIDTH, 'h': ICON_HEIGHT}
            assert not _seg_crosses_box(seg, nb), \
                f"el tramo {seg} pisa el icono de {e['id']}"


def test_direct_route_between_same_row_neighbors_survives():
    """Vecinos de la MISMA fila sin nada en el medio siguen con la ruta
    directa L→R (el corredor entre ellos ya es limpio)."""
    els = [{'id': f'n{i}', 'type': 'server', 'label': f'N{i}'}
           for i in range(2)]
    conns = [{'from': 'n0', 'to': 'n1'}]
    spec = [{'id': 'za', 'label': 'A', 'members': ['n0']},
            {'id': 'zb', 'label': 'B', 'members': ['n1']}]
    L = Layout(elements=els, connections=conns,
               canvas={'width': 900, 'height': 400})
    layout_by_areas(L, spec)
    c = L.connections[0]
    a, b = c['_from_port'], c['_to_port']
    # sale por la derecha y entra por la izquierda (misma y de puertos)
    assert abs(a[1] - b[1]) < 60, 'la ruta directa no debería subir al corredor'


def test_independent_routes_get_distinct_lanes():
    """WISH-ROUTE-007: dos rutas independientes que comparten corredor van
    en carriles distintos (y de tramo horizontal separadas ≥8px); los
    ramales de un MISMO bus sí comparten su troncal."""
    els, conns, spec = [], [], []
    for a, role in ((0, 'control'), (1, 'chain'), (2, 'external')):
        ids = []
        for i in range(2):
            eid = f'a{a}n{i}'
            els.append({'id': eid, 'type': 'server', 'label': f'N{a}.{i}'})
            ids.append(eid)
        conns.append({'from': ids[0], 'to': ids[1]})
        spec.append({'id': f'z{a}', 'label': f'Z{a}', 'members': ids,
                     'role': role})
    # dos rutas INDEPENDIENTES fila 0 → fila 2 (comparten los corredores)
    conns.append({'from': 'a0n0', 'to': 'a2n0'})
    conns.append({'from': 'a0n1', 'to': 'a2n1'})
    L = Layout(elements=els, connections=conns,
               canvas={'width': 1200, 'height': 1200})
    layout_by_areas(L, spec)
    inter = [c for c in L.connections if c.get('_inter_area')]
    assert len(inter) == 2
    # las y de sus tramos horizontales largos no coinciden
    def horiz_ys(c):
        pts = c['computed_path']['points']
        return {round(y1, 1) for (x1, y1), (x2, y2)
                in zip(pts, pts[1:])
                if abs(y1 - y2) < 0.5 and abs(x1 - x2) > 30}
    ys0, ys1 = horiz_ys(inter[0]), horiz_ys(inter[1])
    if ys0 and ys1:
        assert not (ys0 & ys1), \
            f'rutas independientes montadas en el mismo carril: {ys0 & ys1}'
