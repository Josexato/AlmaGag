"""
Consideraciones de layout — align / near / avoid (rescate ④ desde LAF, revisado).

Son **blandas** (de ahí el nombre): expresan intención del usuario, no una ley.
Cada una se aplica **sólo si no destruye la diagramación** — si al aplicarla
aumentan las colisiones, se revierte y se informa en los logs que no se pudo
cumplir (sin explicar el porqué). Así una consideración nunca degrada el diagrama.

Esto las diferencia de una *restricción dura* (que se impone aunque rompa el
resto). El motor (AUTO) las corre detrás de una guarda, igual que la
compactación ① .

Schema (array top-level `considerations`; alias legacy `constraints`):

    "considerations": [
      {"align": ["a", "b", "c"], "axis": "x"},   # misma columna (X común)
      {"align": ["d", "e"], "axis": "y"},         # misma fila (Y común)
      {"near":  ["app", "db"]},                    # acercar (reduce dispersión)
      {"avoid": ["front", "back"]}                 # no solapar (separa el par)
    ]

- `align`: lleva los elementos a una X (axis 'x', default) o Y ('y') común.
- `near`: acerca a los miembros hacia su centroide sin encimarlos.
- `avoid`: si dos elementos se solapan, los separa por el eje de menor penetración.

`extract_considerations` normaliza el schema; `apply_one` aplica UNA consideración
(geometría pura); `apply_considerations` es el driver GUARDADO que decide cuáles
se conservan. Sin `considerations`, todo es no-op (cero regresión).
"""

import logging
from typing import Callable, List, Tuple

from AlmaGag.config import ICON_WIDTH, ICON_HEIGHT

logger = logging.getLogger('AlmaGag')

_KINDS = ('align', 'near', 'avoid')
NEAR_ALPHA = 0.5      # fracción del acercamiento hacia el centroide
AVOID_MARGIN = 16.0   # holgura al separar (px)


def extract_considerations(data: dict) -> List[dict]:
    """Normaliza el array `considerations` (o su alias legacy `constraints`) del
    SDJF. Tolerante: descarta entradas inválidas con un warning. Devuelve
    [{'kind','ids','axis'}]."""
    raw = data.get('considerations')
    if raw is None:
        raw = data.get('constraints')      # alias retrocompatible
    if not raw or not isinstance(raw, list):
        return []
    out: List[dict] = []
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        kind = next((k for k in _KINDS if k in entry), None)
        if kind is None:
            logger.warning(f"[CONSIDERACIONES] entrada sin tipo válido {list(entry)}; "
                           f"esperado uno de {_KINDS}. Ignorada.")
            continue
        ids = entry.get(kind)
        if not isinstance(ids, list) or len(ids) < 2:
            logger.warning(f"[CONSIDERACIONES] '{kind}' requiere ≥2 ids; ignorada.")
            continue
        axis = entry.get('axis', 'x')
        if axis not in ('x', 'y'):
            axis = 'x'
        out.append({'kind': kind, 'ids': list(ids), 'axis': axis})
    return out


def label(cons: dict) -> str:
    """Etiqueta corta de una consideración para logs: `align [a, b, c]`."""
    return f"{cons['kind']} {cons['ids']}"


def _center(e) -> Tuple[float, float]:
    return (e['x'] + e.get('width', ICON_WIDTH) / 2.0,
            e['y'] + e.get('height', ICON_HEIGHT) / 2.0)


def apply_one(layout, cons: dict) -> None:
    """Aplica UNA consideración in-place sobre `layout.elements` (geometría pura,
    sin guarda). El caller decide si conserva el resultado."""
    by_id = layout.elements_by_id
    els = [by_id[i] for i in cons['ids'] if i in by_id and 'x' in by_id[i]]
    if len(els) < 2:
        return
    if cons['kind'] == 'align':
        _apply_align(els, cons['axis'])
    elif cons['kind'] == 'near':
        _apply_near(els)
    elif cons['kind'] == 'avoid':
        _apply_avoid(els)


def apply_considerations(
    layout,
    considerations: List[dict],
    evaluate: Callable[[object], int],
    reroute: Callable[[object], None],
) -> Tuple[object, List[dict]]:
    """Driver GUARDADO: aplica cada consideración sólo si no aumenta las
    colisiones. Devuelve (layout_resultante, no_aplicadas).

    Para cada consideración prueba sobre una copia (aplicar → re-rutear →
    evaluar); la conserva si las colisiones no suben respecto a la mejor hasta
    ahora, si no la descarta. `evaluate(layout)` devuelve el nº de colisiones y
    lo cachea; `reroute(layout)` recalcula los paths."""
    current = layout
    base = evaluate(current)
    unmet: List[dict] = []
    for cons in considerations:
        trial = current.copy()
        apply_one(trial, cons)
        trial.invalidate_collision_cache()
        reroute(trial)
        score = evaluate(trial)
        if score <= base:
            current, base = trial, score
        else:
            unmet.append(cons)
    return current, unmet


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
