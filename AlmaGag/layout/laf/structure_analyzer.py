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
        primary_node_ids: {elem_id: "NdDp01-001"} IDs únicos para nodos abstractos (depth 0 + VCs)
        all_node_ids: {elem_id: "NdDp02-001"} IDs para TODOS los elementos (incluye depth 1+)
        primary_node_types: {elem_id: "Simple|Contenedor|Contenedor Virtual|TOI"} Tipo de nodo primario
        leaf_nodes: {elem_id} Nodos hoja (outdegree=0) en el grafo de conexiones
        terminal_leaf_nodes: {elem_id} Hojas terminales (sin hermanos con ramas activas)
        source_nodes: Set of element IDs that have no incoming edges
        ancestor_nodes: Set of source nodes with the largest descendant tree per group
        toi_nodes: Set of source nodes that are NOT ancestors (TOI = "tío")
        toi_virtual_containers: List of {id, members, toi_id, pivot_id} virtual family groups
        element_to_toi_container: {elem_id: container_index} maps members to their virtual container
        scc_virtual_containers: List of {id, members} SCC groups (ciclos de 3+ nodos)
        element_to_scc_container: {elem_id: container_index} maps SCC members
        loop_virtual_containers: List of {id, members} Loop groups (ciclos mutuos de 2 nodos)
        element_to_loop_container: {elem_id: container_index} maps Loop members
        leaf_virtual_containers: List of {id, members, parent_id} Leaf groups
        element_to_leaf_container: {elem_id: container_index} maps Leaf members
        ndpr_elements: List of NdDp node IDs (collapsed view for phases 1-5)
        ndpr_topological_levels: {ndpr_id: level} levels for NdDp nodes only
        ndpr_connection_graph: {ndpr_id: [ndpr_ids]} abstract connections between NdDp nodes
        element_to_ndpr: {elem_id: ndpr_id} maps every element to its NdDp representative
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
    all_node_ids: Dict[str, str] = field(default_factory=dict)
    primary_node_types: Dict[str, str] = field(default_factory=dict)
    leaf_nodes: Set[str] = field(default_factory=set)
    terminal_leaf_nodes: Set[str] = field(default_factory=set)
    source_nodes: Set[str] = field(default_factory=set)
    ancestor_nodes: Set[str] = field(default_factory=set)
    toi_nodes: Set[str] = field(default_factory=set)
    toi_virtual_containers: List[Dict] = field(default_factory=list)
    element_to_toi_container: Dict[str, int] = field(default_factory=dict)
    scc_virtual_containers: List[Dict] = field(default_factory=list)
    element_to_scc_container: Dict[str, int] = field(default_factory=dict)
    loop_virtual_containers: List[Dict] = field(default_factory=list)
    element_to_loop_container: Dict[str, int] = field(default_factory=dict)
    leaf_virtual_containers: List[Dict] = field(default_factory=list)
    element_to_leaf_container: Dict[str, int] = field(default_factory=dict)
    ndpr_elements: List[str] = field(default_factory=list)
    ndpr_topological_levels: Dict[str, int] = field(default_factory=dict)
    ndpr_connection_graph: Dict[str, List[str]] = field(default_factory=dict)
    element_to_ndpr: Dict[str, str] = field(default_factory=dict)

    def get_max_container_depth(self) -> int:
        """
        Calcula la profundidad máxima de anidamiento de contenedores.

        Incluye TOI VCs como profundidad 0 (se expanden en la primera iteración).
        Si no hay containers ni VCs, retorna 0.

        Returns:
            int: Profundidad máxima de anidamiento
        """
        max_depth = 0

        # Considerar contenedores reales
        for elem_id, node in self.element_tree.items():
            if node['is_container'] and node['parent'] is None:
                # Contenedor de nivel superior: depth 0
                # Sus hijos containers añaden profundidad
                depth = self._get_container_nesting_depth(elem_id)
                max_depth = max(max_depth, depth)

        # VCs sintéticos cuentan como depth 0 (se expanden junto con containers nivel 0)
        all_vcs = (self.toi_virtual_containers + self.scc_virtual_containers +
                   self.loop_virtual_containers + self.leaf_virtual_containers)
        if all_vcs:
            max_depth = max(max_depth, 0)

        return max_depth

    # Prefijos de contenedores virtuales sintéticos
    VC_PREFIXES = ('_toi_vc_', '_scc_vc_', '_loop_vc_', '_leaf_vc_')

    @staticmethod
    def is_virtual_container(node_id: str) -> bool:
        """Verifica si un ID corresponde a un contenedor virtual sintético."""
        return any(node_id.startswith(p) for p in StructureInfo.VC_PREFIXES)

    def get_vc_members(self, vc_id: str) -> set:
        """Obtiene los miembros de un contenedor virtual por su ID."""
        for vc_list in (self.scc_virtual_containers, self.toi_virtual_containers,
                        self.loop_virtual_containers, self.leaf_virtual_containers):
            for vc in vc_list:
                if vc['id'] == vc_id:
                    return set(vc['members'])
        return set()

    def _get_container_nesting_depth(self, container_id: str) -> int:
        """Calcula profundidad de anidamiento de un contenedor (recursivo)."""
        children = self.element_tree[container_id]['children']
        max_child_depth = 0
        for child_id in children:
            if self.element_tree[child_id]['is_container']:
                max_child_depth = max(
                    max_child_depth,
                    1 + self._get_container_nesting_depth(child_id)
                )
        return max_child_depth

    @staticmethod
    def calculate_accessibility_scores_for_graph(
        elements, connection_graph, incoming_graph, topological_levels,
        alpha=0.03, beta=0.01, gamma=0.0, max_score=0.99
    ):
        """
        Calcula accessibility scores para un grafo arbitrario (parcial o completo).

        Misma fórmula que _calculate_accessibility_scores pero standalone.

        Returns:
            Dict[str, float]: {elem_id: score}
        """
        scores = {}
        for elem_id in elements:
            base_v = topological_levels.get(elem_id, 0)

            # W_hijos: outdegree - 1
            outdeg = len(connection_graph.get(elem_id, []))
            w_hijos = max(0, outdeg - 1) * beta

            # W_precedence: padres desde niveles lejanos
            w_precedence = 0.0
            parents = incoming_graph.get(elem_id, [])
            if parents:
                parent_bases = [topological_levels.get(p, 0) for p in parents]
                max_base_parent = max(parent_bases)
                for p in parents:
                    base_p = topological_levels.get(p, 0)
                    if base_p < max_base_parent:
                        dist = base_v - base_p
                        w_precedence += dist * alpha

            # W_fanin
            w_fanin = 0.0
            if gamma > 0 and parents:
                w_fanin = max(0, len(parents) - 1) * gamma

            scores[elem_id] = min(max_score, w_hijos + w_precedence + w_fanin)

        return scores

    def get_expandable_ndpr(self) -> List[str]:
        """
        Retorna lista de NdDp IDs que son VCs o containers con hijos.

        Orden: mismo de ndpr_elements (ya ordenado por centralidad).
        Excluye nodos simples que no necesitan expansión.
        """
        expandable = []
        for ndpr_id in self.ndpr_elements:
            if StructureInfo.is_virtual_container(ndpr_id):
                expandable.append(ndpr_id)
            else:
                node = self.element_tree.get(ndpr_id, {})
                if node.get('is_container') and node.get('children'):
                    expandable.append(ndpr_id)
        return expandable

    def build_graph_with_expanded(self, expanded_ids: Set[str]) -> 'PartialGraph':
        """
        Construye un grafo parcialmente expandido controlado por conjunto explícito.

        NdDp en expanded_ids → expandir miembros/hijos
        NdDp NO en expanded_ids → mantener colapsado con tamaño estimado
        Nodos simples → siempre visibles

        Args:
            expanded_ids: Conjunto de NdDp IDs a expandir

        Returns:
            PartialGraph con elementos parciales, conexiones y tamaños colapsados
        """
        partial_elements = []
        collapsed_sizes = {}
        element_to_partial = {}

        horizontal_offset = 0.4

        for ndpr_id in self.ndpr_elements:
            is_vc = StructureInfo.is_virtual_container(ndpr_id)

            if is_vc:
                members = self.get_vc_members(ndpr_id)
                if ndpr_id in expanded_ids:
                    # Expandir VC: mostrar sus miembros
                    for member_id in sorted(members):
                        partial_elements.append(member_id)
                        element_to_partial[member_id] = member_id
                        # Miembros container siguen colapsados
                        node = self.element_tree.get(member_id, {})
                        if node.get('is_container') and node.get('children'):
                            n_children = len(node['children'])
                            collapsed_sizes[member_id] = n_children * horizontal_offset
                else:
                    # VC colapsado
                    partial_elements.append(ndpr_id)
                    element_to_partial[ndpr_id] = ndpr_id
                    collapsed_sizes[ndpr_id] = len(members) * horizontal_offset
            else:
                node = self.element_tree.get(ndpr_id, {})
                is_container = node.get('is_container', False)

                if not is_container:
                    # Nodo simple: siempre visible
                    partial_elements.append(ndpr_id)
                    element_to_partial[ndpr_id] = ndpr_id
                else:
                    # Container real
                    partial_elements.append(ndpr_id)
                    element_to_partial[ndpr_id] = ndpr_id

                    if ndpr_id in expanded_ids:
                        # Expandir hijos del container
                        children = node.get('children', [])
                        for child_id in children:
                            partial_elements.append(child_id)
                            element_to_partial[child_id] = child_id
                            child_node = self.element_tree.get(child_id, {})
                            if child_node.get('is_container') and child_node.get('children'):
                                n_children = len(child_node['children'])
                                collapsed_sizes[child_id] = n_children * horizontal_offset
                    else:
                        # Container colapsado
                        n_children = len(node.get('children', []))
                        if n_children > 0:
                            collapsed_sizes[ndpr_id] = n_children * horizontal_offset

        # Build connection graph for partial elements
        partial_set = set(partial_elements)
        partial_connection_graph = {}
        for elem_id in partial_elements:
            partial_connection_graph[elem_id] = []

        # Map all real elements to their visible representative
        elem_to_visible = {}
        for elem_id in self.element_tree:
            if elem_id in partial_set:
                elem_to_visible[elem_id] = elem_id
            else:
                current = elem_id
                while current and current not in partial_set:
                    parent = self.element_tree.get(current, {}).get('parent')
                    if parent is None:
                        ndpr = self.element_to_ndpr.get(current)
                        if ndpr and ndpr in partial_set:
                            current = ndpr
                        else:
                            current = None
                        break
                    current = parent
                if current and current in partial_set:
                    elem_to_visible[elem_id] = current

        # Build connections between visible elements
        seen_edges = set()
        for from_id, to_list in self.connection_graph.items():
            vis_from = elem_to_visible.get(from_id)
            if not vis_from:
                continue
            for to_id in to_list:
                vis_to = elem_to_visible.get(to_id)
                if not vis_to or vis_from == vis_to:
                    continue
                edge = (vis_from, vis_to)
                if edge not in seen_edges:
                    seen_edges.add(edge)
                    if vis_from in partial_connection_graph:
                        partial_connection_graph[vis_from].append(vis_to)

        return self._build_partial_graph(
            partial_elements, partial_connection_graph, collapsed_sizes
        )

    def build_graph_at_depth(self, depth: int) -> 'PartialGraph':
        """
        Construye un grafo parcialmente expandido para una profundidad dada.

        - Profundidad <= depth: NdDp expandidos a elementos reales visibles
        - Profundidad > depth: NdDp aún colapsados con tamaño estimado

        Args:
            depth: Nivel de profundidad a expandir (0 = expandir containers
                   de nivel superior y VCs)

        Returns:
            PartialGraph con elementos parciales, conexiones y tamaños colapsados
        """
        partial_elements = []
        collapsed_sizes = {}
        element_to_partial = {}  # maps real elem_id -> partial node id

        # Horizontal offset en unidades abstractas (misma escala que _expand_ndpr)
        horizontal_offset = 0.4

        for ndpr_id in self.ndpr_elements:
            # Check if this NdDp is a virtual container
            is_vc = StructureInfo.is_virtual_container(ndpr_id)

            if is_vc:
                members = self.get_vc_members(ndpr_id)
                # VCs always expand at depth 0
                if depth >= 0:
                    for member_id in sorted(members):
                        partial_elements.append(member_id)
                        element_to_partial[member_id] = member_id
                        # Check if member is a container that needs collapsing
                        node = self.element_tree.get(member_id, {})
                        if node.get('is_container') and node.get('children'):
                            child_depth = self._get_container_nesting_depth(member_id)
                            if child_depth > depth:
                                # Still collapsed: estimate size
                                n_children = len(node['children'])
                                collapsed_sizes[member_id] = n_children * horizontal_offset
                else:
                    partial_elements.append(ndpr_id)
                    element_to_partial[ndpr_id] = ndpr_id
                    collapsed_sizes[ndpr_id] = len(members) * horizontal_offset
            else:
                # Regular NdDp (simple or real container)
                node = self.element_tree.get(ndpr_id, {})
                is_container = node.get('is_container', False)

                if not is_container:
                    # Simple node: always visible
                    partial_elements.append(ndpr_id)
                    element_to_partial[ndpr_id] = ndpr_id
                else:
                    # Real container
                    partial_elements.append(ndpr_id)
                    element_to_partial[ndpr_id] = ndpr_id

                    if depth >= 0:
                        # Expand children at this depth
                        self._expand_container_at_depth(
                            ndpr_id, depth, 0, partial_elements,
                            collapsed_sizes, element_to_partial, horizontal_offset
                        )
                    else:
                        # Still collapsed
                        n_children = len(node.get('children', []))
                        if n_children > 0:
                            collapsed_sizes[ndpr_id] = n_children * horizontal_offset

        # Build connection graph for partial elements
        partial_set = set(partial_elements)
        partial_connection_graph = {}
        for elem_id in partial_elements:
            partial_connection_graph[elem_id] = []

        # Map all real elements to their visible representative
        elem_to_visible = {}
        for elem_id in self.element_tree:
            if elem_id in partial_set:
                elem_to_visible[elem_id] = elem_id
            else:
                # Find nearest visible ancestor
                current = elem_id
                while current and current not in partial_set:
                    parent = self.element_tree.get(current, {}).get('parent')
                    if parent is None:
                        # Try NdDp mapping
                        ndpr = self.element_to_ndpr.get(current)
                        if ndpr and ndpr in partial_set:
                            current = ndpr
                        else:
                            current = None
                        break
                    current = parent
                if current and current in partial_set:
                    elem_to_visible[elem_id] = current

        # Build connections between visible elements
        seen_edges = set()
        for from_id, to_list in self.connection_graph.items():
            vis_from = elem_to_visible.get(from_id)
            if not vis_from:
                continue
            for to_id in to_list:
                vis_to = elem_to_visible.get(to_id)
                if not vis_to or vis_from == vis_to:
                    continue
                edge = (vis_from, vis_to)
                if edge not in seen_edges:
                    seen_edges.add(edge)
                    if vis_from in partial_connection_graph:
                        partial_connection_graph[vis_from].append(vis_to)

        return self._build_partial_graph(
            partial_elements, partial_connection_graph, collapsed_sizes
        )

    def _expand_container_at_depth(
        self, container_id: str, target_depth: int, current_depth: int,
        partial_elements: list, collapsed_sizes: dict,
        element_to_partial: dict, horizontal_offset: float
    ) -> None:
        """
        Expande recursivamente hijos de un contenedor hasta target_depth.
        """
        children = self.element_tree[container_id].get('children', [])
        for child_id in children:
            child_node = self.element_tree.get(child_id, {})
            partial_elements.append(child_id)
            element_to_partial[child_id] = child_id

            if child_node.get('is_container') and child_node.get('children'):
                if current_depth < target_depth:
                    # Expand deeper
                    self._expand_container_at_depth(
                        child_id, target_depth, current_depth + 1,
                        partial_elements, collapsed_sizes,
                        element_to_partial, horizontal_offset
                    )
                else:
                    # Still collapsed: estimate size
                    n_children = len(child_node['children'])
                    collapsed_sizes[child_id] = n_children * horizontal_offset


    def _build_partial_graph(
        self, partial_elements: list,
        partial_connection_graph: dict, collapsed_sizes: dict
    ) -> 'PartialGraph':
        """
        Finaliza un grafo parcial: calcula niveles topológicos con propagación
        y compactación, y construye el grafo inverso.
        """
        # Seed topological levels from raw/ndpr levels
        partial_topological_levels = {}
        for elem_id in partial_elements:
            if elem_id in self.topological_levels:
                partial_topological_levels[elem_id] = self.topological_levels[elem_id]
            elif elem_id in self.ndpr_topological_levels:
                partial_topological_levels[elem_id] = self.ndpr_topological_levels[elem_id]
            else:
                partial_topological_levels[elem_id] = 0

        # Propagar restricciones: si X→Y, level(Y) >= level(X)+1
        max_iters = len(partial_elements) + 1
        for _ in range(max_iters):
            changed = False
            for src, targets in partial_connection_graph.items():
                for tgt in targets:
                    if partial_topological_levels[tgt] <= partial_topological_levels[src]:
                        partial_topological_levels[tgt] = partial_topological_levels[src] + 1
                        changed = True
            if not changed:
                break

        # Compactar niveles eliminando huecos
        used_levels = sorted(set(partial_topological_levels.values()))
        level_map = {old: new for new, old in enumerate(used_levels)}
        for elem_id in partial_topological_levels:
            partial_topological_levels[elem_id] = level_map[partial_topological_levels[elem_id]]

        # Build incoming (reverse) graph
        partial_incoming_graph = {eid: [] for eid in partial_elements}
        for from_id, to_list in partial_connection_graph.items():
            for to_id in to_list:
                if to_id in partial_incoming_graph and from_id not in partial_incoming_graph[to_id]:
                    partial_incoming_graph[to_id].append(from_id)

        return PartialGraph(
            elements=partial_elements,
            connection_graph=partial_connection_graph,
            topological_levels=partial_topological_levels,
            collapsed_sizes=collapsed_sizes,
            incoming_graph=partial_incoming_graph
        )


@dataclass
class PartialGraph:
    """Grafo parcialmente expandido para una iteración de profundidad."""
    elements: List[str] = field(default_factory=list)
    connection_graph: Dict[str, List[str]] = field(default_factory=dict)
    topological_levels: Dict[str, int] = field(default_factory=dict)
    collapsed_sizes: Dict[str, float] = field(default_factory=dict)
    incoming_graph: Dict[str, List[str]] = field(default_factory=dict)


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

        Pipeline organizado en 5 pasos core + 1 bloque de métricas auxiliares:
        1. _build_element_tree: árbol de elementos y primarios
        2. _build_graphs_and_leaves: grafo conexiones + incoming + hojas
        3. _detect_structural_groups: bottom-up (contenedores → top-level)
        4. _calculate_topological_levels: niveles topológicos (BFS)
        5. _build_ndpr_abstraction: NdDp IDs + grafo abstracto

        Agrupamiento bottom-up por scope (Hojas → Loops → TOIs → SCCs):
        Fase 1: dentro de cada contenedor real
        Fase 2: top-level (contenedores colapsados a nodos)

        Métricas auxiliares (usadas en fases posteriores o debug):
        - container_metrics, accessibility_scores, element_types, connection_sequences

        Args:
            layout: Layout con elements, connections, elements_by_id

        Returns:
            StructureInfo con toda la información estructural
        """
        info = StructureInfo()

        # CORE: Estructura mínima para layout
        self._build_element_tree(layout, info)
        self._build_graphs_and_leaves(layout, info)
        self._detect_structural_groups(info)
        self._calculate_topological_levels(layout, info)
        self._build_ndpr_abstraction(layout, info)

        # MÉTRICAS: Auxiliares para fases posteriores
        self._calculate_auxiliary_metrics(layout, info)

        return info

    def _build_graphs_and_leaves(self, layout, info: StructureInfo) -> None:
        """
        Construye grafos de conexiones (directo e inverso) e identifica hojas.

        Fusiona los pasos:
        - _build_connection_graph: grafo de adyacencia {from: [to_list]}
        - _build_incoming_graph: grafo inverso {to: [from_list]}
        - _identify_leaf_and_terminal_nodes: leaf_nodes, terminal_leaf_nodes

        Args:
            layout: Layout con connections
            info: StructureInfo a poblar
        """
        self._build_connection_graph(layout, info)
        self._build_incoming_graph(info)
        self._identify_leaf_and_terminal_nodes(info)

    def _build_ndpr_abstraction(self, layout, info: StructureInfo) -> None:
        """
        Construye la abstracción NdDp: IDs + grafo abstracto.

        Los agrupamientos (SCCs, Loops, TOIs, Hojas) ya están integrados
        en element_tree por _detect_structural_groups.

        Args:
            layout: Layout con elements
            info: StructureInfo a poblar
        """
        self._classify_primary_nodes(layout, info)
        self._build_ndpr_abstract_graph(info)

    def _calculate_auxiliary_metrics(self, layout, info: StructureInfo) -> None:
        """
        Calcula métricas auxiliares usadas en fases posteriores o debug.

        Agrupa:
        - _calculate_container_metrics: total_icons, max_depth (usado en inflator Fase 8)
        - _calculate_accessibility_scores: scores intra-nivel (recalculado por iteración)
        - _group_elements_by_type: agrupación por tipo (sort heurístico)
        - _generate_connection_sequences: metadata de orden de conexiones

        Args:
            layout: Layout con elements, connections
            info: StructureInfo a poblar
        """
        self._calculate_container_metrics(layout, info)
        self._calculate_accessibility_scores(
            info,
            alpha=self.centrality_alpha,
            beta=self.centrality_beta,
            gamma=self.centrality_gamma,
            max_score=self.centrality_max_score,
        )
        self._group_elements_by_type(layout, info)
        self._generate_connection_sequences(layout, info)

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

        # Identificar elementos primarios (sin padre)
        info.primary_elements = [
            elem_id for elem_id, node in info.element_tree.items()
            if node['parent'] is None
        ]

        # Calcular profundidad de cada nodo (requiere primary_elements)
        self._calculate_depths(info)

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

    # ────────────────────────────────────────────────────────────────────
    #  Detección bottom-up de agrupamientos estructurales
    # ────────────────────────────────────────────────────────────────────

    def _detect_structural_groups(self, info: StructureInfo) -> None:
        """
        Detecta e integra agrupamientos bottom-up en dos fases:

        Fase 1: Dentro de cada contenedor real — analiza conexiones internas
        Fase 2: Top-level — contenedores colapsados como nodos depth-0

        En cada fase se ejecuta: Hojas → Loops → TOIs → SCCs
        """
        # Fase 1: Dentro de cada contenedor real
        containers = [
            eid for eid, node in info.element_tree.items()
            if node['is_container'] and node['children']
        ]
        for container_id in containers:
            children = info.element_tree[container_id]['children']
            if len(children) < 2:
                continue
            scope_nodes = set(children)
            scope_graph, scope_incoming = self._build_scope_graphs(
                scope_nodes, info
            )
            self._run_scope_groupings(
                info, scope_nodes, scope_graph, scope_incoming
            )

        # Fase 2: Top-level (elementos libres + contenedores como nodos)
        top_nodes = set(
            eid for eid in info.primary_elements
            if info.element_tree[eid]['parent'] is None
        )
        self._run_scope_groupings(
            info, top_nodes, info.connection_graph, info.incoming_graph
        )

        # Integrar todos los VCs detectados en element_tree
        self._integrate_all_vcs_into_tree(info)

    def _build_scope_graphs(
        self, scope_nodes: set, info: StructureInfo
    ) -> tuple:
        """
        Construye sub-grafos de conexiones para un scope (subconjunto de nodos).

        Solo incluye aristas donde ambos extremos están en scope_nodes.
        """
        scope_graph = {n: [] for n in scope_nodes}
        scope_incoming = {n: [] for n in scope_nodes}

        for from_id in scope_nodes:
            for to_id in info.connection_graph.get(from_id, []):
                if to_id in scope_nodes:
                    if to_id not in scope_graph[from_id]:
                        scope_graph[from_id].append(to_id)
                    if from_id not in scope_incoming[to_id]:
                        scope_incoming[to_id].append(from_id)

        return scope_graph, scope_incoming

    def _run_scope_groupings(
        self, info: StructureInfo,
        nodes: set, conn_graph: dict, inc_graph: dict
    ) -> None:
        """
        Ejecuta pipeline de agrupamiento en un scope:
        Hojas → Loops → TOIs → SCCs

        Modelo: detectar → comprimir VC en nodo único → siguiente agrupador.
        Cada VC comprimido participa como nodo atómico en las detecciones
        posteriores.
        """
        # Copias de trabajo que se modifican al comprimir
        w_nodes = set(nodes)
        w_conn = {n: list(conn_graph.get(n, [])) for n in nodes}
        w_inc = {n: list(inc_graph.get(n, [])) for n in nodes}

        # 1. Hojas terminales → comprimir
        leaf_vcs = self._detect_leaves_in_scope(info, w_nodes, w_conn, w_inc)
        for vc in leaf_vcs:
            self._compress_vc(vc['id'], vc['members'], w_nodes, w_conn, w_inc)

        # 2. Loops (ciclos simples de 2+ nodos) → comprimir
        sccs = self._tarjan_on_scope(w_nodes, w_conn)
        for scc in sccs:
            if self._is_simple_cycle(scc, w_conn):
                vc = self._create_loop_vc(info, scc)
                self._compress_vc(vc['id'], vc['members'], w_nodes, w_conn, w_inc)

        # 3. TOIs → comprimir (iterativo: detectar menor, comprimir, re-detectar)
        #    Así TOIs pequeños se comprimen primero y TOIs grandes los absorben.
        while True:
            toi_vcs = self._detect_tois_in_scope(info, w_nodes, w_conn, w_inc)
            if not toi_vcs:
                break
            # Solo comprimir el primero (ya ordenado de menor a mayor)
            vc = toi_vcs[0]
            self._compress_vc(vc['id'], vc['members'], w_nodes, w_conn, w_inc)

        # 4. SCCs (componentes fuertemente conexos complejos, no ciclos simples)
        sccs = self._tarjan_on_scope(w_nodes, w_conn)
        for scc in sccs:
            idx = len(info.scc_virtual_containers)
            vc_id = f'_scc_vc_{idx}'
            info.scc_virtual_containers.append({
                'id': vc_id,
                'members': set(scc),
            })
            for mid in scc:
                info.element_to_scc_container[mid] = idx

        # 5. Segunda pasada de hojas (post-compresión: nodos que quedaron
        #    como hojas terminales después de comprimir loops/TOIs/SCCs)
        leaf_vcs2 = self._detect_leaves_in_scope(info, w_nodes, w_conn, w_inc)
        for vc in leaf_vcs2:
            self._compress_vc(vc['id'], vc['members'], w_nodes, w_conn, w_inc)

    @staticmethod
    def _compress_vc(
        vc_id: str, members: set,
        w_nodes: set, w_conn: dict, w_inc: dict
    ) -> None:
        """
        Comprime un VC en un nodo único dentro del grafo de trabajo.

        - Reemplaza todos los miembros por vc_id en w_nodes
        - Redirige aristas externas al nodo VC
        - Elimina aristas internas (entre miembros)
        """
        # Recopilar aristas externas
        external_out = set()
        external_in = set()
        for mid in members:
            for target in w_conn.get(mid, []):
                if target not in members:
                    external_out.add(target)
            for source in w_inc.get(mid, []):
                if source not in members:
                    external_in.add(source)

        # Eliminar miembros del grafo
        for mid in members:
            w_nodes.discard(mid)
            w_conn.pop(mid, None)
            w_inc.pop(mid, None)
            # Limpiar referencias desde nodos externos
            for target in list(external_out):
                if target in w_inc:
                    w_inc[target] = [s for s in w_inc[target] if s not in members]
            for source in list(external_in):
                if source in w_conn:
                    w_conn[source] = [t for t in w_conn[source] if t not in members]

        # Insertar nodo VC
        w_nodes.add(vc_id)
        w_conn[vc_id] = list(external_out)
        w_inc[vc_id] = list(external_in)

        # Conectar nodos externos al VC
        for source in external_in:
            if source in w_conn and vc_id not in w_conn[source]:
                w_conn[source].append(vc_id)
        for target in external_out:
            if target in w_inc and vc_id not in w_inc[target]:
                w_inc[target].append(vc_id)

    @staticmethod
    def _is_simple_cycle(scc: set, conn_graph: dict) -> bool:
        """
        Verifica si un SCC es un ciclo simple: cada nodo tiene exactamente
        un sucesor y un predecesor dentro del SCC.
        """
        for node in scc:
            out_in_scc = [t for t in conn_graph.get(node, []) if t in scc]
            if len(out_in_scc) != 1:
                return False
        return True

    def _create_loop_vc(self, info: StructureInfo, members: set) -> dict:
        """Crea un VC de tipo Loop y lo registra en info."""
        idx = len(info.loop_virtual_containers)
        vc_id = f'_loop_vc_{idx}'
        vc = {
            'id': vc_id,
            'members': set(members),
        }
        info.loop_virtual_containers.append(vc)
        for mid in members:
            info.element_to_loop_container[mid] = idx
        return vc

    # ── Algoritmos por scope ──────────────────────────────────────────

    @staticmethod
    def _tarjan_on_scope(nodes: set, conn_graph: dict) -> list:
        """
        Ejecuta Tarjan sobre un scope y retorna SCCs de 2+ nodos.
        """
        index_counter = [0]
        stack = []
        on_stack = set()
        indices = {}
        lowlinks = {}
        all_sccs = []

        def strongconnect(v):
            indices[v] = index_counter[0]
            lowlinks[v] = index_counter[0]
            index_counter[0] += 1
            stack.append(v)
            on_stack.add(v)

            for w in conn_graph.get(v, []):
                if w not in nodes:
                    continue
                if w not in indices:
                    strongconnect(w)
                    lowlinks[v] = min(lowlinks[v], lowlinks[w])
                elif w in on_stack:
                    lowlinks[v] = min(lowlinks[v], indices[w])

            if lowlinks[v] == indices[v]:
                scc = set()
                while True:
                    w = stack.pop()
                    on_stack.discard(w)
                    scc.add(w)
                    if w == v:
                        break
                if len(scc) >= 2:
                    all_sccs.append(scc)

        for elem_id in nodes:
            if elem_id not in indices:
                strongconnect(elem_id)

        return all_sccs

    def _detect_leaves_in_scope(
        self, info: StructureInfo,
        nodes: set, conn_graph: dict, inc_graph: dict
    ) -> list:
        """
        Detecta y agrupa hojas terminales dentro de un scope.

        Una hoja es un nodo sin conexiones salientes dentro del scope.
        Una hoja terminal: todos los hermanos de sus padres son también hojas.

        Se agrupan 2+ hojas terminales hermanas (mismo padre) en un leaf VC.

        Retorna lista de VCs creados para compresión posterior.
        """
        created_vcs = []

        # Identificar hojas en el scope
        scope_leaves = set()
        for nid in nodes:
            out_in_scope = [t for t in conn_graph.get(nid, []) if t in nodes]
            if not out_in_scope:
                scope_leaves.add(nid)

        if not scope_leaves:
            return created_vcs

        # Identificar hojas terminales
        terminal = set()
        for leaf_id in scope_leaves:
            preds = [p for p in inc_graph.get(leaf_id, []) if p in nodes]
            if not preds:
                terminal.add(leaf_id)
                continue
            is_terminal = True
            for pred_id in preds:
                siblings = [s for s in conn_graph.get(pred_id, [])
                            if s in nodes and s != leaf_id]
                for sib in siblings:
                    if sib not in scope_leaves:
                        is_terminal = False
                        break
                if not is_terminal:
                    break
            if is_terminal:
                terminal.add(leaf_id)

        # Agrupar por padre común (2+ hojas terminales)
        parent_to_leaves = {}
        for leaf_id in terminal:
            preds = [p for p in inc_graph.get(leaf_id, []) if p in nodes]
            for pred_id in preds:
                if pred_id not in parent_to_leaves:
                    parent_to_leaves[pred_id] = []
                parent_to_leaves[pred_id].append(leaf_id)

        claimed = set()
        for parent_id, leaves in parent_to_leaves.items():
            unclaimed_leaves = [l for l in leaves if l not in claimed]
            if len(unclaimed_leaves) < 2:
                continue
            idx = len(info.leaf_virtual_containers)
            vc_id = f'_leaf_vc_{idx}'
            members = set(unclaimed_leaves)
            vc = {
                'id': vc_id,
                'members': members,
                'parent_id': parent_id,
            }
            info.leaf_virtual_containers.append(vc)
            for lid in members:
                info.element_to_leaf_container[lid] = idx
            claimed |= members
            created_vcs.append(vc)

        return created_vcs

    def _detect_tois_in_scope(
        self, info: StructureInfo,
        nodes: set, conn_graph: dict, inc_graph: dict
    ) -> list:
        """
        Detecta TOIs dentro de un scope.

        Nodos origen = sin incoming dentro del scope.
        Ancestros = origen con más descendientes. TOIs = los demás.

        Retorna lista de VCs creados para compresión posterior.
        """
        created_vcs = []

        # Nodos origen en el scope
        source_nodes = set()
        for nid in nodes:
            inc_in_scope = [p for p in inc_graph.get(nid, []) if p in nodes]
            if not inc_in_scope:
                source_nodes.add(nid)

        if len(source_nodes) <= 1:
            return created_vcs

        # Contar descendientes por BFS dentro del scope
        def count_desc(start):
            visited = set()
            queue = [start]
            while queue:
                n = queue.pop()
                if n in visited:
                    continue
                visited.add(n)
                for nb in conn_graph.get(n, []):
                    if nb in nodes and nb not in visited:
                        queue.append(nb)
            return len(visited) - 1

        def get_all_desc(start):
            visited = set()
            queue = [start]
            while queue:
                n = queue.pop()
                if n in visited:
                    continue
                visited.add(n)
                for nb in conn_graph.get(n, []):
                    if nb in nodes and nb not in visited:
                        queue.append(nb)
            visited.discard(start)
            return visited

        desc_counts = {eid: count_desc(eid) for eid in source_nodes}
        max_desc = max(desc_counts.values())

        ancestor_nodes = {
            eid for eid in source_nodes if desc_counts[eid] == max_desc
        }
        toi_nodes = source_nodes - ancestor_nodes

        if not toi_nodes:
            return created_vcs

        # Registrar en info para clasificación
        info.source_nodes |= source_nodes
        info.ancestor_nodes |= ancestor_nodes
        info.toi_nodes |= toi_nodes

        # Crear VCs: TOI + descendientes + co-padres de hijos directos
        # Ordenar TOIs de menor a mayor por descendientes (el más pequeño forma
        # su VC primero y se comprime; TOIs más grandes lo absorben naturalmente)
        sorted_tois = sorted(toi_nodes, key=lambda t: count_desc(t))
        claimed = set()
        for toi_id in sorted_tois:
            if toi_id in claimed:
                continue
            # Descendientes del TOI (BFS forward)
            descendants = get_all_desc(toi_id)
            # Co-padres: padres de los hijos directos del TOI source
            # (excluir ancestros y el propio TOI)
            toi_children = [t for t in conn_graph.get(toi_id, []) if t in nodes]
            co_parents = set()
            for child_id in toi_children:
                for parent_id in inc_graph.get(child_id, []):
                    if (parent_id in nodes
                            and parent_id not in ancestor_nodes
                            and parent_id != toi_id
                            and parent_id not in descendants):
                        co_parents.add(parent_id)
            members = ({toi_id} | descendants | co_parents) - claimed

            if len(members) < 2:
                continue

            container_idx = len(info.toi_virtual_containers)
            vc = {
                'id': f'_toi_vc_{container_idx}',
                'toi_id': toi_id,
                'members': members,
            }
            info.toi_virtual_containers.append(vc)
            for mid in members:
                info.element_to_toi_container[mid] = container_idx
            # Retornar solo el primer (menor) VC para compresión iterativa
            return [vc]

        return created_vcs

    # ── Integración genérica de VCs ──────────────────────────────────

    def _integrate_all_vcs_into_tree(self, info: StructureInfo) -> None:
        """
        Integra todos los VCs detectados en element_tree.

        Orden: SCCs → Loops → TOIs → Hojas (no importa, cada uno
        reclama solo nodos sin padre asignado).
        """
        all_vcs = (info.scc_virtual_containers +
                   info.loop_virtual_containers +
                   info.toi_virtual_containers +
                   info.leaf_virtual_containers)
        self._integrate_vc_list_into_tree(info, all_vcs)

    def _integrate_vc_list_into_tree(
        self, info: StructureInfo, vc_list: list
    ) -> None:
        """
        Integra una lista de VCs en el element_tree (patrón genérico).

        Solo reclama miembros que aún no tienen padre VC asignado.
        Recalcula profundidades tras la integración.
        """
        if not vc_list:
            return

        for vc in vc_list:
            vc_id = vc['id']
            actual_children = []

            for member_id in vc['members']:
                if member_id in info.element_tree:
                    current_parent = info.element_tree[member_id]['parent']
                    if current_parent is None or current_parent == vc_id:
                        info.element_tree[member_id]['parent'] = vc_id
                        if member_id not in actual_children:
                            actual_children.append(member_id)

            info.element_tree[vc_id] = {
                'parent': None,
                'children': actual_children,
                'depth': 0,
                'is_container': True
            }

        # Recalcular profundidades desde raíces
        def set_depth(elem_id, depth):
            info.element_tree[elem_id]['depth'] = depth
            for child_id in info.element_tree[elem_id]['children']:
                set_depth(child_id, depth + 1)

        for elem_id, node in info.element_tree.items():
            if node['parent'] is None:
                set_depth(elem_id, 0)

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

    def _classify_primary_nodes(self, layout, info: StructureInfo) -> None:
        """
        Asigna IDs NdDp (Node Depth) y clasifica cada nodo.

        Formato: NdDp{depth_level:02d}-{seq:03d}
        - depth_level = depth + 1 (depth 0 → NdDp01, depth 1 → NdDp02, etc.)
        - seq = contador secuencial dentro de cada nivel de profundidad

        primary_node_ids: solo nodos abstractos (depth 0 + TOI VCs)
        all_node_ids: TODOS los elementos a cualquier profundidad

        Tipos de nodo:
        - Simple: Nodo sin hijos, no contenido en ningún contenedor
        - Contenedor: Nodo que contiene otros elementos (real)
        - Contenedor Virtual: Nodo parte de un ciclo detectado (legacy)
        - Contenedor Virtual SCC: SCC de 3+ nodos (Strongly Connected Component)
        - Contenedor Virtual Loop: Ciclo mutuo de 2 nodos
        - Contenedor Virtual TOI: Contenedor virtual generado por detección TOI
        - Contenedor Virtual Leaf: Agrupación de hojas terminales
        - TOI: Nodo origen que no es ancestro (contenido en su VC TOI)

        Args:
            layout: Layout con elements
            info: StructureInfo a poblar
        """
        from collections import defaultdict

        # Detectar nodos sin nivel topológico (posibles ciclos)
        nodes_without_level = set()
        for elem_id in info.primary_elements:
            if elem_id not in info.topological_levels:
                nodes_without_level.add(elem_id)

        # Build set of elements that are inside any container (real or virtual)
        # so they don't get their own primary_node_id (abstract view)
        contained_elements = set()

        # Elements inside real containers
        for elem_id in info.primary_elements:
            if info.element_tree[elem_id]['parent'] is not None:
                contained_elements.add(elem_id)

        # Elements inside any virtual container (SCC, Loop, TOI, Leaf)
        all_vc_lists = [
            info.scc_virtual_containers, info.loop_virtual_containers,
            info.toi_virtual_containers, info.leaf_virtual_containers,
        ]
        for vc_list in all_vc_lists:
            for vc in vc_list:
                for member_id in vc['members']:
                    contained_elements.add(member_id)

        # Determine which VCs are nested (inside real container or another VC)
        nested_vcs = set()
        # VCs anidados en contenedores reales
        for vc_list in all_vc_lists:
            for vc in vc_list:
                for member_id in vc['members']:
                    tree_node = info.element_tree.get(member_id, {})
                    parent = tree_node.get('parent')
                    if parent is not None and not StructureInfo.is_virtual_container(str(parent)):
                        nested_vcs.add(vc['id'])
                        break
        # VCs que son miembros de otro VC
        all_vc_members = {}
        for vc_list in all_vc_lists:
            for vc in vc_list:
                for member_id in vc['members']:
                    if StructureInfo.is_virtual_container(member_id):
                        nested_vcs.add(member_id)

        # Contadores por nivel de profundidad
        depth_counters = defaultdict(int)

        # Pass 1: Assign NdDp to depth-0 elements (abstract view → primary_node_ids)
        for elem_id in info.primary_elements:
            if elem_id in contained_elements:
                # Classify but don't assign primary_node_id
                if elem_id in info.toi_nodes:
                    info.primary_node_types[elem_id] = "TOI"
                elif elem_id in info.element_to_scc_container:
                    info.primary_node_types[elem_id] = "SCC"
                elif elem_id in info.element_to_loop_container:
                    info.primary_node_types[elem_id] = "Loop"
                elif elem_id in info.element_to_toi_container:
                    info.primary_node_types[elem_id] = "TOI Virtual"
                elif elem_id in info.element_to_leaf_container:
                    info.primary_node_types[elem_id] = "Leaf"
                else:
                    info.primary_node_types[elem_id] = "Simple"
                continue

            # Assign NdDp01 ID (depth 0 → level 1)
            depth_counters[1] += 1
            node_id = f"NdDp01-{depth_counters[1]:03d}"
            info.primary_node_ids[elem_id] = node_id

            # Classify
            if elem_id in nodes_without_level:
                node_type = "Contenedor Virtual"
            elif info.element_tree[elem_id]['is_container']:
                node_type = "Contenedor"
            else:
                node_type = "Simple"

            info.primary_node_types[elem_id] = node_type

        # Assign NdDp01 IDs to all virtual containers (unless nested)
        vc_type_map = [
            (info.scc_virtual_containers, "Contenedor Virtual SCC"),
            (info.loop_virtual_containers, "Contenedor Virtual Loop"),
            (info.toi_virtual_containers, "Contenedor Virtual TOI"),
            (info.leaf_virtual_containers, "Contenedor Virtual Leaf"),
        ]
        for vc_list, vc_type_label in vc_type_map:
            for vc in vc_list:
                if vc['id'] in nested_vcs:
                    continue
                depth_counters[1] += 1
                node_id = f"NdDp01-{depth_counters[1]:03d}"
                info.primary_node_ids[vc['id']] = node_id
                info.primary_node_types[vc['id']] = vc_type_label

        # Pass 2: Assign NdDp to ALL elements (all_node_ids)
        # Depth-0 elements already have their IDs from primary_node_ids
        for elem_id, node_id in info.primary_node_ids.items():
            info.all_node_ids[elem_id] = node_id

        # Assign NdDp to contained elements (depth 1+)
        # Also assign to TOI/TOI Virtual elements at depth 0 that don't have primary IDs
        for elem_id, node_data in info.element_tree.items():
            if elem_id in info.all_node_ids:
                continue
            depth = node_data['depth']
            depth_level = depth + 1
            depth_counters[depth_level] += 1
            node_id = f"NdDp{depth_level:02d}-{depth_counters[depth_level]:03d}"
            info.all_node_ids[elem_id] = node_id

            # Classify if not already classified
            if elem_id not in info.primary_node_types:
                if node_data['is_container']:
                    info.primary_node_types[elem_id] = "Contenedor"
                else:
                    info.primary_node_types[elem_id] = "Simple"

    def _build_ndpr_abstract_graph(self, info: StructureInfo) -> None:
        """
        Build abstract NdDp01-only view: collapsed levels and connection graph.

        Maps every element to its NdDp01 representative:
        - Elements with their own NdDp01 → themselves
        - Elements inside any VC (SCC/Loop/TOI/Leaf) → the VC's id
        - Elements inside a real container → the container's id

        Then builds:
        - ndpr_elements: ordered list of NdDp01 node IDs
        - ndpr_topological_levels: level for each NdDp01 node
        - ndpr_connection_graph: connections between NdDp01 nodes (no self-loops)
        """
        # Mapa de elemento → VC id (todos los tipos de VC)
        elem_to_vc_id = {}
        vc_mappings = [
            (info.element_to_scc_container, info.scc_virtual_containers),
            (info.element_to_loop_container, info.loop_virtual_containers),
            (info.element_to_toi_container, info.toi_virtual_containers),
            (info.element_to_leaf_container, info.leaf_virtual_containers),
        ]
        for elem_map, vc_list in vc_mappings:
            for elem_id, vc_idx in elem_map.items():
                if elem_id not in elem_to_vc_id:
                    elem_to_vc_id[elem_id] = vc_list[vc_idx]['id']

        # Resolver VCs anidados: si un VC es miembro de otro VC,
        # sus elementos deben mapearse al VC más externo con NdDp01
        def resolve_vc(vc_id):
            while vc_id in elem_to_vc_id:
                vc_id = elem_to_vc_id[vc_id]
            return vc_id

        for elem_id in list(elem_to_vc_id):
            elem_to_vc_id[elem_id] = resolve_vc(elem_to_vc_id[elem_id])

        # 1. Map every element to its abstract representative
        for elem_id in info.primary_elements:
            if elem_id in info.primary_node_ids:
                info.element_to_ndpr[elem_id] = elem_id
            elif elem_id in elem_to_vc_id:
                info.element_to_ndpr[elem_id] = elem_to_vc_id[elem_id]
            else:
                # Inside a real container - find parent with NdDp01
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

        # 2. Build ndpr_elements list (ordered by NdDp ID)
        info.ndpr_elements = sorted(
            info.primary_node_ids.keys(),
            key=lambda eid: info.primary_node_ids[eid]
        )

        # 3. Assign levels to NdDp nodes
        #    Paso 1: niveles iniciales
        for ndpr_id in info.ndpr_elements:
            if StructureInfo.is_virtual_container(ndpr_id):
                # VC level = min level de miembros reales (no VCs anidados)
                members = info.get_vc_members(ndpr_id)
                member_levels = [
                    info.topological_levels[m]
                    for m in members
                    if m in info.topological_levels
                ]
                info.ndpr_topological_levels[ndpr_id] = min(member_levels) if member_levels else 0
            else:
                info.ndpr_topological_levels[ndpr_id] = info.topological_levels.get(ndpr_id, 0)

        # 4. Build abstract connection graph between NdDp nodes
        for ndpr_id in info.ndpr_elements:
            info.ndpr_connection_graph[ndpr_id] = []

        seen_edges = set()
        for from_id, to_list in info.connection_graph.items():
            ndpr_from = info.element_to_ndpr.get(from_id, from_id)
            for to_id in to_list:
                ndpr_to = info.element_to_ndpr.get(to_id, to_id)
                # Skip self-loops (internal connections within same NdDp01)
                if ndpr_from == ndpr_to:
                    continue
                edge = (ndpr_from, ndpr_to)
                if edge not in seen_edges:
                    seen_edges.add(edge)
                    if ndpr_from in info.ndpr_connection_graph:
                        info.ndpr_connection_graph[ndpr_from].append(ndpr_to)

        # 5. Propagar restricciones — si X→Y, level(Y) >= level(X)+1
        #    Max iteraciones = N nodos (en DAG converge en N pasos)
        max_iters = len(info.ndpr_elements) + 1
        for _ in range(max_iters):
            changed = False
            for src, targets in info.ndpr_connection_graph.items():
                for tgt in targets:
                    if info.ndpr_topological_levels[tgt] <= info.ndpr_topological_levels[src]:
                        info.ndpr_topological_levels[tgt] = info.ndpr_topological_levels[src] + 1
                        changed = True
            if not changed:
                break

        # 6. Compactar niveles eliminando huecos
        used_levels = sorted(set(info.ndpr_topological_levels.values()))
        level_map = {old: new for new, old in enumerate(used_levels)}
        for ndpr_id in info.ndpr_topological_levels:
            info.ndpr_topological_levels[ndpr_id] = level_map[info.ndpr_topological_levels[ndpr_id]]

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
