"""
Template 'architecture' — layout en T para diagramas arquitectónicos
(WISH-LAYOUT-004 Fase 1 + scorer Fase 2).

Patrón objetivo:
- Hay containers (= "algoritmos" o agrupadores).
- Algún container puede ser "shared" (palabra clave en label).
- Hay flujo top-down: entry → algoritmos → salida.
- Pocos ciclos.
"""

from AlmaGag.layout.templates.base import BaseTemplate
from AlmaGag.layout.templates.features import GraphFeatures


def _is_shared(container):
    # Fase 4: role declarado tiene prioridad sobre heurística por label
    if container.get('role') == 'shared':
        return True
    lbl = (container.get('label') or '').lower()
    return any(k in lbl for k in ('shared', 'compart', 'agnost'))


def _extract_id(ref):
    return ref['id'] if isinstance(ref, dict) else ref


def _categorize(elements, connections):
    """
    Categoriza elementos por rol topológico para el layout en T.
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
            continue
        # Fase 4: role declarado fuerza la categoría
        role = e.get('role')
        if role == 'entry':
            cats['entry'].append(e)
            continue
        if role == 'output' or role == 'terminal':
            cats['terminals'].append(e)
            continue
        if role == 'abstract':
            cats['abstracts'].append(e)
            continue
        # Heurística por estructura
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

    # BUGS-TPL-003: la cadena se apila en VERTICAL, así que su orden debe
    # ser el TOPOLÓGICO — ordenar por out-degree invertía request→router→
    # dispatcher (dispatcher, con 2 salidas, le ganaba a router y la
    # arista request→router atravesaba su icono). Longest-path acotado
    # (tolera ciclos); el out-degree queda solo como desempate.
    seq = cats['entry'] + cats['chain']
    seq_ids = {e['id'] for e in seq}
    lvl = {i: 0 for i in seq_ids}
    for _ in range(len(seq_ids)):
        changed = False
        for c in connections:
            f, t = c.get('from'), c.get('to')
            if f in seq_ids and t in seq_ids and f != t \
                    and lvl[f] + 1 > lvl[t]:
                lvl[t] = lvl[f] + 1
                changed = True
        if not changed:
            break
    cats['entry'].sort(key=lambda e: (lvl[e['id']], -out_count[e['id']]))
    cats['chain'].sort(key=lambda e: (lvl[e['id']], -out_count[e['id']]))
    return cats


def _order_containers_with_shared_center(containers):
    """Pone los containers shared al medio de la fila."""
    shared = [c for c in containers if _is_shared(c)]
    other = [c for c in containers if not _is_shared(c)]
    if not shared:
        return list(containers)
    half = len(other) // 2
    return other[:half] + shared + other[half:]


class ArchitectureTemplate(BaseTemplate):
    """Layout en T para arquitecturas jerárquicas con containers y shared."""

    name = 'architecture'

    def detect_score(self, features: GraphFeatures) -> float:
        """
        Señales positivas para 'architecture':
        - Tiene containers (>=2).
        - Firma estructural: 1 punto de entrada → containers paralelos → salida(s).
        - DAG (sin ciclos).
        - Profundidad moderada (3-10 niveles).
        - Branching moderado (no es chain pura).
        - (señal débil) algún label menciona 'shared'/'compart'/'agnost'.

        BUGS-TPL-001: la ventana de depth 3..7 excluía arquitecturas reales
        con cadenas más largas (cakephp-mvc, depth=10) y el peso del keyword
        'shared' estaba sobre-ajustado a la nomenclatura interna. Se amplía la
        ventana a 3..10 y se añade un bonus por la firma estructural
        entry→containers→terminal, que no depende de la nomenclatura.
        """
        score = 0.0
        if features.n_containers >= 2:
            score += 0.35
        if features.n_containers >= 3:
            score += 0.10

        # Firma estructural de arquitectura: un único punto de entrada,
        # al menos una salida, y 2+ containers paralelos en el medio.
        # Es la señal genérica (no depende de keywords) — generaliza a
        # cualquier diagrama arquitectónico (ej. MVC).
        if (features.n_root_nodes_no_incoming == 1
                and features.n_leaf_nodes_no_outgoing >= 1
                and features.n_containers >= 2):
            score += 0.10

        # Señal débil por nomenclatura (no excluyente).
        if any(k in features.label_keywords for k in ('shared', 'compart', 'agnost')):
            score += 0.15

        # Fase 4: bonus por roles declarados típicos de arquitectura
        declared_role_values = set(features.declared_roles.values())
        arch_roles = declared_role_values & {'entry', 'output', 'shared', 'abstract'}
        if arch_roles:
            score += 0.15 * min(len(arch_roles), 3) / 3  # hasta +0.15
        if not features.has_cycles:
            score += 0.10
        if 3 <= features.topological_depth <= 10:
            score += 0.15
        if 1.5 <= features.branching_factor <= 4.0:
            score += 0.10
        return min(score, 1.0)

    def apply(self, data: dict) -> None:
        apply_architecture_template(data)


# === Implementación del layout en T (Fase 1) ===

def apply_architecture_template(data):
    """Asigna coordenadas in-place siguiendo el patrón de arquitectura en T."""
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

    n_containers = len(cats['containers'])
    if n_containers > 0:
        containers_total_w = (
            n_containers * CONTAINER_W_ESTIMATED
            + (n_containers - 1) * CONTAINER_GAP_X
        )
    else:
        containers_total_w = 600

    canvas = data.setdefault('canvas', {})
    canvas_w = max(containers_total_w + 100, 800)
    center_x = canvas_w // 2

    # 1. Entry + chain vertical centrado
    y = TOP_MARGIN
    for e in cats['entry'] + cats['chain']:
        if 'x' not in e:
            e['x'] = center_x - ICON_W_HALF
        if 'y' not in e:
            e['y'] = y
        y += ENTRY_SPACING_Y

    # 2. Containers en fila, shared al medio
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

    # 3. Contract debajo, centrado
    abstract_y = middle_y + CONTAINER_ROW_H + ABSTRACT_GAP_Y
    for a in cats['abstracts']:
        if 'x' not in a:
            a['x'] = center_x - ICON_W_HALF
        if 'y' not in a:
            a['y'] = abstract_y
        abstract_y += TERMINAL_GAP_Y

    # 4. Terminales al final — BUGS-TPL-002: en UNA FILA, cada uno bajo su
    # padre primario (afinidad topológica), no en columna única centrada:
    # la columna apilaba db/cache/response a 100px bajo el contenedor
    # central (cakephp-mvc: aspecto 0.84 con canvas declarado 1.56) y
    # obligaba a sus aristas a compartir el mismo canal vertical.
    terminal_y = abstract_y + TERMINAL_GAP_Y if cats['abstracts'] else abstract_y
    owner = {}
    for e in elements:
        for ref in e.get('contains', []) or []:
            owner[_extract_id(ref)] = e['id']
    by_id = {e['id']: e for e in elements}

    def _anchor_x(eid):
        """Centro x del primario que ancla a `eid` (contenedor padre o él
        mismo); None si aún no tiene coordenadas."""
        p = by_id.get(owner.get(eid, eid))
        if not p or 'x' not in p:
            return None
        half = CONTAINER_W_ESTIMATED / 2 if 'contains' in p else ICON_W_HALF
        return p['x'] + half

    TERMINAL_SPACING_X = 150
    pending = [t for t in cats['terminals'] if 'x' not in t or 'y' not in t]
    slots = []
    for t in pending:
        parents = [c.get('from') for c in connections if c.get('to') == t['id']]
        xs = [x for x in (_anchor_x(p) for p in parents) if x is not None]
        ax = sum(xs) / len(xs) if xs else center_x
        slots.append((ax, t))
    slots.sort(key=lambda s: s[0])
    # separar anclas que colisionan en la fila (empuje a la derecha)
    placed_x = []
    for ax, t in slots:
        x = ax - ICON_W_HALF
        if placed_x and x < placed_x[-1] + TERMINAL_SPACING_X:
            x = placed_x[-1] + TERMINAL_SPACING_X
        placed_x.append(x)
        if 'x' not in t:
            t['x'] = x
        if 'y' not in t:
            t['y'] = terminal_y
    if pending:
        terminal_y += TERMINAL_GAP_Y

    canvas['width'] = canvas_w
    canvas['height'] = terminal_y + 100
