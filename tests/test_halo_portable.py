"""§O50 — halo de texto portable (geometría SVG 1.1, nunca `paint-order`).

El halo por `paint-order:stroke` era SVG2/navegador-only: cairosvg y librsvg
pintan el trazo ENCIMA del relleno y las etiquetas desaparecen al rasterizar.
El invariante nuevo: cada <text> emitido lleva debajo, en el mismo padre, una
copia con trazo blanco; el documento no depende de `paint-order`.
"""

import xml.etree.ElementTree as ET

import pytest

from AlmaGag.draw.primitives.svg import (
    TEXT_HALO_ATTRS, create_canvas, inject_text_halos)
from AlmaGag.generator import generate_diagram

SVG_NS = 'http://www.w3.org/2000/svg'
TEXT = f'{{{SVG_NS}}}text'


def _render_fixture(tmp_path):
    out = tmp_path / 'halo.svg'
    generate_diagram('docs/diagrams/gags/03-conexiones.sdjf',
                     output_file=str(out), layout_algorithm='select')
    return out.read_text(encoding='utf-8')


def test_no_paint_order_in_emitted_svg(tmp_path):
    assert 'paint-order' not in _render_fixture(tmp_path)


def test_every_text_has_halo_twin_below(tmp_path):
    """Cada <text> visible va precedido por su gemelo con trazo blanco."""
    root = ET.fromstring(_render_fixture(tmp_path))
    halos = originals = 0
    for parent in root.iter():
        children = list(parent)
        for i, child in enumerate(children):
            if child.tag != TEXT:
                continue
            if child.get('stroke') == TEXT_HALO_ATTRS['stroke']:
                halos += 1
                continue
            originals += 1
            assert i > 0 and children[i - 1].tag == TEXT, \
                f'<text> sin gemelo de halo: {ET.tostring(child)[:120]}'
            twin = children[i - 1]
            for k, v in TEXT_HALO_ATTRS.items():
                assert twin.get(k) == v
            assert list(twin.itertext()) == list(child.itertext())
    assert originals > 0 and halos == originals


def test_halo_preserves_stacking_and_content():
    """El halo se inserta en el mismo padre, justo antes del original."""
    src = (f'<svg xmlns="{SVG_NS}"><rect/>'
           '<g id="grp"><text x="1" y="2" fill="#14181d">Hola</text></g>'
           '<text>Chau</text></svg>')
    root = ET.fromstring(inject_text_halos(src))
    grp = root.find(f'{{{SVG_NS}}}g')
    assert [c.tag for c in grp] == [TEXT, TEXT]
    assert grp[0].get('stroke') == '#ffffff'
    assert grp[0].get('fill') == '#ffffff'
    assert grp[1].get('fill') == '#14181d'   # el original no se toca
    assert grp[0].text == grp[1].text == 'Hola'
    # los <text> de primer nivel también reciben gemelo
    top_texts = [c for c in root if c.tag == TEXT]
    assert len(top_texts) == 2


def test_defs_content_not_duplicated():
    src = (f'<svg xmlns="{SVG_NS}"><defs><text>plantilla</text></defs>'
           '<text>real</text></svg>')
    root = ET.fromstring(inject_text_halos(src))
    defs = root.find(f'{{{SVG_NS}}}defs')
    assert len(list(defs)) == 1          # dentro de <defs> no se inyecta
    assert len([c for c in root if c.tag == TEXT]) == 2


def test_cairosvg_rasterizes_legible_text(tmp_path):
    """Verificación O50: rasterizar con cairosvg SIN parche deja glifos oscuros.

    Con el halo `paint-order` viejo, cairosvg cubría el relleno con el trazo
    blanco y un canvas con sólo texto quedaba sin píxeles oscuros.
    """
    cairosvg = pytest.importorskip('cairosvg')
    from PIL import Image
    import io

    out = tmp_path / 'solo-texto.svg'
    dwg = create_canvas(str(out), 200, 60)
    dwg.add(dwg.rect(insert=(0, 0), size=(200, 60), fill='#ffffff'))
    dwg.add(dwg.text('Etiqueta', insert=(20, 35), font_size='16px',
                     font_family='Arial, sans-serif', fill='#14181d'))
    dwg.save()

    png = cairosvg.svg2png(url=str(out))
    img = Image.open(io.BytesIO(png)).convert('L')
    dark = sum(1 for p in img.get_flattened_data() if p < 100)
    assert dark > 50, 'las etiquetas se pierden al rasterizar con cairosvg'
