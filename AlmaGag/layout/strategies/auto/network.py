"""
§N45/§N47 — Topología de red no jerárquica: zonas + hub-and-spoke.

Una red no tiene origen→sumidero: tiene HUBS (las nubes WAN) y SITIOS. Nivelar
por distancia al origen (pipeline) produce la tira 1900×1200 con ~60% vacío que
el review midió en condestable. Este módulo:

1. `detect_network_topology` — señales §N45 (2 de 3 bastan): (a) nodos
   cloud/inet de grado alto (hubs), (b) mayoría de conexiones bidireccionales,
   (c) ciclos no dirigidos. Sólo aplica sin coordenadas manuales.
2. `build_sites` — los `near[]` del .gag son SEMILLAS de sitio (pueden ser
   parciales: los .gag reales los traen incompletos); se expanden con los
   vecinos no-hub conectados al sitio, y los nodos sueltos forman mini-sitios
   por componente conexa (sin hubs de por medio).
3. `apply_network_layout` — banda central de hubs (columna: satisface el
   `avoid` entre nubes separándolas verticalmente) y sitios alrededor
   (izquierda/derecha/abajo/arriba) elegidos por determinismo de ids (§N47:
   dos .gag que comparten ids producen la misma plantilla de zonas). Cada
   sitio se SINTETIZA como consideración `near` → la maquinaria §N46 (grilla
   compacta, bloque rígido, caja de zona, etiquetas estructurales) hace el
   sub-layout sin código nuevo.
"""

import logging
import math
from typing import Dict, List, Set, Tuple

from AlmaGag.config import ICON_WIDTH, ICON_HEIGHT

logger = logging.getLogger('AlmaGag')

# §O55: una sola verdad — los alias de nube (inet/wan/internet → cloud) viven
# en draw/icons.ICON_TYPE_ALIASES; ser hub y dibujarse como nube van juntos.
from AlmaGag.draw.icons import ICON_TYPE_ALIASES
HUB_TYPES = {'cloud'} | {a for a, t in ICON_TYPE_ALIASES.items() if t == 'cloud'}
HUB_MIN_DEGREE = 2   # las nubes con ≥2 enlaces son banda WAN (la
                     # detección ya exige 30% no-dirigido, sin FP)


def _degrees(elements, connections) -> Dict[str, int]:
    deg: Dict[str, int] = {e['id']: 0 for e in elements}
    for c in connections:
        for k in ('from', 'to'):
            if c.get(k) in deg:
                deg[c[k]] += 1
    return deg


def find_hubs(elements, connections) -> List[str]:
    """Nubes/inet de grado ≥ HUB_MIN_DEGREE, en orden de aparición."""
    deg = _degrees(elements, connections)
    return [e['id'] for e in elements
            if str(e.get('type', '')).lower() in HUB_TYPES
            and deg.get(e['id'], 0) >= HUB_MIN_DEGREE]


def detect_network_topology(elements, connections) -> bool:
    """§N45: 2 de 3 señales → el grafo es topología de red, no flujo.

    Nunca aplica si hay coordenadas manuales (el autor ya decidió el layout)
    ni si el grafo es trivial."""
    if any('x' in e or 'y' in e for e in elements):
        return False
    if len(elements) < 6 or not connections:
        return False

    # (a) hubs: nubes de grado alto — obligatorio (hub-and-spoke los necesita)
    if not find_hubs(elements, connections):
        return False
    # (b) carácter NO dirigido — obligatorio y el discriminador clave: una red
    # tiene enlaces bidireccionales/none (el tráfico va y viene); un flujo con
    # icono de nube y ciclos sigue siendo 100% forward (06-flujo-ejecucion,
    # svg-to-bwt-flow y system-architecture eran falsos positivos sin esto).
    undirected = sum(1 for c in connections
                     if c.get('direction') in ('bidirectional', 'none'))
    if undirected * 10 < len(connections) * 3:      # < 30%
        return False
    return True


def build_sites(elements, connections, considerations) -> List[List[str]]:
    """Sitios completos a partir de semillas `near` (posiblemente parciales).

    - Cada `near[]` es una semilla; se fusionan las que compartan miembros.
    - Expansión: un no-hub adyacente a un sitio (sin pasar por hubs) se une al
      sitio con más vecinos suyos.
    - Los no-hub restantes forman mini-sitios por componente conexa del grafo
      SIN hubs (los hubs separan sitios, no los unen).
    Determinista (§N47): ordena por id en cada paso.
    """
    hubs = set(find_hubs(elements, connections))
    ids = [e['id'] for e in elements if 'contains' not in e]
    non_hub = [i for i in ids if i not in hubs]

    adj: Dict[str, Set[str]] = {i: set() for i in ids}
    for c in connections:
        a, b = c.get('from'), c.get('to')
        if a in adj and b in adj:
            adj[a].add(b)
            adj[b].add(a)

    # 1) semillas desde near (fusionando solapadas)
    sites: List[Set[str]] = []
    for cons in considerations or []:
        if cons.get('kind') != 'near':
            continue
        group = {i for i in cons['ids'] if i in adj and i not in hubs}
        if len(group) < 1:
            continue
        merged = None
        for s in sites:
            if s & group:
                s |= group
                merged = s
                break
        if merged is None:
            sites.append(set(group))

    # 2) expansión por conectividad (iterar hasta estabilidad)
    assigned = {i for s in sites for i in s}
    changed = True
    while changed:
        changed = False
        for i in sorted(non_hub):
            if i in assigned:
                continue
            votes = []
            for si, s in enumerate(sites):
                n = len(adj[i] & s)
                if n:
                    votes.append((n, -si))
            if votes:
                votes.sort(reverse=True)
                sites[-votes[0][1]].add(i)
                assigned.add(i)
                changed = True

    # 3) sobrantes: componentes conexas del grafo sin hubs
    for i in sorted(non_hub):
        if i in assigned:
            continue
        comp, stack = set(), [i]
        while stack:
            n = stack.pop()
            if n in comp or n in hubs or n in assigned:
                continue
            comp.add(n)
            stack.extend(adj[n] - hubs)
        if comp:
            sites.append(comp)
            assigned |= comp

    return [sorted(s) for s in sites if s]


def apply_network_layout(layout, considerations) -> int:
    """§N45: banda central de hubs + sitios alrededor. Escribe coordenadas
    macro (el sub-layout fino lo hace §N46 vía consideraciones sintetizadas) y
    devuelve el número de sitios (0 = no aplicó).

    Muta `considerations` in-place agregando los `near` sintetizados de los
    sitios que no estaban cubiertos por un near del autor."""
    elements = layout.elements
    connections = layout.connections
    if any('contains' in e for e in elements):
        return 0          # sitios + contenedores anidados: fuera de alcance v1
    if not detect_network_topology(elements, connections):
        return 0

    hubs = find_hubs(elements, connections)
    sites = build_sites(elements, connections, considerations)
    if not sites or not hubs:
        return 0

    by_id = layout.elements_by_id

    # --- banda central de hubs: columna vertical (satisface avoid entre nubes) ---
    CX, CY = 640.0, 420.0
    HUB_GAP = 240.0
    hy = CY - (len(hubs) - 1) * HUB_GAP / 2.0
    for h in sorted(hubs):
        e = by_id[h]
        e['x'] = CX - ICON_WIDTH / 2.0
        e['y'] = hy - ICON_HEIGHT / 2.0
        # la banda de hubs también es una zona rotulada (caja «WAN») — mismo
        # dibujo/rigidez que los sitios, sin re-grilla (no hay near que la
        # clusterice: conserva la columna vertical).
        e['_near_zone'] = 9000
        e['_near_zone_label'] = 'WAN'
        hy += HUB_GAP

    # --- sitios alrededor: slots deterministas (izq, der, abajo, arriba, …) ---
    def _site_extent(members) -> Tuple[float, float]:
        n = len(members)
        cols = max(1, math.ceil(math.sqrt(n)))
        rows = math.ceil(n / cols)
        return cols * 210.0, rows * 130.0

    slots = [(-1, 0), (1, 0), (0, 1), (0, -1), (-1, 1), (1, 1)]
    # §N49: el slot de una zona depende SÓLO de su identidad (hash del primer
    # id), no de qué otras zonas existan — una zona compartida entre antes/
    # después conserva su slot y las nuevas toman slots libres por sondeo.
    import hashlib
    def _pref(members):
        # min-hash sobre TODOS los miembros: la zona compartida entre versiones
        # conserva su clave aunque gane/pierda algún miembro version-específico
        # (los ids compartidos dominan el mínimo).
        return min(int(hashlib.md5(m.encode()).hexdigest(), 16)
                   for m in members) % len(slots)
    ordered = sorted(sites, key=lambda s: _pref(s))
    taken = {}
    for members in ordered:
        k = _pref(members)
        while k in taken:
            k = (k + 1) % len(slots)
        taken[k] = members
    for k, members in sorted(taken.items()):
        dx, dy = slots[k % len(slots)]
        w, h = _site_extent(members)
        sx = CX + dx * (w / 2.0 + 330.0)
        sy = CY + dy * (h / 2.0 + 300.0)
        for m in members:
            e = by_id.get(m)
            if e is not None:
                e['x'] = sx - ICON_WIDTH / 2.0
                e['y'] = sy - ICON_HEIGHT / 2.0

    # --- sintetizar near por sitio no cubierto (alimenta §N46) ---
    covered: List[Set[str]] = [set(c['ids']) for c in considerations
                               if c.get('kind') == 'near']
    for members in ordered:
        ms = set(members)
        if len(ms) < 2 or any(ms <= c for c in covered):
            continue          # singletons no son zona; cubiertos ya tienen near
        considerations.append({'kind': 'near', 'ids': list(members), 'axis': 'x'})

    # §N47: los enlaces INTER-ZONA viajan por el corredor con codos
    # ortogonales (salir por el borde del sitio, viajar ortogonal, entrar por
    # el borde del destino) — no en diagonal recta. Los intra-zona quedan
    # rectos (son cortos, dentro de la caja). Se respeta un routing explícito.
    zone_of = {}
    for k, members in enumerate(ordered):
        for m in members:
            zone_of[m] = k
    for h in hubs:
        zone_of[h] = f'hub'
    n_ortho = 0
    for c in connections:
        a, b = c.get('from'), c.get('to')
        if zone_of.get(a) is not None and zone_of.get(a) != zone_of.get(b):
            r = c.setdefault('routing', {})
            if 'type' not in r:
                r['type'] = 'orthogonal'
                n_ortho += 1

    logger.info(f"§N45: topología de red — {len(hubs)} hub(s) en banda central, "
                f"{len(ordered)} sitio(s) alrededor, "
                f"{n_ortho} enlace(s) inter-zona por corredor ortogonal (§N47)")
    return len(ordered)
