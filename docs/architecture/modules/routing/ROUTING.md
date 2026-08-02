# Biblioteca de routing compartida

> **⚠️ DESACTUALIZADO (pre-reorg `strategies/`, ≤jun-2026).** El pipeline
> real es: `generator.py` (expand_unions §H7 → semantics §Q63 → theme §O57 →
> `select_strategy` → templates) → `LayoutEngine` (`auto`/`hier`/`legacy`) →
> banding §P60 → anticolisión §P61 → re-ruteo → métricas §O52. Ver el código
> y `docs/reviews/auditoria-2026-08-02/` (BUGS-DOCS-002/003/004); este
> documento se conserva por su valor histórico hasta su reescritura.


`AlmaGag/routing/` calcula los **paths concretos** de las conexiones entre elementos: dado un layout con posiciones resueltas, decide la geometría exacta de cada línea/curva en el SVG.

Es **biblioteca compartida** — AUTO y LAF la usan vía sus respectivas `routing_policy.py`. La biblioteca no sabe nada del algoritmo de layout; recibe un `Layout` con coordenadas resueltas y escribe los paths.

📍 `AlmaGag/routing/` · entrada principal: `ConnectionRouterManager` en `router_manager.py`

---

## Responsabilidad

**Qué hace:**
- Para cada conexión del layout, calcula la geometría (puntos, curvas).
- Soporta 5 tipos declarativos de routing (ver abajo).
- Maneja port assignment (12 sectores angulares por elemento) para distribuir conexiones múltiples.
- Detecta y rutea self-loops como arcos.
- Routing obstacle-aware para ortogonal (visibility graph estilo libavoid/Adaptagrams).

**Qué no hace:**
- No decide cuándo rutar (eso es responsabilidad del optimizer, vía `routing_policy.py`).
- No mueve elementos ni cambia el layout (solo lee posiciones).
- No emite SVG (eso es `renderer.py`); produce datos de path que el renderer usa.

---

## Tipos declarativos de routing

El SDJF puede especificar `routing.type` en cada conexión. La biblioteca elige el router correspondiente:

| Tipo | Router | Uso típico |
|---|---|---|
| `straight` | `StraightRouter` | Línea directa (default, compatibilidad v1.0/v2.0) |
| `orthogonal` | `OrthogonalRouter` | Líneas H-V o V-H, diagramas de arquitectura |
| `bezier` | `BezierRouter` | Curvas suaves, flow diagrams orgánicos |
| `arc` | `ArcRouter` | Arcos circulares, self-loops, recursión |
| `manual` | `ManualRouter` | Waypoints explícitos del usuario (SDJF v1.5 compat) |

Sintaxis típica en SDJF:

```json
{
  "from": "A", "to": "B",
  "routing": {
    "type": "orthogonal",
    "corner_radius": 10,
    "avoid_elements": true
  }
}
```

---

## Componentes

### `router_manager.py` — `ConnectionRouterManager`

Punto de entrada. Coordina los distintos routers, mantiene compatibilidad con SDJF v1.5 (waypoints viejos), y expone un único método público:

```python
manager.calculate_all_paths(layout)
```

Esto es lo que las `routing_policy.py` invocan. El manager interpreta `routing.type` (o detecta legacy waypoints) y delega al router correcto.

### `router_base.py` — `ConnectionRouter`

Clase base abstracta. Define la interfaz que cada router específico implementa. Cualquier router nuevo debe heredar de aquí.

### `straight_router.py`, `orthogonal_router.py`, `bezier_router.py`, `arc_router.py`, `manual_router.py`

Los 5 routers declarativos. Cada uno implementa el contrato de `router_base` para su geometría específica.

### `port_assignment.py` — `PortAssignment`

Distribuye múltiples conexiones que entran al mismo elemento entre **12 sectores angulares** (uno cada 30°). Si 5 conexiones llegan "desde arriba" al mismo nodo, se reparten en 5 puntos paralelos del sector superior, en vez de superponerse.

### `visibility_graph.py` — `OrthogonalVisibilityGraph`

Routing ortogonal obstacle-aware (estilo libavoid/Adaptagrams):

1. Construye visibility graph desde bounding boxes inflados de obstáculos.
2. Channel lines inter-nivel para routing limpio entre capas.
3. Penalidad de proximidad para empujar paths lejos de bordes.
4. Búsqueda A* minimizando: longitud + bends + proximidad.

Usado por `OrthogonalRouter` con fallback a midpoint routing naive si el visibility graph falla.

---

## Cómo lo invocan AUTO y LAF

Ninguno de los algoritmos accede directamente a `ConnectionRouterManager`. Cada uno tiene su `routing_policy.py` que encapsula la invocación:

- **AUTO** instancia `ConnectionRouterManager` dentro de `AutoRoutingPolicy.__init__` y lo invoca 4 veces durante el pipeline.
- **LAF** recibe el `ConnectionRouterManager` por inyección (construido en `generator.py`) y lo envuelve en `LAFRoutingPolicy`, que lo invoca 1 vez en Fase 10. Permite `router_manager=None` para correr sin routing.

Detalle: `../layout/auto/routing.md` y `../layout/laf/routing.md`.

---

## Para profundizar

- **Política de routing de AUTO**: `../layout/auto/routing.md`
- **Política de routing de LAF**: `../layout/laf/routing.md`
- **Spec del formato `routing.type`**: `docs/spec/SDJF_v2.1_PROPOSAL.md`
- **Conceptos transversales**: `../../../CONCEPTS.md`
