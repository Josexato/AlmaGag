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

    Crea 4 archivos SVG mostrando cada fase:
    1. phase1_structure.svg: Árbol de elementos con métricas
    2. phase2_abstract.svg: Posiciones abstractas (puntos)
    3. phase3_inflated.svg: Elementos con dimensiones reales
    4. phase4_final.svg: Layout completo con contenedores
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

    def capture_phase2(
        self,
        abstract_positions: Dict[str, Tuple[int, int]],
        crossings: int,
        layout
    ) -> None:
        """
        Captura snapshot de Fase 2 (Layout abstracto).

        Args:
            abstract_positions: {elem_id: (x, y)} en coordenadas abstractas
            crossings: Número de cruces detectados
            layout: Layout con conexiones
        """
        self.snapshots['phase2'] = {
            'abstract_positions': deepcopy(abstract_positions),
            'crossings': crossings,
            'connections': deepcopy(layout.connections)
        }

        if self.debug:
            print(f"[VISUALIZER] Phase 2 capturada ({crossings} cruces)")

    def capture_phase3(
        self,
        layout,
        spacing: float
    ) -> None:
        """
        Captura snapshot de Fase 3 (Inflación).

        Args:
            layout: Layout con elementos inflados
            spacing: Spacing calculado
        """
        self.snapshots['phase3'] = {
            'layout': deepcopy(layout),
            'spacing': spacing
        }

        if self.debug:
            print(f"[VISUALIZER] Phase 3 capturada (spacing={spacing:.1f}px)")

    def capture_phase4(
        self,
        layout
    ) -> None:
        """
        Captura snapshot de Fase 4 (Crecimiento).

        Args:
            layout: Layout final con contenedores expandidos
        """
        self.snapshots['phase4'] = {
            'layout': deepcopy(layout)
        }

        if self.debug:
            print(f"[VISUALIZER] Phase 4 capturada")

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
            self._generate_phase2_svg(output_path)

        if 'phase3' in self.snapshots:
            self._generate_phase3_svg(output_path)

        if 'phase4' in self.snapshots:
            self._generate_phase4_svg(output_path)

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
            'Phase 1/4',
            insert=(canvas_width - 100, 30),
            font_size='14px',
            fill='#6c757d'
        ))

        dwg.save()

        if self.debug:
            print(f"[VISUALIZER] Generado: {filename}")

    def _generate_phase2_svg(self, output_path: str) -> None:
        """
        Genera SVG de Fase 2: Layout abstracto (puntos).
        """
        snapshot = self.snapshots['phase2']
        abstract_positions = snapshot['abstract_positions']
        crossings = snapshot['crossings']
        connections = snapshot['connections']

        filename = os.path.join(output_path, "phase2_abstract.svg")

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
            'LAF Phase 2: Abstract Layout',
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
            'Phase 2/4',
            insert=(canvas_width - 100, 30),
            font_size='14px',
            fill='#6c757d'
        ))

        dwg.save()

        if self.debug:
            print(f"[VISUALIZER] Generado: {filename}")

    def _generate_phase3_svg(self, output_path: str) -> None:
        """
        Genera SVG de Fase 3: Elementos inflados.
        """
        snapshot = self.snapshots['phase3']
        layout = snapshot['layout']
        spacing = snapshot['spacing']

        filename = os.path.join(output_path, "phase3_inflated.svg")

        # Canvas basado en elementos
        canvas_width = layout.canvas.get('width', 2000)
        canvas_height = layout.canvas.get('height', 2000)

        dwg = svgwrite.Drawing(filename, size=(canvas_width, canvas_height))

        # Fondo
        dwg.add(dwg.rect(insert=(0, 0), size=(canvas_width, canvas_height), fill='#ffffff'))

        # Título
        dwg.add(dwg.text(
            'LAF Phase 3: Inflated Elements',
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
            'Phase 3/4',
            insert=(canvas_width - 100, 30),
            font_size='14px',
            fill='#6c757d'
        ))

        dwg.save()

        if self.debug:
            print(f"[VISUALIZER] Generado: {filename}")

    def _generate_phase4_svg(self, output_path: str) -> None:
        """
        Genera SVG de Fase 4: Layout final.

        Similar al output final pero con anotaciones de debug.
        """
        snapshot = self.snapshots['phase4']
        layout = snapshot['layout']

        filename = os.path.join(output_path, "phase4_final.svg")

        canvas_width = layout.canvas.get('width', 2000)
        canvas_height = layout.canvas.get('height', 2000)

        dwg = svgwrite.Drawing(filename, size=(canvas_width, canvas_height))

        # Fondo
        dwg.add(dwg.rect(insert=(0, 0), size=(canvas_width, canvas_height), fill='#ffffff'))

        # Título
        dwg.add(dwg.text(
            'LAF Phase 4: Final Layout (Containers Grown)',
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
            'Phase 4/4 - COMPLETE',
            insert=(canvas_width - 180, 30),
            font_size='14px',
            fill='#28a745',
            font_weight='bold'
        ))

        dwg.save()

        if self.debug:
            print(f"[VISUALIZER] Generado: {filename}")
