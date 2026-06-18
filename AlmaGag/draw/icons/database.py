"""
Dibuja el ícono de tipo 'database' para GAG.
Pictograma de cilindro (disco de base de datos).
"""
from AlmaGag.config import ICON_WIDTH, ICON_HEIGHT
from AlmaGag.draw.icons import create_gradient, adjust_lightness


def draw_database(dwg, x, y, color, element_id):
    """
    Dibuja un ícono de tipo 'database' como un cilindro con tapa elíptica.
    """
    g = dwg.g(id=element_id)

    fill = create_gradient(dwg, element_id, color)
    dark = adjust_lightness(color, 0.6)
    light = adjust_lightness(color, 1.3)

    cx = x + ICON_WIDTH / 2
    rx = ICON_WIDTH * 0.42
    ry = 8  # curvatura de la elipse

    body_top = y + ry + 2
    body_bot = y + ICON_HEIGHT - ry - 2

    # Cuerpo del cilindro (rectángulo entre elipses)
    g.add(dwg.rect(
        insert=(cx - rx, body_top), size=(rx * 2, body_bot - body_top),
        fill=fill, stroke='none'
    ))

    # Bordes laterales del cilindro
    g.add(dwg.line(
        start=(cx - rx, body_top), end=(cx - rx, body_bot),
        stroke='black', stroke_width=1.2
    ))
    g.add(dwg.line(
        start=(cx + rx, body_top), end=(cx + rx, body_bot),
        stroke='black', stroke_width=1.2
    ))

    # Elipse inferior (base)
    g.add(dwg.ellipse(
        center=(cx, body_bot), r=(rx, ry),
        fill=fill, stroke='black', stroke_width=1.2
    ))

    # Elipse superior (tapa) - más clara
    g.add(dwg.ellipse(
        center=(cx, body_top), r=(rx, ry),
        fill=light, stroke='black', stroke_width=1.2
    ))

    # Líneas horizontales decorativas (discos internos)
    for i in range(1, 3):
        ly = body_top + (body_bot - body_top) * i / 3
        g.add(dwg.ellipse(
            center=(cx, ly), r=(rx, ry * 0.6),
            fill='none', stroke=dark, stroke_width=0.6
        ))

    dwg.add(g)
