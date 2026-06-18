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
    Genera SVG de Fase 1: Estructura del diagrama.
    """
    snapshot = viz.snapshots['phase1']
    structure_info = snapshot['structure_info']

    filename = os.path.join(output_path, "phase1_structure.svg")

    # Canvas dinámico: altura basada en cantidad de NdDp + VCs + árbol de elementos
    canvas_width = 800
    ndpr_count = len(structure_info.primary_node_ids)
    vc_count = (len(structure_info.scc_virtual_containers) +
                len(structure_info.loop_virtual_containers) +
                len(structure_info.toi_virtual_containers) +
                len(structure_info.leaf_virtual_containers))
    total_elements = len(structure_info.element_tree)
    # ~200px header + 16px per NdDp + 14px per VC detail + 80px legend
    # + 30px section header + 16px per element in tree
    canvas_height = max(600, 200 + (ndpr_count + vc_count) * 18 + 100
                        + 50 + total_elements * 16)

    dwg = svgwrite.Drawing(filename, size=(canvas_width, canvas_height))

    # Fondo
    dwg.add(dwg.rect(insert=(0, 0), size=(canvas_width, canvas_height), fill='#f8f9fa'))

    # Título
    dwg.add(dwg.text(
        'LAF Phase 1: Structure Analysis',
        insert=(20, 30),
        font_size='20px',
        font_weight='bold',
        fill='#212529'
    ))

    # Métricas
    y = 60
    metrics = [
        f"Primary Elements: {len(structure_info.primary_elements)}",
        f"Containers: {len(structure_info.container_metrics)}",
        f"Connections: {len(structure_info.connection_sequences)}",
        f"Topological Levels: {max(structure_info.topological_levels.values()) + 1 if structure_info.topological_levels else 0}",
    ]

    if structure_info.container_metrics:
        max_contained = max(m['total_icons'] for m in structure_info.container_metrics.values())
        metrics.append(f"Max Container Size: {max_contained} icons")

    for metric in metrics:
        dwg.add(dwg.text(
            metric,
            insert=(40, y),
            font_size='14px',
            fill='#495057'
        ))
        y += 25

    # Tabla de nodos abstractos (NdDp01)
    y += 20
    dwg.add(dwg.text(
        'Abstract Nodes (NdDp01):',
        insert=(40, y),
        font_size='16px',
        font_weight='bold',
        fill='#212529'
    ))
    y += 25

    # Header de tabla
    dwg.add(dwg.text(
        'ID            Type                      Element',
        insert=(60, y),
        font_size='11px',
        fill='#495057',
        font_family='monospace',
        font_weight='bold'
    ))
    y += 18

    # Color map for node types
    type_colors = {
        'Simple': '#6c757d',
        'Contenedor': '#0d6efd',
        'Contenedor Virtual SCC': '#e74c3c',
        'Contenedor Virtual Loop': '#f39c12',
        'Contenedor Virtual TOI': '#9b59b6',
        'Contenedor Virtual Leaf': '#27ae60',
        'Contenedor Virtual': '#dc3545',
        'SCC': '#e74c3c',
        'Loop': '#f39c12',
        'TOI': '#8e44ad',
        'TOI Virtual': '#a569bd',
        'Leaf': '#27ae60',
    }

    # Build sorted NdDp list (all entries that have a primary NdDp ID)
    ndpr_entries = sorted(
        structure_info.primary_node_ids.items(),
        key=lambda x: x[1]  # sort by NdDp01-001, NdDp01-002, ...
    )

    displayed_count = 0
    max_display = 20

    for entry_id, node_id in ndpr_entries:
        if displayed_count >= max_display:
            remaining = len(ndpr_entries) - max_display
            dwg.add(dwg.text(
                f"... y {remaining} más",
                insert=(60, y),
                font_size='11px',
                fill='#6c757d',
                font_family='monospace',
                font_style='italic'
            ))
            y += 16
            break

        node_type = structure_info.primary_node_types.get(entry_id, "N/A")
        color = type_colors.get(node_type, '#6c757d')

        entry_display = entry_id if len(entry_id) <= 20 else entry_id[:17] + "..."
        text = f"{node_id}  {node_type:<24}  {entry_display}"

        dwg.add(dwg.text(
            text,
            insert=(60, y),
            font_size='11px',
            fill=color,
            font_family='monospace'
        ))
        y += 16
        displayed_count += 1

        # For any VC type, show contained members indented
        if node_type.startswith('Contenedor Virtual'):
            vc_colors = {
                'Contenedor Virtual SCC': '#e74c3c',
                'Contenedor Virtual Loop': '#f39c12',
                'Contenedor Virtual TOI': '#b07dd6',
                'Contenedor Virtual Leaf': '#27ae60',
            }
            members = structure_info.get_vc_members(entry_id)
            if members:
                members_str = ', '.join(sorted(members))
                if len(members_str) > 55:
                    members_str = members_str[:52] + '...'
                dwg.add(dwg.text(
                    f"              └ {members_str}",
                    insert=(60, y),
                    font_size='10px',
                    fill=vc_colors.get(node_type, '#6c757d'),
                    font_family='monospace'
                ))
                y += 14
                displayed_count += 1

    # Árbol de elementos con profundidad
    y += 25
    dwg.add(dwg.text(
        'Element Tree (Depth):',
        insert=(40, y),
        font_size='16px',
        font_weight='bold',
        fill='#212529'
    ))
    y += 20

    # Header
    dwg.add(dwg.text(
        'Depth  Element                    Type         NdDp',
        insert=(60, y),
        font_size='11px',
        fill='#495057',
        font_family='monospace',
        font_weight='bold'
    ))
    y += 18

    # Colores por profundidad
    depth_colors = ['#212529', '#0d6efd', '#198754', '#e67e22', '#9b59b6', '#dc3545']

    def _get_nddp_label(elem_id):
        """Obtiene NdDp ID para un elemento."""
        nddp = structure_info.all_node_ids.get(elem_id, '')
        if nddp:
            return nddp
        # Fallback: mostrar a cuál NdDp01 pertenece
        if elem_id in structure_info.element_to_ndpr:
            mapped = structure_info.element_to_ndpr[elem_id]
            mapped_nddp = structure_info.all_node_ids.get(mapped, '')
            if mapped_nddp:
                return f'({mapped_nddp})'
        return ''

    def _render_tree_element(elem_id, y_pos, tree_prefix, color):
        """Renderiza un elemento del árbol."""
        node = structure_info.element_tree[elem_id]
        depth = node['depth']
        type_label = 'container' if node['is_container'] else 'icon'
        nddp = _get_nddp_label(elem_id)

        name_display = elem_id if len(elem_id) <= 22 else elem_id[:19] + '...'
        tree_name = f'{tree_prefix}{name_display}'

        text = f'  {depth}    {tree_name:<30} {type_label:<12} {nddp}'
        dwg.add(dwg.text(
            text, insert=(60, y_pos),
            font_size='11px', fill=color, font_family='monospace'
        ))
        return y_pos + 16

    def render_tree_node(elem_id, y_pos, prefix=''):
        node = structure_info.element_tree[elem_id]
        depth = node['depth']
        color = depth_colors[min(depth, len(depth_colors) - 1)]
        y_pos = _render_tree_element(elem_id, y_pos, prefix, color)

        children = node['children']
        for i, child_id in enumerate(children):
            is_last = (i == len(children) - 1)
            child_prefix = prefix + ('└─ ' if is_last else '├─ ')
            next_prefix = prefix + ('   ' if is_last else '│  ')
            child_depth = structure_info.element_tree[child_id]['depth']
            child_color = depth_colors[min(child_depth, len(depth_colors) - 1)]
            y_pos = _render_tree_element(child_id, y_pos, child_prefix, child_color)

            if structure_info.element_tree[child_id]['children']:
                y_pos = render_tree_children(child_id, y_pos, next_prefix)

        return y_pos

    def render_tree_children(parent_id, y_pos, prefix):
        children = structure_info.element_tree[parent_id]['children']
        for i, child_id in enumerate(children):
            is_last = (i == len(children) - 1)
            child_prefix = prefix + ('└─ ' if is_last else '├─ ')
            next_prefix = prefix + ('   ' if is_last else '│  ')
            child_depth = structure_info.element_tree[child_id]['depth']
            child_color = depth_colors[min(child_depth, len(depth_colors) - 1)]
            y_pos = _render_tree_element(child_id, y_pos, child_prefix, child_color)

            if structure_info.element_tree[child_id]['children']:
                y_pos = render_tree_children(child_id, y_pos, next_prefix)

        return y_pos

    # Renderizar desde raíces del element_tree (incluye TOI VCs)
    for elem_id, node in structure_info.element_tree.items():
        if node['parent'] is None:
            y = render_tree_node(elem_id, y)

    # Leyenda de colores
    y += 15
    dwg.add(dwg.text(
        'Legend:',
        insert=(60, y),
        font_size='11px',
        fill='#495057',
        font_weight='bold'
    ))
    y += 15

    legend_items = [
        ('Simple', '#6c757d'),
        ('Contenedor', '#0d6efd'),
        ('CV TOI', '#9b59b6'),
        ('Contenedor Virtual', '#dc3545')
    ]

    depth_legend = [
        (f'Depth {i}', depth_colors[i]) for i in range(min(4, len(depth_colors)))
    ]

    for label, color in legend_items + depth_legend:
        dwg.add(dwg.circle(
            center=(70, y - 3),
            r=4,
            fill=color
        ))
        dwg.add(dwg.text(
            label,
            insert=(80, y),
            font_size='10px',
            fill='#495057'
        ))
        y += 14

    # Ajustar canvas al contenido real
    final_height = max(canvas_height, y + 30)
    dwg['height'] = final_height
    # Actualizar fondo
    dwg.elements[1].attribs['height'] = final_height

    # Badge
    dwg.add(dwg.text(
        'Phase 1/10',
        insert=(canvas_width - 100, 30),
        font_size='14px',
        fill='#6c757d'
    ))

    dwg.save()

    if viz.debug:
        logger.debug(f"[VISUALIZER] Generado: {filename}")
