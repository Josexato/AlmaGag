"""
Tests de §E (arcos de ciclo) y §F18 (etiquetas) del algoritmo hier
(WISH-LAF-002 Fase 3).
"""

import json

from AlmaGag.layout import Layout
from AlmaGag.layout.strategies.hier.optimizer import HierLayoutOptimizer

STRESS = 'docs/diagrams/gags/14-stresstest.sdjf'


def _optimize():
    d = json.load(open(STRESS))
    L = Layout(elements=d['elements'], connections=d['connections'],
               canvas=d.get('canvas', {'width': 1400, 'height': 900}))
    L._diagram_name = 'test'
    return HierLayoutOptimizer(verbose=False).optimize(L)


def _cp(r, f, t):
    for c in r.connections:
        if c['from'] == f and c['to'] == t:
            return c.get('computed_path')
    return None


# ---- §E arcos ----

def test_cycle_edges_are_beziers():
    """Todas las aristas del ciclo (ida + retorno) se dibujan como bezier."""
    r = _optimize()
    for f, t in (('ElemtI', 'ElemtJ'), ('ElemtJ', 'ElemtK'), ('ElemtK', 'ElemtI')):
        cp = _cp(r, f, t)
        assert cp and cp['type'] == 'bezier', f"{f}->{t} no es bezier: {cp}"
        assert cp.get('control_points')


def test_return_edge_marked_for_dashing():
    """§L40: sólo la arista de RETORNO (back-edge K→I) se marca `_cycle_return`
    (→ arco punteado). Las de ida (I→J, J→K) quedan sólidas."""
    r = _optimize()
    def marked(f, t):
        for c in r.connections:
            if c['from'] == f and c['to'] == t:
                return bool(c.get('_cycle_return'))
        return None
    assert marked('ElemtK', 'ElemtI') is True
    assert marked('ElemtI', 'ElemtJ') is False
    assert marked('ElemtJ', 'ElemtK') is False


def test_return_edge_bulges_opposite_to_ida():
    """§E15: ida (I→J, baja) y retorno (K→I, sube) comban a lados opuestos
    en X (lazo coherente)."""
    r = _optimize()
    by_id = {e['id']: e for e in r.elements}
    def bulge_dx(f, t):
        cp = _cp(r, f, t)
        (ax, ay), (bx, by) = cp['points']
        c1 = cp['control_points'][0]
        chord_mid_x = (ax + bx) / 2
        return c1[0] - chord_mid_x
    ida = bulge_dx('ElemtI', 'ElemtJ')
    ret = bulge_dx('ElemtK', 'ElemtI')
    assert ida * ret < 0, f"ida y retorno deberían combar opuesto (ida={ida}, ret={ret})"


def test_return_arc_bulges_away_from_centroid():
    """§E16: el arco de retorno comba hacia AFUERA del centroide (sea cual sea
    el lado en que quede la columna del ciclo)."""
    r = _optimize()
    from AlmaGag.config import ICON_WIDTH
    cxs = [e['x'] + ICON_WIDTH / 2 for e in r.elements if 'x' in e]
    centroid = sum(cxs) / len(cxs)
    cp = _cp(r, 'ElemtK', 'ElemtI')
    (ax, _), (bx, _) = cp['points']
    chord_mid_x = (ax + bx) / 2
    c1x = cp['control_points'][0][0]
    # la comba se aleja del centroide: mismo signo que (columna − centroide)
    assert (c1x - chord_mid_x) * (chord_mid_x - centroid) > 0


# ---- §F18 etiquetas ----

def test_label_sides_assigned():
    r = _optimize()
    for e in r.elements:
        if e.get('label'):
            assert e.get('label_position') in ('top', 'bottom', 'left', 'right')


def test_labels_no_overlap_in_render(tmp_path):
    """El render final no tiene labels sobre iconos ni labels solapados."""
    from AlmaGag.generator import generate_diagram
    from AlmaGag.validation import validate_svg
    out = str(tmp_path / 'stress.svg')
    assert generate_diagram(STRESS, layout_algorithm='hier', output_file=out)
    rep = validate_svg(out)
    assert len(rep.by_rule('R1_label_over_icon')) == 0
    assert len(rep.by_rule('R2_labels_overlap')) == 0


def test_cycle_ports_separated_at_shared_node():
    """H4: la ida y el retorno del ciclo no comparten el mismo punto de anclaje
    en un nodo (antes I→J y K→I aterrizaban ambos en el mismo puerto de I → las
    puntas de flecha se apilaban). Deben quedar separadas ≥12px."""
    r = _optimize()
    ports_at_I = []
    for c in r.connections:
        cp = c.get('computed_path')
        if not (isinstance(cp, dict) and cp.get('type') == 'bezier'):
            continue
        if c['to'] == 'ElemtI':
            ports_at_I.append(c['_to_port'])
        if c['from'] == 'ElemtI':
            ports_at_I.append(c['_from_port'])
    # al menos dos arcos de ciclo tocan I
    assert len(ports_at_I) >= 2
    for i in range(len(ports_at_I)):
        for j in range(i + 1, len(ports_at_I)):
            (ax, ay), (bx, by) = ports_at_I[i], ports_at_I[j]
            assert abs(ax - bx) >= 12 or abs(ay - by) >= 12, \
                f"puertos de ciclo apilados en I: {ports_at_I[i]} vs {ports_at_I[j]}"
