"""
AutoLayoutPositioner - Cálculo automático de posiciones (v4.0)

Posiciona elementos de diagramas SDJF usando análisis topológico:
1. Resolver contenedores (bottom-up)
2. Análisis topológico: niveles, conexiones resueltas a primarios, centralidad
3. Layout jerárquico: barycenter ordering + position optimization + escala X global

Para diagramas sin conexiones, usa layout híbrido por prioridad:
- HIGH → centro, NORMAL → anillo medio, LOW → periferia
"""

import math
import logging
from typing import List, Dict
from AlmaGag.layout.layout import Layout
from AlmaGag.layout.sizing import SizingCalculator
from AlmaGag.layout.graph_analysis import GraphAnalyzer
from AlmaGag.config import (
    ICON_WIDTH, ICON_HEIGHT,
    SPACING_SMALL, SPACING_XLARGE, SPACING_XXLARGE,
    CONTAINER_PADDING, CONTAINER_SPACING, CONTAINER_ELEMENT_SPACING, CONTAINER_ICON_HEIGHT,
    TEXT_LINE_HEIGHT, TEXT_CHAR_WIDTH,
    LABEL_OFFSET_VERTICAL,
    CONTAINER_ICON_X,
    CANVAS_MARGIN_LARGE,
    GRID_SPACING_SMALL,
    RADIUS_NORMAL_MAX, RADIUS_LOW_MAX,
    TOP_MARGIN_DEBUG, TOP_MARGIN_NORMAL,
    LAF_VERTICAL_SPACING
)

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

        # Resolver conexiones a primarios (contained → container padre)
        primary_ids = {e['id'] for e in primary_elements}
        if missing_both and layout.connections:
            resolved_connections = self.graph_analyzer.resolve_connections_to_primary(
                layout.elements, primary_ids, layout.connections
            )
            # Store resolved connections for use in hierarchical layout
            layout._resolved_primary_connections = resolved_connections

            topological_levels = self.graph_analyzer.calculate_topological_levels(
                primary_elements,
                resolved_connections
            )
            layout.topological_levels = topological_levels

            logger.debug(f"\n[NIVELES TOPOLOGICOS] ({len(resolved_connections)} edges resueltas)")
            for elem_id, level in topological_levels.items():
                logger.debug(f"  {elem_id}: nivel {level}")
        else:
            layout.topological_levels = {}
            layout._resolved_primary_connections = []

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
        Ajusta elementos primarios DESPUÉS de que los contenedores se hayan expandido.

        IMPORTANTE: NO borra posiciones del layout jerárquico. Solo desplaza
        elementos libres que colisionan con contenedores expandidos.

        Estrategia:
        1. Identificar contenedores y elementos libres
        2. Para cada elemento libre, verificar si colisiona con algún contenedor
        3. Si colisiona, desplazarlo hacia abajo hasta quedar libre

        Args:
            layout: Layout con contenedores YA expandidos y dimensionados

        Returns:
            Layout: Mismo layout (modificado in-place) con ajustes mínimos
        """
        logger.debug("\n[AJUSTE POST-EXPANSION DE CONTENEDORES]")

        primary_elements = self._get_primary_elements(layout)
        containers = [e for e in primary_elements if 'contains' in e]
        free_elements = [e for e in primary_elements if 'contains' not in e]

        logger.debug(f"  Contenedores: {len(containers)}")
        logger.debug(f"  Elementos libres: {len(free_elements)}")

        if not containers or not free_elements:
            logger.debug("  Nada que ajustar")
            return layout

        # Build list of container bounding boxes
        container_bboxes = []
        for c in containers:
            if 'x' in c and 'y' in c:
                cx = c['x']
                cy = c['y']
                cw = c.get('width', ICON_WIDTH)
                ch = c.get('height', ICON_HEIGHT)
                container_bboxes.append((cx, cy, cx + cw, cy + ch, c['id']))

        if not container_bboxes:
            return layout

        MARGIN = SPACING_SMALL  # 40px margin around containers

        # For each free element, check overlap with containers and shift if needed
        adjustments = 0
        for elem in free_elements:
            if 'x' not in elem or 'y' not in elem:
                continue

            ex = elem['x']
            ey = elem['y']
            ew, eh = self.sizing.get_element_size(elem)

            for (cx1, cy1, cx2, cy2, cid) in container_bboxes:
                # Check overlap (with margin)
                if (ex < cx2 + MARGIN and ex + ew > cx1 - MARGIN and
                        ey < cy2 + MARGIN and ey + eh > cy1 - MARGIN):
                    # Shift element below the container
                    old_y = elem['y']
                    elem['y'] = cy2 + MARGIN
                    adjustments += 1
                    logger.debug(f"    {elem['id']}: Y {old_y:.1f} → {elem['y']:.1f} (evitar {cid})")
                    # Re-check with updated position
                    ey = elem['y']

        logger.debug(f"  Ajustes realizados: {adjustments}")
        logger.debug("[FIN AJUSTE]\n")

        # Mark that hierarchical layout positions are authoritative
        layout._hierarchical_layout_applied = True

        return layout

    def _calculate_hierarchical_layout(self, layout: Layout, elements: List[dict]):
        """
        Auto-layout jerárquico basado en topología del grafo (v4.0).

        Algoritmo:
        1. Agrupar elementos por nivel topológico
        2. Barycenter ordering (minimizar cruces)
        3. Optimizar posiciones abstractas (minimizar distancia de conectores)
        4. Calcular escala X global, asignar Y por nivel, centrar globalmente

        Args:
            layout: Layout con topological_levels calculados
            elements: Elementos sin coordenadas a posicionar
        """
        # 1. Agrupar por nivel topológico (element dicts, not IDs)
        by_level = {}
        for elem in elements:
            level = layout.topological_levels.get(elem['id'], 0)
            if level not in by_level:
                by_level[level] = []
            by_level[level].append(elem)

        if not by_level:
            return

        # Build directed graphs for barycenter (use resolved connections)
        resolved_conns = getattr(layout, '_resolved_primary_connections', None) or layout.connections
        elem_ids = {e['id'] for e in elements}
        outgoing = {e['id']: [] for e in elements}
        incoming = {e['id']: [] for e in elements}
        for conn in resolved_conns:
            f, t = conn['from'], conn['to']
            if f in elem_ids and t in elem_ids:
                outgoing[f].append(t)
                incoming[t].append(f)

        # Centrality scores (use resolved connections)
        centrality = self.graph_analyzer.calculate_centrality_scores(
            elements, resolved_conns, layout.topological_levels
        )

        # 2. Barycenter ordering (reorder elements within each level)
        self._reorder_by_barycenter(by_level, outgoing, incoming, centrality)

        # 3. Assign abstract positions (index within level)
        abstract_positions = {}
        for level_num in sorted(by_level.keys()):
            for idx, elem in enumerate(by_level[level_num]):
                abstract_positions[elem['id']] = (float(idx), float(level_num))

        # 4. Optimize abstract positions (layer-offset bisection)
        abstract_positions = self._optimize_abstract_positions(
            abstract_positions, by_level, outgoing, incoming
        )

        # 5. Compute real coordinates with global X scale
        TOP_MARGIN = TOP_MARGIN_DEBUG if self.visualdebug else TOP_MARGIN_NORMAL
        VERTICAL_SPACING = LAF_VERTICAL_SPACING  # 240px (same as LAF)
        MIN_GAP = SPACING_SMALL  # 40px minimum gap between elements
        LEFT_MARGIN = CANVAS_MARGIN_LARGE  # 100px

        # Get real widths
        widths = {}
        for elem in elements:
            w, h = self.sizing.get_element_size(elem)
            widths[elem['id']] = w

        # Compute global X scale
        global_x_scale = SPACING_XLARGE  # 120px minimum
        for level_num in sorted(by_level.keys()):
            level_elems = by_level[level_num]
            if len(level_elems) < 2:
                continue
            items = sorted(
                [(abstract_positions[e['id']][0], widths[e['id']], e['id']) for e in level_elems],
                key=lambda t: t[0]
            )
            for i in range(len(items) - 1):
                gap = items[i + 1][0] - items[i][0]
                if gap <= 0:
                    continue
                required = items[i][1] + MIN_GAP
                global_x_scale = max(global_x_scale, required / gap)

        # Normalize abstract X to start at 0
        all_abs_x = [abstract_positions[e['id']][0] for e in elements]
        abs_x_shift = -min(all_abs_x) if all_abs_x else 0

        # Assign Y positions per level
        current_y = TOP_MARGIN
        level_y = {}
        for level_num in sorted(by_level.keys()):
            level_y[level_num] = current_y
            max_h = max((e.get('height', ICON_HEIGHT) for e in by_level[level_num]), default=ICON_HEIGHT)
            current_y += max_h + VERTICAL_SPACING

        # Assign real X, Y
        for elem in elements:
            eid = elem['id']
            ax = abstract_positions[eid][0]
            level_num = layout.topological_levels.get(eid, 0)
            elem['x'] = (ax + abs_x_shift) * global_x_scale + LEFT_MARGIN
            elem['y'] = level_y.get(level_num, TOP_MARGIN)

        # Global centering: shift so x_min = LEFT_MARGIN
        x_min = min(e.get('x', 0) for e in elements) if elements else 0
        correction = LEFT_MARGIN - x_min
        if abs(correction) > 0.5:
            for elem in elements:
                elem['x'] += correction

        # Mark hierarchical layout as applied (prevents overwriting by redistribution)
        layout._hierarchical_layout_applied = True

    def _reorder_by_barycenter(
        self,
        by_level: Dict[int, List[dict]],
        outgoing: Dict[str, List[str]],
        incoming: Dict[str, List[str]],
        centrality: Dict[str, float]
    ) -> None:
        """
        Reorder elements within each level using barycenter heuristic
        to minimize edge crossings. Modifies by_level in-place.

        2 iterations of forward + backward passes with centrality blending.
        """
        sorted_levels = sorted(by_level.keys())
        if len(sorted_levels) < 2:
            return

        # Track positions (index within level)
        positions = {}
        for level_num in sorted_levels:
            for idx, elem in enumerate(by_level[level_num]):
                positions[elem['id']] = idx

        for _iteration in range(2):
            # Forward pass (top to bottom)
            for i in range(1, len(sorted_levels)):
                level_num = sorted_levels[i]
                prev_level_num = sorted_levels[i - 1]
                prev_ids = {e['id'] for e in by_level[prev_level_num]}
                level_elems = by_level[level_num]

                if len(level_elems) < 2:
                    continue

                center = (len(level_elems) - 1) / 2.0
                barycenters = {}
                for elem in level_elems:
                    eid = elem['id']
                    # Parents in previous level
                    parents = [p for p in incoming.get(eid, []) if p in prev_ids]
                    if parents:
                        bc_conn = sum(positions[p] for p in parents) / len(parents)
                    else:
                        bc_conn = center

                    # Blend with centrality
                    score = centrality.get(eid, 0.0)
                    alpha = min(0.6, score * 3.5) if score > 0 else 0.0
                    barycenters[eid] = (1.0 - alpha) * bc_conn + alpha * center

                level_elems.sort(key=lambda e: barycenters[e['id']])
                for idx, elem in enumerate(level_elems):
                    positions[elem['id']] = idx

            # Backward pass (bottom to top)
            for i in range(len(sorted_levels) - 2, -1, -1):
                level_num = sorted_levels[i]
                next_level_num = sorted_levels[i + 1]
                next_ids = {e['id'] for e in by_level[next_level_num]}
                level_elems = by_level[level_num]

                if len(level_elems) < 2:
                    continue

                center = (len(level_elems) - 1) / 2.0
                barycenters = {}
                for elem in level_elems:
                    eid = elem['id']
                    # Children in next level
                    children = [c for c in outgoing.get(eid, []) if c in next_ids]
                    if children:
                        bc_conn = sum(positions[c] for c in children) / len(children)
                    else:
                        bc_conn = center

                    score = centrality.get(eid, 0.0)
                    alpha = min(0.6, score * 3.5) if score > 0 else 0.0
                    barycenters[eid] = (1.0 - alpha) * bc_conn + alpha * center

                level_elems.sort(key=lambda e: barycenters[e['id']])
                for idx, elem in enumerate(level_elems):
                    positions[elem['id']] = idx

    def _optimize_abstract_positions(
        self,
        positions: Dict[str, tuple],
        by_level: Dict[int, List[dict]],
        outgoing: Dict[str, List[str]],
        incoming: Dict[str, List[str]],
        max_iterations: int = 10,
        convergence_threshold: float = 0.001
    ) -> Dict[str, tuple]:
        """
        Optimize abstract X positions using layer-offset bisection to minimize
        total connector distance. Preserves intra-layer order from barycenter.
        """
        # Build adjacency with weights (count of edges between pair)
        elem_ids = set(positions.keys())
        edge_counts: Dict[tuple, int] = {}
        for eid in elem_ids:
            for child in outgoing.get(eid, []):
                if child in elem_ids:
                    key = tuple(sorted([eid, child]))
                    edge_counts[key] = edge_counts.get(key, 0) + 1

        adjacency: Dict[str, list] = {eid: [] for eid in elem_ids}
        for (a, b), weight in edge_counts.items():
            adjacency[a].append((b, weight))
            adjacency[b].append((a, weight))

        # Organize by layer
        layers: Dict[int, List[str]] = {}
        for level_num in sorted(by_level.keys()):
            layers[level_num] = [e['id'] for e in by_level[level_num]]

        # Layer offsets
        base_positions = dict(positions)
        layer_offsets = {level: 0.0 for level in layers}

        def apply_offsets():
            result = dict(base_positions)
            for level, nodes in layers.items():
                off = layer_offsets.get(level, 0.0)
                for nid in nodes:
                    x, y = result[nid]
                    result[nid] = (x + off, y)
            return result

        def total_distance(pos):
            total = 0.0
            for eid in elem_ids:
                for neighbor, weight in adjacency.get(eid, []):
                    if eid < neighbor:
                        dx = pos[eid][0] - pos[neighbor][0]
                        dy = pos[eid][1] - pos[neighbor][1]
                        total += weight * math.sqrt(dx * dx + dy * dy)
            return total

        optimized = apply_offsets()
        prev_dist = total_distance(optimized)

        for _iteration in range(max_iterations):
            moved = False

            # Forward pass
            for level in sorted(layers.keys()):
                if self._optimize_layer_offset(level, layers, base_positions, optimized, adjacency, layer_offsets):
                    moved = True
                    optimized = apply_offsets()

            # Backward pass
            for level in sorted(layers.keys(), reverse=True):
                if self._optimize_layer_offset(level, layers, base_positions, optimized, adjacency, layer_offsets):
                    moved = True
                    optimized = apply_offsets()

            new_dist = total_distance(optimized)
            if (prev_dist - new_dist) < convergence_threshold or not moved:
                break
            prev_dist = new_dist

        return optimized

    def _optimize_layer_offset(
        self,
        level: int,
        layers: Dict[int, List[str]],
        base_positions: Dict[str, tuple],
        current_positions: Dict[str, tuple],
        adjacency: Dict[str, list],
        layer_offsets: Dict[int, float]
    ) -> bool:
        """
        Optimize the X offset of a layer using bisection on the derivative
        of total distance (convex function).
        """
        layer_nodes = layers.get(level, [])
        if not layer_nodes:
            return False

        # Collect derivative terms (only cross-layer edges)
        layer_set = set(layer_nodes)
        terms = []  # (a, dy, weight)
        for nid in layer_nodes:
            if nid not in base_positions:
                continue
            bx, y1 = base_positions[nid]
            for neighbor, weight in adjacency.get(nid, []):
                if neighbor in layer_set:
                    continue
                if neighbor not in current_positions:
                    continue
                x_other, y2 = current_positions[neighbor]
                terms.append((bx - x_other, y1 - y2, float(weight)))

        if not terms:
            return False

        current_offset = layer_offsets.get(level, 0.0)

        def derivative(offset):
            d = 0.0
            for a, dy, w in terms:
                dx = a + offset
                denom = math.sqrt(dx * dx + dy * dy)
                if denom == 0:
                    continue
                d += w * (dx / denom)
            return d

        # Find bracket
        low = current_offset - 20.0
        high = current_offset + 20.0
        for _ in range(8):
            if derivative(low) <= 0:
                break
            low -= (high - low)
        for _ in range(8):
            if derivative(high) >= 0:
                break
            high += (high - low)

        if derivative(low) > 0 or derivative(high) < 0:
            return False

        # Bisection
        for _ in range(48):
            mid = (low + high) / 2.0
            if derivative(mid) < 0:
                low = mid
            else:
                high = mid

        optimal = (low + high) / 2.0
        if abs(optimal - current_offset) <= 0.001:
            return False

        layer_offsets[level] = optimal
        return True

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
        max_radius_x = center_x - CANVAS_MARGIN_LARGE  # Margen desde centro hasta borde (1.25x ICON_WIDTH)
        max_radius_y = center_y - CANVAS_MARGIN_LARGE
        max_safe_radius = min(max_radius_x, max_radius_y)

        # Radios adaptativos basados en espacio disponible
        # Si el canvas es grande, usar radios más grandes; si es pequeño, ajustar
        radius_normal = min(max_safe_radius * 0.5, RADIUS_NORMAL_MAX)  # 50% del radio seguro o 3.125x ICON_WIDTH
        radius_low = min(max_safe_radius * 0.8, RADIUS_LOW_MAX)     # 80% del radio seguro o 4.375x ICON_WIDTH

        # HIGH: grid compacto en centro (sorted by centrality)
        high_elements = sorted(
            by_priority[0],
            key=lambda e: self.sizing.get_centrality_score(e, 0),
            reverse=True
        )
        self._position_grid_center(high_elements, center_x, center_y, spacing=SPACING_XLARGE)

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
            # Obtener anchos reales
            widths = []
            for elem in elems:
                width, height = self.sizing.get_element_size(elem)
                widths.append(width)

            # Calcular ancho total con spacing entre elementos
            spacing_between = SPACING_SMALL
            total_width = sum(widths) + (len(elems) - 1) * spacing_between
            start_x = (layout.canvas['width'] - total_width) / 2

            # Posicionar considerando anchos reales
            current_x = start_x
            for i, elem in enumerate(elems):
                elem['x'] = current_x
                current_x += widths[i] + spacing_between

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
        padding = container.get('padding', CONTAINER_PADDING)
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
                label_height = len(lines) * TEXT_LINE_HEIGHT  # 18px por línea
                icon_height = CONTAINER_ICON_HEIGHT  # Altura del icono del contenedor
                header_height = max(CONTAINER_ICON_HEIGHT, label_height)

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
            label_height = len(lines) * TEXT_LINE_HEIGHT + 10
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
        padding = container.get('padding', CONTAINER_PADDING)

        # Calcular espacio del header del contenedor
        header_height = 0
        if container.get('label'):
            label_text = container['label']
            lines = label_text.split('\n')
            label_height = len(lines) * TEXT_LINE_HEIGHT  # 18px por línea
            icon_height = CONTAINER_ICON_HEIGHT  # Altura del icono del contenedor
            header_height = max(CONTAINER_ICON_HEIGHT, label_height)

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

            spacing = GRID_SPACING_SMALL

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
                    # Calcular altura real de la etiqueta basándose en número de líneas
                    label_lines = elem['label'].split('\n')
                    label_height = len(label_lines) * 18  # 18px por línea
                    # La etiqueta está típicamente 15px debajo del ícono
                    elem_bottom += LABEL_OFFSET_VERTICAL + label_height  # offset + altura de etiqueta

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
            label_width = max_line_len * TEXT_CHAR_WIDTH  # 8px por carácter
            label_height = len(lines) * TEXT_LINE_HEIGHT  # 18px por línea

            # El icono del contenedor tiene 50px de altura
            icon_height = CONTAINER_ICON_HEIGHT

            # El header ocupa el máximo entre icono y etiqueta
            header_height = max(CONTAINER_ICON_HEIGHT, label_height)

            # Calcular ancho necesario considerando que la etiqueta está a la derecha del ícono
            # Etiqueta comienza en: 10 (margen) + 80 (ícono) + 10 (margen) = 100
            label_x_position = CONTAINER_ICON_X + ICON_WIDTH + CONTAINER_PADDING
            label_required_width = label_x_position + label_width + CONTAINER_PADDING  # posición + ancho + margen derecho

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

