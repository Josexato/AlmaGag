"""
Dibuja el ícono de tipo 'document' para GAG.
Pictograma de documento/archivo con esquina doblada.
"""
from AlmaGag.config import ICON_WIDTH, ICON_HEIGHT
from AlmaGag.draw.icons import create_gradient, adjust_lightness


def draw_document(dwg, x, y, color, element_id):
    """
    Dibuja un ícono de tipo 'document' como una hoja con esquina doblada.
    """
    g = dwg.g(id=element_id)

    fill = create_gradient(dwg, element_id, color)
    dark = adjust_lightness(color, 0.6)

    w = ICON_WIDTH
    h = ICON_HEIGHT
    fold = 12  # tamaño del doblez de esquina
    mx = 10    # margen horizontal

    # Cuerpo del documento (con esquina recortada)
    points = [
        (x + mx, y),
        (x + w - mx - fold, y),
        (x + w - mx, y + fold),
        (x + w - mx, y + h),
        (x + mx, y + h)
    ]
    g.add(dwg.polygon(
        points=points,
        fill=fill, stroke='black', stroke_width=1.2
    ))

    # Triángulo de la esquina doblada
    fold_points = [
        (x + w - mx - fold, y),
        (x + w - mx, y + fold),
        (x + w - mx - fold, y + fold)
    ]
    g.add(dwg.polygon(
        points=fold_points,
        fill=dark, stroke='black', stroke_width=0.8
    ))

    # Líneas de texto (4 líneas simuladas)
    line_start = x + mx + 6
    line_end_full = x + w - mx - 8
    for i in range(4):
        ly = y + 14 + i * 8
        end = line_end_full - (fold + 4 if i == 0 else 0)
        # Variar largo para parecer texto real
        if i == 3:
            end = line_start + (end - line_start) * 0.6
        g.add(dwg.line(
            start=(line_start, ly), end=(end, ly),
            stroke=dark, stroke_width=1.5, stroke_linecap='round'
        ))

    dwg.add(g)
