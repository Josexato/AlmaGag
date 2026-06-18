"""
Dibuja el ícono de tipo 'server' para GAG.
Pictograma de rack server con bahías de disco y LEDs indicadores.
"""
from AlmaGag.config import ICON_WIDTH, ICON_HEIGHT
from AlmaGag.draw.icons import create_gradient, adjust_lightness


def draw_server(dwg, x, y, color, element_id):
    """
    Dibuja un ícono de tipo 'server' como un rack server con 3 bahías.
    """
    g = dwg.g(id=element_id)

    fill = create_gradient(dwg, element_id, color)
    dark = adjust_lightness(color, 0.6)
    light = adjust_lightness(color, 1.4)

    w = ICON_WIDTH
    h = ICON_HEIGHT
    r = 4  # border radius

    # Cuerpo principal del server
    g.add(dwg.rect(
        insert=(x, y), size=(w, h),
        rx=r, ry=r,
        fill=fill, stroke='black', stroke_width=1.2
    ))

    # 3 bahías horizontales (líneas divisorias)
    bay_h = h / 3
    for i in range(1, 3):
        ly = y + bay_h * i
        g.add(dwg.line(
            start=(x + 2, ly), end=(x + w - 2, ly),
            stroke=dark, stroke_width=0.8
        ))

    # LEDs indicadores (2 por bahía: verde + amarillo)
    led_r = 2.5
    for i in range(3):
        by = y + bay_h * i + bay_h / 2
        # LED verde (activo)
        g.add(dwg.circle(
            center=(x + w - 12, by), r=led_r,
            fill='#00cc44', stroke=dark, stroke_width=0.5
        ))
        # LED amarillo (actividad)
        g.add(dwg.circle(
            center=(x + w - 20, by), r=led_r,
            fill='#ffaa00', stroke=dark, stroke_width=0.5
        ))

    # Ranuras de ventilación (lado izquierdo, 3 líneas cortas por bahía)
    for i in range(3):
        by = y + bay_h * i
        for j in range(3):
            vy = by + 5 + j * (bay_h - 10) / 2
            g.add(dwg.line(
                start=(x + 6, vy), end=(x + 18, vy),
                stroke=dark, stroke_width=0.6
            ))

    dwg.add(g)
