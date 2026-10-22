"""BUGS-LAYOUT-014 — el self-loop no tumba el motor: lazo propio nombrado.

Un b→b contaba como ciclo (entra a hier) pero compute_levels lo filtraba
del grafo de flujo: el SCC nunca lo veía, no caía en back_edges, y
columns lo aceptaba como hijo de sí mismo — RecursionError con un
archivo válido de 2 nodos (hallazgo PY-001 de almagag-jv, fixture c27).
Ahora el self-loop va directo a back_edges con WARNING nombrado y
route_cycle_arcs le dibuja el lazo por el costado derecho del icono.
"""

import json
import logging

from AlmaGag.generator import generate_diagram

REPRO = {'elements': [{'id': 'a', 'label': 'A'}, {'id': 'b', 'label': 'B'}],
         'connections': [{'from': 'a', 'to': 'b'},
                         {'from': 'b', 'to': 'b', 'label': 'otra vez'}],
         'canvas': {'width': 400, 'height': 300}}


def test_el_selfloop_no_revienta_y_se_nombra(tmp_path, caplog):
    src = tmp_path / 'loop.sdjf'
    src.write_text(json.dumps(REPRO), encoding='utf-8')
    out = tmp_path / 'loop.svg'
    with caplog.at_level(logging.WARNING, logger='AlmaGag'):
        assert generate_diagram(str(src), output_file=str(out),
                                layout_algorithm='select')
    assert "self-loop 'b'→'b'" in caplog.text, 'el lazo no quedó nombrado'


def test_el_lazo_se_dibuja_fuera_del_icono(tmp_path):
    """El caso degenerado previo era un bezier de 14px invisible: el lazo
    real comba HACIA AFUERA del borde derecho del icono."""
    import AlmaGag.layout.strategies.auto.auto_renderer as AR
    cap = {}
    orig = AR.AutoSVGRenderer.render

    def spy(self, layout, *a, **k):
        cap['L'] = layout
        return orig(self, layout, *a, **k)

    AR.AutoSVGRenderer.render = spy
    try:
        src = tmp_path / 'loop.sdjf'
        src.write_text(json.dumps(REPRO), encoding='utf-8')
        assert generate_diagram(str(src),
                                output_file=str(tmp_path / 'loop.svg'),
                                layout_algorithm='select')
    finally:
        AR.AutoSVGRenderer.render = orig
    L = cap['L']
    by = {e['id']: e for e in L.elements}
    loop = next(c for c in L.connections
                if c['from'] == 'b' and c['to'] == 'b')
    cp = loop['computed_path']
    assert cp['type'] == 'bezier' and cp.get('control_points'), \
        'el self-loop quedó sin trazado propio'
    from AlmaGag.config import ICON_WIDTH
    borde = by['b']['x'] + ICON_WIDTH
    assert all(cx > borde + 20 for cx, _ in cp['control_points']), \
        'el lazo no comba hacia afuera (bezier degenerado otra vez)'
    p0, p1 = cp['points']
    assert abs(p0[0] - borde) < 1 and abs(p1[0] - borde) < 1
    assert p0 != p1, 'lazo de largo cero'
