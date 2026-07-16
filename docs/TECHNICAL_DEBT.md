# Deuda Técnica — AlmaGag

Este documento registra problemas conocidos y áreas de mejora del proyecto.

**Última actualización**: 2026-06-15

---

## Convención de códigos

Cada entrada tiene un código con estructura uniforme `<CATEGORÍA>-<COMPONENTE>-<NNN>`:

### Categorías

- **`BUGS`** — Cosas que no funcionan como deberían. Hay un comportamiento esperado y la implementación lo viola.
- **`WISH`** — Cosas que se desea crear o mejorar. El sistema funciona, pero se podría hacer mejor.

### Componentes

- **`LAYOUT`** — Issues transversales del módulo `AlmaGag/layout/` que afectan a ambos algoritmos.
- **`LAF`** — Issues exclusivos del algoritmo LAF (`AlmaGag/layout/laf/`).
- **`AUTO`** — Issues exclusivos del algoritmo AUTO (`AlmaGag/layout/auto/`).
- **`ROUT`** — Issues del módulo de routing (`AlmaGag/routing/`): cálculo de paths, port assignment, visibility graph, simplificación.
- **`TPL`** — Issues del módulo de templates (`AlmaGag/layout/templates/`): detección semántica, scorers, aplicación de patrones, calibración del clasificador.
- **`VAL`** — Issues del módulo de validación (`AlmaGag/validation/`): reglas de calidad visual (R1/R2/R3) y sus heurísticas.
- **`DRAW`** — Issues del módulo de dibujo (`AlmaGag/draw/`): nuevos tipos de iconos/shapes, primitivas SVG, gradientes, markers.
- **`ARCH`** — Issues arquitecturales del sistema (acoplamientos, contratos, extensibilidad).
- **`DOCS`** — Documentación que quedó desincronizada del código o del estado actual del proyecto.
- **`DIAG`** — Problemas visuales en los SVG renderizados. Viven en `docs/DIAGRAM_REVIEW.md`, no aquí.

### ⚠️ Importante: distinción con `LAF_PHASE_N_...`

El código de runtime usa identificadores como `LAF_PHASE_6_NDPR_EXPANDED` para nombrar las fases del pipeline durante el debug (`_dump_layout()`). Estos **no son** los códigos `BUGS-LAF-NNN` de este documento. La distinción:

| Patrón | Dónde vive | Qué identifica |
|---|---|---|
| `LAF_PHASE_N_NOMBRE` | `AlmaGag/layout/laf/optimizer.py` | Fase del pipeline LAF (para snapshots de debug) |
| `BUGS-LAF-NNN` / `WISH-LAF-NNN` | Este documento | Issue específico a corregir |

---

## 🐛 BUGS

### BUGS-LAYOUT-001: Etiquetas de Debug Solapadas en Modo VisualDebug ✅ RESUELTO
**Componente**: `layout/auto/auto_renderer.py` + `layout/laf/laf_renderer.py` — `_render_debug_levels` / `_render_debug_ndfn`
**Severidad**: Media
**Reportado**: 2026-01-21
**Resuelto**: 2026-06-18

**Causa raíz**:
Las etiquetas de debug (nivel topológico en rojo, NdFn en rojo/naranja) se renderizaban DENTRO del bbox de cada elemento primario:
- Nivel: `(elem_x, elem_y + 10)` — encima del ícono.
- NdFn: `(elem_x + 2, elem_y + 8)` — pegada al nivel.
- NdFn icon: `(elem_x + 2, elem_y + 16)` — abajo de NdFn.

Resultado en `--visualdebug`: 36/55 etiquetas (65%) solapadas con íconos en el caso de prueba `05-arquitectura-gag`, ilegibles sobre la mayoría de los elementos.

**Fix aplicado** (replicado en ambos renderers — son independientes desde WISH-ARCH-002):
Posicionamiento de las etiquetas FUERA del bbox, apiladas arriba del elemento:
- Nivel: `(elem_x, elem_y - 8)` — texto baseline 8px arriba del top del bbox.
- NdFn: `(elem_x + 2, elem_y - 24)` — arriba del nivel.
- NdFn icon: `(elem_x + 2, elem_y - 33)` — arriba de NdFn.
- Las tres usan `filter='url(#text-glow)'` para halo blanco que asegura legibilidad sobre fondos arbitrarios (mismo filtro que las etiquetas normales).

Aprovecha el `TOP_MARGIN_DEBUG = 80px` que ya se reservaba arriba del canvas en modo debug — los textos quedan en esa franja sin off-canvas.

**Validación**:
- Solapamientos en `05-arquitectura-gag --laf --visualdebug`: 36/55 → 7/55. Los 7 restantes son **falsos positivos**: 2 dentro del strip de debug del canvas (zona reservada), 5 dentro de un container (arriba de sus hijos, donde el "rect contenedor" cubre toda el área). **Cero solapamientos con íconos reales**.
- Smoke 23/23 LAF + 23/23 AUTO OK.
- Tests 17/2.
- Determinismo sin `--visualdebug`: 1 hash único × 3 seeds × 4 archivos. Con `--visualdebug` sigue no-determinista (causa preexistente: badge usa `datetime.now()`, no introducido por este fix).

---

### BUGS-LAYOUT-002: Cálculo Excesivo de Altura de Canvas ✅ RESUELTO
**Componente**: `AlmaGag/layout/laf/container_grower.py` — `calculate_final_canvas()`
**Severidad**: Media
**Reportado**: 2026-01-21
**Resuelto**: 2026-06-18

**Causa raíz**:
`container_grower.calculate_final_canvas()` aplicaba un margen único de **250px** tanto al ancho como al alto. El margen estaba justificado solo por el **badge de debug** (visible en modo `--visualdebug`), que ocupa ~240px de ancho y vive **en la esquina superior derecha** del canvas. El margen vertical de 250px no tenía justificación y desperdiciaba ~33% del canvas en promedio (78-97% en diagramas pequeños).

**Fix aplicado**:
- Nuevas constantes en `config.py`:
  - `LAF_CANVAS_MARGIN_HORIZONTAL = 250` (protege espacio del badge).
  - `LAF_CANVAS_MARGIN_VERTICAL = 50` (margen visual mínimo abajo).
- `container_grower.calculate_final_canvas()` usa las dos constantes por separado.

**Validación** (23 archivos LAF):
| Métrica | Antes | Después |
|---|---:|---:|
| Waste promedio (px) | 365 | 165 |
| Waste promedio (%) | ~33% | ~18% |
| Archivos con waste >25% | 13 | 6 |
| Determinismo (hashes únicos) | 1 | 1 |
| Smoke render | 23/23 OK | 23/23 OK |

El caso peor restante (`13-stresstest.gag`, ~97%) es por estructura inusual del diagrama, no por margen excesivo. Si se quiere atacar, sería un issue separado de "altura mal estimada por contenido", no del margen.

---

### BUGS-LAYOUT-003: No-Determinismo entre Procesos Python ✅ RESUELTO
**Componente**: `AlmaGag/layout/laf/` + `AlmaGag/layout/auto/` + `AlmaGag/layout/graph_analysis.py`
**Severidad**: Media
**Reportado**: 2026-05-14 (hallazgo lateral durante validación del refactor de routing_policy)
**Resuelto**: 2026-06-14 (rama `claude/laf-009-investigation`)

**Descripción**:
LAF (y en menor medida AUTO sobre archivos con ties) producía resultados distintos para el mismo input en procesos Python separados.

**Causa raíz**: 7 puntos en el pipeline donde iteraciones de `set`/`dict` con orden afectado por `PYTHONHASHSEED`, o sorts sin tie-break, propagaban orden inestable.

1. `structure_analyzer.py:1297` — construcción de `element_tree[vc].children` desde `vc['members']` (set).
2. `structure_analyzer.py:1130-1138` — formación de leaf VCs desde `terminal` (set).
3. `structure_analyzer.py:1229` — `sorted_tois` sin tie-break.
4. `structure_analyzer.py:1371` — conversión `set→list` en `contracted_graph`.
5. `graph_analysis.py:calculate_topological_levels` — iteración de `elem_ids` (set) en fixpoint con ciclos.
6. `auto/positioner.py` + `laf/position_optimizer.py` — suma de floats no-conmutativa.
7. `laf/abstract_placer.py` — 5 sorts sin tie-break por `elem_id`.

**Fix aplicado**: `sorted()` con tie-break por `elem_id` en cada punto.

**Validación**: 23 archivos × 5 seeds × 2 algoritmos = 230 invocaciones. Antes: hasta 5 hashes distintos por archivo. Después: 1 hash por archivo en los 46 casos.

---

### BUGS-LAF-001: Distribución Horizontal Asimétrica en Niveles Multi-Elemento ✅ RESUELTO
**Componente**: `AlmaGag/layout/laf/container_grower.py` — `calculate_final_canvas()`
**Severidad**: Baja
**Reportado**: 2026-01-21
**Resuelto**: 2026-06-18

**Causa raíz**:
Tras BUGS-LAYOUT-002, `calculate_final_canvas()` aplicaba siempre `LAF_CANVAS_MARGIN_HORIZONTAL = 250px` al lado derecho del canvas (para proteger el badge de debug que aparece en la esquina superior derecha cuando `--visualdebug` está activo). Pero `LEFT_MARGIN` en Phase 9 es `CANVAS_MARGIN_LARGE = 100px`. Resultado: cuando **no** estaba activo `--visualdebug`, el canvas terminaba con left=100/right=250, asimétrico (contenido pegado al lado izquierdo). El "spacing fijo de 480px" mencionado en la descripción original era un síntoma; el verdadero gap era con respecto al borde del canvas.

**Ejemplo de reproducción** (3 elementos en mismo nivel, sin `--visualdebug`):
```
Antes: Canvas 1390×700  left_margin=100  right_margin=250  Δ=+150 (asimétrico)
Después: Canvas 1240×700  left_margin=100  right_margin=100  Δ=0   (simétrico)
```

**Fix aplicado**:
- `ContainerGrower.__init__` ahora acepta `visualdebug=False`.
- `LAFOptimizer.__init__` propaga `visualdebug` al `ContainerGrower`.
- `calculate_final_canvas()` usa `LAF_CANVAS_MARGIN_HORIZONTAL` (250px) solo si `visualdebug=True`; en caso contrario usa `CANVAS_MARGIN_LARGE` (100px) — mismo valor que `LEFT_MARGIN`, garantizando simetría.

**Validación** (23 archivos LAF, sin `--visualdebug`):
- 17/23 (74%) **perfectamente simétricos** (left=right=100).
- 6/23 con Δ < 100px residual, atribuible a issues conocidos:
  - `git` (Δ=78): caso documentado de overflow de `legend` en BUGS-LAF-002.
  - `05-arquitectura-gag, 06-flujo, 07-containers, reference-cheatsheet`: contenedores muy disparejos en ancho.
- Smoke 46/46 OK (23 × 2 algoritmos).
- Tests 19 passed.
- Determinismo: 1 hash único × 3 seeds × 2 archivos.
- Con `--visualdebug=True`: el badge sigue protegido (right margin = 250px) ✓.
- Compactación adicional: canvas LAF -150px de ancho por archivo (recuperado del margen innecesario).

---

### BUGS-AUTO-001: Labels Huérfanas en AUTO con Contenedores ✅ RESUELTO
**Componente**: `AlmaGag/layout/auto/optimizer.py` — `optimize()` paso 2.5.6
**Severidad**: **Alta** (visualmente roto en cualquier diagrama AUTO con containers)
**Reportado**: 2026-06-18 (detectado por inspección del usuario sobre `07-containers.svg`)
**Resuelto**: 2026-06-18

**Causa raíz**:
En `AutoLayoutOptimizer.optimize()`, el orden de pasos era:
1. Paso 2 — calcular `label_positions` para todos los elementos según sus coords actuales.
2. Pasos 2.5 / 2.5.4 / 2.5.5 — re-resolver containers, propagar coords locales, redistribuir elementos primarios. **Estos movían los íconos.**
3. ... pero las `label_positions` calculadas en el paso 2 **NUNCA se recalculaban** tras ese movimiento.

Resultado: las etiquetas de los elementos contenidos (api, db, webapp, mobile, …) renderizaban en posiciones donde el ícono **ya no estaba**. En `07-containers.svg` las labels "REST API" y "Database" aparecían al fondo del canvas (y=663) huérfanas, mientras los íconos estaban arriba (y=280).

Reproducción (pre-fix):
```
api icon final position:  (-43, 280)
api label final position: (190, 663)  ← 513px de distancia vertical
```

**Fix aplicado**:
Nuevo paso **2.5.6** en `optimize()`: tras la redistribución (paso 2.5.5), limpiar `label_positions` y `connection_labels`, y volver a llamar `_calculate_initial_positions(current)` con las coords finales de los íconos.

```python
current.label_positions = {}
current.connection_labels = {}
self._calculate_initial_positions(current)
```

Post-fix:
```
api icon:  (-43, 280)
api label: (-3, 350)  ← bottom del ícono ✓
```

**Validación**:
- 2 canonical SVGs regenerados con el fix:
  - `07-containers.svg`: labels REST API/Database/Web App/Mobile App/Redis Cache ahora pegadas a sus íconos.
  - `reference-cheatsheet.svg`: misma causa raíz, también corregido.
- Smoke 46/46 OK, tests 19 passed, determinismo intacto.
- 21/23 canonical SVGs sin cambios (solo los que tienen containers se ven afectados).

**Nota**: el fix no resuelve el problema **separado** de contenido off-canvas. Ese se resolvió en `BUGS-AUTO-002`.

---

### BUGS-AUTO-002: Contenido Cortado por el Borde (coords negativas) en AUTO ✅ RESUELTO
**Componente**: `AlmaGag/layout/auto/optimizer.py` — `optimize()` + `_normalize_to_canvas()`
**Severidad**: **Alta** (contenido visiblemente cortado)
**Reportado**: 2026-06-18 (segunda inspección del usuario sobre `07-containers.svg`)
**Resuelto**: 2026-06-18

**Causa raíz**:
La redistribución de elementos primarios alrededor de contenedores expandidos (`positioner.recalculate_positions_with_expanded_containers`) puede empujar elementos a coordenadas negativas. En `07-containers`, el container `backend-module` terminaba en x=-93 — cortado por el borde izquierdo del canvas. El cálculo de canvas (`_calculate_canvas_from_bounds`) solo miraba `x_max`/`y_max`, nunca los mínimos, así que las coords negativas nunca se compensaban.

**Fix aplicado**:
Nuevo método `_normalize_to_canvas()` llamado al final de `optimize()` (antes del return):
- Calcula `min_x`, `min_y` de todos los elementos posicionados.
- **Solo dispara si `min < 0`** (contenido cortado). No re-centra diagramas que ya caben — eso cambiaría layouts correctos.
- Aplica un shift uniforme a elementos, `label_positions` y `connection_labels` para llevar el mínimo a `CANVAS_MARGIN_SMALL` (50px).
- Re-rutea (regenera `computed_path` desde las nuevas posiciones) y recalcula el canvas.

**Validación**:
- `07-containers`: min_x pasó de **-93 a 50** (dentro del canvas). 0 elementos con x<-5 en el SVG.
- **Solo 1/23 canonical afectado** (`07-containers` — el único con coords negativas). Confirmado que ningún otro diagrama tenía el problema.
- Smoke 46/46 OK, tests 19 passed, determinismo intacto.

---

### BUGS-AUTO-003: Connection Labels Sobre Iconos Dentro de Containers ✅ RESUELTO
**Componente**: `AlmaGag/layout/geometry.py` — `label_intersects_elements()`
**Severidad**: **Alta** (etiquetas ilegibles encimadas con iconos)
**Reportado**: 2026-06-18 (tercera inspección del usuario sobre `07-containers.svg`)
**Resuelto**: 2026-06-18

**Causa raíz**:
`label_intersects_elements()` (usada por `LabelPositionOptimizer.score_position()`) trataba el rect de un **container** como un elemento sólido para detección de colisiones de labels. Como los iconos de un container viven DENTRO de su rect, cualquier posición candidata para el label de una conexión interna (ej: "queries" entre `api` y `db`, ambos dentro de `backend-module`) caía dentro del rect del container → **todos los candidatos sumaban el mismo +100**.

Con todos los candidatos empatados en la penalización de container, el desempate (por distancia/densidad) terminaba eligiendo posiciones que caían **encima de un icono**. La colisión con elementos es booleana (+100 fijo, no cuenta cantidad), así que "label sobre icono" (1 colisión real) puntuaba igual que "label en hueco libre dentro del container" (0 colisiones reales, solo el container).

Reproducción (`07-containers`, pre-fix): "queries" (centro de su línea en x=190) se movía a x=139, **encima del icono REST API** (centro x=140).

**Fix aplicado**:
`label_intersects_elements()` ahora **excluye containers** (`if 'contains' in elem: continue`). Los containers son fondos semi-transparentes — los labels legítimamente viven dentro de ellos. Tras el fix, solo los iconos reales cuentan como colisión, y el optimizer elige posiciones en huecos libres en vez de sobre iconos.

**Validación** (connection-labels sobre icono, antes → después):
- `07-containers`: 1 → **0**.
- `git`: 1 → **0**.
- `reference-cheatsheet`: 2 → **0**.
- `06-flujo-ejecucion`: 0 → 0 (reposicionamiento marginal).
- Total: **4 → 0**.
- 4 canonicals regenerados (los que tienen containers).
- Smoke 46/46 OK, tests 19 passed, determinismo intacto.

---

### BUGS-AUTO-004: Containers Solapados sin Resolución (AUTO) ✅ RESUELTO
**Componente**: `AlmaGag/layout/auto/positioner.py` + `AlmaGag/layout/collision.py`
**Severidad**: **Alta** (solape visible entre containers)
**Reportado**: 2026-06-18 (cuarta inspección del usuario sobre `07-containers.svg`)
**Resuelto**: 2026-06-18

**Causa raíz** (doble):
1. **`recalculate_positions_with_expanded_containers()` solo movía elementos libres**, nunca chequeaba container-vs-container. Frontend (nivel topológico 0, alto=233) y Backend (nivel 1) terminaban solapando 137×65 sin que nadie lo arreglara.
2. **El detector general (`CollisionDetector._collect_all_bboxes`) contaba el rect de cada container como obstáculo sólido** — mismo bug que AUTO-003 pero en otro path. Inflaba colisiones falsas y el hill-climbing reportaba 13 colisiones sin poder bajarlas, así que se rendía.

**Fix aplicado**:
- **`positioner._resolve_container_overlaps()`** (nuevo): tras mover free_elements, ordena containers por `y` e itera cascada de empujones — si dos containers solapan, el de mayor `y` se desplaza debajo del otro (+ margen).
- **`positioner._shift_container_subtree()`** (nuevo): mueve un container y todos sus descendientes por `(dx, dy)` preservando la composición interna.
- **`collision._collect_all_bboxes()`**: excluye TODOS los containers (con o sin `_is_container_calculated`). Son fondos semi-transparentes.

**Validación**:
- `07-containers`: overlap **137×65 → 137×0** (containers separados verticalmente con 40px de gap).
- Colisiones reales: **13 → 4**. Las 4 que quedan son falsos positivos legítimos (conn label cerca de su propia conexión, dos "HTTP requests" solapando entre sí — caso a resolver con repulsión de labels).
- Solo `07-containers` afectado entre canonicals (el único con containers solapados).
- Smoke 46/46 OK, tests 19 passed, determinismo intacto.

---

### BUGS-AUTO-005: Labels de Iconos Contenidos Salen Fuera del Container/Canvas ✅ RESUELTO
**Componente**: `AlmaGag/layout/auto/optimizer.py` — `_find_best_label_position` + `_try_relocate_labels` + `collision.count_element_collisions`
**Severidad**: **Alta** (labels visiblemente cortados / fuera de su container)
**Reportado**: 2026-06-18 (quinta inspección — diagrama de arquitectura tras los 4 AUTO previos)
**Resuelto**: 2026-06-18

**Causa raíz** (triple):
1. **`_find_best_label_position` no verificaba off-canvas**: el primer candidato sin colisión ganaba aunque su bbox quedara con x<0 o x>canvas_w. Caso típico: icono pegado al borde izquierdo del container y label en `left` con anchor=end → texto extendido hacia x negativo (auto_opt label en x=55 con texto de ~150px → empezaba en x=-95).
2. **`_try_relocate_labels` tenía el mismo agujero**: relocaba a `top` cuando `bottom` tenía 1-2 colisiones con líneas, sin importar si `top` salía del container o caía sobre el header del container ancestro.
3. **`count_element_collisions` contaba containers como obstáculos** (mismo path que AUTO-003 y AUTO-004 pero en otra función).

Resultado en `05-arquitectura-gag` antes del fix: `AutoLayoutOptimizer` con label en `left` (anchor=end) cortado fuera del canvas, `LAFOptimizer` en `top` pegado contra el label del container LAF.

**Fix aplicado**:
- **`_get_parent_container()`** + **`_label_inside_container()`** (nuevos): un label de un icono contenido debe quedar dentro del container ancestro y fuera de su header (40px).
- **Chequeo de canvas y container** en `_find_best_label_position` y `_try_relocate_labels`: posiciones que se salen se descartan.
- **`count_element_collisions`** excluye containers como obstáculos, mismo razonamiento que AUTO-003/004.

**Validación** (labels off-canvas, antes → después):
- `05-arquitectura-gag`: 2 → **0**.
- `git`: 11 → **0**.
- `reference-cheatsheet`: 12 → **1**.
- **Total: 25 → 1** en los canonicals afectados.
- Todos los iconos dentro de containers ahora con label en `bottom` dentro del container.
- 9 canonicals regenerados.
- Smoke 46/46, tests 19 passed, determinismo intacto.

---

### BUGS-AUTO-006: Labels Bottom Encimados Horizontalmente Dentro de Containers ✅ RESUELTO
**Componente**: `AlmaGag/layout/auto/optimizer.py` — `_stagger_overlapping_contained_labels` (nuevo)
**Severidad**: **Alta** (labels ilegibles superpuestos)
**Reportado**: 2026-06-18 (sexta inspección — tras AUTO-005 los labels quedaron dentro del container pero solapados entre sí)
**Resuelto**: 2026-06-18

**Causa raíz**:
Tras AUTO-005, todos los labels de iconos contenidos se forzaron a `bottom`. Pero los containers estrechos con iconos juntos (ej: `auto_box` 200px de ancho con dos iconos a 100px center-to-center) tenían labels más anchos que el spacing (`AutoLayoutOptimizer (híbrido + hill climbing)` ~180px). Los bboxes se solapaban horizontalmente.

Medición pre-fix en `05-arquitectura-gag`:
- `auto_opt` ↔ `auto_rend`: overlap 60×36
- `laf_opt` ↔ `laf_pipe`: overlap 88×36
- `layout_obj` ↔ `draw_svg`: overlap 108×36
- `router_mgr` ↔ `geometry_utils`: overlap 88×36

**Fix aplicado**:
Nuevo método `_stagger_overlapping_contained_labels()` llamado al final de `optimize()`. Por cada container:
1. Recolecta labels `bottom` de los hijos directos.
2. Ordena por x del bbox.
3. Para cada label, si su bbox solapa horizontal Y verticalmente con uno previo, lo empuja `y2_anterior + GAP` (escalón).
4. Si el escalón se sale del container, **expande la altura del container** para acomodar.

**Validación**:
- Overlaps entre labels post-fix: **4 → 0** en `05-arquitectura-gag`.
- Containers expandidos automáticamente: `auto_box` 171→196, `shared_box` 305→330.
- 4 canonicals regenerados (05-arq, 06-flujo, git, reference-cheatsheet).
- Smoke 46/46, tests 19 passed, determinismo intacto.

---

### BUGS-AUTO-007: Header Label del Container se Sale por la Derecha ✅ RESUELTO
**Componente**: `AlmaGag/layout/auto/positioner.py::_calculate_container_bounds` + `AlmaGag/layout/container_calculator.py` + `AlmaGag/draw/primitives/container.py`
**Severidad**: **Media** (header del container ilegible cuando es largo)
**Reportado**: 2026-06-19 (inspección del usuario sobre `shared_box`)
**Resuelto**: 2026-06-19

**Causa raíz**:
Las 3 funciones que calculan el `min_width` necesario para que el header quepa usaban `TEXT_CHAR_WIDTH = 8` (estimación para texto regular 14px). Pero el header de containers se renderiza **bold 16px**, que en realidad ocupa ~10px/char. La estimación subestimaba el ancho ~25%.

En `05-arquitectura-gag` el label "Shared (algoritmo-agnóstico)" (28 chars) necesitaba `100 + 28×10 + 10 = 390px`. El cálculo daba `100 + 28×8 + 10 = 334px`. El label se salía 46px por el borde derecho del container.

**Fix**: multiplicar `label_width` por 1.25 (8 × 1.25 = 10) en las 3 funciones.

**Validación** (`05-arquitectura-gag`):
- `shared_box` width: 334 → 390. Header cabe.
- 3 canonicals afectados (05-arq, git, reference-cheatsheet) regenerados.
- Smoke 46/46, tests 19 passed.

---

### BUGS-LAF-002: Layout Pobre con Contenedores Hermanos sin Conexiones (caso "dashboard") ✅ RESUELTO
**Componente**: `AlmaGag/layout/laf/optimizer.py` — Fase 1.5 (dashboard reflow) + Fase 9 (redistribución)
**Severidad**: Media
**Reportado**: 2026-05-14 (auditoría externa)
**Resuelto**: 2026-06-18

**Causa raíz** (doble):
1. Cuando 3+ contenedores root viven en el mismo nivel topológico sin conexiones entre ellos, el pipeline LAF los pone en fila horizontal (todos `abstract_y=0`). El canvas se vuelve extremadamente horizontal (caso de prueba 4 contenedores → 5900×243 px, ratio 24:1).
2. Bug secundario en Fase 9 (`_redistribute_vertical_after_growth`): los hijos de un contenedor aparecían en `optimized_layer_order` y eran reposicionados **dos veces** — una vez con el contenedor (correcto), otra independientemente con su `abstract_x` (incorrecto), terminando fuera del contenedor.

**Fix aplicado**:
- **`config.py`**: nueva constante `LAF_DASHBOARD_MIN_CONTAINERS = 3` (umbral).
- **`optimizer.py::_apply_dashboard_reflow()`** (nuevo método, llamado entre Fase 1 y Fase 2): detecta clusters de dashboard (N≥3 contenedores root en mismo nivel sin conexiones inter-contenedor) y promueve cada contenedor a un nuevo nivel topológico siguiendo grid `ceil(sqrt(N))` columnas × `ceil(N/cols)` filas. Los descendientes heredan el nuevo nivel.
- **`optimizer.py::_redistribute_vertical_after_growth()`**: skip de elementos cuyo padre contenedor está en la misma capa (evita doble movimiento).
- **`optimizer.py::_redistribute_vertical_fallback()`**: mismo skip aplicado al fallback.

**Validación**:
- Caso de prueba dashboard (4 contenedores root sin connections): canvas 5900×243 → 1165×656 (ratio 24:1 → 1.8:1).
- Smoke 23/23 LAF + 23/23 AUTO OK.
- Tests 17 passed, 2 skipped.
- Determinismo: 1 hash único × 5 seeds × 3 archivos.
- Efectos colaterales positivos en LAF: `07-containers` 3116→2614 (-16%), `11-stresstest` 700→410 (-41% alto), `git` 7875→1797 ancho (-77%).
- Canonical SVGs (AUTO) sin cambios.

**Limitaciones conocidas (no bloquean cierre)**:
- En el caso `git.sdjf`, el contenedor `legend` queda ~40px fuera del borde izquierdo del canvas (problema de centrado global cuando el grid tiene contenedores muy disparejos en ancho). Pendiente de evaluar como issue separado si molesta.
- El segundo hijo de cada contenedor puede sobresalir ~35px del borde derecho — bug preexistente del `container_grower` (no introducido por este fix).

---

### BUGS-ROUT-001: Rutas Ortogonales con Bends Innecesarios al Cruzar a Container ✅ RESUELTO (v2)
**Componente**: `AlmaGag/routing/orthogonal_router.py` + `AlmaGag/routing/visibility_graph.py`
**Severidad**: Media (afecta legibilidad visual de cualquier diagrama con containers)
**Reportado**: 2026-06-23 (feedback visual del usuario sobre `05-arquitectura-gag` post-actualización a v3.5)
**Resuelto**: 2026-06-23 (v1: commit `32e82a6`, v2: ventanas 4..7 puntos)

**Causa raíz** (doble):

1. **Routing por intermediate point con segmentos independientes**: cuando una conexión cruza el límite de un container (from fuera, to dentro — o viceversa), `OrthogonalRouter.calculate_path` delega a `_calculate_orthogonal_waypoints_with_intermediate`, que computa **2 segmentos independientes** (from → entry_point del container, entry_point → to), cada uno con su propio naive midpoint H-V o V-H (2 bends c/u). Resultado: hasta 4 bends por conexión aunque la geometría permita 1 bend limpio.

2. **Fallback al naive midpoint cuando A* falla**: `_route_with_visibility_graph` cae a `_calculate_orthogonal_waypoints` cuando A* no encuentra ruta. A* falla cuando alguno de los ports asignados por `port_assignment` cae dentro del bbox inflado (`OBSTACLE_MARGIN=25`) de algún container, lo cual ocurre con frecuencia cuando el target está pegado al borde de su container.

**Caso de prueba reproducible** (antes del fix, commit `e2712e4`):

Diagrama `05-arquitectura-gag.gag` con elementos `templates` (fuera de container, y=440) y `auto_opt` (dentro de `auto_box`, y=630).

| Conexión | Bends antes | Bends ideal |
|---|---:|---:|
| `templates → auto_opt` | 3 | 1 |
| `templates → laf_opt` | 3 | 1 |
| `auto_opt → contract` | 4 | 1 |
| `laf_opt → contract` | 4 | 1 |

**Fix aplicado**:

Nueva función `simplify_orthogonal_zigzag(path, obstacles)` en `visibility_graph.py`. Algoritmo:

```
para cada ventana de N puntos consecutivos [p_i, ..., p_{i+N-1}] en el path:
    para cada esquina candidata corner ∈ {(p_i.x, p_{i+N-1}.y), (p_{i+N-1}.x, p_i.y)}:
        si segmento (p_i → corner) y (corner → p_{i+N-1}) no cruzan obstáculos:
            reemplazar el rango por [p_i, corner, p_{i+N-1}]
            marcar changed
            break
N corre de 4 a 7 (configurable); empezar desde N=4 (más conservador) y subir
si no se encontraron reducciones. Cuando hay reducción, reiniciar al N más
pequeño para permitir cadenas de simplificación.
iterar hasta no haber cambios (acotado por len(path))
limpieza final de puntos colineales
```

Llamada desde `OrthogonalRouter.calculate_path` como post-process, **después** de cualquier estrategia de waypoint computation. Los containers padre de `from`/`to` se excluyen de los obstáculos (no podemos chequearlos como obstáculos porque tenemos que cruzarlos para llegar al destino).

**v1 (commit `32e82a6`)**: ventanas de exactamente 4 puntos.
**v2**: ventanas de 4 a 7 puntos progresivas, mejora `15-architecture-template` (20→18 bends) y casos similares con zig-zags más largos.

**Validación**:

| Métrica | Antes (`e2712e4`) | Después (`32e82a6`) |
|---|---:|---:|
| Bends en `05-arquitectura-gag` (12 conexiones) | 28 total | 16 total (−43%) |
| Conexiones con solo 1 bend | 3/12 | 9/12 |
| Conexiones con ≥3 bends | 8/12 | 1/12 |
| Tests | 70/70 | 70/70 |
| Smoke (canonicals representativos) | OK | OK |
| Determinismo | 1 hash | 1 hash |

**Audit global** sobre los 24 canonicals (regenerando con/sin el fix):

| Diagrama | Bends pre | Bends post | Δ |
|---|---:|---:|---:|
| `05-arquitectura-gag` | 36 | 19 | **−47%** |
| `15-architecture-template` | 37 | 18 | **−51%** |
| `13-stresstest` | 45 | 36 | **−20%** |
| `continentes-america` | 24 | 24 | 0% |
| `svg-to-bwt-flow` | 8 | 8 | 0% |
| `reference-cheatsheet` | 9 | 9 | 0% |
| `git` | 6 | 6 | 0% |
| **TOTAL** (130 conexiones afectadas) | **165** | **120** | **−27%** |

Los otros canonicals no listados (16) no usan routing ortogonal sobre containers, así que no se benefician — pero tampoco se degradan.

**Limitaciones conocidas (no bloquean cierre)**:
- Las 3 conexiones residuales en `05-arquitectura-gag` con 2-4 bends son las que tienen que **cruzar completamente** el `shared_box` (los dos endpoints están en lados opuestos del container y el L-shortcut por encima/debajo del container requeriría puntos que no están en el path original). Resolver eso es re-routing, no simplification — issue distinto.
- La simplificación es **orthogonal-only**. Otros routing types (bezier, arc, straight) no usan este post-process. Si en el futuro vuelven a producir paths con bends innecesarios, mover la simplificación a `router_base.ConnectionRouter`.

---

### BUGS-TPL-001: Architecture Scorer Calibrado Demasiado Conservador ✅ RESUELTO
**Componente**: `AlmaGag/layout/templates/architecture.py` — `ArchitectureTemplate.detect_score`
**Severidad**: Media (arquitecturas claras no reciben el template adecuado y caen al fallback agnóstico)
**Reportado**: 2026-06-23 (test neutro `cakephp-mvc.gag`)
**Resuelto**: 2026-06-23

**Caso de prueba reproducible**:

`docs/diagrams/gags/cakephp-mvc.gag` — arquitectura MVC clásica:
- 3 containers (controllers, models, views) + 1 cross-cutting implícito.
- Entry: `request`. Terminal: `response`. Cadena lineal en medio.
- 19 elementos, 18 conexiones, profundidad topológica 8, sin ciclos.

Es estructuralmente un caso de libro del template `architecture`. Sin embargo, los scores resultantes son:

```
architecture=0.55, er=0.45, sequence=0.40, state=0.40, flow=0.35,
dashboard=0.30, hub_and_spoke=0.25
```

`architecture` queda por debajo del threshold (`0.6`). Cae al fallback agnóstico → canvas alargado 1400×2108 y 6 colisiones.

**Causa raíz**:

El scorer suma:
- `+0.35` por `n_containers >= 2` ✓
- `+0.10` por `n_containers >= 3` ✓
- `+0.20` por keyword `shared`/`compart`/`agnost` ✗ (CakePHP no usa esos términos)
- `+0.10` por DAG ✓
- `+0.15` por depth 3..7 ✗ (depth=8 queda fuera del rango)
- Sin roles declarados (`+0.15` no aplica)

Total: `0.55`. Pierde por dos hilos:
1. La ventana de profundidad `3..7` excluye depth=8, que es perfectamente válido en arquitecturas reales.
2. El bonus por keyword es muy específico a la nomenclatura interna de AlmaGag (`shared (algoritmo-agnóstico)`).

**Diagnóstico**:

El scorer está sobre-ajustado al patrón visual de `05-arquitectura-gag` (que usa la palabra "shared" y tiene depth 5). Cualquier arquitectura sin esa nomenclatura específica o con cadena más larga pierde el template.

**Fix aplicado**:
1. Ventana de depth ampliada `3..7` → `3..10` (arquitecturas reales tienen cadenas más largas).
2. Nuevo bonus por **firma estructural** (`+0.10`): `n_root_nodes_no_incoming == 1` + `n_leaf_nodes_no_outgoing >= 1` + `n_containers >= 2`. Es la señal genérica de arquitectura (entry → containers paralelos → salida), independiente de la nomenclatura.
3. Peso del keyword `shared`/`compart`/`agnost` bajado `0.20` → `0.15` (señal débil, no excluyente).

**Validación** (matriz de scores sobre los 24 canonicals, antes vs después):

| Diagrama | architecture antes | después | winner antes | winner después |
|---|---:|---:|---|---|
| `cakephp-mvc` | 0.55 | **0.80** | —(agnostic) | **architecture** ✓ |
| `05-arquitectura-gag` | 0.75 | 0.95 | architecture | architecture |
| `07-containers` | 0.60 | 0.70 | architecture | architecture |
| `06-flujo-ejecucion` | 0.45 | 0.55 | hub_and_spoke | hub_and_spoke |
| `continentes-america` | 0.20 | 0.35 | —(agnostic) | —(agnostic) |
| resto (21) | — | — | (sin cambios) | (sin cambios) |

**Cero regresiones**: ningún canonical cambió de winner salvo `cakephp-mvc` (el objetivo). `cakephp-mvc.svg` regenerado con architecture: canvas 1400×2108 → 1140×1330 (−58% área).

**Tests**: `tests/test_architecture_scorer_calibration.py` (5 tests: MVC sin keyword supera threshold, cadena profunda ya no descalifica, bonus estructural requiere entry único, canonical cakephp detecta architecture, no-regresión de winners). Suite 84/84.

---

### BUGS-VAL-001: R3 Reporta Falsos Positivos con Conectores Rectos Cortos ✅ RESUELTO
**Componente**: `AlmaGag/validation/visual_quality.py` — `_collect_icon_bboxes`, `check_connections_attached`, `_is_connection_stroke`
**Severidad**: Baja (afecta solo a reportes del validador, no al render)
**Reportado**: 2026-06-23 (test neutro `cakephp-mvc.gag`)
**Resuelto**: 2026-06-23

**Caso de prueba reproducible**:

`docs/diagrams/svgs/cakephp-mvc.svg` — el validador reporta `R3=14` (conectores supuestamente "sueltos"). Inspección visual: los 14 conectores están correctamente atados a sus iconos. Son conexiones rectas (straight routing), porque el `.gag` no declara `routing.type`.

**Causa raíz** (hipótesis):

`check_connections_attached` clasifica como dangling cualquier endpoint cuya distancia a icon_bbox > 20px. Pero:
1. Algunos iconos custom (router, computer, laptop, database) son grupos SVG complejos con `<g transform="translate(x,y)">` en vez de `<rect>` simple. `_extract_icon_bboxes` puede estar derivando bboxes inexactos para estos tipos.
2. La tolerancia de `20px` es razonable para iconos centrados, pero con port_assignment los endpoints caen en bordes del icono. Si el bbox extraído del SVG está desplazado, la distancia queda > 20px aunque visualmente esté atado.

**Validación**:
- En `cakephp-mvc.svg`: 10 iconos detectados por el validador vs 19 elementos en el `.gag` → el validador está perdiendo iconos custom y luego reporta sus conectores como dangling.
- En los canonicals con iconos custom embebidos (`05-arquitectura-gag`), R3 también es alta (30) por el mismo motivo.

**Fix aplicado**:
1. `_collect_icon_bboxes` reescrito para reconocer iconos custom:
   - `_group_transform_bbox`: `<g transform="translate(tx,ty) scale(s)">` → bbox `ICON_W×ICON_H` escalado (factory, gear, contract, iconos SVG embebidos).
   - `_group_children_bbox`: `<g>` con `polygon`/`circle`/`ellipse`/`rect` en coords absolutas → bbox por extensión de hijos (diamond y similares).
   - Mantiene la detección de `<rect>` con gradiente suelto (built-ins) sin duplicar los ya cubiertos por un grupo.
2. Tolerancia R3 `20 → 30px` (port_assignment distribuye los puntos en sectores; offsets de hasta ~25px del centro del lado).
3. `_is_connection_stroke` ahora acepta los colores de la paleta semántica (WISH-LAYOUT-007), que de otro modo dejaban las conexiones coloreadas sin detectar (conns=0).

**Validación** (validador HEAD vs nuevo sobre los mismos 26 SVGs canónicos):

| Métrica | HEAD | Nuevo | Δ |
|---|---:|---:|---:|
| R3 total | 241 | 44 | **−82%** |
| `05-arquitectura-gag` R3 | 30 | 1 | −97% |
| `cakephp-mvc` R3 | 14 | 2 | −86% |
| R1 total | 35 | 51 | +16 (más preciso) |

El alza de R1 es **correcta**: al detectar ahora los iconos custom, el validador captura labels que sí caen sobre ellos (overlaps reales antes invisibles), no falsos positivos.

**Tests**: `tests/test_visual_quality.py` +3 (detección de icono por transform y por polygon, conexión entre custom-icons no es dangling, conexión con color semántico se detecta). Suite 99/99.

**Limitación conocida**: un `connection.color` arbitrario fuera de la paleta semántica (ej. `"color": "red"`) puede no detectarse como conexión por `_is_connection_stroke`. El distinguidor robusto sería "tiene marker" — se deja para v2.

---

## 🌟 WISH

### WISH-ARCH-002: Convergencia a un solo algoritmo (auto-selección) 🚧 EN CURSO
**Componente**: `AlmaGag/generator.py` (`select_strategy`), `main.py`, `AlmaGag/layout/`
**Contexto**: la intención original del autor NO es tener tres algoritmos (auto/laf/hier).
AUTO fue el algoritmo original; LAF nació como **lente de debug por fases** de AUTO (mismo
algoritmo, con visibilidad), no como uno aparte; `hier` recombinó y mejoró ideas de ambos. El
objetivo es **un único motor** que interprete la mejor representación **a partir del JSON**, y
que la representación sólo se fuerce por **parámetro de comando** (nunca por un campo del JSON).
**Decisión (autor, 1a+2a)**: AUTO absorbe a hier (un motor); `areas`/`roles` quedan como
*contenido* del JSON; se saca `layout_view` del JSON (la representación va por `--view`).
**Hecho hasta ahora**:
- `layout_view` eliminado del JSON — la representación se fuerza sólo por CLI (`--view`).
- `--layout-algorithm` default = `select`: `almagag archivo.json` sin flags corre
  `select_strategy(data, view)` que elige la estrategia desde el JSON. Política conservadora:
  vista explícita→hier · contenedores→AUTO (hier no los soporta) · `areas`→hier · rombos
  (decision)→hier · resto→AUTO. Verificado: sólo 3 canónicos enrutan a hier (es-primo,
  activacion, red-areas); los 28 de arquitectura/topología siguen en AUTO. `auto/laf/hier`
  explícitos quedan como override avanzado/debug.
- **(i) Fusión estructural — `AlmaGag/layout/engine.py` (`LayoutEngine`)**: el generator ve UN
  solo optimizer (el engine). El engine elige la estrategia (override CLI > `layout._strategy` >
  'auto') y DELEGA en el optimizer correspondiente, adoptando su `renderer`. hier/laf dejan de ser
  algoritmos peer expuestos al generator → son estrategias internas. Cero regresión por
  construcción (delega en el mismo código): las 3 rutas a hier (deterministas) quedan
  byte-idénticas; las rutas a AUTO varían sólo por un **no-determinismo** que se investigó y
  **RESOLVIÓ** (ver abajo).
- **Determinismo (RESUELTO)**: el "capricho de AUTO" NO estaba en AUTO sino en los **templates**
  `flow` y `hub_and_spoke`: iteraban un `set` de ids de string (`for eid in root_ids`) para
  ordenar niveles/spokes, y el orden de iteración de un set de strings depende de
  `PYTHONHASHSEED` → el layout cambiaba entre procesos. Fix: iterar la lista de elementos (orden
  del input), no el set (`templates/flow.py:_topological_order`, `templates/hub_and_spoke.py:_find_hub`).
  Verificado: los 31 canónicos rinden byte-idénticos con cualquier hash seed. Regresión:
  `tests/test_determinism.py` (subprocesos con seeds distintos).
- **(i) prolijo — las 3 estrategias juntas bajo un motor**: `layout/hier/`, `layout/auto/` y
  `layout/laf/` → **`layout/strategies/{hier,auto,legacy}/`**. Ya no hay algoritmos peer al lado del
  motor: `layout/` sólo tiene `engine.py` + `strategies/`. Se puede cambiar de estrategia, pero
  **AUTO es la principal** (`_STRATEGIES` marca `kind`: base/flow/frozen + `DEFAULT_STRATEGY='auto'`).
  `laf` **renombrado a `legacy`** (motor histórico): CLI `--layout-algorithm=legacy` (ya no `laf`),
  congelado, nunca auto-elegido. Byte-idéntico tras los moves; 251 tests en verde.
- **(ii) LAF diferenciado en dos**: LAF se separó en (a) el **motor histórico** = estrategia
  `legacy` (el placement abstracto-primero con VC/SCC/TOI, congelado), y (b) **Epifanía**, el
  **analizador del proceso de conceptualización** = clase `Epifania` en
  `layout/strategies/legacy/epifania/` (ex-`ConceptualizationAnalyzer`/`GrowthVisualizer`, ambos
  conservados como alias retrocompat): NO posiciona, emite un SVG por fase del análisis (estructura
  → topología → centralidad → abstracción VC → placement → ruteo) para *ver cómo NACE la
  abstracción*. CLI `--epifania` (alias `--debug-phases`, `--visualize-growth`), salida en
  `debug/epifania/<diagrama>/`, títulos "Epifanía · Fase N". *Nombre elegido por José (sobre
  "Janus").*
- **(ii-b) Epifanía agnóstica del motor (paso 2) ✅**: `--epifania` ya no es exclusiva de `legacy`.
  `layout/epifania.py::PhaseRecorder` es un grabador **agnóstico**: hace `deepcopy` del layout en
  cada frontera de fase y re-renderiza cada foto con el *renderer real* de la estrategia → un
  "flipbook" del layout real naciendo etapa a etapa (la última foto es byte-idéntica al SVG final,
  verificado). Las estrategias emiten fases con `self._capture(label, layout, note)` (helper no-op
  de `LayoutOptimizer`, costo cero si no hay grabador); el `LayoutEngine` conecta el grabador sólo
  con `--epifania` y sólo a estrategias vivas (auto/hier) — `legacy` conserva su Epifanía "de lujo"
  (VC/centralidad) porque dibuja internos que sólo ese motor tiene. Fases instrumentadas: AUTO
  (posicionamiento → contenedores → ruteo-inicial → iteración-N por mejora → final); hier
  (niveles-columnas → ruteo → arcos → etiquetas → final; + final-areas/lanes/matrix). Salida:
  `debug/epifania/<diagrama>/NN_<fase>.svg` + `index.html` (hoja de contacto). Las capturas son
  sólo-lectura: **no alteran salida ni determinismo**; camino normal (sin `--epifania`) byte-idéntico.

**Pendiente**: afinar el clasificador con más señales (hoy es intencionalmente conservador);
opcional: portar las piezas de rescate ①/② desde `legacy` a `hier`. Test:
`tests/test_strategy_selection.py`, `tests/test_determinism.py`.

**Dirección de trabajo adoptada**: **AUTO = motor / puerta de entrada** (es el maduro, ya maneja
contenedores y es la puerta de `select_strategy`); **hier = estrategia de flujo** (sus módulos
limpios se conservan y se invocan como estrategia, no como algoritmo peer); **LAF = congelar**
(no borrar aún) y **rescatar 4 piezas** hacia el motor único. Diagnóstico de tamaños: espina
compartida ~2.750 LOC · AUTO placement ~2.500 · hier ~1.960 · LAF engine-VC ~7.800 (el que más
divergió) · LAF `GrowthVisualizer` ~2.450 (rescatable).

**Notas de rescate desde LAF** (portar a la maquinaria hier/AUTO cuando toque; independientes de
la dirección — le sirven al motor gane quien gane):

| # | Idea a rescatar | Fuente en LAF | Destino |
|---|---|---|---|
| ① | **Optimizador por bisección de layer-offset** — desplazamiento de toda una capa como variable continua; minimiza la distancia ponderada de conectores buscando la raíz de la derivada (convexa, ~48 iter, forward/backward, conv. <0.001). El aporte más original/limpio de LAF. | `AlmaGag/layout/laf/position_optimizer.py:416-520` | ✅ **INTEGRADA en AUTO**. Utilidad agnóstica `AlmaGag/layout/offset_optimizer.py::optimize_group_offsets` (`tests/test_offset_optimizer.py`, 6) + pasada `AutoLayoutOptimizer._compact_horizontal`. **Hallazgo empírico**: inerte en hier (carriles ya empaquetados) y en AUTO sin contenedores (barycenter ya bueno); **rinde en AUTO con contenedores** tratando cada contenedor como bloque rígido + libres por fila visual. **Guardada**: sólo adopta si bajan los cruces sin subir colisiones → cero regresión (32 canónicos: 2 mejoran, 30 igual, 0 peor). Medido: git cruces 14→11 / colis 73→64; reference-cheatsheet 8→4 / 35→32. Visible en Epifanía (fase `compactacion`). `tests/test_compaction.py` (3). |
| ② | **Contracción de SCC para levelizar** — contrae cada ciclo/componente fuerte a un representante para correr longest-path sobre un DAG. Más sólido que la detección de back-edges ad-hoc de hier hoy. | `AlmaGag/layout/laf/structure_analyzer.py:1015,1326` | ✅ **INTEGRADA** → `strategies/hier/scc.py` (Tarjan iterativo canónico) alimenta `leveling.py` §A. Los back-edges ahora salen de un feedback set derivado de los SCC (canónico, no del recorrido). **Cero regresión**: DAGs → ∅, ciclo simple → misma arista (14-stresstest byte-idéntico). Robustez nueva: ciclos entrelazados → un SCC + feedback set válido (probado). `tests/test_scc.py` (7). Demo visible en Epifanía: `docs/diagrams/gags/ciclo-retrabajo.sdjf`. |
| ③ | **`count_crossings` O(n²)** — cuenta cruces reales (intersección de segmentos). Métrica barata; ni AUTO ni hier la tienen. Usar como criterio de calidad y test de regresión. | `AlmaGag/layout/laf/abstract_placer.py:1358` | ✅ **INTEGRADA** → `AlmaGag/layout/metrics.py::count_crossings` (agnóstica del motor, centros de iconos; mejora: pares que comparten nodo no cuentan). Visible en **Epifanía** (chip ✕N + delta por fase) y en `tests/test_crossings.py` (9 tests). Reveló: AUTO=16 vs hier=1 cruces en 14-stresstest. |
| ④ | **Constraints declarativas** (`constraints.align/near/avoid`) — idea de producto valiosa y transversal (la impl LAF es un stub: solo `align`). | `AlmaGag/layout/laf/optimizer.py:245-321` | ✅ **INTEGRADA**. Schema top-level `constraints: [...]` (array relacional) en `AlmaGag/layout/constraints.py`; AUTO las aplica como paso final (`align` x/y = coord común, `near` = acercar al centroide, `avoid` = separar solapes). `select_strategy` enruta a AUTO si hay `constraints`. Cero regresión (sin `constraints` → no-op). Visible en Epifanía (fase `constraints`). Demo `docs/diagrams/gags/constraints-demo.sdjf`; `tests/test_constraints.py` (8); documentado en `FORMATO_ARCHIVOS.md`. |

*Bonus menores*: `W_precedence` (peso por skip-connections según distancia de nivel,
`structure_analyzer.py:148-172`); pesos de barycenter dinámicos vert:horiz (`abstract_placer.py:50-89`);
patrón "estimar → medir contenido real → re-expandir" para labels de contenedor
(`container_grower.py:20-33`); snapshots por fase (`GrowthVisualizer`) como práctica de debug al
desarrollar hier.

**Descartado a conciencia** (cubierto por auto/hier o demasiado atado al andamiaje de LAF):
abstracción **VC/TOI** ("tío" — atada al dominio genealógico, y la doc `CONCEPTS.md` la define
distinto que el código → concepto no consolidado; comprimir 11/13 nodos del stresstest en un VC
fue lo que rompió LAF y motivó hier); nomenclatura **NdDp/NdPr/NdFn** (inconsistente); spacing con
constantes mágicas; redistribución half-widths; **dashboard-reflow** (fix reactivo — insight
reutilizable: "componentes desconectados van en grid 2D, no en fila"); iconos-de-contenedor
separados (rendering, no layout). Señales de inmadurez de LAF que refuerzan congelarlo:
hiperparámetros "experimentales" sin defaults, docstrings contradictorios, fases que son fixes
reactivos más que diseño.

---

### WISH-LAF-002: Layout Jerárquico `hier` según Criterios A1–F18 (spec Claude Design) ✅ RESUELTO (v1) (Fases 1-2-3 ✅ — A1–F18 sobre 14-stresstest)
**Componente**: `AlmaGag/layout/hier/` (algoritmo nuevo) — leveling.py (§A), columns.py (§B), optimizer.py; + routing/draw (§C–§F)
**Severidad**: Alta (norte de calidad de layout; caso de regresión `14-stresstest.sdjf`)
**Reportado**: 2026-06-24 (spec "Criterios AlmaGag" generada por el usuario con Claude Design)

**Decisión de enfoque (2026-06-24)**: se implementa como un **algoritmo nuevo `--layout-algorithm=hier`**, NO como retrofit de LAF. Razón: LAF abstrae los nodos en contenedores virtuales (SCC/TOI/loop) — en el stresstest 11/13 nodos colapsan en `_scc_vc_0` y el placement ocurre dentro de esa caja, un modelo incompatible con el "niveles + columnas plano" que asume el spec. Un algoritmo limpio: (a) coincide 1:1 con la referencia, (b) no arriesga los 24 canonicals que usan LAF en CI, (c) reusa la lógica §A. LAF queda intacto.

**Motivación**:

El usuario produjo una especificación completa de layout jerárquico (18 criterios A1–F18, con orden de dependencias y render de referencia) para mejorar la presentación de LAF, usando `14-stresstest.sdjf` como caso de verificación. El render actual dispersa el grafo (canvas 1960×1860), destierra el satélite `L`, mete las tomas `B`/`C` en filas propias y usa 7 niveles donde el spec compacta a 6.

**Gap analysis (estado al abrir el ticket)** — 1 hecho, 6 parciales, 11 ausentes:

| Grupo | Criterios | Estado |
|---|---|---|
| A · Niveles | A1 min-parent · A2 satélites · A3 tomas | A1 **invertido** (usa longest-path/max-parent); A2/A3 parciales |
| B · Columnas | B4 ghosts+barycenter · B5 carriles · B6 alineación · B7 bifurcación · B8 tallo | B7 parcial; B4/B5/B6/B8 ausentes |
| C · Puertos | C9 proyección · C10 lado · C11 tomas | 12 sectores angulares (no proyección); C9/C11 ausentes |
| D · Ruteo | D12 mismo-nivel · D13 cruces · D14 carriles | **D14 hecho**; D12/D13 ausentes |
| E · Arcos | E15 winding · E16 signo · E17 comba | arco no se auto-aplica a ciclos; E16/E17 ausentes |
| F · Etiquetas | F18 lado despejado | parcial |

**Criterios de aceptación**: cada criterio A1–F18 verificado contra `14-stresstest.sdjf` (LAF), tal como describe la sección "verificación" de cada uno en el spec.

**Plan por fases** (respeta el orden de dependencias del spec):
- **Fase 1 — §A+§B** (niveles min-parent, satélites, tomas medio-nivel, ghosts+barycenter, carriles, alineación, bifurcación, tallo). *§A entregada (commit `756a7a0`); §B en progreso.*
  - **§A hecho** (`AlmaGag/layout/hier/leveling.py`): `compute_levels()` puro — min-parent (A1) + satélites (A2, con requisito de padre que continúa el flujo) + tomas a medio-nivel (A3) + back-edges. Verificado contra 14-stresstest: `A=0 D=1 B=1.5 E/H/L=2 F/I=3 C=3.5 G/J=4 K/M=5`.
  - **§B v1 hecho** (`AlmaGag/layout/hier/columns.py`): barycenter (B4) + alineación iterativa al ancestro dominante con sesgo tronco/ciclo (B6) + centrado de bifurcación (B7) + separación mínima por fila + tallo raíz (B8) + satélites al costado / tomas al margen exterior. `14-stresstest` en `hier`: canvas **1380×980** (vs 1960×2150 en LAF), 2 columnas principales limpias, sin solapes.
  - **§B5 hecho** (`columns.py`): carriles cycle-aware — cada componente de ciclo (SCC) recibe un carril propio y los nodos acíclicos se descomponen por spine (DFS de primera visita, hijo de subárbol más profundo continúa el carril). 14-stresstest queda con tronco A·D·E·F·G·M en una columna, ciclo I·J·K en otra, H aparte, satélite L al lado, tomas B/C al margen exterior. Canvas 1480×980.
  - **§B4 hecho** (`columns.py`): nodos fantasma en aristas largas. Hallazgo: bajo min-parent NINGUNA arista forward baja >1 nivel (min-parent garantiza Δ≤1); las largas van de un nodo profundo a uno superficial (Δ negativo), así que la detección es `|Δnivel|>1`. Cada arista larga se parte con un ghost por nivel intermedio; los ghosts entran al barycenter/carriles (reducen cruces) y sus X se exponen como `waypoints` en la conexión para el ruteo (§D).
  - **Fase 1 §A+§B COMPLETA.** Falta la consumación de waypoints por el ruteo (§D, Fase 2).
- **Fase 2 — §C+§D COMPLETA** (`AlmaGag/layout/hier/routing.py`): produce `connection['computed_path']`.
  - C9 puertos por proyección del otro extremo sobre el borde (fracción 0.16–0.84), separados por borde.
  - C10 lado del puerto según eje de flujo + llegada perpendicular.
  - C11 ruteo de tomas (salida lateral → horizontal → bajada vertical, 3 puntos).
  - D12 aristas de mismo nivel en recta; D13 cruces reales en recta (bifurcación/fusión conservan codo); D14 carriles de canal (offset por pista).
  - Consume los waypoints §B4. Las back-edges quedan sin path → arco §E (Fase 3). Conexiones a contenidos (sin posición) se saltan sin romper.
- **Fase 3 — §E+§F COMPLETA**:
  - §E (`AlmaGag/layout/hier/arcs.py`): aristas de ciclo como bezier con winding coherente. E15: signo global sobre la normal de la dirección → ida interior, retorno exterior automáticamente. E16: signo elegido desde la back-edge para que su normal apunte lejos del centroide. E17: comba adaptativa (base 44px, crece para librar nodos con proyección interior a la cuerda y perp<72px del lado de la comba, tope 320px).
  - §F18 (`AlmaGag/layout/hier/labels.py`): etiqueta al borde menos concurrido (cuenta conectores por T/B/L/R, desempate abajo→arriba→exterior→interior); setea `label_position`.
  - **§B7 v2 (simetría)**: se completó el centrado de la bifurcación. El tallo (bifurcación superior + ancestros de hijo único) se separa a su propio carril y se centra entre las columnas hijas; además el nodo de entrada del ciclo (H) se fusiona a la columna del ciclo (H·I·J·K vertical, sin diagonal larga H→I). 14-stresstest queda simétrico: tallo A·D centrado, ciclo a un lado, tronco al otro.

**QA de Claude Design (2026-07-13)** — evaluó el render y aprobó el layout («el layout ya está bien; el bug es uno solo»), detectando un único bug de trazado (etapas 10-11): los conectores quedaban recortados 40px (flujo) / 15px (arcos) antes del borde en vez de tocarlo. Corregido:
- Q1/Q3: los puertos hier (ya sobre el borde) se marcan como `_from_port`/`_to_port` → el renderer NO aplica su offset. Arcos: extremos recortados al borde con `clip_to_border` (función única).
- Q2: `_perp_stubs` garantiza un tramo final perpendicular ≥14px (aun en aristas de cruce/rectas) → flechas derechas.
- Q4: la toma sale por el COSTADO hacia el destino (no por el fondo) → salida horizontal + bajada vertical al borde superior.
- Q5: `tests/test_hier_geometry.py` — asserts geométricos (extremos en borde, llegada perpendicular) sobre el stresstest + 24 canónicos; evasión de obstáculos (d) validada en el stresstest.

**QA de Claude Design (2026-07-14) — evaluación es-primo (extensión G19–G23)**: se generó una POC de flowchart (`¿es n primo?`, con rombos de decisión y bucle `while`) y Claude Design la evaluó, extendiendo el spec con cinco criterios nuevos. Todos resueltos (**Fase G**):
- **G19** (`AlmaGag/layout/hier/shapes.py`): el recorte de puertos respeta el POLÍGONO real de la forma, no su bbox. Rombos (`decision`/`diamond`) usan convención flowchart: entrada por el vértice superior; salidas por izquierdo/derecho/inferior (un puerto por vértice, sin fracciones). `routing.py` snapea los puertos de rombo al vértice según dirección dominante; `arcs.py` recorta contra el rombo (`clip_shape`). Los conectores dejan de "flotar" en las esquinas vacías del bbox.
- **G20** (`leveling.py`): un sumidero (0 salidas, ≥2 padres acíclicos) baja a `max(nivel de padres)+1` en vez de subir por min-parent → los terminales del flowchart (NO es primo / ES PRIMO) caen al fondo, cerca de sus orígenes.
- **G21** (`columns.py`): asignación de carriles reescrita a *spine + hijo primario «menos padres»* con fusión de carriles-singleton hacia el head-child; el carve del tallo y el centrado B7 se restringen a bifurcaciones **reales** (excluyen fantasmas). `es-primo` queda en columna única; `14-stresstest` conserva la mariposa simétrica.
- **G22** (`optimizer.py`): contención del viewBox — se reúne toda la geometría (iconos, polylines, waypoints, control-points de bezier, anclas de rótulo), se traslada al espacio positivo si algo se salió por arriba/izquierda (tomas a medio nivel) y se expande el canvas. `bbox(paths) ⊆ viewBox` verificado sobre todos los canónicos.
- **G23** (`labels.py`): el rótulo de conexión (sí/no/repetir) se ancla a ~14px del puerto de SALIDA sobre el primer segmento; el renderer lo prioriza sobre el optimizador de etiquetas.

**QA de Claude Design (2026-07-14) — evaluación v3 (§H)**: midió el es-primo regenerado. Confirmó Q1–Q3 (borde a borde), G20 (not_prime al fondo), G21 (tronco recto), G22 (dentro del viewBox) y E15–E17 (lazo). Quedaban tres defectos de calidad de ruteo, todos resueltos (**Fase H**):
- **H24** (`routing.py`): ruteo largo ortogonal PURO. Se reemplazó el seguimiento diagonal de waypoints por `_ortho_route(p_from, sf, p_to, st, channel)` — router radial que respeta la dirección del puerto (primer/último tramo perpendicular al borde) y sólo emite codos de 90°. Diagonales permitidas únicamente en rectas de 2 puntos (§D12 mismo nivel / §D13 cruces reales) y arcos de ciclo (§E, bezier). Nuevo test `test_all_canonicals_no_diagonal_elbows`.
- **H25** (`columns.py`): el sumidero compartido (0 hijos, ≥2 padres reales) se reubica en la columna ADYACENTE al baricentro de sus padres, del lado libre (menos poblado), en vez de caer al margen lejano. En es-primo `not_prime` pasa de x=110 (4 carriles) a un carril del tronco → aristas cortas y paralelas. Usa `orig_parents` (padres reales antes de la cirugía de ghosts §B4).
- **H26** (`routing.py`): puertos de rombo estrictamente en el vértice, sin micro-codo. La salida se asigna considerando TODAS las aristas del rombo: la que baja recto (menor |Δx|) toma el vértice inferior; las demás salen por el lateral izq/der → el «sí» ya no roba el vértice inferior al «no», y el primer tramo sale radial (sin quiebre a <15px del puerto).

**Fase I+J (2026-07-14) — áreas, roles y densidad** (spec `Criterios AlmaGag.dc.html`, render de referencia `Activacion DC Render.dc.html`). El caso `activacion-datacenter.sdjf` se emitía como una tira de 980×5060; el spec añadió §I27–§I30 y §J30–§J33 para repartirlo a lo ancho. Implementado:
- **J30** (`optimizer.py`): paso vertical = icono + holgura fija (`ICON_HEIGHT+42` ≈ 92px) en vez de 170. es-primo 980→590, activacion 5060→2798 antes de áreas.
- **J31/J32** (`labels.py::wrap_label`): etiquetas partidas por palabras en ≤3 líneas dentro de un ancho máximo (~180px) con «\n»; truncado con «…» si excede. `apply_label_wrapping` corre en el optimizer.
- **I27** (`AlmaGag/layout/hier/areas.py`, nuevo): si el SDJF trae `areas:[{id,label,members,color?}]`, cada área es un sub-lienzo — corre A–H sobre su subgrafo intra-área (reusa `compute_levels`/`compute_columns`/`route_*`), se dimensiona al contenido + etiquetas (label-aware bbox, paso ampliado §J30) y se empaqueta izquierda→derecha (§J33). `optimizer._optimize_areas` despacha cuando hay `areas`.
- **I29** (`areas.py::_route_inter_area`): una arista entre áreas sale por el borde de la caja origen, cruza el corredor entre cajas y entra por el borde de la caja destino; ningún tramo cruza una 3ª caja.
- **I30** (`draw/primitives/phase_areas.py` + `auto_renderer.py`): cajas de fase punteadas rotuladas (fondo); rol por color (barra lateral en cajas, punto en rombos) desde `role` + `roles:{key:{label,color}}`; leyenda de responsables en la franja inferior. Etiquetas de nodo centradas bajo el icono (placement propio, sin el optimizador AUTO).
- Resultado: `activacion-datacenter.sdjf` pasa de 980×5060 (tira) a **2910×1022** (5 fases a lo ancho, roles por color, aristas inter-área cruzando bordes). Tests `test_hier_density.py` (6) + `test_hier_areas.py` (7).

**§I28 + selección de vista (2026-07-14)** — carriles por rol + sistema de vistas híbrido. Se separó **dato** (fase/rol) de **vista** (cómo se agrupa):
- **Selección híbrida**: prioridad `--view` (CLI) > `layout_view` (campo del SDJF) > `auto` (código decide: `areas` si las hay, si no `flow`). Resuelto en `generator.py`; despachado en `optimizer.optimize` por `_layout_view`. Valores: `flow|areas|lanes|matrix`. `matrix` aún no implementada (cae a `areas` con warning).
- **§I28** (`AlmaGag/layout/hier/lanes.py`, nuevo): carriles verticales por rol. Y = nivel de flujo (reusa §A + ruteo §C–§E), X = banda del carril; si no hay `lanes:[…]` explícito se derivan del campo `role`. Franjas de fondo rotuladas (`draw_lane_strips`); cruzar carril = handoff. Es la vista clásica de swimlanes ("¿quién?").
- La misma `activacion-datacenter.sdjf` rinde ahora en 3 vistas: `areas` 2910×1022 (a lo ancho), `lanes` 1550×2856 (swimlanes), `flow` 980×2798 (tira). `--view` en `main.py`; `layout_view`/`lanes` documentados en `docs/spec/FORMATO_ARCHIVOS.md §0.3`.
- Tests `test_hier_lanes.py` (6).

**Vista `matrix` (fase×rol) (2026-07-14)** — `AlmaGag/layout/hier/matrix.py` + `draw_matrix_grid`. La vista más completa (el spec la ofrecía "solo bajo petición" por lo cara de rutear): grilla con **fase en columnas** y **rol en filas**; cada nodo cae en la celda (fase, rol) y si varios comparten celda se apilan por nivel de flujo. Es el flowchart transfuncional clásico (BPMN cross-functional). Headers de fase arriba, bandas de rol tintadas con rótulo a la izquierda, separadores de columna. Requiere `areas` + `role`. `activacion-datacenter.sdjf` en `--view=matrix` → 5×7 celdas, 1318×2564. Tests `test_hier_matrix.py` (3). Con esto las 4 vistas del sistema §I están completas: `flow` | `areas` | `lanes` | `matrix`.

**Bugfix etiquetas agrupadas (2026-07-14)**: `apply_label_wrapping` exigía `x` en el elemento → en áreas/carriles/matriz (que envuelven antes de posicionar) las etiquetas no se partían. Quitado el guard (envolver un string no necesita coords). Además en `lanes` el ancho de carril se hizo proporcional al máximo de nodos por nivel para que dos etiquetas centradas (satélite + padre) no se solapen. §J32 sólo trunca, no maqueta notas externas.

Registro: `--layout-algorithm=hier` en `main.py` + `generator.OPTIMIZERS`. Reusa `AutoSVGRenderer` para el dibujo. Tests en `tests/test_hier_layout.py`, `test_hier_routing.py`, `test_hier_arcs_labels.py`, `test_hier_geometry.py` (210 en total con la Fase H). LAF y sus 24 canonicals quedan intactos. Limitación Fase 1: `hier` posiciona sólo elementos root (grafos planos); el soporte de containers vendrá después.

---

### WISH-ARCH-001: LAFOptimizer Cumpla el Contrato LayoutOptimizer ✅ RESUELTO
**Componente**: `AlmaGag/layout/laf/optimizer.py` + `AlmaGag/generator.py`
**Severidad**: Media-Alta
**Reportado**: 2026-05-14 (detectado durante refactor de routing_policy)
**Resuelto**: 2026-06-18

**Estado anterior**:
- `AutoLayoutOptimizer` hereda de `LayoutOptimizer` (clase base en `optimizer_base.py`).
- `LAFOptimizer` no hereda de nadie y tiene firma de `__init__` distinta (recibe colaboradores por inyección).
- `generator.py` usa `if/elif layout_algorithm == ...` para distinguir (líneas ~578, ~625).
- `render_containers()` recibe `layout_algorithm` como parámetro.

**Fix aplicado** (Tier 1):
1. `LAFOptimizer` ahora hereda de `LayoutOptimizer`.
2. `__init__` self-contained: construye sus deps internamente. Acepta inyección opcional (retrocompat).
3. `optimize()` firma unificada: `(layout, max_iterations=10, dump_iterations=False, input_file=None)`. LAF ignora los kwargs que no aplican.
4. `LAFRoutingPolicy` se uniformó con `AutoRoutingPolicy` — acepta `sizing` y construye `router_manager` internamente. Modo legacy preservado.
5. `generator.py` ahora usa **factoría** (`OPTIMIZERS = {'auto': ..., 'laf': ...}`) en lugar de `if/elif`. Una sola llamada a `optimizer.optimize(...)` para ambos.

**Lo que NO se hizo en este fix** (queda como deuda separada):
- `layout_algorithm` sigue propagándose a `render_containers()` y `draw_container()` para decidir si dibujar el icono inline (AUTO) o como elemento separado (LAF). Es una decisión de **renderizado**, no de optimizer. Registrado como **WISH-ARCH-002**.

---

### WISH-ARCH-002: Eliminar `layout_algorithm` del Renderer ✅ RESUELTO
**Componente**: `AlmaGag/renderer.py` (eliminado) → `layout/auto/renderer.py` + `layout/laf/renderer.py`
**Severidad**: Media
**Reportado**: 2026-06-18 (follow-up explícito de WISH-ARCH-001)
**Resuelto**: 2026-06-18

**Fix aplicado** — separación total entre algoritmos (más fuerte que la Opción A original):
- `AlmaGag/renderer.py` (509 líneas, compartido) **eliminado**.
- `AlmaGag/draw/svg.py` **NUEVO**: primitivas SVG agnósticas (create_canvas, setup_arrow_markers, draw_connections, ndfn_wrap, etc.).
- `AlmaGag/layout/auto/renderer.py` **NUEVO**: clase `AutoSVGRenderer` con toda la orquestación AUTO (no sabe que LAF existe).
- `AlmaGag/layout/laf/renderer.py` **NUEVO**: clase `LAFSVGRenderer` con toda la orquestación LAF, incluyendo `_render_container_icons` (LAF-only).
- Cada optimizer expone `self.renderer` en `__init__`.
- `generator.py` ahora llama `optimizer.renderer.render(layout, output_svg, ...)`.

**Principio aplicado**: "un algoritmo no sabe que el otro existe". Los renderers solo dependen de:
- `AlmaGag/draw/` (primitivas de íconos compartidas)
- `AlmaGag/debug.py` (helpers de debug compartidos)
- `AlmaGag/layout/label_optimizer.py` (optimizador de labels compartido)

**Estructura final**:
```
AlmaGag/
├── draw/
│   ├── svg.py           ← primitivas SVG agnósticas
│   ├── connections.py   (compartido)
│   ├── container.py     (compartido)
│   └── icons.py + 12 tipos
└── layout/
    ├── auto/
    │   ├── optimizer.py
    │   ├── routing_policy.py
    │   └── renderer.py  ← AutoSVGRenderer
    └── laf/
        ├── optimizer.py
        ├── routing_policy.py
        └── renderer.py  ← LAFSVGRenderer
```

**Validación**: smoke 46/46 SVGs, determinismo 3/3 archivos × 3 seeds = 1 hash único, tests 17 passed.

**Descripción**:
Tras resolver WISH-ARCH-001 (contrato del optimizer unificado), queda un residuo de la asimetría AUTO/LAF **en la capa de renderizado**: el parámetro `layout_algorithm` se sigue pasando a `render_containers()` y `draw_container()` para decidir cómo dibujar el icono del container.

**Comportamiento actual**:
- **AUTO**: el icono del container se pinta **inline**, en la esquina superior izquierda del rect del container.
- **LAF**: el icono del container se pinta como **elemento separado**, con su propia (x, y) en el grid del SVG.

El renderer necesita saber qué algoritmo produjo el layout para elegir el modo. Eso es:
1. **Acoplamiento innecesario**: el renderer está atado a los nombres `'auto'` / `'laf'`.
2. **Falsa extensibilidad**: agregar un tercer algoritmo requeriría tocar el renderer.
3. **Decisión en el lugar equivocado**: "¿el icono va inline o separado?" es info del **layout** (cómo se posicionaron los containers), no del **algoritmo** abstracto.

**Por qué es WISH y no BUGS**:
El código **funciona correctamente** — ambos modos producen renders válidos. Es asimetría arquitectural que querrías limpiar, no un bug funcional.

**Solución propuesta — Opción A (recomendada): Flag en el container**

Cada optimizer marca los containers con cómo deben renderizarse:

```python
# AutoLayoutOptimizer.optimize() antes de retornar:
for container in containers:
    container['_icon_inline'] = True

# LAFOptimizer.optimize() antes de retornar:
for container in containers:
    container['_icon_inline'] = False  # el icono es elemento separado
```

Renderer queda agnóstico:
```python
def draw_container(dwg, container, elements_by_id, draw_label=True, draw_icon=True):
    # Ya no recibe layout_algorithm
    if draw_icon and container.get('_icon_inline', True):
        # dibuja el icono en la esquina
```

**Soluciones alternativas**:
- **B**: Unificar comportamiento (ambos algoritmos rinden inline, o ambos separado). Cambio visual visible en SVGs existentes.
- **C**: Strategy pattern en el renderer (`InlineIconContainerRenderer` / `SeparateIconContainerRenderer`). Más OOP pero overkill.

**Impacto del fix**:
- Cambio: ~3-5 líneas en cada optimizer + simplificación en `draw/container.py` y `renderer.py`.
- Re-render afectado: 5 SVGs con containers, deberían quedar visualmente idénticos.
- Riesgo: bajo. Cambio puramente refactorial.

**Estimación**: ~30 min de implementación + 15 min de validación visual.

**Prioridad**: Media (deuda residual de WISH-ARCH-001; mejora cosmética del código).

**Validación**: 46/46 SVGs smoke OK; determinismo 3/3 archivos × 3 seeds intacto; tests 17/2.

**Por qué es WISH y no BUGS**:
El código **funciona**: LAF corre OK, los renders son válidos. Es asimetría arquitectural que querrías limpiar, no un crash o resultado incorrecto.

**Impacto**:
- Acoplamiento entre algoritmo de layout y fases posteriores.
- Imposible agregar un tercer algoritmo sin modificar `generator.py`.
- El Strategy Pattern documentado en `ARCHITECTURE.md` no se cumple en la práctica.
- Es la causa de la asimetría en `routing_policy.py`.

**Solución propuesta**:
- Hacer que `LAFOptimizer` herede de `LayoutOptimizer`.
- Unificar firma `optimize(layout, **kwargs) -> Layout`.
- Eliminar `layout_algorithm` como parámetro propagado a `render_containers`.
- Cuando se resuelva, el constructor de `LAFRoutingPolicy` probablemente se uniformará con el de `AutoRoutingPolicy`.

---

### WISH-ARCH-003: Tier 2 Refactor — Reorganizar `draw/` + Split de `visualizer.py` ✅ RESUELTO
**Componente**: `AlmaGag/draw/` + `AlmaGag/layout/laf/visualizer.py`
**Severidad**: Media (deuda estructural, no funcional)
**Reportado**: 2026-06-18
**Resuelto**: 2026-06-18

**Fix aplicado**:

**Sub-tarea A — Reorganizar `draw/`** (commit `f51794f`):
```
draw/
├── primitives/                  ← svg, container, connections, callout
└── icons/                       ← __init__ (dispatcher) + 11 tipos
```
- 11 iconos movidos a `draw/icons/` vía `git mv` (historia preservada).
- 4 primitivas movidas a `draw/primitives/` vía `git mv`.
- Dispatcher renombrado: `draw/icons.py` → `draw/icons/__init__.py`.
- 3 dynamic imports actualizados, imports estáticos en renderers actualizados.

**Sub-tarea B — Split de `visualizer.py`**:
Antes: 1 archivo de 2876 líneas con `GrowthVisualizer` + 10 `_generate_phaseN_svg`.
Después: paquete `visualizer/` con 1 archivo por fase + class slim.

```
laf/visualizer/
├── __init__.py              (862 líneas, class GrowthVisualizer + helpers + thin wrappers)
├── phase1.py                (322 líneas)
├── phase2_topology.py       (555 líneas)
├── phase3_centrality.py     (298 líneas)
├── phase4_abstract.py       (245 líneas)
├── phase5_optimized.py      (212 líneas)
├── phase7_iterative.py      (373 líneas)
├── phase8_inflated.py       (53 líneas)
├── phase9_redistributed.py  (48 líneas)
├── phase10_routed.py        (48 líneas)
└── phase11_final.py         (48 líneas)
```

Cada `phaseN_*.py` expone `def generate(viz, output_path)` con el body original (self → viz transformados). Los `_generate_phaseN_svg` de la clase quedan como thin wrappers de 3 líneas:
```python
def _generate_phase1_svg(self, output_path: str) -> None:
    from AlmaGag.layout.laf.visualizer import phase1
    phase1.generate(self, output_path)
```

Helpers internos (`_draw_colored_connections`, `_segments_intersect`, `_are_collinear`, `_build_ndpr_positions`, `_draw_ndpr_node`, `_build_ndfn_labels`, `_draw_elements_with_ndfn`, `_draw_straight_connections`, `_draw_routed_connections`) quedaron en la clase para acceso vía `viz.X` desde cualquier fase.

Refactor mecánico: script `split_visualizer.py` extrajo cada fase + script `fix_helpers.py` reubicó helpers misplaced.

**Validación**:
- Smoke 46/46 OK (23 × 2 algoritmos).
- Tests 19 passed.
- `--visualize-growth` genera las 10 fases SVG correctamente.
- 0/23 canonical SVGs afectados.
- Refactor puro, sin cambios funcionales. (durante el ciclo Tier 1)

**Estado actual**:
1. **`AlmaGag/draw/` plano con 16+ módulos mezclados**:
   ```
   draw/
   ├── svg.py            ← primitivas SVG agnósticas (creado en WISH-ARCH-002)
   ├── icons.py          ← dispatcher de iconos
   ├── container.py
   ├── connections.py
   ├── bwt.py            ← banana with tape (fallback)
   ├── server.py, cloud.py, building.py, database.py, ...  ← tipos de iconos
   └── ...
   ```
   La mezcla de "primitivas + dispatcher + tipos concretos + utils" en un mismo paquete dificulta navegar y agregar nuevos tipos sin tocar todo.

2. **`AlmaGag/layout/laf/visualizer.py` con ~2900 líneas**: contiene `GrowthVisualizer` que captura snapshots SVG de cada fase del pipeline LAF para `--visualize-growth`. Una sola clase con 11 métodos `capture_phaseN_*`, cada uno con lógica de renderizado específica (muchas duplicaciones del renderer principal).

**Solución propuesta**:

Sub-tarea **A — Reorganizar `draw/`**:
```
draw/
├── primitives/
│   ├── svg.py           ← create_canvas, markers, ndfn_wrap, draw_connections
│   ├── container.py
│   └── connections.py
├── icons/
│   ├── __init__.py      ← dispatcher (importlib)
│   ├── server.py
│   ├── cloud.py
│   ├── ... (1 archivo por tipo)
│   └── bwt.py           ← fallback
└── __init__.py
```

Sub-tarea **B — Split de `visualizer.py`**:
```
laf/
├── visualizer/
│   ├── __init__.py            ← exports GrowthVisualizer
│   ├── base.py                ← clase + utils compartidos
│   ├── phase1_structure.py
│   ├── phase2_topology.py
│   ├── phase3_centrality.py
│   ├── phase4_abstract.py
│   ├── phase5_optimized.py
│   ├── phase6_ndpr_expanded.py
│   ├── phase7_iterative.py
│   ├── phase8_inflated.py
│   ├── phase9_redistributed.py
│   ├── phase10_routed.py
│   └── phase11_final.py
```

Cada `phaseN_*.py` expone una función `capture(visualizer, ...args)` que el `GrowthVisualizer` invoca. Reduce el tamaño de cada archivo a 200-400 líneas y permite testear fases individualmente.

**Por qué es WISH y no BUGS**:
El código funciona correctamente. Es organización del código, no corrección de comportamiento.

**Impacto del fix**:
- Sub-tarea A: ~30 min, sin cambios funcionales, solo `git mv` + actualizar imports.
- Sub-tarea B: 2-3 horas, mayor riesgo por el tamaño (~2900 líneas), pero el resultado deja cada fase auto-contenida.
- Re-render afectado: ninguno (refactor puro).

**Estimación**: 1 día (medio refactor + medio validación visual).

**Prioridad**: Media-baja. No bloquea features pero mejora mucho la mantenibilidad del módulo de visualización.

---

### WISH-LAF-001: Más Optimización de Cruces de Conexiones ✅ RESUELTO (v1: pesos dinámicos)
**Componente**: `AlmaGag/layout/laf/abstract_placer.py` — Fase 4 (barycenter)
**Severidad**: Baja
**Reportado**: 2026-01-21
**Resuelto**: 2026-06-18

**Fix v1 aplicado** — propuesta #1 del ticket original (ajuste dinámico de pesos):

- **`config.py`** — 2 constantes nuevas: `BARYCENTER_PREV_WEIGHT_MIN = 0.5`, `BARYCENTER_PREV_WEIGHT_MAX = 0.85`.
- **`AbstractPlacer._compute_barycenter_weights(structure_info)`** — calcula `(prev_w, same_w)` según la proporción vertical:horizontal del grafo:
  - Grafo puramente vertical (ratio=1.0) → `prev_w = 0.85`.
  - Grafo balanceado (ratio≈0.5) → `prev_w ≈ 0.675`.
  - Grafo con muchas same-layer connections (ratio=0.0) → `prev_w = 0.5`.
- Pesos cacheados en `self._prev_weight`, `self._same_weight` durante `place_elements()`.
- Reemplazan los 4 hardcoded `0.7` / `0.3` en `_calculate_barycenter`, `_calculate_barycenter_backward`, `_calculate_barycenter_from_graph`, `_calculate_barycenter_backward_from_graph`.

**Distribución observada** en las 23 fuentes:
- 16 archivos: `prev_w=0.85` (grafos verticales puros — arquitecturas, flujos).
- 5 archivos: `prev_w` entre 0.69-0.83 (grafos mixtos).
- 2 archivos: `prev_w` entre 0.64-0.69 (`git`, `roadmap-versions` — más same-layer).

**Métrica de cruces (Fase 5)**: idéntica antes y después del fix (787 cruces totales en 23 archivos).

**¿Por qué no bajan los cruces?** En la práctica el orden topológico domina: dentro de cada capa los elementos se ordenan por barycenter, y el cambio de pesos modifica el VALOR pero rara vez el ORDEN relativo. Para reducir cruces hace falta atacar el problema con otras técnicas (propuestas #2 y #3 del ticket original).

**Lo que NO se hizo en v1 (queda como follow-ups)**:
- **Edge straightening post-procesamiento**: nueva sub-fase después de Fase 5 que mueve nodos en pequeñas magnitudes para enderezar líneas que cruzan tangencialmente. Requiere modificar `position_optimizer.py`.
- **Heurística por tipo de diagrama**: aprender de un corpus de SDJF qué tipo de layout (architecture/flow/poster) se beneficia de qué presets.

Estos follow-ups se registran agrupados como `WISH-LAF-001 follow-up`.

---

### WISH-LAYOUT-001: Sistema de Etiquetas Inteligente ✅ RESUELTO (cerrado por implementaciones existentes + follow-ups específicos)
**Componente**: Label positioning (transversal)
**Severidad**: Enhancement
**Reportado**: 2026-01-21
**Resuelto**: 2026-06-18

**Por qué se cierra**:
El ticket original era un paraguas vago. Al auditar el código, los 3 sub-objetivos están cubiertos por implementaciones existentes o por tickets más específicos.

**Mapeo bullet-a-implementación**:

| Sub-objetivo original | Estado | Implementación |
|---|---|---|
| Detectar colisiones de etiquetas entre sí y con elementos | ✅ Cubierto | `AlmaGag/layout/label_optimizer.py::LabelPositionOptimizer` con penalty system (`PENALTY_COLLISION_ELEMENT=100`, `PENALTY_COLLISION_LABEL=50`, `PENALTY_COLLISION_LINE=75`). Detección activa en cada render. |
| Ajustar posición automáticamente (arriba/abajo/laterales) | ✅ Cubierto | `LabelPositionOptimizer.optimize_labels()` prueba posiciones canónicas en orden (`bottom`, `right`, `top`, `left`) eligiendo la de menor score combinado (colisiones + densidad local + bounds). |
| Usar "leaders" (líneas guía) cuando se separa etiqueta del elemento | ✅ Cubierto | `WISH-LAYOUT-003` resuelto al 2026-06-18: `AlmaGag/draw/primitives/callout.py::draw_callout()` dibuja un leader line semipunteado desde el centro del icono al callout box. |

**Lo que sigue siendo deuda** (registrado como follow-ups específicos, no parte del paraguas original):

- **`WISH-LAYOUT-002` follow-up** (`constraints.near` / `constraints.avoid`): integración de proximidad/alejamiento en el barycenter de Fase 4. NO es de etiquetas; lo agrupé acá al cerrar v1 porque ambos tocan posicionamiento, pero conceptualmente no pertenece a este paraguas.
- **`WISH-LAF-001` follow-up** (edge straightening + heurística por tipo): optimización de cruces en Fase 5. NO es de etiquetas; misma razón.
- **Mejora del placement de callouts** (smart placement vía `CollisionDetector` en lugar del fallback derecha→abajo actual): es una mejora natural del callout v1 pero queda fuera de este paraguas — abrir si hace falta como `WISH-LAYOUT-003` v2.

**Referencias originales** (mantenidas como inspiración para futuros tickets de este área):
- Graphviz label placement algorithms.
- D3.js force-directed label positioning.

---

### WISH-LAYOUT-003: Auto-Callout para Labels Grandes ✅ RESUELTO (v1)
**Componente**: `AlmaGag/draw/callout.py` (nuevo) + ambos renderers
**Severidad**: Media
**Reportado**: 2026-06-15
**Resuelto**: 2026-06-18

**Fix v1 aplicado**:

- **`config.py`** — 6 constantes nuevas:
  - `CALLOUT_MIN_LINES = 6` (umbral conservador para no afectar diagramas existentes).
  - `CALLOUT_MIN_CHARS = 150`.
  - `CALLOUT_BOX_PADDING = 10`.
  - `CALLOUT_LEADER_OFFSET = 40` (gap entre icono y callout box).
  - `CALLOUT_BOX_FILL_OPACITY = 0.85`.
  - `CALLOUT_LEADER_DASHARRAY = "4,3"` (línea semipunteada).

- **`AlmaGag/draw/callout.py`** (nuevo, ~135 líneas) — API:
  - `should_use_callout(elem, label_text)` — detección con override `"callout": true/false` en SDJF.
  - `get_canonical_label(label)` — primera línea como label visible adyacente al icono.
  - `calculate_callout_position(elem, canvas_w, canvas_h)` — v1: derecha del icono con fallback a abajo si overflow.
  - `draw_callout(dwg, elem, full_text, canvas_w, canvas_h)` — renderiza rect + text multilínea + leader line.

- **`auto_renderer.py` + `laf_renderer.py`** — `_render_element_labels()` modificado:
  - Detecta callout, renderiza label canónico en el icono, dibuja callout box.
  - Cambio replicado en ambos renderers (siguen independientes desde WISH-ARCH-002).

**Override explícito**: SDJF puede forzar/desactivar con `"callout": true/false` por elemento (gana sobre umbrales).

**Validación**:
- Caso sintético `callout_test.sdjf` con label de 12 líneas (Pipeline LAF 11 fases): callout box renderizado + leader line ✓.
- **0/23 canonical SVGs afectados** (umbral conservador deja diagramas existentes intactos).
- Smoke 46/46 OK.
- Tests 19 passed.
- Determinismo: 1 hash único × 3 seeds × 3 archivos.

**Limitaciones de v1 (follow-ups documentados como parte de `WISH-LAYOUT-001`)**:
- Placement naive (derecha con fallback a abajo). No usa `CollisionDetector` para evitar solapamientos con otros elementos.
- No participa del collision detection del `LabelPositionOptimizer`.
- Si hay múltiples callouts en el mismo cuadrante, se solapan.

Estas mejoras se integran al sistema más amplio de etiquetas inteligente (WISH-LAYOUT-001).

---

### WISH-LAYOUT-002: Soporte para Restricciones de Posicionamiento ✅ RESUELTO (v1: solo `align`)
**Componente**: `AlmaGag/layout/laf/optimizer.py` — nueva Fase 1.4
**Severidad**: Enhancement
**Reportado**: 2026-01-21
**Resuelto**: 2026-06-18

**Fix v1 aplicado**: soporte para `constraints.align` en SDJF.

```json
{
  "elements": [
    {
      "id": "database",
      "type": "database",
      "constraints": {"align": "bottom"}
    }
  ]
}
```

Valores soportados:
- `"top"` → fuerza nivel topológico 0.
- `"bottom"` → fuerza nivel topológico max (=N-1 niveles).
- `"center"` → fuerza nivel topológico max // 2.

**Implementación**:
- Nuevo método `LAFOptimizer._apply_alignment_constraints()`.
- Llamado entre Fase 1.5 (dashboard reflow) y Fase 2 (topology display).
- Modifica `structure_info.topological_levels` Y `ndpr_topological_levels` (este último es lo que usa la fase iterativa 4-5-6 vía NdPr; sin actualizarlo el constraint se ignoraba).
- Descendientes heredan el nivel del ancestro alineado.

**Validación**:
- Caso `legend con align:bottom`: elemento sin conexiones bajaba a nivel 0 → ahora va a nivel max. ✓
- Caso `trigger con align:top`: ya estaba en nivel 0, no movement (comportamiento correcto). ✓
- Caso `trigger con align:center` en grafo de 5 niveles: trigger pasa de nivel 0 a un nivel medio. ✓
- Smoke 46/46 OK, tests 19 passed, determinismo intacto.
- 0/23 canonical SVGs afectados (los canonical no usan `constraints`).

**Lo que NO se implementó en v1 (queda como deuda separada)**:

- **`near: ["api", "cache"]`** — agruparía elementos por proximidad horizontal. Requeriría integrar pesos en el barycenter de Fase 4 (`abstract_placer.py`). Más complejo porque hay que balancear con la minimización de cruces.
- **`avoid: ["frontend"]`** — alejaría elementos. Mismo nivel de complejidad que `near` pero con peso negativo.

Estas dos quedan como **follow-up de WISH-LAYOUT-002**: requieren entender la interacción con cruces/Sugiyama y probablemente merecen un sub-ticket o entrada en `WISH-LAYOUT-001` (etiquetas inteligentes ↔ posicionamiento inteligente).

---

### WISH-LAYOUT-004: Auto-Detección Semántica de la Distribución Óptima (NORTE del proyecto) ✅ RESUELTO (4 fases entregadas)
**Componente**: `AlmaGag/layout/templates/` (nuevo) + `AlmaGag/generator.py`
**Severidad**: **Alta** (núcleo de la propuesta de valor de AlmaGag)
**Reportado**: 2026-06-19 (inspección del diagrama de arquitectura)
**Fase 1 resuelta**: 2026-06-19

**Estado por fase**:

**✅ Fase 1 — Template 'architecture'** (2026-06-19):
- Nuevo módulo `AlmaGag/layout/templates/` con framework de templates.
- Template `architecture`: layout en T (entry vertical → containers en fila con shared al centro → contract → terminals).
- Heurística de categorización por rol topológico.
- Opt-in vía `"layout_template": "architecture"` en SDJF.
- Respeta coords manuales. Calcula canvas automáticamente.
- 8 tests + ejemplo `15-architecture-template.gag`.

**✅ Fase 2 — Framework de auto-detección + 2 templates más** (2026-06-19):

Replanteo: en lugar de "catálogo opt-in" (que sería declarativo, no inferencial), Fase 2 ahora es **clasificador automático del grafo** + **scorers por template**.

- **`GraphFeatures`** (`templates/features.py`): extrae 15+ métricas del grafo (n_root, degrees, max_degree_ratio, topological_depth, ciclos, branching_factor, pct_inter_container_connections, keywords semánticas).
- **`BaseTemplate`** + **`TemplateClassifier`** (`templates/base.py`): interfaz + clasificador con threshold (0.6) y min_lead (0.05) configurables.
- **3 templates** con sus respectivos `detect_score()`:
  - `architecture`: containers ≥ 2, keyword shared, DAG, depth 3-7.
  - `flow`: depth ≥ 4, branching ~1, sin containers, sin ciclos.
  - `hub_and_spoke`: max_degree_ratio ≥ 2.5, depth ≤ 2, pocos containers. Layout circular (n<8) o columnas izq/der (n≥8 estilo SD-WAN).
- **`generator.py`**:
  - `"layout_template": "auto"` → clasificador (Fase 2).
  - `"layout_template": "<name>"` → override manual.
  - Sin declaración → comportamiento agnóstico (AUTO/LAF normal).
- **16 tests** del clasificador (`tests/test_template_classifier.py`).

Resultados del clasificador sobre los 23 canonicals:
- Aciertos claros: `05-arq` / `15-template` → architecture (0.75); `svg-to-bwt-flow`, `03-conexiones` → flow (0.90); `system-architecture` → hub_and_spoke (0.85).
- Casos ambiguos / catálogos visuales → None (fallback agnóstico) — comportamiento correcto.

**✅ Fase 3 — Templates adicionales + calibración** (2026-06-19):

4 templates nuevos con sus detectores + layouts:
- `dashboard` (`templates/dashboard.py`): containers paralelos sin conexiones inter → grid `ceil(sqrt(N))` × `ceil(N/cols)`.
- `er` (`templates/er.py`): Entity-Relationship → distribución radial-concéntrica (entidades más conectadas al centro).
- `sequence` (`templates/sequence.py`): swimlanes verticales en columnas + mensajes ordenados temporalmente.
- `state` (`templates/state.py`): estados en distribución circular (uniforme).

Calibración con los 23 canonicals:
- 3 architecture (05-arq, 07-containers, 15-template).
- 6 flow (03-conexiones, 12-custom, 14-stresstest, layout-opt, routing-arch, svg-to-bwt-flow).
- 3 hub_and_spoke (06-flujo, 13-stresstest, system-arch).
- 1 dashboard (reference-cheatsheet).
- 1 er (10-hybrid-layout).
- 10 `(ninguno)` — catálogos visuales y casos ambiguos, fallback correcto a algoritmo agnóstico.

Ajustes de calibración aplicados:
- ER scorer: cortocircuito a 0 si `n_connections < 3` (sin relaciones no hay ER).
- ER scorer: penalty fuerte (-0.45) si hay containers (no es ER puro entonces).
- Keywords semánticos: agregados `entity`, `table`, `database` a `SEMANTIC_TOKENS`.

11 tests nuevos en `tests/test_template_fase3.py`. Total: 54 (era 43).

**✅ Fase 4 — Semantic hints + templates anidados** (2026-06-19):

(a) Semantic hints (`role` por elemento):
- Campo `"role"` opcional con valores: entry, output, shared, hub, spoke, abstract, state, actor, terminal.
- `GraphFeatures.declared_roles` mapea elem_id → role.
- Roles sobreescriben heurística por label/topología (architecture/hub_and_spoke/state).
- Scorers dan bonus por roles consistentes con el patrón.

(b) Templates anidados por container:
- Campo `"layout_template"` opcional en cualquier container.
- Nuevo módulo `templates/nested.py` con procesamiento bottom-up.
- `apply_sub_templates` se llama SIEMPRE (independiente del template padre).
- Containers guardan `_inner_width`/`_inner_height` desde su sub-grafo.
- `offset_nested_children` ajusta hijos a coords globales después del padre.
- Política: el hijo siempre infla; el padre se adapta.

10 tests nuevos. Total 54 → 64. WISH-LAYOUT-004 cerrado integralmente.

**✅ Fase 4 — Semantic hints + templates anidados** (2026-06-19):

(a) Semantic hints (`role` por elemento):
- Campo `"role"` opcional con valores: entry, output, shared, hub, spoke, abstract, state, actor, terminal.
- `GraphFeatures.declared_roles` mapea elem_id → role.
- Roles sobreescriben heurística por label/topología (architecture/hub_and_spoke/state).
- Scorers dan bonus por roles consistentes con el patrón.

(b) Templates anidados por container:
- Campo `"layout_template"` opcional en cualquier container.
- Nuevo módulo `templates/nested.py` con procesamiento bottom-up.
- `apply_sub_templates` se llama SIEMPRE (independiente del template padre).
- Containers guardan `_inner_width`/`_inner_height` desde su sub-grafo.
- `offset_nested_children` ajusta hijos a coords globales después del padre.
- Política: el hijo siempre infla; el padre se adapta.

10 tests nuevos. Total 54 → 64. WISH-LAYOUT-004 cerrado integralmente.

**Reportado originalmente**: 2026-06-19 (inspección del diagrama de arquitectura)

**Descripción**:
AlmaGag se vende como "generador automático de diagramas SVG desde JSON descriptivo". Pero en la práctica, para diagramas con estructura específica (arquitectura, flow, dashboard, ER, secuencia, etc.) el sistema **necesita coords manuales** para producir un layout legible. AUTO sin coords pone los elementos pero el resultado raramente es lo que un humano dibujaría; LAF distribuye por topología pero a costa de canvas excesivos.

**Reproducción concreta** (`05-arquitectura-gag.gag` sin coords manuales):
- AUTO: 1400×1872 — sin la lógica "shared al medio entre algoritmos"; queda alto y sin balance.
- LAF: 3230×1908 — distribuye horizontal por topología, canvas excesivo.
- AUTO + coords manuales (estado actual): 1200×1180, layout en T balanceado — **pero las 8 posiciones hardcodeadas son trabajo manual**.

**Lo que se desea**:
Que el algoritmo **infiera la intención del diagrama** y elija la distribución apropiada sin que el usuario tenga que escribir coords. Algunos patrones reconocibles:

| Patrón | Pista de detección | Layout ideal |
|---|---|---|
| Arquitectura jerárquica | Pocos nodos raíz, varios niveles, containers como agrupadores | Top-down con shared al centro entre alternativas |
| Flow / pipeline | Cadena lineal de pasos | Horizontal o vertical recto |
| Dashboard / poster | Containers paralelos sin conexiones entre sí | Grid (ya parcialmente resuelto en LAF Fase 1.5) |
| ER / clases | Nodos con relaciones múltiples | Force-directed o circular |
| Secuencia | Conexiones con orden temporal | Swimlanes |
| Estado | Self-loops y ciclos | Estados como nodos, transiciones como aristas |

**Posibles enfoques** (a explorar en sub-tareas):

1. **Detección de patrones por heurística**: clasificar el grafo por número de niveles topológicos, fan-out del nodo raíz, ratio cross-level vs same-level connections, presencia/ausencia de containers, ciclos, etc.
2. **Templates pre-definidos**: bibliotecas de layouts (arch, flow, dashboard, sequence, etc.) que el usuario seleccione vía `"layout_template": "architecture"` en el SDJF.
3. **Semantic hints en el SDJF**: tags por elemento (`"role": "entry"`, `"role": "shared"`, `"role": "output"`) que ayuden al algoritmo.
4. **ML / LLM-assisted layout**: usar un modelo para inferir la mejor disposición a partir de la estructura del grafo y las etiquetas semánticas de los elementos.
5. **Constraint solver**: extensión de `WISH-LAYOUT-002` con más constraints (`above`, `below`, `between`, `inside_group`) y un solver que satisfaga el máximo número.

**Por qué es importante**:
Es el **norte del proyecto**. AlmaGag deja de ser un "generador" y se convierte en un "asistente con coords manuales" si los usuarios tienen que escribir 8-30 posiciones para cada diagrama complejo. Resolver esto convierte AlmaGag en una herramienta competitiva con Mermaid/Graphviz/D3 que infieren bastante por sí solas.

**Relación con tickets existentes**:
- **Subsume** los follow-ups de `WISH-LAYOUT-002` (`constraints.near` / `constraints.avoid`) y `WISH-LAF-001` (heurística por tipo de diagrama).
- **Habilita** que el diagrama de arquitectura del propio proyecto se genere sin las 8 coords manuales actuales.
- **Refuerza** el benchmark contra Mermaid (`docs/diagrams/benchmark/`).

**Estimación**: trabajo grande, no acotable en una iteración. Mínimo:
- Fase 1 (1-2 días): heurística para reconocer "arquitectura jerárquica" + template top-down con shared al centro.
- Fase 2 (1 semana): catalogar 5-6 patrones más comunes y sus templates.
- Fase 3 (continua): semantic hints en SDJF + constraint solver extendido.

**Prioridad**: **Alta a largo plazo**. No bloquea features inmediatas pero es la diferencia entre "herramienta de nicho" y "herramienta competitiva". Mantener visible como el norte del proyecto.

---

### WISH-DOCS-001: Sincronizar `architecture.mmd` Benchmark con el Nuevo `.gag` ✅ RESUELTO
**Componente**: `docs/diagrams/benchmark/architecture.mmd`
**Severidad**: Baja
**Reportado**: 2026-06-18
**Resuelto**: 2026-06-18

**Causa**: `architecture.mmd` representaba la arquitectura pre-ciclo (con `auto_optimizer v2.1`, `laf_optimizer v1.8`, `renderer.py` único, módulo `Routing` granular). El nuevo `05-arquitectura-gag.gag` ya reflejaba post WISH-ARCH-001/002 + BUGS-LAF-002 con factoría OPTIMIZERS, renderers separados y `draw/svg.py`. El benchmark seguía corriendo pero comparaba grafos distintos.

**Fix aplicado**:
- `architecture.mmd` reescrito: mismos 16 elementos en 3 containers (AUTO, LAF, Shared) que el `.gag`. Heritage de optimizers al contrato `LayoutOptimizer` representada con flechas punteadas (`-. "hereda" .->`). Forma `>...]` (parallelogram-asymmetric) para distinguir la clase abstracta.
- `architecture.svg` y `architecture.png` regenerados con `mmdc` (puppeteer config con `--no-sandbox`).
- `benchmark/README.md` actualizado: tabla de archivos, métricas objetivas (canvas, tamaños, líneas), próximos benchmarks. Mencionado explícitamente WISH-DOCS-001 como ancla de sync.

**Validación**: ambos diagramas representan ahora el mismo grafo (16 elementos × 3 containers × ~15 conexiones).

---

### WISH-DOCS-002: Actualizar `EVOLUTION.md` con el Ciclo Actual ✅ RESUELTO
**Componente**: `docs/architecture/EVOLUTION.md`
**Severidad**: Baja
**Reportado**: 2026-06-18
**Resuelto**: 2026-06-18

**Fix aplicado**:
Reemplazado el placeholder "v2.2 - (Futuro)" por 3 entradas nuevas que cubren ~18 meses faltantes:

- **v3.0 — LAF (Sprints 1-11)** — introducción del pipeline LAF de 11 fases inspirado en Sugiyama. Tabla con la responsabilidad de cada fase. Métricas vs AUTO sobre `05-arquitectura-gag`: cruces -87%, colisiones -80%.

- **v3.3 — SDJF v2.1 + BUGS-DIAG-* (8 fixes visuales)** — pulido visual del set canonical (containers semi-transparentes, labels gigantes, bandas densas, grid spacing).

- **v3.4 — Ciclo "13 items en un sprint" (2026-06-18)** — entrada extensa del ciclo actual, con tablas separadas por categoría:
  - Refactores: Tier 1 (WISH-ARCH-001/002, `generator.py` 838→187 líneas) + Tier 2 (WISH-ARCH-003, `visualizer.py` 2876→11 archivos).
  - Fixes funcionales: tabla con las 5 BUGS resueltas (LAYOUT-001/002/003 + LAF-001/002) y sus métricas clave.
  - Features: WISH-LAYOUT-003 callouts.
  - Documentación: WISH-DOCS-001/002.
  - Métricas globales: antes/después en una tabla.
  - Diagrama de arquitectura: descripción del nuevo `.gag` con iconos custom.

**Validación**: doc renderiza correctamente en GitHub markdown.

---

### WISH-LAYOUT-005: Container Especial "Contract Band" Envolvente ✅ RESUELTO (v1)
**Componente**: SDJF spec + `AlmaGag/draw/primitives/container.py` + `AlmaGag/layout/container_calculator.py` + `AlmaGag/layout/auto/positioner.py` + `AlmaGag/layout/auto/auto_renderer.py`
**Severidad**: Media (mejora expresividad de diagramas arquitectónicos)
**Reportado**: 2026-06-23 (feedback visual del usuario sobre diagrama manual)
**Resuelto**: 2026-06-23

**Motivación**:

En diagramas arquitectónicos es común expresar "estos N elementos son intercambiables a través de este contrato" con una **banda horizontal** que envuelve un grupo `[endpoint_A, abstract, endpoint_B]`. Visualmente la banda comunica que es un eje único de simetría, no un container jerárquico clásico.

AlmaGag hoy solo tiene containers tipo "caja con título": el background rectangular agrupa pero no transmite el sentido de banda/eje.

**Caso de prueba**:
Diagrama manual del usuario (2026-06-23): banda horizontal azul claro envuelve `[green-rect-izq, yellow-diamond, green-rect-der]` haciendo evidente la equivalencia funcional.

**Propuesta**:
- Nuevo tipo de container en SDJF: `"type": "band"` o `"shape": "band"` (compatible con `"contains": [...]`).
- Render: rect muy ancho y bajo (alto = max height de hijos + padding), sin título arriba sino lateral. Color de fondo más sutil que un container normal.
- Comportamiento de layout: hijos en fila horizontal con padding uniforme, no en grid.
- Compatible con el `architecture` template (banda = capa del medio en la T).

**Fix aplicado (v1)**:

Un container con `"shape": "band"` (cualquier container con `contains` puede llevarlo) se comporta distinto:

1. **Layout de hijos** (`positioner._layout_contained_elements_locally`): todos los hijos en **una sola fila** horizontal (`cols = n`), con offset lateral izquierdo para el título y sin reserva de header arriba. Es el eje de equivalencia.
2. **Bounds** (`container_calculator.calculate_container_bounds` + `positioner._calculate_container_bounds`, ambos band-aware vía helper `is_band` / `band_label_margin`): reservan margen lateral izquierdo (`band_label_margin = n_líneas*18 + 16`) en vez de header arriba; alto = hijos + 2·padding (hug vertical).
3. **Render del rect** (`draw/primitives/container.py`): fondo más sutil (`CONTAINER_FILL_OPACITY * 0.6`), esquinas de barra (`radius = min(height/2, 24)`), sin icono superior.
4. **Título** (`auto_renderer._render_container_labels`): rotado -90° sobre el borde izquierdo, centrado verticalmente.

**Validación**:
- Canonical `16-contract-band.gag` — banda envuelve `[server, diamond, server]` en fila, 0 colisiones.
- `tests/test_band_container.py` — 5 tests (detección, margen por líneas, hijos en fila única, sin overflow horizontal, label rotado en SVG).
- Regresión: containers normales (`05-arquitectura-gag`, `07-containers`, `reference-cheatsheet`) byte-idénticos vs HEAD.
- Tests 79/79 passed.

**Follow-up (2026-06-23, mismo ticket)** — feedback visual del usuario:
1. **Icono en cada container**: se detectó que el renderer AUTO pasaba `draw_icon=False` y por eso **ningún** container AUTO mostraba su icono de tipo (aunque el label ya venía offseteado `x + 10 + ICON_WIDTH + 10` dejando el hueco). Se activó `draw_icon=True`: containers normales dibujan el icono en la esquina superior izquierda; las bands lo dibujan tras el título rotado, alineado con la fila de hijos (`band_left_region = título + ICON_WIDTH + gap`). Regenerados todos los canonicals con containers.
2. **Centrado**: el eje del band demo se alineó (Entry, hijo central y Output centrados en la misma X).

**Pendiente (v2, no bloquea)**:
- Soporte en el renderer LAF (hoy solo AUTO maneja el título lateral; LAF dibujaría el label como header normal).
- Integración con el `architecture` template (auto-detectar la capa media como band).

---

### WISH-LAYOUT-006: Auto Label-Position por Geometría del Container ✅ RESUELTO (v1)
**Componente**: `AlmaGag/layout/auto/optimizer.py`
**Severidad**: Media (mejora legibilidad de diagramas con containers anchos/estrechos)
**Reportado**: 2026-06-23 (feedback visual del usuario sobre diagrama manual)
**Resuelto**: 2026-06-23

**Motivación**:

El usuario en su diagrama manual posiciona los labels de iconos contenidos **hacia afuera del centro del container**: icono izquierdo → label a la izquierda; icono derecho → label a la derecha. Esa heurística:
- Evita solape entre labels de hermanos adyacentes (problema BUGS-AUTO-006 que ya parchamos con stagger).
- Aprovecha el espacio libre fuera del container.

AlmaGag hoy elige label_position con un default global (`bottom`) o con `_find_best_label_position` que prueba 4 lados en orden fijo. No considera la geometría del container padre.

**Propuesta**:
- En `_find_best_label_position`, cuando el elemento tiene un container padre, sesgar la preferencia hacia el lado **lejano** del centro del container.
- Para containers row (hijos alineados horizontalmente): preferir `left` para el primer hijo, `right` para el último, `bottom`/`top` para los del medio.
- Para containers column: análogo con `top`/`bottom`.
- Reduce dependencia del stagger horizontal (BUGS-AUTO-006).

**Fix aplicado (v1)**:

Nuevo helper `_outward_label_preference(layout, element, parent_container)`:
- Devuelve `'left'` para el hijo **más a la izquierda** de su fila, `'right'` para el **más a la derecha**, `None` para los internos o únicos.
- **Gate single-row**: solo sesga si todos los hijos del container están en una sola fila (`max(y)-min(y) <= 0.6·icon_h`). En grids multi-fila devuelve `None` — sesgar un extremo pondría su label sobre vecinos de otra fila (medido: empeoraba R1 en `reference-cheatsheet`).

Integración como **reordenamiento del fallback** en `_find_best_label_position`: la posición preferida (`bottom` o la del usuario) se mantiene primera; el lado outward se inserta en 2º lugar, antes del resto. Así, cuando `bottom` colisiona, el extremo prueba su lado externo antes que los demás — sin forzar el cambio cuando `bottom` ya funciona (cero regresiones en los canonicals deterministas).

Bug colateral corregido: `_label_inside_container` reservaba una franja superior de 40px (header) también en bands, que **no tienen header** (el título va lateral). Ahora `header_h=0` para bands, permitiendo labels en su parte alta.

**Validación**:
- `tests/test_outward_labels.py` — 5 tests (helper: leftmost→left, rightmost→right, middle→None, multi-fila→None, sin-container→None; + band sin franja superior).
- Balance R1/R2 sobre canonicals deterministas (excluyendo `06-flujo-ejecucion`, que tiene no-determinismo **preexistente** en placement de labels): **sin cambios** (31/83 → 31/83). El efecto aparece solo cuando `bottom` colisiona, sin degradar lo que ya funcionaba.
- Suite 89/89.

**Pendiente (v2, no bloquea)**:
- Forzar outward como preferida en bands requiere reservar margen lateral **simétrico** (hoy solo el lado izquierdo tiene espacio: título + icono; el label `right` del último hijo se sale y cae a `bottom`). Necesita que el bounds-calc de la band reserve sitio para los labels de los extremos.
- Soporte para containers column (sesgo vertical `top`/`bottom`).
- Investigar/abrir ticket para el no-determinismo de `06-flujo-ejecucion` (label placement varía entre corridas; remanente de BUGS-LAYOUT-003).

---

### WISH-LAYOUT-007: Color Semántico por Tipo de Conexión ✅ RESUELTO (v1)
**Componente**: SDJF spec + `AlmaGag/draw/primitives/svg.py` + renderers
**Severidad**: Baja (mejora expresividad de diagramas con múltiples tipos de relación)
**Reportado**: 2026-06-23 (feedback visual del usuario sobre diagrama manual)
**Resuelto**: 2026-06-23

**Motivación**:

En diagramas con múltiples tipos de relación (data flow, control flow, sync, callback, event), el color del conector codifica la semántica de un vistazo. El usuario lo hizo manualmente: 17 conexiones naranja (data flow) + 1 verde bidireccional (sync de estado).

AlmaGag hoy:
- `color_connections=True` → colorea cada conexión con un color único determinado por id (no semántico).
- Si `color_connections=False`, todas en negro.
- `connection.color` no existe en SDJF.

**Propuesta**:
1. **Campo nuevo en SDJF**: `connection.semantic_type` (string libre) o `connection.color` (hex/nombre).
2. **Mapeo automático**: si `semantic_type` está presente, asignar color de paleta predefinida (`data_flow=orange`, `control_flow=blue`, `sync=green`, `event=purple`, `callback=teal`).
3. **Override directo**: `connection.color` tiene precedencia sobre `semantic_type`.
4. **Compatibilidad**: si nada de esto se declara, comportamiento actual (negro o `color_connections`).
5. Bonus: leyenda automática si hay 2+ `semantic_type` distintos en el diagrama.

**Fix aplicado (v1)**:

- `AlmaGag/draw/primitives/svg.py`:
  - `SEMANTIC_CONNECTION_COLORS`: paleta `data_flow`(naranja), `control_flow`(azul), `sync`(verde), `event`(púrpura), `callback`(teal), `dependency`(gris), `error`(rojo).
  - `resolve_connection_color(conn)`: `conn['color']` (override) → `SEMANTIC_CONNECTION_COLORS[conn['semantic_type']]` → `None`.
  - `setup_arrow_markers` refactorizado: si `color_connections` → arcoíris (como antes); si no, calcula color por `resolve_connection_color`; si **alguna** conexión declara color/tipo, devuelve per-connection styles (las sin tipo quedan negras); si ninguna → markers planos (comportamiento clásico intacto).
- Renderers (`auto_renderer.py`, `laf_renderer.py`): manejan el tuple per-connection independientemente del flag `color_connections`.

**Validación**:
- `tests/test_semantic_connection_colors.py` — 7 tests (precedencia color>semantic, mapeo por tipo, None sin declarar, markers planos sin semantic, per-connection con semantic, arcoíris intacto).
- Canonical `17-semantic-connections.gag` (data_flow/sync/event/callback) — 0 colisiones.
- Regresión: canonicals sin `semantic_type` byte-idénticos (05-arquitectura, 07-containers). Suite 96/96.

**Pendiente (v2, no bloquea)**:
- Leyenda automática (swatch + etiqueta por `semantic_type` presente). Requiere reservar área sin solapar contenido (placement no trivial); se deja como incremento.

---

### WISH-DRAW-001: Shape `diamond` (abstract/decision) como Icono Nativo ✅ RESUELTO
**Componente**: `AlmaGag/draw/icons/` — nuevo módulo `diamond.py` + alias `decision.py`
**Severidad**: Baja (cosmético, mejora claridad visual)
**Reportado**: 2026-06-23 (feedback visual del usuario sobre diagrama manual)
**Resuelto**: 2026-06-23

**Motivación**:

El usuario usa un diamante amarillo para el nodo abstracto/contrato en el centro de la banda. El diamante es convención UML/BPMN para "decision" o "interface", y comunica el rol abstracto al instante. AlmaGag hoy:
- `type: "contract"` renderiza un rect dashed con texto `«abstract»` (estilo UML clase abstracta).
- No hay shape `diamond` registrado.

Ambos son válidos UML pero el diamante es más universal en diagramas arquitectónicos (no solo de clases). Vale tenerlo disponible.

**Propuesta**:
1. Crear `AlmaGag/draw/icons/diamond.py` con `draw_diamond(dwg, x, y, color, element_id)`:
   - Polígono rombo (4 puntos) en gradiente.
   - Tamaño base ICON_WIDTH × ICON_HEIGHT, ajustable con `wp`/`hp`.
2. Registrar en el dispatcher (`AlmaGag/draw/icons/__init__.py`).
3. Disponible como `"type": "diamond"` en cualquier SDJF.
4. **Opcional**: añadir `"type": "decision"` como alias semántico.

**Fix aplicado**:
- `AlmaGag/draw/icons/diamond.py` — `draw_diamond(dwg, x, y, color, element_id)`: polígono rombo con sus 4 vértices en los puntos medios del bbox `ICON_WIDTH × ICON_HEIGHT`. El centro y los anclajes de conexión coinciden con los de cualquier icono rectangular (port_assignment funciona sin cambios). Gradiente + línea de realce diagonal sutil.
- `AlmaGag/draw/icons/decision.py` — alias: `"type": "decision"` renderiza el mismo rombo (el dispatcher importa por nombre de módulo, así que necesita su propio archivo).
- Compatible con `wp`/`hp` (vía bbox), gradientes y todos los routing types.

**Validación**:
- `tests/test_diamond_icon.py` — 4 tests (render del polígono, alias decision==diamond, dispatcher resuelve ambos tipos sin caer al fallback bwt).
- Tests 74/74 passed.
- Render de prueba: rombos correctos en `diamond` y `decision`, sin warnings de ícono por defecto.

---

## 📊 Métricas

### Conteo por categoría

| | BUGS | WISH | Total |
|---|---:|---:|---:|
| **LAYOUT** | 3 (3 resueltos ✅) | 4 (3 resueltos ✅) | 7 |
| **LAF** | 2 (ambos resueltos ✅) | 1 (resuelto ✅) | 3 |
| **ARCH** | 0 | 3 (3 resueltos ✅) | 3 |
| **AUTO** | 7 (7 resueltos ✅) | 0 | 7 |
| **DOCS** | 0 | 2 (2 resueltos ✅) | 2 |
| **DIAG** | 8 (8 resueltos ✅) | 0 | 8 |
| **Total** | **20** | **10** | **30** |

Conteos DIAG viven en `DIAGRAM_REVIEW.md` — **los 8 BUGS-DIAG están RESUELTOS al 2026-06-15**.
**Al 2026-06-18, 0 BUGS funcionales pendientes.** Resueltos en este ciclo:
WISH-ARCH-001/002, BUGS-LAYOUT-001/002, BUGS-LAF-001/002.

Problemas visuales DIAG (8 entradas) viven en `DIAGRAM_REVIEW.md`.

### Priorización sugerida

**Backlog activo (al 2026-06-19)**:

| Prioridad | Código | Resumen |
|---|---|---|
| Baja | `WISH-LAYOUT-002` follow-up | Implementar `constraints.near` y `constraints.avoid` (v1 cerró `align`). Sigue siendo válido aunque WISH-LAYOUT-004 ya entregó los semantic hints. |
| Baja | `WISH-LAYOUT-004` follow-up | Refinamientos: más templates específicos, calibración con corpus etiquetado más grande, constraint solver `above/below/between`. No bloquea uso del sistema. |
| Baja | `WISH-LAF-001` follow-up | Edge straightening post-procesamiento + heurística por tipo de diagrama (v1 cerró pesos dinámicos). **Subsumido por WISH-LAYOUT-004**. |
| Baja | `WISH-LAYOUT-003` v2 | Smart placement de callouts vía `CollisionDetector` (v1 usa fallback derecha→abajo). |

**Tickets cerrados al 2026-06-19**: 20 BUGS resueltos + 9 WISH cerrados/parciales.
**Pendiente como norte estratégico**: `WISH-LAYOUT-004` (auto-distribución semántica).

---

## Mapeo desde códigos anteriores

Para referencias históricas (commits, PRs, comentarios), este es el mapeo desde los códigos `LAF-NNN` previos a la convención actual:

| Código anterior | Código actual |
|---|---|
| LAF-001 | BUGS-LAYOUT-001 |
| LAF-002 | BUGS-LAYOUT-002 |
| LAF-003 | BUGS-LAF-001 |
| LAF-004 | WISH-LAF-001 |
| LAF-005 | WISH-LAYOUT-001 |
| LAF-006 | WISH-LAYOUT-002 |
| LAF-007 | BUGS-LAF-002 |
| LAF-008 | WISH-ARCH-001 |
| LAF-009 | BUGS-LAYOUT-003 ✅ |

---

## 🔗 Enlaces relacionados

- [LAF Progress](./architecture/modules/layout/laf/PROGRESS.md) — Estado de implementación de sistema LAF.
- [LAF Comparison](./architecture/modules/layout/laf/COMPARISON.md) — Comparativa LAF vs AUTO.
- [DIAGRAM_REVIEW.md](./DIAGRAM_REVIEW.md) — Issues visuales en SVGs (códigos `BUGS-DIAG-NNN`).
