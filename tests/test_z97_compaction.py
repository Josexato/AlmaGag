"""Z97 re-solver (WISH-LAYOUT-030) — compactación por intervalos de la
grilla: la celda floja devuelve el aire.

Antes: UNA escala global px/unidad — la celda más densa la fijaba y a
las demás les sobraba aire (tinta 5%). Ahora la estructura de CORTES se
conserva (adyacencias intactas) pero cada intervalo mide lo que las
celdas que lo cruzan piden. Los ratios declarados son MÁXIMOS de
proporción, no mínimos de tamaño (doctrina Z97 del doc de criterios).
Bench de referencia (grilla 3×2, densidades dispares): tinta 8.5%→12.1%.
"""

from AlmaGag.layout import Layout
from AlmaGag.layout.strategies.hier.areas import AREA_GAP, layout_by_areas


def _mk(n0, n1, size0=(1, 1), size1=(1, 1), label0='Chica', label1='Densa'):
    els, conns = [], []
    a_ids, b_ids = [], []
    for i in range(n0):
        els.append({'id': f'a{i}', 'label': f'Nodo A{i}'})
        a_ids.append(f'a{i}')
    for i in range(n1):
        els.append({'id': f'b{i}', 'label': f'Nodo B{i}'})
        b_ids.append(f'b{i}')
    spec = [{'id': 'z0', 'label': label0, 'members': a_ids},
            {'id': 'z1', 'label': label1, 'members': b_ids}]
    part = {'scheme': 'bsp', 'splits': [
        {'area': 'z0', 'size': list(size0), 'anchor': 'base'},
        {'area': 'z1', 'size': list(size1), 'at': 'right_of', 'of': 'z0'}]}
    L = Layout(elements=els, connections=conns,
               canvas={'width': 1400, 'height': 900, 'partition': part})
    return L, spec


def test_la_celda_floja_devuelve_el_aire():
    """Celdas gemelas [1,1] con contenidos 1 vs 6: antes la escala global
    las hacía IGUALES (la densa fijaba px/unidad); ahora cada intervalo x
    mide lo suyo — la floja se recorta y la adyacencia se conserva."""
    L, spec = _mk(1, 6)
    boxes = {b['id']: b for b in layout_by_areas(L, spec)}
    z0, z1 = boxes['z0'], boxes['z1']
    assert z0['w'] < 0.6 * z1['w'], \
        f"z0 sigue inflada a escala global ({z0['w']:.0f} vs {z1['w']:.0f})"
    assert abs(z1['x'] - (z0['x'] + z0['w'] + AREA_GAP)) < 1, \
        'la compactación rompió la adyacencia z0—z1'
    # banda vertical compartida: mismo intervalo y → misma altura
    assert abs(z0['h'] - z1['h']) < 1 and abs(z0['y'] - z1['y']) < 1


def test_contenidos_iguales_siguen_simetricos():
    L, spec = _mk(3, 3)
    boxes = {b['id']: b for b in layout_by_areas(L, spec)}
    assert abs(boxes['z0']['w'] - boxes['z1']['w']) < 1


def test_piso_del_rotulo_del_area():
    """Una celda compactada al contenido no puede cortar su propio
    título: el ancho mínimo es el del rótulo del área."""
    L, spec = _mk(1, 6, label0='Nombre de bloque bastante largo')
    boxes = {b['id']: b for b in layout_by_areas(L, spec)}
    assert boxes['z0']['w'] >= 7.5 * len('Nombre de bloque bastante largo'), \
        'el rótulo del área no cabe en su celda compactada'
