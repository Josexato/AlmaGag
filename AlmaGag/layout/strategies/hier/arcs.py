"""
§E — Arcos de ciclo (WISH-LAF-002 Fase 3).

Las aristas que forman parte de un ciclo (aristas de recorrido + back-edge)
se dibujan como arcos con sentido de giro coherente:

- E15: un signo global aplicado a la normal de la dirección de recorrido
  (nU = (-dy, dx)/len). Con un signo, la ida queda como curva interior y el
  retorno como arco exterior — el lazo natural.
- E16: el signo se elige desde la arista de RETORNO (mayor caída de nivel)
  para que su normal apunte lejos del centroide del grafo.
- E17: comba adaptativa — base ~44px, crece sólo para librar nodos con
  proyección interior a la cuerda (0.06<t<0.94) y perpendicular pequeña
  (|perp|<~72px) del lado de la comba; tope ~320px.
"""

import math
from typing import Dict, List, Tuple
from AlmaGag.config import ICON_WIDTH, ICON_HEIGHT
from AlmaGag.layout.strategies.hier.shapes import clip_shape

BULGE_BASE = 44.0
BULGE_CAP = 320.0
PROX_PERP = 72.0
ICON_HALF = ICON_WIDTH / 2


def _center(e):
    return (e['x'] + ICON_WIDTH / 2, e['y'] + ICON_HEIGHT / 2)


def clip_to_border(elem, tx, ty):
    """
    Punto sobre el borde REAL del icono en la dirección (tx,ty) desde su centro
    (§G19: rombo para decisiones, rectángulo para el resto). Los extremos de
    todo cycle-arc caen EXACTAMENTE sobre el polígono de la forma.
    """
    return clip_shape(elem, tx, ty)


def route_cycle_arcs(layout, levels):
    """Asigna computed_path tipo 'bezier' a las aristas de ciclo (in-place)."""
    by_id = {e['id']: e for e in layout.elements}
    level = levels.level
    back = levels.back_edges
    if not back:
        return

    def placed(eid):
        e = by_id.get(eid)
        return e is not None and 'x' in e and 'y' in e

    # Grafo de flujo (sin back-edges) para hallar los componentes de ciclo.
    children: Dict[str, List[str]] = {}
    for c in layout.connections:
        f, t = c.get('from'), c.get('to')
        if placed(f) and placed(t) and (f, t) not in back:
            children.setdefault(f, []).append(t)

    # Componentes de ciclo: por cada back-edge (u→v), nodos en algún camino
    # v→…→u (grafo de flujo) + {u, v}.
    def cycle_nodes(u, v):
        comp = {u, v}
        stack = [v]
        seen = set()
        while stack:
            n = stack.pop()
            if n in seen:
                continue
            seen.add(n)
            # ¿n alcanza u?
            st2, sn2, reach = [n], set(), False
            while st2:
                m = st2.pop()
                if m in sn2:
                    continue
                sn2.add(m)
                if m == u:
                    reach = True
                    break
                st2.extend(children.get(m, []))
            if reach:
                comp.add(n)
            stack.extend(children.get(n, []))
        return comp

    # Centroide del grafo (nodos posicionados).
    cxs = [(_center(e)) for e in layout.elements if placed(e['id'])]
    cx0 = sum(p[0] for p in cxs) / len(cxs)
    cy0 = sum(p[1] for p in cxs) / len(cxs)

    handled = set()
    for (u, v) in back:
        if not (placed(u) and placed(v)):
            continue
        comp = cycle_nodes(u, v)
        # aristas del ciclo: (a→b) con ambos en comp (incluye back-edge u→v).
        cyc_edges = []
        for c in layout.connections:
            a, b = c.get('from'), c.get('to')
            if a in comp and b in comp and placed(a) and placed(b):
                cyc_edges.append(c)

        # E16: signo desde la arista de retorno (la back-edge u→v).
        ru, rv = _center(by_id[u]), _center(by_id[v])
        dx, dy = rv[0] - ru[0], rv[1] - ru[1]
        dlen = math.hypot(dx, dy) or 1.0
        nU = (-dy / dlen, dx / dlen)              # normal de la dirección
        mid = ((ru[0] + rv[0]) / 2, (ru[1] + rv[1]) / 2)
        away = (mid[0] - cx0, mid[1] - cy0)       # lejos del centroide
        sign = 1.0 if (nU[0] * away[0] + nU[1] * away[1]) >= 0 else -1.0

        # nodos del grafo para el cálculo de comba adaptativa
        node_centers = [(_center(e), e['id']) for e in layout.elements
                        if placed(e['id'])]

        for c in cyc_edges:
            a, b = by_id[c['from']], by_id[c['to']]
            ca, cb = _center(a), _center(b)
            ex, ey = cb[0] - ca[0], cb[1] - ca[1]
            elen = math.hypot(ex, ey) or 1.0
            n = (-ey / elen, ex / elen)           # normal de ESTA arista
            bdir = (sign * n[0], sign * n[1])     # E15: mismo signo global

            # E17: comba adaptativa — librar nodos cerca de la cuerda del lado.
            bulge = BULGE_BASE
            for (pc, pid) in node_centers:
                if pid in (c['from'], c['to']):
                    continue
                # proyección t sobre la cuerda
                t = ((pc[0] - ca[0]) * ex + (pc[1] - ca[1]) * ey) / (elen * elen)
                if not (0.06 < t < 0.94):
                    continue
                perp = (pc[0] - ca[0]) * n[0] + (pc[1] - ca[1]) * n[1]
                # sólo nodos del lado de la comba
                if perp * sign < 0:
                    continue
                if abs(perp) > PROX_PERP:
                    continue
                margin = ICON_HALF + 16
                need = (abs(perp) + margin) / (2 * t * (1 - t))
                bulge = max(bulge, need)
            bulge = min(bulge, BULGE_CAP)

            # Extremos EXACTAMENTE sobre el borde (no en el centro): se recorta
            # el centro hacia el otro nodo. Corrige el hueco de 15px (QA-Q1).
            start = clip_to_border(a, *cb)
            end = clip_to_border(b, *ca)
            sx, sy = start
            dx, dy = end[0] - sx, end[1] - sy

            # Puntos de control del bezier (1/3 y 2/3, desplazados por la comba).
            off = bulge * 1.33
            c1 = (sx + dx / 3 + bdir[0] * off, sy + dy / 3 + bdir[1] * off)
            c2 = (sx + 2 * dx / 3 + bdir[0] * off, sy + 2 * dy / 3 + bdir[1] * off)
            c['computed_path'] = {
                'type': 'bezier',
                'points': [start, end],
                'control_points': [c1, c2],
            }
            # marcar puertos → el renderer no aplica su offset de 15px
            c['_from_port'] = start
            c['_to_port'] = end
            # §E/§L40: la arista de RETORNO (la back-edge u→v) se dibuja
            # punteada — el arco exterior que cierra el lazo, distinto de las
            # aristas de ida (sólidas). Sólo marca; el renderer decide el dash
            # y respeta cualquier `style` explícito del usuario.
            if (c['from'], c['to']) == (u, v):
                c['_cycle_return'] = True
            handled.add((c['from'], c['to']))

    return handled
