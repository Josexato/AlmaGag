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
    Genera SVG de Fase 7: Diagrama visual de cada iteración de expansión.

    Dibuja un mini-diagrama por iteración mostrando nodos (círculos),
    conexiones (líneas) y nodos colapsados (rectángulos).
    """
    snapshot = viz.snapshots['phase7']
    summary = snapshot.get('iterative_summary', {})
    iterations = summary.get('iterations', [])
    structure_info = snapshot.get('structure_info')

    filename = os.path.join(output_path, "phase7_iterative.svg")

    if not iterations:
        # Sin datos: SVG mínimo
        dwg = svgwrite.Drawing(filename, size=(400, 100))
        dwg.add(dwg.rect(insert=(0, 0), size=(400, 100), fill='#f8f9fa'))
        dwg.add(dwg.text('Phase 7: No iterations', insert=(20, 50),
                         font_size='16px', fill='#6c757d'))
        dwg.save()
        return

    # Layout: cada iteración ocupa un panel horizontal
    panel_width = 700
    panel_height = 350
    panel_margin = 30
    header_height = 80
    table_height = 30 + len(iterations) * 22

    total_height = (
        header_height + table_height + panel_margin +
        len(iterations) * (panel_height + panel_margin) + 40
    )
    canvas_width = panel_width + 80

    dwg = svgwrite.Drawing(filename, size=(canvas_width, total_height))
    dwg.add(dwg.rect(insert=(0, 0), size=(canvas_width, total_height), fill='#f8f9fa'))

    # Título
    dwg.add(dwg.text(
        'LAF Phase 7: Iterative Expansion',
        insert=(20, 30), font_size='20px', font_weight='bold', fill='#212529'
    ))
    dwg.add(dwg.text(
        f"{summary.get('expandable_count', summary.get('max_depth', 0))} expandables, "
        f"{summary.get('total_iterations', 0)} iterations, "
        f"{summary.get('final_elements', 0)} final elements",
        insert=(20, 52), font_size='13px', fill='#6c757d'
    ))
    dwg.add(dwg.text(
        'Phase 7/11', insert=(canvas_width - 100, 30),
        font_size='14px', fill='#6c757d'
    ))

    # Tabla resumen compacta
    ty = header_height
    headers = ['Iter', 'Depth', 'Nodes', 'Collapsed', 'X(pre)', 'X(post)']
    col_x = [30, 90, 170, 250, 350, 450]
    for i, h in enumerate(headers):
        dwg.add(dwg.text(h, insert=(col_x[i], ty),
                         font_size='11px', font_weight='bold', fill='#495057',
                         font_family='monospace'))
    ty += 3
    dwg.add(dwg.line(start=(25, ty), end=(550, ty),
                     stroke='#dee2e6', stroke_width=1))
    ty += 16
    for it in iterations:
        vals = [
            str(it['iteration']), it['label'],
            str(it['nodes']), str(it['collapsed']),
            str(it['crossings_before']), str(it['crossings_after']),
        ]
        for i, v in enumerate(vals):
            dwg.add(dwg.text(v, insert=(col_x[i], ty),
                             font_size='10px', fill='#212529',
                             font_family='monospace'))
        ty += 22

    # Diagramas de cada iteración
    panel_y = header_height + table_height + panel_margin

    # Colores por iteración
    iter_colors = ['#4263eb', '#2b8a3e', '#e67700', '#ae3ec9', '#c92a2a']

    for idx, it in enumerate(iterations):
        positions = it.get('positions', {})
        conn_graph = it.get('connection_graph', {})
        collapsed = it.get('collapsed_sizes', {})

        if not positions:
            continue

        # Panel border
        px = 30
        py = panel_y
        color = iter_colors[idx % len(iter_colors)]

        dwg.add(dwg.rect(
            insert=(px, py), size=(panel_width, panel_height),
            fill='#ffffff', stroke='#dee2e6', stroke_width=1, rx=6
        ))

        # Panel title
        dwg.add(dwg.text(
            f"Iteración {it['iteration']}: {it['label']}  "
            f"({it['nodes']} nodos, {it['crossings_after']} cruces)",
            insert=(px + 12, py + 20),
            font_size='13px', font_weight='bold', fill=color
        ))

        # Dibujar nodos y conexiones dentro del panel
        draw_area_x = px + 20
        draw_area_y = py + 40
        draw_area_w = panel_width - 40
        draw_area_h = panel_height - 55

        # Calcular escala para mapear posiciones abstractas al área de dibujo
        all_x = [p[0] for p in positions.values()]
        all_y = [p[1] for p in positions.values()]
        min_x, max_x = min(all_x), max(all_x)
        min_y, max_y = min(all_y), max(all_y)
        range_x = max_x - min_x if max_x != min_x else 1
        range_y = max_y - min_y if max_y != min_y else 1

        margin = 25  # margen interno para que los nodos no toquen el borde
        scale_x = (draw_area_w - 2 * margin) / range_x
        scale_y = (draw_area_h - 2 * margin) / range_y
        scale = min(scale_x, scale_y)

        def to_screen(ax, ay):
            sx = draw_area_x + margin + (ax - min_x) * scale
            sy = draw_area_y + margin + (ay - min_y) * scale
            return sx, sy

        # Tamaño de nodos (calculado antes para usarlo en conexiones)
        node_radius = max(6, min(14, 200 // max(len(positions), 1)))

        # Dibujar conexiones dirigidas con separación de solapamientos
        # Paso 1: Recolectar todas las aristas con coordenadas de pantalla
        all_edges = []  # [(from_id, to_id, x1, y1, x2, y2)]
        for from_id, to_list in conn_graph.items():
            if from_id not in positions:
                continue
            for to_id in to_list:
                if to_id not in positions:
                    continue
                x1, y1 = to_screen(*positions[from_id])
                x2, y2 = to_screen(*positions[to_id])
                length = math.sqrt((x2 - x1)**2 + (y2 - y1)**2)
                if length < 0.01:
                    continue
                all_edges.append((from_id, to_id, x1, y1, x2, y2))

        # Paso 2: Agrupar aristas por corredor visual (pendiente + intercepción similar)
        # Dos aristas comparten corredor si tienen pendiente similar y su
        # línea de soporte (ax+by=c) tiene intercepción cercana
        corridor_threshold = 8.0  # px de tolerancia para considerar mismo corredor
        corridors = []  # [(slope_key, intercept, [edge_indices])]

        for edge_i, (_, _, x1, y1, x2, y2) in enumerate(all_edges):
            dx = x2 - x1
            dy = y2 - y1
            length = math.sqrt(dx*dx + dy*dy)

            # Normalizar dirección (siempre apuntando "a la derecha" o "abajo" para consistencia)
            if dx < 0 or (abs(dx) < 0.01 and dy < 0):
                dx, dy = -dx, -dy

            # Pendiente cuantizada (ángulo en grados, redondeado a 5°)
            angle = math.degrees(math.atan2(dy, dx))
            slope_key = round(angle / 5) * 5

            # Intercepción perpendicular: distancia del origen a la línea
            # Fórmula: d = |(-dy*x1 + dx*y1)| / length (con signo para distinguir lados)
            nx = -dy / length
            ny = dx / length
            intercept = nx * x1 + ny * y1

            # Buscar corredor existente compatible
            placed = False
            for ci, (sk, ci_intercept, ci_edges) in enumerate(corridors):
                if sk == slope_key and abs(ci_intercept - intercept) < corridor_threshold:
                    ci_edges.append(edge_i)
                    placed = True
                    break
            if not placed:
                corridors.append((slope_key, intercept, [edge_i]))

        # Paso 3: Dibujar aristas con offset por corredor
        arrow_size = max(4, min(8, node_radius * 0.6))
        dot_radius = max(2.5, min(5, node_radius * 0.35))
        spread_per_edge = 5.0  # px de separación entre líneas del mismo corredor

        for _sk, _ci, edge_indices in corridors:
            n_in_corridor = len(edge_indices)
            for local_idx, edge_i in enumerate(edge_indices):
                from_id, to_id, x1, y1, x2, y2 = all_edges[edge_i]

                dx = x2 - x1
                dy = y2 - y1
                length = math.sqrt(dx*dx + dy*dy)

                # Normal perpendicular unitaria
                nx = -dy / length
                ny = dx / length

                # Offset perpendicular para separar líneas en el mismo corredor
                if n_in_corridor > 1:
                    spread = spread_per_edge * (n_in_corridor - 1)
                    offset = -spread / 2 + local_idx * spread_per_edge
                else:
                    offset = 0.0

                ox1 = x1 + nx * offset
                oy1 = y1 + ny * offset
                ox2 = x2 + nx * offset
                oy2 = y2 + ny * offset

                # Acortar línea para no entrar en el nodo
                ux = dx / length
                uy = dy / length
                shrink = node_radius + 2
                sx1 = ox1 + ux * shrink
                sy1 = oy1 + uy * shrink
                sx2 = ox2 - ux * shrink
                sy2 = oy2 - uy * shrink

                # Línea
                dwg.add(dwg.line(
                    start=(sx1, sy1), end=(sx2, sy2),
                    stroke='#868e96', stroke_width=1.5, opacity=0.7
                ))

                # Bolita en el origen
                dwg.add(dwg.circle(
                    center=(sx1, sy1), r=dot_radius,
                    fill='#868e96', opacity=0.8
                ))

                # Flecha en el destino
                ax_tip = sx2
                ay_tip = sy2
                ax_l = ax_tip - ux * arrow_size + nx * arrow_size * 0.5
                ay_l = ay_tip - uy * arrow_size + ny * arrow_size * 0.5
                ax_r = ax_tip - ux * arrow_size - nx * arrow_size * 0.5
                ay_r = ay_tip - uy * arrow_size - ny * arrow_size * 0.5
                dwg.add(dwg.polygon(
                    points=[(ax_tip, ay_tip), (ax_l, ay_l), (ax_r, ay_r)],
                    fill='#868e96', opacity=0.8
                ))

        # Calcular centralidad efectiva (alpha) para cada nodo
        # Misma lógica que AbstractPlacer: score → alpha, penalización si tiene hojas
        effective_alphas = {}
        if structure_info:
            positions_set = set(positions.keys())
            # Detectar nodos con hojas same-layer (sin conexiones inter-capa)
            has_same_layer_leaves = set()
            for eid in positions:
                same_targets = [t for t in conn_graph.get(eid, []) if t in positions_set]
                for t in same_targets:
                    t_out = len([x for x in conn_graph.get(t, []) if x not in positions_set])
                    t_in = sum(1 for s, ts in conn_graph.items()
                               if s not in positions_set and t in ts)
                    if t_out + t_in == 0:
                        has_same_layer_leaves.add(eid)
                        break

            for eid in positions:
                score = structure_info.accessibility_scores.get(eid, 0.0)
                # Fórmula de _calculate_centrality_weight
                if score <= 0:
                    alpha = 0.0
                elif score >= 0.10:
                    alpha = 0.95
                else:
                    alpha = min(0.95, 0.6 + score * 3.5)
                # Penalización por hojas same-layer
                if eid in has_same_layer_leaves:
                    alpha *= 0.3
                effective_alphas[eid] = alpha

        # Dibujar nodos
        for node_id, (ax, ay) in positions.items():
            sx, sy = to_screen(ax, ay)

            if node_id in collapsed:
                # Nodo colapsado: rectángulo
                rect_w = max(20, collapsed[node_id] * scale * 0.5)
                rect_h = node_radius * 2.2
                dwg.add(dwg.rect(
                    insert=(sx - rect_w / 2, sy - rect_h / 2),
                    size=(rect_w, rect_h),
                    fill='#fff3bf', stroke='#e67700', stroke_width=1.5,
                    rx=3, opacity=0.9
                ))
            else:
                # Nodo normal: círculo
                dwg.add(dwg.circle(
                    center=(sx, sy), r=node_radius,
                    fill=color, stroke='#ffffff', stroke_width=1.5,
                    opacity=0.85
                ))

            # Etiqueta del nodo (nombre corto)
            short_name = node_id[:12] if len(node_id) > 12 else node_id
            label_size = max(7, min(10, 120 // max(len(positions), 1)))
            dwg.add(dwg.text(
                short_name,
                insert=(sx, sy + node_radius + label_size + 2),
                font_size=f'{label_size}px', fill='#495057',
                text_anchor='middle', font_family='sans-serif'
            ))

            # Valores de centralidad: score, alpha efectiva, y orden
            centrality_scores = it.get('centrality_scores', {})
            centrality_order = it.get('centrality_order', {})

            # Calcular posición ordinal del nodo en centrality_order
            node_order_pos = None
            for _level, elems in centrality_order.items():
                for pos_idx, (eid, _sc) in enumerate(elems):
                    if eid == node_id:
                        node_order_pos = pos_idx + 1  # 1-based
                        break
                if node_order_pos is not None:
                    break

            c_score = centrality_scores.get(node_id, 0.0)
            eff_alpha = effective_alphas.get(node_id, 0.0) if effective_alphas else 0.0

            # Línea 1: score de centralidad + alpha
            if eff_alpha > 0:
                score_text = f'c:{c_score:.3f} α:{eff_alpha:.2f}'
            else:
                score_text = f'c:{c_score:.3f} α:0'
            dwg.add(dwg.text(
                score_text,
                insert=(sx, sy + node_radius + label_size * 2 + 4),
                font_size=f'{max(6, label_size - 1)}px', fill='#adb5bd',
                text_anchor='middle', font_family='monospace'
            ))

            # Línea 2: posición en el orden
            if node_order_pos is not None:
                dwg.add(dwg.text(
                    f'ord:{node_order_pos}',
                    insert=(sx, sy + node_radius + label_size * 3 + 6),
                    font_size=f'{max(6, label_size - 1)}px', fill='#adb5bd',
                    text_anchor='middle', font_family='monospace'
                ))

        panel_y += panel_height + panel_margin

    dwg.save()
    if viz.debug:
        logger.debug(f"[VISUALIZER] Generado: {filename}")
