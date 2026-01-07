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

    def calculate_levels(self, elements: List[dict]) -> Dict[str, int]:
        """
        Asigna nivel (fila lógica) a cada elemento basado en su posición Y.

        Elementos con Y similar (±80px) están en el mismo nivel.

        Args:
            elements: Lista de elementos del diagrama

        Returns:
            Dict[str, int]: {element_id: level_number}
        """
        sorted_by_y = sorted(elements, key=lambda e: e['y'])
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
