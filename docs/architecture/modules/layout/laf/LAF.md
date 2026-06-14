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
| Dashboard / poster (contenedores agrupando, sin conexiones inter) | **AUTO** (LAF-007: LAF los layoutea pobremente) |
| Velocidad sobre calidad de layout | **AUTO** |
| Debug parcial del pipeline (correr sin routing) | **LAF** con `router_manager=None` |

Para detalle cuantitativo, ver `COMPARISON.md`.

---

## Las 11 fases del pipeline

> **Nota sobre "10 vs 11 fases"**: documentación histórica menciona "10 fases". El código actual define **11**, contando la generación de SVG como Fase 11. La discrepancia es solo de etiquetado — el pipeline real es el mismo. La numeración de este doc es la del código (`LAFOptimizer` docstring + `laf/README.md`).

### Fase 1 — Análisis de estructura

Construye el árbol de elementos, analiza el grafo de conexiones, calcula niveles topológicos (longest-path), computa accessibility scores, detecta **TOI Virtual Containers**, y construye el grafo abstracto **NdPr** (Nodo Primario).

📍 `AlmaGag/layout/laf/structure_analyzer.py`

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

Emite el SVG final: metadata NdFn (`<desc>` elements), filtro Gaussian blur de text glow, `DrawingGroupProxy` para wrapping, canvas ajustado dinámicamente.

📍 `AlmaGag/generator.py` + `AlmaGag/renderer.py`

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

> **Importante**: LAF tiene **no-determinismo entre procesos Python** (LAF-009). El mismo input puede producir 2 layouts distintos en corridas separadas. Para reproducibilidad estricta: `PYTHONHASHSEED=0 almagag ...`.

---

## Limitaciones conocidas

- **LAF-007** — Layout pobre con dashboards. Cuando hay 3+ contenedores en el mismo nivel sin conexiones inter-contenedor, LAF los pone en fila horizontal expandiendo el canvas a >20.000 px. **Workaround**: usar AUTO con coordenadas manuales en los contenedores padre. Ver `../auto/AUTO.md` sección "Dashboard layout".

- **LAF-008** — `LAFOptimizer` no cumple el contrato `LayoutOptimizer`. A diferencia de `AutoLayoutOptimizer` (que hereda de la base), LAF tiene firma propia y `generator.py` lo distingue con `if/elif`. Imposible agregar un tercer algoritmo sin tocar generator. Ver `../../../TECHNICAL_DEBT.md`.

- **LAF-009** — No-determinismo entre procesos. Causa probable: `PYTHONHASHSEED` randomization en algún punto donde el pipeline itera `set`/`dict` sin orden estable. Ver `../../../TECHNICAL_DEBT.md`.

---

## Atributos del optimizer

`LAFOptimizer.__init__` recibe estos componentes (todos opcionales, inyectados desde `generator.py`):

- `positioner` — `AutoLayoutPositioner` (no usado activamente en LAF, mantenido por compatibilidad).
- `container_calculator` — `ContainerCalculator`.
- `routing` — `LAFRoutingPolicy` (envuelve el `router_manager` recibido).
- `collision_detector` — `CollisionDetector`.
- `label_optimizer` — `LabelPositionOptimizer`.
- `geometry` — `GeometryCalculator`.
- Hiperparámetros de centralidad (ver tabla arriba).

---

## Para profundizar

- **Política de routing**: `routing.md`
- **Historia del desarrollo**: `PROGRESS.md` (11 sprints, evolución de fases)
- **Comparación cuantitativa con AUTO**: `COMPARISON.md`
- **Conceptos transversales (NdDp, NdPr, NdFn, TOI...)**: `../../../../CONCEPTS.md`
- **Deuda técnica**: `../../../../TECHNICAL_DEBT.md`
- **README del subpaquete**: `../../../../../AlmaGag/layout/laf/README.md` (vista interna del código)
