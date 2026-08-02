"""
Consideraciones de layout — align / near / avoid (rescate ④ desde LAF, revisado).

Son **blandas** (de ahí el nombre): expresan intención del usuario, no una ley.
Cada una se aplica **sólo si no destruye la diagramación** — si al aplicarla
aumentan las colisiones, se revierte y se informa en los logs que no se pudo
cumplir (sin explicar el porqué). Así una consideración nunca degrada el diagrama.

Esto las diferencia de una *restricción dura* (que se impone aunque rompa el
resto). El motor (AUTO) las corre detrás de una guarda, igual que la
compactación ① .

Schema (array top-level `considerations`; alias legacy `constraints`):

    "considerations": [
      {"align": ["a", "b", "c"], "axis": "x"},   # misma columna (X común)
      {"align": ["d", "e"], "axis": "y"},         # misma fila (Y común)
      {"near":  ["app", "db"]},                    # acercar (reduce dispersión)
      {"avoid": ["front", "back"]}                 # no solapar (separa el par)
    ]

- `align`: lleva los elementos a una X (axis 'x', default) o Y ('y') común.
- `near`: acerca a los miembros hacia su centroide sin encimarlos.
- `avoid`: si dos elementos se solapan, los separa por el eje de menor penetración.

`extract_considerations` normaliza el schema; `apply_one` aplica UNA consideración
(geometría pura); `apply_considerations` es el driver GUARDADO que decide cuáles
se conservan. Sin `considerations`, todo es no-op (cero regresión).
"""

import logging
from typing import Callable, List, Tuple

from AlmaGag.config import ICON_WIDTH, ICON_HEIGHT

logger = logging.getLogger('AlmaGag')

_KINDS = ('align', 'near', 'avoid')
NEAR_ALPHA = 0.5      # fracción del acercamiento hacia el centroide
AVOID_MARGIN = 16.0   # holgura al separar (px)


def extract_considerations(data: dict) -> List[dict]:
    """Normaliza el array `considerations` (o su alias legacy `constraints`) del
    SDJF. Tolerante: descarta entradas inválidas con un warning. Devuelve
    [{'kind','ids','axis'}]."""
    raw = data.get('considerations')
    if raw is None:
        raw = data.get('constraints')      # alias retrocompatible
    if not raw or not isinstance(raw, list):
        return []
    out: List[dict] = []
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        kind = next((k for k in _KINDS if k in entry), None)
        if kind is None:
            logger.warning(f"[CONSIDERACIONES] entrada sin tipo válido {list(entry)}; "
                           f"esperado uno de {_KINDS}. Ignorada.")
            continue
        ids = entry.get(kind)
        if not isinstance(ids, list) or len(ids) < 2:
            logger.warning(f"[CONSIDERACIONES] '{kind}' requiere ≥2 ids; ignorada.")
            continue
        axis = entry.get('axis', 'x')
        if axis not in ('x', 'y'):
            axis = 'x'
        cons = {'kind': kind, 'ids': list(ids), 'axis': axis}
        # §N46: un `near` puede llevar rótulo opcional para su zona.
        if kind == 'near' and entry.get('label'):
            cons['label'] = str(entry['label'])
        out.append(cons)
    return out


def label(cons: dict) -> str:
    """Etiqueta corta de una consideración para logs: `align [a, b, c]`."""
    return f"{cons['kind']} {cons['ids']}"


def areas_to_near_seeds(data) -> int:
    """§O53 (mediano plazo): representa `areas` en AUTO como zonas near (§N46).

    Cuando una señal de mayor precedencia fuerza AUTO (considerations/
    constraints), las cajas de fase declaradas en `areas` ya no se pierden:
    cada área con 2+ miembros válidos se siembra como consideración `near`
    con su rótulo — el cluster, la caja punteada rotulada (banda §O54) y la
    expulsión de intrusos salen gratis de la maquinaria N46. Los miembros
    contenedores se excluyen (la grilla near asume elementos normales).

    Muta el arreglo activo (`considerations` o su alias `constraints`) sin
    duplicar semillas near existentes. Devuelve cuántas áreas sembró.
    """
    areas = data.get('areas') or []
    if not areas:
        return 0
    normal_ids = {e['id'] for e in data.get('elements', [])
                  if 'contains' not in e}
    if data.get('considerations') is not None:
        target = data['considerations']
    elif data.get('constraints') is not None:
        target = data['constraints']
    else:
        target = data.setdefault('considerations', [])
    if not isinstance(target, list):
        return 0
    seeded = [set(c.get('near') or []) for c in target if isinstance(c, dict)]
    n = 0
    for a in areas:
        if not isinstance(a, dict):
            continue
        members = [m for m in (a.get('members') or []) if m in normal_ids]
        if len(members) < 2 or set(members) in seeded:
            continue
        seed = {'near': members}
        if a.get('label') or a.get('id'):
            seed['label'] = str(a.get('label') or a.get('id'))
        target.append(seed)
        seeded.append(set(members))
        n += 1
    return n


def _center(e) -> Tuple[float, float]:
    return (e['x'] + e.get('width', ICON_WIDTH) / 2.0,
            e['y'] + e.get('height', ICON_HEIGHT) / 2.0)


def apply_one(layout, cons: dict) -> None:
    """Aplica UNA consideración in-place sobre `layout.elements` (geometría pura,
    sin guarda). El caller decide si conserva el resultado."""
    by_id = layout.elements_by_id
    els = [by_id[i] for i in cons['ids'] if i in by_id and 'x' in by_id[i]]
    if len(els) < 2:
        return
    if cons['kind'] == 'align':
        _apply_align(els, cons['axis'])
    elif cons['kind'] == 'near':
        _apply_near(els)
    elif cons['kind'] == 'avoid':
        _apply_avoid(els)


def apply_considerations(
    layout,
    considerations: List[dict],
    evaluate: Callable[[object], int],
    reroute: Callable[[object], None],
) -> Tuple[object, List[dict]]:
    """Driver GUARDADO: aplica cada consideración sólo si no aumenta las
    colisiones. Devuelve (layout_resultante, no_aplicadas).

    Para cada consideración prueba sobre una copia (aplicar → re-rutear →
    evaluar); la conserva si las colisiones no suben respecto a la mejor hasta
    ahora, si no la descarta. `evaluate(layout)` devuelve el nº de colisiones y
    lo cachea; `reroute(layout)` recalcula los paths."""
    current = layout
    base = evaluate(current)
    unmet: List[dict] = []
    for cons in considerations:
        trial = current.copy()
        apply_one(trial, cons)
        trial.invalidate_collision_cache()
        reroute(trial)
        score = evaluate(trial)
        if score <= base:
            current, base = trial, score
        else:
            unmet.append(cons)
    return current, unmet


def cluster_near_groups(layout, considerations: List[dict]) -> int:
    """§N46: promueve cada `near[]` a ZONA — cluster compacto por construcción.

    En vez del empujón blando post-hoc (que en redes reales dejaba miembros a
    ~730px, el hallazgo N46 de condestable), los miembros de cada `near` se
    colocan en una grilla compacta centrada en su centroide ANTES del ruteo:
    el resto del pipeline (contenedores, canvas, colisiones, rutas) trabaja ya
    con la zona armada, así el `near` se cumple por construcción.

    Marca cada miembro con `_near_zone` (índice de grupo) y `_near_zone_label`
    (rótulo opcional) — los dicts de elemento sobreviven a `layout.copy()`,
    a diferencia de los atributos del layout — para que el renderer dibuje la
    caja de zona. Devuelve cuántos grupos clusterizó. Miembros contenidos en
    un contenedor (`contains`) se saltan: su posición la manda el contenedor.
    """
    by_id = layout.elements_by_id
    contained = set()
    for e in layout.elements:
        for ref in e.get('contains', []) or []:
            contained.add(ref['id'] if isinstance(ref, dict) else ref)

    n_groups = 0
    for gi, cons in enumerate(c for c in considerations if c['kind'] == 'near'):
        # §Q65: un near de ÁREAS es afinidad de zonas (consumido por el
        # banding P60), no un cluster de miembros — y un contenedor jamás se
        # clusteriza como icono (movería la caja sin su subárbol).
        if cons.get('_zone_affinity'):
            continue
        els = [by_id[i] for i in cons['ids']
               if i in by_id and 'x' in by_id[i] and i not in contained
               and 'contains' not in by_id[i]]
        if len(els) < 2:
            continue

        # pitch por grupo: sitio para el icono + su etiqueta estimada
        def _est(e):
            lines = str(e.get('label', '')).split('\n')
            w = max((len(ln) for ln in lines), default=0) * 7.0
            h = len(lines) * 17.0
            return max(ICON_WIDTH, w) + 28.0, ICON_HEIGHT + h + 22.0
        dims = [_est(e) for e in els]
        pitch_x = max(d[0] for d in dims)
        pitch_y = max(d[1] for d in dims)

        # centroide actual → la zona se arma donde el placement la dejó
        centers = [_center(e) for e in els]
        gx = sum(c[0] for c in centers) / len(centers)
        gy = sum(c[1] for c in centers) / len(centers)

        # grilla compacta; orden por posición actual (estable entre corridas y
        # entre archivos que comparten ids — ayuda a N47)
        els.sort(key=lambda e: (e['y'], e['x']))
        import math
        cols = max(1, math.ceil(math.sqrt(len(els))))
        rows = math.ceil(len(els) / cols)

        # B4 dentro de la zona: para grupos chicos, elegir la asignación
        # miembro→celda que minimiza cruces y longitud de las aristas INTERNAS
        # (el orden posicional degeneraba en el cruce en X de la zona de mina).
        if 3 <= len(els) <= 6:
            import itertools
            ids_set = {e['id'] for e in els}
            intra = [(c2['from'], c2['to']) for c2 in layout.connections
                     if c2.get('from') in ids_set and c2.get('to') in ids_set]
            if intra:
                cells = [((k % cols) * pitch_x, (k // cols) * pitch_y)
                         for k in range(len(els))]
                def _score(order):
                    p = {e['id']: cells[k] for k, e in enumerate(order)}
                    length = sum(abs(p[a][0]-p[b][0]) + abs(p[a][1]-p[b][1])
                                 for a, b in intra)
                    cross = 0
                    for i2 in range(len(intra)):
                        a1, b1 = intra[i2]
                        for j2 in range(i2+1, len(intra)):
                            a2, b2 = intra[j2]
                            if {a1, b1} & {a2, b2}:
                                continue
                            from AlmaGag.layout.metrics import segments_intersect
                            if segments_intersect(p[a1], p[b1], p[a2], p[b2]):
                                cross += 1
                    return (cross, length)
                els = list(min(itertools.permutations(els), key=_score))
        x0 = gx - (cols - 1) * pitch_x / 2.0
        y0 = gy - (rows - 1) * pitch_y / 2.0
        for k, e in enumerate(els):
            r, c = divmod(k, cols)
            cx = x0 + c * pitch_x
            cy = y0 + r * pitch_y
            e['x'] = cx - e.get('width', ICON_WIDTH) / 2.0
            e['y'] = cy - e.get('height', ICON_HEIGHT) / 2.0
            e['_near_zone'] = gi
            if cons.get('label'):
                e['_near_zone_label'] = cons['label']
        n_groups += 1
    return n_groups


ZONE_PAD = 24.0

# §O54: geometría del rótulo de zona — banda superior RESERVADA de 18px
# dentro de la caja (los miembros nunca la pisan por construcción) y rótulo
# 11px bold anclado al borde superior-izquierdo de SU caja.
ZONE_LABEL_BAND = 18.0
ZONE_BOX_PAD = 16.0
ZONE_LABEL_ROOM = 40.0      # sitio bajo el último icono para su etiqueta
_ZONE_LABEL_FS = 11.0


def near_zone_boxes(elements):
    """Cajas de zona `near` desde las posiciones FINALES de los miembros.

    Geometría ÚNICA compartida por el render (§N46 `draw_near_zones`) y el
    detector de colisiones (§O54: el rótulo entra al contador labels).
    Devuelve, por zona con 2+ miembros posicionados, un dict:
      {'zone': gi, 'bbox': (x1, y1, x2, y2), 'label': str|None,
       'label_bbox': (lx1, ly1, lx2, ly2)|None}
    El bbox incluye la banda de rótulo cuando la zona tiene label.
    """
    zones = {}
    for e in elements:
        gi = e.get('_near_zone')
        if gi is None or 'x' not in e or 'y' not in e:
            continue
        zones.setdefault(gi, []).append(e)

    boxes = []
    for gi, members in sorted(zones.items()):
        if len(members) < 2:
            continue
        x1 = min(m['x'] for m in members) - ZONE_BOX_PAD
        y1 = min(m['y'] for m in members) - ZONE_BOX_PAD
        x2 = max(m['x'] + m.get('width', ICON_WIDTH) for m in members) + ZONE_BOX_PAD
        y2 = max(m['y'] + m.get('height', ICON_HEIGHT) for m in members) \
            + ZONE_BOX_PAD + ZONE_LABEL_ROOM
        label = next((m.get('_near_zone_label') for m in members
                      if m.get('_near_zone_label')), None)
        label_bbox = None
        if label:
            y1 -= ZONE_LABEL_BAND           # banda reservada: sólo del rótulo
            lw = len(label) * _ZONE_LABEL_FS * 0.62
            label_bbox = (x1 + 10, y1 + 3, x1 + 10 + lw, y1 + 3 + _ZONE_LABEL_FS)
        boxes.append({'zone': gi, 'bbox': (x1, y1, x2, y2),
                      'label': label, 'label_bbox': label_bbox})
    return boxes


def evict_zone_intruders(layout) -> int:
    """§N46: expulsa de cada zona `near` a los elementos que NO son miembros.

    El clustering arma la zona en el centroide del grupo — una región que el
    placement pudo haber poblado con otros nodos. Un intruso dentro del bbox de
    la zona provoca conectores que perforan el cluster (arista×nodo). Se empuja
    a cada intruso fuera por el eje de menor desplazamiento. Devuelve cuántos
    intrusos movió."""
    zones = {}
    for e in layout.elements:
        gi = e.get('_near_zone')
        if gi is not None and 'x' in e:
            zones.setdefault(gi, []).append(e)
    if not zones:
        return 0

    def _bbox(members):
        return (min(m['x'] for m in members) - ZONE_PAD,
                min(m['y'] for m in members) - ZONE_PAD,
                max(m['x'] + m.get('width', ICON_WIDTH) for m in members) + ZONE_PAD,
                max(m['y'] + m.get('height', ICON_HEIGHT) for m in members) + ZONE_PAD)

    moved = 0

    # 1) Zona vs zona: si dos zonas se solapan se separan como BLOQUES (mover
    #    un miembro individual desarmaría su grilla). Eje de menor penetración.
    keys = sorted(zones)
    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            a, b = zones[keys[i]], zones[keys[j]]
            ax1, ay1, ax2, ay2 = _bbox(a)
            bx1, by1, bx2, by2 = _bbox(b)
            ox = min(ax2, bx2) - max(ax1, bx1)
            oy = min(ay2, by2) - max(ay1, by1)
            if ox <= 0 or oy <= 0:
                continue
            if ox < oy:
                shift = ox / 2.0 + 12.0
                left, right = (a, b) if ax1 <= bx1 else (b, a)
                for m in left:
                    m['x'] -= shift
                for m in right:
                    m['x'] += shift
            else:
                shift = oy / 2.0 + 12.0
                top, bottom = (a, b) if ay1 <= by1 else (b, a)
                for m in top:
                    m['y'] -= shift
                for m in bottom:
                    m['y'] += shift
            moved += 1

    # 2) Intrusos: sólo elementos SIN zona (un miembro de otra zona nunca se
    #    empuja individualmente — eso lo resuelve el paso 1).
    for gi, members in zones.items():
        x1, y1, x2, y2 = _bbox(members)
        for e in layout.elements:
            if (e.get('_near_zone') is not None or 'x' not in e
                    or 'contains' in e):
                continue
            ew = e.get('width', ICON_WIDTH)
            eh = e.get('height', ICON_HEIGHT)
            if e['x'] + ew <= x1 or e['x'] >= x2 or e['y'] + eh <= y1 or e['y'] >= y2:
                continue                              # fuera de la zona
            # desplazamiento mínimo hacia cada borde
            candidates = [
                (x1 - (e['x'] + ew), 'x'),            # izquierda (negativo)
                (x2 - e['x'], 'x'),                   # derecha (positivo)
                (y1 - (e['y'] + eh), 'y'),            # arriba (negativo)
                (y2 - e['y'], 'y'),                   # abajo (positivo)
            ]
            d, axis = min(candidates, key=lambda t: abs(t[0]))
            e[axis] += d + (12.0 if d > 0 else -12.0)
            e['_evicted'] = True     # su etiqueta también se vuelve estructural
            moved += 1
    return moved


def _apply_align(els, axis) -> None:
    """Lleva los centros de los elementos a una coordenada común (la media)."""
    centers = [_center(e) for e in els]
    if axis == 'x':
        target = sum(cx for cx, cy in centers) / len(centers)
        for e in els:
            e['x'] = target - e.get('width', ICON_WIDTH) / 2.0
    else:
        target = sum(cy for cx, cy in centers) / len(centers)
        for e in els:
            e['y'] = target - e.get('height', ICON_HEIGHT) / 2.0


def _apply_near(els) -> None:
    """Acerca los elementos hacia el centroide del grupo (fracción NEAR_ALPHA)."""
    centers = [_center(e) for e in els]
    gx = sum(cx for cx, cy in centers) / len(centers)
    gy = sum(cy for cx, cy in centers) / len(centers)
    for e, (cx, cy) in zip(els, centers):
        e['x'] += (gx - cx) * NEAR_ALPHA
        e['y'] += (gy - cy) * NEAR_ALPHA


def _apply_avoid(els) -> None:
    """Separa cada par de elementos solapados por el eje de menor penetración."""
    for i in range(len(els)):
        for j in range(i + 1, len(els)):
            a, b = els[i], els[j]
            aw, ah = a.get('width', ICON_WIDTH), a.get('height', ICON_HEIGHT)
            bw, bh = b.get('width', ICON_WIDTH), b.get('height', ICON_HEIGHT)
            ax, ay = a['x'], a['y']
            bx, by = b['x'], b['y']
            ox = min(ax + aw, bx + bw) - max(ax, bx)
            oy = min(ay + ah, by + bh) - max(ay, by)
            if ox <= 0 or oy <= 0:
                continue                         # no se solapan
            if ox < oy:                          # separar en X (menor penetración)
                shift = (ox + AVOID_MARGIN) / 2.0
                if ax <= bx:
                    a['x'] -= shift; b['x'] += shift
                else:
                    a['x'] += shift; b['x'] -= shift
            else:                                # separar en Y
                shift = (oy + AVOID_MARGIN) / 2.0
                if ay <= by:
                    a['y'] -= shift; b['y'] += shift
                else:
                    a['y'] += shift; b['y'] -= shift
