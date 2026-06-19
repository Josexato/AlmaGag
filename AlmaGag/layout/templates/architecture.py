"""
Template 'architecture' — layout en T para diagramas arquitectónicos
(WISH-LAYOUT-004 Fase 1).

Heurística:
1. Identifica el grafo en categorías por rol topológico:
   - entry: nodos raíz no-container (sin incoming), tipo document/server.
   - chain: nodos intermedios que están entre entry y los algoritmos
     (encadenados verticalmente arriba).
   - containers: elementos con 'contains' (los "algoritmos").
   - shared: container cuyo label sugiere ser compartido ('shared',
     'compartido', 'agnóstico'). Va al centro de la fila de containers.
   - abstract: nodos tipo 'contract' (clases base abstractas). Van
     debajo de los containers, centrados.
   - terminals: nodos sin outgoing (salidas). Al final del diagrama.
2. Distribuye en filas top-down:
   - Row 1+: entry y chain en columna vertical centrada (x=center).
   - Row middle: containers en fila horizontal, shared al medio.
   - Row low: contract centrado.
   - Row bottom: terminals centrados.
3. Ajusta el canvas para que quepa el contenido + margen.

NO sobreescribe coordenadas que el usuario haya puesto manualmente —
solo asigna a elementos sin x/y.
"""

from typing import Tuple


def _is_shared(container):
    """True si el label sugiere container 'compartido'."""
    lbl = (container.get('label') or '').lower()
    return any(k in lbl for k in ('shared', 'compart', 'agnost'))


def _extract_id(ref):
    return ref['id'] if isinstance(ref, dict) else ref


def _categorize(elements, connections):
    """
    Categoriza elementos por rol topológico.

    Returns: dict con keys 'entry', 'chain', 'containers', 'abstracts',
    'terminals' — listas de elementos ordenadas.
    """
    by_id = {e['id']: e for e in elements}
    in_count = {e['id']: 0 for e in elements}
    out_count = {e['id']: 0 for e in elements}
    for c in connections:
        fr, to = c.get('from'), c.get('to')
        if fr in out_count:
            out_count[fr] += 1
        if to in in_count:
            in_count[to] += 1

    contained_ids = set()
    for e in elements:
        if 'contains' in e:
            for ref in e.get('contains', []):
                contained_ids.add(_extract_id(ref))

    cats = {
        'entry': [],
        'chain': [],
        'containers': [],
        'abstracts': [],
        'terminals': [],
    }

    for e in elements:
        eid = e['id']
        if eid in contained_ids:
            continue  # hijo de container — su posición la calcula el container
        if 'contains' in e:
            cats['containers'].append(e)
        elif e.get('type') == 'contract':
            cats['abstracts'].append(e)
        elif in_count[eid] == 0 and out_count[eid] > 0:
            cats['entry'].append(e)
        elif out_count[eid] == 0 and in_count[eid] > 0:
            cats['terminals'].append(e)
        else:
            cats['chain'].append(e)

    # Ordenar entry/chain por out_count desc (más conectados arriba)
    cats['entry'].sort(key=lambda e: -out_count[e['id']])
    cats['chain'].sort(key=lambda e: -out_count[e['id']])
    return cats


def _order_containers_with_shared_center(containers):
    """Pone los containers shared al medio de la fila."""
    shared = [c for c in containers if _is_shared(c)]
    other = [c for c in containers if not _is_shared(c)]
    if not shared:
        return list(containers)
    # Distribuir: mitad izquierda de other + shared(s) + mitad derecha de other
    half = len(other) // 2
    return other[:half] + shared + other[half:]


def apply_architecture_template(data):
    """
    Asigna coordenadas in-place a los elementos de `data` siguiendo el
    patrón de arquitectura en T.

    Constantes de layout (en píxeles):
    - ENTRY_SPACING_Y = 130 (entre nodos del entry layer)
    - MIDDLE_GAP_Y = 80    (gap entre chain y containers)
    - CONTAINER_W_ESTIMATED = 280
    - CONTAINER_GAP_X = 100 (gap entre containers)
    - CONTAINER_ROW_H = 320 (alto reservado por la fila de containers)
    - ABSTRACT_GAP_Y = 80
    - TERMINAL_GAP_Y = 100
    """
    ENTRY_SPACING_Y = 130
    MIDDLE_GAP_Y = 80
    CONTAINER_W_ESTIMATED = 280
    CONTAINER_GAP_X = 100
    CONTAINER_ROW_H = 320
    ABSTRACT_GAP_Y = 80
    TERMINAL_GAP_Y = 100
    ICON_W_HALF = 40
    TOP_MARGIN = 60

    elements = data.get('elements', [])
    connections = data.get('connections', [])
    if not elements:
        return

    cats = _categorize(elements, connections)

    # Estimar ancho necesario por la fila de containers
    n_containers = len(cats['containers'])
    if n_containers > 0:
        containers_total_w = (
            n_containers * CONTAINER_W_ESTIMATED
            + (n_containers - 1) * CONTAINER_GAP_X
        )
    else:
        containers_total_w = 600

    # Canvas y centro
    canvas = data.setdefault('canvas', {})
    canvas_w = max(containers_total_w + 100, 800)
    center_x = canvas_w // 2

    # 1. Entry + chain en columna vertical centrada
    y = TOP_MARGIN
    for e in cats['entry'] + cats['chain']:
        if 'x' not in e:
            e['x'] = center_x - ICON_W_HALF
        if 'y' not in e:
            e['y'] = y
        y += ENTRY_SPACING_Y

    # 2. Fila de containers — shared al medio
    middle_y = y + MIDDLE_GAP_Y
    if n_containers > 0:
        ordered = _order_containers_with_shared_center(cats['containers'])
        start_x = center_x - containers_total_w // 2
        x = start_x
        for c in ordered:
            if 'x' not in c:
                c['x'] = x
            if 'y' not in c:
                c['y'] = middle_y
            x += CONTAINER_W_ESTIMATED + CONTAINER_GAP_X

    # 3. Contract centrado debajo de containers
    abstract_y = middle_y + CONTAINER_ROW_H + ABSTRACT_GAP_Y
    for a in cats['abstracts']:
        if 'x' not in a:
            a['x'] = center_x - ICON_W_HALF
        if 'y' not in a:
            a['y'] = abstract_y
        abstract_y += TERMINAL_GAP_Y

    # 4. Terminales centrados al final
    terminal_y = abstract_y + TERMINAL_GAP_Y if cats['abstracts'] else abstract_y
    for t in cats['terminals']:
        if 'x' not in t:
            t['x'] = center_x - ICON_W_HALF
        if 'y' not in t:
            t['y'] = terminal_y
        terminal_y += TERMINAL_GAP_Y

    # Ajustar canvas height
    canvas['width'] = canvas_w
    canvas['height'] = terminal_y + 100
