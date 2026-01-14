"""
AutoLayoutOptimizer - Implementación del optimizador automático v2.1

Este optimizador implementa la estrategia de resolución de colisiones en 3 fases:
1. Reubicar etiquetas a posiciones alternativas
2. Mover elementos de baja prioridad
3. Expandir canvas dinámicamente

Características:
- Análisis de grafo (niveles, grupos, prioridades)
- Detección de colisiones precisas
- Movimiento inteligente de elementos
- Selección del mejor candidato entre iteraciones
"""

from copy import deepcopy
from typing import List, Tuple, Optional
from AlmaGag.layout.optimizer_base import LayoutOptimizer
from AlmaGag.layout.layout import Layout
from AlmaGag.layout.sizing import SizingCalculator
from AlmaGag.layout.auto_positioner import AutoLayoutPositioner
from AlmaGag.layout.geometry import GeometryCalculator
from AlmaGag.layout.collision import CollisionDetector
from AlmaGag.layout.graph_analysis import GraphAnalyzer
from AlmaGag.layout.container_calculator import ContainerCalculator
from AlmaGag.routing.router_manager import ConnectionRouterManager
from AlmaGag.config import ICON_WIDTH, ICON_HEIGHT


class AutoLayoutOptimizer(LayoutOptimizer):
    """
    Implementación del optimizador automático v2.1.

    Estrategia de optimización:
    - Fase 0: Auto-routing de conexiones (SDJF v2.1)
    - Fase 1: Reubicar etiquetas (más rápido, menos invasivo)
    - Fase 2: Mover elementos (más efectivo, más costoso)
    - Fase 3: Expandir canvas (último recurso)

    Attributes:
        geometry (GeometryCalculator): Calculadora geométrica
        collision_detector (CollisionDetector): Detector de colisiones
        graph_analyzer (GraphAnalyzer): Analizador de grafos
        router_manager (ConnectionRouterManager): Gestor de routing de conexiones
        POSITIONS (List[str]): Posiciones posibles para etiquetas
    """

    POSITIONS = ['bottom', 'right', 'top', 'left']

    def __init__(self, verbose: bool = False):
        """
        Inicializa el optimizador.

        Args:
            verbose: Si True, imprime información de debug
        """
        super().__init__(verbose)
        self.sizing = SizingCalculator()
        self.geometry = GeometryCalculator(self.sizing)
        self.collision_detector = CollisionDetector(self.geometry)
        self.graph_analyzer = GraphAnalyzer()
        self.positioner = AutoLayoutPositioner(self.sizing, self.graph_analyzer)
        self.container_calculator = ContainerCalculator(self.sizing, self.geometry)
        self.router_manager = ConnectionRouterManager()

    def analyze(self, layout: Layout) -> None:
        """
        Analiza el grafo y escribe características en el layout.

        Calcula y escribe en layout:
        - graph: Grafo de adyacencia
        - levels: Niveles verticales
        - groups: Grupos conectados
        - priorities: Prioridades calculadas

        Args:
            layout: Layout a analizar (modificado in-place)
        """
        layout.graph = self.graph_analyzer.build_graph(
            layout.elements,
            layout.connections
        )
        layout.levels = self.graph_analyzer.calculate_levels(layout.elements)
        layout.groups = self.graph_analyzer.identify_groups(
            layout.graph,
            layout.elements
        )
        layout.priorities = self.graph_analyzer.calculate_priorities(
            layout.elements,
            layout.graph
        )

    def evaluate(self, layout: Layout) -> int:
        """
        Evalúa colisiones y cachea resultados en layout.

        Args:
            layout: Layout a evaluar

        Returns:
            int: Número de colisiones detectadas
        """
        count, pairs = self.collision_detector.detect_all_collisions(layout)
        layout._collision_count = count
        layout._collision_pairs = pairs
        return count

    def optimize(self, layout: Layout, max_iterations: int = 10) -> Layout:
        """
        Optimiza layout con selección del mejor candidato.

        Flujo:
        0. Auto-layout para coordenadas faltantes (SDJF v2.0)
        0.5. Auto-routing de conexiones (SDJF v2.1)
        1. Analizar layout inicial
        2. Calcular posiciones iniciales
        3. Evaluar colisiones iniciales
        4. Iterar:
            a. Crear copia del layout actual (candidato)
            b. Aplicar estrategia (relocate labels / move elements)
            c. Evaluar colisiones del candidato
            d. Si es mejor, guardar como best_layout
        5. Retornar el mejor layout encontrado

        Args:
            layout: Layout inicial (NO se modifica)
            max_iterations: Número máximo de iteraciones

        Returns:
            Layout: Mejor layout encontrado
        """
        # Trabajar sobre una copia inicial
        current = layout.copy()

        # 0. Auto-layout para elementos sin coordenadas (SDJF v2.0)
        #    NOTA: Debe hacerse ANTES del análisis para que las prioridades
        #    se calculen correctamente y el posicionador las use
        self.analyze(current)  # Análisis preliminar para prioridades
        self.positioner.calculate_missing_positions(current)

        # 0.5. Calcular dimensiones de contenedores (v2.1 FIX)
        #      Los contenedores deben tener dimensiones ANTES de routing y optimización
        #      para que se consideren como obstáculos reales
        self.container_calculator.update_container_dimensions(current)
        self._log("Dimensiones de contenedores calculadas")

        # 0.6. Auto-routing de conexiones (SDJF v2.1)
        #      Calcula paths para todas las conexiones después de posicionar elementos
        #      IMPORTANTE: Asignar sizing al layout para que routers puedan obtener tamaños correctos
        current.sizing = self.sizing
        self.router_manager.calculate_all_paths(current)
        self._log("Routing de conexiones calculado")

        # 1. Análisis de grafo (re-analizar después de auto-layout y contenedores)
        self.analyze(current)

        # 2. Posiciones iniciales de etiquetas
        self._calculate_initial_positions(current)

        # 2.5. CRÍTICO: Recalcular contenedores AHORA que las etiquetas tienen posición
        #      En línea 144 se calcularon solo con íconos (label_positions vacío)
        #      Ahora recalculamos incluyendo las etiquetas
        self.container_calculator.update_container_dimensions(current)
        self._log("Dimensiones de contenedores recalculadas (incluyendo etiquetas)")

        # 2.6. CRÍTICO: Recalcular routing DESPUÉS de actualizar contenedores
        #      Los contenedores expandidos cambian los obstáculos → rutas deben actualizarse
        self.router_manager.calculate_all_paths(current)
        self._log("Routing recalculado después de actualizar contenedores")

        # 2.7. NUEVO: Verificar si canvas es suficiente y expandir si es necesario
        #      Esto debe hacerse DESPUÉS de calcular contenedores finales
        #      para que el canvas acomode todo desde el inicio
        recommended_canvas = current.get_recommended_canvas()
        if (recommended_canvas['width'] > current.canvas['width'] or
            recommended_canvas['height'] > current.canvas['height']):
            old_canvas = current.canvas.copy()
            current.canvas = recommended_canvas
            self._log(f"Canvas expandido automaticamente: "
                      f"{old_canvas['width']}x{old_canvas['height']} -> "
                      f"{recommended_canvas['width']}x{recommended_canvas['height']}")

            # Recalcular routing con el nuevo canvas
            self.router_manager.calculate_all_paths(current)
            self._log("Routing recalculado con canvas expandido")

        # 3. Evaluación inicial
        initial_collisions = self.evaluate(current)

        self._log(f"Colisiones iniciales: {initial_collisions}")
        self._log(f"Niveles: {len(set(current.levels.values()))}, "
                  f"Grupos: {len(current.groups)}")

        # Prioridades para debug
        if self.verbose:
            priority_counts = {'high': 0, 'normal': 0, 'low': 0}
            for priority_val in current.priorities.values():
                priority_name = self.graph_analyzer.get_priority_name(priority_val)
                priority_counts[priority_name] += 1
            self._log(f"Prioridades: {priority_counts['high']} high, "
                      f"{priority_counts['normal']} normal, "
                      f"{priority_counts['low']} low")

        # Guardar mejor configuración
        best_layout = current
        min_collisions = initial_collisions
        moved_elements = []

        # 4. Optimización iterativa
        for iteration in range(max_iterations):
            if min_collisions == 0:
                break

            # Crear candidato (copia)
            candidate = best_layout.copy()

            # Estrategia A: Reubicar etiquetas
            improved = self._try_relocate_labels(candidate)

            if not improved:
                # Estrategia B: Mover elementos (con pesos SDJF v2.0)
                collision_pairs = candidate._collision_pairs or []
                victim_id = self._select_element_to_move_weighted(candidate, collision_pairs)

                if victim_id and victim_id not in moved_elements:
                    dx, dy = self._calculate_move_direction(candidate, victim_id)

                    # Expandir canvas si el movimiento lo requiere
                    elem = candidate.elements_by_id.get(victim_id)
                    if elem and 'x' in elem and 'y' in elem:
                        # Escalar movimiento por peso inverso (SDJF v2.0)
                        # Elementos pesados (hp/wp > 1.0) se mueven menos
                        weight = self.sizing.get_element_weight(elem)
                        scaled_dx = int(dx / weight) if weight > 0 else dx
                        scaled_dy = int(dy / weight) if weight > 0 else dy

                        new_x = elem['x'] + scaled_dx
                        new_y = elem['y'] + scaled_dy
                        self._ensure_canvas_fits(
                            candidate,
                            new_x + ICON_WIDTH + 150,
                            new_y + ICON_HEIGHT + 100
                        )

                        self._shift_element(candidate, victim_id, scaled_dx, scaled_dy)
                        moved_elements.append(victim_id)

                        # Recalcular después de mover
                        candidate.invalidate_collision_cache()
                        self._recalculate_structures(candidate)
                else:
                    # Estrategia C: Expandir canvas
                    candidate.canvas = candidate.get_recommended_canvas()
                    break

            # Evaluar candidato
            collisions = self.evaluate(candidate)

            # Guardar si es mejor
            if collisions < min_collisions:
                best_layout = candidate
                min_collisions = collisions

                self._log(f"Iteración {iteration + 1}: {collisions} colisiones")

        if self.verbose and min_collisions > 0:
            self._log(f"[WARN] {min_collisions} colisiones no resueltas (inicial: {initial_collisions})")

            # Mostrar info de canvas expandido
            if (best_layout.canvas['width'] > layout.canvas['width'] or
                    best_layout.canvas['height'] > layout.canvas['height']):
                self._log(f"Canvas expandido a {best_layout.canvas['width']}x{best_layout.canvas['height']}")

        return best_layout

    def _calculate_initial_positions(self, layout: Layout) -> None:
        """
        Calcula posiciones iniciales de todas las etiquetas.

        v2.0: Ordena por prioridad para que elementos importantes
        obtengan sus posiciones preferidas primero.

        Modifica layout.label_positions y layout.connection_labels in-place.

        Args:
            layout: Layout con elementos y conexiones
        """
        # Calcular posiciones de etiquetas de conexiones primero
        for conn in layout.connections:
            if conn.get('label'):
                key = f"{conn['from']}->{conn['to']}"
                layout.connection_labels[key] = self.geometry.get_connection_center(
                    layout,
                    conn
                )

        # Filtrar contenedores SIN dimensiones calculadas
        # (Contenedores con dimensiones se tratan como elementos normales)
        normal_elements = [
            e for e in layout.elements
            if 'contains' not in e or e.get('_is_container_calculated', False)
        ]

        # Ordenar elementos por prioridad (high primero)
        sorted_elements = sorted(
            normal_elements,
            key=lambda e: layout.priorities.get(e['id'], 1)
        )

        # Calcular posiciones de etiquetas de íconos en orden de prioridad
        for elem in sorted_elements:
            if elem.get('label'):
                preferred = elem.get('label_position', 'bottom')
                pos = self._find_best_label_position(layout, elem, preferred)
                layout.label_positions[elem['id']] = pos

    def _try_relocate_labels(self, layout: Layout) -> bool:
        """
        Intenta reubicar etiquetas con colisiones a otras posiciones.

        Modifica layout.label_positions in-place.

        Args:
            layout: Layout a optimizar

        Returns:
            bool: True si se mejoró alguna posición
        """
        improved = False

        for elem in layout.elements:
            if not elem.get('label'):
                continue

            elem_id = elem['id']
            current_collisions = self.collision_detector.count_element_collisions(
                layout,
                elem_id
            )

            if current_collisions == 0:
                continue

            # Probar otras posiciones
            current_pos = layout.label_positions.get(elem_id)
            if not current_pos:
                continue

            current_position_name = current_pos[3]
            best_collisions = current_collisions
            best_pos = current_pos

            for pos_name in self.POSITIONS:
                if pos_name == current_position_name:
                    continue

                # Temporalmente cambiar posición
                num_lines = len(elem.get('label', '').split('\n'))
                test_pos = self.geometry.get_text_coords(elem, pos_name, num_lines)
                layout.label_positions[elem_id] = test_pos

                new_collisions = self.collision_detector.count_element_collisions(
                    layout,
                    elem_id
                )

                if new_collisions < best_collisions:
                    best_collisions = new_collisions
                    best_pos = test_pos

            # Restaurar mejor posición
            layout.label_positions[elem_id] = best_pos
            if best_collisions < current_collisions:
                improved = True

        if improved:
            layout.invalidate_collision_cache()

        return improved

    def _find_best_label_position(
        self,
        layout: Layout,
        element: dict,
        preferred: str = 'bottom'
    ) -> Tuple[float, float, str, str]:
        """
        Encuentra la mejor posición para una etiqueta.

        Considera colisiones con:
        - Otros íconos
        - Etiquetas de conexiones
        - Etiquetas de otros íconos
        - Líneas de conexión

        Args:
            layout: Layout actual
            element: Elemento del diagrama
            preferred: Posición preferida

        Returns:
            Tuple: (x, y, anchor, position)
        """
        label = element.get('label', '')
        if not label:
            return None

        num_lines = len(label.split('\n'))

        # Ordenar posiciones con preferida primero
        positions = list(self.POSITIONS)
        if preferred in positions:
            positions.remove(preferred)
            positions.insert(0, preferred)

        # Recolectar bboxes de otros elementos (íconos y etiquetas existentes)
        # Incluir contenedores con dimensiones calculadas
        occupied_bboxes = []
        for elem in layout.elements:
            if elem['id'] != element['id']:
                # Incluir contenedores CON dimensiones, excluir sin dimensiones
                if 'contains' in elem and not elem.get('_is_container_calculated', False):
                    continue
                occupied_bboxes.append(self.geometry.get_icon_bbox(elem))

        # Añadir etiquetas de conexiones
        for conn in layout.connections:
            bbox = self.geometry.get_connection_label_bbox(layout, conn)
            if bbox:
                occupied_bboxes.append(bbox)

        # Añadir etiquetas de otros íconos ya calculadas
        for elem_id, pos_info in layout.label_positions.items():
            if elem_id != element['id']:
                other_elem = layout.elements_by_id.get(elem_id)
                if other_elem:
                    bbox = self.geometry.get_label_bbox(other_elem, pos_info[3])
                    if bbox:
                        occupied_bboxes.append(bbox)

        # Recolectar líneas de conexión
        connection_lines = []
        for conn in layout.connections:
            endpoints = self.geometry.get_connection_endpoints(layout, conn)
            if endpoints:
                connection_lines.append(endpoints)

        # Probar cada posición
        for pos in positions:
            text_bbox = self.geometry.get_label_bbox(element, pos)
            if text_bbox is None:
                continue

            has_collision = False

            # Verificar colisión con bboxes
            for occ_bbox in occupied_bboxes:
                if self.geometry.rectangles_intersect(text_bbox, occ_bbox):
                    has_collision = True
                    break

            # Verificar colisión con líneas de conexión
            if not has_collision:
                for line in connection_lines:
                    if self.geometry.line_intersects_rect(line, text_bbox):
                        has_collision = True
                        break

            if not has_collision:
                return self.geometry.get_text_coords(element, pos, num_lines)

        # Si todas colisionan, usar preferida
        return self.geometry.get_text_coords(element, preferred, num_lines)

    def _select_element_to_move(
        self,
        layout: Layout,
        collision_pairs: List[Tuple]
    ) -> Optional[str]:
        """
        Selecciona el elemento de MENOR prioridad para mover.

        Reglas:
        1. Si colisión es label_vs_line → mover el elemento de la etiqueta
        2. Si colisión es label_vs_icon → mover el de menor prioridad
        3. Nunca mover elementos con prioridad 'high' (valor 0)

        Args:
            layout: Layout actual
            collision_pairs: Lista de (id1, id2, collision_type)

        Returns:
            Optional[str]: ID del elemento a mover, o None
        """
        candidates = {}

        for id1, id2, coll_type in collision_pairs:
            if 'label_vs_line' in coll_type:
                # La etiqueta (id1) debe moverse
                elem = layout.elements_by_id.get(id1)
                if elem:
                    priority = layout.priorities.get(id1, 1)
                    if priority > 0:  # No mover high priority
                        candidates[id1] = priority
            else:
                # Mover el de menor prioridad
                for eid in [id1, id2]:
                    if '->' in str(eid):  # Es una conexión, no elemento
                        continue
                    elem = layout.elements_by_id.get(eid)
                    if elem:
                        priority = layout.priorities.get(eid, 1)
                        if priority > 0:
                            candidates[eid] = priority

        if not candidates:
            return None

        # Retornar el de menor prioridad (mayor número = menor prioridad)
        return max(candidates, key=candidates.get)

    def _select_element_to_move_weighted(
        self,
        layout: Layout,
        collision_pairs: List[Tuple]
    ) -> Optional[str]:
        """
        Selecciona elemento a mover considerando PESO (SDJF v2.0).

        Elementos ligeros (hp/wp = 1.0) son candidatos preferidos.
        Elementos pesados (hp/wp > 1.0) se evitan.

        Score = collisions / weight
        Mayor score = mejor candidato (muchas colisiones, poco peso)

        Args:
            layout: Layout actual
            collision_pairs: Lista de (id1, id2, collision_type)

        Returns:
            Optional[str]: ID del elemento a mover, o None
        """
        # Contar colisiones por elemento
        collision_count = {}
        for id1, id2, coll_type in collision_pairs:
            for eid in [id1, id2]:
                if '->' in str(eid):  # Es una conexión, no elemento
                    continue
                collision_count[eid] = collision_count.get(eid, 0) + 1

        # Calcular scores considerando peso
        candidates = {}
        for elem_id, collisions in collision_count.items():
            elem = layout.elements_by_id.get(elem_id)
            if not elem:
                continue

            # Ignorar contenedores sin dimensiones calculadas
            if 'contains' in elem and not elem.get('_is_container_calculated', False):
                continue

            # Ignorar elementos sin coordenadas
            if elem.get('x') is None or elem.get('y') is None:
                continue

            # No mover HIGH priority
            priority = layout.priorities.get(elem_id, 1)
            if priority == 0:
                continue

            # Calcular peso del elemento
            weight = self.sizing.get_element_weight(elem)

            # Score: priorizar muchas colisiones + bajo peso
            score = collisions / weight
            candidates[elem_id] = score

        if not candidates:
            return None

        # Retornar elemento con mayor score
        return max(candidates, key=candidates.get)

    def _calculate_move_direction(
        self,
        layout: Layout,
        element_id: str
    ) -> Tuple[int, int]:
        """
        Determina hacia dónde y cuánto mover un elemento.

        Estrategia:
        1. Calcular espacio libre en cada dirección
        2. Elegir dirección con más espacio (preferir abajo/derecha)
        3. Si no hay espacio suficiente → mover abajo y expandir canvas

        Args:
            layout: Layout actual
            element_id: ID del elemento a mover

        Returns:
            Tuple[int, int]: (dx, dy) desplazamiento recomendado
        """
        elem = layout.elements_by_id.get(element_id)
        if not elem:
            return (0, 0)

        # Calcular espacio libre en cada dirección
        free_space = self._find_free_space(layout, elem)

        # Preferir mover hacia abajo o derecha (más natural en diagramas)
        preferred_order = ['down', 'right', 'left', 'up']

        for direction in preferred_order:
            if free_space[direction] >= 80:
                distance = min(free_space[direction], 100)
                if direction == 'down':
                    return (0, distance)
                elif direction == 'right':
                    return (distance, 0)
                elif direction == 'left':
                    return (-distance, 0)
                elif direction == 'up':
                    return (0, -distance)

        # No hay suficiente espacio → mover abajo y expandir canvas
        return (0, 80)

    def _find_free_space(
        self,
        layout: Layout,
        element: dict
    ) -> dict:
        """
        Calcula cuánto espacio libre hay en cada dirección.

        Args:
            layout: Layout actual
            element: Elemento a evaluar

        Returns:
            dict: {'down': px, 'up': px, 'right': px, 'left': px}
        """
        elem_bbox = self.geometry.get_icon_bbox(element)
        ex1, ey1, ex2, ey2 = elem_bbox

        free = {'down': 999, 'up': 999, 'right': 999, 'left': 999}

        for other in layout.elements:
            if other['id'] == element['id']:
                continue

            other_bbox = self.geometry.get_icon_bbox(other)
            ox1, oy1, ox2, oy2 = other_bbox

            # Espacio abajo (otros elementos debajo que solapan en X)
            if ox1 < ex2 and ox2 > ex1:  # Solapan en X
                if oy1 > ey2:  # Está debajo
                    free['down'] = min(free['down'], oy1 - ey2)

            # Espacio arriba
            if ox1 < ex2 and ox2 > ex1:
                if oy2 < ey1:
                    free['up'] = min(free['up'], ey1 - oy2)

            # Espacio derecha (otros elementos a la derecha que solapan en Y)
            if oy1 < ey2 and oy2 > ey1:  # Solapan en Y
                if ox1 > ex2:
                    free['right'] = min(free['right'], ox1 - ex2)

            # Espacio izquierda
            if oy1 < ey2 and oy2 > ey1:
                if ox2 < ex1:
                    free['left'] = min(free['left'], ex1 - ox2)

        # Considerar bordes del canvas
        free['down'] = min(free['down'], layout.canvas['height'] - ey2 - 100)
        free['right'] = min(free['right'], layout.canvas['width'] - ex2 - 100)
        free['up'] = min(free['up'], ey1 - 50)
        free['left'] = min(free['left'], ex1 - 50)

        return {k: max(0, v) for k, v in free.items()}

    def _shift_element(
        self,
        layout: Layout,
        element_id: str,
        dx: int = 0,
        dy: int = 60
    ) -> None:
        """
        Desplaza un elemento y actualiza índices.

        Modifica layout.elements in-place.

        Args:
            layout: Layout a modificar
            element_id: ID del elemento a desplazar
            dx: Desplazamiento horizontal
            dy: Desplazamiento vertical
        """
        elem = layout.elements_by_id.get(element_id)
        if elem and 'x' in elem and 'y' in elem:
            elem['x'] += dx
            elem['y'] += dy

    def _recalculate_structures(self, layout: Layout) -> None:
        """
        Recalcula todas las estructuras después de mover elementos.

        Actualiza:
        - elements_by_id
        - Dimensiones de contenedores (basándose en nuevas posiciones)
        - Rutas de conexiones (routing optimizado para nuevas posiciones)
        - Análisis de grafo (levels, groups, priorities)
        - Posiciones de etiquetas (recalculadas desde cero)

        Args:
            layout: Layout a recalcular
        """
        layout.elements_by_id = {e['id']: e for e in layout.elements}

        # CRÍTICO: Recalcular routing PRIMERO (antes de contenedores y etiquetas)
        # Las conexiones deben reflejar las nuevas posiciones de elementos
        # Asegurar que layout tenga sizing disponible para routers
        layout.sizing = self.sizing
        self.router_manager.calculate_all_paths(layout)

        self.analyze(layout)
        layout.label_positions = {}
        layout.connection_labels = {}
        self._calculate_initial_positions(layout)

        # CRÍTICO: Recalcular dimensiones de contenedores DESPUÉS de recalcular etiquetas
        # Los contenedores deben reflejar TANTO las nuevas posiciones de elementos
        # COMO las nuevas posiciones de sus etiquetas
        self.container_calculator.update_container_dimensions(layout)

    def _ensure_canvas_fits(
        self,
        layout: Layout,
        needed_x: int,
        needed_y: int
    ) -> None:
        """
        Expande canvas si es necesario para acomodar el movimiento.

        Args:
            layout: Layout a modificar
            needed_x: Coordenada X mínima necesaria
            needed_y: Coordenada Y mínima necesaria
        """
        if needed_x > layout.canvas['width']:
            layout.canvas['width'] = int(needed_x + 50)
        if needed_y > layout.canvas['height']:
            layout.canvas['height'] = int(needed_y + 50)
