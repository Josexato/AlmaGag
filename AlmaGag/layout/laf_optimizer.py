"""
LAFOptimizer - Layout Abstracto Primero

Coordinador del sistema LAF que ejecuta las 9 fases:
1. Análisis de estructura (grafo, accesibilidad, centralidad)
2. Análisis topológico (niveles jerárquicos, longest-path)
3. Ordenamiento por centralidad (centrales al centro, hojas a extremos)
4. Layout abstracto (Sugiyama barycenter, minimización de cruces)
5. Optimización de posiciones (layer-offset bisection, minimiza distancia de conectores)
6. Inflación de elementos (dimensiones reales)
7. Crecimiento de contenedores (bottom-up)
8. Redistribución vertical con escala X global (preserva ángulos de Fase 5)
9. Routing (paths de conexiones)
10. Generación de SVG

Version: v1.5 (Sprint 5 + Fase 7 angle-preserving)
"""

from typing import List
from AlmaGag.layout.laf.structure_analyzer import StructureAnalyzer
from AlmaGag.layout.laf.abstract_placer import AbstractPlacer
from AlmaGag.layout.laf.position_optimizer import PositionOptimizer
from AlmaGag.layout.laf.inflator import ElementInflator
from AlmaGag.layout.laf.container_grower import ContainerGrower
from AlmaGag.layout.laf.visualizer import GrowthVisualizer
from AlmaGag.layout.sizing import SizingCalculator
from AlmaGag.config import LAF_SPACING_BASE
import logging

# Importar la función de dump_layout_table si está en debug
logger = logging.getLogger('AlmaGag')


class LAFOptimizer:
    """
    Optimizador LAF (Layout Abstracto Primero).

    Ejecuta layout en 9 fases para minimizar cruces y distancias de conectores.
    Fase 5 (Claude-SolFase5): Optimiza posiciones de nodos primarios para
    minimizar la distancia total de conectores, sin realizar inflación.
    """

    def __init__(
        self,
        positioner=None,
        container_calculator=None,
        router_manager=None,
        collision_detector=None,
        label_optimizer=None,
        geometry=None,
        visualize_growth: bool = False,
        debug: bool = False,
        centrality_alpha: float = 0.15,
        centrality_beta: float = 0.10,
        centrality_gamma: float = 0.15,
        centrality_max_score: float = 100.0,
    ):
        """
        Inicializa el optimizador LAF.

        Args:
            positioner: AutoLayoutPositioner (no usado en LAF, pero para compatibilidad)
            container_calculator: ContainerCalculator
            router_manager: RouterManager
            collision_detector: CollisionDetector
            label_optimizer: LabelOptimizer
            geometry: GeometryCalculator
            visualize_growth: Si True, genera SVGs de cada fase
            debug: Si True, imprime logs de debug
            centrality_alpha: Peso por distancia en skip connections (Fase 3)
            centrality_beta: Peso por hijo extra / hub-ness (Fase 3)
            centrality_gamma: Peso por fan-in extra (Fase 3, 0=desactivado)
            centrality_max_score: Clamp máximo del score de accesibilidad (Fase 3)
        """
        self.positioner = positioner
        self.container_calculator = container_calculator
        self.router_manager = router_manager
        self.collision_detector = collision_detector
        self.label_optimizer = label_optimizer
        self.geometry = geometry
        self.visualize_growth = visualize_growth
        self.debug = debug

        # Obtener visualdebug del positioner si está disponible
        visualdebug = getattr(positioner, 'visualdebug', False) if positioner else False

        # SizingCalculator para dimensiones reales (hp/wp)
        self.sizing = SizingCalculator()

        # Módulos LAF
        self.structure_analyzer = StructureAnalyzer(debug=debug, centrality_alpha=centrality_alpha,
                                                    centrality_beta=centrality_beta,
                                                    centrality_gamma=centrality_gamma,
                                                    centrality_max_score=centrality_max_score)
        self.abstract_placer = AbstractPlacer(debug=debug)
        self.position_optimizer = PositionOptimizer(debug=debug)
        self.inflator = ElementInflator(label_optimizer=label_optimizer, debug=debug, visualdebug=visualdebug)
        self.container_grower = ContainerGrower(sizing_calculator=self.sizing, debug=debug)
        self.visualizer = GrowthVisualizer(debug=debug) if visualize_growth else None

    def _dump_layout(self, layout, phase_name):
        """Helper para hacer dump del layout en cada fase (solo con --dump-iterations)."""
        if getattr(layout, '_dump_iterations', False):
            try:
                from AlmaGag.generator import dump_layout_table
                containers = [e for e in layout.elements if 'contains' in e]
                dump_layout_table(layout, layout.elements_by_id, containers, phase=phase_name)
            except Exception as e:
                logger.warning(f"[LAF] No se pudo hacer dump de layout: {e}")

    def _write_abstract_positions_to_layout(self, abstract_positions, layout):
        """
        Escribe posiciones abstractas temporalmente en los elementos.

        Estas posiciones serán sobrescritas en Fase 6 con las posiciones reales.
        Solo se hace para que aparezcan en el dump del CSV de fases anteriores.

        Args:
            abstract_positions: {element_id: (abstract_x, abstract_y)}
            layout: Layout a modificar
        """
        for elem_id, (abstract_x, abstract_y) in abstract_positions.items():
            elem = layout.elements_by_id.get(elem_id)
            if elem:
                # Escribir coordenadas abstractas (serán sobrescritas en Fase 6)
                elem['x'] = abstract_x
                elem['y'] = abstract_y

                # No asignar dimensiones aún (se hará en Fase 6)

    def _populate_layout_analysis(self, layout, structure_info):
        """
        Pobla los atributos de análisis del layout desde structure_info.

        Args:
            layout: Layout a poblar
            structure_info: Información estructural del StructureAnalyzer
        """
        # 1. Poblar layout.graph desde structure_info.connection_graph
        layout.graph = structure_info.connection_graph.copy()

        # 2. Poblar layout.levels desde structure_info.topological_levels
        layout.levels = structure_info.topological_levels.copy()

        # Asignar niveles a elementos contenidos basándose en su contenedor padre
        for elem in layout.elements:
            elem_id = elem['id']
            if elem_id not in layout.levels:
                # Buscar el elemento primario (contenedor padre)
                parent = structure_info.element_tree.get(elem_id, {}).get('parent')
                while parent is not None:
                    if parent in layout.levels:
                        layout.levels[elem_id] = layout.levels[parent]
                        break
                    parent = structure_info.element_tree.get(parent, {}).get('parent')

                # Si no se encontró padre, asignar nivel 0
                if elem_id not in layout.levels:
                    layout.levels[elem_id] = 0

        # 3. Calcular grupos usando DFS sobre el grafo (solo primarios)
        layout.groups = self._calculate_groups(layout)

        # 3b. Agregar elementos contenidos a los grupos de su contenedor padre
        self._add_contained_elements_to_groups(layout, structure_info)

        # 4. Calcular prioridades usando GraphAnalyzer
        if self.positioner and self.positioner.graph_analyzer:
            layout.priorities = self.positioner.graph_analyzer.calculate_priorities(
                layout.elements,
                layout.graph
            )
        else:
            # Prioridad por defecto basada en label_priority
            layout.priorities = {}
            for elem in layout.elements:
                elem_id = elem['id']
                label_priority = elem.get('label_priority', 'normal')
                if label_priority == 'high':
                    layout.priorities[elem_id] = 0
                elif label_priority == 'low':
                    layout.priorities[elem_id] = 2
                else:
                    layout.priorities[elem_id] = 1

    def _add_contained_elements_to_groups(self, layout, structure_info):
        """
        Agrega elementos contenidos a los grupos de su contenedor padre.

        Args:
            layout: Layout con groups poblado (solo primarios por ahora)
            structure_info: StructureInfo con element_tree
        """
        # Crear mapa de elemento -> grupo para búsqueda rápida
        elem_to_group = {}
        for group_idx, group in enumerate(layout.groups):
            for elem_id in group:
                elem_to_group[elem_id] = group_idx

        # Agregar elementos contenidos al grupo de su contenedor
        for elem in layout.elements:
            elem_id = elem['id']

            # Si ya está en un grupo (es primario), continuar
            if elem_id in elem_to_group:
                continue

            # Buscar el contenedor padre
            parent = structure_info.element_tree.get(elem_id, {}).get('parent')
            while parent is not None:
                if parent in elem_to_group:
                    # Encontramos el contenedor primario, agregarlo al mismo grupo
                    group_idx = elem_to_group[parent]
                    layout.groups[group_idx].append(elem_id)
                    elem_to_group[elem_id] = group_idx
                    break
                parent = structure_info.element_tree.get(parent, {}).get('parent')

    def _calculate_groups(self, layout):
        """
        Identifica subgrafos conectados usando DFS sobre grafo no dirigido.

        IMPORTANTE: Solo calcula grupos para elementos primarios.
        Los elementos contenidos se agregarán al grupo de su contenedor padre
        en _populate_layout_analysis().

        Args:
            layout: Layout con graph poblado

        Returns:
            List[List[str]]: [[elem_ids del grupo 1], [elem_ids del grupo 2], ...]
        """
        # Primero, construir grafo no dirigido desde el grafo dirigido
        # NOTA: layout.graph solo contiene elementos primarios
        undirected_graph = {}
        for node, neighbors in layout.graph.items():
            if node not in undirected_graph:
                undirected_graph[node] = []
            for neighbor in neighbors:
                # Agregar conexión bidireccional
                if neighbor not in undirected_graph:
                    undirected_graph[neighbor] = []
                if neighbor not in undirected_graph[node]:
                    undirected_graph[node].append(neighbor)
                if node not in undirected_graph[neighbor]:
                    undirected_graph[neighbor].append(node)

        # Asegurar que todos los nodos del grafo están inicializados
        for node in layout.graph.keys():
            if node not in undirected_graph:
                undirected_graph[node] = []

        visited = set()
        groups = []

        def dfs(node, group):
            if node in visited:
                return
            visited.add(node)
            group.append(node)

            # Visitar todos los vecinos (ahora bidireccionales)
            for neighbor in undirected_graph.get(node, []):
                dfs(neighbor, group)

        # Explorar solo elementos que están en el grafo (primarios)
        for node in undirected_graph.keys():
            if node not in visited:
                group = []
                dfs(node, group)
                if group:
                    groups.append(group)

        return groups

    def _compute_ndfn_groups(self, structure_info, layout):
        """
        Calcula bounding box y centroide de cada grupo NdFn.

        Agrupa cada elemento primario con todos sus hijos (si es contenedor)
        y calcula el centro geométrico del grupo completo.

        Returns:
            Dict[str, dict]: {elem_id: {centroid_x, centroid_y, bbox_width, bbox_height, bbox_x, bbox_y}}
        """
        from AlmaGag.config import ICON_WIDTH, ICON_HEIGHT

        groups = {}
        for elem_id in structure_info.primary_elements:
            elem = layout.elements_by_id.get(elem_id)
            if not elem:
                continue

            rects = [(elem.get('x', 0), elem.get('y', 0),
                      elem.get('width', ICON_WIDTH), elem.get('height', ICON_HEIGHT))]

            node = structure_info.element_tree.get(elem_id)
            if node and node['children']:
                for child_id in node['children']:
                    child = layout.elements_by_id.get(child_id)
                    if child and 'x' in child:
                        rects.append((child['x'], child['y'],
                                      child.get('width', ICON_WIDTH),
                                      child.get('height', ICON_HEIGHT)))

            min_x = min(r[0] for r in rects)
            min_y = min(r[1] for r in rects)
            max_x = max(r[0] + r[2] for r in rects)
            max_y = max(r[1] + r[3] for r in rects)

            groups[elem_id] = {
                'centroid_x': (min_x + max_x) / 2,
                'centroid_y': (min_y + max_y) / 2,
                'bbox_width': max_x - min_x,
                'bbox_height': max_y - min_y,
                'bbox_x': min_x,
                'bbox_y': min_y
            }

        return groups

    def _redistribute_vertical_after_growth(self, structure_info, layout):
        """
        Redistribuye elementos después del crecimiento de contenedores,
        preservando los ángulos de conectores de Fase 5.

        Algoritmo:
        1. Obtener posiciones abstractas de Fase 5 (abstract_x, abstract_y)
        2. Calcular escala X global usando bbox_width de grupos NdFn
        3. Asignar Y secuencial por nivel (max_height + 240px)
        4. Posicionar por centroide de grupo NdFn
        5. Centrar globalmente con un dx uniforme

        Si no hay posiciones de Fase 5, usa fallback con centrado por nivel.

        Args:
            structure_info: Información estructural con topological_levels
            layout: Layout con elementos ya posicionados y contenedores expandidos
        """
        from AlmaGag.config import (
            TOP_MARGIN_DEBUG, TOP_MARGIN_NORMAL, ICON_HEIGHT, ICON_WIDTH,
            LAF_SPACING_BASE, LAF_VERTICAL_SPACING, CANVAS_MARGIN_LARGE,
            SPACING_SMALL
        )

        # Obtener visualdebug del positioner si está disponible
        visualdebug = getattr(self.positioner, 'visualdebug', False) if self.positioner else False
        TOP_MARGIN = TOP_MARGIN_DEBUG if visualdebug else TOP_MARGIN_NORMAL

        VERTICAL_SPACING = LAF_VERTICAL_SPACING  # 240px
        MIN_HORIZONTAL_GAP = SPACING_SMALL  # 40px
        LEFT_MARGIN = CANVAS_MARGIN_LARGE  # 100px

        # --- Paso 1: Construir by_level ---
        by_level = {}

        if hasattr(layout, 'optimized_layer_order') and layout.optimized_layer_order:
            for layer_idx, layer_elements in enumerate(layout.optimized_layer_order):
                if not layer_elements:
                    continue
                first_elem_id = layer_elements[0]
                actual_level = structure_info.topological_levels.get(first_elem_id, layer_idx)
                by_level[actual_level] = layer_elements.copy()

            if self.debug:
                print(f"[REDISTRIBUTE] Orden optimizado (Fase 5): {len(by_level)} niveles")
        else:
            for elem_id in structure_info.primary_elements:
                level = structure_info.topological_levels.get(elem_id, 0)
                if level not in by_level:
                    by_level[level] = []
                by_level[level].append(elem_id)

            if self.debug:
                print(f"[REDISTRIBUTE] ADVERTENCIA: No se encontró orden optimizado, usando orden por defecto")

        # --- Check if we have Phase 5 positions ---
        phase5 = getattr(layout, '_phase5_positions', None)
        if not phase5:
            # Fallback: use old per-level centering approach
            self._redistribute_vertical_fallback(structure_info, layout, by_level, TOP_MARGIN, VERTICAL_SPACING)
            return

        # --- Paso 1.5: Calcular grupos NdFn (centroides + bounding boxes) ---
        ndfn_groups = self._compute_ndfn_groups(structure_info, layout)

        if self.debug:
            containers = [eid for eid, g in ndfn_groups.items() if g['bbox_width'] > ICON_WIDTH]
            print(f"[REDISTRIBUTE] Grupos NdFn: {len(ndfn_groups)} ({len(containers)} contenedores)")

        # --- Paso 2: Calcular escala X global (usando bbox_width de grupos NdFn) ---
        global_x_scale = LAF_SPACING_BASE  # 480px minimum

        for level_num in sorted(by_level.keys()):
            level_elements = by_level[level_num]
            if len(level_elements) < 2:
                continue

            # Collect (abstract_x, bbox_width) for each group, sorted by abstract_x
            items = []
            for elem_id in level_elements:
                abs_x = phase5.get(elem_id, (0, 0))[0]
                group = ndfn_groups.get(elem_id)
                width = group['bbox_width'] if group else ICON_WIDTH
                items.append((abs_x, width, elem_id))

            items.sort(key=lambda t: t[0])

            # For each adjacent pair, compute required scale
            # Scale is applied to centroids, so we need half-widths of both neighbors
            for i in range(len(items) - 1):
                abs_x_i = items[i][0]
                abs_x_next = items[i + 1][0]
                abstract_gap = abs_x_next - abs_x_i

                if abstract_gap <= 0:
                    continue  # Same position, skip

                half_width_i = items[i][1] / 2
                half_width_next = items[i + 1][1] / 2
                required_gap = half_width_i + half_width_next + MIN_HORIZONTAL_GAP
                required_scale = required_gap / abstract_gap
                global_x_scale = max(global_x_scale, required_scale)

        if self.debug:
            print(f"[REDISTRIBUTE] Global X scale: {global_x_scale:.1f}px/unit")

        # --- Paso 3: Asignar Y secuencialmente (usando bbox_height de grupos NdFn) ---
        current_y = TOP_MARGIN
        level_y_positions = {}

        for level_num in sorted(by_level.keys()):
            level_elements = by_level[level_num]
            level_y_positions[level_num] = current_y

            # Compute max height using NdFn group bounding box
            max_height = 0
            for elem_id in level_elements:
                group = ndfn_groups.get(elem_id)
                if group:
                    max_height = max(max_height, group['bbox_height'])
                else:
                    elem = layout.elements_by_id.get(elem_id)
                    if elem:
                        max_height = max(max_height, elem.get('height', ICON_HEIGHT))

            current_y += max_height + VERTICAL_SPACING

        # --- Paso 4: Posicionar por centroide de grupo NdFn ---
        # Normalize abstract_x so minimum is 0
        all_abs_x = [phase5.get(eid, (0, 0))[0]
                     for level_elems in by_level.values()
                     for eid in level_elems
                     if eid in phase5]
        abs_x_shift = -min(all_abs_x) if all_abs_x else 0

        for level_num in sorted(by_level.keys()):
            level_elements = by_level[level_num]
            new_y = level_y_positions[level_num]

            for elem_id in level_elements:
                elem = layout.elements_by_id.get(elem_id)
                if not elem:
                    continue

                group = ndfn_groups.get(elem_id)

                # Posición objetivo del centroide del grupo
                abs_x = phase5.get(elem_id, (0, 0))[0]
                target_centroid_x = (abs_x + abs_x_shift) * global_x_scale + LEFT_MARGIN

                # Delta basado en centroide actual del grupo
                if group:
                    current_centroid_x = group['centroid_x']
                else:
                    current_centroid_x = elem.get('x', 0) + elem.get('width', ICON_WIDTH) / 2
                dx = target_centroid_x - current_centroid_x

                old_y = elem.get('y', 0)
                dy = new_y - old_y

                elem['x'] = elem.get('x', 0) + dx
                elem['y'] = new_y

                # Update label
                if elem_id in layout.label_positions:
                    label_x, label_y, anchor, baseline = layout.label_positions[elem_id]
                    layout.label_positions[elem_id] = (
                        label_x + dx,
                        label_y + dy,
                        anchor,
                        baseline
                    )

                # If container, update contained children with same delta
                if 'contains' in elem:
                    node = structure_info.element_tree.get(elem_id)
                    if node and node['children']:
                        for child_id in node['children']:
                            child = layout.elements_by_id.get(child_id)
                            if child:
                                if 'x' in child:
                                    child['x'] += dx
                                if 'y' in child:
                                    child['y'] += dy

                                if child_id in layout.label_positions:
                                    cx, cy, ca, cb = layout.label_positions[child_id]
                                    layout.label_positions[child_id] = (
                                        cx + dx,
                                        cy + dy,
                                        ca,
                                        cb
                                    )

        # --- Paso 5: Centrado global único (usando bounding boxes de grupos NdFn) ---
        # Recalcular grupos NdFn después del reposicionamiento
        ndfn_groups = self._compute_ndfn_groups(structure_info, layout)
        x_min = float('inf')
        x_max = float('-inf')
        for level_elems in by_level.values():
            for elem_id in level_elems:
                group = ndfn_groups.get(elem_id)
                if not group:
                    continue
                x_min = min(x_min, group['bbox_x'])
                x_max = max(x_max, group['bbox_x'] + group['bbox_width'])

        if x_min != float('inf'):
            correction_dx = LEFT_MARGIN - x_min
            if abs(correction_dx) > 0.5:  # Only apply if meaningful
                self._apply_global_dx(correction_dx, by_level, layout, structure_info)

        if self.debug:
            print(f"[REDISTRIBUTE] OK: {len(by_level)} niveles, altura={current_y:.0f}px")

        # --- Paso 6: Recalcular canvas ---
        canvas_width, canvas_height = self.container_grower.calculate_final_canvas(
            structure_info,
            layout
        )
        layout.canvas['width'] = canvas_width
        layout.canvas['height'] = canvas_height

        if self.debug:
            print(f"[REDISTRIBUTE] Canvas final: {canvas_width:.0f}x{canvas_height:.0f}px")

    def _apply_global_dx(self, dx, by_level, layout, structure_info):
        """Apply a uniform horizontal shift to ALL elements."""
        from AlmaGag.config import ICON_WIDTH

        for level_elems in by_level.values():
            for elem_id in level_elems:
                elem = layout.elements_by_id.get(elem_id)
                if not elem:
                    continue

                elem['x'] = elem.get('x', 0) + dx

                if elem_id in layout.label_positions:
                    lx, ly, la, lb = layout.label_positions[elem_id]
                    layout.label_positions[elem_id] = (lx + dx, ly, la, lb)

                if 'contains' in elem:
                    node = structure_info.element_tree.get(elem_id)
                    if node and node['children']:
                        for child_id in node['children']:
                            child = layout.elements_by_id.get(child_id)
                            if child and 'x' in child:
                                child['x'] += dx
                                if child_id in layout.label_positions:
                                    cx, cy, ca, cb = layout.label_positions[child_id]
                                    layout.label_positions[child_id] = (cx + dx, cy, ca, cb)

    def _redistribute_vertical_fallback(self, structure_info, layout, by_level, top_margin, vertical_spacing):
        """
        Fallback redistribution when Phase 5 positions are not available.
        Uses the old per-level centering approach.
        """
        from AlmaGag.config import ICON_HEIGHT, LAF_SPACING_BASE

        current_y = top_margin

        for level_num in sorted(by_level.keys()):
            level_elements = by_level[level_num]

            max_height = 0
            for elem_id in level_elements:
                elem = layout.elements_by_id.get(elem_id)
                if not elem:
                    continue
                elem_height = elem.get('height', ICON_HEIGHT)
                max_height = max(max_height, elem_height)

            for elem_id in level_elements:
                elem = layout.elements_by_id.get(elem_id)
                if not elem:
                    continue

                old_y = elem.get('y', 0)
                dy = current_y - old_y
                elem['y'] = current_y

                if elem_id in layout.label_positions:
                    label_x, label_y, anchor, baseline = layout.label_positions[elem_id]
                    label_offset_y = label_y - old_y
                    new_label_y = current_y + label_offset_y
                    layout.label_positions[elem_id] = (label_x, new_label_y, anchor, baseline)

                if 'contains' in elem:
                    node = structure_info.element_tree.get(elem_id)
                    if node and node['children']:
                        for child_id in node['children']:
                            child = layout.elements_by_id.get(child_id)
                            if child and 'y' in child:
                                child['y'] += dy
                                if child_id in layout.label_positions:
                                    clx, cly, ca, cb = layout.label_positions[child_id]
                                    layout.label_positions[child_id] = (clx, cly + dy, ca, cb)

            current_y += max_height + vertical_spacing

        # Recalculate canvas and center per-level
        canvas_width, canvas_height = self.container_grower.calculate_final_canvas(structure_info, layout)
        layout.canvas['width'] = canvas_width
        layout.canvas['height'] = canvas_height

        for level_num in sorted(by_level.keys()):
            level_elements = by_level[level_num]
            self._center_elements_horizontally(level_elements, layout, structure_info, spacing=LAF_SPACING_BASE)

        canvas_width, canvas_height = self.container_grower.calculate_final_canvas(structure_info, layout)
        layout.canvas['width'] = canvas_width
        layout.canvas['height'] = canvas_height

    def _center_elements_horizontally(
        self,
        level_elements: List[str],
        layout,
        structure_info,
        spacing: float = LAF_SPACING_BASE
    ) -> None:
        """
        Centra elementos de un nivel horizontalmente en el canvas.

        NOTA: Solo se usa en el fallback (sin posiciones de Fase 5).
        En el flujo normal, Phase 7 usa escala X global en vez de centrado por nivel.

        Args:
            level_elements: IDs de elementos del nivel (YA ORDENADOS)
            layout: Layout con elementos posicionados
            structure_info: Información estructural con element_tree
            spacing: Spacing horizontal entre elementos
        """
        from AlmaGag.config import ICON_WIDTH, CANVAS_MARGIN_LARGE

        if not level_elements:
            return

        # Caso especial: un solo elemento
        if len(level_elements) == 1:
            elem = layout.elements_by_id.get(level_elements[0])
            if elem:
                elem['x'] = layout.canvas['width'] / 2
            return

        # Calcular ancho total del nivel
        total_width = 0
        for i, elem_id in enumerate(level_elements):
            elem = layout.elements_by_id.get(elem_id)
            if elem:
                elem_width = elem.get('width', ICON_WIDTH)
                total_width += elem_width
                if i < len(level_elements) - 1:
                    total_width += spacing

        # Calcular posición inicial para centrar
        canvas_width = layout.canvas['width']
        start_x = (canvas_width - total_width) / 2

        # Asegurar margen mínimo
        start_x = max(start_x, CANVAS_MARGIN_LARGE)

        # Distribuir elementos horizontalmente
        current_x = start_x
        for elem_id in level_elements:
            elem = layout.elements_by_id.get(elem_id)
            if not elem:
                continue

            old_x = elem.get('x', 0)
            elem_width = elem.get('width', ICON_WIDTH)

            # Calcular desplazamiento horizontal
            dx = current_x - old_x

            # Asignar nueva posición X
            elem['x'] = current_x

            # Actualizar etiqueta X
            if elem_id in layout.label_positions:
                label_x, label_y, anchor, baseline = layout.label_positions[elem_id]
                new_label_x = label_x + dx
                layout.label_positions[elem_id] = (
                    new_label_x,
                    label_y,
                    anchor,
                    baseline
                )

            # Si es contenedor, actualizar X de hijos
            if 'contains' in elem:
                node = structure_info.element_tree.get(elem_id)
                if node and node['children']:
                    for child_id in node['children']:
                        child = layout.elements_by_id.get(child_id)
                        if child and 'x' in child:
                            child['x'] += dx

                            # Actualizar etiqueta del hijo
                            if child_id in layout.label_positions:
                                cx, cy, ca, cb = layout.label_positions[child_id]
                                layout.label_positions[child_id] = (
                                    cx + dx,
                                    cy,
                                    ca,
                                    cb
                                )

            # Avanzar a la siguiente posición
            current_x += elem_width + spacing

    def optimize(self, layout):
        """
        Ejecuta el pipeline LAF de 9 fases.

        Fases:
        1-3: Análisis (estructura, topología, centralidad)
        4: Layout abstracto (Sugiyama barycenter)
        5: Optimización de posiciones (layer-offset bisection)
        6: Inflación + Crecimiento de contenedores
        7: Redistribución vertical (escala X global preservando ángulos de Fase 5)
        8: Routing
        9: Visualización SVG

        Args:
            layout: Layout inicial

        Returns:
            Layout: Layout optimizado
        """
        if self.debug:
            print("\n[LAF] Pipeline LAF (9 fases)")

        # FASE 1: Análisis de estructura
        structure_info = self.structure_analyzer.analyze(layout)

        if self.visualizer:
            diagram_name = getattr(layout, '_diagram_name', 'diagram')
            self.visualizer.capture_phase1(structure_info, diagram_name)

        if self.debug:
            scored_count = sum(1 for v in structure_info.accessibility_scores.values() if v > 0)
            max_score = max(structure_info.accessibility_scores.values()) if scored_count else 0
            print(f"[LAF] Fase 1 OK: {len(structure_info.primary_elements)} primarios, "
                  f"{len(structure_info.container_metrics)} contenedores, "
                  f"{len(structure_info.connection_sequences)} conexiones")

            # Tabla compacta de nodos primarios
            print(f"  {'ID':<8} {'Tipo':<12} {'Elemento':<28} Nv  Hijos  Score")
            for elem_id in structure_info.primary_elements:
                nid = structure_info.primary_node_ids.get(elem_id, "?")
                ntype = structure_info.primary_node_types.get(elem_id, "?")
                lv = structure_info.topological_levels.get(elem_id, "?")
                ch = len(structure_info.element_tree.get(elem_id, {}).get('children', []))
                sc = structure_info.accessibility_scores.get(elem_id, 0.0)
                name = elem_id[:28] if len(elem_id) <= 28 else elem_id[:25] + "..."
                sc_str = f"{sc:.4f}" if sc > 0 else "-"
                print(f"  {nid:<8} {ntype:<12} {name:<28} {str(lv):<3} {ch:<6} {sc_str}")

        self._populate_layout_analysis(layout, structure_info)
        self._dump_layout(layout, "LAF_PHASE_1_STRUCTURE")

        # FASE 2: Análisis topológico (ya calculado en Fase 1, solo visualizar)
        if self.visualizer:
            self.visualizer.capture_phase2_topology(structure_info)
        self._dump_layout(layout, "LAF_PHASE_2_TOPOLOGY")

        if self.debug:
            by_level = {}
            for eid, lv in structure_info.topological_levels.items():
                by_level.setdefault(lv, []).append(eid)
            levels_str = " | ".join(f"{lv}:{','.join(by_level[lv])}" for lv in sorted(by_level))
            print(f"[LAF] Fase 2 OK: {levels_str}")

        # FASE 3: Ordenamiento por centralidad
        centrality_order = self._order_by_centrality(structure_info)

        if self.visualizer:
            self.visualizer.capture_phase3_centrality(structure_info, centrality_order)
        self._dump_layout(layout, "LAF_PHASE_3_CENTRALITY")

        if self.debug:
            print(f"[LAF] Fase 3 OK: {len(centrality_order)} niveles ordenados por centralidad")

        # FASE 4: Layout abstracto
        abstract_positions = self.abstract_placer.place_elements(
            structure_info, layout, centrality_order=centrality_order
        )
        crossings = self.abstract_placer.count_crossings(abstract_positions, layout.connections)

        if self.visualizer:
            self.visualizer.capture_phase4_abstract(
                abstract_positions, crossings, layout, structure_info
            )
        self._write_abstract_positions_to_layout(abstract_positions, layout)
        self._dump_layout(layout, "LAF_PHASE_4_ABSTRACT")

        if self.debug:
            print(f"[LAF] Fase 4 OK: {len(abstract_positions)} posiciones, {crossings} cruces")

        # FASE 5: Optimización de posiciones (Claude-SolFase5)
        optimized_positions = self.position_optimizer.optimize_positions(
            abstract_positions, structure_info, layout
        )
        optimized_crossings = self.abstract_placer.count_crossings(
            optimized_positions, layout.connections
        )
        self._write_abstract_positions_to_layout(optimized_positions, layout)
        self._update_optimized_layer_order(optimized_positions, structure_info, layout)
        layout._phase5_positions = optimized_positions

        if self.visualizer:
            self.visualizer.capture_phase5_optimized(
                optimized_positions, optimized_crossings, layout, structure_info
            )
        self._dump_layout(layout, "LAF_PHASE_5_OPTIMIZED")

        if self.debug:
            cross_delta = f" ({crossings}->{optimized_crossings})" if crossings != optimized_crossings else ""
            print(f"[LAF] Fase 5 OK: {len(optimized_positions)} optimizadas, {optimized_crossings} cruces{cross_delta}")

        # FASE 6: Inflación + Crecimiento de contenedores
        spacing = self.inflator.inflate_elements(optimized_positions, structure_info, layout)

        self.container_grower.grow_containers(structure_info, layout)
        canvas_width, canvas_height = self.container_grower.calculate_final_canvas(
            structure_info, layout
        )
        layout.canvas['width'] = canvas_width
        layout.canvas['height'] = canvas_height

        if self.visualizer:
            self.visualizer.capture_phase6_inflated(layout, spacing, structure_info)
        self._dump_layout(layout, "LAF_PHASE_6_INFLATED_AND_GROWN")

        if self.debug:
            print(f"[LAF] Fase 6 OK: spacing={spacing:.0f}px, canvas {canvas_width:.0f}x{canvas_height:.0f}px")

        # FASE 7: Redistribución vertical
        self._redistribute_vertical_after_growth(structure_info, layout)

        if self.visualizer:
            self.visualizer.capture_phase7_redistributed(layout, structure_info)
        self._dump_layout(layout, "LAF_PHASE_7_REDISTRIBUTED")

        if self.debug:
            print(f"[LAF] Fase 7 OK: redistribución vertical")

        # FASE 8: Routing
        if self.router_manager:
            self.router_manager.calculate_all_paths(layout)
            if self.visualizer:
                self.visualizer.capture_phase8_routed(layout, structure_info)
            if self.debug:
                print(f"[LAF] Fase 8 OK: {len(layout.connections)} conexiones ruteadas")

        # Colisiones finales
        if self.collision_detector and self.debug:
            collision_count, _ = self.collision_detector.detect_all_collisions(layout)
            if collision_count > 0:
                print(f"[LAF] WARN: {collision_count} colisiones detectadas")

        # FASE 9: Generar visualizaciones
        if self.visualizer:
            self.visualizer.capture_phase9_final(layout, structure_info)
            self.visualizer.generate_all()
            if self.debug:
                print(f"[LAF] Fase 9 OK: SVGs en debug/growth/")

        if self.debug:
            print(f"[LAF] Pipeline completo")

        layout.sizing = self.sizing
        layout.structure_info = structure_info
        return layout

    def _update_optimized_layer_order(self, optimized_positions, structure_info, layout):
        """
        Actualiza optimized_layer_order según las posiciones optimizadas por Claude-SolFase5.

        Después de la optimización de posiciones, el orden dentro de cada capa
        puede haber cambiado. Este método actualiza layout.optimized_layer_order
        para reflejar el nuevo orden, que será usado en Fase 7 (Redistribución).

        Args:
            optimized_positions: {elem_id: (x, y)} posiciones optimizadas
            structure_info: Información estructural
            layout: Layout con optimized_layer_order
        """
        if not hasattr(layout, 'optimized_layer_order') or not layout.optimized_layer_order:
            return

        # Reconstruir optimized_layer_order con el nuevo orden X
        new_order = []
        for layer in layout.optimized_layer_order:
            # Filtrar elementos que estén en las posiciones optimizadas
            layer_with_pos = [
                (elem_id, optimized_positions.get(elem_id, (0, 0))[0])
                for elem_id in layer
                if elem_id in optimized_positions
            ]
            # Ordenar por posición X optimizada
            layer_with_pos.sort(key=lambda x: x[1])
            new_order.append([elem_id for elem_id, _ in layer_with_pos])

        layout.optimized_layer_order = new_order

        if self.debug:
            print(f"[LAF] optimized_layer_order actualizado con orden de Claude-SolFase5")

    def _order_by_centrality(self, structure_info):
        """
        Ordena elementos dentro de cada nivel topológico por accessibility score.

        Algoritmo optimizado:
        1. Clasificar elementos en 3 grupos:
           - Centrales: score > 0 (mayor accesibilidad)
           - Normales: score = 0 con hijos
           - Hojas: score = 0 sin hijos (terminales)

        2. Distribuir en el nivel:
           - Centro: elementos centrales ordenados por score (mayor al medio)
           - Lados: elementos normales
           - Extremos: hojas (más alejadas del centro)

        Args:
            structure_info: StructureInfo con accessibility_scores, topological_levels,
                           connection_graph y element_tree

        Returns:
            Dict[int, List[Tuple[str, float]]]: {level: [(elem_id, score), ...]} ordenado
        """
        # Agrupar elementos por nivel
        by_level = {}
        for elem_id in structure_info.primary_elements:
            level = structure_info.topological_levels.get(elem_id, 0)
            if level not in by_level:
                by_level[level] = []

            score = structure_info.accessibility_scores.get(elem_id, 0.0)
            by_level[level].append((elem_id, score))

        # Ordenar cada nivel usando el nuevo algoritmo
        centrality_order = {}
        for level, elements in by_level.items():
            # Clasificar elementos en grupos
            centrales = []  # score > 0
            normales = []   # score = 0 con hijos
            hojas = []      # score = 0 sin hijos

            for elem_id, score in elements:
                node = structure_info.element_tree.get(elem_id)
                has_children = node and node.get('children', [])

                # Asignar score mínimo a hojas para que tengan algo de centralidad en Fase 4
                is_leaf = not has_children
                if is_leaf and score == 0:
                    score = 0.0001
                    # Actualizar en structure_info para que Fase 4 vea el score modificado
                    structure_info.accessibility_scores[elem_id] = score

                # Clasificar: las hojas con score 0.0001 van al grupo hojas, no centrales
                if score > 0.0001:  # Cambio: > 0.0001 en lugar de > 0
                    centrales.append((elem_id, score))
                elif has_children:
                    normales.append((elem_id, score))
                else:
                    # Es hoja: no tiene hijos (score=0 o score=0.0001)
                    hojas.append((elem_id, score))

            # Ordenar centrales por score descendente
            centrales.sort(key=lambda x: x[1], reverse=True)

            # Distribuir elementos centrales alrededor del centro
            # Los de mayor score en el medio exacto
            central_distributed = self._distribute_around_center(centrales)

            # Para normales y hojas: ordenar por número de conexiones
            # (más conexiones = más importante, va más cerca del centro)
            def connection_count(elem_id):
                in_count = sum(1 for targets in structure_info.connection_graph.values()
                              if elem_id in targets)
                out_count = len(structure_info.connection_graph.get(elem_id, []))
                return in_count + out_count

            normales.sort(key=lambda x: connection_count(x[0]), reverse=True)
            hojas.sort(key=lambda x: connection_count(x[0]), reverse=True)

            # Distribuir normales a los lados de centrales
            normales_distributed = self._distribute_sides(normales)

            # Distribuir hojas en extremos
            hojas_distributed = self._distribute_extremes(hojas)

            # Combinar: hojas_izq + normales_izq + centrales + normales_der + hojas_der
            left_hojas = hojas_distributed[0]
            right_hojas = hojas_distributed[1]
            left_normales = normales_distributed[0]
            right_normales = normales_distributed[1]

            reordered = (left_hojas + left_normales +
                        central_distributed +
                        right_normales + right_hojas)

            centrality_order[level] = reordered

        return centrality_order

    def _distribute_around_center(self, elements):
        """
        Distribuye elementos alrededor del centro, con los más importantes en el medio.

        Si hay múltiples elementos con el score máximo (>= 2), todos se agrupan al centro
        de modo que su punto medio esté centrado.

        Args:
            elements: Lista de (elem_id, score) ordenada por score descendente

        Returns:
            Lista de (elem_id, score) distribuida centro -> lados
        """
        if not elements:
            return []

        # Encontrar todos los elementos con score máximo
        max_score = elements[0][1]
        center_group = []
        remaining = []

        for elem_id, score in elements:
            if score == max_score:
                center_group.append((elem_id, score))
            else:
                remaining.append((elem_id, score))

        # Si solo hay 1 elemento con score máximo, va al centro exacto
        # Si hay >= 2, se agrupan de modo que su punto medio esté centrado
        center = center_group

        # Distribuir elementos restantes a los lados (alternando)
        left = []
        right = []

        for i, elem in enumerate(remaining):
            if i % 2 == 0:
                left.insert(0, elem)  # Insertar al inicio (más cerca del centro)
            else:
                right.append(elem)

        return left + center + right

    def _distribute_sides(self, elements):
        """
        Distribuye elementos en lados izquierdo y derecho.

        Args:
            elements: Lista de (elem_id, score)

        Returns:
            Tupla ([izquierda], [derecha])
        """
        left = []
        right = []

        for i, elem in enumerate(elements):
            if i % 2 == 0:
                left.insert(0, elem)
            else:
                right.append(elem)

        return (left, right)

    def _distribute_extremes(self, elements):
        """
        Distribuye hojas en extremos (más alejadas del centro).

        Args:
            elements: Lista de (elem_id, score) de hojas

        Returns:
            Tupla ([extremo_izq], [extremo_der])
        """
        left = []
        right = []

        for i, elem in enumerate(elements):
            if i % 2 == 0:
                left.insert(0, elem)  # Más lejanas primero
            else:
                right.append(elem)

        return (left, right)
