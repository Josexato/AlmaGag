import os, json, svgwrite, logging, csv, colorsys
from datetime import datetime
from AlmaGag.config import (
    WIDTH, HEIGHT, ICON_WIDTH, ICON_HEIGHT,
    TEXT_LINE_HEIGHT, TEXT_CHAR_WIDTH,
    CONTAINER_ICON_X, CONTAINER_ICON_Y, CONTAINER_LABEL_X, CONTAINER_LABEL_Y,
    LABEL_OFFSET_VERTICAL, CONTAINER_PADDING
)
from AlmaGag.layout import Layout, AutoLayoutOptimizer
from AlmaGag.layout.label_optimizer import LabelPositionOptimizer, Label
from AlmaGag.draw.icons import draw_icon_shape, draw_icon_label
from AlmaGag.draw.connections import draw_connection_line, draw_connection_label
from AlmaGag.draw.container import draw_container
from AlmaGag.debug import add_debug_badge, convert_svg_to_png

# Logger global para AlmaGag
logger = logging.getLogger('AlmaGag')

def dump_layout_table(optimized_layout, elements_by_id, containers, phase="FINAL", csv_file=None):
    """
    Genera una tabla con información detallada de todos los elementos del layout.
    Guarda en CSV para análisis posterior.

    Args:
        optimized_layout: Layout optimizado con información de niveles y grupos
        elements_by_id: Diccionario de elementos por ID
        containers: Lista de contenedores
        phase: Nombre de la fase del proceso (ej: "INITIAL", "PHASE_1", "PHASE_2", etc.)
        csv_file: Ruta del archivo CSV donde guardar (si None, genera con timestamp)
    """
    # Si no se proporciona csv_file, generar con timestamp
    if csv_file is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_file = f"debug/layout_evolution_{timestamp}.csv"
    logger.debug("\n" + "="*170)
    logger.debug(f"DUMP DEL LAYOUT - TABLA DE ELEMENTOS [{phase}]")
    logger.debug("="*170)

    # Header de la tabla (con Phase y Indice)
    header = f"{'Phase':<20}{'Indice':<12}{'Nivel':<8}{'Grupo':<8}{'Tipo':<15}{'ID':<30}{'Referencial':<30}{'X Local':<12}{'Y Local':<12}{'X Global':<12}{'Y Global':<12}{'Ancho':<12}{'Alto':<12}"
    logger.debug(header)
    logger.debug("-" * 170)

    rows = []

    # Función auxiliar para encontrar el grupo de un elemento
    def find_group(elem_id, groups):
        for idx, group_list in enumerate(groups, 1):
            if elem_id in group_list:
                return idx
        return 0

    # Contador global para índice único
    global_index = 0

    # Identificar elementos contenidos para excluirlos del procesamiento principal
    contained_elements = set()
    for container in containers:
        for item in container.get('contains', []):
            item_id = item['id'] if isinstance(item, dict) else item
            contained_elements.add(item_id)

    # Procesar solo elementos primarios (no contenidos)
    for element in optimized_layout.elements:
        elem_id = element['id']

        # Saltar elementos contenidos - ya fueron procesados con su contenedor
        if elem_id in contained_elements:
            continue

        level = optimized_layout.levels.get(elem_id, 0)
        group = find_group(elem_id, optimized_layout.groups)

        # Determinar si es contenedor
        is_container = 'contains' in element

        if is_container:
            # CONTENEDOR
            global_index += 1
            container_index = global_index

            x_global = element.get('x', None)
            y_global = element.get('y', None)
            width = element.get('width', None)
            height = element.get('height', None)

            # Índice para contenedor: XX.00.00
            indice = f"{container_index:02d}.00.00"

            rows.append({
                'phase': phase,
                'indice': indice,
                'nivel': level,
                'grupo': group,
                'tipo': 'Contenedor',
                'id': f"{elem_id}.Cnt",
                'referencial': 'origen',
                'x_local': 0,
                'y_local': 0,
                'x_global': x_global if x_global is not None else 0,
                'y_global': y_global if y_global is not None else 0,
                'width': width if width is not None else 0,
                'height': height if height is not None else 0
            })

            # ÍCONO DEL CONTENEDOR (pegado al borde superior)
            icon_x_local = CONTAINER_ICON_X  # Padding left
            icon_y_local = CONTAINER_ICON_Y   # Sin padding top - pegado arriba
            icon_x_global = x_global + icon_x_local if x_global is not None else 0
            icon_y_global = y_global + icon_y_local if y_global is not None else 0

            # Índice para ícono del contenedor: XX.01.00
            child_num = 1
            icon_indice = f"{container_index:02d}.{child_num:02d}.00"

            rows.append({
                'phase': phase,
                'indice': icon_indice,
                'nivel': level,
                'grupo': group,
                'tipo': 'Icono',
                'id': elem_id,
                'referencial': f"{elem_id}.Cnt",
                'x_local': icon_x_local,
                'y_local': icon_y_local,
                'x_global': icon_x_global,
                'y_global': icon_y_global,
                'width': ICON_WIDTH,
                'height': ICON_HEIGHT
            })

            # ETIQUETA DEL CONTENEDOR
            if element.get('label'):
                label_x_local = CONTAINER_LABEL_X
                label_y_local = CONTAINER_LABEL_Y  # Alineada con el icono (baseline)
                label_x_global = x_global + label_x_local if x_global is not None else 0
                label_y_global = y_global + label_y_local if y_global is not None else 0

                lines = element['label'].split('\n')
                label_width = max(len(line) for line in lines) * 8
                label_height = len(lines) * TEXT_LINE_HEIGHT

                # Índice para etiqueta del contenedor: XX.01.01
                label_indice = f"{container_index:02d}.01.01"

                rows.append({
                    'phase': phase,
                    'indice': label_indice,
                    'nivel': level,
                    'grupo': group,
                    'tipo': 'Etiqueta',
                    'id': f"{elem_id}.Lbl",
                    'referencial': elem_id,
                    'x_local': label_x_local,
                    'y_local': label_y_local,
                    'x_global': label_x_global,
                    'y_global': label_y_global,
                    'width': label_width,
                    'height': label_height
                })

            # ELEMENTOS CONTENIDOS
            child_index = 1  # Empezar en 1 (00 es contenedor, 01 es ícono del contenedor)
            for ref in element.get('contains', []):
                child_index += 1  # Incrementar para cada hijo
                ref_id = ref['id'] if isinstance(ref, dict) else ref
                contained_elem = elements_by_id.get(ref_id)

                if contained_elem:
                    # Calcular posición local
                    container_x = element.get('x', None)
                    container_y = element.get('y', None)
                    elem_x_global = contained_elem.get('x', None)
                    elem_y_global = contained_elem.get('y', None)

                    if elem_x_global is not None and elem_y_global is not None:
                        elem_x_local = elem_x_global - container_x
                        elem_y_local = elem_y_global - container_y
                    else:
                        elem_x_local = 0
                        elem_y_local = 0

                    elem_width = contained_elem.get('width', ICON_WIDTH)
                    elem_height = contained_elem.get('height', ICON_HEIGHT)

                    # Indice para ícono del hijo: AA.BB.00
                    child_icon_indice = f"{container_index:02d}.{child_index:02d}.00"

                    # ÍCONO DEL ELEMENTO CONTENIDO
                    rows.append({
                        'phase': phase,
                        'indice': child_icon_indice,
                        'nivel': level,
                        'grupo': group,
                        'tipo': 'Icono',
                        'id': ref_id,
                        'referencial': f"{elem_id}.Cnt",
                        'x_local': elem_x_local,
                        'y_local': elem_y_local,
                        'x_global': elem_x_global,
                        'y_global': elem_y_global,
                        'width': elem_width,
                        'height': elem_height
                    })

                    # ETIQUETA DEL ELEMENTO CONTENIDO
                    if contained_elem.get('label'):
                        # Usar posición de layout.label_positions si existe
                        if ref_id in optimized_layout.label_positions:
                            label_pos = optimized_layout.label_positions[ref_id]
                            label_x_global, label_y_global = label_pos[0], label_pos[1]

                            # Calcular coordenadas locales
                            if container_x is not None and container_y is not None:
                                label_x_local = label_x_global - container_x
                                label_y_local = label_y_global - container_y
                            else:
                                label_x_local = 0
                                label_y_local = 0
                        else:
                            # Fallback: calcular como antes
                            label_x_local = elem_x_local + elem_width / 2 if elem_x_local is not None else 0
                            label_y_local = elem_y_local + elem_height + 15 if elem_y_local is not None else 0
                            label_x_global = elem_x_global + elem_width / 2 if elem_x_global is not None else 0
                            label_y_global = elem_y_global + elem_height + 15 if elem_y_global is not None else 0

                        label_text = contained_elem['label']
                        # Calcular ancho basándose en la línea más larga (no total de caracteres)
                        label_lines_csv = label_text.split('\n')
                        label_width_est = max(len(line) for line in label_lines_csv) * 8 if label_lines_csv else 0
                        label_height_est = len(label_lines_csv) * 18

                        # Indice para etiqueta del hijo: AA.BB.01
                        child_label_indice = f"{container_index:02d}.{child_index:02d}.01"

                        rows.append({
                            'phase': phase,
                            'indice': child_label_indice,
                            'nivel': level,
                            'grupo': group,
                            'tipo': 'Etiqueta',
                            'id': f"{ref_id}.Lbl",
                            'referencial': ref_id,
                            'x_local': label_x_local,
                            'y_local': label_y_local,
                            'x_global': label_x_global,
                            'y_global': label_y_global,
                            'width': label_width_est,
                            'height': label_height_est
                        })
        else:
            # ELEMENTO NORMAL (NO CONTENEDOR)
            global_index += 1
            element_index = global_index

            x_global = element.get('x', None)
            y_global = element.get('y', None)
            width = element.get('width', ICON_WIDTH)
            height = element.get('height', ICON_HEIGHT)

            # Indice para elemento normal: AA.00.00
            normal_indice = f"{element_index:02d}.00.00"

            # ÍCONO
            rows.append({
                'phase': phase,
                'indice': normal_indice,
                'nivel': level,
                'grupo': group,
                'tipo': 'Icono',
                'id': elem_id,
                'referencial': 'origen',
                'x_local': 0,
                'y_local': 0,
                'x_global': x_global,
                'y_global': y_global,
                'width': width,
                'height': height
            })

            # ETIQUETA
            if element.get('label'):
                label_x_global = x_global + width / 2 if x_global is not None else 0
                label_y_global = y_global + height + 15 if y_global is not None else 0

                label_text = element['label']
                lines = label_text.split('\n')
                label_width_est = max(len(line) for line in lines) * 8
                label_height_est = len(lines) * 18

                # Indice para etiqueta de elemento normal: AA.00.01
                normal_label_indice = f"{element_index:02d}.00.01"

                rows.append({
                    'phase': phase,
                    'indice': normal_label_indice,
                    'nivel': level,
                    'grupo': group,
                    'tipo': 'Etiqueta',
                    'id': f"{elem_id}.Lbl",
                    'referencial': elem_id,
                    'x_local': 0,
                    'y_local': 0,
                    'x_global': label_x_global,
                    'y_global': label_y_global,
                    'width': label_width_est,
                    'height': label_height_est
                })

    # Imprimir todas las filas
    for row in rows:
        phase_str = str(row['phase'])
        indice_str = str(row['indice'])
        nivel_str = str(row['nivel']) if row['nivel'] is not None else 0
        grupo_str = str(row['grupo']) if row['grupo'] is not None else 0
        x_local_str = f"{row['x_local']:.1f}" if isinstance(row['x_local'], (int, float)) else str(row['x_local'])
        y_local_str = f"{row['y_local']:.1f}" if isinstance(row['y_local'], (int, float)) else str(row['y_local'])
        x_global_str = f"{row['x_global']:.1f}" if isinstance(row['x_global'], (int, float)) else str(row['x_global'])
        y_global_str = f"{row['y_global']:.1f}" if isinstance(row['y_global'], (int, float)) else str(row['y_global'])
        width_str = f"{row['width']:.1f}" if isinstance(row['width'], (int, float)) else str(row['width'])
        height_str = f"{row['height']:.1f}" if isinstance(row['height'], (int, float)) else str(row['height'])

        line = f"{phase_str:<20}{indice_str:<12}{nivel_str:<8}{grupo_str:<8}{row['tipo']:<15}{row['id']:<30}{row['referencial']:<30}{x_local_str:<12}{y_local_str:<12}{x_global_str:<12}{y_global_str:<12}{width_str:<12}{height_str:<12}"
        logger.debug(line)

    logger.debug("="*170 + "\n")

    # Guardar en CSV
    _save_to_csv(rows, csv_file)

def _save_to_csv(rows, csv_file):
    """
    Guarda las filas del layout en un archivo CSV.
    Crea el archivo con headers si no existe, o appenda si ya existe.

    Args:
        rows: Lista de diccionarios con los datos
        csv_file: Ruta del archivo CSV
    """
    if not rows:
        return

    # Crear directorio si no existe
    csv_dir = os.path.dirname(csv_file)
    if csv_dir and not os.path.exists(csv_dir):
        os.makedirs(csv_dir)

    # Verificar si el archivo existe
    file_exists = os.path.exists(csv_file)

    # Headers del CSV
    fieldnames = ['phase', 'indice', 'nivel', 'grupo', 'tipo', 'id', 'referencial',
                  'x_local', 'y_local', 'x_global', 'y_global', 'width', 'height']

    try:
        with open(csv_file, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)

            # Escribir headers solo si el archivo es nuevo
            if not file_exists:
                writer.writeheader()

            # Escribir filas
            writer.writerows(rows)

        logger.debug(f"[CSV] Datos guardados en: {csv_file} ({len(rows)} filas)")
    except Exception as e:
        logger.error(f"[CSV] Error al guardar CSV: {e}")

def draw_grid(dwg, width, height, grid_size=20):
    """
    Dibuja una rejilla de guía en el fondo del diagrama.

    Args:
        dwg: SVG drawing object
        width: Ancho del canvas
        height: Alto del canvas
        grid_size: Tamaño de cada celda de la rejilla (default 20px)
    """
    # Crear grupo para la rejilla
    grid_group = dwg.g(id='grid', opacity=0.4)

    # Líneas verticales
    for x in range(0, int(width) + 1, grid_size):
        grid_group.add(dwg.line(
            start=(x, 0),
            end=(x, height),
            stroke='#C0C0C0',
            stroke_width=1
        ))

    # Líneas horizontales
    for y in range(0, int(height) + 1, grid_size):
        grid_group.add(dwg.line(
            start=(0, y),
            end=(width, y),
            stroke='#C0C0C0',
            stroke_width=1
        ))

    dwg.add(grid_group)

def draw_guide_lines(dwg, width, guide_lines):
    """
    Dibuja líneas horizontales de guía en posiciones específicas.

    Args:
        dwg: SVG drawing object
        width: Ancho del canvas
        guide_lines: Lista de posiciones Y donde dibujar líneas (ej: [186, 236])
    """
    if not guide_lines:
        return

    # Crear grupo para las líneas de guía
    guide_group = dwg.g(id='guide_lines', opacity=0.8)

    for y in guide_lines:
        # Línea horizontal
        guide_group.add(dwg.line(
            start=(0, y),
            end=(width, y),
            stroke='#FF0000',  # Rojo para destacar
            stroke_width=1.5,
            stroke_dasharray='5,5'  # Línea punteada
        ))

        # Etiqueta con la posición Y
        guide_group.add(dwg.text(
            f'Y={y}',
            insert=(5, y - 3),
            font_size='10px',
            font_family='Arial, sans-serif',
            fill='#FF0000',
            font_weight='bold'
        ))

    dwg.add(guide_group)

def draw_debug_free_ranges(dwg, free_ranges, width):
    """
    Dibuja las franjas libres de redistribución en modo debug.

    Args:
        dwg: SVG drawing object
        free_ranges: Lista de tuplas (y_start, y_end) representando franjas libres
        width: Ancho del canvas
    """
    if not free_ranges:
        return

    # Color azul acero claro (light steel blue)
    light_steel_blue = '#B0C4DE'

    # Crear grupo para las franjas con baja opacidad para que no oculte el contenido
    ranges_group = dwg.g(id='debug_free_ranges', opacity=0.15)

    for i, (y_start, y_end) in enumerate(free_ranges):
        height = y_end - y_start

        # Rectángulo de franja
        ranges_group.add(dwg.rect(
            insert=(0, y_start),
            size=(width, height),
            fill=light_steel_blue,
            stroke='#4682B4',  # Steel blue más oscuro para el borde
            stroke_width=2,
            stroke_dasharray='5,5'
        ))

        # Fondo blanco semi-transparente para el texto
        text_bg_width = 250
        text_bg_height = 20
        ranges_group.add(dwg.rect(
            insert=(8, y_start + 2),
            size=(text_bg_width, text_bg_height),
            fill='white',
            opacity=0.8,
            rx=3,
            ry=3
        ))

        # Etiqueta con información de la franja
        ranges_group.add(dwg.text(
            f'Franja {i+1}: Y[{y_start:.0f}-{y_end:.0f}] h={height:.0f}px',
            insert=(10, y_start + 16),
            font_size='12px',
            font_family='Arial, sans-serif',
            fill='#2F4F4F',  # Dark slate gray para mejor contraste
            font_weight='bold'
        ))

    dwg.add(ranges_group)

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

def generate_diagram(json_file, debug=False, visualdebug=False, exportpng=False, guide_lines=None, dump_iterations=False, output_file=None, layout_algorithm='auto', visualize_growth=False, color_connections=False, **centrality_kwargs):
    # Configurar logging si debug está activo
    if debug:
        logging.basicConfig(
            level=logging.DEBUG,
            format='[%(levelname)s] %(name)s: %(message)s',
            force=True
        )
        logger.setLevel(logging.DEBUG)
        logger.debug("="*70)
        logger.debug("MODO DEBUG ACTIVADO")
        logger.debug("="*70)
    else:
        logging.basicConfig(level=logging.WARNING)
        logger.setLevel(logging.WARNING)

    if not os.path.exists(json_file):
        print(f"[ERROR] Archivo no encontrado: {json_file}")
        return False

    logger.debug(f"Leyendo archivo: {json_file}")

    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"[ERROR] Error al leer el JSON: {e}")
        return False

    # Determinar ruta de salida
    if output_file:
        # Usar la ruta proporcionada
        output_svg = output_file
        # Crear directorio de salida si no existe
        output_dir = os.path.dirname(output_svg)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
            logger.debug(f"Directorio creado: {output_dir}")
    else:
        # Comportamiento por defecto: generar en el directorio actual
        base_name = os.path.splitext(os.path.basename(json_file))[0]
        output_svg = f"{base_name}.svg"

    logger.debug(f"Elementos: {len(data.get('elements', []))}")
    logger.debug(f"Conexiones: {len(data.get('connections', []))}")

    # Leer canvas del JSON o usar valores por defecto
    canvas = data.get('canvas', {})
    canvas_width = canvas.get('width', WIDTH)
    canvas_height = canvas.get('height', HEIGHT)

    all_elements = data.get('elements', [])
    all_connections = data.get('connections', [])

    # === NUEVO FLUJO: Layout + AutoLayoutOptimizer v2.1 ===

    # 1. Crear Layout inmutable
    initial_layout = Layout(
        elements=all_elements,
        connections=all_connections,
        canvas={'width': canvas_width, 'height': canvas_height}
    )

    # Agregar nombre del diagrama para visualizador
    diagram_name = os.path.splitext(os.path.basename(json_file))[0]
    initial_layout._diagram_name = diagram_name

    # 2. Instanciar optimizador
    if layout_algorithm == 'laf':
        from AlmaGag.layout.laf_optimizer import LAFOptimizer
        from AlmaGag.layout.sizing import SizingCalculator
        from AlmaGag.layout.geometry import GeometryCalculator
        from AlmaGag.layout.collision import CollisionDetector
        from AlmaGag.layout.auto_positioner import AutoLayoutPositioner
        from AlmaGag.layout.container_calculator import ContainerCalculator
        from AlmaGag.routing.router_manager import ConnectionRouterManager
        # LabelPositionOptimizer ya está importado globalmente en línea 9
        from AlmaGag.layout.graph_analysis import GraphAnalyzer

        # Crear componentes necesarios para LAF
        sizing = SizingCalculator()
        geometry = GeometryCalculator(sizing)
        collision_detector = CollisionDetector(geometry)
        graph_analyzer = GraphAnalyzer()
        positioner = AutoLayoutPositioner(sizing, graph_analyzer, visualdebug=visualdebug)
        container_calculator = ContainerCalculator(sizing, geometry)
        router_manager = ConnectionRouterManager()
        label_optimizer = LabelPositionOptimizer(geometry, canvas_width, canvas_height, debug=debug)

        optimizer = LAFOptimizer(
            positioner=positioner,
            container_calculator=container_calculator,
            router_manager=router_manager,
            collision_detector=collision_detector,
            label_optimizer=label_optimizer,
            geometry=geometry,
            visualize_growth=visualize_growth,
            debug=debug,
            **centrality_kwargs
        )
        logger.debug(f"LAFOptimizer instanciado (debug={debug})")
    else:
        optimizer = AutoLayoutOptimizer(verbose=debug, visualdebug=visualdebug)
        logger.debug(f"AutoLayoutOptimizer instanciado (verbose={debug}, visualdebug={visualdebug})")

    # 3. Optimizar (retorna NUEVO layout)
    #    NOTA: optimize() ahora maneja auto-layout para coordenadas faltantes (SDJF v2.0)

    # Generar nombre de CSV con timestamp para evitar sobreescritura
    csv_file = None
    if debug:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_file = f"debug/layout_evolution_{timestamp}.csv"
        logger.debug(f"[CSV] Archivo de evolución: {csv_file}")

    if layout_algorithm == 'laf':
        # LAF optimizer solo toma el layout
        optimized_layout = optimizer.optimize(initial_layout)
    else:
        # AutoLayoutOptimizer toma parámetros adicionales
        optimized_layout = optimizer.optimize(
            initial_layout,
            max_iterations=10,
            dump_iterations=dump_iterations,
            input_file=json_file
        )

    # Mostrar info de estructura (después de auto-layout)
    num_levels = len(set(optimized_layout.levels.values()))
    num_groups = len(optimized_layout.groups)
    high_priority = sum(1 for priority in optimized_layout.priorities.values() if priority == 0)
    normal_priority = sum(1 for priority in optimized_layout.priorities.values() if priority == 1)
    low_priority = sum(1 for priority in optimized_layout.priorities.values() if priority == 2)

    # Mostrar resultados
    remaining = optimized_layout._collision_count if optimized_layout._collision_count is not None else 0

    if remaining > 0:
        print(f"[WARN] AutoLayout v2.1: {remaining} colisiones detectadas")
    else:
        print(f"[OK] AutoLayout v2.1: 0 colisiones detectadas")

    print(f"     - {num_levels} niveles, {num_groups} grupo(s)")
    print(f"     - Prioridades: {high_priority} high, {normal_priority} normal, {low_priority} low")

    # 5. Obtener canvas final (puede haber sido expandido)
    final_canvas = optimized_layout.canvas
    if final_canvas['width'] > canvas_width or final_canvas['height'] > canvas_height:
        canvas_width = final_canvas['width']
        canvas_height = final_canvas['height']
        print(f"     - Canvas expandido a {canvas_width}x{canvas_height}")

    # 6. Crear SVG
    dwg = svgwrite.Drawing(output_svg, size=(canvas_width, canvas_height))
    dwg.viewbox(0, 0, canvas_width, canvas_height)

    # Agregar franja de debug PRIMERO (debe estar debajo de todo)
    if visualdebug:
        add_debug_badge(dwg, canvas_width, canvas_height)
        logger.debug("Badge de debug agregado")

    # Dibujar rejilla de guía (solo en modo visualdebug)
    if visualdebug:
        draw_grid(dwg, canvas_width, canvas_height, grid_size=20)
        logger.debug("Rejilla de guía dibujada (20px)")

    # Dibujar líneas de guía horizontales (si se especifican)
    if guide_lines:
        draw_guide_lines(dwg, canvas_width, guide_lines)
        logger.debug(f"Líneas de guía dibujadas en Y={guide_lines}")

    # Dibujar franjas libres de redistribución (modo visualdebug)
    if visualdebug:
        if hasattr(optimized_layout, 'debug_free_ranges') and optimized_layout.debug_free_ranges:
            draw_debug_free_ranges(dwg, optimized_layout.debug_free_ranges, canvas_width)
            logger.debug(f"Franjas libres dibujadas: {len(optimized_layout.debug_free_ranges)}")

    # Obtener resultados optimizados
    elements = optimized_layout.elements
    connections = optimized_layout.connections  # Conexiones con rutas optimizadas

    # Configurar markers para flechas direccionales (después de obtener connections)
    marker_result = setup_arrow_markers(dwg, connections, color_connections)
    if color_connections and isinstance(marker_result, tuple):
        markers, per_conn_styles = marker_result
    else:
        markers = marker_result
        per_conn_styles = None
    label_positions = optimized_layout.label_positions
    conn_labels = optimized_layout.connection_labels
    elements_by_id = {e['id']: e for e in elements}

    # Separar contenedores de elementos normales
    containers = [e for e in elements if 'contains' in e]
    normal_elements = [e for e in elements if 'contains' not in e]

    # Dump del layout en modo debug
    if debug and csv_file:
        dump_layout_table(optimized_layout, elements_by_id, containers, phase="OPTIMIZED", csv_file=csv_file)

    # === Renderizado en orden correcto ===
    # 0. Dibujar todos los contenedores (solo fondo, sin ícono ni labels)
    for container in containers:
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"[RECT] {container['id']}: ({container.get('x', 0):.1f}, {container.get('y', 0):.1f}) {container.get('width', 0):.1f}x{container.get('height', 0):.1f}")
        draw_container(dwg, container, elements_by_id, draw_label=False, layout_algorithm=layout_algorithm, draw_icon=False)

    # 1. Dibujar todos los íconos normales (sin etiquetas)
    logger.debug(f"\n[DIBUJAR ELEMENTOS] Total: {len(normal_elements)}")
    for elem in normal_elements:
        if 'x' in elem and 'y' in elem:
            logger.debug(f"  {elem['id']}: ({elem['x']:.1f}, {elem['y']:.1f}) "
                       f"size({elem.get('width', ICON_WIDTH):.1f} x {elem.get('height', ICON_HEIGHT):.1f})")
        draw_icon_shape(dwg, elem)

    # 1.5. Dibujar íconos de contenedores (encima de elementos contenidos)
    for container in containers:
        # Dibujar solo el ícono del contenedor, sin rectángulo ni label
        # Esto se hace DESPUÉS de los elementos contenidos para que no quede tapado

        container_id = container['id']

        # IMPORTANTE: Usar las mismas coordenadas que draw_container usa para el rectángulo
        # Si el contenedor tiene '_is_container_calculated', usar sus coordenadas directamente
        # Si no, calcular bounds (igual que draw_container)
        if '_is_container_calculated' in container and all(k in container for k in ['x', 'y']):
            container_x = container['x']
            container_y = container['y']
        else:
            # Calcular bounds (igual que draw_container)
            from AlmaGag.draw.container import calculate_container_bounds
            bounds = calculate_container_bounds(container, elements_by_id)
            container_x = bounds['x']
            container_y = bounds['y']

        # IMPORTANTE: draw_building agrega su propio padding interno de ICON_HEIGHT * 0.2 (10px)
        # Por lo tanto, pasamos las coordenadas del contenedor directamente
        # para que el ícono quede en (container_x + padding, container_y + padding) después
        # de que draw_building agregue su padding
        icon_x = container_x
        icon_y = container_y

        icon_type = container.get('type', 'building')
        color = container.get('color', 'lightgray')

        # DEBUG: Mostrar coordenadas
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"[ICON] {container_id}: container=({container_x:.1f}, {container_y:.1f}), icon=({icon_x:.1f}, {icon_y:.1f})")

        # Dibujar ícono directamente
        try:
            import importlib
            icon_module = importlib.import_module(f'AlmaGag.draw.{icon_type}')
            draw_func = getattr(icon_module, f'draw_{icon_type}')
            icon_elem_id = f"{container_id}_icon"
            draw_func(dwg, icon_x, icon_y, color, icon_elem_id)
        except (ImportError, AttributeError) as e:
            # Fallback: dibujar rectángulo simple
            from AlmaGag.draw.icons import create_gradient
            gradient_id = create_gradient(dwg, container_id, color)
            icon_size = min(ICON_WIDTH, ICON_HEIGHT) * 0.6
            dwg.add(dwg.rect(
                insert=(icon_x, icon_y),
                size=(icon_size, icon_size),
                fill=gradient_id,
                stroke='black',
                opacity=1.0
            ))

    # 2. Dibujar todas las conexiones optimizadas (sin etiquetas)
    conn_centers = {}
    for i, conn in enumerate(connections):  # Usar connections optimizadas, no all_connections
        if per_conn_styles and i < len(per_conn_styles):
            conn_markers = per_conn_styles[i]['markers']
            conn_color = per_conn_styles[i]['color']
        else:
            conn_markers = markers
            conn_color = 'black'
        center = draw_connection_line(dwg, elements_by_id, conn, conn_markers, stroke_color=conn_color)
        key = f"{conn['from']}->{conn['to']}"
        conn_centers[key] = center

    # 2.5. Optimizar posiciones de etiquetas (v3.0 - Label Collision Optimizer)
    logger.debug("\n" + "="*70)
    logger.debug("INICIANDO OPTIMIZACION DE ETIQUETAS")
    logger.debug("="*70)

    label_optimizer = LabelPositionOptimizer(
        optimizer.geometry,  # Reusar GeometryCalculator del optimizador
        canvas_width,
        canvas_height,
        debug=debug
    )

    # Recolectar todas las etiquetas a optimizar
    labels_to_optimize = []

    # Etiquetas de conexiones optimizadas
    for conn in connections:  # Usar connections optimizadas
        if conn.get('label'):
            key = f"{conn['from']}->{conn['to']}"
            center = conn_centers.get(key)
            if center:
                labels_to_optimize.append(Label(
                    id=key,
                    text=conn['label'],
                    anchor_x=center[0],
                    anchor_y=center[1],
                    font_size=12,
                    priority=1,  # Normal
                    category="connection"
                ))

    # Etiquetas de elementos normales (incluye elementos dentro de contenedores)
    for elem in elements:
        # Solo agregar elementos que NO son contenedores
        if 'contains' not in elem and elem.get('label') and 'x' in elem and 'y' in elem:
            elem_id = elem['id']

            # IMPORTANTE: Si el elemento tiene posición precalculada (por ContainerGrower/Sugiyama),
            # usar esa posición y marcar como fixed para que LabelOptimizer no la mueva
            if elem_id in label_positions:
                label_x, label_y, anchor, baseline = label_positions[elem_id]
                is_fixed = True  # Posición ya calculada por ContainerGrower
            else:
                # Calcular posición automática (elementos NO contenidos)
                elem_width = elem.get('width', ICON_WIDTH)
                elem_height = elem.get('height', ICON_HEIGHT)
                label_x = elem['x'] + elem_width / 2
                label_y = elem['y'] + elem_height / 2
                is_fixed = False  # Puede ser reposicionada por LabelOptimizer

            labels_to_optimize.append(Label(
                id=elem_id,
                text=elem['label'],
                anchor_x=label_x,
                anchor_y=label_y,
                font_size=14,
                priority=2,  # Baja (pueden moverse más)
                category="element",
                fixed=is_fixed
            ))

    # Etiquetas de contenedores - NO optimizar, posición fija
    # (Las dibujamos directamente más adelante)

    # Optimizar todas las posiciones de etiquetas
    logger.debug(f"\nTotal de etiquetas a optimizar: {len(labels_to_optimize)}")
    logger.debug(f"  - Conexiones: {sum(1 for l in labels_to_optimize if l.category == 'connection')}")
    logger.debug(f"  - Contenedores: {sum(1 for l in labels_to_optimize if l.category == 'container')}")
    logger.debug(f"  - Elementos: {sum(1 for l in labels_to_optimize if l.category == 'element')}")

    # CRÍTICO: Pasar elements optimizados (con coordenadas), NO all_elements (JSON crudo)
    # v3.2: Pasar también connections para detectar colisiones entre etiquetas y líneas
    optimized_label_positions = label_optimizer.optimize_labels(labels_to_optimize, elements, connections)

    logger.debug(f"\nPosiciones optimizadas generadas: {len(optimized_label_positions)}")
    logger.debug("="*70 + "\n")

    # 3. Dibujar todas las etiquetas de elementos normales con posiciones optimizadas
    for elem in elements:
        if 'contains' not in elem and elem.get('label'):
            optimized_pos = optimized_label_positions.get(elem['id'])
            if optimized_pos:
                # Usar posición optimizada, pero manejar saltos de línea
                label_text = elem['label']
                lines = label_text.split('\n')

                for i, line in enumerate(lines):
                    dwg.add(dwg.text(
                        line,
                        insert=(optimized_pos.x, optimized_pos.y + (i * 18)),
                        text_anchor=optimized_pos.anchor,
                        font_size="14px",
                        font_family="Arial, sans-serif",
                        fill="black"
                    ))
            else:
                # Fallback: usar posición antigua del layout
                position_info = label_positions.get(elem['id'])
                draw_icon_label(dwg, elem, position_info)

    # Dibujar etiquetas de conexiones optimizadas con posiciones optimizadas
    for conn in connections:  # Usar connections optimizadas
        if conn.get('label'):
            key = f"{conn['from']}->{conn['to']}"
            optimized_pos = optimized_label_positions.get(key)
            if optimized_pos:
                # Usar posición optimizada
                dwg.add(dwg.text(
                    conn['label'],
                    insert=(optimized_pos.x, optimized_pos.y),
                    text_anchor=optimized_pos.anchor,
                    font_size="12px",
                    font_family="Arial, sans-serif",
                    fill="gray"
                ))
            else:
                # Fallback a método antiguo
                center = conn_centers.get(key)
                if center:
                    draw_connection_label(dwg, conn, center)

    # Dibujar etiquetas de contenedores en posición fija (NO optimizadas)
    for container in containers:
        if container.get('label'):
            # Calcular posición fija: a la derecha del ícono, dentro del contenedor
            if 'x' in container and 'y' in container:
                # LOG: Geometría del contenedor (COORDENADAS LOCALES)
                logger.debug(f"\n{'='*70}")
                logger.debug(f"[GEOMETRIA LOCAL CONTENEDOR] {container['id']}")
                logger.debug(f"{'='*70}")
                if 'width' in container and 'height' in container:
                    logger.debug(f"Contenedor global: ({container['x']:.1f}, {container['y']:.1f}) "
                               f"size({container['width']:.1f} x {container['height']:.1f})")
                else:
                    logger.debug(f"Contenedor global: ({container['x']:.1f}, {container['y']:.1f}) "
                               f"size(pending - Phase 4 not implemented)")
                logger.debug(f"\nElementos en coordenadas LOCALES (relativas a esquina superior izquierda):")

                container_x = container['x']
                container_y = container['y']

                # 1. Ícono del contenedor (siempre en posición fija)
                # El icono está pegado al borde superior (sin padding top)
                icon_local_x = 10  # Padding left
                icon_local_y = 0   # Sin padding top - pegado arriba
                logger.debug(f"\n  1) ICONO CONTENEDOR:")
                logger.debug(f"     Local: ({icon_local_x}, {icon_local_y})")
                logger.debug(f"     Size: {ICON_WIDTH} x {ICON_HEIGHT}")
                logger.debug(f"     Global: ({container_x + icon_local_x:.1f}, {container_y + icon_local_y:.1f})")

                # 2. Etiqueta del contenedor
                label_local_x = 10 + ICON_WIDTH + 10
                label_local_y = 16  # baseline primera línea (alineado con top del ícono)
                lines = container['label'].split('\n')
                label_width = max(len(line) for line in lines) * 8
                label_height = len(lines) * TEXT_LINE_HEIGHT
                logger.debug(f"\n  2) ETIQUETA CONTENEDOR: '{container['label'].replace(chr(10), ' / ')}'")
                logger.debug(f"     Local: ({label_local_x}, {label_local_y}) [baseline primera línea]")
                logger.debug(f"     Size: ~{label_width} x {label_height} [{len(lines)} líneas]")
                logger.debug(f"     Global: ({container_x + label_local_x:.1f}, {container_y + label_local_y:.1f})")

                # 3. Elementos internos del contenedor
                contains = container.get('contains', [])
                if contains:
                    logger.debug(f"\n  3) ELEMENTOS INTERNOS: {len(contains)}")
                    for idx, ref in enumerate(contains, 1):
                        ref_id = ref['id'] if isinstance(ref, dict) else ref
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

                            # 4. Etiqueta del elemento interno (si existe)
                            if elem.get('label'):
                                elem_label = elem['label']
                                # La etiqueta del elemento se dibuja relativa al elemento
                                # Típicamente debajo del elemento
                                elem_label_y_offset = elem_height + 15  # Debajo del elemento
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
                        text_anchor="start",  # Alineado a la izquierda
                        font_size="16px",
                        font_family="Arial, sans-serif",
                        font_weight="bold",
                        fill="black"
                    ))

    # ============================================================================
    # DEBUG: Dibujar niveles topológicos de elementos primarios
    # ============================================================================
    if visualdebug:
        logger.debug("\n[DEBUG] Dibujando niveles topológicos de elementos primarios")

        # Identificar elementos contenidos
        contained_ids = set()
        for container in containers:
            for item in container.get('contains', []):
                elem_id = item['id'] if isinstance(item, dict) else item
                contained_ids.add(elem_id)

        # Identificar elementos primarios (no contenidos)
        # Incluir TANTO elementos simples COMO contenedores primarios
        primary_elements = []
        for elem in elements:
            if elem['id'] not in contained_ids and 'x' in elem and 'y' in elem:
                primary_elements.append(elem)

        # Agregar contenedores primarios (no están en la lista de elements)
        for container in containers:
            if container['id'] not in contained_ids and 'x' in container and 'y' in container:
                primary_elements.append(container)

        logger.debug(f"  Total elementos primarios: {len(primary_elements)}")

        # Dibujar cuadrado rojo punteado y nivel para cada elemento primario
        for elem in primary_elements:
            elem_id = elem['id']
            elem_x = elem['x']
            elem_y = elem['y']
            elem_width = elem.get('width', ICON_WIDTH)
            elem_height = elem.get('height', ICON_HEIGHT)

            # Obtener nivel topológico
            level = optimized_layout.levels.get(elem_id, 0)

            # Expandir el rectángulo para incluir la etiqueta si existe
            box_x = elem_x
            box_y = elem_y
            box_width = elem_width
            box_height = elem_height

            if elem.get('label'):
                lines = elem['label'].split('\n')
                label_height = len(lines) * 18
                box_height = elem_height + 15 + label_height  # 15px margen + altura de etiquetas

            # Dibujar cuadrado rojo punteado
            dwg.add(dwg.rect(
                insert=(box_x - 5, box_y - 5),  # Margen de 5px
                size=(box_width + 10, box_height + 10),
                fill='none',
                stroke='red',
                stroke_width=2,
                stroke_dasharray='5,5',
                opacity=0.7
            ))

            # Dibujar número de nivel en esquina superior izquierda
            dwg.add(dwg.text(
                str(level),
                insert=(box_x - 5 + 5, box_y - 5 + 15),  # 5px padding interno
                text_anchor="start",
                font_size="14px",
                font_family="Arial, sans-serif",
                font_weight="bold",
                fill="red"
            ))

            logger.debug(f"    {elem_id}: nivel={level}, pos=({elem_x:.0f}, {elem_y:.0f}), size=({elem_width:.0f}x{elem_height:.0f})")

    dwg.save()
    print(f"[OK] Diagrama generado exitosamente: {output_svg}")

    # Convertir automáticamente a PNG si se especifica la opción
    if exportpng:
        convert_svg_to_png(output_svg)

    return True
