import os, json, svgwrite
from AlmaGag.config import WIDTH, HEIGHT
from AlmaGag.layout import Layout, AutoLayoutOptimizer
from AlmaGag.draw.icons import draw_icon_shape, draw_icon_label
from AlmaGag.draw.connections import draw_connection_line, draw_connection_label
from AlmaGag.draw.container import draw_container

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

def generate_diagram(json_file):
    if not os.path.exists(json_file):
        print(f"[ERROR] Archivo no encontrado: {json_file}")
        return

    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"[ERROR] Error al leer el JSON: {e}")
        return

    base_name = os.path.splitext(os.path.basename(json_file))[0]
    output_svg = f"{base_name}.svg"

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
    optimizer = AutoLayoutOptimizer(verbose=False)

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

    # Configurar markers para flechas direccionales
    markers = setup_arrow_markers(dwg)

    # Obtener resultados optimizados
    elements = optimized_layout.elements
    label_positions = optimized_layout.label_positions
    conn_labels = optimized_layout.connection_labels
    elements_by_id = {e['id']: e for e in elements}

    # Separar contenedores de elementos normales
    containers = [e for e in elements if 'contains' in e]
    normal_elements = [e for e in elements if 'contains' not in e]

    # === Renderizado en orden correcto ===
    # 0. Dibujar todos los contenedores (fondo)
    for container in containers:
        draw_container(dwg, container, elements_by_id)

    # 1. Dibujar todos los íconos normales (sin etiquetas)
    for elem in normal_elements:
        draw_icon_shape(dwg, elem)

    # 2. Dibujar todas las conexiones (sin etiquetas)
    conn_centers = {}
    for conn in all_connections:
        center = draw_connection_line(dwg, elements_by_id, conn, markers)
        key = f"{conn['from']}->{conn['to']}"
        conn_centers[key] = center

    # 3. Dibujar todas las etiquetas (íconos + conexiones)
    # Nota: Los contenedores ya tienen su etiqueta dibujada
    for elem in normal_elements:
        if elem.get('label'):
            pos = label_positions.get(elem['id'])
            draw_icon_label(dwg, elem, pos)

    for conn in all_connections:
        if conn.get('label'):
            key = f"{conn['from']}->{conn['to']}"
            center = conn_centers.get(key) or conn_labels.get(key)
            if center:
                draw_connection_label(dwg, conn, center)

    dwg.save()
    print(f"[OK] Diagrama generado exitosamente: {output_svg}")
