"""WISH-DRAW-004 (V82) — leyenda y estado como constructos de primera clase.

`element.status: ok|partial|empty` → badge ◉◪▢ que colorea la línea de
estado (última línea del label) sin que el autor pinte el glifo;
`canvas.legend[]` → leyenda libre (texto + swatch) al pie, apilada con
las demás. Juntos reemplazan el hack del flow blanco f4 (que U74/U77 ya
caza como error).
"""

import json

from AlmaGag.draw.icons import STATUS_BADGES
from AlmaGag.generator import generate_diagram

PPTO = 'docs/diagrams/gags/mina-presupuesto.sdjf'


def test_status_badge_colors_the_status_line(tmp_path):
    d = {'elements': [
            {'id': 'a', 'type': 'server', 'status': 'ok',
             'label': 'Nodo A\ncon datos'},
            {'id': 'b', 'type': 'server', 'status': 'partial',
             'label': 'Nodo B\ncasi'},
            {'id': 'c', 'type': 'server', 'status': 'empty',
             'label': 'Nodo C\nen cero'}],
         'connections': [{'from': 'a', 'to': 'b'}, {'from': 'b', 'to': 'c'}]}
    src = tmp_path / 'st.sdjf'
    src.write_text(json.dumps(d))
    out = tmp_path / 'st.svg'
    generate_diagram(str(src), output_file=str(out),
                     layout_algorithm='select')
    svg = out.read_text(encoding='utf-8')
    for status, (glyph, color) in STATUS_BADGES.items():
        assert glyph in svg, f'falta el glifo de {status}'
        assert color in svg, f'falta el color de {status}'
    assert '◉ con datos' in svg          # glifo antepuesto a la línea


def test_canvas_legend_draws_swatches(tmp_path):
    d = {'canvas': {'legend': [{'label': 'activo', 'color': '#2e7d32'},
                               'nota sin swatch']},
         'elements': [{'id': 'a', 'type': 'server', 'label': 'A'},
                      {'id': 'b', 'type': 'server', 'label': 'B'}],
         'connections': [{'from': 'a', 'to': 'b'}]}
    src = tmp_path / 'lg.sdjf'
    src.write_text(json.dumps(d))
    out = tmp_path / 'lg.svg'
    generate_diagram(str(src), output_file=str(out),
                     layout_algorithm='select')
    svg = out.read_text(encoding='utf-8')
    assert 'Leyenda:' in svg
    assert 'activo' in svg and 'nota sin swatch' in svg
    assert '#2e7d32' in svg              # swatch con el color declarado


def test_presupuesto_uses_first_class_constructs(tmp_path):
    """El fixture reescrito emite leyenda + estados SIN el flow f4: los
    glifos viajan como `status`, no pintados en los labels."""
    d = json.load(open(PPTO))
    assert 'legend' in d['canvas']
    assert sum(1 for e in d['elements'] if e.get('status')) >= 20
    assert not any('◉' in (e.get('label') or '') or '▢' in (e.get('label') or '')
                   for e in d['elements'])
    out = tmp_path / 'ppto.svg'
    generate_diagram(PPTO, output_file=str(out), layout_algorithm='select')
    svg = out.read_text(encoding='utf-8')
    assert 'Leyenda:' in svg and '◉ con datos' in svg
