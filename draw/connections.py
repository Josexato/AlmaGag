"""
AlmaGag.draw.connections

Este módulo maneja el dibujo de conexiones entre elementos del diagrama.
Incluye lógica para calcular offsets visuales y evitar superposición con íconos.

Autor: José + ALMA
Fecha: 2025-07-06
"""

import math
from AlmaGag.config import ICON_WIDTH, ICON_HEIGHT


def compute_visual_offset(elem):
    """
    Determina qué tan lejos del centro debe comenzar o terminar una línea
    de conexión para evitar superposición con la representación visual del elemento.

    Parámetros:
        elem (dict): Elemento con 'type' opcional.

    Retorna:
        float: Distancia de offset desde el centro del ícono.
    """
    elem_type = elem.get('type', 'unknown')
    if elem_type == 'cloud':
        return max(ICON_WIDTH, ICON_HEIGHT) / 2  # Para elipses (nubes)
    return max(ICON_WIDTH, ICON_HEIGHT) / 2.5  # Para rectángulos u otros


def draw_connection_line(dwg, elements_by_id, connection, markers):
    """
    Dibuja solo la línea de conexión, sin etiqueta.
    Soporta waypoints para routing complejo.

    Parámetros:
        dwg (svgwrite.Drawing): Objeto SVG donde se dibuja.
        elements_by_id (dict): Mapa de id → elemento.
        connection (dict): Diccionario con:
            - 'from': id del elemento origen.
            - 'to': id del elemento destino.
            - 'waypoints' (opcional): lista de puntos intermedios [{"x": 100, "y": 200}, ...]
            - 'direction' (opcional): dirección de la flecha.
        markers (dict): Diccionario con markers SVG para flechas.

    Returns:
        tuple: (mid_x, mid_y) coordenadas del centro de la línea
    """
    from_elem = elements_by_id[connection['from']]
    to_elem = elements_by_id[connection['to']]

    # Centro de cada elemento
    x1 = from_elem['x'] + ICON_WIDTH // 2
    y1 = from_elem['y'] + ICON_HEIGHT // 2
    x2 = to_elem['x'] + ICON_WIDTH // 2
    y2 = to_elem['y'] + ICON_HEIGHT // 2

    # Obtener waypoints si existen
    waypoints = connection.get('waypoints', [])

    # Configurar markers según direction
    direction = connection.get('direction', 'none')

    if not waypoints:
        # === Comportamiento original: línea recta ===
        # Calcular vector direccional y longitud
        dx = x2 - x1
        dy = y2 - y1
        length = math.hypot(dx, dy)
        if length == 0:
            length = 1

        # Aplicar offset visual para evitar superposición con íconos
        offset_start = compute_visual_offset(from_elem)
        offset_end = compute_visual_offset(to_elem)

        new_x1 = x1 + offset_start * dx / length
        new_y1 = y1 + offset_start * dy / length
        new_x2 = x2 - offset_end * dx / length
        new_y2 = y2 - offset_end * dy / length

        line_attrs = {
            'start': (new_x1, new_y1),
            'end': (new_x2, new_y2),
            'stroke': 'black',
            'stroke_width': 2
        }

        if direction == 'forward':
            line_attrs['marker_end'] = markers['forward']
        elif direction == 'backward':
            line_attrs['marker_start'] = markers['backward']
        elif direction == 'bidirectional':
            line_attrs['marker_start'] = markers['bidirectional'][0]
            line_attrs['marker_end'] = markers['bidirectional'][1]

        dwg.add(dwg.line(**line_attrs))

        # Retornar centro de la línea
        mid_x = (new_x1 + new_x2) / 2
        mid_y = (new_y1 + new_y2) / 2
        return (mid_x, mid_y)

    else:
        # === Nuevo comportamiento: polyline con waypoints ===

        # Primer waypoint
        first_wp_x = waypoints[0]['x']
        first_wp_y = waypoints[0]['y']

        # Último waypoint
        last_wp_x = waypoints[-1]['x']
        last_wp_y = waypoints[-1]['y']

        # Calcular offset para el primer segmento (from_elem → primer waypoint)
        dx_start = first_wp_x - x1
        dy_start = first_wp_y - y1
        length_start = math.hypot(dx_start, dy_start)
        if length_start == 0:
            length_start = 1

        offset_start = compute_visual_offset(from_elem)
        start_x = x1 + offset_start * dx_start / length_start
        start_y = y1 + offset_start * dy_start / length_start

        # Calcular offset para el último segmento (último waypoint → to_elem)
        dx_end = x2 - last_wp_x
        dy_end = y2 - last_wp_y
        length_end = math.hypot(dx_end, dy_end)
        if length_end == 0:
            length_end = 1

        offset_end = compute_visual_offset(to_elem)
        end_x = x2 - offset_end * dx_end / length_end
        end_y = y2 - offset_end * dy_end / length_end

        # Construir lista de puntos para la polyline
        points = [(start_x, start_y)]
        for wp in waypoints:
            points.append((wp['x'], wp['y']))
        points.append((end_x, end_y))

        # Crear polyline
        polyline_attrs = {
            'points': points,
            'stroke': 'black',
            'stroke_width': 2,
            'fill': 'none'
        }

        # Aplicar markers solo en los extremos
        if direction == 'forward':
            polyline_attrs['marker_end'] = markers['forward']
        elif direction == 'backward':
            polyline_attrs['marker_start'] = markers['backward']
        elif direction == 'bidirectional':
            polyline_attrs['marker_start'] = markers['bidirectional'][0]
            polyline_attrs['marker_end'] = markers['bidirectional'][1]

        dwg.add(dwg.polyline(**polyline_attrs))

        # Calcular centro aproximado (punto medio de todos los segmentos)
        total_x = sum(p[0] for p in points)
        total_y = sum(p[1] for p in points)
        mid_x = total_x / len(points)
        mid_y = total_y / len(points)

        return (mid_x, mid_y)


def draw_connection_label(dwg, connection, position):
    """
    Dibuja solo la etiqueta de una conexión.

    Parámetros:
        dwg (svgwrite.Drawing): Objeto SVG donde se dibuja.
        connection (dict): Diccionario con 'label'.
        position (tuple): (x, y) coordenadas del centro de la conexión.
    """
    label = connection.get('label', '')
    if not label:
        return

    mid_x, mid_y = position
    dwg.add(dwg.text(
        label,
        insert=(mid_x, mid_y - 10),
        text_anchor="middle",
        font_size="12px",
        font_family="Arial, sans-serif",
        fill="gray"
    ))


def draw_connection(dwg, elements_by_id, connection, markers):
    """
    Dibuja una línea completa (línea + etiqueta) entre dos elementos.

    NOTA: Esta función se mantiene por compatibilidad. Para el nuevo flujo
    con AutoLayout, usar draw_connection_line() y draw_connection_label() por separado.

    Parámetros:
        dwg (svgwrite.Drawing): Objeto SVG donde se dibuja.
        elements_by_id (dict): Mapa de id → elemento.
        connection (dict): Diccionario con:
            - 'from': id del elemento origen.
            - 'to': id del elemento destino.
            - 'label' (opcional): texto a mostrar en la línea.
            - 'direction' (opcional): dirección de la flecha.
              Valores: 'forward', 'backward', 'bidirectional', 'none'
        markers (dict): Diccionario con markers SVG para flechas.

    Ejemplo:
        {
            "from": "router1",
            "to": "switch2",
            "label": "enlace 1Gbps",
            "direction": "forward"
        }
    """
    # Dibujar línea
    center = draw_connection_line(dwg, elements_by_id, connection, markers)

    # Dibujar etiqueta
    draw_connection_label(dwg, connection, center)
