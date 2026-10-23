"""
AutoRoutingPolicy — política de routing del algoritmo AUTO.

Encapsula cómo AUTO invoca el router_manager (biblioteca compartida en
AlmaGag/routing/) durante su pipeline de optimización. Centraliza el patrón
"setear sizing en el layout antes de rutar" que aparece en cada invocación
del optimizer y mantiene simetría con laf/routing_policy.py.
"""

from AlmaGag.routing.router_manager import ConnectionRouterManager


class AutoRoutingPolicy:
    """Política de routing para AutoLayoutOptimizer.

    Único método público: route(). Las invocaciones del optimizer (auto-route
    inicial, routing final, re-route tras expansión de canvas, re-route tras
    movimiento) comparten el mismo body — sus diferencias semánticas se
    documentan en los callsites.
    """

    def __init__(self, sizing):
        self._sizing = sizing
        self._router_manager = ConnectionRouterManager()

    def route(self, layout):
        """Calcula paths de todas las conexiones para el layout dado.

        Inyecta el SizingCalculator en el layout (los routers lo necesitan
        para conocer bounding boxes de iconos) y delega el cálculo de paths
        al router_manager compartido.
        """
        layout.sizing = self._sizing
        self._router_manager.calculate_all_paths(layout)
        # §P60: las conexiones inter-zona marcadas viajan por troncal
        # compartida (una por par de zonas) — se recalculan sobre la
        # geometría vigente en cada re-ruteo, pisando el path individual.
        from AlmaGag.layout.strategies.auto.zones import route_zone_trunks
        route_zone_trunks(layout)
        # WISH-ROUTE-001 (T70/T71/T72): cirugía de extremos para las
        # conexiones que cruzan bordes de contenedor — puerto en el
        # perímetro, cruce perpendicular, navegación interna ortogonal y
        # puertos repartidos. Corre en CADA re-ruteo (geometría vigente).
        from AlmaGag.routing.container_ports import (route_container_ports,
                                                     route_node_ports)
        route_container_ports(layout)
        # WISH-ROUTE-002 (V80): T72 aplicado a NODOS — convergencias con
        # ≥2 puntas en el mismo lado se reparten (≥18px) y el tramo final
        # se hace perpendicular al borde.
        route_node_ports(layout)
        # Grupo AA (AA98/AA99): en árboles familiares, cónyuge—unión en
        # horizontal pura y unión→hijos como peine — se re-aplica en cada
        # re-ruteo pisando el path individual (patrón route_zone_trunks).
        from AlmaGag.layout.strategies.auto.genealogy import route_family_joints
        route_family_joints(layout)
        # BUGS-ROUTE-010 (Z96 en AUTO): la ruta no atraviesa lo que no es
        # suyo — mismo desvío que hier (areas y flujo plano), corre al
        # final de CADA re-ruteo sobre la geometría vigente.
        _dodge_foreign_boxes(layout)


def _dodge_foreign_boxes(layout):
    """Z96 para AUTO: desvía los tramos ortogonales que cruzan DE LADO A
    LADO un icono ajeno, un contenedor ajeno (entrar no es atravesar: los
    contenedores de los extremos se excluyen) o el ICONO DE CABECERA de
    cualquier contenedor (nunca es destino — cruzarlo nunca es legítimo).
    Sin `outers`: en AUTO los labels no viven fijos bajo el icono (los
    administra el optimizador y §P61 los reacomoda tras el ruteo)."""
    from AlmaGag.config import ICON_WIDTH, ICON_HEIGHT, CONTAINER_PADDING
    from AlmaGag.layout.metrics import _seg_hits_rect
    from AlmaGag.layout.dodge import (dodge_boxes, relocate_corners,
                                      route_around_boxes)

    icon_box, cont_box, header_box, parents = {}, {}, {}, {}
    for e in layout.elements:
        if 'x' not in e or 'y' not in e:
            continue
        if 'contains' in e:
            if not e.get('_is_container_calculated'):
                continue
            x0, y0 = e['x'], e['y']
            x1 = x0 + e.get('width', ICON_WIDTH)
            y1 = y0 + e.get('height', ICON_HEIGHT)
            cont_box[e['id']] = (x0, y0, x1, y1)
            if e.get('type', 'building') != 'area':
                hx, hy = x0 + CONTAINER_PADDING, y0 + CONTAINER_PADDING
                header_box[e['id']] = (hx, hy, hx + ICON_WIDTH,
                                       hy + ICON_HEIGHT)
            for ref in e.get('contains', []) or []:
                parents[ref['id'] if isinstance(ref, dict) else ref] = e['id']
        else:
            icon_box[e['id']] = (e['x'], e['y'], e['x'] + ICON_WIDTH,
                                 e['y'] + ICON_HEIGHT)

    if not (icon_box or cont_box):
        return

    def _offenses(pts, boxes):
        # cajas con ALGUNA penetración (parcial o total): lo que mide §H6
        # — una pata de desvío que roza un icono vecino también cuenta.
        n = 0
        for b in boxes:
            if any(_seg_hits_rect(p[0], p[1], q[0], q[1], b)
                   for p, q in zip(pts, pts[1:])):
                n += 1
        return n

    reg = {}
    for c in layout.connections:
        cp = c.get('computed_path')
        if not (isinstance(cp, dict) and cp.get('type') in ('polyline', 'line')
                and cp.get('points')):
            continue
        f, t = c.get('from'), c.get('to')
        own = {f, t, parents.get(f), parents.get(t)}
        # Contenedores PRIMERO: el desvío grande elimina de paso las
        # travesías de sus miembros — al revés, la ruta hace escalerita
        # esquivando iconos interiores de una caja que igual va a rodear.
        obs = [bx for cid, bx in cont_box.items() if cid not in own]
        obs += [bx for cid, bx in header_box.items() if cid not in (f, t)]
        obs += [bx for eid, bx in icon_box.items() if eid not in (f, t)]
        before = list(cp['points'])
        pts = route_around_boxes(before, obs, reg=reg)
        pts = dodge_boxes(pts, obs, reg=reg)
        pts = relocate_corners(pts, obs, reg=reg)
        if [tuple(q) for q in pts] == [tuple(q) for q in before]:
            continue
        # Best-effort (precedente Z95): el candidato desviado solo gana si
        # REDUCE las cajas ofendidas — una geometría apretada puede dejar
        # la pata del desvío rozando al vecino y eso empeora el censo §H6.
        if _offenses(pts, obs) < _offenses(before, obs):
            cp['points'] = pts
            cp['type'] = 'polyline'
