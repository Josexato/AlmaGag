"""Z96 fase 2 (WISH-LAYOUT-030) — la ruta no atraviesa lo que no es suyo.

El post-pass de layout_by_areas desvía travesías COMPLETAS de iconos
ajenos y celdas de área ajenas (además de los contenedores de ARCH-009
v2). La travesía se DETECTA con la caja núcleo (el icono pelado) y se
DESVÍA rodeando la exterior (icono + label, W87): detectar con la
inflada esconde travesías del icono puro, y desviar con la pelada
aterriza el desvío sobre la etiqueta. Entrar a una caja para llegar al
destino NO es atravesar — se respeta.

Medido al implementar: caso real A (scratchpad) arista×nodo 4→0; caso
real B 11→2 (los 2 restantes son codos DENTRO del icono — otra clase,
el desvío de travesías no los ve).
"""

from AlmaGag.layout.strategies.hier.areas import _dodge_boxes


CORE = (100.0, 20.0, 180.0, 80.0)
OUTER = (60.0, 20.0, 220.0, 120.0)


def _inside(p, box):
    return box[0] < p[0] < box[2] and box[1] < p[1] < box[3]


def test_travesia_del_core_se_desvia_rodeando_el_outer():
    pts = _dodge_boxes([(0.0, 50.0), (300.0, 50.0)], [CORE],
                       outers={CORE: OUTER})
    assert len(pts) > 2, 'no desvió la travesía'
    assert not any(_inside(p, CORE) for p in pts), 'el desvío pisa el icono'
    assert not any(_inside(p, OUTER) for p in pts), 'el desvío pisa el label'


def test_endpoint_dentro_del_outer_no_esconde_la_travesia():
    """El segmento cruza el icono ENTERO pero termina sobre la zona del
    label del vecino — con detección por caja inflada esto se escondía
    (no era 'travesía completa' de la inflada). La detección es por el
    núcleo."""
    pts = _dodge_boxes([(0.0, 50.0), (210.0, 50.0)], [CORE],
                       outers={CORE: OUTER})
    assert len(pts) > 2, 'la travesía del icono quedó escondida tras el label'
    assert not any(_inside(p, CORE) for p in pts)


def test_entrar_no_es_atravesar():
    """Un segmento que ENTRA al icono (llega a su puerto/interior) se
    respeta — el desvío es solo para travesías de lado a lado."""
    pts = _dodge_boxes([(0.0, 50.0), (140.0, 50.0)], [CORE],
                       outers={CORE: OUTER})
    assert pts == [(0.0, 50.0), (140.0, 50.0)]


def test_codo_dentro_del_icono_se_recorta_por_la_esquina():
    """Z96 fase 3: el vértice que cae DENTRO de un icono ajeno (invisible
    para el desvío de travesías: nada cruza de lado a lado) se recorta
    rodeando la esquina — tres puntos ortogonales por fuera del borde."""
    from AlmaGag.layout.strategies.hier.areas import _relocate_corners
    box = (100.0, 100.0, 180.0, 150.0)
    # codo en L: horizontal entra por la izquierda, vertical sale por abajo
    pts = _relocate_corners(
        [(0.0, 120.0), (140.0, 120.0), (140.0, 300.0)], [box])
    assert not any(_inside(p, box) for p in pts), 'el codo sigue adentro'
    for a, b in zip(pts, pts[1:]):
        assert abs(a[0] - b[0]) < 0.01 or abs(a[1] - b[1]) < 0.01, \
            f'tramo diagonal {a}->{b}'
    assert pts[0] == (0.0, 120.0) and pts[-1] == (140.0, 300.0), \
        'el recorte movió los extremos'

    # codo con un vecino ADENTRO de la caja: otra clase, no se toca
    pts2 = _relocate_corners(
        [(120.0, 110.0), (140.0, 110.0), (140.0, 300.0)], [box])
    assert pts2 == [(120.0, 110.0), (140.0, 110.0), (140.0, 300.0)]

    # codo fuera de toda caja: intacto
    pts3 = _relocate_corners(
        [(0.0, 50.0), (300.0, 50.0), (300.0, 200.0)], [box])
    assert pts3 == [(0.0, 50.0), (300.0, 50.0), (300.0, 200.0)]
