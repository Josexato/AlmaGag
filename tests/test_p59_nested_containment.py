"""§P59 — la contención anidada reserva espacio real.

La grilla local de un contenedor dimensionaba las celdas a ICON_WIDTH×
ICON_HEIGHT fijos: un hijo-contenedor ya resuelto (cientos de px) aplastaba
a sus hermanos y la caja del padre cubría el amontonamiento. Ahora la celda
usa el tamaño REAL del hijo (ancho por columna, alto por fila) y con hijos
tamaño-icono se reduce exactamente al comportamiento anterior (K35 intacto).

Verifica del revisor: para todo contenedor, bbox(hijos) ⊆ caja; ningún
elemento ∉ contains intersecta la caja; en el fixture minero, cero torres
dentro del DC.
"""

import json

import pytest

from AlmaGag.generator import select_strategy
from AlmaGag.layout import Layout
from AlmaGag.layout.engine import LayoutEngine
from AlmaGag.utils import extract_item_id

FIXTURE = 'docs/diagrams/gags/mina-arquitectura-fisica.sdjf'


def _bbox(e):
    return (e['x'], e['y'], e['x'] + e.get('width', 80), e['y'] + e.get('height', 50))


def _intersects(a, b):
    return not (a[2] <= b[0] or a[0] >= b[2] or a[3] <= b[1] or a[1] >= b[3])


@pytest.fixture(scope='module')
def result():
    d = json.load(open(FIXTURE))
    L = Layout(elements=d['elements'], connections=d['connections'],
               canvas={'width': 1400, 'height': 900})
    L._strategy = select_strategy(d, 'auto')
    return LayoutEngine(verbose=False, strategy=None).optimize(L)


def _closure(container, by):
    acc = set()
    stack = [container]
    while stack:
        c = stack.pop()
        for r in c['contains']:
            i = extract_item_id(r)
            acc.add(i)
            ch = by.get(i)
            if ch and 'contains' in ch:
                stack.append(ch)
    return acc


def test_children_contained_in_box(result):
    """bbox de cada hijo ⊆ caja de su contenedor, a toda profundidad."""
    by = result.elements_by_id
    for c in result.elements:
        if 'contains' not in c:
            continue
        cb = _bbox(c)
        for r in c['contains']:
            e = by.get(extract_item_id(r))
            if not e or 'x' not in e:
                continue
            eb = _bbox(e)
            assert (eb[0] >= cb[0] and eb[1] >= cb[1]
                    and eb[2] <= cb[2] and eb[3] <= cb[3]), \
                f'{e["id"]} {eb} se sale de {c["id"]} {cb}'


def test_no_foreign_icon_inside_any_box(result):
    """Ningún icono ∉ contains intersecta una caja: cero torres en el DC."""
    by = result.elements_by_id
    for c in result.elements:
        if 'contains' not in c:
            continue
        cb = _bbox(c)
        members = _closure(c, by)
        for e in result.elements:
            if e['id'] in members or e['id'] == c['id']:
                continue
            if 'contains' in e or 'x' not in e:
                continue
            assert not _intersects(_bbox(e), cb), \
                f'intruso: {e["id"]} dentro de {c["id"]}'


def test_sibling_boxes_do_not_overlap(result):
    """Las cajas no anidadas entre sí no se solapan (super-nodos rígidos)."""
    by = result.elements_by_id
    containers = [e for e in result.elements if 'contains' in e]
    for i, a in enumerate(containers):
        ca = _closure(a, by)
        for b in containers[i + 1:]:
            if b['id'] in ca or a['id'] in _closure(b, by):
                continue
            assert not _intersects(_bbox(a), _bbox(b)), \
                f'cajas solapadas: {a["id"]} vs {b["id"]}'


def test_nested_cell_respects_child_size():
    """Unidad: un hijo-contenedor de 300×200 dentro de una grilla no pisa a
    sus hermanos icono (celdas por tamaño real)."""
    d = {'elements': [
        {'id': 'zona', 'type': 'area', 'label': 'Zona',
         'contains': ['sub', 'a', 'b', 'c']},
        {'id': 'sub', 'type': 'building', 'label': 'Sub',
         'contains': ['x', 'y']},
        {'id': 'x', 'type': 'server', 'label': 'X'},
        {'id': 'y', 'type': 'server', 'label': 'Y'},
        {'id': 'a', 'type': 'server', 'label': 'A'},
        {'id': 'b', 'type': 'server', 'label': 'B'},
        {'id': 'c', 'type': 'server', 'label': 'C'},
    ], 'connections': []}
    L = Layout(elements=d['elements'], connections=[],
               canvas={'width': 1200, 'height': 900})
    L._strategy = select_strategy(d, 'auto')
    res = LayoutEngine(verbose=False, strategy=None).optimize(L)
    by = res.elements_by_id
    sub = _bbox(by['sub'])
    assert sub[2] - sub[0] > 100          # el sub-contenedor creció de verdad
    for i in ('a', 'b', 'c'):
        assert not _intersects(_bbox(by[i]), sub), f'{i} pisa al sub-contenedor'
