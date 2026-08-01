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
from AlmaGag.config import ICON_WIDTH, ICON_HEIGHT, CORNER_RADIUS_DEFAULT, FONT_SIZE_CONNECTION


def compute_visual_offset(elem):
    """
    Determina qué tan lejos del centro debe comenzar o terminar una línea
    de conexión para evitar superposición con la representación visual del elemento.

    Usa las dimensiones reales del elemento (width/height) en vez de
    constantes fijas, para funcionar con cualquier ícono o tamaño.

    Parámetros:
        elem (dict): Elemento con dimensiones y tipo.

    Retorna:
        float: Distancia de offset desde el centro del ícono.
    """
    # Containers: routing already calculated the exact border point
    if elem.get('contains'):
        return 0

    w = elem.get('width', ICON_WIDTH)
    h = elem.get('height', ICON_HEIGHT)
    return max(w, h) / 2


def _apply_direction_markers(attrs, direction, markers):
    """
    Aplica markers según la dirección de la conexión.

    - forward: círculo en origen, flecha en destino
    - backward: flecha en origen, círculo en destino
    - bidirectional: flechas en ambos extremos
    """
    if direction == 'forward':
        attrs['marker_start'] = markers.get('circle_start', '')
        attrs['marker_end'] = markers.get('arrow_end', markers.get('forward', ''))
    elif direction == 'backward':
        attrs['marker_start'] = markers.get('arrow_start', markers.get('backward', ''))
        attrs['marker_end'] = markers.get('circle_end', '')
    elif direction == 'bidirectional':
        bidi = markers.get('bidirectional')
        if bidi:
            attrs['marker_start'] = bidi[0]
            attrs['marker_end'] = bidi[1]
        else:
            attrs['marker_start'] = markers.get('arrow_start', '')
            attrs['marker_end'] = markers.get('arrow_end', '')


def _dash_for(connection):
    """Patrón de guiones según `connection['style']` ('dashed' | 'dotted').
    Devuelve None para línea sólida (default). Útil para enlaces de respaldo /
    secundarios en topologías de red."""
    style = connection.get('style') or connection.get('line_style')
    if style == 'dashed':
        return '7,5'
    if style == 'dotted':
        return '2,4'
    # §E/§L40: arista de retorno de un ciclo → arco punteado (a menos que el
    # usuario haya fijado un estilo explícito, ya cubierto arriba).
    if connection.get('_cycle_return') or connection.get('_cycle_arc'):
        return '6,4'
    return None


def draw_connection_line(dwg, elements_by_id, connection, markers, stroke_color='black'):
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
        stroke_color (str): Color de trazo para la línea (default: 'black').

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
    dash = _dash_for(connection)

    computed_path = connection.get('computed_path')
    if computed_path:
        return _draw_computed_path(dwg, from_elem, to_elem, connection, computed_path, markers, stroke_color, dash)

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
            'stroke': stroke_color,
            'stroke_width': 2
        }
        if dash:
            line_attrs['stroke_dasharray'] = dash

        _apply_direction_markers(line_attrs, direction, markers)

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
            'stroke': stroke_color,
            'stroke_width': 2,
            'fill': 'none'
        }
        if dash:
            polyline_attrs['stroke_dasharray'] = dash

        # Aplicar markers solo en los extremos
        _apply_direction_markers(polyline_attrs, direction, markers)

        dwg.add(dwg.polyline(**polyline_attrs))

        # Calcular centro aproximado (punto medio de todos los segmentos)
        total_x = sum(p[0] for p in points)
        total_y = sum(p[1] for p in points)
        mid_x = total_x / len(points)
        mid_y = total_y / len(points)

        return (mid_x, mid_y)


def _draw_computed_path(dwg, from_elem, to_elem, connection, computed_path, markers, stroke_color='black', dash=None):
    """
    Dibuja una conexión usando un path pre-computado por el routing system (v2.1).

    Args:
        dwg: SVG drawing object
        from_elem: Elemento origen
        to_elem: Elemento destino
        connection: Conexión con 'direction'
        computed_path: Path dict con 'type' y 'points'
        markers: Markers SVG para flechas
        stroke_color: Color de trazo (default: 'black')

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

    # K34 — regla de oro: todo conector empieza y termina EXACTO sobre el borde
    # del ícono. Si el extremo (puerto asignado o centro) ya está en el borde, se
    # respeta (puertos buenos de hier/arcos); si no (centro, o puerto mal ubicado
    # por coords explícitas), se recorta al borde. Único camino de emisión.
    is_self_loop = from_elem['id'] == to_elem['id']
    if is_self_loop or len(points) < 2:
        adjusted_points = points
    else:
        adjusted_points = list(points)
        if not from_elem.get('contains') and not _on_border(from_elem, adjusted_points[0]):
            c = clip_to_border(from_elem, adjusted_points[1])
            if c is not None:
                adjusted_points[0] = c
        if not to_elem.get('contains') and not _on_border(to_elem, adjusted_points[-1]):
            c = clip_to_border(to_elem, adjusted_points[-2])
            if c is not None:
                adjusted_points[-1] = c

    if path_type == 'line':
        return _draw_straight_line(dwg, adjusted_points, direction, markers, stroke_color, dash)
    elif path_type == 'polyline':
        corner_radius = computed_path.get('corner_radius', 0)
        return _draw_polyline(dwg, adjusted_points, direction, markers, corner_radius, stroke_color, dash)
    elif path_type == 'bezier':
        control_points = computed_path.get('control_points', [])
        return _draw_bezier_curve(dwg, adjusted_points, control_points, direction, markers, stroke_color, dash)
    elif path_type == 'arc':
        arc_center = computed_path.get('arc_center', (0, 0))
        radius = computed_path.get('radius', 50)
        return _draw_arc(dwg, adjusted_points, arc_center, radius, direction, markers, stroke_color, dash)
    else:
        # Unknown type, fallback to straight line
        return _draw_straight_line(dwg, adjusted_points, direction, markers, stroke_color, dash)


def _on_border(elem, point, tol=1.5):
    """True si `point` cae sobre el borde del rectángulo de `elem` (±tol). Sirve
    para respetar puertos ya bien ubicados y sólo recortar los que flotan."""
    ex, ey = elem.get('x'), elem.get('y')
    if ex is None or ey is None:
        return True                       # sin geometría → no tocar
    w = elem.get('width', ICON_WIDTH)
    h = elem.get('height', ICON_HEIGHT)
    px, py = point
    on_x = abs(px - ex) <= tol or abs(px - (ex + w)) <= tol
    on_y = abs(py - ey) <= tol or abs(py - (ey + h)) <= tol
    in_x = ex - tol <= px <= ex + w + tol
    in_y = ey - tol <= py <= ey + h + tol
    return (on_x and in_y) or (on_y and in_x)


def clip_to_border(elem, toward):
    """Punto sobre el BORDE del rectángulo de `elem` en la dirección hacia
    `toward` (x, y), partiendo del centro del ícono (K34 — recorte compartido).

    A diferencia del viejo offset radial `max(w,h)/2` (que para diagonales caía
    fuera del rectángulo → conectores flotando), esto resuelve la intersección
    rayo-rectángulo: el extremo cae EXACTO en el borde a cualquier ángulo.
    Los contenedores se devuelven sin tocar (el router ya dio su punto de borde).
    """
    ex, ey = elem.get('x'), elem.get('y')
    if ex is None or ey is None:
        return None
    w = elem.get('width', ICON_WIDTH)
    h = elem.get('height', ICON_HEIGHT)
    cx, cy = ex + w / 2.0, ey + h / 2.0
    dx, dy = toward[0] - cx, toward[1] - cy
    if dx == 0 and dy == 0:
        return (cx, cy)
    tx = (w / 2.0) / abs(dx) if dx != 0 else float('inf')
    ty = (h / 2.0) / abs(dy) if dy != 0 else float('inf')
    t = min(tx, ty)
    return (cx + dx * t, cy + dy * t)


def _apply_visual_offsets(points, from_elem, to_elem):
    """
    Recorta los extremos del path al borde de cada ícono (K34), en vez de
    aplicar un offset radial fijo. Así todo conector empieza y termina EXACTO
    sobre el borde del rectángulo, a cualquier ángulo.

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

    # Origen: recortar al borde salvo contenedor (el router ya dio el borde).
    if not from_elem.get('contains'):
        clipped = clip_to_border(from_elem, points[1])
        if clipped is not None:
            adjusted[0] = clipped

    # Destino: idem, mirando hacia el penúltimo punto.
    if not to_elem.get('contains'):
        clipped = clip_to_border(to_elem, points[-2])
        if clipped is not None:
            adjusted[-1] = clipped

    return adjusted


def _draw_straight_line(dwg, points, direction, markers, stroke_color='black', dash=None):
    """Dibuja una línea recta entre dos puntos."""
    if len(points) < 2:
        return (0, 0)

    x1, y1 = points[0]
    x2, y2 = points[-1]

    line_attrs = {
        'start': (x1, y1),
        'end': (x2, y2),
        'stroke': stroke_color,
        'stroke_width': 2
    }
    if dash:
        line_attrs['stroke_dasharray'] = dash

    _apply_direction_markers(line_attrs, direction, markers)

    dwg.add(dwg.line(**line_attrs))

    # Retornar centro
    return (x1 + x2) / 2, (y1 + y2) / 2


def _draw_polyline(dwg, points, direction, markers, corner_radius=0, stroke_color='black', dash=None):
    """Dibuja una polyline, opcionalmente con esquinas redondeadas via SVG path Q curves."""
    if len(points) < 2:
        return (0, 0)

    if corner_radius > 0 and len(points) > 2:
        return _draw_rounded_polyline(dwg, points, direction, markers, corner_radius, stroke_color, dash)

    polyline_attrs = {
        'points': points,
        'stroke': stroke_color,
        'stroke_width': 2,
        'fill': 'none'
    }
    if dash:
        polyline_attrs['stroke_dasharray'] = dash

    _apply_direction_markers(polyline_attrs, direction, markers)

    dwg.add(dwg.polyline(**polyline_attrs))

    # Calcular centro (promedio de puntos)
    total_x = sum(p[0] for p in points)
    total_y = sum(p[1] for p in points)
    return total_x / len(points), total_y / len(points)


def _draw_rounded_polyline(dwg, points, direction, markers, corner_radius, stroke_color='black', dash=None):
    """Dibuja polyline con esquinas redondeadas usando SVG path con curvas cuadraticas (Q)."""
    # Construir SVG path: M start L...Q...L... end
    x0, y0 = points[0]
    path_d = f"M {x0:.1f},{y0:.1f}"

    for i in range(1, len(points) - 1):
        # Punto anterior, actual (vertice), siguiente
        px, py = points[i - 1]
        vx, vy = points[i]
        nx, ny = points[i + 1]

        # Vectores de entrada y salida
        in_dx, in_dy = vx - px, vy - py
        out_dx, out_dy = nx - vx, ny - vy

        in_len = math.hypot(in_dx, in_dy)
        out_len = math.hypot(out_dx, out_dy)

        if in_len == 0 or out_len == 0:
            path_d += f" L {vx:.1f},{vy:.1f}"
            continue

        # Radio efectivo: no puede ser mayor que la mitad de cualquier segmento adyacente
        r = min(corner_radius, in_len / 2, out_len / 2)

        # Punto donde empieza la curva (sobre el segmento de entrada, a distancia r del vertice)
        sx = vx - (in_dx / in_len) * r
        sy = vy - (in_dy / in_len) * r

        # Punto donde termina la curva (sobre el segmento de salida, a distancia r del vertice)
        ex = vx + (out_dx / out_len) * r
        ey = vy + (out_dy / out_len) * r

        # L hasta inicio de curva, Q con vertice como control point hasta fin de curva
        path_d += f" L {sx:.1f},{sy:.1f} Q {vx:.1f},{vy:.1f} {ex:.1f},{ey:.1f}"

    # Linea final al ultimo punto
    xn, yn = points[-1]
    path_d += f" L {xn:.1f},{yn:.1f}"

    path_attrs = {
        'd': path_d,
        'stroke': stroke_color,
        'stroke_width': 2,
        'fill': 'none'
    }
    if dash:
        path_attrs['stroke_dasharray'] = dash

    _apply_direction_markers(path_attrs, direction, markers)

    dwg.add(dwg.path(**path_attrs))

    # Calcular centro (promedio de puntos)
    total_x = sum(p[0] for p in points)
    total_y = sum(p[1] for p in points)
    return total_x / len(points), total_y / len(points)


def _draw_bezier_curve(dwg, points, control_points, direction, markers, stroke_color='black', dash=None):
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
        'stroke': stroke_color,
        'stroke_width': 2,
        'fill': 'none'
    }
    if dash:
        path_attrs['stroke_dasharray'] = dash

    _apply_direction_markers(path_attrs, direction, markers)

    dwg.add(dwg.path(**path_attrs))

    # Retornar centro aproximado (punto medio de la curva)
    return (x1 + x2) / 2, (y1 + y2) / 2


def _draw_arc(dwg, points, arc_center, radius, direction, markers, stroke_color='black', dash=None):
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

    # Self-loops: start y end están cerca, necesitan large-arc=1 para el loop completo
    dist = math.hypot(x2 - x1, y2 - y1)
    large_arc = 1 if dist < radius * 2 else 0
    path_d = f"M {x1},{y1} A {radius},{radius} 0 {large_arc},1 {x2},{y2}"

    path_attrs = {
        'd': path_d,
        'stroke': stroke_color,
        'stroke_width': 2,
        'fill': 'none'
    }
    if dash:
        path_attrs['stroke_dasharray'] = dash

    _apply_direction_markers(path_attrs, direction, markers)

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
        font_size=f"{FONT_SIZE_CONNECTION}px",
        font_family="Arial, sans-serif",
        fill="#14181d",
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
