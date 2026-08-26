"""Grupo AA — árboles genealógicos y jerarquías con nodos-unión (AA98/AA99/AA100).

«La convención genealógica es línea horizontal entre cónyuges con bajada
única al centro» (criterios de Claude Design, 20-ago-2026, sobre
13-stresstest). Tres criterios:

- AA98: generación = rango; la unión es un T-JOINT en el carril de la
  pareja (cónyuge—unión—cónyuge, cero codos), no un nodo descolgado.
- AA99: el fan-out unión→hijos es un PEINE — una troncal horizontal y
  una bajada vertical por hijo (trazo compartido, no N curvas).
- AA100: label a ≤14px de su icono, lado uniforme por fila (debajo);
  si los labels chocan, se ensancha el paso de columna — nunca alternar.

Detección CONSERVADORA (cero riesgo para el resto del corpus): aplica
sólo si el archivo no declara coords/áreas/contains, hay ≥1 nodo-unión
(2 entradas + ≥1 salida + type union/marriage o sin label) y TODAS las
conexiones tocan una unión — un árbol familiar puro. Cualquier otra
forma cae al pipeline AUTO normal.
"""

import logging
from AlmaGag.config import ICON_WIDTH, ICON_HEIGHT

logger = logging.getLogger('AlmaGag')

ROW_H = 210.0          # paso vertical entre generaciones (aire del peine
                       # + aspecto ≤3 con el slot de unión ensanchando filas)
COL_GAP = 24.0         # aire entre columnas además del label
UNION_SLOT = ICON_WIDTH + 16.0   # hueco propio de la unión entre cónyuges:
# su icono no se monta sobre la pareja y la bajada del peine pasa lejos
# de los labels anchos (José Heráclides medía 12px de holgura al drop)
LABEL_CHAR_W = 6.6     # ancho aprox. por carácter (12px) — espejo de hier
LABEL_GAP = 14.0       # AA100: el label vive a ≤14px de su icono
MARGIN = 60.0
TRUNK_FRAC = 0.62      # altura del peine dentro del corredor entre filas
UNION_TYPES = {'union', 'marriage'}


def detect_family(layout):
    """Devuelve {'unions': {uid: {'parents': [...], 'children': [...]}}}
    o None si el grafo no es un árbol familiar puro."""
    elements = layout.elements
    conns = layout.connections
    if not conns:
        return None
    if any('x' in e or 'y' in e for e in elements):
        return None
    if any('contains' in e for e in elements):
        return None
    by_id = {e['id']: e for e in elements}
    inc, out = {}, {}
    for c in conns:
        f, t = c.get('from'), c.get('to')
        if f not in by_id or t not in by_id:
            return None
        out.setdefault(f, []).append(t)
        inc.setdefault(t, []).append(f)
    unions = {}
    for e in elements:
        eid = e['id']
        if len(inc.get(eid, [])) == 2 and len(out.get(eid, [])) >= 1 and \
                (e.get('type') in UNION_TYPES or not e.get('label')):
            unions[eid] = {'parents': list(inc[eid]),
                           'children': list(out[eid])}
    if not unions:
        return None
    # árbol familiar PURO: toda conexión toca una unión, los padres e
    # hijos de una unión son personas (no uniones).
    for c in conns:
        if c.get('from') not in unions and c.get('to') not in unions:
            return None
    for u in unions.values():
        if any(p in unions for p in u['parents'] + u['children']):
            return None
    return {'unions': unions, 'inc': inc, 'out': out}


def _col_width(e):
    """AA100: la columna es tan ancha como su label (nunca menos que el
    icono) — espaciar columnas, no alejar el label."""
    lbl = e.get('label') or ''
    w = max((len(ln) for ln in lbl.split('\n')), default=0) * LABEL_CHAR_W
    return max(ICON_WIDTH, w) + COL_GAP


def apply_family_layout(layout):
    """AA98/AA100: coloca el árbol por generaciones con las uniones como
    T-joint en el carril de la pareja. Devuelve nº de uniones o 0."""
    fam = detect_family(layout)
    if not fam:
        return 0
    unions = fam['unions']
    by_id = {e['id']: e for e in layout.elements}

    union_of = {}           # persona -> unión de la que es padre/madre
    for uid, u in unions.items():
        for p in u['parents']:
            union_of[p] = uid

    # raíz: la unión cuyos DOS padres no son hijos de ninguna otra unión
    child_of = {c: uid for uid, u in unions.items() for c in u['children']}
    roots = [uid for uid, u in unions.items()
             if not any(p in child_of for p in u['parents'])]
    if not roots:
        return 0

    pos = {}                # id -> (x, y) esquina sup-izq del icono
    gen_of = {}

    def block_width(person):
        """Ancho del bloque familiar de una persona (pareja + descendencia)."""
        w_self = _col_width(by_id[person])
        uid = union_of.get(person)
        if uid is None:
            return w_self
        u = unions[uid]
        spouse = [p for p in u['parents'] if p != person]
        w_couple = w_self + UNION_SLOT + \
            sum(_col_width(by_id[s]) for s in spouse)
        w_kids = sum(block_width(c) for c in u['children'])
        return max(w_couple, w_kids)

    def place_block(person, x0, gen):
        """Coloca a la persona, su cónyuge, su unión y su descendencia
        dentro de [x0, x0+width). Devuelve el ancho usado."""
        w = block_width(person)
        y = MARGIN + gen * ROW_H
        uid = union_of.get(person)
        if uid is None:
            pos[person] = (x0 + w / 2 - ICON_WIDTH / 2, y)
            gen_of[person] = gen
            return w
        u = unions[uid]
        spouse = [p for p in u['parents'] if p != person]
        # descendencia primero: reparte el ancho entre los hijos
        w_kids = sum(block_width(c) for c in u['children'])
        kx = x0 + (w - w_kids) / 2
        for c in u['children']:
            kx += place_block(c, kx, gen + 1)
        # pareja centrada sobre su descendencia; unión al punto medio,
        # MISMO carril (AA98: cero codos cónyuge—unión)
        w_self = _col_width(by_id[person])
        w_sp = sum(_col_width(by_id[s]) for s in spouse)
        cx0 = x0 + (w - (w_self + UNION_SLOT + w_sp)) / 2
        pos[person] = (cx0 + w_self / 2 - ICON_WIDTH / 2, y)
        gen_of[person] = gen
        sx = cx0 + w_self + UNION_SLOT
        for s in spouse:
            pos[s] = (sx + _col_width(by_id[s]) / 2 - ICON_WIDTH / 2, y)
            gen_of[s] = gen
            sx += _col_width(by_id[s])
        ua, ub = u['parents']
        ux = (pos[ua][0] + pos[ub][0]) / 2
        pos[uid] = (ux, y)               # mismo carril que la pareja
        gen_of[uid] = gen
        return w

    x_cursor = MARGIN
    for r in roots:
        pa = unions[r]['parents'][0]
        x_cursor += place_block(pa, x_cursor, 0)

    # personas fuera del árbol (no debería haber con la detección pura)
    if len(pos) != len(layout.elements):
        return 0

    for e in layout.elements:
        e['x'], e['y'] = pos[e['id']]
        e['label_position'] = 'bottom'   # AA100: lado uniforme por fila
    # la marca viaja EN las conexiones: las copias del layout durante las
    # iteraciones no preservan atributos, y el re-ruteo debe seguir
    # sabiendo qué es T-joint y qué es peine.
    for c in layout.connections:
        if c.get('to') in unions:
            c['_family_joint'] = 'T'
        elif c.get('from') in unions:
            c['_family_joint'] = 'comb'
    logger.info(f"[AA] árbol familiar: {len(unions)} unión(es) como "
                f"T-joint, {1 + max(gen_of.values())} generación(es)")
    return len(unions)


def force_family_labels(layout):
    """AA100: en un árbol familiar el label es ESTRUCTURAL — centrado
    bajo su icono (≤14px de aire), lado uniforme en toda fila. La
    alternancia arriba/abajo era el parche del optimizador; el espacio
    ya lo reservó la columna (misma convención que las zonas §N46)."""
    if not any('_family_joint' in c for c in layout.connections):
        return
    for e in layout.elements:
        if 'x' in e and e.get('label'):
            cx = e['x'] + e.get('width', ICON_WIDTH) / 2.0
            ly = e['y'] + e.get('height', ICON_HEIGHT) + 20
            layout.label_positions[e['id']] = (cx, ly, 'middle', 'bottom')


def route_family_joints(layout):
    """AA98/AA99: paths del árbol familiar sobre la geometría vigente —
    cónyuge—unión en horizontal pura (T-joint) y unión→hijos como PEINE
    (troncal compartida + bajada por hijo). Se re-aplica en cada
    re-ruteo, pisando el path individual (patrón route_zone_trunks)."""
    by_id = {e['id']: e for e in layout.elements}
    for c in layout.connections:
        f, t = c.get('from'), c.get('to')
        joint = c.get('_family_joint')
        if joint == 'T' and f in by_id and t in by_id:   # cónyuge → unión
            s, u = by_id[f], by_id[t]
            cy = s['y'] + ICON_HEIGHT / 2
            if s['x'] + ICON_WIDTH / 2 <= u['x'] + ICON_WIDTH / 2:
                a = (s['x'] + ICON_WIDTH, cy)
                b = (u['x'], u['y'] + ICON_HEIGHT / 2)
            else:
                a = (s['x'], cy)
                b = (u['x'] + ICON_WIDTH, u['y'] + ICON_HEIGHT / 2)
            c['computed_path'] = {'type': 'polyline', 'points': [a, b]}
        elif joint == 'comb' and f in by_id and t in by_id:   # peine
            u, d = by_id[f], by_id[t]
            ux = u['x'] + ICON_WIDTH / 2
            trunk_y = u['y'] + ICON_HEIGHT + \
                (ROW_H - ICON_HEIGHT) * TRUNK_FRAC
            cx = d['x'] + ICON_WIDTH / 2
            pts = [(ux, u['y'] + ICON_HEIGHT), (ux, trunk_y),
                   (cx, trunk_y), (cx, d['y'])]
            c['computed_path'] = {'type': 'polyline', 'points': pts}
