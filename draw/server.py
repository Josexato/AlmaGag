"""
Dibuja el ícono de tipo 'server' para GAG.
"""
from AlmaGag.config import ICON_WIDTH, ICON_HEIGHT

def draw_server(dwg, x, y, color):
    """
    Dibuja un ícono de tipo 'server' como una figura SVG simple.
    """
    dwg.add(dwg.rect(insert=(x, y),
                     size=(ICON_WIDTH, ICON_HEIGHT),
                     fill=color,
                     stroke='black'))
