"""
Optimizador de offsets por bisección — rescate ① desde LAF (el aporte más limpio).

Idea: dado un conjunto de nodos ya posicionados y agrupados (p.ej. por fila/nivel
o por columna/carril), desplazar cada GRUPO como un bloque rígido en un eje para
minimizar la longitud ponderada total de los conectores que cruzan entre grupos.

La longitud de una arista es √((Δpos+offset)² + Δperp²). Su derivada respecto al
offset del grupo, Σ w·(Δpos+offset)/√(...), es monótona creciente → la función es
**convexa** y tiene un único mínimo. Se halla la raíz de la derivada por
bracketing + bisección (sin gradiente, robusto). Como el óptimo de un grupo
depende de los demás, se itera (descenso por coordenadas).

Función pura y agnóstica del motor: no sabe de filas ni columnas, sólo de
"grupos que se mueven juntos en un eje". hier la usa para afinar la X.
"""

import math
from typing import Dict, List, Tuple

Pos = Tuple[float, float]


def _derivative(terms: List[Tuple[float, float, float]], offset: float) -> float:
    """d/doffset de Σ w·√((a+offset)² + perp²) = Σ w·(a+offset)/√(...)."""
    d = 0.0
    for a, perp, w in terms:
        dx = a + offset
        denom = math.sqrt(dx * dx + perp * perp)
        if denom == 0.0:
            continue
        d += w * (dx / denom)
    return d


def _optimal_offset(terms: List[Tuple[float, float, float]],
                    start: float, bracket: float) -> float:
    """Raíz de la derivada (convexa) por bracketing + bisección. `terms` son
    (a, perp, w): a = desplazamiento base en el eje, perp = separación en el otro
    eje, w = peso. Devuelve el offset óptimo (o `start` si no hay bracket)."""
    if not terms:
        return start
    low, high = start - bracket, start + bracket
    d_low, d_high = _derivative(terms, low), _derivative(terms, high)
    # Expandir el intervalo hasta que la derivada cambie de signo.
    guard = 0
    while d_low > 0 and guard < 8:
        low -= (high - low)
        d_low = _derivative(terms, low)
        guard += 1
    guard = 0
    while d_high < 0 and guard < 8:
        high += (high - low)
        d_high = _derivative(terms, high)
        guard += 1
    if d_low > 0 or d_high < 0:
        return start                       # sin bracket claro → no mover
    for _ in range(48):
        mid = (low + high) / 2.0
        if _derivative(terms, mid) < 0.0:
            low = mid
        else:
            high = mid
    return (low + high) / 2.0


def optimize_group_offsets(
    groups: Dict[object, List[str]],
    positions: Dict[str, Pos],
    adjacency: Dict[str, List[Tuple[str, float]]],
    axis: str = 'x',
    iterations: int = 4,
    bracket: float = 20.0,
    tol: float = 0.001,
) -> Dict[object, float]:
    """Offset óptimo por grupo para minimizar la longitud ponderada de conectores.

    Args:
        groups: {clave_grupo: [node_ids]} — nodos que se desplazan juntos.
        positions: {node_id: (x, y)} posiciones base.
        adjacency: {node_id: [(neighbor_id, weight)]} — aristas (no dirigidas a
            efectos de la métrica). Sólo cuentan las que cruzan de grupo.
        axis: 'x' (desplaza en X, perpendicular Y) o 'y' (al revés).
        iterations: pasadas de descenso por coordenadas.
        bracket: semiancho inicial de búsqueda del bracket (px).
        tol: cambio mínimo para seguir iterando.

    Devuelve {clave_grupo: offset} (0.0 para grupos sin aristas inter-grupo).
    """
    ax, perp_ax = (0, 1) if axis == 'x' else (1, 0)
    group_of: Dict[str, object] = {}
    for key, nodes in groups.items():
        for n in nodes:
            group_of[n] = key

    offsets: Dict[object, float] = {k: 0.0 for k in groups}

    def cur(node):
        """Posición actual del nodo en el eje = base + offset de su grupo."""
        return positions[node][ax] + offsets.get(group_of.get(node), 0.0)

    for _ in range(iterations):
        moved = 0.0
        for key, nodes in groups.items():
            terms: List[Tuple[float, float, float]] = []
            for n in nodes:
                if n not in positions:
                    continue
                base = positions[n][ax]
                perp_n = positions[n][perp_ax]
                for nb, w in adjacency.get(n, []):
                    if nb not in positions or group_of.get(nb) == key:
                        continue                   # intra-grupo no depende del offset
                    a = base - cur(nb)
                    perp = perp_n - positions[nb][perp_ax]
                    terms.append((a, perp, float(w)))
            if not terms:
                continue
            new = _optimal_offset(terms, offsets[key], bracket)
            moved = max(moved, abs(new - offsets[key]))
            offsets[key] = new
        if moved <= tol:
            break
    return offsets
