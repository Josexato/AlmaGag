"""
Tests del algoritmo de layout jerárquico `hier` (WISH-LAF-002 Fase 1).

Verifican §A (niveles min-parent, satélites, tomas) y §B (columnas: sin
solapes, canvas compacto) usando 14-stresstest como caso de regresión.
"""

import json
import os
import tempfile

from AlmaGag.layout import Layout
from AlmaGag.layout.hier.leveling import compute_levels
from AlmaGag.layout.hier.optimizer import HierLayoutOptimizer

STRESS = 'docs/diagrams/gags/14-stresstest.sdjf'


def _stress_data():
    return json.load(open(STRESS))


# ---------- §A leveling ----------

def test_levels_min_parent_stresstest():
    d = _stress_data()
    lv = compute_levels(d['elements'], d['connections'])
    L = lv.level
    # min-parent: F e I mismo nivel (ambos de H); niveles 0-5 contiguos
    assert L['ElemtF'] == L['ElemtI'] == 3
    assert L['ElemtA'] == 0 and L['ElemtD'] == 1
    assert L['ElemtM'] == 5
    ints = sorted({int(v) for v in L.values()})
    assert ints == [0, 1, 2, 3, 4, 5]


def test_satellite_L_beside_H():
    d = _stress_data()
    lv = compute_levels(d['elements'], d['connections'])
    assert lv.satellites.get('ElemtL') == 'ElemtH'
    assert lv.level['ElemtL'] == lv.level['ElemtH']  # mismo nivel que el padre


def test_side_feeders_half_level():
    d = _stress_data()
    lv = compute_levels(d['elements'], d['connections'])
    assert lv.side_feeders.get('ElemtB') == 'ElemtE'
    assert lv.side_feeders.get('ElemtC') == 'ElemtG'
    assert lv.level['ElemtB'] == lv.level['ElemtE'] - 0.5
    assert lv.level['ElemtC'] == lv.level['ElemtG'] - 0.5


def test_back_edge_detected():
    d = _stress_data()
    lv = compute_levels(d['elements'], d['connections'])
    assert ('ElemtK', 'ElemtI') in lv.back_edges


def test_pure_fanout_not_satellites():
    """Un fan-out puro (padre sin hijo no-hoja) NO vuelve satélites a las
    hojas: §A2 exige que el padre continúe el flujo."""
    lv = compute_levels(
        [{'id': 'A'}, {'id': 'B'}, {'id': 'C'}, {'id': 'D'}],
        [{'from': 'A', 'to': 'B'}, {'from': 'A', 'to': 'C'}, {'from': 'A', 'to': 'D'}],
    )
    assert lv.satellites == {}
    assert lv.level['B'] == lv.level['C'] == lv.level['D'] == 1


# ---------- §B columns ----------

def _optimize(data):
    L = Layout(elements=data['elements'], connections=data['connections'],
               canvas=data.get('canvas', {'width': 1400, 'height': 900}))
    L._diagram_name = 'test'
    return HierLayoutOptimizer(verbose=False).optimize(L)


def test_no_overlapping_positions():
    r = _optimize(_stress_data())
    seen = {}
    for e in r.elements:
        key = (round(e['x']), round(e['y']))
        assert key not in seen, f"{e['id']} solapa {seen.get(key)} en {key}"
        seen[key] = e['id']


def test_compact_canvas():
    """hier compacta bastante más que el layout disperso previo."""
    r = _optimize(_stress_data())
    assert r.canvas['width'] <= 1600
    assert r.canvas['height'] <= 1200


def test_hier_renders_svg():
    data = _stress_data()
    tmp = tempfile.NamedTemporaryFile(suffix='.svg', delete=False)
    tmp.close()
    from AlmaGag.generator import generate_diagram
    ok = generate_diagram(STRESS, layout_algorithm='hier', output_file=tmp.name)
    assert ok
    svg = open(tmp.name).read()
    os.unlink(tmp.name)
    assert '<svg' in svg and 'ElemtA' in svg
