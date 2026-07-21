"""
Alias semántico de 'diamond' (WISH-DRAW-001).

`type: "decision"` renderiza el mismo rombo que `type: "diamond"`,
pero comunica intención de decisión/branch en flujos.
"""
from AlmaGag.draw.icons.diamond import draw_diamond


def draw_decision(dwg, x, y, color, element_id):
    draw_diamond(dwg, x, y, color, element_id)
