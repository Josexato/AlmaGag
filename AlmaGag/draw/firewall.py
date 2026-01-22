"""
Dibuja el ícono de tipo 'firewall' para GAG.
Basado en fw3.svg - patrón de hexágonos de firewall.
"""
from AlmaGag.config import ICON_WIDTH, ICON_HEIGHT
from AlmaGag.draw.icons import create_gradient

def draw_firewall(dwg, x, y, color, element_id):
    """
    Dibuja un ícono de tipo 'firewall' como un patrón de hexágonos.
    Basado en el diseño de fw3.svg con hexágonos en degradado de colores cálidos.
    """
    # Crear grupo para el ícono
    g = dwg.g(id=element_id)

    # Escala: el SVG original está en mm (210x297), necesitamos ajustarlo a ICON_WIDTH x ICON_HEIGHT
    # Usar viewBox para escalar automáticamente
    # Definir el área visible del patrón original (ajustado manualmente para centrarse en el contenido)
    viewbox_x, viewbox_y = -10, 0
    viewbox_w, viewbox_h = 50, 30

    # Grupo con transformación para escalar y posicionar los hexágonos
    # Escala para ajustar viewbox (50x30) al tamaño del ícono (80x50)
    scale_x = ICON_WIDTH / viewbox_w
    scale_y = ICON_HEIGHT / viewbox_h

    hex_group = dwg.g(transform=f"translate({x},{y}) scale({scale_x},{scale_y}) translate({-viewbox_x},{-viewbox_y})")

    # Definir los hexágonos del patrón de firewall
    # Hexágono base (path optimizado)
    hex_path = "m 211.5145,221.09759 -99.80744,57.62385 -99.807437,-57.62385 0,-115.2477 99.807437,-57.623854 99.80744,57.623854 z"

    # Matriz de hexágonos con diferentes opacidades y colores para efecto de llamas
    hexagons = [
        # Fila inferior (rojo oscuro)
        {"transform": "matrix(0.0751447,0.02631765,-0.04338481,0.0455835,8.97,11.04)", "fill": "#a90000", "opacity": "0.72"},
        {"transform": "matrix(0.0751447,0.02631765,-0.04338481,0.0455835,13.97,16.29)", "fill": "#ff7000", "opacity": "0.82"},
        {"transform": "matrix(0.0751447,0.02631765,-0.04338481,0.0455835,18.97,11.04)", "fill": "#ffa900", "opacity": "0.72"},
        {"transform": "matrix(0.0751447,0.02631765,-0.04338481,0.0455835,18.97,21.54)", "fill": "#d40000", "opacity": "0.85"},
        {"transform": "matrix(0.0751447,0.02631765,-0.04338481,0.0455835,23.97,26.80)", "fill": "#a90000", "opacity": "1.0"},
        {"transform": "matrix(0.0751447,0.02631765,-0.04338481,0.0455835,23.97,16.29)", "fill": "#ff7000", "opacity": "0.82"},
        {"transform": "matrix(0.0751447,0.02631765,-0.04338481,0.0455835,28.97,11.04)", "fill": "#ffa900", "opacity": "0.72"},
        {"transform": "matrix(0.0751447,0.02631765,-0.04338481,0.0455835,28.97,21.54)", "fill": "#d40000", "opacity": "0.85"},
        {"transform": "matrix(0.0751447,0.02631765,-0.04338481,0.0455835,33.97,16.29)", "fill": "#ff7000", "opacity": "0.82"},
        {"transform": "matrix(0.0751447,0.02631765,-0.04338481,0.0455835,38.97,11.04)", "fill": "#ffa900", "opacity": "0.72"},
        # Fila media (naranja/amarillo)
        {"transform": "matrix(0.0751447,0.02631765,-0.04338481,0.0455835,13.97,5.78)", "fill": "#ffd400", "opacity": "0.45"},
        {"transform": "matrix(0.0751447,0.02631765,-0.04338481,0.0455835,18.97,0.53)", "fill": "#ffe200", "opacity": "0.5"},
        {"transform": "matrix(0.0751447,0.02631765,-0.04338481,0.0455835,23.97,5.78)", "fill": "#ffd400", "opacity": "0.45"},
        {"transform": "matrix(0.0751447,0.02631765,-0.04338481,0.0455835,23.97,-4.73)", "fill": "#ffe200", "opacity": "0.6"},
        {"transform": "matrix(0.0751447,0.02631765,-0.04338481,0.0455835,28.97,0.53)", "fill": "#ffe200", "opacity": "0.5"},
        {"transform": "matrix(0.0751447,0.02631765,-0.04338481,0.0455835,33.97,5.78)", "fill": "#ffd400", "opacity": "0.45"},
    ]

    # Dibujar cada hexágono
    for hex_data in hexagons:
        hex_group.add(dwg.path(
            d=hex_path,
            transform=hex_data["transform"],
            fill=hex_data["fill"],
            opacity=hex_data["opacity"],
            stroke="#cbcbcb",
            stroke_width="0.48"
        ))

    g.add(hex_group)
    dwg.add(g)
