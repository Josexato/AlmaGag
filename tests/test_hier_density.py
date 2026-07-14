"""
Tests de §J (densidad y etiquetas) del algoritmo hier.

- J30: paso vertical compacto (icono + holgura fija, sin bandas vacías > icono).
- J31/J32: etiqueta multilínea ≤3 líneas dentro de un ancho máximo.
- J33: los grafos con ramas usan el eje transversal (no una tira 1×N).
"""

import json

from AlmaGag.layout import Layout
from AlmaGag.layout.hier.optimizer import HierLayoutOptimizer, LEVEL_SPACING
from AlmaGag.layout.hier.labels import wrap_label, LABEL_MAX_LINES, LABEL_MAX_WIDTH
from AlmaGag.config import ICON_HEIGHT, ICON_WIDTH, TEXT_CHAR_WIDTH

STRESS = 'docs/diagrams/gags/14-stresstest.sdjf'
ADC = 'docs/diagrams/gags/activacion-datacenter.sdjf'


def _optimize(path):
    d = json.load(open(path))
    L = Layout(elements=d['elements'], connections=d['connections'],
               canvas=d.get('canvas', {'width': 1400, 'height': 900}))
    L._diagram_name = path
    return HierLayoutOptimizer(verbose=False).optimize(L)


# ---- J30 paso compacto ----

def test_pitch_is_compact():
    """§J30: el paso centro-a-centro = icono + holgura fija (~42px), no ~170."""
    air = LEVEL_SPACING - ICON_HEIGHT
    assert 0 < air <= ICON_HEIGHT, f"aire {air} entre niveles debería ser ≤ icono"


def test_no_empty_bands_between_consecutive_levels():
    """§J30: entre niveles enteros consecutivos ocupados no hay banda vacía
    mayor que ~2× el icono."""
    r = _optimize(STRESS)
    ys = sorted({round(e['y']) for e in r.elements if 'y' in e})
    for a, b in zip(ys, ys[1:]):
        assert b - a <= 2 * ICON_HEIGHT + 5, f"banda vacía {b-a}px entre {a} y {b}"


# ---- J31/J32 etiqueta multilínea ----

def test_wrap_label_max_3_lines():
    long = "Solicita creación de Proyecto en SGA al Back Office Corporativo por correo"
    out = wrap_label(long)
    lines = out.split('\n')
    assert len(lines) <= LABEL_MAX_LINES
    cap = int(LABEL_MAX_WIDTH / TEXT_CHAR_WIDTH)
    assert all(len(ln) <= cap for ln in lines), f"línea excede {cap} chars: {lines}"
    assert out.split('\n')[-1].endswith('…')   # §J32 truncado


def test_wrap_label_short_untouched():
    assert wrap_label("i = 2") == "i = 2"
    assert wrap_label("¿Es correcto el precio?").count('\n') <= 1


def test_rendered_labels_within_limits():
    """§J31: toda etiqueta de elemento del diagrama queda en ≤3 líneas y cada
    línea dentro del ancho máximo."""
    r = _optimize(ADC)
    cap = int(LABEL_MAX_WIDTH / TEXT_CHAR_WIDTH)
    for e in r.elements:
        lbl = e.get('label')
        if not lbl:
            continue
        lines = lbl.split('\n')
        assert len(lines) <= LABEL_MAX_LINES, f"{e['id']} tiene {len(lines)} líneas"
        assert all(len(ln) <= cap for ln in lines), f"{e['id']} línea larga: {lines}"


# ---- J33 usar el ancho ----

def test_branched_graph_uses_width():
    """§J33: un grafo con ramas (14-stresstest) reparte los nodos a lo ancho —
    el rango X ocupado supera el 40% del ancho del canvas y la relación
    alto/ancho no es de tira (≤ 3:1)."""
    r = _optimize(STRESS)
    xs = [e['x'] for e in r.elements if 'x' in e]
    used = (max(xs) + ICON_WIDTH) - min(xs)
    assert used > 0.4 * r.canvas['width'], f"ancho usado {used} < 40% de {r.canvas['width']}"
    assert r.canvas['height'] / r.canvas['width'] <= 3.0
