"""§O58 — exportar PNG sin navegador: Chrome si está, cairosvg si no.

`--exportpng` ya existía pero sólo buscaba Chrome en rutas de Windows; ahora
`convert_svg_to_png` localiza Chrome/Chromium/Edge en cualquier plataforma y,
si no hay ninguno, rasteriza con cairosvg (fiable desde §O50). Con eso los
PNG de revisión se pueden regenerar desde CI.
"""

import io

import pytest

from AlmaGag import debug as ag_debug
from AlmaGag.generator import generate_diagram


@pytest.fixture(scope='module')
def svg(tmp_path_factory):
    out = tmp_path_factory.mktemp('o58') / 'diagrama.svg'
    assert generate_diagram('docs/diagrams/gags/03-conexiones.sdjf',
                            output_file=str(out), layout_algorithm='select')
    return out


def _assert_png_with_dark_text(png_path):
    from PIL import Image
    img = Image.open(png_path).convert('L')
    assert img.width > 100 and img.height > 100
    dark = sum(1 for p in img.get_flattened_data() if p < 100)
    assert dark > 100, 'PNG sin contenido oscuro (¿etiquetas perdidas?)'


def test_fallback_cairosvg_without_chrome(svg, tmp_path, monkeypatch):
    """Sin ningún Chrome disponible, cairosvg genera el PNG igual."""
    pytest.importorskip('cairosvg')
    monkeypatch.setattr(ag_debug, '_find_chrome_executable', lambda: None)
    png = tmp_path / 'via-cairo.png'
    result = ag_debug.convert_svg_to_png(str(svg), png_path=str(png))
    assert result == str(png)
    _assert_png_with_dark_text(png)


def test_chrome_used_when_available(svg, tmp_path):
    """Con Chromium presente (este entorno lo tiene), la vía Chrome funciona."""
    chrome = ag_debug._find_chrome_executable()
    if not chrome:
        pytest.skip('sin Chrome/Chromium en este entorno')
    png = tmp_path / 'via-chrome.png'
    result = ag_debug.convert_svg_to_png(str(svg), scale=1.0, png_path=str(png))
    assert result == str(png)
    _assert_png_with_dark_text(png)


def test_no_backend_returns_none(svg, tmp_path, monkeypatch, caplog):
    """Sin Chrome NI cairosvg: aviso claro y retorno None, sin explotar."""
    import builtins
    monkeypatch.setattr(ag_debug, '_find_chrome_executable', lambda: None)
    real_import = builtins.__import__

    def no_cairosvg(name, *a, **kw):
        if name == 'cairosvg':
            raise ImportError('simulado')
        return real_import(name, *a, **kw)

    monkeypatch.setattr(builtins, '__import__', no_cairosvg)
    png = tmp_path / 'nunca.png'
    assert ag_debug.convert_svg_to_png(str(svg), png_path=str(png)) is None
    assert not png.exists()


def test_default_output_in_debug_outputs(svg, tmp_path, monkeypatch):
    """Sin png_path explícito, el PNG cae en debug/outputs/<nombre>.png."""
    pytest.importorskip('cairosvg')
    monkeypatch.setattr(ag_debug, '_find_chrome_executable', lambda: None)
    monkeypatch.chdir(tmp_path)
    result = ag_debug.convert_svg_to_png(str(svg))
    assert result == str(tmp_path / 'debug' / 'outputs' / 'diagrama.png')
