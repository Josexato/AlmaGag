# Fase 2: Análisis Topológico (LAF)

## Propósito

La **Fase 2: Análisis Topológico** es una nueva fase de visualización agregada en v3.0 que hace visible información crítica que anteriormente estaba "oculta". Los **niveles topológicos** y **accessibility scores** siempre se calculaban en Fase 1, pero nunca se mostraban de forma clara al usuario.

Esta fase NO modifica el layout - solo visualiza datos ya calculados para facilitar el debugging y la comprensión del proceso LAF.

## ¿Qué se visualiza?

### 1. Niveles Topológicos

Los niveles topológicos organizan elementos según sus dependencias:
- **Nivel 0**: Elementos sin padres (puntos de entrada)
- **Nivel 1**: Elementos que dependen solo de nivel 0
- **Nivel 2**: Elementos que dependen de nivel 1
- etc.

**Regla especial (hojas):** Los nodos hoja (sin hijos) se mantienen en el nivel de su padre en lugar de incrementar +1.

**Ejemplo:**
```
Nivel 0: input, optimizer, layout_module-stage
Nivel 1: main, render, label_position_optimizer
Nivel 2: generator
Nivel 3: svgwrite
```

### 2. Accessibility Scores

Los **accessibility scores** indican la "importancia" de cada elemento para el centering horizontal en niveles:

**Fórmula:**
```
score = W_hijos + W_precedence + W_fanin

Donde:
- W_hijos: 0.015 por cada hijo (hub-ness)
- W_precedence: 0.025 si tiene padres en niveles distantes (skip connections)
- W_fanin: 0.010 por cada padre adicional en mismo nivel (fan-in)
```

**Interpretación:**
- **Score alto (>0.05)**: Hub importante, debe centrarse
- **Score medio (0.02-0.05)**: Elemento importante
- **Score bajo (<0.02)**: Elemento normal

**Ejemplo:**
```
optimizer: 0.0450 (nivel 0) - 3 hijos
render: 0.0320 (nivel 1) - 2 hijos + skip connection
layout_module-stage: 0.0210 (nivel 0) - 1 hijo + skip
```

## Salida en Consola

```
[LAF] FASE 2: Análisis topológico
--------------------------------------------------------------
[LAF] Niveles topológicos:
      Nivel 0: input, layout_module-stage, optimizer
      Nivel 1: main, render, label_position_optimizer
      Nivel 2: generator
      Nivel 3: svgwrite

[LAF] Scores de accesibilidad:
      optimizer: 0.0450 (nivel 0)
      render: 0.0320 (nivel 1)
      layout_module-stage: 0.0210 (nivel 0)

[LAF] [OK] Análisis topológico completado
      - 30 elementos con niveles
      - 5 elementos con accessibility score > 0
```

## Visualización SVG: phase2_topology.svg

El archivo `debug/growth/{diagram}/phase2_topology.svg` muestra:

### Layout

```
Level 0  ───────────────────────────────────────
         ⚫ input  ⚫ optimizer  ⚫ layout_module
              (0.04)        (0.02)

Level 1  ───────────────────────────────────────
         ⚫ main  ⚫ render  ⚫ label_optimizer
                 (0.03)

Level 2  ───────────────────────────────────────
         ⚫ generator

Level 3  ───────────────────────────────────────
         ⚫ svgwrite
```

### Color Coding

- 🔴 **Rojo** (score > 0.05): Muy importante - Hub principal
- 🟡 **Amarillo** (0.02 - 0.05): Importante - Hub secundario
- 🔵 **Azul** (< 0.02): Normal - Elemento estándar

### Elementos

- **Círculos**: Representan elementos
- **Posición vertical**: Indica el nivel topológico
- **Color**: Indica el accessibility score
- **Labels**:
  - Primera línea: ID del elemento (truncado si es muy largo)
  - Segunda línea: Score (solo si > 0)

### Leyenda

Incluye una leyenda en la parte inferior explicando los colores y sus rangos de score.

## Ejemplo Real: 05-arquitectura-gag.gag

Para el diagrama de arquitectura GAG:

**Niveles:**
```
Nivel 0 (6 elementos):
  - input, output, generator, parser, layout_module, router_module

Nivel 1 (8 elementos):
  - main, render, generator-svg, parser-gag, layout_algorithm
  - router-orthogonal, collision_detector, label_optimizer

Nivel 2 (4 elementos):
  - svgwrite, pathlib, laf_optimizer, ortho_router

Nivel 3 (2 elementos):
  - container_grower, path_smoother
```

**Top Scores:**
```
1. layout_module: 0.0600 (Nivel 0) - Hub principal con 4 hijos
2. generator: 0.0450 (Nivel 0) - Hub con 3 hijos
3. router_module: 0.0450 (Nivel 0) - Hub con 3 hijos
4. layout_algorithm: 0.0320 (Nivel 1) - Skip connection + 2 hijos
5. parser-gag: 0.0250 (Nivel 1) - Skip connection
```

## Cómo Usar Esta Información

### Durante Debugging

1. **Verificar niveles**: ¿Los elementos están en el nivel correcto?
2. **Identificar hubs**: ¿Los scores reflejan la importancia visual?
3. **Detectar problemas**: ¿Hay elementos importantes con score bajo?

### Para Entender el Layout

- Los elementos con **score alto** se centrarán más en Fase 6 (Redistribución)
- Los **niveles** determinan el orden vertical en el diagrama
- La **distribución por nivel** afecta el espaciado vertical

### Casos Problemáticos

**Problema:** Hub importante no tiene score alto
```
Causa: No tiene suficientes hijos o skip connections
Solución: Revisar si debe tener más conexiones salientes
```

**Problema:** Elemento normal tiene score muy alto
```
Causa: Demasiados hijos artificiales
Solución: Revisar la estructura del diagrama
```

## Cambios en v3.0

### Antes (v2.x)
- Los niveles y scores se calculaban pero NO se mostraban
- Era difícil debuggear problemas de centering
- No había forma de validar la topología

### Ahora (v3.0)
- **Nueva Fase 2** dedicada a visualización topológica
- Debug output detallado en consola
- SVG con color coding por score
- Todas las fases renumeradas (+1 desde Fase 2)

## Archivos Relacionados

- **Cálculo**: `AlmaGag/layout/laf/structure_analyzer.py`
  - `_calculate_topological_levels()` - Niveles
  - `_calculate_accessibility_scores()` - Scores

- **Visualización**: `AlmaGag/layout/laf_optimizer.py` (líneas 610-640)
  - Debug output en consola

- **SVG**: `AlmaGag/layout/laf/visualizer.py`
  - `capture_phase2_topology()` - Captura snapshot
  - `_generate_phase2_topology_svg()` - Genera SVG

## Siguientes Fases

Después de visualizar la topología en Fase 2:

- **Fase 3**: Abstract Placement - Usa niveles para layering
- **Fase 4**: Inflation - Convierte a píxeles reales
- **Fase 5**: Container Growth - Expande contenedores
- **Fase 6**: Vertical Redistribution - Usa scores para centering
- **Fase 7**: Routing - Calcula paths de conexiones
- **Fase 8**: SVG Generation - Renderizado final

## Referencias

- [FLUJO_EJECUCION.md](../docs/FLUJO_EJECUCION.md) - Documentación completa del flujo LAF
- [explicacion_fase3_abstract.md](explicacion_fase3_abstract.md) - Fase 3: Abstract Placement
- [LAF-PROGRESS.md](../docs/LAF-PROGRESS.md) - Historial de desarrollo

---

**Versión:** 3.0
**Fecha:** 2026-02-08
**Sprint:** 6 - Renumeración y mejora del sistema de fases
