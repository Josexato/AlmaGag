"""WISH-LAYOUT-025 — escenografía asistida.

El motor mide el contenido por área, condensa el grafo y lee las señales
narrativas para RECOMENDAR un canvas.partition con razones nombradas.
Recomienda, jamás impone (§R): la salida es un plan declarable que
layout_by_areas consume tal cual.
"""

from AlmaGag.layout import Layout
from AlmaGag.layout.strategies.hier.areas import layout_by_areas
from AlmaGag.layout.strategies.hier.escenografia import suggest_partition


def _mk():
    """Mini-tabernero: feeder, columna vertebral de 3 (con journey),
    destino y un hub hacia 3 áreas."""
    els, conns = [], []

    def area(aid, n):
        ids = []
        for i in range(n):
            eid = f'{aid}n{i}'
            els.append({'id': eid, 'type': 'server', 'label': f'{aid} {i}'})
            ids.append(eid)
        for u, v in zip(ids, ids[1:]):
            conns.append({'from': u, 'to': v})
        return {'id': aid, 'label': f'Área {aid}', 'members': ids}
    spec = [area('feed', 2), area('a', 2), area('b', 3), area('c', 2),
            area('sink', 2), area('hub', 3)]
    conns += [
        {'from': 'feedn1', 'to': 'an0'},          # feeder → columna
        {'from': 'an1', 'to': 'bn0'},
        {'from': 'bn2', 'to': 'cn0'},
        {'from': 'cn1', 'to': 'sinkn0'},          # columna → destino
        {'from': 'hubn0', 'to': 'an0'},           # hub → 3 áreas
        {'from': 'hubn1', 'to': 'bn0'},
        {'from': 'hubn2', 'to': 'cn0'},
    ]
    d = {'elements': els, 'connections': conns, 'areas': spec,
         'journeys': [{'id': 'j', 'label': 'J',
                       'path': ['an0', 'an1', 'bn0', 'bn2', 'cn0', 'cn1']}]}
    return d


def test_suggestion_reads_the_narrative():
    out = suggest_partition(_mk())
    assert out is not None
    splits = {s['area']: s for s in out['partition']['splits']}
    assert set(splits) == {'feed', 'a', 'b', 'c', 'sink', 'hub'}
    # el hub va como banda de ancho completo (estirado al ancho de grilla)
    total_w = out['partition']['ratio'][0]
    assert abs(splits['hub']['size'][0] - total_w) < 0.2, \
        'el hub debe ser banda de ancho completo'
    # la columna vertebral queda contigua en su fila (b a la derecha de a)
    assert splits['b'].get('at') == 'right_of' and splits['b']['of'] == 'a'
    assert splits['c'].get('at') == 'right_of' and splits['c']['of'] == 'b'
    # las razones nombran la columna y el hub
    razones = ' '.join(out['razones'])
    assert 'columna vertebral' in razones and 'hub' in razones


def test_suggestion_is_consumable_as_declared():
    """El plan sugerido alimenta layout_by_areas SIN caídas: todas las
    áreas caen en celdas y el contenido queda dentro de su caja."""
    d = _mk()
    out = suggest_partition(d)
    L = Layout(elements=d['elements'], connections=d['connections'],
               canvas={'width': 1400, 'height': 900,
                       'partition': out['partition']})
    boxes = {b['id']: b for b in layout_by_areas(L, d['areas'])}
    area_of = {m: a['id'] for a in d['areas'] for m in a['members']}
    for e in L.elements:
        b = boxes[area_of[e['id']]]
        assert b['x'] - 1 <= e['x'] and b['y'] - 1 <= e['y'], \
            f"{e['id']} fuera de su celda"


def test_declared_roles_win():
    d = _mk()
    for a in d['areas']:
        a['role'] = 'chain'
    d['areas'][0]['role'] = 'control'
    out = suggest_partition(d)
    assert any('roles declarados' in r for r in out['razones'])


def test_too_few_areas_is_named(caplog):
    import logging
    with caplog.at_level(logging.WARNING, logger='AlmaGag'):
        out = suggest_partition({'elements': [], 'connections': [],
                                 'areas': [{'id': 'x', 'members': []}]})
    assert out is None
    assert '≥2 áreas' in caplog.text
