"""BUGS-ARCH-001 — Layout.copy() preserva los atributos de contexto.

El generator/engine cuelgan atributos ad-hoc del layout (considerations,
areas, roles, estrategia…). copy() los perdía todos: cada consumidor debía
acordarse de leer del layout ORIGINAL (contrato implícito que mordió en
§Q65). Ahora hay un registro explícito (CONTEXT_ATTRS) que copy() preserva
por referencia — el contexto es compartido, no clonado: una marca sobre
`_considerations` (p.ej. `_zone_affinity`) debe verse en todas las copias.
"""

from AlmaGag.layout import Layout


def _mk():
    return Layout(elements=[{'id': 'a', 'type': 'server', 'x': 1, 'y': 2}],
                  connections=[], canvas={'width': 100, 'height': 100})


def test_copy_preserves_registered_context():
    L = _mk()
    L._considerations = [{'kind': 'near', 'ids': ['a', 'b']}]
    L._areas = [{'id': 'f1'}]
    L._roles = {'soc': {'label': 'SOC'}}
    L._diagram_name = 'demo'
    L._strategy = 'auto'
    c = L.copy()
    assert c._considerations is L._considerations   # por REFERENCIA
    assert c._areas is L._areas
    assert c._roles is L._roles
    assert c._diagram_name == 'demo'
    assert c._strategy == 'auto'


def test_copy_shares_consideration_marks():
    """Una marca puesta vía la copia se ve desde el original (contexto
    compartido — el caso §Q65)."""
    L = _mk()
    L._considerations = [{'kind': 'near', 'ids': ['a', 'b']}]
    c = L.copy()
    c._considerations[0]['_zone_affinity'] = True
    assert L._considerations[0].get('_zone_affinity') is True


def test_copy_without_context_stays_clean():
    L = _mk()
    c = L.copy()
    for attr in Layout.CONTEXT_ATTRS:
        assert not hasattr(c, attr) or getattr(c, attr) == getattr(L, attr)


def test_elements_still_deep_copied():
    L = _mk()
    c = L.copy()
    c.elements[0]['x'] = 999
    assert L.elements[0]['x'] == 1
