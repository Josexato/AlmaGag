# Changelog - AlmaGag

Todas las mejoras notables de AlmaGag están documentadas en este archivo.

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
