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
