"""
Dibuja el ícono de tipo 'building' para GAG.
"""
from AlmaGag.config import ICON_WIDTH, ICON_HEIGHT
from AlmaGag.draw.icons import create_gradient

def draw_building(dwg, x, y, color, element_id):
    """
    Dibuja un ícono de tipo 'building' como una figura SVG con gradiente.
    Incluye padding interno del 20% de la altura.
    """
    # Padding del 20% de la altura del ícono
    padding = ICON_HEIGHT * 0.2  # 50 * 0.2 = 10px

    # Ajustar posición y tamaño con padding
    icon_x = x + padding
    icon_y = y + padding
    icon_width = ICON_WIDTH - (2 * padding)  # 80 - 20 = 60px
    icon_height = ICON_HEIGHT - (2 * padding)  # 50 - 20 = 30px

    fill = create_gradient(dwg, element_id, color)
    dwg.add(dwg.rect(insert=(icon_x, icon_y),
                     size=(icon_width, icon_height),
                     fill=fill,
                     stroke='black'))
