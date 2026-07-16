"""
§A — Asignación de niveles jerárquicos (WISH-LAF-002).

Función pura sobre (elements, connections). No depende de StructureInfo ni de
la maquinaria de contenedores virtuales de LAF.

- A1 (min-parent): nivel(n) = min(nivel(padre válido)) + 1 sobre el grafo sin
  back-edges. Compacta y alinea hermanos (a diferencia del longest-path).
- A2 (satélites): hoja (0 salidas, 1 entrada, fuera de ciclo) cuyo único padre
  se ramifica (≥2 salidas) Y continúa el flujo (tiene hijo no-hoja) → nivel del
  padre; se coloca al costado (no en fila propia).
- A3 (tomas laterales): fuente (0 entradas, 1 salida) cuyo destino ya tiene ≥2
  padres acíclicos → nivel = nivel(destino) − 0.5, al margen exterior.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Set, Tuple

from AlmaGag.layout.strategies.hier.scc import (
    strongly_connected_components, feedback_back_edges)


@dataclass
class Levels:
    """Resultado de §A."""
    level: Dict[str, float]                       # id → nivel (puede ser X.5 en tomas)
    satellites: Dict[str, str] = field(default_factory=dict)     # hoja → padre
    side_feeders: Dict[str, str] = field(default_factory=dict)   # fuente → destino
    back_edges: Set[Tuple[str, str]] = field(default_factory=set)
    sccs: List[Set[str]] = field(default_factory=list)           # componentes de 2+ (ciclos)


def compute_levels(elements: List[dict], connections: List[dict]) -> Levels:
    """Calcula niveles §A para elementos NO contenidos (root)."""
    contained = set()
    for e in elements:
        for ref in e.get('contains', []):
            contained.add(ref['id'] if isinstance(ref, dict) else ref)
    ids = [e['id'] for e in elements if e['id'] not in contained]
    idset = set(ids)

    out_graph: Dict[str, List[str]] = {i: [] for i in ids}
    incoming: Dict[str, List[str]] = {i: [] for i in ids}
    for c in connections:
        f, t = c.get('from'), c.get('to')
        if f in idset and t in idset and f != t:
            out_graph[f].append(t)
            incoming[t].append(f)

    # §A back-edges vía SCC (rescate ②): componentes canónicos → feedback set
    # que depende sólo del ciclo, no del recorrido global. En un DAG da ∅; en un
    # ciclo simple, la arista que lo cierra (idéntico al DFS previo).
    sccs = strongly_connected_components(ids, out_graph)
    cyclic_sccs = [c for c in sccs if len(c) >= 2]
    back_edges = feedback_back_edges(ids, out_graph, incoming, sccs)

    outdeg = {i: len(out_graph[i]) for i in ids}
    acyclic_out = {i: 0 for i in ids}
    acyclic_in: Dict[str, List[str]] = {i: [] for i in ids}
    for f in ids:
        for t in out_graph[f]:
            if (f, t) in back_edges:
                continue
            acyclic_out[f] += 1
            acyclic_in[t].append(f)

    # --- A2: satélites ---
    satellites: Dict[str, str] = {}
    for i in ids:
        if outdeg[i] != 0:
            continue
        parents = incoming[i]
        if len(parents) != 1:
            continue
        if any((p, i) in back_edges or (i, p) in back_edges for p in parents):
            continue
        p = parents[0]
        if acyclic_out.get(p, 0) < 2:
            continue
        # el padre debe continuar el flujo (algún hijo no-hoja)
        if any(outdeg.get(ch, 0) > 0 for ch in out_graph[p] if (p, ch) not in back_edges):
            satellites[i] = p

    # --- A3: tomas laterales ---
    side_feeders: Dict[str, str] = {}
    for i in ids:
        if len(incoming[i]) != 0:
            continue
        if len(out_graph[i]) != 1:
            continue
        t = out_graph[i][0]
        if len(acyclic_in.get(t, [])) >= 2:
            side_feeders[i] = t

    excluded = set(satellites) | set(side_feeders)

    # --- A1: min-parent (relajación topológica sobre grafo sin back-edges) ---
    def valid_parents(n):
        return [p for p in acyclic_in.get(n, []) if p not in excluded]

    level: Dict[str, float] = {i: 0 for i in ids if i not in excluded}
    for _ in range(len(ids) + 1):
        changed = False
        for n in ids:
            if n in excluded:
                continue
            ps = valid_parents(n)
            new = (min(level[p] for p in ps) + 1) if ps else 0
            if new != level.get(n):
                level[n] = new
                changed = True
        if not changed:
            break

    # G20 (excepción a A1): un SUMIDERO (0 salidas, ≥2 padres acíclicos) va
    # DEBAJO de su último padre → nivel = max(nivel de padres)+1. Así los
    # terminales de un flowchart (NO es primo, ES PRIMO) caen al fondo, cerca
    # de todos sus orígenes, en vez de subir por min-parent y alargar aristas.
    for i in ids:
        if i in excluded or outdeg[i] != 0:
            continue
        # padres ya nivelados (excluye satélites/tomas, que se asignan luego)
        ps = [p for p in acyclic_in.get(i, []) if p in level]
        if len(ps) >= 2:
            level[i] = max(level[p] for p in ps) + 1

    # satélites = nivel del padre; tomas = nivel del destino − 0.5
    for sat, parent in satellites.items():
        level[sat] = level.get(parent, 0)
    for feeder, target in side_feeders.items():
        level[feeder] = level.get(target, 0) - 0.5

    return Levels(level=level, satellites=satellites,
                  side_feeders=side_feeders, back_edges=back_edges,
                  sccs=cyclic_sccs)
