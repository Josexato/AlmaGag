"""
Regresión de DETERMINISMO: la misma entrada debe producir el mismo SVG, sin
importar `PYTHONHASHSEED`. El bug (2026-07): los templates `flow` y
`hub_and_spoke` iteraban un `set` de ids de string para ordenar niveles/spokes,
y el orden de iteración de sets depende del hash seed → el layout cambiaba entre
corridas. Fix: iterar la lista de elementos (orden del input), no el set.

Se corre en subprocesos porque `PYTHONHASHSEED` sólo se fija al arrancar el
intérprete.
"""

import os
import sys
import subprocess

import pytest


def _render(path, seed, out):
    env = dict(os.environ, PYTHONHASHSEED=str(seed))
    r = subprocess.run([sys.executable, '-m', 'AlmaGag.main', path, '-o', out],
                       env=env, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return open(out).read()


@pytest.mark.parametrize('canonical', [
    'docs/diagrams/gags/14-stresstest.sdjf',       # template 'flow'
    'docs/diagrams/gags/06-flujo-ejecucion.sdjf',  # template 'hub_and_spoke' + contenedores
])
def test_render_is_hashseed_independent(canonical, tmp_path):
    a = _render(canonical, 1, str(tmp_path / 'a.svg'))
    b = _render(canonical, 99, str(tmp_path / 'b.svg'))
    assert a == b, f"{os.path.basename(canonical)} cambia entre PYTHONHASHSEED 1 y 99"
