import os, json, svgwrite, logging
from AlmaGag.config import WIDTH, HEIGHT, ICON_WIDTH, ICON_HEIGHT
from AlmaGag.layout import Layout, AutoLayoutOptimizer
from AlmaGag.layout.label_optimizer import LabelPositionOptimizer, Label
from AlmaGag.draw.icons import draw_icon_shape, draw_icon_label
from AlmaGag.draw.connections import draw_connection_line, draw_connection_label
from AlmaGag.draw.container import draw_container
from AlmaGag.debug import add_debug_badge, convert_svg_to_png

# Logger global para AlmaGag
logger = logging.getLogger('AlmaGag')

def dump_layout_table(optimized_layout, elements_by_id, containers):
    """
    Genera una tabla con información detallada de todos los elementos del layout.

    Args:
        optimized_layout: Layout optimizado con información de niveles y grupos
        elements_by_id: Diccionario de elementos por ID
        containers: Lista de contenedores
    """
    logger.debug("\n" + "="*150)
    logger.debug("DUMP DEL LAYOUT - TABLA DE ELEMENTOS")
    logger.debug("="*150)

    # Header de la tabla
    header = f"{'Nivel':<8}{'Grupo':<8}{'Tipo':<15}{'ID':<30}{'Referencial':<30}{'X Local':<12}{'Y Local':<12}{'X Global':<12}{'Y Global':<12}{'Ancho':<12}{'Alto':<12}"
    logger.debug(header)
    logger.debug("-" * 150)

    rows = []

    # Función auxiliar para encontrar el grupo de un elemento
    def find_group(elem_id, groups):
        for idx, group_list in enumerate(groups, 1):
            if elem_id in group_list:
                return idx
        return 'n/a'

    # Procesar todos los elementos
    for element in optimized_layout.elements:
        elem_id = element['id']
        level = optimized_layout.levels.get(elem_id, 'n/a')
        group = find_group(elem_id, optimized_layout.groups)

        # Determinar si es contenedor
        is_container = 'contains' in element

        if is_container:
            # CONTENEDOR
            x_global = element.get('x', 'n/a')
            y_global = element.get('y', 'n/a')
            width = element.get('width', 'n/a')
            height = element.get('height', 'n/a')

            rows.append({
                'nivel': level,
                'grupo': group,
                'tipo': 'Contenedor',
                'id': f"{elem_id}.Cnt",
                'referencial': 'origen',
                'x_local': 'n/a',
                'y_local': 'n/a',
                'x_global': x_global,
                'y_global': y_global,
                'width': width,
                'height': height
            })

            # ÍCONO DEL CONTENEDOR
            icon_x_local = 10
            icon_y_local = 10
            icon_x_global = x_global + icon_x_local if x_global != 'n/a' else 'n/a'
            icon_y_global = y_global + icon_y_local if y_global != 'n/a' else 'n/a'

            rows.append({
                'nivel': level,
                'grupo': group,
                'tipo': 'Ícono',
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
                label_x_local = 10 + ICON_WIDTH + 10
                label_y_local = 5 + 16
                label_x_global = x_global + label_x_local if x_global != 'n/a' else 'n/a'
                label_y_global = y_global + label_y_local if y_global != 'n/a' else 'n/a'

                lines = element['label'].split('\n')
                label_width = max(len(line) for line in lines) * 8
                label_height = len(lines) * 18

                rows.append({
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
            for ref in element.get('contains', []):
                ref_id = ref['id'] if isinstance(ref, dict) else ref
                contained_elem = elements_by_id.get(ref_id)

                if contained_elem:
                    # Calcular posición local
                    container_x = element.get('x', 0)
                    container_y = element.get('y', 0)
                    elem_x_global = contained_elem.get('x', 'n/a')
                    elem_y_global = contained_elem.get('y', 'n/a')

                    if elem_x_global != 'n/a' and elem_y_global != 'n/a':
                        elem_x_local = elem_x_global - container_x
                        elem_y_local = elem_y_global - container_y
                    else:
                        elem_x_local = 'n/a'
                        elem_y_local = 'n/a'

                    elem_width = contained_elem.get('width', ICON_WIDTH)
                    elem_height = contained_elem.get('height', ICON_HEIGHT)

                    # ÍCONO DEL ELEMENTO CONTENIDO
                    rows.append({
                        'nivel': level,
                        'grupo': group,
                        'tipo': 'Ícono',
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
                        label_x_local = elem_x_local + elem_width / 2 if elem_x_local != 'n/a' else 'n/a'
                        label_y_local = elem_y_local + elem_height + 15 if elem_y_local != 'n/a' else 'n/a'
                        label_x_global = elem_x_global + elem_width / 2 if elem_x_global != 'n/a' else 'n/a'
                        label_y_global = elem_y_global + elem_height + 15 if elem_y_global != 'n/a' else 'n/a'

                        label_text = contained_elem['label']
                        label_width_est = len(label_text) * 8
                        label_height_est = 18

                        rows.append({
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
            x_global = element.get('x', 'n/a')
            y_global = element.get('y', 'n/a')
            width = element.get('width', ICON_WIDTH)
            height = element.get('height', ICON_HEIGHT)

            # ÍCONO
            rows.append({
                'nivel': level,
                'grupo': group,
                'tipo': 'Ícono',
                'id': elem_id,
                'referencial': 'origen',
                'x_local': 'n/a',
                'y_local': 'n/a',
                'x_global': x_global,
                'y_global': y_global,
                'width': width,
                'height': height
            })

            # ETIQUETA
            if element.get('label'):
                label_x_global = x_global + width / 2 if x_global != 'n/a' else 'n/a'
                label_y_global = y_global + height + 15 if y_global != 'n/a' else 'n/a'

                label_text = element['label']
                lines = label_text.split('\n')
                label_width_est = max(len(line) for line in lines) * 8
                label_height_est = len(lines) * 18

                rows.append({
                    'nivel': level,
                    'grupo': group,
                    'tipo': 'Etiqueta',
                    'id': f"{elem_id}.Lbl",
                    'referencial': elem_id,
                    'x_local': 'n/a',
                    'y_local': 'n/a',
                    'x_global': label_x_global,
                    'y_global': label_y_global,
                    'width': label_width_est,
                    'height': label_height_est
                })

    # Imprimir todas las filas
    for row in rows:
        nivel_str = str(row['nivel']) if row['nivel'] != 'n/a' else 'n/a'
        grupo_str = str(row['grupo']) if row['grupo'] != 'n/a' else 'n/a'
        x_local_str = f"{row['x_local']:.1f}" if isinstance(row['x_local'], (int, float)) else str(row['x_local'])
        y_local_str = f"{row['y_local']:.1f}" if isinstance(row['y_local'], (int, float)) else str(row['y_local'])
        x_global_str = f"{row['x_global']:.1f}" if isinstance(row['x_global'], (int, float)) else str(row['x_global'])
        y_global_str = f"{row['y_global']:.1f}" if isinstance(row['y_global'], (int, float)) else str(row['y_global'])
        width_str = f"{row['width']:.1f}" if isinstance(row['width'], (int, float)) else str(row['width'])
        height_str = f"{row['height']:.1f}" if isinstance(row['height'], (int, float)) else str(row['height'])

        line = f"{nivel_str:<8}{grupo_str:<8}{row['tipo']:<15}{row['id']:<30}{row['referencial']:<30}{x_local_str:<12}{y_local_str:<12}{x_global_str:<12}{y_global_str:<12}{width_str:<12}{height_str:<12}"
        logger.debug(line)

    logger.debug("="*150 + "\n")

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

def setup_arrow_markers(dwg):
    """
    Crea los markers SVG para flechas direccionales.

    Markers:
    - arrow-end: flecha para el final de la línea (forward)
    - arrow-start: flecha para el inicio de la línea (backward)

    Retorna un dict con los markers creados.
    """
    # Marker para flecha al final (forward)
    marker_end = dwg.marker(
        id='arrow-end',
        insert=(10, 5),
        size=(10, 10),
        orient='auto'
    )
    marker_end.add(dwg.path(
        d='M 0 0 L 10 5 L 0 10 z',
        fill='black'
    ))
    dwg.defs.add(marker_end)

    # Marker para flecha al inicio (backward)
    marker_start = dwg.marker(
        id='arrow-start',
        insert=(0, 5),
        size=(10, 10),
        orient='auto'
    )
    marker_start.add(dwg.path(
        d='M 10 0 L 0 5 L 10 10 z',
        fill='black'
    ))
    dwg.defs.add(marker_start)

    return {
        'forward': marker_end.get_funciri(),
        'backward': marker_start.get_funciri(),
        'bidirectional': (marker_start.get_funciri(), marker_end.get_funciri())
    }

def generate_diagram(json_file, debug=False, guide_lines=None):
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
        return

    logger.debug(f"Leyendo archivo: {json_file}")

    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"[ERROR] Error al leer el JSON: {e}")
        return

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

    # 2. Instanciar optimizador
    optimizer = AutoLayoutOptimizer(verbose=debug)
    logger.debug(f"AutoLayoutOptimizer instanciado (verbose={debug})")

    # 3. Optimizar (retorna NUEVO layout)
    #    NOTA: optimize() ahora maneja auto-layout para coordenadas faltantes (SDJF v2.0)
    optimized_layout = optimizer.optimize(initial_layout, max_iterations=10)

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

    # Dibujar rejilla de guía (solo en modo debug)
    if debug:
        draw_grid(dwg, canvas_width, canvas_height, grid_size=20)
        logger.debug("Rejilla de guía dibujada (20px)")

        # Dibujar líneas de guía horizontales (si se especifican)
        if guide_lines:
            draw_guide_lines(dwg, canvas_width, guide_lines)
            logger.debug(f"Líneas de guía dibujadas en Y={guide_lines}")

    # Configurar markers para flechas direccionales
    markers = setup_arrow_markers(dwg)

    # Agregar badge de debug solo en modo debug (fecha de generación y versión GAG)
    if debug:
        add_debug_badge(dwg, canvas_width, canvas_height)
        logger.debug("Badge de debug agregado")

    # Obtener resultados optimizados
    elements = optimized_layout.elements
    connections = optimized_layout.connections  # Conexiones con rutas optimizadas
    label_positions = optimized_layout.label_positions
    conn_labels = optimized_layout.connection_labels
    elements_by_id = {e['id']: e for e in elements}

    # Separar contenedores de elementos normales
    containers = [e for e in elements if 'contains' in e]
    normal_elements = [e for e in elements if 'contains' not in e]

    # Dump del layout en modo debug
    if debug:
        dump_layout_table(optimized_layout, elements_by_id, containers)

    # === Renderizado en orden correcto ===
    # 0. Dibujar todos los contenedores (fondo, sin labels - se dibujan después optimizadas)
    for container in containers:
        draw_container(dwg, container, elements_by_id, draw_label=False)

    # 1. Dibujar todos los íconos normales (sin etiquetas)
    logger.debug(f"\n[DIBUJAR ELEMENTOS] Total: {len(normal_elements)}")
    for elem in normal_elements:
        if 'x' in elem and 'y' in elem:
            logger.debug(f"  {elem['id']}: ({elem['x']:.1f}, {elem['y']:.1f}) "
                       f"size({elem.get('width', ICON_WIDTH):.1f} x {elem.get('height', ICON_HEIGHT):.1f})")
        draw_icon_shape(dwg, elem)

    # 2. Dibujar todas las conexiones optimizadas (sin etiquetas)
    conn_centers = {}
    for conn in connections:  # Usar connections optimizadas, no all_connections
        center = draw_connection_line(dwg, elements_by_id, conn, markers)
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
            elem_width = elem.get('width', ICON_WIDTH)
            elem_height = elem.get('height', ICON_HEIGHT)
            labels_to_optimize.append(Label(
                id=elem['id'],
                text=elem['label'],
                anchor_x=elem['x'] + elem_width / 2,
                anchor_y=elem['y'] + elem_height / 2,
                font_size=14,
                priority=2,  # Baja (pueden moverse más)
                category="element"
            ))

    # Etiquetas de contenedores - NO optimizar, posición fija
    # (Las dibujamos directamente más adelante)

    # Optimizar todas las posiciones de etiquetas
    logger.debug(f"\nTotal de etiquetas a optimizar: {len(labels_to_optimize)}")
    logger.debug(f"  - Conexiones: {sum(1 for l in labels_to_optimize if l.category == 'connection')}")
    logger.debug(f"  - Contenedores: {sum(1 for l in labels_to_optimize if l.category == 'container')}")
    logger.debug(f"  - Elementos: {sum(1 for l in labels_to_optimize if l.category == 'element')}")

    # CRÍTICO: Pasar elements optimizados (con coordenadas), NO all_elements (JSON crudo)
    optimized_label_positions = label_optimizer.optimize_labels(labels_to_optimize, elements)

    logger.debug(f"\nPosiciones optimizadas generadas: {len(optimized_label_positions)}")
    logger.debug("="*70 + "\n")

    # 3. Dibujar todas las etiquetas de elementos normales con posiciones optimizadas
    for elem in elements:
        if 'contains' not in elem and elem.get('label'):
            optimized_pos = optimized_label_positions.get(elem['id'])
            if optimized_pos:
                # Usar posición optimizada
                dwg.add(dwg.text(
                    elem['label'],
                    insert=(optimized_pos.x, optimized_pos.y),
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
                logger.debug(f"Contenedor global: ({container['x']:.1f}, {container['y']:.1f}) "
                           f"size({container['width']:.1f} x {container['height']:.1f})")
                logger.debug(f"\nElementos en coordenadas LOCALES (relativas a esquina superior izquierda):")

                container_x = container['x']
                container_y = container['y']

                # 1. Ícono del contenedor (siempre en posición fija)
                icon_local_x = 10
                icon_local_y = 10
                logger.debug(f"\n  1) ICONO CONTENEDOR:")
                logger.debug(f"     Local: ({icon_local_x}, {icon_local_y})")
                logger.debug(f"     Size: {ICON_WIDTH} x {ICON_HEIGHT}")
                logger.debug(f"     Global: ({container_x + icon_local_x:.1f}, {container_y + icon_local_y:.1f})")

                # 2. Etiqueta del contenedor
                label_local_x = 10 + ICON_WIDTH + 10
                label_local_y = 10 + 16  # baseline primera línea (alineado con top del ícono)
                lines = container['label'].split('\n')
                label_width = max(len(line) for line in lines) * 8
                label_height = len(lines) * 18
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

    dwg.save()
    print(f"[OK] Diagrama generado exitosamente: {output_svg}")

    # Convertir automáticamente a PNG en carpeta debugs/
    convert_svg_to_png(output_svg)
