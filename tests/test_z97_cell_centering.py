"""Z97 (WISH-LAYOUT-030) — el contenido va centrado en su celda + audit
de subutilización.

La escala px/unidad de la partición la fija la celda más densa (§P59:
toda celda aloja su contenido); a las demás les sobra aire. Z97 v1:
ese aire se reparte SIMÉTRICO (contenido centrado, no pegado
arriba-izquierda) y la celda que usa <35% de su área queda NOMBRADA en
el audit con la proporción que su contenido pide — el autor ajusta
size[] con dato. El re-solver que devuelve el aire re-escalando celdas
hermanas sigue pendiente en el ticket.
"""

import logging

from AlmaGag.config import ICON_WIDTH
from AlmaGag.layout import Layout
from AlmaGag.layout.strategies.hier.areas import layout_by_areas


def _mk(size0, size1):
    """z0: 2 nodos sueltos (fila); z1: columna de 8 (fija la escala
    vertical; celdas altas para que el gate Z94 no serpentee)."""
    els, conns = [], []
    for i in range(2):
        els.append({'id': f'a{i}', 'label': f'Solo {i}'})
    ids = []
    for i in range(8):
        eid = f'b{i}'
        els.append({'id': eid, 'label': f'Paso {i}'})
        ids.append(eid)
    conns += [{'from': u, 'to': v} for u, v in zip(ids, ids[1:])]
    spec = [{'id': 'z0', 'label': 'Chica', 'members': ['a0', 'a1']},
            {'id': 'z1', 'label': 'Densa', 'members': ids}]
    part = {'scheme': 'bsp', 'splits': [
        {'area': 'z0', 'size': size0, 'anchor': 'base'},
        {'area': 'z1', 'size': size1, 'at': 'right_of', 'of': 'z0'}]}
    L = Layout(elements=els, connections=conns,
               canvas={'width': 1400, 'height': 900, 'partition': part})
    return L, spec


def test_contenido_centrado_en_celda_sobrada(caplog):
    # celdas gemelas [1,4]: z1 (columna de 8) fija la escala vertical y
    # z0 (fila de 2) la horizontal — a z0 le sobra CIELO
    with caplog.at_level(logging.WARNING, logger='AlmaGag'):
        L, spec = _mk([1, 4], [1, 4])
        boxes = {b['id']: b for b in layout_by_areas(L, spec)}
    z0 = boxes['z0']
    icons = [e for e in L.elements if e['id'].startswith('a')]
    # el aire sobrante de z0 es VERTICAL (z1, columna de 6, fija la
    # escala vertical): antes el contenido quedaba pegado al header
    from AlmaGag.config import ICON_HEIGHT
    from AlmaGag.layout.strategies.hier.areas import AREA_HEAD
    top = min(e['y'] for e in icons) - z0['y']
    bottom = z0['y'] + z0['h'] - max(e['y'] + ICON_HEIGHT for e in icons)
    assert top > 100, 'el contenido sigue pegado al header'
    assert abs(top - bottom) <= AREA_HEAD + 0.25 * max(top, bottom), \
        f'aire asimétrico: {top:.0f}px arriba vs {bottom:.0f}px abajo'
    assert "Z97: celda 'z0'" in caplog.text, \
        'la celda subutilizada no quedó nombrada'
    assert 'pide proporción' in caplog.text


def test_celdas_que_calzan_con_su_contenido_no_avisan(caplog):
    """Ratios declarados acordes al contenido (fila [4,1], columna
    [1,4]): ninguna celda queda subutilizada y el audit calla."""
    with caplog.at_level(logging.WARNING, logger='AlmaGag'):
        L, spec = _mk([4, 1], [1, 4])
        layout_by_areas(L, spec)
    assert 'Z97' not in caplog.text
