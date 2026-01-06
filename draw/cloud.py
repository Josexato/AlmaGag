"""
Dibuja el ícono de tipo 'cloud' para GAG.
"""
from AlmaGag.config import ICON_WIDTH, ICON_HEIGHT
from AlmaGag.draw.icons import create_gradient

def draw_cloud(dwg, x, y, color, element_id):
    """
    Dibuja un ícono de tipo 'cloud' como una elipse SVG con gradiente.
    """
    fill = create_gradient(dwg, element_id, color)
    dwg.add(dwg.ellipse(center=(x + ICON_WIDTH / 2, y + ICON_HEIGHT / 2),
                        r=(ICON_WIDTH / 2, ICON_HEIGHT / 2),
                        fill=fill,
                        stroke='black'))