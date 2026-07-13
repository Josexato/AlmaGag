"""
§B — Posicionamiento transversal (columnas) (WISH-LAF-002).

Trabaja en unidades de columna abstractas sobre el resultado de §A.

- B4: nodos fantasma en aristas largas + barycenter (minimiza cruces).
- B5: carriles rectos por cadena (X mediana, separación mínima entre carriles).
- B6: alineación al ancestro dominante (padre de menor nivel).
- B7: centrado del nodo bifurcación entre las cabezas de sus columnas.
- B8: tallo raíz — propaga la X de la bifurcación a los ancestros de hijo único.
"""

from typing import Dict, List, Tuple
from AlmaGag.layout.hier.leveling import Levels


def _int_level(v: float) -> int:
    # las tomas viven a X.5; para agrupar en filas usamos el entero inferior.
    return int(v) if float(v).is_integer() else int(v)  # floor implícito para X.5≥0


def compute_columns(levels: Levels, elements: List[dict],
                    connections: List[dict], passes: int = 20) -> Dict[str, float]:
    """
    Devuelve {id: x_abstracta}. Y se deriva del nivel (en el optimizer).
    """
    level = levels.level
    satellites = levels.satellites
    side_feeders = levels.side_feeders
    back = levels.back_edges

    main_ids = [i for i in level if i not in satellites and i not in side_feeders]
    idset = set(level)

    # Grafo de flujo (sin back-edges, sin satélites/tomas como nodos de columna).
    children: Dict[str, List[str]] = {i: [] for i in main_ids}
    parents: Dict[str, List[str]] = {i: [] for i in main_ids}
    for c in connections:
        f, t = c.get('from'), c.get('to')
        if f in main_ids and t in main_ids and (f, t) not in back:
            children[f].append(t)
            parents[t].append(f)

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

    def dominant_parent(n):
        ps = parents.get(n, [])
        if not ps:
            return None
        # B6: ancestro de menor nivel; empate → mismo "tipo" (tronco/ciclo)
        # que el nodo, luego acíclico, luego orden estable.
        n_cyclic = n in cyclic
        return min(ps, key=lambda p: (
            level[p],
            0 if (p in cyclic) == n_cyclic else 1,
            0 if p not in cyclic else 1,
            order.get(p, 0),
        ))

    # --- B5/B6/B7: alineación iterativa a la columna del ancestro dominante
    # + centrado de bifurcaciones, con separación mínima por fila. Produce
    # columnas verticales por cadena (tronco / ciclo) sin colapsos.
    for _ in range(passes):
        for lv in levels_sorted:               # B6 (top-down)
            for i in by_level[lv]:
                dp = dominant_parent(i)
                if dp is not None:
                    x[i] = x[dp]
        for lv in reversed(levels_sorted):      # B7 (bottom-up)
            for i in by_level[lv]:
                ch = [c for c in children.get(i, []) if c in x]
                if len(ch) >= 2:
                    x[i] = sum(x[c] for c in ch) / len(ch)
        for lv in levels_sorted:                # separación por fila
            row = sorted(by_level[lv], key=lambda n: (x[n], order[n]))
            for k in range(1, len(row)):
                if x[row[k]] - x[row[k - 1]] < MIN_SEP:
                    x[row[k]] = x[row[k - 1]] + MIN_SEP

    # --- B8: tallo raíz — ancestros de hijo único sobre la bifurcación
    # heredan su X (tramo raíz→bifurcación vertical). ---
    biforcations = [i for i in main_ids if len(children.get(i, [])) >= 2]
    if biforcations:
        top_bif = min(biforcations, key=lambda i: (level[i], order.get(i, 0)))
        node = top_bif
        for _ in range(len(main_ids)):
            ps = parents.get(node, [])
            if len(ps) != 1 or len(children.get(ps[0], [])) != 1:
                break
            x[ps[0]] = x[top_bif]
            node = ps[0]

    # --- Satélites: al costado del padre (columna contigua) ---
    for sat, parent in satellites.items():
        x[sat] = x.get(parent, 0) + 1.5 * STEP

    # --- Tomas: al margen exterior, del lado más lejano al centro ---
    if x:
        center = sum(x.values()) / len(x)
    else:
        center = 0
    for feeder, target in side_feeders.items():
        tx = x.get(target, 0)
        x[feeder] = tx - 2.0 * STEP if tx <= center else tx + 2.0 * STEP

    return x
