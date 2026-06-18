"""
GrowthVisualizer - Fase de Visualización de LAF

Genera snapshots SVG de cada fase del proceso LAF para debugging
y documentación.

Author: José + ALMA + Claude (Claude-SolFase5)
Version: v1.1
Date: 2026-02-15
"""

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


class GrowthVisualizer:
    """
    Genera visualizaciones SVG del proceso de crecimiento LAF.

    Crea 11 archivos SVG mostrando cada fase:
    1. phase1_structure.svg: Árbol de elementos con métricas
    2. phase2_topology.svg: Niveles topológicos y accessibility scores
    3. phase3_centrality.svg: Ordenamiento por centralidad
    4. phase4_abstract.svg: Posiciones abstractas (puntos)
    5. phase5_optimized.svg: Posiciones optimizadas (Claude-SolFase5)
    6. phase6_ndpr_expanded.svg: Expansión NdDp01 → elementos
    7. phase7_iterative.svg: Resumen de corrida iterativa 4-5-6
    8. phase8_inflated.svg: Inflación + Contenedores expandidos
    9. phase9_redistributed.svg: Redistribución vertical
    10. phase10_routed.svg: Routing de conexiones
    11. phase11_final.svg: Layout final completo
    """

    def __init__(self, output_dir: str = "debug/growth", debug: bool = False):
        """
        Inicializa el visualizador.

        Args:
            output_dir: Directorio donde guardar los SVGs
            debug: Si True, imprime logs de debug
        """
        self.output_dir = output_dir
        self.debug = debug

        # Snapshots capturados
        self.snapshots = {}

    @staticmethod
    def _find_vc_info(structure_info, vc_id: str) -> dict:
        """Busca un VC dict por ID en todas las listas de VCs."""
        for vc_list in (structure_info.scc_virtual_containers,
                        structure_info.toi_virtual_containers,
                        structure_info.loop_virtual_containers,
                        structure_info.leaf_virtual_containers):
            for vc in vc_list:
                if vc['id'] == vc_id:
                    return vc
        return {}

    @staticmethod
    def _get_vc_label(vc_info: dict) -> str:
        """Obtiene etiqueta corta para un VC (toi_id si existe, si no el id)."""
        label = vc_info.get('toi_id', vc_info.get('id', ''))
        if len(label) > 10:
            label = label[:8] + '..'
        return label

    def capture_phase1(
        self,
        structure_info,
        diagram_name: str
    ) -> None:
        """
        Captura snapshot de Fase 1 (Análisis de estructura).

        Args:
            structure_info: StructureInfo con análisis completo
            diagram_name: Nombre del diagrama (para carpeta)
        """
        self.snapshots['phase1'] = {
            'structure_info': deepcopy(structure_info),
            'diagram_name': diagram_name
        }

        pass

    def capture_phase2_topology(
        self,
        structure_info
    ) -> None:
        """
        Captura snapshot de Fase 2 (Análisis topológico).

        Args:
            structure_info: StructureInfo con niveles topológicos y accessibility scores
        """
        self.snapshots['phase2'] = {
            'structure_info': deepcopy(structure_info)
        }

        pass

    def capture_phase3_centrality(
        self,
        structure_info,
        centrality_order: Dict[int, List[Tuple[str, float]]]
    ) -> None:
        """
        Captura snapshot de Fase 3 (Ordenamiento por centralidad).

        Args:
            structure_info: StructureInfo con información estructural
            centrality_order: Dict con elementos ordenados por nivel y score
        """
        # Guardar sin deepcopy para evitar problemas de serialización
        self.snapshots['phase3'] = {
            'structure_info': structure_info,
            'centrality_order': dict(centrality_order)  # Convertir a dict simple
        }

        pass

    def capture_phase4_abstract(
        self,
        abstract_positions: Dict[str, Tuple[int, int]],
        crossings: int,
        layout,
        structure_info
    ) -> None:
        """
        Captura snapshot de Fase 4 (Layout abstracto).

        Args:
            abstract_positions: {elem_id: (x, y)} en coordenadas abstractas
            crossings: Número de cruces detectados
            layout: Layout con conexiones
            structure_info: Información estructural para filtrar primarios
        """
        self.snapshots['phase4'] = {
            'abstract_positions': deepcopy(abstract_positions),
            'crossings': crossings,
            'connections': deepcopy(layout.connections),
            'structure_info': structure_info
        }

        pass

    def capture_phase5_optimized(
        self,
        optimized_positions,
        crossings: int,
        layout,
        structure_info
    ) -> None:
        """
        Captura snapshot de Fase 5 (Optimización de posiciones - Claude-SolFase5).

        Args:
            optimized_positions: {elem_id: (x, y)} posiciones optimizadas
            crossings: Número de cruces después de optimización
            layout: Layout con conexiones
            structure_info: Información estructural
        """
        self.snapshots['phase5'] = {
            'optimized_positions': deepcopy(optimized_positions),
            'crossings': crossings,
            'connections': deepcopy(layout.connections),
            'structure_info': structure_info
        }

        pass

    def capture_phase7_iterative(
        self,
        iterative_summary: dict,
        structure_info=None
    ) -> None:
        """
        Captura snapshot de Fase 7 (Resumen de corrida iterativa 4-5-6).

        Args:
            iterative_summary: Dict con expandable_count, total_iterations, iterations[]
            structure_info: Información estructural
        """
        self.snapshots['phase7'] = {
            'iterative_summary': iterative_summary,
            'structure_info': structure_info
        }

    def capture_phase8_inflated(
        self,
        layout,
        spacing: float,
        structure_info=None
    ) -> None:
        """
        Captura snapshot de Fase 8 (Inflación + Contenedores).

        Args:
            layout: Layout con elementos inflados y contenedores expandidos
            spacing: Spacing calculado
            structure_info: Información estructural con primary_node_ids
        """
        self.snapshots['phase8'] = {
            'layout': deepcopy(layout),
            'spacing': spacing,
            'structure_info': structure_info
        }

    def capture_phase9_redistributed(
        self,
        layout,
        structure_info=None
    ) -> None:
        """
        Captura snapshot de Fase 9 (Redistribución vertical).

        Args:
            layout: Layout después de redistribución vertical
            structure_info: Información estructural para NdFn labels
        """
        self.snapshots['phase9'] = {
            'layout': deepcopy(layout),
            'structure_info': structure_info
        }

    def capture_phase10_routed(
        self,
        layout,
        structure_info=None
    ) -> None:
        """
        Captura snapshot de Fase 10 (Routing).

        Args:
            layout: Layout con paths de conexiones calculados
            structure_info: Información estructural para NdFn labels
        """
        self.snapshots['phase10'] = {
            'layout': deepcopy(layout),
            'structure_info': structure_info
        }

    def capture_phase11_final(
        self,
        layout,
        structure_info=None
    ) -> None:
        """
        Captura snapshot de Fase 11 (Generación SVG final).

        Args:
            layout: Layout final completo
            structure_info: Información estructural para NdFn labels
        """
        self.snapshots['phase11'] = {
            'layout': deepcopy(layout),
            'structure_info': structure_info
        }

    def generate_all(self) -> None:
        """
        Genera todos los SVGs de visualización.
        """
        if not self.snapshots:
            if self.debug:
                logger.warning(f"[VISUALIZER] No hay snapshots capturados")
            return

        # Crear directorio de salida
        diagram_name = self.snapshots.get('phase1', {}).get('diagram_name', 'diagram')
        output_path = os.path.join(self.output_dir, diagram_name)
        os.makedirs(output_path, exist_ok=True)

        if self.debug:
            logger.debug(f"[VISUALIZER] Generando visualizaciones en: {output_path}")

        # Generar cada fase
        if 'phase1' in self.snapshots:
            self._generate_phase1_svg(output_path)

        if 'phase2' in self.snapshots:
            self._generate_phase2_topology_svg(output_path)

        if 'phase3' in self.snapshots:
            self._generate_phase3_centrality_svg(output_path)

        if 'phase4' in self.snapshots:
            self._generate_phase4_abstract_svg(output_path)

        if 'phase5' in self.snapshots:
            self._generate_phase5_optimized_svg(output_path)

        if 'phase7' in self.snapshots:
            self._generate_phase7_iterative_svg(output_path)

        if 'phase8' in self.snapshots:
            self._generate_phase8_inflated_svg(output_path)

        if 'phase9' in self.snapshots:
            self._generate_phase9_redistributed_svg(output_path)

        if 'phase10' in self.snapshots:
            self._generate_phase10_routed_svg(output_path)

        if 'phase11' in self.snapshots:
            self._generate_phase11_final_svg(output_path)

        if self.debug:
            logger.debug(f"[VISUALIZER] Generación completada: {len(self.snapshots)} fases")

    # Helper extraído de phase1.py
    def _draw_colored_connections(self, dwg, node_positions, connection_graph, node_radius=12):
        """
        Dibuja conexiones con colores por origen y distribución colineal.

        Cada nodo origen recibe un color único. Conexiones colineales (mismo origen,
        ángulo similar) se separan con offsets perpendiculares para evitar superposición.

        Args:
            dwg: svgwrite Drawing
            node_positions: {elem_id: (x, y)}
            connection_graph: {from_id: [to_id, ...]}
            node_radius: radio de los nodos para calcular offset de flechas
        """
        import math

        # Paleta de colores bien diferenciados
        origin_colors = [
            '#E53935', '#1E88E5', '#43A047', '#FB8C00', '#8E24AA',
            '#00ACC1', '#D81B60', '#7CB342', '#3949AB', '#F4511E',
            '#00897B', '#C0CA33', '#5E35B1', '#039BE5', '#e53935',
            '#6D4C41', '#546E7A', '#FFB300', '#1565C0', '#2E7D32',
        ]

        # Asignar un color estable por origen
        origin_color_map = {}
        color_idx = 0
        for from_id in sorted(connection_graph.keys()):
            if from_id in node_positions:
                origin_color_map[from_id] = origin_colors[color_idx % len(origin_colors)]
                color_idx += 1

        # Paso 1: Recopilar todas las conexiones con geometría
        conn_list = []
        for from_id, to_list in connection_graph.items():
            if from_id not in node_positions:
                continue
            from_x, from_y = node_positions[from_id]
            for to_id in to_list:
                if to_id not in node_positions:
                    continue
                to_x, to_y = node_positions[to_id]
                dx = to_x - from_x
                dy = to_y - from_y
                dist = math.hypot(dx, dy)
                if dist < 1:
                    continue
                angle = math.atan2(dy, dx)
                conn_list.append({
                    'from_id': from_id, 'to_id': to_id,
                    'from_pos': (from_x, from_y), 'to_pos': (to_x, to_y),
                    'angle': angle,
                })

        # Paso 2: Detectar grupos colineales y asignar offsets perpendiculares
        ANGLE_THRESHOLD = 0.25  # ~14°
        COLLINEAR_SPACING = 10.0

        by_origin = {}
        for idx, conn in enumerate(conn_list):
            by_origin.setdefault(conn['from_id'], []).append(idx)

        collinear_offsets = {}  # {idx: (dx, dy)}

        for origin, indices in by_origin.items():
            if len(indices) < 2:
                continue
            visited = set()
            for i_pos, i_idx in enumerate(indices):
                if i_idx in visited:
                    continue
                group = [i_idx]
                a1 = conn_list[i_idx]['angle']
                for j_pos in range(i_pos + 1, len(indices)):
                    j_idx = indices[j_pos]
                    if j_idx in visited:
                        continue
                    a2 = conn_list[j_idx]['angle']
                    diff = abs(a1 - a2)
                    if diff > math.pi:
                        diff = 2 * math.pi - diff
                    if diff < ANGLE_THRESHOLD:
                        group.append(j_idx)
                        visited.add(j_idx)
                if len(group) < 2:
                    continue
                visited.add(i_idx)
                # Distribuir simétricamente con offset perpendicular
                ordered = sorted(group, key=lambda idx: conn_list[idx]['to_id'])
                count = len(ordered)
                center = (count - 1) / 2.0
                for order_pos, g_idx in enumerate(ordered):
                    multiplier = order_pos - center
                    ang = conn_list[g_idx]['angle']
                    # Vector perpendicular a la dirección de la conexión
                    perp_x = -math.sin(ang)
                    perp_y = math.cos(ang)
                    collinear_offsets[g_idx] = (
                        perp_x * multiplier * COLLINEAR_SPACING,
                        perp_y * multiplier * COLLINEAR_SPACING,
                    )

        # Paso 3: Dibujar con offsets aplicados
        for idx, conn in enumerate(conn_list):
            from_x, from_y = conn['from_pos']
            to_x, to_y = conn['to_pos']
            line_color = origin_color_map.get(conn['from_id'], '#495057')

            # Aplicar offset colineal
            off_dx, off_dy = collinear_offsets.get(idx, (0.0, 0.0))
            from_x += off_dx
            from_y += off_dy
            to_x += off_dx
            to_y += off_dy

            # Recalcular dirección tras offset
            dx = to_x - from_x
            dy = to_y - from_y
            dist = math.hypot(dx, dy)
            if dist < 1:
                continue
            ux = dx / dist
            uy = dy / dist

            # Puntos de inicio/fin en el borde de los nodos
            start_x = from_x + node_radius * ux
            start_y = from_y + node_radius * uy
            end_x = to_x - (node_radius + 8) * ux
            end_y = to_y - (node_radius + 8) * uy

            # Círculo de origen
            dwg.add(dwg.circle(
                center=(start_x, start_y),
                r=3,
                fill=line_color,
                opacity=0.7
            ))

            # Línea
            dwg.add(dwg.line(
                start=(start_x, start_y),
                end=(end_x, end_y),
                stroke=line_color,
                stroke_width=1.5,
                opacity=0.6
            ))

            # Punta de flecha
            arrow_length = 10
            arrow_width = 0.35
            angle = math.atan2(uy, ux)
            tip_x, tip_y = end_x, end_y
            b1x = tip_x - arrow_length * math.cos(angle + arrow_width)
            b1y = tip_y - arrow_length * math.sin(angle + arrow_width)
            b2x = tip_x - arrow_length * math.cos(angle - arrow_width)
            b2y = tip_y - arrow_length * math.sin(angle - arrow_width)

            dwg.add(dwg.polygon(
                points=[(tip_x, tip_y), (b1x, b1y), (b2x, b2y)],
                fill=line_color,
                opacity=0.7
            ))

    # Helper extraído de phase1.py
    def _segments_intersect(self, p1, p2, p3, p4):
        """
        Verifica si dos segmentos de línea se intersectan.

        Segmento 1: p1 -> p2
        Segmento 2: p3 -> p4

        Returns: True si se intersectan, False si no
        """
        def ccw(A, B, C):
            # Counter-clockwise: (C.y - A.y) * (B.x - A.x) > (B.y - A.y) * (C.x - A.x)
            return (C[1] - A[1]) * (B[0] - A[0]) > (B[1] - A[1]) * (C[0] - A[0])

        # Dos segmentos se intersectan si los endpoints de uno están en lados opuestos del otro
        return (ccw(p1, p3, p4) != ccw(p2, p3, p4)) and (ccw(p1, p2, p3) != ccw(p1, p2, p4))

    # Helper extraído de phase1.py
    def _are_collinear(self, conn1, conn2, angle_threshold=0.2):
        """
        Detecta si dos conexiones son colineales (mismo origen, direcciones similares).

        Args:
            conn1, conn2: Diccionarios con información de conexión
            angle_threshold: Diferencia máxima de ángulo (radianes) para considerar colineales

        Returns: True si son colineales, False si no
        """
        import math

        # Mismo origen?
        if conn1['from_id'] != conn2['from_id']:
            return False

        # Ángulos similares?
        angle_diff = abs(conn1['angle'] - conn2['angle'])

        # Normalizar diferencia de ángulo (considerar wrap-around en ±π)
        if angle_diff > math.pi:
            angle_diff = 2 * math.pi - angle_diff

        return angle_diff < angle_threshold

    # Helper extraído de phase2_topology.py
    def _build_ndpr_positions(self, raw_positions, structure_info):
        """
        Collapse raw element positions into NdDp-level positions.

        If positions are already NdDp-level (all keys are NdDp IDs),
        return them directly without computing centroids.

        Otherwise, simple NdDp nodes keep their position and TOI VCs
        get the centroid of their member positions.

        Returns: {ndpr_id: (x, y)}
        """
        # Check if positions are already NdDp-level
        ndpr_set = set(structure_info.ndpr_elements)
        if ndpr_set and all(k in ndpr_set for k in raw_positions):
            return dict(raw_positions)

        ndpr_pos = {}

        for ndpr_id in structure_info.ndpr_elements:
            node_type = structure_info.primary_node_types.get(ndpr_id, 'Simple')

            if node_type.startswith('Contenedor Virtual'):
                # Centroid of member positions
                vc_members = structure_info.get_vc_members(ndpr_id)
                if vc_members:
                    member_positions = [
                        raw_positions[m]
                        for m in vc_members
                        if m in raw_positions
                    ]
                    if member_positions:
                        cx = sum(p[0] for p in member_positions) / len(member_positions)
                        cy = sum(p[1] for p in member_positions) / len(member_positions)
                        ndpr_pos[ndpr_id] = (cx, cy)
            elif ndpr_id in raw_positions:
                ndpr_pos[ndpr_id] = raw_positions[ndpr_id]

        return ndpr_pos

    def _draw_ndpr_node(self, dwg, ndpr_id, cx, cy, structure_info, radius=12,
                        color_fn=None):
        """
        Draw a single NdDp node: rounded rect for VCs, circle for others.

        Args:
            color_fn: Optional callable(ndpr_id, structure_info) -> fill_color.
                      If None, uses default type-based coloring.
        """
        node_type = structure_info.primary_node_types.get(ndpr_id, 'Simple')
        is_vc = node_type == 'Contenedor Virtual TOI'
        node_id = structure_info.primary_node_ids.get(ndpr_id, ndpr_id)

        if color_fn:
            fill_color = color_fn(ndpr_id, structure_info)
        elif is_vc:
            fill_color = '#9b59b6'
        elif node_type == 'Contenedor':
            fill_color = '#ffc107'
        else:
            fill_color = '#0d6efd'

        if is_vc:
            vc_w, vc_h = radius * 2.5, radius * 1.8
            dwg.add(dwg.rect(
                insert=(cx - vc_w / 2, cy - vc_h / 2),
                size=(vc_w, vc_h),
                rx=8, ry=8,
                fill=fill_color, opacity=0.8,
                stroke='#212529', stroke_width=2
            ))
        else:
            dwg.add(dwg.circle(
                center=(cx, cy), r=radius,
                fill=fill_color, opacity=0.8,
                stroke='#212529', stroke_width=2
            ))

        return node_id, is_vc

    # Helper extraído de phase5_optimized.py
    def _draw_elements_with_ndfn(self, dwg, layout, ndfn_labels):
        """
        Dibuja todos los elementos del layout con etiquetas NdFn.
        Contenedores en amarillo semitransparente, elementos normales en azul.
        """
        for elem in layout.elements:
            if 'x' not in elem or 'y' not in elem:
                continue

            x = elem['x']
            y = elem['y']
            w = elem.get('width', ICON_WIDTH)
            h = elem.get('height', ICON_HEIGHT)
            elem_id = elem.get('id', '')

            if 'contains' in elem:
                fill_color = '#ffc107'
                stroke_color = '#ff9800'
                opacity = 0.3
            else:
                fill_color = '#0d6efd'
                stroke_color = '#084298'
                opacity = 0.7

            dwg.add(dwg.rect(
                insert=(x, y),
                size=(w, h),
                fill=fill_color,
                stroke=stroke_color,
                stroke_width=2,
                opacity=opacity
            ))

            dwg.add(dwg.text(
                elem_id,
                insert=(x + w/2, y + h/2),
                text_anchor='middle',
                font_size='10px',
                fill='#212529',
                font_family='monospace'
            ))

            ndfn = ndfn_labels.get(elem_id, '')
            if ndfn:
                dwg.add(dwg.text(
                    ndfn,
                    insert=(x + 2, y + 10),
                    font_size='8px',
                    fill='#dc3545',
                    font_family='monospace',
                    font_weight='bold'
                ))

            ndfn_icon = ndfn_labels.get(f"{elem_id}__icon", '')
            if ndfn_icon:
                dwg.add(dwg.text(
                    ndfn_icon,
                    insert=(x + 2, y + 20),
                    font_size='8px',
                    fill='#e85d04',
                    font_family='monospace',
                    font_weight='bold'
                ))

    # Helper extraído de phase5_optimized.py
    def _draw_straight_connections(self, dwg, layout):
        """
        Dibuja conexiones como líneas rectas entre centros de elementos.
        Usado en fases sin routing (6, 7).
        """
        import math

        elements_by_id = {e['id']: e for e in layout.elements if 'x' in e}

        for conn in layout.connections:
            from_id = conn.get('from', '')
            to_id = conn.get('to', '')

            from_elem = elements_by_id.get(from_id)
            to_elem = elements_by_id.get(to_id)
            if not from_elem or not to_elem:
                continue

            fx = from_elem['x'] + from_elem.get('width', ICON_WIDTH) / 2
            fy = from_elem['y'] + from_elem.get('height', ICON_HEIGHT) / 2
            tx = to_elem['x'] + to_elem.get('width', ICON_WIDTH) / 2
            ty = to_elem['y'] + to_elem.get('height', ICON_HEIGHT) / 2

            dwg.add(dwg.line(
                start=(fx, fy), end=(tx, ty),
                stroke='#adb5bd',
                stroke_width=1.2,
                opacity=0.5
            ))

            # Flecha
            angle = math.atan2(ty - fy, tx - fx)
            arrow_len = 8
            arrow_w = 0.4
            dwg.add(dwg.polygon(
                points=[
                    (tx, ty),
                    (tx - arrow_len * math.cos(angle + arrow_w),
                     ty - arrow_len * math.sin(angle + arrow_w)),
                    (tx - arrow_len * math.cos(angle - arrow_w),
                     ty - arrow_len * math.sin(angle - arrow_w))
                ],
                fill='#adb5bd', opacity=0.5
            ))

    # Helper extraído de phase5_optimized.py
    def _draw_routed_connections(self, dwg, layout):
        """
        Dibuja conexiones usando computed_path calculado por el router.
        Usado en fases con routing (8, 9).
        """
        import math

        for conn in layout.connections:
            computed_path = conn.get('computed_path')
            if not computed_path:
                continue
            points = computed_path.get('points', [])
            if len(points) < 2:
                continue

            path_str = f"M {points[0][0]} {points[0][1]}"
            for x, y in points[1:]:
                path_str += f" L {x} {y}"

            dwg.add(dwg.path(
                d=path_str,
                stroke='#6c757d',
                stroke_width=2,
                fill='none',
                opacity=0.6
            ))

            # Flecha en el punto final
            if len(points) >= 2:
                px, py = points[-2]
                tx, ty = points[-1]
                angle = math.atan2(ty - py, tx - px)
                arrow_len = 8
                arrow_w = 0.4
                dwg.add(dwg.polygon(
                    points=[
                        (tx, ty),
                        (tx - arrow_len * math.cos(angle + arrow_w),
                         ty - arrow_len * math.sin(angle + arrow_w)),
                        (tx - arrow_len * math.cos(angle - arrow_w),
                         ty - arrow_len * math.sin(angle - arrow_w))
                    ],
                    fill='#6c757d', opacity=0.6
                ))

    # Helper extraído de phase8_inflated.py
    def _build_ndfn_labels(self, layout, structure_info):
        """
        Construye etiquetas NdFn (Nodo Final) para cada elemento.

        Formato:
        - Nodo primario simple:        NdFn.AAA.NdDpXX-YYY.0
        - Contenedor box:              NdFn.AAA.NdDpXX-YYY.0
        - Contenedor ícono:            NdFn.AAA.NdDpXX-YYY.1 (skip si virtual)
        - Elementos contenidos:        NdFn.AAA.NdDpXX-YYY.2, .3, .4...

        AAA = secuencial global, NdDpXX-YYY = NdDp ID del elemento
        """
        labels = {}
        if not structure_info:
            return labels

        # Mapear elem_id → NdDp ID (todos los elementos)
        nddp_map = dict(structure_info.all_node_ids)

        # Mapear contenedores: elem_id → lista de hijos
        container_children = {}
        elements_by_id = {e['id']: e for e in layout.elements}
        for elem_id, elem in elements_by_id.items():
            if 'contains' in elem and elem['contains']:
                children = []
                for item in elem['contains']:
                    child_id = extract_item_id(item)
                    children.append(child_id)
                container_children[elem_id] = children

        # Asignar AAA secuencial global
        aaa = 1
        for elem_id in structure_info.primary_elements:
            nddp = nddp_map.get(elem_id, 'NdDp00-000')
            node_type = structure_info.primary_node_types.get(elem_id, 'Simple')
            is_container = elem_id in container_children
            is_virtual = node_type == 'Contenedor Virtual'

            # .0 = el box del contenedor o el nodo simple
            labels[elem_id] = f"NdFn.{aaa:03d}.{nddp}.0"
            aaa += 1

            if is_container:
                # .1 = ícono del contenedor (skip si virtual)
                if not is_virtual:
                    labels[f"{elem_id}__icon"] = f"NdFn.{aaa:03d}.{nddp}.1"
                    aaa += 1

                # .2, .3, .4... = elementos contenidos
                sub_idx = 2
                for child_id in container_children[elem_id]:
                    child_nddp = nddp_map.get(child_id, 'NdDp00-000')
                    labels[child_id] = f"NdFn.{aaa:03d}.{child_nddp}.{sub_idx}"
                    aaa += 1
                    sub_idx += 1

        return labels

    def _generate_phase1_svg(self, output_path: str) -> None:
        from AlmaGag.layout.laf.visualizer import phase1
        phase1.generate(self, output_path)

    def _generate_phase2_topology_svg(self, output_path: str) -> None:
        from AlmaGag.layout.laf.visualizer import phase2_topology
        phase2_topology.generate(self, output_path)

    def _generate_phase3_centrality_svg(self, output_path: str) -> None:
        from AlmaGag.layout.laf.visualizer import phase3_centrality
        phase3_centrality.generate(self, output_path)

    def _generate_phase4_abstract_svg(self, output_path: str) -> None:
        from AlmaGag.layout.laf.visualizer import phase4_abstract
        phase4_abstract.generate(self, output_path)

    def _generate_phase5_optimized_svg(self, output_path: str) -> None:
        from AlmaGag.layout.laf.visualizer import phase5_optimized
        phase5_optimized.generate(self, output_path)

    def _generate_phase7_iterative_svg(self, output_path: str) -> None:
        from AlmaGag.layout.laf.visualizer import phase7_iterative
        phase7_iterative.generate(self, output_path)

    def _generate_phase8_inflated_svg(self, output_path: str) -> None:
        from AlmaGag.layout.laf.visualizer import phase8_inflated
        phase8_inflated.generate(self, output_path)

    def _generate_phase9_redistributed_svg(self, output_path: str) -> None:
        from AlmaGag.layout.laf.visualizer import phase9_redistributed
        phase9_redistributed.generate(self, output_path)

    def _generate_phase10_routed_svg(self, output_path: str) -> None:
        from AlmaGag.layout.laf.visualizer import phase10_routed
        phase10_routed.generate(self, output_path)

    def _generate_phase11_final_svg(self, output_path: str) -> None:
        from AlmaGag.layout.laf.visualizer import phase11_final
        phase11_final.generate(self, output_path)
