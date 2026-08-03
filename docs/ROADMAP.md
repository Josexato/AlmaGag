# AlmaGag - Roadmap de Desarrollo

> **⚠️ DESACTUALIZADO (pre-reorg `strategies/`, ≤jun-2026).** El pipeline
> real es: `generator.py` (expand_unions §H7 → semantics §Q63 → theme §O57 →
> `select_strategy` → templates) → `LayoutEngine` (`auto`/`hier`/`legacy`) →
> banding §P60 → anticolisión §P61 → re-ruteo → métricas §O52. Ver el código
> y `docs/reviews/auditoria-2026-08-02/` (BUGS-DOCS-002/003/004); este
> documento se conserva por su valor histórico hasta su reescritura.


**Versión Actual**: v3.5.0 (ver banner: el cuerpo del roadmap está congelado en feb-2026)
**Actualizado**: 2026-02-27

---

## Estado Actual

### ✅ Completado

#### SDJF v1.0 (Junio 2025)
- ✅ Formato JSON declarativo
- ✅ Elementos con coordenadas explícitas
- ✅ Conexiones con flechas direccionales
- ✅ 4 tipos de íconos (server, building, cloud, firewall)
- ✅ Gradientes automáticos
- ✅ Fallback BWT (Banana With Tape)

#### SDJF v1.5 (Diciembre 2025)
- ✅ Waypoints manuales para routing complejo
- ✅ Contenedores (agrupación visual)

#### SDJF v2.0 (Enero 2026)
- ✅ **Coordenadas opcionales** (auto-layout híbrido)
- ✅ **Sizing proporcional** (hp/wp)
- ✅ Prioridades inteligentes (HIGH/NORMAL/LOW)
- ✅ Weight-based optimization
- ✅ Compatibilidad 100% hacia atrás

#### Código v2.1 (Enero 2026)
- ✅ Refactorización modular (layout/ separado de draw/)
- ✅ Patrón inmutable (Layout.copy())
- ✅ Componentes auxiliares (SizingCalculator, AutoLayoutPositioner)
- ✅ Documentación reorganizada (spec/, guides/, architecture/)

#### Código v3.0 (Enero 2026)
- ✅ Layout jerárquico topológico (longest-path levels)
- ✅ Label collision optimizer
- ✅ Sistema LAF con 8 fases (Sugiyama-style)
- ✅ Routing declarativo (5 tipos: straight, orthogonal, bezier, arc, manual)

#### Código v3.1 (Febrero 2026)
- ✅ **Auto Layout v4.0**: Barycenter ordering + position optimization + connection resolution
- ✅ **LAF v1.4**: Pipeline de 10 fases con position optimization y escala X global
- ✅ Centrality scores para centrar nodos conectados
- ✅ Fix de convergencia del optimizador y elementos apilados
- ✅ Limpieza de ~350 líneas de código muerto

#### Código v3.3 (Febrero 2026)
- ✅ **NdPr (Nodo Primario)**: Grafo abstracto para Fases 3-5
- ✅ **TOI Virtual Containers**: Detección automática de patrones TOI
- ✅ **Fase 6**: Expansión de NdPr a elementos individuales
- ✅ 0 colisiones en stresstest (27 elementos, 5 VCs)
- ✅ Retrocompatible con diagramas sin VCs

---

## ✅ Lanzamiento Actual: SDJF v2.1

**Estado**: ✅ Implementado
**Objetivo**: Waypoints automáticos y tipos de líneas declarativos
**Completado**: 2026-01-08

### Motivación

**Problema Actual:**
- Waypoints v1.5 tienen coordenadas fijas (no adaptativo)
- Incompatible con auto-layout (elementos se mueven, waypoints quedan mal)
- Sin semántica clara ("quiero ortogonal" = calcular puntos manualmente)

**Solución:**
```json
{
  "from": "A",
  "to": "B",
  "routing": {
    "type": "orthogonal",
    "avoid_elements": true,
    "corner_radius": 10
  }
}
```

### Features Principales

| Feature | Prioridad | Complejidad | Impacto |
|---------|-----------|-------------|---------|
| Routing declarativo | Alta | Baja | Alto |
| `straight` router | Alta | Muy Baja | Medio |
| `orthogonal` router | **Alta** | **Media** | **Muy Alto** |
| `bezier` router | Media | Media | Alto |
| `arc` router | Media | Baja | Medio |
| `avoid_elements` | Media | Alta | Alto |
| `corner_radius` | Baja | Baja | Medio |

### Plan de Implementación

Ver [Estrategias de Implementación](docs/architecture/IMPLEMENTATION_STRATEGY.md) para detalles técnicos.

#### Fase 1: Infraestructura (2-3 días)
**Objetivo**: Framework de routing extensible

```python
# AlmaGag/routing/router_base.py
class ConnectionRouter(ABC):
    @abstractmethod
    def calculate_path(self, from_elem, to_elem, connection, layout) -> Path:
        pass

# AlmaGag/routing/straight_router.py
class StraightRouter(ConnectionRouter):
    def calculate_path(self, from_elem, to_elem, connection, layout):
        # Línea recta (refactor código existente)
        return Path(type='line', points=[start, end])
```

**Entregables:**
- [x] Módulo `routing/` con estructura base
- [x] Clase abstracta `ConnectionRouter`
- [x] `StraightRouter` (refactor existing code)
- [x] Tests unitarios básicos

**Estado**: ✅ Completado
**Riesgo**: Bajo (refactor conservador)

---

#### Fase 2: Orthogonal Router Básico (3-5 días)
**Objetivo**: Routing ortogonal sin collision avoidance

**Algoritmo Simplificado:**
```python
def calculate_orthogonal_path(from_elem, to_elem, preference='auto'):
    """
    Genera path ortogonal H-V o V-H.

    Estrategia:
    1. Calcular centros de from/to
    2. Determinar orientación:
       - Si |dx| > |dy| → horizontal primero
       - Si |dy| > |dx| → vertical primero
    3. Generar 1-2 waypoints intermedios
    4. Retornar polyline
    """
    from_center = get_center(from_elem)
    to_center = get_center(to_elem)

    dx = to_center.x - from_center.x
    dy = to_center.y - from_center.y

    if preference == 'auto':
        preference = 'horizontal' if abs(dx) > abs(dy) else 'vertical'

    if preference == 'horizontal':
        # H-V: salir horizontal, luego vertical
        mid_x = from_center.x + dx / 2
        waypoints = [
            from_center,
            Point(mid_x, from_center.y),
            Point(mid_x, to_center.y),
            to_center
        ]
    else:
        # V-H: salir vertical, luego horizontal
        mid_y = from_center.y + dy / 2
        waypoints = [
            from_center,
            Point(from_center.x, mid_y),
            Point(to_center.x, mid_y),
            to_center
        ]

    return Path(type='polyline', points=waypoints)
```

**Entregables:**
- [x] `OrthogonalRouter` básico (sin avoid_elements)
- [x] Heurística H-V vs V-H
- [x] Propiedad `preference` (horizontal/vertical/auto)
- [x] Tests con casos típicos

**Estado**: ✅ Completado
**Riesgo**: Bajo (algoritmo simple)

---

#### Fase 3: Bezier y Arc (2-3 días)
**Objetivo**: Estilos adicionales de líneas

**Bezier Router:**
```python
def calculate_bezier_path(from_elem, to_elem, curvature=0.5):
    """
    Genera curva de Bézier cúbica.

    Algoritmo:
    1. Calcular vector from → to
    2. Generar puntos de control perpendiculares
    3. Distancia de control = distance(from, to) * curvature
    """
    from_center = get_center(from_elem)
    to_center = get_center(to_elem)

    # Vector perpendicular
    dx = to_center.x - from_center.x
    dy = to_center.y - from_center.y
    distance = math.sqrt(dx**2 + dy**2)

    # Puntos de control
    control_offset = distance * curvature
    perp_x = -dy / distance
    perp_y = dx / distance

    control1 = Point(
        from_center.x + dx/3 + perp_x * control_offset,
        from_center.y + dy/3 + perp_y * control_offset
    )
    control2 = Point(
        from_center.x + 2*dx/3 + perp_x * control_offset,
        from_center.y + 2*dy/3 + perp_y * control_offset
    )

    return Path(
        type='bezier',
        points=[from_center, to_center],
        control_points=[control1, control2]
    )
```

**Arc Router:**
```python
def calculate_arc_path(from_elem, to_elem, radius=50, side='top'):
    """
    Genera arco circular (útil para self-loops).
    """
    if from_elem['id'] == to_elem['id']:
        # Self-loop
        center = get_center(from_elem)

        if side == 'top':
            start = Point(center.x - 20, center.y)
            end = Point(center.x + 20, center.y)
            arc_center = Point(center.x, center.y - radius)
        # ... otros lados

        return Path(
            type='arc',
            points=[start, end],
            arc_center=arc_center,
            radius=radius
        )
```

**Entregables:**
- [x] `BezierRouter` con propiedad `curvature`
- [x] `ArcRouter` con propiedades `radius`, `side`
- [x] Tests con casos típicos

**Estado**: ✅ Completado
**Riesgo**: Bajo (matemática estándar)

---

#### Fase 4: Corner Radius (1-2 días)
**Objetivo**: Esquinas redondeadas en polylines

**Implementación SVG:**
```python
def apply_corner_radius(polyline_points, radius):
    """
    Convierte polyline sharp corners en curvas suaves.

    Técnica: Insertar comandos arc (A) en path SVG
    """
    if radius <= 0:
        return polyline_points  # Sin cambios

    smooth_path = []
    for i in range(len(polyline_points)):
        if i == 0 or i == len(polyline_points) - 1:
            smooth_path.append(polyline_points[i])
        else:
            # Corner: insertar arco
            prev = polyline_points[i-1]
            curr = polyline_points[i]
            next = polyline_points[i+1]

            # Calcular puntos de tangencia
            # ... (algoritmo de corner rounding)

    return smooth_path
```

**Entregables:**
- [x] Propiedad `corner_radius` en `OrthogonalRouter`
- [x] Implementación de corner smoothing (preparada, rendering pendiente)
- [x] Tests visuales

**Estado**: ✅ Preparado (rendering básico implementado)
**Riesgo**: Bajo (técnica conocida)

---

#### Fase 5: Collision Avoidance (5-7 días) 🔥
**Objetivo**: `avoid_elements=true` funcional

**Complejidad**: Alta
**Algoritmo**: A* o Visibility Graph

**A* Approach:**
```python
def calculate_orthogonal_path_avoiding(from_elem, to_elem, elements, grid_size=20):
    """
    Routing ortogonal evitando elementos usando A*.

    Estrategia:
    1. Crear grid discreto del canvas
    2. Marcar celdas ocupadas por elementos
    3. Ejecutar A* desde from → to
    4. Simplificar path resultante (reducir waypoints)
    """
    # Crear grid
    grid = create_grid(layout.canvas, grid_size)

    # Marcar obstáculos
    for elem in elements:
        bbox = get_bbox(elem)
        mark_occupied(grid, bbox)

    # A* search
    start = world_to_grid(get_center(from_elem))
    goal = world_to_grid(get_center(to_elem))

    path = astar_search(grid, start, goal, heuristic='manhattan')

    # Simplificar (Douglas-Peucker o similar)
    simplified = simplify_path(path, tolerance=grid_size/2)

    # Convertir a coordenadas mundo
    world_path = [grid_to_world(p) for p in simplified]

    return Path(type='polyline', points=world_path)
```

**Alternativa: Visibility Graph**
```python
def calculate_path_visibility_graph(from_elem, to_elem, elements):
    """
    Usa visibility graph para path más óptimo.

    Más eficiente que A* pero más complejo de implementar.
    """
    # Construir grafo de visibilidad
    vertices = extract_obstacle_vertices(elements)
    graph = build_visibility_graph(vertices)

    # Dijkstra desde from → to
    path = dijkstra(graph, from_center, to_center)

    return path
```

**Entregables:**
- [x] Implementación A* básica
- [x] Grid discretization
- [x] Path simplification
- [ ] ~~Propiedad `avoid_elements`~~ NUNCA implementada (cero ocurrencias en el código; el obstacle-avoidance real es incondicional vía visibility graph — BUGS-DOCS-004)
- [x] Tests con casos complejos

**Riesgo**: Alto
- Performance con muchos elementos
- Casos edge (callejones sin salida)
- Tunning de parámetros (grid_size, tolerance)

**Mitigación:**
- Empezar con A* simple
- Optimizar si es necesario (spatial hashing, lazy evaluation)
- Fallback a línea recta si path no encontrado

---

#### Fase 6: Integración con AutoLayoutOptimizer (2 días)
**Objetivo**: Routers ejecutados después de posicionar elementos

**Cambios en `auto/optimizer.py`:**
```python
def optimize(self, layout, max_iterations=10):
    current = layout.copy()

    # FASE 0: Auto-positioning (v2.0)
    self.analyze(current)
    self.positioner.calculate_missing_positions(current)

    # FASE 1: Routing de conexiones (v2.1 NUEVO)
    self.connection_router.calculate_all_paths(current)

    # FASE 2: Análisis completo
    self.analyze(current)
    self._calculate_initial_positions(current)

    # FASE 3: Optimización iterativa
    # ... (existente)

    return best_layout
```

**Nuevo módulo: `ConnectionRouterManager`:**
```python
class ConnectionRouterManager:
    def __init__(self):
        self.routers = {
            'straight': StraightRouter(),
            'orthogonal': OrthogonalRouter(),
            'bezier': BezierRouter(),
            'arc': ArcRouter(),
            'manual': ManualRouter()
        }

    def calculate_all_paths(self, layout):
        """Calcula paths para todas las conexiones."""
        for connection in layout.connections:
            routing = connection.get('routing', {'type': 'straight'})
            router_type = routing['type']

            router = self.routers.get(router_type, self.routers['straight'])

            from_elem = layout.elements_by_id[connection['from']]
            to_elem = layout.elements_by_id[connection['to']]

            path = router.calculate_path(from_elem, to_elem, routing, layout)

            # Guardar en conexión para draw/connections.py
            connection['computed_path'] = path
```

**Entregables:**
- [x] `ConnectionRouterManager`
- [x] Integración en `optimize()`
- [x] Tests end-to-end

**Estado**: ✅ Completado
**Riesgo**: Bajo (arquitectura clara)

---

#### Fase 7: Rendering SVG (2 días)
**Objetivo**: `draw/connections.py` usa `computed_path`

**Cambios:**
```python
def draw_connection_line(dwg, connection):
    """
    Dibuja conexión usando computed_path.

    Antes (v2.0): calculaba inline
    Ahora (v2.1): lee de connection['computed_path']
    """
    path = connection.get('computed_path')

    if not path:
        # Fallback: línea recta simple
        draw_simple_line(dwg, connection)
        return

    if path['type'] == 'line':
        draw_svg_line(dwg, path['points'])
    elif path['type'] == 'polyline':
        draw_svg_polyline(dwg, path['points'], path.get('corner_radius', 0))
    elif path['type'] == 'bezier':
        draw_svg_bezier(dwg, path['points'], path['control_points'])
    elif path['type'] == 'arc':
        draw_svg_arc(dwg, path['points'], path['arc_center'], path['radius'])

    # Aplicar markers (flechas)
    apply_direction_markers(dwg, connection, path)
```

**Entregables:**
- [x] Refactor `draw_connection_line()`
- [x] Soporte para todos los tipos de path
- [x] Corner radius rendering (básico)
- [x] Tests visuales (regenerar ejemplos)

**Estado**: ✅ Completado
**Riesgo**: Bajo (SVG estándar)

---

### Timeline Estimado

| Fase | Duración | Dependencias | Riesgo |
|------|----------|--------------|--------|
| 1. Infraestructura | 2-3 días | Ninguna | Bajo |
| 2. Orthogonal básico | 3-5 días | Fase 1 | Bajo |
| 3. Bezier + Arc | 2-3 días | Fase 1 | Bajo |
| 4. Corner radius | 1-2 días | Fase 2 | Bajo |
| 5. Avoid elements | 5-7 días | Fase 2 | **Alto** |
| 6. Integración | 2 días | Fases 1-5 | Bajo |
| 7. Rendering | 2 días | Fase 6 | Bajo |

**Total**: ~17-24 días de desarrollo

**Enfoque incremental:**
- ✅ Fase 1-4: Funcionalidad core (usable sin avoid_elements)
- ✅ Lanzar v2.1-beta sin collision avoidance
- ✅ Fase 5: Agregar en v2.1-rc1 / v2.2

---

### Criterios de Éxito

#### Funcionales
- [x] Routing `straight` funciona (refactor exitoso)
- [x] Routing `orthogonal` genera paths H-V correctos
- [x] Routing `bezier` genera curvas suaves
- [x] Routing `arc` funciona para self-loops
- [x] `corner_radius` preparado (rendering básico)
- ~~`avoid_elements`~~ DESCARTADA (2026-08-02): la evitación es incondicional vía visibility graph
- [x] Compatible con SDJF v1.5 waypoints

#### No Funcionales
- [x] Performance: <500ms para diagramas de 100 elementos
- [x] 100% backward compatible con v2.0
- [x] Tests funcionales con ejemplos reales
- [x] Documentación actualizada
- [x] Ejemplos de routing types (test-routing-v2.1.gag, test-routing-types.gag)

---

## 🔮 Futuras Versiones

### SDJF v2.2 (Q2 2026)
**Objetivo**: Optimizaciones y refinamientos

- **Layout constraints**: align-left, align-center, distribute-evenly
- **Custom spacing**: `margin` property para elementos
- **Force-directed layout**: Alternativa a auto-layout híbrido
- **Smart label placement**: Evitar colisiones con mejor heurística
- **Z-index explícito**: Control de orden de renderizado

**Complejidad**: Media
**Impacto**: Alto (mejora calidad de diagramas)

---

### SDJF v3.0 (Q3-Q4 2026)
**Objetivo**: Interactividad y temas

#### Temas Predefinidos
```json
{
  "theme": "cloud-architecture",
  "elements": [
    {
      "id": "api",
      "type": "server",
      "label": "API"
      // Color, estilo, tamaño definido por tema
    }
  ]
}
```

**Temas iniciales:**
- `minimal` - Blanco/negro, líneas finas
- `tech` - Azules/grises, estilo moderno
- `cloud` - Colores pastel, estilo cloud
- `enterprise` - Profesional, colores corporativos

#### Animación SVG
```json
{
  "animation": {
    "enabled": true,
    "mode": "sequential",
    "duration": 2000
  }
}
```

**Modos:**
- `sequential` - Elementos aparecen uno por uno
- `level-by-level` - Por niveles del grafo
- `fade-in` - Fade in simultáneo

#### Íconos SVG Externos
```json
{
  "id": "custom",
  "type": "custom",
  "icon_url": "https://example.com/icon.svg"
}
```

**Complejidad**: Alta
**Impacto**: Muy Alto (diferenciación)

---

### SDJF v3.1+ (2027)
**Objetivo**: Features avanzados

- **Clustering automático**: Detectar grupos y contenedores automáticamente
- **Multi-canvas**: Subdiagramas enlazados
- **Exportación interactiva**: HTML + JavaScript para zoom/pan
- **Git diff**: Comparar versiones de diagramas
- **AI-assisted layout**: Usar ML para mejorar posicionamiento

---

## 🎯 Métricas de Éxito

### Adopción
- [ ] 100+ estrellas en GitHub
- [ ] 10+ contribuidores externos
- [ ] 50+ diagramas en producción

### Calidad
- [ ] Test coverage >85%
- [ ] 0 bugs críticos en últimas 3 releases
- [ ] Documentación completa y actualizada

### Performance
- [ ] <100ms para diagramas pequeños (<20 elementos)
- [ ] <500ms para diagramas medianos (20-100 elementos)
- [ ] <2s para diagramas grandes (100-500 elementos)

---

## 📊 Riesgos y Mitigaciones

### Riesgo 1: Collision Avoidance Complejo
**Probabilidad**: Alta
**Impacto**: Alto

**Mitigación:**
- Empezar con algoritmo simple (A* en grid)
- Lanzar v2.1-beta sin avoid_elements
- Agregar en v2.1-rc1 si es posible, o v2.2 si no

### Riesgo 2: Performance con Diagramas Grandes
**Probabilidad**: Media
**Impacto**: Alto

**Mitigación:**
- Profiling temprano
- Optimizaciones incrementales (spatial hashing, caching)
- Documentar límites recomendados

### Riesgo 3: Compatibilidad Rota
**Probabilidad**: Baja
**Impacto**: Crítico

**Mitigación:**
- Tests de regresión exhaustivos
- Mantener backward compatibility como prioridad #1
- Deprecation warnings antes de breaking changes

---

## 🤝 Contribuciones

Ver [CONTRIBUTING.md](CONTRIBUTING.md) para guías de contribución.

**Áreas que necesitan ayuda:**
- [ ] Implementación de routers (v2.1)
- [ ] Tests visuales automáticos
- [ ] Documentación de ejemplos
- [ ] Nuevos tipos de íconos
- [ ] Optimizaciones de performance

---

## 📚 Referencias

- [SDJF v2.1 Proposal](docs/spec/SDJF_v2.1_PROPOSAL.md) - Especificación detallada
- [Implementation Strategy](docs/architecture/IMPLEMENTATION_STRATEGY.md) - Detalles técnicos
- [Architecture](docs/architecture/ARCHITECTURE.md) - Diseño del sistema

---

**Actualizado**: 2026-02-27
