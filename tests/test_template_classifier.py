"""
Tests para el clasificador automático de templates (WISH-LAYOUT-004 Fase 2).

Verifica:
- Extracción de GraphFeatures (n_root, degrees, depth, ciclos, keywords).
- Scoring por template (architecture, flow, hub_and_spoke).
- TemplateClassifier: ganador, threshold, min_lead.
- Auto-detect over fixtures de los 3 patrones principales.
"""

from AlmaGag.layout.templates import (
    GraphFeatures,
    ArchitectureTemplate,
    StepsTemplate,
    HubAndSpokeTemplate,
    TemplateClassifier,
    get_default_classifier,
    auto_apply_template,
    apply_template,
)


# ============================================================================
# Fixtures
# ============================================================================

def _arch_data():
    """Mini-arquitectura con shared al medio."""
    return {
        'elements': [
            {'id': 'in', 'type': 'document', 'label': 'input'},
            {'id': 'main', 'type': 'server', 'label': 'main.py'},
            {'id': 'gen', 'type': 'server', 'label': 'generator'},
            {'id': 'auto_box', 'type': 'building', 'label': 'AUTO',
             'contains': [{'id': 'auto_opt'}]},
            {'id': 'auto_opt', 'type': 'gear', 'label': 'AutoOptimizer'},
            {'id': 'laf_box', 'type': 'building', 'label': 'LAF',
             'contains': [{'id': 'laf_opt'}]},
            {'id': 'laf_opt', 'type': 'gear', 'label': 'LAFOptimizer'},
            {'id': 'shared_box', 'type': 'firewall',
             'label': 'Shared (algoritmo-agnóstico)',
             'contains': [{'id': 'router'}]},
            {'id': 'router', 'type': 'router', 'label': 'Router'},
            {'id': 'contract', 'type': 'contract', 'label': 'LayoutOptimizer'},
            {'id': 'out', 'type': 'document', 'label': 'output'},
        ],
        'connections': [
            {'from': 'in', 'to': 'main'},
            {'from': 'main', 'to': 'gen'},
            {'from': 'gen', 'to': 'auto_opt'},
            {'from': 'gen', 'to': 'laf_opt'},
            {'from': 'auto_opt', 'to': 'contract'},
            {'from': 'laf_opt', 'to': 'contract'},
            {'from': 'auto_opt', 'to': 'router'},
            {'from': 'laf_opt', 'to': 'router'},
            {'from': 'auto_opt', 'to': 'out'},
            {'from': 'laf_opt', 'to': 'out'},
        ],
    }


def _flow_data():
    """Cadena larga de pasos sin containers."""
    return {
        'elements': [
            {'id': 's1', 'type': 'server', 'label': 'step 1'},
            {'id': 's2', 'type': 'server', 'label': 'step 2'},
            {'id': 's3', 'type': 'server', 'label': 'step 3'},
            {'id': 's4', 'type': 'server', 'label': 'step 4'},
            {'id': 's5', 'type': 'server', 'label': 'step 5'},
            {'id': 's6', 'type': 'server', 'label': 'step 6'},
        ],
        'connections': [
            {'from': 's1', 'to': 's2'},
            {'from': 's2', 'to': 's3'},
            {'from': 's3', 'to': 's4'},
            {'from': 's4', 'to': 's5'},
            {'from': 's5', 'to': 's6'},
        ],
    }


def _hub_spoke_data():
    """Hub central conectado a 6 satélites."""
    elements = [
        {'id': 'hub', 'type': 'database', 'label': 'central hub'},
    ]
    connections = []
    for i in range(1, 7):
        sid = f'branch{i}'
        elements.append({'id': sid, 'type': 'building', 'label': f'branch {i}'})
        connections.append({'from': sid, 'to': 'hub'})
    return {'elements': elements, 'connections': connections}


# ============================================================================
# GraphFeatures
# ============================================================================

def test_features_arch_has_containers_and_keywords():
    f = GraphFeatures.extract(_arch_data()['elements'], _arch_data()['connections'])
    assert f.n_containers == 3
    assert 'shared' in f.label_keywords or 'agnost' in f.label_keywords
    assert not f.has_cycles


def test_features_flow_has_high_depth_and_low_branching():
    f = GraphFeatures.extract(_flow_data()['elements'], _flow_data()['connections'])
    assert f.topological_depth >= 5
    assert f.branching_factor < 1.5
    assert f.n_containers == 0


def test_features_hub_has_high_degree_ratio():
    f = GraphFeatures.extract(_hub_spoke_data()['elements'], _hub_spoke_data()['connections'])
    # Hub tiene 6 conexiones, cada spoke tiene 1 → ratio alto
    assert f.max_degree_ratio >= 2.5
    assert f.n_containers == 0


def test_features_extract_keywords_lowercase():
    data = {
        'elements': [
            {'id': 'a', 'label': 'Shared Service'},
            {'id': 'b', 'label': 'Step 1'},
            {'id': 'c', 'label': 'Hub Node'},
        ],
        'connections': [],
    }
    f = GraphFeatures.extract(data['elements'], data['connections'])
    assert 'shared' in f.label_keywords
    assert 'step' in f.label_keywords
    assert 'hub' in f.label_keywords


# ============================================================================
# Scoring por template
# ============================================================================

def test_architecture_scores_arch_data_high():
    f = GraphFeatures.extract(_arch_data()['elements'], _arch_data()['connections'])
    score = ArchitectureTemplate().detect_score(f)
    assert score >= 0.6


def test_flow_scores_chain_high():
    f = GraphFeatures.extract(_flow_data()['elements'], _flow_data()['connections'])
    score = StepsTemplate().detect_score(f)
    assert score >= 0.6


def test_hub_scores_star_topology_high():
    f = GraphFeatures.extract(_hub_spoke_data()['elements'], _hub_spoke_data()['connections'])
    score = HubAndSpokeTemplate().detect_score(f)
    assert score >= 0.5


def test_flow_scores_arch_data_lower_than_arch():
    f = GraphFeatures.extract(_arch_data()['elements'], _arch_data()['connections'])
    assert ArchitectureTemplate().detect_score(f) > StepsTemplate().detect_score(f)


# ============================================================================
# Classifier
# ============================================================================

def test_classifier_picks_architecture_for_arch():
    tpl, scores = get_default_classifier().classify(_arch_data())
    assert tpl is not None
    assert tpl.name == 'architecture'


def test_classifier_picks_flow_for_chain():
    tpl, scores = get_default_classifier().classify(_flow_data())
    assert tpl is not None
    assert tpl.name == 'steps'


def test_classifier_picks_hub_for_star():
    tpl, scores = get_default_classifier().classify(_hub_spoke_data())
    assert tpl is not None
    assert tpl.name == 'hub_and_spoke'


def test_classifier_returns_none_below_threshold():
    """Grafo trivial: 2 nodos, 1 conexión. No matchea ningún patrón."""
    data = {
        'elements': [{'id': 'a'}, {'id': 'b'}],
        'connections': [{'from': 'a', 'to': 'b'}],
    }
    tpl, scores = get_default_classifier().classify(data)
    assert tpl is None


def test_classifier_returns_none_on_tie():
    """Si dos templates están empatados (min_lead no se cumple), None."""
    # Threshold por defecto = 0.6, min_lead = 0.05.
    # Forzamos un caso donde dos templates dan >=0.6 muy cerca.
    templates = [
        type('A', (), {'name': 'A', 'detect_score': lambda self, f: 0.80, 'apply': lambda self, d: None})(),
        type('B', (), {'name': 'B', 'detect_score': lambda self, f: 0.78, 'apply': lambda self, d: None})(),
    ]
    cls = TemplateClassifier(templates)
    tpl, _ = cls.classify({'elements': [{'id': 'x'}], 'connections': []})
    assert tpl is None  # diferencia < min_lead


# ============================================================================
# auto_apply_template + apply_template (override)
# ============================================================================

def test_auto_apply_assigns_coords_for_architecture():
    data = _arch_data()
    applied, scores = auto_apply_template(data)
    assert applied == 'architecture'
    # Verificar que se asignaron coords a elementos non-contained
    for e in data['elements']:
        if e['id'] in ('auto_opt', 'laf_opt', 'router'):
            continue  # contenidos
        assert 'x' in e and 'y' in e


def test_manual_override_takes_precedence():
    """`layout_template: 'flow'` debe aplicar flow aunque el grafo se parezca a arch."""
    data = _arch_data()
    # Aplicar override directo (simula que el usuario lo declaró)
    applied = apply_template('steps', data)
    assert applied is True
    # Todos los elementos non-contained deben tener x/y
    for e in data['elements']:
        if e['id'] in ('auto_opt', 'laf_opt', 'router'):
            continue
        assert 'x' in e and 'y' in e


def test_apply_template_unknown_name_returns_false():
    assert apply_template('nonexistent', {'elements': [], 'connections': []}) is False
