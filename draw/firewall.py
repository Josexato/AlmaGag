"""
Dibuja el ícono de tipo 'firewall' para GAG.
"""

def draw_firewall(dwg, x, y, color):
    """
    Dibuja un ícono de tipo 'firewall' como una figura SVG simple.
    """
    dwg.add(dwg.rect(insert=(x, y),
                     size=(80, 50),
                     fill=color,
                     stroke='black'))
