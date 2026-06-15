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

### BUGS-LAYOUT-001: Etiquetas de Debug Solapadas en Modo VisualDebug
**Componente**: `generator.py` — Renderizado SVG
**Severidad**: Media
**Reportado**: 2026-01-21

**Descripción**:
Las etiquetas naranjas de debug (nivel topológico) en modo `--visualdebug` se solapan con elementos del diagrama, dificultando la lectura.

**Reproducción**:
```bash
almagag docs/diagrams/gags/05-arquitectura-gag.gag --layout-algorithm=laf --visualdebug --exportpng
```

**Solución propuesta**:
- Calcular posición automática de etiquetas debug evitando colisiones.
- Alternativamente: usar sistema de capas SVG con transparencia.
- Considerar fondo semi-transparente para legibilidad.

**Workaround**: usar modo normal sin `--visualdebug` para diagramas finales.

---

### BUGS-LAYOUT-002: Cálculo Excesivo de Altura de Canvas
**Componente**: `AlmaGag/layout/laf/optimizer.py` — Fase 4.5
**Severidad**: Media
**Reportado**: 2026-01-21

**Descripción**:
El canvas final tiene altura excesiva con mucho espacio vacío en la parte inferior. La redistribución vertical calcula bien las posiciones Y, pero la altura total parece sobrestimada.

**Datos**:
```
Canvas calculado: 1402×3807px
Altura utilizada real: ~2000px
Espacio desperdiciado: ~1800px (47%)
```

**Análisis**:
- `container_grower.calculate_final_canvas()` en `laf/optimizer.py:388-393`.
- Posiblemente incluye padding excesivo o calcula basándose en dimensiones intermedias.

**Solución propuesta**:
1. Revisar `calculate_final_canvas()` en `ContainerGrower`.
2. Calcular altura basándose en elemento más bajo + margen (no multiplicadores).
3. Verificar que no se acumulen márgenes de fases diferentes.

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

### BUGS-LAF-002: Layout Pobre con Contenedores Hermanos sin Conexiones (caso "dashboard")
**Componente**: `AlmaGag/layout/laf/optimizer.py` — Fases 4-5-6 + Fase 8
**Severidad**: Media
**Reportado**: 2026-05-14 (auditoría externa)

**Descripción**:
Cuando hay 3+ contenedores en el mismo nivel sin conexiones entre ellos (típico de dashboards/posters), LAF los pone en fila horizontal y expande el canvas a >20.000 px de ancho.

**Reproducción**:
```bash
# JSON con 4 contenedores agrupando elementos, sin connections inter-contenedor
almagag dashboard.sdjf --layout-algorithm=laf
# Resultado: canvas ~20526×463 (extremadamente horizontal)
```

**Workaround actual**:
Usar AUTO con coordenadas manuales en los contenedores padre. Documentado en `architecture/modules/layout/auto/AUTO.md` (sección "Dashboard layout").

**Solución propuesta**:
Detectar "modo dashboard" (cluster de contenedores sin conexiones inter-cluster) y aplicar layout en grid 2×2, 2×3, o stack vertical según cantidad.

---

## 🌟 WISH

### WISH-ARCH-001: LAFOptimizer Cumpla el Contrato LayoutOptimizer
**Componente**: `AlmaGag/layout/laf/optimizer.py` + `AlmaGag/generator.py`
**Severidad**: Media-Alta
**Reportado**: 2026-05-14 (detectado durante refactor de routing_policy)

**Estado actual**:
- `AutoLayoutOptimizer` hereda de `LayoutOptimizer` (clase base en `optimizer_base.py`).
- `LAFOptimizer` no hereda de nadie y tiene firma de `__init__` distinta (recibe colaboradores por inyección).
- `generator.py` usa `if/elif layout_algorithm == ...` para distinguir (líneas ~578, ~625).
- `render_containers()` recibe `layout_algorithm` como parámetro.

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
| **LAYOUT** | 3 (1 resuelto) | 3 | 6 |
| **LAF** | 2 | 1 | 3 |
| **ARCH** | 0 | 1 | 1 |
| **AUTO** | 0 | 0 | 0 |
| **Total** | **5** | **5** | **10** |

Problemas visuales DIAG (8 entradas) viven en `DIAGRAM_REVIEW.md`.

### Priorización sugerida

**Atacar primero**:
- `BUGS-LAF-002` (dashboard layout) — afecta usabilidad real.
- `BUGS-LAYOUT-002` (canvas excesivo) — afecta todos los renders.

**Cuando se planifique refactor arquitectural**:
- `WISH-ARCH-001` (contrato LayoutOptimizer) — bloquea extensibilidad futura.

**Backlog**:
- `BUGS-LAYOUT-001` (debug labels), `BUGS-LAF-001` (distribución asimétrica), `WISH-LAF-001`, `WISH-LAYOUT-001`, `WISH-LAYOUT-002`.

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
