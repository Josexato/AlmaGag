"""
Componentes fuertemente conexos (SCC) para el nivelado §A — rescate ② desde LAF.

hier detectaba las aristas de ciclo con un DFS de coloreo global cuyo resultado
depende de por dónde entra el recorrido al ciclo. Los SCC, en cambio, son
**canónicos**: el conjunto de componentes fuertemente conexos de un grafo es
único, no depende del orden. Contrayendo cada SCC a un representante se obtiene
la *condensación*, un DAG garantizado — base sólida para nivelar (longest/
min-parent) incluso con ciclos entrelazados que rompían al DFS ad-hoc.

Este módulo aporta:
- `strongly_connected_components`: Tarjan **iterativo** (sin límite de recursión)
  y determinista (itera en el orden de entrada).
- `feedback_back_edges`: conjunto de aristas de retorno derivado de los SCC —
  sólo aristas DENTRO de un SCC, elegidas por un DFS restringido al componente.
  Para un DAG da ∅; para un ciclo simple, la arista que lo cierra.

Sobre grafos acíclicos y ciclos simples reproduce exactamente lo que hier hacía;
la diferencia (y la robustez) aparece en SCC de 3+ con múltiples ciclos.
"""

from typing import Dict, List, Set, Tuple


def strongly_connected_components(
    ids: List[str], out_graph: Dict[str, List[str]]
) -> List[Set[str]]:
    """SCCs por Tarjan iterativo. Orden determinista (por orden de entrada).

    Devuelve la lista de componentes (cada uno un set de ids). Los nodos triviales
    (sin ciclo) salen como componentes de un elemento.
    """
    index_of: Dict[str, int] = {}
    lowlink: Dict[str, int] = {}
    on_stack: Set[str] = set()
    stack: List[str] = []
    sccs: List[Set[str]] = []
    counter = 0

    for root in ids:
        if root in index_of:
            continue
        # Pila explícita de trabajo: (nodo, índice del próximo vecino a visitar).
        work: List[Tuple[str, int]] = [(root, 0)]
        while work:
            v, pi = work[-1]
            if pi == 0:
                index_of[v] = counter
                lowlink[v] = counter
                counter += 1
                stack.append(v)
                on_stack.add(v)
            neighbors = out_graph.get(v, [])
            if pi < len(neighbors):
                work[-1] = (v, pi + 1)
                w = neighbors[pi]
                if w not in index_of:
                    work.append((w, 0))
                elif w in on_stack:
                    lowlink[v] = min(lowlink[v], index_of[w])
            else:
                # Terminó v: propagar lowlink al padre y, si es raíz, cerrar SCC.
                if lowlink[v] == index_of[v]:
                    comp: Set[str] = set()
                    while True:
                        w = stack.pop()
                        on_stack.discard(w)
                        comp.add(w)
                        if w == v:
                            break
                    sccs.append(comp)
                work.pop()
                if work:
                    parent = work[-1][0]
                    lowlink[parent] = min(lowlink[parent], lowlink[v])
    return sccs


def feedback_back_edges(
    ids: List[str],
    out_graph: Dict[str, List[str]],
    incoming: Dict[str, List[str]],
    sccs: List[Set[str]],
) -> Set[Tuple[str, str]]:
    """Aristas de retorno (feedback set) derivadas de los SCC.

    Sólo se consideran aristas cuyos dos extremos están en el mismo SCC no
    trivial (o self-loops). Dentro de cada componente se corre un DFS restringido
    al SCC, arrancando por los nodos de ENTRADA (con predecesor externo) en orden
    de entrada, y las aristas que apuntan a un nodo GRIS son las de retorno. Esto
    hace que el feedback set dependa sólo del componente, no del recorrido global.
    """
    comp_of: Dict[str, int] = {}
    for ci, comp in enumerate(sccs):
        for n in comp:
            comp_of[n] = ci

    # self-loops: son su propia arista de retorno.
    back: Set[Tuple[str, str]] = set()
    cyclic: Dict[int, Set[str]] = {}
    for f in ids:
        for t in out_graph.get(f, []):
            if f == t:
                back.add((f, t))
            elif comp_of.get(f) == comp_of.get(t):
                cyclic.setdefault(comp_of[f], set()).add(f)
                cyclic.setdefault(comp_of[f], set()).add(t)

    WHITE, GRAY, BLACK = 0, 1, 2
    for ci, members in cyclic.items():
        color = {n: WHITE for n in members}
        # Entradas: miembros con un predecesor FUERA del componente. Si ninguno
        # (ciclo aislado), todos son candidatos. Orden de entrada para determinismo.
        entries = [n for n in ids if n in members
                   and any(comp_of.get(p) != ci for p in incoming.get(n, []))]
        roots = entries or [n for n in ids if n in members]

        def dfs(start):
            wstack = [(start, 0)]
            while wstack:
                v, pi = wstack[-1]
                if pi == 0:
                    color[v] = GRAY
                nbrs = [w for w in out_graph.get(v, []) if w in members]
                if pi < len(nbrs):
                    wstack[-1] = (v, pi + 1)
                    w = nbrs[pi]
                    if color[w] == GRAY:
                        back.add((v, w))             # arista de retorno
                    elif color[w] == WHITE:
                        wstack.append((w, 0))
                else:
                    color[v] = BLACK
                    wstack.pop()

        for r in roots:
            if color[r] == WHITE:
                dfs(r)

    return back
