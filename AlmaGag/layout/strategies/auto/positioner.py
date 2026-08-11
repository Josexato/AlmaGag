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
from AlmaGag.layout.container_calculator import is_band, band_label_margin, band_left_region
from AlmaGag.config import (
    ICON_WIDTH, ICON_HEIGHT,
    SPACING_SMALL, SPACING_MEDIUM, SPACING_LARGE, SPACING_XLARGE, SPACING_XXLARGE,
    LABEL_OFFSET_BOTTOM, LABEL_OFFSET_TOP,
    CONTAINER_PADDING, CONTAINER_SPACING, CONTAINER_ELEMENT_SPACING, CONTAINER_ICON_HEIGHT,
    TEXT_LINE_HEIGHT, TEXT_CHAR_WIDTH,
    LABEL_OFFSET_VERTICAL,
    CONTAINER_ICON_X,
    CANVAS_MARGIN_LARGE,
    GRID_SPACING_SMALL,
    CONTAINER_GRID_ROW_SPACING,
    RADIUS_NORMAL_MAX, RADIUS_LOW_MAX,
    TOP_MARGIN_DEBUG, TOP_MARGIN_NORMAL,
)
from AlmaGag.utils import extract_item_id, calculate_label_dimensions

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

        # WISH-LAYOUT-009: sin contenedores no hay nada que hacer, pero SIN
        # LIBRES la resolución contenedor-contenedor sigue siendo necesaria
        # (un diagrama 100% seccionado — p. ej. template dashboard — quedaba
        # con cajas montadas tras crecer la grilla label-aware).
        if not containers:
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

        # WISH-AUTO-010: un libre MULTI-ZONA (todos sus vecinos dentro de
        # contenedores, y en ≥2 contenedores distintos) no se deja caer al
        # fondo del canvas: se coloca en la periferia del bbox de
        # contenedores, en el lado más cercano al baricentro de sus
        # vecinos (mismo espíritu que §P60 con las zonas de servicio).
        self._place_multizone_free_elements(layout, free_elements,
                                            container_bboxes, MARGIN)

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
                    # WISH-LAYOUT-008: la etiqueta almacenada viaja con él
                    self._shift_stored_label(layout, elem['id'], 0,
                                             elem['y'] - old_y)
                    adjustments += 1
                    logger.debug(f"    {elem['id']}: Y {old_y:.1f} → {elem['y']:.1f} (evitar {cid})")
                    # Re-check with updated position
                    ey = elem['y']

        logger.debug(f"  Ajustes realizados: {adjustments}")

        # BUGS-AUTO-004: detectar y resolver solape entre containers.
        # El positioner pone containers en niveles topológicos pero no chequea
        # solape geométrico — frontend (nivel 0) puede terminar encima de
        # backend (nivel 1) si frontend es alto y backend arranca temprano.
        # Empujamos el container con y mayor hacia abajo hasta separarlos.
        self._resolve_container_overlaps(containers, layout, MARGIN)

        logger.debug("[FIN AJUSTE]\n")

        # Mark that hierarchical layout positions are authoritative
        layout._hierarchical_layout_applied = True

        return layout

    def _place_multizone_free_elements(self, layout, free_elements,
                                       container_bboxes, margin):
        """WISH-AUTO-010: libres cuyos vecinos viven TODOS en contenedores
        (≥2 distintos) van a la periferia del bloque de contenedores, al
        lado más cercano al baricentro de sus vecinos — no exiliados al
        fondo con diagonales que cruzan la lámina entera."""
        # miembro (a cualquier profundidad) → contenedor de primer nivel
        parent = {}
        for c in layout.elements:
            for ref in c.get('contains', []):
                parent[extract_item_id(ref)] = c['id']

        def _top(eid):
            seen = set()
            while eid in parent and eid not in seen:
                seen.add(eid)
                eid = parent[eid]
            return eid

        top_ids = {b[4] for b in container_bboxes}
        gx1 = min(b[0] for b in container_bboxes)
        gy1 = min(b[1] for b in container_bboxes)
        gx2 = max(b[2] for b in container_bboxes)
        gy2 = max(b[3] for b in container_bboxes)

        placed_boxes = []
        for elem in free_elements:
            if 'x' not in elem or 'y' not in elem:
                continue
            # sólo aplica al MAL puesto: el que hoy pisa una caja (el
            # ajuste clásico lo iba a exiliar) o el que ya quedó exiliado
            # FUERA del hull de contenedores y lejos de sus vecinos; un
            # libre peninsular bien ubicado no se toca.
            ew, eh = self.sizing.get_element_size(elem)
            overlaps = any(
                elem['x'] < b[2] + margin and elem['x'] + ew > b[0] - margin
                and elem['y'] < b[3] + margin and elem['y'] + eh > b[1] - margin
                for b in container_bboxes)
            outside = (elem['x'] >= gx2 + margin or elem['x'] + ew <= gx1 - margin
                       or elem['y'] >= gy2 + margin or elem['y'] + eh <= gy1 - margin)
            if not overlaps and not outside:
                continue
            nbr_ids = set()
            for conn in layout.connections:
                if conn.get('from') == elem['id']:
                    nbr_ids.add(conn.get('to'))
                elif conn.get('to') == elem['id']:
                    nbr_ids.add(conn.get('from'))
            nbr_ids.discard(None)
            if not nbr_ids:
                continue
            zones = set()
            centers = []
            hosted = True
            for nid in nbr_ids:
                ne = layout.elements_by_id.get(nid)
                if ne is None or 'x' not in ne:
                    hosted = False
                    break
                t = _top(nid)
                if t == nid or t not in top_ids:
                    hosted = False       # vecino libre: caso normal
                    break
                zones.add(t)
                centers.append((ne['x'] + ne.get('width', ICON_WIDTH) / 2.0,
                                ne['y'] + ne.get('height', ICON_HEIGHT) / 2.0))
            if not hosted or len(zones) < 2:
                continue

            bx = sum(p[0] for p in centers) / len(centers)
            by = sum(p[1] for p in centers) / len(centers)
            if not overlaps:
                # exiliado = fuera del hull Y lejos del baricentro (más de
                # media diagonal del hull); si ya está cerca, se respeta
                ecx, ecy = elem['x'] + ew / 2, elem['y'] + eh / 2
                half_diag = ((gx2 - gx1) ** 2 + (gy2 - gy1) ** 2) ** 0.5 / 2
                if ((ecx - bx) ** 2 + (ecy - by) ** 2) ** 0.5 <= half_diag:
                    continue
            w, h = self.sizing.get_element_size(elem)
            # etiqueta de varios renglones: aire extra bajo el icono
            label_h = self._est_contained_label_height(elem)

            def _clamp(v, lo, hi):
                return max(lo, min(v, hi))

            candidates = [
                (_clamp(bx - w / 2, gx1, gx2 - w),
                 gy1 - margin - h - label_h),                       # arriba
                (_clamp(bx - w / 2, gx1, gx2 - w), gy2 + margin),   # abajo
                (gx1 - margin - w - ICON_WIDTH,
                 _clamp(by - h / 2, gy1, gy2 - h)),                 # izquierda
                (gx2 + margin + ICON_WIDTH,
                 _clamp(by - h / 2, gy1, gy2 - h)),                 # derecha
            ]

            def _cost(pos):
                cx, cy = pos[0] + w / 2, pos[1] + h / 2
                return sum(((cx - px) ** 2 + (cy - py) ** 2) ** 0.5
                           for px, py in centers)

            nx, ny = min(candidates, key=_cost)
            # no montarse sobre otro libre ya reubicado
            for (ox1, oy1, ox2, oy2) in placed_boxes:
                if nx < ox2 + margin and nx + w > ox1 - margin \
                        and ny < oy2 + margin and ny + h > oy1 - margin:
                    nx = ox2 + margin
            dx, dy = nx - elem['x'], ny - elem['y']
            if abs(dx) < 0.5 and abs(dy) < 0.5:
                continue
            elem['x'], elem['y'] = nx, ny
            self._shift_stored_label(layout, elem['id'], dx, dy)
            placed_boxes.append((nx, ny, nx + w, ny + h))
            logger.debug(f"    {elem['id']}: libre multi-zona → periferia "
                         f"({nx:.0f}, {ny:.0f}) cerca del baricentro "
                         f"({bx:.0f}, {by:.0f})")

    def _resolve_container_overlaps(self, containers, layout, margin):
        """
        Empuja containers solapados hacia abajo hasta separarlos.

        Estrategia: ordenar por y, y para cada par solapado mover el más bajo
        (mayor y) debajo del más alto. Mover un container implica mover sus
        descendientes (mismo dy) para preservar la composición.
        """
        if len(containers) < 2:
            return

        # BUGS-AUTO-008 (hermano): un contenedor ANIDADO solapa a su ancestro
        # POR DISEÑO — empujarlo "debajo" lo saca de su padre y rompe la
        # contención P59. Sólo se separan pares sin relación de ancestría.
        def _closure(c):
            acc, stack = set(), [extract_item_id(r) for r in c.get('contains', [])]
            by = layout.elements_by_id
            while stack:
                i = stack.pop()
                acc.add(i)
                ch = by.get(i)
                if ch and 'contains' in ch:
                    stack.extend(extract_item_id(r) for r in ch['contains'])
            return acc
        descendants = {c['id']: _closure(c) for c in containers}

        def _related(a, b):
            return b['id'] in descendants[a['id']] or a['id'] in descendants[b['id']]

        for _ in range(len(containers)):  # iterar varias veces por cascada
            changed = False
            sorted_c = sorted(containers, key=lambda c: c.get('y', 0))
            for i, c1 in enumerate(sorted_c):
                if 'x' not in c1 or 'y' not in c1:
                    continue
                c1x1, c1y1 = c1['x'], c1['y']
                c1x2 = c1x1 + c1.get('width', ICON_WIDTH)
                c1y2 = c1y1 + c1.get('height', ICON_HEIGHT)
                for c2 in sorted_c[i+1:]:
                    if 'x' not in c2 or 'y' not in c2:
                        continue
                    c2x1, c2y1 = c2['x'], c2['y']
                    c2x2 = c2x1 + c2.get('width', ICON_WIDTH)
                    c2y2 = c2y1 + c2.get('height', ICON_HEIGHT)
                    overlap_x = c1x1 < c2x2 and c2x1 < c1x2
                    overlap_y = c1y1 < c2y2 and c2y1 < c1y2
                    if overlap_x and overlap_y and not _related(c1, c2):
                        # Mover c2 (el más bajo) debajo de c1
                        dy = (c1y2 + margin) - c2y1
                        if dy > 0:
                            self._shift_container_subtree(c2, layout, 0, dy)
                            changed = True
                            logger.debug(
                                f"    [OVERLAP] {c2['id']}: Y +{dy:.0f} "
                                f"(evitar {c1['id']})"
                            )
            if not changed:
                break

    def _shift_container_subtree(self, container, layout, dx, dy):
        """Mueve un container + todos sus descendientes por (dx, dy).

        WISH-LAYOUT-008: las etiquetas ALMACENADAS viajan con su elemento —
        con medición veraz, una etiqueta que se queda atrás puntúa «limpia»
        en el espacio vacío y el diagrama la dibuja huérfana.
        """
        container['x'] += dx
        container['y'] += dy
        self._shift_stored_label(layout, container['id'], dx, dy)
        # Mover descendientes recursivamente
        for ref in container.get('contains', []):
            ref_id = extract_item_id(ref)
            child = layout.elements_by_id.get(ref_id)
            if child and 'x' in child and 'y' in child:
                if 'contains' in child:
                    self._shift_container_subtree(child, layout, dx, dy)
                else:
                    child['x'] += dx
                    child['y'] += dy
                    self._shift_stored_label(layout, ref_id, dx, dy)

    @staticmethod
    def _shift_stored_label(layout, eid, dx, dy):
        lp = getattr(layout, 'label_positions', None)
        if lp and eid in lp:
            x, y, anchor, baseline = lp[eid]
            lp[eid] = (x + dx, y + dy, anchor, baseline)

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
        resolved_conns = getattr(layout, '_resolved_primary_connections', None) or layout.connections

        # WISH-LAYOUT-014 (V81): un contenedor-FEEDER — toda su relación con
        # el grafo es UNA arista hacia un nodo primario que no es contenedor
        # — no ocupa un rango propio (partía el tronco: dppto→ppto a 635px y
        # el lienzo a 2205). Se aparta del apilado por niveles y al final se
        # coloca AL COSTADO del rango de su destino.
        all_ids = {e['id'] for e in elements}
        by_id = {e['id']: e for e in elements}
        feeders: Dict[str, str] = {}
        for e in elements:
            if 'contains' not in e:
                continue
            nbrs = set()
            for conn in resolved_conns:
                f, t = conn['from'], conn['to']
                if f == e['id'] and t in all_ids:
                    nbrs.add(t)
                elif t == e['id'] and f in all_ids:
                    nbrs.add(f)
            nbrs.discard(e['id'])
            if len(nbrs) == 1:
                target = next(iter(nbrs))
                if 'contains' not in by_id[target]:
                    feeders[e['id']] = target
        if feeders and len(feeders) < len(elements):
            elements = [e for e in elements if e['id'] not in feeders]

        # WISH-LAYOUT-017: un align de eje y entre RANGOS distintos es
        # contrato de FILA (la «capa de resúmenes» del roll-up: cadenas de
        # profundidad desigual cuyos cabezales deben compartir altura). Se
        # honra por PROMOCIÓN DE RANGO: cada miembro sube al rango común
        # factible — todos sus predecesores por debajo y sus sucesores por
        # arriba. Si no existe rango factible, no se toca nada y el audit
        # nombra la violación (mitad honesta, como V79).
        topo = dict(layout.topological_levels)
        _ids_here = {e['id'] for e in elements}
        _preds: Dict[str, List[str]] = {}
        _succs: Dict[str, List[str]] = {}
        for conn in resolved_conns:
            f, t = conn['from'], conn['to']
            if f in _ids_here and t in _ids_here:
                _succs.setdefault(f, []).append(t)
                _preds.setdefault(t, []).append(f)
        for cons in getattr(layout, '_considerations', None) or []:
            if cons.get('kind') != 'align' or cons.get('axis') != 'y':
                continue
            mids = [i for i in cons.get('ids', [])
                    if i in _ids_here and i in topo]
            if len(mids) < 2 or len({topo[i] for i in mids}) < 2:
                continue          # mismo rango: lo resuelve la vía blanda
            lo = max((max((topo[p] for p in _preds.get(i, [])), default=-1) + 1)
                     for i in mids)
            hi = min((min((topo[s] for s in _succs.get(i, [])),
                          default=float('inf')) - 1)
                     for i in mids)
            target = max(lo, max(topo[i] for i in mids))
            if target > hi:
                logger.debug(f"    V17: align y {mids} sin rango común "
                             f"factible (lo={lo}, hi={hi}) — lo nombrará "
                             f"el audit")
                continue
            for i in mids:
                topo[i] = target
            logger.debug(f"    V17: align y {mids} → rango {target} "
                         f"(promoción de fila)")

        # 1. Agrupar por nivel topológico (element dicts, not IDs)
        by_level = {}
        for elem in elements:
            level = topo.get(elem['id'], 0)
            if level not in by_level:
                by_level[level] = []
            by_level[level].append(elem)

        if not by_level:
            return

        # WISH-LAYOUT-012 (V78): `canvas.flow` declara la orientación de
        # lectura. 'up' (roll-ups: de los recursos al consolidado) invierte
        # los rangos — fuentes en la banda inferior, sumidero arriba.
        # Default 'down' (histórico). left/right aún no: warning honesto.
        flow = str((getattr(layout, 'canvas', None) or {})
                   .get('flow', 'down')).lower()
        flow_levels = None
        if flow in ('left', 'right'):
            logger.warning(f"§V78: canvas.flow '{flow}' aún no implementado "
                           f"— se emite con 'down'")
        elif flow == 'up':
            mx = max(by_level.keys())
            by_level = {mx - k: v for k, v in by_level.items()}
            flow_levels = {e['id']: mx - topo.get(e['id'], 0)
                           for e in elements}

        # Build directed graphs for barycenter (use resolved connections)
        elem_ids = {e['id'] for e in elements}
        outgoing = {e['id']: [] for e in elements}
        incoming = {e['id']: [] for e in elements}
        for conn in resolved_conns:
            f, t = conn['from'], conn['to']
            if f in elem_ids and t in elem_ids:
                outgoing[f].append(t)
                incoming[t].append(f)

        # U76/J33: una CADENA PURA (cada nivel con un solo eslabón,
        # consecutivos conectados) apilada por nivel da la tira 1×N que
        # J33/O51 prohíben. Se pliega en serpentina y se saltan barycenter
        # y layer-offset (el orden del recorrido ES el orden; el offset por
        # capa desalinearía los empalmes verticales).
        folded = self._fold_chain_serpentine(by_level, outgoing, incoming)
        if folded:
            by_level, abstract_positions, levels_map = folded
        else:
            levels_map = flow_levels or topo

            # Centrality scores (use resolved connections)
            centrality = self.graph_analyzer.calculate_centrality_scores(
                elements, resolved_conns, topo
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
        MIN_GAP = SPACING_SMALL  # 40px minimum gap between elements
        LEFT_MARGIN = CANVAS_MARGIN_LARGE  # 100px

        # Get real widths
        widths = {}
        for elem in elements:
            w, h = self.sizing.get_element_size(elem)
            widths[elem['id']] = w

        # Ancho estimado de la ETIQUETA centrada bajo el icono: dos hermanos
        # con etiquetas anchas necesitan paso suficiente para que sus labels
        # no se pisen — si no, el optimizador de etiquetas las corre de su
        # icono y la fila se vuelve ambigua (¿de quién es este label?).
        # Cap a 3×ICON_WIDTH: los textos kilométricos ya los maneja el
        # auto-callout, no el espaciado.
        from AlmaGag.utils import calculate_label_dimensions
        label_ws = {}
        for elem in elements:
            lbl = elem.get('label') or ''
            lw = calculate_label_dimensions(lbl)[0] if lbl else 0
            label_ws[elem['id']] = min(lw, ICON_WIDTH * 3)

        # Compute global X scale
        LABEL_GAP = 12  # aire mínimo entre etiquetas vecinas
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
                required = max(
                    items[i][1] + MIN_GAP,
                    (label_ws[items[i][2]] + label_ws[items[i + 1][2]]) / 2.0
                    + LABEL_GAP,
                )
                global_x_scale = max(global_x_scale, required / gap)

        # Normalize abstract X to start at 0
        all_abs_x = [abstract_positions[e['id']][0] for e in elements]
        abs_x_shift = -min(all_abs_x) if all_abs_x else 0

        # Assign Y positions per level.
        # WISH-LAYOUT-016: el gap entre rangos no es la constante de 240 —
        # es lo que de verdad vive en el corredor: el label inferior del
        # rango de arriba + aire para los barridos horizontales (+ el label
        # de conexión si algún enlace entre rangos adyacentes lo trae) + el
        # label superior del rango de abajo. El 240 fijo regalaba 100-180px
        # de aire puro por corredor (lámina TM: 8 corredores, 1891px de
        # alto). Labels de enlaces que saltan >1 rango no reservan aquí:
        # los coloca el optimizador veraz y los vigila §P61.
        def _bottom_stack(elems):
            h = 0.0
            for e in elems:
                if e.get('label') and e.get('label_position', 'bottom') != 'top':
                    _, lh, _ = calculate_label_dimensions(e['label'])
                    h = max(h, LABEL_OFFSET_BOTTOM + lh)
            return h

        def _top_stack(elems):
            h = 0.0
            for e in elems:
                if e.get('label') and e.get('label_position') == 'top':
                    _, lh, _ = calculate_label_dimensions(e['label'])
                    h = max(h, lh + LABEL_OFFSET_TOP)
            return h

        lvl_of = {e['id']: lv for lv, es in by_level.items() for e in es}
        corridor_conn_label: Dict[int, float] = {}
        # OJO: resolved_conns viene sin 'label' (se reconstruye con
        # from/to/weight) — los labels viven en las conexiones ORIGINALES.
        for conn in layout.connections:
            la, lb = lvl_of.get(conn['from']), lvl_of.get(conn['to'])
            if la is None or lb is None or abs(la - lb) != 1:
                continue
            if not conn.get('label'):
                continue
            _, lh, _ = calculate_label_dimensions(conn['label'])
            lo = min(la, lb)
            corridor_conn_label[lo] = max(corridor_conn_label.get(lo, 0.0),
                                          lh + 10.0)

        # Los barridos horizontales del ruteo corren a MITAD del corredor:
        # cada mitad debe librar el stack de labels de su lado (si no, el
        # barrido pisa el label, el optimizador lo echa del 'bottom' y
        # termina sobre el icono). half = stack más alto + separación, con
        # piso de SPACING_MEDIUM para flechas/carriles en rangos sin label.
        LABEL_CLEAR = 12.0
        current_y = TOP_MARGIN
        level_y = {}
        sorted_levels = sorted(by_level.keys())
        for i, level_num in enumerate(sorted_levels):
            if i > 0:
                prev = sorted_levels[i - 1]
                half = max(_bottom_stack(by_level[prev]) + LABEL_CLEAR,
                           _top_stack(by_level[level_num]) + LABEL_CLEAR,
                           SPACING_MEDIUM)
                current_y += 2 * half + corridor_conn_label.get(prev, 0.0)
            level_y[level_num] = current_y
            max_h = max((e.get('height', ICON_HEIGHT) for e in by_level[level_num]), default=ICON_HEIGHT)
            current_y += max_h

        # Assign real X, Y
        for elem in elements:
            eid = elem['id']
            ax = abstract_positions[eid][0]
            level_num = levels_map.get(eid, 0)
            elem['x'] = (ax + abs_x_shift) * global_x_scale + LEFT_MARGIN
            elem['y'] = level_y.get(level_num, TOP_MARGIN)

        # Global centering: shift so x_min = LEFT_MARGIN
        x_min = min(e.get('x', 0) for e in elements) if elements else 0
        correction = LEFT_MARGIN - x_min
        if abs(correction) > 0.5:
            for elem in elements:
                elem['x'] += correction

        # WISH-ROUTE-002 (V80): un eslabón 1:1 entre rangos consecutivos
        # (padre con esa única arista hacia abajo, hijo con esa única
        # arista hacia arriba) se alinea a la MISMA columna — la arista
        # queda vertical pura y el label del padre no convive con un
        # barrido horizontal (repro: pulab→mo, 161px de desfase). Se mueve
        # el extremo de grado 1 hacia el otro, sólo si el hueco existe
        # (pitch label-aware contra los vecinos de su fila).
        deg = {i: len(outgoing.get(i, [])) + len(incoming.get(i, []))
               for i in elem_ids}
        by_row: Dict[int, List[dict]] = {}
        for e in elements:
            by_row.setdefault(levels_map.get(e['id'], 0), []).append(e)

        def _center(e):
            return e['x'] + e.get('width', ICON_WIDTH) / 2.0

        # WISH-LAYOUT-013 (V79): un align de eje x entre RANGOS distintos
        # — CONTRATO del autor: se honra ANTES que los snaps estéticos
        # (V80/casi-alineados), para que una hoja recién alineada a su
        # ancla no bloquee el hueco de la columna del tronco (It9-3).
        # es contrato de COLUMNA (dppto/ppto/constr = un solo tronco). El
        # camino blando no puede honrarlo (mueve todo o nada contra la
        # guarda de colisiones); aquí se honra en el origen: cada miembro
        # va a la columna objetivo (mediana) si TODOS tienen hueco en su
        # fila — pitch label-aware, como el snap V80.
        _x_align_ids = {i for c2 in (getattr(layout, '_considerations', None) or [])
                        if c2.get('kind') == 'align' and c2.get('axis') == 'x'
                        for i in c2.get('ids', [])}

        # WISH-LAYOUT-019 (W88): el journey es primitivo de COLOCACIÓN, no
        # solo overlay. Cada journey cuyos miembros EXCLUSIVOS (no
        # compartidos con otro journey) viven en rangos distintos deriva un
        # contrato de columna implícito — mismo mecanismo que el honor V79,
        # procesado DESPUÉS de los aligns declarados (el autor gana; un
        # miembro de align declarado nunca es empujado por uno derivado).
        # Los nodos compartidos (el consolidado) quedan libres: son la
        # confluencia. El audit sólo vigila lo declarado — un derivado
        # infactible simplemente no se aplica.
        _jcount: Dict[str, int] = {}
        for _j in (getattr(layout, '_journeys', None) or []):
            if isinstance(_j, dict):
                for _i in _j.get('path', []):
                    if isinstance(_i, str):
                        _jcount[_i] = _jcount.get(_i, 0) + 1
        _derived_cons = []
        for _j in (getattr(layout, '_journeys', None) or []):
            if not isinstance(_j, dict):
                continue
            _excl = [i for i in _j.get('path', [])
                     if isinstance(i, str) and _jcount.get(i) == 1
                     and i in by_id and 'x' in by_id[i] and i in levels_map]
            if len(_excl) < 2:
                continue
            if len({levels_map.get(i, 0) for i in _excl}) < 2:
                continue
            _derived_cons.append({'kind': 'align', 'axis': 'x',
                                  'ids': _excl,
                                  '_derived_journey': _j.get('id', '?')})

        def _pair_required(a, b):
            return max((a.get('width', ICON_WIDTH)
                        + b.get('width', ICON_WIDTH)) / 2.0 + MIN_GAP,
                       (label_ws.get(a['id'], 0)
                        + label_ws.get(b['id'], 0)) / 2.0 + LABEL_GAP)

        for cons in list(getattr(layout, '_considerations', None) or []) \
                + _derived_cons:
            if cons.get('kind') != 'align' or cons.get('axis') != 'x':
                continue
            members = [by_id[i] for i in cons.get('ids', [])
                       if i in by_id and 'x' in by_id[i]
                       and i in levels_map]
            if len(members) < 2:
                continue
            if len({levels_map.get(m['id'], 0) for m in members}) < 2:
                continue          # mismo rango: sigue en la vía blanda
            centers = sorted(_center(m) for m in members)
            target = centers[len(centers) // 2]
            # W88: un contrato DERIVADO de journey se honra POR MIEMBRO
            # (mueve los que caben, salta los que no) — el todo-o-nada
            # queda para los aligns DECLARADOS, donde media columna sería
            # peor que ninguna y el audit debe poder nombrar el todo.
            derived = '_derived_journey' in cons
            moves = []
            honorable = True
            member_ids = {m['id'] for m in members}
            # It9-3 + W88: entrada a columna con empuje EN CADENA — los
            # vecinos no-contrato se corren hacia afuera lo mínimo, en
            # cascada (una fila apretada necesita correr 2-3, no 1). Si un
            # eslabón de la cadena es contrato (align x declarado, miembro
            # del grupo o contenedor), el plan muere.
            def _plan_column_entry(m, tgt, row):
                pos = {id(e): _center(e) for e in row}
                pos[id(m)] = tgt
                others = sorted((e for e in row if e is not m),
                                key=lambda e: pos[id(e)])
                plan = []
                for side in (1.0, -1.0):
                    seq = [e for e in others
                           if (pos[id(e)] >= tgt) == (side > 0)]
                    if side < 0:
                        seq = list(reversed(seq))
                    cur, prev = tgt, m
                    for e in seq:
                        req = _pair_required(prev, e)
                        need = cur + side * req
                        if (pos[id(e)] - need) * side < 0:
                            if (e['id'] in _x_align_ids
                                    or e['id'] in member_ids
                                    or 'contains' in e):
                                return None
                            plan.append((e, need - pos[id(e)]))
                            pos[id(e)] = need
                        cur, prev = pos[id(e)], e
                return plan

            for m in members:
                dx = target - _center(m)
                if abs(dx) < 1.0:
                    continue
                row = by_row.get(levels_map.get(m['id'], 0), [])
                m_moves = _plan_column_entry(m, target, row)
                m_ok = m_moves is not None
                if not m_ok:
                    if derived:
                        continue          # este miembro no cabe: se salta
                    honorable = False
                    break
                if derived:
                    for o, odx in m_moves:
                        o['x'] += odx
                    m['x'] += dx
                    moves.append((m, dx))
                else:
                    moves.extend(m_moves)
                    moves.append((m, dx))
            if derived:
                if moves:
                    logger.debug(
                        f"    W88: journey '{cons['_derived_journey']}' — "
                        f"{[m['id'] for m, _ in moves]} a la columna "
                        f"{target:.0f}")
            elif honorable:
                for m, dx in moves:
                    m['x'] += dx
                if moves:
                    logger.debug(f"    V79: align x honrado — "
                                 f"{[m['id'] for m, _ in moves]} → {target:.0f}")

        for _ in range(2):
            for conn in resolved_conns:
                f, t = conn.get('from'), conn.get('to')
                if f not in elem_ids or t not in elem_ids or f == t:
                    continue
                rf = levels_map.get(f, 0)
                rt = levels_map.get(t, 0)
                if rf == rt:
                    continue
                free = anchor = None
                if (abs(rf - rt) == 1 and outgoing.get(f) == [t]
                        and incoming.get(t) == [f]):
                    # eslabón 1:1 puro (V80): mover el extremo de grado 1
                    if deg.get(f) == 1:
                        free, anchor = by_id[f], by_id[t]
                    elif deg.get(t) == 1:
                        free, anchor = by_id[t], by_id[f]
                if free is None:
                    # BUGS-ROUTE-003 (snap casi-alineados): un extremo cuya
                    # ÚNICA arista hacia el otro lado queda a media ranura
                    # (≤40px) de la columna del otro — el jog residual no
                    # aporta información; alinear si la fila tiene hueco y
                    # la columna nueva no pisa iconos de filas intermedias
                    # (repro: rproc a 34px de la columna de resumen, 3
                    # rangos más arriba).
                    if outgoing.get(f) == [t]:
                        cand_free, cand_anchor = by_id[f], by_id[t]
                    elif incoming.get(t) == [f]:
                        cand_free, cand_anchor = by_id[t], by_id[f]
                    else:
                        continue
                    if 'contains' in cand_free:
                        continue
                    if abs(_center(cand_anchor) - _center(cand_free)) \
                            > ICON_WIDTH / 2.0:
                        continue
                    # la vertical nueva debe librar los iconos intermedios
                    new_col = _center(cand_anchor)
                    lo = min(levels_map.get(cand_free['id'], 0),
                             levels_map.get(cand_anchor['id'], 0))
                    hi = max(levels_map.get(cand_free['id'], 0),
                             levels_map.get(cand_anchor['id'], 0))
                    blocked = False
                    for mid_row in range(lo + 1, hi):
                        for other in by_row.get(mid_row, []):
                            clearance = (other.get('width', ICON_WIDTH) / 2.0
                                         + MIN_GAP / 2.0)
                            if abs(new_col - _center(other)) < clearance:
                                blocked = True
                                break
                        if blocked:
                            break
                    if blocked:
                        continue
                    free, anchor = cand_free, cand_anchor
                if free['id'] in _x_align_ids:
                    # It10-6: un miembro de align x DECLARADO no se snapea —
                    # el contrato del autor fija su columna (el snap corría
                    # después del honor y lo deshacía).
                    continue
                dx = _center(anchor) - _center(free)
                if abs(dx) < 1.0:
                    continue
                new_c = _center(free) + dx
                row = by_row.get(levels_map.get(free['id'], 0), [])
                fits = True
                for other in row:
                    if other is free:
                        continue
                    required = max(
                        (free.get('width', ICON_WIDTH)
                         + other.get('width', ICON_WIDTH)) / 2.0 + MIN_GAP,
                        (label_ws.get(free['id'], 0)
                         + label_ws.get(other['id'], 0)) / 2.0 + LABEL_GAP)
                    if abs(new_c - _center(other)) < required:
                        fits = False
                        break
                if fits:
                    free['x'] += dx
                    logger.debug(f"    V80: {free['id']} alineado a la "
                                 f"columna de {anchor['id']} (dx {dx:+.0f})")

        # WISH-LAYOUT-014: cada feeder va al costado del rango de su
        # destino — el lado de la arista más corta — fuera de lo ya tendido
        # en su franja vertical, centrado en su destino. El tronco no se
        # estira y la arista queda corta y perpendicular al borde.
        for fid, tid in feeders.items():
            fc = by_id[fid]
            tgt = by_id.get(tid)
            if tgt is None or 'x' not in tgt:
                continue
            cw = fc.get('width', ICON_WIDTH)
            ch = fc.get('height', ICON_HEIGHT)
            cy = tgt['y'] + tgt.get('height', ICON_HEIGHT) / 2.0 - ch / 2.0
            band = [e for e in elements if 'x' in e
                    and e['y'] < cy + ch + MIN_GAP
                    and e['y'] + e.get('height', ICON_HEIGHT) > cy - MIN_GAP]
            gap = SPACING_XLARGE          # aire para la arista y los labels
            right_x = max((e['x'] + e.get('width', ICON_WIDTH) for e in band),
                          default=tgt['x']) + gap
            left_x = min((e['x'] for e in band), default=tgt['x']) - gap - cw
            t_r = tgt['x'] + tgt.get('width', ICON_WIDTH)
            if right_x - t_r <= tgt['x'] - (left_x + cw):
                fc['x'] = right_x
            else:
                fc['x'] = left_x
            fc['y'] = cy
            logger.debug(f"    {fid}: contenedor-feeder al costado de {tid} "
                         f"({fc['x']:.0f}, {fc['y']:.0f})")

        # Mark hierarchical layout as applied (prevents overwriting by redistribution)
        layout._hierarchical_layout_applied = True

    @staticmethod
    def _fold_chain_serpentine(by_level, outgoing, incoming):
        """U76/J33: grafo-cadena → serpentina boustrophedon.

        Si TODOS los niveles tienen exactamente un elemento, hay ≥5
        eslabones y cada par consecutivo está conectado (en cualquier
        sentido), la cadena se pliega en filas de ceil(sqrt(2n)) columnas
        (lámina apaisada ~φ en vez de tira 1×N). Las filas alternan el
        sentido de recorrido, así cada eslabón queda ADYACENTE al
        siguiente: horizontal dentro de la fila, vertical en el doblez.
        Devuelve (by_level, abstract_positions, levels_map) o None."""
        lv = sorted(by_level.keys())
        if len(lv) < 5 or any(len(by_level[k]) != 1 for k in lv):
            return None
        chain = [by_level[k][0] for k in lv]
        for a, b in zip(chain, chain[1:]):
            if b['id'] not in outgoing.get(a['id'], []) \
                    and b['id'] not in incoming.get(a['id'], []):
                return None
        n = len(chain)
        cols = math.ceil(math.sqrt(2 * n))
        new_by_level: Dict[int, List[dict]] = {}
        abstract = {}
        levels_map = {}
        for i, e in enumerate(chain):
            row, col = divmod(i, cols)
            c = col if row % 2 == 0 else cols - 1 - col
            abstract[e['id']] = (float(c), float(row))
            levels_map[e['id']] = row
            new_by_level.setdefault(row, []).append(e)
        logger.info(f"    - U76: cadena de {n} eslabones plegada en "
                    f"serpentina de {cols} columnas")
        return new_by_level, abstract, levels_map

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

        # En un BOSQUE (todo nodo con ≤1 padre) el barycenter PURO alinea cada
        # hijo bajo su padre y da cero cruces; el tirón de centralidad hacia el
        # centro de la fila (pensado para hubs de flujos densos) ahí sólo
        # desordena hermanos y cruza ramas (caso organigrama).
        is_forest = all(len(v) <= 1 for v in incoming.values())

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
                    alpha = 0.0 if is_forest else (
                        min(0.6, score * 3.5) if score > 0 else 0.0)
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
                    alpha = 0.0 if is_forest else (
                        min(0.6, score * 3.5) if score > 0 else 0.0)
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
        # Build adjacency with weights (count of edges between pair).
        # Use sorted iteration for determinism: floating-point operations downstream
        # are not perfectly commutative, so iteration order affects bit-exact output.
        elem_ids = set(positions.keys())
        elem_ids_sorted = sorted(elem_ids)
        edge_counts: Dict[tuple, int] = {}
        for eid in elem_ids_sorted:
            for child in outgoing.get(eid, []):
                if child in elem_ids:
                    key = tuple(sorted([eid, child]))
                    edge_counts[key] = edge_counts.get(key, 0) + 1

        adjacency: Dict[str, list] = {eid: [] for eid in elem_ids_sorted}
        for (a, b), weight in sorted(edge_counts.items()):
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
            for eid in elem_ids_sorted:
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
        contained_ids = [extract_item_id(ref) for ref in container['contains']]
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

            # BUGS-LAYOUT-011: misma cuenta de header que el layout local
            header_height = self._container_header_height(container, padding)

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

    @staticmethod
    def _container_header_height(container: dict, padding: float) -> float:
        """BUGS-LAYOUT-011: alto del header de un contenedor, medido desde
        su techo hasta donde puede empezar el contenido.

        El icono decorativo se DIBUJA en [y+padding, y+padding+50]
        (draw_container): el header debe llegar hasta su borde inferior
        real — la cuenta vieja (max(50, label) sin el padding superior)
        dejaba al primer hijo soldado al icono, y sin label ni siquiera
        reservaba el icono (hijos encima). Áreas (T73, sin icono) y bands
        (título lateral) conservan su cuenta."""
        label_h = 0.0
        if container.get('label'):
            label_h = len(container['label'].split('\n')) * TEXT_LINE_HEIGHT
        if is_band(container):
            return 0.0
        if container.get('type', 'building') != 'area':
            return padding + max(float(CONTAINER_ICON_HEIGHT), label_h)
        return max(float(CONTAINER_ICON_HEIGHT), label_h) if label_h else 0.0

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

        # Posición Y inicial para elementos = header + padding_mid
        start_y = self._container_header_height(container, padding) + padding

        # Filtrar por scope
        full_elements = []
        for elem in elements:
            scope = self._get_scope(elem, container)
            if scope == 'full':
                full_elements.append(elem)

        # WISH-LAYOUT-005: una band coloca a TODOS sus hijos en una sola fila
        # horizontal (es un eje de equivalencia), con offset lateral para el
        # título rotado y sin header arriba.
        if is_band(container):
            full_elements = [e for e in elements
                             if self._get_scope(e, container) == 'full']
            spacing = GRID_SPACING_SMALL
            left = band_left_region(container) + padding
            # WISH-LAYOUT-009: el avance de la fila es por HIJO — el ancho de
            # su etiqueta manda sobre el del icono (pitch label-aware).
            xacc = left
            for elem in full_elements:
                cell_w = max(float(ICON_WIDTH),
                             self._est_contained_label_width(elem))
                elem['_local_x'] = xacc + (cell_w - float(ICON_WIDTH)) / 2.0
                elem['_local_y'] = padding
                xacc += cell_w + spacing
            return

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

            spacing = GRID_SPACING_SMALL  # gap horizontal entre celdas

            # K35 + WISH-LAYOUT-009: la celda se dimensiona al LABEL más ancho
            # de cada columna (no sólo al ícono) para que las etiquetas no
            # invadan la columna vecina. Antes sólo en grids angostos (≤2
            # columnas) — en anchos el pitch de icono fundía filas enteras
            # (fila de torres del minero, grilla LAF de 06-flujo) y la pasada
            # global agotaba sus candidatos. Hoy los vecinos SÍ acompañan el
            # crecimiento (super-nodo rígido §P59 + invariante de solapes +
            # medición veraz), así que el ensanche es por columna en TODA
            # grilla. El contenedor crece para alojarlo.
            #
            # §P59: la celda se dimensiona además al tamaño REAL del hijo — un
            # contenedor anidado ya resuelto puede medir cientos de px y el
            # pitch fijo de icono lo encimaba con sus hermanos. Ancho por
            # columna y alto por FILA.
            def _child_w(e):
                return max(float(e.get('width', ICON_WIDTH)),
                           self._est_contained_label_width(e))

            col_w = {}
            row_h = {}
            for i, elem in enumerate(full_elements):
                c, r = i % cols, i // cols
                col_w[c] = max(col_w.get(c, float(ICON_WIDTH)), _child_w(elem))
                row_h[r] = max(row_h.get(r, float(ICON_HEIGHT)),
                               float(elem.get('height', ICON_HEIGHT)))
            col_left = {}
            xacc = padding
            for c in range(cols):
                col_left[c] = xacc
                xacc += col_w.get(c, float(ICON_WIDTH)) + spacing
            # WISH-LAYOUT-009: reserva vertical por FILA — el alto del label
            # más alto de ESA fila (no un máximo global), para que la fila de
            # abajo arranque debajo de los textos de la de arriba.
            row_label_h = {}
            for i, elem in enumerate(full_elements):
                r = i // cols
                row_label_h[r] = max(row_label_h.get(r, 0.0),
                                     self._est_contained_label_height(elem))
            row_top = {}
            yacc = start_y
            for r in range(max(row_h) + 1):
                row_top[r] = yacc
                yacc += row_h[r] + max(CONTAINER_GRID_ROW_SPACING,
                                       row_label_h.get(r, 0.0) + spacing)

            for i, elem in enumerate(full_elements):
                row = i // cols
                col = i % cols
                ew = float(elem.get('width', ICON_WIDTH))
                elem['_local_x'] = col_left[col] + (col_w[col] - ew) / 2.0
                elem['_local_y'] = row_top[row]

    @staticmethod
    def _est_contained_label_width(elem: dict) -> float:
        """Ancho estimado del label de un elemento contenido (~7px/char a 14px;
        nunca menor al ícono)."""
        lbl = elem.get('label', '')
        if not lbl:
            return float(ICON_WIDTH)
        maxchars = max((len(line) for line in lbl.split('\n')), default=0)
        return max(float(ICON_WIDTH), maxchars * 7.0)

    @staticmethod
    def _est_contained_label_height(elem: dict) -> float:
        """Alto estimado del label multilínea (px)."""
        lbl = elem.get('label', '')
        return len(lbl.split('\n')) * TEXT_LINE_HEIGHT if lbl else 0.0

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
            ref_id = extract_item_id(ref)
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

            # WISH-LAYOUT-009: el ancho cubre la EXTENSIÓN local real
            # (los _local_x son coordenadas dentro del contenedor, no
            # relativas a min_x): la fórmula content_width + 2·padding
            # descartaba el origen y el offset de centrado de la primera
            # columna dejaba al último hijo fuera del borde derecho.
            base_width = max(max_x + padding, ICON_WIDTH + 2 * padding)

        # WISH-LAYOUT-005: band reserva margen lateral para el título rotado
        # + icono (no header arriba) y hugs verticalmente.
        # WISH-LAYOUT-009: el ancho se mide sobre la EXTENSIÓN local real
        # (iconos + vuelo horizontal de etiquetas). La fórmula anterior
        # (content_width + left_region) asumía contenido pegado al margen;
        # con celdas label-aware el primer icono arranca corrido
        # (celda−icono)/2 y la banda quedaba corta exactamente ese offset.
        if container is not None and is_band(container):
            right_max = 0.0
            for e in elements:
                lx = float(e.get('_local_x', 0.0))
                ew = float(e.get('width', ICON_WIDTH))
                lw = self._est_contained_label_width(e)
                right_max = max(right_max, lx + ew, lx + ew / 2.0 + lw / 2.0)
            return (right_max + padding, content_height + 2 * padding)

        # Calcular espacio del header del contenedor (icono + etiqueta)
        # El header comienza después del padding top
        header_height = 0

        if container and 'label' in container:
            label_text = container['label']
            lines = label_text.split('\n')
            max_line_len = max(len(line) for line in lines) if lines else 0
            # BUGS-AUTO-007: el header del container se renderiza bold 16px,
            # no regular 14px. Con TEXT_CHAR_WIDTH=8 (estimación para regular)
            # labels largos como 'Shared (algoritmo-agnóstico)' se salían ~46px
            # por el borde derecho. Multiplicamos por 1.25 para compensar.
            label_width = max_line_len * TEXT_CHAR_WIDTH * 1.25  # bold 16px aprox 10px/char
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
                    ref_id = extract_item_id(ref)
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
                    ref_id = extract_item_id(ref)
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

