"""BUGS-VAL-007 (X90) — el schema HABLA.

Principio: **constructo declarado = renderizado o error explicable, nunca
silencio**. El caso tabernero declaró `spec_version: 2.0` y claves que el
motor no conoce, y la corrida no dijo UNA palabra sobre qué entendió y qué
ignoró. Esta pasada corre al cargar el JSON y NOMBRA:

- `spec_version` declarada (el formato aún no está versionado — el contrato
  formal con JSON Schema es WISH-ARCH-007; mientras tanto se registra).
- Toda clave DESCONOCIDA en las superficies de autoría: raíz, `elements[]`,
  `connections[]`, `canvas`, `areas[]`, `journeys[]`, `lanes[]`,
  `canvas.legend[]`.
- Secciones cuya FORMA no es la esperada (lista donde va dict, etc.).

Convención: las claves que empiezan con `_` son comentarios del autor
(`_comment`) y se aceptan en silencio. Las secciones de vocabulario
(`theme`, `semantics`, `roles`, `icons`, `unions`) se auditan sólo en
forma — su interior es contrato de WISH-ARCH-007.

La pasada es SOLO de nombres: no muta el JSON ni bloquea la corrida
(la compuerta dura es WISH-VAL-001/Y95).
"""

import logging

logger = logging.getLogger('AlmaGag')

# Claves aceptadas por superficie — inventario VERIFICADO contra el código
# (cada entrada tiene un consumidor real; si una clave nueva se implementa,
# se agrega aquí en el mismo commit — el test de fixtures vigila que el
# repo entero pase en silencio).
ROOT_KEYS = {
    'spec_version',                              # registrada (WISH-ARCH-007)
    'elements', 'connections', 'canvas',         # núcleo
    'areas', 'lanes',                            # vistas §I27/§I28
    'journeys',                                  # §U74/W88
    'considerations', 'constraints',             # §④ (+ alias legacy)
    'icons',                                     # .gag extendido
    'layout_template',                           # WISH-LAYOUT-004
    'roles', 'semantics', 'theme', 'unions',     # vocabulario §I28/§Q63/§O57/§H7
}

ELEMENT_KEYS = {
    'id', 'type', 'label', 'contains', 'shape',
    'x', 'y', 'width', 'height', 'hp', 'wp',
    'color', 'role', 'status', 'callout',
    'label_position', 'label_priority',
    'padding', 'aspect_ratio',               # contenedores (container.py)
}

CONNECTION_KEYS = {
    'from', 'to', 'label', 'type', 'color', 'style', 'line_style',
    'direction', 'routing', 'semantic_type',
    'waypoints', 'routing_type',                 # compat v1.5 (router_manager)
}

CANVAS_KEYS = {'width', 'height', 'flow', 'legend',
               'partition'}                 # WISH-LAYOUT-021 (X91b)

AREA_KEYS = {'id', 'label', 'members', 'color',
             'role'}                        # WISH-LAYOUT-020 (bandas X91)

JOURNEY_KEYS = {'id', 'label', 'color', 'path'}

LANE_KEYS = {'id', 'label', 'color', 'members'}

LEGEND_KEYS = {'label', 'color'}


def _unknown(d, accepted):
    """Claves de `d` fuera de `accepted`, ignorando comentarios (`_...`)."""
    return sorted(k for k in d if not k.startswith('_') and k not in accepted)


def _audit_items(items, accepted, where, describe):
    """Audita una lista de dicts; devuelve cuántos hallazgos nombró."""
    n = 0
    if not isinstance(items, list):
        return n
    for i, item in enumerate(items):
        if not isinstance(item, dict):
            logger.warning(f"[schema] {where}[{i}] no es un objeto "
                           f"({type(item).__name__}) — se ignora")
            n += 1
            continue
        bad = _unknown(item, accepted)
        if bad:
            logger.warning(f"[schema] clave(s) desconocida(s) "
                           f"{', '.join(repr(k) for k in bad)} en "
                           f"{where}[{i}] ({describe(item)}) — se ignoran")
            n += 1
    return n


def audit_schema(data) -> int:
    """Nombra todo lo declarado que el motor no reconoce. Devuelve el número
    de hallazgos (0 = el archivo entero se entiende)."""
    if not isinstance(data, dict):
        return 0
    n = 0

    sv = data.get('spec_version')
    if sv is not None:
        logger.info(f"[schema] spec_version {sv!r} declarada — el formato "
                    f"aún no está versionado; el motor la registra y sigue "
                    f"(contrato formal: WISH-ARCH-007)")

    bad = _unknown(data, ROOT_KEYS)
    if bad:
        logger.warning(f"[schema] clave(s) desconocida(s) en la raíz: "
                       f"{', '.join(repr(k) for k in bad)} — se ignoran")
        n += 1

    n += _audit_items(data.get('elements'), ELEMENT_KEYS, 'elements',
                      lambda e: repr(e.get('id', '?')))
    n += _audit_items(data.get('connections'), CONNECTION_KEYS, 'connections',
                      lambda c: f"{c.get('from', '?')}→{c.get('to', '?')}")
    n += _audit_items(data.get('areas'), AREA_KEYS, 'areas',
                      lambda a: repr(a.get('id', '?')))
    n += _audit_items(data.get('journeys'), JOURNEY_KEYS, 'journeys',
                      lambda j: repr(j.get('id', '?')))
    n += _audit_items(data.get('lanes'), LANE_KEYS, 'lanes',
                      lambda l: repr(l.get('id', '?')))

    canvas = data.get('canvas')
    if canvas is not None:
        if isinstance(canvas, dict):
            bad = _unknown(canvas, CANVAS_KEYS)
            if bad:
                logger.warning(f"[schema] clave(s) desconocida(s) en canvas: "
                               f"{', '.join(repr(k) for k in bad)} — "
                               f"se ignoran")
                n += 1
            n += _audit_items(canvas.get('legend'), LEGEND_KEYS,
                              'canvas.legend', lambda i: repr(i.get('label', '?')))
        else:
            logger.warning(f"[schema] canvas no es un objeto "
                           f"({type(canvas).__name__}) — se ignora")
            n += 1

    # Secciones de vocabulario: sólo la FORMA (el interior es WISH-ARCH-007).
    for key, want in (('roles', dict), ('semantics', dict), ('theme', dict),
                      ('icons', dict), ('unions', list),
                      ('considerations', list), ('constraints', list)):
        v = data.get(key)
        if v is not None and not isinstance(v, want):
            logger.warning(f"[schema] {key} debería ser "
                           f"{'objeto' if want is dict else 'lista'} "
                           f"({type(v).__name__}) — se ignora")
            n += 1

    if n:
        logger.warning(f"[schema] {n} hallazgo(s) — lo no reconocido se "
                       f"nombró arriba; nada se descarta en silencio")
    return n
