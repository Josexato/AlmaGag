"""
Dibuja el ícono de tipo 'cloud' para GAG.
Pictograma de nube compuesta por círculos superpuestos.
"""
from AlmaGag.config import ICON_WIDTH, ICON_HEIGHT
from AlmaGag.draw.icons import create_gradient, adjust_lightness


def draw_cloud(dwg, x, y, color, element_id):
    """
    Dibuja un ícono de tipo 'cloud' como una nube formada por círculos.
    """
    g = dwg.g(id=element_id)

    fill = create_gradient(dwg, element_id, color)
    dark = adjust_lightness(color, 0.7)

    cx = x + ICON_WIDTH / 2
    cy = y + ICON_HEIGHT / 2

    # Base plana inferior (elipse ancha)
    g.add(dwg.ellipse(
        center=(cx, cy + 8),
        r=(ICON_WIDTH * 0.45, ICON_HEIGHT * 0.22),
        fill=fill, stroke=dark, stroke_width=0.8
    ))

    # Lóbulo central superior (el más grande)
    g.add(dwg.circle(
        center=(cx, cy - 4),
        r=ICON_HEIGHT * 0.34,
        fill=fill, stroke=dark, stroke_width=0.8
    ))

    # Lóbulo izquierdo
    g.add(dwg.circle(
        center=(cx - 14, cy + 2),
        r=ICON_HEIGHT * 0.26,
        fill=fill, stroke=dark, stroke_width=0.8
    ))

    # Lóbulo derecho
    g.add(dwg.circle(
        center=(cx + 14, cy + 2),
        r=ICON_HEIGHT * 0.26,
        fill=fill, stroke=dark, stroke_width=0.8
    ))

    # Capa interior sin borde para cubrir las intersecciones
    g.add(dwg.ellipse(
        center=(cx, cy + 4),
        r=(ICON_WIDTH * 0.38, ICON_HEIGHT * 0.28),
        fill=fill, stroke='none'
    ))

    dwg.add(g)
