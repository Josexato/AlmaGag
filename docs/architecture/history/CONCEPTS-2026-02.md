# Conceptos de AlmaGag — Glosario unificado

> **⚠️ DESACTUALIZADO (pre-reorg `strategies/`, ≤jun-2026).** El pipeline
> real es: `generator.py` (expand_unions §H7 → semantics §Q63 → theme §O57 →
> `select_strategy` → templates) → `LayoutEngine` (`auto`/`hier`/`legacy`) →
> banding §P60 → anticolisión §P61 → re-ruteo → métricas §O52. Ver el código
> y `docs/reviews/auditoria-2026-08-02/` (BUGS-DOCS-002/003/004); este
> documento se conserva por su valor histórico hasta su reescritura.


Este documento es el **punto de entrada conceptual** para entender el vocabulario que usa AlmaGag en código, docs y especificaciones. Para detalle de implementación, ver `architecture/` y `spec/`.

---

## Glosario por categoría

### 1. Formatos de entrada

**SDJF** — Simple Diagram JSON Format. Formato JSON declarativo de AlmaGag. Describe `elements`, `connections` y opcionalmente `canvas`. Sin layout: las coordenadas son opcionales.
📍 `docs/spec/SDJF_v2.1_PROPOSAL.md` (versión actual)

**GAG** — Variante de SDJF que permite **iconos SVG embebidos inline** dentro del JSON. Mismo esquema que SDJF más un campo de SVG por elemento. Diferenciador clave de AlmaGag.
📍 `docs/spec/FORMATO_ARCHIVOS.md`

### 2. Algoritmos de layout

**AUTO** — Algoritmo de layout original. Respeta coordenadas manuales (`x`/`y` en el JSON) y auto-posiciona el resto. Rápido para diagramas simples y casos "dashboard" (ver workaround BUGS-LAF-002).
📍 `AlmaGag/layout/auto/optimizer.py` · doc: `architecture/modules/layout/auto/AUTO.md`

**LAF** — Layout Abstracto Primero. Pipeline de fases con minimización de cruces estilo Sugiyama. **Ignora coordenadas manuales** (todo se posiciona desde cero). Mejor para arquitecturas/flows densos.
📍 `AlmaGag/layout/laf/optimizer.py` · doc: `architecture/modules/layout/laf/LAF.md`

### 3. Modelo de análisis estructural (lo más oscuro del proyecto)

Tres niveles de nodos que LAF maneja simultáneamente durante su pipeline. Cada uno opera en una abstracción distinta:

**NdDp — Nodo de Profundidad** — ID que codifica nivel de anidación en el grafo. Ej: `NdDp02-001` = nodo del nivel 2, índice 001. Usado en análisis topológico (longest-path levels).
📍 `AlmaGag/layout/laf/structure_analyzer.py`

**NdPr — Nodo Primario** — Grafo abstracto que opera sobre nodos agregados (contenedores virtuales + elementos primarios) en lugar de elementos individuales. Fases 3-5 de LAF trabajan sobre NdPr para reducir cruces en grafos densos.
📍 `AlmaGag/layout/laf/structure_analyzer.py`

**NdFn — Nodo Final** — Etiqueta de debug visual con índice global. Aparece sobre cada elemento renderizado cuando se activa `--visualdebug`. Útil para correlacionar SVG con tablas de debug.
📍 `AlmaGag/layout/laf/structure_analyzer.py` · uso en `AlmaGag/renderer.py`

**TOI / Virtual Container** — Contenedor que agrupa elementos virtualmente sin existir como tal en el JSON. Detectado automáticamente por análisis topológico: cuando varios elementos comparten patrón "Triple Origen Idéntico" (todos hijos del mismo padre, sin conexiones entre sí), LAF los trata como una unidad.
📍 `AlmaGag/layout/laf/structure_analyzer.py`

### 4. Modelo de datos

**Layout** — Value Object inmutable que contiene el estado completo del diagrama en cualquier punto del pipeline. Análisis lazy (`collision_count`, `graph`, `levels`, `groups` se calculan bajo demanda y se cachean). Invalidación de caché explícita con `invalidate_collision_cache()`.
📍 `AlmaGag/layout/layout.py`

**Container** — **No es entidad propia**. Es un `element` con campo `contains: [...]`. El código detecta containers vía `'contains' in element`. Centralización pendiente (WISH-LAYOUT-001 en TECHNICAL_DEBT).
📍 dispersos: `AlmaGag/routing/router_base.py`, `AlmaGag/layout/geometry.py`, `AlmaGag/generator.py`

**BWT — Banana With Tape** — Icono de fallback que aparece cuando un elemento tiene `type` que no está registrado en el sistema de iconos. Mascota informal del proyecto y mecanismo de degradación visible.
📍 `AlmaGag/draw/bwt.py`

**Routing Policy** — Política de routing por algoritmo. Encapsula **cuándo** el optimizer invoca el `ConnectionRouterManager` (biblioteca compartida en `AlmaGag/routing/`). Hay una por algoritmo: `AutoRoutingPolicy` (4 invocaciones en el pipeline AUTO) y `LAFRoutingPolicy` (1 invocación opcional en Fase 10 de LAF). Misma interfaz pública (`.route()`), construcción interna asimétrica (síntoma de WISH-ARCH-001).
📍 `AlmaGag/layout/auto/routing_policy.py` · `AlmaGag/layout/laf/routing_policy.py`

---

## Ejemplo end-to-end trazado

Considerá este SDJF mínimo:

```json
{
  "canvas": {"width": 600, "height": 300},
  "elements": [
    {"id": "A", "type": "server", "label": "Server A"},
    {"id": "B", "type": "database", "label": "DB"},
    {"id": "C", "type": "server", "label": "Server B"}
  ],
  "connections": [
    {"from": "A", "to": "B"},
    {"from": "C", "to": "B"}
  ]
}
```

Tres nodos, dos conexiones, sin coordenadas manuales. AlmaGag lo procesa así (vista conceptual, no exhaustiva):

**1. Parseo y `Layout` inicial.** El JSON se materializa en un `Layout` con `elements` (3), `connections` (2), `canvas`. Los atributos lazy (`graph`, `levels`, `groups`) aún no se calculan.

**2. Análisis del grafo.** `GraphAnalyzer` construye adyacencia, calcula niveles topológicos (`A`, `C` en nivel 0; `B` en nivel 1) e identifica que los 3 forman un solo grupo conexo.

**3. Auto-posicionamiento.** AUTO o LAF asigna `x`/`y` a cada elemento. Resultado conceptual: `A` arriba-izquierda, `C` arriba-derecha, `B` abajo-centro.

**4. Routing.** La `RoutingPolicy` activa invoca `ConnectionRouterManager`, que calcula los paths concretos de las 2 conexiones (líneas/curvas/ortogonales según `routing.type` o default).

**5. Renderizado.** `renderer.py` recorre el `Layout` final y emite SVG: marcadores de flecha, gradientes por tipo de icono, etiquetas posicionadas, conexiones dibujadas. Output: un SVG ~3KB.

Para ejemplos reales corribles, ver `docs/diagrams/gags/` — el archivo más simple es `08-auto-layout.sdjf` (6 elementos, 6 conexiones).

---

## Para profundizar

- **Especificación del formato**: `docs/spec/`
- **Arquitectura técnica**: `docs/architecture/ARCHITECTURE.md`
- **Algoritmo AUTO en detalle**: `docs/architecture/modules/layout/auto/AUTO.md`
- **Algoritmo LAF en detalle**: `docs/architecture/modules/layout/laf/LAF.md`
- **Biblioteca de routing**: `docs/architecture/modules/routing/ROUTING.md`
- **Deuda técnica conocida**: `docs/TECHNICAL_DEBT.md`
- **Roadmap**: `docs/ROADMAP.md`
