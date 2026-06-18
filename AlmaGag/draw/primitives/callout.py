"""
draw/callout.py - Auto-callout para labels grandes (WISH-LAYOUT-003).

Cuando un label excede los umbrales (CALLOUT_MIN_LINES, CALLOUT_MIN_CHARS)
se renderiza como un callout box separado conectado al icono con una línea
(leader). El icono queda con un label canónico corto (primera línea).

Soporta override explícito por elemento via `"callout": true/false` en SDJF.

API:
- should_use_callout(elem, label_text) -> bool
- get_canonical_label(label_text) -> str
- draw_callout(dwg, anchor_x, anchor_y, full_text, box_x, box_y)
"""

from AlmaGag.config import (
    CALLOUT_MIN_LINES, CALLOUT_MIN_CHARS,
    CALLOUT_BOX_PADDING, CALLOUT_LEADER_OFFSET,
    CALLOUT_BOX_FILL_OPACITY, CALLOUT_LEADER_DASHARRAY,
    TEXT_LINE_HEIGHT, TEXT_CHAR_WIDTH,
)


def should_use_callout(elem, label_text=None):
    """
    Decide si un elemento debe renderizar su label como callout.

    Prioridad: override explícito en SDJF > umbrales automáticos.

    Args:
        elem: dict del elemento (puede tener "callout": true/false).
        label_text: label a evaluar (opcional, default elem['label']).

    Returns:
        bool: True si corresponde callout.
    """
    if 'callout' in elem:
        return bool(elem['callout'])

    text = label_text if label_text is not None else elem.get('label', '')
    if not text:
        return False

    lines = text.split('\n')
    n_lines = len(lines)
    n_chars = len(text)

    return n_lines >= CALLOUT_MIN_LINES or n_chars >= CALLOUT_MIN_CHARS


def get_canonical_label(label_text):
    """
    Versión corta del label que queda adyacente al icono cuando se usa callout.
    Heurística: primera línea del label original.
    """
    if not label_text:
        return ''
    return label_text.split('\n', 1)[0]


def calculate_callout_position(elem, canvas_width, canvas_height):
    """
    Posición del callout box. v1: a la derecha del icono con offset fijo.
    Si se sale del canvas a la derecha, intenta abajo del icono.

    Args:
        elem: dict con x, y, width, height del elemento.
        canvas_width, canvas_height: tamaño del canvas.

    Returns:
        (box_x, box_y, placement) donde placement es 'right' | 'bottom'.
    """
    ex = elem.get('x', 0)
    ey = elem.get('y', 0)
    ew = elem.get('width', 80)
    eh = elem.get('height', 50)

    # Default: derecha del icono.
    box_x = ex + ew + CALLOUT_LEADER_OFFSET
    box_y = ey
    placement = 'right'

    # Si el callout se saldría del canvas a la derecha, ponerlo abajo.
    # (Estimación: el callout box típico ocupa ~200px de ancho.)
    if box_x + 200 > canvas_width:
        box_x = ex
        box_y = ey + eh + CALLOUT_LEADER_OFFSET
        placement = 'bottom'

    return (box_x, box_y, placement)


def _measure_callout(full_text):
    """Estima dimensiones del callout box basado en el texto."""
    lines = full_text.split('\n')
    n_lines = len(lines)
    max_line_chars = max((len(line) for line in lines), default=0)

    text_w = max_line_chars * TEXT_CHAR_WIDTH
    text_h = n_lines * TEXT_LINE_HEIGHT
    box_w = text_w + 2 * CALLOUT_BOX_PADDING
    box_h = text_h + 2 * CALLOUT_BOX_PADDING

    return (box_w, box_h, text_w, text_h)


def draw_callout(dwg, elem, full_text, canvas_width, canvas_height,
                 box_fill='white', box_stroke='#666', text_fill='black'):
    """
    Dibuja el callout box + leader line para un elemento con label grande.

    Args:
        dwg: Drawing SVG.
        elem: dict con x, y, width, height del elemento que el callout etiqueta.
        full_text: texto completo del label (multilínea).
        canvas_width, canvas_height: tamaño del canvas para placement.
        box_fill: color de fondo del box.
        box_stroke: color del borde del box.
        text_fill: color del texto.

    Returns:
        (box_x, box_y, box_w, box_h): bbox del callout box dibujado.
    """
    box_x, box_y, _ = calculate_callout_position(elem, canvas_width, canvas_height)
    box_w, box_h, _, _ = _measure_callout(full_text)

    ex = elem.get('x', 0)
    ey = elem.get('y', 0)
    ew = elem.get('width', 80)
    eh = elem.get('height', 50)
    icon_center_x = ex + ew / 2
    icon_center_y = ey + eh / 2

    leader_end_x = box_x
    leader_end_y = box_y + box_h / 2

    dwg.add(dwg.line(
        start=(icon_center_x, icon_center_y),
        end=(leader_end_x, leader_end_y),
        stroke=box_stroke, stroke_width=1.2,
        stroke_dasharray=CALLOUT_LEADER_DASHARRAY,
    ))

    dwg.add(dwg.rect(
        insert=(box_x, box_y),
        size=(box_w, box_h),
        rx=4, ry=4,
        fill=box_fill, fill_opacity=CALLOUT_BOX_FILL_OPACITY,
        stroke=box_stroke, stroke_width=1.2,
    ))

    text_x = box_x + CALLOUT_BOX_PADDING
    text_y = box_y + CALLOUT_BOX_PADDING + 14  # baseline del primer line

    for i, line in enumerate(full_text.split('\n')):
        dwg.add(dwg.text(
            line,
            insert=(text_x, text_y + i * TEXT_LINE_HEIGHT),
            text_anchor='start', font_size='12px',
            font_family='Arial, sans-serif', fill=text_fill,
        ))

    return (box_x, box_y, box_w, box_h)
