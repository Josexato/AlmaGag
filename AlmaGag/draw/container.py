"""
AlmaGag.draw.container

Este módulo maneja el dibujo de elementos contenedores (containers) que pueden
agrupar otros elementos dentro de ellos.

Los contenedores se representan como rectángulos con bordes redondeados que
contienen otros elementos, permitiendo agrupar conceptos visuales.

Autor: José + ALMA
Fecha: 2026-01-07
"""

from AlmaGag.config import ICON_WIDTH, ICON_HEIGHT
from AlmaGag.draw.icons import create_gradient
import importlib


def calculate_container_bounds(container, elements_by_id):
    """
    Calcula automáticamente el bounding box de un contenedor basado en
    los elementos que contiene.

    Parámetros:
        container (dict): Elemento contenedor con campo 'contains'.
        elements_by_id (dict): Mapa de id → elemento.

    Retorna:
        dict: {'x': x_min, 'y': y_min, 'width': width, 'height': height}
    """
    contains = container.get('contains', [])
    if not contains:
        # Sin elementos contenidos, usar tamaño por defecto
        return {
            'x': container.get('x', 0),
            'y': container.get('y', 0),
            'width': 200,
            'height': 150
        }

    # Obtener padding (espacio interno)
    padding = container.get('padding', 40)

    # Encontrar bounds de todos los elementos contenidos
    min_x = float('inf')
    min_y = float('inf')
    max_x = float('-inf')
    max_y = float('-inf')

    for item in contains:
        # Soportar formato dict {"id": "...", "scope": "..."} o string directo
        elem_id = item['id'] if isinstance(item, dict) else item

        if elem_id not in elements_by_id:
            continue

        elem = elements_by_id[elem_id]
        elem_x = elem.get('x', 0)
        elem_y = elem.get('y', 0)
        elem_w = elem.get('width', ICON_WIDTH)
        elem_h = elem.get('height', ICON_HEIGHT)

        min_x = min(min_x, elem_x)
        min_y = min(min_y, elem_y)
        max_x = max(max_x, elem_x + elem_w)
        max_y = max(max_y, elem_y + elem_h)

    # Aplicar padding
    min_x -= padding
    min_y -= padding
    max_x += padding
    max_y += padding

    width = max_x - min_x
    height = max_y - min_y

    # Aplicar aspect_ratio si se especifica
    aspect_ratio = container.get('aspect_ratio')
    if aspect_ratio:
        current_ratio = width / height if height > 0 else 1
        if current_ratio < aspect_ratio:
            # Ensanchar
            new_width = height * aspect_ratio
            min_x -= (new_width - width) / 2
            width = new_width
        elif current_ratio > aspect_ratio:
            # Alargar
            new_height = width / aspect_ratio
            min_y -= (new_height - height) / 2
            height = new_height

    return {
        'x': min_x,
        'y': min_y,
        'width': width,
        'height': height
    }


def draw_container(dwg, container, elements_by_id, draw_label=True):
    """
    Dibuja un elemento contenedor como un rectángulo con bordes redondeados
    y un ícono en la esquina superior izquierda.

    Parámetros:
        dwg (svgwrite.Drawing): Objeto SVG donde se dibuja.
        container (dict): Elemento contenedor con:
            - 'contains': lista de elementos contenidos
            - 'x', 'y', 'width', 'height': dimensiones pre-calculadas (v2.2+)
            - 'type' (opcional): tipo de ícono para esquina superior izquierda
            - 'label' (opcional): etiqueta del contenedor
            - 'color' (opcional): color del contenedor
            - 'aspect_ratio' (opcional): proporción width/height
            - 'padding' (opcional): espacio interno (default: 40)
        elements_by_id (dict): Mapa de id → elemento.
        draw_label (bool): Si es False, no dibuja la etiqueta del contenedor.
                          Útil cuando la etiqueta se maneja externamente (default: True).
    """
    # IMPORTANTE (v2.2+): Usar dimensiones pre-calculadas si existen.
    # container_calculator ya calculó las dimensiones considerando
    # TANTO íconos como etiquetas de elementos contenidos.
    # Solo recalcular si no existen (fallback para compatibilidad).
    if '_is_container_calculated' in container and all(k in container for k in ['x', 'y', 'width', 'height']):
        # Usar dimensiones ya calculadas (incluyen etiquetas)
        x = container['x']
        y = container['y']
        width = container['width']
        height = container['height']
    else:
        # Fallback: calcular bounds (solo para retrocompatibilidad)
        bounds = calculate_container_bounds(container, elements_by_id)
        x = bounds['x']
        y = bounds['y']
        width = bounds['width']
        height = bounds['height']

    # Calcular radio de bordes redondeados (5% del lado más corto)
    radius = min(width, height) * 0.05

    # Obtener color
    color = container.get('color', 'lightgray')

    # Crear gradiente para el contenedor
    gradient_id = create_gradient(dwg, container['id'], color)

    # Dibujar rectángulo con bordes redondeados
    rect = dwg.rect(
        insert=(x, y),
        size=(width, height),
        rx=radius,
        ry=radius,
        fill=gradient_id,  # create_gradient ya retorna url(#...)
        stroke='black',
        stroke_width=2,
        opacity=0.3  # Transparente para ver elementos dentro
    )
    dwg.add(rect)

    # Dibujar ícono en esquina superior izquierda
    icon_type = container.get('type', 'building')
    icon_size = min(ICON_WIDTH, ICON_HEIGHT) * 0.6  # Ícono más pequeño
    icon_x = x + 10
    icon_y = y + 10

    # Intentar cargar módulo del ícono
    try:
        icon_module = importlib.import_module(f'AlmaGag.draw.{icon_type}')
        # Obtener función específica draw_<type>
        draw_func = getattr(icon_module, f'draw_{icon_type}')
        # Dibujar ícono (el módulo crea su propio gradiente)
        icon_elem_id = f"{container['id']}_icon"
        draw_func(dwg, icon_x, icon_y, color, icon_elem_id)
    except (ImportError, AttributeError) as e:
        # Fallback: dibujar rectángulo simple
        dwg.add(dwg.rect(
            insert=(icon_x, icon_y),
            size=(icon_size, icon_size),
            fill=gradient_id,  # create_gradient ya retorna url(#...)
            stroke='black',
            opacity=1.0
        ))

    # Dibujar etiqueta del contenedor (si existe y draw_label=True)
    if draw_label:
        label = container.get('label', '')
        if label:
            # Posicionar etiqueta arriba del contenedor
            label_x = x + width / 2
            label_y = y - 10

            lines = label.split('\n')
            for i, line in enumerate(lines):
                dwg.add(dwg.text(
                    line,
                    insert=(label_x, label_y - (len(lines) - 1 - i) * 18),
                    text_anchor="middle",
                    font_size="16px",
                    font_family="Arial, sans-serif",
                    font_weight="bold",
                    fill="black"
                ))
