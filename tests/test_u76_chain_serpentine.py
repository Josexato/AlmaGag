"""U76/J33 — un grafo-cadena se pliega en serpentina, no en tira 1×N."""

from AlmaGag.layout import Layout
from AlmaGag.layout.engine import LayoutEngine


def _chain(n):
    els = [{'id': f'p{i}', 'type': 'server', 'label': f'Paso {i}'}
           for i in range(1, n + 1)]
    conns = [{'from': f'p{i}', 'to': f'p{i+1}', 'direction': 'forward'}
             for i in range(1, n)]
    return els, conns


def _optimize(els, conns):
    L = Layout(elements=els, connections=conns,
               canvas={'width': 1000, 'height': 700})
    L._strategy = 'auto'
    return LayoutEngine(verbose=False, strategy='auto').optimize(L)


def test_chain_folds_into_rows_with_adjacent_links():
    """Cadena de 8: filas de ceil(sqrt(16))=4 columnas (2 filas), y cada
    eslabón queda ADYACENTE al siguiente (misma fila o mismo doblez)."""
    out = _optimize(*_chain(8))
    ys = sorted({round(out.elements_by_id[f'p{i}']['y']) for i in range(1, 9)})
    assert len(ys) == 2, f'esperaba 2 filas, hay {len(ys)}: {ys}'
    rows = {eid: round(e['y']) for eid, e in out.elements_by_id.items()}
    xs = {eid: e['x'] for eid, e in out.elements_by_id.items()}
    order = sorted(xs, key=lambda k: xs[k])
    for i in range(1, 8):
        a, b = f'p{i}', f'p{i+1}'
        if rows[a] == rows[b]:
            # misma fila: vecinos inmediatos en x
            ia, ib = order.index(a), order.index(b)
            same_row = [k for k in order if rows[k] == rows[a]]
            ja, jb = same_row.index(a), same_row.index(b)
            assert abs(ja - jb) == 1, f'{a}-{b} no adyacentes en su fila'
        else:
            # doblez: misma columna (empalme vertical)
            assert abs(xs[a] - xs[b]) < 1.0, \
                f'doblez {a}-{b} desalineado: {xs[a]} vs {xs[b]}'


def test_chain_aspect_is_not_a_strip():
    """El bbox de la cadena plegada no es tira 1×N: ancho/alto ≥ 1."""
    out = _optimize(*_chain(8))
    els = list(out.elements_by_id.values())
    w = max(e['x'] + e.get('width', 80) for e in els) - min(e['x'] for e in els)
    h = max(e['y'] + e.get('height', 50) for e in els) - min(e['y'] for e in els)
    assert w / h >= 1.0, f'sigue siendo tira: {w:.0f}x{h:.0f}'


def test_short_chain_and_branching_graph_do_not_fold():
    """Cadena corta (<5) apila normal; un grafo con bifurcación tampoco
    se pliega (el barycenter sigue a cargo)."""
    out = _optimize(*_chain(4))
    ys = {round(out.elements_by_id[f'p{i}']['y']) for i in range(1, 5)}
    assert len(ys) == 4                      # un nivel por eslabón

    els, conns = _chain(5)
    els.append({'id': 'rama', 'type': 'server', 'label': 'Rama'})
    conns.append({'from': 'p2', 'to': 'rama', 'direction': 'forward'})
    out = _optimize(els, conns)
    # p3 y rama comparten nivel (hijos de p2): no hubo pliegue
    assert round(out.elements_by_id['p3']['y']) == \
        round(out.elements_by_id['rama']['y'])
