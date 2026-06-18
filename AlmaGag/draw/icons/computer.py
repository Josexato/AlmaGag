"""
Dibuja el ícono de tipo 'computer' para GAG.
Pictograma de monitor de escritorio con base.
"""
from AlmaGag.config import ICON_WIDTH, ICON_HEIGHT
from AlmaGag.draw.icons import create_gradient, adjust_lightness


def draw_computer(dwg, x, y, color, element_id):
    """
    Dibuja un ícono de tipo 'computer' como un monitor con base.
    """
    g = dwg.g(id=element_id)

    fill = create_gradient(dwg, element_id, color)
    dark = adjust_lightness(color, 0.5)
    light = adjust_lightness(color, 1.5)

    w = ICON_WIDTH
    h = ICON_HEIGHT

    # Monitor (parte superior, ~70%)
    mon_h = h * 0.68
    g.add(dwg.rect(
        insert=(x + 2, y), size=(w - 4, mon_h),
        rx=3, ry=3,
        fill=dark, stroke='black', stroke_width=1.2
    ))
    # Pantalla (interior)
    bezel = 4
    g.add(dwg.rect(
        insert=(x + 2 + bezel, y + bezel),
        size=(w - 4 - bezel * 2, mon_h - bezel * 2 - 2),
        fill=light, stroke=dark, stroke_width=0.5
    ))

    # Cuello/soporte
    neck_w = 10
    neck_h = 6
    neck_x = x + w / 2 - neck_w / 2
    neck_y = y + mon_h
    g.add(dwg.rect(
        insert=(neck_x, neck_y), size=(neck_w, neck_h),
        fill=fill, stroke='black', stroke_width=0.8
    ))

    # Base
    base_w = 30
    base_h = 4
    base_x = x + w / 2 - base_w / 2
    base_y = neck_y + neck_h
    g.add(dwg.rect(
        insert=(base_x, base_y), size=(base_w, base_h),
        rx=2, ry=2,
        fill=fill, stroke='black', stroke_width=1.0
    ))

    # LED indicador en el borde inferior del monitor
    g.add(dwg.circle(
        center=(x + w / 2, y + mon_h - 3), r=1.5,
        fill='#00cc44', stroke=dark, stroke_width=0.4
    ))

    dwg.add(g)
