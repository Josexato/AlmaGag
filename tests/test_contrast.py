"""H8 — aviso de contraste bajo en colores de conexión (no bloqueante)."""
from AlmaGag.validation.visual_quality import (
    contrast_vs_white, check_color_contrast)


def test_contrast_ratio_values():
    assert round(contrast_vs_white('#e6a8a3'), 1) == 2.0   # falla (<3)
    assert contrast_vs_white('#b5645e') >= 3.0             # pasa
    assert contrast_vs_white('#ffffff') < 1.1             # blanco s/ blanco


def test_low_contrast_connection_warned():
    data = {'connections': [
        {'from': 'a', 'to': 'b', 'color': '#e6a8a3'},   # 2.0:1 → warn
        {'from': 'a', 'to': 'c', 'color': '#b5645e'},   # 4.2:1 → ok
        {'from': 'a', 'to': 'd'},                         # sin color → ignora
    ]}
    warns = check_color_contrast(data)
    assert len(warns) == 1
    assert warns[0].rule == 'contrast_low'
    assert warns[0].extra['color'] == '#e6a8a3'


def test_sdwan_source_has_adequate_contrast():
    """La fuente SD-WAN ya no usa el respaldo de bajo contraste."""
    import json
    data = json.load(open('docs/diagrams/gags/red-dual-homing.sdjf'))
    assert check_color_contrast(data) == []
