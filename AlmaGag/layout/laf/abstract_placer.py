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

        if self.debug:
            print(f"\n[ABSTRACT] Ordering completado")

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
        Ordena elementos dentro de cada capa usando heurísticas.

        Modifica layers in-place.

        Heurísticas (en orden de prioridad):
        1. Tipo de elementos (agrupar similares)
        2. Barycenter (minimizar cruces con capa anterior)
        3. Cantidad de conexiones (más conectados al centro)

        Args:
            layers: Lista de capas a ordenar
            structure_info: Información estructural
            layout: Layout con connections
        """
        # Primera capa: ordenar por tipo + cantidad de conexiones
        if layers:
            self._order_first_layer(layers[0], structure_info)

        # Capas siguientes: aplicar barycenter + tipo
        for layer_idx in range(1, len(layers)):
            self._order_layer_barycenter(
                layers[layer_idx],
                layers[layer_idx - 1],
                structure_info,
                layout
            )

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

    def _order_layer_barycenter(
        self,
        current_layer: List[str],
        previous_layer: List[str],
        structure_info: StructureInfo,
        layout
    ) -> None:
        """
        Ordena capa usando barycenter heuristic para minimizar cruces.

        El barycenter de un nodo es el promedio de posiciones de sus vecinos
        en la capa anterior.

        Args:
            current_layer: Capa actual a ordenar (modifica in-place)
            previous_layer: Capa anterior (ya ordenada)
            structure_info: Información estructural
            layout: Layout con connections
        """
        # Crear mapa de posiciones de capa anterior
        prev_positions = {elem_id: idx for idx, elem_id in enumerate(previous_layer)}

        # Calcular barycenter para cada elemento
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

        # Ordenar por barycenter, luego por tipo
        def get_sort_key(elem_id: str) -> Tuple[float, str]:
            barycenter = barycenters.get(elem_id, len(previous_layer) / 2)

            # Tipo del elemento
            elem_type = 'unknown'
            for etype, ids in structure_info.element_types.items():
                if elem_id in ids:
                    elem_type = etype
                    break

            return (barycenter, elem_type)

        current_layer.sort(key=get_sort_key)

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
