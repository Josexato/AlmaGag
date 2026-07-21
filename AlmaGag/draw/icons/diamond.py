"""
Dibuja el ícono de tipo 'diamond' para GAG.
Rombo (decision / abstract) — convención UML/BPMN.

Útil para nodos abstractos, decisiones o interfaces en diagramas
arquitectónicos (WISH-DRAW-001).
"""
from AlmaGag.config import ICON_WIDTH, ICON_HEIGHT
from AlmaGag.draw.icons import create_gradient, adjust_lightness


def draw_diamond(dwg, x, y, color, element_id):
    """
    Dibuja un rombo (diamante) inscrito en el bbox ICON_WIDTH x ICON_HEIGHT.

    Los cuatro vértices tocan los puntos medios de cada lado del bbox,
    de modo que el centro y los anclajes de conexión coinciden con los
    de cualquier otro icono rectangular.
    """
    g = dwg.g(id=element_id)

    fill = create_gradient(dwg, element_id, color)
    dark = adjust_lightness(color, 0.6)

    cx = x + ICON_WIDTH / 2
    cy = y + ICON_HEIGHT / 2

    top = (cx, y)
    right = (x + ICON_WIDTH, cy)
    bottom = (cx, y + ICON_HEIGHT)
    left = (x, cy)

    g.add(dwg.polygon(
        points=[top, right, bottom, left],
        fill=fill, stroke='black', stroke_width=1.5
    ))

    # Línea de realce diagonal sutil (da sensación de volumen)
    g.add(dwg.line(
        start=left, end=right,
        stroke=dark, stroke_width=0.6, opacity=0.5
    ))

    dwg.add(g)


# Alias semántico: 'decision' renderiza igual que 'diamond'.
draw_decision = draw_diamond
