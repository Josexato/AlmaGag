"""
Dibuja el ícono de tipo 'cloud' para GAG.
"""

def draw_cloud(dwg, x, y, color):
    """
    Dibuja un ícono de tipo 'cloud' como una elipse SVG.
    """
    dwg.add(dwg.ellipse(center=(x + 40, y + 25),
                        r=(40, 25),
                        fill=color,
                        stroke='black'))