# Grupos P y Q — Contención anidada, zonas de servicio y autoría (PENDIENTE)

Nueva sección del review de Claude Design (2-ago-2026, artifact
`baa24892-f8a2-4e35-b734-1fcd7ff72970`). Evaluada sobre un SDJF REAL de
arquitectura física minera (5 zonas `area`, 38 elementos, 26 conexiones,
contención anidada área→edificio→equipos). **El fixture aún no está en el
repo: hay que anonimizarlo antes de commitearlo (P62).**

Diagnóstico del revisor: el SDJF está bien modelado; los defectos son del
renderer — la contención anidada no reserva espacio, la zona de servicios
quedó al centro, ≥6 grupos de rótulos fundidos y ~7 diagonales largas
cruzando zonas. Aplican K35/N47 ya escritos; esto cubre lo nuevo.

## Grupo P — renderer

| # | Criterio | Resumen |
|---|---|---|
| P59 | Contención anidada reserva espacio real | layout bottom-up: caja del contenedor = bbox(hijos + etiquetas + banda de rótulo O54); el nivel superior la posiciona como super-nodo RÍGIDO; ningún elemento ∉ contains puede intersectarla. Recursivo a cualquier profundidad. Verifica: bbox(hijos+labels) ⊆ caja y cero intrusos |
| P60 | Zonas de servicio a la periferia + troncal por zona destino | clasificar zonas: operativas (tráfico inter-zona) en banda principal; servicio/soporte (solo enlaces administrativos salientes) en periferia. Enlaces a una misma zona destino agrupados en UNA troncal ortogonal hasta el borde (I29); cero diagonales inter-zona (H24) |
| P61 | Pasada anticolisión a TODA profundidad | el camino de áreas I27 con sub-layout no ejecuta F18/J31 ni colisiones sobre miembros. La pasada (etiqueta↔etiqueta/icono, arista↔etiqueta) debe ser etapa GLOBAL post-layout sobre el árbol completo; pitch dentro de área ≥ icono + 3×11px + holgura para labels de 3 líneas. Verifica: contador labels incluye miembros anidados; 0 fusiones (hoy ≥6); separación texto↔texto ≥8px |
| P62 | Higiene de fixtures: anonimizar antes de commitear | reemplazar empresas/proyectos/personas por genéricos conservando estructura, tipos, LONGITUDES de label (para reproducir colisiones) y semántica. Verifica: grep de términos sensibles vacío; labels ±10% de longitud original |

## Grupo Q — suficiencia del SDJF (guía de autoría + fallback del motor)

Veredicto del revisor: la topología y agrupación del SDJF sin posiciones son
~80% derivables; tres vacíos exigieron juicio editorial:

| # | Criterio | Resumen |
|---|---|---|
| Q63 | `semantic_type` declarado, no inferido del label | 7 clases de enlace distinguidas solo por texto. Autoría: declararlo (contrato N48). Motor: fallback por palabras clave PERMITIDO con `WARNING [semantic] inferido de label`, nunca en silencio; sin match → clase neutra |
| Q64 | Vocabulario de iconos de red como built-ins | el fixture usa tower/cow/generator/truck/cpe/powergrid — ninguno existe. Motor: añadir el paquete de red al catálogo (torre/antena, unidad móvil, generador, vehículo, CPE, red eléctrica); mientras no exista: BWT visible (O55). Verifica: fixture sin ningún BWT usando solo el catálogo |
| Q65 | Afinidad y orden entre áreas (opcional + derivación) | opcional `considerations.near[areaA, areaB]` a nivel de áreas (sintaxis N46). Sin declarar: áreas unidas por transporte → adyacentes en banda central; solo-administrativas → periferia (P60); desempate por orden de aparición; determinista |

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

1. Conseguir el SDJF fuente (vive en el chat del caso real) y anonimizarlo
   según P62 → fixture de regresión.
2. Orden sugerido: P62 (fixture) → P59 → P61 → P60 → Q63/Q64 → Q65.
3. Convenciones de siempre: un criterio por commit, test de regresión,
   guarda anti-regresión con la línea `[motor]`, verificación visual PNG,
   `python -m pytest -q --import-mode=importlib` (hoy: 394 verdes).
