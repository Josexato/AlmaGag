"""
§B — Posicionamiento transversal (columnas) (WISH-LAF-002).

Trabaja en unidades de columna abstractas sobre el resultado de §A.

- B4: nodos fantasma en aristas largas + barycenter (minimiza cruces).
- B5: carriles rectos por cadena (X mediana, separación mínima entre carriles).
- B6: alineación al ancestro dominante (padre de menor nivel).
- B7: centrado del nodo bifurcación entre las cabezas de sus columnas.
- B8: tallo raíz — propaga la X de la bifurcación a los ancestros de hijo único.
"""

from collections import defaultdict
from typing import Dict, List, Tuple
from AlmaGag.layout.hier.leveling import Levels


def _int_level(v: float) -> int:
    # las tomas viven a X.5; para agrupar en filas usamos el entero inferior.
    return int(v) if float(v).is_integer() else int(v)  # floor implícito para X.5≥0


def compute_columns(levels: Levels, elements: List[dict],
                    connections: List[dict], passes: int = 20):
    """
    Devuelve (x, waypoints):
      x          {id: x_abstracta} de nodos reales (Y se deriva del nivel).
      waypoints  {(from, to): [x_abstracta por nivel intermedio]} para las
                 aristas largas partidas con nodos fantasma (§B4).
    """
    level = dict(levels.level)  # copia (se le agregan ghosts)
    satellites = levels.satellites
    side_feeders = levels.side_feeders
    back = levels.back_edges

    real_ids = [i for i in level if i not in satellites and i not in side_feeders]
    main_ids = list(real_ids)

    # Grafo de flujo (sin back-edges, sin satélites/tomas como nodos de columna).
    children: Dict[str, List[str]] = {i: [] for i in main_ids}
    parents: Dict[str, List[str]] = {i: [] for i in main_ids}
    for c in connections:
        f, t = c.get('from'), c.get('to')
        if f in main_ids and t in main_ids and (f, t) not in back:
            children[f].append(t)
            parents[t].append(f)

    # --- §B4: nodos fantasma en aristas largas (|Δnivel entero| > 1) ---
    # La arista f→t se parte en f→g1→…→gk→t con un ghost por nivel intermedio.
    # Los ghosts participan del barycenter/carriles (reducen cruces y dan a la
    # arista un carril propio); sus X se devuelven como waypoints para el ruteo.
    # Bajo min-parent (§A1) ninguna arista forward baja más de 1 nivel; las
    # largas van de un nodo PROFUNDO a uno SUPERFICIAL (Δ negativo grande).
    # Se parten en ambos sentidos: |Δnivel entero| > 1.
    ghost_chain: Dict[tuple, List[str]] = {}
    long_edges = []
    for f in real_ids:
        for t in list(children.get(f, [])):
            lf, lt = int(level[f]), int(level[t])
            if abs(lt - lf) > 1:
                long_edges.append((f, t, lf, lt))
    for (f, t, lf, lt) in long_edges:
        children[f] = [c for c in children[f] if c != t]
        parents[t] = [p for p in parents[t] if p != f]
        step = 1 if lt > lf else -1
        chain = []
        prev = f
        for L in range(lf + step, lt, step):
            g = f"__g_{f}_{t}_{L}"
            level[g] = L
            children[g] = []
            parents[g] = []
            main_ids.append(g)
            children[prev].append(g)
            parents[g].append(prev)
            chain.append(g)
            prev = g
        children[prev].append(t)
        parents[t].append(prev)
        ghost_chain[(f, t)] = chain

    idset = set(level)

    # Nodos cíclicos: por cada back-edge (u→v), el ciclo es v→…→u en el grafo
    # de flujo. Se usa para preferir el TRONCO (padre acíclico) al elegir el
    # padre dominante — así el tronco y el ciclo quedan en columnas separadas.
    cyclic: set = set()
    for (u, v) in back:
        cyclic.add(u)
        cyclic.add(v)
        # reachability v→…→u
        stack, seen = [v], set()
        while stack:
            n = stack.pop()
            if n in seen:
                continue
            seen.add(n)
            if n == u:
                continue
            for ch in children.get(n, []):
                stack.append(ch)
        # incluir nodos en algún camino v→u
        for n in seen:
            # n está en el ciclo si puede volver a u
            st2, sn2 = [n], set()
            reach_u = False
            while st2:
                m = st2.pop()
                if m in sn2:
                    continue
                sn2.add(m)
                if m == u:
                    reach_u = True
                    break
                for ch in children.get(m, []):
                    st2.append(ch)
            if reach_u:
                cyclic.add(n)

    # Filas por nivel entero.
    by_level: Dict[int, List[str]] = {}
    for i in main_ids:
        by_level.setdefault(int(level[i]), []).append(i)
    levels_sorted = sorted(by_level)

    # Orden inicial estable por id dentro de cada fila.
    for lv in levels_sorted:
        by_level[lv].sort()
    order: Dict[str, int] = {}
    for lv in levels_sorted:
        for idx, i in enumerate(by_level[lv]):
            order[i] = idx

    # --- B4: barycenter alternando arriba/abajo ---
    for p in range(passes):
        downward = (p % 2 == 0)
        seq = levels_sorted if downward else list(reversed(levels_sorted))
        for lv in seq:
            row = by_level[lv]
            if len(row) <= 1:
                continue
            neigh = parents if downward else children
            def bary(n):
                ns = [order[m] for m in neigh.get(n, []) if m in order]
                return sum(ns) / len(ns) if ns else order[n]
            row.sort(key=lambda n: (bary(n), n))
            for idx, i in enumerate(row):
                order[i] = idx

    # X inicial = orden ordinal * paso.
    STEP = 1.0
    x: Dict[str, float] = {}
    for lv in levels_sorted:
        for i in by_level[lv]:
            x[i] = order[i] * STEP

    MIN_SEP = 1.5 * STEP
    LANE = 2.0 * STEP

    # --- B5: carriles cycle-aware ---
    # (1) Cada componente de ciclo (SCC) recibe UN carril: sus miembros forman
    #     una columna vertical (I·J·K). (2) Los nodos acíclicos se descomponen
    #     por spine (DFS de primera visita, hijo de subárbol más profundo
    #     continúa el carril). Así tronco y ciclo quedan en columnas propias.
    def subtree_depth(n, seen):
        if n in seen:
            return 0
        seen.add(n)
        # sólo aristas hacia nodos acíclicos (el spine no entra al ciclo)
        return 1 + max((subtree_depth(c, seen) for c in children.get(n, [])
                        if c not in cyclic), default=0)

    lane_of: Dict[str, int] = {}
    next_lane = [-1]

    def new_lane():
        next_lane[0] += 1
        return next_lane[0]

    # (1) componentes de ciclo → un carril cada uno.
    cyc_seen: set = set()
    for n in sorted(cyclic, key=lambda n: (level[n], order.get(n, 0))):
        if n in cyc_seen:
            continue
        comp, stack = [], [n]
        while stack:
            m = stack.pop()
            if m in cyc_seen:
                continue
            cyc_seen.add(m)
            comp.append(m)
            for c in children.get(m, []):
                if c in cyclic and c not in cyc_seen:
                    stack.append(c)
            for p in parents.get(m, []):
                if p in cyclic and p not in cyc_seen:
                    stack.append(p)
        ln = new_lane()
        for m in comp:
            lane_of[m] = ln

    # (2) spine DFS sobre nodos acíclicos.
    visited: set = set(lane_of)

    def dfs(node, lane):
        visited.add(node)
        lane_of[node] = lane
        kids = [c for c in children.get(node, [])
                if c not in visited and c not in cyclic]
        kids.sort(key=lambda c: (-subtree_depth(c, set()), order.get(c, 0)))
        for idx, c in enumerate(kids):
            if c in visited:
                continue
            dfs(c, lane if idx == 0 else new_lane())

    roots = sorted([i for i in main_ids if not parents.get(i)],
                   key=lambda n: (level[n], order.get(n, 0)))
    for r in roots:
        if r not in visited and r not in cyclic:
            dfs(r, new_lane())
    for n in sorted(main_ids, key=lambda n: (level[n], order.get(n, 0))):
        if n not in lane_of:
            dfs(n, new_lane()) if n not in cyclic else None

    # Fusionar carriles acíclicos SINGLETON que alimentan un carril de ciclo:
    # el nodo de entrada (p.ej. H→I) pasa a ENCABEZAR la columna del ciclo,
    # evitando un carril suelto y el conector diagonal largo hacia el ciclo.
    cycle_lanes = {lane_of[n] for n in cyclic if n in lane_of}
    lane_members = defaultdict(list)
    for n, ln in lane_of.items():
        lane_members[ln].append(n)
    for n in list(main_ids):
        ln = lane_of.get(n)
        if ln in cycle_lanes or len(lane_members.get(ln, [])) != 1:
            continue
        # ¿algún hijo en un carril de ciclo?
        for c in children.get(n, []):
            if lane_of.get(c) in cycle_lanes:
                lane_of[n] = lane_of[c]
                break

    # Separar el TALLO (bifurcación superior + ancestros de hijo único) a su
    # propio carril, para que no quede pegado a la columna de un hijo y B7
    # pueda centrarlo entre las columnas que genera (simetría del fork).
    def _child_lanes(i):
        return {lane_of.get(c) for c in children.get(i, []) if c in lane_of}
    bifs0 = [i for i in main_ids if len(_child_lanes(i)) >= 2]
    if bifs0:
        top = min(bifs0, key=lambda i: (level[i], order.get(i, 0)))
        stem = [top]
        node = top
        for _ in range(len(main_ids)):
            ps = parents.get(node, [])
            if len(ps) != 1 or len(children.get(ps[0], [])) != 1:
                break
            stem.append(ps[0])
            node = ps[0]
        next_lane[0] += 1
        stem_lane = next_lane[0]
        for s in stem:
            lane_of[s] = stem_lane

    # Ordenar carriles izquierda→derecha por baricentro del orden de miembros.
    n_lanes = next_lane[0] + 1
    members = {ln: [n for n in main_ids if lane_of.get(n) == ln] for ln in range(n_lanes)}
    def lane_bary(ln):
        ms = members[ln]
        return sum(order.get(m, 0) for m in ms) / len(ms) if ms else 0
    used = [ln for ln in range(n_lanes) if members[ln]]
    lane_x = {ln: rank * LANE for rank, ln in enumerate(sorted(used, key=lane_bary))}
    for n in main_ids:
        x[n] = lane_x[lane_of[n]]

    def _resolve_rows():
        for lv in levels_sorted:
            row = sorted(by_level[lv], key=lambda n: (x[n], order[n]))
            for k in range(1, len(row)):
                if x[row[k]] - x[row[k - 1]] < MIN_SEP:
                    x[row[k]] = x[row[k - 1]] + MIN_SEP

    _resolve_rows()

    # --- B7: centrado de bifurcación entre los carriles de sus hijos ---
    # Un nodo cuyos hijos encabezan ≥2 carriles distintos se reubica en el
    # promedio de esas columnas → forks simétricos. Se aplica de abajo hacia
    # arriba para que el efecto suba por el tallo.
    for lv in reversed(levels_sorted):
        for i in by_level[lv]:
            ch = [c for c in children.get(i, []) if c in x]
            child_lanes = {lane_of.get(c) for c in ch}
            if len(ch) >= 2 and len(child_lanes) >= 2 and lane_of.get(i) not in child_lanes:
                x[i] = sum(x[c] for c in ch) / len(ch)

    # --- B8: tallo raíz — ancestros de hijo único sobre la bifurcación
    # heredan la X (centrada) de la bifurcación → tramo raíz→fork vertical. ---
    biforcations = [i for i in main_ids
                    if len({lane_of.get(c) for c in children.get(i, [])}) >= 2]
    for bif in sorted(biforcations, key=lambda i: (level[i], order.get(i, 0))):
        node = bif
        for _ in range(len(main_ids)):
            ps = parents.get(node, [])
            if len(ps) != 1 or len(children.get(ps[0], [])) != 1:
                break
            x[ps[0]] = x[bif]
            node = ps[0]

    # Extensión de las columnas principales (para colocar satélites/tomas
    # SIN encimarlas con los nodos del tronco/ciclo). Considera nodos reales.
    real_xs = [x[n] for n in real_ids if n in x] or [0.0]
    main_min, main_max = min(real_xs), max(real_xs)
    center = sum(real_xs) / len(real_xs)

    # --- §A2 satélites: al costado del padre, hacia afuera del centro ---
    for sat, parent in satellites.items():
        px = x.get(parent, 0)
        x[sat] = px + 1.5 * STEP if px >= center else px - 1.5 * STEP

    # --- §A3/§C11 tomas: al MARGEN exterior (más allá de las columnas
    # principales), del lado del destino respecto al centro ---
    left_margin = main_min - LANE
    right_margin = main_max + LANE
    for feeder, target in side_feeders.items():
        tx = x.get(target, center)
        x[feeder] = left_margin if tx <= center else right_margin

    # Waypoints §B4: (x, nivel) de los ghosts por arista larga.
    waypoints = {edge: [(x[g], level[g]) for g in chain if g in x]
                 for edge, chain in ghost_chain.items()}
    # X de todos los nodos reales (incluye satélites y tomas; excluye ghosts).
    real_x = {n: x[n] for n in x if not str(n).startswith('__g_')}
    return real_x, waypoints
