#!/usr/bin/env bash
# run-review.sh — regenera el paquete de revisión de forma reproducible (§H10).
#
# Genera los 4 diagramas de la iteración de revisión desde su fuente .sdjf/.gag
# con los flags EXACTOS, en docs/reviews/iteracion-3/, y estampa el commit hash
# para que quien revise reproduzca los mismos artefactos que el reporte cita.
#
# Uso:   bash docs/diagrams/run-review.sh
# Requisitos: pip install -e .  (o PYTHONPATH=$PWD)
set -euo pipefail

cd "$(dirname "$0")/../.."          # raíz del repo
OUT="docs/reviews/iteracion-3"
GAGS="docs/diagrams/gags"
mkdir -p "$OUT"

PY="python -m AlmaGag.main"
COMMIT="$(git rev-parse --short HEAD 2>/dev/null || echo 'sin-git')"
echo "== AlmaGag · paquete de revisión · commit ${COMMIT} =="

# par (salida, fuente, flags) — el motor se auto-selecciona salvo nota
gen () { # $1=salida $2=fuente $3=flags
  echo "-> $1  (fuente: $2 ${3:-})"
  $PY "$GAGS/$2" -o "$OUT/$1" ${3:-}
}

gen "1-arquitectura.svg" "05-arquitectura-gag.gag"      # motor auto
gen "2-stresstest.svg"   "14-stresstest.sdjf"           # ciclo → hier (auto-selección)
gen "3-genealogico.svg"  "11-stresstest.sdjf"           # motor auto
gen "4-sdwan.svg"        "red-dual-homing.sdjf"         # topología (coords manuales)

echo "${COMMIT}" > "$OUT/.commit"
echo "== listo. SVGs regenerados en $OUT (commit ${COMMIT}) =="
echo "   Epifanía (flipbook por fase):  $PY <fuente> --epifania -o /tmp/x.svg"
echo "   → un SVG por fase en debug/epifania/<diagrama>/ (+ index.html)"

# Iteración 4 (sección N — topologías de red)
OUT4="docs/reviews/iteracion-4"
mkdir -p "$OUT4"
$PY "$GAGS/red-minera-antes.gag"   -o "$OUT4/1-red-antes.svg"
$PY "$GAGS/red-minera-despues.gag" -o "$OUT4/2-red-despues.svg"
echo "${COMMIT}" > "$OUT4/.commit"

# Iteración 5 (grupo O — emisión/portabilidad): una lámina por clase de
# diagrama + su PNG SIN navegador (vía cairosvg, §O50+§O58) — regenerable
# desde CI sin Chrome.
OUT5="docs/reviews/iteracion-5"
mkdir -p "$OUT5"
$PY "$GAGS/05-arquitectura-gag.gag"    -o "$OUT5/1-arquitectura.svg"
$PY "$GAGS/red-minera-antes.gag"       -o "$OUT5/2-wan.svg"
$PY "$GAGS/es-primo.gag"               -o "$OUT5/3-flowchart.svg"
$PY "$GAGS/organigrama-empresa.sdjf"   -o "$OUT5/4-organigrama.svg"
python3 - <<'PYEOF'
from AlmaGag.debug import _png_via_cairosvg
for n in ('1-arquitectura', '2-wan', '3-flowchart', '4-organigrama'):
    ok = _png_via_cairosvg(f'docs/reviews/iteracion-5/{n}.svg',
                           f'docs/reviews/iteracion-5/{n}.png', scale=1.0)
    print(('   PNG ok  ' if ok else '   PNG FALLÓ') + f' {n}.png')
PYEOF
echo "${COMMIT}" > "$OUT5/.commit"
