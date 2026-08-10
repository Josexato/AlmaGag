"""
WISH-ROUTE-001 (grupo T del review) — ruteo hacia contenedores.

Los invariantes de borde y ortogonalidad regían sólo entre nodos sueltos;
hacia contenedores el path por defecto (straight) cruzaba el borde en
diagonal, remataba sobre el icono interior y apilaba puntas. Esta pasada
POST-ruteo hace cirugía de extremos conservando el cuerpo del path:

- T70: si el destino/origen es un CONTENEDOR, el path termina en un puerto
  de su PERÍMETRO y llega perpendicular al borde (stub exterior H/V).
- T71: si el destino/origen es un HIJO contenido, tres tramos: cuerpo
  externo → cruce PERPENDICULAR del borde por el puerto → navegación
  interna ortogonal hasta el borde del hijo.
- T72: los puertos de un mismo lado de un contenedor se reparten con
  separación mínima (PORT_MIN_SEP); el borde superior reserva la franja
  del rótulo (TITLE_GUARD desde la izquierda).

Se aplica a paths line/polyline (straight por defecto y orthogonal); las
curvas declaradas por el autor (manual/bezier/arc) y las troncales §P60
(`_zone_trunk`) se respetan tal cual.
"""

from typing import Dict, List, Optional, Tuple

from AlmaGag.config import ICON_HEIGHT, ICON_WIDTH
from AlmaGag.utils import extract_item_id

PORT_MIN_SEP = 18.0     # T72: separación mínima entre puntas en un borde
STUB = 20.0             # largo del tramo perpendicular exterior
INSET = 16.0            # avance interno tras cruzar el borde
TITLE_GUARD = 56.0      # franja del rótulo en el borde superior (desde x1)
EDGE_MARGIN = 10.0      # los puertos no pisan las esquinas

_SKIP_ROUTING = {'manual', 'bezier', 'arc'}


def _rect(e) -> Tuple[float, float, float, float]:
    w = e.get('width', ICON_WIDTH)
    h = e.get('height', ICON_HEIGHT)
    return (e['x'], e['y'], e['x'] + w, e['y'] + h)


def _inside(p, r, eps=0.5) -> bool:
    return (r[0] + eps < p[0] < r[2] - eps
            and r[1] + eps < p[1] < r[3] - eps)


def _xy(p):
    return (p[0], p[1]) if not hasattr(p, 'x') else (p.x, p.y)


def _seg_border_crossing(a, b, r):
    """(lado, coord) donde el segmento a→b (a fuera, b dentro) cruza el
    rect r. lado ∈ {left,right,top,bottom}; coord es la posición sobre el
    borde (y para lados verticales, x para horizontales)."""
    ax, ay = a
    bx, by = b
    best = None      # (t, lado, coord)
    if abs(bx - ax) > 1e-9:
        for x_edge, lado in ((r[0], 'left'), (r[2], 'right')):
            t = (x_edge - ax) / (bx - ax)
            if 0.0 <= t <= 1.0:
                y = ay + t * (by - ay)
                if r[1] - 0.5 <= y <= r[3] + 0.5:
                    if best is None or t < best[0]:
                        best = (t, lado, y)
    if abs(by - ay) > 1e-9:
        for y_edge, lado in ((r[1], 'top'), (r[3], 'bottom')):
            t = (y_edge - ay) / (by - ay)
            if 0.0 <= t <= 1.0:
                x = ax + t * (bx - ax)
                if r[0] - 0.5 <= x <= r[2] + 0.5:
                    if best is None or t < best[0]:
                        best = (t, lado, x)
    return (best[1], best[2]) if best else None


def _port_point(r, lado, coord):
    if lado == 'left':
        return (r[0], coord)
    if lado == 'right':
        return (r[2], coord)
    if lado == 'top':
        return (coord, r[1])
    return (coord, r[3])


def _normal(lado):
    """Normal EXTERIOR del lado."""
    return {'left': (-1, 0), 'right': (1, 0),
            'top': (0, -1), 'bottom': (0, 1)}[lado]


def _ancestors(eid: str, parent: Dict[str, str]) -> List[str]:
    out, cur, seen = [], eid, set()
    while cur in parent and cur not in seen:
        seen.add(cur)
        cur = parent[cur]
        out.append(cur)
    return out


def _build_maps(layout):
    parent: Dict[str, str] = {}
    for c in layout.elements:
        if 'contains' in c:
            for ref in c.get('contains', []):
                parent[extract_item_id(ref)] = c['id']
    return parent


def _boundary_for(eid: str, other_id: str, parent, by_id):
    """Contenedor cuyo borde cruza esta punta, y modo:
    - 'terminal': el endpoint ES un contenedor y el otro extremo está
      fuera de su subárbol → el path termina en su perímetro (T70).
    - 'child': el endpoint vive dentro de un contenedor que NO contiene
      al otro extremo → cruce + navegación interna (T71)."""
    anc_e = _ancestors(eid, parent)
    anc_o = _ancestors(other_id, parent)
    e = by_id.get(eid)
    if e is not None and 'contains' in e and eid not in anc_o:
        return e, 'terminal'
    crossing = [a for a in anc_e if a not in anc_o and a != other_id]
    if crossing:
        top = crossing[-1]           # el más EXTERNO
        c = by_id.get(top)
        if c is not None and 'x' in c and 'y' in c:
            return c, 'child'
    return None, None


def _center(e):
    x1, y1, x2, y2 = _rect(e)
    return ((x1 + x2) / 2.0, (y1 + y2) / 2.0)


def _plan_side(pts, boundary, endpoint, mode, obstacles=()):
    """Plan de cirugía para la punta FINAL de pts. Devuelve dict o None."""
    r = _rect(boundary)
    # último punto estrictamente FUERA del rect, mirando desde el final
    k = None
    for i in range(len(pts) - 1, -1, -1):
        if not _inside(pts[i], r) and not _on_rect_border(pts[i], r):
            k = i
            break
    if k is None:
        return None
    if k == len(pts) - 1:
        # el path entero termina fuera del rect (extremo re-anclado por el
        # renderer o punta rancia): cruce sintético hacia el interior
        target = _center(boundary) if mode == 'terminal' else _center(endpoint)
        cross = _seg_border_crossing(pts[k], target, r)
    else:
        cross = (_seg_border_crossing(pts[k], pts[k + 1], r)
                 or _seg_border_crossing(pts[k], _center(endpoint), r))
    if cross is None:
        return None
    lado, coord = cross
    if mode == 'child':
        # C9: el puerto deseado es la PROYECCIÓN del hijo sobre el borde…
        # salvo que el corredor directo cruce HERMANOS (misma fila/columna):
        # entonces se elige un CARRIL libre y el hijo se aborda por su lado
        # perpendicular (_pick_lane).
        coord = _pick_lane(r, _rect(endpoint), lado, obstacles)
    return {'k': k, 'lado': lado, 'coord': coord,
            'boundary': boundary, 'endpoint': endpoint, 'mode': mode}


def _on_rect_border(p, r, eps=0.5) -> bool:
    x, y = p
    on_v = (abs(x - r[0]) <= eps or abs(x - r[2]) <= eps) and \
        r[1] - eps <= y <= r[3] + eps
    on_h = (abs(y - r[1]) <= eps or abs(y - r[3]) <= eps) and \
        r[0] - eps <= x <= r[2] + eps
    return on_v or on_h


def _sibling_rects(boundary, endpoint_id, by_id, exclude):
    """Rects de los DEMÁS descendientes dibujables del contenedor — los
    obstáculos de la navegación interna. `exclude` = endpoint + sus
    ancestros (un sub-contenedor que CONTIENE al endpoint no es obstáculo
    para el corredor que entra hacia él)."""
    out = []
    stack = [extract_item_id(ref) for ref in boundary.get('contains', [])]
    while stack:
        i = stack.pop()
        if i in exclude:
            continue
        e = by_id.get(i)
        if not e or 'x' not in e or 'y' not in e:
            continue
        if 'contains' in e:
            stack.extend(extract_item_id(ref) for ref in e.get('contains', []))
        out.append(_rect(e))
    return out


def _segment_blocked(a, b, rects, margin=3.0) -> bool:
    ax, ay = a
    bx, by = b
    x1, x2 = min(ax, bx) - 0.1, max(ax, bx) + 0.1
    y1, y2 = min(ay, by) - 0.1, max(ay, by) + 0.1
    for (rx1, ry1, rx2, ry2) in rects:
        rx1, ry1, rx2, ry2 = rx1 - margin, ry1 - margin, rx2 + margin, ry2 + margin
        if x2 < rx1 or x1 > rx2 or y2 < ry1 or y1 > ry2:
            continue
        if abs(ax - bx) < 0.2 and rx1 < ax < rx2:      # vertical
            return True
        if abs(ay - by) < 0.2 and ry1 < ay < ry2:      # horizontal
            return True
    return False


def _pick_lane(r, ch, lado, obstacles):
    """Coordenada de puerto para modo child. Prefiere la proyección del
    hijo (corredor directo); si el directo cruza hermanos, busca el carril
    libre más cercano por fuera de la fila/columna del hijo."""
    ccx = (ch[0] + ch[2]) / 2.0
    ccy = (ch[1] + ch[3]) / 2.0
    horiz = lado in ('left', 'right')
    if horiz:
        lo, hi = r[1] + EDGE_MARGIN, r[3] - EDGE_MARGIN
        direct = min(max(ccy, lo), hi)
        edge_x = ch[0] if lado == 'left' else ch[2]
        port_x = r[0] if lado == 'left' else r[2]
        if not _segment_blocked((port_x, direct), (edge_x, direct), obstacles):
            return direct
        # carriles perpendiculares: por encima / por debajo del hijo
        cands = [ch[1] - PORT_MIN_SEP, ch[3] + PORT_MIN_SEP,
                 ch[1] - 2 * PORT_MIN_SEP, ch[3] + 2 * PORT_MIN_SEP]
        for lane in cands:
            if not lo <= lane <= hi:
                continue
            leg1 = ((port_x, lane), (ccx, lane))
            edge_y = ch[1] if lane < ccy else ch[3]
            leg2 = ((ccx, lane), (ccx, edge_y))
            if not _segment_blocked(*leg1, rects=obstacles) \
                    and not _segment_blocked(*leg2, rects=obstacles):
                return lane
        return direct
    lo, hi = r[0] + EDGE_MARGIN, r[2] - EDGE_MARGIN
    if lado == 'top':
        lo = max(lo, r[0] + TITLE_GUARD)
    direct = min(max(ccx, lo), hi)
    edge_y = ch[1] if lado == 'top' else ch[3]
    port_y = r[1] if lado == 'top' else r[3]
    if not _segment_blocked((direct, port_y), (direct, edge_y), obstacles):
        return direct
    cands = [ch[0] - PORT_MIN_SEP, ch[2] + PORT_MIN_SEP,
             ch[0] - 2 * PORT_MIN_SEP, ch[2] + 2 * PORT_MIN_SEP]
    for lane in cands:
        if not lo <= lane <= hi:
            continue
        leg1 = ((lane, port_y), (lane, ccy))
        edge_x = ch[0] if lane < ccx else ch[2]
        leg2 = ((lane, ccy), (edge_x, ccy))
        if not _segment_blocked(*leg1, rects=obstacles) \
                and not _segment_blocked(*leg2, rects=obstacles):
            return lane
    return direct


def _chain(plan):
    """Cadena del lado, del EXTERIOR hacia el endpoint:
    (stub, [port, *navegación_interna...]). El último punto de la cadena
    es donde termina el path (borde del contenedor o borde del hijo)."""
    r = _rect(plan['boundary'])
    lado, coord = plan['lado'], plan['coord']
    port = _port_point(r, lado, coord)
    nx, ny = _normal(lado)
    stub = (port[0] + nx * STUB, port[1] + ny * STUB)
    inner = [port]
    if plan['mode'] == 'child':
        # T71: navegación interna ortogonal hasta el borde del hijo. Si el
        # puerto quedó alineado con el hijo, corredor recto; si quedó en un
        # carril perpendicular (_pick_lane o corrimiento T72), se viaja por
        # el carril y se entra por el lado del hijo que mira al carril.
        ch = _rect(plan['endpoint'])
        ccx, ccy = (ch[0] + ch[2]) / 2.0, (ch[1] + ch[3]) / 2.0
        if lado in ('left', 'right'):
            edge_x = ch[0] if lado == 'left' else ch[2]
            if ch[1] + 2 <= port[1] <= ch[3] - 2:
                inner += [(edge_x, port[1])]
            else:
                edge_y = ch[1] if port[1] < ccy else ch[3]
                inner += [(ccx, port[1]), (ccx, edge_y)]
        else:
            edge_y = ch[1] if lado == 'top' else ch[3]
            if ch[0] + 2 <= port[0] <= ch[2] - 2:
                inner += [(port[0], edge_y)]
            else:
                edge_x = ch[0] if port[0] < ccx else ch[2]
                inner += [(port[0], ccy), (edge_x, ccy)]
    return stub, inner


def _bend_to(anchor, stub, lado):
    """Codo que conecta `anchor` con `stub` dejando el tramo pegado al stub
    ALINEADO con el eje del cruce (H para left/right, V para top/bottom)."""
    if lado in ('left', 'right'):
        return (anchor[0], stub[1])
    return (stub[0], anchor[1])


def _bridge(stub_a, lado_a, stub_b, lado_b):
    """Codos entre dos stubs cuando el cuerpo del path desapareció: sale de
    stub_a por el eje de su cruce y llega a stub_b por el eje del suyo."""
    a_horiz = lado_a in ('left', 'right')
    b_horiz = lado_b in ('left', 'right')
    if a_horiz and b_horiz:
        mx = (stub_a[0] + stub_b[0]) / 2.0
        return [(mx, stub_a[1]), (mx, stub_b[1])]
    if not a_horiz and not b_horiz:
        my = (stub_a[1] + stub_b[1]) / 2.0
        return [(stub_a[0], my), (stub_b[0], my)]
    if a_horiz:                       # sale H, llega V
        return [(stub_b[0], stub_a[1])]
    return [(stub_a[0], stub_b[1])]   # sale V, llega H


def _outer_leg(a, b, lado, layout, conn, boundaries, departure=False):
    """Puntos INTERMEDIOS del corredor exterior a→b. Intenta el grafo de
    visibilidad (obstacle-aware, contenedores blandos, los boundaries del
    cruce con paso libre); si falla, codo simple. Con `departure=True`, a
    es el stub de SALIDA y el primer segmento se alinea al eje del cruce;
    si no, b es el stub de LLEGADA y se alinea el último."""
    try:
        from AlmaGag.routing.router_base import Point
        from AlmaGag.routing.visibility_graph import find_orthogonal_path
        sizing = getattr(layout, 'sizing', None)
        vg = find_orthogonal_path(
            Point(a[0], a[1]), Point(b[0], b[1]), layout,
            conn.get('from', ''), conn.get('to', ''), sizing,
            related_containers=boundaries, soft_containers=True)
        if vg and len(vg) >= 2:
            return [_xy(p) for p in vg[1:-1]]
    except Exception:
        pass
    if departure:
        if lado in ('left', 'right'):
            return [(b[0], a[1])]      # sale H desde el stub, luego V
        return [(a[0], b[1])]          # sale V desde el stub, luego H
    return [_bend_to(a, b, lado)]


def _spread(requests, title_guard=True):
    """T72: reparte las coordenadas de puerto de un mismo (contenedor, lado)
    con separación mínima, dentro del rango útil del borde. Para NODOS
    (V80) se llama con title_guard=False: no hay franja de rótulo."""
    by_side: Dict[Tuple[str, str], List[dict]] = {}
    for req in requests:
        key = (req['boundary']['id'], req['lado'])
        by_side.setdefault(key, []).append(req)
    for (cid, lado), reqs in by_side.items():
        r = _rect(reqs[0]['boundary'])
        if lado in ('left', 'right'):
            lo, hi = r[1] + EDGE_MARGIN, r[3] - EDGE_MARGIN
        else:
            lo, hi = r[0] + EDGE_MARGIN, r[2] - EDGE_MARGIN
            if lado == 'top' and title_guard:
                lo = max(lo, r[0] + TITLE_GUARD)   # franja del rótulo
        reqs.sort(key=lambda q: q['coord'])
        n = len(reqs)
        span = hi - lo
        sep = PORT_MIN_SEP if span >= PORT_MIN_SEP * (n - 1) else (
            span / max(n - 1, 1))
        # barrido hacia adelante y hacia atrás: mantiene el orden y la
        # cercanía a la posición deseada, garantizando la separación
        coords = [min(max(q['coord'], lo), hi) for q in reqs]
        for i in range(1, n):
            if coords[i] < coords[i - 1] + sep:
                coords[i] = coords[i - 1] + sep
        if n and coords[-1] > hi:
            coords[-1] = hi
            for i in range(n - 2, -1, -1):
                if coords[i] > coords[i + 1] - sep:
                    coords[i] = coords[i + 1] - sep
        for q, c in zip(reqs, coords):
            q['coord'] = c


def route_container_ports(layout) -> int:
    """Aplica T70/T71/T72 a las conexiones que cruzan bordes de contenedor.
    Devuelve cuántas conexiones se reescribieron."""
    by_id = layout.elements_by_id
    parent = _build_maps(layout)
    if not parent:
        return 0

    plans = []               # (conn, plan_from|None, plan_to|None)
    requests = []
    for conn in layout.connections:
        if conn.get('_zone_trunk'):
            continue
        f, t = conn.get('from'), conn.get('to')
        if not f or not t or f == t:
            continue
        routing = conn.get('routing') or {}
        if routing.get('type') in _SKIP_ROUTING:
            continue
        fe, te = by_id.get(f), by_id.get(t)
        if not fe or not te or 'x' not in fe or 'x' not in te:
            continue
        b_to, m_to = _boundary_for(t, f, parent, by_id)
        b_from, m_from = _boundary_for(f, t, parent, by_id)
        if b_to is None and b_from is None:
            continue
        cp = conn.get('computed_path') or {}
        pts = [_xy(p) for p in (cp.get('points') or [])]
        # waypoints v1.5 del autor: se respetan sólo si el path conserva
        # puntos intermedios REALES; degenerado a recta = sin geometría
        if 'waypoints' in conn and len(pts) > 2:
            continue
        if len(pts) < 2:
            pts = [_center(fe), _center(te)]

        obs_to = (_sibling_rects(b_to, t, by_id, {t, *_ancestors(t, parent)})
                  if b_to is not None and m_to == 'child' else ())
        obs_from = (_sibling_rects(b_from, f, by_id,
                                   {f, *_ancestors(f, parent)})
                    if b_from is not None and m_from == 'child' else ())
        plan_to = (_plan_side(pts, b_to, te, m_to, obs_to)
                   if b_to is not None else None)
        rev = list(reversed(pts))
        plan_from = (_plan_side(rev, b_from, fe, m_from, obs_from)
                     if b_from is not None else None)
        if plan_to is None and plan_from is None:
            continue
        plans.append((conn, pts, plan_from, plan_to))
        for p in (plan_from, plan_to):
            if p is not None:
                requests.append(p)

    if not plans:
        return 0
    _spread(requests)

    rewritten = 0
    for conn, pts, plan_from, plan_to in plans:
        n = len(pts)
        # índice del último punto exterior por cada lado, en coords del pts
        kf = (n - 1 - plan_from['k']) if plan_from else 0
        kt = plan_to['k'] if plan_to else n - 1
        both = plan_from is not None and plan_to is not None
        middle = [] if (both and kf > kt) else pts[kf:kt + 1]

        boundaries = {p['boundary']['id']
                      for p in (plan_from, plan_to) if p is not None}
        body: List[Tuple[float, float]] = []
        if plan_from is not None:
            stub_f, chain_f = _chain(plan_from)
            body.extend(reversed(chain_f))     # endpoint → … → puerto
            body.append(stub_f)
        if middle:
            if plan_from is not None:
                body.extend(_outer_leg(stub_f, middle[0], plan_from['lado'],
                                       layout, conn, boundaries,
                                       departure=True))
            body.extend(middle)
        if plan_to is not None:
            stub_t, chain_t = _chain(plan_to)
            if middle:
                body.extend(_outer_leg(body[-1], stub_t, plan_to['lado'],
                                       layout, conn, boundaries))
            elif plan_from is not None:
                body.extend(_bridge(stub_f, plan_from['lado'],
                                    stub_t, plan_to['lado']))
            body.append(stub_t)
            body.extend(chain_t)

        clean = [body[0]]
        for p in body[1:]:
            if abs(p[0] - clean[-1][0]) > 0.25 or abs(p[1] - clean[-1][1]) > 0.25:
                clean.append(p)
        if len(clean) < 2:
            continue
        conn['computed_path'] = {
            'type': 'polyline',
            'points': [(round(x, 1), round(y, 1)) for x, y in clean],
        }
        rewritten += 1
    return rewritten


def _which_side(p, r, eps=1.5):
    """Lado del rect r sobre el que cae el punto p (None si no toca)."""
    x, y = p
    if abs(y - r[1]) <= eps and r[0] - eps <= x <= r[2] + eps:
        return 'top'
    if abs(y - r[3]) <= eps and r[0] - eps <= x <= r[2] + eps:
        return 'bottom'
    if abs(x - r[0]) <= eps and r[1] - eps <= y <= r[3] + eps:
        return 'left'
    if abs(x - r[2]) <= eps and r[1] - eps <= y <= r[3] + eps:
        return 'right'
    return None


def route_node_ports(layout) -> int:
    """WISH-ROUTE-002 (V80) — T72 aplicado a NODOS.

    Cuando ≥2 conexiones tocan el MISMO lado de un nodo (convergencia),
    sus puntas se reparten (≥PORT_MIN_SEP) y el tramo final se reescribe
    PERPENDICULAR al borde vía un carril a STUB px — se acabaron las
    llegadas tangenciales que barren el borde y las puntas apiladas.
    Los hijos contenidos ya los gobierna T71; manual/bezier/arc y las
    troncales §P60 se respetan tal cual."""
    parent = _build_maps(layout)
    nodes = {e['id']: e for e in layout.elements
             if 'x' in e and 'contains' not in e and e['id'] not in parent}
    groups: Dict[Tuple[str, str], List[dict]] = {}
    for conn in layout.connections:
        rt = (conn.get('routing') or {}).get('type')
        if rt in _SKIP_ROUTING or conn.get('_zone_trunk') \
                or conn.get('from') == conn.get('to'):
            continue
        cp = conn.get('computed_path')
        raw = cp.get('points') if isinstance(cp, dict) else None
        if not raw or len(raw) < 2:
            continue
        pts = [_xy(p) for p in raw]
        # V80 gobierna paths ORTOGONALES: un tramo diagonal es estilo
        # straight legítimo (árboles, hubs), no una convergencia sucia.
        if any(abs(a[0] - b[0]) > 0.5 and abs(a[1] - b[1]) > 0.5
               for a, b in zip(pts, pts[1:])):
            continue
        # sólo LLEGADAS: ahí vive la flecha y ahí pide puertos el review
        for at_end in (True,):
            nid = conn['to'] if at_end else conn['from']
            node = nodes.get(nid)
            if node is None:
                continue
            r = _rect(node)
            tip = pts[-1] if at_end else pts[0]
            side = _which_side(tip, r)
            if side is None:
                continue
            coord = tip[0] if side in ('top', 'bottom') else tip[1]
            groups.setdefault((nid, side), []).append(
                {'conn': conn, 'end': at_end, 'boundary': node,
                 'lado': side, 'coord': coord})

    def _already_clean(ms):
        """Grupo que YA cumple V80 (llegadas perpendiculares y puntas
        separadas ≥PORT_MIN_SEP): no se toca — la cirugía sólo opera
        sobre la violación, no sobre lo sano."""
        tips = []
        for m in ms:
            pts = [_xy(p) for p in m['conn']['computed_path']['points']]
            tip, prev = (pts[-1], pts[-2]) if m['end'] else (pts[0], pts[1])
            if m['lado'] in ('top', 'bottom'):
                if abs(prev[0] - tip[0]) > 0.5:
                    return False
            elif abs(prev[1] - tip[1]) > 0.5:
                return False
            tips.append(tip)
        for i in range(len(tips)):
            for j in range(i + 1, len(tips)):
                d = ((tips[i][0] - tips[j][0]) ** 2
                     + (tips[i][1] - tips[j][1]) ** 2) ** 0.5
                if d < PORT_MIN_SEP - 0.5:
                    return False
        return True

    crowded = [ms for ms in groups.values()
               if len(ms) >= 2 and not _already_clean(ms)]
    if not crowded:
        return 0
    _spread([m for ms in crowded for m in ms], title_guard=False)

    current: Dict[int, List[Tuple[float, float]]] = {}
    rewritten = 0
    for ms in crowded:
        for m in ms:
            conn = m['conn']
            key = id(conn)
            if key not in current:
                current[key] = [_xy(p)
                                for p in conn['computed_path']['points']]
            pts = current[key]
            r = _rect(m['boundary'])
            lado = m['lado']
            port = _port_point(r, lado, m['coord'])
            lane = {'top': r[1] - STUB, 'bottom': r[3] + STUB,
                    'left': r[0] - STUB, 'right': r[2] + STUB}[lado]

            def in_band(p):
                if lado == 'top':
                    return p[1] >= lane - 0.5
                if lado == 'bottom':
                    return p[1] <= lane + 0.5
                if lado == 'left':
                    return p[0] >= lane - 0.5
                return p[0] <= lane + 0.5

            seq = list(pts) if m['end'] else list(reversed(pts))
            body = seq[:-1]
            while len(body) > 1 and in_band(body[-1]):
                body.pop()
            last = body[-1]
            tail = []
            if lado in ('top', 'bottom'):
                if abs(last[1] - lane) > 0.5:
                    tail.append((last[0], lane))
                tail.append((port[0], lane))
            else:
                if abs(last[0] - lane) > 0.5:
                    tail.append((lane, last[1]))
                tail.append((lane, port[1]))
            tail.append(port)
            new_seq = body[:]
            for t in tail:
                if abs(t[0] - new_seq[-1][0]) > 0.05 \
                        or abs(t[1] - new_seq[-1][1]) > 0.05:
                    new_seq.append(t)
            if len(new_seq) < 2:
                continue
            new_pts = new_seq if m['end'] else list(reversed(new_seq))
            current[key] = new_pts
            conn['computed_path'] = {
                'type': 'polyline',
                'points': [(round(x, 1), round(y, 1)) for x, y in new_pts],
            }
            rewritten += 1
    return rewritten
