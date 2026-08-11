"""WISH-ROUTE-004 (W87) — el tramo que atraviesa el label de su propio
extremo se VE, se nombra y P61 lo resuelve cuando hay lado limpio.

Antes, el cruce con el label del propio extremo estaba exento en el
detector y en el score de P61: la dashed resumen→cron cortaba
«Cron. Val.» y nadie lo veía. Ahora:
- el detector emite pares `label_vs_own_line` (canal APARTE: no suman al
  agregado ni a label_overlap — §H6);
- el score de P61 los pesa 0.5 (mudarse a un lugar LIMPIO sí; crear un
  solape nuevo para evitarlos, no);
- un candidato con coordenada negativa muere (el recorte O51 sólo
  contrae: un label en y<0 sale cortado de la lámina).
"""

import json

from AlmaGag.generator import select_strategy
from AlmaGag.layout import Layout
from AlmaGag.layout.collision import CollisionDetector
from AlmaGag.layout.considerations import extract_considerations
from AlmaGag.layout.engine import LayoutEngine
from AlmaGag.layout.geometry import GeometryCalculator
from AlmaGag.layout.metrics import quality_counters


def test_detector_names_own_line_traversal_without_counting():
    """El par se nombra; el agregado no sube (canal aparte)."""
    L = Layout(elements=[{'id': 'a', 'type': 'server', 'label': 'A'},
                         {'id': 'b', 'type': 'server', 'label': 'Destino'}],
               connections=[{'from': 'a', 'to': 'b'}],
               canvas={'width': 600, 'height': 600})
    by = L.elements_by_id
    by['a']['x'], by['a']['y'] = 200, 400
    by['b']['x'], by['b']['y'] = 200, 100
    # label de b DEBAJO de su icono; la conexión sube atravesándolo entero
    L.label_positions = {'b': (240.0, 185.0, 'middle', 'bottom')}
    L.connections[0]['computed_path'] = {
        'points': [(240, 400), (240, 150)]}
    det = CollisionDetector(GeometryCalculator())
    count, pairs = det.detect_all_collisions(L)
    own = [p for p in pairs if p[2] == 'label_vs_own_line']
    assert own == [('b', 'a->b', 'label_vs_own_line')]
    assert count == 0, 'el canal propio no debe sumar al agregado'


def test_p61_clears_traversed_label_when_clean_side_exists():
    """Cadena con flow up: la llegada por abajo atraviesa el label bottom
    del destino; P61 lo muda a un lado limpio → label_own_line 0."""
    d = {'elements': [
            {'id': 'top', 'type': 'server', 'label': 'Consolidado\nfinal'},
            {'id': 'mid', 'type': 'server', 'label': 'Etapa media\ncon detalle'},
            {'id': 'src', 'type': 'server', 'label': 'Fuente\nde datos'}],
         'connections': [{'from': 'src', 'to': 'mid'},
                         {'from': 'mid', 'to': 'top'}],
         'canvas': {'width': 900, 'height': 900, 'flow': 'up'}}
    L = Layout(elements=d['elements'], connections=d['connections'],
               canvas=d['canvas'])
    L._strategy = select_strategy(d, None)
    L._considerations = extract_considerations(d)
    out = LayoutEngine(verbose=False, strategy=None).optimize(L)
    q = quality_counters(out)
    assert 'label_own_line' in q
    assert q['label_own_line'] == 0, \
        f"quedaron atravesados con lados libres: " \
        f"{[p for p in (out._collision_pairs or []) if p[2] == 'label_vs_own_line']}"
    # y ningún label quedó fuera del lienzo (candidatos negativos muertos)
    geo = GeometryCalculator()
    for eid, pi in out.label_positions.items():
        bb = geo.get_label_bbox_stored(out.elements_by_id[eid], pi)
        if bb:
            assert bb[0] >= 0 and bb[1] >= 0, f'label de {eid} fuera del lienzo'
