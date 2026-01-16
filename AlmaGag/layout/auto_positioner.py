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
import logging
from typing import List, Dict
from AlmaGag.layout.layout import Layout
from AlmaGag.layout.sizing import SizingCalculator
from AlmaGag.layout.graph_analysis import GraphAnalyzer
from AlmaGag.config import ICON_WIDTH, ICON_HEIGHT

logger = logging.getLogger('AlmaGag.AutoPositioner')


class ContainerHierarchy:
    """
    Representa la jerarquía de contenedores y su orden de resolución.
    """

    def __init__(self, containers: List[dict], hierarchy: Dict[str, List[str]], order: List[str]):
        """
        Args:
            containers: Lista de elementos contenedores
            hierarchy: Grafo de contención {container_id: [child_container_ids]}
            order: Orden de resolución bottom-up (hijos antes que padres)
        """
        self.containers = containers
        self.hierarchy = hierarchy
        self.order = order
        self.containers_by_id = {c['id']: c for c in containers}

    def bottom_up_order(self) -> List[dict]:
        """
        Retorna contenedores en orden bottom-up para resolución.
        """
        return [self.containers_by_id[c_id] for c_id in self.order if c_id in self.containers_by_id]


class AutoLayoutPositioner:
    """
    Calcula posiciones automáticas para elementos sin coordenadas.

    Implementa estrategia híbrida: prioridad + grid + centralidad.
    """

    def __init__(self, sizing: SizingCalculator, graph_analyzer: GraphAnalyzer, visualdebug: bool = False):
        """
        Inicializa el posicionador.

        Args:
            sizing: Calculadora de tamaños para scoring de centralidad
            graph_analyzer: Analizador de grafos para prioridades
            visualdebug: Si True, usa TOP_MARGIN=80 para área de debug visual, sino usa 20
        """
        self.sizing = sizing
        self.graph_analyzer = graph_analyzer
        self.visualdebug = visualdebug

    def calculate_missing_positions(self, layout: Layout) -> Layout:
        """
        Calcula x, y para elementos que no tienen coordenadas.

        Estrategia (v3.0 - Layout en 3 Fases):
        FASE 1: Resolver contenedores (bottom-up)
        FASE 2: Análisis topológico de elementos primarios
        FASE 3: Distribución espacial y propagación

        Args:
            layout: Layout con algunos elementos sin x/y

        Returns:
            Layout: Mismo layout (modificado in-place) con coordenadas calculadas
        """
        # ============================================
        # FASE 1: RESOLVER CONTENEDORES (BOTTOM-UP)
        # ============================================

        container_hierarchy = self._analyze_container_hierarchy(layout)

        for container in container_hierarchy.bottom_up_order():
            self._resolve_container(layout, container)

        # ============================================
        # FASE 2: ANÁLISIS TOPOLÓGICO GLOBAL
        # ============================================

        primary_elements = self._get_primary_elements(layout)

        # Separar primarios con/sin coordenadas
        missing_both = [e for e in primary_elements if 'x' not in e and 'y' not in e]
        missing_x = [e for e in primary_elements if 'x' not in e and 'y' in e]
        missing_y = [e for e in primary_elements if 'x' in e and 'y' not in e]

        # Calcular niveles topológicos SOLO para elementos primarios
        if missing_both and layout.connections:
            topological_levels = self.graph_analyzer.calculate_topological_levels(
                primary_elements,  # Solo primarios
                layout.connections
            )
            layout.topological_levels = topological_levels

            # LOG: Mostrar niveles topológicos
            logger.debug(f"\n[NIVELES TOPOLOGICOS]")
            for elem_id, level in topological_levels.items():
                logger.debug(f"  {elem_id}: nivel {level}")
        else:
            layout.topological_levels = {}

        # ============================================
        # FASE 3: DISTRIBUCIÓN ESPACIAL GLOBAL
        # ============================================

        # Posicionar elementos primarios
        if missing_both:
            if layout.topological_levels:
                self._calculate_hierarchical_layout(layout, missing_both)
            else:
                self._calculate_hybrid_layout(layout, missing_both)

        # Calcular coordenadas parciales para primarios
        if missing_x:
            self._calculate_x_only(layout, missing_x)
        if missing_y:
            self._calculate_y_only(layout, missing_y)

        # Propagar coordenadas globales a elementos internos
        self._propagate_coordinates_to_contained(layout)

        return layout

    def recalculate_positions_with_expanded_containers(self, layout: Layout) -> Layout:
        """
        Redistribuye elementos primarios DESPUÉS de que los contenedores se hayan expandido.

        Este método se invoca en la Fase 7 (después de recalcular contenedores con etiquetas)
        para reposicionar elementos que ahora pueden colisionar con contenedores expandidos.

        Estrategia:
        1. Identificar elementos primarios que NO son contenedores
           - Contenedores YA están posicionados y dimensionados → NO mover
           - Solo redistribuir elementos "libres" (ej: nube en red-edificios.gag)

        2. Resetear coordenadas de elementos libres

        3. Redistribuir usando layout jerárquico o híbrido

        4. Propagar coordenadas a elementos contenidos

        Args:
            layout: Layout con contenedores YA expandidos y dimensionados

        Returns:
            Layout: Mismo layout (modificado in-place) con elementos redistribuidos
        """
        logger.debug("\n[REDISTRIBUCION POST-EXPANSION DE CONTENEDORES]")

        # 1. Identificar elementos primarios (no contenidos)
        primary_elements = self._get_primary_elements(layout)

        # 2. Separar contenedores de elementos libres
        containers = [e for e in primary_elements if 'contains' in e]
        free_elements = [e for e in primary_elements if 'contains' not in e]

        logger.debug(f"  Contenedores (mantener posiciones): {len(containers)}")
        logger.debug(f"  Elementos libres (redistribuir): {len(free_elements)}")

        # IMPORTANTE: Solo redistribuir si HAY contenedores que se expandieron
        # Si no hay contenedores, los elementos ya están bien posicionados
        if not containers:
            logger.debug("  Sin contenedores → No redistribuir (elementos ya posicionados)")
            return layout

        if not free_elements:
            logger.debug("  Sin elementos libres para redistribuir")
            return layout

        # 3. Resetear coordenadas de elementos libres
        for elem in free_elements:
            if 'x' in elem:
                del elem['x']
            if 'y' in elem:
                del elem['y']
            logger.debug(f"    Resetear: {elem['id']}")

        # 4. Redistribuir elementos libres EVITANDO contenedores
        # ESTRATEGIA: Usar niveles topológicos PERO con spacing ajustado para contenedores
        logger.debug(f"  Redistribuyendo elementos libres (evitando contenedores)")
        self._redistribute_free_elements_with_containers(layout, free_elements, containers)

        # 5. NO propagar coordenadas aquí - ya fueron propagadas en el optimizer
        #    Los elementos contenidos NO se mueven durante la redistribución (solo elementos libres)
        #    Propagar aquí sobrescribiría las coordenadas centradas con valores incorrectos

        logger.debug("[FIN REDISTRIBUCION]\n")

        return layout

    def _calculate_hierarchical_layout(self, layout: Layout, elements: List[dict]):
        """
        Auto-layout jerárquico basado en topología del grafo (v3.1).

        Algoritmo:
        1. Agrupar elementos por nivel topológico
        2. Calcular posición Y para cada nivel considerando alto real del nivel anterior
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
        VERTICAL_SPACING = 100  # Espacio entre niveles
        HORIZONTAL_SPACING = 120  # Espacio entre elementos del mismo nivel
        # TOP_MARGIN = 80px si visualdebug (área de debug badge), 20px si no
        TOP_MARGIN = 80 if self.visualdebug else 20

        # Calcular centro horizontal del canvas
        center_x = layout.canvas['width'] / 2

        # Rastrear posición Y actual (dónde termina el nivel anterior)
        current_y = TOP_MARGIN

        # Posicionar cada nivel
        for level_num in sorted(by_level.keys()):
            level_elements = by_level[level_num]
            num_elements = len(level_elements)

            # Calcular altura máxima de los elementos en este nivel
            max_height = 0
            for elem in level_elements:
                elem_height = elem.get('height', ICON_HEIGHT)
                max_height = max(max_height, elem_height)

            # Posición Y para este nivel (donde termina el nivel anterior + spacing)
            y_position = current_y

            logger.debug(f"\n[NIVEL {level_num}] Y={y_position:.1f}, Elementos={num_elements}, Max_height={max_height:.1f}")

            # Calcular ancho total necesario para este nivel
            total_width = num_elements * HORIZONTAL_SPACING

            # Calcular X inicial para centrar el nivel
            start_x = center_x - (total_width / 2) + (HORIZONTAL_SPACING / 2)

            # Posicionar elementos horizontalmente
            for i, elem in enumerate(level_elements):
                elem['x'] = start_x + (i * HORIZONTAL_SPACING)
                elem['y'] = y_position
                logger.debug(f"  {elem['id']}: ({elem['x']:.1f}, {elem['y']:.1f})")

            # Actualizar current_y para el siguiente nivel
            # current_y = donde termina este nivel + spacing
            current_y = y_position + max_height + VERTICAL_SPACING

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

    def _analyze_container_hierarchy(self, layout: Layout) -> ContainerHierarchy:
        """
        Analiza jerarquía de contenedores y retorna orden de resolución.

        Retorna:
            ContainerHierarchy con orden bottom-up (hijos antes que padres)
        """
        containers = [e for e in layout.elements if 'contains' in e]

        if not containers:
            return ContainerHierarchy([], {}, [])

        # Construir grafo de contención
        hierarchy = {}
        for container in containers:
            children = []
            for contained_ref in container['contains']:
                child_id = contained_ref['id'] if isinstance(contained_ref, dict) else contained_ref
                child = layout.elements_by_id.get(child_id)
                if child and 'contains' in child:
                    # Es un contenedor anidado
                    children.append(child_id)
            hierarchy[container['id']] = children

        # Calcular orden bottom-up (DFS post-order)
        order = self._topological_sort_containers(hierarchy)

        return ContainerHierarchy(containers, hierarchy, order)

    def _topological_sort_containers(self, hierarchy: Dict[str, List[str]]) -> List[str]:
        """
        Ordena contenedores en orden bottom-up (hijos antes que padres).

        Usa DFS post-order traversal.

        Args:
            hierarchy: {container_id: [child_container_ids]}

        Returns:
            Lista de container_ids en orden bottom-up
        """
        visited = set()
        order = []

        def dfs_postorder(node_id):
            if node_id in visited:
                return
            visited.add(node_id)

            # Visitar hijos primero
            for child_id in hierarchy.get(node_id, []):
                dfs_postorder(child_id)

            # Agregar este nodo al orden (post-order)
            order.append(node_id)

        # Iniciar DFS desde todos los contenedores
        for container_id in hierarchy.keys():
            dfs_postorder(container_id)

        return order

    def _resolve_container(self, layout: Layout, container: dict):
        """
        Resuelve un contenedor: posiciona elementos internos y calcula dimensiones.

        Asume que contenedores hijos ya están resueltos.

        Args:
            layout: Layout con elements_by_id
            container: Contenedor a resolver
        """
        # Obtener elementos contenidos
        contained_ids = [ref['id'] if isinstance(ref, dict) else ref for ref in container['contains']]
        contained_elements = [layout.elements_by_id[id] for id in contained_ids if id in layout.elements_by_id]

        if not contained_elements:
            # Contenedor vacío
            container['width'] = ICON_WIDTH + 40
            container['height'] = ICON_HEIGHT + 40
            container['_resolved'] = True
            return

        # Posicionar elementos internos (layout local)
        self._layout_contained_elements_locally(container, contained_elements)

        # Calcular envolvente del contenedor (basado en elementos internos + padding + etiqueta)
        padding = container.get('padding', 10)
        min_width, min_height = self._calculate_container_bounds(
            contained_elements,
            padding,
            container  # Pasar contenedor para calcular espacio de etiqueta
        )

        # Asignar dimensiones al contenedor (ahora es un "elemento primario")
        container['width'] = min_width
        container['height'] = min_height
        container['_resolved'] = True

        # NUEVO: Re-centrar elemento si es único (Opción 4 - Post-Cálculo)
        # Ahora que conocemos las dimensiones finales del contenedor, podemos centrar correctamente
        if len(contained_elements) == 1:
            elem = contained_elements[0]

            # Calcular espacio del header del contenedor
            header_height = 0
            if container.get('label'):
                lines = container['label'].split('\n')
                label_height = len(lines) * 18  # 18px por línea
                icon_height = 50  # Altura del icono del contenedor
                header_height = max(icon_height, label_height)

            # Obtener tamaño del elemento
            elem_width = elem.get('width', ICON_WIDTH)
            elem_height = elem.get('height', ICON_HEIGHT)

            # Calcular posición centrada
            # Horizontal: centrado en el ancho total del contenedor
            centered_x = (min_width - elem_width) / 2

            # Vertical: centrado en el espacio disponible para contenido
            # min_height = (2*padding) + header_height + content_height
            # Espacio disponible para contenido = content_height = min_height - (2*padding) - header_height
            content_area_height = min_height - (2 * padding) - header_height

            # Centrar elemento en el área de contenido (después del header + padding)
            centered_y = header_height + padding + ((content_area_height - elem_height) / 2)

            # Sobrescribir posición local con centrado
            elem['_local_x'] = centered_x
            elem['_local_y'] = centered_y

            logger.debug(f"  [CENTRADO] Elemento único re-centrado: ({centered_x:.1f}, {centered_y:.1f})")
            logger.debug(f"    header_height={header_height:.1f}, content_area={content_area_height:.1f}")

        # LOG: Información del contenedor resuelto
        logger.debug(f"\n[CONTENEDOR RESUELTO] {container['id']}")
        logger.debug(f"  Dimensiones: {min_width:.1f} x {min_height:.1f}")
        if container.get('label'):
            lines = container['label'].split('\n')
            label_height = len(lines) * 18 + 10
            logger.debug(f"  Espacio etiqueta: {label_height}px (arriba)")
        logger.debug(f"  Elementos internos: {len(contained_elements)}")
        for elem in contained_elements:
            logger.debug(f"    - {elem['id']}: local({elem.get('_local_x', 0):.1f}, {elem.get('_local_y', 0):.1f}) "
                        f"size({elem.get('width', ICON_WIDTH):.1f} x {elem.get('height', ICON_HEIGHT):.1f})")

    def _layout_contained_elements_locally(self, container: dict, elements: List[dict]):
        """
        Posiciona elementos DENTRO del contenedor (coordenadas locales).

        Estrategias:
        - scope: "border" → en el borde del contenedor (se calculará después)
        - scope: "full" → distribución interna (grid simple)

        Args:
            container: Contenedor padre
            elements: Elementos a posicionar
        """
        padding = container.get('padding', 10)

        # Calcular espacio del header del contenedor
        header_height = 0
        if container.get('label'):
            label_text = container['label']
            lines = label_text.split('\n')
            label_height = len(lines) * 18  # 18px por línea
            icon_height = 50  # Altura del icono del contenedor
            header_height = max(icon_height, label_height)

        # Posición Y inicial para elementos = header + padding_mid
        start_y = header_height + padding

        # Filtrar por scope
        full_elements = []
        for elem in elements:
            scope = self._get_scope(elem, container)
            if scope == 'full':
                full_elements.append(elem)

        # Layout para elementos "full" (distribución interna simple)
        if full_elements:
            # Grid simple basado en número de elementos
            n = len(full_elements)
            if n == 1:
                cols = 1
            elif n <= 4:
                cols = 2
            else:
                cols = int(n ** 0.5) + 1

            spacing = 20

            for i, elem in enumerate(full_elements):
                row = i // cols
                col = i % cols
                elem['_local_x'] = padding + col * (ICON_WIDTH + spacing)
                elem['_local_y'] = start_y + row * (ICON_HEIGHT + spacing)

    def _get_scope(self, elem: dict, container: dict) -> str:
        """
        Obtiene el scope de un elemento dentro de un contenedor.

        Args:
            elem: Elemento
            container: Contenedor padre

        Returns:
            'full' o 'border'
        """
        # Buscar en las referencias del contenedor
        for ref in container.get('contains', []):
            ref_id = ref['id'] if isinstance(ref, dict) else ref
            if ref_id == elem['id']:
                if isinstance(ref, dict):
                    return ref.get('scope', 'full')
                return 'full'
        return 'full'

    def _calculate_container_bounds(self, elements: List[dict], padding: float, container: dict = None) -> tuple:
        """
        Calcula dimensiones mínimas del contenedor basándose en elementos internos.

        Args:
            elements: Elementos contenidos
            padding: Padding del contenedor
            container: Contenedor (para calcular espacio de su etiqueta)

        Returns:
            (width, height): Dimensiones mínimas
        """
        if not elements:
            content_width = ICON_WIDTH
            content_height = ICON_HEIGHT
            base_width = ICON_WIDTH + 2 * padding
        else:
            # Encontrar bounding box de elementos
            min_x = float('inf')
            min_y = float('inf')
            max_x = float('-inf')
            max_y = float('-inf')

            for elem in elements:
                local_x = elem.get('_local_x', 0)
                local_y = elem.get('_local_y', 0)
                elem_width = elem.get('width', ICON_WIDTH)
                elem_height = elem.get('height', ICON_HEIGHT)

                min_x = min(min_x, local_x)
                min_y = min(min_y, local_y)
                max_x = max(max_x, local_x + elem_width)

                # Considerar también el espacio de la etiqueta del elemento (si existe)
                elem_bottom = local_y + elem_height
                if elem.get('label'):
                    # La etiqueta está típicamente 15px debajo del ícono y tiene ~18px de altura
                    elem_bottom += 15 + 18  # offset + altura de etiqueta

                max_y = max(max_y, elem_bottom)

            # Calcular dimensiones del contenido (sin padding aún)
            content_width = max_x - min_x
            content_height = max_y - min_y

            # Mínimos razonables para contenido
            content_width = max(content_width, ICON_WIDTH)
            content_height = max(content_height, ICON_HEIGHT)

            # Agregar padding horizontal (izquierda + derecha)
            base_width = content_width + 2 * padding

        # Calcular espacio del header del contenedor (icono + etiqueta)
        # El header comienza después del padding top
        header_height = 0

        if container and 'label' in container:
            label_text = container['label']
            lines = label_text.split('\n')
            max_line_len = max(len(line) for line in lines) if lines else 0
            label_width = max_line_len * 8  # 8px por carácter
            label_height = len(lines) * 18  # 18px por línea

            # El icono del contenedor tiene 50px de altura
            icon_height = 50

            # El header ocupa el máximo entre icono y etiqueta
            header_height = max(icon_height, label_height)

            # Calcular ancho necesario considerando que la etiqueta está a la derecha del ícono
            # Etiqueta comienza en: 10 (margen) + 80 (ícono) + 10 (margen) = 100
            label_x_position = 10 + ICON_WIDTH + 10
            label_required_width = label_x_position + label_width + 10  # posición + ancho + margen derecho

            # Usar el mayor entre base_width y label_required_width
            width = max(base_width, label_required_width)
        else:
            width = base_width

        # Altura total = header + padding_mid + content + padding_bottom
        # = header_height + padding + content_height + padding
        # = (2 * padding) + header_height + content_height
        height = (2 * padding) + header_height + content_height

        return (width, height)

    def _get_primary_elements(self, layout: Layout) -> List[dict]:
        """
        Retorna elementos primarios para análisis topológico.

        Primarios = Contenedores resueltos + Elementos sin padre

        Args:
            layout: Layout con elementos

        Returns:
            Lista de elementos primarios
        """
        primary = []

        # Todos los IDs contenidos
        contained_ids = set()
        for elem in layout.elements:
            if 'contains' in elem:
                for ref in elem['contains']:
                    ref_id = ref['id'] if isinstance(ref, dict) else ref
                    contained_ids.add(ref_id)

        # Contenedores resueltos + elementos sin padre
        for elem in layout.elements:
            if 'contains' in elem and elem.get('_resolved'):
                # Contenedor resuelto → primario
                primary.append(elem)
            elif elem['id'] not in contained_ids:
                # No está contenido → primario
                primary.append(elem)

        return primary

    def _propagate_coordinates_to_contained(self, layout: Layout):
        """
        Propaga coordenadas globales a elementos internos (FASE 3.2).

        Coordenada_global = Contenedor(x,y) + Espacio_etiqueta + Offset_local

        Args:
            layout: Layout con contenedores posicionados
        """
        for container in layout.elements:
            if 'contains' in container and container.get('x') is not None:
                container_x = container['x']
                container_y = container['y']

                # LOG: Conversión de coordenadas
                logger.debug(f"\n[PROPAGACION COORDENADAS] {container['id']}")
                logger.debug(f"  Contenedor en: ({container_x:.1f}, {container_y:.1f})")
                logger.debug(f"  Conversión local -> global:")

                for ref in container['contains']:
                    ref_id = ref['id'] if isinstance(ref, dict) else ref
                    elem = layout.elements_by_id.get(ref_id)
                    if elem and '_local_x' in elem:
                        local_x = elem['_local_x']
                        local_y = elem['_local_y']

                        # Convertir coordenadas locales a globales
                        # Las coordenadas locales ya incluyen el espacio del header
                        elem['x'] = container_x + local_x
                        elem['y'] = container_y + local_y

                        logger.debug(f"    {ref_id}: local({local_x:.1f}, {local_y:.1f}) -> "
                                   f"global({elem['x']:.1f}, {elem['y']:.1f})")

                        # Limpiar campos temporales
                        del elem['_local_x']
                        del elem['_local_y']

    def _redistribute_free_elements_with_containers(
        self,
        layout: Layout,
        free_elements: List[dict],
        containers: List[dict]
    ):
        """
        Redistribuye elementos libres EVITANDO contenedores existentes.

        Estrategia:
        1. Identificar franjas verticales ocupadas por contenedores
        2. Encontrar franjas libres (regiones entre/alrededor de contenedores)
        3. Posicionar elementos libres en franjas libres usando topología

        Args:
            layout: Layout con contenedores posicionados
            free_elements: Elementos libres a reposicionar
            containers: Contenedores YA posicionados (no mover)
        """
        if not free_elements:
            return

        # 1. Identificar franjas verticales ocupadas por contenedores
        occupied_ranges = []
        for container in containers:
            if 'y' in container and 'height' in container:
                y_start = container['y']
                y_end = container['y'] + container['height']
                occupied_ranges.append((y_start, y_end))
                logger.debug(f"    Contenedor {container['id']}: Y [{y_start:.1f} - {y_end:.1f}]")

        occupied_ranges.sort()  # Ordenar por y_start

        # 2. Encontrar franjas libres
        canvas_height = layout.canvas['height']
        free_ranges = []

        # Añadir franja antes del primer contenedor
        if occupied_ranges:
            first_start = occupied_ranges[0][0]
            if first_start > 150:  # Necesita al menos 150px para tener espacio (100 + 50 de margen)
                free_ranges.append((100, first_start - 50))  # Dejar 50px de margen

        # Añadir franjas entre contenedores
        for i in range(len(occupied_ranges) - 1):
            current_end = occupied_ranges[i][1]
            next_start = occupied_ranges[i + 1][0]
            gap = next_start - current_end
            if gap > 100:  # Si hay espacio suficiente (>100px)
                free_ranges.append((current_end + 50, next_start - 50))

        # Añadir franja después del último contenedor
        if occupied_ranges:
            last_end = occupied_ranges[-1][1]
            if last_end + 100 < canvas_height:
                free_ranges.append((last_end + 50, canvas_height - 50))

        # Si no hay contenedores, toda el área está libre
        if not occupied_ranges:
            free_ranges.append((100, canvas_height - 50))

        logger.debug(f"    Franjas libres encontradas: {len(free_ranges)}")
        for i, (start, end) in enumerate(free_ranges):
            logger.debug(f"      Franja {i+1}: Y [{start:.1f} - {end:.1f}] (altura: {end-start:.1f})")

        # Guardar franjas en el layout para visualización en modo debug
        layout.debug_free_ranges = free_ranges

        # 3. Posicionar elementos libres en franjas libres
        if not free_ranges:
            # No hay espacio libre → usar posición por defecto en centro
            logger.debug("    WARN: No hay franjas libres, usando centro del canvas")
            center_x = layout.canvas['width'] / 2
            center_y = layout.canvas['height'] / 2
            for elem in free_elements:
                elem['x'] = center_x
                elem['y'] = center_y
            return

        # Usar niveles topológicos si están disponibles
        if hasattr(layout, 'topological_levels') and layout.topological_levels:
            self._position_free_elements_by_topology(layout, free_elements, free_ranges)
        else:
            # Sin topología, distribuir equiespaciadamente
            self._position_free_elements_equispaced(layout, free_elements, free_ranges)

    def _position_free_elements_by_topology(
        self,
        layout: Layout,
        elements: List[dict],
        free_ranges: List[tuple]
    ):
        """
        Posiciona elementos usando niveles topológicos en franjas libres.

        Args:
            layout: Layout con topological_levels
            elements: Elementos a posicionar
            free_ranges: Lista de (y_start, y_end) franjas libres
        """
        # Agrupar elementos por nivel
        by_level = {}
        for elem in elements:
            level = layout.topological_levels.get(elem['id'], 0)
            if level not in by_level:
                by_level[level] = []
            by_level[level].append(elem)

        # Asignar cada nivel a una franja libre
        num_levels = len(by_level)
        center_x = layout.canvas['width'] / 2

        for level_idx, level_num in enumerate(sorted(by_level.keys())):
            level_elements = by_level[level_num]

            # Seleccionar franja para este nivel
            # Distribuir niveles equiespaciadamente en franjas libres
            franja_idx = min(level_idx, len(free_ranges) - 1)
            y_start, y_end = free_ranges[franja_idx]

            # Posicionar en el centro de la franja
            y_position = (y_start + y_end) / 2

            # Distribuir horizontalmente
            num_elements = len(level_elements)
            if num_elements == 1:
                level_elements[0]['x'] = center_x
                level_elements[0]['y'] = y_position
            else:
                spacing = 120
                total_width = num_elements * spacing
                start_x = center_x - (total_width / 2) + (spacing / 2)
                for i, elem in enumerate(level_elements):
                    elem['x'] = start_x + (i * spacing)
                    elem['y'] = y_position

            logger.debug(f"    Nivel {level_num} → Franja {franja_idx+1}, Y={y_position:.1f}")

    def _position_free_elements_equispaced(
        self,
        layout: Layout,
        elements: List[dict],
        free_ranges: List[tuple]
    ):
        """
        Posiciona elementos equiespaciadamente en franjas libres.

        Args:
            layout: Layout
            elements: Elementos a posicionar
            free_ranges: Lista de (y_start, y_end) franjas libres
        """
        center_x = layout.canvas['width'] / 2
        num_elements = len(elements)

        # Distribuir elementos en franjas libres
        for i, elem in enumerate(elements):
            # Seleccionar franja para este elemento
            franja_idx = min(i, len(free_ranges) - 1)
            y_start, y_end = free_ranges[franja_idx]

            # Posicionar en el centro de la franja
            y_position = (y_start + y_end) / 2

            elem['x'] = center_x
            elem['y'] = y_position

            logger.debug(f"    {elem['id']} → Franja {franja_idx+1}, Y={y_position:.1f}")
