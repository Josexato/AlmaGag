"""BUGS-LAYOUT-011 — el header reserva el espacio REAL del icono decorativo.

El icono del contenedor se dibuja en [y+padding, y+padding+50]
(draw_container): los miembros deben arrancar debajo de su borde inferior
con aire (≥ padding), aunque el contenedor no tenga label. Antes el primer
miembro quedaba soldado al icono (gap = 0) y sin label caía encima.
"""

from AlmaGag.config import CONTAINER_ICON_HEIGHT, CONTAINER_PADDING
from AlmaGag.layout import Layout
from AlmaGag.layout.engine import LayoutEngine


def _optimize(d):
    L = Layout(elements=d['elements'], connections=d['connections'],
               canvas={'width': 1200, 'height': 800})
    L._strategy = 'auto'
    return LayoutEngine(verbose=False, strategy='auto').optimize(L)


def _box_and_members(out, box_id, member_ids):
    box = out.elements_by_id[box_id]
    return box, [out.elements_by_id[m] for m in member_ids]


def _base(label):
    els = [{'id': 'box', 'type': 'building', 'contains': ['a', 'b', 'c']},
           {'id': 'a', 'type': 'server', 'label': 'Alfa'},
           {'id': 'b', 'type': 'server', 'label': 'Beta'},
           {'id': 'c', 'type': 'server', 'label': 'Gama'}]
    if label:
        els[0]['label'] = label
    return {'elements': els,
            'connections': [{'from': 'a', 'to': 'b'}, {'from': 'b', 'to': 'c'}]}


def test_members_clear_decorative_icon_with_label():
    """Contenedor con icono y label: todo miembro arranca con ≥ padding de
    aire bajo el borde REAL del icono ([y+padding, y+padding+50])."""
    out = _optimize(_base('Caja con icono'))
    box, members = _box_and_members(out, 'box', ['a', 'b', 'c'])
    icon_bottom = box['y'] + CONTAINER_PADDING + CONTAINER_ICON_HEIGHT
    for m in members:
        assert m['y'] >= icon_bottom + CONTAINER_PADDING - 0.5, \
            f"{m['id']} a {m['y'] - icon_bottom:.0f}px del icono decorativo"


def test_members_clear_decorative_icon_without_label():
    """Sin label el icono se dibuja igual: la reserva no puede ser cero
    (antes los miembros caían ENCIMA del icono)."""
    out = _optimize(_base(None))
    box, members = _box_and_members(out, 'box', ['a', 'b', 'c'])
    icon_bottom = box['y'] + CONTAINER_PADDING + CONTAINER_ICON_HEIGHT
    for m in members:
        assert m['y'] >= icon_bottom + CONTAINER_PADDING - 0.5, \
            f"{m['id']} pisa el icono decorativo del contenedor"


def test_area_header_math_unchanged():
    """Un área (T73: sin icono decorativo) conserva su cuenta: el primer
    miembro arranca en y + max(50, label) + padding — sin los 10 extra."""
    d = _base('Zona')
    d['elements'][0]['type'] = 'area'
    out = _optimize(d)
    box, members = _box_and_members(out, 'box', ['a', 'b', 'c'])
    expected = box['y'] + CONTAINER_ICON_HEIGHT + CONTAINER_PADDING
    assert min(m['y'] for m in members) == expected
