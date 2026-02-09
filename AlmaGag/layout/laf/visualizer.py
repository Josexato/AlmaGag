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

    def capture_phase3_abstract(
        self,
        abstract_positions: Dict[str, Tuple[int, int]],
        crossings: int,
        layout
    ) -> None:
        """
        Captura snapshot de Fase 3 (Layout abstracto).

        Args:
            abstract_positions: {elem_id: (x, y)} en coordenadas abstractas
            crossings: Número de cruces detectados
            layout: Layout con conexiones
        """
        self.snapshots['phase3'] = {
            'abstract_positions': deepcopy(abstract_positions),
            'crossings': crossings,
            'connections': deepcopy(layout.connections)
        }

        if self.debug:
            print(f"[VISUALIZER] Phase 3 capturada ({crossings} cruces)")

    def capture_phase4_inflated(
        self,
        layout,
        spacing: float
    ) -> None:
        """
        Captura snapshot de Fase 4 (Inflación).

        Args:
            layout: Layout con elementos inflados
            spacing: Spacing calculado
        """
        self.snapshots['phase4'] = {
            'layout': deepcopy(layout),
            'spacing': spacing
        }

        if self.debug:
            print(f"[VISUALIZER] Phase 4 capturada (spacing={spacing:.1f}px)")

    def capture_phase5_containers(
        self,
        layout
    ) -> None:
        """
        Captura snapshot de Fase 5 (Crecimiento de contenedores).

        Args:
            layout: Layout con contenedores expandidos
        """
        self.snapshots['phase5'] = {
            'layout': deepcopy(layout)
        }

        if self.debug:
            print(f"[VISUALIZER] Phase 5 capturada")

    def capture_phase6_redistributed(
        self,
        layout
    ) -> None:
        """
        Captura snapshot de Fase 6 (Redistribución vertical).

        Args:
            layout: Layout después de redistribución vertical
        """
        self.snapshots['phase6'] = {
            'layout': deepcopy(layout)
        }

        if self.debug:
            print(f"[VISUALIZER] Phase 6 capturada")

    def capture_phase7_routed(
        self,
        layout
    ) -> None:
        """
        Captura snapshot de Fase 7 (Routing).

        Args:
            layout: Layout con paths de conexiones calculados
        """
        self.snapshots['phase7'] = {
            'layout': deepcopy(layout)
        }

        if self.debug:
            print(f"[VISUALIZER] Phase 7 capturada")

    def capture_phase8_final(
        self,
        layout
    ) -> None:
        """
        Captura snapshot de Fase 8 (Generación SVG final).

        Args:
            layout: Layout final completo
        """
        self.snapshots['phase8'] = {
            'layout': deepcopy(layout)
        }

        if self.debug:
            print(f"[VISUALIZER] Phase 8 capturada")

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
            self._generate_phase3_abstract_svg(output_path)

        if 'phase4' in self.snapshots:
            self._generate_phase4_inflated_svg(output_path)

        if 'phase5' in self.snapshots:
            self._generate_phase5_containers_svg(output_path)

        if 'phase6' in self.snapshots:
            self._generate_phase6_redistributed_svg(output_path)

        if 'phase7' in self.snapshots:
            self._generate_phase7_routed_svg(output_path)

        if 'phase8' in self.snapshots:
            self._generate_phase8_final_svg(output_path)

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

        # Árbol de elementos (simplificado)
        y += 20
        dwg.add(dwg.text(
            'Element Tree:',
            insert=(40, y),
            font_size='16px',
            font_weight='bold',
            fill='#212529'
        ))
        y += 25

        for elem_id in structure_info.primary_elements:
            node = structure_info.element_tree.get(elem_id, {})
            is_container = node.get('is_container', False)
            children_count = len(node.get('children', []))

            symbol = '[C]' if is_container else '[E]'
            text = f"{symbol} {elem_id}"
            if is_container and children_count > 0:
                text += f" ({children_count} children)"

            dwg.add(dwg.text(
                text,
                insert=(60, y),
                font_size='12px',
                fill='#0d6efd' if is_container else '#6c757d',
                font_family='monospace'
            ))
            y += 20

        # Badge
        dwg.add(dwg.text(
            'Phase 1/8',
            insert=(canvas_width - 100, 30),
            font_size='14px',
            fill='#6c757d'
        ))

        dwg.save()

        if self.debug:
            print(f"[VISUALIZER] Generado: {filename}")

    def _generate_phase2_topology_svg(self, output_path: str) -> None:
        """
        Genera SVG de Fase 2: Análisis topológico.
        Muestra niveles topológicos y accessibility scores con color coding.
        """
        snapshot = self.snapshots['phase2']
        structure_info = snapshot['structure_info']

        filename = os.path.join(output_path, "phase2_topology.svg")

        canvas_width = 1000
        canvas_height = 800

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
        level_height = 80
        start_y = 120
        node_radius = 20

        # Dibujar niveles
        for level in sorted(by_level.keys()):
            elements = by_level[level]
            y = start_y + level * level_height

            # Label del nivel
            dwg.add(dwg.text(
                f'Level {level}',
                insert=(20, y - 10),
                font_size='14px',
                font_weight='bold',
                fill='#495057'
            ))

            # Línea horizontal del nivel
            dwg.add(dwg.line(
                start=(100, y),
                end=(canvas_width - 20, y),
                stroke='#dee2e6',
                stroke_width=1,
                stroke_dasharray='5,5'
            ))

            # Distribuir elementos horizontalmente
            num_elements = len(elements)
            spacing = (canvas_width - 220) / max(num_elements, 1)
            start_x = 120

            for i, elem_id in enumerate(elements):
                x = start_x + i * spacing
                score = structure_info.accessibility_scores.get(elem_id, 0)

                # Color según score
                if score > 0.05:
                    color = '#dc3545'  # Rojo - Alto
                elif score > 0.02:
                    color = '#ffc107'  # Amarillo - Medio
                else:
                    color = '#0d6efd'  # Azul - Bajo/Normal

                # Dibujar nodo
                dwg.add(dwg.circle(
                    center=(x, y),
                    r=node_radius,
                    fill=color,
                    opacity=0.7,
                    stroke='#212529',
                    stroke_width=2
                ))

                # Label con ID (truncar si es muy largo)
                label = elem_id if len(elem_id) <= 15 else elem_id[:12] + '...'
                dwg.add(dwg.text(
                    label,
                    insert=(x, y + node_radius + 15),
                    font_size='10px',
                    fill='#212529',
                    text_anchor='middle',
                    font_family='monospace'
                ))

                # Mostrar score si > 0
                if score > 0:
                    dwg.add(dwg.text(
                        f'{score:.4f}',
                        insert=(x, y + 5),
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
            'Phase 2/8',
            insert=(canvas_width - 100, 30),
            font_size='14px',
            fill='#6c757d'
        ))

        dwg.save()

        if self.debug:
            print(f"[VISUALIZER] Generado: {filename}")

    def _generate_phase3_abstract_svg(self, output_path: str) -> None:
        """
        Genera SVG de Fase 3: Layout abstracto (puntos).
        """
        snapshot = self.snapshots['phase3']
        abstract_positions = snapshot['abstract_positions']
        crossings = snapshot['crossings']
        connections = snapshot['connections']

        filename = os.path.join(output_path, "phase3_abstract.svg")

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
            'Phase 3/8',
            insert=(canvas_width - 100, 30),
            font_size='14px',
            fill='#6c757d'
        ))

        dwg.save()

        if self.debug:
            print(f"[VISUALIZER] Generado: {filename}")

    def _generate_phase4_inflated_svg(self, output_path: str) -> None:
        """
        Genera SVG de Fase 4: Elementos inflados.
        """
        snapshot = self.snapshots['phase4']
        layout = snapshot['layout']
        spacing = snapshot['spacing']

        filename = os.path.join(output_path, "phase4_inflated.svg")

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
            'Phase 4/8',
            insert=(canvas_width - 100, 30),
            font_size='14px',
            fill='#6c757d'
        ))

        dwg.save()

        if self.debug:
            print(f"[VISUALIZER] Generado: {filename}")

    def _generate_phase5_containers_svg(self, output_path: str) -> None:
        """
        Genera SVG de Fase 5: Contenedores expandidos.

        Similar al output final pero con anotaciones de debug.
        """
        snapshot = self.snapshots['phase5']
        layout = snapshot['layout']

        filename = os.path.join(output_path, "phase5_containers.svg")

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
            'Phase 5/8',
            insert=(canvas_width - 100, 30),
            font_size='14px',
            fill='#6c757d'
        ))

        dwg.save()

        if self.debug:
            print(f"[VISUALIZER] Generado: {filename}")

    def _generate_phase6_redistributed_svg(self, output_path: str) -> None:
        """
        Genera SVG de Fase 6: Redistribución vertical.
        """
        snapshot = self.snapshots['phase6']
        layout = snapshot['layout']

        filename = os.path.join(output_path, "phase6_redistributed.svg")

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
            'Phase 6/8',
            insert=(canvas_width - 100, 30),
            font_size='14px',
            fill='#6c757d'
        ))

        dwg.save()

        if self.debug:
            print(f"[VISUALIZER] Generado: {filename}")

    def _generate_phase7_routed_svg(self, output_path: str) -> None:
        """
        Genera SVG de Fase 7: Routing de conexiones.
        """
        snapshot = self.snapshots['phase7']
        layout = snapshot['layout']

        filename = os.path.join(output_path, "phase7_routed.svg")

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
            'Phase 7/8',
            insert=(canvas_width - 100, 30),
            font_size='14px',
            fill='#6c757d'
        ))

        dwg.save()

        if self.debug:
            print(f"[VISUALIZER] Generado: {filename}")

    def _generate_phase8_final_svg(self, output_path: str) -> None:
        """
        Genera SVG de Fase 8: Generación SVG final.
        """
        snapshot = self.snapshots['phase8']
        layout = snapshot['layout']

        filename = os.path.join(output_path, "phase8_final.svg")

        canvas_width = layout.canvas.get('width', 2000)
        canvas_height = layout.canvas.get('height', 2000)

        dwg = svgwrite.Drawing(filename, size=(canvas_width, canvas_height))

        # Fondo
        dwg.add(dwg.rect(insert=(0, 0), size=(canvas_width, canvas_height), fill='#ffffff'))

        # Título
        dwg.add(dwg.text(
            'LAF Phase 8: SVG Generation (COMPLETE)',
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
            'Phase 8/8 - COMPLETE',
            insert=(canvas_width - 200, 30),
            font_size='14px',
            fill='#28a745',
            font_weight='bold'
        ))

        dwg.save()

        if self.debug:
            print(f"[VISUALIZER] Generado: {filename}")
