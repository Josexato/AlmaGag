#!/usr/bin/env python3
"""Guarda anti-regresión: la línea [motor] de TODOS los fixtures.

Imprime una línea estable por fixture de docs/diagrams/gags/ y de
docs/diagrams/constructos/ (el corpus compartido con almagag-jv) con los
contadores de calidad (cruces, arista×nodo, labels, tinta, aspecto).
Uso típico (patrón probar → medir → revertir si empeora):

    python scripts/measure_fixtures.py > /tmp/antes.txt
    # ... cambios ...
    python scripts/measure_fixtures.py > /tmp/despues.txt
    diff /tmp/antes.txt /tmp/despues.txt

Los constructos con vista CLI declarada (views.json — la vista no vive en
el archivo, §R) se miden con esa vista. Un fixture que revienta imprime
«ERROR <mensaje>»: la línea es estable y la guarda documenta el bug
conocido (c27/BUGS-LAYOUT-014) sin callar al resto.

Nota de guerra: la primera versión de este medidor vivía fuera del repo y
falló en silencio (sys.path sin la raíz) — las guardas compararon archivos
vacíos durante un bloque entero. Por eso ahora (a) vive versionado, (b)
aborta ruidosamente si no midió nada.
"""

import glob
import io
import json
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from AlmaGag.generator import generate_diagram  # noqa: E402

CONSTRUCTOS = 'docs/diagrams/constructos'


def main() -> int:
    logger = logging.getLogger('AlmaGag')
    fixtures = sorted(glob.glob('docs/diagrams/gags/*.sdjf')
                      + glob.glob('docs/diagrams/gags/*.gag'))
    fixtures += sorted(glob.glob(f'{CONSTRUCTOS}/*.sdjf')
                       + glob.glob(f'{CONSTRUCTOS}/*.gag'))
    views = {}
    views_path = os.path.join(CONSTRUCTOS, 'views.json')
    if os.path.exists(views_path):
        with open(views_path) as fh:
            views = json.load(fh)
    measured = 0
    for f in fixtures:
        buf = io.StringIO()
        handler = logging.StreamHandler(buf)
        handler.setLevel(logging.INFO)
        logger.addHandler(handler)
        try:
            generate_diagram(f, output_file='/tmp/_measure.svg',
                             layout_algorithm='select',
                             view=views.get(os.path.basename(f), 'auto'))
        except Exception as e:  # noqa: BLE001 — un fixture roto no calla al resto
            print(f'{os.path.basename(f)} | ERROR {type(e).__name__}: {e}')
            continue
        finally:
            logger.removeHandler(handler)
        line = next((l for l in buf.getvalue().splitlines() if 'cruces(' in l), None)
        if line:
            print(f"{os.path.basename(f)} | {line.split('] ', 1)[-1]}")
            measured += 1
    if measured == 0:
        print('ERROR: no se midió ningún fixture — guarda inválida', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
