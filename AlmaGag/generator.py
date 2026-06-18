import os
import json
import csv
import logging

from datetime import datetime
from AlmaGag.config import (
    WIDTH, HEIGHT, ICON_WIDTH, ICON_HEIGHT,
    TEXT_LINE_HEIGHT, TEXT_CHAR_WIDTH,
    CONTAINER_ICON_X, CONTAINER_ICON_Y, CONTAINER_LABEL_X, CONTAINER_LABEL_Y,
    LABEL_OFFSET_VERTICAL, CONTAINER_PADDING
)
from AlmaGag.layout import Layout, AutoLayoutOptimizer
from AlmaGag.layout.label_optimizer import LabelPositionOptimizer, Label
from AlmaGag.debug import (
    add_debug_badge, convert_svg_to_png,
    dump_layout_table, _save_to_csv,
    draw_grid, draw_guide_lines, draw_debug_free_ranges,
)
from AlmaGag.utils import extract_item_id
from AlmaGag.renderer import (
    DrawingGroupProxy, setup_arrow_markers, draw_connections,
    draw_connection_labels, ndfn_wrap, render_containers,
    render_icons, render_container_icons, create_canvas,
    render_element_labels, render_container_labels,
    render_debug_levels, render_debug_ndfn,
)

# Logger global para AlmaGag
logger = logging.getLogger('AlmaGag')


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
        logging.basicConfig(level=logging.INFO)
        logger.setLevel(logging.INFO)

    if not os.path.exists(json_file):
        logger.error(f"Archivo no encontrado: {json_file}")
        return False

    logger.debug(f"Leyendo archivo: {json_file}")

    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError, OSError) as e:
        logger.error(f"Error al leer el JSON: {e}")
        return False

    # Extraer iconos SVG embebidos (formato .gag extendido)
    embedded_icons = data.get('icons', None)
    if embedded_icons:
        logger.info(f"{len(embedded_icons)} icono(s) SVG embebido(s) detectado(s)")

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

    # 2. Instanciar optimizador (WISH-ARCH-001 resuelto: factoría unificada).
    # Ambos optimizers heredan de LayoutOptimizer y son self-contained.
    from AlmaGag.layout.laf.optimizer import LAFOptimizer
    OPTIMIZERS = {
        'auto': AutoLayoutOptimizer,
        'laf':  LAFOptimizer,
    }
    optimizer_cls = OPTIMIZERS[layout_algorithm]
    optimizer_kwargs = {'verbose': debug, 'visualdebug': visualdebug}
    if layout_algorithm == 'laf':
        optimizer_kwargs['visualize_growth'] = visualize_growth
        optimizer_kwargs.update(centrality_kwargs)
    optimizer = optimizer_cls(**optimizer_kwargs)
    logger.debug(f"{optimizer_cls.__name__} instanciado ({optimizer_kwargs})")

    # 3. Optimizar (retorna NUEVO layout)
    #    NOTA: optimize() ahora maneja auto-layout para coordenadas faltantes (SDJF v2.0)

    # Generar nombre de CSV con timestamp para evitar sobreescritura
    csv_file = None
    if debug:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_file = f"debug/layout_evolution_{timestamp}.csv"
        logger.debug(f"[CSV] Archivo de evolución: {csv_file}")

    # Firma unificada: optimize(layout, max_iterations, dump_iterations, input_file).
    # LAF ignora los kwargs que no aplican a su pipeline.
    optimized_layout = optimizer.optimize(
        initial_layout,
        max_iterations=10,
        dump_iterations=dump_iterations,
        input_file=json_file,
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
        logger.warning(f"AutoLayout v2.1: {remaining} colisiones detectadas")
    else:
        logger.info(f"AutoLayout v2.1: 0 colisiones detectadas")

    logger.info(f"     - {num_levels} niveles, {num_groups} grupo(s)")
    logger.info(f"     - Prioridades: {high_priority} high, {normal_priority} normal, {low_priority} low")

    # 5. Obtener canvas final (puede haber sido expandido)
    final_canvas = optimized_layout.canvas
    if final_canvas['width'] > canvas_width or final_canvas['height'] > canvas_height:
        canvas_width = final_canvas['width']
        canvas_height = final_canvas['height']
        logger.info(f"     - Canvas expandido a {canvas_width}x{canvas_height}")

    # 6. Crear SVG con filtro text-glow
    dwg = create_canvas(output_svg, canvas_width, canvas_height)

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

    # === Construir etiquetas NdFn para debug ===
    ndfn_labels = {}
    if visualdebug and hasattr(optimized_layout, 'structure_info') and optimized_layout.structure_info:
        si = optimized_layout.structure_info
        ndpr_map = {eid: nid for eid, nid in si.all_node_ids.items()}
        container_children = {}
        for eid, elem in elements_by_id.items():
            if 'contains' in elem and elem['contains']:
                container_children[eid] = [
                    extract_item_id(item)
                    for item in elem['contains']
                ]
        aaa = 1
        for eid in si.primary_elements:
            nddp = ndpr_map.get(eid, 'NdDp00-000')
            node_type = si.primary_node_types.get(eid, 'Simple')
            is_container = eid in container_children
            is_virtual = node_type == 'Contenedor Virtual'
            ndfn_labels[eid] = f"NdFn.{aaa:03d}.{nddp}.0"
            aaa += 1
            if is_container:
                if not is_virtual:
                    ndfn_labels[f"{eid}__icon"] = f"NdFn.{aaa:03d}.{nddp}.1"
                    aaa += 1
                sub_idx = 2
                for child_id in container_children[eid]:
                    child_nddp = ndpr_map.get(child_id, 'NdDp00-000')
                    ndfn_labels[child_id] = f"NdFn.{aaa:03d}.{child_nddp}.{sub_idx}"
                    aaa += 1
                    sub_idx += 1
        logger.debug(f"[NdFn] {len(ndfn_labels)} etiquetas generadas para visualdebug")

    # === Renderizado en orden correcto ===
    # 0. Dibujar todos los contenedores (solo fondo, sin ícono ni labels)
    render_containers(dwg, containers, elements_by_id, ndfn_labels, layout_algorithm)

    # 1. Dibujar todos los íconos normales (sin etiquetas)
    render_icons(dwg, normal_elements, ndfn_labels, embedded_icons=embedded_icons)

    # 1.5. Dibujar íconos de contenedores (encima de elementos contenidos)
    render_container_icons(dwg, containers, elements_by_id, ndfn_labels, embedded_icons=embedded_icons)

    # 2. Dibujar todas las conexiones optimizadas (sin etiquetas)
    conn_centers = draw_connections(dwg, connections, elements_by_id, markers, per_conn_styles, ndfn_labels)

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

    # Identificar elementos contenidos (sus etiquetas ya fueron posicionadas
    # por ContainerGrower con detección de colisiones interna)
    contained_element_ids = set()
    for container in containers:
        for item in container.get('contains', []):
            cid = extract_item_id(item)
            contained_element_ids.add(cid)

    # Etiquetas de elementos normales (excluye contenidos — ya posicionados por ContainerGrower)
    for elem in elements:
        # Solo agregar elementos que NO son contenedores NI están contenidos
        if 'contains' not in elem and elem['id'] not in contained_element_ids and elem.get('label') and 'x' in elem and 'y' in elem:
            elem_id = elem['id']
            elem_width = elem.get('width', ICON_WIDTH)
            elem_height = elem.get('height', ICON_HEIGHT)
            elem_cx = elem['x'] + elem_width / 2
            elem_cy = elem['y'] + elem_height / 2

            if elem_id in label_positions:
                # Posición pre-calculada por ContainerGrower: usar como anchor
                # pero permitir que el optimizador la reposicione si hay colisión
                label_x, label_y, anchor, baseline = label_positions[elem_id]
            else:
                # Elementos sin posición pre-calculada: centro del ícono
                label_x = elem_cx
                label_y = elem_cy

            labels_to_optimize.append(Label(
                id=elem_id,
                text=elem['label'],
                anchor_x=label_x,
                anchor_y=label_y,
                font_size=14,
                priority=2,  # Baja (pueden moverse más)
                category="element",
                fixed=False,
                element_center_x=elem_cx,
                element_center_y=elem_cy
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
    render_element_labels(dwg, elements, optimized_label_positions, label_positions)

    # Dibujar etiquetas de conexiones optimizadas con posiciones optimizadas
    draw_connection_labels(dwg, connections, conn_centers, optimized_label_positions)

    # Dibujar etiquetas de contenedores en posición fija (NO optimizadas)
    render_container_labels(dwg, containers, elements_by_id)

    if visualdebug:
        render_debug_levels(dwg, elements, containers, optimized_layout.levels)

    # Agregar etiquetas NdFn como anotaciones visibles (solo visualdebug)
    if ndfn_labels:
        render_debug_ndfn(dwg, elements, ndfn_labels)

    dwg.save()
    logger.info(f"Diagrama generado exitosamente: {output_svg}")

    # Convertir automáticamente a PNG si se especifica la opción
    if exportpng:
        convert_svg_to_png(output_svg)

    return True
