#!/usr/bin/env python3
"""Guarda anti-regresión: la línea [motor] de TODOS los fixtures.

Imprime una línea estable por fixture de docs/diagrams/gags/ con los
contadores de calidad (cruces, arista×nodo, labels, tinta, aspecto).
Uso típico (patrón probar → medir → revertir si empeora):

    python scripts/measure_fixtures.py > /tmp/antes.txt
    # ... cambios ...
    python scripts/measure_fixtures.py > /tmp/despues.txt
    diff /tmp/antes.txt /tmp/despues.txt

Nota de guerra: la primera versión de este medidor vivía fuera del repo y
falló en silencio (sys.path sin la raíz) — las guardas compararon archivos
vacíos durante un bloque entero. Por eso ahora (a) vive versionado, (b)
aborta ruidosamente si no midió nada.
"""

import glob
import io
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from AlmaGag.generator import generate_diagram  # noqa: E402


def main() -> int:
    logger = logging.getLogger('AlmaGag')
    fixtures = sorted(glob.glob('docs/diagrams/gags/*.sdjf')
                      + glob.glob('docs/diagrams/gags/*.gag'))
    measured = 0
    for f in fixtures:
        buf = io.StringIO()
        handler = logging.StreamHandler(buf)
        handler.setLevel(logging.INFO)
        logger.addHandler(handler)
        try:
            generate_diagram(f, output_file='/tmp/_measure.svg',
                             layout_algorithm='select')
        except Exception as e:  # noqa: BLE001 — un fixture roto no calla al resto
            print(f'{os.path.basename(f)} | ERROR {e}')
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
