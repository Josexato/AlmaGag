"""
Dibuja el ícono de tipo 'building' para GAG.
Pictograma de edificio con ventanas y puerta.
"""
from AlmaGag.config import ICON_WIDTH, ICON_HEIGHT
from AlmaGag.draw.icons import create_gradient, adjust_lightness


def draw_building(dwg, x, y, color, element_id):
    """
    Dibuja un ícono de tipo 'building' como un edificio con ventanas.
    """
    g = dwg.g(id=element_id)

    fill = create_gradient(dwg, element_id, color)
    dark = adjust_lightness(color, 0.5)
    light = adjust_lightness(color, 1.5)

    w = ICON_WIDTH
    h = ICON_HEIGHT
    r = 2

    # Cuerpo principal del edificio
    g.add(dwg.rect(
        insert=(x + 8, y + 4), size=(w - 16, h - 4),
        rx=r, ry=r,
        fill=fill, stroke='black', stroke_width=1.2
    ))

    # Techo (triángulo)
    roof_points = [
        (x + 4, y + 4),
        (x + w / 2, y - 6),
        (x + w - 4, y + 4)
    ]
    g.add(dwg.polygon(
        points=roof_points,
        fill=dark, stroke='black', stroke_width=1.0
    ))

    # Ventanas (2 filas x 3 columnas)
    win_w, win_h = 10, 7
    win_color = light
    cols = [x + 15, x + 35, x + 55]
    rows = [y + 10, y + 24]

    for row_y in rows:
        for col_x in cols:
            g.add(dwg.rect(
                insert=(col_x, row_y), size=(win_w, win_h),
                fill=win_color, stroke=dark, stroke_width=0.7
            ))
            # Cruz de la ventana
            g.add(dwg.line(
                start=(col_x + win_w / 2, row_y),
                end=(col_x + win_w / 2, row_y + win_h),
                stroke=dark, stroke_width=0.5
            ))
            g.add(dwg.line(
                start=(col_x, row_y + win_h / 2),
                end=(col_x + win_w, row_y + win_h / 2),
                stroke=dark, stroke_width=0.5
            ))

    # Puerta central
    door_w, door_h = 10, 12
    door_x = x + w / 2 - door_w / 2
    door_y = y + h - door_h
    g.add(dwg.rect(
        insert=(door_x, door_y), size=(door_w, door_h),
        fill=dark, stroke='black', stroke_width=0.8
    ))
    # Pomo
    g.add(dwg.circle(
        center=(door_x + door_w - 2.5, door_y + door_h / 2),
        r=1.2, fill=light
    ))

    dwg.add(g)
