# Política de routing de AUTO

> **⚠️ DESACTUALIZADO (pre-reorg `strategies/`, ≤jun-2026).** El pipeline
> real es: `generator.py` (expand_unions §H7 → semantics §Q63 → theme §O57 →
> `select_strategy` → templates) → `LayoutEngine` (`auto`/`hier`/`legacy`) →
> banding §P60 → anticolisión §P61 → re-ruteo → métricas §O52. Ver el código
> y `docs/reviews/auditoria-2026-08-02/` (BUGS-DOCS-002/003/004); este
> documento se conserva por su valor histórico hasta su reescritura.


`AutoRoutingPolicy` encapsula **cuándo y cómo** el algoritmo AUTO invoca al `ConnectionRouterManager` (biblioteca compartida en `AlmaGag/routing/`) durante su pipeline de optimización.

📍 `AlmaGag/layout/auto/routing_policy.py`

---

## Responsabilidad

Separar dos preocupaciones:

- **Quién decide cuándo rutar** → `AutoLayoutOptimizer` (vía esta policy).
- **Cómo se calculan los paths concretos** → `ConnectionRouterManager` (biblioteca compartida en `AlmaGag/routing/`, doc en `../../routing/ROUTING.md`).

La policy centraliza también el patrón "setear `sizing` en el layout antes de rutar", que se repite en todas las invocaciones.

---

## Contrato público

```python
class AutoRoutingPolicy:
    def __init__(self, sizing): ...
    def route(self, layout) -> None: ...
```

- **`__init__(sizing)`** — Recibe un `SizingCalculator`. Internamente instancia su propio `ConnectionRouterManager`.
- **`route(layout)`** — Calcula paths de todas las conexiones del layout, inyectando `sizing` previamente.

Único método público. No expone el `router_manager` interno (es implementation-detail).

---

## Invocaciones en el pipeline de AUTO

`AutoLayoutOptimizer` llama a `self.routing.route()` en **4 momentos** del pipeline. Aunque el body es idéntico en las 4, las diferencias semánticas viven en el callsite:

| # | Momento | Por qué se invoca |
|---|---|---|
| 1 | Tras calcular dimensiones de contenedores (Fase 0.6) | Necesario antes de posicionar labels: las labels se ubican relativo a los paths |
| 2 | Tras calcular canvas desde bounds (Fase 2.7) | Routing único con canvas y posiciones finales |
| 3 | Iteración: tras expansión de canvas | Recalcular paths (posiciones no cambian, pero el bounding box sí); precedido por `invalidate_collision_cache()` |
| 4 | Iteración: tras movimiento de elementos | Recalcular paths con nuevas posiciones |

---

## Asimetría con LAF

`AutoRoutingPolicy` y `LAFRoutingPolicy` comparten **misma interfaz pública** (`.route()`), pero difieren en construcción:

| | AUTO | LAF |
|---|---|---|
| Construcción del `router_manager` | Internamente, en `__init__` | Recibido por inyección desde `generator.py` |
| Opcionalidad | Obligatorio | Opcional (`router_manager=None` permitido) |
| Property `.enabled` | No la necesita (siempre activo) | Sí (`True` si el `router_manager` fue inyectado) |
| Invocaciones por pipeline completo | 4 | 1 |

Esta asimetría refleja que AUTO **siempre** rutea (es parte de su contrato) mientras LAF puede correr en modos de debug parcial sin routing. Ver `LAFRoutingPolicy` en `../laf/routing.md`.

---

## Para profundizar

- **Algoritmo AUTO**: `AUTO.md`
- **Biblioteca de routing**: `../../routing/ROUTING.md`
- **Política simétrica en LAF**: `../laf/routing.md`
