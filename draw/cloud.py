"""
Dibuja el ícono de tipo 'cloud' para GAG.
"""
from AlmaGag.config import ICON_WIDTH, ICON_HEIGHT

def draw_cloud(dwg, x, y, color):
    """
    Dibuja un ícono de tipo 'cloud' como una elipse SVG.
    """
    dwg.add(dwg.ellipse(center=(x + ICON_WIDTH / 2, y + ICON_HEIGHT / 2),
                        r=(ICON_WIDTH / 2, ICON_HEIGHT / 2),
                        fill=color,
                        stroke='black'))