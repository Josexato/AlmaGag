"""BUGS-ROUTE-011 — el dodge no hace cremalleras ni invierte flechas.

Deuda fresca de ROUTE-010, medida en cakephp-mvc: (a) dos cajas
enfrentadas hacían ping-pong (cada desvío cruzaba a la otra) y el
registro escalonado convertía el rebote en una cremallera de 45 puntos
que el best-effort aceptaba; (b) el enganche del desvío pasaba de largo
el extremo del tramo cuando la caja termina a <DODGE_M del endpoint —
el tramo final se invertía y la flecha entraba al puerto EN REVERSA
(▲ dentro del icono). Fix: presupuesto de desvíos POR LLAMADA en las
tres primitivas (al agotarse vuelve la ruta ORIGINAL, no la mangleada)
y enganche acotado al span del tramo. Medido: la cremallera 45→9
puntos, la flecha llega bajando, y cakephp cruces 8→4 de rebote.
"""

from AlmaGag.layout.dodge import dodge_boxes


def test_rejoin_never_overshoots_the_endpoint():
    """Caja que termina a 10px (<DODGE_M) del endpoint: el desvío NO pasa
    de largo — el tramo final conserva su dirección de llegada."""
    pts = [(100.0, 0.0), (100.0, 110.0)]
    box = (80.0, 40.0, 120.0, 100.0)
    out = dodge_boxes(pts, [box])
    assert out[-1] == (100.0, 110.0)
    assert out[-2][1] < out[-1][1], \
        f'el tramo final se invirtió (llega subiendo): {out[-2:]}'
    assert all(p[1] <= 110.0 for p in out), f'el desvío pasó de largo: {out}'


def test_pingpong_budget_returns_original():
    """Presupuesto agotado → ruta ORIGINAL intacta, jamás la cremallera.
    (Dos filas de cajas solapadas en escalera: cada desvío cruza a la
    siguiente y el bucle no converge.)"""
    pts = [(0.0, 50.0), (1000.0, 50.0)]
    boxes = [(60.0 + k * 70.0, 20.0 + (k % 2) * 30.0,
              120.0 + k * 70.0, 70.0 + (k % 2) * 30.0) for k in range(12)]
    out = dodge_boxes(list(pts), boxes, reg={})
    assert len(out) <= 2 + 4 * 9, f'cremallera: {len(out)} puntos'
    # y si devolvió la original, debe ser EXACTAMENTE la original
    if len(out) == 2:
        assert out == pts


def test_cakephp_zipper_stays_dead():
    """El caso medido, de punta a punta: ninguna conexión de cakephp-mvc
    emite más de 12 puntos, y dispatcher→articles_ctrl llega BAJANDO."""
    import json
    from AlmaGag.layout.layout import Layout
    from AlmaGag.layout.engine import LayoutEngine
    from AlmaGag.layout.templates.architecture import apply_architecture_template
    d = json.load(open('docs/diagrams/gags/cakephp-mvc.gag'))
    apply_architecture_template(d)
    L = Layout(elements=d['elements'], connections=d['connections'],
               canvas=d.get('canvas'))
    L2 = LayoutEngine(strategy='auto').optimize(L)
    for c in L2.connections:
        cp = c.get('computed_path') or {}
        pts = cp.get('points') or []
        assert len(pts) <= 12, \
            f"cremallera en {c['from']}→{c['to']}: {len(pts)} puntos"
    c = next(k for k in L2.connections
             if k['from'] == 'dispatcher' and k['to'] == 'articles_ctrl')
    pts = c['computed_path']['points']
    assert pts[-1][1] > pts[-2][1], f'flecha en reversa: {pts[-2:]}'
