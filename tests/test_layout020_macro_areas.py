"""WISH-LAYOUT-020 (X91) — el ÁREA es unidad de layout.

Macro-colocación BIDIMENSIONAL de las cajas de área: si la fila única
respeta el aspecto §O52 se queda (estabilidad); si lo viola, envoltura
tipo estantería hacia ASPECT_TARGET — jamás una cinta 1×N (tabernero:
9 áreas en 11129×893, aspecto 14.36). `area.role` declara la banda
(control/feeder arriba, chain centro, external abajo, overlay al fondo)
y gana a la derivación. El ruteo inter-área elige el lado por eje
dominante (ya no asume izquierda→derecha).
"""

from AlmaGag.config import ICON_HEIGHT, ICON_WIDTH
from AlmaGag.layout import Layout
from AlmaGag.layout.metrics import ASPECT_RANGE
from AlmaGag.layout.strategies.hier.areas import layout_by_areas


def _mk(n_areas, per_area, conns_chain=True):
    """n_areas áreas de per_area nodos en cadena + enlaces inter-área."""
    els, conns, spec = [], [], []
    for a in range(n_areas):
        ids = []
        for i in range(per_area):
            eid = f'a{a}n{i}'
            els.append({'id': eid, 'type': 'server', 'label': f'Nodo {a}.{i}'})
            ids.append(eid)
        if conns_chain:
            for u, v in zip(ids, ids[1:]):
                conns.append({'from': u, 'to': v})
        spec.append({'id': f'z{a}', 'label': f'Área {a}', 'members': ids})
    for a in range(n_areas - 1):
        conns.append({'from': f'a{a}n{per_area-1}', 'to': f'a{a+1}n0'})
    L = Layout(elements=els, connections=conns,
               canvas={'width': 1400, 'height': 900})
    return L, spec


def _aspect(boxes):
    x2 = max(b['x'] + b['w'] for b in boxes)
    y2 = max(b['y'] + b['h'] for b in boxes)
    return x2 / y2


def test_many_areas_wrap_to_healthy_aspect():
    """9 áreas nunca quedan en cinta 1×N: hay ≥2 filas y el aspecto de la
    grilla de cajas cae en el rango §O52."""
    L, spec = _mk(9, 5)
    boxes = layout_by_areas(L, spec)
    ys = {round(b['y']) for b in boxes}
    assert len(ys) >= 2, f'las 9 áreas siguen en una fila: ys={ys}'
    assert ASPECT_RANGE[0] <= _aspect(boxes) <= ASPECT_RANGE[1], \
        f'aspecto {_aspect(boxes):.2f} fuera de rango'


def test_healthy_single_row_is_stable():
    """Pocas áreas chicas cuya fila única ya respeta el aspecto NO se
    envuelven (cero regresión en fixtures sanos)."""
    L, spec = _mk(2, 2)
    boxes = layout_by_areas(L, spec)
    assert len({round(b['y']) for b in boxes}) == 1


def test_declared_role_wins_over_derivation():
    """`area.role`: control arriba, chain al centro, external abajo,
    overlay al fondo — el orden vertical es el semántico."""
    L, spec = _mk(4, 2)
    spec[0]['role'] = 'external'
    spec[1]['role'] = 'chain'
    spec[2]['role'] = 'control'
    spec[3]['role'] = 'overlay'
    boxes = {b['id']: b for b in layout_by_areas(L, spec)}
    assert boxes['z2']['y'] < boxes['z1']['y'] < boxes['z0']['y'] \
        < boxes['z3']['y'], {k: v['y'] for k, v in boxes.items()}


def test_inter_area_route_uses_dominant_axis():
    """Con cajas apiladas (roles), el enlace inter-área sale por ABAJO y
    entra por ARRIBA — ya no el R→L de la fila única."""
    L, spec = _mk(2, 2)
    spec[0]['role'] = 'control'
    spec[1]['role'] = 'external'
    layout_by_areas(L, spec)
    by = {e['id']: e for e in L.elements}
    inter = [c for c in L.connections if c.get('_inter_area')]
    assert inter, 'debe haber enlace inter-área ruteado'
    c = inter[0]
    a, b = c['_from_port'], c['_to_port']
    s, d = by[c['from']], by[c['to']]
    assert abs(a[1] - (s['y'] + ICON_HEIGHT)) < 0.5, 'sale por el borde inferior'
    assert abs(b[1] - d['y']) < 0.5, 'entra por el borde superior'
    # y el camino es ortogonal
    pts = c['computed_path']['points']
    for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
        assert abs(x1 - x2) < 0.5 or abs(y1 - y2) < 0.5, 'tramo diagonal'


def test_row_content_alignment_preserved():
    """Dentro de cada fila el contenido queda DENTRO de su caja (el shift
    respeta AREA_HEAD + AREA_PAD)."""
    L, spec = _mk(6, 4)
    boxes = {b['id']: b for b in layout_by_areas(L, spec)}
    area_of = {}
    for a in spec:
        for m in a['members']:
            area_of[m] = a['id']
    for e in L.elements:
        b = boxes[area_of[e['id']]]
        assert b['x'] <= e['x'] and e['x'] + ICON_WIDTH <= b['x'] + b['w'], \
            f"{e['id']} fuera de su caja en x"
        assert b['y'] <= e['y'] and e['y'] + ICON_HEIGHT <= b['y'] + b['h'], \
            f"{e['id']} fuera de su caja en y"
