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
from AlmaGag.layout.strategies.hier.leveling import Levels


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

    # Padres reales por nodo ANTES de la cirugía de ghosts (§B4 reemplaza al
    # padre de una arista larga por su cadena fantasma). §H25 los necesita.
    orig_parents = {i: list(parents.get(i, [])) for i in main_ids}

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

    # --- B5: carriles por descomposición de cadenas (longest-path primero) ---
    # Se extrae repetidamente la cadena forward más larga y se le da un carril.
    # El back-edge no participa (grafo ya sin ciclos → DAG). Esto sirve para
    # AMBOS casos: cuando el ciclo es el tronco queda inline (una columna, como
    # en es-primo); cuando es una rama lateral con tronco paralelo, queda en su
    # propia columna (como el ciclo I·J·K del stresstest).
    def _is_ghost(n):
        return str(n).startswith('__g_')

    # Longitud de cadena contando sólo nodos REALES (los ghosts de aristas
    # largas no inflan la cadena → no compiten con el tronco).
    _lp: Dict[str, int] = {}

    def longest(n):
        if n not in _lp:
            w = 0 if _is_ghost(n) else 1
            _lp[n] = w + max((longest(c) for c in children.get(n, [])), default=0)
        return _lp[n]

    # Hijo PRIMARIO que continúa la cadena/columna: el "más propio" de esta
    # rama = MENOS padres (un hijo con muchos padres es un cruce/fusión, no la
    # continuación); en empate, la cadena real más larga; luego orden estable.
    # Esto separa el tronco del ciclo en el stresstest (F→G sigue el tronco,
    # F→I cruza al ciclo) y mantiene el ciclo inline cuando es el único camino
    # (es-primo: init→cond→divides→inc).
    def _primary_key(c):
        return (-len(parents.get(c, [])), longest(c), -order.get(c, 0))

    lane_of: Dict[str, int] = {}
    next_lane = [-1]

    def new_lane():
        next_lane[0] += 1
        return next_lane[0]

    visited: set = set()

    def dfs(node, lane):
        visited.add(node)
        lane_of[node] = lane
        kids = [c for c in children.get(node, []) if c not in visited]
        kids.sort(key=_primary_key, reverse=True)
        for idx, c in enumerate(kids):
            if c in visited:
                continue
            dfs(c, lane if idx == 0 else new_lane())

    roots = sorted([i for i in main_ids if not parents.get(i)],
                   key=lambda n: (level[n], order.get(n, 0)))
    for r in roots:
        if r not in visited:
            dfs(r, new_lane())
    for n in sorted(main_ids, key=lambda n: (level[n], order.get(n, 0))):
        if n not in visited:
            dfs(n, new_lane())

    # Fusionar carriles SINGLETON (un solo nodo real) cuyo nodo alimenta otro
    # carril → ese nodo pasa a ENCABEZAR esa columna. Evita orfanatos como H
    # (H→I, con I ya reclamado por el carril del ciclo → H encabeza el ciclo).
    _rls = defaultdict(int)
    for _n, _ln in lane_of.items():
        if not _is_ghost(_n):
            _rls[_ln] += 1
    def _heads_lane(c):
        # c encabeza su carril si ningún padre suyo está en ese mismo carril.
        cln = lane_of.get(c)
        return all(lane_of.get(p) != cln for p in parents.get(c, []))

    for n in sorted(main_ids, key=lambda n: level[n]):
        if _is_ghost(n):
            continue
        ln = lane_of.get(n)
        if _rls.get(ln, 0) != 1:
            continue
        # preferir el hijo que ENCABEZA su carril (así n pasa a ser la nueva
        # cabeza real de esa columna, p.ej. H→I encabeza el ciclo, no H→F que
        # cae a mitad del tronco).
        cand = [c for c in children.get(n, [])
                if not _is_ghost(c) and lane_of.get(c) not in (None, ln)]
        cand.sort(key=lambda c: (0 if _heads_lane(c) else 1, level[c]))
        if cand:
            c = cand[0]
            cln = lane_of[c]
            _rls[ln] -= 1
            _rls[cln] += 1
            lane_of[n] = cln

    # Separar el TALLO (bifurcación superior + ancestros de hijo único) a su
    # propio carril, para que no quede pegado a la columna de un hijo y B7
    # pueda centrarlo entre las columnas que genera (simetría del fork).
    # G21: SOLO si las dos ramas son cadenas de ≥2 nodos (columnas reales). Si
    # una rama es hoja/sumidero, el tallo sigue recto sobre la cadena dominante.
    # Tamaño de carril contando sólo nodos REALES (los ghosts de aristas
    # largas no forman una columna → no cuentan como rama de un fork).
    lane_size = defaultdict(int)
    for _n, _ln in lane_of.items():
        if not _is_ghost(_n):
            lane_size[_ln] += 1

    def _child_lanes(i):
        return {lane_of.get(c) for c in children.get(i, [])
                if c in lane_of and not _is_ghost(c)}

    def _is_real_fork(i):
        cls = _child_lanes(i)
        return len(cls) >= 2 and all(lane_size.get(ln, 0) >= 2 for ln in cls)

    bifs0 = [i for i in main_ids if _is_real_fork(i)]
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
            # G21: sólo centra si es un fork real (ambas ramas ≥2 nodos) y el
            # nodo no continúa una de esas columnas.
            if _is_real_fork(i) and lane_of.get(i) not in child_lanes:
                x[i] = sum(x[c] for c in ch) / len(ch)

    # --- B8: tallo raíz — ancestros de hijo único sobre la bifurcación
    # heredan la X (centrada) de la bifurcación → tramo raíz→fork vertical. ---
    biforcations = [i for i in main_ids if _is_real_fork(i)]
    for bif in sorted(biforcations, key=lambda i: (level[i], order.get(i, 0))):
        node = bif
        for _ in range(len(main_ids)):
            ps = parents.get(node, [])
            if len(ps) != 1 or len(children.get(ps[0], [])) != 1:
                break
            x[ps[0]] = x[bif]
            node = ps[0]

    # --- §H25: sumidero compartido junto a sus padres ---
    # Un sumidero (0 hijos) con ≥2 padres reales cae, por descomposición de
    # carriles, en una columna del margen lejano (obliga carriles larguísimos
    # que cruzan el diagrama). Se reubica en la columna ADYACENTE al baricentro
    # de sus padres, del lado LIBRE (el menos poblado) → carriles cortos y
    # paralelos que bajan pegados a la cadena dominante.
    for i in main_ids:
        if _is_ghost(i) or children.get(i):
            continue
        rp = [p for p in orig_parents.get(i, []) if p in x and not _is_ghost(p)]
        if len(rp) < 2:
            continue
        bx = sum(x[p] for p in rp) / len(rp)
        left = sum(1 for n in real_ids if n != i and x.get(n, bx) < bx - 0.01)
        right = sum(1 for n in real_ids if n != i and x.get(n, bx) > bx + 0.01)
        # una sola columna de separación (MIN_SEP: sin hueco para otro carril).
        x[i] = bx - MIN_SEP if left <= right else bx + MIN_SEP
    _resolve_rows()

    # Extensión de las columnas principales (para colocar satélites/tomas
    # SIN encimarlas con los nodos del tronco/ciclo). Considera nodos reales.
    real_xs = [x[n] for n in real_ids if n in x] or [0.0]
    main_min, main_max = min(real_xs), max(real_xs)
    center = sum(real_xs) / len(real_xs)

    # --- §A2 satélites: al costado del padre, hacia afuera del centro ---
    for sat, parent in satellites.items():
        px = x.get(parent, 0)
        x[sat] = px + 1.5 * STEP if px >= center else px - 1.5 * STEP

    # --- §A3/§C11 tomas (K38): a UN carril del destino, del lado libre
    # (exterior respecto al centro), NO en el margen del canvas. La toma vive a
    # medio nivel sobre su destino (§A3), así que un solo paso lateral basta:
    # el conector queda corto (≈1 columna) en vez de cruzar todo el diagrama.
    # Varias tomas al MISMO destino se escalonan hacia afuera para no encimarse. ---
    feeders_by_target: Dict[str, List[str]] = defaultdict(list)
    for feeder, target in side_feeders.items():
        feeders_by_target[target].append(feeder)
    for target, feeders in feeders_by_target.items():
        tx = x.get(target, center)
        outward = -1 if tx <= center else 1
        for rank, feeder in enumerate(sorted(feeders)):
            x[feeder] = tx + outward * MIN_SEP * (rank + 1)

    # Waypoints §B4: (x, nivel) de los ghosts por arista larga.
    waypoints = {edge: [(x[g], level[g]) for g in chain if g in x]
                 for edge, chain in ghost_chain.items()}
    # X de todos los nodos reales (incluye satélites y tomas; excluye ghosts).
    real_x = {n: x[n] for n in x if not str(n).startswith('__g_')}
    return real_x, waypoints
