# SDJF v2.1 - Waypoints Automáticos y Tipos de Líneas

**Estado**: ✅ Implementado
**Versión**: 2.1
**Fecha**: 2026-01-08

## Motivación

### Problema Actual (v1.5 y v2.0)

En SDJF v1.5 se introdujeron waypoints manuales:

```json
{
  "from": "A",
  "to": "B",
  "waypoints": [
    {"x": 450, "y": 490},
    {"x": 300, "y": 490}
  ]
}
```

**Limitaciones:**
1. **Coordenadas fijas**: Los waypoints tienen `x`, `y` explícitos
2. **No adaptativo**: Si elementos se mueven (auto-layout v2.0), los waypoints quedan descolocados
3. **Sin semántica**: No hay manera de expresar "quiero routing ortogonal" sin calcular puntos manualmente
4. **Incompatible con auto-layout**: Auto-layout calcula posiciones de elementos, pero no de waypoints

### Visión v2.1

**Waypoints declarativos** controlados por auto-layout, con soporte para diferentes estilos de líneas.

## Propuesta: Propiedad `routing`

### Nueva Propiedad en Conexiones

```json
{
  "from": "server1",
  "to": "database",
  "routing": {
    "type": "orthogonal",
    "avoid_elements": true
  },
  "label": "query",
  "direction": "forward"
}
```

### Tipos de Routing

| Tipo | Descripción | Waypoints | Uso |
|------|-------------|-----------|-----|
| `straight` | Línea recta directa | No | Simple, directo (default) |
| `orthogonal` | Líneas horizontales/verticales | Sí (auto) | Diagramas arquitecturales |
| `bezier` | Curva de Bézier suave | No | Flujos, organigramas |
| `arc` | Arco circular | No | Retroalimentación, bucles |
| `manual` | Waypoints explícitos (v1.5) | Sí (manual) | Control total |

## Especificación Detallada

### 1. Routing: `straight` (default)

Línea recta directa entre elementos. Compatible con v1.0/v2.0.

```json
{
  "from": "A",
  "to": "B",
  "routing": {"type": "straight"}
}
```

**Implementación:**
- SVG `<line>` desde centro A hasta centro B
- Aplica offsets visuales según tipo de ícono
- Sin waypoints

**Comportamiento:**
- ✅ Rápido de calcular
- ⚠️ Puede cruzar elementos intermedios

---

### 2. Routing: `orthogonal`

Líneas horizontales y verticales (estilo diagrama de flujo).

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

**Propiedades:**

| Propiedad | Tipo | Default | Descripción |
|-----------|------|---------|-------------|
| `type` | string | - | `"orthogonal"` |
| `avoid_elements` | boolean | true | Si debe evitar elementos intermedios |
| `corner_radius` | integer | 0 | Radio de esquinas redondeadas (px) |
| `preference` | string | `"horizontal"` | Primera dirección: `"horizontal"` o `"vertical"` |

**Algoritmo Propuesto:**

```
1. Calcular posición de A y B (después de auto-layout)
2. Determinar orientación preferida:
   - Si B está más a la derecha/izquierda → horizontal primero
   - Si B está más arriba/abajo → vertical primero
3. Generar waypoints automáticos:
   a. Salir de A en dirección preferida
   b. Navegar hacia B evitando colisiones
   c. Llegar a B en ángulo recto
4. Aplicar corner_radius si > 0 (bordes suavizados)
```

**Implementación:**
- SVG `<polyline>` con 2-4 waypoints calculados
- Algoritmo A* o heurística simple para `avoid_elements=true`
- Corner radius usando atributos SVG o curvas

**Ejemplo Generado:**
```json
// Input (usuario)
{
  "from": "server",
  "to": "db",
  "routing": {"type": "orthogonal"}
}

// Output (después de auto-layout)
<polyline points="120,250 300,250 300,400 520,400" />
```

---

### 3. Routing: `bezier`

Curvas suaves de Bézier.

```json
{
  "from": "A",
  "to": "B",
  "routing": {
    "type": "bezier",
    "curvature": 0.5
  }
}
```

**Propiedades:**

| Propiedad | Tipo | Default | Descripción |
|-----------|------|---------|-------------|
| `type` | string | - | `"bezier"` |
| `curvature` | float | 0.5 | Intensidad de curvatura [0.0, 1.0] |

**Algoritmo Propuesto:**

```
1. Calcular posición de A y B
2. Calcular puntos de control basados en:
   - Vector A→B
   - Distancia entre A y B
   - Factor curvature
3. Generar curva cúbica de Bézier
```

**Implementación:**
- SVG `<path>` con comando `C` (cubic Bézier)
- Puntos de control perpendiculares al vector A→B

**Ejemplo Generado:**
```json
// Input
{
  "from": "api",
  "to": "cache",
  "routing": {"type": "bezier", "curvature": 0.6}
}

// Output (SVG path)
<path d="M 120,250 C 180,200 280,200 340,250" />
```

---

### 4. Routing: `arc`

Arco circular (útil para loops/retroalimentación).

```json
{
  "from": "A",
  "to": "A",
  "routing": {
    "type": "arc",
    "radius": 50,
    "side": "top"
  }
}
```

**Propiedades:**

| Propiedad | Tipo | Default | Descripción |
|-----------|------|---------|-------------|
| `type` | string | - | `"arc"` |
| `radius` | integer | 50 | Radio del arco en píxeles |
| `side` | string | `"top"` | Lado del elemento: `"top"`, `"bottom"`, `"left"`, `"right"` |

**Casos de Uso:**
- Self-loops (A → A)
- Retroalimentación visual
- Evitar cruce de líneas

**Implementación:**
- SVG `<path>` con comandos de arco `A`
- Calcular puntos inicial y final en bordes del elemento

**Ejemplo Generado:**
```json
// Input
{
  "from": "optimizer",
  "to": "optimizer",
  "routing": {"type": "arc", "radius": 60, "side": "top"}
}

// Output (SVG path con arco)
<path d="M 120,200 A 60,60 0 0,1 160,200" />
```

---

### 5. Routing: `manual` (compatible v1.5)

Waypoints explícitos (backward compatible).

```json
{
  "from": "A",
  "to": "B",
  "routing": {
    "type": "manual",
    "waypoints": [
      {"x": 450, "y": 490},
      {"x": 300, "y": 490}
    ]
  }
}
```

**Comportamiento:**
- ⚠️ Coordenadas fijas (no adapta si elementos se mueven)
- ✅ Control total sobre el path
- ✅ Compatible con v1.5

---

## Compatibilidad

### Con v1.0/v2.0

```json
{
  "from": "A",
  "to": "B",
  "label": "connection"
}
```
→ Se asume `routing: {"type": "straight"}` (default)

### Con v1.5 (waypoints manuales)

```json
{
  "from": "A",
  "to": "B",
  "waypoints": [{"x": 100, "y": 200}]
}
```
→ Se convierte internamente a:
```json
{
  "routing": {
    "type": "manual",
    "waypoints": [{"x": 100, "y": 200}]
  }
}
```

### Migración

**v1.5 → v2.1 (recomendado):**

```diff
 {
   "from": "optimizer",
   "to": "geometry",
-  "waypoints": [
-    {"x": 450, "y": 490},
-    {"x": 300, "y": 490}
-  ]
+  "routing": {
+    "type": "orthogonal",
+    "avoid_elements": true
+  }
 }
```

**Beneficio:** Waypoints calculados automáticamente, adaptativo a cambios de layout.

## Orden de Implementación

### Fase 1: Infraestructura (Prioridad Alta)

1. **Router Factory**: Clase base para diferentes tipos de routing
   ```python
   class ConnectionRouter(ABC):
       @abstractmethod
       def calculate_path(self, from_elem, to_elem, layout) -> Path:
           pass
   ```

2. **Routers Concretos**:
   - `StraightRouter` (trivial, ya existe)
   - `OrthogonalRouter` (prioritario)
   - `BezierRouter` (medio)
   - `ArcRouter` (bajo)
   - `ManualRouter` (compatibilidad v1.5)

3. **Integración con AutoLayoutOptimizer**:
   - Calcular paths **después** de posicionar elementos
   - Waypoints automáticos basados en coordenadas finales

### Fase 2: Orthogonal Router (Prioridad Alta)

**Algoritmo Simplificado:**

```python
def calculate_orthogonal_path(from_elem, to_elem, avoid_elements):
    """
    Genera waypoints ortogonales (H-V o V-H).

    Estrategia:
    1. Determinar cuadrante relativo (derecha/izquierda, arriba/abajo)
    2. Decidir si salir horizontal o vertical primero
    3. Generar 1-2 waypoints intermedios
    4. Validar colisiones si avoid_elements=True
    """
    from_center = get_center(from_elem)
    to_center = get_center(to_elem)

    dx = to_center.x - from_center.x
    dy = to_center.y - from_center.y

    # Heurística simple: mayor distancia determina primera dirección
    if abs(dx) > abs(dy):
        # Horizontal primero
        waypoint1 = (from_center.x + dx/2, from_center.y)
        waypoint2 = (from_center.x + dx/2, to_center.y)
    else:
        # Vertical primero
        waypoint1 = (from_center.x, from_center.y + dy/2)
        waypoint2 = (to_center.x, from_center.y + dy/2)

    # Si avoid_elements=True, ajustar waypoints para evitar colisiones
    if avoid_elements:
        waypoint1, waypoint2 = adjust_to_avoid_collisions(
            waypoint1, waypoint2, layout.elements
        )

    return [from_center, waypoint1, waypoint2, to_center]
```

### Fase 3: Bezier y Arc (Prioridad Media)

- Fórmulas matemáticas estándar
- SVG paths generados con librerías existentes

### Fase 4: Colisión Avoidance (Prioridad Baja)

- Algoritmo A* o visibility graph para `avoid_elements=true`
- Optimización compleja, puede ser v2.2

## Ejemplo Completo v2.1

```json
{
  "canvas": {"width": 1000, "height": 700},
  "elements": [
    {
      "id": "frontend",
      "type": "cloud",
      "label": "Frontend",
      "hp": 1.5,
      "color": "lightblue"
    },
    {
      "id": "api",
      "type": "server",
      "label": "REST API",
      "label_priority": "high",
      "hp": 2.0,
      "color": "gold"
    },
    {
      "id": "database",
      "type": "building",
      "label": "Database",
      "label_priority": "high",
      "hp": 1.8,
      "color": "orange"
    },
    {
      "id": "cache",
      "type": "cloud",
      "label": "Redis",
      "color": "cyan"
    }
  ],
  "connections": [
    {
      "from": "frontend",
      "to": "api",
      "routing": {"type": "bezier", "curvature": 0.5},
      "label": "HTTPS",
      "direction": "forward"
    },
    {
      "from": "api",
      "to": "database",
      "routing": {"type": "orthogonal", "avoid_elements": true},
      "label": "SQL",
      "direction": "forward"
    },
    {
      "from": "api",
      "to": "cache",
      "routing": {"type": "orthogonal", "corner_radius": 10},
      "label": "get/set",
      "direction": "bidirectional"
    },
    {
      "from": "cache",
      "to": "cache",
      "routing": {"type": "arc", "radius": 50, "side": "top"},
      "label": "evict",
      "direction": "forward"
    }
  ]
}
```

**Resultado Esperado:**
- `frontend → api`: Curva suave de Bézier
- `api → database`: Línea ortogonal evitando elementos
- `api ↔ cache`: Línea ortogonal con esquinas redondeadas
- `cache → cache`: Arco circular (self-loop)
- Todos los waypoints calculados automáticamente después de auto-layout

## Beneficios

1. **Declarativo**: El usuario expresa *qué quiere*, no *cómo hacerlo*
2. **Adaptativo**: Waypoints se recalculan si elementos se mueven
3. **Compatible**: v1.5 waypoints siguen funcionando
4. **Expresivo**: Diferentes estilos visuales sin cálculos manuales
5. **Semántico**: `orthogonal`, `bezier`, `arc` tienen significado claro

## Consideraciones de Implementación

### Módulo Nuevo: `AlmaGag/routing/`

```
AlmaGag/routing/
├── __init__.py
├── router_base.py         # Interfaz ConnectionRouter
├── straight_router.py     # Línea recta (ya existe en connections.py)
├── orthogonal_router.py   # Routing ortogonal
├── bezier_router.py       # Curvas Bézier
├── arc_router.py          # Arcos circulares
└── manual_router.py       # Waypoints explícitos (v1.5 compat)
```

### Integración con AutoLayoutOptimizer

```python
# En optimize() después de posicionar elementos:

def optimize(self, layout, max_iterations=10):
    # 1. Posicionar elementos (ya existe)
    positioned_layout = self.positioner.calculate_missing_positions(layout)

    # 2. Calcular paths de conexiones (NUEVO)
    routed_layout = self.connection_router.calculate_all_paths(positioned_layout)

    # 3. Optimizar colisiones (ya existe)
    optimized_layout = self._resolve_collisions(routed_layout, max_iterations)

    return optimized_layout
```

### Cambio en `draw/connections.py`

```python
# Antes (v1.5)
def draw_connection_line(dwg, from_elem, to_elem, connection):
    if 'waypoints' in connection:
        # Polyline con waypoints manuales
        draw_polyline(dwg, waypoints)
    else:
        # Línea recta
        draw_line(dwg, from_elem, to_elem)

# Después (v2.1)
def draw_connection_line(dwg, connection):
    # connection ya tiene 'computed_path' después de routing
    path = connection['computed_path']

    if path['type'] == 'line':
        draw_svg_line(dwg, path['points'])
    elif path['type'] == 'polyline':
        draw_svg_polyline(dwg, path['points'], path.get('corner_radius', 0))
    elif path['type'] == 'bezier':
        draw_svg_bezier(dwg, path['control_points'])
    elif path['type'] == 'arc':
        draw_svg_arc(dwg, path['start'], path['end'], path['radius'])
```

## Roadmap

- [x] **v2.1-alpha**: Infraestructura de routing + `straight` (refactor existing)
- [x] **v2.1-beta**: `orthogonal` básico (sin avoid_elements)
- [x] **v2.1-rc1**: `bezier` + `arc` + corner_radius
- [ ] **v2.2**: `orthogonal` con `avoid_elements=true` (A* o heurística)
- [ ] **v2.3**: Optimización avanzada, visibility graphs

---

**Estado**: ✅ Implementado (v2.1)
**Siguiente Paso**: Implementar collision avoidance en v2.2
**Feedback**: Bienvenido en issues o PRs

## Ejemplos de Uso

Ver archivos de prueba:
- `test-routing-v2.1.gag` - Ejemplo completo con todos los tipos de routing
- `test-routing-types.gag` - Demostración de cada tipo de routing individual
