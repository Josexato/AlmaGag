"""
Dibuja el ícono de tipo 'server' para GAG.
"""
from AlmaGag.config import ICON_WIDTH, ICON_HEIGHT
from AlmaGag.draw.icons import create_gradient

def draw_server(dwg, x, y, color, element_id):
    """
    Dibuja un ícono de tipo 'server' como una figura SVG con gradiente.
    """
    fill = create_gradient(dwg, element_id, color)
    dwg.add(dwg.rect(insert=(x, y),
                     size=(ICON_WIDTH, ICON_HEIGHT),
                     fill=fill,
                     stroke='black'))
