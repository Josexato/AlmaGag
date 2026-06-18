"""
Dibuja el ícono de tipo 'router' para GAG.
Pictograma de router/switch de red con puertos y antenas.
"""
from AlmaGag.config import ICON_WIDTH, ICON_HEIGHT
from AlmaGag.draw.icons import create_gradient, adjust_lightness


def draw_router(dwg, x, y, color, element_id):
    """
    Dibuja un ícono de tipo 'router' como un dispositivo de red con antenas.
    """
    g = dwg.g(id=element_id)

    fill = create_gradient(dwg, element_id, color)
    dark = adjust_lightness(color, 0.5)
    light = adjust_lightness(color, 1.4)

    w = ICON_WIDTH
    h = ICON_HEIGHT

    # Cuerpo principal (caja trapezoidal simulada con rect)
    body_y = y + 14
    body_h = h - 14
    g.add(dwg.rect(
        insert=(x + 2, body_y), size=(w - 4, body_h),
        rx=3, ry=3,
        fill=fill, stroke='black', stroke_width=1.2
    ))

    # Antenas (2 líneas diagonales desde la parte superior)
    # Antena izquierda
    g.add(dwg.line(
        start=(x + 20, body_y), end=(x + 10, y + 2),
        stroke='black', stroke_width=1.5
    ))
    g.add(dwg.circle(center=(x + 10, y + 2), r=2.5, fill=dark, stroke='black', stroke_width=0.8))

    # Antena derecha
    g.add(dwg.line(
        start=(x + w - 20, body_y), end=(x + w - 10, y + 2),
        stroke='black', stroke_width=1.5
    ))
    g.add(dwg.circle(center=(x + w - 10, y + 2), r=2.5, fill=dark, stroke='black', stroke_width=0.8))

    # Puertos de red (fila inferior, 4 rectángulos pequeños)
    port_w, port_h = 8, 6
    port_y = body_y + body_h - port_h - 4
    port_spacing = (w - 16) / 4
    for i in range(4):
        px = x + 8 + i * port_spacing
        g.add(dwg.rect(
            insert=(px, port_y), size=(port_w, port_h),
            fill=dark, stroke='black', stroke_width=0.6
        ))

    # LEDs de estado (fila superior del cuerpo)
    led_y = body_y + 6
    for i in range(5):
        lx = x + 12 + i * 12
        led_color = '#00cc44' if i < 3 else '#ffaa00'
        g.add(dwg.circle(
            center=(lx, led_y), r=2,
            fill=led_color, stroke=dark, stroke_width=0.4
        ))

    dwg.add(g)
