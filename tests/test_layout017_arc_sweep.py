"""BUGS-LAYOUT-017 — la comba E17 ya no barre la lámina (E17 v2).

Dos cegueras juntas hacían spaghetti en ciclos largos (censo honesto de
BUGS-LOG-003 sobre layout-optimization-flow: cruces=4, arista×nodo=2):
E17 solo miraba nodos a ±72px de la CUERDA — una comba crecida barre
mucho más lejos y pisaba nodos que ese test no veía — y el signo global
E15 obligaba a combar hacia un lado poblado con el otro vacío. Ahora la
comba se calcula por punto fijo sobre la banda barrida completa y las
aristas de IDA eligen el lado más barato (desempate: el signo global,
que conserva el giro coherente — los ciclos clásicos emiten SVG byte-
idéntico); el RETORNO conserva su lado E16 (lazo exterior).
"""

import json
from AlmaGag.layout.layout import Layout
from AlmaGag.layout.engine import LayoutEngine
from AlmaGag.layout.metrics import quality_counters
from AlmaGag.layout.strategies.hier.arcs import (_side_bulge, BULGE_BASE,
                                                 BULGE_CAP)


def test_swept_band_sees_beyond_the_old_72px():
    """Punto fijo de la banda: un nodo pegado a la cuerda infla la comba,
    y OTRO nodo lejano (perp=170, invisible para el test viejo de ±72px)
    queda dentro de la banda barrida y la encarece hasta el tope — ese
    lado pierde contra el lado vacío."""
    ca, ex, ey, elen, n = (0.0, 0.0), 400.0, 0.0, 400.0, (0.0, 1.0)
    nodes = [((200.0, 46.0), 'cerca'), ((160.0, 170.0), 'lejos')]
    caro = _side_bulge(ca, ex, ey, elen, n, 1.0, nodes, ())
    vacio = _side_bulge(ca, ex, ey, elen, n, -1.0, nodes, ())
    assert caro >= BULGE_CAP - 0.5, f'la banda no vio el nodo lejano: {caro}'
    assert abs(vacio - BULGE_BASE) < 0.5, f'el lado vacío debe costar base: {vacio}'


def test_cycle_heavy_diagram_stays_legible():
    """El caso medido: layout-optimization-flow (doble ciclo, 14 arcos).
    Congelado el censo post-fix: ≤1 cruce (el apretón retorno×ida que la
    doctrina E16 acepta) y CERO arista×nodo — era 4 y 2 con el barrido."""
    d = json.load(open('docs/diagrams/gags/layout-optimization-flow.sdjf'))
    L = Layout(elements=d['elements'], connections=d['connections'],
               canvas=d.get('canvas', {'width': 1200, 'height': 800}))
    L2 = LayoutEngine(strategy='hier').optimize(L)
    q = quality_counters(L2)
    assert q['edge_x_edge'] <= 1, q
    assert q['edge_x_node'] == 0, q
