"""
HierLayoutOptimizer — algoritmo de layout jerárquico (WISH-LAF-002).

Implementa el pipeline plano de la spec: §A niveles → §B columnas →
(§C/§D puertos+ruteo, §E/§F arcos+etiquetas en fases siguientes). Mapea las
coordenadas abstractas (columna, nivel) a coordenadas reales y delega el
render en AutoSVGRenderer (mismo estilo de iconos/etiquetas).
"""

import logging

from AlmaGag.layout.optimizer_base import LayoutOptimizer
from AlmaGag.layout.sizing import SizingCalculator
from AlmaGag.layout.geometry import GeometryCalculator
from AlmaGag.layout.auto.auto_renderer import AutoSVGRenderer
from AlmaGag.layout.auto.routing_policy import AutoRoutingPolicy
from AlmaGag.layout.graph_analysis import GraphAnalyzer
from AlmaGag.config import ICON_WIDTH, ICON_HEIGHT
from AlmaGag.layout.hier.leveling import compute_levels
from AlmaGag.layout.hier.columns import compute_columns
from AlmaGag.layout.hier.routing import route_connections
from AlmaGag.layout.hier.arcs import route_cycle_arcs
from AlmaGag.layout.hier.labels import assign_label_sides

logger = logging.getLogger('AlmaGag')

# Espaciado en px entre columnas y entre niveles (abstracto → real).
COL_SPACING = 200.0     # separación horizontal por unidad de columna
LEVEL_SPACING = 170.0   # separación vertical por nivel
MARGIN_X = 100.0
MARGIN_Y = 40.0


class HierLayoutOptimizer(LayoutOptimizer):
    def __init__(self, verbose: bool = False, visualdebug: bool = False, **kwargs):
        super().__init__(verbose=verbose)
        self.visualdebug = visualdebug
        self.sizing = SizingCalculator()
        self.geometry = GeometryCalculator(self.sizing)
        self.routing = AutoRoutingPolicy(self.sizing)
        self.graph_analyzer = GraphAnalyzer()
        self.renderer = AutoSVGRenderer(self.geometry)

    def optimize(self, layout, max_iterations: int = 10,
                 dump_iterations: bool = False, input_file=None, **kwargs):
        L = layout.copy()
        if hasattr(layout, '_diagram_name'):
            L._diagram_name = layout._diagram_name

        elements = L.elements
        connections = L.connections

        # §A niveles + §B columnas.
        lv = compute_levels(elements, connections)
        cols, wp_abstract = compute_columns(lv, elements, connections)

        # Mapear (columna, nivel) → coords reales. Y por nivel (las tomas a
        # X.5 caen entre filas).
        all_cols = list(cols.values()) + [cx for chain in wp_abstract.values() for cx, _ in chain]
        min_col = min(all_cols) if all_cols else 0

        def to_x(col):
            return MARGIN_X + (col - min_col) * COL_SPACING

        for e in elements:
            eid = e['id']
            if eid not in cols:
                continue  # contenido (no root); se resuelve aparte si aplica
            e['x'] = to_x(cols[eid])
            e['y'] = MARGIN_Y + lv.level[eid] * LEVEL_SPACING

        # §B4: waypoints de aristas largas → coords reales sobre la conexión.
        icon_half = ICON_WIDTH / 2
        for c in connections:
            key = (c.get('from'), c.get('to'))
            if key in wp_abstract and wp_abstract[key]:
                c['waypoints'] = [
                    {'x': to_x(cx) + icon_half,
                     'y': MARGIN_Y + gl * LEVEL_SPACING + ICON_HEIGHT / 2}
                    for cx, gl in wp_abstract[key]
                ]

        # Canvas ajustado al contenido.
        xs = [e['x'] for e in elements if 'x' in e]
        ys = [e['y'] for e in elements if 'y' in e]
        if xs and ys:
            width = max(xs) + ICON_WIDTH + MARGIN_X
            height = max(ys) + ICON_HEIGHT + MARGIN_Y
            L.canvas = {'width': max(width, 400), 'height': max(height, 300)}

        # §C/§D: puertos por proyección + ruteo (Fase 2). Setea computed_path
        # en cada conexión (las back-edges quedan sin path aquí).
        route_connections(L, lv)
        # §E: arcos de ciclo (Fase 3) — pisan las aristas del ciclo (ida) y
        # dibujan la back-edge de retorno con comba coherente.
        route_cycle_arcs(L, lv)
        # §F18: preferencia de lado de la etiqueta = borde menos concurrido.
        assign_label_sides(L)

        # Atributos de análisis que el generator lee.
        L.levels = {eid: int(v) for eid, v in lv.level.items()}
        L.groups = [list(cols.keys())]
        L.priorities = {eid: 1 for eid in lv.level}
        L._collision_count = 0
        L._hier_levels = lv  # para fases §C-§F

        if self.verbose:
            logger.debug(f"[HIER] niveles={sorted(set(L.levels.values()))} "
                         f"satélites={lv.satellites} tomas={lv.side_feeders}")

        return L
