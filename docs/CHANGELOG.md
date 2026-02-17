# Changelog - AlmaGag

Todas las mejoras notables de AlmaGag están documentadas en este archivo.

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
