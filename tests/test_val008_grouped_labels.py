"""BUGS-VAL-008 (X93) — el contador `labels` ve las etiquetas estructurales.

Dos mitades del punto ciego del tabernero (labels=0 con 28 pares reales):
1. En vistas agrupadas (§I27/§I28) las etiquetas de nodo no viven en
   `label_positions` (son estructurales: `draw_area_node_labels`) — el
   detector ahora sintetiza su bbox REAL y las mide.
2. Sólo el optimizer de AUTO poblaba `_collision_pairs`; con hier el
   contador oficial reportaba 0 siempre — `quality_counters` ahora mide
   bajo demanda si nadie midió.
"""

from AlmaGag.config import ICON_HEIGHT, ICON_WIDTH
from AlmaGag.layout import Layout
from AlmaGag.layout.collision import CollisionDetector
from AlmaGag.layout.geometry import GeometryCalculator
from AlmaGag.layout.metrics import quality_counters


def _grouped_layout():
    """Dos nodos en fila apretada + un label de conexión ENCIMA del título
    del vecino — el patrón exacto del tabernero."""
    els = [
        {'id': 'a', 'type': 'server', 'label': 'Proveedor crítico primario',
         'x': 100, 'y': 100},
        {'id': 'b', 'type': 'server', 'label': 'Insumos', 'x': 300, 'y': 100},
    ]
    conns = [{'from': 'a', 'to': 'b', 'label': 'suministro principal'}]
    L = Layout(elements=els, connections=conns,
               canvas={'width': 800, 'height': 400})
    L.areas = [{'id': 'z1', 'label': 'Zona', 'members': ['a', 'b']}]
    # label del vecino centrado exactamente sobre el título estructural de a
    L.connection_labels['a->b'] = (
        100 + ICON_WIDTH / 2, 100 + ICON_HEIGHT + 14)
    return L


def test_structural_label_bbox_matches_drawn_geometry():
    g = GeometryCalculator()
    e = {'id': 'a', 'label': 'Uno\nDos', 'x': 100, 'y': 100}
    bb = g.get_structural_label_bbox(e)
    assert bb is not None
    x1, y1, x2, y2 = bb
    # centrado bajo el icono (draw_area_node_labels)
    assert abs((x1 + x2) / 2 - (100 + ICON_WIDTH / 2)) < 0.5
    # arranca donde arranca el texto dibujado (baseline y+ICON_HEIGHT+14)
    assert y1 == 100 + ICON_HEIGHT
    assert y2 > y1
    # sin label o sin posición → None
    assert g.get_structural_label_bbox({'id': 'x'}) is None
    assert g.get_structural_label_bbox({'id': 'x', 'label': 'L'}) is None


def test_grouped_view_counts_structural_labels():
    L = _grouped_layout()
    det = CollisionDetector(GeometryCalculator())
    bboxes = det._collect_all_bboxes(L)
    kinds = [(t, i) for _, t, i in bboxes]
    # las etiquetas estructurales de a y b están MEDIDAS pese a no vivir
    # en label_positions
    assert ('icon_label', 'a') in kinds
    assert ('icon_label', 'b') in kinds
    n, pairs = det.detect_all_collisions(L)
    overlap = [p for p in pairs if 'label' in p[2]]
    assert overlap, 'el label de conexión sobre el título estructural debe contarse'


def test_ungrouped_view_does_not_invent_labels():
    """Sin areas/lanes/matrix no hay etiquetas estructurales: el detector
    sólo mide label_positions (contrato WISH-LAYOUT-008 intacto)."""
    L = _grouped_layout()
    L.areas = None
    det = CollisionDetector(GeometryCalculator())
    kinds = [(t, i) for _, t, i in det._collect_all_bboxes(L)]
    assert ('icon_label', 'a') not in kinds
    assert ('icon_label', 'b') not in kinds


def test_quality_counters_measure_on_demand():
    """Camino hier: nadie pobló _collision_pairs → el contador mide él
    mismo en vez de reportar 0."""
    L = _grouped_layout()
    assert L._collision_pairs is None
    q = quality_counters(L)
    assert q['label_overlap'] >= 1, 'labels=0 con solapes reales es el bug'
    # y deja la medición almacenada (la cifra oficial es una sola)
    assert L._collision_pairs is not None


def test_quality_counters_respect_prior_measurement():
    """Si el optimizer YA midió (camino AUTO), el contador no re-mide."""
    L = _grouped_layout()
    L._collision_pairs = []
    q = quality_counters(L)
    assert q['label_overlap'] == 0
