"""
ContainerGrower - Fase 6 de LAF (Inflación + Crecimiento de Contenedores)

Expande contenedores a sus dimensiones finales basándose en elementos
contenidos, siguiendo un enfoque bottom-up.

Author: José + ALMA
Version: v1.0
Date: 2026-01-17
"""

import logging
from typing import Dict, List, Tuple
from AlmaGag.config import ICON_WIDTH, ICON_HEIGHT
from AlmaGag.layout.laf.structure_analyzer import StructureInfo

logger = logging.getLogger('AlmaGag')


class ContainerGrower:
    """
    Expande contenedores a dimensiones reales (bottom-up).

    Algoritmo:
    1. Ordenar contenedores por profundidad (más anidados primero)
    2. Para cada contenedor:
       - Calcular bounding box de elementos contenidos
       - Incluir etiquetas de elementos contenidos
       - Agregar padding proporcional
       - Agregar espacio para etiqueta del contenedor
       - Posicionar ícono del contenedor
       - Propagar coordenadas globales a hijos
    """

    def __init__(self, sizing_calculator=None, debug: bool = False):
        """
        Inicializa el crecedor de contenedores.

        Args:
            sizing_calculator: SizingCalculator para obtener tamaños con hp/wp
            debug: Si True, imprime logs de debug
        """
        self.sizing = sizing_calculator
        self.debug = debug

    def grow_containers(
        self,
        structure_info: StructureInfo,
        layout
    ) -> None:
        """
        Expande contenedores bottom-up.

        Args:
            structure_info: Información estructural con element_tree
            layout: Layout a modificar in-place
        """
        # Paso 1: Ordenar contenedores por profundidad (bottom-up)
        sorted_containers = self._sort_containers_by_depth(structure_info)

        # Paso 2: Procesar cada contenedor
        for container_id in sorted_containers:
            self._grow_single_container(
                container_id,
                structure_info,
                layout
            )

    def _sort_containers_by_depth(
        self,
        structure_info: StructureInfo
    ) -> List[str]:
        """
        Ordena contenedores por profundidad (bottom-up).

        Args:
            structure_info: Información estructural

        Returns:
            Lista de container_ids ordenados por profundidad descendente
        """
        containers = []

        for elem_id, node in structure_info.element_tree.items():
            if node['is_container']:
                containers.append((elem_id, node['depth']))

        # Ordenar por profundidad descendente (más anidados primero)
        containers.sort(key=lambda x: x[1], reverse=True)

        return [container_id for container_id, _ in containers]

    def _build_contained_subgraph(
        self,
        children: List[str],
        connections: List[dict]
    ) -> Dict[str, List[str]]:
        """
        Construye grafo de conexiones entre elementos contenidos.

        Solo considera conexiones INTERNAS (ambos extremos dentro del contenedor).

        Args:
            children: IDs de elementos contenidos
            connections: Todas las conexiones del diagrama

        Returns:
            {elem_id: [connected_ids]} solo para conexiones internas
        """
        children_set = set(children)
        subgraph = {child_id: [] for child_id in children}

        for conn in connections:
            from_id = conn.get('from')
            to_id = conn.get('to')

            # Solo conexiones internas (ambos extremos dentro del contenedor)
            if from_id in children_set and to_id in children_set:
                subgraph[from_id].append(to_id)

        pass  # subgrafo construido

        return subgraph

    def _assign_to_layers(
        self,
        children: List[str],
        subgraph: Dict[str, List[str]],
        layout
    ) -> List[List[str]]:
        """
        Asigna elementos a capas usando BFS desde nodos fuente.

        Implementa Layering de Sugiyama: niveles topológicos bottom-up.

        Args:
            children: IDs de elementos contenidos
            subgraph: Grafo de conexiones internas
            layout: Layout con elements_by_id

        Returns:
            [[layer0_elems], [layer1_elems], ...] ordenado por nivel topológico
        """
        # Calcular in-degree (cuántas conexiones entrantes)
        in_degree = {child_id: 0 for child_id in children}
        for from_id in subgraph:
            for to_id in subgraph[from_id]:
                in_degree[to_id] += 1

        # BFS desde nodos fuente (in_degree == 0)
        levels = {}
        queue = [(child_id, 0) for child_id in children if in_degree[child_id] == 0]

        # Si no hay fuentes (grafo cíclico o sin conexiones), usar todos como fuentes
        if not queue:
            queue = [(child_id, 0) for child_id in children]

        visited = set()
        while queue:
            elem_id, level = queue.pop(0)

            if elem_id in visited:
                continue
            visited.add(elem_id)

            levels[elem_id] = level

            # Agregar hijos al siguiente nivel
            for child_id in subgraph.get(elem_id, []):
                if child_id not in visited:
                    queue.append((child_id, level + 1))

        # Agrupar por nivel
        max_level = max(levels.values()) if levels else 0
        layers = [[] for _ in range(max_level + 1)]

        for elem_id, level in levels.items():
            layers[level].append(elem_id)

        # Elementos sin conexiones (huérfanos) van a la última capa
        orphans = [c for c in children if c not in levels]
        if orphans:
            layers.append(orphans)

        pass  # layering asignado

        return layers

    def _order_layers_barycenter(
        self,
        layers: List[List[str]],
        subgraph: Dict[str, List[str]],
        layout,
        iterations: int = 3
    ) -> None:
        """
        Ordena elementos dentro de capas usando barycenter heuristic.

        Minimiza cruces de conexiones entre capas consecutivas.
        Modifica layers in-place.

        Args:
            layers: Lista de capas a ordenar
            subgraph: Grafo de conexiones internas
            layout: Layout con elements_by_id
            iterations: Número de iteraciones de optimización
        """
        pass  # optimización de orden

        for iteration in range(iterations):
            # Forward pass (de arriba hacia abajo)
            for i in range(1, len(layers)):
                self._reorder_layer_by_barycenter(
                    layers[i],
                    layers[i-1],
                    subgraph,
                    layout,
                    direction='forward'
                )

            # Backward pass (de abajo hacia arriba)
            for i in range(len(layers) - 2, -1, -1):
                self._reorder_layer_by_barycenter(
                    layers[i],
                    layers[i+1],
                    subgraph,
                    layout,
                    direction='backward'
                )

    def _reorder_layer_by_barycenter(
        self,
        layer: List[str],
        adjacent_layer: List[str],
        subgraph: Dict[str, List[str]],
        layout,
        direction: str
    ) -> None:
        """
        Reordena una capa según barycenter de conexiones con capa adyacente.

        Modifica layer in-place.

        Args:
            layer: Capa a reordenar
            adjacent_layer: Capa adyacente (anterior o posterior)
            subgraph: Grafo de conexiones
            layout: Layout con elements_by_id
            direction: 'forward' o 'backward'
        """
        # Construir índice de posiciones en capa adyacente
        adjacent_positions = {elem_id: idx for idx, elem_id in enumerate(adjacent_layer)}

        # Calcular barycenter para cada elemento
        barycenters = []

        for elem_id in layer:
            # Encontrar elementos conectados en capa adyacente
            if direction == 'forward':
                # Buscar predecesores (quién apunta a mí desde la capa anterior)
                connected = [
                    from_id for from_id in adjacent_layer
                    if elem_id in subgraph.get(from_id, [])
                ]
            else:  # backward
                # Buscar sucesores (a quién apunto en la capa posterior)
                connected = [
                    to_id for to_id in subgraph.get(elem_id, [])
                    if to_id in adjacent_layer
                ]

            if connected:
                # Barycenter = promedio de posiciones conectadas
                positions = [adjacent_positions[c] for c in connected]
                barycenter = sum(positions) / len(positions)
            else:
                # Sin conexiones: mantener posición actual
                barycenter = layer.index(elem_id)

            # Ordenar también por tipo (heurística secundaria para desempate)
            elem = layout.elements_by_id.get(elem_id, {})
            elem_type = elem.get('type', 'default')

            barycenters.append((barycenter, elem_type, elem_id))

        # Ordenar por barycenter (y tipo como desempate)
        barycenters.sort(key=lambda x: (x[0], x[1]))

        # Actualizar layer in-place
        layer[:] = [elem_id for _, _, elem_id in barycenters]

    @staticmethod
    def _compute_label_bbox(elem, label_x, label_y, label_height, anchor):
        """Calcula el bounding box de una etiqueta."""
        label_text = elem.get('label', '')
        lines = label_text.split('\n')
        label_width = max(len(line) for line in lines) * 8  # ~8px/char at 14px font

        if anchor == 'middle':
            x1 = label_x - label_width / 2
            x2 = label_x + label_width / 2
        elif anchor == 'end':
            x1 = label_x - label_width
            x2 = label_x
        else:  # 'start'
            x1 = label_x
            x2 = label_x + label_width

        return (x1, label_y, x2, label_y + label_height)

    @staticmethod
    def _bbox_overlaps(a, b):
        """Verifica si dos bboxes (x1,y1,x2,y2) se solapan."""
        return not (a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1])

    def _find_best_label_position(self, elem, current_x, current_y,
                                   elem_width, elem_height, placed_bboxes):
        """
        Busca la mejor posición para una etiqueta entre 4 candidatas,
        verificando colisiones contra bboxes ya colocados.

        Returns:
            (label_x, label_y, anchor, position_name, label_height)
        """
        label_text = elem.get('label', '')
        lines = label_text.split('\n')
        label_height = len(lines) * 18

        candidates = [
            ('bottom', current_x + elem_width / 2,
             current_y + elem_height + 15, 'middle'),
            ('right', current_x + elem_width + 10,
             current_y + elem_height / 2, 'start'),
            ('top', current_x + elem_width / 2,
             current_y - label_height - 5, 'middle'),
            ('left', current_x - 10,
             current_y + elem_height / 2, 'end'),
        ]

        for pos_name, lx, ly, anchor in candidates:
            bbox = self._compute_label_bbox(elem, lx, ly, label_height, anchor)
            has_collision = False
            for placed in placed_bboxes:
                if self._bbox_overlaps(bbox, placed):
                    has_collision = True
                    break
            if not has_collision:
                return lx, ly, anchor, pos_name, label_height

        # Fallback: bottom (posición original)
        return (candidates[0][1], candidates[0][2],
                candidates[0][3], 'bottom', label_height)

    def _position_contained_elements(
        self,
        children: List[str],
        layout,
        padding: float,
        header_height: float,
        container_width: float
    ) -> None:
        """
        Posiciona elementos contenidos usando Sugiyama miniatura.

        CONDICIONES IMPLEMENTADAS:
        1. Distribución simétrica (centrado) ✅
        2. Tamaños reales (hp/wp, contenedores anidados) ✅
        3. Bottom-up resuelto (llamado desde grow_containers) ✅
        4. No bloquea header del contenedor ✅
        5. Minimiza cruces de conexiones (Sugiyama) ✅

        Args:
            children: Lista de IDs de elementos hijos
            layout: Layout con elements_by_id, connections, label_positions
            padding: Padding del contenedor
            header_height: Altura del header (ícono + etiqueta del contenedor)
            container_width: Ancho del contenedor (para centrar)
        """
        if not children:
            return

        spacing = ICON_WIDTH * 0.625  # 50px

        # FASE 1: Análisis de grafo
        subgraph = self._build_contained_subgraph(children, layout.connections)

        # FASE 2: Layering (niveles topológicos)
        layers = self._assign_to_layers(children, subgraph, layout)

        # FASE 3: Ordering (barycenter para minimizar cruces)
        self._order_layers_barycenter(layers, subgraph, layout, iterations=3)

        # FASE 4: Positioning (distribuir simétricamente)
        # IMPORTANTE: Los elementos se posicionan en el "box de contenido",
        # con coordenadas locales relativas al contenido (SIN header).
        # El header se añadirá arriba al convertir a globales.
        current_y = padding

        # Tracking de bboxes colocados para detección de colisiones de etiquetas
        placed_bboxes = []  # Lista de (x1, y1, x2, y2)

        for layer_idx, layer in enumerate(layers):
            # Calcular dimensiones de elementos en esta capa
            layer_widths = []
            layer_heights = []
            layer_max_height = 0

            for elem_id in layer:
                elem = layout.elements_by_id.get(elem_id)
                if not elem:
                    continue

                # Tamaño real (CONDICIÓN 2: considera hp/wp o contenedores anidados)
                if self.sizing:
                    elem_w, elem_h = self.sizing.get_element_size(elem)
                else:
                    elem_w, elem_h = ICON_WIDTH, ICON_HEIGHT

                layer_widths.append(elem_w)
                layer_heights.append(elem_h)
                layer_max_height = max(layer_max_height, elem_h)

                # Considerar altura de etiqueta
                if elem.get('label'):
                    lines = elem['label'].split('\n')
                    label_height = len(lines) * 18
                    elem_total_height = elem_h + 15 + label_height
                    layer_max_height = max(layer_max_height, elem_total_height)

            # Calcular ancho total de la capa
            total_layer_width = sum(layer_widths) + (len(layer_widths) - 1) * spacing

            # Centrar capa (CONDICIÓN 1: distribución simétrica)
            # available_width es el ancho del box de contenido (sin padding)
            available_width = container_width - 2 * padding
            start_x = (available_width - total_layer_width) / 2

            # CONDICIÓN 4: Los elementos se posicionan en el box de contenido,
            # el header se añade arriba al convertir a globales.
            # No necesitamos offset horizontal adicional.

            # Posicionar elementos de la capa
            current_x = start_x
            layer_bottom = current_y

            for elem_id, elem_width, elem_height in zip(layer, layer_widths, layer_heights):
                elem = layout.elements_by_id.get(elem_id)
                if not elem:
                    continue

                # Asignar posición LOCAL (relativa al box de contenido)
                elem['x'] = current_x
                elem['y'] = current_y
                elem['width'] = elem_width
                elem['height'] = elem_height

                # Registrar bbox del ícono para detección de colisiones
                placed_bboxes.append((
                    current_x, current_y,
                    current_x + elem_width, current_y + elem_height
                ))

                # Calcular posición de etiqueta con detección de colisiones
                if elem.get('label'):
                    label_x, label_y, anchor, pos_name, label_h = (
                        self._find_best_label_position(
                            elem, current_x, current_y,
                            elem_width, elem_height, placed_bboxes
                        )
                    )

                    layout.label_positions[elem_id] = (
                        label_x, label_y, anchor, pos_name
                    )

                    # Registrar bbox de la etiqueta colocada
                    label_bbox = self._compute_label_bbox(
                        elem, label_x, label_y, label_h, anchor
                    )
                    placed_bboxes.append(label_bbox)

                    # Actualizar layer_bottom considerando la posición real
                    label_bottom = label_bbox[3]  # y2 del bbox
                    layer_bottom = max(layer_bottom, label_bottom)

                else:
                    layer_bottom = max(layer_bottom, current_y + elem_height)

                # Avanzar horizontalmente
                current_x += elem_width + spacing

            # Siguiente capa
            current_y = layer_bottom + spacing

    def _measure_placed_content(
        self,
        children: List[str],
        layout,
        padding: float
    ) -> Tuple[float, float, float]:
        """
        Mide el bounding box real de los elementos posicionados + sus etiquetas.

        Coordenadas locales (relativas al box de contenido del contenedor).

        Args:
            children: IDs de elementos hijos
            layout: Layout con elements_by_id y label_positions
            padding: Padding del contenedor

        Returns:
            (min_x, max_x, max_y) del contenido colocado (coordenadas locales)
        """
        min_x = float('inf')
        max_x = float('-inf')
        max_y = float('-inf')

        for child_id in children:
            child = layout.elements_by_id.get(child_id)
            if not child or 'x' not in child:
                continue

            cx = child['x']
            cy = child['y']
            cw = child.get('width', ICON_WIDTH)
            ch = child.get('height', ICON_HEIGHT)

            min_x = min(min_x, cx)
            max_x = max(max_x, cx + cw)
            max_y = max(max_y, cy + ch)

            # Considerar etiqueta posicionada
            if child_id in layout.label_positions:
                lx, ly, anchor, _ = layout.label_positions[child_id]
                label_text = child.get('label', '')
                if label_text:
                    lines = label_text.split('\n')
                    label_w = max(len(line) for line in lines) * 8
                    label_h = len(lines) * 18

                    if anchor == 'middle':
                        lx1 = lx - label_w / 2
                        lx2 = lx + label_w / 2
                    elif anchor == 'end':
                        lx1 = lx - label_w
                        lx2 = lx
                    else:  # 'start'
                        lx1 = lx
                        lx2 = lx + label_w

                    min_x = min(min_x, lx1)
                    max_x = max(max_x, lx2)
                    max_y = max(max_y, ly + label_h)

        if min_x == float('inf'):
            return (0, 0, 0)

        return (min_x, max_x, max_y)

    def _calculate_content_dimensions(
        self,
        children: List[str],
        layout,
        spacing: float
    ) -> Tuple[float, float]:
        """
        Calcula dimensiones necesarias para contenido (sin posicionar).

        Usa Sugiyama para determinar capas y calcular el ancho máximo
        y altura total necesaria.

        Args:
            children: Lista de IDs de elementos hijos
            layout: Layout con elements_by_id y connections
            spacing: Espaciado entre elementos

        Returns:
            (max_width, total_height): Dimensiones del contenido
        """
        if not children:
            return (0, 0)

        # Usar Sugiyama para determinar capas
        subgraph = self._build_contained_subgraph(children, layout.connections)
        layers = self._assign_to_layers(children, subgraph, layout)
        self._order_layers_barycenter(layers, subgraph, layout, iterations=3)

        max_width = 0
        total_height = 0

        for layer in layers:
            # Calcular ancho de esta capa
            layer_widths = []
            layer_max_height = 0

            for elem_id in layer:
                elem = layout.elements_by_id.get(elem_id)
                if not elem:
                    continue

                # Tamaño real
                if self.sizing:
                    elem_w, elem_h = self.sizing.get_element_size(elem)
                else:
                    elem_w, elem_h = ICON_WIDTH, ICON_HEIGHT

                layer_widths.append(elem_w)
                layer_max_height = max(layer_max_height, elem_h)

                # Considerar etiqueta
                if elem.get('label'):
                    lines = elem['label'].split('\n')
                    label_height = len(lines) * 18
                    elem_total_height = elem_h + 15 + label_height
                    layer_max_height = max(layer_max_height, elem_total_height)

            # Ancho total de la capa
            layer_width = sum(layer_widths) + (len(layer_widths) - 1) * spacing
            max_width = max(max_width, layer_width)

            # Altura acumulada
            total_height += layer_max_height + spacing

        # Quitar último spacing
        if total_height > 0:
            total_height -= spacing

        return (max_width, total_height)

    def _calculate_header_height(self, container: dict) -> float:
        """
        Calcula la altura del header del contenedor (ícono + etiqueta).

        La etiqueta está a la derecha del ícono, empezando en y=16.
        El header debe tener suficiente altura para acomodar AMBOS.

        Args:
            container: Elemento contenedor

        Returns:
            float: Altura del header
        """
        # Altura del ícono del contenedor (desde y=0)
        icon_height = ICON_HEIGHT  # 50px

        # Posición Y donde empieza la etiqueta (centrada con el ícono)
        label_start_y = 16

        # Calcular hasta dónde se extiende la etiqueta
        if container.get('label'):
            label_text = container['label']
            lines = label_text.split('\n')
            label_height = len(lines) * 18  # 18px por línea
            label_bottom = label_start_y + label_height

            # El header debe acomodar lo que se extienda más abajo
            return max(icon_height, label_bottom)
        else:
            return icon_height

    def _grow_single_container(
        self,
        container_id: str,
        structure_info: StructureInfo,
        layout
    ) -> None:
        """
        Calcula dimensiones y posiciones para un contenedor.

        NUEVO FLUJO (v2.0 con Sugiyama):
        1. Calcular header del contenedor
        2. Calcular dimensiones necesarias (PRIMERA PASADA - sin posicionar)
        3. Calcular ancho del contenedor
        4. Posicionar elementos (SEGUNDA PASADA - con ancho conocido para centrar)
        5. Calcular altura final
        6. Convertir coordenadas locales a globales

        Args:
            container_id: ID del contenedor
            structure_info: Información estructural
            layout: Layout a modificar
        """
        container = layout.elements_by_id.get(container_id)
        if not container:
            return

        node = structure_info.element_tree[container_id]
        children = node['children']

        if not children:
            container['width'] = 200
            container['height'] = 150
            return

        # Padding: usar el especificado en el contenedor o calcular proporcionalmente
        padding = container.get('padding', ICON_WIDTH * 0.125)  # Default: 10px con ICON_WIDTH=80
        spacing = ICON_WIDTH * 0.625  # 50px

        # PASO 1: Calcular header del contenedor
        header_height = self._calculate_header_height(container)

        # PASO 2: Calcular dimensiones necesarias (PRIMERA PASADA)
        content_width, content_height = self._calculate_content_dimensions(
            children, layout, spacing
        )

        # PASO 3: Calcular ancho del contenedor
        final_width = content_width + (2 * padding)

        # Verificar ancho mínimo para etiqueta del contenedor
        if container.get('label'):
            label_text = container['label']
            lines = label_text.split('\n')
            max_line_len = max(len(line) for line in lines) if lines else 0
            label_width = max_line_len * 8
            min_width_for_label = 10 + ICON_WIDTH + 10 + label_width + 10
            final_width = max(final_width, min_width_for_label)

        # PASO 4: Posicionar elementos (SEGUNDA PASADA - con ancho conocido)
        self._position_contained_elements(
            children, layout, padding, header_height, final_width
        )

        # PASO 4.5: Recalcular bounds reales (íconos + etiquetas posicionadas)
        # Las etiquetas pueden haberse colocado a la derecha/izquierda y exceder
        # el ancho estimado en paso 2. Expandir contenedor si es necesario.
        actual_min_x, actual_max_x, actual_max_y = self._measure_placed_content(
            children, layout, padding
        )
        actual_content_width = actual_max_x - actual_min_x
        actual_content_height = actual_max_y

        if actual_content_width + (2 * padding) > final_width:
            old_width = final_width
            final_width = actual_content_width + (2 * padding)

            # Re-centrar elementos: shift_x para compensar el nuevo ancho
            # actual_min_x es la x mínima del contenido; queremos que el contenido
            # quede centrado en el nuevo ancho
            desired_min_x = (final_width - 2 * padding - actual_content_width) / 2
            shift_x = desired_min_x - actual_min_x
            if abs(shift_x) > 0.5:
                for child_id in children:
                    child = layout.elements_by_id.get(child_id)
                    if child and 'x' in child:
                        child['x'] += shift_x
                    if child_id in layout.label_positions:
                        lx, ly, anch, bl = layout.label_positions[child_id]
                        layout.label_positions[child_id] = (lx + shift_x, ly, anch, bl)

            # Verificar ancho mínimo para etiqueta del contenedor (de nuevo)
            if container.get('label'):
                label_text = container['label']
                lines = label_text.split('\n')
                max_line_len = max(len(line) for line in lines) if lines else 0
                lbl_width = max_line_len * 8
                min_width_for_label = 10 + ICON_WIDTH + 10 + lbl_width + 10
                final_width = max(final_width, min_width_for_label)

        # Usar la altura real del contenido si es mayor que la estimada
        content_height = max(content_height, actual_content_height)

        # PASO 5: Calcular altura final del contenedor
        final_height = padding + header_height + padding + content_height + padding

        if self.debug:
            logger.debug(f"  {container_id}: {final_width:.0f}x{final_height:.0f}px ({len(children)} hijos)")

        # Asignar dimensiones finales
        container['width'] = final_width
        container['height'] = final_height

        # Marcar como contenedor calculado para que draw_container use estas dimensiones
        container['_is_container_calculated'] = True

        # PASO 6: Posicionar etiqueta del contenedor
        if container.get('label'):
            # Etiqueta a la derecha del ícono del contenedor
            label_x = 10 + ICON_WIDTH + 10  # Margen + ícono + margen
            label_y = 16  # Centrada verticalmente con el ícono
            layout.label_positions[container_id] = (
                label_x,
                label_y,
                'start',  # Alineada a la izquierda desde label_x
                'top'     # Baseline en top
            )

        # PASO 7: Convertir coordenadas locales a globales
        container_x = container.get('x', 0)
        container_y = container.get('y', 0)

        # IMPORTANTE: Las coordenadas locales están en el "box de contenido".
        # Al convertir a globales, sumamos:
        # - container_y: posición Y del contenedor en el canvas
        # - padding: espacio superior del contenedor
        # - header_height: espacio del header (ícono + etiqueta del contenedor)
        content_offset_y = padding + header_height

        pass  # propagando coordenadas

        for child_id in children:
            child = layout.elements_by_id.get(child_id)
            if child and 'x' in child and 'y' in child:
                # Guardar coordenadas locales (relativas al box de contenido)
                local_x = child['x']
                local_y = child['y']

                # Convertir a coordenadas GLOBALES
                # x_global = local_x + padding + container_x
                # y_global = local_y + content_offset_y + container_y
                child['x'] = local_x + padding + container_x
                child['y'] = local_y + content_offset_y + container_y

                # Actualizar etiqueta también (suma padding + content_offset_y)
                if child_id in layout.label_positions:
                    label_x, label_y, anchor, baseline = layout.label_positions[child_id]

                    global_label_x = label_x + padding + container_x
                    global_label_y = label_y + content_offset_y + container_y

                    layout.label_positions[child_id] = (
                        global_label_x,
                        global_label_y,
                        anchor,
                        baseline
                    )

    def calculate_final_canvas(
        self,
        structure_info: StructureInfo,
        layout
    ) -> Tuple[float, float]:
        """
        Calcula dimensiones finales del canvas después del crecimiento.

        IMPORTANTE: Debe considerar TODOS los elementos (primarios y contenidos)
        ya que los elementos contenidos tienen coordenadas globales después
        de la conversión local->global en la Fase 6.

        Args:
            structure_info: Información estructural
            layout: Layout con elementos posicionados

        Returns:
            Tupla (width, height) del canvas
        """
        # Encontrar bounds de TODOS los elementos (primarios y contenidos)
        max_x = 0
        max_y = 0

        # Recorrer todos los elementos del layout
        for elem in layout.elements:
            elem_id = elem['id']

            # Skip elementos sin posición
            if 'x' not in elem or 'y' not in elem:
                continue

            elem_x = elem['x']
            elem_y = elem['y']
            elem_w = elem.get('width', ICON_WIDTH)
            elem_h = elem.get('height', ICON_HEIGHT)

            max_x = max(max_x, elem_x + elem_w)
            max_y = max(max_y, elem_y + elem_h)

            # Incluir etiqueta si existe
            if elem_id in layout.label_positions:
                label_x, label_y, _, _ = layout.label_positions[elem_id]
                label_text = elem.get('label', '')

                # Calcular ancho real de la etiqueta considerando múltiples líneas
                lines = label_text.split('\n')
                max_line_len = max(len(line) for line in lines) if lines else 0
                label_w = max_line_len * 8  # 8px por carácter
                label_h = len(lines) * 18   # 18px por línea

                max_x = max(max_x, label_x + label_w)
                max_y = max(max_y, label_y + label_h)

        # Agregar margen
        # Margen base: 50px
        # Margen adicional para badge de debug que se dibuja en esquina superior derecha
        # El badge se posiciona en x=canvas_width-200 con texto de ~232px
        # Total: se necesita al menos 232px adicionales desde la posición del badge
        # Margen seguro: 250px para acomodar badge + espacio
        margin = 250
        canvas_width = max_x + margin
        canvas_height = max_y + margin

        return (canvas_width, canvas_height)
