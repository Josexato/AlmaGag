"""
Test del auto-selector de estrategia (convergencia a un solo algoritmo).

`almagag archivo.json` sin flags → el motor elige la estrategia a partir del
JSON; sólo un parámetro de COMANDO fuerza otra. La política no debe enrutar a
`hier` diagramas que hoy dependen de AUTO (contenedores, arquitecturas).
"""

from AlmaGag.generator import select_strategy


def test_plain_graph_goes_auto():
    data = {'elements': [{'id': 'a', 'type': 'server'}, {'id': 'b', 'type': 'database'}],
            'connections': [{'from': 'a', 'to': 'b'}]}
    assert select_strategy(data) == 'auto'


def test_containers_stay_auto():
    """hier no soporta contenedores anidados → deben quedar en AUTO."""
    data = {'elements': [
        {'id': 'box', 'type': 'building', 'contains': ['x']},
        {'id': 'x', 'type': 'decision'}]}    # ¡tiene rombo pero también contenedor!
    assert select_strategy(data) == 'auto'


def test_decision_nodes_go_hier():
    data = {'elements': [{'id': 'a', 'type': 'document'},
                         {'id': 'q', 'type': 'decision'}]}
    assert select_strategy(data) == 'hier'


def test_areas_go_hier():
    data = {'areas': [{'id': 'F1', 'members': ['a']}],
            'elements': [{'id': 'a', 'type': 'server'}]}
    assert select_strategy(data) == 'hier'


def test_cycle_without_coords_goes_hier():
    """Un flujo con ciclo y sin coords manuales → hier (arcos de ciclo)."""
    data = {'elements': [{'id': 'a'}, {'id': 'b'}, {'id': 'c'}],
            'connections': [{'from': 'a', 'to': 'b'}, {'from': 'b', 'to': 'c'},
                            {'from': 'c', 'to': 'a'}]}   # ciclo a→b→c→a
    assert select_strategy(data) == 'hier'


def test_self_loop_goes_hier():
    data = {'elements': [{'id': 'a'}, {'id': 'b'}],
            'connections': [{'from': 'a', 'to': 'a'}, {'from': 'a', 'to': 'b'}]}
    assert select_strategy(data) == 'hier'


def test_acyclic_dag_stays_auto():
    """Un DAG SIN ciclo se queda en AUTO (hier lo renderiza peor — K37)."""
    data = {'elements': [{'id': 'a'}, {'id': 'b'}, {'id': 'c'}],
            'connections': [{'from': 'a', 'to': 'b'}, {'from': 'a', 'to': 'c'},
                            {'from': 'b', 'to': 'c'}]}   # DAG, sin ciclo
    assert select_strategy(data) == 'auto'


def test_cycle_with_manual_coords_stays_auto():
    """Con coords manuales se respeta la disposición del usuario → AUTO."""
    data = {'elements': [{'id': 'a', 'x': 0, 'y': 0}, {'id': 'b', 'x': 100, 'y': 0}],
            'connections': [{'from': 'a', 'to': 'b'}, {'from': 'b', 'to': 'a'}]}
    assert select_strategy(data) == 'auto'


def test_explicit_view_forces_hier():
    """Una vista pedida por CLI es de hier, aunque el grafo sea plano."""
    data = {'elements': [{'id': 'a', 'type': 'server'}]}
    assert select_strategy(data, view='lanes') == 'hier'
    assert select_strategy(data, view='auto') == 'auto'


def test_considerations_beat_areas_with_warning(caplog):
    """§O53 (N46⇄I27): considerations→AUTO gana a areas→hier, pero la señal
    anulada se nombra en un WARNING — nunca se pierde en silencio."""
    import logging
    data = {'areas': [{'id': 'F1', 'members': ['a']}],
            'considerations': [{'near': ['a', 'b']}],
            'elements': [{'id': 'a'}, {'id': 'b'}]}
    with caplog.at_level(logging.WARNING, logger='AlmaGag'):
        assert select_strategy(data) == 'auto'
    text = '\n'.join(r.message for r in caplog.records)
    assert '§O53' in text and 'areas' in text and 'anulada' in text


def test_containers_beat_areas_with_warning(caplog):
    import logging
    data = {'areas': [{'id': 'F1', 'members': ['x']}],
            'elements': [{'id': 'box', 'contains': ['x']}, {'id': 'x'}]}
    with caplog.at_level(logging.WARNING, logger='AlmaGag'):
        assert select_strategy(data) == 'auto'
    text = '\n'.join(r.message for r in caplog.records)
    assert '§O53' in text and 'contains' in text and 'areas' in text


def test_explicit_view_annuls_considerations_with_warning(caplog):
    import logging
    data = {'considerations': [{'align': ['a', 'b']}],
            'elements': [{'id': 'a'}, {'id': 'b'}]}
    with caplog.at_level(logging.WARNING, logger='AlmaGag'):
        assert select_strategy(data, view='lanes') == 'hier'
    text = '\n'.join(r.message for r in caplog.records)
    assert '§O53' in text and 'considerations' in text


def test_no_warning_without_conflict(caplog):
    """Sin señales en conflicto no hay ruido §O53."""
    import logging
    with caplog.at_level(logging.WARNING, logger='AlmaGag'):
        assert select_strategy({'areas': [{'id': 'F1'}],
                                'elements': [{'id': 'a'}]}) == 'hier'
        assert select_strategy({'elements': [{'id': 'a'}]}) == 'auto'
    assert '§O53' not in '\n'.join(r.message for r in caplog.records)


def test_default_generate_diagram_uses_selector(tmp_path):
    """generate_diagram sin `layout_algorithm` corre el selector (default)."""
    from AlmaGag.generator import generate_diagram
    out = str(tmp_path / 'o.svg')
    # es-primo tiene rombos → el selector debe elegir hier y renderizar OK
    assert generate_diagram('docs/diagrams/gags/es-primo.gag', output_file=out)
