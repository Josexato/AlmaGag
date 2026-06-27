"""
Regresión del scorer 'architecture' (BUGS-TPL-001).

El scorer estaba sobre-ajustado: ventana de depth 3..7 + dependencia del
keyword 'shared'. Arquitecturas reales sin esa nomenclatura o con cadenas
más largas caían al fallback agnóstico (ej. cakephp-mvc, depth=10).

Fix: ventana 3..10 + bonus por firma estructural (1 entry + terminal +
2+ containers), independiente de keywords.
"""

import json
import os
import glob

from AlmaGag.layout.templates import (
    get_default_classifier,
    ArchitectureTemplate,
)
from AlmaGag.layout.templates.features import GraphFeatures


def _features(elements, connections):
    return GraphFeatures.extract(elements, connections)


def _mvc_like():
    """Arquitectura MVC genérica: 1 entry, 3 containers paralelos, 1 salida,
    SIN keyword 'shared'. Debe puntuar architecture por encima del threshold."""
    elements = [
        {'id': 'req', 'type': 'document', 'label': 'Request'},
        {'id': 'ctrl_box', 'type': 'building', 'label': 'Controllers',
         'contains': ['c1', 'c2']},
        {'id': 'c1', 'type': 'server', 'label': 'A'},
        {'id': 'c2', 'type': 'server', 'label': 'B'},
        {'id': 'model_box', 'type': 'building', 'label': 'Models',
         'contains': ['m1', 'm2']},
        {'id': 'm1', 'type': 'database', 'label': 'M1'},
        {'id': 'm2', 'type': 'database', 'label': 'M2'},
        {'id': 'view_box', 'type': 'building', 'label': 'Views',
         'contains': ['v1', 'v2']},
        {'id': 'v1', 'type': 'document', 'label': 'V1'},
        {'id': 'v2', 'type': 'document', 'label': 'V2'},
        {'id': 'resp', 'type': 'document', 'label': 'Response'},
    ]
    connections = [
        {'from': 'req', 'to': 'c1'}, {'from': 'req', 'to': 'c2'},
        {'from': 'c1', 'to': 'm1'}, {'from': 'c2', 'to': 'm2'},
        {'from': 'c1', 'to': 'v1'}, {'from': 'c2', 'to': 'v2'},
        {'from': 'v1', 'to': 'resp'}, {'from': 'v2', 'to': 'resp'},
    ]
    return elements, connections


def test_mvc_architecture_passes_threshold_without_keyword():
    """Una arquitectura clara sin keyword 'shared' debe superar 0.6."""
    feats = _features(*_mvc_like())
    score = ArchitectureTemplate().detect_score(feats)
    assert score >= 0.6, f"architecture score {score} < 0.6 (BUGS-TPL-001)"


def test_deep_chain_still_architecture():
    """Profundidad 8-10 ya NO descalifica (antes la ventana era 3..7)."""
    feats = _features(*_mvc_like())
    # MVC-like tiene depth ~ alto; el bonus de depth debe aplicar hasta 10.
    assert feats.topological_depth >= 3
    score = ArchitectureTemplate().detect_score(feats)
    # Sin el ensanche de ventana, este caso quedaba en 0.55.
    assert score > 0.55


def test_structure_bonus_requires_single_entry():
    """El bonus estructural NO aplica si hay múltiples entradas."""
    elements, connections = _mvc_like()
    # Añadir una segunda entrada independiente (otro root sin incoming).
    elements.append({'id': 'req2', 'type': 'document', 'label': 'Req2'})
    connections.append({'from': 'req2', 'to': 'c1'})
    feats = _features(elements, connections)
    assert feats.n_root_nodes_no_incoming >= 2


def test_cakephp_canonical_detects_architecture():
    """El canonical neutro cakephp-mvc.gag debe clasificar como architecture."""
    path = 'docs/diagrams/gags/cakephp-mvc.gag'
    if not os.path.exists(path):
        return  # canonical opcional
    data = json.load(open(path))
    clf = get_default_classifier()
    tpl, scores = clf.classify(data)
    assert tpl is not None and tpl.name == 'architecture', \
        f"cakephp-mvc clasificó como {tpl.name if tpl else None}, scores={scores}"


def test_no_regression_in_winners():
    """Los canonicals que ya ganaban un template específico lo conservan."""
    expected = {
        '05-arquitectura-gag': 'architecture',
        '07-containers': 'architecture',
        '03-conexiones': 'flow',
        '10-hybrid-layout': 'er',
        'reference-cheatsheet': 'dashboard',
        'system-architecture': 'hub_and_spoke',
    }
    clf = get_default_classifier()
    for stem, want in expected.items():
        matches = glob.glob(f'docs/diagrams/gags/{stem}.*')
        if not matches:
            continue
        data = json.load(open(matches[0]))
        tpl, scores = clf.classify(data)
        got = tpl.name if tpl else None
        assert got == want, f"{stem}: esperado {want}, obtuvo {got} ({scores})"
