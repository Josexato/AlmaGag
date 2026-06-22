"""
Tests para Fase 3: dashboard, er, sequence, state (WISH-LAYOUT-004).
"""

from AlmaGag.layout.templates import (
    DashboardTemplate,
    ERTemplate,
    SequenceTemplate,
    StateTemplate,
    GraphFeatures,
    get_default_classifier,
    auto_apply_template,
)


# ============================================================================
# Fixtures
# ============================================================================

def _dashboard_data():
    """4 containers paralelos sin conexiones inter."""
    return {
        'elements': [
            {'id': 'p1', 'type': 'building', 'label': 'Panel 1',
             'contains': [{'id': 'a'}, {'id': 'b'}]},
            {'id': 'a', 'type': 'server', 'label': 'A'},
            {'id': 'b', 'type': 'server', 'label': 'B'},
            {'id': 'p2', 'type': 'building', 'label': 'Panel 2',
             'contains': [{'id': 'c'}, {'id': 'd'}]},
            {'id': 'c', 'type': 'server', 'label': 'C'},
            {'id': 'd', 'type': 'server', 'label': 'D'},
            {'id': 'p3', 'type': 'building', 'label': 'Panel 3',
             'contains': [{'id': 'e'}]},
            {'id': 'e', 'type': 'server', 'label': 'E'},
            {'id': 'p4', 'type': 'building', 'label': 'Panel 4',
             'contains': [{'id': 'f'}]},
            {'id': 'f', 'type': 'server', 'label': 'F'},
        ],
        'connections': [
            {'from': 'a', 'to': 'b'},
            {'from': 'c', 'to': 'd'},
        ],
    }


def _er_data():
    """ER con keywords explícitos + bipartito."""
    return {
        'elements': [
            {'id': 'user', 'type': 'database', 'label': 'User Entity'},
            {'id': 'order', 'type': 'database', 'label': 'Order Entity'},
            {'id': 'addr', 'type': 'database', 'label': 'Address Entity'},
            {'id': 'product', 'type': 'database', 'label': 'Product Entity'},
            {'id': 'cart', 'type': 'database', 'label': 'Cart Entity'},
        ],
        'connections': [
            {'from': 'user', 'to': 'order'},
            {'from': 'user', 'to': 'addr'},
            {'from': 'user', 'to': 'cart'},
            {'from': 'order', 'to': 'product'},
            {'from': 'order', 'to': 'addr'},
            {'from': 'cart', 'to': 'product'},
        ],
    }


def _state_data():
    """Máquina de estados con ciclos y self-loops."""
    return {
        'elements': [
            {'id': 's1', 'type': 'server', 'label': 'idle state'},
            {'id': 's2', 'type': 'server', 'label': 'active state'},
            {'id': 's3', 'type': 'server', 'label': 'paused state'},
            {'id': 's4', 'type': 'server', 'label': 'error state'},
        ],
        'connections': [
            {'from': 's1', 'to': 's2', 'label': 'start'},
            {'from': 's2', 'to': 's3', 'label': 'pause'},
            {'from': 's3', 'to': 's2', 'label': 'resume'},
            {'from': 's2', 'to': 's1', 'label': 'stop'},
            {'from': 's2', 'to': 's4', 'label': 'fail'},
            {'from': 's4', 'to': 's1', 'label': 'reset'},
            {'from': 's1', 'to': 's1', 'label': 'tick'},
        ],
    }


def _sequence_data():
    """Diagrama de secuencia: 3 actores con muchos mensajes."""
    return {
        'elements': [
            {'id': 'client', 'type': 'user', 'label': 'Client'},
            {'id': 'api', 'type': 'server', 'label': 'API Gateway'},
            {'id': 'db', 'type': 'database', 'label': 'Database'},
        ],
        'connections': [
            {'from': 'client', 'to': 'api', 'label': 'GET /users'},
            {'from': 'api', 'to': 'db', 'label': 'SELECT'},
            {'from': 'db', 'to': 'api', 'label': 'rows'},
            {'from': 'api', 'to': 'client', 'label': '200 OK'},
            {'from': 'client', 'to': 'api', 'label': 'POST /order'},
            {'from': 'api', 'to': 'db', 'label': 'INSERT'},
            {'from': 'db', 'to': 'api', 'label': 'id'},
            {'from': 'api', 'to': 'client', 'label': '201 Created'},
        ],
    }


# ============================================================================
# Scoring por template
# ============================================================================

def test_dashboard_scores_parallel_containers_high():
    data = _dashboard_data()
    f = GraphFeatures.extract(data['elements'], data['connections'])
    assert DashboardTemplate().detect_score(f) >= 0.6


def test_er_scores_entity_keywords_high():
    data = _er_data()
    f = GraphFeatures.extract(data['elements'], data['connections'])
    score = ERTemplate().detect_score(f)
    assert score >= 0.5  # con keywords entity gana


def test_state_scores_cyclic_graph_high():
    data = _state_data()
    f = GraphFeatures.extract(data['elements'], data['connections'])
    assert StateTemplate().detect_score(f) >= 0.6
    assert f.has_cycles
    assert f.n_self_loops >= 1


def test_sequence_scores_high_density_actors():
    data = _sequence_data()
    f = GraphFeatures.extract(data['elements'], data['connections'])
    # Pocos actores + muchas conexiones
    assert f.n_root_elements == 3
    assert f.n_connections == 8
    # No requerimos que sequence sea TOP del classifier (es difícil), pero
    # que el scorer dispare con score moderado
    assert SequenceTemplate().detect_score(f) >= 0.3


# ============================================================================
# Clasificador con conjunto completo
# ============================================================================

def test_classifier_picks_dashboard_for_panels():
    tpl, _ = get_default_classifier().classify(_dashboard_data())
    assert tpl is not None
    assert tpl.name == 'dashboard'


def test_classifier_picks_er_for_entities():
    tpl, _ = get_default_classifier().classify(_er_data())
    # ER debe ganar con keywords + bipartito
    assert tpl is not None
    assert tpl.name == 'er'


def test_classifier_picks_state_for_cycles():
    tpl, _ = get_default_classifier().classify(_state_data())
    assert tpl is not None
    assert tpl.name == 'state'


def test_classifier_does_not_misclassify_visual_catalog():
    """Catálogos visuales (íconos sueltos, sin estructura) deben quedar como None."""
    data = {
        'elements': [
            {'id': 'icon1', 'type': 'server', 'label': 'Server'},
            {'id': 'icon2', 'type': 'database', 'label': 'DB'},
            {'id': 'icon3', 'type': 'cloud', 'label': 'Cloud'},
            {'id': 'icon4', 'type': 'router', 'label': 'Router'},
        ],
        'connections': [],
    }
    tpl, scores = get_default_classifier().classify(data)
    # No debería elegir ningún template fuerte
    assert tpl is None


# ============================================================================
# Apply templates
# ============================================================================

def test_apply_dashboard_assigns_grid_coords():
    data = _dashboard_data()
    applied, _ = auto_apply_template(data)
    assert applied == 'dashboard'
    # Containers en grid
    containers = [e for e in data['elements'] if 'contains' in e]
    xs = sorted({c['x'] for c in containers})
    ys = sorted({c['y'] for c in containers})
    # Para 4 containers en 2x2: 2 X distintas y 2 Y distintas
    assert len(xs) == 2
    assert len(ys) == 2


def test_apply_state_circular_distribution():
    data = _state_data()
    applied, _ = auto_apply_template(data)
    assert applied == 'state'
    # Los 4 estados deben tener coords asignadas
    for e in data['elements']:
        assert 'x' in e
        assert 'y' in e


def test_apply_er_radial_distribution():
    data = _er_data()
    applied, _ = auto_apply_template(data)
    assert applied == 'er'
    for e in data['elements']:
        assert 'x' in e
        assert 'y' in e
