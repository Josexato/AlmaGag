"""BUGS-ROUTE-012 — el desvío elige el lado del VIAJE.

Rodear por el lado geométricamente «cercano» cuando el destino queda
del otro costado dibuja una C (ida, rodeo y vuelta): template→response
rodeaba a cell por la izquierda con response a la derecha (problema 5
del segundo reporte GAG-WV — verificado). Ahora, si el destino de la
polilínea cae claramente a un lado de la caja, el desvío va por ese
lado; si cae en su franja, decide el cercano (comportamiento
histórico, congelado como fallback). Guarda sin UN número movido y
SVGs hier byte-idénticos (c21, c19, c15 verificados con cmp).
"""

from AlmaGag.layout.dodge import dodge_boxes


def test_detour_follows_the_destination_side():
    """Vertical que cruza una caja descentrada: el lado cercano es el
    izquierdo (40px vs 24px... invertido: aquí 24 vs 40), pero el destino
    final está a la DERECHA — el desvío va por la derecha."""
    # caja con el tramo más cerca del borde izquierdo (cercano = izquierda)
    pts = [(100.0, 0.0), (100.0, 200.0), (300.0, 200.0), (300.0, 300.0)]
    box = (90.0, 60.0, 180.0, 140.0)       # x=100: izq 10px, der 80px
    out = dodge_boxes(list(pts), [box])
    xs = [p[0] for p in out]
    assert max(xs[:-2]) > 180.0, f'no rodeó por el lado del destino: {out}'
    assert min(xs) >= 90.0 - 13.0, out     # y jamás por la izquierda


def test_fallback_nearest_when_dest_in_span():
    """Destino dentro de la franja x de la caja: decide el cercano (el
    contrato histórico no cambia)."""
    pts = [(100.0, 0.0), (100.0, 200.0)]
    box = (90.0, 60.0, 180.0, 140.0)       # destino x=100 ∈ [90,180]
    out = dodge_boxes(list(pts), [box])
    assert min(p[0] for p in out) < 90.0, \
        f'el fallback cercano (izquierda, 10px) se perdió: {out}'
