"""BUGS-TPL-004 — la cadena de entrada se ancla al baricentro de sus
hijos reales, no al centro del canvas.

En cakephp-mvc, dispatcher alimenta SOLO a los controllers (columna
izquierda) pero la cadena request→router→dispatcher colgaba sobre el
centro del canvas (encima de models_box): sus aristas viajaban hasta la
columna correcta cruzando el canal central (problema 3 del segundo
reporte GAG-WV — verificado; su «elimina 4 de los 8 cruces» no resistió
la medición: solo 1 par involucraba a dispatcher). Ahora los containers
se colocan primero y la cadena hereda el baricentro de sus destinos
externos resueltos al contenedor; sin destinos externos, el centro del
canvas (contrato histórico).
"""

import json
from AlmaGag.layout.templates.architecture import apply_architecture_template


def test_chain_hangs_over_its_real_children():
    d = json.load(open('docs/diagrams/gags/cakephp-mvc.gag'))
    apply_architecture_template(d)
    by = {e['id']: e for e in d['elements']}
    controllers_cx = by['controllers_box']['x'] + 140      # 280/2 estimado
    models_cx = by['models_box']['x'] + 140
    for eid in ('request', 'router', 'dispatcher'):
        cx = by[eid]['x'] + 40
        assert abs(cx - controllers_cx) < abs(cx - models_cx), \
            f'{eid} sigue colgado del centro: x={by[eid]["x"]}'
    # y comparten columna (la cadena no se desparrama)
    assert len({by[k]['x'] for k in ('request', 'router', 'dispatcher')}) == 1


def test_chain_without_external_targets_stays_centered():
    """Cadena que no alimenta a nadie fuera de sí: centro del canvas
    (el contrato histórico no cambia)."""
    d = {
        'elements': [
            {'id': 'a', 'type': 'server', 'label': 'A'},
            {'id': 'b', 'type': 'server', 'label': 'B'},
            {'id': 'box', 'type': 'building', 'label': 'Caja',
             'contains': ['m']},
            {'id': 'm', 'type': 'server', 'label': 'M'},
            {'id': 'box2', 'type': 'building', 'label': 'Caja2',
             'contains': ['n']},
            {'id': 'n', 'type': 'server', 'label': 'N'},
        ],
        'connections': [{'from': 'a', 'to': 'b'},
                        {'from': 'm', 'to': 'n'}],
    }
    apply_architecture_template(d)
    by = {e['id']: e for e in d['elements']}
    canvas_cx = d['canvas']['width'] // 2
    assert abs((by['a']['x'] + 40) - canvas_cx) < 1.0, by['a']
