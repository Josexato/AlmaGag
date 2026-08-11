"""WISH-LAYOUT-021 (X91b) — `canvas.partition`: el macro-plano declarado.

Scheme `bsp`: lista ordenada de colocaciones relativas (base + at/of) con
tamaños en PROPORCIONES — el motor escala la partición entera al contenido
real (§P59). Scheme `grid`: filas de ids (azúcar). Precedencia: partition
> role > derivación; un plan inválido se NOMBRA y cae al siguiente nivel.
"""

import logging

from AlmaGag.config import ICON_HEIGHT, ICON_WIDTH
from AlmaGag.layout import Layout
from AlmaGag.layout.strategies.hier.areas import layout_by_areas


def _mk(n_areas, per_area, partition=None):
    els, conns, spec = [], [], []
    for a in range(n_areas):
        ids = []
        for i in range(per_area):
            eid = f'a{a}n{i}'
            els.append({'id': eid, 'type': 'server', 'label': f'Nodo {a}.{i}'})
            ids.append(eid)
        for u, v in zip(ids, ids[1:]):
            conns.append({'from': u, 'to': v})
        spec.append({'id': f'z{a}', 'label': f'Área {a}', 'members': ids})
    canvas = {'width': 1400, 'height': 900}
    if partition:
        canvas['partition'] = partition
    L = Layout(elements=els, connections=conns, canvas=canvas)
    return L, spec


def test_bsp_places_cells_as_declared():
    """El ejemplo del artefacto: A1 base, A2 a su derecha, A3 a la derecha
    de A2, A4 debajo de A1 — y las proporciones se conservan."""
    part = {'scheme': 'bsp', 'ratio': [8, 4], 'splits': [
        {'area': 'z0', 'size': [3, 2], 'anchor': 'base'},
        {'area': 'z1', 'size': [3, 2], 'at': 'right_of', 'of': 'z0'},
        {'area': 'z2', 'size': [2, 2], 'at': 'right_of', 'of': 'z1'},
        {'area': 'z3', 'size': [8, 2], 'at': 'below', 'of': 'z0'}]}
    L, spec = _mk(4, 3, part)
    boxes = {b['id']: b for b in layout_by_areas(L, spec)}
    z0, z1, z2, z3 = (boxes[k] for k in ('z0', 'z1', 'z2', 'z3'))
    assert z1['x'] > z0['x'] and abs(z1['y'] - z0['y']) < 1, 'z1 derecha de z0'
    assert z2['x'] > z1['x'], 'z2 derecha de z1'
    assert z3['y'] > z0['y'] and abs(z3['x'] - z0['x']) < 1, 'z3 debajo de z0'
    # proporciones: z0 y z1 declaran el mismo ancho (3) → mismo px (±2%)
    assert abs(z0['w'] - z1['w']) / z0['w'] < 0.02
    # z3 declara 8 de ancho contra 3 de z0: la CELDA (caja + corredor
    # AREA_GAP) conserva el ratio exacto (±2%)
    from AlmaGag.layout.strategies.hier.areas import AREA_GAP
    ratio = (z3['w'] + AREA_GAP) / (z0['w'] + AREA_GAP)
    assert abs(ratio - 8 / 3) / (8 / 3) < 0.02, f'ratio {ratio:.3f} ≠ 8/3'


def test_bsp_content_fits_its_cell():
    part = {'scheme': 'bsp', 'splits': [
        {'area': 'z0', 'size': [1, 1], 'anchor': 'base'},
        {'area': 'z1', 'size': [1, 1], 'at': 'right_of', 'of': 'z0'}]}
    L, spec = _mk(2, 4, part)
    boxes = {b['id']: b for b in layout_by_areas(L, spec)}
    area_of = {m: a['id'] for a in spec for m in a['members']}
    for e in L.elements:
        b = boxes[area_of[e['id']]]
        assert b['x'] <= e['x'] and e['x'] + ICON_WIDTH <= b['x'] + b['w']
        assert b['y'] <= e['y'] and e['y'] + ICON_HEIGHT <= b['y'] + b['h']


def test_partition_wins_over_role():
    """Con partition, el role no manda: z0 (external, iría abajo) queda
    ARRIBA de z1 porque el plan lo declara base con z1 debajo."""
    part = {'scheme': 'bsp', 'splits': [
        {'area': 'z0', 'size': [2, 1], 'anchor': 'base'},
        {'area': 'z1', 'size': [2, 1], 'at': 'below', 'of': 'z0'}]}
    L, spec = _mk(2, 2, part)
    spec[0]['role'] = 'external'
    spec[1]['role'] = 'control'
    boxes = {b['id']: b for b in layout_by_areas(L, spec)}
    assert boxes['z0']['y'] < boxes['z1']['y']


def test_invalid_plan_is_named_and_falls_back(caplog):
    """of no colocado → el plan se descarta CON NOMBRE y la colocación cae
    a role/derivación (no revienta, no silencio)."""
    part = {'scheme': 'bsp', 'splits': [
        {'area': 'z0', 'size': [1, 1], 'anchor': 'base'},
        {'area': 'z1', 'size': [1, 1], 'at': 'right_of', 'of': 'zX'}]}
    L, spec = _mk(2, 2, part)
    with caplog.at_level(logging.WARNING, logger='AlmaGag'):
        boxes = layout_by_areas(L, spec)
    assert len(boxes) == 2, 'la colocación derivada debe seguir funcionando'
    assert "of='zX'" in caplog.text


def test_unknown_scheme_is_named(caplog):
    part = {'scheme': 'voronoi', 'splits': []}
    L, spec = _mk(2, 2, part)
    with caplog.at_level(logging.WARNING, logger='AlmaGag'):
        layout_by_areas(L, spec)
    assert "scheme 'voronoi'" in caplog.text


def test_grid_scheme_rows():
    part = {'scheme': 'grid', 'rows': [['z0', 'z1'], ['z2']]}
    L, spec = _mk(3, 2, part)
    boxes = {b['id']: b for b in layout_by_areas(L, spec)}
    assert abs(boxes['z0']['y'] - boxes['z1']['y']) < 1, 'z0 y z1 en fila'
    assert boxes['z2']['y'] > boxes['z0']['y'], 'z2 en la fila siguiente'


def test_area_outside_plan_is_named(caplog):
    part = {'scheme': 'bsp', 'splits': [
        {'area': 'z0', 'size': [1, 1], 'anchor': 'base'}]}
    L, spec = _mk(2, 2, part)
    with caplog.at_level(logging.WARNING, logger='AlmaGag'):
        boxes = {b['id']: b for b in layout_by_areas(L, spec)}
    assert 'z1' in caplog.text and 'fuera del plan' in caplog.text
    assert boxes['z1']['y'] > boxes['z0']['y'], 'fila propia al final'
