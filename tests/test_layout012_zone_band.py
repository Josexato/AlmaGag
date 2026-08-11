"""BUGS-LAYOUT-012 — banda de zona: techos alineados, no centrado vertical.

Hallazgo del GAG Skiller (reporte 2): las cajas de zona se centraban
verticalmente en la banda §P60, así que dos zonas hermanas de alto
distinto dejaban sus techos — y por tanto sus PRIMERAS FILAS — desfasados
(9px medidos con cajas de 269 y 287). La semántica correcta es que los
miembros equivalentes de zonas hermanas caigan en la misma fila absoluta:
las zonas operativas se alinean al TECHO de la banda por construcción.
"""

import json

import pytest

from AlmaGag.generator import select_strategy
from AlmaGag.layout import Layout
from AlmaGag.layout.engine import LayoutEngine

FIXTURE = 'docs/diagrams/gags/mina-arquitectura-fisica.sdjf'
OPERATIONAL = {'z_mina', 'z_pila'}


def _optimize(d):
    L = Layout(elements=d['elements'], connections=d['connections'],
               canvas={'width': 1400, 'height': 900})
    L._strategy = select_strategy(d, 'auto')
    return LayoutEngine(verbose=False, strategy=None).optimize(L)


def test_sibling_zone_roofs_share_row_in_fixture():
    """mina-arquitectura-fisica: z_mina y z_pila tienen alturas distintas
    y aun así sus techos coinciden (≤0.5px)."""
    d = json.load(open(FIXTURE))
    out = _optimize(d)
    by = out.elements_by_id
    tops = {z: by[z]['y'] for z in OPERATIONAL}
    heights = {z: by[z].get('height', 0) for z in OPERATIONAL}
    assert max(tops.values()) - min(tops.values()) <= 0.5, \
        f'techos de zonas hermanas desfasados: {tops} (alturas {heights})'


def test_uneven_zones_align_roofs_and_periphery_clears_band():
    """Sintético: zona de 4 miembros (alta) junto a zona de 2 (baja) —
    techos iguales; la zona de servicio cae ENTERA bajo la banda (usa
    band_h, el alto real de la banda, para situar la periferia)."""
    d = {'elements': [
            {'id': 'za', 'type': 'area', 'label': 'ZONA A',
             'contains': [{'id': i, 'scope': 'full'}
                          for i in ['a1', 'a2', 'a3', 'a4']]},
            {'id': 'zb', 'type': 'area', 'label': 'ZONA B',
             'contains': [{'id': i, 'scope': 'full'} for i in ['b1', 'b2']]},
            {'id': 'zs', 'type': 'area', 'label': 'SERVICIO',
             'contains': [{'id': 's1', 'scope': 'full'}]},
            {'id': 'a1', 'type': 'router', 'label': 'A1'},
            {'id': 'a2', 'type': 'server', 'label': 'A2'},
            {'id': 'a3', 'type': 'server', 'label': 'A3'},
            {'id': 'a4', 'type': 'server', 'label': 'A4'},
            {'id': 'b1', 'type': 'router', 'label': 'B1'},
            {'id': 'b2', 'type': 'server', 'label': 'B2'},
            {'id': 's1', 'type': 'user', 'label': 'S1'}],
         'connections': [
            {'from': 'a1', 'to': 'a2'}, {'from': 'a1', 'to': 'a3'},
            {'from': 'a1', 'to': 'a4'}, {'from': 'b1', 'to': 'b2'},
            {'from': 'a1', 'to': 'b1', 'direction': 'bidirectional',
             'label': 'troncal'},
            {'from': 's1', 'to': 'a1', 'direction': 'forward',
             'label': 'gestion'}]}
    out = _optimize(d)
    by = out.elements_by_id
    ya, yb = by['za']['y'], by['zb']['y']
    ha = by['za'].get('height', 0)
    hb = by['zb'].get('height', 0)
    assert abs(ha - hb) > 5, 'el sintético debe tener zonas de alto distinto'
    assert abs(ya - yb) <= 0.5, \
        f'techos desfasados: za={ya} (h={ha}) vs zb={yb} (h={hb})'
    band_bottom = max(ya + ha, yb + hb)
    assert by['zs']['y'] > band_bottom, \
        'la zona de servicio no quedó bajo la banda completa'
