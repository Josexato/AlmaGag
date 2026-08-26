"""Z94 (WISH-LAYOUT-030) — serpenteo intra-celda.

Una cadena dominante (corrida 1-en/1-salida de ≥5 eslabones) dentro de una
celda de partition ANCHA no sale como columna kilométrica: serpentea en
boustrophedon respetando el aspecto de la celda. El orden de lectura queda
intacto (los giros son verticales limpias porque fin de fila e inicio de la
siguiente comparten columna) y los feeders convergen a la cabeza con peine
invertido (AA99 al revés).
"""

from AlmaGag.layout.strategies.hier.areas import (COL_SPACING, _chain_run,
                                                  _sub_layout)
from AlmaGag.config import ICON_WIDTH, ICON_HEIGHT


def _chain(n, prefix='s'):
    members = [{'id': f'{prefix}{i}', 'label': f'Paso {i}'} for i in range(n)]
    conns = [{'from': f'{prefix}{i}', 'to': f'{prefix}{i+1}'}
             for i in range(n - 1)]
    return members, conns


def test_gate_cadena_larga_en_celda_ancha_serpentea():
    """7 eslabones + celda 2:1 → varias filas, y el bbox respeta la celda
    (alto:ancho ≤ 2.5× el alto:ancho de la celda — el Verifica de Z94)."""
    members, conns = _chain(7)
    w, h = _sub_layout(members, conns, aspect_hint=2.0)
    ys = sorted({round(e['y'], 1) for e in members})
    assert len(ys) >= 2, 'la cadena salió en una sola fila/columna'
    assert (h / w) <= 2.5 * (1 / 2.0), \
        f'bbox {w:.0f}x{h:.0f} viola el aspecto de la celda'


def test_giros_verticales_y_orden_de_lectura():
    """Cada eslabón consecutivo: misma fila (tramo horizontal puro) o giro
    vertical en la MISMA columna. Nada diagonal, nada que salte filas."""
    members, conns = _chain(7)
    _sub_layout(members, conns, aspect_hint=2.0)
    by = {e['id']: e for e in members}
    for c in conns:
        s, d = by[c['from']], by[c['to']]
        pts = c['computed_path']['points']
        assert len(pts) == 2, f"{c['from']}→{c['to']}: tramo con codos"
        same_row = abs(s['y'] - d['y']) < 1
        if same_row:
            assert abs(pts[0][1] - pts[1][1]) < 0.6, 'horizontal impuro'
        else:
            assert abs(s['x'] - d['x']) < 1, \
                f"giro {c['from']}→{c['to']} cambia de columna"
            assert abs(pts[0][0] - pts[1][0]) < 0.6, 'vertical impuro'


def test_feeders_en_fila_superior_con_peine_a_la_cabeza():
    """Los alimentadores de la cabeza van arriba y convergen con peine
    invertido: troncal horizontal única + bajada única a la cabeza."""
    members, conns = _chain(6)
    members += [{'id': f'f{i}', 'label': f'Insumo {i}'} for i in range(2)]
    conns += [{'from': f'f{i}', 'to': 's0'} for i in range(2)]
    _sub_layout(members, conns, aspect_hint=2.0)
    by = {e['id']: e for e in members}
    run_top = min(by[f's{i}']['y'] for i in range(6))
    combs = [c for c in conns if c['from'].startswith('f')]
    assert combs and all(by[c['from']]['y'] < run_top for c in combs), \
        'feeders no quedaron en la fila superior'
    trunks = {round(c['computed_path']['points'][1][1], 1) for c in combs}
    drops = {round(c['computed_path']['points'][-1][0], 1) for c in combs}
    assert len(trunks) == 1, 'peine invertido sin troncal única'
    assert len(drops) == 1, 'peine invertido con varias bajadas'
    hx = by['s0']['x'] + ICON_WIDTH / 2
    assert abs(drops.pop() - hx) < 1, 'la bajada no cae en la cabeza'


def test_gate_conservador_no_dispara():
    """Sin celda declarada NO serpentea; una rama interna mata la corrida;
    4 eslabones no llegan al mínimo."""
    members, conns = _chain(7)
    _sub_layout(members, conns, aspect_hint=None)
    xs = {round(e['x'], 1) for e in members}
    assert len(xs) == 1, 'serpenteó sin celda declarada'

    members, conns = _chain(6)
    conns.append({'from': 's2', 'to': 's4'})          # rama interior
    assert _chain_run(members, conns) is None

    members, conns = _chain(4)
    assert _chain_run(members, conns) is None
