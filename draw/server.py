"""
Dibuja el ícono de tipo 'server' para GAG.
"""

def draw_server(dwg, x, y, color):
    """
    Dibuja un ícono de tipo 'server' como una figura SVG simple.
    """
    dwg.add(dwg.rect(insert=(x, y),
                     size=(80, 50),
                     fill=color,
                     stroke='black'))
