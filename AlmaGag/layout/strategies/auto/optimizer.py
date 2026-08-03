"""
AutoLayoutOptimizer - Optimizador automático de layouts

Pipeline de optimización:
0. Auto-layout: posicionar elementos (jerárquico con barycenter + position optimization)
1. Contenedores: calcular dimensiones, centrar, propagar coordenadas
2. Routing: calcular paths de conexiones
3. Iteración: reducir colisiones via reubicación de etiquetas, movimiento de
   elementos, o expansión de canvas (max 10 iteraciones)
"""

import logging
from copy import deepcopy
from typing import List, Tuple, Optional
from AlmaGag.layout.optimizer_base import LayoutOptimizer

logger = logging.getLogger('AlmaGag')
from AlmaGag.layout.layout import Layout
from AlmaGag.layout.sizing import SizingCalculator
from AlmaGag.layout.strategies.auto.positioner import AutoLayoutPositioner
from AlmaGag.layout.geometry import GeometryCalculator
from AlmaGag.layout.collision import CollisionDetector
from AlmaGag.layout.graph_analysis import GraphAnalyzer
from AlmaGag.layout.container_calculator import ContainerCalculator, is_band
from AlmaGag.layout.strategies.auto.routing_policy import AutoRoutingPolicy
from AlmaGag.config import (
    ICON_WIDTH, ICON_HEIGHT,
    CANVAS_MARGIN_XLARGE, CANVAS_MARGIN_LARGE, CANVAS_MARGIN_SMALL,
    MOVEMENT_THRESHOLD, MOVEMENT_MAX_DISTANCE, MOVEMENT_DEFAULT_DY
)
from AlmaGag.utils import extract_item_id
from AlmaGag.layout.offset_optimizer import optimize_group_offsets
from AlmaGag.layout.metrics import count_crossings


class AutoLayoutOptimizer(LayoutOptimizer):
    """
    Optimizador automático de layouts.

    Pipeline:
    0. Auto-layout jerárquico (barycenter, position optimization, escala X global)
    1. Contenedores: dimensiones, centrado, propagación de coordenadas
    2. Routing y canvas desde bounds
    3. Iteración: label relocation → element movement → canvas expansion

    Attributes:
        geometry (GeometryCalculator): Calculadora geométrica
        collision_detector (CollisionDetector): Detector de colisiones
        graph_analyzer (GraphAnalyzer): Analizador de grafos
        routing (AutoRoutingPolicy): Política de routing del algoritmo AUTO
    """

    POSITIONS = ['bottom', 'right', 'top', 'left']

    def __init__(self, verbose: bool = False, visualdebug: bool = False):
        """
        Inicializa el optimizador.

        Args:
            verbose: Si True, imprime información de debug
            visualdebug: Si True, usa TOP_MARGIN grande para área de debug visual
        """
        super().__init__(verbose)
        self.sizing = SizingCalculator()
        self.geometry = GeometryCalculator(self.sizing)
        self.collision_detector = CollisionDetector(self.geometry)
        self.graph_analyzer = GraphAnalyzer()
        self.positioner = AutoLayoutPositioner(self.sizing, self.graph_analyzer, visualdebug=visualdebug)
        self.container_calculator = ContainerCalculator(self.sizing, self.geometry)
        self.routing = AutoRoutingPolicy(self.sizing)
        # Cada algoritmo expone su propio renderer (separación total — WISH-ARCH-002).
        from AlmaGag.layout.strategies.auto.auto_renderer import AutoSVGRenderer
        self.renderer = AutoSVGRenderer(self.geometry)

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

    def optimize(
        self,
        layout: Layout,
        max_iterations: int = 10,
        dump_iterations: bool = False,
        input_file: Optional[str] = None
    ) -> Layout:
        """
        Optimiza layout con selección del mejor candidato.

        Flujo:
        0. Auto-layout jerárquico (barycenter + position optimization)
        1. Contenedores: dimensiones, centrado con etiquetas, propagación
        2. Ajuste post-expansión (desplazar solapamientos con contenedores)
        3. Canvas desde bounds + routing final
        4. Iteración (max 10):
            a. Label relocation (más rápido, menos invasivo)
            b. Element movement (mover elementos con colisiones)
            c. Canvas expansion (último recurso, solo re-rutea)
        5. Retornar el mejor layout encontrado

        Args:
            layout: Layout inicial (NO se modifica)
            max_iterations: Número máximo de iteraciones
            dump_iterations: Si True, guarda snapshots JSON de cada iteración
            input_file: Ruta del archivo .gag de entrada (para nombrar dumps)

        Returns:
            Layout: Mejor layout encontrado
        """
        # Trabajar sobre una copia inicial
        current = layout.copy()

        # Inicializar dumper de iteraciones si está habilitado
        dumper = None
        if dump_iterations:
            from AlmaGag.iteration_debug.iteration_dumper import IterationDumper
            dumper = IterationDumper(input_file=input_file or "unknown.gag")

        # 0. Auto-layout para elementos sin coordenadas (SDJF v2.0)
        #    NOTA: Debe hacerse ANTES del análisis para que las prioridades
        #    se calculen correctamente y el posicionador las use
        self.analyze(current)  # Análisis preliminar para prioridades

        # §N45: si el grafo es una TOPOLOGÍA DE RED (hubs de nubes + ciclos /
        # bidireccionales) y no hay coords manuales, el placement macro es
        # hub-and-spoke: banda central de nubes y sitios alrededor. Los sitios
        # se sintetizan como `near` → §N46 hace el sub-layout de cada uno.
        _net_considerations = getattr(layout, '_considerations', None)
        if _net_considerations is not None:
            from AlmaGag.layout.strategies.auto.network import apply_network_layout
            n_sites = apply_network_layout(current, _net_considerations)
            if n_sites:
                self._capture('topologia-red', current,
                              f'§N45: banda de hubs + {n_sites} sitio(s)')

        # §P60 (gate temprano): el macro-layout banda/periferia sólo aplica si
        # las zonas-área top-level NO traen coordenadas del autor. Se evalúa
        # ANTES del posicionamiento (después todo tiene coords) y se ejecuta
        # en 2.5.55, con las zonas ya resueltas como super-nodos rígidos.
        from AlmaGag.layout.strategies.auto.zones import zones_lack_author_coords
        _p60_eligible = zones_lack_author_coords(current.elements)

        self.positioner.calculate_missing_positions(current)

        # 0.5. Calcular dimensiones de contenedores (v2.1 FIX)
        #      Los contenedores deben tener dimensiones ANTES de routing y optimización
        #      para que se consideren como obstáculos reales
        self.container_calculator.update_container_dimensions(current)
        self._log("Dimensiones de contenedores calculadas")

        # 0.6. Auto-routing de conexiones (necesario antes de calcular label positions)
        self.routing.route(current)
        # Epifanía: primera foto completa (posiciones + contenedores dimensionados
        # + ruteo inicial). Antes de este punto los contenedores no tienen tamaño.
        self._capture('posicionamiento', current,
                      'auto-layout jerárquico (barycenter) + contenedores + ruteo')

        # 1. Análisis de grafo (re-analizar después de auto-layout y contenedores)
        self.analyze(current)

        # 2. Posiciones iniciales de etiquetas
        self._calculate_initial_positions(current)

        # 2.5. CRÍTICO: Recalcular contenedores AHORA que las etiquetas tienen posición
        #      Antes se calcularon solo con íconos (label_positions vacío)
        #      Ahora recalculamos incluyendo las etiquetas y re-aplicando centrado

        # Limpiar flag _resolved para forzar re-cálculo con centrado
        for elem in current.elements:
            if 'contains' in elem and elem.get('_resolved'):
                del elem['_resolved']
                # También resetear coordenadas locales de elementos contenidos
                for ref in elem.get('contains', []):
                    ref_id = extract_item_id(ref)
                    contained = current.elements_by_id.get(ref_id)
                    if contained:
                        if '_local_x' in contained:
                            del contained['_local_x']
                        if '_local_y' in contained:
                            del contained['_local_y']

        # Re-resolver contenedores con centrado
        container_hierarchy = self.positioner._analyze_container_hierarchy(current)
        for container in container_hierarchy.bottom_up_order():
            self.positioner._resolve_container(current, container)

        self._log("Dimensiones de contenedores recalculadas (incluyendo etiquetas)")

        # 2.5.4. CRÍTICO: Propagar coordenadas locales actualizadas (centrado)
        #        El recalculo de contenedores actualiza _local_x/_local_y (centrado)
        #        pero no las propaga a coordenadas globales
        self.positioner._propagate_coordinates_to_contained(current)
        self._log("Coordenadas locales propagadas a elementos contenidos")

        # 2.5.5. NUEVO: Redistribuir elementos primarios DESPUÉS de expandir contenedores
        #        Los contenedores expandidos pueden causar colisiones → redistribuir elementos libres
        self.positioner.recalculate_positions_with_expanded_containers(current)
        self._log("Elementos primarios redistribuidos con contenedores expandidos")
        self._capture('contenedores', current,
                      'dimensiones + centrado con etiquetas + redistribución')

        # 2.5.52. §P60: zonas de servicio a la periferia. Con las zonas ya
        # resueltas y dimensionadas (super-nodos rígidos, P59), la banda
        # principal queda para las operativas (transporte inter-zona) y las
        # de servicio bajan a la fila periférica; los enlaces inter-zona se
        # marcan para rutear por troncales (una por par origen→destino).
        if _p60_eligible:
            from AlmaGag.layout.strategies.auto.zones import apply_zone_banding
            n_svc = apply_zone_banding(
                current, self.positioner._shift_container_subtree,
                considerations=getattr(layout, '_considerations', None))
            if n_svc:
                # la periferia pudo dejar elementos libres pisando zonas
                self.positioner.recalculate_positions_with_expanded_containers(current)
                self._capture('zonas-servicio', current,
                              f'§P60: banda operativa + {n_svc} zona(s) de '
                              f'servicio a periferia')

        # 2.5.55. §N46: `near[]` como ZONA por construcción. Cada grupo near se
        # clusteriza en grilla compacta en su centroide ANTES del canvas y el
        # ruteo — el resto del pipeline trabaja con la zona ya armada, en vez
        # del empujón blando post-hoc que dejaba miembros a ~730px (condestable).
        considerations = getattr(layout, '_considerations', None) or []
        n_zones = 0
        if considerations:
            from AlmaGag.layout.considerations import (
                cluster_near_groups, evict_zone_intruders)
            n_zones = cluster_near_groups(current, considerations)
            if n_zones:
                # intrusos: nodos ajenos que el placement dejó dentro de la
                # zona provocan conectores que perforan el cluster
                evicted = evict_zone_intruders(current)
                # las etiquetas se calcularon con las posiciones pre-cluster
                current.label_positions = {}
                current.connection_labels = {}
                self._calculate_initial_positions(current)
                # Etiqueta de miembro de zona: SIEMPRE centrada bajo el icono
                # (misma convención que §I27 en áreas) — el pitch del cluster ya
                # reservó ese espacio; dejarlas al optimizador las entrevera
                # entre miembros vecinos. Posición estructural, no negociable.
                for e in current.elements:
                    if ((e.get('_near_zone') is not None or e.get('_evicted'))
                            and 'x' in e and e.get('label')):
                        cx = e['x'] + e.get('width', ICON_WIDTH) / 2.0
                        ly = e['y'] + e.get('height', ICON_HEIGHT) + 20
                        current.label_positions[e['id']] = (cx, ly, 'middle', 'bottom')
                self._log(f"§N46: {n_zones} grupo(s) near como zona"
                          f" ({evicted} intruso(s) expulsado(s))")
                self._capture('zonas-near', current,
                              f'{n_zones} zona(s) near por construcción · '
                              f'{evicted} intruso(s) fuera')

        # 2.5.6. CRÍTICO: Recalcular label_positions con las posiciones FINALES de los íconos.
        # Antes de este paso, los labels se calcularon en step 2 con coords originales,
        # pero los íconos se movieron en steps 2.5/2.5.4/2.5.5 (containers
        # recalculados, coords propagadas, redistribución). Sin este recálculo
        # las etiquetas quedan "huérfanas" en posiciones donde el ícono YA NO está
        # (visible en 07-containers como labels REST API/Database al fondo del canvas).
        current.label_positions = {}
        current.connection_labels = {}
        self._calculate_initial_positions(current)
        self._log("Label positions recalculadas tras movimiento de íconos por containers")

        # 2.6. Calcular canvas desde bounds de todos los elementos posicionados
        self._calculate_canvas_from_bounds(current)

        # 2.65. Normalizar a coords no-negativas ANTES del loop de optimización.
        # Sin esto el optimizer ve bboxes con coords negativas (containers
        # cortados por el borde tras 2.5.5) y la heurística de víctimas
        # genera movimientos enormes intentando "alejarse" de un fantasma
        # en coords negativas — termina solapando containers (caso 07-containers
        # donde frontend-module se movía ~357px a la izquierda encima de
        # backend-module). Llamarlo acá deja al optimizer trabajar con
        # un layout sano (BUGS-AUTO-002 / BUGS-AUTO-004).
        self._normalize_to_canvas(current)

        # 2.7. Routing único: calcular paths con canvas y posiciones finales
        self.routing.route(current)
        self._log("Routing calculado")

        # 3. Evaluación inicial
        initial_collisions = self.evaluate(current)

        # Capturar estado inicial para dump
        if dumper:
            dumper.capture_initial_state(current, initial_collisions)

        self._log(f"Colisiones iniciales: {initial_collisions}")
        self._log(f"Niveles: {len(set(current.levels.values()))}, "
                  f"Grupos: {len(current.groups)}")
        self._capture('ruteo-inicial', current,
                      f'canvas desde bounds + routing · {initial_collisions} colisiones')

        # Rescate ①: compactación horizontal por bisección de offset. Desplaza
        # cada nivel (fila) por el offset que minimiza la longitud de conectores.
        # GUARDADA: sólo se adopta si baja los cruces y no sube las colisiones.
        compacted = self._compact_horizontal(current)
        if compacted is not current:
            current = compacted
            initial_collisions = self.evaluate(current)
            self._capture('compactacion', current,
                          f'offset por nivel (rescate ①) · '
                          f'{count_crossings(current)} cruces · {initial_collisions} colisiones')

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

            # Guardar estado antes de aplicar estrategia (para dump)
            layout_before = candidate.copy() if dumper else None
            collisions_before = min_collisions

            # Log de inicio de iteración (verbose)
            if self.verbose:
                self._log(f"Iteración {iteration + 1}/{max_iterations}: probando mejoras...")

            # Variables para rastrear estrategia aplicada
            strategy_type = "unknown"
            strategy_desc = ""
            victim_id = None
            dx = dy = 0

            # Estrategia A: Reubicar etiquetas
            improved = self._try_relocate_labels(candidate)

            if improved:
                strategy_type = "label_relocation"
                strategy_desc = "Reubicación de etiquetas a posiciones alternativas"
                # Only invalidate collision cache - no need for full recalculation
                candidate.invalidate_collision_cache()
            else:
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
                            new_x + ICON_WIDTH + CANVAS_MARGIN_XLARGE,
                            new_y + ICON_HEIGHT + CANVAS_MARGIN_LARGE
                        )

                        self._shift_element(candidate, victim_id, scaled_dx, scaled_dy)
                        moved_elements.append(victim_id)

                        strategy_type = "element_movement"
                        strategy_desc = f"Mover elemento {victim_id} por ({scaled_dx}, {scaled_dy})"

                        # Recalcular después de mover
                        candidate.invalidate_collision_cache()
                        self._recalculate_structures(candidate)
                else:
                    # Estrategia C: Expandir canvas y continuar optimizando
                    old_canvas = candidate.canvas.copy()
                    candidate.canvas = candidate.get_recommended_canvas()

                    strategy_type = "canvas_expansion"
                    strategy_desc = f"Expandir canvas de {old_canvas['width']}x{old_canvas['height']} a {candidate.canvas['width']}x{candidate.canvas['height']}"

                    # Only re-route (positions unchanged) and invalidate cache
                    candidate.invalidate_collision_cache()
                    self.routing.route(candidate)
                    # Do NOT reset moved_elements - keep tracking to avoid re-moving
                    if self.verbose:
                        self._log(f"  Canvas expandido")

            # Evaluar candidato
            collisions = self.evaluate(candidate)

            # Determinar si se acepta y si es el mejor
            accepted = collisions < min_collisions
            became_best = accepted

            # Capturar iteración para dump
            if dumper:
                strategy_info = self._extract_strategy_info(
                    layout_before,
                    candidate,
                    improved,
                    victim_id,
                    dx,
                    dy,
                    strategy_type,
                    strategy_desc
                )
                dumper.capture_iteration(
                    iteration_num=iteration + 1,
                    layout_before=layout_before,
                    layout_after=candidate,
                    strategy_type=strategy_info[0],
                    strategy_desc=strategy_info[1],
                    changes=strategy_info[2],
                    collisions_before=collisions_before,
                    collisions_after=collisions,
                    accepted=accepted,
                    became_best=became_best
                )

            # Guardar si es mejor
            if collisions < min_collisions:
                prev_collisions = min_collisions
                best_layout = candidate
                min_collisions = collisions
                self._capture(f'iteracion-{iteration + 1}', candidate,
                              f'{strategy_type} · {collisions} colisiones '
                              f'(−{prev_collisions - collisions})')
                if self.verbose:
                    self._log(f"  [OK] Mejora: {collisions} colisiones (reduccion: {prev_collisions - collisions})")
            else:
                if self.verbose:
                    self._log(f"  [--] Sin mejora: {collisions} colisiones (mejor: {min_collisions})")

        if self.verbose and min_collisions > 0:
            self._log(f"[WARN] {min_collisions} colisiones no resueltas (inicial: {initial_collisions})")

            # Mostrar info de canvas expandido
            if (best_layout.canvas['width'] > layout.canvas['width'] or
                    best_layout.canvas['height'] > layout.canvas['height']):
                self._log(f"Canvas expandido a {best_layout.canvas['width']}x{best_layout.canvas['height']}")

        # Normalizar: trasladar todo a coords no-negativas si algo quedó
        # fuera del borde izquierdo/superior (BUGS-AUTO-002).
        self._normalize_to_canvas(best_layout)

        # BUGS-AUTO-006: si labels de iconos contenidos quedan solapados
        # horizontalmente en bottom (caso típico: container estrecho con
        # iconos juntos y labels más anchos que el spacing), escalonar
        # verticalmente y expandir el container para acomodar.
        self._stagger_overlapping_contained_labels(best_layout)
        # WISH-LAYOUT-008/009: el escalonado y la grilla label-aware EXPANDEN
        # contenedores — pueden montar cajas entre sí O sobre elementos
        # libres (invisible para el detector por diseño). Se restauran ambos
        # invariantes antes del re-ruteo final (que verá geometría sana).
        self.positioner.recalculate_positions_with_expanded_containers(
            best_layout)

        # H3: normalizar/escalonar movió iconos y expandió contenedores sin
        # re-rutear → las rutas quedaban obsoletas y cruzaban las cajas ya
        # crecidas. Se re-rutea (obstacle-aware, H2) para que las conexiones
        # rodeen los contenedores en su tamaño final.
        # BUGS-AUTO-009: el re-ruteo es INCONDICIONAL. El guardado que había
        # aquí comparaba las rutas frescas contra rutas RANCIAS
        # (pre-normalización), que el renderer luego re-anclaba dibujando
        # diagonales que ningún evaluador midió — comparación viciada a favor
        # del material viejo. Sobre la geometría final sólo existe un estado
        # medible: el re-ruteado.
        best_layout.invalidate_collision_cache()
        self.routing.route(best_layout)
        # H3: re-rutear invalida posiciones de etiqueta (nota del review) → tras
        # el re-ruteo se reubican las etiquetas de icono que hayan quedado
        # solapadas por las rutas nuevas.
        self._stagger_overlapping_contained_labels(best_layout)
        # WISH-LAYOUT-009: ese stagger EXPANDE contenedores otra vez — si
        # montó cajas (entre sí o sobre libres), se restauran los invariantes
        # y se re-rutea sobre la geometría definitivamente sana.
        self.positioner.recalculate_positions_with_expanded_containers(
            best_layout)
        best_layout.invalidate_collision_cache()
        self.routing.route(best_layout)
        for _ in range(3):
            if not self._try_relocate_labels(best_layout):
                break
            best_layout.invalidate_collision_cache()
        self._capture('reruteo', best_layout,
                      f'rutas obstacle-aware tras layout final · '
                      f'{count_crossings(best_layout)} cruces · '
                      f'{self.evaluate(best_layout)} colisiones')
        min_collisions = self.evaluate(best_layout)

        # Guardar dump final si está habilitado
        if dumper:
            dump_path = dumper.save(best_layout, min_collisions)
            logger.info(f"[DUMP] Iteraciones guardadas en: {dump_path}")
            logger.info(f"       Total iteraciones: {len(dumper.iterations) - 1}")
            logger.info(f"       Colisiones: {initial_collisions} -> {min_collisions}")

        # Rescate ④: consideraciones BLANDAS del usuario (align/avoid). Son
        # intención, no ley: cada una se aplica sólo si no aumenta las colisiones
        # (guarda); la que no se puede cumplir cede y se informa en el log (sin
        # el porqué). Sin `considerations` es un no-op.
        # §N46: `near` ya NO pasa por aquí — se cumple por construcción como
        # zona (paso 2.5.55); si se clusterizó, sólo align/avoid quedan blandas.
        considerations = getattr(layout, '_considerations', None)
        if considerations:
            # §Q65: la afinidad de áreas ya fue consumida por el banding P60 —
            # aplicarla blanda movería la caja de zona sin su subárbol.
            live = [c for c in considerations if not c.get('_zone_affinity')]
            soft = ([c for c in live if c['kind'] != 'near']
                    if n_zones else live)
            from AlmaGag.layout.considerations import apply_considerations, label
            best_layout, unmet = apply_considerations(
                best_layout, soft, self.evaluate, self.routing.route)
            for cons in unmet:
                logger.info(f"[CONSIDERACIONES] no se pudo cumplir: {label(cons)}")
            best_layout.invalidate_collision_cache()
            self._normalize_to_canvas(best_layout)
            self.routing.route(best_layout)
            self._calculate_canvas_from_bounds(best_layout)
            min_collisions = self.evaluate(best_layout)
            met = len(soft) - len(unmet)
            self._capture('consideraciones', best_layout,
                          f'{met}/{len(soft)} consideraciones blandas · '
                          f'{n_zones} zona(s) near · {min_collisions} colisiones')

        # §P60: las troncales inter-zona son ESTRUCTURALES (cero diagonales,
        # H24) — se recalculan sobre la geometría definitiva, después de que
        # las consideraciones blandas (y su re-ruteo) hayan movido lo último.
        from AlmaGag.layout.strategies.auto.zones import route_zone_trunks
        if route_zone_trunks(best_layout):
            best_layout.invalidate_collision_cache()
            min_collisions = self.evaluate(best_layout)

        # §P61: pasada anticolisión GLOBAL sobre el árbol completo — última
        # etapa, con la geometría definitiva (nada se mueve después). Sólo
        # reubica etiquetas: cruces/arista×nodo/tinta no pueden cambiar.
        # WISH-LAYOUT-008: el detector mide SIEMPRE la posición almacenada
        # (medición veraz total), ya no sólo en esta etapa.
        from AlmaGag.layout.strategies.auto.anticollision import (
            global_label_anticollision)
        if global_label_anticollision(best_layout, self.geometry):
            best_layout.invalidate_collision_cache()
        best_layout.invalidate_collision_cache()
        min_collisions = self.evaluate(best_layout)

        self._capture('final', best_layout,
                      f'normalizado + labels escalonados · {min_collisions} colisiones')

        return best_layout

    def _compact_horizontal(self, layout: Layout) -> Layout:
        """Rescate ①: compacta el layout en X desplazando cada nivel (fila) por
        el offset que minimiza la longitud ponderada de conectores (bisección
        convexa). Devuelve un layout NUEVO si mejora, o el MISMO objeto si no.

        Guarda de seguridad — sólo adopta la compactación si:
          - baja el número de cruces (métrica objetivo), y
          - no aumenta las colisiones (métrica primaria de AUTO).

        Bloques que se desplazan juntos: cada CONTENEDOR (con todo su contenido)
        como bloque rígido — así una traslación horizontal no rompe sus
        coordenadas locales — y los nodos LIBRES agrupados por fila visual."""
        positioned = [e for e in layout.elements if 'x' in e and 'y' in e]
        if len(positioned) < 3:
            return layout

        pos = {e['id']: (e['x'] + e.get('width', ICON_WIDTH) / 2.0,
                         e['y'] + e.get('height', ICON_HEIGHT) / 2.0)
               for e in positioned}

        # Membresía en contenedores — BUGS-AUTO-008: por CIERRE transitivo
        # hacia el contenedor TOP-LEVEL. Con la membresía directa, un
        # contenedor anidado quedaba en DOS bloques (el de su padre y el
        # suyo) y `node_group` resolvía por último-gana: offsets distintos
        # para el anidado, sus hijos y el bloque del padre → cizalla que
        # rompe la contención P59.
        containers = [e for e in layout.elements if 'contains' in e]
        parent_of: dict = {}
        for cont in containers:
            for ref in cont.get('contains', []):
                parent_of[extract_item_id(ref)] = cont['id']

        def _top_container(eid):
            seen = set()
            while eid in parent_of and eid not in seen:
                seen.add(eid)
                eid = parent_of[eid]
            return eid

        contained_of: dict = {}
        for cont in containers:
            for ref in cont.get('contains', []):
                contained_of[extract_item_id(ref)] = _top_container(cont['id'])

        # Grupos: cada contenedor TOP-LEVEL + su subárbol COMPLETO = un solo
        # bloque rígido (BUGS-AUTO-008); §N46 zona near = bloque rígido
        # (offsets por fila la cizallarían); libres por fila visual.
        row_h = ICON_HEIGHT
        groups: dict = {}
        top_containers = [c for c in containers if c['id'] not in parent_of]
        for cont in top_containers:
            tid = cont['id']
            members = [tid] + [m for m, top in contained_of.items() if top == tid]
            groups[('cont', tid)] = [m for m in members if m in pos]
        zone_of: dict = {}
        for e in positioned:
            gi = e.get('_near_zone')
            if gi is not None and e['id'] not in contained_of:
                zone_of[e['id']] = gi
                groups.setdefault(('zone', gi), []).append(e['id'])
        for eid, (cx, cy) in pos.items():
            if (eid in contained_of or eid in zone_of
                    or any(eid == c['id'] for c in containers)):
                continue
            groups.setdefault(('row', round(cy / row_h)), []).append(eid)
        if len(groups) < 2:
            return layout

        node_group = {n: k for k, members in groups.items() for n in members}

        adj: dict = {}
        for c in layout.connections:
            a, b = c.get('from'), c.get('to')
            if a in pos and b in pos:
                adj.setdefault(a, []).append((b, 1.0))
                adj.setdefault(b, []).append((a, 1.0))

        offsets = optimize_group_offsets(groups, pos, adj, axis='x')
        if all(abs(v) < 1.0 for v in offsets.values()):
            return layout

        candidate = layout.copy()
        for e in candidate.elements:
            if 'x' in e and e['id'] in node_group:
                off = offsets.get(node_group[e['id']], 0.0)
                e['x'] += off
                # WISH-LAYOUT-008: la etiqueta almacenada viaja con su bloque
                if e['id'] in candidate.label_positions:
                    lx, ly, an, bl = candidate.label_positions[e['id']]
                    candidate.label_positions[e['id']] = (lx + off, ly, an, bl)
        candidate.invalidate_collision_cache()
        # WISH-LAYOUT-008: los offsets por bloque pueden montar contenedores
        # entre sí o sobre libres (solapes que NI la guarda NI el detector
        # ven, por diseño). Los invariantes se restauran antes de evaluar.
        self.positioner.recalculate_positions_with_expanded_containers(
            candidate)
        self._normalize_to_canvas(candidate)
        self.routing.route(candidate)

        # Guarda: adoptar sólo si mejora cruces sin empeorar colisiones.
        if (count_crossings(candidate) < count_crossings(layout) and
                self.evaluate(candidate) <= self.evaluate(layout)):
            self._log("Compactación horizontal (①) adoptada")
            return candidate
        return layout

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
                center = self.geometry.get_connection_center(layout, conn)
                if center:
                    layout.connection_labels[key] = center

        # Filtrar elementos que ya tienen posiciones calculadas
        # (excluir contenedores sin dimensiones y elementos sin coordenadas)
        normal_elements = [
            e for e in layout.elements
            if 'x' in e and ('contains' not in e or e.get('_is_container_calculated', False))
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
            # §N46: la etiqueta de un miembro de zona es estructural (centrada
            # bajo el icono, con espacio reservado por el pitch del cluster).
            if elem.get('_near_zone') is not None or elem.get('_evicted'):
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

            canvas_w = layout.canvas.get('width', 0)
            canvas_h = layout.canvas.get('height', 0)
            parent_container = self._get_parent_container(layout, elem)
            for pos_name in self.POSITIONS:
                if pos_name == current_position_name:
                    continue

                # BUGS-AUTO-005: rechazar posiciones off-canvas y, si el icono
                # está dentro de un container, también fuera del container.
                test_bbox = self.geometry.get_label_bbox(elem, pos_name)
                if test_bbox is not None:
                    x1, y1, x2, y2 = test_bbox
                    if x1 < 0 or y1 < 0 or x2 > canvas_w or y2 > canvas_h:
                        continue
                    if parent_container is not None and not self._label_inside_container(test_bbox, parent_container):
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

    def _outward_label_preference(self, layout: Layout, element: dict, parent_container):
        """
        WISH-LAYOUT-006: sesga el label del hijo MÁS EXTERNO de cada fila
        hacia el borde libre del container, para evitar solapes entre
        hermanos sin invadir a los vecinos.

        - Hijo más a la izquierda de su fila (y hay más de uno) → 'left'.
        - Hijo más a la derecha de su fila → 'right'.
        - Hijos internos o únicos → None (usar default 'bottom').

        Solo se sesga el extremo porque ahí el label apunta a espacio libre
        (entre el icono y el borde del container). Sesgar un icono interno
        pondría su label sobre el vecino. Es además solo una PREFERENCIA:
        `_find_best_label_position` la rechaza si no cabe y vuelve al default.
        """
        if parent_container is None:
            return None
        if 'x' not in parent_container or 'width' not in parent_container:
            return None

        # Recolectar todos los hijos posicionados del container.
        eh = element.get('height', ICON_HEIGHT)
        row_tol = eh * 0.6
        children = []
        for ref in parent_container.get('contains', []):
            sib = layout.elements_by_id.get(extract_item_id(ref))
            if sib is not None and 'x' in sib:
                children.append(sib)
        if len(children) < 2:
            return None

        # Gate: solo sesgar en containers de UNA SOLA fila (bands, grupos
        # simples). En grids multi-fila sesgar el extremo pone el label sobre
        # vecinos de otras filas y empeora R1 (medido en reference-cheatsheet).
        ys = [c.get('y', 0) for c in children]
        if max(ys) - min(ys) > row_tol:
            return None

        xs = [c.get('x', 0) for c in children]
        ex = element.get('x', 0)
        if ex <= min(xs):
            return 'left'
        if ex >= max(xs):
            return 'right'
        return None

    def _get_parent_container(self, layout: Layout, element: dict):
        """Devuelve el container que contiene a `element`, o None."""
        elem_id = element.get('id')
        if not elem_id:
            return None
        for other in layout.elements:
            if 'contains' not in other:
                continue
            for ref in other.get('contains', []):
                ref_id = extract_item_id(ref)
                if ref_id == elem_id:
                    return other
        return None

    def _label_inside_container(self, label_bbox, container, header_h=40):
        """True si el label_bbox cae dentro del container, fuera de su header."""
        if 'x' not in container or 'y' not in container:
            return True  # sin coords, no restringir
        # WISH-LAYOUT-006: las bands no tienen header arriba (el título va
        # lateral rotado), así que no se reserva franja superior.
        if is_band(container):
            header_h = 0
        cx1 = container['x']
        cy1 = container['y']
        cx2 = cx1 + container.get('width', 80)
        cy2 = cy1 + container.get('height', 50)
        x1, y1, x2, y2 = label_bbox
        # debe estar dentro de los bordes y debajo del header
        return x1 >= cx1 and x2 <= cx2 and y1 >= cy1 + header_h and y2 <= cy2

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

        # BUGS-AUTO-005: si el icono está contenido, el label debe quedar
        # dentro del container (y fuera del header). Calculamos el parent
        # una vez aquí; el chequeo concreto se hace por candidato.
        parent_container = self._get_parent_container(layout, element)

        positions = list(self.POSITIONS)
        if preferred in positions:
            positions.remove(preferred)
            positions.insert(0, preferred)

        # WISH-LAYOUT-006: para un hijo en el extremo de una fila de container,
        # cuando la posición preferida ('bottom') colisione, probar PRIMERO el
        # lado hacia afuera del centro (el extremo izq → 'left', der → 'right').
        # Solo reordena el fallback; no cambia la preferida, así que no degrada
        # los casos donde 'bottom' ya funciona.
        outward = self._outward_label_preference(layout, element, parent_container)
        # Solo reordenar si outward NO es ya la preferida (si lo es, ya está
        # en el índice 0 y moverla la degradaría).
        if outward in positions and positions[0] != outward:
            positions.remove(outward)
            positions.insert(1, outward)

        # Recolectar bboxes de otros elementos (íconos y etiquetas existentes)
        # BUGS-AUTO-005: los containers son fondos semi-transparentes — los
        # labels viven legítimamente dentro de ellos. Si se incluyen, el
        # optimizador termina prefiriendo posiciones FUERA del container que
        # también caen fuera del canvas (ej: auto_opt → label en x negativo).
        # Excluirlos siempre, igual que el fix BUGS-AUTO-003 en
        # label_intersects_elements y BUGS-AUTO-004 en CollisionDetector.
        occupied_bboxes = []
        for elem in layout.elements:
            if elem['id'] == element['id']:
                continue
            if 'contains' in elem:
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
        canvas_w = layout.canvas.get('width', 0)
        canvas_h = layout.canvas.get('height', 0)
        for pos in positions:
            text_bbox = self.geometry.get_label_bbox(element, pos)
            if text_bbox is None:
                continue

            # BUGS-AUTO-005: rechazar posiciones que caen fuera del canvas.
            # Sin esto, posiciones "libres de colisión" pero off-canvas (ej:
            # label a la izquierda de un icono pegado al borde) ganaban sobre
            # posiciones dentro del canvas con leve colisión.
            x1, y1, x2, y2 = text_bbox
            if x1 < 0 or y1 < 0 or x2 > canvas_w or y2 > canvas_h:
                continue

            # BUGS-AUTO-005: si el icono vive dentro de un container, el label
            # también debe quedar dentro (excluyendo el header donde está el
            # label del container).
            if parent_container is not None and not self._label_inside_container(text_bbox, parent_container):
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

            # §N46: los miembros de zona near no se mueven individualmente —
            # la zona es un bloque por construcción (moverlos la desarma).
            if elem.get('_near_zone') is not None:
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
            if free_space[direction] >= MOVEMENT_THRESHOLD:
                distance = min(free_space[direction], MOVEMENT_MAX_DISTANCE)
                if direction == 'down':
                    return (0, distance)
                elif direction == 'right':
                    return (distance, 0)
                elif direction == 'left':
                    return (-distance, 0)
                elif direction == 'up':
                    return (0, -distance)

        # No hay suficiente espacio → mover abajo y expandir canvas
        return (0, MOVEMENT_THRESHOLD)

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
        free['down'] = min(free['down'], layout.canvas['height'] - ey2 - CANVAS_MARGIN_LARGE)
        free['right'] = min(free['right'], layout.canvas['width'] - ex2 - CANVAS_MARGIN_LARGE)
        free['up'] = min(free['up'], ey1 - CANVAS_MARGIN_SMALL)
        free['left'] = min(free['left'], ex1 - CANVAS_MARGIN_SMALL)

        return {k: max(0, v) for k, v in free.items()}

    def _shift_element(
        self,
        layout: Layout,
        element_id: str,
        dx: int = 0,
        dy: int = int(MOVEMENT_DEFAULT_DY)
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

        Actualiza (en orden):
        1. elements_by_id (mapa de acceso rápido)
        2. Rutas de conexiones (routing para nuevas posiciones)
        3. Análisis de grafo (levels, groups, priorities)
        4. Posiciones de etiquetas (recalculadas desde cero)
        5. Contenedores: re-resolución con centrado + propagación de coordenadas

        Args:
            layout: Layout a recalcular
        """
        layout.elements_by_id = {e['id']: e for e in layout.elements}

        # §P61: contenedores PRIMERO, ruteo y etiquetas DESPUÉS. El orden viejo
        # ruteaba primero "para reflejar las nuevas posiciones" y luego la
        # re-resolución de contenedores volvía a mover a los contenidos: cada
        # iteración del loop dejaba rancios los paths (y etiquetas) de todo
        # miembro de contenedor, y el guardado H3 comparaba rutas frescas
        # contra ese material rancio.

        # Recalcular contenedores con centrado (igual que en optimize())
        # Limpiar flag _resolved para forzar re-cálculo con centrado
        for elem in layout.elements:
            if 'contains' in elem and elem.get('_resolved'):
                del elem['_resolved']
                # También resetear coordenadas locales de elementos contenidos
                for ref in elem.get('contains', []):
                    ref_id = extract_item_id(ref)
                    contained = layout.elements_by_id.get(ref_id)
                    if contained:
                        if '_local_x' in contained:
                            del contained['_local_x']
                        if '_local_y' in contained:
                            del contained['_local_y']

        # Re-resolver contenedores con centrado
        container_hierarchy = self.positioner._analyze_container_hierarchy(layout)
        for container in container_hierarchy.bottom_up_order():
            self.positioner._resolve_container(layout, container)

        # Propagar coordenadas locales actualizadas (centrado)
        self.positioner._propagate_coordinates_to_contained(layout)

        # WISH-LAYOUT-008/009: los invariantes «contenedores sin solape»
        # (BUGS-AUTO-004) y «ningún libre sobre un contenedor» deben
        # sobrevivir a los movimientos del loop — la resolución sólo corría
        # en el posicionado inicial y un movimiento posterior podía dejar
        # cajas montadas sin que nadie las separara (el detector no cuenta
        # container-vs-container ni libre-vs-container por diseño).
        self.positioner.recalculate_positions_with_expanded_containers(layout)

        # Ruteo y etiquetas sobre las posiciones DEFINITIVAS de esta iteración
        self.routing.route(layout)
        self.analyze(layout)
        layout.label_positions = {}
        layout.connection_labels = {}
        self._calculate_initial_positions(layout)

    def _stagger_overlapping_contained_labels(self, layout: Layout) -> None:
        """
        Escalona verticalmente labels solapados de iconos contenidos
        (fix BUGS-AUTO-006).

        Cuando un container tiene iconos juntos y los labels son más anchos
        que el spacing entre ellos, en `bottom` se solapan horizontalmente
        (ej: auto_opt y auto_rend a 100px center-to-center, labels de 150px).

        Estrategia: agrupar labels bottom por container, ordenar por x, y
        para cada pareja solapada empujar el segundo a una y más baja
        (escalón). Expandir la altura del container para acomodar.
        """
        GAP = 4
        for container in layout.elements:
            if 'contains' not in container:
                continue
            if 'x' not in container or 'y' not in container:
                continue

            # Recolectar labels bottom de los hijos directos
            children_labels = []
            for ref in container.get('contains', []):
                ref_id = extract_item_id(ref)
                child = layout.elements_by_id.get(ref_id)
                pos = layout.label_positions.get(ref_id)
                if not child or not pos:
                    continue
                if pos[3] != 'bottom':
                    continue
                bb = self.geometry.get_label_bbox(child, 'bottom')
                if bb:
                    children_labels.append((ref_id, child, list(bb), pos))

            if len(children_labels) < 2:
                continue

            # Ordenar por x del bbox
            children_labels.sort(key=lambda t: t[2][0])

            # Resolver solapes: empujar el siguiente hacia abajo cuando hay
            # overlap horizontal con cualquier anterior que esté a la misma y.
            container_bottom = container['y'] + container.get('height', 50)
            for i in range(1, len(children_labels)):
                rid, child, bb, pos = children_labels[i]
                x1, y1, x2, y2 = bb
                # Buscar el max y2 de labels previos cuyo x e y se solapen.
                push_to_y1 = None
                for j in range(i):
                    pid, pchild, pbb, ppos = children_labels[j]
                    px1, py1, px2, py2 = pbb
                    # Overlap real en ambos ejes (no solo x-overlap)
                    if x1 < px2 and px1 < x2 and y1 < py2 and py1 < y2:
                        candidate = py2 + GAP
                        if push_to_y1 is None or candidate > push_to_y1:
                            push_to_y1 = candidate

                if push_to_y1 is None:
                    continue

                # Calcular dy: nueva y del label = push_to_y1 + altura/2
                # (porque text y es baseline, no top)
                label_h = y2 - y1
                # En get_label_bbox para bottom: y1 = text_y - 14, y2 = text_y + text_height - 14
                # Para mover el bbox a empezar en push_to_y1: nueva text_y = push_to_y1 + 14
                old_text_y = pos[1]
                # bbox.y1 = old_text_y - 14, así que dy = push_to_y1 - (old_text_y - 14)
                dy = push_to_y1 - y1
                new_text_y = old_text_y + dy
                layout.label_positions[rid] = (pos[0], new_text_y, pos[2], pos[3])
                # Actualizar bbox local
                children_labels[i] = (rid, child, [x1, y1 + dy, x2, y2 + dy], (pos[0], new_text_y, pos[2], pos[3]))

                # Si el label nuevo se sale del container por abajo, expandir
                new_y2 = y2 + dy
                if new_y2 > container_bottom:
                    extra = new_y2 - container_bottom + GAP
                    container['height'] = container.get('height', 50) + extra
                    container_bottom += extra

    def _normalize_to_canvas(self, layout: Layout) -> None:
        """
        Traslada todo el contenido para que no haya coordenadas negativas
        (fix BUGS-AUTO-002).

        La redistribución de elementos primarios alrededor de contenedores
        expandidos puede empujar elementos/contenedores a x<0 o y<0, dejándolos
        cortados por el borde izquierdo/superior del canvas (ej: container
        backend-module en x=-93 en 07-containers).

        Calcula el bounding box real de TODO (íconos + contenedores), y si el
        mínimo cae por debajo del margen, aplica un shift uniforme a:
        - elementos (x, y)
        - label_positions
        - connection_labels
        Luego re-rutea (regenera computed_path desde las nuevas posiciones) y
        recalcula el canvas.
        """
        positioned = [e for e in layout.elements if 'x' in e and 'y' in e]
        if not positioned:
            return

        min_x = min(e['x'] for e in positioned)
        min_y = min(e['y'] for e in positioned)

        # Solo normalizar si hay contenido cortado por el borde (coords < 0).
        # No re-centrar diagramas que ya caben — eso cambiaría layouts correctos.
        margin = CANVAS_MARGIN_SMALL
        dx = (margin - min_x) if min_x < 0 else 0.0
        dy = (margin - min_y) if min_y < 0 else 0.0

        if dx == 0.0 and dy == 0.0:
            return

        for elem in positioned:
            elem['x'] += dx
            elem['y'] += dy

        shifted_labels = {}
        for eid, pos in layout.label_positions.items():
            lx, ly, anchor, baseline = pos
            shifted_labels[eid] = (lx + dx, ly + dy, anchor, baseline)
        layout.label_positions = shifted_labels

        shifted_conn = {}
        for key, center in layout.connection_labels.items():
            shifted_conn[key] = (center[0] + dx, center[1] + dy)
        layout.connection_labels = shifted_conn

        # Re-rutear regenera computed_path desde las posiciones ya trasladadas.
        self.routing.route(layout)
        self._calculate_canvas_from_bounds(layout)
        self._log(f"Normalizado a canvas: shift ({dx:.0f}, {dy:.0f}) aplicado")

    def _calculate_canvas_from_bounds(self, layout: Layout) -> None:
        """
        Calculate canvas size from actual bounds of all positioned elements.
        Replaces incremental canvas expansion with a single calculation.
        """
        x_max = 0.0
        y_max = 0.0

        for elem in layout.elements:
            if 'x' not in elem or 'y' not in elem:
                continue
            ex = elem['x'] + elem.get('width', ICON_WIDTH)
            ey = elem['y'] + elem.get('height', ICON_HEIGHT)
            # Account for labels below elements
            ey += ICON_HEIGHT  # Approximate label space
            x_max = max(x_max, ex)
            y_max = max(y_max, ey)

        needed_width = int(x_max + CANVAS_MARGIN_LARGE)
        needed_height = int(y_max + CANVAS_MARGIN_LARGE)

        if needed_width > layout.canvas['width'] or needed_height > layout.canvas['height']:
            old_w, old_h = layout.canvas['width'], layout.canvas['height']
            layout.canvas['width'] = max(layout.canvas['width'], needed_width)
            layout.canvas['height'] = max(layout.canvas['height'], needed_height)
            self._log(f"Canvas ajustado: {old_w}x{old_h} -> {layout.canvas['width']}x{layout.canvas['height']}")

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
            layout.canvas['width'] = int(needed_x + CANVAS_MARGIN_SMALL)
        if needed_y > layout.canvas['height']:
            layout.canvas['height'] = int(needed_y + CANVAS_MARGIN_SMALL)

    def _extract_strategy_info(
        self,
        layout_before: Layout,
        layout_after: Layout,
        improved: bool,
        victim_id: Optional[str],
        dx: int,
        dy: int,
        strategy_type: str,
        strategy_desc: str
    ) -> Tuple[str, str, List[dict]]:
        """
        Extrae información detallada sobre la estrategia aplicada.

        Analiza las diferencias entre layout_before y layout_after para
        identificar qué elementos cambiaron y cómo.

        Args:
            layout_before: Layout antes de aplicar estrategia
            layout_after: Layout después de aplicar estrategia
            improved: Si la estrategia mejoró el layout
            victim_id: ID del elemento afectado (si aplica)
            dx: Desplazamiento horizontal aplicado
            dy: Desplazamiento vertical aplicado
            strategy_type: Tipo de estrategia aplicada
            strategy_desc: Descripción de la estrategia

        Returns:
            Tuple[str, str, List[dict]]: (tipo, descripción, lista de cambios)
        """
        changes = []

        # Detectar etiquetas reubicadas
        if strategy_type == "label_relocation":
            for elem_id in layout_after.label_positions:
                pos_before = layout_before.label_positions.get(elem_id)
                pos_after = layout_after.label_positions.get(elem_id)

                if pos_before and pos_after and pos_before != pos_after:
                    changes.append({
                        "type": "label_relocated",
                        "element_id": elem_id,
                        "position_before": pos_before[3],  # position name
                        "position_after": pos_after[3],
                        "coords_before": {"x": round(pos_before[0], 2), "y": round(pos_before[1], 2)},
                        "coords_after": {"x": round(pos_after[0], 2), "y": round(pos_after[1], 2)}
                    })

        # Detectar elementos movidos
        elif strategy_type == "element_movement" and victim_id:
            elem_before = layout_before.elements_by_id.get(victim_id)
            elem_after = layout_after.elements_by_id.get(victim_id)

            if elem_before and elem_after:
                changes.append({
                    "type": "element_moved",
                    "element_id": victim_id,
                    "coords_before": {
                        "x": round(elem_before.get('x', 0), 2),
                        "y": round(elem_before.get('y', 0), 2)
                    },
                    "coords_after": {
                        "x": round(elem_after.get('x', 0), 2),
                        "y": round(elem_after.get('y', 0), 2)
                    },
                    "displacement": {"dx": dx, "dy": dy}
                })

        # Detectar expansión de canvas
        elif strategy_type == "canvas_expansion":
            changes.append({
                "type": "canvas_expanded",
                "canvas_before": {
                    "width": layout_before.canvas['width'],
                    "height": layout_before.canvas['height']
                },
                "canvas_after": {
                    "width": layout_after.canvas['width'],
                    "height": layout_after.canvas['height']
                }
            })

        return (strategy_type, strategy_desc, changes)
