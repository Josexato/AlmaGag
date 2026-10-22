"""BUGS-LOG-004 — icono×icono entra al audit (PY-005b de almagag-jv).

Dos iconos montados EXACTOS (c21: bd y cache en la misma posición)
reportaban labels=0 y ningún contador lo decía — la lámina mentía
«limpia». El contador es la cifra oficial (doctrina BUGS-VAL-008):
el canal icono×icono suma a la línea [motor] y dispara el WARNING.
"""

from AlmaGag.layout import Layout
from AlmaGag.layout.metrics import quality_counters


def test_dos_iconos_montados_se_cuentan():
    L = Layout(
        elements=[{'id': 'a', 'label': 'A', 'x': 100, 'y': 50},
                  {'id': 'b', 'label': 'B', 'x': 100, 'y': 50},
                  {'id': 'c', 'label': 'C', 'x': 400, 'y': 50}],
        connections=[],
        canvas={'width': 600, 'height': 300})
    q = quality_counters(L)
    assert q['icon_x_icon'] >= 1, \
        'dos iconos en la posición exacta siguen invisibles al audit'


def test_iconos_separados_no_suman():
    L = Layout(
        elements=[{'id': 'a', 'label': 'A', 'x': 100, 'y': 50},
                  {'id': 'b', 'label': 'B', 'x': 400, 'y': 50}],
        connections=[],
        canvas={'width': 600, 'height': 300})
    assert quality_counters(L)['icon_x_icon'] == 0
