"""LAF Visualizer — auto-extraído de visualizer.py (WISH-ARCH-003 sub-tarea B)."""

import os
import math
import logging
import svgwrite
from typing import Dict, List, Tuple
from copy import deepcopy
from AlmaGag.config import ICON_WIDTH, ICON_HEIGHT
from AlmaGag.utils import extract_item_id
from AlmaGag.layout.laf.structure_analyzer import StructureInfo

logger = logging.getLogger('AlmaGag')


def generate(viz, output_path):
    """
    Genera SVG de Fase 2: Análisis topológico.
    Muestra niveles topológicos, IDs de nodos primarios, nombres y conexiones.
    Detecta y resalta conexiones que se cruzan.
    """
    snapshot = viz.snapshots['phase2']
    structure_info = snapshot['structure_info']

    filename = os.path.join(output_path, "phase2_topology.svg")

    # Organizar NdDp por nivel (vista colapsada)
    by_level = {}
    max_level = 0
    use_ndpr = bool(structure_info.ndpr_topological_levels)
    levels_source = structure_info.ndpr_topological_levels if use_ndpr else structure_info.topological_levels
    for elem_id, level in levels_source.items():
        if level not in by_level:
            by_level[level] = []
        by_level[level].append(elem_id)
        max_level = max(max_level, level)

    # Calcular espacio vertical por nivel
    level_height = 100
    start_y = 120
    bottom_margin = 200  # Espacio para leyenda

    # Calcular dimensiones del canvas dinámicamente
    canvas_width = 1200
    canvas_height = start_y + (max_level + 1) * level_height + bottom_margin

    dwg = svgwrite.Drawing(filename, size=(canvas_width, canvas_height))

    # Fondo
    dwg.add(dwg.rect(insert=(0, 0), size=(canvas_width, canvas_height), fill='#f8f9fa'))

    # Título
    dwg.add(dwg.text(
        'LAF Phase 2: Topological Analysis',
        insert=(20, 30),
        font_size='20px',
        font_weight='bold',
        fill='#212529'
    ))

    # Radio de nodos
    node_radius = 22

    # Diccionario para guardar posiciones de nodos (para dibujar flechas después)
    node_positions = {}

    # PASO 1: Calcular posiciones de todos los nodos
    for level in sorted(by_level.keys()):
        elements = by_level[level]
        level_y = start_y + level * level_height

        # Distribuir elementos horizontalmente
        num_elements = len(elements)
        spacing = (canvas_width - 240) / max(num_elements, 1)
        start_x = 140

        for i, elem_id in enumerate(elements):
            node_x = start_x + i * spacing
            node_positions[elem_id] = (node_x, level_y)

    # PASO 2: Calcular todas las conexiones y detectar cruces
    import math

    # Lista de todas las conexiones con sus coordenadas
    connections = []

    conn_graph = structure_info.ndpr_connection_graph if use_ndpr else structure_info.connection_graph
    for from_id, to_list in conn_graph.items():
        if from_id not in node_positions:
            continue

        from_x, from_y = node_positions[from_id]

        for to_id in to_list:
            if to_id not in node_positions:
                continue

            to_x, to_y = node_positions[to_id]

            # Calcular puntos de inicio y fin
            dx = to_x - from_x
            dy = to_y - from_y
            angle = math.atan2(dy, dx)

            conn_start_x = from_x + node_radius * math.cos(angle)
            conn_start_y = from_y + node_radius * math.sin(angle)
            conn_end_x = to_x - (node_radius + 8) * math.cos(angle)
            conn_end_y = to_y - (node_radius + 8) * math.sin(angle)

            connections.append({
                'from_id': from_id,
                'to_id': to_id,
                'start': (conn_start_x, conn_start_y),
                'end': (conn_end_x, conn_end_y),
                'angle': angle,
                'to_pos': (to_x, to_y)
            })

    # Detectar cruces entre conexiones
    crossing_indices = set()
    crossing_count = 0

    for i, conn1 in enumerate(connections):
        for j, conn2 in enumerate(connections):
            if i >= j:  # Evitar comparar consigo mismo y duplicados
                continue

            # Verificar si los segmentos se cruzan
            if viz._segments_intersect(
                conn1['start'], conn1['end'],
                conn2['start'], conn2['end']
            ):
                crossing_indices.add(i)
                crossing_indices.add(j)
                crossing_count += 1

    # Detectar flechas colineales (mismo origen, dirección similar)
    # Agrupar por origen
    by_origin = {}
    for i, conn in enumerate(connections):
        origin = conn['from_id']
        if origin not in by_origin:
            by_origin[origin] = []
        by_origin[origin].append((i, conn))

    # Detectar grupos colineales dentro de cada origen
    collinear_groups = []  # Lista de listas de índices
    collinear_indices = set()  # Todos los índices que son colineales

    for origin, conns in by_origin.items():
        if len(conns) < 2:
            continue

        # Encontrar grupos de flechas colineales
        visited = set()
        for idx1, (i, conn1) in enumerate(conns):
            if i in visited:
                continue

            group = [i]
            for idx2, (j, conn2) in enumerate(conns):
                if idx1 >= idx2 or j in visited:
                    continue

                if viz._are_collinear(conn1, conn2):
                    group.append(j)
                    visited.add(j)

            if len(group) > 1:  # Solo grupos con 2+ flechas
                collinear_groups.append(group)
                collinear_indices.update(group)
                visited.add(i)

    # Asignar colores muy diferentes a grupos colineales
    # Usar colores con máximo contraste entre grupos consecutivos
    collinear_colors = [
        '#FF1744',  # Rojo brillante
        '#00E5FF',  # Cyan brillante
        '#76FF03',  # Verde lima
        '#FF9100',  # Naranja
        '#D500F9',  # Púrpura
        '#FFEA00',  # Amarillo
        '#00B0FF',  # Azul claro
        '#FF6E40',  # Naranja rojizo
        '#69F0AE',  # Verde menta
        '#E040FB'   # Magenta
    ]
    color_assignments = {}  # {index: color}

    for group_idx, group in enumerate(collinear_groups):
        color = collinear_colors[group_idx % len(collinear_colors)]
        for conn_idx in group:
            color_assignments[conn_idx] = color

    # Asignar desplazamientos simétricos a conexiones colineales
    # para separarlas visualmente (arriba/abajo respecto a su dirección).
    collinear_offsets = {}  # {index: (dx, dy)}
    collinear_spacing = 10.0

    for group in collinear_groups:
        # Orden estable para que el patrón sea reproducible.
        ordered = sorted(group, key=lambda idx: (
            connections[idx]['to_id'],
            connections[idx]['angle']
        ))
        count = len(ordered)
        center = (count - 1) / 2.0

        for order_idx, conn_idx in enumerate(ordered):
            conn = connections[conn_idx]
            multiplier = order_idx - center  # simétrico (ej: -0.5, +0.5)
            angle = conn['angle']

            # Vector normal unitario a la conexión.
            nx = -math.sin(angle)
            ny = math.cos(angle)

            dx = nx * multiplier * collinear_spacing
            dy = ny * multiplier * collinear_spacing
            collinear_offsets[conn_idx] = (dx, dy)

    # Dibujar conexiones (flechas)
    for i, conn in enumerate(connections):
        has_crossing = i in crossing_indices
        is_collinear = i in collinear_indices

        # Prioridad: colineal > cruce > normal
        if is_collinear:
            line_color = color_assignments[i]
            arrow_color = color_assignments[i]
            opacity = 0.45  # Baja opacidad para ver superposición
        elif has_crossing:
            line_color = '#dc3545'  # Rojo para cruces
            arrow_color = '#dc3545'
            opacity = 0.8
        else:
            line_color = '#495057'  # Gris normal
            arrow_color = '#495057'
            opacity = 0.6

        # Aplicar offset visual si pertenece a grupo colineal.
        offset_dx, offset_dy = collinear_offsets.get(i, (0.0, 0.0))
        start_x, start_y = conn['start']
        end_x, end_y = conn['end']
        draw_start = (start_x + offset_dx, start_y + offset_dy)
        draw_end = (end_x + offset_dx, end_y + offset_dy)

        # Dibujar bolita de origen (pequeña)
        origin_x, origin_y = draw_start
        dwg.add(dwg.circle(
            center=(origin_x, origin_y),
            r=3,
            fill=line_color,
            opacity=opacity,
            stroke=line_color,
            stroke_width=1
        ))

        # Dibujar línea
        dwg.add(dwg.line(
            start=draw_start,
            end=draw_end,
            stroke=line_color,
            stroke_width=2,
            opacity=opacity
        ))

        # Dibujar punta de flecha
        arrow_length = 12
        arrow_width = 0.4

        angle = conn['angle']
        arrow_tip_x, arrow_tip_y = draw_end

        arrow_base1_x = arrow_tip_x - arrow_length * math.cos(angle + arrow_width)
        arrow_base1_y = arrow_tip_y - arrow_length * math.sin(angle + arrow_width)

        arrow_base2_x = arrow_tip_x - arrow_length * math.cos(angle - arrow_width)
        arrow_base2_y = arrow_tip_y - arrow_length * math.sin(angle - arrow_width)

        dwg.add(dwg.polygon(
            points=[(arrow_tip_x, arrow_tip_y),
                    (arrow_base1_x, arrow_base1_y),
                    (arrow_base2_x, arrow_base2_y)],
            fill=arrow_color,
            opacity=opacity,
            stroke=arrow_color,
            stroke_width=0.5
        ))

    # PASO 3: Dibujar niveles y nodos
    for level in sorted(by_level.keys()):
        elements = by_level[level]
        level_y = start_y + level * level_height

        # Barra de fondo para el nivel (alternando colores)
        bar_height = level_height - 20
        bar_y = level_y - 50
        bar_color = '#e3f2fd' if level % 2 == 0 else '#f1f8e9'  # Azul claro / Verde claro

        dwg.add(dwg.rect(
            insert=(10, bar_y),
            size=(canvas_width - 20, bar_height),
            fill=bar_color,
            opacity=0.3,
            stroke='#90caf9' if level % 2 == 0 else '#aed581',
            stroke_width=1,
            stroke_dasharray='5,5'
        ))

        # Label del nivel
        dwg.add(dwg.text(
            f'Level {level}',
            insert=(20, level_y - 10),
            font_size='14px',
            font_weight='bold',
            fill='#495057'
        ))

        # Línea horizontal del nivel (más tenue)
        dwg.add(dwg.line(
            start=(120, level_y),
            end=(canvas_width - 20, level_y),
            stroke='#dee2e6',
            stroke_width=1,
            stroke_dasharray='5,5',
            opacity=0.5
        ))

        for elem_id in elements:
            node_x, node_y = node_positions[elem_id]
            score = structure_info.accessibility_scores.get(elem_id, 0)
            node_id = structure_info.primary_node_ids.get(elem_id, "N/A")
            node_type = structure_info.primary_node_types.get(elem_id, "Simple")
            elem_level = levels_source.get(elem_id, 0)
            is_vc = node_type == 'Contenedor Virtual TOI'

            # Color según tipo de nodo
            if is_vc:
                color = '#9b59b6'  # Púrpura para VCs TOI
            elif score > 0.05:
                color = '#dc3545'  # Rojo - Alto
            elif score > 0.02:
                color = '#ffc107'  # Amarillo - Medio
            else:
                color = '#0d6efd'  # Azul - Bajo/Normal

            # Dibujar nodo: rectángulo redondeado para VCs, círculo para el resto
            if is_vc:
                vc_w, vc_h = node_radius * 2.5, node_radius * 1.8
                dwg.add(dwg.rect(
                    insert=(node_x - vc_w / 2, node_y - vc_h / 2),
                    size=(vc_w, vc_h),
                    rx=8, ry=8,
                    fill=color,
                    opacity=0.8,
                    stroke='#212529',
                    stroke_width=2
                ))
            else:
                dwg.add(dwg.circle(
                    center=(node_x, node_y),
                    r=node_radius,
                    fill=color,
                    opacity=0.8,
                    stroke='#212529',
                    stroke_width=2
                ))

            # ID del nodo primario ARRIBA del nodo con nivel
            node_label = f"{node_id} [L{elem_level}]"
            dwg.add(dwg.text(
                node_label,
                insert=(node_x, node_y - node_radius - 8),
                font_size='11px',
                fill='#212529',
                text_anchor='middle',
                font_family='monospace',
                font_weight='bold'
            ))

            # Nombre DEBAJO del nodo
            if is_vc:
                # For VCs, show member count
                vc_members = structure_info.get_vc_members(elem_id)
                if vc_members:
                    label = f"VC ({len(vc_members)} elem)"
                else:
                    label = elem_id
            else:
                label = elem_id if len(elem_id) <= 18 else elem_id[:15] + '...'

            dwg.add(dwg.text(
                label,
                insert=(node_x, node_y + node_radius + 16),
                font_size='10px',
                fill='#6c757d',
                text_anchor='middle',
                font_family='monospace'
            ))

            # Mostrar score o member count DENTRO del nodo
            if is_vc:
                vc_info = viz._find_vc_info(structure_info, elem_id)
                if vc_info:
                    vc_label = viz._get_vc_label(vc_info)
                    dwg.add(dwg.text(
                        vc_label,
                        insert=(node_x, node_y + 4),
                        font_size='9px',
                        fill='white',
                        text_anchor='middle',
                        font_weight='bold',
                        font_family='monospace'
                    ))
            elif score > 0:
                dwg.add(dwg.text(
                    f'{score:.3f}',
                    insert=(node_x, node_y + 4),
                    font_size='9px',
                    fill='white',
                    text_anchor='middle',
                    font_weight='bold',
                    font_family='monospace'
                ))

    # Leyenda
    legend_y = canvas_height - 100
    dwg.add(dwg.text(
        'Accessibility Score:',
        insert=(20, legend_y),
        font_size='14px',
        font_weight='bold',
        fill='#212529'
    ))

    legend_items = [
        ('High (>0.05)', '#dc3545'),
        ('Medium (0.02-0.05)', '#ffc107'),
        ('Low (<0.02)', '#0d6efd')
    ]

    for i, (label, color) in enumerate(legend_items):
        x = 20
        y = legend_y + 25 + i * 20

        dwg.add(dwg.circle(
            center=(x + 10, y - 3),
            r=8,
            fill=color,
            opacity=0.7
        ))

        dwg.add(dwg.text(
            label,
            insert=(x + 25, y),
            font_size='12px',
            fill='#495057'
        ))

    # Badge
    dwg.add(dwg.text(
        'Phase 2/10',
        insert=(canvas_width - 100, 30),
        font_size='14px',
        fill='#6c757d'
    ))

    # Contadores
    crossing_text = f"Crossings: {crossing_count}"
    crossing_color = '#28a745' if crossing_count == 0 else '#dc3545'  # Verde si 0, rojo si >0

    dwg.add(dwg.text(
        crossing_text,
        insert=(20, 60),
        font_size='16px',
        font_weight='bold',
        fill=crossing_color
    ))

    # Contador de grupos colineales
    collinear_text = f"Collinear groups: {len(collinear_groups)}"
    collinear_color = '#28a745' if len(collinear_groups) == 0 else '#f39c12'  # Verde si 0, naranja si >0

    dwg.add(dwg.text(
        collinear_text,
        insert=(180, 60),
        font_size='16px',
        font_weight='bold',
        fill=collinear_color
    ))

    # Leyenda de colores de flechas
    dwg.add(dwg.text(
        'Arrows:',
        insert=(20, 85),
        font_size='12px',
        font_weight='bold',
        fill='#495057'
    ))

    # Normal arrows
    dwg.add(dwg.circle(
        center=(30, 103),
        r=4,
        fill='#495057',
        opacity=0.6
    ))
    dwg.add(dwg.text(
        'Normal',
        insert=(40, 106),
        font_size='11px',
        fill='#495057'
    ))

    # Crossing arrows
    dwg.add(dwg.circle(
        center=(95, 103),
        r=4,
        fill='#dc3545',
        opacity=0.8
    ))
    dwg.add(dwg.text(
        'Crossing',
        insert=(105, 106),
        font_size='11px',
        fill='#dc3545'
    ))

    # Collinear arrows
    dwg.add(dwg.circle(
        center=(175, 103),
        r=4,
        fill='#FF1744',
        opacity=0.45
    ))
    dwg.add(dwg.text(
        'Collinear',
        insert=(185, 106),
        font_size='11px',
        fill='#FF1744'
    ))

    dwg.add(dwg.text(
        '(same origin, similar direction - low opacity)',
        insert=(185, 118),
        font_size='9px',
        fill='#6c757d',
        font_style='italic'
    ))

    dwg.save()

    if viz.debug:
        logger.debug(f"[VISUALIZER] Generado: {filename}")
