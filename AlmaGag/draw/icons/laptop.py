"""
Dibuja el ícono de tipo 'laptop' para GAG.
Pictograma de laptop/portátil con pantalla y teclado.
"""
from AlmaGag.config import ICON_WIDTH, ICON_HEIGHT
from AlmaGag.draw.icons import create_gradient, adjust_lightness


def draw_laptop(dwg, x, y, color, element_id):
    """
    Dibuja un ícono de tipo 'laptop' como un portátil abierto visto de frente.
    """
    g = dwg.g(id=element_id)

    fill = create_gradient(dwg, element_id, color)
    dark = adjust_lightness(color, 0.5)
    light = adjust_lightness(color, 1.5)

    w = ICON_WIDTH
    h = ICON_HEIGHT

    # Pantalla (parte superior, ~65% de la altura)
    screen_h = h * 0.62
    screen_margin = 6
    g.add(dwg.rect(
        insert=(x + 4, y), size=(w - 8, screen_h),
        rx=3, ry=3,
        fill=dark, stroke='black', stroke_width=1.2
    ))
    # Área de display (interior de la pantalla)
    g.add(dwg.rect(
        insert=(x + 4 + screen_margin, y + screen_margin * 0.6),
        size=(w - 8 - screen_margin * 2, screen_h - screen_margin * 1.4),
        fill=light, stroke=dark, stroke_width=0.5
    ))

    # Base/teclado (parte inferior)
    base_y = y + screen_h
    base_h = h - screen_h
    g.add(dwg.rect(
        insert=(x, base_y), size=(w, base_h),
        rx=2, ry=2,
        fill=fill, stroke='black', stroke_width=1.2
    ))

    # Teclas (grid 6x2)
    key_w, key_h = 7, 3
    key_start_x = x + 8
    key_start_y = base_y + 3
    for row in range(2):
        for col in range(6):
            kx = key_start_x + col * (key_w + 3)
            ky = key_start_y + row * (key_h + 2)
            g.add(dwg.rect(
                insert=(kx, ky), size=(key_w, key_h),
                rx=0.5, ry=0.5,
                fill=dark, stroke='none'
            ))

    # Touchpad
    tp_w, tp_h = 16, 6
    g.add(dwg.rect(
        insert=(x + w / 2 - tp_w / 2, base_y + base_h - tp_h - 1),
        size=(tp_w, tp_h),
        rx=1, ry=1,
        fill=dark, stroke='none', opacity=0.4
    ))

    dwg.add(g)
