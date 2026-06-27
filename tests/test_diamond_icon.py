"""
Tests para el icono 'diamond' / 'decision' (WISH-DRAW-001).
"""

import svgwrite
from AlmaGag.draw.icons.diamond import draw_diamond, draw_decision
from AlmaGag.draw.icons import draw_icon_shape
from AlmaGag.config import ICON_WIDTH, ICON_HEIGHT


def _render(elem):
    dwg = svgwrite.Drawing(size=(600, 300))
    draw_icon_shape(dwg, elem)
    return dwg.tostring()


def test_diamond_renders_polygon():
    dwg = svgwrite.Drawing(size=(200, 200))
    draw_diamond(dwg, 50, 50, 'gold', 'd1')
    out = dwg.tostring()
    assert '<polygon' in out
    # Cuatro vértices en los puntos medios del bbox
    cx, cy = 50 + ICON_WIDTH / 2, 50 + ICON_HEIGHT / 2
    assert f'{cx},50' in out          # top
    assert f'50,{cy}' in out          # left


def test_decision_is_alias_of_diamond():
    dwg1 = svgwrite.Drawing(size=(200, 200))
    draw_diamond(dwg1, 10, 10, 'yellow', 'x')
    dwg2 = svgwrite.Drawing(size=(200, 200))
    draw_decision(dwg2, 10, 10, 'yellow', 'x')
    assert dwg1.tostring() == dwg2.tostring()


def test_dispatcher_resolves_diamond_type():
    """El dispatcher (importlib) debe encontrar el módulo, sin caer al bwt."""
    out = _render({'id': 'd', 'type': 'diamond', 'color': 'gold', 'x': 100, 'y': 100})
    assert '<polygon' in out
    # No debe haber caído al fallback Banana With Tape
    assert 'banana' not in out.lower()


def test_dispatcher_resolves_decision_type():
    out = _render({'id': 'b', 'type': 'decision', 'color': 'yellow', 'x': 100, 'y': 100})
    assert '<polygon' in out
    assert 'banana' not in out.lower()
