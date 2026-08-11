"""
Tests para Fase 4: semantic hints (role) + templates anidados
(WISH-LAYOUT-004).
"""

from AlmaGag.layout.templates import (
    GraphFeatures,
    ArchitectureTemplate,
    HubAndSpokeTemplate,
    StateTemplate,
    get_default_classifier,
    auto_apply_template,
    apply_template,
)
from AlmaGag.layout.templates.nested import (
    collect_containers_with_template,
    apply_nested_templates,
)


# ============================================================================
# Semantic hints: role
# ============================================================================

def test_features_capture_declared_roles():
    data = {
        'elements': [
            {'id': 'a', 'role': 'entry', 'label': 'A'},
            {'id': 'b', 'role': 'shared', 'label': 'B'},
            {'id': 'c', 'role': 'hub', 'label': 'C'},
            {'id': 'd', 'label': 'D'},  # sin role
        ],
        'connections': [
            {'from': 'a', 'to': 'b'},
            {'from': 'a', 'to': 'c'},
        ],
    }
    f = GraphFeatures.extract(data['elements'], data['connections'])
    assert f.declared_roles == {'a': 'entry', 'b': 'shared', 'c': 'hub'}
    # Los roles declarados también suman como keywords
    assert 'entry' in f.label_keywords
    assert 'shared' in f.label_keywords
    assert 'hub' in f.label_keywords


def test_architecture_score_bonuses_declared_roles():
    """Sin role la heurística da X; con roles debe dar más."""
    base = {
        'elements': [
            {'id': 'in', 'label': 'in'},
            {'id': 'main', 'label': 'main'},
            {'id': 'box1', 'label': 'AUTO', 'contains': [{'id': 'x'}]},
            {'id': 'x', 'label': 'X'},
            {'id': 'box2', 'label': 'LAF', 'contains': [{'id': 'y'}]},
            {'id': 'y', 'label': 'Y'},
            {'id': 'out', 'label': 'out'},
        ],
        'connections': [
            {'from': 'in', 'to': 'main'},
            {'from': 'main', 'to': 'x'},
            {'from': 'main', 'to': 'y'},
            {'from': 'x', 'to': 'out'},
            {'from': 'y', 'to': 'out'},
        ],
    }
    f_base = GraphFeatures.extract(base['elements'], base['connections'])
    score_base = ArchitectureTemplate().detect_score(f_base)

    # Mismo grafo con roles declarados
    hinted = {
        'elements': [
            {'id': 'in', 'role': 'entry', 'label': 'in'},
            {'id': 'main', 'label': 'main'},
            {'id': 'box1', 'label': 'AUTO', 'contains': [{'id': 'x'}]},
            {'id': 'x', 'label': 'X'},
            {'id': 'box2', 'label': 'LAF', 'contains': [{'id': 'y'}]},
            {'id': 'y', 'label': 'Y'},
            {'id': 'out', 'role': 'output', 'label': 'out'},
        ],
        'connections': base['connections'],
    }
    f_hinted = GraphFeatures.extract(hinted['elements'], hinted['connections'])
    score_hinted = ArchitectureTemplate().detect_score(f_hinted)

    assert score_hinted > score_base


def test_hub_and_spoke_role_hub_overrides_heuristic():
    """Cuando el usuario declara role='hub' ese nodo gana aunque no tenga
    el degree más alto."""
    data = {
        'elements': [
            # node 'b' tiene 3 conexiones (más que 'a' que tiene 2)
            # pero 'a' declara role:hub → debe ser el hub.
            {'id': 'a', 'role': 'hub', 'label': 'A'},
            {'id': 'b', 'label': 'B'},
            {'id': 'c', 'label': 'C'},
            {'id': 'd', 'label': 'D'},
            {'id': 'e', 'label': 'E'},
        ],
        'connections': [
            {'from': 'a', 'to': 'b'},
            {'from': 'a', 'to': 'c'},
            {'from': 'b', 'to': 'c'},
            {'from': 'b', 'to': 'd'},
            {'from': 'b', 'to': 'e'},
        ],
    }
    from AlmaGag.layout.templates.hub_and_spoke import _find_hub
    hub, spokes = _find_hub(data['elements'], data['connections'])
    assert hub == 'a'
    assert set(spokes) == {'b', 'c', 'd', 'e'}


def test_state_score_bonus_for_role_state():
    base_elems = [
        {'id': 's1', 'label': 's1'},
        {'id': 's2', 'label': 's2'},
        {'id': 's3', 'label': 's3'},
    ]
    base_conns = [
        {'from': 's1', 'to': 's2'},
        {'from': 's2', 'to': 's3'},
        {'from': 's3', 'to': 's1'},
        {'from': 's1', 'to': 's1'},
    ]
    f_base = GraphFeatures.extract(base_elems, base_conns)
    score_base = StateTemplate().detect_score(f_base)

    hinted_elems = [{**e, 'role': 'state'} for e in base_elems]
    f_hinted = GraphFeatures.extract(hinted_elems, base_conns)
    score_hinted = StateTemplate().detect_score(f_hinted)

    assert score_hinted > score_base


def test_architecture_apply_respects_role_entry():
    """`role:entry` fuerza que el nodo entre al entry layer
    aunque tenga incoming connections."""
    data = {
        'elements': [
            # 'special' tiene incoming pero su role es entry: debe estar arriba.
            {'id': 'noise', 'label': 'noise'},
            {'id': 'special', 'role': 'entry', 'label': 'I am entry'},
            {'id': 'box', 'label': 'Box', 'contains': [{'id': 'inner'}]},
            {'id': 'inner', 'label': 'I'},
        ],
        'connections': [
            {'from': 'noise', 'to': 'special'},  # special tiene incoming
            {'from': 'special', 'to': 'inner'},
        ],
    }
    apply_template('architecture', data)
    by_id = {e['id']: e for e in data['elements']}
    # special debe tener una y similar a la entry layer (arriba) no a chain
    assert 'y' in by_id['special']
    # box (container) debe estar abajo de special
    assert by_id['special']['y'] < by_id['box']['y']


# ============================================================================
# Templates anidados
# ============================================================================

def test_collect_containers_with_template_orders_bottom_up():
    """Los containers más anidados deben procesarse primero."""
    elements = [
        {'id': 'outer', 'contains': [{'id': 'middle'}], 'layout_template': 'steps'},
        {'id': 'middle', 'contains': [{'id': 'inner'}], 'layout_template': 'hub_and_spoke'},
        {'id': 'inner', 'contains': [{'id': 'leaf'}], 'layout_template': 'state'},
        {'id': 'leaf'},
    ]
    order = collect_containers_with_template(elements)
    names = [n for n, _ in order]
    # 'inner' debe estar antes que 'middle' y 'outer'
    assert names.index('inner') < names.index('middle')
    assert names.index('middle') < names.index('outer')


def test_nested_templates_dimension_container():
    """Un container con sub-template inflado por sus hijos debe quedar con
    width/height suficientes para contenerlos."""
    data = {
        'layout_template': 'auto',
        'elements': [
            {'id': 'wrapper', 'label': 'Wrapper',
             'layout_template': 'steps',
             'contains': [
                 {'id': 's1'}, {'id': 's2'}, {'id': 's3'}, {'id': 's4'},
             ]},
            {'id': 's1', 'label': 'step 1'},
            {'id': 's2', 'label': 'step 2'},
            {'id': 's3', 'label': 'step 3'},
            {'id': 's4', 'label': 'step 4'},
            {'id': 'driver', 'label': 'driver'},
        ],
        'connections': [
            {'from': 'driver', 'to': 's1'},
            {'from': 's1', 'to': 's2'},
            {'from': 's2', 'to': 's3'},
            {'from': 's3', 'to': 's4'},
        ],
    }
    auto_apply_template(data)
    wrapper = next(e for e in data['elements'] if e['id'] == 'wrapper')
    # Wrapper debe tener dimensiones suficientes para 4 hijos en flow vertical
    assert wrapper.get('_inner_height', 0) >= 4 * 100  # 4 niveles × espacio


def test_nested_children_offset_to_global_coords():
    """Después del template padre, los hijos del container con sub-template
    deben tener coords GLOBALES (no relativas)."""
    data = {
        'layout_template': 'architecture',
        'elements': [
            {'id': 'wrapper', 'label': 'Wrapper',
             'layout_template': 'steps',
             'contains': [
                 {'id': 'c1'}, {'id': 'c2'}, {'id': 'c3'}, {'id': 'c4'},
             ]},
            {'id': 'c1', 'label': 'c1'},
            {'id': 'c2', 'label': 'c2'},
            {'id': 'c3', 'label': 'c3'},
            {'id': 'c4', 'label': 'c4'},
            {'id': 'in', 'label': 'in', 'role': 'entry'},
        ],
        'connections': [
            {'from': 'in', 'to': 'c1'},
            {'from': 'c1', 'to': 'c2'},
            {'from': 'c2', 'to': 'c3'},
            {'from': 'c3', 'to': 'c4'},
        ],
    }
    apply_template('architecture', data)
    wrapper = next(e for e in data['elements'] if e['id'] == 'wrapper')
    c1 = next(e for e in data['elements'] if e['id'] == 'c1')
    # c1 debe estar DENTRO del wrapper
    assert wrapper['x'] <= c1['x']
    assert wrapper['y'] <= c1['y']
    assert c1['x'] < wrapper['x'] + wrapper.get('width', wrapper.get('_inner_width', 0))


def test_nested_apply_returns_applied_list():
    data = {
        'elements': [
            {'id': 'a', 'contains': [{'id': 'x'}, {'id': 'y'}],
             'layout_template': 'hub_and_spoke'},
            {'id': 'x', 'label': 'x'},
            {'id': 'y', 'label': 'y'},
        ],
        'connections': [{'from': 'x', 'to': 'y'}],
    }
    classifier = get_default_classifier()
    result = apply_nested_templates(data, classifier.by_name)
    assert result == [('a', 'hub_and_spoke')]


def test_nested_unknown_template_skipped():
    data = {
        'elements': [
            {'id': 'a', 'contains': [{'id': 'x'}],
             'layout_template': 'nonexistent'},
            {'id': 'x', 'label': 'x'},
        ],
        'connections': [],
    }
    classifier = get_default_classifier()
    result = apply_nested_templates(data, classifier.by_name)
    assert result == []  # no se aplicó nada (template desconocido)
