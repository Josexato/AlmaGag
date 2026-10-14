# Corpus de constructos — compartido AlmaGag Python ⇄ almagag-jv

27 fixtures `.sdjf`/`.gag` públicos (labels genéricos, ningún nombre real)
que cubren los constructos que los 40 fixtures históricos no tocan:
`canvas.partition` (bsp, grid, compactación por intervalos, plan inválido),
serpenteo Z94, genealogías AA98–AA100, `steps`, vistas `columns`/`lanes`/
`matrix`, `area.role`, bus troncal, corredores, abanico, áreas ⊃
contenedores, zonas físicas §P59/§P60, journeys, roles/status/legend, theme
+ semántica, `canvas.flow: up`, considerations §O53, iconos embebidos/BWT,
ciclos y self-loop, y el fixture del presupuesto de performance (c26).

**Un solo corpus, dos motores, los mismos jueces.** Ningún archivo trae
coordenadas ni knobs de layout (frontera §R).

## Archivos

| Archivo | Qué es |
|---|---|
| `cNN-*.sdjf` / `.gag` | los fixtures |
| `views.json` | vista CLI por fixture (`c11` → `lanes`, `c12` → `matrix`); la vista NO vive en el archivo (§R) |
| `MANIFEST.json` | por fixture: constructo, propiedad que congela y **evidencia** de que el constructo se activó en el oráculo (`log:<regex>`, `motor:<perfil>`, `error:<tipo>` o `visual`) |

Evidencia verificada contra Python v3.20.0 (`9c7087d`): 18/18 evidencias
ejecutables cumplen; 9 visuales revisadas en PNG. Referencia medida en
`golden/constructos-v3.20.0.json`: 26/27 renderizan; **c27 revienta en el
Python** (PY-001, `docs/HALLAZGOS-PYTHON.md`).

## Cómo aportarlo al repo Python

1. Copiar los `cNN-*` a `docs/diagrams/constructos/` (no a `gags/`, para no
   alterar la línea base histórica de `scripts/measure_fixtures.py`).
2. `measure_fixtures.py` usa `--view auto` para todo; c11/c12 necesitan
   `views.json` (o medirse con `python -m AlmaGag.main cNN.sdjf --view lanes`).
3. c27 queda como test rojo de PY-001 hasta su fix.
4. Medición reproducible desde este repo:
   `python golden/scripts/measure_reference.py --python-repo <AlmaGag> --fixtures fixtures/constructos --views fixtures/constructos/views.json --out golden/constructos-v3.20.0.json`
   (aborta si el checkout no está en el commit de `golden/PROVENANCE.json` o tiene cambios).

Regenerar los archivos: son JSON escritos a mano vía generador; editar el
JSON directamente es válido — el sha256 en el golden detecta el cambio y
obliga a re-medir.
