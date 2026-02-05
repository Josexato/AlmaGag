"""
AbstractPlacer - Posicionamiento abstracto de elementos minimizando cruces

Implementa algoritmo híbrido basado en Sugiyama para layout jerárquico:
1. Layering: Asignar elementos a capas según nivel topológico
2. Ordering: Ordenar dentro de capas usando barycenter + tipo
3. Positioning: Distribuir uniformemente minimizando cruces

Author: José + ALMA
Version: v1.0
Date: 2026-01-17
"""

from typing import Dict, List, Tuple, Set
from AlmaGag.layout.laf.structure_analyzer import StructureInfo


class AbstractPlacer:
    """
    Posiciona elementos como puntos de 1px minimizando cruces.

    Usa 4 heurísticas:
    1. Tipo de elementos (similares cerca)
    2. Secuencia topológica (respeta orden de conexión)
    3. Distribución simétrica por tipo
    4. Minimización de cruces por capas (barycenter)
    """

    # Cuánto influye el Score de accesibilidad en la atracción al centro.
    # 0.0 = sin efecto, 1.0 = Score domina completamente sobre barycenter.
    # Valores típicos: 0.2 - 0.4
    SCORE_CENTER_INFLUENCE = 0.3

    def __init__(self, debug: bool = False):
        """
        Inicializa el placer abstracto.

        Args:
            debug: Si True, imprime logs de debug
        """
        self.debug = debug

    def place_elements(
        self,
        structure_info: StructureInfo,
        layout
    ) -> Dict[str, Tuple[int, int]]:
        """
        Calcula posiciones abstractas (x, y) para TODOS los elementos.

        Algoritmo:
        1. Agrupar elementos primarios por nivel topológico (capas horizontales)
        2. Dentro de cada capa, ordenar por tipo + barycenter
        3. Aplicar barycenter heuristic para minimizar cruces
        4. Distribuir simétricamente dentro de cada capa
        5. Asignar posiciones abstractas a elementos contenidos (grid horizontal)

        Args:
            structure_info: Información estructural del diagrama
            layout: Layout con connections

        Returns:
            {element_id: (abstract_x, abstract_y)}
            - abstract_x, abstract_y son flotantes/enteros
            - Incluye TODOS los elementos (primarios y contenidos)
        """
        # Fase 1: Layering (asignar elementos primarios a capas)
        layers = self._assign_layers(structure_info)

        if self.debug:
            print(f"\n[ABSTRACT] Layering completado: {len(layers)} capas")
            for level, elements in enumerate(layers):
                print(f"  Capa {level}: {len(elements)} elementos")

        # Fase 2: Ordering (ordenar dentro de capas)
        self._order_within_layers(layers, structure_info, layout)

        # CRÍTICO: Guardar COPIA PROFUNDA del orden optimizado para usarlo en Fase 4.5
        # Esto preserva el orden de barycenter bidireccional + hub positioning
        layout.optimized_layer_order = [layer.copy() for layer in layers]

        if self.debug:
            print(f"\n[ABSTRACT] Ordering completado")
            print(f"           Orden final guardado para Fase 4.5:")
            for idx, layer in enumerate(layout.optimized_layer_order):
                if len(layer) > 1:
                    print(f"             Capa {idx}: {' -> '.join(layer)}")

            # Verificar que coincide con el estado actual de layers
            for idx in range(len(layers)):
                if len(layers[idx]) > 1 and layers[idx] != layout.optimized_layer_order[idx]:
                    print(f"           ⚠️ ADVERTENCIA: Capa {idx} difiere:")
                    print(f"              layers actual: {' -> '.join(layers[idx])}")
                    print(f"              guardado:      {' -> '.join(layout.optimized_layer_order[idx])}")

        # Fase 3: Positioning (asignar coordenadas abstractas a primarios)
        positions = self._assign_abstract_positions(layers)

        # Fase 4: Positioning de elementos contenidos (grid horizontal)
        self._assign_contained_positions(positions, structure_info, layout)

        if self.debug:
            primary_count = len(structure_info.primary_elements)
            contained_count = len(positions) - primary_count
            print(f"\n[ABSTRACT] Posiciones asignadas:")
            print(f"           - Primarios: {primary_count}")
            print(f"           - Contenidos: {contained_count}")
            print(f"           - Total: {len(positions)}")

        # Calcular cruces finales
        if self.debug:
            initial_crossings = self.count_crossings(positions, layout.connections)
            print(f"\n[ABSTRACT] Cruces calculados: {initial_crossings}")

        return positions

    def _assign_layers(self, structure_info: StructureInfo) -> List[List[str]]:
        """
        Asigna elementos a capas según nivel topológico.

        Args:
            structure_info: Información estructural

        Returns:
            Lista de capas, cada capa es lista de element_ids
            Capa 0 = nivel topológico 0 (sin dependencias entrantes)
            Capa N = nivel topológico N
        """
        # Obtener máximo nivel
        if not structure_info.topological_levels:
            # Fallback: todos en capa 0
            return [structure_info.primary_elements]

        max_level = max(structure_info.topological_levels.values())

        # Inicializar capas
        layers = [[] for _ in range(max_level + 1)]

        # Asignar elementos a capas
        for elem_id in structure_info.primary_elements:
            level = structure_info.topological_levels.get(elem_id, 0)
            layers[level].append(elem_id)

        return layers

    def _order_within_layers(
        self,
        layers: List[List[str]],
        structure_info: StructureInfo,
        layout
    ) -> None:
        """
        Ordena elementos dentro de cada capa usando barycenter bidireccional.

        Modifica layers in-place.

        NUEVO: Barycenter bidireccional con múltiples iteraciones.
        - Forward barycenter: considera capa anterior
        - Backward barycenter: considera capa siguiente
        - Iteraciones: repite proceso para refinar orden

        Args:
            layers: Lista de capas a ordenar
            structure_info: Información estructural
            layout: Layout con connections
        """
        # Primera capa: ordenar por tipo + cantidad de conexiones
        if layers:
            self._order_first_layer(layers[0], structure_info)

        # Aplicar barycenter bidireccional con múltiples iteraciones
        # para minimizar cruces de conectores
        iterations = 4  # Número de pasadas de optimización

        for iteration in range(iterations):
            # Forward pass: considerar capa anterior
            for layer_idx in range(1, len(layers)):
                self._order_layer_barycenter_forward(
                    layers[layer_idx],
                    layers[layer_idx - 1],
                    structure_info,
                    layout
                )

            # Backward pass: considerar capa siguiente
            for layer_idx in range(len(layers) - 2, 0, -1):
                self._order_layer_barycenter_backward(
                    layers[layer_idx],
                    layers[layer_idx + 1],
                    structure_info,
                    layout
                )

            # Hub positioning DESPUÉS de ambos passes para que sea el último ajuste
            for layer_idx in range(len(layers)):
                if len(layers[layer_idx]) >= 3:
                    self._position_hub_containers_in_center(
                        layers[layer_idx],
                        structure_info,
                        layout
                    )

            if self.debug and iteration == iterations - 1:
                print(f"\n           Orden FINAL después de iteración {iteration + 1}:")
                for layer_idx, layer in enumerate(layers):
                    if len(layer) > 1:
                        print(f"             Capa {layer_idx}: {' -> '.join(layer)}")

    def _order_first_layer(
        self,
        layer: List[str],
        structure_info: StructureInfo
    ) -> None:
        """
        Ordena primera capa por tipo + cantidad de conexiones.

        Args:
            layer: Lista de element_ids a ordenar (modifica in-place)
            structure_info: Información estructural
        """
        # Obtener tipo y cantidad de conexiones de cada elemento
        def get_sort_key(elem_id: str) -> Tuple[str, int]:
            # Tipo del elemento
            elem_type = 'unknown'
            for etype, ids in structure_info.element_types.items():
                if elem_id in ids:
                    elem_type = etype
                    break

            # Cantidad de conexiones (salientes)
            conn_count = len(structure_info.connection_graph.get(elem_id, []))

            return (elem_type, -conn_count)  # Negativo para ordenar desc

        layer.sort(key=get_sort_key)

    def _order_layer_barycenter_forward(
        self,
        current_layer: List[str],
        previous_layer: List[str],
        structure_info: StructureInfo,
        layout
    ) -> None:
        """
        Ordena capa usando forward barycenter (considera capa anterior).

        MEJORADO: Para contenedores, también considera conexiones entrantes
        a sus hijos desde otros elementos del mismo nivel.

        Args:
            current_layer: Capa actual a ordenar (modifica in-place)
            previous_layer: Capa anterior (ya ordenada)
            structure_info: Información estructural
            layout: Layout con connections
        """
        # Crear mapa de posiciones de capa anterior
        prev_positions = {elem_id: idx for idx, elem_id in enumerate(previous_layer)}

        # Crear mapa temporal de posiciones actuales
        current_positions = {elem_id: idx for idx, elem_id in enumerate(current_layer)}

        # Calcular barycenter para cada elemento (PRIMERA PASADA)
        barycenters = {}
        for elem_id in current_layer:
            barycenter = self._calculate_barycenter(
                elem_id,
                current_layer,
                prev_positions,
                structure_info,
                layout
            )
            barycenters[elem_id] = barycenter

        # SEGUNDA PASADA: Recalcular barycenters de contenedores usando
        # los barycenters de otros elementos (no sus posiciones)
        for elem_id in current_layer:
            container_node = structure_info.element_tree.get(elem_id)
            if container_node and container_node['is_container'] and container_node['children']:
                barycenter = self._calculate_container_barycenter(
                    elem_id,
                    current_layer,
                    barycenters,  # Usar barycenters en lugar de posiciones
                    structure_info,
                    layout
                )
                barycenters[elem_id] = barycenter

        # Ajustar barycenters con scores de accesibilidad (atracción al centro)
        if len(current_layer) > 2:
            center = (len(current_layer) - 1) / 2.0
            influence = self.SCORE_CENTER_INFLUENCE
            for elem_id in current_layer:
                score = structure_info.accessibility_scores.get(elem_id, 0.0)
                if score > 0:
                    bc = barycenters.get(elem_id, center)
                    adjusted = bc + score * influence * (center - bc)
                    barycenters[elem_id] = adjusted

        # Ordenar por barycenter, luego por tipo, con tiebreaker para contenedores
        def get_sort_key(elem_id: str) -> Tuple[float, int, str]:
            barycenter = barycenters.get(elem_id, len(previous_layer) / 2)

            # Tiebreaker: contenedores primero en caso de empate (prioridad 0)
            # Esto los empuja hacia el medio cuando hay múltiples elementos con mismo barycenter
            container_node = structure_info.element_tree.get(elem_id)
            is_container = 1 if (container_node and container_node['is_container']) else 2

            # Tipo del elemento
            elem_type = 'unknown'
            for etype, ids in structure_info.element_types.items():
                if elem_id in ids:
                    elem_type = etype
                    break

            return (barycenter, is_container, elem_type)

        if self.debug:
            print(f"           Barycenters antes de ordenar (con score-adjustment):")
            for elem_id in current_layer:
                bc = barycenters.get(elem_id, -1)
                score = structure_info.accessibility_scores.get(elem_id, 0.0)
                score_str = f" [score={score:.3f}]" if score > 0 else ""
                print(f"             {elem_id}: {bc:.2f}{score_str}")

        current_layer.sort(key=get_sort_key)

        if self.debug:
            print(f"           Orden después de sort: {' -> '.join(current_layer)}")

    def _position_hub_containers_in_center(
        self,
        current_layer: List[str],
        structure_info: StructureInfo,
        layout
    ) -> None:
        """
        Post-procesa la capa para mover contenedores "hub" al centro.

        Un contenedor es un "hub" si recibe conexiones desde múltiples
        elementos del mismo nivel (2 o más fuentes). Estos contenedores
        deben estar en el centro para minimizar cruces.

        Args:
            current_layer: Capa ordenada (modifica in-place)
            structure_info: Información estructural
            layout: Layout con conexiones
        """
        if len(current_layer) < 3:
            return  # No tiene sentido centrar con menos de 3 elementos

        for elem_id in current_layer:
            # Verificar si es contenedor
            container_node = structure_info.element_tree.get(elem_id)
            if not container_node or not container_node['is_container'] or not container_node['children']:
                continue

            children = set(container_node['children'])

            # Contar fuentes únicas de conexión desde el mismo nivel
            sources = set()
            for conn in layout.connections:
                from_id = conn['from']
                to_id = conn['to']

                # Si conecta a un hijo de este contenedor
                if to_id in children:
                    # Resolver from a primario
                    from_primary_id = from_id
                    if from_id not in structure_info.primary_elements:
                        from_node = structure_info.element_tree.get(from_id)
                        while from_node and from_node['parent']:
                            from_parent = from_node['parent']
                            if from_parent in structure_info.primary_elements:
                                from_primary_id = from_parent
                                break
                            from_node = structure_info.element_tree.get(from_parent)

                    # Si la fuente está en el mismo nivel
                    if from_primary_id in current_layer and from_primary_id != elem_id:
                        sources.add(from_primary_id)

            # Si tiene 2+ fuentes, es un hub: moverlo al centro
            if len(sources) >= 2:
                current_idx = current_layer.index(elem_id)
                center_idx = len(current_layer) // 2

                if current_idx != center_idx:
                    # Mover al centro
                    current_layer.pop(current_idx)
                    current_layer.insert(center_idx, elem_id)

                    if self.debug:
                        print(f"           [HUB] {elem_id}: {len(sources)} fuentes -> movido a centro (pos {center_idx})")

    def _order_layer_barycenter_backward(
        self,
        current_layer: List[str],
        next_layer: List[str],
        structure_info: StructureInfo,
        layout
    ) -> None:
        """
        Ordena capa usando backward barycenter (considera capa siguiente).

        El barycenter de un nodo es el promedio de posiciones de sus vecinos
        en la capa siguiente. Útil para refinar el orden considerando
        conexiones hacia adelante.

        Args:
            current_layer: Capa actual a ordenar (modifica in-place)
            next_layer: Capa siguiente (ya ordenada)
            structure_info: Información estructural
            layout: Layout con connections
        """
        # Crear mapa de posiciones de capa siguiente
        next_positions = {elem_id: idx for idx, elem_id in enumerate(next_layer)}

        # Calcular barycenter backward para cada elemento
        barycenters = {}
        for elem_id in current_layer:
            barycenter = self._calculate_barycenter_backward(
                elem_id,
                current_layer,
                next_positions,
                structure_info,
                layout
            )
            barycenters[elem_id] = barycenter

        # Ajustar barycenters con scores de accesibilidad (atracción al centro)
        if len(current_layer) > 2:
            center = (len(current_layer) - 1) / 2.0
            influence = self.SCORE_CENTER_INFLUENCE
            for elem_id in current_layer:
                score = structure_info.accessibility_scores.get(elem_id, 0.0)
                if score > 0:
                    bc = barycenters[elem_id]
                    barycenters[elem_id] = bc + score * influence * (center - bc)

        # Ordenar por barycenter
        def get_sort_key(elem_id: str) -> float:
            return barycenters.get(elem_id, len(next_layer) / 2)

        current_layer.sort(key=get_sort_key)

    def _get_temp_positions(self, layers: List[List[str]]) -> Dict[str, Tuple[int, int]]:
        """
        Calcula posiciones temporales para los layers actuales.

        Útil para calcular cruces durante las iteraciones de optimización.

        Args:
            layers: Lista de capas con elementos ordenados

        Returns:
            Dict con posiciones abstractas temporales
        """
        positions = {}
        for layer_idx, layer in enumerate(layers):
            for elem_idx, elem_id in enumerate(layer):
                positions[elem_id] = (elem_idx, layer_idx)
        return positions

    def _calculate_container_barycenter(
        self,
        container_id: str,
        current_layer: List[str],
        source_barycenters: Dict[str, float],
        structure_info: StructureInfo,
        layout
    ) -> float:
        """
        Calcula barycenter especial para contenedores.

        Considera conexiones ENTRANTES a sus hijos desde otros elementos
        del mismo nivel. Usa los BARYCENTERS de los elementos fuente,
        no sus posiciones actuales, para mejor convergencia.

        Args:
            container_id: ID del contenedor
            current_layer: Elementos del nivel actual
            source_barycenters: Barycenters de elementos del nivel actual
            structure_info: Información estructural
            layout: Layout con conexiones

        Returns:
            float: Posición óptima del contenedor
        """
        # Obtener hijos del contenedor
        container_node = structure_info.element_tree.get(container_id)
        if not container_node or not container_node['children']:
            return len(current_layer) / 2

        children = set(container_node['children'])

        # Encontrar elementos del mismo nivel que se conectan a los hijos
        source_barycenter_values = []

        for conn in layout.connections:
            from_id = conn['from']
            to_id = conn['to']

            # Si la conexión va HACIA un hijo de este contenedor
            if to_id in children:
                # Resolver from a primario
                from_primary_id = from_id
                if from_id not in structure_info.primary_elements:
                    from_node = structure_info.element_tree.get(from_id)
                    while from_node and from_node['parent']:
                        from_parent = from_node['parent']
                        if from_parent in structure_info.primary_elements:
                            from_primary_id = from_parent
                            break
                        from_node = structure_info.element_tree.get(from_parent)

                # Si el origen está en el mismo nivel, usar su barycenter
                if from_primary_id in source_barycenters and from_primary_id != container_id:
                    source_barycenter_values.append(source_barycenters[from_primary_id])

        # Calcular barycenter basado en los barycenters de las fuentes
        if source_barycenter_values:
            avg_barycenter = sum(source_barycenter_values) / len(source_barycenter_values)

            # CRÍTICO: Mezclar con posición central para atraer contenedores hacia el medio
            # Esto minimiza cruces cuando múltiples elementos se conectan a los hijos del contenedor
            center_position = (len(current_layer) - 1) / 2.0

            # Peso: 50% barycenter de fuentes, 50% centro
            # Esto ayuda a posicionar contenedores en el medio de sus "clientes"
            barycenter = avg_barycenter * 0.5 + center_position * 0.5

            if self.debug:
                print(f"           [CONTAINER] {container_id}: {len(source_barycenter_values)} conexiones")
                print(f"                       avg_sources={avg_barycenter:.2f}, center={center_position:.2f} -> barycenter={barycenter:.2f}")
            return barycenter
        else:
            # Sin conexiones entrantes: posición central
            return (len(current_layer) - 1) / 2.0

    def _calculate_barycenter(
        self,
        elem_id: str,
        current_layer: List[str],
        prev_positions: Dict[str, int],
        structure_info: StructureInfo,
        layout
    ) -> float:
        """
        Calcula posición X óptima basada en conexiones.

        MEJORADO: Ahora considera también conexiones del mismo nivel.

        Args:
            elem_id: ID del elemento a posicionar
            current_layer: Elementos de la capa actual
            prev_positions: {elem_id: posición_x} de capa anterior
            structure_info: Información estructural
            layout: Layout con conexiones

        Returns:
            float: Posición X óptima (barycenter)
        """
        # 1. Resolver elemento a primario
        elem_primary_id = elem_id
        if elem_id not in structure_info.primary_elements:
            node = structure_info.element_tree.get(elem_id)
            while node and node['parent']:
                parent = node['parent']
                if parent in structure_info.primary_elements:
                    elem_primary_id = parent
                    break
                node = structure_info.element_tree.get(parent)

        # 2. CONEXIONES DESDE CAPA ANTERIOR (peso 70%)
        prev_neighbor_positions = []

        for conn in layout.connections:
            from_id = conn['from']
            to_id = conn['to']

            # Resolver a primarios
            from_primary_id = from_id
            if from_id not in structure_info.primary_elements:
                from_node = structure_info.element_tree.get(from_id)
                while from_node and from_node['parent']:
                    from_parent = from_node['parent']
                    if from_parent in structure_info.primary_elements:
                        from_primary_id = from_parent
                        break
                    from_node = structure_info.element_tree.get(from_parent)

            to_primary_id = to_id
            if to_id not in structure_info.primary_elements:
                to_node = structure_info.element_tree.get(to_id)
                while to_node and to_node['parent']:
                    to_parent = to_node['parent']
                    if to_parent in structure_info.primary_elements:
                        to_primary_id = to_parent
                        break
                    to_node = structure_info.element_tree.get(to_parent)

            # Si conecta DESDE capa anterior A este elemento
            if to_primary_id == elem_primary_id and from_primary_id in prev_positions:
                prev_neighbor_positions.append(prev_positions[from_primary_id])

        # 3. NUEVO: CONEXIONES DESDE MISMO NIVEL (peso 30%)
        same_level_neighbor_positions = []

        # Crear mapa temporal de posiciones actuales (índices en current_layer)
        current_positions = {e_id: idx for idx, e_id in enumerate(current_layer)}

        for conn in layout.connections:
            from_id = conn['from']
            to_id = conn['to']

            # Resolver a primarios (mismo código que arriba)
            from_primary_id = from_id
            if from_id not in structure_info.primary_elements:
                from_node = structure_info.element_tree.get(from_id)
                while from_node and from_node['parent']:
                    from_parent = from_node['parent']
                    if from_parent in structure_info.primary_elements:
                        from_primary_id = from_parent
                        break
                    from_node = structure_info.element_tree.get(from_parent)

            to_primary_id = to_id
            if to_id not in structure_info.primary_elements:
                to_node = structure_info.element_tree.get(to_id)
                while to_node and to_node['parent']:
                    to_parent = to_node['parent']
                    if to_parent in structure_info.primary_elements:
                        to_primary_id = to_parent
                        break
                    to_node = structure_info.element_tree.get(to_parent)

            # Si conecta DESDE el mismo nivel A este elemento
            if (to_primary_id == elem_primary_id and
                from_primary_id in current_positions and
                from_primary_id != elem_primary_id):
                same_level_neighbor_positions.append(current_positions[from_primary_id])

        # 4. Calcular barycenter combinado con pesos
        total_weight = 0
        weighted_sum = 0

        # Peso para conexiones de capa anterior: 70%
        if prev_neighbor_positions:
            prev_barycenter = sum(prev_neighbor_positions) / len(prev_neighbor_positions)
            weighted_sum += prev_barycenter * 0.7 * len(prev_neighbor_positions)
            total_weight += 0.7 * len(prev_neighbor_positions)

        # Peso para conexiones del mismo nivel: 30%
        if same_level_neighbor_positions:
            same_barycenter = sum(same_level_neighbor_positions) / len(same_level_neighbor_positions)
            weighted_sum += same_barycenter * 0.3 * len(same_level_neighbor_positions)
            total_weight += 0.3 * len(same_level_neighbor_positions)

        # 5. Retornar barycenter final
        if total_weight > 0:
            return weighted_sum / total_weight
        else:
            # Sin conexiones: centrar en la capa
            if prev_positions:
                return len(prev_positions) / 2
            else:
                return len(current_layer) / 2

    def _calculate_barycenter_backward(
        self,
        elem_id: str,
        current_layer: List[str],
        next_positions: Dict[str, int],
        structure_info: StructureInfo,
        layout
    ) -> float:
        """
        Calcula barycenter considerando conexiones hacia la capa siguiente.

        IMPORTANTE: Si elem_id es un contenedor, también considera conexiones
        a sus elementos contenidos.

        Args:
            elem_id: ID del elemento a posicionar
            current_layer: Elementos de la capa actual
            next_positions: {elem_id: posición_x} de capa siguiente
            structure_info: Información estructural
            layout: Layout con conexiones

        Returns:
            float: Posición X óptima (barycenter)
        """
        # Resolver elemento a primario
        elem_primary_id = elem_id
        if elem_id not in structure_info.primary_elements:
            node = structure_info.element_tree.get(elem_id)
            while node and node['parent']:
                parent = node['parent']
                if parent in structure_info.primary_elements:
                    elem_primary_id = parent
                    break
                node = structure_info.element_tree.get(parent)

        # Si es un contenedor, obtener sus hijos
        elem_and_children = [elem_primary_id]
        container_node = structure_info.element_tree.get(elem_primary_id)
        if container_node and container_node['children']:
            elem_and_children.extend(container_node['children'])

        # Buscar conexiones HACIA la capa siguiente
        next_neighbor_positions = []

        for conn in layout.connections:
            from_id = conn['from']
            to_id = conn['to']

            # Resolver from a primario
            from_primary_id = from_id
            if from_id not in structure_info.primary_elements:
                from_node = structure_info.element_tree.get(from_id)
                while from_node and from_node['parent']:
                    from_parent = from_node['parent']
                    if from_parent in structure_info.primary_elements:
                        from_primary_id = from_parent
                        break
                    from_node = structure_info.element_tree.get(from_parent)

            # Resolver to a primario
            to_primary_id = to_id
            if to_id not in structure_info.primary_elements:
                to_node = structure_info.element_tree.get(to_id)
                while to_node and to_node['parent']:
                    to_parent = to_node['parent']
                    if to_parent in structure_info.primary_elements:
                        to_primary_id = to_parent
                        break
                    to_node = structure_info.element_tree.get(to_parent)

            # Si conecta DESDE este elemento (o sus hijos) HACIA capa siguiente
            if from_primary_id in elem_and_children and to_primary_id in next_positions:
                next_neighbor_positions.append(next_positions[to_primary_id])
            # CRÍTICO: También considerar conexiones A elementos contenidos
            elif to_id in elem_and_children and from_primary_id in current_layer:
                # Una conexión apunta a un hijo de este contenedor desde otro elemento del mismo nivel
                # Usar la posición del elemento que está enviando la conexión
                current_positions = {e_id: idx for idx, e_id in enumerate(current_layer)}
                if from_primary_id in current_positions:
                    next_neighbor_positions.append(current_positions[from_primary_id])

        # Calcular barycenter (promedio de posiciones de vecinos)
        if next_neighbor_positions:
            barycenter = sum(next_neighbor_positions) / len(next_neighbor_positions)
        else:
            # Sin vecinos: posición central
            barycenter = len(next_positions) / 2

        return barycenter

    def _assign_abstract_positions(
        self,
        layers: List[List[str]]
    ) -> Dict[str, Tuple[int, int]]:
        """
        Asigna coordenadas abstractas (x, y) a elementos.

        Args:
            layers: Lista de capas ordenadas

        Returns:
            {element_id: (abstract_x, abstract_y)}
        """
        positions = {}

        for layer_idx, layer in enumerate(layers):
            layer_width = len(layer)

            for elem_idx, elem_id in enumerate(layer):
                # Posición Y = índice de capa
                abstract_y = layer_idx

                # Posición X = índice en la capa
                # Distribuir uniformemente en rango [0, layer_width-1]
                abstract_x = elem_idx

                positions[elem_id] = (abstract_x, abstract_y)

        return positions

    def _assign_contained_positions(
        self,
        positions: Dict[str, Tuple[int, int]],
        structure_info: StructureInfo,
        layout
    ) -> None:
        """
        Asigna posiciones abstractas a elementos contenidos.

        Los elementos contenidos heredan la posición Y de su contenedor,
        y reciben un offset horizontal pequeño para distribuirse.

        Args:
            positions: Diccionario de posiciones (modificado in-place)
            structure_info: Información estructural
            layout: Layout con elementos
        """
        # Offset horizontal abstracto entre elementos contenidos
        # Usar 0.15 unidades abstractas para separación
        horizontal_offset = 0.15

        # Offset vertical para que los hijos estén DENTRO del contenedor
        # (debajo del ícono del contenedor en coordenadas abstractas)
        vertical_offset = 0.3  # Offset pequeño hacia abajo

        for container_id, node in structure_info.element_tree.items():
            # Solo procesar contenedores
            if not node['is_container']:
                continue

            # Verificar que el contenedor tenga posición
            if container_id not in positions:
                continue

            container_pos = positions[container_id]
            children = node['children']

            if not children:
                continue

            # Distribuir hijos horizontalmente DESDE el contenedor (no centrados)
            # Comenzar ligeramente a la derecha del contenedor
            start_x = container_pos[0] + 0.1  # Pequeño offset a la derecha

            # Asignar posiciones a cada hijo
            for i, child_id in enumerate(children):
                # X: offset horizontal desde el contenedor (siempre positivo)
                child_x = start_x + (i * horizontal_offset)

                # Y: ligeramente debajo del contenedor
                child_y = container_pos[1] + vertical_offset

                positions[child_id] = (child_x, child_y)

                if self.debug:
                    print(f"           {child_id} -> ({child_x:.2f}, {child_y:.2f}) [hijo de {container_id}]")

    def count_crossings(
        self,
        positions: Dict[str, Tuple[int, int]],
        connections: List[dict]
    ) -> int:
        """
        Cuenta cruces entre conexiones en layout abstracto.

        Algoritmo O(n²):
        - Para cada par de conexiones (e1->e2, e3->e4):
          - Si líneas se cruzan → +1
        - Usar test geométrico simple

        Args:
            positions: {element_id: (x, y)}
            connections: Lista de conexiones

        Returns:
            int: Cantidad de cruces
        """
        crossings = 0
        n = len(connections)

        # Comparar cada par de conexiones
        for i in range(n):
            conn1 = connections[i]
            from1 = conn1['from']
            to1 = conn1['to']

            # Skip si no tenemos posiciones
            if from1 not in positions or to1 not in positions:
                continue

            p1 = positions[from1]
            p2 = positions[to1]

            for j in range(i + 1, n):
                conn2 = connections[j]
                from2 = conn2['from']
                to2 = conn2['to']

                # Skip si no tenemos posiciones
                if from2 not in positions or to2 not in positions:
                    continue

                p3 = positions[from2]
                p4 = positions[to2]

                # Test de cruce de líneas
                if self._lines_intersect(p1, p2, p3, p4):
                    crossings += 1

        return crossings

    def _lines_intersect(
        self,
        p1: Tuple[int, int],
        p2: Tuple[int, int],
        p3: Tuple[int, int],
        p4: Tuple[int, int]
    ) -> bool:
        """
        Verifica si dos líneas se cruzan usando test de orientación.

        Args:
            p1, p2: Endpoints de línea 1
            p3, p4: Endpoints de línea 2

        Returns:
            bool: True si las líneas se cruzan
        """
        def orientation(p, q, r):
            """
            Calcula orientación del triplete (p, q, r).
            Returns:
                0 -> Colineal
                1 -> Clockwise
                2 -> Counterclockwise
            """
            val = (q[1] - p[1]) * (r[0] - q[0]) - (q[0] - p[0]) * (r[1] - q[1])
            if abs(val) < 0.001:
                return 0
            return 1 if val > 0 else 2

        def on_segment(p, q, r):
            """Verifica si q está en el segmento pr (asumiendo colineal)."""
            if (q[0] <= max(p[0], r[0]) and q[0] >= min(p[0], r[0]) and
                q[1] <= max(p[1], r[1]) and q[1] >= min(p[1], r[1])):
                return True
            return False

        o1 = orientation(p1, p2, p3)
        o2 = orientation(p1, p2, p4)
        o3 = orientation(p3, p4, p1)
        o4 = orientation(p3, p4, p2)

        # Caso general
        if o1 != o2 and o3 != o4:
            return True

        # Casos especiales (colineales)
        if o1 == 0 and on_segment(p1, p3, p2):
            return True
        if o2 == 0 and on_segment(p1, p4, p2):
            return True
        if o3 == 0 and on_segment(p3, p1, p4):
            return True
        if o4 == 0 and on_segment(p3, p2, p4):
            return True

        return False
