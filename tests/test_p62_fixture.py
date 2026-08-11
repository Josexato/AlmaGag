"""§P62 — higiene de los fixtures del caso real (arquitectura física minera).

El caso real se promovió a fixtures ANONIMIZADOS: empresas/proyecto/
ubicaciones/proveedores reemplazados por genéricos (cliente ficticio MinaCo,
proyecto CobreSur) conservando estructura, tipos, semántica de conexiones y
longitudes de label (±10%) para que las colisiones se reproduzcan tal cual.

Archivos vigilados:
- mina-arquitectura-fisica.sdjf — el físico ORIGINAL (37/26, grupo P).
- mina-fisico-v2.gag — el físico EVOLUCIONADO (25/19, 5 zonas, 3-ago).
- mina-hld.gag — el HLD adoptado (26/20, 4 contenedores, iconos del skill).
- mina-presupuesto.sdjf — la estructura del formato de presupuesto
  (23/19, grupo V, 10-ago; el hack f4 del original se eliminó porque el
  contrato U74/U77 lo caza como error).
"""

import json
import re

from AlmaGag.generator import generate_diagram

FIXTURES = [
    'docs/diagrams/gags/mina-arquitectura-fisica.sdjf',
    'docs/diagrams/gags/mina-fisico-v2.gag',
    'docs/diagrams/gags/mina-hld.gag',
    'docs/diagrams/gags/mina-presupuesto.sdjf',
]

# Términos sensibles del caso real: si cualquiera reaparece, el test truena.
# La comparación es CASE-INSENSITIVE («LA TAPADA» también es fuga).
LEAKS = ['tia maria', 'tiamaria', 'tapada', 'cachendo', 'spcc', 'huawei',
         'claroty', 'cicsa', 'cocachacra', 'mollendo', 'ticar', 'ly-304',
         'teldat', 'hicare', 'kite', 'imaster', 'neteco', 'netengine',
         'easymacro', 'tm4']

import pytest


@pytest.mark.parametrize('fixture', FIXTURES)
def test_fixture_is_anonymized(fixture):
    t = open(fixture, encoding='utf-8').read().lower()
    for leak in LEAKS:
        assert leak not in t, f'{fixture} contiene dato real: {leak}'
    assert not re.search(r'\bilo\b', t), f'{fixture} contiene dato real: Ilo'


def test_fixture_structure_preserved():
    """La anonimización no tocó la estructura que el grupo P necesita:
    5 áreas, contención anidada (área→edificio→equipos), 26 conexiones."""
    d = json.load(open(FIXTURES[0]))
    areas = [e for e in d['elements'] if e.get('type') == 'area']
    assert len(areas) == 5
    assert len(d['elements']) == 37
    assert len(d['connections']) == 26
    contains = {e['id']: [i['id'] for i in e['contains']]
                for e in d['elements'] if 'contains' in e}
    assert 'dc_mina' in contains['z_mina']          # anidación nivel 2
    assert set(contains['dc_mina']) == {'core_p', 'nms'}
    # sin posiciones fijas: todo el layout es derivado (evaluación del revisor)
    assert not any('x' in e or 'y' in e for e in d['elements'])


def test_v2_fixtures_structure():
    """Los fixtures evolucionados (3-ago) conservan la estructura real:
    físico v2 = 25/19 con 5 zonas; HLD = 26/20 con 4 contenedores, todo
    sin coordenadas (layout 100% derivado)."""
    f = json.load(open('docs/diagrams/gags/mina-fisico-v2.gag'))
    assert len(f['elements']) == 25 and len(f['connections']) == 19
    assert sum(1 for e in f['elements'] if e.get('type') == 'area') == 5
    h = json.load(open('docs/diagrams/gags/mina-hld.gag'))
    assert len(h['elements']) == 26 and len(h['connections']) == 20
    assert sum(1 for e in h['elements'] if 'contains' in e) == 4
    for d in (f, h):
        assert not any('x' in e or 'y' in e for e in d['elements'])


def test_presupuesto_structure():
    """El fixture del grupo V conserva la estructura real: 23 elementos /
    19 conexiones, 5 align[] declarados (4 en y, 1 en x), 3 journeys válidos
    (el hack f4 no viaja: U74/U77 lo caza), 1 contenedor-feeder, y cero
    coordenadas (layout 100% derivado)."""
    d = json.load(open('docs/diagrams/gags/mina-presupuesto.sdjf'))
    assert len(d['elements']) == 23 and len(d['connections']) == 19
    aligns = [c for c in d['considerations'] if 'align' in c]
    assert len(aligns) == 5
    assert sum(1 for a in aligns if a['axis'] == 'x') == 1
    assert len(d['journeys']) == 3
    assert all(f.get('label') for f in d['journeys'])
    contains = [e for e in d['elements'] if 'contains' in e]
    assert len(contains) == 1 and contains[0]['id'] == 'indir'
    assert not any('x' in e or 'y' in e for e in d['elements'])


@pytest.mark.parametrize('fixture', FIXTURES)
def test_fixture_renders(fixture, tmp_path):
    out = tmp_path / 'out.svg'
    assert generate_diagram(fixture, output_file=str(out),
                            layout_algorithm='select')
    svg = out.read_text(encoding='utf-8')
    # vocabulario anonimizado presente (MinaCo en las mineras; InteCo en
    # el presupuesto)
    assert 'MinaCo' in svg or 'InteCo' in svg
