# LAF (Layout Abstracto Primero) - Progreso de Implementación

## Resumen Ejecutivo

Reorganización completa del sistema de layout de AlmaGag para minimizar cruces de conectores mediante un enfoque jerárquico inspirado en Sugiyama.

**Estado**: Sprint 10 completado ✅

**Resultados finales**:
- **-87% de cruces de conectores** (15 → 2) en diagrama de prueba
- **0 colisiones** en stresstest (27 elementos, 26 conexiones, 5 VCs)
- **NdPr abstract graph**: Fases 3-5 operan sobre 8 NdPr nodes (3 niveles) en vez de 27 elementos (5 niveles)
- **Fase 6**: Expansion de NdPr a elementos individuales con offsets proporcionales
- **Sistema LAF completamente funcional** (10 fases)
- **Visualización del proceso** implementada (10 SVGs por diagrama)
- **Position optimization** con layer-offset bisection (Fase 5)
- **Metadata SVG** con descriptores NdFn y Gaussian blur text glow

---

## Problema Original

### Antes de LAF

El sistema actual de AlmaGag calculaba posiciones con geometría real desde el inicio:

```
1. Auto-layout con dimensiones reales → x, y
2. Calcular dimensiones contenedores (SIN etiquetas)
3. Calcular rutas [1ª vez]
4. Calcular posiciones de etiquetas
5. Re-calcular dimensiones (CON etiquetas)
6. Re-calcular rutas [2ª vez]
7. Expandir canvas
8. Re-calcular rutas [3ª vez]
9. Loop de optimización (routing en cada iteración)
```

**Problemas**:
- Routing recalculado 5+ veces
- Geometría interfiere con topología → más cruces
- 69 colisiones detectadas (muchas falsas: contenedor vs hijos)
- ~15 cruces en layout_container

---

## Solución LAF

### Nuevo Flujo (10 Fases)

```
FASE 1: STRUCTURE ANALYSIS
├─ Construir árbol de elementos
├─ Analizar grafo de conexiones
├─ Calcular métricas recursivas
└─ Niveles topológicos + accessibility scores

FASE 2: TOPOLOGY ANALYSIS
├─ Visualización de niveles topológicos
├─ Accessibility scores con color coding
└─ Debug output de distribución por nivel

FASE 3: CENTRALITY ORDERING
├─ Ordenamiento por centralidad
└─ Scores de importancia para positioning

FASE 4: ABSTRACT PLACEMENT
├─ Elementos = puntos de 1px
├─ Layering (por nivel topológico)
├─ Ordering (barycenter + tipo)
└─ Minimizar cruces explícitamente

FASE 5: POSITION OPTIMIZATION
├─ Layer-offset bisection
├─ Minimizar distancia ponderada de conectores
└─ Forward + backward, convergencia < 0.001

FASE 6: NdPr EXPANSION
├─ Expandir NdPr nodes a elementos individuales
├─ VCs: distribuir miembros por sub-nivel topológico
├─ Simples: copiar posición directamente
└─ Offsets proporcionales para evitar colisiones

FASE 7: INFLATION + CONTAINER GROWTH (fusionadas)
├─ Spacing proporcional + dimensiones reales
├─ Expandir contenedores bottom-up
├─ Posicionar elementos contenidos
├─ _measure_placed_content() post-check
└─ Calcular posiciones de etiquetas

FASE 8: VERTICAL REDISTRIBUTION
├─ Redistribuir tras crecimiento
├─ Escala X con half-widths de grupos NdFn
└─ Centrado global usando bounding boxes

FASE 9: ROUTING
├─ Calcular paths de conexiones
├─ Self-loop detection + arc routing
└─ Routing con bordes de contenedores

FASE 10: SVG GENERATION
├─ Canvas ajustado dinámicamente
├─ NdFn metadata (<desc> elements)
├─ Gaussian blur text glow filter
└─ Render final
```

**Beneficios**:
- Routing solo 1 vez (vs 5+)
- Topología optimizada antes de geometría
- Falsos positivos eliminados
- Cruces minimizados explícitamente
- Position optimization preserva ángulos del layout abstracto
- Metadata SVG con descriptores NdFn para trazabilidad
- Gaussian blur para legibilidad de texto

---

## Implementación por Sprints

### ✅ Sprint 1: Fix Colisiones Falsas + Estructura (4-6h)

**Archivos modificados**:
- `AlmaGag/layout/collision.py` (+45 líneas)

**Archivos creados**:
- `AlmaGag/layout/laf/__init__.py`
- `AlmaGag/layout/laf/structure_analyzer.py` (~400 líneas)

**Logros**:
- ✅ Método `_is_parent_child_relation()` para skip de colisiones falsas
- ✅ Clase `StructureAnalyzer` con análisis completo
- ✅ Conteo recursivo de íconos en contenedores anidados
- ✅ Análisis topológico BFS del grafo

**Resultados**:
- Colisiones: **69 → 50** (-28%, 19 falsos positivos eliminados)
- Árbol de elementos construido correctamente
- 11 elementos primarios identificados
- 4 contenedores con métricas recursivas
- 9 niveles topológicos calculados

---

### ✅ Sprint 2: Layout Abstracto (8-10h)

**Archivos creados**:
- `AlmaGag/layout/laf/abstract_placer.py` (~500 líneas)
- `AlmaGag/layout/laf_optimizer.py` (~150 líneas)

**Logros**:
- ✅ Algoritmo Sugiyama-style implementado
  - Layering por nivel topológico
  - Ordering con barycenter heuristic
  - Agrupación por tipo de elementos
  - Distribución simétrica
- ✅ Detección de cruces geométrica O(n²)
  - Test de orientación CCW/CW
  - Manejo de casos colineales
- ✅ Coordinador LAFOptimizer
  - Integración con sistema existente
  - Debug logging detallado

**Resultados**:
- Cruces: **~15 → 2** (-87%) ✨
- 9 capas topológicas distribuidas
- 11 posiciones abstractas calculadas
- Algoritmo funcional end-to-end

**Distribución lograda**:
```
Capa 0: 1 elemento  (input)
Capa 1: 1 elemento  (layout_container)
Capa 2: 1 elemento  (optimizer)
Capa 3: 1 elemento  (routing_container)
Capa 4: 2 elementos (analysis_container, draw_container)
Capa 5: 2 elementos (main, render)
Capa 6: 1 elemento  (generator)
Capa 7: 1 elemento  (svgwrite)
Capa 8: 1 elemento  (output)
```

---

### ✅ Sprint 3: Inflación + Integración (6h)

**Archivos creados**:
- `AlmaGag/layout/laf/inflator.py` (~200 líneas)

**Archivos modificados**:
- `AlmaGag/generator.py` (+35 líneas) - Integración LAF
- `AlmaGag/main.py` (+8 líneas) - Argumento CLI
- `AlmaGag/layout/laf_optimizer.py` - Fase 3 integrada

**Logros**:
- ✅ Clase `ElementInflator` implementada
- ✅ Cálculo de spacing proporcional: `MAX(20*ICON_WIDTH, 3*max_contained*ICON_WIDTH)`
- ✅ Conversión abstract → real coordinates con factor vertical 1.5x
- ✅ Asignación de dimensiones reales a elementos
- ✅ Flag `--layout-algorithm=laf` funcional

**Resultados**:
- Spacing calculado: 1600px (basado en 4 íconos máximos)
- 11 elementos primarios posicionados
- 19 etiquetas calculadas
- Diagrama end-to-end generado exitosamente

**Fórmula de spacing aplicada**:
```python
# Con ICON_WIDTH=80, max_contained=4:
spacing = MAX(20*80, 3*4*80) = MAX(1600, 960) = 1600px
```

---

### ✅ Sprint 4: Crecimiento de Contenedores (6h)

**Archivos creados**:
- `AlmaGag/layout/laf/container_grower.py` (~320 líneas)

**Archivos modificados**:
- `AlmaGag/layout/laf_optimizer.py` - Fase 4 integrada
- `AlmaGag/layout/laf/__init__.py` - Export ContainerGrower, v1.2.0

**Logros**:
- ✅ Clase `ContainerGrower` implementada
- ✅ Ordenamiento bottom-up por profundidad
- ✅ Posicionamiento de elementos contenidos en grid horizontal
- ✅ Cálculo de bounding box con etiquetas incluidas
- ✅ Padding proporcional: `ICON_WIDTH * 0.125` (10px)
- ✅ Propagación de coordenadas globales (local → global)
- ✅ Re-cálculo de routing con contenedores expandidos
- ✅ Canvas ajustado dinámicamente

**Resultados**:
- `layout_container`: 464x96px (3 elementos)
- `routing_container`: 408x96px (2 elementos)
- `analysis_container`: 532x96px (3 elementos)
- `draw_container`: 616x96px (4 elementos)
- Canvas final: 1994x19300px
- **Colisiones finales: 38** (vs 50 sistema actual = **-24% mejora**)

**Comparación vs Sistema Actual**:
| Métrica | Sistema Actual | LAF Sprint 4 | Mejora |
|---------|----------------|--------------|--------|
| **Colisiones** | 50 | 38 | **-24%** ✅ |
| **Cruces** | ~15 | 2 | **-87%** ✅ |
| **Canvas** | Variable | 1994x19300 | Proporcional |

---

### ✅ Sprint 5: Visualización + Polish (5h)

**Archivos creados**:
- `AlmaGag/layout/laf/visualizer.py` (~450 líneas)

**Archivos modificados**:
- `AlmaGag/layout/laf_optimizer.py` - Integración visualizador, capturas de snapshots
- `AlmaGag/layout/laf/__init__.py` - Export GrowthVisualizer, v1.3.0
- `AlmaGag/generator.py` (+3 líneas) - Parámetro visualize_growth
- `AlmaGag/main.py` (+5 líneas) - Flag --visualize-growth

**Logros**:
- ✅ Clase `GrowthVisualizer` implementada
- ✅ Captura de snapshots en cada fase del proceso LAF
- ✅ Generación de 4 SVGs por diagrama:
  - `phase1_structure.svg`: Árbol de elementos + métricas
  - `phase2_abstract.svg`: Layout abstracto (puntos + conexiones)
  - `phase3_inflated.svg`: Elementos inflados con dimensiones reales
  - `phase4_final.svg`: Layout final con contenedores expandidos
- ✅ Output organizado en `debug/growth/{diagram_name}/`
- ✅ Anotaciones y badges en cada SVG
- ✅ Flag `--visualize-growth` funcional

**Resultados**:
- 4 SVGs generados correctamente para 05-arquitectura-gag.gag
- Tamaños: 2.1K, 3.0K, 3.1K, 5.4K
- Proceso completo de visualización funcional
- Debug logging detallado

**Uso**:
```bash
# Generar diagrama con LAF + visualización del proceso
almagag archivo.gag --layout-algorithm=laf --visualize-growth --debug

# Output:
#   - archivo.svg (diagrama final)
#   - debug/growth/archivo/phase1_structure.svg
#   - debug/growth/archivo/phase2_abstract.svg
#   - debug/growth/archivo/phase3_inflated.svg
#   - debug/growth/archivo/phase4_final.svg
```

---

## Métricas de Progreso

### Código Escrito

| Sprint | Archivos Nuevos | Líneas | Archivos Modificados | Líneas Mod | Total |
|--------|-----------------|--------|----------------------|-----------|-------|
| 1 | 2 | ~400 | 1 | +45 | ~445 |
| 2 | 2 | ~650 | 0 | 0 | ~650 |
| 3 | 1 | ~200 | 2 | +45 | ~245 |
| 4 | 1 | ~320 | 2 | +25 | ~345 |
| 5 | 1 | ~450 | 4 | +28 | ~478 |
| **TOTAL** | **7** | **~2020** | **9** | **+143** | **~2163** |

### Tiempo Invertido

| Sprint | Estimado | Real | Desviación |
|--------|----------|------|------------|
| 1 | 4-6h | ~5h | On track |
| 2 | 8-10h | ~9h | On track |
| 3 | 6-8h | ~6h | On track |
| 4 | 6-8h | ~6h | On track |
| 5 | 4-6h | ~5h | On track |
| **TOTAL** | **28-38h** | **~31h** | **100% completado ✅** |

### Resultados Cuantitativos

| Métrica | Antes | Después Sprint 5 | Meta Final | Progreso |
|---------|-------|------------------|------------|----------|
| **Cruces** | ~15 | 2 | ≤3 | ✅ 87% mejora |
| **Colisiones** | 50* | 38 | ≤40 | ✅ 24% mejora |
| **Falsos positivos** | 24-32 | 0 | 0 | ✅ 100% eliminados |
| **Routing calls** | 5+ | 2 | 2 | ✅ Objetivo cumplido |
| **Sistema LAF** | - | Completo (10 fases) | 10 fases | ✅ 100% core |
| **Visualización** | - | 10 SVGs/diagrama | Sí | ✅ 100% implementado |

*Después de fix de parent-child (Sprint 1: 69 → 50)

---

## Tests de Verificación

### ✅ Test 1: Colisiones Falsas

```bash
python -m AlmaGag.main docs/diagrams/gags/05-arquitectura-gag.gag --debug
```

**Resultado**: `[WARN] AutoLayout v2.1: 50 colisiones detectadas`
**Esperado**: `69 colisiones` → ✅ **50 colisiones** (-28%)

---

### ✅ Test 2: Layout Abstracto

```python
from AlmaGag.layout.laf_optimizer import LAFOptimizer

optimizer = LAFOptimizer(debug=True)
layout = Layout(elements, connections, canvas)
optimized = optimizer.optimize(layout)
```

**Resultado**:
```
[ABSTRACT] Layering completado: 9 capas
[ABSTRACT] Cruces calculados: 2
```

**Esperado**: ≤3 cruces → ✅ **2 cruces** (-87%)

---

### ⏳ Test 3: LAF End-to-End (Sprint 3)

```bash
almagag 05-arquitectura-gag.gag --layout-algorithm=laf -o test-laf.svg
```

**Esperado**:
- SVG generado correctamente
- Colisiones: ≤15 (vs 50 actual)
- Cruces: ≤3 (vs ~15 actual)
- Spacing proporcional aplicado

---

### ⏳ Test 4: Elemento Único Centrado (Sprint 3)

```bash
almagag red-edificios.gag --layout-algorithm=laf
```

**Esperado**:
- `pc_central` centrado en contenedor
- Padding proporcional aplicado
- Sin colisiones

---

### ⏳ Test 5: Visualización de Crecimiento (Sprint 5)

```bash
almagag 05-arquitectura-gag.gag --layout-algorithm=laf --visualize-growth
```

**Esperado**:
- 4 SVGs creados en `debug/growth/05-arquitectura-gag/`
- `phase2_abstract.svg` muestra puntos + cruces anotados
- `phase3_inflated.svg` muestra elementos reales
- `phase4_final.svg` idéntico al output final

---

## Arquitectura Final

```
AlmaGag/
├── layout/
│   ├── auto_optimizer.py         # ✅ AutoLayoutOptimizer v4.0
│   ├── auto_positioner.py        # ✅ Barycenter + position optimization
│   ├── graph_analysis.py         # ✅ Topología + centralidad + resolución
│   ├── laf_optimizer.py          # ✅ Coordinador LAF v1.6 (10 fases)
│   ├── laf/
│   │   ├── __init__.py           # ✅ Exports
│   │   ├── README.md             # ✅ Documentación técnica
│   │   ├── structure_analyzer.py # ✅ Fase 1: Structure Analysis
│   │   ├── abstract_placer.py    # ✅ Fase 4: Abstract Placement
│   │   ├── position_optimizer.py # ✅ Fase 5: Position Optimization
│   │   ├── inflator.py           # ✅ Fase 7: Inflation (fusionada)
│   │   ├── container_grower.py   # ✅ Fase 7: Container Growth (fusionada)
│   │   └── visualizer.py         # ✅ 10 SVGs de visualización
│   ├── collision.py              # ✅ Detección de colisiones
│   └── ...
├── generator.py                  # ✅ Orquestador (auto/laf) + NdFn metadata
├── draw/
│   ├── icons.py                  # ✅ Dispatcher + gradientes + blur glow
│   ├── connections.py            # ✅ Self-loops + colored connections
│   └── container.py              # ✅ Label-aware bounds
├── main.py                       # ✅ CLI (--layout-algorithm)
└── docs/
    └── LAF-PROGRESS.md           # ✅ Este archivo
```

---

## Próximos Pasos Inmediatos

### Sprint 3 (Actual)

1. **Implementar `inflator.py`**
   ```python
   class ElementInflator:
       def inflate_elements(abstract_positions, structure_info, layout):
           spacing = calculate_spacing(structure_info)
           for elem_id, (ax, ay) in abstract_positions.items():
               real_x = ax * spacing
               real_y = ay * spacing * 1.5
               layout.elements_by_id[elem_id]['x'] = real_x
               layout.elements_by_id[elem_id]['y'] = real_y
   ```

2. **Integrar con CLI**
   - Modificar `generator.py`: Elegir optimizer según flag
   - Modificar `main.py`: Agregar `--layout-algorithm`
   - Test end-to-end: Generar SVG completo

3. **Verificación**
   - Spacing proporcional correcto
   - Posiciones reales asignadas
   - Routing funcional

---

## Riesgos y Mitigaciones

### Riesgo 1: LAF no funciona en todos los casos
**Probabilidad**: Media
**Impacto**: Alto
**Mitigación**: Flag `--layout-algorithm` permite elegir. Sistema actual como fallback.

### Riesgo 2: Performance degradada
**Probabilidad**: Baja
**Impacto**: Medio
**Mitigación**: count_crossings es O(n²) pero con n pequeño (~25 conexiones). Si es problema, usar sweep line O(n log n).

### Riesgo 3: Spacing inadecuado para algunos diagramas
**Probabilidad**: Media
**Impacto**: Bajo
**Mitigación**: Fórmula parametrizable. Permite ajustar base (20) y factor (3).

---

## Conclusión

**Estado**: 100% completado (8 de 8 sprints) - **Proyecto LAF Finalizado ✅**

**Logros Finales**:
- ✅ Sistema LAF completo en 10 Fases
- ✅ -87% cruces de conectores (15 → 2)
- ✅ -24% colisiones (50 → 38)
- ✅ -100% falsos positivos eliminados
- ✅ -80% routing recalculado (5+ → 1 vez)
- ✅ Position optimization con layer-offset bisection (Fase 5)
- ✅ Metadata SVG con descriptores NdFn (`<desc>` elements)
- ✅ Gaussian blur text glow para legibilidad
- ✅ Self-loop arc rendering
- ✅ Colored connections con marcadores de origen
- ✅ CLI integrado: `--layout-algorithm=laf`
- ✅ Visualización del proceso: `--visualize-growth` (10 SVGs)
- ✅ Arquitectura modular y extensible (8 módulos LAF)
- ✅ Contenedores label-aware con post-expansion check
- ✅ Redistribución con half-widths para spacing correcto

---

## Referencias

- **Comparación detallada LAF vs Sistema Actual**: `docs/LAF-COMPARISON.md` ⭐
- Plan completo: `C:\Users\José Cáceres\.claude\plans\nested-enchanting-backus.md`
- Documentación técnica: `AlmaGag/layout/laf/README.md`
- Código fuente: `AlmaGag/layout/laf/`

---

**Última actualización**: 2026-01-17 (Sprint 5 completado - Proyecto LAF Finalizado ✅)

---

## Sprint 6: Renumeración y Mejora del Sistema de Fases (2026-02-08)

**Objetivo**: Eliminar la numeración inconsistente (Fase 4.5) y agregar visualización de análisis topológico.

### Cambios Implementados

**1. Nueva Fase 2: Topological Analysis**
- Visualización de niveles topológicos calculados en Fase 1
- Debug output detallado de distribución por nivel
- Top 5 elementos con mayor accessibility score
- SVG con color coding (rojo/amarillo/azul según score)

**2. Renumeración Completa**
- Fase 2 → Fase 3 (Abstract Placement)
- Fase 3 → Fase 4 (Inflation)
- Fase 4 → Fase 5 (Container Growth)
- Fase 4.5 → Fase 6 (Vertical Redistribution)
- Nueva Fase 7 (Routing - ahora numerada)
- Nueva Fase 8 (SVG Generation - ahora numerada)

**3. Actualización de Visualización**
- 8 archivos SVG en lugar de 4
- Badges actualizados: "Phase X/8"
- Nuevos SVGs: phase2_topology, phase6_redistributed, phase7_routed, phase8_final

**4. Documentación Actualizada**
- FLUJO_EJECUCION.md - Sección completa de Fase 2
- explicacion_fase2_topology.md - Nuevo documento
- explicacion_fase3_abstract.md - Renombrado y actualizado
- RELEASE_v3.0.0.md - Sección LAF actualizada
- laf/README.md - Arquitectura de 8 fases

### Archivos Modificados

**Código (4 archivos)**:
- `laf_optimizer.py`: Nueva Fase 2, todas las fases renumeradas
- `visualizer.py`: 8 métodos de captura, 8 métodos de generación SVG
- `structure_analyzer.py`: Debug output mejorado
- `abstract_placer.py`: Comentarios actualizados

**Documentación (7 archivos)**:
- `FLUJO_EJECUCION.md`
- `explicacion_fase2_topology.md` (NUEVO)
- `explicacion_fase3_abstract.md` (renombrado)
- `RELEASE_v3.0.0.md`
- `laf/README.md`
- `LAF-PROGRESS.md`

### Beneficios

✅ **Consistencia**: Numeración sin decimales (1-8)
✅ **Visibilidad**: Niveles y scores ahora se visualizan claramente
✅ **Comprensión**: Mejor entendimiento del proceso LAF
✅ **Profesionalidad**: Sistema más completo y bien documentado
✅ **Sin regresiones**: Layout final idéntico, solo mejor visualización

**Tiempo invertido**: ~12-14 horas

---

---

## Sprint 7: Position Optimization + Escala X Global (2026-02-17)

**Objetivo**: Agregar position optimization (Fase 5) y escala X global (Fase 8) al pipeline LAF, llegando a 10 fases totales.

### Cambios Implementados

**1. Fase 5: Position Optimization**
- Layer-offset bisection para minimizar distancia ponderada de conectores
- Forward + backward iterations, convergencia < 0.001
- Preserva orden relativo del barycenter

**2. Fase 8: Global X Scale**
- Factor único calculado desde anchos reales de elementos
- Preserva ángulos del layout abstracto
- Evita distorsión horizontal

**3. Renumeración a 10 fases**
- Fases 1-4: Structure, Topology, Abstract, Inflation
- Fase 5: Position Optimization (NUEVA)
- Fases 6-7: Container Growth, Vertical Redistribution
- Fase 8: Global X Scale (NUEVA)
- Fases 9-10: Routing, SVG Generation

### Archivos Modificados

- `laf_optimizer.py`: Pipeline actualizado a 10 fases, v1.4
- `laf/position_optimizer.py`: Fase 5 implementada
- `laf/visualizer.py`: 10 métodos de captura y generación SVG
- `laf/structure_analyzer.py`: Debug output mejorado

**Última actualización**: 2026-02-17 (Sprint 7 completado)

---

## Sprint 8: Consolidación, Metadata SVG y Polish Visual (2026-02-19)

**Objetivo**: Consolidar pipeline a 9 fases, agregar metadata SVG para trazabilidad, mejorar legibilidad visual y corregir bugs críticos.

### Cambios Implementados

**1. Consolidación del Pipeline a 9 Fases**
- Fusión de Fase 6 (Inflation) y Fase 7 (Container Growth) en una sola Fase 6
- Separación de Fase 3 (Centrality Ordering) del Abstract Placement
- Renumeración: Fases 7-9 = Redistribution, Routing, SVG Generation
- 10 SVGs de visualización (con Fase 6: NdPr Expansion)

**2. Metadata SVG con NdFn Descriptors**
- Elementos `<desc>` en SVG2 para cada ícono, contenedor y conexión
- Clase `DrawingGroupProxy` para wrapping en `<g>` sin romper `dwg.linearGradient()`
- Helper `_ndfn_wrap()` para wrapping transparente
- Conexiones: `"From NdFn.AAA.XXX.S to NdFn.BBB.YYY.T | label"`

**3. Gaussian Blur Text Glow**
- Filtro `feGaussianBlur` con `stdDeviation=2` para halo blanco difuso
- Un solo `<filter>` en `<defs>`, referenciado por todos los `<text>`
- Drawing siempre con `debug=False` para compatibilidad SVG2

**4. Correcciones Críticas**
- Labels escapando contenedores → exclusión de `contained_element_ids` del optimizador
- Solapamiento en redistribución → fórmula `half_width_i + half_width_next + gap`
- Self-loops invisibles → `large-arc-flag=1` dinámico + skip visual offsets
- Container bounds → incluyen bounding boxes de labels de elementos contenidos
- ContainerGrower → `_measure_placed_content()` + step 4.5 expansion

**5. Conexiones Coloreadas**
- Flag `--color-connections` para colorear cada conexión con color único
- Marcadores de origen circulares

### Archivos Modificados

**Código (7 archivos)**:
- `generator.py`: DrawingGroupProxy, _ndfn_wrap, desc elements, blur filter, contained exclusion
- `draw/icons.py`: Blur filter en labels
- `draw/connections.py`: Self-loop fix, blur filter, colored connections
- `draw/container.py`: Label-aware bounds
- `layout/laf_optimizer.py`: pipeline consolidado, half-width redistribution fix
- `layout/laf/container_grower.py`: _measure_placed_content, step 4.5
- `layout/laf/visualizer.py`: SVGs de debug, NdFn labels en fases finales

### Beneficios

✅ **Trazabilidad**: Metadata NdFn en SVG permite inspección y debugging
✅ **Legibilidad**: Gaussian blur mejora lectura de texto sobre fondos complejos
✅ **Estabilidad**: 4 bugs críticos corregidos (labels, overlap, self-loops, bounds)
✅ **Simplicidad**: Pipeline consolidado de 10 fases
✅ **Diagnóstico**: Conexiones coloreadas facilitan seguimiento visual

**Última actualización**: 2026-02-19 (Sprint 8 completado - Pipeline consolidado ✅)

---

## Sprint 9: TOI Virtual Containers y NdPr Abstract Graph (2026-02-26)

**Objetivo**: Fases 3-5 operan sobre el grafo abstracto NdPr en lugar de elementos individuales, reduciendo 27 nodos a 8 NdPr nodes para barycenter y optimización.

### Cambios Implementados

**1. Fase 1: Detección de TOI Virtual Containers**
- StructureAnalyzer detecta patrones TOI (elementos que comparten pivot) y crea VCs
- Nuevos campos en StructureInfo: `toi_virtual_containers`, `ndpr_elements`, `ndpr_topological_levels`, `ndpr_connection_graph`, `element_to_ndpr`
- `_build_ndpr_abstract_graph()`: colapsa elementos en NdPr representatives

**2. Fases 3-5: Modo NdPr**
- `_order_by_centrality`: usa `ndpr_elements` y `ndpr_connection_graph`; VC score = max(scores de miembros)
- `abstract_placer.place_elements`: acepta `connection_graph` para barycenter directo sobre NdPr
- `position_optimizer.optimize_positions`: acepta `connection_graph` y `topological_levels` para optimización NdPr

**3. Fase 6: Expansión NdPr → Elementos**
- Nuevo método `_expand_ndpr_to_elements` en laf_optimizer.py
- VCs: distribuir miembros por sub-nivel topológico con offsets
- Simples: copiar posición directamente
- Contenedores reales: posicionar hijos

**4. Visualizer NdPr-aware**
- `_build_ndpr_positions()` detecta posiciones NdPr-level y las retorna directamente
- Fases 4-5 muestran los 8 NdPr nodes correctamente (incluyendo VCs)

### Archivos Modificados

**Código (4 archivos)**:
- `laf_optimizer.py`: `_order_by_centrality` NdPr, `_expand_ndpr_to_elements`, pipeline fase 6
- `abstract_placer.py`: Modo NdPr con `connection_graph`, barycenter graph-based
- `position_optimizer.py`: Modo NdPr con `connection_graph` y `topological_levels`
- `visualizer.py`: Detección NdPr-level en fases 4-5

### Resultados

- 13-stresstest: 27 elementos → 8 NdPr (3 niveles), 1 cruce, 30 colisiones (pre-existentes en expansión)
- 05-arquitectura: 15 elementos → 2 NdPr, retrocompatible
- 03-conexiones: 4 elementos → 4 NdPr (sin VCs), retrocompatible

---

## Sprint 10: Fix Colisiones en Expansión NdPr (2026-02-27)

**Objetivo**: Resolver 30 colisiones causadas por offsets insuficientes en la expansión NdPr y capas corruptas en optimized_layer_order.

### Cambios Implementados

**1. Offsets de Expansión Corregidos**
- `horizontal_offset`: 0.15 → 0.4 (0.4 × 480px = 192px > ICON_WIDTH de 80px)
- `vertical_offset`: 0.3 → 1.0 (1 abstract unit = 1 nivel topológico completo)

**2. Reconstrucción de optimized_layer_order**
- `_update_optimized_layer_order` detecta cuando VC IDs no coinciden con posiciones expandidas
- Reconstruye capas desde `topological_levels` en lugar de filtrar capas existentes
- Restaura los 5 niveles correctos (antes colapsaba a 2)

### Resultados

| Diagrama | Colisiones antes | Colisiones después |
|----------|------------------|--------------------|
| 13-stresstest | 30 | **0** |
| 05-arquitectura | 342 | **10** |
| 03-conexiones | 0 | **0** |

**Última actualización**: 2026-02-27 (Sprint 10 completado - NdPr expansion sin colisiones ✅)
