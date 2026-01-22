"""
Dibuja el ícono de tipo 'building' para GAG.
Basado en building.svg - cubo 3D isométrico.
"""
from AlmaGag.config import ICON_WIDTH, ICON_HEIGHT
from AlmaGag.draw.icons import create_gradient

def draw_building(dwg, x, y, color, element_id):
    """
    Dibuja un ícono de tipo 'building' como un cubo 3D isométrico.
    Basado en el diseño de building.svg con perspectiva 3D.
    Incluye padding interno del 20% de la altura.
    """
    # Padding del 20% de la altura del ícono (mantener compatibilidad)
    padding = ICON_HEIGHT * 0.2  # 50 * 0.2 = 10px

    # Ajustar posición y tamaño con padding
    icon_x = x + padding
    icon_y = y + padding
    icon_width = ICON_WIDTH - (2 * padding)  # 80 - 20 = 60px
    icon_height = ICON_HEIGHT - (2 * padding)  # 50 - 20 = 30px

    # Crear grupo para el ícono
    g = dwg.g(id=element_id)

    # Área del SVG original que contiene el cubo
    viewbox_x, viewbox_y = 0.9, 1.4
    viewbox_w, viewbox_h = 49.8, 43.3

    # Escala para ajustar al tamaño del ícono con padding
    scale_x = icon_width / viewbox_w
    scale_y = icon_height / viewbox_h

    # Grupo con transformación para escalar y posicionar el cubo
    cube_group = dwg.g(transform=f"translate({icon_x},{icon_y}) scale({scale_x},{scale_y}) translate({-viewbox_x},{-viewbox_y})")

    # Crear gradiente basado en el color proporcionado
    # Los tonos se derivan del color base
    fill = create_gradient(dwg, element_id, color)

    # Las 6 caras del cubo 3D isométrico (del SVG original)
    # Cada cara tiene un path y un fill que varía en luminosidad para dar efecto 3D

    # Cara izquierda (más clara)
    cube_group.add(dwg.path(
        d="M 22.754087,32.116749 0.94545599,43.000013 V 4.7289739 L 22.754087,1.5702876 Z",
        fill="#e9e9ff",
        stroke="none"
    ))

    # Cara derecha (oscura)
    cube_group.add(dwg.path(
        d="M 50.712576,33.120864 V 1.4628125 L 22.754087,1.5702876 V 32.116749 Z",
        fill="#353564",
        stroke="none"
    ))

    # Cara inferior (medio-oscura)
    cube_group.add(dwg.path(
        d="M 50.712576,33.120864 35.295871,44.770537 0.94545599,43.000013 22.754087,32.116749 Z",
        fill="#4d4d9f",
        stroke="none"
    ))

    # Cara superior (azul brillante)
    cube_group.add(dwg.path(
        d="M 50.712576,1.4628125 35.295871,4.7384198 0.94545599,4.7289739 22.754087,1.5702876 Z",
        fill="#1c1ce6",
        opacity="1",
        stroke="none"
    ))

    # Cara frontal (azul medio)
    cube_group.add(dwg.path(
        d="M 35.295871,44.770537 V 4.7384198 L 0.94545599,4.7289739 V 43.000013 Z",
        fill="#1a52ff",
        opacity="0.96",
        stroke="none"
    ))

    # Cara lateral derecha visible (azul claro)
    cube_group.add(dwg.path(
        d="M 50.712576,33.120864 35.295871,44.770537 V 4.7384198 L 50.712576,1.4628125 Z",
        fill="#1c9bd0",
        stroke="none"
    ))

    # Añadir el borde general del cubo
    cube_group.add(dwg.rect(
        insert=(viewbox_x, viewbox_y),
        size=(viewbox_w, viewbox_h),
        fill="none",
        stroke="#cbcbcb",
        stroke_width="0.48",
        opacity="0.67"
    ))

    g.add(cube_group)
    dwg.add(g)
