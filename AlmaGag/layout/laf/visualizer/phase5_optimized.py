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
    Genera SVG de Fase 5: Posiciones optimizadas (NdDp nodes only).
    VCs shown as rounded rectangles with centroid of member positions.
    """
    snapshot = viz.snapshots['phase5']
    optimized_positions = snapshot['optimized_positions']
    crossings = snapshot['crossings']
    connections = snapshot['connections']
    structure_info = snapshot['structure_info']

    filename = os.path.join(output_path, "phase5_optimized.svg")

    # Build NdDp positions
    use_ndpr = bool(structure_info.ndpr_elements)
    ndpr_set = set(structure_info.ndpr_elements)
    if use_ndpr:
        # Check if positions are already NdDp-level
        if all(k in ndpr_set for k in optimized_positions):
            ndpr_positions = dict(optimized_positions)
        else:
            raw_positions = {
                eid: pos for eid, pos in optimized_positions.items()
                if eid in structure_info.primary_elements
            }
            ndpr_positions = viz._build_ndpr_positions(raw_positions, structure_info)
        conn_graph = structure_info.ndpr_connection_graph
    else:
        ndpr_positions = {
            eid: pos for eid, pos in optimized_positions.items()
            if eid in structure_info.primary_elements
        }
        conn_graph = structure_info.connection_graph

    if not ndpr_positions:
        return

    min_x = min(x for x, y in ndpr_positions.values())
    max_x = max(x for x, y in ndpr_positions.values())
    min_y = min(y for x, y in ndpr_positions.values())
    max_y = max(y for x, y in ndpr_positions.values())

    padding = 180
    scale = 200

    canvas_width = max(800, int(2 * padding + (max_x - min_x) * scale))
    canvas_height = max(600, int(2 * padding + (max_y - min_y) * scale))

    def to_canvas(ax, ay):
        cx = padding + (ax - min_x) * scale
        cy = padding + (ay - min_y) * scale
        return (cx, cy)

    dwg = svgwrite.Drawing(filename, size=(canvas_width, canvas_height))
    dwg.add(dwg.rect(insert=(0, 0), size=(canvas_width, canvas_height), fill='#f0fff0'))

    dwg.add(dwg.text(
        'LAF Phase 5: Position Optimization (Claude-SolFase5)',
        insert=(20, 30),
        font_size='20px',
        font_weight='bold',
        fill='#212529'
    ))

    dwg.add(dwg.text(
        f"Crossings: {crossings}",
        insert=(20, 55),
        font_size='16px',
        fill='#dc3545' if crossings > 3 else '#28a745',
        font_weight='bold'
    ))

    dwg.add(dwg.text(
        'Positions optimized to minimize total connector distance',
        insert=(20, 75),
        font_size='12px',
        fill='#6c757d',
        font_style='italic'
    ))

    # Canvas positions
    canvas_positions = {eid: to_canvas(*pos) for eid, pos in ndpr_positions.items()}

    # Draw connections with colored arrows
    viz._draw_colored_connections(dwg, canvas_positions, conn_graph, node_radius=14)

    # Draw NdDp nodes
    node_radius = 14
    for ndpr_id, (ax, ay) in ndpr_positions.items():
        cx, cy = to_canvas(ax, ay)
        node_type = structure_info.primary_node_types.get(ndpr_id, 'Simple')
        is_vc = node_type == 'Contenedor Virtual TOI'
        is_container = node_type == 'Contenedor'

        if is_vc:
            fill_color = '#9b59b6'
        elif is_container:
            fill_color = '#ffc107'
        else:
            fill_color = '#28a745'

        viz._draw_ndpr_node(dwg, ndpr_id, cx, cy, structure_info,
                             radius=node_radius,
                             color_fn=lambda eid, si, c=fill_color: c)

        node_id = structure_info.primary_node_ids.get(ndpr_id, ndpr_id)
        dwg.add(dwg.text(
            node_id,
            insert=(cx, cy - node_radius - 8),
            font_size='11px',
            fill='#212529',
            font_family='monospace',
            font_weight='bold',
            text_anchor='middle'
        ))

        # Inside label
        if is_vc:
            vc_info = viz._find_vc_info(structure_info, ndpr_id)
            if vc_info:
                vc_label = viz._get_vc_label(vc_info)
                dwg.add(dwg.text(
                    vc_label,
                    insert=(cx, cy + 4),
                    font_size='8px',
                    fill='white',
                    text_anchor='middle',
                    font_family='monospace',
                    font_weight='bold'
                ))
        elif is_container:
            dwg.add(dwg.text(
                'TBG',
                insert=(cx, cy + 4),
                font_size='9px',
                fill='white',
                text_anchor='middle',
                font_family='monospace',
                font_weight='bold'
            ))

        # Name below
        if is_vc:
            vc_members = structure_info.get_vc_members(ndpr_id)
            if vc_members:
                elem_name = f"VC ({len(vc_members)} elem)"
            else:
                elem_name = ndpr_id
        else:
            elem_name = ndpr_id if len(ndpr_id) <= 15 else ndpr_id[:12] + '...'

        dwg.add(dwg.text(
            elem_name,
            insert=(cx, cy + node_radius + 18),
            font_size='10px',
            fill='#495057',
            font_family='monospace',
            text_anchor='middle'
        ))

        # Score
        score = structure_info.accessibility_scores.get(ndpr_id, 0.0)
        score_text = f'c={score:.3f}' if score > 0 else 'c=0'
        dwg.add(dwg.text(
            score_text,
            insert=(cx, cy + node_radius + 30),
            font_size='9px',
            fill='#dc3545' if score > 0.05 else '#6c757d',
            font_family='monospace',
            text_anchor='middle',
            font_weight='bold' if score > 0.05 else 'normal'
        ))

        # Position
        dwg.add(dwg.text(
            f'({ax:.1f}, {ay})',
            insert=(cx, cy + node_radius + 42),
            font_size='9px',
            fill='#6c757d',
            font_family='monospace',
            text_anchor='middle',
            font_style='italic'
        ))

    # Badge
    dwg.add(dwg.text(
        'Phase 5/10 - Claude-SolFase5',
        insert=(canvas_width - 260, 30),
        font_size='14px',
        fill='#28a745',
        font_weight='bold'
    ))

    dwg.save()

    if viz.debug:
        logger.debug(f"[VISUALIZER] Generado: {filename}")
