# Arquitectura de AlmaGag

**Versión del Código**: v3.5 + SDJF v2.1
**Fecha**: 2026-06-23

## Visión General

AlmaGag es un generador de diagramas SVG que transforma archivos JSON (formato SDJF/`.gag`) en gráficos vectoriales mediante un pipeline de procesamiento modular. Tres capas de decisión sobre dónde poner cada elemento:

1. **Templates (`layout/templates/`)** — Detección semántica del patrón estructural del grafo (architecture / flow / hub_and_spoke / dashboard / er / sequence / state). Asigna coords cuando faltan **antes** de que corra el algoritmo de layout. Opt-in vía `"layout_template": "auto" | "<name>"`. **Norte estratégico del proyecto (WISH-LAYOUT-004).**
2. **Algoritmos de layout** — Resuelven coordenadas restantes:
   - **AUTO** — Híbrido. Respeta coordenadas manuales y auto-posiciona el resto vía optimización iterativa (hill climbing).
   - **LAF** — Layout Abstracto Primero. Pipeline de 11 fases inspirado en Sugiyama/Graphviz que ignora coordenadas y minimiza cruces.
   Ambos cumplen `LayoutOptimizer`, seleccionables vía CLI (`--layout-algorithm`).
3. **Validación visual (`validation/`)** — Audit post-render contra 3 reglas de calidad (labels-no-sobre-icono, labels-no-solapados, no-conectores-sueltos). Usable como regresión visual.

### Refactores recientes (resumen)

| Código | Resuelto | Resumen |
|---|---|---|
| WISH-LAYOUT-004 (Fase 1-4) | 2026-06-19..23 | Auto-detección semántica del template óptimo según estructura del grafo. 7 templates + nested templates + semantic hints (`role`). Módulo `layout/templates/`. |
| BUGS-AUTO-001..007 | 2026-06-19..22 | 7 fixes en cascada en el pipeline AUTO con containers: re-cálculo de labels, normalización a coords no-negativas, containers no bloquean labels, resolución de overlap entre containers, clamping de labels a canvas/container, escalonado horizontal, ancho correcto para bold en headers. |
| WISH-ARCH-003 | 2026-06-19 | Reorg de `draw/` en `primitives/` (4 archivos) + `icons/` (11 archivos). Split de `laf/visualizer.py` (2876 líneas) en paquete `laf/visualizer/` con 11 archivos (uno por fase). |
| WISH-LAYOUT-003 | 2026-06-19 | Auto-callout para labels grandes (≥6 líneas / ≥150 chars) en `draw/primitives/callout.py`. |
| WISH-LAYOUT-002 v1 | 2026-06-19 | SDJF: `constraints.align` para grupos co-alineados. |
| WISH-LAF-001 v1 | 2026-06-19 | Pesos dinámicos del barycenter (más cruces de conexiones reducidos). |
| `validation/` (3 reglas) | 2026-06-23 | Módulo nuevo: chequeo automático de calidad visual sobre SVGs y `.gag`. |
| WISH-ARCH-001 | 2026-06-18 | `LAFOptimizer` hereda de `LayoutOptimizer`; `generator.py` usa factoría (`OPTIMIZERS` dict) en vez de `if/elif`. |
| WISH-ARCH-002 | 2026-06-18 | Renderers separados por algoritmo (`AutoSVGRenderer`, `LAFSVGRenderer`); primitivas SVG agnósticas en `draw/primitives/svg.py`. Eliminado `AlmaGag/renderer.py` (legacy compartido). |
| BUGS-LAYOUT-002 | 2026-06-18 | LAF: margen vertical de canvas separado del horizontal (waste ~33% → ~18%). |
| BUGS-LAF-002 | 2026-06-18 | LAF: nuevo Fase 1.5 "dashboard reflow" + skip de doble-mover de hijos en Fase 9. |
| BUGS-LAYOUT-001 | 2026-06-18 | Renderers: etiquetas de `--visualdebug` movidas fuera del bbox del elemento, con `text-glow`. |
| BUGS-LAYOUT-003 | 2026-06-14 | LAF + AUTO: 7 puntos de no-determinismo cerrados con `sorted()` + tie-break por `elem_id`. |
| BUGS-DIAG-001..008 | 2026-06-15 | 8 fixes visuales en SVGs canónicos (ver `DIAGRAM_REVIEW.md`). |

## Diagrama de Arquitectura

![Arquitectura de GAG](../diagrams/svgs/05-arquitectura-gag.svg)

## Flujo de Ejecución

```
┌─────────────┐
│  archivo.gag│
│   (SDJF)    │
└──────┬──────┘
       │
       v
┌─────────────┐
│  main.py    │  CLI entry point (argparse + dispatch a generator)
└──────┬──────┘
       │
       v
┌────────────────────────────────────────────────────────────┐
│  generator.py (190 líneas)  —  Orquestador delgado         │
│  ┌──────────────────────────────────────────────────┐      │
│  │ 1. Parse JSON                                    │      │
│  │ 2. Template detection (WISH-LAYOUT-004):         │      │
│  │      data["layout_template"] == "auto"           │      │
│  │           → classify(features) → apply           │      │
│  │      data["layout_template"] == "<name>"         │      │
│  │           → apply ese template (override manual) │      │
│  │      ausente → agnóstico (algoritmo AUTO/LAF)    │      │
│  │      [sub-templates en containers SIEMPRE corren]│      │
│  │ 3. Layout (Value Object inmutable)               │      │
│  │ 4. Factoría: OPTIMIZERS[layout_algorithm]        │      │
│  │       ├─ 'auto' → AutoLayoutOptimizer            │      │
│  │       └─ 'laf'  → LAFOptimizer                   │      │
│  │ 5. optimizer.optimize(layout)                    │      │
│  │ 6. optimizer.renderer.render(layout, output)     │      │
│  │       AutoSVGRenderer (inline icon)              │      │
│  │       LAFSVGRenderer (separate icon + NdFn)      │      │
│  └──────────────────────────────────────────────────┘      │
└──────┬─────────────────────────────────────────────────────┘
       │
       v
┌─────────────┐
│ archivo.svg │  (con <desc> NdFn metadata si LAF + visualdebug)
└─────────────┘

(opcional, fuera del pipeline de render)
┌─────────────────────────────────┐
│ validation.validate_svg(path)   │  3 reglas R1/R2/R3 → QualityReport
│ validation.validate_gag(path)   │  reusa posiciones reales del optimizer
└─────────────────────────────────┘
```

Tras WISH-ARCH-002 (2026-06-18), cada algoritmo es **autosuficiente**: su optimizer construye su propio renderer en `__init__`, y `generator.py` solo despacha sin conocer detalles de cada algoritmo. Las primitivas SVG agnósticas (`create_canvas`, `setup_arrow_markers`, `draw_connections`, etc.) viven en `AlmaGag/draw/primitives/svg.py` (renombrado de `draw/svg.py` por WISH-ARCH-003).

El paso 2 (template detection) corre **antes** de que el optimizer vea el layout, por lo que las coordenadas que el template asigne se respetan como manuales por el resto del pipeline. Si el SDJF no declara `layout_template`, el paso 2 se omite por completo y el comportamiento es el agnóstico clásico (AUTO/LAF normal sobre las coords del JSON).

### Pipeline LAF (12 fases — 11 numeradas + 1.5)

```
Fase 1:    Structure Analysis      → laf/structure_analyzer.py
Fase 1.5:  Dashboard Reflow        → laf/optimizer.py (fix BUGS-LAF-002)
Fase 2:    Topology Analysis       → laf/optimizer.py (viz)
Fase 3:    Centrality Ordering     → laf/optimizer.py
Fase 4:    Abstract Placement      → laf/abstract_placer.py
Fase 5:    Position Optimization   → laf/position_optimizer.py
Fase 6:    NdPr Expansion          → laf/optimizer.py
Fase 7:    Iterative Summary       → laf/visualizer.py
Fase 8:    Inflation + Growth      → laf/inflator.py + laf/container_grower.py
Fase 9:    Vertical Redistribution → laf/optimizer.py
Fase 10:   Routing                 → laf/routing_policy.py → routing/router_manager.py
Fase 10.5: Re-optimize labels      → laf/optimizer.py (post-routing)
Fase 11:   SVG Generation          → laf/laf_renderer.py
```

**Fase 1.5 (dashboard reflow)** detecta clusters de 3+ contenedores root en el mismo nivel topológico sin conexiones inter-contenedor y los redistribuye en grid `ceil(sqrt(N))` cols × `ceil(N/cols)` filas. Sin esto, LAF apilaba esos contenedores en fila horizontal generando canvas extremos (5900×243 en posters). Ver `modules/layout/laf/LAF.md`.

## Módulos Principales

### 1. `main.py`

**Responsabilidad:** Punto de entrada CLI

**Argumentos principales:**
- `archivo.gag` - Archivo de entrada (SDJF JSON)
- `--layout-algorithm={auto|laf}` - Selección de algoritmo (default: auto)
- `-o output.svg` - Archivo de salida
- `--debug` - Logs detallados
- `--visualdebug` - Elementos visuales de debug (grilla, niveles, NdFn labels)
- `--visualize-growth` - Genera 9 SVGs de cada fase LAF
- `--color-connections` - Conexiones con colores únicos
- `--exportpng` - Exporta también a PNG

---

### 2. `generator.py`

**Responsabilidad:** Orquestador delgado del proceso completo (187 líneas tras Tier 1).

```python
from AlmaGag.layout import Layout, AutoLayoutOptimizer
from AlmaGag.layout.laf.optimizer import LAFOptimizer

# Factoría: ambos optimizers heredan de LayoutOptimizer (WISH-ARCH-001).
OPTIMIZERS = {
    'auto': AutoLayoutOptimizer,
    'laf':  LAFOptimizer,
}

def generate_diagram(json_file, layout_algorithm='auto', ...):
    # 1. Parse + Layout inmutable
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    layout = Layout(
        elements=data['elements'],
        connections=data['connections'],
        canvas=data.get('canvas', {'width': WIDTH, 'height': HEIGHT}),
    )

    # 2. Optimizer self-contained — construye sus propios colaboradores.
    optimizer_cls = OPTIMIZERS[layout_algorithm]
    optimizer = optimizer_cls(verbose=debug, visualdebug=visualdebug, ...)

    # 3. Optimizar con firma unificada.
    optimizer.optimize(layout, max_iterations=10, ...)

    # 4. Renderizar — cada optimizer trae su renderer (WISH-ARCH-002).
    optimizer.renderer.render(
        layout, output_svg,
        visualdebug=visualdebug, debug=debug, ...,
    )
```

**Lo que `generator.py` ya NO hace** (tras WISH-ARCH-001/002):
- No conoce el orden de renderizado por algoritmo (eso vive en cada renderer).
- No instancia colaboradores del optimizer (`sizing`, `geometry`, `router_manager`, etc.) — el optimizer los construye internamente.
- No usa `if layout_algorithm == 'laf' / elif ...` — la factoría desacopla.

**Orden de renderizado** (definido por cada renderer, idéntico en ambos):
1. **Container backgrounds** → rect de fondo (LAF + AUTO).
2. **Icons** de elementos no-container.
3. **Container icons** (solo LAF — elemento separado; AUTO los dibuja inline en el rect).
4. **Connections** (líneas + markers).
5. **Labels** optimizados (`LabelPositionOptimizer`) + container labels.
6. **Debug overlays** (solo si `--visualdebug`).

---

### 3. `config.py`

**Responsabilidad:** Constantes globales

```python
# Dimensiones base de íconos (usadas por hp/wp en SDJF v2.0)
ICON_WIDTH = 80
ICON_HEIGHT = 50

# Tamaño de canvas por defecto
DEFAULT_CANVAS_WIDTH = 1400
DEFAULT_CANVAS_HEIGHT = 900
```

---

### 4. Módulo `layout/` (Refactorización v2.1)

**Responsabilidad:** Almacenamiento de datos y optimización

#### `layout/layout.py`

**Clase `Layout`** - Contenedor inmutable del estado

```python
@dataclass
class Layout:
    elements: List[dict]
    connections: List[dict]
    canvas: dict
    elements_by_id: dict = field(init=False)

    # Atributos de análisis (escritos por optimizador)
    levels: dict = field(default_factory=dict)
    groups: List[Set[str]] = field(default_factory=list)
    priorities: dict = field(default_factory=dict)

    def copy(self) -> 'Layout':
        """Crea deep copy independiente para optimización."""
        return Layout(
            elements=deepcopy(self.elements),
            connections=deepcopy(self.connections),
            canvas=self.canvas.copy()
        )
```

**Patrón de diseño:** Inmutabilidad
- `optimize()` NO modifica el layout original
- Retorna nuevo layout optimizado
- Permite comparar candidatos durante iteraciones

#### `layout/optimizer_base.py`

**Clase abstracta `LayoutOptimizer`**

```python
class LayoutOptimizer(ABC):
    @abstractmethod
    def optimize(self, layout: Layout, max_iterations: int = 10,
                 dump_iterations: bool = False, input_file=None) -> Layout:
        """Optimiza layout, retorna nuevo layout."""
        pass
```

**Contrato actual (post WISH-ARCH-001)**:
- Ambos optimizers (`AutoLayoutOptimizer`, `LAFOptimizer`) heredan de esta clase.
- Firma `optimize()` unificada: LAF ignora silenciosamente los kwargs que no aplican.
- Cada optimizer expone `self.renderer` (instancia de `AutoSVGRenderer` o `LAFSVGRenderer`), construido en `__init__`.
- Construcción **self-contained**: el optimizer crea sus propios colaboradores (`sizing`, `geometry`, `router_manager`, etc.). Acepta inyección opcional vía kwargs (legacy / tests).

**Propósito**: contrato estable para algoritmos. Agregar un tercer algoritmo solo requiere implementar `LayoutOptimizer` + un renderer y agregar una entrada al dict `OPTIMIZERS` en `generator.py`.

#### `layout/auto/optimizer.py`

**Clase `AutoLayoutOptimizer`** — algoritmo de layout original. Respeta coordenadas manuales y resuelve el resto con auto-positioning + optimización iterativa (hill climbing) de colisiones. Routing encapsulado en `AutoRoutingPolicy`. Su `renderer` es `AutoSVGRenderer` (definido en `layout/auto/auto_renderer.py`).

Post-passes del optimizer (todos cubren bugs BUGS-AUTO-001..007):
- `_recalculate_label_positions_after_container_move` — fix BUGS-AUTO-001 (labels huérfanas tras mover icons por containers).
- `_normalize_to_canvas` — fix BUGS-AUTO-002 (coords negativas → desplaza todo al origen).
- `_resolve_container_overlaps` + `_shift_container_subtree` — fix BUGS-AUTO-004 (containers solapados, cascada de empujones).
- `_stagger_overlapping_contained_labels` — fix BUGS-AUTO-006 (labels bottom solapados horizontalmente; escalona en vertical y expande container).
- `_label_inside_container` + `_label_within_canvas` chequeos en `_find_best_label_position` — fix BUGS-AUTO-005 (labels off-canvas / fuera de container).

📍 Referencia detallada (5 fases, tabla AUTO vs LAF, workaround Dashboard layout): `modules/layout/auto/AUTO.md`.

#### `layout/sizing.py` (NUEVO en v2.0)

**Clase `SizingCalculator`** - Soporte para hp/wp

```python
class SizingCalculator:
    def get_element_size(self, element) -> Tuple[float, float]:
        """Calcula (width, height) final considerando hp/wp."""
        if 'width' in element and 'height' in element:
            return (element['width'], element['height'])

        hp = element.get('hp', 1.0)
        wp = element.get('wp', 1.0)

        width = element.get('width', ICON_WIDTH * wp)
        height = element.get('height', ICON_HEIGHT * hp)

        return (width, height)

    def get_element_weight(self, element) -> float:
        """Peso = hp × wp (para optimización)."""
        hp = element.get('hp', 1.0)
        wp = element.get('wp', 1.0)
        return hp * wp

    def get_centrality_score(self, element, priority: int) -> float:
        """Score = (3 - priority) × hp × wp."""
        hp = element.get('hp', 1.0)
        wp = element.get('wp', 1.0)
        priority_weight = 3 - priority
        return priority_weight * hp * wp
```

#### `layout/auto/positioner.py` (post-refactor)

**Clase `AutoLayoutPositioner`** — auto-layout para coordenadas faltantes (introducido en SDJF v2.0). Estrategia híbrida prioridad + grid + centralidad: HIGH al centro, NORMAL en anillo medio, LOW en anillo externo.

📍 Detalle en `modules/layout/auto/AUTO.md` (sección "Fase 0 — Auto-positioning").

#### `layout/geometry.py`

**Clase `GeometryCalculator`** - Cálculos geométricos

```python
class GeometryCalculator:
    def __init__(self, sizing=None):
        self.sizing = sizing

    def get_icon_bbox(self, element) -> Optional[Tuple]:
        """Retorna (x1, y1, x2, y2) o None si falta coord."""
        x = element.get('x')
        y = element.get('y')
        if x is None or y is None:
            return None

        # Usar sizing para hp/wp (v2.0)
        if self.sizing:
            width, height = self.sizing.get_element_size(element)
        else:
            width, height = ICON_WIDTH, ICON_HEIGHT

        return (x, y, x + width, y + height)

    def rectangles_intersect(self, bbox1, bbox2) -> bool:
        """Detecta overlap entre dos rectángulos."""
        x1_min, y1_min, x1_max, y1_max = bbox1
        x2_min, y2_min, x2_max, y2_max = bbox2

        return not (x1_max <= x2_min or x2_max <= x1_min or
                    y1_max <= y2_min or y2_max <= y1_min)

    def line_intersects_rect(self, line_start, line_end, bbox) -> bool:
        """Detecta si línea cruza rectángulo."""
        # Implementación usando algoritmo de Cohen-Sutherland
        # ...
```

#### `layout/collision.py`

**Clase `CollisionDetector`** - Detección de colisiones

```python
class CollisionDetector:
    def __init__(self, geometry):
        self.geometry = geometry

    def detect_all_collisions(self, layout) -> List[Tuple]:
        """Retorna lista de colisiones (id1, id2, tipo)."""
        collisions = []
        all_bboxes = self._collect_all_bboxes(layout)

        for i, (bbox1, type1, id1) in enumerate(all_bboxes):
            for bbox2, type2, id2 in all_bboxes[i+1:]:
                if self.geometry.rectangles_intersect(bbox1, bbox2):
                    collisions.append((id1, id2, f"{type1}-{type2}"))

        return collisions

    def _collect_all_bboxes(self, layout):
        """Recolecta bboxes de íconos, labels y conexiones."""
        bboxes = []

        # Filtrar elementos sin coordenadas (v2.0)
        positioned = [e for e in layout.elements if 'x' in e and 'y' in e]

        # Bboxes de íconos
        for elem in positioned:
            bbox = self.geometry.get_icon_bbox(elem)
            if bbox:
                bboxes.append((bbox, 'icon', elem['id']))

        # Bboxes de labels
        for elem in positioned:
            label_pos = layout.label_positions.get(elem['id'])
            if label_pos:
                bbox = self.geometry.get_label_bbox(elem, label_pos)
                if bbox:
                    bboxes.append((bbox, 'label', elem['id']))

        # Bboxes de conexiones
        # ...

        return bboxes
```

#### `layout/graph_analysis.py`

**Clase `GraphAnalyzer`** - Análisis de estructura

```python
class GraphAnalyzer:
    def calculate_priorities(self, layout):
        """Calcula prioridades basadas en conexiones."""
        connection_count = {}

        for conn in layout.connections:
            for node_id in [conn['from'], conn['to']]:
                connection_count[node_id] = connection_count.get(node_id, 0) + 1

        priorities = {}
        for elem in layout.elements:
            elem_id = elem['id']

            # Manual override
            if 'label_priority' in elem:
                priority_map = {'high': 0, 'normal': 1, 'low': 2}
                priorities[elem_id] = priority_map.get(elem['label_priority'], 1)
            else:
                # Automático
                count = connection_count.get(elem_id, 0)
                if count >= 4:
                    priorities[elem_id] = 0  # HIGH
                elif count >= 2:
                    priorities[elem_id] = 1  # NORMAL
                else:
                    priorities[elem_id] = 2  # LOW

        layout.priorities = priorities

    def identify_groups(self, layout):
        """Identifica componentes conectados (DFS)."""
        # Implementación estándar de DFS
        # ...
```

---

### 5. Módulo `layout/laf/`

**Responsabilidad:** Layout jerárquico minimizando cruces (filosofía "abstracto primero, geometría después", inspirado en Sugiyama/Graphviz).

**Coordinador:** `layout/laf/optimizer.py:LAFOptimizer` — hereda de `LayoutOptimizer`.

**Módulos principales** (cada uno cubre fases específicas del pipeline):
- `structure_analyzer.py` — Fase 1 (árbol, grafo, niveles, scores, NdPr, TOI Virtual Containers).
- `optimizer.py::_apply_dashboard_reflow()` — Fase 1.5 (detecta y redistribuye clusters de dashboard en grid 2D, fix BUGS-LAF-002).
- `abstract_placer.py` — Fase 4 (placement abstracto, Sugiyama barycenter).
- `position_optimizer.py` — Fase 5 (layer-offset bisection).
- `inflator.py` — Fase 8 (abstract → coordenadas reales).
- `container_grower.py` — Fase 8 (crecimiento bottom-up, label-aware) + `calculate_final_canvas()` con márgenes separados H/V (BUGS-LAYOUT-002).
- `visualizer.py` — SVGs de debug del proceso (sólo con `--visualize-growth`).
- `routing_policy.py` — `LAFRoutingPolicy` (Fase 10).
- `laf_renderer.py` — `LAFSVGRenderer` (Fase 11): dibuja containers + iconos separados + NdFn metadata (WISH-ARCH-002).

**Resultado:** -87% cruces, -24% colisiones vs AUTO (medido en suite de regresión).

**Issues activos al 2026-06-18**: `BUGS-LAF-001` (distribución asimétrica horizontal, cosmético). Histórico de issues resueltos: BUGS-LAF-002, BUGS-LAYOUT-002, BUGS-LAYOUT-003, WISH-ARCH-001/002.

📍 Referencia detallada: `modules/layout/laf/LAF.md`.

---

### 6. Módulo `layout/templates/` — NUEVO 2026-06-19..23 (WISH-LAYOUT-004)

**Responsabilidad:** Detección semántica del patrón estructural del grafo y asignación de coordenadas según ese patrón. Es el **norte estratégico** del proyecto: el sistema infiere la mejor distribución a partir de la estructura (no requiere que el usuario la declare).

#### Pipeline interno

```
SDJF (sin coords)
   │
   v
GraphFeatures.extract(elements, connections)
   ├─ n_root_elements, n_containers, n_contained
   ├─ n_root_nodes_no_incoming / n_leaf_nodes_no_outgoing
   ├─ max_degree, avg_degree, max_degree_ratio
   ├─ has_cycles, n_self_loops, topological_depth
   ├─ pct_inter_container_connections, branching_factor
   └─ label_keywords (semantic), declared_roles (`role`)
   │
   v
TemplateClassifier — corre detect_score(features) en cada template
   ├─ threshold = 0.6   (mínimo absoluto para aplicar)
   └─ min_lead  = 0.05  (ventaja sobre el segundo, evita empates ambiguos)
   │
   v
template.apply(data)  → asigna x/y a cada elemento root sin coords
   │                     (respeta coords manuales pre-existentes)
   v
apply_nested_templates(data) → procesa containers bottom-up con sub-template
   │                            (asigna `_inner_width`/`_inner_height` al padre)
   v
offset_nested_children(data) → suma offsets del padre a las coords relativas
```

#### Templates registrados

| Nombre | Patrón estructural | Layout |
|---|---|---|
| `architecture` | Entry vertical → containers en fila → contract central → terminales | T-shape con containers row |
| `flow` | Cadena vertical depth ≥ 4 con branching ~1 | Pipeline vertical |
| `hub_and_spoke` | Un nodo central con grado >> resto (incluye SD-WAN) | Radial / columnas |
| `dashboard` | Containers paralelos sin conexiones inter-container | Grid `⌈√N⌉ × ⌈N/cols⌉` |
| `er` | Grafo plano, sin containers, n_connections ≥ 3, keywords entity/table/database | Layout ER |
| `sequence` | Actores horizontales + flujo temporal | Swimlanes |
| `state` | Ciclos + self-loops, role `state` | Circular |

Calibración hecha contra los 23 canonicals (cortocircuito ER `n_connections < 3` y penalty `-0.45` por containers; bonus `+0.55` por keywords).

#### Semantic hints — `role` field

El SDJF puede declarar el rol semántico de un elemento (`role: entry|output|terminal|shared|hub|spoke|abstract|state|actor`). Cada template lo respeta como override declarativo sobre la inferencia. Ej.: en `architecture`, un elemento con `role: shared` se centra entre los containers contract aunque no calce con el patrón inferido.

#### Templates anidados

Los sub-templates SIEMPRE corren (incluso si el padre no aplica): un container puede declarar su propio `layout_template` que aplica solo a sus hijos directos. Procesamiento bottom-up; conflict policy: "hijo siempre infla, padre adapta".

#### Llamadas públicas (`AlmaGag/layout/templates/__init__.py`)

- `auto_apply_template(data) → (name_or_None, all_scores)` — clasifica + aplica si pasa threshold + nested.
- `apply_template(name, data) → bool` — override manual por nombre + nested.
- `apply_sub_templates(data) → list` — solo nested (corre siempre).
- `get_default_classifier() → TemplateClassifier` — instancia configurada con los 7 templates.

📍 Detalle de cada template: ver `AlmaGag/layout/templates/*.py` (`architecture.py`, `flow.py`, ...). Cada uno expone `name`, `detect_score(features) → [0,1]` y `apply(data)`.

---

### 7. Módulo `draw/` (reorganizado por WISH-ARCH-003 2026-06-19)

**Responsabilidad:** Primitivas de dibujo SVG **agnósticas del algoritmo**.

Tras WISH-ARCH-002 (2026-06-18), la orquestación específica de cada algoritmo vive en su propio renderer (`layout/auto/auto_renderer.py`, `layout/laf/laf_renderer.py`). El módulo `draw/` queda como librería pura, separada por subdominio:

- **`draw/primitives/`** — utilities SVG agnósticas: `svg.py` (canvas, markers, ndfn_wrap, draw_connections), `connections.py` (líneas + self-loops + colored connections), `container.py` (container rect + label-aware bounds), `callout.py` (auto-callout WISH-LAYOUT-003 para labels grandes).
- **`draw/icons/`** — un archivo por tipo de icono + dispatcher: `__init__.py` (dispatcher dinámico vía `importlib`), `server.py`, `cloud.py`, `firewall.py`, `building.py`, `router.py`, `computer.py`, `laptop.py`, `database.py`, `document.py`, `user.py`, `bwt.py` (fallback Banana With Tape).

#### `draw/primitives/svg.py`

Primitivas SVG compartidas entre los renderers, sin conocimiento de algoritmo:

- `create_canvas(output_path, width, height)` — crea el `Drawing` con filtro `text-glow` global.
- `setup_arrow_markers(dwg, connections, color_connections)` — markers de flechas (arrow-end/start, circle-end/start) + estilos per-connection si está activo `--color-connections`.
- `ndfn_wrap(dwg, elem_id, ndfn_labels)` — envuelve el dibujo de un elemento en un `<g>` con `<desc>` NdFn cuando hay metadata.
- `draw_connections(dwg, connections, ...)` — dibuja líneas/curvas con markers.
- `draw_connection_labels(dwg, connections, conn_centers, optimized_positions)` — labels de conexiones con posición optimizada.
- `DrawingGroupProxy` — proxy que difiere el `add()` al drawing real hasta tener el wrapping completo.

#### `draw/icons/__init__.py`

**Dispatcher de íconos + sistema de gradientes + blur glow**

```python
def create_gradient(dwg, element_id, base_color):
    """Crea gradiente lineal (claro → oscuro)."""
    gradient_id = f'gradient-{element_id}'
    light_color = adjust_lightness(base_color, 1.3)
    dark_color = adjust_lightness(base_color, 0.7)

    gradient = dwg.linearGradient(id=gradient_id, x1="0%", y1="0%", x2="0%", y2="100%")
    gradient.add_stop_color(offset="0%", color=light_color)
    gradient.add_stop_color(offset="100%", color=dark_color)
    dwg.defs.add(gradient)

    return f'url(#{gradient_id})'

def draw_icon_shape(dwg, element):
    """Dispatcher dinámico de íconos."""
    x, y = element.get('x'), element.get('y')
    if x is None or y is None:
        return  # Sin coords, skip (v2.0)

    elem_type = element.get('type', 'unknown')
    color = element.get('color', 'gray')
    element_id = element.get('id', f'{elem_type}_{x}_{y}')

    try:
        module = importlib.import_module(f'AlmaGag.draw.icons.{elem_type}')
        draw_func = getattr(module, f'draw_{elem_type}')
        draw_func(dwg, x, y, color, element_id)
    except Exception as e:
        # Fallback: Banana With Tape
        from AlmaGag.draw.icons.bwt import draw_bwt
        draw_bwt(dwg, x, y)

def draw_icon_label(dwg, element, label_pos):
    """Dibuja label del ícono (separado de shape)."""
    # ...
```

**Módulos de íconos específicos** (todos en `draw/icons/`):
- `server.py`, `cloud.py`, `firewall.py`, `building.py` — formas base con gradiente
- `router.py`, `computer.py`, `laptop.py`, `database.py`, `document.py`, `user.py` — iconos específicos por tipo
- `bwt.py` - Plátano con cinta (fallback cuando el `type` no tiene módulo registrado)

#### `draw/primitives/connections.py`

**Renderizado de conexiones**

```python
def draw_connection_line(dwg, elements_by_id, connection, markers):
    """Dibuja línea de conexión (recta o con waypoints)."""
    from_elem = elements_by_id.get(connection['from'])
    to_elem = elements_by_id.get(connection['to'])

    # Validar coordenadas (v2.0)
    if not from_elem or not to_elem:
        return None
    if from_elem.get('x') is None or to_elem.get('x') is None:
        return None

    # Waypoints (v1.5)
    waypoints = connection.get('waypoints', [])

    if waypoints:
        # Polyline con puntos intermedios
        points = []
        # ... calcular offsets ...
        polyline = dwg.polyline(points, stroke='black', fill='none')
        dwg.add(polyline)
    else:
        # Línea recta
        line = dwg.line(start=(from_x, from_y), end=(to_x, to_y),
                        stroke='black', fill='none')
        dwg.add(line)

    # Aplicar markers (flechas)
    direction = connection.get('direction', 'none')
    if direction == 'forward':
        line['marker-end'] = markers['arrow-end']
    elif direction == 'backward':
        line['marker-start'] = markers['arrow-start']
    elif direction == 'bidirectional':
        line['marker-start'] = markers['arrow-start']
        line['marker-end'] = markers['arrow-end']

    return line

def draw_connection_label(dwg, elements_by_id, connection):
    """Dibuja label en el centro de la conexión."""
    # ...
```

#### `draw/primitives/container.py`

**Renderizado de contenedores**

```python
def draw_container(dwg, container, elements_by_id):
    """Dibuja rectángulo redondeado alrededor de elementos."""
    # Calcular bounds dinámicamente
    bounds = calculate_container_bounds(container, elements_by_id)

    # Dibujar rectángulo con gradiente
    gradient_id = create_gradient(dwg, container['id'], container.get('color', 'lightgray'))
    rect = dwg.rect(
        insert=(bounds['x'], bounds['y']),
        size=(bounds['width'], bounds['height']),
        rx=radius, ry=radius,
        fill=gradient_id,
        opacity=0.3
    )
    dwg.add(rect)

    # Dibujar ícono en esquina
    # ...

    # Dibujar label
    # ...

def calculate_container_bounds(container, elements_by_id):
    """Calcula bounding box de elementos contenidos."""
    contained_ids = container['contains']
    contained = [elements_by_id[id] for id in contained_ids if id in elements_by_id]

    # Calcular min/max de x, y
    # ...

    # Aplicar padding y aspect_ratio
    # ...
```

---

### 8. Módulo `routing/`

**Responsabilidad:** Cálculo de paths para conexiones. Compartido por ambos algoritmos.

```
routing/
├── router_base.py            # Interfaz BaseRouter
├── router_manager.py         # ConnectionRouterManager (despacho por tipo)
├── straight_router.py        # Línea recta (default)
├── orthogonal_router.py      # Manhattan / 90°
├── bezier_router.py          # Curvas suaves
├── arc_router.py             # Arcos
├── manual_router.py          # Waypoints explícitos en SDJF
├── port_assignment.py        # Selección de puntos de anclaje al icono
└── visibility_graph.py       # Pathfinding evadiendo obstáculos
```

Cada conexión puede declarar su routing en el SDJF: `"routing": {"type": "orthogonal|bezier|arc|straight|manual"}`. Sin declaración, cada algoritmo elige según su `RoutingPolicy` (`AutoRoutingPolicy` en `layout/auto/routing_policy.py`, `LAFRoutingPolicy` en `layout/laf/routing_policy.py`).

📍 Detalle: `modules/routing/ROUTING.md`.

---

### 9. Módulo `validation/` — NUEVO 2026-06-23

**Responsabilidad:** Audit automático de calidad visual sobre SVGs renderizados. Cubre las 3 reglas explícitas del usuario:

| Regla | Descripción | Tolerancia |
|---|---|---|
| **R1** `label_over_icon` | Las etiquetas NO deben caer encima de iconos. | área de overlap > 80 px² |
| **R2** `labels_overlap` | Las etiquetas NO deben solaparse entre sí. | área de overlap > 50 px² |
| **R3** `dangling_connection` | Los conectores NO deben terminar en el aire (sin endpoint cercano a icono). | distancia endpoint→icono > 20 px |

#### API pública (`AlmaGag/validation/__init__.py`)

```python
from AlmaGag.validation import validate_svg, validate_gag, QualityReport

# Modo 1: parsear un SVG ya renderizado.
report = validate_svg('output.svg')               # auto-detecta iconos
report = validate_svg('output.svg', icon_bboxes=[(x1,y1,x2,y2), ...])  # explícito

# Modo 2: validar un .gag corriendo el optimizer (usa posiciones reales).
report = validate_gag('diagrama.gag', layout_algorithm='auto')

# Inspección del reporte.
report.passed        # bool — ¿pasó las 3 reglas?
report.n_icons, report.n_labels, report.n_connections
report.by_rule('R1_label_over_icon')   # filter de Violations
```

#### Heurísticas para reducir falsos positivos en R3

R3 es la regla con más ruido (decoración interna de iconos puede parecer conector). Filtros aplicados:
- Solo cuenta como conexión líneas con stroke `'black'` o `'gray'` (descarta colores HEX decorativos).
- Líneas sin marker (arrow-end/start/mid) Y longitud < 50px se ignoran (decoración interna).
- Para `.gag` con iconos SVG custom embebidos, `validate_gag()` usa las posiciones reales del optimizer en vez de parsear bboxes del SVG (que no detecta iconos custom).

#### Uso esperado

- **Audit periódico** del set canonical de SVGs (regresión visual).
- **Test de aceptación** de nuevos templates (cada template debe producir SVGs con `report.passed == True`).
- **Tests unitarios** del validador en `tests/test_visual_quality.py`.

---

## Patrones de Diseño Utilizados

### 1. Inmutabilidad (Layout)

```python
# NO modifica el layout original
optimized = optimizer.optimize(initial_layout)

# Layout.copy() crea deep copies independientes
candidate = best_layout.copy()
```

**Beneficios:**
- Facilita debugging (comparar estados)
- Thread-safe (futuro)
- Optimización transparente

### 2. Strategy Pattern (LayoutOptimizer)

```python
class LayoutOptimizer(ABC):
    @abstractmethod
    def optimize(self, layout, max_iterations):
        pass

class AutoLayoutOptimizer(LayoutOptimizer):
    # Implementación específica
```

**Beneficios:**
- Fácil agregar nuevos algoritmos
- Intercambiable en runtime
- Testeable independientemente

### 3. Dependency Injection

```python
class AutoLayoutOptimizer:
    def __init__(self):
        self.sizing = SizingCalculator()
        self.geometry = GeometryCalculator(self.sizing)  # DI
        self.collision_detector = CollisionDetector(self.geometry)  # DI
```

**Beneficios:**
- Componentes desacoplados
- Fácil de testear con mocks
- Flexible para modificaciones

### 4. Dynamic Import (Íconos)

```python
module = importlib.import_module(f'AlmaGag.draw.{elem_type}')
draw_func = getattr(module, f'draw_{elem_type}')
```

**Beneficios:**
- Fácil agregar nuevos tipos
- No requiere registry centralizado
- Fallback transparente

### 5. Pipeline (Generator)

```
Parse → Layout → Optimize → Create Canvas → Render → Save
```

**Beneficios:**
- Flujo claro y linear
- Fácil insertar pasos intermedios
- Cada paso tiene responsabilidad única

### 6. Factory Pattern (Selección de Optimizer) — NUEVO 2026-06-18

```python
# AlmaGag/generator.py
OPTIMIZERS = {
    'auto': AutoLayoutOptimizer,
    'laf':  LAFOptimizer,
}

optimizer_cls = OPTIMIZERS[layout_algorithm]
optimizer = optimizer_cls(verbose=debug, visualdebug=visualdebug, ...)
```

**Beneficios:**
- Selección por CLI sin `if/elif` ni acoplamiento al nombre del algoritmo.
- Agregar un tercer algoritmo: implementar `LayoutOptimizer` + renderer, añadir entrada al dict.
- Cumple el contrato `LayoutOptimizer` (Strategy Pattern) en la práctica, no solo en intención.

### 7. Self-contained Construction — NUEVO 2026-06-18

Cada optimizer construye sus propios colaboradores dentro de `__init__`:

```python
class LAFOptimizer(LayoutOptimizer):
    def __init__(self, verbose=False, visualdebug=False, ..., **legacy_kwargs):
        super().__init__(verbose=verbose)
        # Construcción interna de defaults estándar.
        self.sizing = SizingCalculator()
        self.geometry = GeometryCalculator(self.sizing)
        # ...
        # Cada optimizer tiene su propio renderer.
        self.renderer = LAFSVGRenderer(self.geometry)
        # Inyección opcional para legacy/tests (kwargs).
```

**Beneficios:**
- `generator.py` queda agnóstico de las dependencias internas del algoritmo.
- Cambiar las dependencias por defecto de un algoritmo no propaga a otros sitios.
- Mantiene inyección opcional vía kwargs para retrocompatibilidad con tests.

---

## Estructura de Directorios (2026-06-23)

```
AlmaGag/
├── main.py                          # CLI entry point (argparse + dispatch)
├── generator.py                     # Orquestador delgado (190 líneas)
│                                    #   con template detection + factoría
├── config.py                        # Constantes globales
├── debug.py                         # Helpers de debug: badge, grid, guide_lines
│
├── draw/                            # Primitivas de dibujo SVG (algoritmo-agnósticas)
│   ├── primitives/                  # WISH-ARCH-003 (2026-06-19): subdominio
│   │   ├── svg.py                   #   create_canvas, markers, ndfn_wrap, draw_connections
│   │   ├── connections.py           #   Líneas + self-loops + colored connections
│   │   ├── container.py             #   Container rect + label-aware bounds
│   │   └── callout.py               #   WISH-LAYOUT-003: auto-callout para labels grandes
│   └── icons/                       # WISH-ARCH-003: 1 archivo por tipo + dispatcher
│       ├── __init__.py              #   Dispatcher dinámico (importlib)
│       ├── server.py, cloud.py, firewall.py, building.py
│       ├── router.py, computer.py, laptop.py
│       ├── database.py, document.py, user.py
│       └── bwt.py                   #   Banana With Tape (fallback)
│
├── layout/                          # Módulo de Layout y Optimización
│   ├── layout.py                    # Layout (Value Object inmutable)
│   ├── optimizer_base.py            # LayoutOptimizer (contrato base)
│   ├── sizing.py                    # SizingCalculator (hp/wp)
│   ├── geometry.py                  # GeometryCalculator
│   ├── collision.py                 # CollisionDetector
│   ├── graph_analysis.py            # GraphAnalyzer
│   ├── label_optimizer.py           # LabelPositionOptimizer
│   ├── container_calculator.py      # ContainerCalculator
│   ├── templates/                   # NUEVO (WISH-LAYOUT-004): inferencia semántica
│   │   ├── __init__.py              #   auto_apply_template, apply_template
│   │   ├── base.py                  #   BaseTemplate + TemplateClassifier
│   │   ├── features.py              #   GraphFeatures.extract(elements, conns)
│   │   ├── architecture.py          #   Patrón architecture (T)
│   │   ├── flow.py                  #   Pipeline vertical
│   │   ├── hub_and_spoke.py         #   Hub central + spokes
│   │   ├── dashboard.py             #   Grid de containers paralelos
│   │   ├── er.py                    #   Entity-Relationship
│   │   ├── sequence.py              #   Swimlanes temporales
│   │   ├── state.py                 #   State machine circular
│   │   └── nested.py                #   Sub-templates en containers
│   ├── auto/                        # Algoritmo AUTO
│   │   ├── optimizer.py             #   AutoLayoutOptimizer (1171 líneas)
│   │   │                            #   con post-passes BUGS-AUTO-001..007
│   │   ├── positioner.py            #   AutoLayoutPositioner (Fase 0)
│   │   ├── routing_policy.py        #   AutoRoutingPolicy
│   │   └── auto_renderer.py         #   AutoSVGRenderer (Fase 5 equiv.)
│   └── laf/                         # Algoritmo LAF
│       ├── optimizer.py             #   LAFOptimizer (2091 líneas)
│       │                            #   con _apply_dashboard_reflow (Fase 1.5)
│       ├── structure_analyzer.py    #   Fase 1
│       ├── abstract_placer.py       #   Fase 4
│       ├── position_optimizer.py    #   Fase 5
│       ├── inflator.py              #   Fase 8 (inflación)
│       ├── container_grower.py      #   Fase 8 (crecimiento)
│       ├── visualizer/              #   WISH-ARCH-003: 1 archivo por fase
│       │   ├── phase1.py, phase2_topology.py, phase3_centrality.py
│       │   ├── phase4_abstract.py, phase5_optimized.py
│       │   ├── phase7_iterative.py, phase8_inflated.py
│       │   ├── phase9_redistributed.py, phase10_routed.py
│       │   └── phase11_final.py
│       ├── routing_policy.py        #   LAFRoutingPolicy (Fase 10)
│       └── laf_renderer.py          #   LAFSVGRenderer (Fase 11)
│
├── routing/                         # Cálculo de paths (compartido)
│   ├── router_base.py               # Interfaz BaseRouter
│   ├── router_manager.py            # ConnectionRouterManager
│   ├── straight_router.py           # Línea recta (default)
│   ├── orthogonal_router.py         # Manhattan / 90°
│   ├── bezier_router.py             # Curvas suaves
│   ├── arc_router.py                # Arcos
│   ├── manual_router.py             # Waypoints explícitos en SDJF
│   ├── port_assignment.py           # Selección de anclajes al icono
│   └── visibility_graph.py          # Pathfinding evadiendo obstáculos
│
├── validation/                      # NUEVO (2026-06-23): audit de calidad visual
│   ├── __init__.py                  # validate_svg, validate_gag, QualityReport
│   └── visual_quality.py            # 3 reglas R1/R2/R3
│
└── iteration_debug/                 # Dump CSV de evolución por iteración

docs/
├── architecture/                    # ARCHITECTURE.md + EVOLUTION.md + modules/
├── guides/                          # CLI-REFERENCE, QUICKSTART, LAYOUT-DECISION
├── spec/                            # Especificaciones SDJF
├── diagrams/                        # .gag/.sdjf + .svg + benchmark/ (mermaid)
├── TECHNICAL_DEBT.md                # BUGS-* + WISH-* + métricas
└── DIAGRAM_REVIEW.md                # BUGS-DIAG-* visuales

tests/                               # 70 tests passed al 2026-06-23

.github/workflows/ci.yml             # Tests + render smoke + determinism guard
```

**Cambios estructurales en el último ciclo** (2026-06-19..23):
- `AlmaGag/layout/templates/` **creado** — 7 templates + classifier + nested (WISH-LAYOUT-004 Fases 1-4).
- `AlmaGag/validation/` **creado** — validador de las 3 reglas de calidad visual.
- `AlmaGag/draw/svg.py` → `AlmaGag/draw/primitives/svg.py` (WISH-ARCH-003).
- `AlmaGag/draw/{icons.py, server.py, cloud.py, …}` → `AlmaGag/draw/icons/{__init__.py, server.py, cloud.py, …}` (WISH-ARCH-003).
- `AlmaGag/draw/primitives/callout.py` **creado** (WISH-LAYOUT-003).
- `AlmaGag/layout/laf/visualizer.py` (2876 líneas, monolítico) **eliminado**; split en `laf/visualizer/` con 11 archivos (uno por fase).
- `AlmaGag/generator.py`: 187 → 190 líneas (añadido step de template detection).
- Tests: 17 + 2 skipped → 70 passed.

---

## Extensibilidad

### Agregar Nuevo Tipo de Ícono

1. Crear `draw/mi_icono.py`:
```python
from AlmaGag.config import ICON_WIDTH, ICON_HEIGHT
from AlmaGag.draw.icons import create_gradient

def draw_mi_icono(dwg, x, y, color, element_id):
    fill = create_gradient(dwg, element_id, color)
    # Dibujar usando SVG primitives
    dwg.add(dwg.circle(center=(x + ICON_WIDTH/2, y + ICON_HEIGHT/2),
                       r=25, fill=fill, stroke='black'))
```

2. Usar en SDJF:
```json
{
  "id": "elem1",
  "type": "mi_icono",
  "x": 100,
  "y": 200
}
```

**No requiere modificar código existente** (dynamic import).

### Agregar Nuevo Template (WISH-LAYOUT-004)

1. Crear `layout/templates/mi_template.py`:

```python
from AlmaGag.layout.templates.base import BaseTemplate
from AlmaGag.layout.templates.features import GraphFeatures


class MiTemplate(BaseTemplate):
    name = 'mi_template'

    def detect_score(self, features: GraphFeatures) -> float:
        # Heurísticas basadas en features estructurales del grafo.
        # Devuelve [0, 1] — qué tan probable es que este grafo
        # encaje en este patrón.
        score = 0.0
        if features.n_containers >= 3:
            score += 0.5
        if features.max_degree_ratio > 0.4:
            score += 0.3
        if 'mi_keyword' in features.label_keywords:
            score += 0.2
        return min(score, 1.0)

    def apply(self, data: dict) -> None:
        # Asigna x, y a cada elemento root sin coords.
        # Respeta coords manuales pre-existentes.
        # ...
```

2. Registrarlo en `layout/templates/__init__.py`:

```python
def get_default_classifier() -> TemplateClassifier:
    return TemplateClassifier([
        ArchitectureTemplate(),
        # ...
        MiTemplate(),  # ← una línea
    ])
```

3. Usarlo en SDJF:

```json
{
  "layout_template": "mi_template",
  "elements": [...]
}
```

O dejar que la auto-detección lo descubra: `"layout_template": "auto"` corre `classify()` y elige el de mayor score si supera el threshold (0.6) con ventaja sobre el segundo (≥0.05).

4. (Opcional) Agregar tests en `tests/test_template_*.py` con grafos sintéticos donde tu template gane.

**Calibración**: tras agregar un template, regenerar los 23 canonicals con `python smoke_test.py` y verificar que no haya regresiones (templates existentes manteniendo sus selecciones, sin falsos positivos del nuevo).

---

### Agregar Nuevo Optimizador

1. Crear paquete `layout/mi_algoritmo/`:

```python
# layout/mi_algoritmo/optimizer.py
from AlmaGag.layout.optimizer_base import LayoutOptimizer
from AlmaGag.layout.mi_algoritmo.mi_renderer import MiSVGRenderer

class MiOptimizer(LayoutOptimizer):
    def __init__(self, verbose=False, visualdebug=False, **kwargs):
        super().__init__(verbose=verbose)
        # Construir colaboradores internamente (self-contained).
        self.sizing = SizingCalculator()
        self.geometry = GeometryCalculator(self.sizing)
        # ...
        self.renderer = MiSVGRenderer(self.geometry)

    def optimize(self, layout, max_iterations=10, dump_iterations=False, input_file=None):
        # Implementación personalizada — ignorar kwargs que no aplican.
        # ... algoritmo ...
        return layout
```

```python
# layout/mi_algoritmo/mi_renderer.py
class MiSVGRenderer:
    def __init__(self, geometry_calculator):
        self.geometry = geometry_calculator

    def render(self, layout, output_svg, *, visualdebug=False, debug=False, ...):
        # Usar primitivas de draw/svg.py (agnósticas)
        # y dibujar el SVG completo.
```

2. Registrarlo en `generator.py`:

```python
from AlmaGag.layout.mi_algoritmo.optimizer import MiOptimizer

OPTIMIZERS = {
    'auto':         AutoLayoutOptimizer,
    'laf':          LAFOptimizer,
    'mi_algoritmo': MiOptimizer,  # ← una línea
}
```

3. Agregarlo a las choices del CLI en `main.py`:

```python
parser.add_argument(
    "--layout-algorithm",
    choices=['auto', 'laf', 'mi_algoritmo'],
    default='auto',
)
```

**No requiere tocar el código de los otros algoritmos** — el principio "un algoritmo no sabe que los otros existen" se cumple desde WISH-ARCH-002.

---

## Performance

### Complejidad Temporal

| Operación | Complejidad | Notas |
|-----------|-------------|-------|
| Parse JSON | O(n) | n = elementos + conexiones |
| Auto-positioning | O(n log n) | Sorting por centrality |
| Collision detection | O(n²) | All-pairs comparison |
| Optimization (1 iter) | O(n²) | Colisiones + movimiento |
| SVG rendering | O(n) | Linear por cada elemento |

**Total:** O(k × n²) donde k = max_iterations

### Optimizaciones Implementadas

1. **Early exit**: Si 0 colisiones, termina iteraciones
2. **Bbox caching**: Bboxes calculados una vez por iteración
3. **Priority queues**: Elementos ordenados por score
4. **Lazy evaluation**: Solo calcula lo necesario

### Escalabilidad

- **Pequeño** (<20 elementos): Instantáneo (<0.1s)
- **Mediano** (20-100 elementos): Rápido (<1s)
- **Grande** (100-500 elementos): Aceptable (1-5s)
- **Muy grande** (>500 elementos): Puede requerir optimización

**Recomendación:** Para diagramas >500 elementos, considerar spatial hashing o quadtrees.

---

## Testing

### Estrategia de Testing

1. **Unit tests**: Cada componente independiente
   - `GeometryCalculator.rectangles_intersect()`
   - `SizingCalculator.get_element_weight()`
   - `GraphAnalyzer.calculate_priorities()`

2. **Integration tests**: Flujo completo
   - Parse SDJF → Optimize → Render
   - Verificar SVG generado válido

3. **Visual regression tests**: Comparar SVGs
   - Regenerar ejemplos después de cambios
   - Diff visual con herramientas como Playwright

### Archivos de Test Actuales (2026-06-23)

#### Tests unitarios (`tests/`)

```
tests/
├── test_architecture_template.py       # 8 tests — WISH-LAYOUT-004 Fase 1
├── test_template_classifier.py         # 16 tests — WISH-LAYOUT-004 Fase 2
├── test_template_fase3.py              # 11 tests — WISH-LAYOUT-004 Fase 3
├── test_template_fase4.py              # 10 tests — WISH-LAYOUT-004 Fase 4
├── test_visual_quality.py              # 6 tests — validator R1/R2/R3
├── test_pipeline_consistency.py        # Pipeline AUTO/LAF idempotente
├── test_position_optimizer_normalization.py
├── test_terminal_leaf_nodes.py
└── test_topological_levels.py          # 13 tests — niveles topológicos LAF
```

**Total: 70 tests passed** (al 2026-06-23).

#### Canonicals visuales (`docs/diagrams/gags/`)

23 archivos `.gag` que se renderizan en CI como smoke test. Cubren todos los tipos de iconos, container nesting, waypoints, hp/wp, custom icons, y los 7 templates de layout. La regeneración masiva con `python smoke_test.py` confirma que no hay regresiones.

**Validación visual adicional**: usar `AlmaGag.validation.validate_svg(path)` para chequear las 3 reglas R1/R2/R3 sobre cada SVG generado.

---

## Dependencias

```
svgwrite>=1.4.3     # Generación de SVG
```

**Filosofía:** Dependencias mínimas, código autónomo.

---

**Última actualización**: 2026-06-23
**Versión documentada**: AlmaGag v3.5 + SDJF v2.1 | 3 capas (Templates → Algoritmo → Validation) | LAF Pipeline 11 fases (12 con 1.5 dashboard reflow) | 7 templates de auto-distribución
