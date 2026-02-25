"""
GrowthVisualizer - Fase de Visualización de LAF

Genera snapshots SVG de cada fase del proceso LAF para debugging
y documentación.

Author: José + ALMA + Claude (Claude-SolFase5)
Version: v1.1
Date: 2026-02-15
"""

import os
import logging
import svgwrite
from typing import Dict, List, Tuple
from copy import deepcopy
from AlmaGag.config import ICON_WIDTH, ICON_HEIGHT
from AlmaGag.utils import extract_item_id

logger = logging.getLogger('AlmaGag')


class GrowthVisualizer:
    """
    Genera visualizaciones SVG del proceso de crecimiento LAF.

    Crea 10 archivos SVG mostrando cada fase:
    1. phase1_structure.svg: Árbol de elementos con métricas
    2. phase2_topology.svg: Niveles topológicos y accessibility scores
    3. phase3_centrality.svg: Ordenamiento por centralidad
    4. phase4_abstract.svg: Posiciones abstractas (puntos)
    5. phase5_optimized.svg: Posiciones optimizadas (Claude-SolFase5)
    6. phase6_inflated.svg: Inflación + Contenedores expandidos
    7. phase7_redistributed.svg: Redistribución vertical
    8. phase8_routed.svg: Routing de conexiones
    9. phase9_final.svg: Layout final completo
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

    def capture_phase6_inflated(
        self,
        layout,
        spacing: float,
        structure_info=None
    ) -> None:
        """
        Captura snapshot de Fase 6 (Inflación + Contenedores).

        Args:
            layout: Layout con elementos inflados y contenedores expandidos
            spacing: Spacing calculado
            structure_info: Información estructural con primary_node_ids
        """
        self.snapshots['phase6'] = {
            'layout': deepcopy(layout),
            'spacing': spacing,
            'structure_info': structure_info
        }

    def capture_phase7_redistributed(
        self,
        layout,
        structure_info=None
    ) -> None:
        """
        Captura snapshot de Fase 7 (Redistribución vertical).

        Args:
            layout: Layout después de redistribución vertical
            structure_info: Información estructural para NdFn labels
        """
        self.snapshots['phase7'] = {
            'layout': deepcopy(layout),
            'structure_info': structure_info
        }

    def capture_phase8_routed(
        self,
        layout,
        structure_info=None
    ) -> None:
        """
        Captura snapshot de Fase 8 (Routing).

        Args:
            layout: Layout con paths de conexiones calculados
            structure_info: Información estructural para NdFn labels
        """
        self.snapshots['phase8'] = {
            'layout': deepcopy(layout),
            'structure_info': structure_info
        }

    def capture_phase9_final(
        self,
        layout,
        structure_info=None
    ) -> None:
        """
        Captura snapshot de Fase 9 (Generación SVG final).

        Args:
            layout: Layout final completo
            structure_info: Información estructural para NdFn labels
        """
        self.snapshots['phase9'] = {
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

        if 'phase6' in self.snapshots:
            self._generate_phase6_inflated_svg(output_path)

        if 'phase7' in self.snapshots:
            self._generate_phase7_redistributed_svg(output_path)

        if 'phase8' in self.snapshots:
            self._generate_phase8_routed_svg(output_path)

        if 'phase9' in self.snapshots:
            self._generate_phase9_final_svg(output_path)

        if self.debug:
            logger.debug(f"[VISUALIZER] Generación completada: {len(self.snapshots)} fases")

    def _generate_phase1_svg(self, output_path: str) -> None:
        """
        Genera SVG de Fase 1: Estructura del diagrama.
        """
        snapshot = self.snapshots['phase1']
        structure_info = snapshot['structure_info']

        filename = os.path.join(output_path, "phase1_structure.svg")

        # Canvas dinámico: altura basada en cantidad de NdPr + VCs
        canvas_width = 800
        ndpr_count = len(structure_info.primary_node_ids)
        vc_count = len(structure_info.toi_virtual_containers)
        # ~200px header + 16px per NdPr + 14px per VC detail + 80px legend
        canvas_height = max(600, 200 + (ndpr_count + vc_count) * 18 + 100)

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

        # Tabla de nodos primarios (NdPr)
        y += 20
        dwg.add(dwg.text(
            'Primary Nodes (NdPr):',
            insert=(40, y),
            font_size='16px',
            font_weight='bold',
            fill='#212529'
        ))
        y += 25

        # Header de tabla
        dwg.add(dwg.text(
            'ID         Type                      Element',
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
            'Contenedor Virtual TOI': '#9b59b6',
            'Contenedor Virtual': '#dc3545',
        }

        # Build sorted NdPr list (all entries that have a NdPr ID)
        ndpr_entries = sorted(
            structure_info.primary_node_ids.items(),
            key=lambda x: x[1]  # sort by NdPr001, NdPr002, ...
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

            # For TOI VCs, show member count
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

            # For TOI VCs, show contained members indented
            if node_type == 'Contenedor Virtual TOI':
                # Find the VC by id
                for vc in structure_info.toi_virtual_containers:
                    if vc['id'] == entry_id:
                        members_sorted = sorted(vc['members'])
                        members_str = ', '.join(members_sorted)
                        if len(members_str) > 55:
                            members_str = members_str[:52] + '...'
                        dwg.add(dwg.text(
                            f"         └ {members_str}",
                            insert=(60, y),
                            font_size='10px',
                            fill='#b07dd6',
                            font_family='monospace'
                        ))
                        y += 14
                        displayed_count += 1
                        break

        # Leyenda de colores
        y += 10
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

        for label, color in legend_items:
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

        # Badge
        dwg.add(dwg.text(
            'Phase 1/9',
            insert=(canvas_width - 100, 30),
            font_size='14px',
            fill='#6c757d'
        ))

        dwg.save()

        if self.debug:
            logger.debug(f"[VISUALIZER] Generado: {filename}")

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

    def _generate_phase2_topology_svg(self, output_path: str) -> None:
        """
        Genera SVG de Fase 2: Análisis topológico.
        Muestra niveles topológicos, IDs de nodos primarios, nombres y conexiones.
        Detecta y resalta conexiones que se cruzan.
        """
        snapshot = self.snapshots['phase2']
        structure_info = snapshot['structure_info']

        filename = os.path.join(output_path, "phase2_topology.svg")

        # Organizar NdPr por nivel (vista colapsada)
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
                if self._segments_intersect(
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

                    if self._are_collinear(conn1, conn2):
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
                    for vc in structure_info.toi_virtual_containers:
                        if vc['id'] == elem_id:
                            label = f"VC ({len(vc['members'])} elem)"
                            break
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
                    for vc in structure_info.toi_virtual_containers:
                        if vc['id'] == elem_id:
                            # Show TOI name inside VC
                            toi_label = vc.get('toi_id', '')
                            if len(toi_label) > 10:
                                toi_label = toi_label[:8] + '..'
                            dwg.add(dwg.text(
                                toi_label,
                                insert=(node_x, node_y + 4),
                                font_size='9px',
                                fill='white',
                                text_anchor='middle',
                                font_weight='bold',
                                font_family='monospace'
                            ))
                            break
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
            'Phase 2/9',
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

        if self.debug:
            logger.debug(f"[VISUALIZER] Generado: {filename}")

    def _build_ndpr_positions(self, raw_positions, structure_info):
        """
        Collapse raw element positions into NdPr-level positions.

        Simple NdPr nodes keep their position. TOI VCs get the centroid
        of their member positions.

        Returns: {ndpr_id: (x, y)}
        """
        ndpr_pos = {}

        for ndpr_id in structure_info.ndpr_elements:
            node_type = structure_info.primary_node_types.get(ndpr_id, 'Simple')

            if node_type == 'Contenedor Virtual TOI':
                # Centroid of member positions
                for vc in structure_info.toi_virtual_containers:
                    if vc['id'] == ndpr_id:
                        member_positions = [
                            raw_positions[m]
                            for m in vc['members']
                            if m in raw_positions
                        ]
                        if member_positions:
                            cx = sum(p[0] for p in member_positions) / len(member_positions)
                            cy = sum(p[1] for p in member_positions) / len(member_positions)
                            ndpr_pos[ndpr_id] = (cx, cy)
                        break
            elif ndpr_id in raw_positions:
                ndpr_pos[ndpr_id] = raw_positions[ndpr_id]

        return ndpr_pos

    def _draw_ndpr_node(self, dwg, ndpr_id, cx, cy, structure_info, radius=12,
                        color_fn=None):
        """
        Draw a single NdPr node: rounded rect for VCs, circle for others.

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

    def _generate_phase3_centrality_svg(self, output_path: str) -> None:
        """
        Genera SVG de Fase 3: Ordenamiento por centralidad.

        Muestra cómo los nodos se ordenan dentro de cada nivel según su accessibility score.
        """
        if 'phase3' not in self.snapshots:
            if self.debug:
                logger.warning(f"[VISUALIZER] No hay datos de Phase 3 para generar")
            return

        phase3_data = self.snapshots.get('phase3', {})
        structure_info = phase3_data.get('structure_info')
        centrality_order = phase3_data.get('centrality_order', {})

        if not structure_info or not centrality_order:
            if self.debug:
                logger.warning(f"[VISUALIZER] Datos incompletos para Phase 3")
            return

        filename = os.path.join(output_path, 'phase3_centrality.svg')

        # Collapse centrality_order to NdPr level
        use_ndpr = bool(structure_info.ndpr_elements)
        if use_ndpr:
            # Build NdPr-level centrality: aggregate scores per NdPr per level
            ndpr_scores = {}  # {ndpr_id: max_score}
            for level, elements in centrality_order.items():
                for elem_id, score in elements:
                    ndpr_id = structure_info.element_to_ndpr.get(elem_id, elem_id)
                    if ndpr_id not in ndpr_scores or score > ndpr_scores[ndpr_id]:
                        ndpr_scores[ndpr_id] = score

            # Build NdPr centrality_order using ndpr_topological_levels
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
            f'NdPr nodes ordered by accessibility score within each level',
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
        self._draw_colored_connections(dwg, all_node_positions,
                                       conn_graph, node_radius=node_radius)

        # Dibujar nodos NdPr
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

                self._draw_ndpr_node(dwg, elem_id, x, y, structure_info,
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
                    for vc in structure_info.toi_virtual_containers:
                        if vc['id'] == elem_id:
                            toi_label = vc.get('toi_id', '')
                            if len(toi_label) > 10:
                                toi_label = toi_label[:8] + '..'
                            dwg.add(dwg.text(
                                toi_label,
                                insert=(x, y + 4),
                                font_size='8px',
                                fill='white',
                                text_anchor='middle',
                                font_weight='bold',
                                font_family='monospace'
                            ))
                            break
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
                    for vc in structure_info.toi_virtual_containers:
                        if vc['id'] == elem_id:
                            label = f"VC ({len(vc['members'])} elem)"
                            break
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
            'NdPr nodes ordered: Higher scores toward center, lower scores toward edges',
            insert=(20, legend_y + 80 + 20),
            font_size='11px',
            fill='#6c757d',
            font_style='italic'
        ))

        # Badge
        dwg.add(dwg.text(
            'Phase 3/9',
            insert=(canvas_width - 100, 30),
            font_size='14px',
            fill='#6c757d'
        ))

        dwg.save()

        if self.debug:
            logger.debug(f"[VISUALIZER] Generado: {filename}")

    def _generate_phase4_abstract_svg(self, output_path: str) -> None:
        """
        Genera SVG de Fase 4: Layout abstracto (NdPr nodes only).
        VCs shown as rounded rectangles with centroid of member positions.
        """
        snapshot = self.snapshots['phase4']
        abstract_positions = snapshot['abstract_positions']
        crossings = snapshot['crossings']
        connections = snapshot['connections']
        structure_info = snapshot['structure_info']

        filename = os.path.join(output_path, "phase4_abstract.svg")

        # Build NdPr positions (collapse VCs to centroids)
        use_ndpr = bool(structure_info.ndpr_elements)
        if use_ndpr:
            # Filter raw positions to primary elements only
            raw_positions = {
                eid: pos for eid, pos in abstract_positions.items()
                if eid in structure_info.primary_elements
            }
            ndpr_positions = self._build_ndpr_positions(raw_positions, structure_info)
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
        self._draw_colored_connections(dwg, canvas_positions, conn_graph, node_radius=14)

        # Draw NdPr nodes
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

            self._draw_ndpr_node(dwg, ndpr_id, cx, cy, structure_info,
                                 radius=node_radius,
                                 color_fn=lambda eid, si, c=fill_color: c)

            node_id = structure_info.primary_node_ids.get(ndpr_id, ndpr_id)

            # ARRIBA: NdPrXXX
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
                for vc in structure_info.toi_virtual_containers:
                    if vc['id'] == ndpr_id:
                        toi_label = vc.get('toi_id', '')
                        if len(toi_label) > 10:
                            toi_label = toi_label[:8] + '..'
                        dwg.add(dwg.text(
                            toi_label,
                            insert=(cx, cy + 4),
                            font_size='8px',
                            fill='white',
                            text_anchor='middle',
                            font_family='monospace',
                            font_weight='bold'
                        ))
                        break
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
                for vc in structure_info.toi_virtual_containers:
                    if vc['id'] == ndpr_id:
                        elem_name = f"VC ({len(vc['members'])} elem)"
                        break
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
            'Phase 4/9',
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

        if self.debug:
            logger.debug(f"[VISUALIZER] Generado: {filename}")

    def _generate_phase5_optimized_svg(self, output_path: str) -> None:
        """
        Genera SVG de Fase 5: Posiciones optimizadas (NdPr nodes only).
        VCs shown as rounded rectangles with centroid of member positions.
        """
        snapshot = self.snapshots['phase5']
        optimized_positions = snapshot['optimized_positions']
        crossings = snapshot['crossings']
        connections = snapshot['connections']
        structure_info = snapshot['structure_info']

        filename = os.path.join(output_path, "phase5_optimized.svg")

        # Build NdPr positions
        use_ndpr = bool(structure_info.ndpr_elements)
        if use_ndpr:
            raw_positions = {
                eid: pos for eid, pos in optimized_positions.items()
                if eid in structure_info.primary_elements
            }
            ndpr_positions = self._build_ndpr_positions(raw_positions, structure_info)
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
        self._draw_colored_connections(dwg, canvas_positions, conn_graph, node_radius=14)

        # Draw NdPr nodes
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

            self._draw_ndpr_node(dwg, ndpr_id, cx, cy, structure_info,
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
                for vc in structure_info.toi_virtual_containers:
                    if vc['id'] == ndpr_id:
                        toi_label = vc.get('toi_id', '')
                        if len(toi_label) > 10:
                            toi_label = toi_label[:8] + '..'
                        dwg.add(dwg.text(
                            toi_label,
                            insert=(cx, cy + 4),
                            font_size='8px',
                            fill='white',
                            text_anchor='middle',
                            font_family='monospace',
                            font_weight='bold'
                        ))
                        break
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
                for vc in structure_info.toi_virtual_containers:
                    if vc['id'] == ndpr_id:
                        elem_name = f"VC ({len(vc['members'])} elem)"
                        break
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
            'Phase 5/9 - Claude-SolFase5',
            insert=(canvas_width - 260, 30),
            font_size='14px',
            fill='#28a745',
            font_weight='bold'
        ))

        dwg.save()

        if self.debug:
            logger.debug(f"[VISUALIZER] Generado: {filename}")

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

    def _generate_phase6_inflated_svg(self, output_path: str) -> None:
        """
        Genera SVG de Fase 6: Inflación + Contenedores expandidos.
        """
        snapshot = self.snapshots['phase6']
        layout = snapshot['layout']
        spacing = snapshot['spacing']
        structure_info = snapshot.get('structure_info')

        filename = os.path.join(output_path, "phase6_inflated_grown.svg")

        canvas_width = layout.canvas.get('width', 2000)
        canvas_height = layout.canvas.get('height', 2000)

        dwg = svgwrite.Drawing(filename, size=(canvas_width, canvas_height))
        dwg.add(dwg.rect(insert=(0, 0), size=(canvas_width, canvas_height), fill='#ffffff'))

        dwg.add(dwg.text(
            'LAF Phase 6: Inflation + Container Growth',
            insert=(20, 30), font_size='20px', font_weight='bold', fill='#212529'
        ))
        dwg.add(dwg.text(
            f"Spacing: {spacing:.0f}px",
            insert=(20, 55), font_size='14px', fill='#6c757d'
        ))

        ndfn_labels = self._build_ndfn_labels(layout, structure_info)
        self._draw_straight_connections(dwg, layout)
        self._draw_elements_with_ndfn(dwg, layout, ndfn_labels)

        dwg.add(dwg.text(
            'Phase 6/9', insert=(canvas_width - 100, 30),
            font_size='14px', fill='#6c757d'
        ))

        dwg.save()
        if self.debug:
            logger.debug(f"[VISUALIZER] Generado: {filename}")

    def _build_ndfn_labels(self, layout, structure_info):
        """
        Construye etiquetas NdFn (Nodo Final) para cada elemento.

        Formato:
        - Nodo primario simple:        NdFn.AAA.XXX.0
        - Contenedor box:              NdFn.AAA.XXX.0
        - Contenedor ícono:            NdFn.AAA.XXX.1 (skip si virtual)
        - Elementos contenidos:        NdFn.AAA.XXX.2, .3, .4...

        AAA = secuencial global, XXX = NdPr histórico
        """
        labels = {}
        if not structure_info:
            return labels

        # Mapear elem_id → NdPr number
        ndpr_map = {}
        for elem_id, ndpr_id in structure_info.primary_node_ids.items():
            # Extraer número de "NdPr001" → "001"
            ndpr_map[elem_id] = ndpr_id.replace('NdPr', '')

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
            xxx = ndpr_map.get(elem_id, '000')
            node_type = structure_info.primary_node_types.get(elem_id, 'Simple')
            is_container = elem_id in container_children
            is_virtual = node_type == 'Contenedor Virtual'

            # .0 = el box del contenedor o el nodo simple
            labels[elem_id] = f"NdFn.{aaa:03d}.{xxx}.0"
            aaa += 1

            if is_container:
                # .1 = ícono del contenedor (skip si virtual)
                if not is_virtual:
                    # El ícono del contenedor es el propio elem_id
                    # pero como nodo visual dentro del contenedor
                    # Lo marcamos como sub-índice 1
                    labels[f"{elem_id}__icon"] = f"NdFn.{aaa:03d}.{xxx}.1"
                    aaa += 1

                # .2, .3, .4... = elementos contenidos
                sub_idx = 2
                for child_id in container_children[elem_id]:
                    labels[child_id] = f"NdFn.{aaa:03d}.{xxx}.{sub_idx}"
                    aaa += 1
                    sub_idx += 1

        return labels

    def _generate_phase7_redistributed_svg(self, output_path: str) -> None:
        """
        Genera SVG de Fase 7: Redistribución vertical.
        """
        snapshot = self.snapshots['phase7']
        layout = snapshot['layout']
        structure_info = snapshot.get('structure_info')

        filename = os.path.join(output_path, "phase7_redistributed.svg")

        canvas_width = layout.canvas.get('width', 2000)
        canvas_height = layout.canvas.get('height', 2000)

        dwg = svgwrite.Drawing(filename, size=(canvas_width, canvas_height))
        dwg.add(dwg.rect(insert=(0, 0), size=(canvas_width, canvas_height), fill='#ffffff'))

        dwg.add(dwg.text(
            'LAF Phase 7: Vertical Redistribution',
            insert=(20, 30), font_size='20px', font_weight='bold', fill='#212529'
        ))

        ndfn_labels = self._build_ndfn_labels(layout, structure_info)
        self._draw_straight_connections(dwg, layout)
        self._draw_elements_with_ndfn(dwg, layout, ndfn_labels)

        dwg.add(dwg.text(
            'Phase 7/9', insert=(canvas_width - 100, 30),
            font_size='14px', fill='#6c757d'
        ))

        dwg.save()
        if self.debug:
            logger.debug(f"[VISUALIZER] Generado: {filename}")

    def _generate_phase8_routed_svg(self, output_path: str) -> None:
        """
        Genera SVG de Fase 8: Routing de conexiones.
        """
        snapshot = self.snapshots['phase8']
        layout = snapshot['layout']
        structure_info = snapshot.get('structure_info')

        filename = os.path.join(output_path, "phase8_routed.svg")

        canvas_width = layout.canvas.get('width', 2000)
        canvas_height = layout.canvas.get('height', 2000)

        dwg = svgwrite.Drawing(filename, size=(canvas_width, canvas_height))
        dwg.add(dwg.rect(insert=(0, 0), size=(canvas_width, canvas_height), fill='#ffffff'))

        dwg.add(dwg.text(
            'LAF Phase 8: Connection Routing',
            insert=(20, 30), font_size='20px', font_weight='bold', fill='#212529'
        ))

        ndfn_labels = self._build_ndfn_labels(layout, structure_info)
        self._draw_routed_connections(dwg, layout)
        self._draw_elements_with_ndfn(dwg, layout, ndfn_labels)

        dwg.add(dwg.text(
            'Phase 8/9', insert=(canvas_width - 100, 30),
            font_size='14px', fill='#6c757d'
        ))

        dwg.save()
        if self.debug:
            logger.debug(f"[VISUALIZER] Generado: {filename}")

    def _generate_phase9_final_svg(self, output_path: str) -> None:
        """
        Genera SVG de Fase 9: Generación SVG final.
        """
        snapshot = self.snapshots['phase9']
        layout = snapshot['layout']
        structure_info = snapshot.get('structure_info')

        filename = os.path.join(output_path, "phase9_final.svg")

        canvas_width = layout.canvas.get('width', 2000)
        canvas_height = layout.canvas.get('height', 2000)

        dwg = svgwrite.Drawing(filename, size=(canvas_width, canvas_height))
        dwg.add(dwg.rect(insert=(0, 0), size=(canvas_width, canvas_height), fill='#ffffff'))

        dwg.add(dwg.text(
            'LAF Phase 9: SVG Generation (COMPLETE)',
            insert=(20, 30), font_size='20px', font_weight='bold', fill='#28a745'
        ))

        ndfn_labels = self._build_ndfn_labels(layout, structure_info)
        self._draw_routed_connections(dwg, layout)
        self._draw_elements_with_ndfn(dwg, layout, ndfn_labels)

        dwg.add(dwg.text(
            'Phase 9/9 - COMPLETE', insert=(canvas_width - 240, 30),
            font_size='14px', fill='#28a745', font_weight='bold'
        ))

        dwg.save()
        if self.debug:
            logger.debug(f"[VISUALIZER] Generado: {filename}")
