"""
StructureAnalyzer - Análisis de estructura del diagrama para layout abstracto

Analiza el árbol de elementos, grafo de conexiones y métricas útiles
para algoritmos de placement que minimizan cruces.

Author: José + ALMA
Version: v1.0
Date: 2026-01-17
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional, Set
from AlmaGag.utils import extract_item_id

logger = logging.getLogger('AlmaGag')


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
        primary_node_ids: {elem_id: "NdPr001"} IDs únicos para nodos primarios
        primary_node_types: {elem_id: "Simple|Contenedor|Contenedor Virtual"} Tipo de nodo primario
        leaf_nodes: {elem_id} Nodos hoja (outdegree=0) en el grafo de conexiones
        terminal_leaf_nodes: {elem_id} Hojas terminales (sin hermanos con ramas activas)
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
    primary_node_ids: Dict[str, str] = field(default_factory=dict)
    primary_node_types: Dict[str, str] = field(default_factory=dict)
    leaf_nodes: Set[str] = field(default_factory=set)
    terminal_leaf_nodes: Set[str] = field(default_factory=set)


class StructureAnalyzer:
    """
    Analiza la estructura del diagrama para layout abstracto.

    Responsabilidades:
    - Construir árbol de elementos (primarios vs contenidos)
    - Analizar grafo de conexiones (DAG, niveles, grupos)
    - Calcular métricas para heurísticas de placement
    """

    def __init__(
        self,
        debug: bool = False,
        centrality_alpha: float = 0.15,
        centrality_beta: float = 0.10,
        centrality_gamma: float = 0.15,
        centrality_max_score: float = 100.0,
    ):
        """
        Inicializa el analizador de estructura.

        Args:
            debug: Si True, imprime logs de debug
            centrality_alpha: Peso por unidad de distancia en W_precedence (skip connections)
            centrality_beta: Peso por hijo extra en W_hijos (hub-ness)
            centrality_gamma: Peso por padre extra en W_fanin (0.0 = desactivado)
            centrality_max_score: Clamp máximo del score de accesibilidad
        """
        self.debug = debug
        self.centrality_alpha = centrality_alpha
        self.centrality_beta = centrality_beta
        self.centrality_gamma = centrality_gamma
        self.centrality_max_score = centrality_max_score

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

        # Construir grafo inverso (incoming edges)
        self._build_incoming_graph(info)

        # Detectar hojas y hojas terminales
        self._identify_leaf_and_terminal_nodes(info)

        # Calcular niveles topológicos
        self._calculate_topological_levels(layout, info)

        # Clasificar y asignar IDs a nodos primarios
        self._classify_primary_nodes(layout, info)

        # Calcular scores de accesibilidad intra-nivel
        self._calculate_accessibility_scores(
            info,
            alpha=self.centrality_alpha,
            beta=self.centrality_beta,
            gamma=self.centrality_gamma,
            max_score=self.centrality_max_score,
        )

        # Agrupar elementos por tipo
        self._group_elements_by_type(layout, info)

        # Generar secuencia de conexiones
        self._generate_connection_sequences(layout, info)

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
                child_id = extract_item_id(item)
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

        Reglas de post-procesamiento:
        1) Hojas normales se alinean al nivel del padre dominante.
        2) Hojas terminales suben un nivel sobre su padre dominante.

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
                    info.topological_levels[neighbor_id] = max(
                        info.topological_levels[neighbor_id],
                        level + 1
                    )

        # Build local reverse graph for parent lookup
        local_incoming = {}
        for from_id, to_list in info.connection_graph.items():
            for to_id in to_list:
                if to_id not in local_incoming:
                    local_incoming[to_id] = []
                if from_id not in local_incoming[to_id]:
                    local_incoming[to_id].append(from_id)

        # Correccion de consistencia para nodos no-hoja:
        # todo nodo con hijos debe estar al menos un nivel sobre su padre dominante.
        # Esto corrige casos donde BFS actualiza un padre tarde y no reprocesa hijos.
        self._enforce_non_leaf_parent_progression(info, local_incoming)

        # Apply leaf correction: leaves stay at their dominant parent's level
        for elem_id in info.primary_elements:
            outdeg = len(info.connection_graph.get(elem_id, []))
            if outdeg == 0:
                parents = local_incoming.get(elem_id, [])
                if parents:
                    max_base_parent = max(
                        info.topological_levels[p] for p in parents
                    )
                    info.topological_levels[elem_id] = max_base_parent

        # Corrección para hojas terminales: suben un nivel sobre su padre dominante
        for elem_id in info.terminal_leaf_nodes:
            parents = local_incoming.get(elem_id, [])
            if parents:
                max_parent_level = max(info.topological_levels[p] for p in parents)
                info.topological_levels[elem_id] = max_parent_level + 1

    def _detect_cycle_nodes(
        self,
        info: StructureInfo,
        local_incoming: Dict[str, List[str]]
    ) -> Set[Tuple[str, str]]:
        """
        Detecta aristas que forman parte de ciclos en el grafo de conexiones
        primarias y retorna el conjunto de back-edges a ignorar.

        Usa DFS con coloreo (WHITE/GRAY/BLACK) para encontrar back-edges.

        Returns:
            Set de tuplas (parent, child) que son back-edges de ciclos.
        """
        WHITE, GRAY, BLACK = 0, 1, 2
        color = {eid: WHITE for eid in info.primary_elements}
        back_edges: Set[Tuple[str, str]] = set()

        def dfs(node: str) -> None:
            color[node] = GRAY
            for neighbor in info.connection_graph.get(node, []):
                if neighbor not in color:
                    continue
                if color[neighbor] == GRAY:
                    # Back-edge: neighbor → node en local_incoming
                    back_edges.add((node, neighbor))
                elif color[neighbor] == WHITE:
                    dfs(neighbor)
            color[node] = BLACK

        for eid in info.primary_elements:
            if color[eid] == WHITE:
                dfs(eid)

        if back_edges and self.debug:
            logger.debug(f"  Ciclos detectados - back-edges ignorados: {back_edges}")

        return back_edges

    def _enforce_non_leaf_parent_progression(
        self,
        info: StructureInfo,
        local_incoming: Dict[str, List[str]]
    ) -> None:
        """
        Garantiza para nodos con hijos (outdeg > 0):
            level(node) >= max(level(parent)) + 1
        aplicando un fixpoint hasta converger.

        Detecta ciclos y excluye back-edges para evitar loops infinitos.
        """
        # Detectar back-edges de ciclos para excluirlos del fixpoint
        back_edges = self._detect_cycle_nodes(info, local_incoming)

        max_iterations = len(info.primary_elements) * 2
        changed = True
        iteration = 0
        while changed:
            if iteration >= max_iterations:
                if self.debug:
                    logger.debug(f"  _enforce_non_leaf_parent_progression: "
                          f"max iterations ({max_iterations}) alcanzado, "
                          f"posible ciclo residual")
                break
            changed = False
            iteration += 1
            for elem_id in info.primary_elements:
                outdeg = len(info.connection_graph.get(elem_id, []))
                if outdeg == 0:
                    continue

                parents = local_incoming.get(elem_id, [])
                if not parents:
                    continue

                # Filtrar parents que forman back-edges (ciclos)
                acyclic_parents = [
                    p for p in parents
                    if (p, elem_id) not in back_edges
                ]
                if not acyclic_parents:
                    continue

                required_level = max(info.topological_levels.get(p, 0) for p in acyclic_parents) + 1
                current_level = info.topological_levels.get(elem_id, 0)

                if current_level < required_level:
                    info.topological_levels[elem_id] = required_level
                    changed = True

    def _classify_primary_nodes(self, layout, info: StructureInfo) -> None:
        """
        Asigna IDs únicos y clasifica cada nodo primario.

        Tipos:
        - Simple: Nodo sin hijos (no es contenedor)
        - Contenedor: Nodo que contiene otros elementos
        - Contenedor Virtual: Nodo parte de un ciclo detectado

        Args:
            layout: Layout con elements
            info: StructureInfo a poblar
        """
        # Detectar nodos sin nivel topológico (posibles ciclos)
        nodes_without_level = set()
        for elem_id in info.primary_elements:
            if elem_id not in info.topological_levels:
                nodes_without_level.add(elem_id)

        # Asignar IDs secuenciales y clasificar
        node_counter = 1
        for elem_id in info.primary_elements:
            # Asignar ID único
            node_id = f"NdPr{node_counter:03d}"
            info.primary_node_ids[elem_id] = node_id

            # Clasificar por tipo
            if elem_id in nodes_without_level:
                # Parte de un ciclo
                node_type = "Contenedor Virtual"
            elif info.element_tree[elem_id]['is_container']:
                # Es un contenedor real
                node_type = "Contenedor"
            else:
                # Nodo simple
                node_type = "Simple"

            info.primary_node_types[elem_id] = node_type
            node_counter += 1

        pass  # clasificación completada, debug se muestra en laf_optimizer

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

    def _identify_leaf_and_terminal_nodes(self, info: StructureInfo) -> None:
        """
        Identifica nodos hoja y nodos hoja terminal.

        Definiciones:
        - leaf node: nodo primario con outdegree = 0.
        - terminal leaf: hoja L tal que para cada predecesor directo P de L,
          todos los demás sucesores de P (distintos de L) también son hoja.

        Esta métrica permite distinguir hojas "realmente terminales" de hojas
        que conviven con ramas activas en sus nodos predecesores.

        Args:
            info: StructureInfo con connection_graph e incoming_graph poblados
        """
        leaf_nodes = set()

        # Paso 1: identificar hojas por outdegree
        for elem_id in info.primary_elements:
            outdeg = len(info.connection_graph.get(elem_id, []))
            if outdeg == 0:
                leaf_nodes.add(elem_id)

        # Paso 2: identificar hojas terminales
        terminal_leaf_nodes = set()
        for leaf_id in leaf_nodes:
            predecessors = info.incoming_graph.get(leaf_id, [])

            # Hoja aislada/sin predecesores: se considera terminal por definición
            if not predecessors:
                terminal_leaf_nodes.add(leaf_id)
                continue

            is_terminal = True
            for pred_id in predecessors:
                successors = info.connection_graph.get(pred_id, [])

                # Revisar "hermanos" en el grafo dirigido (otros sucesores del mismo predecesor)
                for sibling_id in successors:
                    if sibling_id == leaf_id:
                        continue

                    sibling_outdeg = len(info.connection_graph.get(sibling_id, []))
                    if sibling_outdeg > 0:
                        # Existe un hermano con rama activa -> leaf_id no es terminal
                        is_terminal = False
                        break

                if not is_terminal:
                    break

            if is_terminal:
                terminal_leaf_nodes.add(leaf_id)

        info.leaf_nodes = leaf_nodes
        info.terminal_leaf_nodes = terminal_leaf_nodes

        pass  # hojas identificadas, debug se muestra en laf_optimizer

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

        pass  # scores calculados, debug se muestra en laf_optimizer

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
        logger.debug(f"\n[STRUCTURE] Análisis completado:")
        logger.debug(f"  - Elementos primarios: {len(info.primary_elements)}")
        logger.debug(f"  - Contenedores: {len(info.container_metrics)}")

        if info.container_metrics:
            max_contained = max(m['total_icons'] for m in info.container_metrics.values())
            logger.debug(f"  - Max contenido: {max_contained} íconos")

        logger.debug(f"  - Conexiones: {len(info.connection_sequences)}")
        logger.debug(f"  - Tipos de elementos: {list(info.element_types.keys())}")
        logger.debug(f"  - Hojas detectadas: {len(info.leaf_nodes)}")
        logger.debug(f"  - Hojas terminales: {len(info.terminal_leaf_nodes)}")

        # Niveles topológicos
        if info.topological_levels:
            max_level = max(info.topological_levels.values())
            logger.debug(f"  - Niveles topológicos: {max_level + 1}")

            # Distribución por nivel
            by_level = {}
            for elem_id, level in info.topological_levels.items():
                if level not in by_level:
                    by_level[level] = []
                by_level[level].append(elem_id)

            logger.debug(f"  - Distribución por nivel:")
            for level in sorted(by_level.keys()):
                count = len(by_level[level])
                logger.debug(f"      Nivel {level}: {count} elementos")

        # Accessibility scores
        if info.accessibility_scores:
            scored_count = sum(1 for v in info.accessibility_scores.values() if v > 0)
            if scored_count:
                max_score = max(info.accessibility_scores.values())
                logger.debug(f"  - Nodos con score > 0: {scored_count}, max score: {max_score:.4f}")

                # Top 3 elementos con mayor score
                scored = {k: v for k, v in info.accessibility_scores.items() if v > 0}
                top_3 = sorted(scored.items(), key=lambda x: x[1], reverse=True)[:3]
                logger.debug(f"  - Top 3 elementos por accessibility score:")
                for elem_id, score in top_3:
                    logger.debug(f"      {elem_id}: {score:.4f}")
