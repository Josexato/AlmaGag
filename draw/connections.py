"""
AlmaGag.draw.connections

Este módulo maneja el dibujo de conexiones entre elementos del diagrama.
Incluye lógica para calcular offsets visuales y evitar superposición con íconos.

Versión 2.1:
- Soporte para routing declarativo (straight, orthogonal, bezier, arc)
- Paths pre-computados por ConnectionRouterManager
- Corner radius para polylines
- Curvas Bézier y arcos

Autor: José + ALMA
Fecha: 2026-01-08
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

    v2.1: Soporta routing declarativo con computed_path.
    Si no hay computed_path, usa comportamiento legacy (waypoints manuales o línea recta).

    Parámetros:
        dwg (svgwrite.Drawing): Objeto SVG donde se dibuja.
        elements_by_id (dict): Mapa de id → elemento.
        connection (dict): Diccionario con:
            - 'from': id del elemento origen.
            - 'to': id del elemento destino.
            - 'computed_path' (opcional, v2.1): path pre-computado por routing system
            - 'waypoints' (opcional, legacy): lista de puntos intermedios
            - 'direction' (opcional): dirección de la flecha.
        markers (dict): Diccionario con markers SVG para flechas.

    Returns:
        tuple: (mid_x, mid_y) coordenadas del centro de la línea o None si elementos sin coords
    """
    from_elem = elements_by_id.get(connection['from'])
    to_elem = elements_by_id.get(connection['to'])

    # Validar que ambos elementos existen y tienen coordenadas
    if not from_elem or not to_elem:
        return None

    if from_elem.get('x') is None or from_elem.get('y') is None:
        return None
    if to_elem.get('x') is None or to_elem.get('y') is None:
        return None

    # v2.1: Check if connection has computed_path from routing system
    computed_path = connection.get('computed_path')
    if computed_path:
        return _draw_computed_path(dwg, from_elem, to_elem, connection, computed_path, markers)

    # Legacy behavior: waypoints or straight line
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


def _draw_computed_path(dwg, from_elem, to_elem, connection, computed_path, markers):
    """
    Dibuja una conexión usando un path pre-computado por el routing system (v2.1).

    Args:
        dwg: SVG drawing object
        from_elem: Elemento origen
        to_elem: Elemento destino
        connection: Conexión con 'direction'
        computed_path: Path dict con 'type' y 'points'
        markers: Markers SVG para flechas

    Returns:
        tuple: (mid_x, mid_y) centro de la conexión
    """
    path_type = computed_path.get('type', 'line')
    points = computed_path.get('points', [])
    direction = connection.get('direction', 'none')

    if not points or len(points) < 2:
        # Fallback: línea recta simple
        x1 = from_elem['x'] + ICON_WIDTH // 2
        y1 = from_elem['y'] + ICON_HEIGHT // 2
        x2 = to_elem['x'] + ICON_WIDTH // 2
        y2 = to_elem['y'] + ICON_HEIGHT // 2
        return (x1 + x2) / 2, (y1 + y2) / 2

    # Aplicar offsets visuales para evitar superposición con íconos
    adjusted_points = _apply_visual_offsets(points, from_elem, to_elem)

    if path_type == 'line':
        return _draw_straight_line(dwg, adjusted_points, direction, markers)
    elif path_type == 'polyline':
        corner_radius = computed_path.get('corner_radius', 0)
        return _draw_polyline(dwg, adjusted_points, direction, markers, corner_radius)
    elif path_type == 'bezier':
        control_points = computed_path.get('control_points', [])
        return _draw_bezier_curve(dwg, adjusted_points, control_points, direction, markers)
    elif path_type == 'arc':
        arc_center = computed_path.get('arc_center', (0, 0))
        radius = computed_path.get('radius', 50)
        return _draw_arc(dwg, adjusted_points, arc_center, radius, direction, markers)
    else:
        # Unknown type, fallback to straight line
        return _draw_straight_line(dwg, adjusted_points, direction, markers)


def _apply_visual_offsets(points, from_elem, to_elem):
    """
    Aplica offsets visuales a los puntos para evitar superposición con íconos.

    Args:
        points: Lista de tuplas (x, y)
        from_elem: Elemento origen
        to_elem: Elemento destino

    Returns:
        list: Puntos ajustados
    """
    if len(points) < 2:
        return points

    adjusted = list(points)

    # Ajustar primer punto (origen)
    x1, y1 = points[0]
    x2, y2 = points[1] if len(points) > 1 else points[0]

    dx = x2 - x1
    dy = y2 - y1
    length = math.hypot(dx, dy)

    if length > 0:
        offset_start = compute_visual_offset(from_elem)
        adjusted[0] = (
            x1 + offset_start * dx / length,
            y1 + offset_start * dy / length
        )

    # Ajustar último punto (destino)
    if len(points) > 1:
        xn_1, yn_1 = points[-2]
        xn, yn = points[-1]

        dx = xn - xn_1
        dy = yn - yn_1
        length = math.hypot(dx, dy)

        if length > 0:
            offset_end = compute_visual_offset(to_elem)
            adjusted[-1] = (
                xn - offset_end * dx / length,
                yn - offset_end * dy / length
            )

    return adjusted


def _draw_straight_line(dwg, points, direction, markers):
    """Dibuja una línea recta entre dos puntos."""
    if len(points) < 2:
        return (0, 0)

    x1, y1 = points[0]
    x2, y2 = points[-1]

    line_attrs = {
        'start': (x1, y1),
        'end': (x2, y2),
        'stroke': 'black',
        'stroke_width': 2
    }

    # Aplicar markers
    if direction == 'forward':
        line_attrs['marker_end'] = markers['forward']
    elif direction == 'backward':
        line_attrs['marker_start'] = markers['backward']
    elif direction == 'bidirectional':
        line_attrs['marker_start'] = markers['bidirectional'][0]
        line_attrs['marker_end'] = markers['bidirectional'][1]

    dwg.add(dwg.line(**line_attrs))

    # Retornar centro
    return (x1 + x2) / 2, (y1 + y2) / 2


def _draw_polyline(dwg, points, direction, markers, corner_radius=0):
    """Dibuja una polyline, opcionalmente con esquinas redondeadas."""
    if len(points) < 2:
        return (0, 0)

    if corner_radius > 0:
        # TODO: Implementar corner radius con path SVG
        # Por ahora, usar polyline sharp
        pass

    polyline_attrs = {
        'points': points,
        'stroke': 'black',
        'stroke_width': 2,
        'fill': 'none'
    }

    # Aplicar markers
    if direction == 'forward':
        polyline_attrs['marker_end'] = markers['forward']
    elif direction == 'backward':
        polyline_attrs['marker_start'] = markers['backward']
    elif direction == 'bidirectional':
        polyline_attrs['marker_start'] = markers['bidirectional'][0]
        polyline_attrs['marker_end'] = markers['bidirectional'][1]

    dwg.add(dwg.polyline(**polyline_attrs))

    # Calcular centro (promedio de puntos)
    total_x = sum(p[0] for p in points)
    total_y = sum(p[1] for p in points)
    return total_x / len(points), total_y / len(points)


def _draw_bezier_curve(dwg, points, control_points, direction, markers):
    """Dibuja una curva de Bézier cúbica."""
    if len(points) < 2:
        return (0, 0)

    x1, y1 = points[0]
    x2, y2 = points[-1]

    # Usar puntos de control si están disponibles
    if control_points and len(control_points) >= 2:
        cx1, cy1 = control_points[0]
        cx2, cy2 = control_points[1]
    else:
        # Fallback: generar puntos de control simples
        cx1, cy1 = x1 + (x2 - x1) / 3, y1 + (y2 - y1) / 3
        cx2, cy2 = x1 + 2 * (x2 - x1) / 3, y1 + 2 * (y2 - y1) / 3

    # Crear path SVG con curva Bézier cúbica
    path_d = f"M {x1},{y1} C {cx1},{cy1} {cx2},{cy2} {x2},{y2}"

    path_attrs = {
        'd': path_d,
        'stroke': 'black',
        'stroke_width': 2,
        'fill': 'none'
    }

    # Aplicar markers
    if direction == 'forward':
        path_attrs['marker_end'] = markers['forward']
    elif direction == 'backward':
        path_attrs['marker_start'] = markers['backward']
    elif direction == 'bidirectional':
        path_attrs['marker_start'] = markers['bidirectional'][0]
        path_attrs['marker_end'] = markers['bidirectional'][1]

    dwg.add(dwg.path(**path_attrs))

    # Retornar centro aproximado (punto medio de la curva)
    return (x1 + x2) / 2, (y1 + y2) / 2


def _draw_arc(dwg, points, arc_center, radius, direction, markers):
    """Dibuja un arco circular."""
    if len(points) < 2:
        return (0, 0)

    x1, y1 = points[0]
    x2, y2 = points[-1]
    cx, cy = arc_center

    # Crear path SVG con arco
    # A rx ry x-axis-rotation large-arc-flag sweep-flag x y
    # large-arc-flag: 0 si ángulo < 180°, 1 si >= 180°
    # sweep-flag: 1 para sentido horario, 0 para antihorario

    # Para simplificar, usar large-arc=0, sweep=1
    path_d = f"M {x1},{y1} A {radius},{radius} 0 0,1 {x2},{y2}"

    path_attrs = {
        'd': path_d,
        'stroke': 'black',
        'stroke_width': 2,
        'fill': 'none'
    }

    # Aplicar markers
    if direction == 'forward':
        path_attrs['marker_end'] = markers['forward']
    elif direction == 'backward':
        path_attrs['marker_start'] = markers['backward']
    elif direction == 'bidirectional':
        path_attrs['marker_start'] = markers['bidirectional'][0]
        path_attrs['marker_end'] = markers['bidirectional'][1]

    dwg.add(dwg.path(**path_attrs))

    # Retornar centro del arco
    return (cx, cy)


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
