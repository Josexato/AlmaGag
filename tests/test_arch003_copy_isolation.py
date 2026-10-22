"""BUGS-ARCH-003 — Layout.copy(): mutar una copia jamás toca otra escena.

La copia superficial de la lista de conexiones compartía los DICTS:
los routers escriben computed_path/puertos/marcas dentro de ellos, así
que rutear un candidato del optimizer podía pisar el trazado de otro
(o del ganador) sin dejar huella. Hallazgo de la fase 0 de almagag-jv,
confirmado ejecutando; el hack _family_joint de it15 era este aliasing
usado a favor (sigue funcionando: deepcopy conserva los valores, ya
sin compartir identidad).
"""

from AlmaGag.layout import Layout


def _mk():
    return Layout(
        elements=[{'id': 'a', 'label': 'A'}, {'id': 'b', 'label': 'B'}],
        connections=[{'from': 'a', 'to': 'b', 'label': 'x',
                      'computed_path': {'type': 'polyline',
                                        'points': [(0, 0), (10, 0)]}}],
        canvas={'width': 400, 'height': 300})


def test_mutar_la_copia_no_toca_el_original():
    L = _mk()
    C = L.copy()
    C.connections[0]['computed_path'] = {'type': 'polyline',
                                         'points': [(9, 9)]}
    C.connections[0]['_marca'] = 'candidato'
    C.connections[0]['computed_path']['points'].append((1, 1))
    assert L.connections[0]['computed_path']['points'] == [(0, 0), (10, 0)]
    assert '_marca' not in L.connections[0]


def test_mutar_lo_anidado_de_la_copia_tampoco():
    """El caso fino: mutar DENTRO del computed_path compartido (sin
    reasignar el dict) era el aliasing que nadie veía."""
    L = _mk()
    C = L.copy()
    C.connections[0]['computed_path']['points'].append((99, 99))
    assert (99, 99) not in L.connections[0]['computed_path']['points']


def test_las_marcas_del_original_llegan_a_la_copia():
    """deepcopy conserva los VALORES: una marca previa (p.ej.
    _family_joint) viaja a la copia — lo que muere es la identidad
    compartida, no la herencia."""
    L = _mk()
    L.connections[0]['_family_joint'] = 'T'
    C = L.copy()
    assert C.connections[0]['_family_joint'] == 'T'
    C.connections[0]['_family_joint'] = 'comb'
    assert L.connections[0]['_family_joint'] == 'T'
