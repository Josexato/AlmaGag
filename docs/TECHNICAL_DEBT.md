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

## 🌟 WISH

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
