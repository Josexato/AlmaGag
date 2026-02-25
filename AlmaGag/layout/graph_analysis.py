"""
GraphAnalyzer - Análisis de estructura del grafo

Este módulo es stateless y proporciona métodos para analizar la estructura
del grafo de elementos y conexiones:
- Construcción de grafo de adyacencia
- Cálculo de niveles (filas lógicas)
- Identificación de grupos conectados (DFS)
- Cálculo de prioridades automáticas
"""

from typing import Dict, List
from AlmaGag.utils import extract_item_id


class GraphAnalyzer:
    """
    Analizador de estructura del grafo de diagramas.

    Esta clase es stateless - todos los métodos toman los datos necesarios
    como argumentos y retornan resultados sin efectos secundarios.
    """

    PRIORITY_ORDER = {'high': 0, 'normal': 1, 'low': 2}

    def build_graph(
        self,
        elements: List[dict],
        connections: List[dict]
    ) -> Dict[str, List[str]]:
        """
        Construye grafo de adyacencia desde connections.

        Args:
            elements: Lista de elementos del diagrama
            connections: Lista de conexiones

        Returns:
            Dict[str, List[str]]: {element_id: [connected_ids]}
        """
        graph = {e['id']: [] for e in elements}

        for conn in connections:
            from_id = conn['from']
            to_id = conn['to']
            if from_id in graph:
                graph[from_id].append(to_id)
            if to_id in graph:
                graph[to_id].append(from_id)

        return graph

    def calculate_topological_levels(
        self,
        elements: List[dict],
        connections: List[dict]
    ) -> Dict[str, int]:
        """
        Calcula niveles basándose en la topología del grafo (jerarquía).

        Usa longest-path BFS: cada nodo se asigna al máximo nivel alcanzable
        desde cualquier raíz. Incluye correcciones para hojas y fixpoint
        para nodos no-hoja.

        Args:
            elements: Lista de elementos del diagrama (pueden ser elementos primarios)
            connections: Lista de conexiones direccionales

        Returns:
            Dict[str, int]: {element_id: level_number}
        """
        elem_ids = {e['id'] for e in elements}

        # Construir grafo direccional
        outgoing = {e['id']: [] for e in elements}
        incoming = {e['id']: [] for e in elements}

        for conn in connections:
            from_id = conn['from']
            to_id = conn['to']
            if from_id in elem_ids and to_id in elem_ids:
                outgoing[from_id].append(to_id)
                incoming[to_id].append(from_id)

        # Encontrar raíces (sin incoming edges)
        roots = [e_id for e_id in elem_ids if len(incoming[e_id]) == 0]

        if not roots:
            roots = [max(outgoing, key=lambda k: len(outgoing[k]))] if outgoing else []

        # Longest-path assignment: propagate levels iteratively
        # Capped at N iterations to handle cycles safely
        levels = {e_id: 0 for e_id in elem_ids}
        for root in roots:
            levels[root] = 0

        n = len(elem_ids)
        for _round in range(n):
            changed = False
            for parent in elem_ids:
                for child in outgoing.get(parent, []):
                    if child == parent:
                        continue  # skip self-loops
                    new_level = levels[parent] + 1
                    if new_level > levels[child]:
                        levels[child] = new_level
                        changed = True
            if not changed:
                break

        # Relocate minor source nodes (spouses/in-laws) to co-parent's level.
        # Among source nodes, only those with the largest descendant tree stay
        # at level 0. Others are placed at the same level as the other parent
        # of their shared child node.
        if len(roots) > 1:
            def _count_desc(start):
                vis = set()
                q = [start]
                while q:
                    nd = q.pop()
                    if nd in vis:
                        continue
                    vis.add(nd)
                    for nb in outgoing.get(nd, []):
                        if nb not in vis:
                            q.append(nb)
                return len(vis) - 1

            desc_counts = {r: _count_desc(r) for r in roots}
            max_desc = max(desc_counts.values())
            minor_sources = [r for r in roots if desc_counts[r] < max_desc]

            for src in minor_sources:
                co_parent_level = None
                for child in outgoing.get(src, []):
                    for op in incoming.get(child, []):
                        if op != src:
                            lvl = levels.get(op, 0)
                            if co_parent_level is None or lvl > co_parent_level:
                                co_parent_level = lvl
                if co_parent_level is not None:
                    levels[src] = co_parent_level

        # Leaf correction: leaves align to dominant parent's level
        for e_id in elem_ids:
            if outgoing.get(e_id):
                continue  # not a leaf
            parents = incoming.get(e_id, [])
            if not parents:
                continue
            # Check if terminal leaf (all siblings of parent are also leaves)
            is_terminal = True
            for parent in parents:
                for sibling in outgoing.get(parent, []):
                    if sibling != e_id and outgoing.get(sibling):
                        is_terminal = False
                        break
                if not is_terminal:
                    break

            max_parent = max(levels[p] for p in parents)
            if is_terminal:
                levels[e_id] = max_parent + 1
            else:
                levels[e_id] = max_parent

        return levels

    def calculate_centrality_scores(
        self,
        elements: List[dict],
        connections: List[dict],
        levels: Dict[str, int]
    ) -> Dict[str, float]:
        """
        Calcula scores de centralidad basados en grado de conexiones.

        Nodos con más conexiones reciben scores más altos y se posicionan
        al centro de su nivel durante el barycenter ordering.

        Args:
            elements: Lista de elementos
            connections: Lista de conexiones
            levels: Niveles topológicos calculados

        Returns:
            Dict[str, float]: {element_id: centrality_score}
        """
        elem_ids = {e['id'] for e in elements}

        # Count directed edges
        outdegree = {e_id: 0 for e_id in elem_ids}
        indegree = {e_id: 0 for e_id in elem_ids}

        for conn in connections:
            from_id = conn['from']
            to_id = conn['to']
            if from_id in elem_ids and to_id in elem_ids:
                outdegree[from_id] += 1
                indegree[to_id] += 1

        scores = {}
        for e_id in elem_ids:
            w_hijos = max(0, outdegree[e_id] - 1) * 0.10
            w_fanin = max(0, indegree[e_id] - 1) * 0.15
            scores[e_id] = w_hijos + w_fanin

        return scores

    def resolve_connections_to_primary(
        self,
        all_elements: List[dict],
        primary_ids: set,
        connections: List[dict]
    ) -> List[dict]:
        """
        Resolve connections so both endpoints map to primary elements.

        When a connection endpoint is a contained element, it gets resolved
        to its primary parent container. Self-loops and duplicates are removed.

        Args:
            all_elements: All elements (including contained)
            primary_ids: Set of primary element IDs
            connections: Original connections list

        Returns:
            List of resolved connection dicts with 'from', 'to', and 'weight'
        """
        # Build child -> parent container map
        child_to_parent = {}
        for elem in all_elements:
            if 'contains' not in elem:
                continue
            container_id = elem['id']
            for ref in elem.get('contains', []):
                child_id = extract_item_id(ref)
                child_to_parent[child_id] = container_id

        def resolve(elem_id):
            """Walk up containment tree until we find a primary element."""
            visited = set()
            current = elem_id
            while current not in primary_ids and current in child_to_parent:
                if current in visited:
                    break  # cycle protection
                visited.add(current)
                current = child_to_parent[current]
            return current if current in primary_ids else None

        # Resolve all connections
        edge_counts = {}
        for conn in connections:
            from_primary = resolve(conn['from'])
            to_primary = resolve(conn['to'])

            if from_primary is None or to_primary is None:
                continue
            if from_primary == to_primary:
                continue  # self-loop after resolution

            key = (from_primary, to_primary)
            edge_counts[key] = edge_counts.get(key, 0) + 1

        resolved = []
        for (f, t), weight in edge_counts.items():
            resolved.append({'from': f, 'to': t, 'weight': weight})

        return resolved

    def calculate_levels(self, elements: List[dict]) -> Dict[str, int]:
        """
        Asigna nivel (fila lógica) a cada elemento basado en su posición Y.

        Elementos con Y similar (±80px) están en el mismo nivel.

        NOTA: Este método se usa DESPUÉS del auto-layout para verificar.
        Para auto-layout inicial, usar calculate_topological_levels().

        Args:
            elements: Lista de elementos del diagrama

        Returns:
            Dict[str, int]: {element_id: level_number}
        """
        # Filtrar contenedores (elementos con 'contains') y elementos sin coordenadas
        normal_elements = [e for e in elements if 'contains' not in e and 'y' in e]

        sorted_by_y = sorted(normal_elements, key=lambda e: e['y'])
        levels = {}
        current_level = 0
        last_y = -100

        for elem in sorted_by_y:
            if elem['y'] - last_y > 80:  # Nueva fila
                current_level += 1
            levels[elem['id']] = current_level
            last_y = elem['y']

        return levels

    def identify_groups(
        self,
        graph: Dict[str, List[str]],
        elements: List[dict]
    ) -> List[List[str]]:
        """
        Identifica subgrafos conectados usando DFS.

        Args:
            graph: Grafo de adyacencia
            elements: Lista de elementos del diagrama

        Returns:
            List[List[str]]: [[elem_ids del grupo 1], [elem_ids del grupo 2], ...]
        """
        visited = set()
        groups = []

        def dfs(node, group):
            if node in visited:
                return
            visited.add(node)
            group.append(node)
            for neighbor in graph.get(node, []):
                dfs(neighbor, group)

        for elem in elements:
            if elem['id'] not in visited:
                group = []
                dfs(elem['id'], group)
                groups.append(group)

        return groups

    def calculate_auto_priority(
        self,
        element_id: str,
        graph: Dict[str, List[str]]
    ) -> str:
        """
        Calcula prioridad automática basada en número de conexiones.

        Elementos con más conexiones son más importantes.

        Args:
            element_id: ID del elemento
            graph: Grafo de adyacencia

        Returns:
            str: 'high', 'normal', o 'low'
        """
        connections = len(graph.get(element_id, []))
        if connections >= 4:
            return 'high'
        elif connections >= 2:
            return 'normal'
        return 'low'

    def calculate_priorities(
        self,
        elements: List[dict],
        graph: Dict[str, List[str]]
    ) -> Dict[str, int]:
        """
        Calcula prioridades para todos los elementos.

        Prioridad manual tiene precedencia sobre automática.
        Automática basada en número de conexiones:
        - >= 4 conexiones: high (0)
        - >= 2 conexiones: normal (1)
        - < 2 conexiones: low (2)

        Args:
            elements: Lista de elementos del diagrama
            graph: Grafo de adyacencia

        Returns:
            Dict[str, int]: {element_id: priority_value}
                priority_value: 0=high, 1=normal, 2=low
        """
        priorities = {}

        for elem in elements:
            elem_id = elem['id']

            # Prioridad manual tiene precedencia
            manual_priority = elem.get('label_priority')
            if manual_priority in self.PRIORITY_ORDER:
                priorities[elem_id] = self.PRIORITY_ORDER[manual_priority]
            else:
                # Calcular automáticamente
                auto_priority = self.calculate_auto_priority(elem_id, graph)
                priorities[elem_id] = self.PRIORITY_ORDER[auto_priority]

        return priorities

    def get_priority_name(self, priority_value: int) -> str:
        """
        Convierte valor numérico de prioridad a nombre.

        Args:
            priority_value: 0, 1, o 2

        Returns:
            str: 'high', 'normal', o 'low'
        """
        reverse_map = {v: k for k, v in self.PRIORITY_ORDER.items()}
        return reverse_map.get(priority_value, 'normal')
