# Estrategias de Implementación - SDJF v2.1

**Objetivo**: Guía técnica detallada para implementar waypoints automáticos
**Audiencia**: Desarrolladores contribuyendo a AlmaGag
**Actualizado**: 2026-01-08

---

## Índice

1. [Arquitectura General](#arquitectura-general)
2. [Fase 1: Infraestructura](#fase-1-infraestructura)
3. [Fase 2: Orthogonal Router](#fase-2-orthogonal-router)
4. [Fase 3: Bezier y Arc](#fase-3-bezier-y-arc)
5. [Fase 4: Corner Radius](#fase-4-corner-radius)
6. [Fase 5: Collision Avoidance](#fase-5-collision-avoidance)
7. [Fase 6-7: Integración y Rendering](#fase-6-7-integración-y-rendering)
8. [Testing Strategy](#testing-strategy)
9. [Performance Considerations](#performance-considerations)

---

## Arquitectura General

### Nuevos Componentes

```
AlmaGag/
├── routing/                      # NUEVO módulo
│   ├── __init__.py
│   ├── router_base.py           # Interfaz abstracta
│   ├── straight_router.py       # Línea recta (refactor)
│   ├── orthogonal_router.py     # Routing H-V / V-H
│   ├── bezier_router.py         # Curvas de Bézier
│   ├── arc_router.py            # Arcos circulares
│   ├── manual_router.py         # Compatibilidad v1.5
│   ├── router_manager.py        # Dispatcher de routers
│   └── utils/
│       ├── path.py              # Clases Path, Point
│       ├── geometry.py          # Helpers geométricos
│       └── astar.py             # A* para collision avoidance
│
├── layout/
│   └── auto_optimizer.py        # MODIFICAR: integrar routing
│
└── draw/
    └── connections.py            # MODIFICAR: usar computed_path
```

### Flujo de Datos

```
JSON Input
    ↓
Layout (con conexiones sin paths)
    ↓
AutoLayoutOptimizer.optimize()
    ├─ Auto-positioning (v2.0)
    ├─ ConnectionRouterManager.calculate_all_paths()  ← NUEVO
    │   ├─ Para cada conexión:
    │   │   ├─ Leer routing spec
    │   │   ├─ Seleccionar router apropiado
    │   │   └─ Calcular path → connection['computed_path']
    │   └─ Retornar layout con paths calculados
    └─ Collision resolution (existente)
    ↓
Layout con computed_paths
    ↓
draw_connection_line() lee computed_path  ← MODIFICAR
    ↓
SVG Output
```

---

## Fase 1: Infraestructura

### 1.1 Clases de Datos

**`routing/utils/path.py`**

```python
from dataclasses import dataclass
from typing import List, Optional, Literal

@dataclass
class Point:
    """Punto 2D en el canvas."""
    x: float
    y: float

    def distance_to(self, other: 'Point') -> float:
        """Distancia euclidiana."""
        return math.sqrt((self.x - other.x)**2 + (self.y - other.y)**2)

    def __add__(self, other: 'Point') -> 'Point':
        return Point(self.x + other.x, self.y + other.y)

    def __sub__(self, other: 'Point') -> 'Point':
        return Point(self.x - other.x, self.y - other.y)

    def __mul__(self, scalar: float) -> 'Point':
        return Point(self.x * scalar, self.y * scalar)


PathType = Literal['line', 'polyline', 'bezier', 'arc']


@dataclass
class Path:
    """
    Representa un path calculado para una conexión.

    Usado para comunicación entre routers y rendering.
    """
    type: PathType
    points: List[Point]
    control_points: Optional[List[Point]] = None  # Para bezier
    arc_center: Optional[Point] = None            # Para arc
    radius: Optional[float] = None                # Para arc
    corner_radius: Optional[float] = None         # Para polyline

    def to_svg_commands(self) -> str:
        """Convierte path a comandos SVG."""
        if self.type == 'line':
            return self._line_to_svg()
        elif self.type == 'polyline':
            return self._polyline_to_svg()
        elif self.type == 'bezier':
            return self._bezier_to_svg()
        elif self.type == 'arc':
            return self._arc_to_svg()

    def _line_to_svg(self) -> str:
        p1, p2 = self.points
        return f"M {p1.x},{p1.y} L {p2.x},{p2.y}"

    def _polyline_to_svg(self) -> str:
        if self.corner_radius and self.corner_radius > 0:
            return self._polyline_with_rounded_corners()
        else:
            points_str = " ".join([f"{p.x},{p.y}" for p in self.points])
            return f"M {self.points[0].x},{self.points[0].y} L {points_str[2:]}"

    def _bezier_to_svg(self) -> str:
        p0, p1 = self.points
        c1, c2 = self.control_points
        return f"M {p0.x},{p0.y} C {c1.x},{c1.y} {c2.x},{c2.y} {p1.x},{p1.y}"

    def _arc_to_svg(self) -> str:
        # SVG arc command: A rx ry x-axis-rotation large-arc-flag sweep-flag x y
        p1, p2 = self.points
        r = self.radius
        return f"M {p1.x},{p1.y} A {r},{r} 0 0,1 {p2.x},{p2.y}"

    def _polyline_with_rounded_corners(self) -> str:
        """Genera SVG path con esquinas redondeadas."""
        if len(self.points) < 3:
            return self._polyline_to_svg()  # No hay esquinas

        radius = self.corner_radius
        commands = [f"M {self.points[0].x},{self.points[0].y}"]

        for i in range(1, len(self.points) - 1):
            prev = self.points[i - 1]
            curr = self.points[i]
            next_pt = self.points[i + 1]

            # Vectores
            v1 = Point(curr.x - prev.x, curr.y - prev.y)
            v2 = Point(next_pt.x - curr.x, next_pt.y - curr.y)

            # Normalizar
            len1 = math.sqrt(v1.x**2 + v1.y**2)
            len2 = math.sqrt(v2.x**2 + v2.y**2)

            # Calcular puntos de tangencia
            t1 = Point(curr.x - (v1.x / len1) * radius,
                      curr.y - (v1.y / len1) * radius)
            t2 = Point(curr.x + (v2.x / len2) * radius,
                      curr.y + (v2.y / len2) * radius)

            # Línea hasta tangencia, luego arco
            commands.append(f"L {t1.x},{t1.y}")
            commands.append(f"Q {curr.x},{curr.y} {t2.x},{t2.y}")

        # Línea final
        commands.append(f"L {self.points[-1].x},{self.points[-1].y}")

        return " ".join(commands)
```

### 1.2 Interfaz Base

**`routing/router_base.py`**

```python
from abc import ABC, abstractmethod
from typing import Dict, Any
from AlmaGag.routing.utils.path import Path, Point

class ConnectionRouter(ABC):
    """
    Interfaz abstracta para routers de conexiones.

    Cada router implementa un estilo de línea diferente.
    """

    @abstractmethod
    def calculate_path(self,
                      from_elem: Dict[str, Any],
                      to_elem: Dict[str, Any],
                      routing_spec: Dict[str, Any],
                      layout: 'Layout') -> Path:
        """
        Calcula path entre dos elementos.

        Args:
            from_elem: Elemento origen (con 'x', 'y')
            to_elem: Elemento destino (con 'x', 'y')
            routing_spec: Especificación de routing (ej: {"type": "orthogonal", ...})
            layout: Layout completo (para avoid_elements, etc.)

        Returns:
            Path: Path calculado listo para renderizar

        Raises:
            ValueError: Si elementos no tienen coordenadas
        """
        pass

    def _get_center(self, element: Dict[str, Any]) -> Point:
        """Helper: obtiene centro del elemento."""
        x = element.get('x')
        y = element.get('y')

        if x is None or y is None:
            raise ValueError(f"Element {element.get('id')} missing coordinates")

        # Considerar hp/wp si existe SizingCalculator
        from AlmaGag.config import ICON_WIDTH, ICON_HEIGHT
        width = element.get('width', ICON_WIDTH)
        height = element.get('height', ICON_HEIGHT)

        return Point(x + width / 2, y + height / 2)

    def _apply_offset(self, center: Point, towards: Point, offset: float) -> Point:
        """Helper: aplica offset desde centro hacia dirección."""
        dx = towards.x - center.x
        dy = towards.y - center.y
        distance = math.sqrt(dx**2 + dy**2)

        if distance == 0:
            return center

        # Normalizar y aplicar offset
        return Point(
            center.x + (dx / distance) * offset,
            center.y + (dy / distance) * offset
        )
```

### 1.3 Straight Router (Refactor)

**`routing/straight_router.py`**

```python
from AlmaGag.routing.router_base import ConnectionRouter
from AlmaGag.routing.utils.path import Path, Point

class StraightRouter(ConnectionRouter):
    """
    Router de línea recta directa.

    Compatible con v1.0/v2.0 (default).
    """

    def calculate_path(self, from_elem, to_elem, routing_spec, layout):
        """Genera línea recta con offsets visuales."""
        from_center = self._get_center(from_elem)
        to_center = self._get_center(to_elem)

        # Aplicar offsets visuales (evitar overlap con íconos)
        from_offset = self._calculate_offset(from_elem)
        to_offset = self._calculate_offset(to_elem)

        start = self._apply_offset(from_center, to_center, from_offset)
        end = self._apply_offset(to_center, from_center, to_offset)

        return Path(type='line', points=[start, end])

    def _calculate_offset(self, element):
        """Calcula offset según tipo de elemento."""
        elem_type = element.get('type', 'server')

        # Offsets por tipo (cloud usa elipse, necesita más offset)
        offsets = {
            'cloud': 35,
            'building': 30,
            'server': 30,
            'firewall': 30
        }

        return offsets.get(elem_type, 30)
```

### 1.4 Router Manager

**`routing/router_manager.py`**

```python
from typing import Dict
from AlmaGag.routing.router_base import ConnectionRouter
from AlmaGag.routing.straight_router import StraightRouter
from AlmaGag.routing.manual_router import ManualRouter


class ConnectionRouterManager:
    """
    Dispatcher que selecciona y ejecuta routers apropiados.

    Responsabilidades:
    - Mantener registry de routers
    - Parsear routing spec
    - Ejecutar router correcto
    - Fallback a straight si router no existe
    """

    def __init__(self):
        self.routers: Dict[str, ConnectionRouter] = {
            'straight': StraightRouter(),
            'manual': ManualRouter()
            # Otros routers se agregarán en fases posteriores
        }

    def register_router(self, name: str, router: ConnectionRouter):
        """Registra nuevo router (extensibilidad)."""
        self.routers[name] = router

    def calculate_all_paths(self, layout: 'Layout'):
        """
        Calcula paths para todas las conexiones en layout.

        Modifica layout in-place agregando 'computed_path' a cada conexión.
        """
        for connection in layout.connections:
            # Parsear spec
            routing_spec = self._parse_routing_spec(connection)

            # Seleccionar router
            router_type = routing_spec['type']
            router = self.routers.get(router_type, self.routers['straight'])

            # Obtener elementos
            from_elem = layout.elements_by_id.get(connection['from'])
            to_elem = layout.elements_by_id.get(connection['to'])

            if not from_elem or not to_elem:
                continue  # Skip conexión inválida

            # Calcular path
            try:
                path = router.calculate_path(from_elem, to_elem, routing_spec, layout)
                connection['computed_path'] = path
            except Exception as e:
                print(f"[WARN] Error calculando path para {connection.get('from')} -> {connection.get('to')}: {e}")
                # Fallback: straight line simple
                fallback_path = self.routers['straight'].calculate_path(
                    from_elem, to_elem, {'type': 'straight'}, layout
                )
                connection['computed_path'] = fallback_path

    def _parse_routing_spec(self, connection: dict) -> dict:
        """
        Parsea especificación de routing de la conexión.

        Soporta:
        - v2.1: {"routing": {"type": "orthogonal", ...}}
        - v1.5: {"waypoints": [...]} → convierte a manual
        - v1.0: {} → default straight
        """
        if 'routing' in connection:
            return connection['routing']
        elif 'waypoints' in connection:
            # Compatibilidad v1.5
            return {
                'type': 'manual',
                'waypoints': connection['waypoints']
            }
        else:
            # Default: straight
            return {'type': 'straight'}
```

### 1.5 Manual Router (Compatibilidad v1.5)

**`routing/manual_router.py`**

```python
from AlmaGag.routing.router_base import ConnectionRouter
from AlmaGag.routing.utils.path import Path, Point

class ManualRouter(ConnectionRouter):
    """
    Router con waypoints explícitos (v1.5).

    Backward compatible con conexiones que tienen 'waypoints'.
    """

    def calculate_path(self, from_elem, to_elem, routing_spec, layout):
        """Genera polyline con waypoints explícitos."""
        from_center = self._get_center(from_elem)
        to_center = self._get_center(to_elem)

        waypoints = routing_spec.get('waypoints', [])

        if not waypoints:
            # No hay waypoints, usar straight
            from AlmaGag.routing.straight_router import StraightRouter
            return StraightRouter().calculate_path(from_elem, to_elem, routing_spec, layout)

        # Construir path con waypoints
        points = [from_center]

        for wp in waypoints:
            points.append(Point(wp['x'], wp['y']))

        points.append(to_center)

        return Path(type='polyline', points=points)
```

---

## Fase 2: Orthogonal Router

### 2.1 Algoritmo Básico (Sin Avoid Elements)

**`routing/orthogonal_router.py`**

```python
from AlmaGag.routing.router_base import ConnectionRouter
from AlmaGag.routing.utils.path import Path, Point
import math

class OrthogonalRouter(ConnectionRouter):
    """
    Router ortogonal (horizontal-vertical o vertical-horizontal).

    Genera paths con ángulos de 90 grados.
    """

    def calculate_path(self, from_elem, to_elem, routing_spec, layout):
        """
        Genera path ortogonal.

        Routing spec propiedades:
        - preference: 'horizontal' | 'vertical' | 'auto' (default: 'auto')
        - avoid_elements: bool (default: False) - Fase 5
        - corner_radius: float (default: 0) - Fase 4
        """
        from_center = self._get_center(from_elem)
        to_center = self._get_center(to_elem)

        preference = routing_spec.get('preference', 'auto')
        avoid_elements = routing_spec.get('avoid_elements', False)

        if avoid_elements:
            # Fase 5: usar A*
            return self._calculate_avoiding(from_center, to_center, layout, routing_spec)
        else:
            # Fase 2: heurística simple
            return self._calculate_simple(from_center, to_center, preference)

    def _calculate_simple(self, from_pt: Point, to_pt: Point, preference: str) -> Path:
        """
        Heurística simple: un punto intermedio.

        Estrategia:
        - Auto: elegir H-V si |dx| > |dy|, sino V-H
        - Horizontal: salir horizontal primero
        - Vertical: salir vertical primero
        """
        dx = to_pt.x - from_pt.x
        dy = to_pt.y - from_pt.y

        # Determinar preferencia
        if preference == 'auto':
            preference = 'horizontal' if abs(dx) > abs(dy) else 'vertical'

        if preference == 'horizontal':
            # H-V: horizontal primero
            mid_x = from_pt.x + dx / 2
            waypoints = [
                from_pt,
                Point(mid_x, from_pt.y),
                Point(mid_x, to_pt.y),
                to_pt
            ]
        else:
            # V-H: vertical primero
            mid_y = from_pt.y + dy / 2
            waypoints = [
                from_pt,
                Point(from_pt.x, mid_y),
                Point(to_pt.x, mid_y),
                to_pt
            ]

        # Simplificar: eliminar puntos colineales
        simplified = self._simplify_orthogonal(waypoints)

        return Path(type='polyline', points=simplified)

    def _simplify_orthogonal(self, points: List[Point]) -> List[Point]:
        """
        Elimina puntos intermedios innecesarios (colineales).

        Ejemplo: [A, B, C] donde A-B-C son colineales → [A, C]
        """
        if len(points) < 3:
            return points

        simplified = [points[0]]

        for i in range(1, len(points) - 1):
            prev = simplified[-1]
            curr = points[i]
            next_pt = points[i + 1]

            # Colinear si mismo eje (x o y idénticos)
            if not ((prev.x == curr.x == next_pt.x) or (prev.y == curr.y == next_pt.y)):
                simplified.append(curr)

        simplified.append(points[-1])

        return simplified

    def _calculate_avoiding(self, from_pt, to_pt, layout, routing_spec):
        """
        Fase 5: Routing evitando elementos usando A*.

        Por ahora, fallback a simple.
        """
        # TODO: Implementar en Fase 5
        return self._calculate_simple(from_pt, to_pt, 'auto')
```

### 2.2 Tests Unitarios

**`tests/test_orthogonal_router.py`**

```python
import unittest
from AlmaGag.routing.orthogonal_router import OrthogonalRouter
from AlmaGag.routing.utils.path import Point

class TestOrthogonalRouter(unittest.TestCase):

    def setUp(self):
        self.router = OrthogonalRouter()
        self.from_elem = {'id': 'A', 'x': 100, 'y': 100}
        self.to_elem = {'id': 'B', 'x': 300, 'y': 300}

    def test_horizontal_preference(self):
        """Path debe ir horizontal primero."""
        routing_spec = {'type': 'orthogonal', 'preference': 'horizontal'}
        path = self.router.calculate_path(
            self.from_elem,
            self.to_elem,
            routing_spec,
            layout=None
        )

        self.assertEqual(path.type, 'polyline')
        self.assertEqual(len(path.points), 4)

        # Verificar que segundo punto tiene misma Y que primero (horizontal)
        self.assertEqual(path.points[1].y, path.points[0].y)

    def test_vertical_preference(self):
        """Path debe ir vertical primero."""
        routing_spec = {'type': 'orthogonal', 'preference': 'vertical'}
        path = self.router.calculate_path(
            self.from_elem,
            self.to_elem,
            routing_spec,
            layout=None
        )

        # Verificar que segundo punto tiene misma X que primero (vertical)
        self.assertEqual(path.points[1].x, path.points[0].x)

    def test_auto_preference_horizontal(self):
        """Auto debe elegir horizontal si |dx| > |dy|."""
        to_elem_far_right = {'id': 'B', 'x': 500, 'y': 150}
        routing_spec = {'type': 'orthogonal', 'preference': 'auto'}

        path = self.router.calculate_path(
            self.from_elem,
            to_elem_far_right,
            routing_spec,
            layout=None
        )

        # |dx|=400, |dy|=50 → debería ir horizontal primero
        self.assertEqual(path.points[1].y, path.points[0].y)

    def test_simplification(self):
        """Puntos colineales deben eliminarse."""
        # TODO: Test con caso específico de simplificación
        pass
```

---

## Fase 3: Bezier y Arc

### 3.1 Bezier Router

**`routing/bezier_router.py`**

```python
from AlmaGag.routing.router_base import ConnectionRouter
from AlmaGag.routing.utils.path import Path, Point
import math

class BezierRouter(ConnectionRouter):
    """
    Router de curvas de Bézier cúbicas.

    Genera curvas suaves entre elementos.
    """

    def calculate_path(self, from_elem, to_elem, routing_spec, layout):
        """
        Genera curva de Bézier.

        Routing spec propiedades:
        - curvature: float (0.0 - 1.0, default: 0.5) - Intensidad de curvatura
        """
        from_center = self._get_center(from_elem)
        to_center = self._get_center(to_elem)

        curvature = routing_spec.get('curvature', 0.5)

        # Calcular puntos de control
        control_points = self._calculate_control_points(
            from_center,
            to_center,
            curvature
        )

        return Path(
            type='bezier',
            points=[from_center, to_center],
            control_points=control_points
        )

    def _calculate_control_points(self, p0: Point, p1: Point, curvature: float):
        """
        Calcula puntos de control para curva cúbica.

        Estrategia: puntos perpendiculares al vector p0→p1
        """
        # Vector p0 → p1
        dx = p1.x - p0.x
        dy = p1.y - p0.y
        distance = math.sqrt(dx**2 + dy**2)

        if distance == 0:
            # Elementos en misma posición, no curvar
            return [p0, p1]

        # Vector perpendicular (rotación 90°)
        perp_x = -dy / distance
        perp_y = dx / distance

        # Distancia de control basada en curvature
        control_distance = distance * curvature * 0.5

        # Puntos de control a 1/3 y 2/3 del camino
        c1 = Point(
            p0.x + dx / 3 + perp_x * control_distance,
            p0.y + dy / 3 + perp_y * control_distance
        )

        c2 = Point(
            p0.x + 2 * dx / 3 + perp_x * control_distance,
            p0.y + 2 * dy / 3 + perp_y * control_distance
        )

        return [c1, c2]
```

### 3.2 Arc Router

**`routing/arc_router.py`**

```python
from AlmaGag.routing.router_base import ConnectionRouter
from AlmaGag.routing.utils.path import Path, Point
import math

class ArcRouter(ConnectionRouter):
    """
    Router de arcos circulares.

    Útil para self-loops y retroalimentación.
    """

    def calculate_path(self, from_elem, to_elem, routing_spec, layout):
        """
        Genera arco circular.

        Routing spec propiedades:
        - radius: float (default: 50) - Radio del arco
        - side: 'top' | 'bottom' | 'left' | 'right' (default: 'top')
        """
        from_center = self._get_center(from_elem)
        to_center = self._get_center(to_elem)

        radius = routing_spec.get('radius', 50)
        side = routing_spec.get('side', 'top')

        if from_elem['id'] == to_elem['id']:
            # Self-loop
            return self._calculate_self_loop(from_center, radius, side)
        else:
            # Arco entre dos elementos
            return self._calculate_arc_between(from_center, to_center, radius)

    def _calculate_self_loop(self, center: Point, radius: float, side: str) -> Path:
        """Genera self-loop (arco que sale y regresa al mismo elemento)."""
        offset = 20  # Distancia desde borde del elemento

        if side == 'top':
            start = Point(center.x - offset, center.y)
            end = Point(center.x + offset, center.y)
            arc_center = Point(center.x, center.y - radius)
        elif side == 'bottom':
            start = Point(center.x - offset, center.y)
            end = Point(center.x + offset, center.y)
            arc_center = Point(center.x, center.y + radius)
        elif side == 'left':
            start = Point(center.x, center.y - offset)
            end = Point(center.x, center.y + offset)
            arc_center = Point(center.x - radius, center.y)
        else:  # right
            start = Point(center.x, center.y - offset)
            end = Point(center.x, center.y + offset)
            arc_center = Point(center.x + radius, center.y)

        return Path(
            type='arc',
            points=[start, end],
            arc_center=arc_center,
            radius=radius
        )

    def _calculate_arc_between(self, p0: Point, p1: Point, radius: float) -> Path:
        """Arco entre dos elementos diferentes."""
        # SVG arc entre dos puntos
        return Path(
            type='arc',
            points=[p0, p1],
            radius=radius
        )
```

---

## Fase 4: Corner Radius

Ver implementación en `Path._polyline_with_rounded_corners()` (ya implementada en Fase 1.1).

**Integración:**

```python
# En OrthogonalRouter.calculate_path()
corner_radius = routing_spec.get('corner_radius', 0)

path = Path(
    type='polyline',
    points=simplified,
    corner_radius=corner_radius
)
```

---

## Fase 5: Collision Avoidance

### 5.1 A* Implementation

**`routing/utils/astar.py`**

```python
import heapq
from typing import List, Tuple, Set, Optional
from dataclasses import dataclass, field

@dataclass(order=True)
class Node:
    """Nodo para A* priority queue."""
    f_score: float
    position: Tuple[int, int] = field(compare=False)
    g_score: float = field(compare=False)


class Grid:
    """Grid 2D para pathfinding."""

    def __init__(self, width: int, height: int, cell_size: int):
        self.width = width
        self.height = height
        self.cell_size = cell_size
        self.cols = width // cell_size
        self.rows = height // cell_size
        self.occupied: Set[Tuple[int, int]] = set()

    def mark_occupied(self, x1: float, y1: float, x2: float, y2: float):
        """Marca rectángulo como ocupado."""
        col1 = int(x1 / self.cell_size)
        row1 = int(y1 / self.cell_size)
        col2 = int(x2 / self.cell_size)
        row2 = int(y2 / self.cell_size)

        for row in range(row1, row2 + 1):
            for col in range(col1, col2 + 1):
                if 0 <= row < self.rows and 0 <= col < self.cols:
                    self.occupied.add((row, col))

    def is_walkable(self, row: int, col: int) -> bool:
        """Verifica si celda es transitable."""
        if row < 0 or row >= self.rows or col < 0 or col >= self.cols:
            return False
        return (row, col) not in self.occupied

    def world_to_grid(self, x: float, y: float) -> Tuple[int, int]:
        """Convierte coordenadas mundo a grid."""
        return (int(y / self.cell_size), int(x / self.cell_size))

    def grid_to_world(self, row: int, col: int) -> Tuple[float, float]:
        """Convierte grid a coordenadas mundo."""
        return (col * self.cell_size + self.cell_size / 2,
                row * self.cell_size + self.cell_size / 2)


def astar_search(grid: Grid,
                 start: Tuple[int, int],
                 goal: Tuple[int, int]) -> Optional[List[Tuple[int, int]]]:
    """
    A* pathfinding algorithm.

    Args:
        grid: Grid con obstáculos marcados
        start: (row, col) inicio
        goal: (row, col) objetivo

    Returns:
        Lista de (row, col) puntos del path, o None si no hay path
    """
    if not grid.is_walkable(start[0], start[1]) or not grid.is_walkable(goal[0], goal[1]):
        return None

    # Priority queue: (f_score, (row, col))
    open_set = []
    heapq.heappush(open_set, Node(f_score=0, position=start, g_score=0))

    # Tracking
    came_from = {}
    g_score = {start: 0}

    while open_set:
        current_node = heapq.heappop(open_set)
        current = current_node.position

        if current == goal:
            return _reconstruct_path(came_from, current)

        # Explorar vecinos (4-connected: arriba, abajo, izq, der)
        neighbors = [
            (current[0] - 1, current[1]),  # arriba
            (current[0] + 1, current[1]),  # abajo
            (current[0], current[1] - 1),  # izquierda
            (current[0], current[1] + 1)   # derecha
        ]

        for neighbor in neighbors:
            if not grid.is_walkable(neighbor[0], neighbor[1]):
                continue

            tentative_g = g_score[current] + 1

            if neighbor not in g_score or tentative_g < g_score[neighbor]:
                came_from[neighbor] = current
                g_score[neighbor] = tentative_g
                f_score = tentative_g + _manhattan_distance(neighbor, goal)

                heapq.heappush(open_set, Node(
                    f_score=f_score,
                    position=neighbor,
                    g_score=tentative_g
                ))

    return None  # No path found


def _manhattan_distance(p1: Tuple[int, int], p2: Tuple[int, int]) -> int:
    """Heurística Manhattan."""
    return abs(p1[0] - p2[0]) + abs(p1[1] - p2[1])


def _reconstruct_path(came_from: dict, current: Tuple[int, int]) -> List[Tuple[int, int]]:
    """Reconstruye path desde came_from."""
    path = [current]
    while current in came_from:
        current = came_from[current]
        path.append(current)
    path.reverse()
    return path


def simplify_path(path: List[Tuple], tolerance: float = 1.0) -> List[Tuple]:
    """
    Simplifica path eliminando puntos innecesarios.

    Usa Douglas-Peucker algorithm.
    """
    if len(path) < 3:
        return path

    # Encontrar punto más lejano
    dmax = 0
    index = 0
    end = len(path) - 1

    for i in range(1, end):
        d = _perpendicular_distance(path[i], path[0], path[end])
        if d > dmax:
            index = i
            dmax = d

    # Si punto más lejano > tolerance, recursivo
    if dmax > tolerance:
        left = simplify_path(path[:index + 1], tolerance)
        right = simplify_path(path[index:], tolerance)
        return left[:-1] + right
    else:
        return [path[0], path[end]]


def _perpendicular_distance(point, line_start, line_end):
    """Distancia perpendicular de point a línea."""
    x0, y0 = point
    x1, y1 = line_start
    x2, y2 = line_end

    numerator = abs((y2 - y1) * x0 - (x2 - x1) * y0 + x2 * y1 - y2 * x1)
    denominator = math.sqrt((y2 - y1)**2 + (x2 - x1)**2)

    if denominator == 0:
        return 0

    return numerator / denominator
```

### 5.2 Integración en OrthogonalRouter

```python
# En OrthogonalRouter._calculate_avoiding()

def _calculate_avoiding(self, from_pt, to_pt, layout, routing_spec):
    """Routing evitando elementos usando A*."""
    from AlmaGag.routing.utils.astar import Grid, astar_search, simplify_path

    # Crear grid
    grid_size = routing_spec.get('grid_size', 20)
    grid = Grid(layout.canvas['width'], layout.canvas['height'], grid_size)

    # Marcar obstáculos
    for elem in layout.elements:
        if 'x' not in elem or 'y' not in elem:
            continue  # Sin coordenadas, skip

        # Get bbox considerando sizing
        bbox = self._get_element_bbox(elem, layout)
        grid.mark_occupied(bbox[0], bbox[1], bbox[2], bbox[3])

    # Convertir a grid
    start_grid = grid.world_to_grid(from_pt.x, from_pt.y)
    goal_grid = grid.world_to_grid(to_pt.x, to_pt.y)

    # A* search
    path_grid = astar_search(grid, start_grid, goal_grid)

    if not path_grid:
        # No path found, fallback a simple
        print("[WARN] A* no encontró path, usando straight")
        return self._calculate_simple(from_pt, to_pt, 'auto')

    # Simplificar
    simplified_grid = simplify_path(path_grid, tolerance=grid_size / 2)

    # Convertir a coordenadas mundo
    path_world = []
    for row, col in simplified_grid:
        x, y = grid.grid_to_world(row, col)
        path_world.append(Point(x, y))

    return Path(type='polyline', points=path_world)
```

---

## Fase 6-7: Integración y Rendering

Ver detalles en [ROADMAP.md](../ROADMAP.md) Fases 6-7.

---

## Testing Strategy

### Niveles de Testing

1. **Unit Tests**: Cada router independientemente
2. **Integration Tests**: Manager + routers juntos
3. **Visual Regression**: Regenerar ejemplos, comparar SVGs
4. **Performance Tests**: Medir tiempo con diagramas grandes

### Visual Regression Testing

```bash
# Regenerar todos los ejemplos
for file in docs/examples/*.gag; do
    almagag "$file"
done

# Comparar con versión anterior (manual o con herramienta)
git diff docs/examples/*.svg
```

---

## Performance Considerations

### Optimizaciones

1. **Caching de bboxes**: Calcular una vez por iteración
2. **Lazy evaluation**: Solo calcular paths si elementos tienen coords
3. **Spatial hashing**: Para collision avoidance con muchos elementos
4. **Grid size adaptativo**: Más grande para diagramas grandes

### Benchmarks

Target performance:
- <100ms para diagramas pequeños (<20 elementos, 30 conexiones)
- <500ms para diagramas medianos (20-100 elementos)
- <2s para diagramas grandes (100-500 elementos)

---

**Actualizado**: 2026-01-08
**Próximo paso**: Comenzar Fase 1 - Infraestructura
