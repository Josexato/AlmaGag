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
import logging

logger = logging.getLogger('AlmaGag')
from xml.etree import ElementTree as ET
from AlmaGag.config import (
    ICON_WIDTH, ICON_HEIGHT,
    LABEL_OFFSET_BOTTOM, LABEL_OFFSET_SIDE,
    TEXT_LINE_HEIGHT, TEXT_CHAR_WIDTH
)
from AlmaGag.utils import calculate_label_dimensions


# ============================================================================
# SOPORTE PARA ICONOS SVG EMBEBIDOS (.gag format)
# ============================================================================

class RawSVGElement:
    """Adapter para inyectar XML raw en svgwrite (implementa get_xml())."""
    elementname = 'g'

    def __init__(self, svg_string):
        self._xml = ET.fromstring(svg_string)

    def get_xml(self):
        return self._xml


def draw_embedded_icon(dwg, x, y, color, element_id, svg_string):
    """
    Renderiza un icono SVG embebido en la posicion (x, y).

    Parsea el SVG string, extrae viewBox para calcular escala uniforme
    a ICON_WIDTH x ICON_HEIGHT, y lo envuelve en <g transform="translate scale">.
    """
    wrapped = svg_string.strip()

    if wrapped.startswith('<svg'):
        tmp = ET.fromstring(wrapped)
        vb = tmp.get('viewBox', f'0 0 {ICON_WIDTH} {ICON_HEIGHT}')
        parts = vb.split()
        orig_w, orig_h = float(parts[2]), float(parts[3])
        scale_x = ICON_WIDTH / orig_w
        scale_y = ICON_HEIGHT / orig_h
        scale = min(scale_x, scale_y)
        transform = f'translate({x},{y}) scale({scale})'
        inner_xml = ''.join(ET.tostring(child, encoding='unicode') for child in tmp)
        g_str = f'<g id="{element_id}" transform="{transform}">{inner_xml}</g>'
    else:
        transform = f'translate({x},{y})'
        g_str = f'<g id="{element_id}" transform="{transform}">{wrapped}</g>'

    dwg.add(RawSVGElement(g_str))

# Diccionario de colores CSS nombrados a valores hex
CSS_COLORS = {
    'lightgreen': '#90EE90', 'gold': '#FFD700', 'tomato': '#FF6347',
    'lightblue': '#ADD8E6', 'gray': '#808080', 'grey': '#808080',
    'red': '#FF0000', 'green': '#008000', 'blue': '#0000FF',
    'yellow': '#FFFF00', 'orange': '#FFA500', 'purple': '#800080',
    'pink': '#FFC0CB', 'cyan': '#00FFFF', 'white': '#FFFFFF',
    'black': '#000000', 'silver': '#C0C0C0', 'lime': '#00FF00',
    'lavender': '#E6E6FA', 'lightyellow': '#FFFFE0',
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


# ============================================================================
# POSICIONAMIENTO INTELIGENTE DE TEXTO
# ============================================================================

def get_text_coords(element, position, num_lines=1):
    """
    Calcula las coordenadas del texto según la posición deseada.

    Args:
        element: Elemento con 'x', 'y'
        position: 'bottom', 'top', 'left', 'right'
        num_lines: Número de líneas de texto

    Returns:
        tuple: (x, y, text_anchor, position_name)
    """
    x, y = element['x'], element['y']
    center_x = x + ICON_WIDTH // 2   # Centro horizontal del ícono
    center_y = y + ICON_HEIGHT // 2  # Centro vertical del ícono

    if position == 'bottom':
        return (center_x, y + ICON_HEIGHT + 20, 'middle', 'bottom')
    elif position == 'top':
        # Ajustar hacia arriba según número de líneas
        text_y = y - 10 - ((num_lines - 1) * TEXT_LINE_HEIGHT)
        return (center_x, text_y, 'middle', 'top')
    elif position == 'right':
        return (x + ICON_WIDTH + 15, center_y, 'start', 'right')
    elif position == 'left':
        return (x - 15, center_y, 'end', 'left')
    else:
        # Default: bottom
        return (center_x, y + ICON_HEIGHT + 20, 'middle', 'bottom')


def get_text_bbox(element, position, num_lines=1):
    """
    Calcula el bounding box aproximado del texto en una posición.

    Returns:
        tuple: (x1, y1, x2, y2) del área ocupada por el texto
    """
    text_x, text_y, anchor, _ = get_text_coords(element, position, num_lines)

    # Estimación del ancho del texto (aproximado)
    label = element.get('label', '')
    text_width, text_height, _ = calculate_label_dimensions(label)

    # Calcular bbox según anchor
    if anchor == 'middle':
        x1 = text_x - text_width // 2
        x2 = text_x + text_width // 2
    elif anchor == 'start':
        x1 = text_x
        x2 = text_x + text_width
    else:  # 'end'
        x1 = text_x - text_width
        x2 = text_x

    # Y va de arriba hacia abajo
    if position == 'top':
        y1 = text_y - 14  # Ajuste por baseline
        y2 = text_y + text_height - 14
    elif position in ('left', 'right'):
        y1 = text_y - (text_height // 2)
        y2 = text_y + (text_height // 2)
    else:  # bottom
        y1 = text_y - 14
        y2 = text_y + text_height - 14

    return (x1, y1, x2, y2)


def rectangles_intersect(rect1, rect2):
    """
    Verifica si dos rectángulos se intersectan.

    Args:
        rect1, rect2: tuplas (x1, y1, x2, y2)

    Returns:
        bool: True si se intersectan
    """
    x1_1, y1_1, x2_1, y2_1 = rect1
    x1_2, y1_2, x2_2, y2_2 = rect2

    # No hay intersección si uno está completamente a un lado del otro
    if x2_1 < x1_2 or x2_2 < x1_1:
        return False
    if y2_1 < y1_2 or y2_2 < y1_1:
        return False

    return True


def has_collision(text_bbox, current_elem, all_elements):
    """
    Verifica si el texto colisiona con otros elementos (íconos).

    Args:
        text_bbox: (x1, y1, x2, y2) del texto
        current_elem: Elemento actual
        all_elements: Lista de todos los elementos

    Returns:
        bool: True si hay colisión
    """
    current_id = current_elem.get('id', '')

    for elem in all_elements:
        if elem.get('id', '') == current_id:
            continue

        # Bounding box del ícono
        icon_bbox = (
            elem['x'],
            elem['y'],
            elem['x'] + ICON_WIDTH,
            elem['y'] + ICON_HEIGHT
        )

        if rectangles_intersect(text_bbox, icon_bbox):
            return True

    return False


def calculate_label_position(element, all_elements, preferred='bottom'):
    """
    Calcula la mejor posición para el texto evitando colisiones.

    Args:
        element: Elemento actual
        all_elements: Lista de todos los elementos
        preferred: Posición preferida ('bottom', 'top', 'left', 'right')

    Returns:
        tuple: (x, y, text_anchor, position_name)
    """
    label = element.get('label', '')
    num_lines = len(label.split('\n')) if label else 1

    # Orden de prioridad para probar posiciones
    positions_order = ['bottom', 'right', 'top', 'left']

    # Mover la preferida al inicio
    if preferred in positions_order:
        positions_order.remove(preferred)
        positions_order.insert(0, preferred)

    # Probar cada posición
    for pos in positions_order:
        text_bbox = get_text_bbox(element, pos, num_lines)
        if not has_collision(text_bbox, element, all_elements):
            return get_text_coords(element, pos, num_lines)

    # Si todas colisionan, usar la preferida
    return get_text_coords(element, preferred, num_lines)


def draw_icon_shape(dwg, element, embedded_icons=None):
    """
    Dibuja solo la forma del ícono, sin etiqueta.

    Parámetros:
        dwg (svgwrite.Drawing): Objeto de dibujo SVG.
        element (dict): Elemento con 'x', 'y', 'type', 'color'.
        embedded_icons (dict, opcional): Iconos SVG embebidos {type: svg_string}.

    Comportamiento:
        - Si el tipo coincide con un icono embebido → renderiza SVG inline.
        - Si el tipo es un módulo Python válido → llama a draw_<type>().
        - Si nada funciona → dibuja ícono por defecto (plátano con cinta).
    """
    x = element.get('x')
    y = element.get('y')

    if x is None or y is None:
        elem_id = element.get('id', 'unknown')
        logger.warning(f"Element {elem_id} sin coordenadas, omitiendo")
        return

    elem_type = element.get('type', 'unknown')
    color = element.get('color', 'gray')
    element_id = element.get('id', f'{elem_type}_{x}_{y}')

    # Prioridad 1: icono SVG embebido (.gag format)
    if embedded_icons and elem_type in embedded_icons:
        draw_embedded_icon(dwg, x, y, color, element_id, embedded_icons[elem_type])
        return

    # Prioridad 2: módulo Python (draw/{type}.py)
    try:
        module = importlib.import_module(f'AlmaGag.draw.{elem_type}')
        draw_func = getattr(module, f'draw_{elem_type}')
        draw_func(dwg, x, y, color, element_id)
    except (ImportError, AttributeError) as e:
        logger.warning(f"No se pudo dibujar '{elem_type}', se usará ícono por defecto. Error: {e}")
        from AlmaGag.draw.bwt import draw_bwt
        draw_bwt(dwg, x, y)


def draw_icon_label(dwg, element, position_info):
    """
    Dibuja solo la etiqueta de un ícono en la posición indicada.

    Parámetros:
        dwg (svgwrite.Drawing): Objeto de dibujo SVG.
        element (dict): Elemento con 'label'.
        position_info (tuple): (x, y, anchor, position_name) calculado por AutoLayout.
    """
    label = element.get('label', '')
    if not label or not position_info:
        return

    text_x, text_y, anchor, _ = position_info
    lines = label.split('\n')

    for i, line in enumerate(lines):
        dwg.add(dwg.text(
            line,
            insert=(text_x, text_y + (i * TEXT_LINE_HEIGHT)),
            text_anchor=anchor,
            font_size="14px",
            font_family="Arial, sans-serif",
            fill="black",
            filter='url(#text-glow)'
        ))


def draw_icon(dwg, element, all_elements=None):
    """
    Dibuja un ícono completo (forma + etiqueta) en el canvas SVG.

    NOTA: Esta función se mantiene por compatibilidad. Para el nuevo flujo
    con AutoLayout, usar draw_icon_shape() y draw_icon_label() por separado.

    Parámetros:
        dwg (svgwrite.Drawing): Objeto de dibujo SVG.
        element (dict): Elemento con las claves:
            - 'x' (int): coordenada X del ícono.
            - 'y' (int): coordenada Y del ícono.
            - 'type' (str): tipo del ícono ('server', 'cloud', etc).
            - 'label' (str, opcional): texto a mostrar.
            - 'color' (str, opcional): color de relleno (por defecto: 'gray').
            - 'label_position' (str, opcional): posición del texto
              ('bottom', 'top', 'left', 'right'). Por defecto: auto-detectar.

    Comportamiento:
        - Si el tipo es válido y el módulo correspondiente existe:
            → llama a draw_<type>(dwg, x, y, color).
        - Si el tipo no existe o hay error:
            → se dibuja el ícono por defecto (plátano con cinta).
        - El texto se posiciona inteligentemente evitando colisiones.
    """
    # Dibujar forma del ícono
    draw_icon_shape(dwg, element)

    # Renderizar texto con posicionamiento inteligente
    label = element.get('label', '')
    if label:
        lines = label.split('\n')
        preferred_pos = element.get('label_position', 'bottom')

        if all_elements:
            position_info = calculate_label_position(element, all_elements, preferred_pos)
        else:
            position_info = get_text_coords(element, preferred_pos, len(lines))

        draw_icon_label(dwg, element, position_info)
