"""
Test del estilo de línea de conexión (`style: dashed|dotted`) — enlaces de
respaldo/secundarios en topologías de red.
"""

import os
import tempfile

from AlmaGag.draw.primitives.connections import _dash_for


def test_dash_for_styles():
    assert _dash_for({}) is None
    assert _dash_for({'style': 'solid'}) is None
    assert _dash_for({'style': 'dashed'}) == '7,5'
    assert _dash_for({'style': 'dotted'}) == '2,4'
    assert _dash_for({'line_style': 'dashed'}) == '7,5'   # alias


def test_dashed_connection_renders_dasharray():
    """Una conexión con style:dashed emite stroke-dasharray; una sólida no."""
    from AlmaGag.generator import generate_diagram
    tmp = tempfile.NamedTemporaryFile(suffix='.svg', delete=False)
    tmp.close()
    ok = generate_diagram('docs/diagrams/gags/red-dual-homing.sdjf', output_file=tmp.name)
    assert ok
    svg = open(tmp.name).read()
    os.unlink(tmp.name)
    assert 'stroke-dasharray' in svg, "los enlaces de respaldo deberían ser punteados"
