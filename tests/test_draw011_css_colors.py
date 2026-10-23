"""BUGS-DRAW-011 — named colors CSS completos y fallback NOMBRADO.

CSS_COLORS tenía 19 nombres: todo lo demás (wheat, plum, …) caía EN
SILENCIO al gris #808080 — el SVG nativo entiende los 148 named colors,
pero el gradiente de iconos/contenedores calcula claro/oscuro desde RGB
y ahí se perdía el color del autor (doble violación O55, «fallo crítico
4» del reporte externo sobre cakephp-mvc — verificado en el gradiente:
models_box arrancaba en #a6a6a6 en vez de wheat).
"""

import logging
from AlmaGag.draw.icons import CSS_COLORS, color_to_rgb


def test_standard_named_colors_resolve():
    """Los nombres del caso real y una muestra del estándar resuelven a
    su RGB, no al gris de fallback."""
    assert color_to_rgb('wheat') == (0xF5, 0xDE, 0xB3)
    assert color_to_rgb('plum') == (0xDD, 0xA0, 0xDD)
    assert color_to_rgb('REBECCAPURPLE') == (0x66, 0x33, 0x99)
    assert len(CSS_COLORS) >= 148, len(CSS_COLORS)


def test_unknown_color_warns_once(caplog):
    """Un color inexistente cae al gris PERO nombrado (O55), y el aviso
    no se repite por cada icono que lo use."""
    with caplog.at_level(logging.WARNING, logger='AlmaGag'):
        assert color_to_rgb('colorinventado') == (0x80, 0x80, 0x80)
        color_to_rgb('colorinventado')
    hits = [r for r in caplog.records if 'colorinventado' in r.message]
    assert len(hits) == 1, [r.message for r in hits]
    assert '§O55' in hits[0].message
