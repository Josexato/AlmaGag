"""BUGS-TPL-003 — la cadena del template architecture se apila en orden
TOPOLÓGICO, no por out-degree.

El sort por -out_count invertía request→router→dispatcher (dispatcher,
con 2 salidas, le ganaba a router con 1): la arista request→router
atravesaba el icono de dispatcher y el flujo se leía en zigzag
(cakephp-mvc, «fallo crítico 2» del reporte externo — verificado).
Ahora la cadena entry+chain se ordena por longest-path acotado sobre su
propio subgrafo; el out-degree queda como desempate dentro del rango.
"""

import json
from AlmaGag.layout.templates.architecture import apply_architecture_template


def test_declared_chain_keeps_its_order():
    d = json.load(open('docs/diagrams/gags/cakephp-mvc.gag'))
    apply_architecture_template(d)
    by = {e['id']: e for e in d['elements']}
    assert by['request']['y'] < by['router']['y'] < by['dispatcher']['y'], \
        {k: by[k]['y'] for k in ('request', 'router', 'dispatcher')}


def test_tiebreak_still_prefers_fanout():
    """Dos nodos del MISMO rango topológico siguen ordenándose por
    out-degree (el criterio viejo sobrevive como desempate)."""
    d = {
        'elements': [
            {'id': 'e', 'type': 'server', 'label': 'Entry'},
            {'id': 'a', 'type': 'server', 'label': 'A'},
            {'id': 'b', 'type': 'server', 'label': 'B'},
            {'id': 't1', 'type': 'server', 'label': 'T1'},
            {'id': 't2', 'type': 'server', 'label': 'T2'},
            {'id': 't3', 'type': 'server', 'label': 'T3'},
        ],
        'connections': [
            {'from': 'e', 'to': 'a'}, {'from': 'e', 'to': 'b'},
            # a y b comparten rango 1; b tiene más salidas
            {'from': 'a', 'to': 't1'},
            {'from': 'b', 'to': 't2'}, {'from': 'b', 'to': 't3'},
            {'from': 't1', 'to': 't2'},
        ],
    }
    apply_architecture_template(d)
    by = {e['id']: e for e in d['elements']}
    assert by['e']['y'] < min(by['a']['y'], by['b']['y'])
    assert by['b']['y'] <= by['a']['y'], 'el desempate por fan-out se perdió'
