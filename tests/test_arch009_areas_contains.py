"""WISH-ARCH-009 — contenedores como miembros de área (hier).

«Zonas para la escenografía, contenedores para la profundidad» (el autor,
18-ago-2026). Antes `contains` forzaba AUTO y anulaba las áreas; ahora la
vista por ámbitos monta los contenedores DENTRO de sus áreas: el contenedor
se mide bottom-up (sub-layout de sus hijos) y entra a la grilla del área
como nodo gordo con su caja dibujada = la reservada.
"""

import copy
import json

from AlmaGag.generator import select_strategy
from AlmaGag.layout.layout import Layout
from AlmaGag.layout.strategies.hier.areas import layout_by_areas
from AlmaGag.config import ICON_WIDTH, ICON_HEIGHT


DATA = {
    'elements': [
        {'id': 'c1', 'type': 'building', 'label': 'Caja Uno',
         'contains': ['n1', 'n2']},
        {'id': 'c2', 'type': 'building', 'label': 'Caja Dos',
         'contains': ['n3']},
        {'id': 'c3', 'type': 'building', 'label': 'Caja Tres',
         'contains': ['n4']},
        {'id': 'n1', 'type': 'server', 'label': 'Nodo Uno'},
        {'id': 'n2', 'type': 'server', 'label': 'Nodo Dos'},
        {'id': 'n3', 'type': 'database', 'label': 'Nodo Tres'},
        {'id': 'n4', 'type': 'user', 'label': 'Nodo Cuatro'},
    ],
    'connections': [
        {'from': 'n1', 'to': 'n2'},          # intra-contenedor (c1)
        {'from': 'n2', 'to': 'n3'},          # c1 → c2, misma área
        {'from': 'n3', 'to': 'n4'},          # Z1 → Z2, inter-área
    ],
    'areas': [
        {'id': 'Z1', 'label': 'Zona Uno', 'members': ['c1', 'c2']},
        {'id': 'Z2', 'label': 'Zona Dos', 'members': ['c3']},
    ],
}


def _run():
    data = copy.deepcopy(DATA)
    L = Layout(elements=data['elements'], connections=data['connections'],
               canvas={'width': 1400, 'height': 900})
    boxes = layout_by_areas(L, data['areas'])
    return L, boxes


def test_areas_mas_contains_selecciona_hier():
    """La mezcla áreas+contains ya no cede a AUTO: las áreas ganan."""
    assert select_strategy(copy.deepcopy(DATA), 'auto') == 'hier'


def test_contains_sin_areas_sigue_en_auto():
    data = copy.deepcopy(DATA)
    del data['areas']
    assert select_strategy(data, 'auto') == 'auto'


def test_zonas_se_dibujan_y_los_hijos_no_son_solo():
    """Las cajas devueltas son las 2 zonas declaradas — ni los hijos ni los
    contenedores se derraman como áreas singleton."""
    _L, boxes = _run()
    reales = {b['id'] for b in boxes if not b.get('solo')}
    assert reales == {'Z1', 'Z2'}
    solos = [b['id'] for b in boxes if b.get('solo')]
    assert solos == []


def test_contenedor_dentro_de_su_zona_y_hijos_dentro_del_contenedor():
    L, boxes = _run()
    by_id = {e['id']: e for e in L.elements}
    zona = {b['id']: b for b in boxes}
    for cid, zid in (('c1', 'Z1'), ('c2', 'Z1'), ('c3', 'Z2')):
        c = by_id[cid]
        z = zona[zid]
        assert c.get('_is_container_calculated'), cid
        assert c['width'] > ICON_WIDTH and c['height'] > ICON_HEIGHT
        assert z['x'] <= c['x'] and c['x'] + c['width'] <= z['x'] + z['w'], \
            f"{cid} se sale de {zid} en x"
        assert z['y'] <= c['y'] and c['y'] + c['height'] <= z['y'] + z['h'], \
            f"{cid} se sale de {zid} en y"
    for kid, cid in (('n1', 'c1'), ('n2', 'c1'), ('n3', 'c2'), ('n4', 'c3')):
        k, c = by_id[kid], by_id[cid]
        assert c['x'] <= k['x'] and \
            k['x'] + ICON_WIDTH <= c['x'] + c['width'], \
            f"{kid} se sale de {cid} en x"
        assert c['y'] <= k['y'] and \
            k['y'] + ICON_HEIGHT <= c['y'] + c['height'], \
            f"{kid} se sale de {cid} en y"


def test_conexiones_rutadas_en_los_tres_niveles():
    """Intra-contenedor, contenedor→contenedor (misma área) e inter-área:
    las tres llevan computed_path; la inter-área queda marcada."""
    L, _boxes = _run()
    by_pair = {(c['from'], c['to']): c for c in L.connections}
    assert by_pair[('n1', 'n2')].get('computed_path')
    assert by_pair[('n2', 'n3')].get('computed_path')
    inter = by_pair[('n3', 'n4')]
    assert inter.get('computed_path')
    assert inter.get('_inter_area')


def test_area_sin_contenedores_no_cambia():
    """Guarda de regresión: un área de iconos planos sigue el camino viejo
    (mismas posiciones que antes de ARCH-009)."""
    data = {
        'elements': [
            {'id': 'a', 'type': 'server', 'label': 'A'},
            {'id': 'b', 'type': 'server', 'label': 'B'},
        ],
        'connections': [{'from': 'a', 'to': 'b'}],
        'areas': [{'id': 'Z', 'label': 'Zona', 'members': ['a', 'b']}],
    }
    L = Layout(elements=copy.deepcopy(data['elements']),
               connections=copy.deepcopy(data['connections']),
               canvas={'width': 800, 'height': 600})
    boxes = layout_by_areas(L, data['areas'])
    assert {b['id'] for b in boxes} == {'Z'}
    by_id = {e['id']: e for e in L.elements}
    assert '_cw' not in by_id['a'] and '_cw' not in by_id['b']
