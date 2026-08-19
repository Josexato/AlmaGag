"""WISH-LAYOUT-025 — escenografía asistida (principio de Escenografía).

«Las áreas se definen antes que la historia, como el mapa general de una
idea» (el autor, 12-ago-2026). Este módulo es la derivación que CONFIESA
su plan: el motor MIDE el contenido de cada área, CONDENSA el grafo
(quién habla con quién y cuánto), LEE las señales narrativas (roles
declarados, la columna vertebral de los journeys, hubs multi-área) y
emite un `canvas.partition` declarable con las razones nombradas.

Contrato §R: el motor RECOMIENDA con números, jamás impone — la salida
es JSON para pegar, ajustar o ignorar; la precedencia sigue siendo
partition declarada > area.role > derivación.

Heurística v1 (filas de arriba a abajo):
1. `role` declarado en alguna área → bandas semánticas y listo.
2. Fila superior: las áreas que ALIMENTAN la columna vertebral (más
   salidas hacia ella que entradas desde ella) — proveedores, gobierno.
3. Fila central: la columna vertebral — el journey condensado más largo,
   en su orden; sin journeys, la cadena más larga del grafo condensado.
4. Fila inferior: los DESTINOS (más entradas que salidas).
5. Bandas de ancho completo al fondo: los HUBS (≥3 áreas destino
   distintas — buses, capas transversales).

Los tamaños salen del contenido MEDIDO (unidad UNIT px): ninguna celda
domina la escala y el vacío accidental desaparece — el vacío que quede
es escenografía, no accidente.
"""

import json
import logging
from collections import Counter

from AlmaGag.utils import extract_item_id
from AlmaGag.layout.layout import Layout

logger = logging.getLogger('AlmaGag')

UNIT = 150.0          # px de contenido por unidad de proporción
HUB_MIN_AREAS = 3     # mismo umbral que el bus X92


def _build_area_of(data):
    """Elemento → área, incluyendo la herencia ARCH-009: los hijos de un
    contenedor miembro de área pertenecen a esa área (las conexiones
    viajan entre hijos — sin esto el grafo condensado queda VACÍO en el
    patrón zona+contenedor y el análisis es ciego)."""
    by_elem = {e['id']: e for e in data.get('elements', [])}
    area_of = {}
    for a in data.get('areas') or []:
        for m in a.get('members', []):
            area_of[m] = a['id']
    for m, aid in list(area_of.items()):
        e = by_elem.get(m)
        if e and e.get('contains'):
            for item in e['contains']:
                area_of.setdefault(extract_item_id(item), aid)
    return area_of


def connectivity_table(data):
    """La tabla del autor (18-ago-2026, armada a mano en Excel): por cada
    elemento conectado, enlaces INTERNOS (misma área) y ENTRE ÁREAS, con
    hallazgos nombrados — un elemento sin enlaces internos y con varios
    externos es un hub puro: su membresía es narrativa, no estructural.
    Devuelve (filas, hallazgos): filas = [(id, internos, externos, área)]."""
    area_of = _build_area_of(data)
    interno, externo = Counter(), Counter()
    for c in data.get('connections', []):
        f, t = c.get('from'), c.get('to')
        fa, ta = area_of.get(f), area_of.get(t)
        if fa is None or ta is None:
            continue
        if fa == ta:
            interno[f] += 1
            interno[t] += 1
        else:
            externo[f] += 1
            externo[t] += 1
    ids = sorted(set(interno) | set(externo),
                 key=lambda i: (area_of.get(i, ''), i))
    filas = [(i, interno[i], externo[i], area_of.get(i, '?')) for i in ids]
    hallazgos = []
    for i, n_in, n_ex, aid in filas:
        if n_in == 0 and n_ex >= HUB_MIN_AREAS:
            hallazgos.append(
                f"'{i}': 0 enlaces internos y {n_ex} entre áreas — hub "
                f"puro: su membresía en {aid} es narrativa, no "
                f"estructural (candidato a role 'hub' o al borde)")
    coh = {}
    for i, n_in, n_ex, aid in filas:
        a, b = coh.get(aid, (0, 0))
        coh[aid] = (a + n_in, b + n_ex)
    for aid, (n_in, n_ex) in sorted(coh.items()):
        if n_ex > n_in:
            hallazgos.append(
                f"área {aid}: {n_in // 2} enlace(s) interno(s) contra "
                f"{n_ex} hacia afuera — más pasillo que casa: revisar si "
                f"la agrupación cuenta la historia o sólo la decora")
    return filas, hallazgos


def _measure_areas(data):
    """Sub-layout por área sobre COPIAS → {aid: (w, h)} en px."""
    from AlmaGag.layout.strategies.hier.areas import layout_by_areas
    d = json.loads(json.dumps({'elements': data.get('elements', []),
                               'connections': data.get('connections', []),
                               'areas': data.get('areas', [])}))
    L = Layout(elements=d['elements'], connections=d['connections'],
               canvas={'width': 1400, 'height': 900})
    boxes = layout_by_areas(L, d['areas'])
    return {b['id']: (b['w'], b['h']) for b in boxes if not b.get('solo')}


def _condensed(data, area_of):
    """Grafo condensado dirigido: Counter{(área_from, área_to): n}."""
    pairs = Counter()
    for c in data.get('connections', []):
        fa, ta = area_of.get(c.get('from')), area_of.get(c.get('to'))
        if fa and ta and fa != ta:
            pairs[(fa, ta)] += 1
    return pairs


def _backbone(data, area_of, area_ids):
    """La columna vertebral: el journey condensado más largo; sin
    journeys, la cadena más larga del grafo condensado (DFS acotado)."""
    best = []
    for j in data.get('journeys', []) or []:
        path, prev = [], None
        for n in j.get('path', []):
            aid = area_of.get(n)
            if aid and aid != prev:
                path.append(aid)
                prev = aid
        if len(path) > len(best):
            best = path
    if best:
        return best
    pairs = _condensed(data, area_of)
    succ = {}
    for (f, t), _n in pairs.items():
        succ.setdefault(f, []).append(t)
    longest = []

    def dfs(node, path):
        nonlocal longest
        if len(path) > len(longest):
            longest = list(path)
        if len(path) >= len(area_ids):
            return
        for nxt in succ.get(node, []):
            if nxt not in path:
                dfs(nxt, path + [nxt])
    for a in area_ids:
        dfs(a, [a])
    return longest


def suggest_partition(data):
    """Devuelve {'partition': {...}, 'razones': [...]} o None si el
    archivo no da para escenografía (menos de 2 áreas)."""
    areas = data.get('areas') or []
    if len(areas) < 2:
        logger.warning("[escenografia] se necesitan ≥2 áreas para "
                       "sugerir un plano — nada que recomendar")
        return None
    area_ids = [a['id'] for a in areas]
    area_of = _build_area_of(data)    # ARCH-009: los hijos heredan el área
    razones = []

    dims = _measure_areas(data)
    units = {aid: (max(round((w + 0.0) / UNIT, 1), 0.8),
                   max(round((h + 0.0) / UNIT, 1), 0.8))
             for aid, (w, h) in dims.items()}

    roles = {a['id']: a.get('role') for a in areas if a.get('role')}
    pairs = _condensed(data, area_of)

    # hubs: ≥HUB_MIN_AREAS áreas destino distintas
    out_targets = {}
    for (f, t), _n in pairs.items():
        out_targets.setdefault(f, set()).add(t)
    hubs = [a for a in area_ids
            if len(out_targets.get(a, ())) >= HUB_MIN_AREAS]

    if roles:
        from AlmaGag.layout.strategies.hier.areas import (
            _ROLE_BAND, _BAND_DEFAULT)
        bands = {}
        for aid in area_ids:
            b = _ROLE_BAND.get(roles.get(aid), _BAND_DEFAULT)
            bands.setdefault(b, []).append(aid)
        rows = [bands[k] for k in sorted(bands)]
        razones.append('roles declarados: bandas semánticas '
                       '(control/feeder · chain · external · overlay)')
    else:
        spine = [a for a in _backbone(data, area_of, area_ids)
                 if a not in hubs]
        if spine:
            razones.append(f"columna vertebral: {' → '.join(spine)} "
                           f"(journey condensado más largo)")
        rest = [a for a in area_ids if a not in spine and a not in hubs]
        top, bottom = [], []
        for a in rest:
            out_to = sum(n for (f, t), n in pairs.items()
                         if f == a and t in spine)
            in_from = sum(n for (f, t), n in pairs.items()
                          if t == a and f in spine)
            if out_to >= in_from:
                top.append(a)
                razones.append(f'{a} → fila superior (alimenta la '
                               f'columna: {out_to} salidas vs '
                               f'{in_from} entradas)')
            else:
                bottom.append(a)
                razones.append(f'{a} → fila inferior (destino: '
                               f'{in_from} entradas vs {out_to} salidas)')
        # los HUBS van al MEDIO (observación del autor): un área que
        # conecta con todo, en el fondo obliga a cada ramal a cruzar la
        # lámina entera y apila el tráfico en los márgenes; al centro, los
        # ramales son cortos en ambas direcciones.
        rows = [r for r in (top, spine or rest) if r]
        for h in hubs:
            rows.append([h])
            razones.append(f'{h} → banda CENTRAL '
                           f'({len(out_targets[h])} áreas destino — el hub '
                           f'va al medio, cerca de todo)')
        if bottom:
            rows.append(bottom)

    # celdas: alto uniforme por fila; los hubs se estiran al ancho máximo
    row_dims = []
    for row in rows:
        rw = sum(units[a][0] for a in row if a in units)
        rh = max((units[a][1] for a in row if a in units), default=1.0)
        row_dims.append((row, rw, rh))
    total_w = max(rw for _r, rw, _h in row_dims)
    splits, prev_first, first = [], None, True
    for row, rw, rh in row_dims:
        stretch = len(row) == 1 and row[0] in hubs
        for i, aid in enumerate(row):
            w = round(total_w, 1) if stretch else units[aid][0]
            cell = {'area': aid, 'size': [w, round(rh, 1)]}
            if first:
                cell['anchor'] = 'base'
                first = False
            elif i == 0:
                cell.update({'at': 'below', 'of': prev_first})
            else:
                cell.update({'at': 'right_of', 'of': row[i - 1]})
            splits.append(cell)
        prev_first = row[0]
    total_h = sum(rh for _r, _w, rh in row_dims)
    partition = {'scheme': 'bsp',
                 'ratio': [round(total_w, 1), round(total_h, 1)],
                 'splits': splits}
    razones.append(f'proporciones medidas del contenido real '
                   f'(unidad {UNIT:.0f}px) — ninguna celda domina la escala')
    return {'partition': partition, 'razones': razones}


def sugerir_cli(input_file) -> bool:
    """Camino CLI de --sugerir-escenografia: analiza y ESCRIBE la
    recomendación (razones al log, JSON listo para pegar a stdout)."""
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        logger.error(f"[escenografia] no se pudo leer {input_file}: {e}")
        return False
    out = suggest_partition(data)
    if out is None:
        return False
    filas, hallazgos = connectivity_table(data)
    if filas:
        logger.info("[escenografia] conectividad medida "
                    "(internos | entre-áreas | área):")
        for i, n_in, n_ex, aid in filas:
            logger.info(f"  {i:>12}  {n_in:2d} | {n_ex:2d} | {aid}")
        for h in hallazgos:
            logger.warning(f"[escenografia] {h}")
    logger.info("[escenografia] razones del plano sugerido:")
    for r in out['razones']:
        logger.info(f"  - {r}")
    logger.info("[escenografia] pegar el bloque en canvas.partition — "
                "la declaración del autor siempre gana (§R)")
    print(json.dumps({'partition': out['partition']},
                     indent=2, ensure_ascii=False))
    return True
