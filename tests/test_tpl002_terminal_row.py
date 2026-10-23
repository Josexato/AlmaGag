"""BUGS-TPL-002 — los terminales del template architecture van en FILA
bajo su padre primario, no en columna única centrada.

La columna apilaba db/cache/response a paso fijo bajo el contenedor
central (cakephp-mvc: aspecto 0.84 con canvas declarado 1.56) y obligaba
a sus aristas a compartir un mismo canal vertical. Ahora: una sola fila
de terminales; cada uno anclado al centro x de su padre primario (el
contenedor del padre, si está contenido); los que colisionan en la fila
se empujan a la derecha. El resto del template (entry/chain/containers/
abstracts) no cambia.
"""

import json
from AlmaGag.layout.templates.architecture import apply_architecture_template


def _mvc():
    return json.load(open('docs/diagrams/gags/cakephp-mvc.gag'))


def test_terminals_share_one_row():
    d = _mvc()
    apply_architecture_template(d)
    by = {e['id']: e for e in d['elements']}
    ys = {by[k]['y'] for k in ('db', 'cache', 'response')}
    assert len(ys) == 1, f'los terminales siguen apilados: {ys}'


def test_terminal_anchors_follow_their_parent():
    """db y cache (hijos de tablas en models_box) quedan bajo el contenedor
    central; response (hijo de template en views_box) bajo el de la derecha
    — y nadie se monta con nadie en la fila."""
    d = _mvc()
    apply_architecture_template(d)
    by = {e['id']: e for e in d['elements']}
    models_cx = by['models_box']['x'] + 140      # centro estimado (280/2)
    views_cx = by['views_box']['x'] + 140
    assert abs((by['db']['x'] + 40) - models_cx) < 160, \
        'db no quedó bajo models_box'
    assert by['response']['x'] + 40 > views_cx - 160, \
        'response no siguió a views_box'
    xs = sorted(by[k]['x'] for k in ('db', 'cache', 'response'))
    for a, b in zip(xs, xs[1:]):
        assert b - a >= 150 - 0.5, f'terminales montados en la fila: {xs}'
