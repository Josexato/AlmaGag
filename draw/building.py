"""
Dibuja el ícono de tipo 'building' para GAG.
"""

def draw_building(dwg, x, y, color):
    """
    Dibuja un ícono de tipo 'building' como una figura SVG simple.
    """
    dwg.add(dwg.rect(insert=(x, y),
                     size=(80, 50),
                     fill=color,
                     stroke='black'))
