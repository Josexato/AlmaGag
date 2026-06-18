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
    Genera SVG de Fase 3: Ordenamiento por centralidad.

    Muestra cómo los nodos se ordenan dentro de cada nivel según su accessibility score.
    """
    if 'phase3' not in viz.snapshots:
        if viz.debug:
            logger.warning(f"[VISUALIZER] No hay datos de Phase 3 para generar")
        return

    phase3_data = viz.snapshots.get('phase3', {})
    structure_info = phase3_data.get('structure_info')
    centrality_order = phase3_data.get('centrality_order', {})

    if not structure_info or not centrality_order:
        if viz.debug:
            logger.warning(f"[VISUALIZER] Datos incompletos para Phase 3")
        return

    filename = os.path.join(output_path, 'phase3_centrality.svg')

    # Collapse centrality_order to NdDp level
    use_ndpr = bool(structure_info.ndpr_elements)
    if use_ndpr:
        # Build NdDp-level centrality: aggregate scores per NdDp per level
        ndpr_scores = {}  # {ndpr_id: max_score}
        for level, elements in centrality_order.items():
            for elem_id, score in elements:
                ndpr_id = structure_info.element_to_ndpr.get(elem_id, elem_id)
                if ndpr_id not in ndpr_scores or score > ndpr_scores[ndpr_id]:
                    ndpr_scores[ndpr_id] = score

        # Build NdDp centrality_order using ndpr_topological_levels
        ndpr_centrality = {}
        for ndpr_id in structure_info.ndpr_elements:
            level = structure_info.ndpr_topological_levels.get(ndpr_id, 0)
            score = ndpr_scores.get(ndpr_id, 0.0)
            if level not in ndpr_centrality:
                ndpr_centrality[level] = []
            ndpr_centrality[level].append((ndpr_id, score))

        # Sort each level by score descending
        for level in ndpr_centrality:
            ndpr_centrality[level].sort(key=lambda x: x[1], reverse=True)

        display_order = ndpr_centrality
        conn_graph = structure_info.ndpr_connection_graph
    else:
        display_order = centrality_order
        conn_graph = structure_info.connection_graph

    # Calcular espacio vertical por nivel
    start_y = 120
    level_height = 100
    bottom_margin = 200

    max_level = max(display_order.keys()) if display_order else 0

    canvas_width = 1200
    canvas_height = start_y + (max_level + 1) * level_height + bottom_margin

    dwg = svgwrite.Drawing(filename, size=(canvas_width, canvas_height))

    dwg.add(dwg.rect(insert=(0, 0), size=(canvas_width, canvas_height), fill='#f8f9fa'))

    dwg.add(dwg.text(
        'LAF Phase 3: Centrality Ordering',
        insert=(20, 30),
        font_size='20px',
        font_weight='bold',
        fill='#212529'
    ))

    dwg.add(dwg.text(
        f'NdDp nodes ordered by accessibility score within each level',
        insert=(20, 55),
        font_size='14px',
        fill='#6c757d'
    ))

    node_radius = 15
    all_node_positions = {}

    for level in sorted(display_order.keys()):
        elements = display_order[level]
        y = start_y + level * level_height

        bar_color = '#e3f2fd' if level % 2 == 0 else '#f1f8e9'
        dwg.add(dwg.rect(
            insert=(10, y - 40),
            size=(canvas_width - 20, 80),
            fill=bar_color,
            opacity=0.3,
            stroke='#90caf9' if level % 2 == 0 else '#aed581',
            stroke_width=1,
            stroke_dasharray='5,5'
        ))

        dwg.add(dwg.text(
            f'Level {level}',
            insert=(20, y - 15),
            font_size='14px',
            font_weight='bold',
            fill='#495057'
        ))

        num_elements = len(elements)
        if num_elements > 0:
            spacing = min(80, (canvas_width - 100) / num_elements)
            canvas_center_x = canvas_width / 2

            max_score = max(score for _, score in elements) if elements else 0
            central_elements = [(idx, elem_id, score) for idx, (elem_id, score)
                               in enumerate(elements) if score == max_score and score > 0]

            if central_elements:
                num_centrals = len(central_elements)
                central_start_x = canvas_center_x - ((num_centrals - 1) * spacing) / 2
                positions = {}
                for i, (idx, _, _) in enumerate(central_elements):
                    positions[idx] = central_start_x + i * spacing
                non_central_indices = [idx for idx in range(num_elements)
                                      if idx not in positions]
                if non_central_indices:
                    left_side_x = min(positions.values()) - spacing
                    right_side_x = max(positions.values()) + spacing
                    for idx in non_central_indices:
                        if idx < min(positions.keys()):
                            positions[idx] = left_side_x
                            left_side_x -= spacing
                        else:
                            positions[idx] = right_side_x
                            right_side_x += spacing
            else:
                start_x = (canvas_width - (num_elements - 1) * spacing) / 2
                positions = {idx: start_x + idx * spacing for idx in range(num_elements)}

            for idx, (elem_id, score) in enumerate(elements):
                x = positions[idx]
                all_node_positions[elem_id] = (x, y)

    # Dibujar conexiones con colores por origen
    viz._draw_colored_connections(dwg, all_node_positions,
                                   conn_graph, node_radius=node_radius)

    # Dibujar nodos NdDp
    for level in sorted(display_order.keys()):
        elements = display_order[level]
        for elem_id, score in elements:
            if elem_id not in all_node_positions:
                continue
            x, y = all_node_positions[elem_id]

            node_type = structure_info.primary_node_types.get(elem_id, 'Simple')
            is_vc = node_type == 'Contenedor Virtual TOI'
            elem_level = (structure_info.ndpr_topological_levels if use_ndpr
                          else structure_info.topological_levels).get(elem_id, level)

            # Color: VC purple, else score-based
            if is_vc:
                color = '#9b59b6'
            elif score > 0.05:
                color = '#dc3545'
            elif score > 0.02:
                color = '#ffc107'
            else:
                color = '#0d6efd'

            viz._draw_ndpr_node(dwg, elem_id, x, y, structure_info,
                                 radius=node_radius,
                                 color_fn=lambda eid, si, c=color: c)

            node_id = structure_info.primary_node_ids.get(elem_id, "N/A")
            node_label = f"{node_id} [L{elem_level}]"
            dwg.add(dwg.text(
                node_label,
                insert=(x, y - node_radius - 5),
                font_size='10px',
                fill='#212529',
                text_anchor='middle',
                font_family='monospace',
                font_weight='bold'
            ))

            # Inside label
            if is_vc:
                vc_info = viz._find_vc_info(structure_info, elem_id)
                if vc_info:
                    vc_label = viz._get_vc_label(vc_info)
                    dwg.add(dwg.text(
                        vc_label,
                        insert=(x, y + 4),
                        font_size='8px',
                        fill='white',
                        text_anchor='middle',
                        font_weight='bold',
                        font_family='monospace'
                    ))
            elif score > 0:
                dwg.add(dwg.text(
                    f'{score:.3f}',
                    insert=(x, y + 4),
                    font_size='8px',
                    fill='white',
                    text_anchor='middle',
                    font_family='monospace',
                    font_weight='bold'
                ))

            # Label below
            if is_vc:
                vc_members = structure_info.get_vc_members(elem_id)
                if vc_members:
                    label = f"VC ({len(vc_members)} elem)"
                else:
                    label = elem_id
            else:
                label = elem_id if len(elem_id) <= 12 else elem_id[:9] + '...'
            dwg.add(dwg.text(
                label,
                insert=(x, y + node_radius + 15),
                font_size='9px',
                fill='#6c757d',
                text_anchor='middle',
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
        ('Low (<0.02)', '#0d6efd'),
        ('CV TOI', '#9b59b6')
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

    dwg.add(dwg.text(
        'NdDp nodes ordered: Higher scores toward center, lower scores toward edges',
        insert=(20, legend_y + 80 + 20),
        font_size='11px',
        fill='#6c757d',
        font_style='italic'
    ))

    # Badge
    dwg.add(dwg.text(
        'Phase 3/10',
        insert=(canvas_width - 100, 30),
        font_size='14px',
        fill='#6c757d'
    ))

    dwg.save()

    if viz.debug:
        logger.debug(f"[VISUALIZER] Generado: {filename}")
