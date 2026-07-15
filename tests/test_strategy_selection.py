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


def test_explicit_view_forces_hier():
    """Una vista pedida por CLI es de hier, aunque el grafo sea plano."""
    data = {'elements': [{'id': 'a', 'type': 'server'}]}
    assert select_strategy(data, view='lanes') == 'hier'
    assert select_strategy(data, view='auto') == 'auto'


def test_default_generate_diagram_uses_selector(tmp_path):
    """generate_diagram sin `layout_algorithm` corre el selector (default)."""
    from AlmaGag.generator import generate_diagram
    out = str(tmp_path / 'o.svg')
    # es-primo tiene rombos → el selector debe elegir hier y renderizar OK
    assert generate_diagram('docs/diagrams/gags/es-primo.gag', output_file=out)
