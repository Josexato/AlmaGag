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
from AlmaGag.config import ICON_WIDTH, ICON_HEIGHT

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
        text_y = y - 10 - ((num_lines - 1) * 18)
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
    max_line_len = max((len(line) for line in label.split('\n')), default=0)
    text_width = max_line_len * 8  # ~8px por caracter en Arial 14px
    text_height = num_lines * 18

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


def draw_icon(dwg, element, all_elements=None):
    """
    Dibuja un ícono en el canvas SVG a partir de los datos del elemento.

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

    Ejemplo de uso:
        draw_icon(dwg, {
            "type": "server",
            "x": 100,
            "y": 150,
            "label": "Servidor 1",
            "color": "lightblue",
            "label_position": "right"
        }, all_elements)
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

    # Renderizar texto con posicionamiento inteligente
    if label:
        lines = label.split('\n')

        # Obtener posición preferida del JSON o usar 'bottom'
        preferred_pos = element.get('label_position', 'bottom')

        # Calcular mejor posición (evitando colisiones si hay lista de elementos)
        if all_elements:
            text_x, text_y, anchor, _ = calculate_label_position(
                element, all_elements, preferred_pos
            )
        else:
            # Sin lista de elementos, usar posición preferida directamente
            text_x, text_y, anchor, _ = get_text_coords(
                element, preferred_pos, len(lines)
            )

        # Renderizar cada línea de texto
        for i, line in enumerate(lines):
            dwg.add(dwg.text(
                line,
                insert=(text_x, text_y + (i * 18)),
                text_anchor=anchor,
                font_size="14px",
                font_family="Arial, sans-serif",
                fill="black"
            ))
