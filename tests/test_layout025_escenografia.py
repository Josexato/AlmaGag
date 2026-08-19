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


def _mk_zonas_contenedores():
    """Patrón ARCH-009: 2 zonas cuyos miembros son contenedores; las
    conexiones viajan entre los HIJOS."""
    return {
        'elements': [
            {'id': 'c1', 'label': 'Caja Uno', 'contains': ['n1', 'n2']},
            {'id': 'c2', 'label': 'Caja Dos', 'contains': ['n3']},
            {'id': 'c3', 'label': 'Caja Tres', 'contains': ['n4']},
            {'id': 'n1', 'type': 'server', 'label': 'N1'},
            {'id': 'n2', 'type': 'server', 'label': 'N2'},
            {'id': 'n3', 'type': 'server', 'label': 'N3'},
            {'id': 'n4', 'type': 'database', 'label': 'N4'},
        ],
        'connections': [
            {'from': 'n1', 'to': 'n2'},          # interno (c1, Z1)
            {'from': 'n2', 'to': 'n3'},          # interno (Z1: c1→c2)
            {'from': 'n4', 'to': 'n1'},          # entre áreas (Z2→Z1)
            {'from': 'n4', 'to': 'n3'},          # entre áreas (Z2→Z1)
            {'from': 'n4', 'to': 'n2'},          # entre áreas (Z2→Z1)
        ],
        'areas': [
            {'id': 'Z1', 'label': 'Zona Uno', 'members': ['c1', 'c2']},
            {'id': 'Z2', 'label': 'Zona Dos', 'members': ['c3']},
        ],
    }


def test_tabla_de_conectividad_del_autor():
    """LAYOUT-027: la tabla que el autor armó a mano en Excel, emitida por
    el motor — internos | entre-áreas | área, con herencia ARCH-009."""
    from AlmaGag.layout.strategies.hier.escenografia import connectivity_table
    filas, hallazgos = connectivity_table(_mk_zonas_contenedores())
    por_id = {f[0]: f for f in filas}
    assert por_id['n1'] == ('n1', 1, 1, 'Z1')
    assert por_id['n2'] == ('n2', 2, 1, 'Z1')
    assert por_id['n3'] == ('n3', 1, 1, 'Z1')
    assert por_id['n4'] == ('n4', 0, 3, 'Z2')
    # n4: 0 internos y 3 entre áreas → hub puro, nombrado
    assert any('hub puro' in h and 'n4' in h for h in hallazgos)


def test_escenografia_ve_a_traves_de_los_contenedores():
    """La herencia ARCH-009 cura la ceguera: el condensado de zonas con
    contenedores ya no es vacío — la dirección Z2→Z1 se mide."""
    out = suggest_partition(_mk_zonas_contenedores())
    assert out is not None
    # el condensado ya no es vacío: la cadena Z2 → Z1 se detecta como
    # columna vertebral (antes de la herencia, ninguna razón veía enlaces)
    assert any('Z2 → Z1' in r for r in out['razones']), out['razones']
