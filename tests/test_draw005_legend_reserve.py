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

    # content_bbox ya aplica el transform del reanclaje al medir el grupo
    for g in legends:
        sub = content_bbox(g)
        if sub is None:
            continue
        top = sub[1]
        assert top >= content_bottom + 4, \
            f'leyenda pisa el contenido (top={top:.0f} vs ' \
            f'fondo del contenido={content_bottom:.0f})'
