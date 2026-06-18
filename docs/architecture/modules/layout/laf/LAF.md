# Algoritmo LAF

**L**ayout **A**bstracto **F**irst (Layout Abstracto Primero). Sistema de layout jerárquico inspirado en Sugiyama/Graphviz que minimiza cruces de conectores procesando primero el grafo en una representación abstracta y aplicando geometría real recién al final del pipeline.

📍 `AlmaGag/layout/laf/optimizer.py` · clase `LAFOptimizer`

---

## ¿Qué es LAF?

A diferencia de AUTO, que respeta coordenadas manuales y optimiza iterativamente desde una posición inicial, LAF **ignora las coordenadas manuales** y construye el layout desde cero en 11 fases. La filosofía: "abstracto primero, geometría después" — ordenar topológicamente sin pensar en píxeles, inflar a tamaños reales recién al final.

Útil cuando querés layout completamente automático sobre un grafo con muchas conexiones, donde el orden topológico importa más que el control de posiciones específicas.

---

## ¿Cuándo usar LAF vs AUTO?

| Caso de uso | Recomendación |
|---|---|
| Grafo denso con muchas conexiones, querés minimizar cruces | **LAF** |
| Diagrama de arquitectura / flow / pipeline | **LAF** |
| Tenés coordenadas manuales que querés respetar | **AUTO** |
| Dashboard / poster (contenedores agrupando, sin conexiones inter) | **LAF** (con grid auto desde 2026-06-18, BUGS-LAF-002 resuelto) o **AUTO** con coords manuales si querés control total |
| Velocidad sobre calidad de layout | **AUTO** |
| Debug parcial del pipeline (correr sin routing) | **LAF** con `router_manager=None` |

Para detalle cuantitativo, ver `COMPARISON.md`.

---

## Las 11 fases del pipeline (+ Fase 1.5)

> **Nota sobre "10 vs 11 fases"**: documentación histórica menciona "10 fases". El código actual define **11** numeradas, contando la generación de SVG como Fase 11, más una **Fase 1.5** insertada en 2026-06-18 para el reflow de dashboards (fix BUGS-LAF-002). La numeración de este doc es la del código (`LAFOptimizer` docstring + `laf/README.md`).

### Fase 1 — Análisis de estructura

Construye el árbol de elementos, analiza el grafo de conexiones, calcula niveles topológicos (longest-path), computa accessibility scores, detecta **TOI Virtual Containers**, y construye el grafo abstracto **NdPr** (Nodo Primario).

📍 `AlmaGag/layout/laf/structure_analyzer.py`

### Fase 1.5 — Reflow de dashboard (BUGS-LAF-002)

Detecta clusters de **3+ contenedores root en el mismo nivel topológico sin conexiones inter-contenedor** (caso "dashboard"/"poster") y los redistribuye en grid 2D modificando `topological_levels`: cada fila del grid recibe un nivel propio (`lv`, `lv+1`, ...). Los descendientes heredan el nuevo nivel.

Sin esta fase, LAF apilaba los contenedores en fila horizontal y el canvas se expandía a >5.000-20.000 px de ancho. Con ella, un poster de 4 contenedores baja de 5900×243 (ratio 24:1) a 1165×656 (ratio 1.8:1).

Umbral configurable en `config.py::LAF_DASHBOARD_MIN_CONTAINERS` (default: 3).

📍 `AlmaGag/layout/laf/optimizer.py::_apply_dashboard_reflow`

### Fase 2 — Análisis topológico (visualización)

Re-procesa los niveles ya calculados en Fase 1 para visualización: color-coding por importancia (rojo = hub, amarillo = importante, azul = normal). No cambia el layout, solo prepara debug.

### Fase 3 — Ordenamiento por centralidad

Ordena los nodos por centralidad sobre NdPr (si está disponible). Los nodos con mayor centralidad terminan más cerca del centro; las hojas se empujan a los extremos. Para VCs, el score es el máximo de los miembros.

### Fase 4 — Layout abstracto

Cada NdPr se trata como un punto de 1 píxel. Aplica layering por nivel topológico y ordering "center-out" por alpha efectiva (centralidad efectiva ajustada con penalización para padres con hojas same-layer). Minimiza cruces explícitamente.

📍 `AlmaGag/layout/laf/abstract_placer.py`

### Fase 5 — Optimización de posiciones

Layer-offset bisection sobre NdPr. Minimiza distancia ponderada de conectores. Forward + backward hasta convergencia (< 0.001).

📍 `AlmaGag/layout/laf/position_optimizer.py`

### Fase 6 — Expansión NdPr → elementos

Cada NdPr se expande a los elementos individuales que representa. Los VCs distribuyen sus miembros por sub-nivel topológico; los nodos simples copian la posición directamente. Reconstruye `optimized_layer_order` por niveles topológicos. Offsets fijos: 0.4 horizontal, 1.0 vertical (en unidades abstractas).

### Fase 7 — Presentación de corrida iterativa

Las fases 4-5-6 se ejecutan iterativamente por profundidad de contenedores. Fase 7 emite el resumen: alpha efectiva por nodo, detección de overlap entre conectores, registro de iteraciones y convergencia. Solo presentación; no modifica el layout.

### Fase 8 — Inflación + crecimiento de contenedores

Aquí termina lo "abstracto" y empieza la geometría real. Cada elemento abstracto se infla a sus dimensiones reales (hp/wp). Los contenedores crecen bottom-up para acomodar a sus hijos, posicionados en grid horizontal. Si labels exceden la estimación, hay un step 4.5 de re-expansion.

📍 `AlmaGag/layout/laf/inflator.py` + `AlmaGag/layout/laf/container_grower.py`

### Fase 9 — Redistribución vertical

Tras el crecimiento, los grupos pueden quedar con espaciados desiguales. Esta fase redistribuye verticalmente preservando los ángulos calculados en Fase 5. Escala X global: `half_width_i + half_width_next + MIN_GAP`. Centrado por bounding boxes.

### Fase 10 — Routing

Invoca `LAFRoutingPolicy.route(layout)`, que delega al `ConnectionRouterManager` compartido. Calcula paths concretos de todas las conexiones: rectas, ortogonales, bezier, arcos, o manuales según `routing.type`. Detección de self-loops + arc routing.

📍 `AlmaGag/layout/laf/routing_policy.py` · doc: `routing.md`

**Opcional**: si LAF se instancia con `router_manager=None`, esta fase se salta (modo debug parcial).

### Fase 10.5 — Re-optimización de etiquetas contenidas

Sub-fase post-routing. Etiquetas dentro de contenedores pueden necesitar ajuste tras conocer los paths reales. Solo se ejecuta si Fase 10 corrió (`self.routing.enabled`).

### Fase 11 — Generación de SVG

Emite el SVG final: metadata NdFn (`<desc>` elements), filtro Gaussian blur de text glow, `DrawingGroupProxy` para wrapping, canvas ajustado dinámicamente. Dibuja los iconos de containers como **elementos separados** (a diferencia de AUTO, que los pinta inline en el rect del container).

📍 `AlmaGag/layout/laf/laf_renderer.py` (`LAFSVGRenderer`). Las primitivas SVG agnósticas (`create_canvas`, `setup_arrow_markers`, `draw_connections`, etc.) viven en `AlmaGag/draw/svg.py` y son compartidas con `AutoSVGRenderer`. Tras WISH-ARCH-002 (2026-06-18), `AlmaGag/renderer.py` original (compartido) fue eliminado.

---

## Configuración / parámetros experimentales

LAF expone 4 hiperparámetros vía CLI. Defaults actuales (en `LAFOptimizer.__init__`):

| Parámetro CLI | Default | Qué controla |
|---|---:|---|
| `--centrality-alpha` | 0.15 | Peso por distancia en skip connections (Fase 3) |
| `--centrality-beta` | 0.10 | Peso por hijo extra / hub-ness (Fase 3) |
| `--centrality-gamma` | 0.15 | Peso por fan-in extra (Fase 3, 0=desactivado) |
| `--centrality-max-score` | 100.0 | Clamp máximo del accessibility score (Fase 3) |

Son experimentales: si activos sugiere que aún se exploran combinaciones óptimas. Ver `TECHNICAL_DEBT.md` para el plan de consolidación.

> **Nota histórica**: LAF tenía no-determinismo entre procesos Python — el mismo input podía producir 2 layouts distintos en corridas separadas. **Resuelto en BUGS-LAYOUT-003** (2026-06-14): ya no requiere `PYTHONHASHSEED=0`. Detalle: `../../../TECHNICAL_DEBT.md#bugs-layout-003`.

---

## Limitaciones conocidas e historial

### Activas

- **BUGS-LAF-001** — Distribución horizontal asimétrica en niveles multi-elemento (cosmético; los niveles están centrados como conjunto pero el spacing interno puede ser disparejo).

### Resueltas (2026)

- **BUGS-LAF-002** ✅ (2026-06-18) — Layout pobre con dashboards. La nueva Fase 1.5 redistribuye clusters en grid 2D. Documentado arriba.
- **BUGS-LAYOUT-001** ✅ (2026-06-18) — Etiquetas de `--visualdebug` solapadas con elementos. Reposicionadas arriba del bbox con `filter='url(#text-glow)'`.
- **BUGS-LAYOUT-002** ✅ (2026-06-18) — Margen vertical excesivo en el canvas final. Separado del horizontal: 250px H (badge de debug) + 50px V.
- **BUGS-LAYOUT-003** ✅ (2026-06-14) — No-determinismo entre procesos. 7 puntos corregidos con `sorted()` + tie-break por `elem_id`.
- **WISH-ARCH-001** ✅ (2026-06-18) — `LAFOptimizer` ahora hereda de `LayoutOptimizer`. `generator.py` usa factoría (`OPTIMIZERS` dict) en vez de `if/elif`.
- **WISH-ARCH-002** ✅ (2026-06-18) — Renderers separados por algoritmo (`LAFSVGRenderer`, `AutoSVGRenderer`). Eliminado `AlmaGag/renderer.py` compartido.

---

## Atributos del optimizer

`LAFOptimizer.__init__` (post WISH-ARCH-001) es **self-contained**: construye sus propios colaboradores internamente y acepta inyección opcional vía kwargs (legacy / tests):

- `sizing` — `SizingCalculator`.
- `geometry` — `GeometryCalculator`.
- `collision_detector` — `CollisionDetector`.
- `container_calculator` — `ContainerCalculator`.
- `positioner` — `AutoLayoutPositioner` (compatibilidad; no usado activamente en LAF).
- `label_optimizer` — `LabelPositionOptimizer`.
- `routing` — `LAFRoutingPolicy` (envuelve un `ConnectionRouterManager`).
- `renderer` — **`LAFSVGRenderer`** (definido en `laf_renderer.py`).
- Hiperparámetros de centralidad (ver tabla arriba).

Si pasás `router_manager=None` al constructor, la Fase 10 (routing) se salta — útil para debug parcial del pipeline.

---

## Para profundizar

- **Política de routing**: `routing.md`
- **Historia del desarrollo**: `PROGRESS.md` (11 sprints, evolución de fases)
- **Comparación cuantitativa con AUTO**: `COMPARISON.md`
- **Conceptos transversales (NdDp, NdPr, NdFn, TOI...)**: `../../../../CONCEPTS.md`
- **Deuda técnica**: `../../../../TECHNICAL_DEBT.md`
- **README del subpaquete**: `../../../../../AlmaGag/layout/laf/README.md` (vista interna del código)
