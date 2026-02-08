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

## Flujo LAF (Layout Abstracto Primero)

### Phase 1: Structure Analysis

**Archivo:** `AlmaGag/layout/laf/structure_analyzer.py:StructureAnalyzer`

**Responsabilidades:**
1. **Build Element Tree** - Identifica elementos primarios vs contenidos
2. **Build Connection Graph** - Grafo dirigido de conexiones
3. **Calculate Topological Levels** - BFS para asignar niveles
4. **Calculate Accessibility Scores** - Score de importancia de nodos
5. **Group by Type** - Agrupa elementos por tipo

**Output:** `StructureInfo` con toda la metadata estructural

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

**Accessibility Scores:**
- `W_hijos` (hub-ness): Nodos con más hijos tienen mayor score
- `W_precedence` (skip connections): Padres de niveles distantes
- `W_fanin` (opcional): Múltiples padres en mismo nivel

### Phase 2: Abstract Placement

**Archivo:** `AlmaGag/layout/laf/abstract_placer.py:AbstractPlacer`

**Responsabilidades:**
1. **Layering** - Asignar elementos a capas por nivel topológico
2. **Ordering** - Ordenar dentro de capas usando:
   - Barycenter heuristic (promedio de posición de vecinos)
   - Accessibility scores (atracción al centro)
   - Tipo de elemento (agrupación)
3. **Positioning** - Distribuir uniformemente en cada capa

**Output:** `abstract_positions` - Posiciones como puntos de 1px

**Barycenter Bidireccional:**
```python
# Forward pass: promedio de posiciones de padres
barycenter_forward = avg([pos(parent) for parent in parents])

# Backward pass: promedio de posiciones de hijos
barycenter_backward = avg([pos(child) for child in children])

# Combinar ambos
barycenter_final = (barycenter_forward + barycenter_backward) / 2
```

**Integración de Accessibility Score:**
```python
# Atraer nodos importantes al centro
center_x = canvas_width / 2
score_influence = SCORE_CENTER_INFLUENCE  # 0.3

adjusted_x = (
    barycenter_x * (1 - score_influence * score) +
    center_x * (score_influence * score)
)
```

### Phase 3: Inflation

**Archivo:** `AlmaGag/layout/laf/inflator.py:ElementInflator`

**Responsabilidades:**
1. **Convert Abstract → Real** - Mapear posiciones abstractas a píxeles reales
2. **Apply Spacing** - Separación horizontal y vertical entre elementos
3. **Position Labels** - Calcular posición de etiquetas de elementos
4. **Calculate Real Dimensions** - Ancho y alto reales de cada elemento

**Output:** Layout con posiciones reales (x, y) y dimensiones (width, height)

**Cálculo de Dimensiones:**
```python
# Para iconos simples
width = ICON_WIDTH (default: 80px)
height = ICON_HEIGHT (default: 50px)

# Para elementos con etiqueta
label_height = len(lines) * LINE_HEIGHT
total_height = icon_height + LABEL_MARGIN + label_height
```

### Phase 4: Container Growth

**Archivo:** `AlmaGag/layout/laf/container_grower.py:ContainerGrower`

**Responsabilidades:**
1. **Expand Containers** - Calcular dimensiones de contenedores
2. **Fit Contents** - Asegurar que contengan todos sus elementos
3. **Recursive Growth** - Expandir contenedores anidados
4. **Adjust Positions** - Reposicionar elementos afectados

**Output:** Layout con contenedores expandidos

**Algoritmo de Crecimiento:**
```python
for container in containers (bottom-up):
    # Calcular bounding box de contenidos
    min_x = min(child.x for child in contents)
    max_x = max(child.x + child.width for child in contents)
    min_y = min(child.y for child in contents)
    max_y = max(child.y + child.height for child in contents)

    # Aplicar padding
    container.width = (max_x - min_x) + 2 * PADDING
    container.height = (max_y - min_y) + 2 * PADDING
```

### Phase 4.5: Redistribution

**Archivo:** `AlmaGag/layout/laf_optimizer.py:_redistribute_vertically()`

**Responsabilidades:**
1. **Vertical Redistribution** - Espaciado uniforme entre niveles
2. **Horizontal Centering** - Centrar elementos dentro de cada nivel
3. **Preserve Order** - Mantener orden optimizado de Phase 2

**Output:** Layout final con distribución óptima

**Centrado Horizontal:**
```python
for level in levels:
    elements = elements_in_level(level)
    total_width = sum(elem.width for elem in elements)
    spacing = calculate_spacing(elements)

    # Centrar el grupo
    start_x = (canvas_width - total_width - spacing) / 2

    for elem in elements:
        elem.x = start_x
        start_x += elem.width + spacing
```

### Phase 5: Routing

**Archivo:** `AlmaGag/routing/router_manager.py:RouterManager`

**Responsabilidades:**
1. **Calculate Paths** - Calcular trayectorias de conexiones
2. **Avoid Collisions** - Evitar solapamiento con elementos
3. **Route Types** - Orthogonal, curved, direct
4. **Waypoints** - Puntos intermedios para rutas complejas

**Output:** Lista de paths SVG para cada conexión

### Phase 6: Visualization (Opcional)

**Archivo:** `AlmaGag/layout/laf/visualizer.py:GrowthVisualizer`

**Solo si:** `--visualize-growth` está activado

**Genera:**
- `debug/growth/{diagram}/phase1_structure.svg`
- `debug/growth/{diagram}/phase2_abstract.svg`
- `debug/growth/{diagram}/phase3_inflated.svg`
- `debug/growth/{diagram}/phase4_final.svg`

### Phase 7: SVG Generation

**Archivo:** `AlmaGag/generator.py:generate_svg()`

**Responsabilidades:**
1. **Create SVG Canvas** - Crear documento SVG
2. **Draw Elements** - Dibujar iconos y contenedores
3. **Draw Connections** - Dibujar líneas/paths
4. **Draw Labels** - Dibujar texto de etiquetas
5. **Apply Visual Debug** - Si `--visualdebug`:
   - Grilla de referencia
   - Números de nivel en rojo
   - Bounding boxes punteados
   - Badge de debug
6. **Save SVG** - Escribir archivo

**Output:** Archivo SVG final

### Phase 8: PNG Export (Opcional)

**Solo si:** `--exportpng` está activado

**Responsabilidades:**
- Convertir SVG a PNG usando librería externa
- Guardar en `debug/outputs/{name}.png`

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
- `phase2_abstract.svg` - Layout abstracto + número de cruces
- `phase3_inflated.svg` - Layout inflado
- `phase4_final.svg` - Layout final

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

**Última actualización:** 2026-02-06
**Versión del sistema:** v3.0+
