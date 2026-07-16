"""
SCC para el nivelado §A de hier (rescate ② desde LAF) —
`AlmaGag.layout.strategies.hier.scc`.

Cubre las dos propiedades que motivan el rescate:
1. **Canonicidad**: el conjunto de SCC no depende del orden de entrada de nodos
   ni aristas (lo que el DFS de coloreo global no garantizaba).
2. **Validez del feedback set**: quitar los back-edges siempre deja un DAG,
   incluso con ciclos entrelazados (SCC de 3+).
"""

from AlmaGag.layout.strategies.hier.scc import (
    strongly_connected_components, feedback_back_edges)


def _graph(ids, edges):
    out = {i: [] for i in ids}
    inc = {i: [] for i in ids}
    for f, t in edges:
        out[f].append(t)
        inc[t].append(f)
    return out, inc


def _is_dag(ids, out, back):
    """Kahn: True si el grafo sin `back` es acíclico."""
    g = {i: [t for t in out[i] if (i, t) not in back] for i in ids}
    indeg = {i: 0 for i in ids}
    for i in ids:
        for t in g[i]:
            indeg[t] += 1
    q = [i for i in ids if indeg[i] == 0]
    seen = 0
    while q:
        n = q.pop()
        seen += 1
        for t in g[n]:
            indeg[t] -= 1
            if indeg[t] == 0:
                q.append(t)
    return seen == len(ids)


def _sccset(sccs):
    """Conjunto canónico de componentes (frozensets) para comparar."""
    return {frozenset(c) for c in sccs}


# ---- estructura ----

def test_dag_has_no_multinode_scc():
    ids = ['A', 'B', 'C']
    out, inc = _graph(ids, [('A', 'B'), ('B', 'C'), ('A', 'C')])
    sccs = strongly_connected_components(ids, out)
    assert all(len(c) == 1 for c in sccs)
    assert feedback_back_edges(ids, out, inc, sccs) == set()


def test_simple_cycle_one_scc_one_backedge():
    ids = ['A', 'B', 'C']
    out, inc = _graph(ids, [('A', 'B'), ('B', 'C'), ('C', 'A')])
    sccs = strongly_connected_components(ids, out)
    assert _sccset(sccs) == {frozenset({'A', 'B', 'C'})}
    back = feedback_back_edges(ids, out, inc, sccs)
    assert len(back) == 1
    assert _is_dag(ids, out, back)


def test_two_separate_cycles_two_sccs():
    ids = ['A', 'B', 'C', 'D']
    out, inc = _graph(ids, [('A', 'B'), ('B', 'A'), ('C', 'D'), ('D', 'C')])
    sccs = strongly_connected_components(ids, out)
    assert _sccset(sccs) == {frozenset({'A', 'B'}), frozenset({'C', 'D'})}


def test_interlocking_cycles_single_scc_feedback_is_dag():
    # A->B->C->A  y  B->C->D->B  → un SCC {A,B,C,D}.
    ids = ['A', 'B', 'C', 'D']
    out, inc = _graph(ids, [('A', 'B'), ('B', 'C'), ('C', 'A'),
                            ('C', 'D'), ('D', 'B')])
    sccs = strongly_connected_components(ids, out)
    assert _sccset(sccs) == {frozenset({'A', 'B', 'C', 'D'})}
    back = feedback_back_edges(ids, out, inc, sccs)
    assert _is_dag(ids, out, back), "quitar back-edges debe dejar un DAG"


def test_self_loop_is_its_own_backedge():
    ids = ['A', 'B']
    out, inc = _graph(ids, [('A', 'A'), ('A', 'B')])
    sccs = strongly_connected_components(ids, out)
    back = feedback_back_edges(ids, out, inc, sccs)
    assert ('A', 'A') in back


# ---- canonicidad (independiente del orden) ----

def test_scc_set_is_order_independent():
    base_ids = ['A', 'B', 'C', 'D', 'E']
    base_edges = [('A', 'B'), ('B', 'C'), ('C', 'A'),   # ciclo ABC
                  ('C', 'D'), ('D', 'E')]               # cola D,E
    out, _ = _graph(base_ids, base_edges)
    canonical = _sccset(strongly_connected_components(base_ids, out))

    # Reordenar nodos y aristas no cambia el conjunto de SCC.
    for ids2, edges2 in [
        (['E', 'D', 'C', 'B', 'A'], list(reversed(base_edges))),
        (['C', 'A', 'E', 'B', 'D'], [('C', 'A'), ('A', 'B'), ('D', 'E'),
                                     ('B', 'C'), ('C', 'D')]),
    ]:
        out2, _ = _graph(ids2, edges2)
        assert _sccset(strongly_connected_components(ids2, out2)) == canonical


def test_feedback_makes_dag_regardless_of_order():
    ids = ['A', 'B', 'C', 'D']
    edges = [('A', 'B'), ('B', 'C'), ('C', 'A'), ('C', 'D'), ('D', 'B')]
    for perm in ([ids, edges],
                 [list(reversed(ids)), list(reversed(edges))]):
        out, inc = _graph(perm[0], perm[1])
        sccs = strongly_connected_components(perm[0], out)
        back = feedback_back_edges(perm[0], out, inc, sccs)
        assert _is_dag(perm[0], out, back)
