"""
Constraints declarativas de layout — rescate ④ desde LAF.

LAF sólo llegó a `align` (top/bottom/center como nivel topológico); `near` y
`avoid` quedaron documentados como "v2" sin implementar. Acá se completan como
constraints **geométricas y relacionales** que el usuario declara en el SDJF y
el motor (AUTO) aplica sobre las posiciones ya calculadas.

Schema (array top-level `constraints`):

    "constraints": [
      {"align": ["a", "b", "c"], "axis": "x"},   # misma columna (X común)
      {"align": ["d", "e"], "axis": "y"},         # misma fila (Y común)
      {"near":  ["app", "db"]},                    # acercar (reduce dispersión)
      {"avoid": ["front", "back"]}                 # no solapar (separa el par)
    ]

- `align`: lleva los elementos a una X (axis 'x', por defecto) o Y (axis 'y')
  común = la media del grupo. Es la más fuerte y la que LAF intentó.
- `near`: acerca a los miembros hacia su centroide (reduce la caja que los
  contiene) sin encimarlos — la resolución de colisiones de AUTO evita solapes.
- `avoid`: si dos elementos se solapan, los separa por el eje de menor
  penetración + un margen.

Funciones puras sobre el layout; agnósticas del renderer. Si el JSON no declara
`constraints`, `extract_constraints` devuelve [] y no se toca nada (cero
regresión sobre los diagramas existentes).
"""

import logging
from typing import Dict, List, Tuple

from AlmaGag.config import ICON_WIDTH, ICON_HEIGHT

logger = logging.getLogger('AlmaGag')

_KINDS = ('align', 'near', 'avoid')
NEAR_ALPHA = 0.5      # fracción del acercamiento hacia el centroide
AVOID_MARGIN = 16.0   # holgura al separar (px)


def extract_constraints(data: dict) -> List[dict]:
    """Normaliza el array `constraints` del SDJF. Tolerante: descarta entradas
    inválidas con un warning. Devuelve [{'kind','ids','axis'}]."""
    raw = data.get('constraints')
    if not raw or not isinstance(raw, list):
        return []
    out: List[dict] = []
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        kind = next((k for k in _KINDS if k in entry), None)
        if kind is None:
            logger.warning(f"[CONSTRAINTS] entrada sin tipo válido {list(entry)}; "
                           f"esperado uno de {_KINDS}. Ignorada.")
            continue
        ids = entry.get(kind)
        if not isinstance(ids, list) or len(ids) < 2:
            logger.warning(f"[CONSTRAINTS] '{kind}' requiere ≥2 ids; ignorada.")
            continue
        axis = entry.get('axis', 'x')
        if axis not in ('x', 'y'):
            axis = 'x'
        out.append({'kind': kind, 'ids': list(ids), 'axis': axis})
    return out


def _center(e) -> Tuple[float, float]:
    return (e['x'] + e.get('width', ICON_WIDTH) / 2.0,
            e['y'] + e.get('height', ICON_HEIGHT) / 2.0)


def apply_constraints(layout, constraints: List[dict], debug: bool = False) -> int:
    """Aplica las constraints in-place sobre `layout.elements`. Devuelve cuántas
    se aplicaron. El orden es align → near → avoid (las duras primero)."""
    by_id = layout.elements_by_id
    applied = 0

    def positioned(ids):
        return [by_id[i] for i in ids if i in by_id and 'x' in by_id[i]]

    order = {'align': 0, 'near': 1, 'avoid': 2}
    for c in sorted(constraints, key=lambda c: order[c['kind']]):
        els = positioned(c['ids'])
        if len(els) < 2:
            continue
        if c['kind'] == 'align':
            _apply_align(els, c['axis'])
        elif c['kind'] == 'near':
            _apply_near(els)
        elif c['kind'] == 'avoid':
            _apply_avoid(els)
        applied += 1
        if debug:
            logger.debug(f"[CONSTRAINTS] {c['kind']} {c['ids']} "
                         f"(axis={c['axis']}) aplicada")
    return applied


def _apply_align(els, axis) -> None:
    """Lleva los centros de los elementos a una coordenada común (la media)."""
    centers = [_center(e) for e in els]
    if axis == 'x':
        target = sum(cx for cx, cy in centers) / len(centers)
        for e in els:
            e['x'] = target - e.get('width', ICON_WIDTH) / 2.0
    else:
        target = sum(cy for cx, cy in centers) / len(centers)
        for e in els:
            e['y'] = target - e.get('height', ICON_HEIGHT) / 2.0


def _apply_near(els) -> None:
    """Acerca los elementos hacia el centroide del grupo (fracción NEAR_ALPHA)."""
    centers = [_center(e) for e in els]
    gx = sum(cx for cx, cy in centers) / len(centers)
    gy = sum(cy for cx, cy in centers) / len(centers)
    for e, (cx, cy) in zip(els, centers):
        e['x'] += (gx - cx) * NEAR_ALPHA
        e['y'] += (gy - cy) * NEAR_ALPHA


def _apply_avoid(els) -> None:
    """Separa cada par de elementos solapados por el eje de menor penetración."""
    for i in range(len(els)):
        for j in range(i + 1, len(els)):
            a, b = els[i], els[j]
            aw, ah = a.get('width', ICON_WIDTH), a.get('height', ICON_HEIGHT)
            bw, bh = b.get('width', ICON_WIDTH), b.get('height', ICON_HEIGHT)
            ax, ay = a['x'], a['y']
            bx, by = b['x'], b['y']
            # solape en cada eje
            ox = min(ax + aw, bx + bw) - max(ax, bx)
            oy = min(ay + ah, by + bh) - max(ay, by)
            if ox <= 0 or oy <= 0:
                continue                         # no se solapan
            if ox < oy:                          # separar en X (menor penetración)
                shift = (ox + AVOID_MARGIN) / 2.0
                if ax <= bx:
                    a['x'] -= shift; b['x'] += shift
                else:
                    a['x'] += shift; b['x'] -= shift
            else:                                # separar en Y
                shift = (oy + AVOID_MARGIN) / 2.0
                if ay <= by:
                    a['y'] -= shift; b['y'] += shift
                else:
                    a['y'] += shift; b['y'] -= shift
