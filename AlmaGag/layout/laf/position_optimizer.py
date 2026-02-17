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
        # Fase 5: optimizar con respecto a padres; hijos se acomodan en su propia capa.
        self.optimize_against_parents_only = True

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
            print(f"[POSOPT] {len(primary_positions)} nodos, {len(layers)} capas, dist_inicial={initial_distance:.2f}")

        # Iteración de optimización por desplazamiento decimal de capa.
        # Se preserva el orden relativo de Fase 4 (baricentro), y en Fase 5
        # solo se traslada cada capa en X para minimizar distancia total.
        base_positions = dict(primary_positions)
        layer_offsets = {level: 0.0 for level in layers.keys()}
        optimized = self._apply_layer_offsets(base_positions, layers, layer_offsets)
        prev_distance = initial_distance

        for iteration in range(max_iterations):
            moved = False

            # Forward pass: optimizar capas de arriba hacia abajo
            for level in sorted(layers.keys()):
                changed = self._optimize_layer_offset(
                    level=level,
                    layers=layers,
                    base_positions=base_positions,
                    current_positions=optimized,
                    adjacency=adjacency,
                    layer_offsets=layer_offsets
                )
                if changed:
                    moved = True
                    optimized = self._apply_layer_offsets(base_positions, layers, layer_offsets)

            # Backward pass: optimizar capas de abajo hacia arriba
            for level in sorted(layers.keys(), reverse=True):
                changed = self._optimize_layer_offset(
                    level=level,
                    layers=layers,
                    base_positions=base_positions,
                    current_positions=optimized,
                    adjacency=adjacency,
                    layer_offsets=layer_offsets
                )
                if changed:
                    moved = True
                    optimized = self._apply_layer_offsets(base_positions, layers, layer_offsets)

            # Calcular nueva distancia total
            new_distance = self._calculate_total_distance(optimized, adjacency)
            improvement = prev_distance - new_distance

            # Verificar convergencia
            if improvement < convergence_threshold or not moved:
                if self.debug:
                    print(f"[POSOPT] Convergencia en iteración {iteration + 1}, dist={new_distance:.2f}")
                break

            prev_distance = new_distance

        # Normalizar posiciones: asegurar que sean enteras y sin huecos
        optimized = self._normalize_positions(optimized, layers)

        # Calcular distancia final
        final_distance = self._calculate_total_distance(optimized, adjacency)
        reduction = initial_distance - final_distance
        reduction_pct = (reduction / initial_distance * 100) if initial_distance > 0 else 0

        if self.debug:
            print(f"[POSOPT] Reducción: {reduction:.2f} ({reduction_pct:.1f}%)")

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

    def _apply_layer_offsets(
        self,
        base_positions: Dict[str, Tuple[float, float]],
        layers: Dict[int, List[str]],
        layer_offsets: Dict[int, float]
    ) -> Dict[str, Tuple[float, float]]:
        """
        Aplica offsets por capa preservando el orden relativo intra-capa.
        """
        result = dict(base_positions)
        for level, nodes in layers.items():
            offset = layer_offsets.get(level, 0.0)
            for node_id in nodes:
                if node_id not in result:
                    continue
                x, y = result[node_id]
                result[node_id] = (x + offset, y)
        return result

    def _optimize_layer_offset(
        self,
        level: int,
        layers: Dict[int, List[str]],
        base_positions: Dict[str, Tuple[float, float]],
        current_positions: Dict[str, Tuple[float, float]],
        adjacency: Dict[str, List[Tuple[str, int]]],
        layer_offsets: Dict[int, float]
    ) -> bool:
        """
        Optimiza el desplazamiento X de una capa completa (offset continuo).
        """
        layer_nodes = layers.get(level, [])
        if not layer_nodes:
            return False

        # Recolectar términos dependientes del offset de esta capa.
        # Solo importan aristas hacia otras capas; intra-capa no cambia.
        terms: List[Tuple[float, float, float]] = []  # (a, dy, weight)
        for node_id in layer_nodes:
            if node_id not in base_positions:
                continue
            base_x, y1 = base_positions[node_id]
            for neighbor_id, weight in adjacency.get(node_id, []):
                if neighbor_id in layer_nodes:
                    continue
                if neighbor_id not in current_positions:
                    continue

                if self.optimize_against_parents_only:
                    # Considerar solo padres (niveles anteriores).
                    neighbor_level = None
                    for lvl, ids in layers.items():
                        if neighbor_id in ids:
                            neighbor_level = lvl
                            break
                    if neighbor_level is None or neighbor_level >= level:
                        continue

                x_other, y2 = current_positions[neighbor_id]
                a = base_x - x_other
                dy = y1 - y2
                terms.append((a, dy, float(weight)))

        if not terms:
            return False

        current_offset = layer_offsets.get(level, 0.0)

        def derivative(offset: float) -> float:
            d = 0.0
            for a, dy, w in terms:
                dx = a + offset
                denom = math.sqrt(dx * dx + dy * dy)
                if denom == 0:
                    continue
                d += w * (dx / denom)
            return d

        # Buscar intervalo con cambio de signo de la derivada (función convexa).
        low = current_offset - 20.0
        high = current_offset + 20.0
        d_low = derivative(low)
        d_high = derivative(high)
        expand = 0
        while d_low > 0 and expand < 8:
            low -= (high - low)
            d_low = derivative(low)
            expand += 1
        expand = 0
        while d_high < 0 and expand < 8:
            high += (high - low)
            d_high = derivative(high)
            expand += 1

        # Si no hay bracket claro, mantener.
        if d_low > 0 or d_high < 0:
            return False

        # Bisección para root de derivada.
        for _ in range(48):
            mid = (low + high) / 2.0
            d_mid = derivative(mid)
            if d_mid < 0:
                low = mid
            else:
                high = mid

        optimal_offset = (low + high) / 2.0
        if abs(optimal_offset - current_offset) <= 0.001:
            return False

        layer_offsets[level] = optimal_offset
        return True

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

        # Discretizar por capa preservando coordenadas absolutas entre capas.
        # Antes se reindexaba cada capa como 0..N, rompiendo alineaciones verticales.
        for _, layer_nodes in layers.items():
            sorted_nodes = sorted(layer_nodes, key=lambda nid: positions[nid][0])

            prev_x = None
            for node_id in sorted_nodes:
                y = positions[node_id][1]
                target_x = int(round(positions[node_id][0]))

                # Asegurar separación mínima intra-capa después de discretizar.
                if prev_x is not None and target_x <= prev_x:
                    target_x = prev_x + 1

                normalized[node_id] = (target_x, int(y))
                prev_x = target_x

        # Desplazar globalmente si hay X negativas.
        if normalized:
            min_x = min(pos[0] for pos in normalized.values())
            if min_x < 0:
                shift = -min_x
                for node_id, (x, y) in list(normalized.items()):
                    normalized[node_id] = (x + shift, y)

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
