"""
§N46 — `near[]` se promueve a ZONA por construcción: cluster compacto, caja
sutil en el render, miembros que ni se desarman ni se pisan entre sí.
Fixtures: red-minera-antes/despues.gag (caso condestable anonimizado).
"""

import json
import math

import pytest

from AlmaGag.layout import Layout
from AlmaGag.layout.engine import LayoutEngine
from AlmaGag.generator import select_strategy, generate_diagram
from AlmaGag.layout.considerations import extract_considerations

FIXTURES = ['docs/diagrams/gags/red-minera-antes.gag',
            'docs/diagrams/gags/red-minera-despues.gag']


def _optimize(path):
    d = json.load(open(path))
    L = Layout(elements=d['elements'], connections=d['connections'],
               canvas=d.get('canvas', {}))
    L._considerations = extract_considerations(d)
    L._strategy = select_strategy(d, 'auto')
    return L._considerations, LayoutEngine(verbose=False, strategy=None).optimize(L)


@pytest.mark.parametrize('path', FIXTURES)
def test_near_groups_satisfied_by_construction(path):
    """Todo grupo near queda compacto: distancia máx entre centros ≤ 320px
    (antes del N46, condestable tenía miembros a ~730px)."""
    considerations, res = _optimize(path)
    by = res.elements_by_id
    for cons in considerations:
        if cons['kind'] != 'near':
            continue
        pts = [(by[i]['x'] + 40, by[i]['y'] + 25)
               for i in cons['ids'] if i in by and 'x' in by[i]]
        assert len(pts) >= 2
        dmax = max(math.dist(a, b) for a in pts for b in pts)
        assert dmax <= 320, f"near {cons['ids']} disperso: {dmax:.0f}px"


@pytest.mark.parametrize('path', FIXTURES)
def test_zone_members_never_overlap_each_other(path):
    """La grilla del cluster es por construcción: cero icon_vs_icon entre
    miembros de la misma zona (regresión de la cizalla de compactación)."""
    considerations, res = _optimize(path)
    zone_of = {}
    for cons in (c for c in considerations if c['kind'] == 'near'):
        for i in cons['ids']:
            zone_of[i] = tuple(cons['ids'])
    for (a, b, kind) in (res._collision_pairs or []):
        if kind == 'icon_vs_icon' and zone_of.get(a) and zone_of.get(a) == zone_of.get(b):
            raise AssertionError(f"miembros de zona solapados: {a} vs {b}")


def test_zone_boxes_drawn(tmp_path):
    """El SVG dibuja una caja punteada por zona (fondo)."""
    out = str(tmp_path / 'rm.svg')
    assert generate_diagram(FIXTURES[0], output_file=out, layout_algorithm='select')
    svg = open(out).read()
    # 3 zonas near en el fixture "antes" → ≥3 rects con el estilo de zona
    assert svg.count('stroke-dasharray="4,4"') + svg.count("stroke-dasharray='4,4'") >= 3


def test_fixtures_are_anonymized():
    """Guardia: las fixtures no traen identificadores reales de cliente."""
    for p in FIXTURES:
        t = open(p, encoding='utf-8').read()
        for leak in ('82966', '83544', '24072602', '25245086', '24809938',
                     'Condestable', 'SPM Peru'):
            assert leak not in t, f"{p} contiene dato real: {leak}"
