"""
Tests del ruteo §C+§D del algoritmo hier (WISH-LAF-002 Fase 2).
"""

import json

from AlmaGag.layout import Layout
from AlmaGag.layout.strategies.hier.optimizer import HierLayoutOptimizer

STRESS = 'docs/diagrams/gags/14-stresstest.sdjf'


def _optimize(data):
    L = Layout(elements=data['elements'], connections=data['connections'],
               canvas=data.get('canvas', {'width': 1400, 'height': 900}))
    L._diagram_name = 'test'
    return HierLayoutOptimizer(verbose=False).optimize(L)


def _cp(r, f, t):
    for c in r.connections:
        if c['from'] == f and c['to'] == t:
            return c.get('computed_path')
    return None


def test_every_forward_edge_has_computed_path():
    r = _optimize(json.load(open(STRESS)))
    for c in r.connections:
        if (c['from'], c['to']) == ('ElemtK', 'ElemtI'):
            continue  # back-edge → arco §E (Fase 3)
        assert c.get('computed_path'), f"{c['from']}->{c['to']} sin computed_path"


def test_back_edge_rendered_as_arc():
    """La back-edge se dibuja como arco de ciclo (§E, Fase 3): bezier."""
    r = _optimize(json.load(open(STRESS)))
    cp = _cp(r, 'ElemtK', 'ElemtI')
    assert cp and cp['type'] == 'bezier'


def test_same_level_edge_is_straight():
    """§D12: F→I (mismo nivel) se dibuja recto (2 puntos)."""
    r = _optimize(json.load(open(STRESS)))
    cp = _cp(r, 'ElemtF', 'ElemtI')
    assert cp and len(cp['points']) == 2


def test_side_feeder_routing_three_points():
    """§C11: toma B→E sale por costado, horizontal, baja (3 puntos)."""
    r = _optimize(json.load(open(STRESS)))
    cp = _cp(r, 'ElemtB', 'ElemtE')
    assert cp and len(cp['points']) == 3


def test_ports_on_element_border():
    """§C9/§C10: el puerto de salida está sobre un borde del icono origen."""
    r = _optimize(json.load(open(STRESS)))
    by_id = {e['id']: e for e in r.elements}
    from AlmaGag.config import ICON_WIDTH, ICON_HEIGHT
    cp = _cp(r, 'ElemtA', 'ElemtD')
    p0 = cp['points'][0]
    a = by_id['ElemtA']
    # el puerto de A está en su borde inferior (flujo hacia abajo)
    assert abs(p0[1] - (a['y'] + ICON_HEIGHT)) < 1.0
    assert a['x'] <= p0[0] <= a['x'] + ICON_WIDTH


def test_containers_do_not_crash_routing():
    """Conexiones a elementos contenidos (sin posición hier) no rompen."""
    d = json.load(open('docs/diagrams/gags/07-containers.sdjf'))
    r = _optimize(d)  # no debe lanzar
    assert r is not None


def test_m44_crossings_pure_straight():
    """§M44: los cruces D13 (E→I, H→F del stresstest) son recta PURA de 2
    puntos, borde a borde — sin stubs perpendiculares (híbrido codo+diagonal)."""
    import json
    from AlmaGag.layout import Layout
    from AlmaGag.layout.strategies.hier.optimizer import HierLayoutOptimizer
    d = json.load(open('docs/diagrams/gags/14-stresstest.sdjf'))
    L = Layout(elements=d['elements'], connections=d['connections'],
               canvas=d.get('canvas', {}))
    L._diagram_name = 't'
    r = HierLayoutOptimizer(verbose=False).optimize(L)
    found = 0
    for c in r.connections:
        if (c['from'], c['to']) in (('ElemtE', 'ElemtI'), ('ElemtH', 'ElemtF')):
            pts = c['computed_path']['points']
            assert len(pts) == 2, f"{c['from']}→{c['to']}: {len(pts)} puntos (híbrido)"
            assert c.get('_straight') is True
            found += 1
    assert found == 2
