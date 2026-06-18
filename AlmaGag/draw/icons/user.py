"""
Dibuja el ícono de tipo 'user' para GAG.
Pictograma de persona/usuario (cabeza + torso).
"""
from AlmaGag.config import ICON_WIDTH, ICON_HEIGHT
from AlmaGag.draw.icons import create_gradient, adjust_lightness


def draw_user(dwg, x, y, color, element_id):
    """
    Dibuja un ícono de tipo 'user' como una silueta de persona.
    """
    g = dwg.g(id=element_id)

    fill = create_gradient(dwg, element_id, color)
    dark = adjust_lightness(color, 0.6)

    cx = x + ICON_WIDTH / 2
    h = ICON_HEIGHT

    # Cabeza (círculo)
    head_r = h * 0.22
    head_cy = y + head_r + 2
    g.add(dwg.circle(
        center=(cx, head_cy), r=head_r,
        fill=fill, stroke='black', stroke_width=1.2
    ))

    # Torso (medio óvalo / arco)
    torso_top = head_cy + head_r + 3
    torso_w = ICON_WIDTH * 0.55
    torso_h = h - (torso_top - y)

    # Forma de torso con path: arco superior + lados rectos + base
    g.add(dwg.path(
        d=f"M {cx - torso_w / 2},{y + h} "
          f"L {cx - torso_w / 2},{torso_top + torso_h * 0.3} "
          f"Q {cx - torso_w / 2},{torso_top} {cx},{torso_top} "
          f"Q {cx + torso_w / 2},{torso_top} {cx + torso_w / 2},{torso_top + torso_h * 0.3} "
          f"L {cx + torso_w / 2},{y + h} Z",
        fill=fill, stroke='black', stroke_width=1.2
    ))

    dwg.add(g)
