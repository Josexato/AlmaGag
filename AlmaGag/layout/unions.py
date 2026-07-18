"""
§H7 — Tipo semántico `union` (matrimonio / punto de unión).

Notación genealógica: dos progenitores comparten muchos hijos. Declararlos con
dos aristas por hijo produce un abanico doble cruzado (10 diagonales para 5
hijos). La convención clásica: unir a los dos padres por una barra y bajar UN
solo tronco por hijo desde el punto de unión.

SDJF declarativo (retrocompatible — si no hay `unions`, no pasa nada):

    "unions": [ { "id": "u1", "between": ["jose", "daria"] } ],
    "connections": [
      { "from": "u1", "to": "silvia" },   // un tronco por hijo
      { "from": "u1", "to": "lica" }
    ]

`expand_unions` traduce cada union a un NODO sintético (tipo `union`, se dibuja
como una barra corta) más dos aristas padre→union (la barra de matrimonio). El
resto del motor lo trata como un nodo normal: el layout lo coloca por baricentro
entre los dos padres y los hijos cuelgan de él → 10 aristas se vuelven 5 (+1
barra) y desaparece el abanico cruzado.
"""


def expand_unions(data: dict) -> int:
    """Expande `data['unions']` in-place a nodo sintético + aristas de barra.

    Devuelve cuántas uniones se expandieron (0 = no-op). Idempotente: marca los
    elementos/aristas creados con `_union*` para no duplicar en una 2ª pasada.
    """
    unions = data.get('unions')
    if not unions:
        return 0

    elements = data.setdefault('elements', [])
    connections = data.setdefault('connections', [])
    existing_ids = {e.get('id') for e in elements}

    n = 0
    for u in unions:
        uid = u.get('id')
        between = u.get('between') or []
        if not uid or len(between) < 2:
            continue
        # nodo sintético de union (barra), si no existe ya
        if uid not in existing_ids:
            elements.append({
                'id': uid,
                'type': 'union',
                'label': '',
                '_union': True,
            })
            existing_ids.add(uid)
        # aristas de barra padre→union (una por progenitor), marcadas
        for parent in between:
            connections.append({
                'from': parent,
                'to': uid,
                'direction': 'none',
                '_union_bar': True,
            })
        n += 1
    return n
