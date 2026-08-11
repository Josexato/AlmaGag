"""WISH-LAYOUT-010 — presupuesto de espacio por contenedor.

El TÍTULO de un contenedor es zona dura para las etiquetas de sus propios
miembros: ninguna etiqueta optimizada puede montarse sobre el texto del
rótulo (icono + caracteres reales, espejo de _render_container_labels).
Guarda de composición: en el caso real (físico v2) los pares «etiqueta
sobre icono» no vuelven a subir.
"""

import json

from AlmaGag.config import ICON_WIDTH
from AlmaGag.generator import select_strategy
from AlmaGag.layout import Layout
from AlmaGag.layout.engine import LayoutEngine
from AlmaGag.layout.geometry import GeometryCalculator
from AlmaGag.utils import extract_item_id

FISICO = 'docs/diagrams/gags/mina-fisico-v2.gag'
HLD = 'docs/diagrams/gags/mina-hld.gag'


def _optimize_file(path):
    d = json.load(open(path))
    L = Layout(elements=d['elements'], connections=d['connections'],
               canvas={'width': 1400, 'height': 900})
    L._strategy = select_strategy(d, None)
    return LayoutEngine(verbose=False, strategy=None).optimize(L)


def _header_text_zone(c):
    """Espejo del rótulo dibujado: icono + texto real, anclado a la izq."""
    lines = c['label'].split('\n')
    local_x = 10.0 if c.get('type') == 'area' else 10.0 + ICON_WIDTH + 10.0
    text_w = max(len(ln) for ln in lines) * 8.0
    return (c['x'], c['y'],
            min(c['x'] + local_x + text_w, c['x'] + c.get('width', 0)),
            c['y'] + len(lines) * 18 + 10)


def _intersect(a, b):
    return not (a[2] < b[0] or b[2] < a[0] or a[3] < b[1] or b[3] < a[1])


def _member_label_boxes(out, geometry):
    """(id_contenedor, id_miembro, bbox de la etiqueta almacenada)."""
    for c in out.elements:
        if 'contains' not in c or not c.get('label') or 'x' not in c:
            continue
        for ref in c['contains']:
            mid = extract_item_id(ref)
            m = out.elements_by_id.get(mid)
            pos = out.label_positions.get(mid)
            if not m or not m.get('label') or not pos:
                continue
            bb = geometry.get_label_bbox_stored(m, pos)
            if bb:
                yield c, mid, bb


def test_member_labels_off_header_text_synthetic():
    """Miembros pegados al techo de la caja: ninguna etiqueta sobre el
    texto del título."""
    d = {'elements': [
            {'id': 'box', 'type': 'area',
             'label': 'ZONA CON TITULO LARGO\nsegunda linea del rotulo',
             'contains': ['a', 'b', 'c']},
            {'id': 'a', 'type': 'server', 'label': 'Servidor A'},
            {'id': 'b', 'type': 'server', 'label': 'Servidor B'},
            {'id': 'c', 'type': 'server', 'label': 'Servidor C'}],
         'connections': [{'from': 'a', 'to': 'b'},
                         {'from': 'b', 'to': 'c'}]}
    L = Layout(elements=d['elements'], connections=d['connections'],
               canvas={'width': 1400, 'height': 900})
    L._strategy = 'auto'
    out = LayoutEngine(verbose=False, strategy='auto').optimize(L)
    geometry = GeometryCalculator()
    for c, mid, bb in _member_label_boxes(out, geometry):
        hz = _header_text_zone(c)
        assert not _intersect(bb, hz), \
            f'etiqueta de {mid} {bb} sobre el título de {c["id"]} {hz}'


def test_member_labels_off_header_text_real_fixtures():
    """Audit en el caso real: físico v2 y HLD, todos los contenedores."""
    geometry = GeometryCalculator()
    for path in (FISICO, HLD):
        out = _optimize_file(path)
        for c, mid, bb in _member_label_boxes(out, geometry):
            hz = _header_text_zone(c)
            assert not _intersect(bb, hz), \
                f'{path}: etiqueta de {mid} sobre el título de {c["id"]}'


def test_fisico_v2_labels_on_icons_do_not_regress():
    """Guarda de composición: pares «algo sobre un ICONO» (violación R1)
    en el físico v2 — 7 en el baseline, 4 tras LAYOUT-010; 5 tras
    BUGS-LAYOUT-012 (techos de zona alineados: el corrimiento de 9px
    movió decisiones del optimizador dentro de z_pila — trade medido y
    verificado en PNG a cambio de primeras filas en la misma fila
    absoluta y troncal inter-zona recta)."""
    out = _optimize_file(FISICO)
    on_icon = [p for p in (out._collision_pairs or [])
               if p[2].startswith('icon_vs_')]
    assert len(on_icon) <= 5, \
        f'{len(on_icon)} pares sobre icono (tope 5): {on_icon}'
