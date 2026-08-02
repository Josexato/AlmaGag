# Grupos P y Q — Contención anidada, zonas de servicio y autoría (PENDIENTE)

Nueva sección del review de Claude Design (2-ago-2026, artifact
`baa24892-f8a2-4e35-b734-1fcd7ff72970`). Evaluada sobre un SDJF REAL de
arquitectura física minera (5 zonas `area`, 37 elementos, 26 conexiones,
contención anidada área→edificio→equipos). **P62 CERRADO**: el fixture ya
está anonimizado en `docs/diagrams/gags/mina-arquitectura-fisica.sdjf`
(cliente MinaCo, proyecto CobreSur; longitudes ±7%; guardia anti-fuga en
`tests/test_p62_fixture.py`). Línea base medida que el grupo P debe bajar:
`[auto] cruces=41 arista×nodo=12 labels=112 tinta=46.6% aspecto=1.09`.

Diagnóstico del revisor: el SDJF está bien modelado; los defectos son del
renderer — la contención anidada no reserva espacio, la zona de servicios
quedó al centro, ≥6 grupos de rótulos fundidos y ~7 diagonales largas
cruzando zonas. Aplican K35/N47 ya escritos; esto cubre lo nuevo.

## Grupo P — renderer

| # | Criterio | Resumen |
|---|---|---|
| P59 ✅ | Contención anidada reserva espacio real | layout bottom-up: caja del contenedor = bbox(hijos + etiquetas + banda de rótulo O54); el nivel superior la posiciona como super-nodo RÍGIDO; ningún elemento ∉ contains puede intersectarla. Recursivo a cualquier profundidad. Verifica: bbox(hijos+labels) ⊆ caja y cero intrusos |
| P60 | Zonas de servicio a la periferia + troncal por zona destino | clasificar zonas: operativas (tráfico inter-zona) en banda principal; servicio/soporte (solo enlaces administrativos salientes) en periferia. Enlaces a una misma zona destino agrupados en UNA troncal ortogonal hasta el borde (I29); cero diagonales inter-zona (H24) |
| P61 | Pasada anticolisión a TODA profundidad | el camino de áreas I27 con sub-layout no ejecuta F18/J31 ni colisiones sobre miembros. La pasada (etiqueta↔etiqueta/icono, arista↔etiqueta) debe ser etapa GLOBAL post-layout sobre el árbol completo; pitch dentro de área ≥ icono + 3×11px + holgura para labels de 3 líneas. Verifica: contador labels incluye miembros anidados; 0 fusiones (hoy ≥6); separación texto↔texto ≥8px |
| P62 ✅ | Higiene de fixtures: anonimizar antes de commitear | reemplazar empresas/proyectos/personas por genéricos conservando estructura, tipos, LONGITUDES de label (para reproducir colisiones) y semántica. Verifica: grep de términos sensibles vacío; labels ±10% de longitud original |

## Grupo Q — suficiencia del SDJF (guía de autoría + fallback del motor)

Veredicto del revisor: la topología y agrupación del SDJF sin posiciones son
~80% derivables; tres vacíos exigieron juicio editorial:

| # | Criterio | Resumen |
|---|---|---|
| Q63 | `semantic_type` declarado, no inferido del label | 7 clases de enlace distinguidas solo por texto. Autoría: declararlo (contrato N48). Motor: fallback por palabras clave PERMITIDO con `WARNING [semantic] inferido de label`, nunca en silencio; sin match → clase neutra |
| Q64 ◐ | Types nuevos: BWT deliberado primero, catálogo cuando recurren | REFINADO (v3 del artifact): usar un type nuevo con BWT es USO VÁLIDO del estándar — nombra lo que aún no tiene forma visual. Exigible: nombre semánticamente claro, porque **el BWT muestra ese nombre** (✅ implementado: rótulo 11 bold sobre el plátano) y **el audit lista los BWT activos** (✅ implementado: línea `§Q64: N type(s) en BWT (inventario…)`). Pendiente del motor: promover al catálogo los types que recurren (señal: mismo type en BWT en ≥2 fixtures) — el paquete de red torre/antena, unidad móvil, generador, vehículo, CPE, red eléctrica es el candidato natural |
| Q65 | Afinidad y orden entre áreas (opcional + derivación) | opcional `considerations.near[areaA, areaB]` a nivel de áreas (sintaxis N46). Sin declarar: áreas unidas por transporte → adyacentes en banda central; solo-administrativas → periferia (P60); desempate por orden de aparición; determinista |

## Sección R — Reparto de responsabilidades motor ⇄ skill (v3 del artifact)

**Regla de frontera**: el skill declara intención y semántica; el motor decide
TODA la geometría. «Si el skill necesita posiciones fijas para que un diagrama
se vea bien, eso es un bug del motor (grupos A–P), no una tarea de autoría.»

- **Motor** (repo): A–F niveles/ruteo/etiquetas · G–H formas/canvas ·
  I27–I30 áreas/carriles/roles · J densidad · K renderer compartido ·
  M arcos · N45–N48 topología y contrato semántico · O50–O58 emisión ·
  P59–P61 contención/servicio/anticolisión · Q63–Q65 los FALLBACKS ·
  L39/P62 proceso de repo.
- **Skill** (autoría): estructura (`area`+`contains` anidado), semántica
  (`direction`, `semantic_type`, `role`), iconografía (catálogo, `icons{}`,
  o type nuevo a BWT deliberado con nombre claro), afinidad
  (`considerations` solo con lectura preferida), redacción (≤3 líneas,
  anonimizar fixtures).
- **Prohibido en el skill**: coordenadas fijas para compensar defectos de
  layout; duplicar semántica en el texto del label en vez de declararla;
  types con nombres crípticos (el BWT muestra el nombre: debe explicarse solo).

## Checklist del autor (del propio artifact)

- Agrupar con `area` + `contains` (I27), anidando contenedores reales
- `direction` en toda conexión
- `semantic_type` cuando hay ≥3 clases de enlace (Q63)
- Todo `type` no estándar resoluble o embebido (Q64)
- Afinidad entre áreas si el autor tiene lectura preferida (Q65)
- Etiquetas ≤3 líneas (J31/J32); lo demás a nota aparte

## Estado previo confirmado

En la misma actualización del artifact, el revisor re-midió el seguimiento
de O56 y declaró el **grupo O completo** («arquitectura {12,14},
WAN {11,12,14}, el test estricto congela la escala {14,12,11}»).

## Para arrancar

1. ~~Conseguir el SDJF fuente y anonimizarlo (P62)~~ HECHO.
2. ~~P59~~ CERRADO: la grilla local dimensiona celdas al tamaño REAL del
   hijo (ancho por columna, alto por fila) — con hijos tamaño-icono se
   reduce al comportamiento anterior (métricas idénticas en el resto de
   fixtures). Verifica en `tests/test_p59_nested_containment.py`: hijos ⊆
   caja a toda profundidad, cero iconos intrusos, cajas hermanas sin
   solape. Fixture minero: labels 112→54, arista×nodo 12→12, cruces 41→52
   (los nodos des-apilados ahora exponen las diagonales de la zona de
   servicios — es el defecto que ataca P60).
3. Orden restante: P61 → P60 → Q63 → Q64 (paquete de red) → Q65.
4. Convenciones de siempre: un criterio por commit, test de regresión,
   guarda anti-regresión con la línea `[motor]`, verificación visual PNG,
   `python -m pytest -q --import-mode=importlib` (hoy: 407 verdes).
   La guarda ahora tiene medidor versionado: `scripts/measure_fixtures.py`
   (una línea estable por fixture; aborta ruidosamente si mide 0).

## P61 — primer intento REVERTIDO (diagnóstico para retomar)

Se intentó (2-ago-2026) espaciado consciente de etiquetas en las grillas
locales de `positioner.py`: cap del ensanche a 2.2×ICON en grids anchos,
pitch vertical por fila sumando `LABEL_OFFSET_VERTICAL`, alineación a la
izquierda sin ensanche, y cobertura cruda del bbox en
`_calculate_container_bounds` (flag `_grid_raw_cover`). Resultado global:
labels mejoraban en casi todos los fixtures, PERO la guarda anti-regresión
(probar → medir → revertir si empeora) detectó dos intercambios malos:

- `06-flujo-ejecucion`: cruces 11→17, arista×nodo 0→3 (labels 30→16) —
  visual confirmó intrusos nuevos dentro del box Generator y fusiones
  nuevas en la 4ª columna.
- `git.sdjf`: labels 60→27 pero arista×nodo 3→5.

Causa raíz: `recalculate_positions_with_expanded_containers` y el
optimizador de labels NO acompañan el crecimiento de las celdas — al
ensanchar la grilla, los vecinos externos no se reubican y las aristas
atraviesan las cajas crecidas. Camino sugerido para el reintento: gatear
los cambios de grid ancho por presencia de hijo-contenedor o labels
multilínea, y/o implementar primero la pasada anticolisión GLOBAL
post-layout que el propio P61 pide (etiqueta↔etiqueta/icono,
arista↔etiqueta sobre el árbol completo), en vez de tocar la grilla local.

Nota de proceso (near-miss): el medidor de la guarda vivía en el
scratchpad y falló EN SILENCIO durante un bloque entero
(`ModuleNotFoundError` con stderr descartado → archivos de métricas
vacíos → diffs vacuamente «limpios»). Se re-validó todo contra worktrees
de los commits base (item-4 `029f0d7`, P59 `ea8edcd`/`5f847de`): master
está limpio (solo las mejoras conocidas: 11-stresstest labels 1→0,
system-architecture 13→1, + fixture minero nuevo). De ahí el medidor
versionado con abort ruidoso.
