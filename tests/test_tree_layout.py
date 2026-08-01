"""Árboles chicos en `auto` (pendiente nº4 de la iteración 5).

Dos causas y sus curas, ambas ACOTADAS a bosques (todo nodo con ≤1 padre):
- La corrección de hojas satélite promovía un hijo hoja al nivel del PADRE
  cuando un hermano tenía descendencia (caso `jsis` del organigrama). En un
  bosque manda la jerarquía: hoja = padre + 1 siempre.
- El paso entre hermanos ignoraba el ancho de las etiquetas (el optimizador
  las corría del icono y la fila quedaba ambigua) y el tirón de centralidad
  del barycenter desordenaba hermanos. En bosques: paso consciente de
  etiquetas y barycenter puro.
En grafos con merges/ciclos nada cambia (métricas idénticas en los 36
fixtures al introducir esto).
"""

import json

import pytest

from AlmaGag.layout import Layout
from AlmaGag.layout.engine import LayoutEngine
from AlmaGag.layout.graph_analysis import GraphAnalyzer
from AlmaGag.generator import select_strategy

ORG = {
    'elements': [{'id': i} for i in
                 ('holding', 'ceo', 'gop', 'gfin', 'gti',
                  'jred', 'jsis', 'jcon', 'jlog', 'eqred')],
    'connections': [
        {'from': 'holding', 'to': 'ceo'},
        {'from': 'ceo', 'to': 'gop'}, {'from': 'ceo', 'to': 'gfin'},
        {'from': 'ceo', 'to': 'gti'},
        {'from': 'gti', 'to': 'jred'}, {'from': 'gti', 'to': 'jsis'},
        {'from': 'gfin', 'to': 'jcon'}, {'from': 'gop', 'to': 'jlog'},
        {'from': 'jred', 'to': 'eqred'},
    ],
}


def test_forest_leaf_never_promoted_to_parent_level():
    """`jsis` (hoja, hermano de un subárbol) va a padre+1, no al nivel del
    padre — la corrección satélite no aplica en bosques."""
    levels = GraphAnalyzer().calculate_topological_levels(
        ORG['elements'], ORG['connections'])
    assert levels['gti'] == 2
    assert levels['jsis'] == 3 == levels['jred'] == levels['jcon'] == levels['jlog']
    assert levels['eqred'] == 4


def test_non_forest_keeps_satellite_leaves():
    """Con un merge (2 padres) el grafo NO es bosque: la hoja no-terminal
    conserva el comportamiento satélite histórico (nivel del padre)."""
    elements = [{'id': i} for i in ('a', 'b', 'c', 'd', 'm')]
    connections = [
        {'from': 'a', 'to': 'b'},       # hoja no-terminal (satélite)
        {'from': 'a', 'to': 'c'}, {'from': 'c', 'to': 'd'},
        {'from': 'a', 'to': 'm'}, {'from': 'c', 'to': 'm'},   # merge
    ]
    levels = GraphAnalyzer().calculate_topological_levels(elements, connections)
    assert levels['b'] == levels['a'], 'el satélite histórico debe conservarse'


def _optimize(data):
    L = Layout(elements=[dict(e) for e in data['elements']],
               connections=data['connections'],
               canvas={'width': 1400, 'height': 900})
    L._strategy = select_strategy(data, 'auto')
    return LayoutEngine(verbose=False, strategy=None).optimize(L)


def test_tree_rows_fit_wide_labels():
    """Hermanos con etiquetas anchas: el paso de fila las acomoda centradas
    (distancia entre centros ≥ ancho medio de las etiquetas vecinas)."""
    data = {'elements': [
        {'id': 'p', 'label': 'Raíz'},
        {'id': 'h1', 'label': 'Jefatura de Contabilidad'},
        {'id': 'h2', 'label': 'Jefatura de Sistemas'},
        {'id': 'h3', 'label': 'Jefatura de Logística'},
    ], 'connections': [{'from': 'p', 'to': f'h{i}'} for i in (1, 2, 3)]}
    res = _optimize(data)
    by = res.elements_by_id
    from AlmaGag.utils import calculate_label_dimensions
    row = sorted((by[f'h{i}'] for i in (1, 2, 3)), key=lambda e: e['x'])
    for a, b in zip(row, row[1:]):
        dist = (b['x'] + b.get('width', 80) / 2) - (a['x'] + a.get('width', 80) / 2)
        need = (calculate_label_dimensions(a['label'])[0]
                + calculate_label_dimensions(b['label'])[0]) / 2
        assert dist >= need, f"paso {dist:.0f}px < etiquetas {need:.0f}px"


def test_org_tree_quality():
    """El organigrama SIN coordenadas: niveles estrictos y calidad decente
    (≤1 cruce, cero arista×nodo, cero solapes de etiqueta)."""
    from AlmaGag.layout.metrics import quality_counters
    data = {'elements': [dict(e, label=f"Nodo {e['id']}") for e in ORG['elements']],
            'connections': ORG['connections']}
    res = _optimize(data)
    lv = res.levels
    assert lv['jsis'] == lv['jred'] == lv['jcon'] == lv['jlog']
    q = quality_counters(res)
    assert q['edge_x_node'] == 0
    assert q['label_overlap'] == 0
    assert q['edge_x_edge'] <= 1
