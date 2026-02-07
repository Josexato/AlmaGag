"""
StructureAnalyzer - Análisis de estructura del diagrama para layout abstracto

Analiza el árbol de elementos, grafo de conexiones y métricas útiles
para algoritmos de placement que minimizan cruces.

Author: José + ALMA
Version: v1.0
Date: 2026-01-17
"""

from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional, Set


@dataclass
class StructureInfo:
    """
    Información estructural del diagrama para layout abstracto.

    Attributes:
        element_tree: Árbol de elementos {id: {parent, children, depth}}
        primary_elements: Lista de IDs de elementos sin padre
        container_metrics: {id: {total_icons, max_depth, direct_children}}
        connection_graph: Grafo de adyacencia {from: [to_list]}
        incoming_graph: Grafo inverso de adyacencia {to: [from_list]}
        topological_levels: {id: level} (respetando dependencias)
        accessibility_scores: {id: score} Score de accesibilidad intra-nivel [0, 0.99]
        element_types: {type: [ids]} (agrupados por tipo)
        connection_sequences: [(from, to, order)] (orden de conexión)
    """
    element_tree: Dict[str, Dict] = field(default_factory=dict)
    primary_elements: List[str] = field(default_factory=list)
    container_metrics: Dict[str, Dict] = field(default_factory=dict)
    connection_graph: Dict[str, List[str]] = field(default_factory=dict)
    incoming_graph: Dict[str, List[str]] = field(default_factory=dict)
    topological_levels: Dict[str, int] = field(default_factory=dict)
    accessibility_scores: Dict[str, float] = field(default_factory=dict)
    element_types: Dict[str, List[str]] = field(default_factory=dict)
    connection_sequences: List[Tuple[str, str, int]] = field(default_factory=list)


class StructureAnalyzer:
    """
    Analiza la estructura del diagrama para layout abstracto.

    Responsabilidades:
    - Construir árbol de elementos (primarios vs contenidos)
    - Analizar grafo de conexiones (DAG, niveles, grupos)
    - Calcular métricas para heurísticas de placement
    """

    def __init__(self, debug: bool = False):
        """
        Inicializa el analizador de estructura.

        Args:
            debug: Si True, imprime logs de debug
        """
        self.debug = debug

    def analyze(self, layout) -> StructureInfo:
        """
        Analiza estructura completa del diagrama.

        Args:
            layout: Layout con elements, connections, elements_by_id

        Returns:
            StructureInfo con toda la información estructural
        """
        info = StructureInfo()

        # Construir árbol de elementos (primarios vs contenidos)
        self._build_element_tree(layout, info)

        # Calcular métricas de contenedores (total_icons recursivo)
        self._calculate_container_metrics(layout, info)

        # Analizar grafo de conexiones
        self._build_connection_graph(layout, info)

        # Calcular niveles topológicos
        self._calculate_topological_levels(layout, info)

        # Construir grafo inverso (incoming edges)
        self._build_incoming_graph(info)

        # Calcular scores de accesibilidad intra-nivel
        self._calculate_accessibility_scores(info)

        # Agrupar elementos por tipo
        self._group_elements_by_type(layout, info)

        # Generar secuencia de conexiones
        self._generate_connection_sequences(layout, info)

        if self.debug:
            self._print_debug_info(info)

        return info

    def _build_element_tree(self, layout, info: StructureInfo) -> None:
        """
        Construye árbol de elementos identificando primarios y contenidos.

        Args:
            layout: Layout con elements
            info: StructureInfo a poblar
        """
        # Inicializar nodos del árbol
        for elem in layout.elements:
            elem_id = elem['id']
            info.element_tree[elem_id] = {
                'parent': None,
                'children': [],
                'depth': 0,
                'is_container': 'contains' in elem
            }

        # Identificar relaciones padre-hijo
        for elem in layout.elements:
            if 'contains' not in elem:
                continue

            container_id = elem['id']
            for item in elem['contains']:
                child_id = item['id'] if isinstance(item, dict) else item
                if child_id in info.element_tree:
                    info.element_tree[child_id]['parent'] = container_id
                    info.element_tree[container_id]['children'].append(child_id)

        # Calcular profundidad de cada nodo
        self._calculate_depths(info)

        # Identificar elementos primarios (sin padre)
        info.primary_elements = [
            elem_id for elem_id, node in info.element_tree.items()
            if node['parent'] is None
        ]

    def _calculate_depths(self, info: StructureInfo) -> None:
        """
        Calcula profundidad de cada nodo en el árbol (recursivo desde raíces).

        Args:
            info: StructureInfo con element_tree
        """
        def calc_depth(elem_id: str, depth: int):
            info.element_tree[elem_id]['depth'] = depth
            for child_id in info.element_tree[elem_id]['children']:
                calc_depth(child_id, depth + 1)

        # Calcular desde elementos primarios (raíces)
        for elem_id in info.primary_elements:
            calc_depth(elem_id, 0)

    def _calculate_container_metrics(self, layout, info: StructureInfo) -> None:
        """
        Calcula métricas de contenedores (total_icons recursivo, max_depth, etc).

        Args:
            layout: Layout con elements
            info: StructureInfo a poblar
        """
        for elem in layout.elements:
            if 'contains' not in elem:
                continue

            container_id = elem['id']
            total_icons = self._count_total_icons_recursive(container_id, info, layout)
            max_depth = self._calculate_max_depth(container_id, info)
            direct_children = len(info.element_tree[container_id]['children'])

            info.container_metrics[container_id] = {
                'total_icons': total_icons,
                'max_depth': max_depth,
                'direct_children': direct_children
            }

    def _count_total_icons_recursive(
        self,
        container_id: str,
        info: StructureInfo,
        layout
    ) -> int:
        """
        Cuenta TODOS los íconos dentro de un contenedor recursivamente.

        Args:
            container_id: ID del contenedor
            info: StructureInfo con element_tree
            layout: Layout con elements_by_id

        Returns:
            int: Cantidad total de íconos (incluyendo subcontenedores)
        """
        total = 0
        children = info.element_tree[container_id]['children']

        for child_id in children:
            child_node = info.element_tree[child_id]
            if child_node['is_container']:
                # Es un subcontenedor: +1 por su ícono + todos sus hijos
                total += 1
                total += self._count_total_icons_recursive(child_id, info, layout)
            else:
                # Es un elemento normal: +1
                total += 1

        return total

    def _calculate_max_depth(self, container_id: str, info: StructureInfo) -> int:
        """
        Calcula profundidad máxima de anidamiento de un contenedor.

        Args:
            container_id: ID del contenedor
            info: StructureInfo con element_tree

        Returns:
            int: Profundidad máxima de anidamiento
        """
        def get_max_child_depth(elem_id: str) -> int:
            children = info.element_tree[elem_id]['children']
            if not children:
                return 0

            max_child = 0
            for child_id in children:
                if info.element_tree[child_id]['is_container']:
                    max_child = max(max_child, 1 + get_max_child_depth(child_id))
            return max_child

        return get_max_child_depth(container_id)

    def _build_connection_graph(self, layout, info: StructureInfo) -> None:
        """
        Construye grafo de conexiones (adyacencia).

        Args:
            layout: Layout con connections
            info: StructureInfo a poblar
        """
        # Inicializar listas de adyacencia para elementos primarios
        for elem_id in info.primary_elements:
            info.connection_graph[elem_id] = []

        # Agregar conexiones
        for conn in layout.connections:
            from_id = conn['from']
            to_id = conn['to']

            # Resolver a elementos primarios si están contenidos
            from_primary = self._get_primary_element(from_id, info)
            to_primary = self._get_primary_element(to_id, info)

            # Ignorar autoloops (conexiones de un contenedor consigo mismo)
            # Esto sucede cuando hay conexiones internas entre elementos del mismo contenedor
            if from_primary == to_primary:
                continue

            if from_primary not in info.connection_graph:
                info.connection_graph[from_primary] = []

            if to_primary not in info.connection_graph[from_primary]:
                info.connection_graph[from_primary].append(to_primary)

    def _get_primary_element(self, elem_id: str, info: StructureInfo) -> str:
        """
        Obtiene el elemento primario de un elemento (si está contenido).

        Args:
            elem_id: ID del elemento
            info: StructureInfo con element_tree

        Returns:
            str: ID del elemento primario (raíz del árbol)
        """
        node = info.element_tree.get(elem_id)
        if not node:
            return elem_id

        # Subir hasta la raíz
        current = elem_id
        while info.element_tree[current]['parent'] is not None:
            current = info.element_tree[current]['parent']

        return current

    def _calculate_topological_levels(self, layout, info: StructureInfo) -> None:
        """
        Calcula niveles topológicos usando BFS en el grafo de conexiones.

        Args:
            layout: Layout con connections
            info: StructureInfo a poblar
        """
        # Inicializar niveles
        for elem_id in info.primary_elements:
            info.topological_levels[elem_id] = 0

        # Calcular niveles usando BFS
        visited = set()
        queue = []

        # Encontrar elementos sin dependencias entrantes (nivel 0)
        has_incoming = set()
        for from_id, to_list in info.connection_graph.items():
            for to_id in to_list:
                has_incoming.add(to_id)

        # Nivel 0: Sin dependencias entrantes
        for elem_id in info.primary_elements:
            if elem_id not in has_incoming:
                queue.append((elem_id, 0))
                visited.add(elem_id)

        # BFS
        while queue:
            current_id, level = queue.pop(0)
            info.topological_levels[current_id] = level

            # Procesar vecinos
            for neighbor_id in info.connection_graph.get(current_id, []):
                if neighbor_id not in visited:
                    queue.append((neighbor_id, level + 1))
                    visited.add(neighbor_id)
                else:
                    # Actualizar nivel si encontramos un camino más largo
                    old_level = info.topological_levels[neighbor_id]
                    new_level = level + 1
                    if new_level > old_level:
                        if self.debug:
                            print(f"[TOPOLOGICAL] {neighbor_id}: nivel {old_level} -> {new_level} (via {current_id})")
                    info.topological_levels[neighbor_id] = max(
                        info.topological_levels[neighbor_id],
                        level + 1
                    )

        # Post-processing: leaf nodes stay at parent level (leaf stays in parent level)
        # Build local reverse graph for parent lookup
        local_incoming = {}
        for from_id, to_list in info.connection_graph.items():
            for to_id in to_list:
                if to_id not in local_incoming:
                    local_incoming[to_id] = []
                if from_id not in local_incoming[to_id]:
                    local_incoming[to_id].append(from_id)

        # Apply leaf correction: leaves stay at their dominant parent's level
        for elem_id in info.primary_elements:
            outdeg = len(info.connection_graph.get(elem_id, []))
            if outdeg == 0:
                parents = local_incoming.get(elem_id, [])
                if parents:
                    max_base_parent = max(
                        info.topological_levels[p] for p in parents
                    )
                    old_level = info.topological_levels[elem_id]
                    info.topological_levels[elem_id] = max_base_parent
                    if self.debug and old_level != max_base_parent:
                        print(
                            f"[TOPOLOGICAL] Leaf correction: {elem_id} "
                            f"level {old_level} -> {max_base_parent} "
                            f"(stays at parent level)"
                        )

        # Debug: Mostrar niveles finales
        if self.debug:
            print(f"\n[TOPOLOGICAL] Niveles finales:")
            for elem_id, level in sorted(info.topological_levels.items(), key=lambda x: (x[1], x[0])):
                print(f"  Nivel {level}: {elem_id}")

    def _build_incoming_graph(self, info: StructureInfo) -> None:
        """
        Construye grafo inverso de adyacencia (incoming edges).

        Para cada nodo, lista los nodos que tienen aristas dirigidas hacia él.
        Es el reverso de connection_graph: si connection_graph tiene A -> B,
        incoming_graph tendrá B <- A.

        Args:
            info: StructureInfo con connection_graph ya poblado
        """
        for elem_id in info.primary_elements:
            info.incoming_graph[elem_id] = []

        for from_id, to_list in info.connection_graph.items():
            for to_id in to_list:
                if to_id not in info.incoming_graph:
                    info.incoming_graph[to_id] = []
                if from_id not in info.incoming_graph[to_id]:
                    info.incoming_graph[to_id].append(from_id)

    def _calculate_accessibility_scores(
        self,
        info: StructureInfo,
        alpha: float = 0.03,
        beta: float = 0.01,
        gamma: float = 0.0,
        max_score: float = 0.99
    ) -> None:
        """
        Calcula scores de accesibilidad intra-nivel para cada elemento primario.

        Score[v] es un heurístico [0, max_score] que indica cuán "accesible"
        debería ser un nodo dentro de su nivel. Nodos con mayor Score se
        atraen hacia el centro del nivel durante el ordenamiento barycenter.

        Componentes:
        - W_hijos (hub-ness): más hijos salientes → más Score.
          Solo cuenta hijos extra más allá del primero.
        - W_precedence (skip connections): padres directos desde niveles
          más lejanos que el padre inmediato aportan distancia * alpha.
        - W_fanin (opcional): fan-in de padres en el mismo nivel máximo.
          Desactivado por defecto (gamma=0).

        Args:
            info: StructureInfo con topological_levels, connection_graph e incoming_graph
            alpha: Peso por unidad de distancia en W_precedence
            beta: Peso por hijo extra en W_hijos
            gamma: Peso por padre extra en W_fanin (0.0 = desactivado)
            max_score: Clamp máximo del score
        """
        for elem_id in info.primary_elements:
            base_v = info.topological_levels.get(elem_id, 0)

            # W_hijos: outdegree - 1 (primer hijo no cuenta)
            outdeg = len(info.connection_graph.get(elem_id, []))
            w_hijos = max(0, outdeg - 1) * beta

            # W_precedence: padres directos desde niveles lejanos
            w_precedence = 0.0
            parents = info.incoming_graph.get(elem_id, [])

            if parents:
                parent_bases = [info.topological_levels.get(p, 0) for p in parents]
                max_base_parent = max(parent_bases)

                for p in parents:
                    base_p = info.topological_levels.get(p, 0)
                    if base_p < max_base_parent:
                        dist = base_v - base_p
                        w_precedence += dist * alpha

            # W_fanin: fan-in extra en el mismo nivel máximo (opcional)
            w_fanin = 0.0
            if gamma > 0 and parents:
                indeg = len(parents)
                w_fanin = max(0, indeg - 1) * gamma

            # Combinar y clamp
            score_raw = w_hijos + w_precedence + w_fanin
            info.accessibility_scores[elem_id] = min(max_score, score_raw)

        if self.debug:
            scored = {k: v for k, v in info.accessibility_scores.items() if v > 0}
            if scored:
                print(f"\n[ACCESSIBILITY] Scores calculados:")
                for elem_id in sorted(scored, key=scored.get, reverse=True):
                    score = scored[elem_id]
                    base = info.topological_levels.get(elem_id, 0)
                    outdeg = len(info.connection_graph.get(elem_id, []))
                    indeg = len(info.incoming_graph.get(elem_id, []))
                    print(f"  {elem_id}: score={score:.4f} (base={base}, out={outdeg}, in={indeg})")
            else:
                print(f"\n[ACCESSIBILITY] Todos los scores son 0 (grafo simple)")

    def _group_elements_by_type(self, layout, info: StructureInfo) -> None:
        """
        Agrupa elementos primarios por tipo.

        Args:
            layout: Layout con elements
            info: StructureInfo a poblar
        """
        for elem in layout.elements:
            if elem['id'] not in info.primary_elements:
                continue

            elem_type = elem.get('type', 'unknown')
            if elem_type not in info.element_types:
                info.element_types[elem_type] = []

            info.element_types[elem_type].append(elem['id'])

    def _generate_connection_sequences(self, layout, info: StructureInfo) -> None:
        """
        Genera secuencia ordenada de conexiones (para heurística de orden).

        Args:
            layout: Layout con connections
            info: StructureInfo a poblar
        """
        for order, conn in enumerate(layout.connections):
            from_id = conn['from']
            to_id = conn['to']

            # Resolver a elementos primarios
            from_primary = self._get_primary_element(from_id, info)
            to_primary = self._get_primary_element(to_id, info)

            info.connection_sequences.append((from_primary, to_primary, order))

    def _print_debug_info(self, info: StructureInfo) -> None:
        """Imprime información de debug sobre la estructura."""
        print(f"\n[STRUCTURE] Análisis completado:")
        print(f"  - Elementos primarios: {len(info.primary_elements)}")
        print(f"  - Contenedores: {len(info.container_metrics)}")

        if info.container_metrics:
            max_contained = max(m['total_icons'] for m in info.container_metrics.values())
            print(f"  - Max contenido: {max_contained} íconos")

        print(f"  - Conexiones: {len(info.connection_sequences)}")
        print(f"  - Tipos de elementos: {list(info.element_types.keys())}")

        # Niveles topológicos
        if info.topological_levels:
            max_level = max(info.topological_levels.values())
            print(f"  - Niveles topológicos: {max_level + 1}")

        # Accessibility scores
        if info.accessibility_scores:
            scored_count = sum(1 for v in info.accessibility_scores.values() if v > 0)
            if scored_count:
                max_score = max(info.accessibility_scores.values())
                print(f"  - Nodos con score > 0: {scored_count}, max score: {max_score:.4f}")
