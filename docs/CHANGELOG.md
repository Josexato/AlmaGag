# Changelog - AlmaGag

Todas las mejoras notables de AlmaGag están documentadas en este archivo.

---

## [3.3.0] - 2026-02-27

### Características Principales

#### NdPr (Nodo Primario) - Grafo abstracto para Fases 3-5
- **Nuevo:** Fase 1 detecta TOI Virtual Containers (VCs) y construye grafo abstracto NdPr
- **Nuevo:** Fases 3-5 operan sobre NdPr nodes en lugar de elementos individuales (27 elem / 5 niveles → 8 NdPr / 3 niveles en stresstest)
- **Nuevo:** Fase 5.5 expande posiciones NdPr a posiciones de elementos individuales
- **Nuevo:** VCs distribuyen miembros por sub-nivel topologico con offsets proporcionales
- **Nuevo:** `abstract_placer.place_elements()` acepta `connection_graph` para modo NdPr
- **Nuevo:** `position_optimizer.optimize_positions()` acepta `connection_graph` y `topological_levels` para modo NdPr
- **Nuevo:** Visualizer detecta posiciones NdPr-level y las muestra directamente (sin centroide)

### Correcciones

#### Colisiones en expansion NdPr (Critical Fix)
- **Corregido:** 30 colisiones icon-vs-icon en stresstest causadas por offsets insuficientes en `_expand_ndpr_to_elements`
- **Solucion:** Offsets aumentados de 0.15→0.4 horizontal y 0.3→1.0 vertical (abstract units)

#### optimized_layer_order corrupto tras expansion NdPr (Critical Fix)
- **Corregido:** `_update_optimized_layer_order` no detectaba que VC IDs ya no existian en posiciones expandidas
- **Solucion:** Reconstruir capas desde `topological_levels` cuando IDs no coinciden, restaurando los 5 niveles correctos

### Archivos Modificados

**LAF Pipeline:**
- `AlmaGag/layout/laf_optimizer.py` — `_order_by_centrality` con NdPr, `_expand_ndpr_to_elements`, `_update_optimized_layer_order` rebuild, pipeline fase 5.5
- `AlmaGag/layout/laf/abstract_placer.py` — Modo NdPr con `connection_graph`, barycenter graph-based
- `AlmaGag/layout/laf/position_optimizer.py` — Modo NdPr con `connection_graph` y `topological_levels`
- `AlmaGag/layout/laf/visualizer.py` — Deteccion NdPr-level en fases 4-5

### Metricas de Mejora

| Metrica | v3.2.0 | v3.3.0 | Delta |
|---------|--------|--------|-------|
| Colisiones (13-stresstest) | 30 | 0 | **-100%** |
| Colisiones (05-arquitectura) | 342 | 10 | **-97%** |
| Nodos en Fases 3-5 (stresstest) | 27 | 8 NdPr | **-70%** |
| Niveles en Fases 3-5 (stresstest) | 5 | 3 | **-40%** |

### Breaking Changes

Ninguno - Retrocompatible con diagramas sin VCs (03-conexiones, etc.)

---

## [3.2.0] - 2026-02-19

### 🎉 Características Principales

#### LAF v2.0 — Pipeline de 9 fases (consolidado)
- **Refactor:** Fusión de Fase 6 (Inflation) y Fase 7 (Container Growth) en una sola Fase 6
- **Nuevo:** Fase 3 (Centrality Ordering) separada del Abstract Placement
- **Resultado:** Pipeline más limpio de 9 fases: Structure → Topology → Centrality → Abstract → Optimization → Inflation+Growth → Redistribution → Routing → Generation

#### Metadata SVG con NdFn descriptors
- **Nuevo:** Elementos `<desc>` en SVG2 con etiquetas NdFn para cada ícono, contenedor y conexión
- **Nuevo:** Clase `DrawingGroupProxy` que envuelve elementos en `<g>` con metadatos sin romper gradientes
- **Nuevo:** Helper `_ndfn_wrap()` para wrapping transparente de elementos
- **Nuevo:** Conexiones etiquetadas como `"From NdFn.AAA.XXX.S to NdFn.BBB.YYY.T | label"`

#### Gaussian blur text glow
- **Nuevo:** Filtro SVG `feGaussianBlur` para halo blanco difuso en todas las etiquetas
- **Mejora:** Legibilidad de texto sobre fondos complejos (gradientes, conexiones superpuestas)
- **Implementación:** Un solo `<filter>` en `<defs>`, referenciado por todos los `<text>` vía `filter="url(#text-glow)"`

#### Conexiones coloreadas
- **Nuevo:** Flag `--color-connections` para colorear cada conexión con un color único
- **Nuevo:** Marcadores de origen circulares en el punto de salida de cada conexión

### 🐛 Correcciones

#### Labels escapando contenedores (Critical Fix)
- **Corregido:** El optimizador de labels ya no mueve etiquetas de elementos contenidos fuera de sus contenedores
- **Solución:** Exclusión de `contained_element_ids` del optimizador + `_measure_placed_content()` en ContainerGrower

#### Solapamiento de elementos en redistribución (Critical Fix)
- **Corregido:** La fórmula de escala X en redistribución usaba solo el ancho del elemento izquierdo
- **Solución:** Ahora usa `half_width_i + half_width_next + MIN_HORIZONTAL_GAP` para calcular separación correcta

#### Self-loops invisibles
- **Corregido:** Arcos de self-loop (from == to) se renderizaban como líneas planas
- **Solución:** `large-arc-flag=1` dinámico cuando `dist < radius * 2`, skip de visual offsets para self-loops

#### Container bounds con labels
- **Corregido:** `calculate_container_bounds()` ahora incluye bounding boxes de etiquetas de elementos contenidos

### 📦 Archivos Modificados

**Core Rendering:**
- `AlmaGag/generator.py` — DrawingGroupProxy, _ndfn_wrap, desc elements, Gaussian blur filter, contained exclusion
- `AlmaGag/draw/icons.py` — Blur filter en labels de íconos
- `AlmaGag/draw/connections.py` — Self-loop fix, blur filter en labels, colored connections
- `AlmaGag/draw/container.py` — Label bounds en calculate_container_bounds

**LAF Pipeline:**
- `AlmaGag/layout/laf_optimizer.py` — 9 fases, half-width fix en redistribución
- `AlmaGag/layout/laf/container_grower.py` — _measure_placed_content, step 4.5 expansion
- `AlmaGag/layout/laf/visualizer.py` — 9 SVGs, NdFn labels en fases 6-9

### 📊 Métricas de Mejora

| Métrica | v3.1.0 | v3.2.0 | Delta |
|---------|--------|--------|-------|
| Fases LAF | 10 | 9 | Consolidado |
| SVGs de visualización | 10 | 9 | Consolidado |
| Labels fuera de contenedores | Sí | No | FIX |
| Self-loops visibles | No | Sí | FIX |
| Solapamiento redistribución | Sí | No | FIX |
| Metadata SVG (desc) | No | Sí | NEW |
| Text glow | No | Sí | NEW |

### 🔧 Breaking Changes

- `svgwrite.Drawing` ahora siempre usa `debug=False` (necesario para atributos SVG2 como `paint-order`)

---

## [3.1.0] - 2026-02-17

### 🎉 Características Principales

#### Auto Layout v4.0 — Calidad comparable a LAF
- **Nuevo:** Barycenter ordering (Sugiyama-style) minimiza cruces dentro de cada nivel
- **Nuevo:** Position optimization con layer-offset bisection minimiza distancia de conectores
- **Nuevo:** Connection resolution — endpoints contenidos se resuelven a sus contenedores padre
- **Nuevo:** Centrality scores — nodos con más conexiones centrados en su nivel
- **Nuevo:** Escala X global calculada desde anchos de elementos

#### LAF v1.4 — Pipeline de 10 fases
- **Nuevo:** Fase 2 (Topology Analysis) con visualización de niveles y scores
- **Nuevo:** Fase 5 (Position Optimization) con layer-offset bisection
- **Nuevo:** Fase 8 (Global X Scale) preservando ángulos del layout abstracto
- **Actualizado:** Numeración consistente 1-10 (eliminado Fase 4.5)
- **Actualizado:** 10 SVGs de visualización por diagrama (vs 4 anterior)

### 🐛 Correcciones

#### Elementos apilados tras expansión de contenedores (Critical Fix)
- **Corregido:** `recalculate_positions_with_expanded_containers()` ya no elimina posiciones de elementos libres
- **Solución:** Solo desplaza elementos que realmente solapan con contenedores expandidos

#### Convergencia del optimizador
- **Corregido:** Expansión de canvas (Strategy C) ya no resetea progreso del optimizador
- **Corregido:** Cache de colisiones invalidado correctamente tras reubicación de etiquetas

#### Spacing vertical
- **Corregido:** Spacing vertical de 100px a 240px (LAF_VERTICAL_SPACING) para contenedores altos

### 📦 Archivos Modificados

**Core Layout:**
- `AlmaGag/layout/auto_positioner.py` — v4.0: barycenter, position optimization, connection resolution
- `AlmaGag/layout/auto_optimizer.py` — Convergencia mejorada, dead code eliminado
- `AlmaGag/layout/graph_analysis.py` — Topological levels (longest-path), centrality scores, connection resolution

**LAF Pipeline:**
- `AlmaGag/layout/laf_optimizer.py` — v1.4: pipeline de 10 fases
- `AlmaGag/layout/laf/position_optimizer.py` — Fase 5: layer-offset bisection
- `AlmaGag/layout/laf/visualizer.py` — 10 SVGs de visualización
- `AlmaGag/layout/laf/structure_analyzer.py` — Debug output mejorado

### 📊 Métricas de Mejora

| Métrica | v3.0.0 | v3.1.0 | Delta |
|---------|--------|--------|-------|
| Colisiones (05-arquitectura) | 90 | 46 | -49% |
| Elementos apilados | 8 | 0 | -100% |
| Convergencia optimizador | Inestable | Estable | FIX |
| Fases LAF | 8 | 10 | +2 |
| SVGs de visualización | 8 | 10 | +2 |

### 🔧 Breaking Changes

Ninguno - Totalmente compatible con archivos .gag anteriores

---

## [3.0.0] - 2026-01-10

### 🎉 Características Principales

#### Layout Jerárquico Inteligente
- **Nuevo:** Posicionamiento basado en topología del grafo (respeta dirección de conexiones)
- **Nuevo:** `calculate_topological_levels()` - Calcula jerarquía usando BFS desde raíces
- **Nuevo:** `_calculate_hierarchical_layout()` - Distribuye elementos por niveles con simetría

#### Mejoras Visuales
- **Alineación vertical perfecta:** Elementos del mismo flujo alineados
- **Distribución simétrica:** Elementos hermanos equidistantes
- **Spacing consistente:** 150px vertical, 120px horizontal
- **Reducción de colisiones:** De 3 a 0 en diagramas típicos

### 🐛 Correcciones

#### Canvas Overflow (Critical Fix)
- **Corregido:** Elementos generados fuera del canvas con coordenadas negativas
- **Solución:** Radios adaptativos calculados dinámicamente según tamaño del canvas
- **Detalle:** `max_safe_radius = min(center_x - 100, center_y - 100)`

#### SVG to PNG Conversion
- **Cambiado:** De cairosvg (requiere GTK+ en Windows) a Chrome/Edge headless
- **Beneficio:** Sin instalaciones adicionales del sistema operativo
- **Soporte:** Chrome, Edge, Chromium en ubicaciones estándar

### 📦 Archivos Modificados

**Core Layout:**
- `AlmaGag/layout/graph_analysis.py` - Niveles topológicos
- `AlmaGag/layout/auto_positioner.py` - Layout jerárquico

**Debug & Utilities:**
- `AlmaGag/debug.py` - Conversión SVG→PNG mejorada
- `pyproject.toml` - Versión 3.0.0

### 📊 Métricas de Mejora

| Métrica | v2.0.0 | v3.0.0 | Delta |
|---------|--------|--------|-------|
| Colisiones (test-auto-layout) | 3 | 0 | -100% |
| Elementos dentro canvas | 75% | 100% | +25% |
| Spacing mínimo | 60px | 120px | +100% |
| Jerarquía visual | ❌ | ✅ | NEW |
| Simetría | ❌ | ✅ | NEW |

### 🔧 Breaking Changes

Ninguno - Totalmente compatible con archivos .gag v2.x

---

## [2.0.0] - 2025-XX-XX

### Características
- Auto-layout con prioridades (high/normal/low)
- Posicionamiento en anillos concéntricos
- Sistema de optimización de colisiones
- Auto-routing de conexiones (5 tipos)
- Contenedores dinámicos

### Formato SDJF
- Coordenadas opcionales (x, y)
- Sizing proporcional (hp, wp)
- Prioridades automáticas
- Múltiples tipos de routing

---

## [1.0.0] - 2024-XX-XX

### Características Iniciales
- Generación básica de diagramas SVG
- Iconos predefinidos (server, database, cloud, building)
- Conexiones simples con etiquetas
- Canvas configurable
- Exportación SVG

---

## Leyenda

- 🎉 **Características principales** - Nuevas funcionalidades importantes
- 🐛 **Correcciones** - Bugs corregidos
- 🔧 **Breaking changes** - Cambios incompatibles con versiones anteriores
- 📦 **Archivos modificados** - Código actualizado
- 📊 **Métricas** - Mejoras cuantificables
