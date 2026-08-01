"""§O52 — densidad de tinta y aspecto en la línea de métricas del motor.

La línea `[motor] cruces=… arista×nodo=… labels=…` se extiende con
`tinta=X% aspecto=Y`; WARNING con tinta<4% o aspecto fuera de [0.4, 3.0].
"""

import logging
import re

from AlmaGag.layout import Layout
from AlmaGag.layout.metrics import ASPECT_RANGE, INK_WARN_PCT, emission_metrics
from AlmaGag.generator import generate_diagram


def _layout(elements, canvas=(1400, 900)):
    return Layout(elements=elements, connections=[],
                  canvas={'width': canvas[0], 'height': canvas[1]})


def test_dense_layout_metrics():
    """4 iconos compactos: lámina ≈ bbox+80 → tinta alta, aspecto ~1."""
    els = [{'id': f'e{i}', 'x': 100 + (i % 2) * 120, 'y': 100 + (i // 2) * 90,
            'width': 80, 'height': 50} for i in range(4)]
    em = emission_metrics(_layout(els))
    assert em['ink_pct'] >= INK_WARN_PCT
    assert ASPECT_RANGE[0] <= em['aspect'] <= ASPECT_RANGE[1]


def test_sparse_layout_low_ink():
    """2 iconos chicos en un canvas enorme sin recorte posible → tinta <4%."""
    els = [{'id': 'a', 'x': 0, 'y': 0, 'width': 40, 'height': 30},
           {'id': 'b', 'x': 1300, 'y': 850, 'width': 40, 'height': 30}]
    em = emission_metrics(_layout(els))
    assert em['ink_pct'] < INK_WARN_PCT


def test_ribbon_aspect_out_of_range():
    """Cadena horizontal larga → aspecto > 3.0 (lámina cinta)."""
    els = [{'id': f'e{i}', 'x': i * 200, 'y': 100, 'width': 80, 'height': 50}
           for i in range(10)]
    em = emission_metrics(_layout(els, canvas=(2200, 260)))
    assert em['aspect'] > ASPECT_RANGE[1]


def test_labels_count_as_ink():
    """Con la lámina fija (la etiqueta cae dentro del bbox), la etiqueta
    suma tinta."""
    els_sin = [{'id': 'a', 'x': 0, 'y': 0, 'width': 80, 'height': 50},
               {'id': 'b', 'x': 400, 'y': 300, 'width': 80, 'height': 50}]
    els_con = [dict(els_sin[0], label='AB'), els_sin[1]]
    assert (emission_metrics(_layout(els_con))['ink_pct']
            > emission_metrics(_layout(els_sin))['ink_pct'])


def test_motor_line_includes_ink_and_aspect(caplog, tmp_path):
    """La línea [motor] emitida por generate_diagram trae tinta= y aspecto=."""
    with caplog.at_level(logging.INFO, logger='AlmaGag'):
        generate_diagram('docs/diagrams/gags/03-conexiones.sdjf',
                         output_file=str(tmp_path / 'o.svg'),
                         layout_algorithm='select')
    text = '\n'.join(r.message for r in caplog.records)
    m = re.search(r'\[\w+\] cruces\(arista×arista\)=\d+ arista×nodo=\d+ '
                  r'labels=\d+ tinta=[\d.]+% aspecto=[\d.]+', text)
    assert m, f'línea de métricas sin tinta/aspecto: {text}'
