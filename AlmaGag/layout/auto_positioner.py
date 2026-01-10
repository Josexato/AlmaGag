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

        Estrategia (v2.3 - Hierarchical Layout):
        1. Calcular niveles topológicos del grafo (jerarquía)
        2. Agrupar elementos por contenedor
        3. Posicionar cada grupo de contenedor de forma compacta
        4. Posicionar elementos libres con layout jerárquico
        5. Calcular coordenadas parciales (x-only, y-only)

        Args:
            layout: Layout con algunos elementos sin x/y

        Returns:
            Layout: Mismo layout (modificado in-place) con coordenadas calculadas
        """
        # Filtrar contenedores (no necesitan auto-layout, se calculan dinámicamente)
        normal_elements = [e for e in layout.elements if 'contains' not in e]

        # Separar elementos con/sin coordenadas completas
        missing_both = [e for e in normal_elements if 'x' not in e and 'y' not in e]
        missing_x = [e for e in normal_elements if 'x' not in e and 'y' in e]
        missing_y = [e for e in normal_elements if 'x' in e and 'y' not in e]

        # NUEVO v2.3: Calcular niveles topológicos ANTES de posicionar
        if missing_both and layout.connections:
            topological_levels = self.graph_analyzer.calculate_topological_levels(
                layout.elements,
                layout.connections
            )
            # Guardar en layout para uso posterior
            layout.topological_levels = topological_levels
        else:
            layout.topological_levels = {}

        # v2.2: Agrupar elementos sin coordenadas por contenedor
        if missing_both:
            groups = self._group_elements_by_container(layout, missing_both)
            self._position_groups(layout, groups)

        # Calcular coordenadas parciales
        if missing_x:
            self._calculate_x_only(layout, missing_x)
        if missing_y:
            self._calculate_y_only(layout, missing_y)

        return layout

    def _calculate_hierarchical_layout(self, layout: Layout, elements: List[dict]):
        """
        Auto-layout jerárquico basado en topología del grafo (v2.3).

        Algoritmo:
        1. Agrupar elementos por nivel topológico
        2. Calcular posición Y para cada nivel (vertical spacing)
        3. Distribuir elementos de cada nivel horizontalmente
        4. Centrar cada nivel respecto al canvas

        Args:
            layout: Layout con topological_levels calculados
            elements: Elementos sin coordenadas a posicionar
        """
        # Agrupar por nivel topológico
        by_level = {}
        for elem in elements:
            level = layout.topological_levels.get(elem['id'], 0)
            if level not in by_level:
                by_level[level] = []
            by_level[level].append(elem)

        # Calcular número de niveles
        num_levels = len(by_level)
        if num_levels == 0:
            return

        # Configuración de spacing
        VERTICAL_SPACING = 150  # Espacio entre niveles
        HORIZONTAL_SPACING = 120  # Espacio entre elementos del mismo nivel
        TOP_MARGIN = 100  # Margen superior

        # Calcular centro horizontal del canvas
        center_x = layout.canvas['width'] / 2

        # Posicionar cada nivel
        for level_num in sorted(by_level.keys()):
            level_elements = by_level[level_num]
            num_elements = len(level_elements)

            # Calcular Y para este nivel
            y_position = TOP_MARGIN + (level_num * VERTICAL_SPACING)

            # Calcular ancho total necesario para este nivel
            total_width = num_elements * HORIZONTAL_SPACING

            # Calcular X inicial para centrar el nivel
            start_x = center_x - (total_width / 2) + (HORIZONTAL_SPACING / 2)

            # Posicionar elementos horizontalmente
            for i, elem in enumerate(level_elements):
                elem['x'] = start_x + (i * HORIZONTAL_SPACING)
                elem['y'] = y_position

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

        # Calcular radios máximos seguros (con margen de 100px)
        max_radius_x = center_x - 100  # Margen desde centro hasta borde
        max_radius_y = center_y - 100
        max_safe_radius = min(max_radius_x, max_radius_y)

        # Radios adaptativos basados en espacio disponible
        # Si el canvas es grande, usar radios más grandes; si es pequeño, ajustar
        radius_normal = min(max_safe_radius * 0.5, 250)  # 50% del radio seguro o 250px
        radius_low = min(max_safe_radius * 0.8, 350)     # 80% del radio seguro o 350px

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
        self._position_ring(normal_elements, center_x, center_y, radius=radius_normal)

        # LOW: anillo externo
        low_elements = by_priority[2]
        self._position_ring(low_elements, center_x, center_y, radius=radius_low)

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

    def _group_elements_by_container(self, layout: Layout, elements: List[dict]) -> dict:
        """
        Agrupa elementos por contenedor (v2.2 - Container-Aware Layout).

        Identifica qué elementos pertenecen a cada contenedor para
        posicionarlos de forma agrupada y compacta.

        Args:
            layout: Layout con información de contenedores
            elements: Elementos a agrupar

        Returns:
            dict: {
                'container_id': [elem1, elem2, ...],
                None: [elem_free1, elem_free2, ...]  # elementos sin contenedor
            }
        """
        groups = {}
        element_to_container = {}

        # Mapear cada elemento a su contenedor (si tiene uno)
        for elem in layout.elements:
            if 'contains' in elem:
                container_id = elem['id']
                contains = elem.get('contains', [])

                # Soportar formato dict {"id": "..."} o string directo
                for item in contains:
                    item_id = item['id'] if isinstance(item, dict) else item
                    element_to_container[item_id] = container_id

        # Agrupar elementos por contenedor
        for elem in elements:
            container_id = element_to_container.get(elem['id'], None)

            if container_id not in groups:
                groups[container_id] = []
            groups[container_id].append(elem)

        return groups

    def _position_groups(self, layout: Layout, groups: dict):
        """
        Posiciona grupos de contenedores y elementos libres (v2.3 - Hierarchical).

        Estrategia:
        1. Posicionar contenedores primero (compactos, en horizontal)
        2. Posicionar elementos libres con layout jerárquico si hay conexiones
        3. Fallback a layout híbrido si no hay jerarquía clara

        Args:
            layout: Layout con canvas info
            groups: Grupos de elementos por contenedor
        """
        # Configuración de espaciado
        CONTAINER_SPACING = 250  # Espacio entre contenedores
        ELEMENT_SPACING_IN_CONTAINER = 120  # Espacio entre elementos del mismo contenedor

        # Posición inicial
        current_x = 100
        current_y = 150

        # 1. Posicionar grupos de contenedores
        container_groups = {k: v for k, v in groups.items() if k is not None}

        for container_id in sorted(container_groups.keys()):
            element_list = container_groups[container_id]

            # Posicionar grupo de contenedor
            group_width = self._position_container_group(
                element_list,
                layout,
                current_x,
                current_y,
                ELEMENT_SPACING_IN_CONTAINER
            )

            # Mover a la siguiente posición horizontal
            current_x += group_width + CONTAINER_SPACING

        # 2. Posicionar elementos libres (sin contenedor)
        free_elements = groups.get(None, [])
        if free_elements:
            # v2.3: Usar layout jerárquico si hay niveles topológicos
            if hasattr(layout, 'topological_levels') and layout.topological_levels:
                self._calculate_hierarchical_layout(layout, free_elements)
            else:
                # Fallback a layout híbrido
                self._calculate_hybrid_layout(layout, free_elements)

    def _position_container_group(
        self,
        elements: List[dict],
        layout: Layout,
        start_x: float,
        start_y: float,
        spacing: float
    ) -> float:
        """
        Posiciona elementos de un contenedor en grid compacto.

        Args:
            elements: Elementos del contenedor
            layout: Layout con información de prioridades
            start_x: Posición X inicial del grupo
            start_y: Posición Y inicial del grupo
            spacing: Espaciado entre elementos

        Returns:
            float: Ancho total del grupo posicionado
        """
        n = len(elements)
        if n == 0:
            return 0

        # Determinar configuración de grid según número de elementos
        if n <= 3:
            cols = 1
            rows = n
        elif n <= 6:
            cols = 2
            rows = (n + 1) // 2
        elif n <= 9:
            cols = 3
            rows = (n + 2) // 3
        else:
            cols = 4
            rows = (n + 3) // 4

        # Posicionar elementos en grid
        for i, elem in enumerate(elements):
            row = i // cols
            col = i % cols

            elem['x'] = start_x + (col * spacing)
            elem['y'] = start_y + (row * spacing)

        # Retornar ancho del grupo
        group_width = cols * spacing
        return group_width
