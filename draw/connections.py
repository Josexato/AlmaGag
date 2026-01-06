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


def draw_connection(dwg, elements_by_id, connection, markers):
    """
    Dibuja una línea entre dos elementos, ajustando los puntos para evitar
    superposición con los íconos.

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
    from_elem = elements_by_id[connection['from']]
    to_elem = elements_by_id[connection['to']]

    # Centro de cada elemento
    x1 = from_elem['x'] + ICON_WIDTH // 2
    y1 = from_elem['y'] + ICON_HEIGHT // 2
    x2 = to_elem['x'] + ICON_WIDTH // 2
    y2 = to_elem['y'] + ICON_HEIGHT // 2

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

    # Configurar markers según direction
    direction = connection.get('direction', 'none')
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
    # 'none' o valor desconocido: sin markers

    # Línea de conexión
    dwg.add(dwg.line(**line_attrs))

    # Etiqueta opcional en el medio
    if 'label' in connection:
        mid_x = (new_x1 + new_x2) / 2
        mid_y = (new_y1 + new_y2) / 2
        dwg.add(dwg.text(
            connection['label'],
            insert=(mid_x, mid_y - 10),
            text_anchor="middle",
            font_size="12px",
            fill="gray"
        ))
