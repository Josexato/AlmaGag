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
from AlmaGag.layout.strategies.auto.auto_renderer import AutoSVGRenderer
from AlmaGag.layout.strategies.auto.routing_policy import AutoRoutingPolicy
from AlmaGag.layout.graph_analysis import GraphAnalyzer
from AlmaGag.config import ICON_WIDTH, ICON_HEIGHT
from AlmaGag.layout.strategies.hier.leveling import compute_levels
from AlmaGag.layout.strategies.hier.columns import compute_columns
from AlmaGag.layout.strategies.hier.routing import route_connections
from AlmaGag.layout.strategies.hier.arcs import route_cycle_arcs
from AlmaGag.layout.strategies.hier.labels import (assign_label_sides,
                                        assign_connection_label_anchors,
                                        apply_label_wrapping)
from AlmaGag.layout.strategies.hier.areas import layout_by_areas

logger = logging.getLogger('AlmaGag')

# Espaciado en px entre columnas y entre niveles (abstracto → real).
# §J30: paso vertical compacto = icono + holgura fija (~42px) ≈ 92px
# centro-a-centro, en vez de 170px (que dejaba ~120px de aire y estiraba el
# diagrama a una tira). Se amplía sólo lo necesario para etiquetas multilínea.
COL_SPACING = 200.0            # separación horizontal por unidad de columna
LEVEL_SPACING = ICON_HEIGHT + 42.0   # 92px — §J30 (icono 50 + holgura 42)
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
        L._areas = getattr(layout, '_areas', None)
        L._roles = getattr(layout, '_roles', None)
        L._lanes = getattr(layout, '_lanes', None)
        # Vista resuelta por el generator (§I): 'columns' | 'areas' | 'lanes' |
        # 'matrix'. Sin resolver (llamada directa a optimize), se infiere.
        view = getattr(layout, '_layout_view', None)
        if view is None:
            view = 'areas' if L._areas else 'columns'

        elements = L.elements
        connections = L.connections

        # §I: despacho por vista.
        if view == 'areas' and L._areas:
            return self._finish_labels(self._optimize_areas(L))
        if view == 'lanes':
            return self._finish_labels(self._optimize_lanes(L))
        if view == 'matrix' and L._areas:
            # §I: matriz fase×rol (la vista más completa; el spec la ofrece
            # "solo bajo petición" por lo cara de rutear).
            return self._finish_labels(self._optimize_matrix(L))
        if view == 'matrix':
            logger.warning("[HIER] vista 'matrix' requiere `areas`; usando flujo")
        # compat: si pidieron 'areas' sin declararlas, sigue el flujo normal.
        if L._areas and view == 'columns':
            pass  # ignora las áreas, layout de flujo plano

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
        self._capture('niveles-columnas', L,
                      '§A niveles + §B columnas → coords reales')

        # §C/§D: puertos por proyección + ruteo (Fase 2). Setea computed_path
        # en cada conexión (las back-edges quedan sin path aquí).
        route_connections(L, lv)
        self._capture('ruteo', L, '§C/§D puertos por proyección + ruteo')
        # §E: arcos de ciclo (Fase 3) — pisan las aristas del ciclo (ida) y
        # dibujan la back-edge de retorno con comba coherente.
        route_cycle_arcs(L, lv)
        self._capture('arcos', L, '§E arcos de ciclo (back-edges)')
        # §J31/§J32: etiquetas multilínea (≤3 líneas, ancho máx) antes de medir
        # lados/canvas.
        apply_label_wrapping(L)
        # §F18: preferencia de lado de la etiqueta = borde menos concurrido.
        assign_label_sides(L)
        # §G23: rótulo de conexión pegado al puerto de salida.
        assign_connection_label_anchors(L)
        self._capture('etiquetas', L, '§F/§G lados de etiqueta + anclas de rótulo')

        # §G22: contención del viewBox — ningún path (polyline/waypoints/comba
        # de bezier) debe salirse del canvas. Se expande el canvas para
        # contener toda la geometría de conectores (los puntos de control del
        # bezier acotan la curva por convexidad) + margen.
        self._expand_canvas_to_paths(L)

        # Atributos de análisis que el generator lee.
        L.levels = {eid: int(v) for eid, v in lv.level.items()}
        L.groups = [list(cols.keys())]
        L.priorities = {eid: 1 for eid in lv.level}
        L._collision_count = 0
        L._hier_levels = lv  # para fases §C-§F

        if self.verbose:
            logger.debug(f"[HIER] niveles={sorted(set(L.levels.values()))} "
                         f"satélites={lv.satellites} tomas={lv.side_feeders}")

        self._capture('final', L, '§G22 canvas contenido')
        return self._finish_labels(L)

    def _finish_labels(self, L):
        """WISH-LAYOUT-008: la ÚNICA optimización de etiquetas es la pasada
        global (compartida con auto) — siembra la verdad en
        `label_positions`/`connection_labels` (respetando la preferencia de
        lado §F18 y las anclas §G23) y resuelve fusiones deslizando por las
        polilíneas reales. El renderer dibuja esos valores tal cual, así que
        la medición almacenada ES la verdad visual."""
        from AlmaGag.layout.strategies.auto.anticollision import (
            global_label_anticollision)
        global_label_anticollision(L, self.geometry)
        return L

    def _optimize_areas(self, L):
        """§I27/§I29: layout por ámbitos (fases). Delega el sub-layout A–H por
        área a `areas.layout_by_areas` y expone `L.areas` para el renderer."""
        apply_label_wrapping(L)                      # §J31 antes del sub-layout
        boxes = layout_by_areas(L, L._areas)
        L.areas = boxes
        L.roles = L._roles
        # Atributos que el generator/renderer leen.
        L.levels = {e['id']: 0 for e in L.elements if 'x' in e}
        L.groups = [[b['id'] for b in boxes]]
        L.priorities = {e['id']: 1 for e in L.elements}
        L._collision_count = 0
        if self.verbose:
            logger.debug(f"[HIER-AREAS] {len(boxes)} áreas, "
                         f"canvas {L.canvas['width']:.0f}x{L.canvas['height']:.0f}")
        self._capture('final-areas', L, f'§I27/§I29 layout por {len(boxes)} ámbitos')
        return L

    def _optimize_matrix(self, L):
        """§I: layout en matriz fase×rol. Delega a `matrix.layout_by_matrix` y
        expone `L.matrix` (grilla) + `L.roles` para el renderer."""
        from AlmaGag.layout.strategies.hier.matrix import layout_by_matrix
        apply_label_wrapping(L)                      # §J31
        grid = layout_by_matrix(L)
        L.matrix = grid
        L.roles = L._roles
        L.levels = {e['id']: 0 for e in L.elements if 'x' in e}
        L.groups = [[c['id'] for c in grid['cols']]]
        L.priorities = {e['id']: 1 for e in L.elements}
        L._collision_count = 0
        if self.verbose:
            logger.debug(f"[HIER-MATRIX] {len(grid['cols'])}×{len(grid['rows'])} "
                         f"canvas {L.canvas['width']:.0f}x{L.canvas['height']:.0f}")
        self._capture('final-matrix', L,
                      f"§I matriz {len(grid['cols'])}×{len(grid['rows'])} fase×rol")
        return L

    def _optimize_lanes(self, L):
        """§I28: layout por carriles de rol. Delega a `lanes.layout_by_lanes` y
        expone `L.lanes` (franjas) + `L.roles` para el renderer."""
        from AlmaGag.layout.strategies.hier.lanes import layout_by_lanes
        apply_label_wrapping(L)                      # §J31
        strips = layout_by_lanes(L)
        L.lanes = strips
        L.roles = L._roles
        L.levels = {e['id']: 0 for e in L.elements if 'x' in e}
        L.groups = [[s['id'] for s in strips]]
        L.priorities = {e['id']: 1 for e in L.elements}
        L._collision_count = 0
        if self.verbose:
            logger.debug(f"[HIER-LANES] {len(strips)} carriles, "
                         f"canvas {L.canvas['width']:.0f}x{L.canvas['height']:.0f}")
        self._capture('final-lanes', L, f'§I28 layout por {len(strips)} carriles de rol')
        return L

    def _expand_canvas_to_paths(self, L):
        """§G22: contención del viewBox. Reúne TODA la geometría (iconos +
        puntos de conector, waypoints, puntos de control del bezier y anclas de
        rótulo), traslada al espacio positivo si algún path se salió por
        arriba/izquierda (p.ej. tomas laterales a medio nivel) y expande el
        canvas para contener el extremo más lejano. bbox ⊆ [0,w]×[0,h]."""
        pad = 20.0
        pts = []
        for e in L.elements:
            if 'x' in e and 'y' in e:
                pts.append((e['x'], e['y']))
                pts.append((e['x'] + ICON_WIDTH, e['y'] + ICON_HEIGHT))
        for c in L.connections:
            cp = c.get('computed_path')
            if cp:
                pts.extend(cp.get('points', []))
                pts.extend(cp.get('control_points', []))
            for w in c.get('waypoints', []) or []:
                pts.append((w['x'], w['y']))
            if c.get('_label_anchor'):
                pts.append(c['_label_anchor'])
        if not pts:
            return
        min_x = min(p[0] for p in pts)
        min_y = min(p[1] for p in pts)
        # Trasladar si algo quedó por encima/izquierda del margen.
        sx = pad - min_x if min_x < pad else 0.0
        sy = pad - min_y if min_y < pad else 0.0
        if sx or sy:
            self._translate(L, sx, sy)
            pts = [(px + sx, py + sy) for px, py in pts]
        max_x = max(p[0] for p in pts)
        max_y = max(p[1] for p in pts)
        L.canvas = {
            'width': max(L.canvas['width'], max_x + pad),
            'height': max(L.canvas['height'], max_y + pad),
        }

    @staticmethod
    def _translate(L, sx, sy):
        """Desplaza iconos, waypoints, paths y anclas de rótulo por (sx,sy)."""
        for e in L.elements:
            if 'x' in e and 'y' in e:
                e['x'] += sx
                e['y'] += sy
        for c in L.connections:
            cp = c.get('computed_path')
            if cp:
                if 'points' in cp:
                    cp['points'] = [(x + sx, y + sy) for x, y in cp['points']]
                if 'control_points' in cp:
                    cp['control_points'] = [(x + sx, y + sy) for x, y in cp['control_points']]
            for w in c.get('waypoints', []) or []:
                w['x'] += sx
                w['y'] += sy
            for k in ('_from_port', '_to_port', '_label_anchor'):
                if c.get(k):
                    c[k] = (c[k][0] + sx, c[k][1] + sy)
