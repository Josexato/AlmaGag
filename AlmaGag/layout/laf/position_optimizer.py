"""
PositionOptimizer - Claude-SolFase5: Optimización de posiciones de nodos primarios

Calcula la mejor posición abstracta para cada nodo primario de manera que
la distancia total de los conectores que unen los elementos primarios sea
la menor posible.

IMPORTANTE: Esta fase trabaja exclusivamente con posiciones abstractas
(coordenadas de grid). NO realiza inflación (conversión a píxeles reales).
La inflación se ejecuta en fases posteriores.

Algoritmo:
1. Construir grafo de adyacencia entre nodos primarios
2. Para cada capa (nivel topológico), calcular la posición X óptima
   de cada nodo minimizando la suma de distancias euclidianas a sus
   vecinos conectados (en capas adyacentes y mismo nivel)
3. Iterar refinando posiciones hasta convergencia o máximo de iteraciones
4. Resolver conflictos de posición (dos nodos en la misma posición)

Author: Claude (Claude-SolFase5)
Version: v1.0
Date: 2026-02-15
"""

from typing import Dict, List, Tuple, Set
from AlmaGag.layout.laf.structure_analyzer import StructureInfo
import math
import logging

logger = logging.getLogger('AlmaGag')


class PositionOptimizer:
    """
    Optimiza posiciones abstractas de nodos primarios para minimizar
    la distancia total de conectores.

    Trabaja sobre coordenadas abstractas (grid), sin inflación.
    """

    def __init__(self, debug: bool = False):
        """
        Inicializa el optimizador de posiciones.

        Args:
            debug: Si True, imprime logs de debug
        """
        self.debug = debug

    def optimize_positions(
        self,
        abstract_positions: Dict[str, Tuple[float, float]],
        structure_info: StructureInfo,
        layout,
        max_iterations: int = 20,
        convergence_threshold: float = 0.001
    ) -> Dict[str, Tuple[float, float]]:
        """
        Optimiza las posiciones abstractas de los nodos primarios para
        minimizar la distancia total de conectores.

        Algoritmo (gradiente sobre baricentro ponderado):
        1. Construir mapa de adyacencia entre nodos primarios
        2. Para cada iteración:
           a. Para cada nodo, calcular posición X óptima como la mediana
              ponderada de las posiciones de sus vecinos conectados
           b. Mantener posición Y fija (nivel topológico)
           c. Resolver conflictos manteniendo orden relativo
        3. Parar cuando la mejora sea menor que el umbral

        Args:
            abstract_positions: {element_id: (x, y)} posiciones del Phase 4
            structure_info: Información estructural del diagrama
            layout: Layout con connections
            max_iterations: Máximo de iteraciones de optimización
            convergence_threshold: Umbral de convergencia (cambio mínimo)

        Returns:
            Dict[str, Tuple[float, float]]: Posiciones optimizadas
        """
        # Separar posiciones primarias de contenidas
        primary_positions = {}
        contained_positions = {}

        for elem_id, pos in abstract_positions.items():
            if elem_id in structure_info.primary_elements:
                primary_positions[elem_id] = pos
            else:
                contained_positions[elem_id] = pos

        if not primary_positions:
            return abstract_positions

        # Construir mapa de adyacencia primario (con pesos de conexión)
        adjacency = self._build_primary_adjacency(structure_info, layout)

        # Organizar nodos por capas (niveles topológicos)
        layers = self._organize_by_layers(primary_positions, structure_info)

        # Calcular distancia total inicial
        initial_distance = self._calculate_total_distance(
            primary_positions, adjacency
        )

        if self.debug:
            print(f"[POSOPT] Claude-SolFase5: Optimización de posiciones")
            print(f"         Nodos primarios: {len(primary_positions)}")
            print(f"         Capas: {len(layers)}")
            print(f"         Conexiones primarias: {sum(len(v) for v in adjacency.values()) // 2}")
            print(f"         Distancia total inicial: {initial_distance:.4f}")

        # Iteración de optimización
        optimized = dict(primary_positions)
        prev_distance = initial_distance

        for iteration in range(max_iterations):
            moved = False

            # Forward pass: optimizar capas de arriba hacia abajo
            for level in sorted(layers.keys()):
                layer_nodes = layers[level]
                if len(layer_nodes) <= 1:
                    continue

                changed = self._optimize_layer(
                    layer_nodes, optimized, adjacency, structure_info
                )
                if changed:
                    moved = True

            # Backward pass: optimizar capas de abajo hacia arriba
            for level in sorted(layers.keys(), reverse=True):
                layer_nodes = layers[level]
                if len(layer_nodes) <= 1:
                    continue

                changed = self._optimize_layer(
                    layer_nodes, optimized, adjacency, structure_info
                )
                if changed:
                    moved = True

            # Calcular nueva distancia total
            new_distance = self._calculate_total_distance(optimized, adjacency)
            improvement = prev_distance - new_distance

            if self.debug:
                print(f"         Iteración {iteration + 1}: "
                      f"distancia={new_distance:.4f}, "
                      f"mejora={improvement:.6f}")

            # Verificar convergencia
            if improvement < convergence_threshold or not moved:
                if self.debug:
                    print(f"         Convergencia alcanzada en iteración {iteration + 1}")
                break

            prev_distance = new_distance

        # Normalizar posiciones: asegurar que sean enteras y sin huecos
        optimized = self._normalize_positions(optimized, layers)

        # Calcular distancia final
        final_distance = self._calculate_total_distance(optimized, adjacency)
        reduction = initial_distance - final_distance
        reduction_pct = (reduction / initial_distance * 100) if initial_distance > 0 else 0

        if self.debug:
            print(f"         Distancia final: {final_distance:.4f}")
            print(f"         Reducción: {reduction:.4f} ({reduction_pct:.1f}%)")
            print(f"[POSOPT] Posiciones optimizadas:")
            for level in sorted(layers.keys()):
                layer_ids = layers[level]
                # Ordenar por posición X optimizada
                sorted_nodes = sorted(layer_ids, key=lambda nid: optimized[nid][0])
                positions_str = " -> ".join(
                    f"{nid}(x={optimized[nid][0]:.1f})"
                    for nid in sorted_nodes
                )
                print(f"           Nivel {level}: {positions_str}")

        # Recalcular posiciones de elementos contenidos
        self._update_contained_positions(
            optimized, contained_positions, abstract_positions, structure_info
        )

        # Combinar posiciones optimizadas con contenidas
        result = dict(optimized)
        result.update(contained_positions)

        return result

    def _build_primary_adjacency(
        self,
        structure_info: StructureInfo,
        layout
    ) -> Dict[str, List[Tuple[str, int]]]:
        """
        Construye mapa de adyacencia entre nodos primarios.

        Cada entrada es una lista de (vecino_id, peso) donde peso es
        el número de conexiones entre los dos nodos primarios.

        Args:
            structure_info: Información estructural
            layout: Layout con connections

        Returns:
            {node_id: [(neighbor_id, weight), ...]} bidireccional
        """
        # Contar conexiones entre pares de primarios
        edge_counts: Dict[Tuple[str, str], int] = {}

        for conn in layout.connections:
            from_id = conn['from']
            to_id = conn['to']

            # Resolver a primarios
            from_primary = self._resolve_to_primary(from_id, structure_info)
            to_primary = self._resolve_to_primary(to_id, structure_info)

            # Ignorar autoloops
            if from_primary == to_primary:
                continue

            # Clave normalizada (orden consistente)
            key = tuple(sorted([from_primary, to_primary]))
            edge_counts[key] = edge_counts.get(key, 0) + 1

        # Construir lista de adyacencia bidireccional
        adjacency: Dict[str, List[Tuple[str, int]]] = {}
        for elem_id in structure_info.primary_elements:
            adjacency[elem_id] = []

        for (a, b), weight in edge_counts.items():
            adjacency.setdefault(a, []).append((b, weight))
            adjacency.setdefault(b, []).append((a, weight))

        return adjacency

    def _resolve_to_primary(
        self, elem_id: str, structure_info: StructureInfo
    ) -> str:
        """Resuelve un elemento a su nodo primario ancestro."""
        if elem_id in structure_info.primary_elements:
            return elem_id

        node = structure_info.element_tree.get(elem_id)
        while node and node['parent']:
            parent = node['parent']
            if parent in structure_info.primary_elements:
                return parent
            node = structure_info.element_tree.get(parent)

        return elem_id

    def _organize_by_layers(
        self,
        positions: Dict[str, Tuple[float, float]],
        structure_info: StructureInfo
    ) -> Dict[int, List[str]]:
        """
        Organiza nodos primarios por capas (nivel topológico).

        Args:
            positions: Posiciones actuales
            structure_info: Información estructural

        Returns:
            {level: [node_ids]} ordenado por posición X actual
        """
        layers: Dict[int, List[str]] = {}

        for elem_id in positions:
            if elem_id not in structure_info.primary_elements:
                continue
            level = structure_info.topological_levels.get(elem_id, 0)
            if level not in layers:
                layers[level] = []
            layers[level].append(elem_id)

        # Ordenar cada capa por posición X actual
        for level in layers:
            layers[level].sort(key=lambda nid: positions[nid][0])

        return layers

    def _calculate_total_distance(
        self,
        positions: Dict[str, Tuple[float, float]],
        adjacency: Dict[str, List[Tuple[str, int]]]
    ) -> float:
        """
        Calcula la distancia total ponderada de todos los conectores.

        Args:
            positions: Posiciones de nodos
            adjacency: Mapa de adyacencia con pesos

        Returns:
            float: Suma de distancias euclidianas ponderadas
        """
        total = 0.0
        counted: Set[Tuple[str, str]] = set()

        for node_id, neighbors in adjacency.items():
            if node_id not in positions:
                continue

            for neighbor_id, weight in neighbors:
                if neighbor_id not in positions:
                    continue

                # Evitar contar dos veces (bidireccional)
                edge_key = tuple(sorted([node_id, neighbor_id]))
                if edge_key in counted:
                    continue
                counted.add(edge_key)

                # Distancia euclidiana ponderada
                x1, y1 = positions[node_id]
                x2, y2 = positions[neighbor_id]
                dist = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
                total += dist * weight

        return total

    def _optimize_layer(
        self,
        layer_nodes: List[str],
        positions: Dict[str, Tuple[float, float]],
        adjacency: Dict[str, List[Tuple[str, int]]],
        structure_info: StructureInfo
    ) -> bool:
        """
        Optimiza las posiciones X de los nodos en una capa.

        Para cada nodo, calcula la posición X óptima como el baricentro
        ponderado de las posiciones de sus vecinos conectados:

            x_opt = Σ(weight_i * x_neighbor_i) / Σ(weight_i)

        Luego resuelve conflictos manteniendo el orden relativo que
        minimiza cruces.

        Args:
            layer_nodes: IDs de nodos en esta capa
            positions: Posiciones actuales (modificadas in-place)
            adjacency: Mapa de adyacencia
            structure_info: Información estructural

        Returns:
            bool: True si algún nodo cambió de posición
        """
        if not layer_nodes:
            return False

        # Calcular posición X óptima para cada nodo
        optimal_x: Dict[str, float] = {}

        for node_id in layer_nodes:
            neighbors = adjacency.get(node_id, [])

            if not neighbors:
                # Sin vecinos: mantener posición actual
                optimal_x[node_id] = positions[node_id][0]
                continue

            # Baricentro ponderado de vecinos
            weighted_sum = 0.0
            total_weight = 0.0

            for neighbor_id, weight in neighbors:
                if neighbor_id not in positions:
                    continue
                weighted_sum += positions[neighbor_id][0] * weight
                total_weight += weight

            if total_weight > 0:
                target_x = weighted_sum / total_weight
                # Mezclar con posición actual para suavizar (factor de amortiguación)
                current_x = positions[node_id][0]
                optimal_x[node_id] = current_x * 0.3 + target_x * 0.7
            else:
                optimal_x[node_id] = positions[node_id][0]

        # Ordenar nodos por su posición X óptima
        sorted_nodes = sorted(layer_nodes, key=lambda nid: optimal_x[nid])

        # Verificar si el nuevo orden es diferente al actual
        current_order = sorted(layer_nodes, key=lambda nid: positions[nid][0])
        changed = False

        # Asignar nuevas posiciones X respetando el orden óptimo
        # y evitando solapamientos (mínimo 1 unidad abstracta de separación)
        MIN_SEPARATION = 1.0

        # Calcular posiciones finales manteniendo orden y separación mínima
        final_positions: Dict[str, float] = {}

        for i, node_id in enumerate(sorted_nodes):
            target = optimal_x[node_id]

            # Asegurar separación con nodo anterior
            if i > 0:
                prev_node = sorted_nodes[i - 1]
                prev_x = final_positions[prev_node]
                target = max(target, prev_x + MIN_SEPARATION)

            final_positions[node_id] = target

        # Centrar el grupo: mover para que el centro del grupo
        # esté alineado con el centro del rango original
        if final_positions:
            new_min = min(final_positions.values())
            new_max = max(final_positions.values())
            new_center = (new_min + new_max) / 2

            old_positions_x = [positions[nid][0] for nid in layer_nodes]
            old_center = (min(old_positions_x) + max(old_positions_x)) / 2

            offset = old_center - new_center
            for node_id in final_positions:
                final_positions[node_id] += offset

        # Aplicar posiciones optimizadas
        for node_id in layer_nodes:
            old_x = positions[node_id][0]
            new_x = final_positions.get(node_id, old_x)
            y = positions[node_id][1]

            if abs(new_x - old_x) > 0.01:
                positions[node_id] = (new_x, y)
                changed = True

        return changed

    def _normalize_positions(
        self,
        positions: Dict[str, Tuple[float, float]],
        layers: Dict[int, List[str]]
    ) -> Dict[str, Tuple[float, float]]:
        """
        Normaliza posiciones: convierte a enteros preservando el orden.

        Las posiciones optimizadas son flotantes que necesitan convertirse
        a enteros para el grid abstracto, preservando el orden relativo
        que minimiza las distancias.

        Args:
            positions: Posiciones optimizadas (flotantes)
            layers: Nodos organizados por capas

        Returns:
            Dict con posiciones normalizadas (enteras)
        """
        normalized = {}

        for level, layer_nodes in layers.items():
            # Ordenar por posición X optimizada
            sorted_nodes = sorted(layer_nodes, key=lambda nid: positions[nid][0])

            # Asignar posiciones enteras preservando orden
            for idx, node_id in enumerate(sorted_nodes):
                y = positions[node_id][1]
                normalized[node_id] = (idx, int(y))

        return normalized

    def _update_contained_positions(
        self,
        optimized_primary: Dict[str, Tuple[float, float]],
        contained_positions: Dict[str, Tuple[float, float]],
        original_positions: Dict[str, Tuple[float, float]],
        structure_info: StructureInfo
    ) -> None:
        """
        Actualiza posiciones de elementos contenidos según las nuevas
        posiciones de sus contenedores primarios.

        Args:
            optimized_primary: Posiciones optimizadas de primarios
            contained_positions: Posiciones de contenidos (modificado in-place)
            original_positions: Posiciones originales (Phase 4)
            structure_info: Información estructural
        """
        for elem_id in list(contained_positions.keys()):
            # Encontrar el contenedor primario
            parent_id = structure_info.element_tree.get(elem_id, {}).get('parent')
            if not parent_id:
                continue

            # Buscar el primario
            primary_id = parent_id
            while primary_id and primary_id not in optimized_primary:
                parent_node = structure_info.element_tree.get(primary_id, {})
                primary_id = parent_node.get('parent')

            if not primary_id or primary_id not in optimized_primary:
                continue

            # Calcular offset del contenido respecto a su contenedor original
            orig_primary = original_positions.get(primary_id, (0, 0))
            orig_contained = original_positions.get(elem_id, (0, 0))

            offset_x = orig_contained[0] - orig_primary[0]
            offset_y = orig_contained[1] - orig_primary[1]

            # Aplicar offset a la nueva posición del primario
            new_primary = optimized_primary[primary_id]
            contained_positions[elem_id] = (
                new_primary[0] + offset_x,
                new_primary[1] + offset_y
            )

    def calculate_connector_distances(
        self,
        positions: Dict[str, Tuple[float, float]],
        structure_info: StructureInfo,
        layout
    ) -> Dict[str, float]:
        """
        Calcula la distancia de cada conector individual (para debug/reportes).

        Args:
            positions: Posiciones de nodos
            structure_info: Información estructural
            layout: Layout con connections

        Returns:
            Dict con {from->to: distancia} para cada conexión
        """
        distances = {}

        for conn in layout.connections:
            from_id = conn['from']
            to_id = conn['to']

            from_primary = self._resolve_to_primary(from_id, structure_info)
            to_primary = self._resolve_to_primary(to_id, structure_info)

            if from_primary == to_primary:
                continue

            if from_primary in positions and to_primary in positions:
                x1, y1 = positions[from_primary]
                x2, y2 = positions[to_primary]
                dist = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
                key = f"{from_primary}->{to_primary}"
                distances[key] = dist

        return distances
