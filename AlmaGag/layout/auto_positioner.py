"""
AutoLayoutPositioner - Cálculo automático de posiciones para SDJF v2.0

Este módulo implementa la estrategia híbrida de auto-layout:
- HIGH priority → centro (grid compacto)
- NORMAL priority → alrededor (anillo medio)
- LOW priority → periferia (anillo externo)

Soporta:
- Auto-layout completo (sin x ni y)
- Coordenadas parciales (calcular solo x o solo y)
- Centralidad basada en tamaño (hp/wp)
"""

import math
from typing import List
from AlmaGag.layout.layout import Layout
from AlmaGag.layout.sizing import SizingCalculator
from AlmaGag.layout.graph_analysis import GraphAnalyzer


class AutoLayoutPositioner:
    """
    Calcula posiciones automáticas para elementos sin coordenadas.

    Implementa estrategia híbrida: prioridad + grid + centralidad.
    """

    def __init__(self, sizing: SizingCalculator, graph_analyzer: GraphAnalyzer):
        """
        Inicializa el posicionador.

        Args:
            sizing: Calculadora de tamaños para scoring de centralidad
            graph_analyzer: Analizador de grafos para prioridades
        """
        self.sizing = sizing
        self.graph_analyzer = graph_analyzer

    def calculate_missing_positions(self, layout: Layout) -> Layout:
        """
        Calcula x, y para elementos que no tienen coordenadas.

        Estrategia:
        1. Separar elementos por tipo de coordenadas faltantes
        2. Calcular coordenadas parciales primero (x-only, y-only)
        3. Auto-layout híbrido para elementos sin coordenadas

        Args:
            layout: Layout con algunos elementos sin x/y

        Returns:
            Layout: Mismo layout (modificado in-place) con coordenadas calculadas
        """
        # Filtrar contenedores (no necesitan auto-layout, se calculan dinámicamente)
        normal_elements = [e for e in layout.elements if 'contains' not in e]

        # Separar elementos con/sin coordenadas
        missing_both = [e for e in normal_elements if 'x' not in e and 'y' not in e]
        missing_x = [e for e in normal_elements if 'x' not in e and 'y' in e]
        missing_y = [e for e in normal_elements if 'x' in e and 'y' not in e]

        # Calcular coordenadas parciales primero
        if missing_x:
            self._calculate_x_only(layout, missing_x)
        if missing_y:
            self._calculate_y_only(layout, missing_y)

        # Auto-layout completo para elementos sin coordenadas
        if missing_both:
            self._calculate_hybrid_layout(layout, missing_both)

        return layout

    def _calculate_hybrid_layout(self, layout: Layout, elements: List[dict]):
        """
        Auto-layout híbrido: prioridad + grid + centralidad.

        Algoritmo:
        1. Agrupar por prioridad: HIGH, NORMAL, LOW
        2. Calcular centrality_score para cada elemento
        3. Posicionar HIGH en centro (grid compacto)
        4. Posicionar NORMAL alrededor (anillo medio)
        5. Posicionar LOW en periferia (anillo externo)

        Args:
            layout: Layout con información de prioridades
            elements: Elementos sin coordenadas a posicionar
        """
        # Agrupar por prioridad
        by_priority = {0: [], 1: [], 2: []}  # HIGH, NORMAL, LOW
        for elem in elements:
            priority = layout.priorities.get(elem['id'], 1)  # Default: NORMAL
            by_priority[priority].append(elem)

        # Calcular centro del canvas
        center_x = layout.canvas['width'] / 2
        center_y = layout.canvas['height'] / 2

        # HIGH: grid compacto en centro (sorted by centrality)
        high_elements = sorted(
            by_priority[0],
            key=lambda e: self.sizing.get_centrality_score(e, 0),
            reverse=True
        )
        self._position_grid_center(high_elements, center_x, center_y, spacing=120)

        # NORMAL: anillo alrededor
        normal_elements = sorted(
            by_priority[1],
            key=lambda e: self.sizing.get_centrality_score(e, 1),
            reverse=True
        )
        self._position_ring(normal_elements, center_x, center_y, radius=300)

        # LOW: anillo externo
        low_elements = by_priority[2]
        self._position_ring(low_elements, center_x, center_y, radius=450)

    def _position_grid_center(
        self,
        elements: List[dict],
        cx: float,
        cy: float,
        spacing: float = 120
    ):
        """
        Posiciona elementos en grid compacto centrado.

        Args:
            elements: Elementos a posicionar (ya ordenados por centralidad)
            cx: Centro X del grid
            cy: Centro Y del grid
            spacing: Espaciado entre elementos
        """
        n = len(elements)
        if n == 0:
            return

        # Grid sqrt(n) × sqrt(n)
        cols = int(math.ceil(math.sqrt(n)))

        for i, elem in enumerate(elements):
            row = i // cols
            col = i % cols

            # Calcular número de filas necesarias
            rows = (n + cols - 1) // cols

            # Centrar grid
            grid_width = cols * spacing
            grid_height = rows * spacing

            elem['x'] = cx - grid_width / 2 + col * spacing + spacing / 2
            elem['y'] = cy - grid_height / 2 + row * spacing + spacing / 2

    def _position_ring(
        self,
        elements: List[dict],
        cx: float,
        cy: float,
        radius: float
    ):
        """
        Posiciona elementos en anillo circular.

        Args:
            elements: Elementos a posicionar
            cx: Centro X del anillo
            cy: Centro Y del anillo
            radius: Radio del anillo
        """
        n = len(elements)
        if n == 0:
            return

        angle_step = 2 * math.pi / n
        for i, elem in enumerate(elements):
            angle = i * angle_step
            elem['x'] = cx + radius * math.cos(angle)
            elem['y'] = cy + radius * math.sin(angle)

    def _calculate_x_only(self, layout: Layout, elements: List[dict]):
        """
        Calcula solo X para elementos que tienen Y.

        Estrategia:
        - Agrupar por nivel (Y similar, ±40px)
        - Distribuir horizontalmente en cada nivel

        Args:
            layout: Layout con canvas info
            elements: Elementos con Y pero sin X
        """
        # Agrupar por nivel (Y similar)
        by_level = {}
        for elem in elements:
            level = self._find_level_for_y(elem['y'])
            if level not in by_level:
                by_level[level] = []
            by_level[level].append(elem)

        # Distribuir horizontalmente en cada nivel
        for level, elems in by_level.items():
            spacing = 120
            total_width = len(elems) * spacing
            start_x = (layout.canvas['width'] - total_width) / 2

            for i, elem in enumerate(elems):
                elem['x'] = start_x + i * spacing + spacing / 2

    def _calculate_y_only(self, layout: Layout, elements: List[dict]):
        """
        Calcula solo Y para elementos que tienen X.

        Estrategia:
        - Asignar Y basado en prioridad
        - HIGH → top (25%), NORMAL → middle (50%), LOW → bottom (75%)

        Args:
            layout: Layout con información de prioridades
            elements: Elementos con X pero sin Y
        """
        # Agrupar por prioridad
        by_priority = {0: [], 1: [], 2: []}
        for elem in elements:
            priority = layout.priorities.get(elem['id'], 1)
            by_priority[priority].append(elem)

        # HIGH → top, NORMAL → middle, LOW → bottom
        level_y = {
            0: layout.canvas['height'] * 0.25,  # HIGH
            1: layout.canvas['height'] * 0.50,  # NORMAL
            2: layout.canvas['height'] * 0.75   # LOW
        }

        for priority, elems in by_priority.items():
            for elem in elems:
                elem['y'] = level_y[priority]

    def _find_level_for_y(self, y: float) -> int:
        """
        Encuentra nivel más cercano para Y dado.

        Usa agrupación por rangos de 80px (consistente con GraphAnalyzer).

        Args:
            y: Coordenada Y

        Returns:
            int: Nivel (0, 1, 2, ...)
        """
        return int(y / 80)
