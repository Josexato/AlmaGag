"""
GraphFeatures — métricas extraídas del grafo del SDJF para alimentar a los
clasificadores de templates (WISH-LAYOUT-004 Fase 2).

Cada template tiene un `detect_score(features)` que mira estas métricas y
devuelve un score [0, 1] indicando qué tan probablemente el grafo coincide
con su patrón.
"""

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Set


def _extract_id(ref):
    return ref['id'] if isinstance(ref, dict) else ref


@dataclass
class GraphFeatures:
    """
    Resumen estructural del grafo del SDJF.

    Convención: solo se consideran elementos ROOT (no contenidos en otros
    containers) para las métricas globales. Los hijos de un container se
    cuentan en `n_contained` pero no participan del análisis topológico
    global — viven dentro de su container.
    """
    n_elements: int  # total de elementos en SDJF
    n_root_elements: int  # elementos no-container que no son hijos de nadie
    n_connections: int  # total de conexiones
    n_containers: int  # elementos con 'contains'
    n_contained: int  # elementos referenciados en algún 'contains'

    n_root_nodes_no_incoming: int  # raíces topológicas (entry points)
    n_leaf_nodes_no_outgoing: int  # hojas (sinks/outputs)

    max_degree: int  # máximo (in + out) entre todos los nodos
    avg_degree: float
    max_degree_ratio: float  # max_degree / avg_degree (1.0 = uniforme)

    has_cycles: bool
    n_self_loops: int
    topological_depth: int  # cantidad de niveles topológicos

    branching_factor: float  # avg out_degree de nodos con outgoing > 0
    pct_inter_container_connections: float  # 0-1
    label_keywords: Set[str] = field(default_factory=set)
    # WISH-LAYOUT-004 Fase 4: roles semánticos declarados por el usuario
    # via "role": "<value>" en cada elemento. Mapea elem_id → role string.
    # Ej: {"entry_a": "entry", "shared_box": "shared", "main_db": "hub"}.
    declared_roles: dict = field(default_factory=dict)

    @classmethod
    def extract(cls, elements, connections) -> 'GraphFeatures':
        n_elements = len(elements)
        n_connections = len(connections)

        # IDs contenidos en algún container
        contained_ids: Set[str] = set()
        container_ids: Set[str] = set()
        container_membership = {}  # child_id -> container_id
        for e in elements:
            if 'contains' in e:
                container_ids.add(e['id'])
                for ref in e.get('contains', []):
                    cid = _extract_id(ref)
                    contained_ids.add(cid)
                    container_membership[cid] = e['id']

        root_elements = [e for e in elements if e['id'] not in contained_ids]
        root_ids: Set[str] = {e['id'] for e in root_elements}

        # Conexiones que involucran elementos root (la topología global)
        in_count = defaultdict(int)
        out_count = defaultdict(int)
        adj_out = defaultdict(list)  # para detectar ciclos
        n_self_loops = 0

        inter_container = 0
        all_with_container = 0

        for c in connections:
            fr, to = c.get('from'), c.get('to')
            if not fr or not to:
                continue
            if fr == to:
                n_self_loops += 1

            # Para grado, miramos en el espacio "root" (resolviendo cada
            # endpoint a su container padre si está contenido).
            fr_root = container_membership.get(fr, fr)
            to_root = container_membership.get(to, to)

            out_count[fr_root] += 1
            in_count[to_root] += 1
            adj_out[fr_root].append(to_root)

            # Métrica de "% inter-container"
            fr_in_container = fr in contained_ids
            to_in_container = to in contained_ids
            if fr_in_container or to_in_container:
                all_with_container += 1
                # Inter-container si los dos extremos pertenecen a containers
                # DISTINTOS (o uno es free y el otro contenido).
                fr_owner = container_membership.get(fr)
                to_owner = container_membership.get(to)
                if fr_owner and to_owner and fr_owner != to_owner:
                    inter_container += 1
                elif fr_owner != to_owner:  # uno contenido, otro no
                    inter_container += 1

        # Grados
        all_root_for_degree = root_ids
        degrees = []
        for rid in all_root_for_degree:
            degrees.append(in_count[rid] + out_count[rid])
        max_degree = max(degrees) if degrees else 0
        avg_degree = sum(degrees) / len(degrees) if degrees else 0.0
        max_degree_ratio = (max_degree / avg_degree) if avg_degree > 0 else 0.0

        # Raíces / hojas topológicas (solo entre elementos root)
        n_root_nodes_no_incoming = sum(
            1 for rid in root_ids
            if in_count[rid] == 0 and out_count[rid] > 0
        )
        n_leaf_nodes_no_outgoing = sum(
            1 for rid in root_ids
            if out_count[rid] == 0 and in_count[rid] > 0
        )

        # Ciclos vía DFS
        has_cycles = cls._has_cycle(adj_out, root_ids)

        # Profundidad topológica (BFS desde raíces; si hay ciclos, devuelve
        # la profundidad alcanzada antes de loops).
        topological_depth = cls._compute_depth(adj_out, root_ids, in_count)

        # Branching factor: avg out_degree de los nodos que tienen outgoing
        nodes_with_outgoing = [rid for rid in root_ids if out_count[rid] > 0]
        if nodes_with_outgoing:
            branching_factor = sum(out_count[rid] for rid in nodes_with_outgoing) / len(nodes_with_outgoing)
        else:
            branching_factor = 0.0

        pct_inter_container_connections = (
            inter_container / all_with_container if all_with_container > 0 else 0.0
        )

        # Keywords semánticas (lowercased, sin acentos básicos)
        label_keywords: Set[str] = set()
        SEMANTIC_TOKENS = {
            'shared', 'compart', 'agnost', 'common',
            'hub', 'spoke', 'branch', 'edge', 'central',
            'step', 'phase', 'stage', 'flow', 'pipeline',
            'entry', 'input', 'output', 'sink', 'source',
            'state', 'transition',
            'entity', 'table', 'database',
        }
        for e in elements:
            lbl = (e.get('label') or '').lower()
            for token in SEMANTIC_TOKENS:
                if token in lbl:
                    label_keywords.add(token)

        # Roles declarados explícitamente por el usuario (Fase 4).
        # Valores reconocidos: entry, output, shared, hub, spoke,
        # actor, state, abstract, terminal.
        declared_roles = {}
        for e in elements:
            role = e.get('role')
            if role:
                declared_roles[e['id']] = role
                # Los roles declarados también suman a label_keywords para
                # que los scorers heurísticos los aprovechen sin cambios.
                label_keywords.add(role)

        return cls(
            n_elements=n_elements,
            n_root_elements=len(root_elements),
            n_connections=n_connections,
            n_containers=len(container_ids),
            n_contained=len(contained_ids),
            n_root_nodes_no_incoming=n_root_nodes_no_incoming,
            n_leaf_nodes_no_outgoing=n_leaf_nodes_no_outgoing,
            max_degree=max_degree,
            avg_degree=avg_degree,
            max_degree_ratio=max_degree_ratio,
            has_cycles=has_cycles,
            n_self_loops=n_self_loops,
            topological_depth=topological_depth,
            branching_factor=branching_factor,
            pct_inter_container_connections=pct_inter_container_connections,
            label_keywords=label_keywords,
            declared_roles=declared_roles,
        )

    @staticmethod
    def _has_cycle(adj_out, root_ids):
        """DFS de ciclos."""
        WHITE, GRAY, BLACK = 0, 1, 2
        color = {nid: WHITE for nid in root_ids}

        def visit(node):
            color[node] = GRAY
            for nb in adj_out.get(node, []):
                if nb not in color:
                    continue  # nodo fuera de root_ids
                if color[nb] == GRAY:
                    return True
                if color[nb] == WHITE and visit(nb):
                    return True
            color[node] = BLACK
            return False

        for nid in root_ids:
            if color[nid] == WHITE and visit(nid):
                return True
        return False

    @staticmethod
    def _compute_depth(adj_out, root_ids, in_count):
        """BFS por niveles desde los nodos con in_count==0."""
        starts = [nid for nid in root_ids if in_count[nid] == 0]
        if not starts:
            return 0
        depth_of = {nid: 0 for nid in starts}
        queue = list(starts)
        max_depth = 0
        while queue:
            node = queue.pop(0)
            for nb in adj_out.get(node, []):
                if nb not in root_ids:
                    continue
                new_d = depth_of[node] + 1
                # Evitar bucles infinitos por ciclos: solo actualizamos si
                # el destino aún no tiene profundidad o si la nueva es mayor
                # y no creció demasiado.
                if nb not in depth_of:
                    depth_of[nb] = new_d
                    queue.append(nb)
                    max_depth = max(max_depth, new_d)
                elif new_d > depth_of[nb] and new_d < len(root_ids):
                    depth_of[nb] = new_d
                    queue.append(nb)
                    max_depth = max(max_depth, new_d)
        return max_depth + 1  # depth en niveles, no en edges
