# Flujo de Ejecución de AlmaGag

Este documento describe el flujo de ejecución completo del sistema AlmaGag cuando se genera un diagrama.

## Diagrama Visual

Ver: `docs/diagrams/svgs/06-flujo-ejecucion.svg`

## Flujo Paso a Paso

### 1. Entry Point: `main.py`

**Archivo:** `AlmaGag/main.py`

- Punto de entrada del programa
- Parse de argumentos de línea de comando
- Configuración de opciones de debug y visualización

**Argumentos clave:**
- `--layout-algorithm={auto|laf}` - Selección de algoritmo
- `--debug` - Logs detallados
- `--visualdebug` - Elementos visuales de debug (grilla, niveles)
- `--visualize-growth` - Genera SVGs de cada fase LAF
- `--exportpng` - Exporta también a PNG

### 2. Carga del Archivo .gag

**Archivo:** `AlmaGag/main.py:load_gag_file()`

- Lee archivo JSON en formato SDJF (Simple Diagram JSON Format)
- Valida estructura básica
- Extrae: `elements`, `connections`, `canvas`

### 3. Creación del Layout Object

**Archivo:** `AlmaGag/layout/__init__.py:Layout`

- Construye objeto Layout con:
  - `elements` - Lista de elementos (iconos, contenedores)
  - `connections` - Lista de conexiones entre elementos
  - `elements_by_id` - Diccionario para acceso rápido
  - Análisis inicial de grafo

### 4. Selección de Algoritmo

Dos caminos posibles:

#### Camino A: LAF Optimizer (Recomendado)
**Archivo:** `AlmaGag/layout/laf_optimizer.py:LAFOptimizer`

Layout Abstracto Primero - Minimiza cruces de conexiones

#### Camino B: Auto Optimizer (Legacy)
**Archivo:** `AlmaGag/layout/auto_optimizer.py:AutoLayoutOptimizer`

Sistema anterior basado en detección de colisiones

---

## Flujo LAF (Layout Abstracto Primero) — 10 Fases

### Phase 1: Structure Analysis

**Archivo:** `AlmaGag/layout/laf/structure_analyzer.py:StructureAnalyzer`

**Responsabilidades:**
1. **Build Element Tree** - Identifica elementos primarios vs contenidos
2. **Build Connection Graph** - Grafo dirigido de conexiones
3. **Calculate Topological Levels** - BFS para asignar niveles (longest-path)
4. **Calculate Accessibility Scores** - Score de importancia de nodos
5. **Group by Type** - Agrupa elementos por tipo

**Output:** `StructureInfo` con toda la metadata estructural

**Detección de TOI Virtual Containers:**
- Identifica patrones TOI (elementos que comparten un nodo pivot)
- Crea Virtual Containers (VCs) que agrupan 4-6 elementos relacionados
- Construye grafo abstracto NdPr: `ndpr_elements`, `ndpr_topological_levels`, `ndpr_connection_graph`
- Ejemplo: 27 elementos (5 niveles) → 8 NdPr nodes (3 niveles)

**Algoritmo de Niveles Topológicos:**
```python
# Forward pass con BFS
# Nivel 0: Nodos sin dependencias entrantes
# Nivel N: max(nivel_de_padres) + 1

for neighbor in successors(current):
    new_level = current_level + 1
    topological_levels[neighbor] = max(
        topological_levels[neighbor],
        new_level
    )
```

### Phase 2: Topological Analysis (Visualización)

**Archivo:** Visualización en `laf_optimizer.py`

**Responsabilidades:**
1. **Mostrar Niveles Topológicos** - Distribución de elementos por nivel
2. **Mostrar Accessibility Scores** - Top elementos con mayor score
3. **Visualizar Topología** - SVG con niveles y color-coding por score

**Output:** Debug info + `phase2_topology.svg`

**Color Coding por Score:**
- **Rojo** (score > 0.05): Elementos muy importantes (hubs principales)
- **Amarillo** (0.02 - 0.05): Elementos importantes
- **Azul** (< 0.02): Elementos normales

### Phase 3: Centrality Ordering

**Archivo:** `AlmaGag/layout/laf_optimizer.py`

**Responsabilidades:**
1. **Ordenar por centralidad** sobre NdPr nodes (si disponible)
2. **VCs:** score = max(accessibility_scores de miembros)
3. **Preparar entrada para Abstract Placement**

**Output:** Orden de centralidad + `phase3_centrality.svg`

### Phase 4: Abstract Placement

**Archivo:** `AlmaGag/layout/laf/abstract_placer.py:AbstractPlacer`

**Modo NdPr** (cuando `connection_graph` se proporciona):
- Opera sobre 8 NdPr nodes en lugar de 27 elementos individuales
- Usa `ndpr_connection_graph` para barycenter directo
- No genera posiciones de contenidos ni aplica adjacencia TOI

**Responsabilidades:**
1. **Layering** - Asignar NdPr nodes a capas por nivel topológico
2. **Ordering** - Ordenar dentro de capas usando barycenter sobre `ndpr_connection_graph`
3. **Positioning** - Distribuir uniformemente en cada capa

**Output:** `abstract_positions` - Posiciones como puntos de 1px + `phase4_abstract.svg`

**Barycenter Bidireccional:**
```python
# Forward pass: promedio de posiciones de padres
barycenter_forward = avg([pos(parent) for parent in parents])

# Backward pass: promedio de posiciones de hijos
barycenter_backward = avg([pos(child) for child in children])

# Combinar ambos
barycenter_final = (barycenter_forward + barycenter_backward) / 2
```

### Phase 5: Position Optimization

**Archivo:** `AlmaGag/layout/laf/position_optimizer.py:PositionOptimizer`

**Modo NdPr:** Recibe `connection_graph` y `topological_levels` explícitos. Todos los NdPr nodes son "primarios" (sin contenidos).

**Responsabilidades:**
1. **Layer-offset bisection** - Minimizar distancia ponderada de conectores
2. **Forward + backward iterations** - Convergencia < 0.001
3. **Preservar orden relativo** del barycenter

**Output:** Posiciones optimizadas + `phase5_optimized.svg`

### Phase 6: NdPr Expansion

**Archivo:** `AlmaGag/layout/laf_optimizer.py:_expand_ndpr_to_elements()`

**Responsabilidades:**
1. **Expandir NdPr → elementos** - Convierte 8 posiciones NdPr a 27 posiciones individuales
2. **VCs:** Distribuir miembros por sub-nivel topológico (offsets: 0.4 horizontal, 1.0 vertical)
3. **Simples:** Copiar posición directamente
4. **Reconstruir `optimized_layer_order`** desde `topological_levels`

**Output:** `expanded_positions` - 27 posiciones de elementos individuales

### Phase 7: Inflation + Container Growth (fusionadas)

**Archivos:**
- `AlmaGag/layout/laf/inflator.py:ElementInflator`
- `AlmaGag/layout/laf/container_grower.py:ContainerGrower`

**Responsabilidades:**
1. **Convert Abstract → Real** - Mapear posiciones abstractas a píxeles reales
2. **Apply Spacing** - Separación horizontal y vertical
3. **Calculate Real Dimensions** - Ancho y alto reales
4. **Expand Containers** - Bottom-up, ajustar a contenido
5. **Position Children** - Grid horizontal dentro de contenedores
6. **_measure_placed_content()** - Post-check de bounds reales incluyendo labels
7. **Step 4.5 expansion** - Expandir si labels exceden estimación

**Output:** Layout con posiciones reales y contenedores expandidos + `phase7_inflated.svg`

**Algoritmo de Crecimiento:**
```python
for container in containers (bottom-up):
    # Posicionar hijos en grid horizontal
    # Calcular bounding box incluyendo labels
    # Aplicar padding
    # _measure_placed_content() → verificar bounds reales
    # Expandir si labels exceden estimación (step 4.5)
```

### Phase 8: Vertical Redistribution

**Archivo:** `AlmaGag/layout/laf_optimizer.py:_redistribute_vertical_after_growth()`

**Responsabilidades:**
1. **Vertical Redistribution** - Espaciado uniforme entre niveles
2. **Horizontal X Scale** - `half_width_i + half_width_next + MIN_GAP`
3. **Global Centering** - Centrar usando bounding boxes de grupos NdFn
4. **Preserve Order** - Mantener orden optimizado de Phase 4

**Output:** Layout redistribuido + `phase8_redistributed.svg`

### Phase 9: Routing

**Archivo:** `AlmaGag/routing/router_manager.py:RouterManager`

**Responsabilidades:**
1. **Calculate Paths** - Trayectorias de conexiones
2. **Self-loop Detection** - Arcos para `from == to` con `large-arc-flag=1`
3. **Container Border Routing** - Conexiones a bordes de contenedores
4. **Route Types** - Orthogonal, curved, direct, arc

**Output:** Lista de computed_paths + `phase9_routed.svg`

### Phase 10: SVG Generation

**Archivo:** `AlmaGag/generator.py:generate_svg()`

**Responsabilidades:**
1. **Create SVG Canvas** - Documento SVG con `debug=False`
2. **Define Filters** - Gaussian blur text glow (`feGaussianBlur`)
3. **NdFn Metadata** - Wrapping en `<g>` con `<desc>` (via `DrawingGroupProxy`)
4. **Draw Containers** - Rectángulos redondeados con gradiente
5. **Draw Icons** - Shapes con gradientes
6. **Draw Connections** - Líneas/paths/arcos, coloreadas opcional
7. **Draw Labels** - Texto con `filter="url(#text-glow)"`
8. **Optimize Labels** - Reposicionar labels (excluir contenidos)
9. **Visual Debug** - Si `--visualdebug`: grilla, niveles, badges
10. **Save SVG** - Escribir archivo

**Output:** Archivo SVG final + `phase10_final.svg`

### PNG Export (Opcional)

**Solo si:** `--exportpng` está activado

**Responsabilidades:**
- Convertir SVG a PNG usando Chrome/Edge headless
- Guardar en `debug/outputs/{name}.png`

### Visualización del Proceso (Opcional)

**Solo si:** `--visualize-growth` está activado

**Archivo:** `AlmaGag/layout/laf/visualizer.py:GrowthVisualizer`

**Genera 10 SVGs** en `debug/growth/{diagram}/`:
1. `phase1_structure.svg` - Árbol de elementos con métricas
2. `phase2_topology.svg` - Niveles topológicos y scores
3. `phase3_centrality.svg` - Ordenamiento por centralidad
4. `phase4_abstract.svg` - Posiciones abstractas (puntos)
5. `phase5_optimized.svg` - Posiciones optimizadas
6. `phase6_expanded.svg` - NdPr expansion a elementos individuales
7. `phase7_inflated.svg` - Inflación + contenedores expandidos
8. `phase8_redistributed.svg` - Redistribución vertical
9. `phase9_routed.svg` - Routing de conexiones
10. `phase10_final.svg` - Layout final completo

---

## Estructuras de Datos Clave

### StructureInfo

Información estructural del diagrama calculada en Phase 1:

```python
@dataclass
class StructureInfo:
    element_tree: Dict[str, Dict]           # Árbol de elementos
    primary_elements: List[str]             # IDs de elementos primarios
    container_metrics: Dict[str, Dict]      # Métricas de contenedores
    connection_graph: Dict[str, List[str]]  # Grafo de adyacencia
    incoming_graph: Dict[str, List[str]]    # Grafo inverso
    topological_levels: Dict[str, int]      # Nivel de cada elemento
    accessibility_scores: Dict[str, float]  # Score de accesibilidad
    element_types: Dict[str, List[str]]     # Elementos por tipo

    # NdPr (Nodo Primario) - Grafo abstracto
    toi_virtual_containers: List[Dict]      # VCs: {id, members, toi_id, pivot_id}
    ndpr_elements: List[str]                # IDs de NdPr nodes ordenados
    ndpr_topological_levels: Dict[str, int] # Nivel de cada NdPr
    ndpr_connection_graph: Dict[str, List[str]]  # Grafo de adyacencia NdPr
    element_to_ndpr: Dict[str, str]         # Mapeo elemento → NdPr representative
```

### Layout Object

Objeto central que mantiene el estado del diagrama:

```python
class Layout:
    elements: List[Dict]              # Lista de elementos
    connections: List[Dict]           # Lista de conexiones
    elements_by_id: Dict[str, Dict]   # Acceso rápido por ID
    canvas: Dict                      # {width, height}
    groups: List[List[str]]           # Grupos conectados
    levels: Dict[str, int]            # Niveles topológicos
    optimized_layer_order: List[List[str]]  # Orden guardado de Phase 2
```

---

## Parámetros de Configuración

### Constantes de Layout

**Archivo:** `AlmaGag/layout/laf/inflator.py`

```python
ICON_WIDTH = 80          # Ancho de ícono por defecto
ICON_HEIGHT = 50         # Alto de ícono por defecto
H_SPACING = 50           # Espaciado horizontal
V_SPACING = 120          # Espaciado vertical
LABEL_MARGIN = 15        # Margen entre ícono y etiqueta
```

### Constantes de Accessibility

**Archivo:** `AlmaGag/layout/laf/structure_analyzer.py`

```python
ALPHA = 0.03   # W_precedence: skip connections
BETA = 0.01    # W_hijos: hub-ness
GAMMA = 0.0    # W_fanin: same-level parents (disabled)
```

### Constantes de Abstract Placer

**Archivo:** `AlmaGag/layout/laf/abstract_placer.py`

```python
SCORE_CENTER_INFLUENCE = 0.3  # Influencia del score en atracción al centro
```

---

## Archivos de Debug

### Logs de Consola

Con `--debug`:
- `[LAF]` - Mensajes del sistema LAF
- `[ABSTRACT]` - Mensajes del abstract placer
- `[TOPOLOGICAL]` - Cambios en niveles topológicos
- `[ACCESSIBILITY]` - Scores calculados
- `[CENTRADO]` - Operaciones de centrado

### Archivos CSV

En `debug/`:
- `layout_evolution_YYYYMMDD_HHMMSS.csv` - Evolución del layout por fases

### Visualizaciones de Crecimiento

En `debug/growth/{diagram}/`:
- `phase1_structure.svg` - Análisis estructural
- `phase2_topology.svg` - Niveles topológicos + scores
- `phase3_centrality.svg` - Ordenamiento por centralidad
- `phase4_abstract.svg` - Layout abstracto + cruces
- `phase5_optimized.svg` - Posiciones optimizadas
- `phase6_expanded.svg` - NdPr expansion
- `phase7_inflated.svg` - Inflación + contenedores
- `phase8_redistributed.svg` - Redistribución vertical
- `phase9_routed.svg` - Routing de conexiones
- `phase10_final.svg` - Layout final

---

## Casos Especiales

### Nodos sin Conexiones

Los nodos aislados (sin conexiones) se colocan en nivel 0 y se posicionan al final del layout.

### Contenedores Anidados

Los contenedores se expanden recursivamente de adentro hacia afuera (bottom-up).

### Cruces de Conexiones

El algoritmo LAF minimiza cruces usando:
1. Ordenamiento topológico correcto
2. Barycenter heuristic bidireccional
3. Accessibility scores para hub positioning

### Canvas Auto-Expansion

Si los elementos no caben en el canvas inicial, se expande automáticamente.

---

## Comparación: LAF vs Auto

| Aspecto | LAF (Recomendado) | Auto (Legacy) |
|---------|-------------------|---------------|
| **Cruces** | Minimizados | No optimizado |
| **Niveles** | Topológicos | Por prioridad |
| **Orden** | Barycenter + Score | Detección colisiones |
| **Velocidad** | Rápido (O(n log n)) | Lento (iterativo) |
| **Contenedores** | Crecimiento bottom-up | Cálculo top-down |
| **Debug** | Visualización por fases | Solo iteraciones |

---

## Referencias

- Algoritmo base: Sugiyama et al. (1981) - "Methods for Visual Understanding of Hierarchical System Structures"
- Barycenter heuristic: Carpano (1980)
- Accessibility scores: Diseño propio basado en PageRank

---

**Última actualización:** 2026-02-28
**Versión del sistema:** v3.3.0 (LAF 10 fases)
