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
- **`ARCH`** — Issues arquitecturales del sistema (acoplamientos, contratos, extensibilidad).
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

### BUGS-LAF-001: Distribución Horizontal Asimétrica en Niveles Multi-Elemento
**Componente**: `AlmaGag/layout/laf/optimizer.py` — `_center_elements_horizontally()`
**Severidad**: Baja
**Reportado**: 2026-01-21

**Descripción**:
Aunque los niveles están centrados horizontalmente como conjunto, la distribución interna de elementos individuales puede ser asimétrica por usar spacing fijo (480 px).

**Ejemplo**:
```
Nivel 3: 3 elementos
  Ancho total: 1350px, Canvas: 1402px, Start X: 100px

  optimizer:              X 480 → 100  (dx=-380)
  laf_optimizer:          X 960 → 660  (dx=-300)
  analysis_module-stage:  X 0   → 1220 (dx=+1220)
```

**Solución propuesta**:
1. Spacing dinámico: `(canvas_width - total_elements_width - 2*MARGIN) / (num_elements - 1)`.
2. Limitar spacing máximo/mínimo para evitar separaciones extremas.
3. Considerar distribución "justificada" para mejor simetría visual.

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

### WISH-LAF-001: Más Optimización de Cruces de Conexiones
**Componente**: `AlmaGag/layout/laf/abstract_placer.py` — Fase 2
**Severidad**: Baja
**Reportado**: 2026-01-21

**Descripción**:
A pesar de implementar optimización de barycenter con conexiones del mismo nivel (peso 30%), **podrían** optimizarse aún más los cruces.

**Datos actuales**:
```
Diagrama: 05-arquitectura-gag.gag
Cruces calculados (Fase 2): 134
```

**Por qué es WISH y no BUGS**:
La optimización ya está implementada y funciona. Esto es una mejora incremental sobre algo que ya hace su trabajo.

**Análisis**:
Implementación actual usa pesos:
- 70% para conexiones verticales (capa anterior).
- 30% para conexiones horizontales (mismo nivel).

**Solución propuesta**:
1. **Ajuste dinámico de pesos** según proporción vertical/horizontal del grafo.
2. **Múltiples iteraciones de barycenter** (actualmente 1 sola pasada).
3. **Post-procesamiento**: fase de "edge straightening".
4. **Heurística por tipo de diagrama**: pesos distintos para arquitecturas vs flows.

**Experimentos sugeridos**:
```python
pesos = [(0.7, 0.3), (0.6, 0.4), (0.5, 0.5)]
```

---

### WISH-LAYOUT-001: Sistema de Etiquetas Inteligente
**Componente**: Label positioning (transversal)
**Severidad**: Enhancement
**Reportado**: 2026-01-21

**Descripción**:
Las etiquetas actualmente se posicionan con reglas fijas. Un sistema inteligente podría:
- Detectar colisiones de etiquetas entre sí y con elementos.
- Ajustar posición automáticamente (arriba/abajo/laterales).
- Usar "leaders" (líneas guía) cuando necesite separar etiqueta del elemento.

**Beneficios**:
- Diagramas más limpios.
- Menos intervención manual del usuario.
- Mejor densidad de información.

**Referencias**:
- Graphviz label placement algorithms.
- D3.js force-directed label positioning.

---

### WISH-LAYOUT-003: Auto-Callout para Labels Grandes
**Componente**: `AlmaGag/renderer.py` + nuevo módulo candidato `AlmaGag/draw/callout.py`
**Severidad**: Media
**Reportado**: 2026-06-15

**Descripción**:
Hoy un label se renderiza siempre adyacente al icono que etiqueta. Si el label tiene 6+ líneas o supera por mucho el tamaño del icono, descalibra el layout porque el algoritmo de colisiones ve un bounding box gigante alrededor de un icono pequeño (ejemplo histórico: `laf_pipeline` con label de 7 líneas describiendo las 11 fases, sobre un icono de 64×46 px — ver BUGS-DIAG-002).

**Propuesta**: detectar automáticamente cuando un label excede umbrales y renderizarlo como un **callout box** separado, conectado al icono mediante una línea/flecha (leader line). El icono queda con un label corto canónico (ej: solo el `id` o las primeras N palabras), y el texto completo vive en un cuadro de texto destacado en una zona libre del canvas.

**Criterio de activación propuesto** (configurables en `config.py`):
- Label excede **N líneas** (sugerencia: 3).
- O label excede **K caracteres totales** (sugerencia: 80).
- O altura/anchura estimada del label excede **R veces el tamaño del icono** (sugerencia: 1.5).

**Comportamiento propuesto**:
1. Renderizar el icono con un label canónico mínimo (heurística: primera línea, o `id`, o `label.split('\n')[0]`).
2. Crear un `<g class="callout">` en zona libre con:
   - `<rect>` de fondo con padding y borde sutil.
   - `<text>` multilinea con el contenido completo del label.
3. Dibujar `<line>` (leader) desde el centro del icono al borde del callout, con marker (flecha o círculo).
4. El callout participa del collision detection como bloque independiente (extiende `CollisionDetector`).

**Inspiración**:
- D3.js force-directed annotations.
- Mermaid sequence diagram notes.
- LaTeX TikZ "annotation" library.
- mxgraph/draw.io text boxes con conector.

**Beneficios**:
- Elementos con labels descriptivos no descalibran el layout.
- Documentación in-diagrama más rica sin sacrificar legibilidad.
- Mantiene la coherencia conceptual: el elemento es el icono; el texto adicional es metadata visualmente separada.
- Resuelve la familia entera de BUGS-DIAG-002 (no solo el caso de `laf_pipeline`).

**Relación con otros issues**:
- Es un caso de uso específico dentro del paraguas más amplio de `WISH-LAYOUT-001` (Sistema de Etiquetas Inteligente).
- Habilitaría a futuros SDJF tener labels más informativos sin pagar el costo visual de BUGS-DIAG-002.

**Implementación estimada**: 1-2 días.
- Heurística de detección: ~50 líneas.
- Renderizado del callout y leader: ~100 líneas en `draw/callout.py`.
- Integración con `CollisionDetector`: ~50 líneas.
- Tests: ~100 líneas (casos con labels chicos no afectados, casos con labels grandes generan callout, casos en borde del umbral).

---

### WISH-LAYOUT-002: Soporte para Restricciones de Posicionamiento
**Componente**: LAF — Fase 2 (Abstract Placement)
**Severidad**: Enhancement
**Reportado**: 2026-01-21

**Descripción**:
Permitir al usuario especificar restricciones en el SDJF:
```json
{
  "elements": [
    {
      "id": "database",
      "type": "database",
      "constraints": {
        "align": "bottom",
        "near": ["api", "cache"],
        "avoid": ["frontend"]
      }
    }
  ]
}
```

**Beneficios**:
- Control sobre layout final.
- Preservar convenciones de arquitectura (ej: DB siempre abajo).
- Respetar agrupamientos semánticos.

**Implementación**:
- Extender `StructureInfo` con constraints.
- Modificar barycenter calculation para incluir pesos de constraints.
- Validar constraints no conflictivas.

---

## 📊 Métricas

### Conteo por categoría

| | BUGS | WISH | Total |
|---|---:|---:|---:|
| **LAYOUT** | 3 (3 resueltos ✅) | 3 | 6 |
| **LAF** | 2 (1 resuelto) | 1 | 3 |
| **ARCH** | 0 | 2 (ambos resueltos ✅) | 2 |
| **AUTO** | 0 | 0 | 0 |
| **DIAG** | 8 (8 resueltos ✅) | 0 | 8 |
| **Total** | **13** | **6** | **19** |

Conteos DIAG viven en `DIAGRAM_REVIEW.md` — **los 8 BUGS-DIAG están RESUELTOS al 2026-06-15**.
**WISH-ARCH-001, WISH-ARCH-002, BUGS-LAYOUT-001, BUGS-LAYOUT-002 y BUGS-LAF-002 resueltos al 2026-06-18.**

Problemas visuales DIAG (8 entradas) viven en `DIAGRAM_REVIEW.md`.

### Priorización sugerida

**Backlog**:
- `BUGS-LAF-001` (distribución asimétrica), `WISH-LAF-001`, `WISH-LAYOUT-001`, `WISH-LAYOUT-002`, `WISH-LAYOUT-003`.

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
