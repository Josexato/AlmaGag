"""§O57 — tokens de tema.

El SDJF/.gag puede declarar una sección `theme` top-level con tokens de
color y referenciarlos por nombre en cualquier `color`:

    "theme": {"vp": "#663399", "acento": "#e8820c"},
    "elements": [{"id": "a", "type": "server", "color": "vp"}]

La resolución es un pre-proceso sobre el JSON crudo: cada `color` cuyo valor
sea una CLAVE del theme se sustituye por su hex ANTES de que el pipeline lo
vea — el resto del motor no sabe de temas. Un hex literal (o nombre CSS que
no sea token) sigue siendo válido y gana: sólo se sustituyen coincidencias
exactas con el theme.
"""

import logging

logger = logging.getLogger('AlmaGag')


def apply_theme(data) -> int:
    """Resuelve tokens de tema en elements/connections/areas/roles.

    Devuelve cuántos colores se resolvieron. No-op (0) sin sección `theme`.
    """
    theme = data.get('theme')
    if not isinstance(theme, dict) or not theme:
        return 0

    resolved = 0

    def _resolve(item):
        nonlocal resolved
        color = item.get('color')
        if isinstance(color, str) and color in theme:
            item['color'] = theme[color]
            resolved += 1

    for key in ('elements', 'connections', 'areas', 'lanes'):
        for item in data.get(key) or []:
            if isinstance(item, dict):
                _resolve(item)
    roles = data.get('roles')
    if isinstance(roles, dict):
        for spec in roles.values():
            if isinstance(spec, dict):
                _resolve(spec)

    if resolved:
        logger.info(f"§O57: {resolved} color(es) resueltos desde theme "
                    f"({len(theme)} token(s))")
    return resolved
