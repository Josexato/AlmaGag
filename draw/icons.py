"""
AlmaGag.draw.icons

Este módulo centraliza la lógica para renderizar íconos SVG en el sistema GAG.
Permite dibujar diferentes tipos de elementos de red basados en su `type`,
delegando la representación gráfica a módulos individuales (uno por tipo).

Si el tipo no se encuentra o el dibujo falla, se renderiza un plátano con cinta
(ícono por defecto que indica ambigüedad o tipo no reconocido).

Autor: José + ALMA 🧠
Fecha: 2025-07-06
"""

import importlib

# Diccionario de colores CSS nombrados a valores hex
CSS_COLORS = {
    'lightgreen': '#90EE90', 'gold': '#FFD700', 'tomato': '#FF6347',
    'lightblue': '#ADD8E6', 'gray': '#808080', 'grey': '#808080',
    'red': '#FF0000', 'green': '#008000', 'blue': '#0000FF',
    'yellow': '#FFFF00', 'orange': '#FFA500', 'purple': '#800080',
    'pink': '#FFC0CB', 'cyan': '#00FFFF', 'white': '#FFFFFF',
    'black': '#000000', 'silver': '#C0C0C0', 'lime': '#00FF00',
}


def color_to_rgb(color):
    """Convierte un color CSS o hex a tupla RGB (0-255)."""
    if color.startswith('#'):
        hex_color = color.lstrip('#')
        if len(hex_color) == 3:
            hex_color = ''.join([c*2 for c in hex_color])
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    return color_to_rgb(CSS_COLORS.get(color.lower(), '#808080'))


def rgb_to_hex(r, g, b):
    """Convierte RGB a hex."""
    return f'#{r:02x}{g:02x}{b:02x}'


def adjust_lightness(color, factor):
    """Ajusta la luminosidad de un color. factor > 1 aclara, < 1 oscurece."""
    r, g, b = color_to_rgb(color)
    if factor > 1:
        # Aclarar: interpolar hacia blanco
        r = int(r + (255 - r) * (factor - 1))
        g = int(g + (255 - g) * (factor - 1))
        b = int(b + (255 - b) * (factor - 1))
    else:
        # Oscurecer: multiplicar
        r = int(r * factor)
        g = int(g * factor)
        b = int(b * factor)
    return rgb_to_hex(min(255, r), min(255, g), min(255, b))


def create_gradient(dwg, element_id, base_color):
    """
    Crea un gradiente lineal automático basado en el color base.

    Genera una variante clara (top) y oscura (bottom) del color.
    El gradiente se agrega a dwg.defs y retorna la referencia URL.

    Args:
        dwg: Objeto svgwrite.Drawing
        element_id: ID único del elemento para nombrar el gradiente
        base_color: Color base (nombre CSS o hex)

    Returns:
        str: Referencia URL al gradiente, ej: "url(#gradient-element1)"
    """
    gradient_id = f'gradient-{element_id}'

    # Generar colores claro y oscuro
    light_color = adjust_lightness(base_color, 1.3)  # 30% más claro
    dark_color = adjust_lightness(base_color, 0.7)   # 30% más oscuro

    # Crear gradiente lineal vertical (de arriba hacia abajo)
    gradient = dwg.linearGradient(id=gradient_id, x1="0%", y1="0%", x2="0%", y2="100%")
    gradient.add_stop_color(offset="0%", color=light_color)
    gradient.add_stop_color(offset="100%", color=dark_color)

    dwg.defs.add(gradient)

    return f'url(#{gradient_id})'


def draw_icon(dwg, element):
    """
    Dibuja un ícono en el canvas SVG a partir de los datos del elemento.

    Parámetros:
        dwg (svgwrite.Drawing): Objeto de dibujo SVG.
        element (dict): Elemento con las claves:
            - 'x' (int): coordenada X del ícono.
            - 'y' (int): coordenada Y del ícono.
            - 'type' (str): tipo del ícono ('server', 'cloud', etc).
            - 'label' (str, opcional): texto a mostrar debajo.
            - 'color' (str, opcional): color de relleno (por defecto: 'gray').

    Comportamiento:
        - Si el tipo es válido y el módulo correspondiente existe:
            → llama a draw_<type>(dwg, x, y, color).
        - Si el tipo no existe o hay error:
            → se dibuja el ícono por defecto (plátano con cinta).

    Ejemplo de uso:
        draw_icon(dwg, {
            "type": "server",
            "x": 100,
            "y": 150,
            "label": "Servidor 1",
            "color": "lightblue"
        })
    """
    x = element['x']
    y = element['y']
    label = element.get('label', '')
    elem_type = element.get('type', 'unknown')
    color = element.get('color', 'gray')

    element_id = element.get('id', f'{elem_type}_{x}_{y}')

    try:
        # Intentar importar el módulo de dibujo específico según tipo
        module = importlib.import_module(f'AlmaGag.draw.{elem_type}')
        draw_func = getattr(module, f'draw_{elem_type}')
        draw_func(dwg, x, y, color, element_id)
    except Exception as e:
        print(f"[WARN] No se pudo dibujar '{elem_type}', se usará ícono por defecto. Error: {e}")
        from AlmaGag.draw.bwt import draw_bwt
        draw_bwt(dwg, x, y)

    # Renderizar texto debajo del ícono (admite múltiples líneas)
    lines = label.split('\n')
    for i, line in enumerate(lines):
        dwg.add(dwg.text(
            line,
            insert=(x + 40, y + 70 + (i * 18)),  # Posición centrada
            text_anchor="middle",
            font_size="14px",
            fill="black"
        ))
