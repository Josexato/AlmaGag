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
        primary_node_types: {elem_id: "Simple|Contenedor|Contenedor Virtual|TOI"} Tipo de nodo primario
        leaf_nodes: {elem_id} Nodos hoja (outdegree=0) en el grafo de conexiones
        terminal_leaf_nodes: {elem_id} Hojas terminales (sin hermanos con ramas activas)
        source_nodes: Set of element IDs that have no incoming edges
        ancestor_nodes: Set of source nodes with the largest descendant tree per group
        toi_nodes: Set of source nodes that are NOT ancestors (TOI = "tío")
        toi_virtual_containers: List of {id, members, toi_id, pivot_id} virtual family groups
        element_to_toi_container: {elem_id: container_index} maps members to their virtual container
        ndpr_elements: List of NdPr node IDs (collapsed view for phases 1-5)
        ndpr_topological_levels: {ndpr_id: level} levels for NdPr nodes only
        ndpr_connection_graph: {ndpr_id: [ndpr_ids]} abstract connections between NdPr nodes
        element_to_ndpr: {elem_id: ndpr_id} maps every element to its NdPr representative
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
    source_nodes: Set[str] = field(default_factory=set)
    ancestor_nodes: Set[str] = field(default_factory=set)
    toi_nodes: Set[str] = field(default_factory=set)
    toi_virtual_containers: List[Dict] = field(default_factory=list)
    element_to_toi_container: Dict[str, int] = field(default_factory=dict)
    ndpr_elements: List[str] = field(default_factory=list)
    ndpr_topological_levels: Dict[str, int] = field(default_factory=dict)
    ndpr_connection_graph: Dict[str, List[str]] = field(default_factory=dict)
    element_to_ndpr: Dict[str, str] = field(default_factory=dict)


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

        # Detectar nodos origen, ancestros, TOI y contenedores virtuales TOI
        self._detect_toi_virtual_containers(info)

        # Clasificar y asignar IDs a nodos primarios
        self._classify_primary_nodes(layout, info)

        # Construir grafo abstracto NdPr (vista colapsada para fases 1-5)
        self._build_ndpr_abstract_graph(info)

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

        # Relocate minor source nodes (spouses/in-laws) to their partner's level.
        # Among all source nodes (no incoming edges), only those with the largest
        # descendant tree stay at level 0. Others are placed at the same level as
        # the other parent of their shared child node.
        self._relocate_minor_sources(info, local_incoming)

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

    def _relocate_minor_sources(
        self,
        info: StructureInfo,
        local_incoming: Dict[str, List[str]]
    ) -> None:
        """
        Among source nodes (no incoming edges, level 0), only those with the
        largest descendant tree stay at level 0.  The rest ('minor sources',
        typically spouses/in-laws) are relocated to the same level as the other
        parent of their shared child node.

        If a minor source has no co-parent (i.e. it is the sole parent of its
        children), it is treated as the root of an independent group and stays
        at level 0.
        """
        # 1. Identify source nodes (no incoming edges)
        source_nodes = [
            eid for eid in info.primary_elements
            if not local_incoming.get(eid)
        ]

        if len(source_nodes) <= 1:
            return

        # 2. Count descendants reachable from each source via connection_graph
        def _count_descendants(start: str) -> int:
            visited = set()
            queue = [start]
            while queue:
                node = queue.pop()
                if node in visited:
                    continue
                visited.add(node)
                for neighbor in info.connection_graph.get(node, []):
                    if neighbor not in visited:
                        queue.append(neighbor)
            return len(visited) - 1  # exclude the start node itself

        desc_counts = {eid: _count_descendants(eid) for eid in source_nodes}
        max_desc = max(desc_counts.values())

        # 3. Major sources stay at level 0; collect minor sources
        minor_sources = [
            eid for eid in source_nodes
            if desc_counts[eid] < max_desc
        ]

        if not minor_sources:
            return

        # 4. For each minor source, find the co-parent's level
        for src in minor_sources:
            children = info.connection_graph.get(src, [])
            co_parent_level = None

            for child in children:
                # Other parents of this child (besides src)
                other_parents = [
                    p for p in local_incoming.get(child, [])
                    if p != src
                ]
                for op in other_parents:
                    lvl = info.topological_levels.get(op, 0)
                    if co_parent_level is None or lvl > co_parent_level:
                        co_parent_level = lvl

            if co_parent_level is not None:
                # Place at same level as co-parent
                info.topological_levels[src] = co_parent_level
            # else: independent group root → stays at level 0

    def _detect_toi_virtual_containers(self, info: StructureInfo) -> None:
        """
        Detect source nodes, ancestors, TOI nodes, and build virtual containers.

        Terminology:
        - Nodos origen: elements with no incoming edges
        - Ancestros: source nodes with the largest descendant tree (per group)
        - TOI ("tío"): source nodes that are NOT ancestors
        - Virtual container: for each child that has a TOI parent, group
          ALL of that child's parents + ALL of that child's descendants

        The virtual container ensures the family unit stays together in layout.
        """
        # 1. Identify source nodes (nodos origen)
        info.source_nodes = set(
            eid for eid in info.primary_elements
            if not info.incoming_graph.get(eid)
        )

        if len(info.source_nodes) <= 1:
            info.ancestor_nodes = set(info.source_nodes)
            return

        # 2. Count descendants for each source node
        def _count_descendants(start: str) -> int:
            visited = set()
            queue = [start]
            while queue:
                node = queue.pop()
                if node in visited:
                    continue
                visited.add(node)
                for nb in info.connection_graph.get(node, []):
                    if nb not in visited:
                        queue.append(nb)
            return len(visited) - 1

        def _get_all_descendants(start: str) -> Set[str]:
            visited = set()
            queue = [start]
            while queue:
                node = queue.pop()
                if node in visited:
                    continue
                visited.add(node)
                for nb in info.connection_graph.get(node, []):
                    if nb not in visited:
                        queue.append(nb)
            visited.discard(start)
            return visited

        desc_counts = {eid: _count_descendants(eid) for eid in info.source_nodes}
        max_desc = max(desc_counts.values())

        # 3. Ancestors = source nodes with max descendants; TOI = the rest
        info.ancestor_nodes = {
            eid for eid in info.source_nodes
            if desc_counts[eid] == max_desc
        }
        info.toi_nodes = info.source_nodes - info.ancestor_nodes

        if not info.toi_nodes:
            return

        # 4. For each child that has a TOI parent, create a virtual container
        #    containing all parents of that child + all descendants of that child
        seen_pivots = set()  # avoid duplicates if multiple TOIs share a child

        for toi_id in info.toi_nodes:
            children_of_toi = info.connection_graph.get(toi_id, [])

            for pivot_id in children_of_toi:
                if pivot_id in seen_pivots:
                    continue
                seen_pivots.add(pivot_id)

                # Collect all parents of this pivot node
                parents = set(info.incoming_graph.get(pivot_id, []))

                # Collect all descendants of this pivot node
                descendants = _get_all_descendants(pivot_id)

                # Virtual container members: parents + pivot + descendants
                members = parents | {pivot_id} | descendants

                container_idx = len(info.toi_virtual_containers)
                info.toi_virtual_containers.append({
                    'id': f'_toi_vc_{container_idx}',
                    'toi_id': toi_id,
                    'pivot_id': pivot_id,
                    'members': members,
                })

                for member_id in members:
                    info.element_to_toi_container[member_id] = container_idx

    def _classify_primary_nodes(self, layout, info: StructureInfo) -> None:
        """
        Asigna IDs únicos (NdPr) y clasifica cada nodo primario.

        Todo contenedor (virtual o real) es un NdPr, salvo que esté
        dentro de otro contenedor.

        Tipos de nodo:
        - Simple: Nodo sin hijos, no contenido en ningún contenedor
        - Contenedor: Nodo que contiene otros elementos (real)
        - Contenedor Virtual: Nodo parte de un ciclo detectado
        - Contenedor Virtual TOI: Contenedor virtual generado por detección TOI
        - TOI: Nodo origen que no es ancestro (contenido en su VC TOI)

        Args:
            layout: Layout con elements
            info: StructureInfo a poblar
        """
        # Detectar nodos sin nivel topológico (posibles ciclos)
        nodes_without_level = set()
        for elem_id in info.primary_elements:
            if elem_id not in info.topological_levels:
                nodes_without_level.add(elem_id)

        # Build set of elements that are inside any container (real or virtual)
        # so they don't get their own NdPr
        contained_elements = set()

        # Elements inside real containers
        for elem_id in info.primary_elements:
            if info.element_tree[elem_id]['parent'] is not None:
                contained_elements.add(elem_id)

        # Elements inside TOI virtual containers (members of VCs)
        for vc in info.toi_virtual_containers:
            for member_id in vc['members']:
                contained_elements.add(member_id)

        # Determine which TOI VCs are nested inside another container
        # (if all members are inside a real container, the VC is nested)
        nested_vcs = set()
        for vc_idx, vc in enumerate(info.toi_virtual_containers):
            for member_id in vc['members']:
                tree_node = info.element_tree.get(member_id, {})
                parent = tree_node.get('parent')
                if parent is not None:
                    # This VC has a member inside a real container → VC is nested
                    nested_vcs.add(vc_idx)
                    break

        # Assign NdPr IDs: first to elements, then to TOI virtual containers
        node_counter = 1

        for elem_id in info.primary_elements:
            # Skip elements contained inside any container (real or virtual TOI)
            if elem_id in contained_elements:
                # Classify but don't assign NdPr
                if elem_id in info.toi_nodes:
                    info.primary_node_types[elem_id] = "TOI"
                elif elem_id in info.element_to_toi_container:
                    info.primary_node_types[elem_id] = "TOI Virtual"
                else:
                    info.primary_node_types[elem_id] = "Simple"
                continue

            # Assign NdPr ID
            node_id = f"NdPr{node_counter:03d}"
            info.primary_node_ids[elem_id] = node_id
            node_counter += 1

            # Classify
            if elem_id in nodes_without_level:
                node_type = "Contenedor Virtual"
            elif info.element_tree[elem_id]['is_container']:
                node_type = "Contenedor"
            else:
                node_type = "Simple"

            info.primary_node_types[elem_id] = node_type

        # Assign NdPr IDs to TOI virtual containers (unless nested)
        for vc_idx, vc in enumerate(info.toi_virtual_containers):
            if vc_idx in nested_vcs:
                continue

            node_id = f"NdPr{node_counter:03d}"
            vc_id = vc['id']
            info.primary_node_ids[vc_id] = node_id
            info.primary_node_types[vc_id] = "Contenedor Virtual TOI"
            node_counter += 1

    def _build_ndpr_abstract_graph(self, info: StructureInfo) -> None:
        """
        Build abstract NdPr-only view: collapsed levels and connection graph.

        Maps every element to its NdPr representative:
        - Elements with their own NdPr → themselves
        - Elements inside a TOI VC → the VC's id
        - Elements inside a real container → the container's id

        Then builds:
        - ndpr_elements: ordered list of NdPr node IDs
        - ndpr_topological_levels: level for each NdPr node
        - ndpr_connection_graph: connections between NdPr nodes (no self-loops)
        """
        # 1. Map every element to its NdPr representative
        for elem_id in info.primary_elements:
            if elem_id in info.primary_node_ids:
                # This element IS a NdPr
                info.element_to_ndpr[elem_id] = elem_id
            elif elem_id in info.element_to_toi_container:
                # Inside a TOI VC
                vc_idx = info.element_to_toi_container[elem_id]
                vc_id = info.toi_virtual_containers[vc_idx]['id']
                info.element_to_ndpr[elem_id] = vc_id
            else:
                # Inside a real container - find parent with NdPr
                current = elem_id
                tree_node = info.element_tree.get(current, {})
                parent = tree_node.get('parent')
                while parent and parent not in info.primary_node_ids:
                    tree_node = info.element_tree.get(parent, {})
                    parent = tree_node.get('parent')
                if parent:
                    info.element_to_ndpr[elem_id] = parent
                else:
                    info.element_to_ndpr[elem_id] = elem_id

        # 2. Build ndpr_elements list (ordered by NdPr ID)
        info.ndpr_elements = sorted(
            info.primary_node_ids.keys(),
            key=lambda eid: info.primary_node_ids[eid]
        )

        # 3. Assign levels to NdPr nodes
        for ndpr_id in info.ndpr_elements:
            if ndpr_id.startswith('_toi_vc_'):
                # VC level = min level of its members
                vc_idx = int(ndpr_id.split('_')[-1])
                vc = info.toi_virtual_containers[vc_idx]
                member_levels = [
                    info.topological_levels.get(m, 0)
                    for m in vc['members']
                ]
                info.ndpr_topological_levels[ndpr_id] = min(member_levels)
            else:
                # Regular element keeps its level
                info.ndpr_topological_levels[ndpr_id] = info.topological_levels.get(ndpr_id, 0)

        # 4. Build abstract connection graph between NdPr nodes
        for ndpr_id in info.ndpr_elements:
            info.ndpr_connection_graph[ndpr_id] = []

        seen_edges = set()
        for from_id, to_list in info.connection_graph.items():
            ndpr_from = info.element_to_ndpr.get(from_id, from_id)
            for to_id in to_list:
                ndpr_to = info.element_to_ndpr.get(to_id, to_id)
                # Skip self-loops (internal connections within same NdPr)
                if ndpr_from == ndpr_to:
                    continue
                edge = (ndpr_from, ndpr_to)
                if edge not in seen_edges:
                    seen_edges.add(edge)
                    if ndpr_from in info.ndpr_connection_graph:
                        info.ndpr_connection_graph[ndpr_from].append(ndpr_to)

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
