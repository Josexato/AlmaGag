"""BUGS-DRAW-002 — currentColor en iconos embebidos se resuelve al color
del elemento (la promesa original de la spec, ahora cumplida)."""

from AlmaGag.draw.icons import draw_icon_shape
from AlmaGag.draw.primitives.svg import create_canvas

TPL = ("<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 80 50'>"
       "<rect width='80' height='50' fill='currentColor' stroke='#111'/></svg>")
FIXED = ("<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 80 50'>"
         "<rect width='80' height='50' fill='#2E75B6'/></svg>")


def _render(tmp_path, elem, icons):
    dwg = create_canvas(str(tmp_path / 'o.svg'), 300, 200)
    draw_icon_shape(dwg, elem, embedded_icons=icons)
    return dwg.tostring()


def test_currentcolor_takes_element_color(tmp_path):
    svg = _render(tmp_path, {'id': 'a', 'type': 'sensor', 'x': 0, 'y': 0,
                             'color': 'tomato'}, {'sensor': TPL})
    assert 'currentColor' not in svg
    assert 'tomato' in svg


def test_currentcolor_defaults_to_gray(tmp_path):
    """Sin `color` declarado, cae al default de los built-ins (gray)."""
    svg = _render(tmp_path, {'id': 'a', 'type': 'sensor', 'x': 0, 'y': 0},
                  {'sensor': TPL})
    assert 'currentColor' not in svg
    assert 'gray' in svg


def test_fixed_colors_untouched(tmp_path):
    """Un icono con hex fijos se inserta tal cual: el color del elemento
    NO lo pinta (regla vigente para catálogos como el del skill)."""
    svg = _render(tmp_path, {'id': 'a', 'type': 'sensor', 'x': 0, 'y': 0,
                             'color': 'tomato'}, {'sensor': FIXED})
    assert '#2E75B6' in svg
    assert 'tomato' not in svg
