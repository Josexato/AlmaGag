# LAF (Layout Abstracto Primero) - Sistema de Layout

## Descripción

Sistema de layout jerárquico que minimiza cruces de conectores mediante un enfoque de **"Layout Abstracto Primero, Geometría Después"**, inspirado en algoritmos como Sugiyama y Graphviz.

## Filosofía

En lugar de posicionar elementos con sus dimensiones reales desde el inicio (lo que causa cruces innecesarios), LAF:

1. **Analiza** la estructura del diagrama (árbol de elementos, grafo de conexiones)
2. **Posiciona** elementos como puntos abstractos minimizando cruces topológicos
3. **Infla** elementos a sus dimensiones reales con spacing proporcional
4. **Expande** contenedores bottom-up para ajustar a su contenido

## Estado Actual (Sprint 2)

### ✅ Implementado

#### Sprint 1: Fix Colisiones Falsas + Estructura Base
- **collision.py**: Fix de detección de colisiones contenedor-hijo
  - Método `_is_parent_child_relation()`
  - Reduce falsos positivos: 69 → 50 colisiones (-28%)

- **structure_analyzer.py** (~400 líneas)
  - Construcción de árbol de elementos (primarios vs contenidos)
  - Cálculo recursivo de métricas de contenedores
  - Análisis topológico del grafo de conexiones
  - Agrupación de elementos por tipo

#### Sprint 2: Layout Abstracto
- **abstract_placer.py** (~500 líneas)
  - Algoritmo de placement híbrido (Sugiyama-style)
  - Layering: Asignación a capas según nivel topológico
  - Ordering: Barycenter heuristic + agrupación por tipo
  - Positioning: Distribución uniforme en grid abstracto
  - Detección de cruces geométrica O(n²)

- **laf_optimizer.py** (~150 líneas)
  - Coordinador de las 4 fases LAF
  - Integración con sistema existente
  - Debug logging detallado

### ⏳ Pendiente

#### Sprint 3: Inflación de Elementos
- **inflator.py**
  - Conversión de coordenadas abstractas a reales
  - Cálculo de spacing proporcional: `MAX(20*ICON_WIDTH, 3*max_contained*ICON_WIDTH)`
  - Asignación de dimensiones reales a elementos
  - Cálculo inicial de posiciones de etiquetas

#### Sprint 4: Crecimiento de Contenedores
- **container_grower.py**
  - Expansión bottom-up de contenedores
  - Cálculo de dimensiones con etiquetas incluidas
  - Propagación de coordenadas globales
  - Re-cálculo de routing con bordes de contenedores

#### Sprint 5: Visualización + Polish
- **visualizer.py**
  - Generación de snapshots SVG de cada fase
  - Métricas y anotaciones visuales
  - Integración con CLI (`--visualize-growth`)

## Resultados Actuales

### Diagrama: 05-arquitectura-gag.gag

| Métrica | Sistema Actual | LAF (Sprint 2) | Mejora |
|---------|----------------|----------------|---------|
| **Cruces de conectores** | ~15 | **2** | **-87%** ✨ |
| **Colisiones falsas** | 69 | 50 | -28% |
| **Capas topológicas** | N/A | 9 | ✓ Estructura clara |
| **Elementos primarios** | N/A | 11 | ✓ Identificados |
| **Conteo recursivo** | N/A | 4 íconos max | ✓ Anidamiento |

### Distribución Topológica

```
Layer 0: [input] ─────────────────────────┐
Layer 1: [layout_container] ──────────────┤
Layer 2: [optimizer] ─────────────────────┤
Layer 3: [routing_container] ─────────────┤
Layer 4: [analysis_container, draw_container] ─┤
Layer 5: [main, render] ──────────────────┤
Layer 6: [generator] ─────────────────────┤
Layer 7: [svgwrite] ──────────────────────┤
Layer 8: [output] ────────────────────────┘

Cruces detectados: 2 (vs ~15 sin LAF)
```

## Arquitectura

```
AlmaGag/layout/laf/
├── __init__.py              # Exports y versión
├── structure_analyzer.py    # Fase 1: Análisis de estructura
│   ├── StructureInfo        # Dataclass con metadata
│   └── StructureAnalyzer    # Analiza árbol + grafo + métricas
├── abstract_placer.py       # Fase 2: Layout abstracto
│   └── AbstractPlacer       # Placement + count_crossings
├── inflator.py             # Fase 3: Inflación (TODO Sprint 3)
├── container_grower.py     # Fase 4: Crecimiento (TODO Sprint 4)
└── visualizer.py           # Fase 5: Visualización (TODO Sprint 5)

AlmaGag/layout/
├── laf_optimizer.py        # Coordinador LAF
└── collision.py            # MODIFICADO: Skip parent-child
```

## Uso (Cuando esté completo)

```bash
# Sistema actual (default)
almagag archivo.gag

# Nuevo sistema LAF
almagag archivo.gag --layout-algorithm=laf

# Con visualización del proceso
almagag archivo.gag --layout-algorithm=laf --visualize-growth --debug
```

**Output esperado:**
```
[LAF] FASE 1: Análisis de estructura
      - Elementos primarios: 11
      - Contenedores: 4 (max: 4 íconos)
      - Conexiones: 25

[LAF] FASE 2: Layout abstracto
      - 9 capas topológicas
      - Cruces de conectores: 2 (-87%)

[LAF] FASE 3: Inflación de elementos
      - Spacing: 2400px (proporcional)
      - Routing calculado

[LAF] FASE 4: Crecimiento de contenedores
      - Contenedores expandidos
      - Canvas: 1479x1130px

[LAF] Colisiones finales: ~10 (vs 69)
```

## Algoritmos Implementados

### 1. Análisis de Estructura

**Objetivo**: Extraer metadata del diagrama para heurísticas de placement.

**Algoritmo**:
```python
def analyze(layout):
    # 1. Construir árbol de elementos
    for elem in elements:
        if 'contains' in elem:
            parent_of[child] = elem.id

    # 2. Calcular métricas recursivas
    for container in containers:
        total_icons = count_recursive(container)

    # 3. Análisis topológico (BFS)
    levels = {}
    queue = [elements_without_incoming]
    while queue:
        elem = queue.pop()
        levels[elem] = max(levels[predecessor] + 1)

    # 4. Agrupar por tipo
    types = {}
    for elem in elements:
        types[elem.type].append(elem)

    return StructureInfo(...)
```

**Complejidad**: O(V + E) donde V = elementos, E = conexiones

### 2. Layout Abstracto (Sugiyama-style)

**Objetivo**: Posicionar elementos como puntos minimizando cruces.

**Algoritmo**:
```python
def place_elements(structure_info):
    # 1. LAYERING: Asignar a capas por nivel topológico
    layers = [[] for _ in range(max_level + 1)]
    for elem, level in topological_levels:
        layers[level].append(elem)

    # 2. ORDERING: Barycenter heuristic
    for layer_idx in range(1, len(layers)):
        for elem in layers[layer_idx]:
            # Promedio de posiciones de vecinos en capa anterior
            neighbors = [n for n in prev_layer if connects(n, elem)]
            barycenter[elem] = avg(positions[neighbors])

        layers[layer_idx].sort(key=barycenter)

    # 3. POSITIONING: Distribuir uniformemente
    positions = {}
    for y, layer in enumerate(layers):
        for x, elem in enumerate(layer):
            positions[elem] = (x, y)

    return positions
```

**Complejidad**: O(V² + E) - El barycenter y count_crossings son O(V²)

### 3. Detección de Cruces

**Objetivo**: Contar cruces entre conexiones.

**Algoritmo** (Test de orientación):
```python
def count_crossings(positions, connections):
    crossings = 0
    for i, conn1 in enumerate(connections):
        p1, p2 = positions[conn1.from], positions[conn1.to]
        for conn2 in connections[i+1:]:
            p3, p4 = positions[conn2.from], positions[conn2.to]
            if lines_intersect(p1, p2, p3, p4):
                crossings += 1
    return crossings

def lines_intersect(p1, p2, p3, p4):
    # Test de orientación (CCW/CW)
    o1 = orientation(p1, p2, p3)
    o2 = orientation(p1, p2, p4)
    o3 = orientation(p3, p4, p1)
    o4 = orientation(p3, p4, p2)

    return (o1 != o2) and (o3 != o4)
```

**Complejidad**: O(E²) donde E = conexiones

## Optimizaciones Futuras

1. **Sweep line algorithm** para count_crossings: O(E log E)
2. **Median heuristic** además de barycenter
3. **Iterative layer assignment** para reducir cruces entre capas
4. **Force-directed refinement** después de placement inicial
5. **Spatial indexing** (R-tree) para collision detection

## Referencias

- **Sugiyama et al. (1981)**: "Methods for Visual Understanding of Hierarchical System Structures"
- **Graphviz DOT algorithm**: Layered graph drawing
- **D3-hierarchy**: Force-directed layouts
- **OGDF (Open Graph Drawing Framework)**: Implementaciones de referencia

## Changelog

### v1.0 - Sprint 2 (2026-01-17)
- ✅ Análisis de estructura completo
- ✅ Layout abstracto con Sugiyama
- ✅ Detección de cruces O(n²)
- ✅ Fix de colisiones falsas (parent-child)
- 📊 Resultados: 2 cruces (vs ~15)

### Próximo: v1.1 - Sprint 3
- ⏳ Inflación de elementos
- ⏳ Spacing proporcional
- ⏳ Posiciones reales calculadas

## Autores

- **José** - Arquitectura y diseño
- **ALMA** - Implementación y documentación

## Licencia

Parte del proyecto AlmaGag - Generador Automático de Grafos
