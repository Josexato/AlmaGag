"""
LAFOptimizer - Layout Abstracto Primero

Coordinador del sistema LAF que ejecuta las 4 fases:
1. Análisis de estructura
2. Layout abstracto (minimización de cruces)
3. Inflación de elementos (dimensiones reales)
4. Crecimiento de contenedores

Versión Sprint 4: Sistema LAF completo (Fases 1-4).

Author: José + ALMA
Version: v1.2 (Sprint 4)
Date: 2026-01-17
"""

from typing import List
from AlmaGag.layout.laf.structure_analyzer import StructureAnalyzer
from AlmaGag.layout.laf.abstract_placer import AbstractPlacer
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

    Ejecuta layout en 4 fases para minimizar cruces de conectores.
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
        debug: bool = False
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
        self.structure_analyzer = StructureAnalyzer(debug=debug)
        self.abstract_placer = AbstractPlacer(debug=debug)
        self.inflator = ElementInflator(label_optimizer=label_optimizer, debug=debug, visualdebug=visualdebug)
        self.container_grower = ContainerGrower(sizing_calculator=self.sizing, debug=debug)
        self.visualizer = GrowthVisualizer(debug=debug) if visualize_growth else None

    def _dump_layout(self, layout, phase_name):
        """Helper para hacer dump del layout en cada fase (solo en modo debug)."""
        if self.debug:
            try:
                from AlmaGag.generator import dump_layout_table
                containers = [e for e in layout.elements if 'contains' in e]
                dump_layout_table(layout, layout.elements_by_id, containers, phase=phase_name)
            except Exception as e:
                logger.warning(f"[LAF] No se pudo hacer dump de layout: {e}")

    def _write_abstract_positions_to_layout(self, abstract_positions, layout):
        """
        Escribe posiciones abstractas temporalmente en los elementos.

        Estas posiciones serán sobrescritas en Fase 3 con las posiciones reales.
        Solo se hace para que aparezcan en el dump del CSV de Fase 2.

        Args:
            abstract_positions: {element_id: (abstract_x, abstract_y)}
            layout: Layout a modificar
        """
        for elem_id, (abstract_x, abstract_y) in abstract_positions.items():
            elem = layout.elements_by_id.get(elem_id)
            if elem:
                # Escribir coordenadas abstractas (serán sobrescritas en Fase 3)
                elem['x'] = abstract_x
                elem['y'] = abstract_y

                # No asignar dimensiones aún (se hará en Fase 3)

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

    def _redistribute_vertical_after_growth(self, structure_info, layout):
        """
        Redistribuye elementos verticalmente después del crecimiento de contenedores.

        Problema: En Fase 3 (Inflación), elementos se posicionan con spacing fijo.
        En Fase 4 (Crecimiento), contenedores se expanden para envolver hijos.
        Solución: Recalcular posiciones Y respetando alturas reales de contenedores.

        Estrategia:
        1. Agrupar elementos primarios por nivel topológico
        2. Calcular posición Y para cada nivel:
           - Nivel 0: TOP_MARGIN
           - Nivel N: max(y_final del nivel anterior) + SPACING
        3. y_final = max(elem.y + elem.height) para todos los elementos del nivel

        Args:
            structure_info: Información estructural con topological_levels
            layout: Layout con elementos ya posicionados y contenedores expandidos
        """
        from AlmaGag.config import (
            TOP_MARGIN_DEBUG, TOP_MARGIN_NORMAL, ICON_HEIGHT,
            LAF_SPACING_BASE, LAF_VERTICAL_SPACING
        )

        # Obtener visualdebug del positioner si está disponible
        visualdebug = getattr(self.positioner, 'visualdebug', False) if self.positioner else False
        TOP_MARGIN = TOP_MARGIN_DEBUG if visualdebug else TOP_MARGIN_NORMAL

        # Spacing entre niveles (mismo que en Fase 5 - Inflación)
        spacing = LAF_SPACING_BASE  # 480px
        VERTICAL_SPACING = LAF_VERTICAL_SPACING  # 240px

        # Agrupar elementos primarios por nivel topológico
        # CRÍTICO: Usar el orden optimizado guardado por abstract_placer en Fase 2
        # Esto preserva el barycenter bidireccional + hub positioning
        by_level = {}

        if hasattr(layout, 'optimized_layer_order') and layout.optimized_layer_order:
            # Usar orden optimizado de Fase 2
            # IMPORTANTE: Los layers están indexados 0,1,2... pero los niveles topológicos
            # pueden ser 0,1,2,3,4... Necesitamos mapear usando el primer elemento de cada capa
            for layer_idx, layer_elements in enumerate(layout.optimized_layer_order):
                if not layer_elements:
                    continue

                # Obtener nivel topológico del primer elemento de la capa
                first_elem_id = layer_elements[0]
                actual_level = structure_info.topological_levels.get(first_elem_id, layer_idx)

                by_level[actual_level] = layer_elements.copy()

            if self.debug:
                print(f"[REDISTRIBUTE] Usando orden optimizado de Fase 2")
                for level in sorted(by_level.keys()):
                    print(f"                Nivel {level}: {' -> '.join(by_level[level])}")
        else:
            # Fallback: agrupar por nivel sin orden específico
            for elem_id in structure_info.primary_elements:
                level = structure_info.topological_levels.get(elem_id, 0)
                if level not in by_level:
                    by_level[level] = []
                by_level[level].append(elem_id)

            if self.debug:
                print(f"[REDISTRIBUTE] ADVERTENCIA: No se encontró orden optimizado, usando orden por defecto")

        if self.debug:
            print(f"[REDISTRIBUTE] Redistribuyendo {len(structure_info.primary_elements)} elementos primarios")
            print(f"               Niveles topológicos: {len(by_level)}")

        # Rastrear posición Y actual (dónde comienza el próximo nivel)
        current_y = TOP_MARGIN

        # Recorrer niveles en orden topológico
        for level_num in sorted(by_level.keys()):
            level_elements = by_level[level_num]

            if self.debug:
                print(f"\n[REDISTRIBUTE] Nivel {level_num}: {len(level_elements)} elementos")
                print(f"               Y inicial: {current_y:.1f}")

            # Calcular altura máxima del nivel
            max_height = 0
            for elem_id in level_elements:
                elem = layout.elements_by_id.get(elem_id)
                if not elem:
                    continue

                # Obtener altura real (contenedores tienen height, íconos usan ICON_HEIGHT)
                elem_height = elem.get('height', ICON_HEIGHT)
                max_height = max(max_height, elem_height)

            # Posicionar elementos del nivel en current_y
            for elem_id in level_elements:
                elem = layout.elements_by_id.get(elem_id)
                if not elem:
                    continue

                # Guardar posición anterior para debug
                old_y = elem.get('y', 0)

                # Calcular desplazamiento vertical
                dy = current_y - old_y

                # Asignar nueva posición Y
                elem['y'] = current_y

                if self.debug:
                    elem_height = elem.get('height', ICON_HEIGHT)
                    print(f"               {elem_id}: Y {old_y:.1f} -> {current_y:.1f} (h={elem_height:.1f})")

                # Actualizar etiqueta también
                if elem_id in layout.label_positions:
                    label_x, label_y, anchor, baseline = layout.label_positions[elem_id]
                    # Calcular offset de la etiqueta respecto al elemento
                    label_offset_y = label_y - old_y
                    # Aplicar mismo offset con la nueva posición
                    new_label_y = current_y + label_offset_y
                    layout.label_positions[elem_id] = (
                        label_x,
                        new_label_y,
                        anchor,
                        baseline
                    )

                # Si es un contenedor, actualizar posiciones de elementos contenidos
                if 'contains' in elem:
                    node = structure_info.element_tree.get(elem_id)
                    if node and node['children']:
                        for child_id in node['children']:
                            child = layout.elements_by_id.get(child_id)
                            if child and 'y' in child:
                                child['y'] += dy
                                if self.debug:
                                    print(f"                 |-- {child_id}: Y += {dy:.1f}")

                                # Actualizar etiqueta del hijo también
                                if child_id in layout.label_positions:
                                    child_label_x, child_label_y, child_anchor, child_baseline = layout.label_positions[child_id]
                                    layout.label_positions[child_id] = (
                                        child_label_x,
                                        child_label_y + dy,
                                        child_anchor,
                                        child_baseline
                                    )

            # Actualizar current_y para el siguiente nivel
            # current_y = donde termina este nivel + spacing
            current_y += max_height + VERTICAL_SPACING

            if self.debug:
                print(f"               Y final del nivel: {current_y - VERTICAL_SPACING:.1f}")
                print(f"               Próximo nivel comenzará en: {current_y:.1f}")

        if self.debug:
            print(f"\n[REDISTRIBUTE] Redistribución completada")
            print(f"               Altura total utilizada: {current_y:.1f}")

        # Recalcular dimensiones finales del canvas después de redistribución
        canvas_width, canvas_height = self.container_grower.calculate_final_canvas(
            structure_info,
            layout
        )
        layout.canvas['width'] = canvas_width
        layout.canvas['height'] = canvas_height

        if self.debug:
            print(f"               Canvas recalculado: {canvas_width:.0f}x{canvas_height:.0f}px")

        # IMPORTANTE: Centrado horizontal DESPUÉS de recalcular canvas final
        if self.debug:
            print(f"\n[REDISTRIBUTE] Aplicando centrado horizontal con canvas final")

        # Aplicar centrado a cada nivel
        for level_num in sorted(by_level.keys()):
            level_elements = by_level[level_num]
            self._center_elements_horizontally(level_elements, layout, structure_info, spacing=spacing)

        # CRÍTICO: Recalcular canvas DESPUÉS del centrado horizontal
        # El centrado puede mover elementos fuera de los bounds calculados anteriormente
        canvas_width, canvas_height = self.container_grower.calculate_final_canvas(
            structure_info,
            layout
        )
        layout.canvas['width'] = canvas_width
        layout.canvas['height'] = canvas_height

        if self.debug:
            print(f"\n[REDISTRIBUTE] Canvas final (post-centrado): {canvas_width:.0f}x{canvas_height:.0f}px")

    def _center_elements_horizontally(
        self,
        level_elements: List[str],
        layout,
        structure_info,
        spacing: float = LAF_SPACING_BASE
    ) -> None:
        """
        Centra elementos de un nivel horizontalmente en el canvas.

        IMPORTANTE: Los elementos ya vienen ordenados por el abstract_placer
        para minimizar cruces. Este método debe RESPETAR ese orden al centrarlos.

        Args:
            level_elements: IDs de elementos del nivel (YA ORDENADOS)
            layout: Layout con elementos posicionados
            structure_info: Información estructural con element_tree
            spacing: Spacing horizontal entre elementos
        """
        from AlmaGag.config import ICON_WIDTH, CANVAS_MARGIN_LARGE

        if not level_elements:
            return

        if self.debug:
            print(f"    [CENTRADO] Orden recibido: {' - '.join(level_elements)}")

        # Caso especial: un solo elemento
        if len(level_elements) == 1:
            elem = layout.elements_by_id.get(level_elements[0])
            if elem:
                old_x = elem.get('x', 0)
                elem['x'] = layout.canvas['width'] / 2

                if self.debug:
                    print(f"    [CENTRADO] Nivel: 1 elemento")
                    print(f"               Canvas: {layout.canvas['width']:.0f}px")
                    print(f"               {level_elements[0]}: X {old_x:.1f} -> {elem['x']:.1f} (centrado)")
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

        if self.debug:
            print(f"    [CENTRADO] Nivel: {len(level_elements)} elementos")
            print(f"               Ancho total: {total_width:.1f}px")
            print(f"               Canvas: {canvas_width:.0f}px")
            print(f"               Start X: {start_x:.1f}px")

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

            if self.debug:
                print(f"               {elem_id}: X {old_x:.1f} -> {current_x:.1f} (dx={dx:+.1f})")

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
        Ejecuta optimización LAF.

        Args:
            layout: Layout inicial

        Returns:
            Layout: Layout optimizado con Fases 1-4 aplicadas

        Sprint 4: Sistema LAF completo (Análisis, Abstracto, Inflación, Crecimiento).
        """
        if self.debug:
            print("\n" + "="*60)
            print("LAF OPTIMIZER - Layout Abstracto Primero")
            print("="*60)

        # FASE 1: Análisis de estructura
        if self.debug:
            print("\n[LAF] FASE 1: Análisis de estructura")
            print("-" * 60)

        structure_info = self.structure_analyzer.analyze(layout)

        # Capturar snapshot Fase 1
        if self.visualizer:
            # Extraer nombre del diagrama del layout si es posible
            diagram_name = getattr(layout, '_diagram_name', 'diagram')
            self.visualizer.capture_phase1(structure_info, diagram_name)

        if self.debug:
            print(f"[LAF] [OK] Analisis completado")
            print(f"      - Elementos primarios: {len(structure_info.primary_elements)}")
            print(f"      - Contenedores: {len(structure_info.container_metrics)}")
            if structure_info.container_metrics:
                max_contained = max(m['total_icons'] for m in structure_info.container_metrics.values())
                print(f"      - Max contenido: {max_contained} iconos")
            print(f"      - Conexiones: {len(structure_info.connection_sequences)}")
            scored_count = sum(1 for v in structure_info.accessibility_scores.values() if v > 0)
            if scored_count:
                max_score = max(structure_info.accessibility_scores.values())
                print(f"      - Nodos con accessibility score > 0: {scored_count} (max: {max_score:.4f})")

            # Tabla de nodos primarios
            print(f"\n[LAF] Nodos primarios clasificados ({len(structure_info.primary_elements)}):")
            print(f"      {'ID':<10} | {'Tipo':<18} | {'Elemento':<30} | {'Nivel':<6} | Hijos")
            print(f"      {'-'*10}-+-{'-'*18}-+-{'-'*30}-+-{'-'*6}-+-------")
            for elem_id in structure_info.primary_elements:
                node_id = structure_info.primary_node_ids.get(elem_id, "N/A")
                node_type = structure_info.primary_node_types.get(elem_id, "N/A")
                level = structure_info.topological_levels.get(elem_id, "N/A")
                level_str = str(level) if level != "N/A" else "N/A"
                children_count = len(structure_info.element_tree.get(elem_id, {}).get('children', []))
                # Truncar elemento ID si es muy largo
                elem_display = elem_id if len(elem_id) <= 30 else elem_id[:27] + "..."
                print(f"      {node_id:<10} | {node_type:<18} | {elem_display:<30} | {level_str:<6} | {children_count}")

        # Poblar atributos de análisis en el layout
        self._populate_layout_analysis(layout, structure_info)

        # Dump layout después de Fase 1
        self._dump_layout(layout, "LAF_PHASE_1_STRUCTURE")

        # FASE 2: Análisis topológico
        if self.debug:
            print("\n[LAF] FASE 2: Análisis topológico")
            print("-" * 60)

            # Mostrar distribución por nivel
            by_level = {}
            for elem_id, level in structure_info.topological_levels.items():
                if level not in by_level:
                    by_level[level] = []
                by_level[level].append(elem_id)

            print(f"[LAF] Niveles topológicos:")
            for level in sorted(by_level.keys()):
                elements = ', '.join(by_level[level])
                print(f"      Nivel {level}: {elements}")

            # Mostrar accessibility scores
            scored = {k: v for k, v in structure_info.accessibility_scores.items() if v > 0}
            if scored:
                print(f"\n[LAF] Scores de accesibilidad:")
                top_5 = sorted(scored.items(), key=lambda x: x[1], reverse=True)[:5]
                for elem_id, score in top_5:
                    level = structure_info.topological_levels.get(elem_id, 0)
                    print(f"      {elem_id}: {score:.4f} (nivel {level})")

            print(f"\n[LAF] [OK] Análisis topológico completado")
            print(f"      - {len(structure_info.topological_levels)} elementos con niveles")
            print(f"      - {len(scored)} elementos con accessibility score > 0")

        # Capturar snapshot Fase 2
        if self.visualizer:
            self.visualizer.capture_phase2_topology(structure_info)

        # Dump layout después de Fase 2
        self._dump_layout(layout, "LAF_PHASE_2_TOPOLOGY")

        # FASE 3: Ordenamiento por centralidad
        if self.debug:
            print("\n[LAF] FASE 3: Ordenamiento por centralidad")
            print("-" * 60)

        # Organizar elementos por nivel y score de centralidad
        centrality_order = self._order_by_centrality(structure_info)

        if self.debug:
            print(f"[LAF] Orden de centralidad por nivel:")
            for level in sorted(centrality_order.keys()):
                elements = centrality_order[level]
                print(f"      Nivel {level}: {len(elements)} elementos")
                for idx, (elem_id, score) in enumerate(elements[:5]):  # Mostrar top 5
                    node_id = structure_info.primary_node_ids.get(elem_id, "N/A")
                    position = "centro" if idx == len(elements) // 2 else ("izq" if idx < len(elements) // 2 else "der")
                    print(f"        {node_id} ({elem_id}): score={score:.4f} -> {position}")
                if len(elements) > 5:
                    print(f"        ... y {len(elements) - 5} más")

            print(f"\n[LAF] [OK] Ordenamiento por centralidad completado")
            print(f"      - {len(centrality_order)} niveles organizados")

        # Capturar snapshot Fase 3
        if self.visualizer:
            self.visualizer.capture_phase3_centrality(structure_info, centrality_order)

        # Dump layout después de Fase 3
        self._dump_layout(layout, "LAF_PHASE_3_CENTRALITY")

        # FASE 4: Layout abstracto
        if self.debug:
            print("\n[LAF] FASE 4: Layout abstracto")
            print("-" * 60)

        # Pasar centrality_order de Fase 3 como orden inicial
        abstract_positions = self.abstract_placer.place_elements(
            structure_info, layout, centrality_order=centrality_order
        )

        # Calcular cruces
        crossings = self.abstract_placer.count_crossings(abstract_positions, layout.connections)

        # Capturar snapshot Fase 4
        if self.visualizer:
            self.visualizer.capture_phase4_abstract(
                abstract_positions, crossings, layout, structure_info
            )

        if self.debug:
            print(f"[LAF] [OK] Layout abstracto completado")
            print(f"      - Posiciones calculadas: {len(abstract_positions)}")
            print(f"      - Cruces de conectores: {crossings}")

        # Escribir posiciones abstractas temporalmente para dump de Fase 4
        self._write_abstract_positions_to_layout(abstract_positions, layout)

        # Dump layout después de Fase 4
        self._dump_layout(layout, "LAF_PHASE_4_ABSTRACT")

        # FASE 5: Inflación
        if self.debug:
            print("\n[LAF] FASE 5: Inflación de elementos")
            print("-" * 60)

        spacing = self.inflator.inflate_elements(abstract_positions, structure_info, layout)

        # Capturar snapshot Fase 5
        if self.visualizer:
            self.visualizer.capture_phase5_inflated(layout, spacing)

        if self.debug:
            print(f"[LAF] [OK] Inflación completada")
            print(f"      - Spacing: {spacing:.1f}px")
            print(f"      - Elementos posicionados: {len(abstract_positions)}")
            if layout.label_positions:
                print(f"      - Etiquetas calculadas: {len(layout.label_positions)}")

        # Dump layout después de Fase 5
        self._dump_layout(layout, "LAF_PHASE_5_INFLATED")

        # FASE 6: Crecimiento de contenedores
        if self.debug:
            print("\n[LAF] FASE 6: Crecimiento de contenedores")
            print("-" * 60)

        self.container_grower.grow_containers(structure_info, layout)

        # Calcular dimensiones finales del canvas
        canvas_width, canvas_height = self.container_grower.calculate_final_canvas(
            structure_info,
            layout
        )
        layout.canvas['width'] = canvas_width
        layout.canvas['height'] = canvas_height

        # Capturar snapshot Fase 6
        if self.visualizer:
            self.visualizer.capture_phase6_containers(layout)

        if self.debug:
            print(f"[LAF] [OK] Contenedores expandidos")
            if structure_info.container_metrics:
                for container_id, metrics in structure_info.container_metrics.items():
                    container = layout.elements_by_id.get(container_id)
                    if container and 'width' in container:
                        print(f"      - {container_id}: {container['width']:.0f}x{container['height']:.0f}px "
                              f"({metrics['total_icons']} íconos)")
            print(f"      - Canvas final: {canvas_width:.0f}x{canvas_height:.0f}px")

        # Dump layout después de Fase 6
        self._dump_layout(layout, "LAF_PHASE_6_GROWN")

        # FASE 7: Redistribución vertical post-crecimiento
        if self.debug:
            print(f"\n[LAF] FASE 7: Redistribución vertical")
            print("-" * 60)

        self._redistribute_vertical_after_growth(structure_info, layout)

        # Capturar snapshot Fase 7
        if self.visualizer:
            self.visualizer.capture_phase7_redistributed(layout)

        if self.debug:
            print(f"[LAF] [OK] Redistribución vertical completada")

        # Dump layout después de Fase 7
        self._dump_layout(layout, "LAF_PHASE_7_REDISTRIBUTED")

        # FASE 8: Re-calcular routing con contenedores expandidos
        if self.router_manager:
            if self.debug:
                print(f"\n[LAF] FASE 8: Routing")
                print("-" * 60)

            self.router_manager.calculate_all_paths(layout)

            # Capturar snapshot Fase 8
            if self.visualizer:
                self.visualizer.capture_phase8_routed(layout)

            if self.debug:
                print(f"[LAF] [OK] Routing final calculado")
                print(f"      - Conexiones: {len(layout.connections)}")

                # Calcular longitud total de paths si está disponible
                total_path_length = 0
                for conn in layout.connections:
                    if 'path' in conn:
                        # Calcular longitud aproximada del path
                        points = conn['path']
                        for i in range(len(points) - 1):
                            x1, y1 = points[i]
                            x2, y2 = points[i + 1]
                            total_path_length += ((x2 - x1)**2 + (y2 - y1)**2)**0.5

                if total_path_length > 0:
                    print(f"      - Longitud total de paths: {total_path_length:.0f}px")

        # Detección de colisiones finales
        if self.collision_detector and self.debug:
            collision_count, _ = self.collision_detector.detect_all_collisions(layout)
            print(f"\n[LAF] Colisiones finales detectadas: {collision_count}")

        # FASE 9: Generar visualizaciones si está activado
        if self.visualizer:
            if self.debug:
                print(f"\n[LAF] FASE 9: Generación de SVG")
                print("-" * 60)

            # Capturar snapshot Fase 9 (final) ANTES de generar para incluirlo
            self.visualizer.capture_phase9_final(layout)

            # Generar todos los SVGs (incluido phase9)
            self.visualizer.generate_all()

            if self.debug:
                print(f"[LAF] [OK] Visualizaciones generadas")
                print(f"      - Directorio: debug/growth/")
                print(f"      - Canvas final: {canvas_width:.0f}x{canvas_height:.0f}px")

        if self.debug:
            print("\n" + "="*60)
            if self.visualize_growth:
                print("[LAF] Sistema LAF completo (Fases 1-9)")
            else:
                print("[LAF] Sistema LAF completo (Fases 1-9)")
            print("[LAF]   - Fase 1: Análisis de estructura")
            print("[LAF]   - Fase 2: Análisis topológico")
            print("[LAF]   - Fase 3: Ordenamiento por centralidad")
            print("[LAF]   - Fase 4: Layout abstracto")
            print("[LAF]   - Fase 5: Inflación de elementos")
            print("[LAF]   - Fase 6: Crecimiento de contenedores")
            print("[LAF]   - Fase 7: Redistribución vertical")
            print("[LAF]   - Fase 8: Routing")
            print("[LAF]   - Fase 9: Generación de SVG")
            print("="*60 + "\n")

        return layout

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
