"""
SVGRenderer — encapsula la creación de elementos SVG para diagramas AlmaGag.

Extraído de generator.py para separar orquestación de renderizado.
"""
import colorsys
import logging

import svgwrite

from AlmaGag.draw.connections import draw_connection_line, draw_connection_label
from AlmaGag.draw.container import draw_container as _draw_container
from AlmaGag.draw.icons import draw_icon_shape as _draw_icon_shape, draw_icon_label as _draw_icon_label
from AlmaGag.draw.container import calculate_container_bounds
from AlmaGag.config import ICON_WIDTH, ICON_HEIGHT, CONTAINER_PADDING, TEXT_LINE_HEIGHT
from AlmaGag.utils import extract_item_id

logger = logging.getLogger('AlmaGag')


class DrawingGroupProxy:
    """Proxy that redirects add() to a Group while delegating factory methods to Drawing.

    Used to wrap SVG elements in <g> groups with <desc> metadata for NdFn labels.
    Factory methods (rect, text, linearGradient, defs, etc.) go to the real Drawing,
    while add() puts elements into the group.
    """

    def __init__(self, dwg, group):
        self._dwg = dwg
        self._group = group

    def add(self, element):
        return self._group.add(element)

    def __getattr__(self, name):
        return getattr(self._dwg, name)


def create_canvas(output_path, canvas_width, canvas_height):
    """Crea el Drawing SVG con filtro global de glow blanco para etiquetas.

    Returns:
        svgwrite.Drawing configurado con viewbox y filtro text-glow.
    """
    dwg = svgwrite.Drawing(output_path, size=(canvas_width, canvas_height), debug=False)
    dwg.viewbox(0, 0, canvas_width, canvas_height)

    # Filtro global de glow blanco para etiquetas (Gaussian blur)
    text_glow = dwg.filter(id='text-glow', x='-20%', y='-20%', width='140%', height='140%')
    text_glow.feGaussianBlur(in_='SourceGraphic', stdDeviation=2, result='blur')
    text_glow.feFlood(flood_color='white', flood_opacity=1, result='color')
    text_glow.feComposite(in_='color', in2='blur', operator='in', result='shadow')
    text_glow.feMerge(layernames=['shadow', 'shadow', 'SourceGraphic'])
    dwg.defs.add(text_glow)

    return dwg


def _generate_color_palette(n):
    """Genera N colores distinguibles usando HSL con hue distribuido uniformemente."""
    colors = []
    for i in range(n):
        hue = i / max(n, 1)
        r, g, b = colorsys.hls_to_rgb(hue, 0.45, 0.70)
        colors.append(f'#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}')
    return colors


def _create_arrow_marker(dwg, marker_id, color, direction='end'):
    """Crea un marker de flecha triangular."""
    if direction == 'end':
        marker = dwg.marker(id=marker_id, insert=(10, 5), size=(10, 10), orient='auto')
        marker.add(dwg.path(d='M 0 0 L 10 5 L 0 10 z', fill=color))
    else:
        marker = dwg.marker(id=marker_id, insert=(0, 5), size=(10, 10), orient='auto')
        marker.add(dwg.path(d='M 10 0 L 0 5 L 10 10 z', fill=color))
    dwg.defs.add(marker)
    return marker


def _create_circle_marker(dwg, marker_id, color):
    """Crea un marker de círculo para el origen de conexiones unidireccionales."""
    marker = dwg.marker(id=marker_id, insert=(5, 5), size=(10, 10), orient='auto')
    marker.add(dwg.circle(center=(5, 5), r=4, fill=color))
    dwg.defs.add(marker)
    return marker


def setup_arrow_markers(dwg, connections=None, color_connections=False):
    """
    Crea los markers SVG para flechas y círculos direccionales.

    - Conexiones unidireccionales: círculo en origen, flecha en destino.
    - Conexiones bidireccionales: flechas en ambos extremos.
    - Si color_connections=True, cada conexión recibe un color distinto.

    Retorna:
        Si color_connections=False: dict global con markers negros.
        Si color_connections=True: (dict_global_fallback, list_per_connection)
           donde list_per_connection[i] = {'markers': {...}, 'color': hex_color}
    """
    # Markers negros por defecto (siempre se crean)
    arrow_end = _create_arrow_marker(dwg, 'arrow-end', 'black', 'end')
    arrow_start = _create_arrow_marker(dwg, 'arrow-start', 'black', 'start')
    circle_start = _create_circle_marker(dwg, 'circle-start', 'black')
    circle_end = _create_circle_marker(dwg, 'circle-end', 'black')

    default_markers = {
        'arrow_end': arrow_end.get_funciri(),
        'arrow_start': arrow_start.get_funciri(),
        'circle_start': circle_start.get_funciri(),
        'circle_end': circle_end.get_funciri(),
        # Compat keys legacy
        'forward': arrow_end.get_funciri(),
        'backward': arrow_start.get_funciri(),
        'bidirectional': (arrow_start.get_funciri(), arrow_end.get_funciri()),
    }

    if not color_connections or not connections:
        return default_markers

    # Generar markers coloreados por conexión
    n = len(connections)
    palette = _generate_color_palette(n)
    per_connection = []

    for i, conn in enumerate(connections):
        color = palette[i]
        suffix = f'-c{i}'

        ae = _create_arrow_marker(dwg, f'arrow-end{suffix}', color, 'end')
        ast = _create_arrow_marker(dwg, f'arrow-start{suffix}', color, 'start')
        cs = _create_circle_marker(dwg, f'circle-start{suffix}', color)
        ce = _create_circle_marker(dwg, f'circle-end{suffix}', color)

        per_connection.append({
            'markers': {
                'arrow_end': ae.get_funciri(),
                'arrow_start': ast.get_funciri(),
                'circle_start': cs.get_funciri(),
                'circle_end': ce.get_funciri(),
                # Compat keys legacy
                'forward': ae.get_funciri(),
                'backward': ast.get_funciri(),
                'bidirectional': (ast.get_funciri(), ae.get_funciri()),
            },
            'color': color,
        })

    return default_markers, per_connection


def draw_connections(dwg, connections, elements_by_id, markers, per_conn_styles, ndfn_labels):
    """Dibuja todas las líneas de conexión (sin etiquetas).

    Retorna dict conn_centers: {key: (mid_x, mid_y)} para posicionar etiquetas después.
    """
    conn_centers = {}
    for i, conn in enumerate(connections):
        if per_conn_styles and i < len(per_conn_styles):
            conn_markers = per_conn_styles[i]['markers']
            conn_color = per_conn_styles[i]['color']
        else:
            conn_markers = markers
            conn_color = 'black'

        # Wrap connection in <g> with <desc> if visualdebug
        conn_ndfn_group = None
        draw_target = dwg
        if ndfn_labels:
            from_ndfn = ndfn_labels.get(conn['from'], conn['from'])
            to_ndfn = ndfn_labels.get(conn['to'], conn['to'])
            # Extract AAA numbers for concise id
            from_aaa = from_ndfn.split('.')[1] if '.' in from_ndfn else conn['from']
            to_aaa = to_ndfn.split('.')[1] if '.' in to_ndfn else conn['to']
            conn_id = f"conn-{from_aaa}-to-{to_aaa}"
            conn_ndfn_group = dwg.g(id=conn_id)
            label = conn.get('label', '')
            desc_text = f"From {from_ndfn} to {to_ndfn}"
            if label:
                desc_text += f" | {label}"
            conn_ndfn_group.set_desc(desc=desc_text)
            draw_target = DrawingGroupProxy(dwg, conn_ndfn_group)

        center = draw_connection_line(draw_target, elements_by_id, conn, conn_markers, stroke_color=conn_color)
        if conn_ndfn_group is not None:
            dwg.add(conn_ndfn_group)

        key = f"{conn['from']}->{conn['to']}"
        conn_centers[key] = center

    return conn_centers


def ndfn_wrap(target, elem_id, ndfn_labels):
    """Wrap drawing target in a <g> with <desc> if NdFn label exists.

    Returns (draw_target, group_or_None). If wrapping, caller must
    add group_or_None to dwg after drawing.
    """
    ndfn = ndfn_labels.get(elem_id, '')
    if not ndfn:
        return target, None
    g = target.g(id=f'ndfn-{elem_id}')
    g.set_desc(desc=f'{ndfn} | {elem_id}')
    return DrawingGroupProxy(target, g), g


def render_containers(dwg, containers, elements_by_id, ndfn_labels, layout_algorithm):
    """Dibuja todos los contenedores (solo fondo, sin ícono ni labels)."""
    for container in containers:
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"[RECT] {container['id']}: ({container.get('x', 0):.1f}, {container.get('y', 0):.1f}) {container.get('width', 0):.1f}x{container.get('height', 0):.1f}")
        draw_target, ndfn_group = ndfn_wrap(dwg, container['id'], ndfn_labels)
        _draw_container(draw_target, container, elements_by_id, draw_label=False, layout_algorithm=layout_algorithm, draw_icon=False)
        if ndfn_group is not None:
            dwg.add(ndfn_group)


def render_icons(dwg, normal_elements, ndfn_labels, embedded_icons=None):
    """Dibuja todos los íconos normales (sin etiquetas)."""
    logger.debug(f"\n[DIBUJAR ELEMENTOS] Total: {len(normal_elements)}")
    for elem in normal_elements:
        if 'x' in elem and 'y' in elem:
            logger.debug(f"  {elem['id']}: ({elem['x']:.1f}, {elem['y']:.1f}) "
                       f"size({elem.get('width', ICON_WIDTH):.1f} x {elem.get('height', ICON_HEIGHT):.1f})")
        draw_target, ndfn_group = ndfn_wrap(dwg, elem['id'], ndfn_labels)
        _draw_icon_shape(draw_target, elem, embedded_icons=embedded_icons)
        if ndfn_group is not None:
            dwg.add(ndfn_group)


def render_container_icons(dwg, containers, elements_by_id, ndfn_labels, embedded_icons=None):
    """Dibuja los íconos de contenedores (encima de elementos contenidos)."""
    import importlib

    for container in containers:
        container_id = container['id']

        # Usar coordenadas pre-calculadas o calcular bounds
        if '_is_container_calculated' in container and all(k in container for k in ['x', 'y']):
            container_x = container['x']
            container_y = container['y']
        else:
            bounds = calculate_container_bounds(container, elements_by_id)
            container_x = bounds['x']
            container_y = bounds['y']

        icon_x = container_x + CONTAINER_PADDING
        icon_y = container_y + CONTAINER_PADDING

        icon_type = container.get('type', 'building')
        color = container.get('color', 'lightgray')

        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"[ICON] {container_id}: container=({container_x:.1f}, {container_y:.1f}), icon=({icon_x:.1f}, {icon_y:.1f})")

        # Wrap container icon in NdFn group if label exists
        icon_ndfn_key = f"{container_id}__icon"
        draw_target, ndfn_group = ndfn_wrap(dwg, icon_ndfn_key, ndfn_labels)

        # Dibujar ícono directamente
        icon_elem_id = f"{container_id}_icon"
        if embedded_icons and icon_type in embedded_icons:
            from AlmaGag.draw.icons import draw_embedded_icon
            draw_embedded_icon(draw_target, icon_x, icon_y, color, icon_elem_id, embedded_icons[icon_type])
        else:
            try:
                icon_module = importlib.import_module(f'AlmaGag.draw.{icon_type}')
                draw_func = getattr(icon_module, f'draw_{icon_type}')
                draw_func(draw_target, icon_x, icon_y, color, icon_elem_id)
            except (ImportError, AttributeError):
                from AlmaGag.draw.icons import create_gradient
                gradient_id = create_gradient(draw_target, container_id, color)
                icon_size = min(ICON_WIDTH, ICON_HEIGHT) * 0.6
                draw_target.add(draw_target.rect(
                    insert=(icon_x, icon_y),
                    size=(icon_size, icon_size),
                    fill=gradient_id,
                    stroke='black',
                    opacity=1.0
                ))

        if ndfn_group is not None:
            dwg.add(ndfn_group)


def render_element_labels(dwg, elements, optimized_label_positions, label_positions):
    """Dibuja etiquetas de elementos normales con posiciones optimizadas o fallback."""
    for elem in elements:
        if 'contains' not in elem and elem.get('label'):
            optimized_pos = optimized_label_positions.get(elem['id'])
            if optimized_pos:
                label_text = elem['label']
                lines = label_text.split('\n')

                for i, line in enumerate(lines):
                    dwg.add(dwg.text(
                        line,
                        insert=(optimized_pos.x, optimized_pos.y + (i * 18)),
                        text_anchor=optimized_pos.anchor,
                        font_size="14px",
                        font_family="Arial, sans-serif",
                        fill="black",
                        filter='url(#text-glow)'
                    ))
            else:
                position_info = label_positions.get(elem['id'])
                _draw_icon_label(dwg, elem, position_info)


def render_container_labels(dwg, containers, elements_by_id):
    """Dibuja etiquetas de contenedores en posición fija (NO optimizadas)."""
    for container in containers:
        if container.get('label'):
            if 'x' in container and 'y' in container:
                container_x = container['x']
                container_y = container['y']

                # LOG: Geometría del contenedor (COORDENADAS LOCALES)
                logger.debug(f"\n{'='*70}")
                logger.debug(f"[GEOMETRIA LOCAL CONTENEDOR] {container['id']}")
                logger.debug(f"{'='*70}")
                if 'width' in container and 'height' in container:
                    logger.debug(f"Contenedor global: ({container_x:.1f}, {container_y:.1f}) "
                               f"size({container['width']:.1f} x {container['height']:.1f})")
                else:
                    logger.debug(f"Contenedor global: ({container_x:.1f}, {container_y:.1f}) "
                               f"size(pending - Phase 4 not implemented)")
                logger.debug(f"\nElementos en coordenadas LOCALES (relativas a esquina superior izquierda):")

                icon_local_x = 10
                icon_local_y = 0
                logger.debug(f"\n  1) ICONO CONTENEDOR:")
                logger.debug(f"     Local: ({icon_local_x}, {icon_local_y})")
                logger.debug(f"     Size: {ICON_WIDTH} x {ICON_HEIGHT}")
                logger.debug(f"     Global: ({container_x + icon_local_x:.1f}, {container_y + icon_local_y:.1f})")

                label_local_x = 10 + ICON_WIDTH + 10
                label_local_y = 16
                lines = container['label'].split('\n')
                label_width = max(len(line) for line in lines) * 8
                label_height = len(lines) * TEXT_LINE_HEIGHT
                logger.debug(f"\n  2) ETIQUETA CONTENEDOR: '{container['label'].replace(chr(10), ' / ')}'")
                logger.debug(f"     Local: ({label_local_x}, {label_local_y}) [baseline primera línea]")
                logger.debug(f"     Size: ~{label_width} x {label_height} [{len(lines)} líneas]")
                logger.debug(f"     Global: ({container_x + label_local_x:.1f}, {container_y + label_local_y:.1f})")

                contains = container.get('contains', [])
                if contains:
                    logger.debug(f"\n  3) ELEMENTOS INTERNOS: {len(contains)}")
                    for idx, ref in enumerate(contains, 1):
                        ref_id = extract_item_id(ref)
                        elem = elements_by_id.get(ref_id)
                        if elem and 'x' in elem:
                            elem_local_x = elem['x'] - container_x
                            elem_local_y = elem['y'] - container_y
                            elem_width = elem.get('width', ICON_WIDTH)
                            elem_height = elem.get('height', ICON_HEIGHT)
                            logger.debug(f"\n     {idx}) {ref_id}:")
                            logger.debug(f"        Local: ({elem_local_x:.1f}, {elem_local_y:.1f})")
                            logger.debug(f"        Size: {elem_width:.1f} x {elem_height:.1f}")
                            logger.debug(f"        Global: ({elem['x']:.1f}, {elem['y']:.1f})")

                            if elem.get('label'):
                                elem_label = elem['label']
                                elem_label_y_offset = elem_height + 15
                                elem_label_local_x = elem_local_x + elem_width / 2
                                elem_label_local_y = elem_local_y + elem_label_y_offset
                                logger.debug(f"        Etiqueta: '{elem_label}'")
                                logger.debug(f"          Local: ({elem_label_local_x:.1f}, {elem_label_local_y:.1f}) [aproximado]")
                                logger.debug(f"          Global: ({container_x + elem_label_local_x:.1f}, {container_y + elem_label_local_y:.1f}) [aproximado]")

                logger.debug(f"{'='*70}\n")

                # Dibujar cada línea de la etiqueta del contenedor
                label_x = container_x + label_local_x
                label_y = container_y + label_local_y
                for i, line in enumerate(lines):
                    dwg.add(dwg.text(
                        line,
                        insert=(label_x, label_y + (i * 18)),
                        text_anchor="start",
                        font_size="16px",
                        font_family="Arial, sans-serif",
                        font_weight="bold",
                        fill="black",
                        filter='url(#text-glow)'
                    ))


def draw_connection_labels(dwg, connections, conn_centers, optimized_label_positions):
    """Dibuja las etiquetas de conexiones con posiciones optimizadas o fallback."""
    for conn in connections:
        if conn.get('label'):
            key = f"{conn['from']}->{conn['to']}"
            optimized_pos = optimized_label_positions.get(key)
            if optimized_pos:
                dwg.add(dwg.text(
                    conn['label'],
                    insert=(optimized_pos.x, optimized_pos.y),
                    text_anchor=optimized_pos.anchor,
                    font_size="12px",
                    font_family="Arial, sans-serif",
                    fill="gray",
                    filter='url(#text-glow)'
                ))
            else:
                center = conn_centers.get(key)
                if center:
                    draw_connection_label(dwg, conn, center)
