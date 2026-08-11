"""WISH-LAYOUT-019 (W88) — el journey es primitivo de COLOCACIÓN.

Cada journey cuyos miembros EXCLUSIVOS viven en rangos distintos deriva
un contrato de columna implícito (mismo mecanismo que el honor V79, con
empuje de vecinos EN CADENA), procesado después de los aligns declarados
— el autor gana. Los nodos compartidos (el consolidado) quedan libres:
son la confluencia. La banda casi recta sale como consecuencia.
"""

import json

from AlmaGag.generator import select_strategy
from AlmaGag.layout import Layout
from AlmaGag.layout.considerations import extract_considerations
from AlmaGag.layout.engine import LayoutEngine


def _optimize(d):
    L = Layout(elements=d['elements'], connections=d['connections'],
               canvas=d.get('canvas', {'width': 1400, 'height': 900}))
    L._strategy = select_strategy(d, None)
    L._considerations = extract_considerations(d)
    L._journeys = d.get('journeys')
    return LayoutEngine(verbose=False, strategy=None).optimize(L)


def _cx(e):
    return e['x'] + e.get('width', 80) / 2.0


def test_exclusive_members_share_column():
    """Dos cadenas de largos 3 y 2 convergen en un sink: los exclusivos
    de cada journey quedan en SU columna; el sink compartido, libre."""
    d = {'elements': [
            {'id': 'sink', 'type': 'server', 'label': 'Consolidado'},
            {'id': 'a2', 'type': 'server', 'label': 'A dos\nresumen'},
            {'id': 'a1', 'type': 'server', 'label': 'A uno\ndetalle'},
            {'id': 'a0', 'type': 'server', 'label': 'A cero\nfuente'},
            {'id': 'b1', 'type': 'server', 'label': 'B uno\nresumen'},
            {'id': 'b0', 'type': 'server', 'label': 'B cero\nfuente'},
            {'id': 'x0', 'type': 'server', 'label': 'Suelto'}],
         'connections': [
            {'from': 'a0', 'to': 'a1'}, {'from': 'a1', 'to': 'a2'},
            {'from': 'a2', 'to': 'sink'},
            {'from': 'b0', 'to': 'b1'}, {'from': 'b1', 'to': 'sink'},
            {'from': 'x0', 'to': 'sink'}],
         'canvas': {'width': 1200, 'height': 900, 'flow': 'up'},
         'journeys': [
            {'id': 'ja', 'label': 'Cadena A', 'path': ['a0', 'a1', 'a2', 'sink']},
            {'id': 'jb', 'label': 'Cadena B', 'path': ['b0', 'b1', 'sink']}]}
    out = _optimize(d)
    by = out.elements_by_id
    ja = [_cx(by[i]) for i in ['a0', 'a1', 'a2']]
    jb = [_cx(by[i]) for i in ['b0', 'b1']]
    assert max(ja) - min(ja) <= 1.0, f'cadena A dispersa: {ja}'
    assert max(jb) - min(jb) <= 1.0, f'cadena B dispersa: {jb}'
    assert abs(ja[0] - jb[0]) > 40, 'las dos cadenas no deberían compartir columna'


def test_declared_align_wins_over_derived():
    """Un align x DECLARADO que fija a un miembro fuera de la columna del
    journey gana: el derivado no lo mueve ni lo empuja."""
    d = {'elements': [
            {'id': 'sink', 'type': 'server', 'label': 'S'},
            {'id': 'a1', 'type': 'server', 'label': 'A1'},
            {'id': 'a0', 'type': 'server', 'label': 'A0'},
            {'id': 'anchor', 'type': 'server', 'label': 'Ancla'},
            {'id': 'pre', 'type': 'server', 'label': 'Pre'}],
         'connections': [
            {'from': 'a0', 'to': 'a1'}, {'from': 'a1', 'to': 'sink'},
            {'from': 'pre', 'to': 'anchor'}, {'from': 'anchor', 'to': 'sink'}],
         'canvas': {'width': 1000, 'height': 800, 'flow': 'up'},
         'considerations': [
            {'align': ['a0', 'anchor'], 'axis': 'x'}],
         'journeys': [
            {'id': 'ja', 'label': 'A', 'path': ['a0', 'a1', 'sink']}]}
    out = _optimize(d)
    by = out.elements_by_id
    # el contrato declarado (a0 con anchor) se cumple
    assert abs(_cx(by['a0']) - _cx(by['anchor'])) <= 1.0, \
        'el align declarado debe seguir cumplido con journeys presentes'


def test_presupuesto_chains_are_columns():
    """El fixture del repo: los exclusivos de cada cadena quedan en una
    columna (dispersión ≤ media ranura)."""
    d = json.load(open('docs/diagrams/gags/mina-presupuesto.sdjf'))
    canvas = dict(d.get('canvas') or {})
    canvas.setdefault('width', 1400)
    canvas.setdefault('height', 900)
    d['canvas'] = canvas
    out = _optimize(d)
    by = out.elements_by_id
    counts = {}
    for j in d['journeys']:
        for i in j['path']:
            counts[i] = counts.get(i, 0) + 1
    for j in d['journeys']:
        excl = [i for i in j['path'] if counts[i] == 1 and i in by]
        if len(excl) < 2:
            continue
        cxs = [_cx(by[i]) for i in excl]
        assert max(cxs) - min(cxs) <= 40.0, \
            f"cadena {j['id']} dispersa: { {i: round(c) for i, c in zip(excl, cxs)} }"
