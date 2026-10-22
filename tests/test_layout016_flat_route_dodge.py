"""BUGS-LAYOUT-016 — Z96 fase 2 en el flujo plano de hier.

El dodge de travesías («la ruta no atraviesa lo que no es suyo») solo
corría en la vista areas; en el hier plano la recta D12 de mismo nivel
podía atravesar un icono hermano (c21: la dashed de sync sobre `bd`,
residual nombrado del ticket 015). Ahora: la recta que atraviesa vuelve
al codo ortogonal y el post-pass la desvía rodeando icono+label (W87),
con registro escalonado compartido (ROUTE-008). Las rectas sanas quedan
rectas — cero regresión en D12/D13.
"""

from AlmaGag.config import ICON_WIDTH, ICON_HEIGHT
from AlmaGag.layout.layout import Layout
from AlmaGag.layout.strategies.hier.dodge import seg_crosses_box
from AlmaGag.layout.strategies.hier.optimizer import HierLayoutOptimizer


def _run(elements, connections):
    L = Layout(elements=elements, connections=connections,
               canvas={'width': 1200, 'height': 800})
    return HierLayoutOptimizer().optimize(L)


def _traversals(layout):
    """Pares (conexión, icono) donde un tramo de polyline cruza de lado a
    lado el core de un icono ajeno."""
    boxes = {e['id']: (e['x'], e['y'], e['x'] + ICON_WIDTH,
                       e['y'] + ICON_HEIGHT)
             for e in layout.elements if 'x' in e}
    hits = []
    for c in layout.connections:
        cp = c.get('computed_path')
        if not (cp and cp.get('type') == 'polyline'):
            continue
        pts = cp['points']
        for eid, b in boxes.items():
            if eid in (c['from'], c['to']):
                continue
            if any(seg_crosses_box(p, q, b) for p, q in zip(pts, pts[1:])):
                hits.append((c['from'], c['to'], eid))
    return hits


# La estructura de c21: tres iconos en el mismo nivel (a, b, c) donde la
# recta a→c pasaría sobre b, más una pata inferior que no estorba.
_ELS = [
    {'id': 'a', 'type': 'server', 'label': 'Aplicación'},
    {'id': 'b', 'type': 'database', 'label': 'Base de datos'},
    {'id': 'c', 'type': 'database', 'label': 'Caché'},
    {'id': 'd', 'type': 'server', 'label': 'Cola de eventos'},
]
_CONNS = [
    {'from': 'a', 'to': 'b', 'semantic_type': 'data_link'},
    {'from': 'a', 'to': 'c', 'semantic_type': 'sync', 'style': 'dashed'},
    {'from': 'a', 'to': 'd', 'semantic_type': 'event'},
]


def test_same_level_straight_dodges_sibling_icon():
    """La recta de mismo nivel que atravesaba al hermano se desvía: cero
    travesías de polyline sobre iconos ajenos, y la ruta sigue ortogonal."""
    L = _run([dict(e) for e in _ELS], [dict(c) for c in _CONNS])
    assert _traversals(L) == [], _traversals(L)
    sync = next(c for c in L.connections
                if c['from'] == 'a' and c['to'] == 'c')
    pts = sync['computed_path']['points']
    assert len(pts) > 2, 'la recta que atravesaba debió volverse codo'
    for p, q in zip(pts, pts[1:]):
        assert abs(p[0] - q[0]) < 0.5 or abs(p[1] - q[1]) < 0.5, \
            f'tramo diagonal en la ruta desviada: {p}→{q}'


def test_clean_straight_stays_straight():
    """D12 sano: la recta de mismo nivel que NO atraviesa nada queda recta
    (cero regresión — el fallback al codo es solo para travesías)."""
    conns = [{'from': 'a', 'to': 'b', 'semantic_type': 'data_link'},
             {'from': 'b', 'to': 'c', 'semantic_type': 'sync'},
             {'from': 'a', 'to': 'd', 'semantic_type': 'event'}]
    L = _run([dict(e) for e in _ELS], conns)
    c = next(k for k in L.connections if k['to'] == 'd')
    assert c.get('_straight'), 'la recta sana perdió su marca D12'
    assert len(c['computed_path']['points']) == 2
