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
    Genera SVG de Fase 4: Layout abstracto (NdDp nodes only).
    VCs shown as rounded rectangles with centroid of member positions.
    """
    snapshot = viz.snapshots['phase4']
    abstract_positions = snapshot['abstract_positions']
    crossings = snapshot['crossings']
    connections = snapshot['connections']
    structure_info = snapshot['structure_info']

    filename = os.path.join(output_path, "phase4_abstract.svg")

    # Build NdDp positions (collapse VCs to centroids)
    use_ndpr = bool(structure_info.ndpr_elements)
    ndpr_set = set(structure_info.ndpr_elements)
    if use_ndpr:
        # Check if positions are already NdDp-level
        if all(k in ndpr_set for k in abstract_positions):
            ndpr_positions = dict(abstract_positions)
        else:
            raw_positions = {
                eid: pos for eid, pos in abstract_positions.items()
                if eid in structure_info.primary_elements
            }
            ndpr_positions = viz._build_ndpr_positions(raw_positions, structure_info)
        conn_graph = structure_info.ndpr_connection_graph
    else:
        ndpr_positions = {
            eid: pos for eid, pos in abstract_positions.items()
            if eid in structure_info.primary_elements
        }
        conn_graph = structure_info.connection_graph

    if not ndpr_positions:
        return

    min_x = min(x for x, y in ndpr_positions.values())
    max_x = max(x for x, y in ndpr_positions.values())
    min_y = min(y for x, y in ndpr_positions.values())
    max_y = max(y for x, y in ndpr_positions.values())

    padding = 150
    canvas_width = 1600
    canvas_height = 1000

    scale_x = (canvas_width - 2 * padding) / max(1, max_x - min_x)
    scale_y = (canvas_height - 2 * padding) / max(1, max_y - min_y)
    scale = min(scale_x, scale_y, 120)

    def to_canvas(ax, ay):
        cx = padding + (ax - min_x) * scale
        cy = padding + (ay - min_y) * scale
        return (cx, cy)

    dwg = svgwrite.Drawing(filename, size=(canvas_width, canvas_height))
    dwg.add(dwg.rect(insert=(0, 0), size=(canvas_width, canvas_height), fill='#f8f9fa'))

    dwg.add(dwg.text(
        'LAF Phase 4: Abstract Layout',
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

    # Canvas positions
    canvas_positions = {eid: to_canvas(*pos) for eid, pos in ndpr_positions.items()}

    # Draw connections
    viz._draw_colored_connections(dwg, canvas_positions, conn_graph, node_radius=14)

    # Draw NdDp nodes
    node_radius = 14
    for ndpr_id, (ax, ay) in ndpr_positions.items():
        cx, cy = to_canvas(ax, ay)
        node_type = structure_info.primary_node_types.get(ndpr_id, 'Simple')
        is_vc = node_type == 'Contenedor Virtual TOI'
        is_container = node_type == 'Contenedor'
        score = structure_info.accessibility_scores.get(ndpr_id, 0.0)

        # Color
        if is_vc:
            fill_color = '#9b59b6'
        elif is_container:
            fill_color = '#ffc107'
        elif score > 0.02:
            fill_color = '#dc3545'
        elif score > 0:
            fill_color = '#fd7e14'
        else:
            fill_color = '#0d6efd'

        viz._draw_ndpr_node(dwg, ndpr_id, cx, cy, structure_info,
                             radius=node_radius,
                             color_fn=lambda eid, si, c=fill_color: c)

        node_id = structure_info.primary_node_ids.get(ndpr_id, ndpr_id)

        # ARRIBA: NdDpXXX
        dwg.add(dwg.text(
            node_id,
            insert=(cx, cy - node_radius - 8),
            font_size='11px',
            fill='#212529',
            font_family='monospace',
            font_weight='bold',
            text_anchor='middle'
        ))

        # CENTRO: label inside node
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
        elif score > 0:
            dwg.add(dwg.text(
                f'{score:.3f}',
                insert=(cx, cy + 4),
                font_size='8px',
                fill='white',
                text_anchor='middle',
                font_family='monospace',
                font_weight='bold'
            ))

        # ABAJO: Name / VC info
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

        # Position
        dwg.add(dwg.text(
            f'({ax:.1f}, {ay})',
            insert=(cx, cy + node_radius + 30),
            font_size='9px',
            fill='#6c757d',
            font_family='monospace',
            text_anchor='middle',
            font_style='italic'
        ))

    # Badge
    dwg.add(dwg.text(
        'Phase 4/10',
        insert=(canvas_width - 100, 30),
        font_size='14px',
        fill='#6c757d'
    ))

    # Legend
    legend_y = canvas_height - 120
    dwg.add(dwg.text(
        'Node Colors:',
        insert=(20, legend_y),
        font_size='14px',
        font_weight='bold',
        fill='#212529'
    ))

    color_items = [
        ('High centrality (>0.02)', '#dc3545'),
        ('Medium centrality (>0)', '#fd7e14'),
        ('Simple element', '#0d6efd'),
        ('Container (TBG)', '#ffc107'),
        ('CV TOI', '#9b59b6')
    ]

    for i, (label, color) in enumerate(color_items):
        y = legend_y + 20 + i * 18
        dwg.add(dwg.circle(
            center=(30, y - 4),
            r=5,
            fill=color,
            stroke='#212529',
            stroke_width=1
        ))
        dwg.add(dwg.text(
            label,
            insert=(45, y),
            font_size='11px',
            fill='#495057',
            font_family='sans-serif'
        ))

    dwg.save()

    if viz.debug:
        logger.debug(f"[VISUALIZER] Generado: {filename}")
