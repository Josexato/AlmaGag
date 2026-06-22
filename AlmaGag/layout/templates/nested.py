"""
Composición de templates anidados a nivel de container
(WISH-LAYOUT-004 Fase 4).

Cuando un container del SDJF declara `"layout_template": "<name>"`, ese
template se aplica SOLO sobre sus hijos (con coords relativas al container).
El template padre ve el container ya dimensionado y lo trata como caja
opaca.

Política de conflicto entre padre e hijo (acordada con el usuario):
- El hijo siempre infla el container según necesite.
- El padre se adapta dimensionando con el bbox final del hijo.

Procesamiento: bottom-up. Recorremos todos los containers, aplicamos su
sub-template (si tienen uno declarado), y luego el template del root
decide la disposición global.
"""

from typing import Set


def _extract_id(ref):
    return ref['id'] if isinstance(ref, dict) else ref


def collect_containers_with_template(elements):
    """
    Devuelve la lista de containers que declaran su propio `layout_template`,
    en orden bottom-up (los más anidados primero).
    """
    container_template = {}
    contains_map = {}  # container_id -> set of child IDs
    for e in elements:
        if 'contains' in e and e.get('layout_template'):
            container_template[e['id']] = e['layout_template']
            contains_map[e['id']] = {_extract_id(r) for r in e.get('contains', [])}

    # Topo-sort: containers cuya posición no depende de otros containers con template
    # Simple: ordenar por profundidad — el más anidado primero.
    by_id = {e['id']: e for e in elements}

    def depth(cid: str, seen: Set[str]) -> int:
        if cid in seen:
            return 0
        seen.add(cid)
        c = by_id.get(cid)
        if not c or 'contains' not in c:
            return 0
        d = 0
        for ref in c.get('contains', []):
            child_id = _extract_id(ref)
            child = by_id.get(child_id)
            if child and 'contains' in child:
                d = max(d, depth(child_id, seen) + 1)
        return d

    # Bottom-up: procesamos primero los más anidados (los que NO contienen
    # otros containers con template). Sort ASCENDENTE por depth.
    return sorted(
        container_template.items(),
        key=lambda kv: depth(kv[0], set()),
    )


def apply_nested_templates(data, registry):
    """
    Aplica sub-templates declarados en containers (Fase 4).

    Args:
        data: dict SDJF.
        registry: callable name -> BaseTemplate (típicamente lookup en
                  el clasificador default).

    Returns:
        list de tuplas (container_id, template_name) aplicadas.
    """
    elements = data.get('elements', [])
    connections = data.get('connections', [])
    if not elements:
        return []

    applied = []
    by_id = {e['id']: e for e in elements}
    nested = collect_containers_with_template(elements)

    for container_id, template_name in nested:
        template = registry(template_name)
        if template is None:
            continue

        container = by_id.get(container_id)
        if container is None:
            continue

        child_ids = {_extract_id(r) for r in container.get('contains', [])}
        child_elements = [e for e in elements if e['id'] in child_ids]

        # Conexiones internas al container
        internal_connections = [
            c for c in connections
            if c.get('from') in child_ids and c.get('to') in child_ids
        ]

        sub_data = {
            'elements': child_elements,
            'connections': internal_connections,
        }

        # Aplicamos el template sobre el sub-grafo
        template.apply(sub_data)

        # Las coords asignadas son absolutas (relativas al canvas 0,0 del
        # sub-template). Para que vivan dentro del container las desplazamos
        # según donde quede el container en el layout padre. Como el padre
        # aún no ha decidido posición, dejamos las coords como están y el
        # padre solo se entera del bbox total.
        # Calcular bbox
        xs, ys, xe, ye = [], [], [], []
        for e in child_elements:
            if 'x' in e and 'y' in e:
                xs.append(e['x'])
                ys.append(e['y'])
                xe.append(e['x'] + e.get('width', 80))
                ye.append(e['y'] + e.get('height', 50))
        if xs:
            min_x, min_y = min(xs), min(ys)
            max_x, max_y = max(xe), max(ye)
            # Normalizar: hacer que el bbox del sub-grafo empiece en (0, 0)
            # más un padding del header del container
            HEADER_OFFSET_Y = 60
            PADDING_X = 20
            for e in child_elements:
                if 'x' in e:
                    e['x'] = e['x'] - min_x + PADDING_X
                if 'y' in e:
                    e['y'] = e['y'] - min_y + HEADER_OFFSET_Y
            container['_inner_width'] = (max_x - min_x) + PADDING_X * 2
            container['_inner_height'] = (max_y - min_y) + HEADER_OFFSET_Y + PADDING_X

        applied.append((container_id, template_name))

    return applied


def offset_nested_children(data):
    """
    Ahora que el template padre asignó posición al container, desplazar
    los hijos sumando (container.x, container.y) — convertimos coords
    relativas a globales.
    """
    elements = data.get('elements', [])
    by_id = {e['id']: e for e in elements}

    for container in elements:
        if 'contains' not in container:
            continue
        if not container.get('layout_template'):
            continue
        if 'x' not in container or 'y' not in container:
            continue
        cx, cy = container['x'], container['y']
        for ref in container.get('contains', []):
            child = by_id.get(_extract_id(ref))
            if child is None:
                continue
            if 'x' in child:
                child['x'] += cx
            if 'y' in child:
                child['y'] += cy

        # Aplicar el inner size al container si el template padre no lo
        # ha sobrescrito todavía.
        if '_inner_width' in container and 'width' not in container:
            container['width'] = container['_inner_width']
        if '_inner_height' in container and 'height' not in container:
            container['height'] = container['_inner_height']
