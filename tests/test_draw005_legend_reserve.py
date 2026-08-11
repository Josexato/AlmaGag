"""BUGS-DRAW-005 — el recorte O51 reserva franja para las leyendas.

Hallazgo del caso TM en el visor: el reanclaje de `ag-bottom-anchored`
conserva la distancia de cada leyenda al borde inferior, pero el borde
recortado quedaba a sólo `margin` del contenido — la pila
Estados/Recorridos/Enlaces caía ENCIMA de los labels de la última fila
('Ingeniería', 'US$ 56 K cotizados'). El borde inferior ahora deja sitio
para la pila completa + respiro de 12px.
"""

import json
import xml.etree.ElementTree as ET

from AlmaGag.draw.primitives.viewbox import (
    BOTTOM_ANCHORED_CLASS, SVG_NS, content_bbox)
from AlmaGag.generator import generate_diagram


def test_legend_stack_sits_below_content(tmp_path):
    d = {'elements': [
            {'id': 'top', 'type': 'server', 'label': 'Consolidado',
             'status': 'ok'},
            {'id': 'a', 'type': 'server', 'label': 'Rama A\ncon dos líneas',
             'status': 'partial'},
            {'id': 'b', 'type': 'server', 'label': 'Rama B\ncon dos líneas',
             'status': 'empty'}],
         'connections': [
            {'from': 'a', 'to': 'top', 'semantic_type': 'data_link'},
            {'from': 'b', 'to': 'top', 'semantic_type': 'control_link'},
            {'from': 'a', 'to': 'b', 'semantic_type': 'event'}],
         'journeys': [{'id': 'j1', 'label': 'Recorrido demo',
                       'path': ['a', 'top']}],
         'canvas': {'width': 900, 'height': 700,
                    'legend': [{'label': 'Estados: ◉ ok ◪ parcial ▢ cero'}]}}
    src = tmp_path / 'leg.gag'
    src.write_text(json.dumps(d), encoding='utf-8')
    out = tmp_path / 'leg.svg'
    assert generate_diagram(str(src), output_file=str(out),
                            layout_algorithm='select')
    root = ET.fromstring(out.read_text(encoding='utf-8'))

    legends = [g for g in root.iter(f'{{{SVG_NS}}}g')
               if BOTTOM_ANCHORED_CLASS in (g.get('class') or '').split()]
    assert legends, 'el fixture debe emitir leyendas ancladas abajo'

    body = content_bbox(root, skip_classes=(BOTTOM_ANCHORED_CLASS,))
    assert body is not None
    content_bottom = body[3]

    # content_bbox ya aplica el transform del reanclaje al medir el grupo.
    # OJO al auditar a mano: el atributo y crudo del <text> queda en el pie
    # del canvas ORIGINAL (p.ej. 874) y el translate del grupo lo trae a la
    # lámina — medir el crudo da un falso «leyenda fuera del viewBox»
    # (reporte 3 del Skiller, refutado con el PNG rasterizado).
    import re as _re
    vb = [float(n) for n in _re.findall(r'[\d.]+', root.get('viewBox'))]
    vb_bottom = vb[1] + vb[3]
    for g in legends:
        sub = content_bbox(g)
        if sub is None:
            continue
        top, bottom = sub[1], sub[3]
        assert top >= content_bottom + 4, \
            f'leyenda pisa el contenido (top={top:.0f} vs ' \
            f'fondo del contenido={content_bottom:.0f})'
        assert bottom <= vb_bottom + 0.5, \
            f'leyenda FUERA del viewBox (bottom={bottom:.0f} vs ' \
            f'borde={vb_bottom:.0f})'


def test_default_canvas_legend_inside_cropped_viewbox(tmp_path):
    """Repro exacto del reporte 3 del Skiller (leg_min): SIN canvas
    declarado, la leyenda se dibuja al pie del default 900 y el recorte
    la trae DENTRO de la lámina vía translate. Medir el atributo y crudo
    del <text> (874) sin el transform da un falso «fuera del viewBox»."""
    import json
    import re as _re
    from AlmaGag.generator import generate_diagram
    d = {'elements': [{'id': i, 'type': 'server', 'label': i.upper()}
                      for i in ['a', 'b', 'c']],
         'connections': [{'from': 'a', 'to': 'b', 'direction': 'forward'},
                         {'from': 'b', 'to': 'c', 'direction': 'forward'}],
         'journeys': [{'id': 'j', 'label': 'Recorrido de prueba',
                       'path': ['a', 'b', 'c']}]}
    src = tmp_path / 'leg_min.sdjf'
    src.write_text(json.dumps(d), encoding='utf-8')
    out = tmp_path / 'leg_min.svg'
    assert generate_diagram(str(src), output_file=str(out),
                            layout_algorithm='select')
    root = ET.fromstring(out.read_text(encoding='utf-8'))
    vb = [float(n) for n in _re.findall(r'[\d.]+', root.get('viewBox'))]
    vb_bottom = vb[1] + vb[3]
    legends = [g for g in root.iter(f'{{{SVG_NS}}}g')
               if BOTTOM_ANCHORED_CLASS in (g.get('class') or '').split()]
    assert legends
    for g in legends:
        sub = content_bbox(g)          # aplica el transform del grupo
        assert sub is not None
        assert sub[3] <= vb_bottom + 0.5, \
            f'leyenda fuera del viewBox: bottom={sub[3]:.0f} vs {vb_bottom:.0f}'
        assert sub[1] >= vb[1], 'leyenda por encima del viewBox'
