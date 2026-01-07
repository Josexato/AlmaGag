import os, json, svgwrite
from AlmaGag.config import WIDTH, HEIGHT
from AlmaGag.autolayout import AutoLayout
from AlmaGag.draw.icons import draw_icon_shape, draw_icon_label
from AlmaGag.draw.connections import draw_connection_line, draw_connection_label

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

    # === AutoLayout v2.0: Detectar y resolver colisiones ===
    layout = AutoLayout(all_elements, all_connections, canvas={'width': canvas_width, 'height': canvas_height})
    initial_collisions = layout.count_collisions()

    # Mostrar info de estructura
    num_levels = len(set(layout.levels.values()))
    num_groups = len(layout.groups)
    high_priority = sum(1 for e in all_elements if layout._get_element_priority(e) == 0)
    normal_priority = sum(1 for e in all_elements if layout._get_element_priority(e) == 1)
    low_priority = sum(1 for e in all_elements if layout._get_element_priority(e) == 2)

    if layout.has_collisions():
        remaining = layout.optimize(max_iterations=10)
        if remaining > 0:
            print(f"[WARN] AutoLayout v2.1: {remaining} colisiones no resueltas (inicial: {initial_collisions})")
        else:
            print(f"[OK] AutoLayout v2.1: colisiones resueltas ({initial_collisions} -> 0)")
    else:
        print(f"[OK] AutoLayout v2.1: 0 colisiones detectadas")

    print(f"     - {num_levels} niveles, {num_groups} grupo(s)")
    print(f"     - Prioridades: {high_priority} high, {normal_priority} normal, {low_priority} low")

    # Usar canvas recomendado si fue expandido
    rec_canvas = layout.recommended_canvas
    if rec_canvas['width'] > canvas_width or rec_canvas['height'] > canvas_height:
        canvas_width = rec_canvas['width']
        canvas_height = rec_canvas['height']
        print(f"     - Canvas expandido a {canvas_width}x{canvas_height}")

    dwg = svgwrite.Drawing(output_svg, size=(canvas_width, canvas_height))
    dwg.viewbox(0, 0, canvas_width, canvas_height)

    # Configurar markers para flechas direccionales
    markers = setup_arrow_markers(dwg)

    elements, label_positions, conn_labels = layout.get_result()
    elements_by_id = {e['id']: e for e in elements}

    # === Renderizado en orden correcto ===
    # 1. Dibujar todos los íconos (sin etiquetas)
    for elem in elements:
        draw_icon_shape(dwg, elem)

    # 2. Dibujar todas las conexiones (sin etiquetas)
    conn_centers = {}
    for conn in all_connections:
        center = draw_connection_line(dwg, elements_by_id, conn, markers)
        key = f"{conn['from']}->{conn['to']}"
        conn_centers[key] = center

    # 3. Dibujar todas las etiquetas (íconos + conexiones)
    for elem in elements:
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
