"""BUGS-ROUTE-010 — Z96 llega a AUTO: la ruta no atraviesa lo que no es
suyo, ahora también en el post-ruteo de AutoRoutingPolicy.

Tres primitivas encadenadas al final de cada re-ruteo: rodeo de
polilíneas que CODEAN dentro de una caja ajena (route_around_boxes — el
dodge por segmentos no las ve), desvío de travesías de un solo tramo
(dodge_boxes) y recorte de codos en L (relocate_corners). Obstáculos:
contenedores ajenos (entrar no es atravesar), el ICONO DE CABECERA de
todo contenedor, e iconos ajenos. Best-effort con precedente Z95: el
candidato desviado solo gana si REDUCE las cajas ofendidas (§H6 cuenta
el roce parcial, y una pata de desvío puede rozar al vecino).
Caso real: cakephp-mvc arista×nodo 4→0 y 06-flujo 5 cruces→1.
"""

from AlmaGag.config import ICON_WIDTH, ICON_HEIGHT, CONTAINER_PADDING
from AlmaGag.layout.layout import Layout
from AlmaGag.layout.strategies.auto.routing_policy import _dodge_foreign_boxes


def _mk(conn_points):
    els = [
        {'id': 'a', 'type': 'server', 'label': 'A', 'x': 0.0, 'y': 150.0},
        {'id': 'b', 'type': 'server', 'label': 'B', 'x': 700.0, 'y': 150.0},
        {'id': 'm1', 'type': 'server', 'label': 'M1', 'x': 350.0, 'y': 160.0},
        {'id': 'M', 'type': 'building', 'label': 'Caja', 'contains': ['m1'],
         'x': 250.0, 'y': 80.0, 'width': 280.0, 'height': 220.0,
         '_is_container_calculated': True},
    ]
    conns = [{'from': 'a', 'to': 'b',
              'computed_path': {'type': 'polyline', 'points': conn_points}}]
    return Layout(elements=els, connections=conns,
                  canvas={'width': 900, 'height': 500})


def _inside(p, b):
    return b[0] < p[0] < b[2] and b[1] < p[1] < b[3]


def test_elbow_inside_foreign_container_is_rerouted():
    """La polilínea que entra a la caja ajena, codea adentro y sale (la
    clase que el dodge por segmentos NO ve) se reemplaza por el rodeo."""
    pts = [(ICON_WIDTH, 170.0), (380.0, 170.0), (380.0, 190.0),
           (700.0, 190.0)]
    L = _mk(pts)
    _dodge_foreign_boxes(L)
    out = L.connections[0]['computed_path']['points']
    box = (250.0, 80.0, 530.0, 300.0)
    assert not any(_inside(p, box) for p in out), out
    for p, q in zip(out, out[1:]):
        assert abs(p[0] - q[0]) < 0.5 or abs(p[1] - q[1]) < 0.5, \
            f'tramo diagonal tras el rodeo: {p}→{q}'


def test_header_icon_is_an_obstacle():
    """El icono de cabecera del contenedor no es atravesable ni siquiera
    por rutas que ENTRAN legítimamente a la caja."""
    els = [
        {'id': 'out', 'type': 'server', 'label': 'O',
         'x': 262.0 - ICON_WIDTH / 2, 'y': 0.0},
        {'id': 'm1', 'type': 'server', 'label': 'M1', 'x': 230.0, 'y': 240.0},
        {'id': 'M', 'type': 'building', 'label': 'Caja', 'contains': ['m1'],
         'x': 250.0, 'y': 80.0, 'width': 280.0, 'height': 220.0,
         '_is_container_calculated': True},
    ]
    hx, hy = 250.0 + CONTAINER_PADDING, 80.0 + CONTAINER_PADDING
    header = (hx, hy, hx + ICON_WIDTH, hy + ICON_HEIGHT)
    x_mid = (header[0] + header[2]) / 2
    conns = [{'from': 'out', 'to': 'm1',
              'computed_path': {'type': 'polyline',
                                'points': [(x_mid, ICON_HEIGHT),
                                           (x_mid, 240.0)]}}]
    L = Layout(elements=els, connections=conns,
               canvas={'width': 700, 'height': 500})
    _dodge_foreign_boxes(L)
    out = L.connections[0]['computed_path']['points']
    from AlmaGag.layout.dodge import seg_crosses_box
    assert not any(seg_crosses_box(p, q, header)
                   for p, q in zip(out, out[1:])), out
