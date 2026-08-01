"""§O55 — alias de iconos: `inet`/`wan` → cloud; lo demás, BWT visible.

`inet`/`wan`/`internet` cuentan como hub para la topología de red (§N45)
pero draw/icons sólo dibuja `cloud`: sin alias caían al plátano por defecto.
Cualquier tipo realmente desconocido sigue cayendo al BWT VISIBLE y con
WARNING — nunca un fallback silencioso.
"""

import logging

import pytest

from AlmaGag.draw.icons import ICON_TYPE_ALIASES, draw_icon_shape
from AlmaGag.draw.primitives.svg import create_canvas
from AlmaGag.layout.strategies.auto.network import HUB_TYPES

BWT_YELLOW = '#ffff00'      # el amarillo del plátano delata el fallback


def _render_icon(tmp_path, elem_type):
    out = tmp_path / f'{elem_type}.svg'
    dwg = create_canvas(str(out), 200, 150)
    draw_icon_shape(dwg, {'id': 'n1', 'type': elem_type, 'x': 50, 'y': 40})
    return dwg.tostring()


@pytest.mark.parametrize('alias', ['inet', 'wan', 'internet'])
def test_alias_renders_cloud_not_bwt(tmp_path, alias):
    svg = _render_icon(tmp_path, alias)
    assert BWT_YELLOW not in svg, f"'{alias}' cayó al plátano por defecto"
    # la nube son círculos con gradiente; el BWT son paths
    assert '<circle' in svg or '<ellipse' in svg


def test_unknown_type_falls_to_visible_bwt(tmp_path, caplog):
    with caplog.at_level(logging.WARNING, logger='AlmaGag'):
        svg = _render_icon(tmp_path, 'tipo-inexistente')
    assert BWT_YELLOW in svg, 'el BWT debe ser VISIBLE en la lámina'
    text = '\n'.join(r.message for r in caplog.records)
    assert '§O55' in text and 'tipo-inexistente' in text


def test_hub_types_derive_from_aliases():
    """Una sola verdad: ser hub (§N45) y dibujarse como nube van juntos."""
    expected = {'cloud'} | {a for a, t in ICON_TYPE_ALIASES.items()
                            if t == 'cloud'}
    assert HUB_TYPES == expected
    assert {'inet', 'wan', 'internet'} <= HUB_TYPES


def test_embedded_icon_with_alias_name_wins(tmp_path):
    """Un embebido llamado 'inet' se respeta tal cual (prioridad 1)."""
    out = tmp_path / 'emb.svg'
    dwg = create_canvas(str(out), 200, 150)
    marker = '<svg xmlns="http://www.w3.org/2000/svg"><rect width="9" height="9" fill="#123456"/></svg>'
    draw_icon_shape(dwg, {'id': 'n1', 'type': 'inet', 'x': 0, 'y': 0},
                    embedded_icons={'inet': marker})
    svg = dwg.tostring()
    assert '#123456' in svg and BWT_YELLOW not in svg
