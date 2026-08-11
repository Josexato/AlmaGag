"""§O56 — escala tipográfica declarada: nodo 16 · conexión 13 · rótulo 12 bold.

Recalibrada en iteración 9 (caso TM en el visor: letra de ~7px aparentes
al ajustar a pantalla): 14/12/11 → 16/13/12, con TEXT_CHAR_WIDTH y
TEXT_LINE_HEIGHT escalados para que la estimación siga siendo veraz.

El contrato vive en config (FONT_SIZE_NODE/CONNECTION/ZONE) y los tres
niveles se emiten con esos valores; la jerarquía se completa por peso
(rótulos bold) y color (conexiones con color semántico, rótulos apagados).
"""

import xml.etree.ElementTree as ET

from AlmaGag.config import (
    FONT_SIZE_CONNECTION, FONT_SIZE_NODE, FONT_SIZE_ZONE, FONT_WEIGHT_ZONE)
from AlmaGag.generator import generate_diagram

NS = '{http://www.w3.org/2000/svg}'


def test_declared_scale_values():
    assert (FONT_SIZE_NODE, FONT_SIZE_CONNECTION, FONT_SIZE_ZONE) == (16, 13, 12)
    assert FONT_WEIGHT_ZONE == '700'


def _texts(path, out_dir):
    out = out_dir / 'o.svg'
    assert generate_diagram(path, output_file=str(out), layout_algorithm='select')
    root = ET.fromstring(out.read_text(encoding='utf-8'))
    return [t for t in root.iter(f'{NS}text')
            if t.get('class') != 'ag-text-halo']


def test_node_and_connection_sizes(tmp_path):
    texts = _texts('docs/diagrams/gags/03-conexiones.sdjf', tmp_path)
    by_size = {}
    for t in texts:
        by_size.setdefault(t.get('font-size'), []).append(''.join(t.itertext()))
    # nodos (Cliente/Firewall/…) al nivel 14; conexiones (forward…) al 12
    assert any('Cliente' in s for s in by_size.get(f'{FONT_SIZE_NODE}px', []))
    assert any('forward' in s for s in by_size.get(f'{FONT_SIZE_CONNECTION}px', []))


def test_zone_and_grouped_node_labels(tmp_path):
    texts = _texts('docs/diagrams/gags/red-dual-homing-areas.sdjf', tmp_path)
    zone = [t for t in texts if ''.join(t.itertext()) == 'Sede A']
    node = [t for t in texts if ''.join(t.itertext()) == 'Firewall']
    assert zone and node
    assert zone[0].get('font-size') == f'{FONT_SIZE_ZONE}px'
    assert zone[0].get('font-weight') == FONT_WEIGHT_ZONE
    assert node[0].get('font-size') == f'{FONT_SIZE_NODE}px'


def test_near_zone_label_at_zone_level(tmp_path):
    texts = _texts('docs/diagrams/gags/red-minera-antes.gag', tmp_path)
    wan = [t for t in texts if t.get('fill') == '#6b6558']
    assert wan
    assert all(t.get('font-size') == f'{FONT_SIZE_ZONE}px' for t in wan)
    assert all(t.get('font-weight') == FONT_WEIGHT_ZONE for t in wan)


def test_no_font_size_outside_declared_scale(tmp_path):
    """Verifica O56 estricta (observación de la iteración 5): ningún
    font-size fuera de la escala declarada en TODO el SVG emitido, en las cuatro
    clases de emisión (arquitectura, WAN, flowchart, organigrama)."""
    allowed = {f'{FONT_SIZE_NODE}px', f'{FONT_SIZE_CONNECTION}px',
               f'{FONT_SIZE_ZONE}px',
               str(FONT_SIZE_NODE), str(FONT_SIZE_CONNECTION),
               str(FONT_SIZE_ZONE)}
    fixtures = ['05-arquitectura-gag.gag', 'red-minera-antes.gag',
                'es-primo.gag', 'organigrama-empresa.sdjf']
    for fx in fixtures:
        out = tmp_path / (fx + '.svg')
        assert generate_diagram(f'docs/diagrams/gags/{fx}',
                                output_file=str(out),
                                layout_algorithm='select')
        root = ET.fromstring(out.read_text(encoding='utf-8'))
        sizes = {t.get('font-size') for t in root.iter(f'{NS}text')
                 if t.get('font-size')}
        rogue = sizes - allowed
        assert not rogue, f'{fx}: font-size fuera de escala: {rogue}'
