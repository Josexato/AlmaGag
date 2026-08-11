"""WISH-DRAW-007 (X93, mitad visible) — anclas §G23 en cascada.

Tres piezas: (1) lo dibujado es lo medido — el bbox del rótulo ANCLADO se
mide en `_label_anchor`, no en el punto medio del path; (2) el ancla no
pisa títulos estructurales ni iconos si hay lugar limpio en la cascada
(pasos de CASCADE px por la PERPENDICULAR del primer segmento); (3) dos
aristas que comparten corredor apilan sus rótulos separados.
"""

from AlmaGag.layout import Layout
from AlmaGag.layout.geometry import GeometryCalculator
from AlmaGag.layout.strategies.hier.labels import (
    CASCADE, assign_connection_label_anchors, _title_boxes)


def _intersects(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def test_anchored_bbox_is_measured_at_the_anchor():
    g = GeometryCalculator()
    L = Layout(elements=[{'id': 'a'}, {'id': 'b'}],
               connections=[{'from': 'a', 'to': 'b', 'label': 'Sí',
                             '_label_anchor': (200.0, 300.0)}],
               canvas={'width': 800, 'height': 600})
    bb = g.get_connection_label_bbox(L, L.connections[0])
    assert bb[0] <= 200 <= bb[2] and bb[1] <= 300 <= bb[3], \
        'el bbox debe rodear el ancla dibujada, no el punto medio del path'


def _mk_decision_case():
    """Decisión con título ancho y salida vertical hacia el nodo de abajo —
    el pasillo emparedado del caso activacion (Sí sobre el título)."""
    els = [
        {'id': 'gw', 'type': 'decision', 'x': 400, 'y': 500,
         'label': '¿Se tiene\naprobación?'},
        {'id': 'dst', 'type': 'server', 'x': 400, 'y': 610,
         'label': 'Carga costos'},
    ]
    conns = [{'from': 'gw', 'to': 'dst', 'label': 'Sí',
              'computed_path': {'type': 'polyline',
                                'points': [(440, 550), (440, 610)]}}]
    return Layout(elements=els, connections=conns,
                  canvas={'width': 900, 'height': 900})


def test_anchor_escapes_structural_title():
    L = _mk_decision_case()
    assign_connection_label_anchors(L)
    c = L.connections[0]
    bb = GeometryCalculator().get_connection_label_bbox(L, c)
    for tb in _title_boxes(L.elements):
        assert not _intersects(bb, tb), \
            f'el ancla {c["_label_anchor"]} sigue sobre un título {tb}'


def test_parallel_labels_stack_apart():
    """Dos aristas con el MISMO primer segmento horizontal: sus anclas no
    se pisan — la segunda cae a otro escalón de la cascada."""
    els = [{'id': s, 'type': 'server', 'x': x, 'y': 100,
            'label': f'Nodo {s}'} for s, x in
           (('a', 100), ('b', 500), ('c', 100), ('d', 500))]
    conns = [
        {'from': 'a', 'to': 'b', 'label': 'suministro principal',
         'computed_path': {'type': 'polyline',
                           'points': [(180, 125), (500, 125)]}},
        {'from': 'c', 'to': 'd', 'label': 'respaldo veinte',
         'computed_path': {'type': 'polyline',
                           'points': [(180, 125), (500, 125)]}},
    ]
    L = Layout(elements=els, connections=conns,
               canvas={'width': 900, 'height': 600})
    assign_connection_label_anchors(L)
    g = GeometryCalculator()
    b1 = g.get_connection_label_bbox(L, L.connections[0])
    b2 = g.get_connection_label_bbox(L, L.connections[1])
    assert not _intersects(b1, b2), 'los rótulos gemelos no deben pisarse'
    dy = abs(L.connections[0]['_label_anchor'][1]
             - L.connections[1]['_label_anchor'][1])
    assert dy >= CASCADE - 0.5, f'separación vertical {dy} < {CASCADE}'
