"""§P62 — higiene del fixture del grupo P (arquitectura física minera).

El caso real se promovió a fixture ANONIMIZADO: empresas/proyecto/
ubicaciones/proveedores reemplazados por genéricos (cliente ficticio MinaCo,
proyecto CobreSur) conservando estructura, tipos, semántica de conexiones y
longitudes de label (peor delta +7%, P62 pide ±10%) para que las colisiones
del grupo P se reproduzcan tal cual.
"""

import json
import re

from AlmaGag.generator import generate_diagram

FIXTURE = 'docs/diagrams/gags/mina-arquitectura-fisica.sdjf'

# Términos sensibles del caso real: si cualquiera reaparece, el test truena.
LEAKS = ['Tia Maria', 'tiamaria', 'Tapada', 'Cachendo', 'SPCC', 'Huawei',
         'Claroty', 'CICSA', 'Cocachacra', 'Mollendo', 'TICAR', 'LY-304']


def test_fixture_is_anonymized():
    t = open(FIXTURE, encoding='utf-8').read()
    for leak in LEAKS:
        assert leak not in t, f'{FIXTURE} contiene dato real: {leak}'
    assert not re.search(r'\bIlo\b', t), f'{FIXTURE} contiene dato real: Ilo'


def test_fixture_structure_preserved():
    """La anonimización no tocó la estructura que el grupo P necesita:
    5 áreas, contención anidada (área→edificio→equipos), 26 conexiones."""
    d = json.load(open(FIXTURE))
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


def test_fixture_renders(tmp_path):
    out = tmp_path / 'mina.svg'
    assert generate_diagram(FIXTURE, output_file=str(out),
                            layout_algorithm='select')
    assert 'MinaCo' in out.read_text(encoding='utf-8')
