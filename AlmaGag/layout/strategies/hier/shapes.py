"""
§G19 — Puertos por forma real del icono (WISH-LAF-002 Fase G).

El recorte de puertos debe respetar el POLÍGONO real de cada forma, no su
bounding-box. Para rombos (decisión) se usa la convención de flowchart:

- entrada (arista entrante) → vértice SUPERIOR;
- salidas (aristas salientes) → vértices IZQUIERDO / DERECHO / INFERIOR,
  uno por vértice según la dirección dominante hacia el otro extremo.

Un puerto por vértice, sin fracciones intermedias (así los conectores no
"flotan" en las esquinas vacías del bbox del rombo).
"""

from AlmaGag.config import ICON_WIDTH, ICON_HEIGHT

DIAMOND_TYPES = {'decision', 'diamond'}

# lado (letra) → palabra usada por routing.flow_sides / labels
SIDE_WORD = {'T': 'top', 'B': 'bottom', 'L': 'left', 'R': 'right'}


def is_diamond(e) -> bool:
    return e is not None and e.get('type') in DIAMOND_TYPES


def _center(e):
    return (e['x'] + ICON_WIDTH / 2, e['y'] + ICON_HEIGHT / 2)


def diamond_vertices(e):
    """Los cuatro vértices del rombo (puntos medios de los lados del bbox)."""
    cx, cy = _center(e)
    return {
        'T': (cx, e['y']),
        'R': (e['x'] + ICON_WIDTH, cy),
        'B': (cx, e['y'] + ICON_HEIGHT),
        'L': (e['x'], cy),
    }


# direcciones unitarias (centro → vértice)
_VDIR = {'T': (0.0, -1.0), 'R': (1.0, 0.0), 'B': (0.0, 1.0), 'L': (-1.0, 0.0)}


def diamond_port(e, toward, is_source):
    """
    Vértice del rombo `e` hacia el punto `toward` (centro del otro extremo).

    Convención flowchart: si `is_source` (arista saliente) el puerto es el
    vértice L/R/B mejor alineado con la dirección; si es entrante, el vértice
    superior T. Devuelve (punto, palabra_de_lado).
    """
    cx, cy = _center(e)
    verts = diamond_vertices(e)
    if not is_source:
        return verts['T'], 'top'
    dx, dy = toward[0] - cx, toward[1] - cy
    cand = ('L', 'R', 'B')
    best = max(cand, key=lambda s: _VDIR[s][0] * dx + _VDIR[s][1] * dy)
    return verts[best], SIDE_WORD[best]


def clip_shape(e, tx, ty):
    """
    Recorta un rayo desde el centro de `e` hacia (tx,ty) contra la FORMA real:
    el rombo si `e` es decisión, si no el rectángulo del bbox. Los cycle-arcs
    (§E) usan esto para que sus extremos caigan sobre el borde real.
    """
    cx = e['x'] + ICON_WIDTH / 2
    cy = e['y'] + ICON_HEIGHT / 2
    dx, dy = tx - cx, ty - cy
    if abs(dx) < 1e-9 and abs(dy) < 1e-9:
        return (cx, cy)
    hw, hh = ICON_WIDTH / 2, ICON_HEIGHT / 2
    if is_diamond(e):
        # rombo: |X-cx|/hw + |Y-cy|/hh = 1  →  s = 1 / (|dx|/hw + |dy|/hh)
        s = 1.0 / (abs(dx) / hw + abs(dy) / hh)
    else:
        sx = hw / abs(dx) if abs(dx) > 1e-9 else float('inf')
        sy = hh / abs(dy) if abs(dy) > 1e-9 else float('inf')
        s = min(sx, sy)
    return (cx + dx * s, cy + dy * s)
