# LAF (Layout Abstracto Primero) - Sistema de Layout

## Descripcion

Sistema de layout jerarquico que minimiza cruces de conectores mediante un enfoque de **"Layout Abstracto Primero, Geometria Despues"**, inspirado en algoritmos como Sugiyama y Graphviz.

## Filosofia

En lugar de posicionar elementos con sus dimensiones reales desde el inicio (lo que causa cruces innecesarios), LAF:

1. **Analiza** la estructura del diagrama (arbol de elementos, grafo de conexiones)
2. **Ordena** elementos por centralidad y barycenter minimizando cruces topologicos
3. **Optimiza** posiciones abstractas con layer-offset bisection
4. **Infla** elementos a dimensiones reales y expande contenedores bottom-up
5. **Redistribuye** con escala X basada en half-widths de grupos NdFn
6. **Renderiza** con metadata SVG (descriptores NdFn) y Gaussian blur text glow

## Pipeline de 9 Fases

```
FASE 1: STRUCTURE ANALYSIS          → structure_analyzer.py
├─ Construir arbol de elementos
├─ Analizar grafo de conexiones
├─ Calcular niveles topologicos (longest-path)
├─ Calcular accessibility scores
├─ Detectar TOI Virtual Containers (VCs)
└─ Construir grafo abstracto NdPr (Nodo Primario)

FASE 2: TOPOLOGY ANALYSIS           → laf_optimizer.py (visualizacion)
├─ Visualizar niveles y scores
└─ Color coding: rojo (hub) / amarillo (importante) / azul (normal)

FASE 3: CENTRALITY ORDERING         → laf_optimizer.py
├─ Ordenamiento por centralidad sobre NdPr (si disponible)
├─ VCs: score = max(accessibility_scores de miembros)
└─ Preparar entrada para abstract placement

FASE 4: ABSTRACT PLACEMENT          → abstract_placer.py
├─ NdPr nodes = puntos de 1px (modo NdPr)
├─ Layering (por nivel topologico NdPr)
├─ Ordering (barycenter bidireccional sobre ndpr_connection_graph)
└─ Minimizar cruces explicitamente

FASE 5: POSITION OPTIMIZATION       → position_optimizer.py
├─ Layer-offset bisection sobre NdPr
├─ Minimizar distancia ponderada de conectores
└─ Forward + backward, convergencia < 0.001

FASE 5.5: NdPr EXPANSION            → laf_optimizer.py
├─ Expandir NdPr a elementos individuales
├─ VCs: distribuir miembros por sub-nivel topologico
├─ Simples: copiar posicion directamente
├─ Reconstruir optimized_layer_order por topological_levels
└─ Offsets: 0.4 horizontal, 1.0 vertical (abstract units)

FASE 6: INFLATION + CONTAINER GROWTH → inflator.py + container_grower.py
├─ Spacing proporcional + dimensiones reales
├─ Expandir contenedores bottom-up
├─ Posicionar hijos en grid horizontal
├─ _measure_placed_content() post-check
└─ Step 4.5 expansion si labels exceden estimacion

FASE 7: VERTICAL REDISTRIBUTION     → laf_optimizer.py
├─ Redistribuir tras crecimiento
├─ Escala X: half_width_i + half_width_next + MIN_GAP
└─ Centrado global usando bounding boxes

FASE 8: ROUTING                     → router_manager.py (integracion)
├─ Calcular paths de conexiones
├─ Self-loop detection + arc routing
└─ Container border routing

FASE 9: SVG GENERATION              → generator.py (integracion)
├─ NdFn metadata (<desc> elements)
├─ Gaussian blur text glow filter
├─ DrawingGroupProxy para wrapping
└─ Canvas ajustado dinamicamente
```

## Arquitectura de Modulos

```
AlmaGag/layout/laf/
├── __init__.py              # Exports y version
├── README.md                # Este archivo
├── structure_analyzer.py    # Fase 1: Analisis de estructura
│   ├── StructureInfo        # Dataclass con metadata (incl. NdPr fields)
│   └── StructureAnalyzer    # Arbol + grafo + metricas + TOI VCs + NdPr graph
├── abstract_placer.py       # Fase 4: Layout abstracto
│   └── AbstractPlacer       # Sugiyama-style placement + count_crossings
│                            # Soporta modo NdPr (connection_graph param)
├── position_optimizer.py    # Fase 5: Optimizacion de posiciones
│   └── PositionOptimizer    # Layer-offset bisection
│                            # Soporta modo NdPr (connection_graph + levels params)
├── inflator.py              # Fase 6: Inflacion
│   └── ElementInflator      # Abstract → real coordinates
├── container_grower.py      # Fase 6: Crecimiento de contenedores
│   └── ContainerGrower      # Bottom-up expansion + label-aware bounds
└── visualizer.py            # 9 SVGs de visualizacion
    └── GrowthVisualizer     # Snapshots de cada fase (NdPr-aware)

AlmaGag/layout/
├── laf_optimizer.py         # Coordinador LAF v2.0 (9 fases)
│   └── LAFOptimizer         # Orquesta todo el pipeline
└── collision.py             # Deteccion de colisiones (skip parent-child)
```

## Resultados

### Diagrama: 13-stresstest.gag (27 elementos, 26 conexiones, 5 VCs)

| Metrica | Sin NdPr | Con NdPr | Mejora |
|---------|----------|----------|--------|
| **Nodos en Fases 3-5** | 27 (5 niveles) | **8 NdPr (3 niveles)** | **-70%** |
| **Colisiones** | 30 | **0** | **-100%** |
| **Cruces** | 1 | **1** | = |

### Diagrama: 05-arquitectura-gag.gag

| Metrica | Sistema Auto | LAF | Mejora |
|---------|-------------|-----|--------|
| **Cruces de conectores** | ~15 | **2** | **-87%** |
| **Colisiones** | 50 | 10 | **-80%** |
| **Routing calls** | 5+ | 1 | **-80%** |
| **Falsos positivos** | 24-32 | 0 | **-100%** |

## Uso

```bash
# Generar con LAF (recomendado para diagramas complejos)
python -m AlmaGag.main archivo.gag --layout-algorithm=laf -o output.svg

# Con visualizacion del proceso (9 SVGs de debug)
python -m AlmaGag.main archivo.gag --layout-algorithm=laf --visualize-growth

# Con conexiones coloreadas
python -m AlmaGag.main archivo.gag --layout-algorithm=laf --color-connections

# Debug completo
python -m AlmaGag.main archivo.gag --layout-algorithm=laf --debug --visualize-growth
```

**Output de visualizacion** en `debug/growth/{diagram}/`:
```
phase1_structure.svg     - Arbol de elementos con metricas
phase2_topology.svg      - Niveles topologicos y accessibility scores
phase3_centrality.svg    - Ordenamiento por centralidad
phase4_abstract.svg      - Posiciones abstractas (puntos 1px)
phase5_optimized.svg     - Posiciones optimizadas (bisection)
phase6_inflated.svg      - Inflacion + contenedores expandidos
phase7_redistributed.svg - Redistribucion vertical + X scale
phase8_routed.svg        - Routing de conexiones
phase9_final.svg         - Layout final completo
```

## Algoritmos Clave

### Barycenter Heuristic (Fase 4)

```python
# Forward pass: promedio de posiciones de padres
barycenter_forward = avg([pos(parent) for parent in parents])

# Backward pass: promedio de posiciones de hijos
barycenter_backward = avg([pos(child) for child in children])

# Combinar
barycenter_final = (forward + backward) / 2
```

### Layer-Offset Bisection (Fase 5)

```python
# Minimizar distancia ponderada de conectores
# Forward: mover cada capa hacia sus predecesores
# Backward: mover cada capa hacia sus sucesores
# Convergencia: delta < 0.001
```

### NdPr Abstraction (Fases 3-5)

```python
# Fase 1 detecta TOI Virtual Containers y construye grafo NdPr:
# 27 elementos (5 niveles) → 8 NdPr nodes (3 niveles)
#   - NdPr simples: jose_heraclides, daria, union_padres
#   - NdPr VCs: _toi_vc_0..4 (agrupan 4-6 elementos cada uno)
#
# Fases 3-5 operan sobre 8 NdPr usando ndpr_connection_graph
# Fase 5.5 expande NdPr → 27 posiciones individuales
```

### NdPr Expansion (Fase 5.5)

```python
# Para cada NdPr:
#   - Simple: copiar posicion directamente
#   - VC: distribuir miembros agrupados por sub-nivel topologico
#     - Sub-nivel 0: parejas (e.g., patricia + ricardo) centradas en anchor
#     - Sub-nivel 1: uniones (e.g., union_patricia) una fila abajo
#     - Sub-nivel 2: hijos (e.g., diego) dos filas abajo
#   - Offsets: 0.4 horizontal, 1.0 vertical (abstract units)
```

### Container Growth (Fase 6)

```python
for container in containers (bottom-up por profundidad):
    # 1. Posicionar hijos en grid horizontal
    # 2. Calcular bounding box (incluyendo labels)
    # 3. Aplicar padding
    # 4. _measure_placed_content() → verificar bounds reales
    # 5. Step 4.5: expandir si labels exceden estimacion
```

### Redistribucion X Scale (Fase 7)

```python
# Formula corregida con half-widths
required_gap = half_width_i + half_width_next + MIN_HORIZONTAL_GAP
# Esto evita solapamiento entre contenedores grandes y elementos pequenos
```

## Historial de Sprints

| Sprint | Fecha | Foco | Fases |
|--------|-------|------|-------|
| 1 | 2026-01-15 | Colisiones falsas + estructura | Fase 1 |
| 2 | 2026-01-17 | Layout abstracto Sugiyama | Fase 4 |
| 3 | 2026-01-18 | Inflacion + integracion CLI | Fase 6 (parte) |
| 4 | 2026-01-19 | Crecimiento de contenedores | Fase 6 (parte) |
| 5 | 2026-01-20 | Visualizacion + polish | Visualizer |
| 6 | 2026-02-08 | Renumeracion + Fase 2 | Fases 2, 3 |
| 7 | 2026-02-17 | Position optimization + X scale | Fase 5 |
| 8 | 2026-02-19 | Consolidacion + metadata + fixes | 9 fases |
| 9 | 2026-02-26 | TOI VCs, NdPr abstract graph | Fases 1, 3-5, 5.5 |
| 10 | 2026-02-27 | NdPr expansion collision fix | Fase 5.5, 7 |

## Referencias

- **Sugiyama et al. (1981)**: "Methods for Visual Understanding of Hierarchical System Structures"
- **Graphviz DOT algorithm**: Layered graph drawing
- **OGDF (Open Graph Drawing Framework)**: Implementaciones de referencia

## Autores

- **Jose** - Arquitectura y diseno
- **ALMA** - Implementacion y documentacion
