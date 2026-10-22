"""WISH-LAYOUT-031 — «jamás una cinta 1×N» también rige con area.role.

c13 (5 bandas de a 1 área) armaba aspecto 0.12: la promesa de la spec
valía solo para el camino sin roles. Si el apilado de bandas viola el
aspecto mínimo, se fusionan bandas ADYACENTES: el orden vertical de la
semántica se vuelve orden de LECTURA dentro de la fila, y ningún role
termina en una fila anterior a la de un role menor.
"""

from AlmaGag.layout.strategies.hier.areas import _macro_rows, _ROLE_BAND
from AlmaGag.layout.metrics import ASPECT_RANGE


def _dim(aid, role, w=220.0, h=180.0):
    return {'aid': aid, 'spec': {'id': aid, 'role': role},
            'members': [], 'conns': [], 'w': w, 'h': h}


def test_cinco_bandas_flacas_se_fusionan_en_orden():
    dims = [_dim('f', 'feeder'), _dim('c', 'chain'), _dim('h', 'hub'),
            _dim('e', 'external'), _dim('o', 'overlay')]
    rows = _macro_rows(dims)
    assert len(rows) < 5, 'sigue siendo la cinta de 5 filas'
    # aspecto estimado dentro del mínimo
    import itertools
    w = max(sum(d['w'] for d in r) for r in rows)
    hh = sum(max(d['h'] for d in r) for r in rows)
    assert w / hh >= ASPECT_RANGE[0]
    # el orden semántico no se invierte: banda menor nunca en fila mayor
    fila = {d['aid']: i for i, r in enumerate(rows) for d in r}
    banda = {d['aid']: _ROLE_BAND[d['spec']['role']] for d in dims}
    for a, b in itertools.combinations(dims, 2):
        ba, bb = banda[a['aid']], banda[b['aid']]
        if ba < bb:
            assert fila[a['aid']] <= fila[b['aid']], \
                f"{a['aid']} (banda {ba}) quedó debajo de {b['aid']} ({bb})"


def test_bandas_sanas_quedan_intactas():
    """Tres bandas anchas que ya respetan el aspecto: ni se tocan."""
    dims = [_dim('f', 'feeder', w=900), _dim('c', 'chain', w=900),
            _dim('e', 'external', w=900)]
    rows = _macro_rows(dims)
    assert len(rows) == 3, 'fusionó bandas que no violaban el aspecto'
