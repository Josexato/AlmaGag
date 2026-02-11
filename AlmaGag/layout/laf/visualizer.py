"""
GrowthVisualizer - Fase 5 de LAF (Visualización del Proceso)

Genera snapshots SVG de cada fase del proceso LAF para debugging
y documentación.

Author: José + ALMA
Version: v1.0
Date: 2026-01-17
"""

import os
import svgwrite
from typing import Dict, List, Tuple
from copy import deepcopy
from AlmaGag.config import ICON_WIDTH, ICON_HEIGHT


class GrowthVisualizer:
    """
    Genera visualizaciones SVG del proceso de crecimiento LAF.

    Crea 8 archivos SVG mostrando cada fase:
    1. phase1_structure.svg: Árbol de elementos con métricas
    2. phase2_topology.svg: Niveles topológicos y accessibility scores
    3. phase3_abstract.svg: Posiciones abstractas (puntos)
    4. phase4_inflated.svg: Elementos con dimensiones reales
    5. phase5_containers.svg: Contenedores expandidos
    6. phase6_redistributed.svg: Redistribución vertical
    7. phase7_routed.svg: Routing de conexiones
    8. phase8_final.svg: Layout final completo
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

        if self.debug:
            print(f"[VISUALIZER] Phase 1 capturada")

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

        if self.debug:
            print(f"[VISUALIZER] Phase 2 capturada (topología)")

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

        if self.debug:
            print(f"[VISUALIZER] Phase 3 capturada (centralidad)")

    def capture_phase4_abstract(
        self,
        abstract_positions: Dict[str, Tuple[int, int]],
        crossings: int,
        layout
    ) -> None:
        """
        Captura snapshot de Fase 4 (Layout abstracto).

        Args:
            abstract_positions: {elem_id: (x, y)} en coordenadas abstractas
            crossings: Número de cruces detectados
            layout: Layout con conexiones
        """
        self.snapshots['phase4'] = {
            'abstract_positions': deepcopy(abstract_positions),
            'crossings': crossings,
            'connections': deepcopy(layout.connections)
        }

        if self.debug:
            print(f"[VISUALIZER] Phase 4 capturada ({crossings} cruces)")

    def capture_phase5_inflated(
        self,
        layout,
        spacing: float
    ) -> None:
        """
        Captura snapshot de Fase 5 (Inflación).

        Args:
            layout: Layout con elementos inflados
            spacing: Spacing calculado
        """
        self.snapshots['phase5'] = {
            'layout': deepcopy(layout),
            'spacing': spacing
        }

        if self.debug:
            print(f"[VISUALIZER] Phase 5 capturada (spacing={spacing:.1f}px)")

    def capture_phase6_containers(
        self,
        layout
    ) -> None:
        """
        Captura snapshot de Fase 6 (Crecimiento de contenedores).

        Args:
            layout: Layout con contenedores expandidos
        """
        self.snapshots['phase6'] = {
            'layout': deepcopy(layout)
        }

        if self.debug:
            print(f"[VISUALIZER] Phase 6 capturada")

    def capture_phase7_redistributed(
        self,
        layout
    ) -> None:
        """
        Captura snapshot de Fase 7 (Redistribución vertical).

        Args:
            layout: Layout después de redistribución vertical
        """
        self.snapshots['phase7'] = {
            'layout': deepcopy(layout)
        }

        if self.debug:
            print(f"[VISUALIZER] Phase 7 capturada")

    def capture_phase8_routed(
        self,
        layout
    ) -> None:
        """
        Captura snapshot de Fase 8 (Routing).

        Args:
            layout: Layout con paths de conexiones calculados
        """
        self.snapshots['phase8'] = {
            'layout': deepcopy(layout)
        }

        if self.debug:
            print(f"[VISUALIZER] Phase 8 capturada")

    def capture_phase9_final(
        self,
        layout
    ) -> None:
        """
        Captura snapshot de Fase 9 (Generación SVG final).

        Args:
            layout: Layout final completo
        """
        self.snapshots['phase9'] = {
            'layout': deepcopy(layout)
        }

        if self.debug:
            print(f"[VISUALIZER] Phase 9 capturada")

    def generate_all(self) -> None:
        """
        Genera todos los SVGs de visualización.
        """
        if not self.snapshots:
            if self.debug:
                print(f"[VISUALIZER] Warning: No hay snapshots capturados")
            return

        # Crear directorio de salida
        diagram_name = self.snapshots.get('phase1', {}).get('diagram_name', 'diagram')
        output_path = os.path.join(self.output_dir, diagram_name)
        os.makedirs(output_path, exist_ok=True)

        if self.debug:
            print(f"\n[VISUALIZER] Generando visualizaciones en: {output_path}")

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
            self._generate_phase5_inflated_svg(output_path)

        if 'phase6' in self.snapshots:
            self._generate_phase6_containers_svg(output_path)

        if 'phase7' in self.snapshots:
            self._generate_phase7_redistributed_svg(output_path)

        if 'phase8' in self.snapshots:
            self._generate_phase8_routed_svg(output_path)

        if 'phase9' in self.snapshots:
            self._generate_phase9_final_svg(output_path)

        if self.debug:
            print(f"[VISUALIZER] Generación completada: {len(self.snapshots)} fases")

    def _generate_phase1_svg(self, output_path: str) -> None:
        """
        Genera SVG de Fase 1: Estructura del diagrama.
        """
        snapshot = self.snapshots['phase1']
        structure_info = snapshot['structure_info']

        filename = os.path.join(output_path, "phase1_structure.svg")

        # Canvas pequeño para visualización
        canvas_width = 800
        canvas_height = 600

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

        # Tabla de nodos primarios
        y += 20
        dwg.add(dwg.text(
            'Primary Nodes:',
            insert=(40, y),
            font_size='16px',
            font_weight='bold',
            fill='#212529'
        ))
        y += 25

        # Header de tabla
        dwg.add(dwg.text(
            'ID         Type              Element',
            insert=(60, y),
            font_size='11px',
            fill='#495057',
            font_family='monospace',
            font_weight='bold'
        ))
        y += 18

        # Mostrar solo los primeros 15 elementos para que quepan en el SVG
        displayed_count = 0
        max_display = 15

        for elem_id in structure_info.primary_elements:
            if displayed_count >= max_display:
                dwg.add(dwg.text(
                    f"... y {len(structure_info.primary_elements) - max_display} más",
                    insert=(60, y),
                    font_size='11px',
                    fill='#6c757d',
                    font_family='monospace',
                    font_style='italic'
                ))
                break

            node_id = structure_info.primary_node_ids.get(elem_id, "N/A")
            node_type = structure_info.primary_node_types.get(elem_id, "N/A")

            # Color según tipo
            if node_type == "Simple":
                color = '#6c757d'  # Gris
            elif node_type == "Contenedor":
                color = '#0d6efd'  # Azul
            else:  # Contenedor Virtual
                color = '#dc3545'  # Rojo

            # Truncar elem_id si es muy largo
            elem_display = elem_id if len(elem_id) <= 20 else elem_id[:17] + "..."

            text = f"{node_id}  {node_type:<16}  {elem_display}"

            dwg.add(dwg.text(
                text,
                insert=(60, y),
                font_size='11px',
                fill=color,
                font_family='monospace'
            ))
            y += 16
            displayed_count += 1

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
            print(f"[VISUALIZER] Generado: {filename}")

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

        canvas_width = 1200
        canvas_height = 900

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

        # Organizar elementos por nivel
        by_level = {}
        max_level = 0
        for elem_id, level in structure_info.topological_levels.items():
            if level not in by_level:
                by_level[level] = []
            by_level[level].append(elem_id)
            max_level = max(max_level, level)

        # Calcular espacio vertical por nivel
        level_height = 100
        start_y = 120
        node_radius = 22

        # Diccionario para guardar posiciones de nodos (para dibujar flechas después)
        node_positions = {}

        # PASO 1: Calcular posiciones de todos los nodos
        for level in sorted(by_level.keys()):
            elements = by_level[level]
            y = start_y + level * level_height

            # Distribuir elementos horizontalmente
            num_elements = len(elements)
            spacing = (canvas_width - 240) / max(num_elements, 1)
            start_x = 140

            for i, elem_id in enumerate(elements):
                x = start_x + i * spacing
                node_positions[elem_id] = (x, y)

        # PASO 2: Calcular todas las conexiones y detectar cruces
        import math

        # Lista de todas las conexiones con sus coordenadas
        connections = []

        for from_id, to_list in structure_info.connection_graph.items():
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

                start_x = from_x + node_radius * math.cos(angle)
                start_y = from_y + node_radius * math.sin(angle)
                end_x = to_x - (node_radius + 8) * math.cos(angle)
                end_y = to_y - (node_radius + 8) * math.sin(angle)

                connections.append({
                    'from_id': from_id,
                    'to_id': to_id,
                    'start': (start_x, start_y),
                    'end': (end_x, end_y),
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

            # Dibujar bolita de origen (pequeña)
            origin_x, origin_y = conn['start']
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
                start=conn['start'],
                end=conn['end'],
                stroke=line_color,
                stroke_width=2,
                opacity=opacity
            ))

            # Dibujar punta de flecha
            arrow_length = 12
            arrow_width = 0.4

            angle = conn['angle']
            to_x, to_y = conn['to_pos']

            arrow_tip_x = to_x - node_radius * math.cos(angle)
            arrow_tip_y = to_y - node_radius * math.sin(angle)

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
            y = start_y + level * level_height

            # Barra de fondo para el nivel (alternando colores)
            bar_height = level_height - 20
            bar_y = y - 50
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
                insert=(20, y - 10),
                font_size='14px',
                font_weight='bold',
                fill='#495057'
            ))

            # Línea horizontal del nivel (más tenue)
            dwg.add(dwg.line(
                start=(120, y),
                end=(canvas_width - 20, y),
                stroke='#dee2e6',
                stroke_width=1,
                stroke_dasharray='5,5',
                opacity=0.5
            ))

            for elem_id in elements:
                x, y = node_positions[elem_id]
                score = structure_info.accessibility_scores.get(elem_id, 0)
                node_id = structure_info.primary_node_ids.get(elem_id, "N/A")

                # Color según score
                if score > 0.05:
                    color = '#dc3545'  # Rojo - Alto
                elif score > 0.02:
                    color = '#ffc107'  # Amarillo - Medio
                else:
                    color = '#0d6efd'  # Azul - Bajo/Normal

                # Dibujar nodo (círculo)
                dwg.add(dwg.circle(
                    center=(x, y),
                    r=node_radius,
                    fill=color,
                    opacity=0.8,
                    stroke='#212529',
                    stroke_width=2
                ))

                # ID del nodo primario ARRIBA del círculo
                dwg.add(dwg.text(
                    node_id,
                    insert=(x, y - node_radius - 8),
                    font_size='11px',
                    fill='#212529',
                    text_anchor='middle',
                    font_family='monospace',
                    font_weight='bold'
                ))

                # Nombre del elemento DEBAJO del círculo (en gris)
                label = elem_id if len(elem_id) <= 18 else elem_id[:15] + '...'
                dwg.add(dwg.text(
                    label,
                    insert=(x, y + node_radius + 16),
                    font_size='10px',
                    fill='#6c757d',
                    text_anchor='middle',
                    font_family='monospace'
                ))

                # Mostrar score DENTRO del círculo si > 0
                if score > 0:
                    dwg.add(dwg.text(
                        f'{score:.3f}',
                        insert=(x, y + 4),
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
            print(f"[VISUALIZER] Generado: {filename}")

    def _generate_phase3_centrality_svg(self, output_path: str) -> None:
        """
        Genera SVG de Fase 3: Ordenamiento por centralidad.

        Muestra cómo los nodos se ordenan dentro de cada nivel según su accessibility score.
        """
        if 'phase3' not in self.snapshots:
            if self.debug:
                print(f"[VISUALIZER] No hay datos de Phase 3 para generar")
            return

        phase3_data = self.snapshots.get('phase3', {})
        structure_info = phase3_data.get('structure_info')
        centrality_order = phase3_data.get('centrality_order', {})

        if not structure_info or not centrality_order:
            if self.debug:
                print(f"[VISUALIZER] Datos incompletos para Phase 3")
            return

        filename = os.path.join(output_path, 'phase3_centrality.svg')
        canvas_width = 1200
        canvas_height = 900

        dwg = svgwrite.Drawing(filename, size=(canvas_width, canvas_height))

        # Fondo
        dwg.add(dwg.rect(insert=(0, 0), size=(canvas_width, canvas_height), fill='#f8f9fa'))

        # Título
        dwg.add(dwg.text(
            'LAF Phase 3: Centrality Ordering',
            insert=(20, 30),
            font_size='20px',
            font_weight='bold',
            fill='#212529'
        ))

        # Descripción
        dwg.add(dwg.text(
            f'Elements ordered by accessibility score within each level',
            insert=(20, 55),
            font_size='14px',
            fill='#6c757d'
        ))

        # Dibujar cada nivel con sus elementos ordenados
        start_y = 120
        level_height = 100

        for level in sorted(centrality_order.keys()):
            elements = centrality_order[level]
            y = start_y + level * level_height

            # Barra de fondo para el nivel
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

            # Label del nivel
            dwg.add(dwg.text(
                f'Level {level}',
                insert=(20, y - 15),
                font_size='14px',
                font_weight='bold',
                fill='#495057'
            ))

            # Calcular posiciones para los elementos (distribución horizontal)
            num_elements = len(elements)
            if num_elements > 0:
                spacing = min(80, (canvas_width - 100) / num_elements)
                start_x = (canvas_width - (num_elements - 1) * spacing) / 2

                for idx, (elem_id, score) in enumerate(elements):
                    x = start_x + idx * spacing
                    node_id = structure_info.primary_node_ids.get(elem_id, "N/A")

                    # Color según score
                    if score > 0.05:
                        color = '#dc3545'  # Rojo - Alto
                    elif score > 0.02:
                        color = '#ffc107'  # Amarillo - Medio
                    else:
                        color = '#0d6efd'  # Azul - Bajo/Normal

                    # Dibujar nodo (círculo)
                    radius = 15 if score > 0.02 else 12  # Nodos importantes más grandes
                    dwg.add(dwg.circle(
                        center=(x, y),
                        r=radius,
                        fill=color,
                        opacity=0.8,
                        stroke='#212529',
                        stroke_width=2
                    ))

                    # ID del nodo
                    dwg.add(dwg.text(
                        node_id,
                        insert=(x, y - radius - 5),
                        font_size='10px',
                        fill='#212529',
                        text_anchor='middle',
                        font_family='monospace',
                        font_weight='bold'
                    ))

                    # Score (si > 0)
                    if score > 0:
                        dwg.add(dwg.text(
                            f'{score:.3f}',
                            insert=(x, y + 4),
                            font_size='8px',
                            fill='white',
                            text_anchor='middle',
                            font_family='monospace',
                            font_weight='bold'
                        ))

                    # Nombre del elemento (debajo)
                    label = elem_id if len(elem_id) <= 12 else elem_id[:9] + '...'
                    dwg.add(dwg.text(
                        label,
                        insert=(x, y + radius + 15),
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

        # Nota sobre ordenamiento
        dwg.add(dwg.text(
            'Elements ordered: Higher scores toward center, lower scores toward edges',
            insert=(20, legend_y + 80),
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
            print(f"[VISUALIZER] Generado: {filename}")

    def _generate_phase4_abstract_svg(self, output_path: str) -> None:
        """
        Genera SVG de Fase 4: Layout abstracto (puntos).
        """
        snapshot = self.snapshots['phase4']
        abstract_positions = snapshot['abstract_positions']
        crossings = snapshot['crossings']
        connections = snapshot['connections']

        filename = os.path.join(output_path, "phase4_abstract.svg")

        # Calcular bounds del layout abstracto
        if not abstract_positions:
            return

        min_x = min(x for x, y in abstract_positions.values())
        max_x = max(x for x, y in abstract_positions.values())
        min_y = min(y for x, y in abstract_positions.values())
        max_y = max(y for x, y in abstract_positions.values())

        # Escalar al canvas
        padding = 100
        canvas_width = 1000
        canvas_height = 800

        scale_x = (canvas_width - 2 * padding) / max(1, max_x - min_x)
        scale_y = (canvas_height - 2 * padding) / max(1, max_y - min_y)
        scale = min(scale_x, scale_y, 50)  # Máximo 50px por unidad

        def to_canvas(ax, ay):
            cx = padding + (ax - min_x) * scale
            cy = padding + (ay - min_y) * scale
            return (cx, cy)

        dwg = svgwrite.Drawing(filename, size=(canvas_width, canvas_height))

        # Fondo
        dwg.add(dwg.rect(insert=(0, 0), size=(canvas_width, canvas_height), fill='#f8f9fa'))

        # Título
        dwg.add(dwg.text(
            'LAF Phase 3: Abstract Layout',
            insert=(20, 30),
            font_size='20px',
            font_weight='bold',
            fill='#212529'
        ))

        # Métricas
        dwg.add(dwg.text(
            f"Crossings: {crossings}",
            insert=(20, 55),
            font_size='16px',
            fill='#dc3545' if crossings > 3 else '#28a745',
            font_weight='bold'
        ))

        # Dibujar conexiones (líneas)
        for conn in connections:
            from_id = conn['from']
            to_id = conn['to']

            if from_id in abstract_positions and to_id in abstract_positions:
                from_x, from_y = to_canvas(*abstract_positions[from_id])
                to_x, to_y = to_canvas(*abstract_positions[to_id])

                dwg.add(dwg.line(
                    start=(from_x, from_y),
                    end=(to_x, to_y),
                    stroke='#adb5bd',
                    stroke_width=1,
                    opacity=0.6
                ))

        # Dibujar elementos (puntos)
        for elem_id, (ax, ay) in abstract_positions.items():
            cx, cy = to_canvas(ax, ay)

            # Punto
            dwg.add(dwg.circle(
                center=(cx, cy),
                r=5,
                fill='#0d6efd',
                stroke='#084298',
                stroke_width=2
            ))

            # Label
            dwg.add(dwg.text(
                elem_id,
                insert=(cx + 10, cy + 5),
                font_size='10px',
                fill='#212529',
                font_family='monospace'
            ))

        # Badge
        dwg.add(dwg.text(
            'Phase 4/9',
            insert=(canvas_width - 100, 30),
            font_size='14px',
            fill='#6c757d'
        ))

        dwg.save()

        if self.debug:
            print(f"[VISUALIZER] Generado: {filename}")

    def _generate_phase5_inflated_svg(self, output_path: str) -> None:
        """
        Genera SVG de Fase 5: Elementos inflados.
        """
        snapshot = self.snapshots['phase5']
        layout = snapshot['layout']
        spacing = snapshot['spacing']

        filename = os.path.join(output_path, "phase5_inflated.svg")

        # Canvas basado en elementos
        canvas_width = layout.canvas.get('width', 2000)
        canvas_height = layout.canvas.get('height', 2000)

        dwg = svgwrite.Drawing(filename, size=(canvas_width, canvas_height))

        # Fondo
        dwg.add(dwg.rect(insert=(0, 0), size=(canvas_width, canvas_height), fill='#ffffff'))

        # Título
        dwg.add(dwg.text(
            'LAF Phase 4: Inflated Elements',
            insert=(20, 30),
            font_size='20px',
            font_weight='bold',
            fill='#212529'
        ))

        # Métricas
        dwg.add(dwg.text(
            f"Spacing: {spacing:.0f}px",
            insert=(20, 55),
            font_size='14px',
            fill='#6c757d'
        ))

        # Dibujar elementos
        for elem in layout.elements:
            if 'x' not in elem or 'y' not in elem:
                continue

            x = elem['x']
            y = elem['y']
            w = elem.get('width', ICON_WIDTH)
            h = elem.get('height', ICON_HEIGHT)

            # Color según tipo
            if 'contains' in elem:
                # Contenedor (aún no expandido)
                fill_color = '#ffc107'
                stroke_color = '#ff9800'
                opacity = 0.3
            else:
                # Elemento normal
                fill_color = '#0d6efd'
                stroke_color = '#084298'
                opacity = 0.7

            # Rectángulo
            dwg.add(dwg.rect(
                insert=(x, y),
                size=(w, h),
                fill=fill_color,
                stroke=stroke_color,
                stroke_width=2,
                opacity=opacity
            ))

            # Label del elemento
            elem_id = elem.get('id', '')
            dwg.add(dwg.text(
                elem_id,
                insert=(x + w/2, y + h/2),
                text_anchor='middle',
                font_size='10px',
                fill='#212529',
                font_family='monospace'
            ))

        # Badge
        dwg.add(dwg.text(
            'Phase 5/9',
            insert=(canvas_width - 100, 30),
            font_size='14px',
            fill='#6c757d'
        ))

        dwg.save()

        if self.debug:
            print(f"[VISUALIZER] Generado: {filename}")

    def _generate_phase6_containers_svg(self, output_path: str) -> None:
        """
        Genera SVG de Fase 6: Contenedores expandidos.

        Similar al output final pero con anotaciones de debug.
        """
        snapshot = self.snapshots['phase6']
        layout = snapshot['layout']

        filename = os.path.join(output_path, "phase6_containers.svg")

        canvas_width = layout.canvas.get('width', 2000)
        canvas_height = layout.canvas.get('height', 2000)

        dwg = svgwrite.Drawing(filename, size=(canvas_width, canvas_height))

        # Fondo
        dwg.add(dwg.rect(insert=(0, 0), size=(canvas_width, canvas_height), fill='#ffffff'))

        # Título
        dwg.add(dwg.text(
            'LAF Phase 5: Container Growth',
            insert=(20, 30),
            font_size='20px',
            font_weight='bold',
            fill='#212529'
        ))

        # Dibujar contenedores primero (fondo)
        for elem in layout.elements:
            if 'contains' not in elem:
                continue

            if 'x' not in elem or 'y' not in elem or 'width' not in elem:
                continue

            x = elem['x']
            y = elem['y']
            w = elem['width']
            h = elem['height']

            # Contenedor
            dwg.add(dwg.rect(
                insert=(x, y),
                size=(w, h),
                fill='#e9ecef',
                stroke='#6c757d',
                stroke_width=2,
                opacity=0.5
            ))

        # Dibujar elementos normales
        for elem in layout.elements:
            if 'contains' in elem:
                continue

            if 'x' not in elem or 'y' not in elem:
                continue

            x = elem['x']
            y = elem['y']
            w = elem.get('width', ICON_WIDTH)
            h = elem.get('height', ICON_HEIGHT)

            # Elemento
            dwg.add(dwg.rect(
                insert=(x, y),
                size=(w, h),
                fill='#0d6efd',
                stroke='#084298',
                stroke_width=2
            ))

            # Label
            elem_id = elem.get('id', '')
            dwg.add(dwg.text(
                elem_id,
                insert=(x + w/2, y + h/2),
                text_anchor='middle',
                font_size='10px',
                fill='#ffffff',
                font_family='monospace',
                font_weight='bold'
            ))

        # Badge
        dwg.add(dwg.text(
            'Phase 6/9',
            insert=(canvas_width - 100, 30),
            font_size='14px',
            fill='#6c757d'
        ))

        dwg.save()

        if self.debug:
            print(f"[VISUALIZER] Generado: {filename}")

    def _generate_phase7_redistributed_svg(self, output_path: str) -> None:
        """
        Genera SVG de Fase 7: Redistribución vertical.
        """
        snapshot = self.snapshots['phase7']
        layout = snapshot['layout']

        filename = os.path.join(output_path, "phase7_redistributed.svg")

        canvas_width = layout.canvas.get('width', 2000)
        canvas_height = layout.canvas.get('height', 2000)

        dwg = svgwrite.Drawing(filename, size=(canvas_width, canvas_height))

        # Fondo
        dwg.add(dwg.rect(insert=(0, 0), size=(canvas_width, canvas_height), fill='#ffffff'))

        # Título
        dwg.add(dwg.text(
            'LAF Phase 6: Vertical Redistribution',
            insert=(20, 30),
            font_size='20px',
            font_weight='bold',
            fill='#212529'
        ))

        # Dibujar layout completo (similar a phase5)
        # Contenedores
        for elem in layout.elements:
            if 'contains' not in elem:
                continue

            if 'x' not in elem or 'y' not in elem or 'width' not in elem:
                continue

            x = elem['x']
            y = elem['y']
            w = elem['width']
            h = elem['height']

            dwg.add(dwg.rect(
                insert=(x, y),
                size=(w, h),
                fill='#e9ecef',
                stroke='#6c757d',
                stroke_width=2,
                opacity=0.5
            ))

        # Elementos
        for elem in layout.elements:
            if 'contains' in elem:
                continue

            if 'x' not in elem or 'y' not in elem:
                continue

            x = elem['x']
            y = elem['y']
            w = elem.get('width', ICON_WIDTH)
            h = elem.get('height', ICON_HEIGHT)

            dwg.add(dwg.rect(
                insert=(x, y),
                size=(w, h),
                fill='#0d6efd',
                stroke='#084298',
                stroke_width=2,
                opacity=0.8
            ))

            elem_id = elem.get('id', '')
            dwg.add(dwg.text(
                elem_id,
                insert=(x + w/2, y + h/2),
                text_anchor='middle',
                font_size='10px',
                fill='white',
                font_family='monospace'
            ))

        # Badge
        dwg.add(dwg.text(
            'Phase 7/9',
            insert=(canvas_width - 100, 30),
            font_size='14px',
            fill='#6c757d'
        ))

        dwg.save()

        if self.debug:
            print(f"[VISUALIZER] Generado: {filename}")

    def _generate_phase8_routed_svg(self, output_path: str) -> None:
        """
        Genera SVG de Fase 8: Routing de conexiones.
        """
        snapshot = self.snapshots['phase8']
        layout = snapshot['layout']

        filename = os.path.join(output_path, "phase8_routed.svg")

        canvas_width = layout.canvas.get('width', 2000)
        canvas_height = layout.canvas.get('height', 2000)

        dwg = svgwrite.Drawing(filename, size=(canvas_width, canvas_height))

        # Fondo
        dwg.add(dwg.rect(insert=(0, 0), size=(canvas_width, canvas_height), fill='#ffffff'))

        # Título
        dwg.add(dwg.text(
            'LAF Phase 7: Routing',
            insert=(20, 30),
            font_size='20px',
            font_weight='bold',
            fill='#212529'
        ))

        # Dibujar conexiones primero
        for conn in layout.connections:
            if 'path' in conn and conn['path']:
                points = conn['path']
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

        # Dibujar contenedores
        for elem in layout.elements:
            if 'contains' not in elem:
                continue

            if 'x' not in elem or 'y' not in elem or 'width' not in elem:
                continue

            x = elem['x']
            y = elem['y']
            w = elem['width']
            h = elem['height']

            dwg.add(dwg.rect(
                insert=(x, y),
                size=(w, h),
                fill='#e9ecef',
                stroke='#6c757d',
                stroke_width=2,
                opacity=0.5
            ))

        # Dibujar elementos
        for elem in layout.elements:
            if 'contains' in elem:
                continue

            if 'x' not in elem or 'y' not in elem:
                continue

            x = elem['x']
            y = elem['y']
            w = elem.get('width', ICON_WIDTH)
            h = elem.get('height', ICON_HEIGHT)

            dwg.add(dwg.rect(
                insert=(x, y),
                size=(w, h),
                fill='#0d6efd',
                stroke='#084298',
                stroke_width=2,
                opacity=0.8
            ))

        # Badge
        dwg.add(dwg.text(
            'Phase 8/9',
            insert=(canvas_width - 100, 30),
            font_size='14px',
            fill='#6c757d'
        ))

        dwg.save()

        if self.debug:
            print(f"[VISUALIZER] Generado: {filename}")

    def _generate_phase9_final_svg(self, output_path: str) -> None:
        """
        Genera SVG de Fase 9: Generación SVG final.
        """
        snapshot = self.snapshots['phase9']
        layout = snapshot['layout']

        filename = os.path.join(output_path, "phase9_final.svg")

        canvas_width = layout.canvas.get('width', 2000)
        canvas_height = layout.canvas.get('height', 2000)

        dwg = svgwrite.Drawing(filename, size=(canvas_width, canvas_height))

        # Fondo
        dwg.add(dwg.rect(insert=(0, 0), size=(canvas_width, canvas_height), fill='#ffffff'))

        # Título
        dwg.add(dwg.text(
            'LAF Phase 9: SVG Generation (COMPLETE)',
            insert=(20, 30),
            font_size='20px',
            font_weight='bold',
            fill='#28a745'
        ))

        # Dibujar conexiones
        for conn in layout.connections:
            if 'path' in conn and conn['path']:
                points = conn['path']
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

        # Dibujar contenedores
        for elem in layout.elements:
            if 'contains' not in elem:
                continue

            if 'x' not in elem or 'y' not in elem or 'width' not in elem:
                continue

            x = elem['x']
            y = elem['y']
            w = elem['width']
            h = elem['height']

            dwg.add(dwg.rect(
                insert=(x, y),
                size=(w, h),
                fill='#e9ecef',
                stroke='#6c757d',
                stroke_width=2,
                opacity=0.5
            ))

        # Dibujar elementos
        for elem in layout.elements:
            if 'contains' in elem:
                continue

            if 'x' not in elem or 'y' not in elem:
                continue

            x = elem['x']
            y = elem['y']
            w = elem.get('width', ICON_WIDTH)
            h = elem.get('height', ICON_HEIGHT)

            dwg.add(dwg.rect(
                insert=(x, y),
                size=(w, h),
                fill='#0d6efd',
                stroke='#084298',
                stroke_width=2,
                opacity=0.8
            ))

        # Badge
        dwg.add(dwg.text(
            'Phase 9/9 - COMPLETE',
            insert=(canvas_width - 240, 30),
            font_size='14px',
            fill='#28a745',
            font_weight='bold'
        ))

        dwg.save()

        if self.debug:
            print(f"[VISUALIZER] Generado: {filename}")
