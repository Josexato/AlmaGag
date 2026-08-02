# Política de routing de LAF

> **⚠️ HISTÓRICO — motor LAF congelado como `legacy` (nunca se auto-elige).**
> Rutas y comandos de este documento son previos a la reorg
> `layout/strategies/` y ya no ejecutan. Estado real: `docs/architecture/…`
> queda superado por el código (`AlmaGag/layout/engine.py::_STRATEGIES`);
> auditoría con detalle: `docs/reviews/auditoria-2026-08-02/` (BUGS-DOCS-002).


`LAFRoutingPolicy` encapsula **cuándo** el algoritmo LAF invoca al `ConnectionRouterManager` (biblioteca compartida en `AlmaGag/routing/`) durante su pipeline. Misma interfaz pública que `AutoRoutingPolicy`, construcción interna asimétrica.

📍 `AlmaGag/layout/laf/routing_policy.py`

---

## Responsabilidad

Igual que `AutoRoutingPolicy`: separar **cuándo** rutar (responsabilidad del optimizer) de **cómo** se calculan los paths (responsabilidad de `AlmaGag/routing/`).

A diferencia de AUTO, LAF puede **omitir routing por completo** si se instancia con `router_manager=None` — útil para debug parcial del pipeline cuando solo querés ver el resultado hasta Fase 9.

---

## Contrato público

```python
class LAFRoutingPolicy:
    def __init__(self, router_manager=None): ...

    @property
    def enabled(self) -> bool: ...

    def route(self, layout) -> None: ...
```

- **`__init__(router_manager=None)`** — Recibe (o no) un `ConnectionRouterManager` ya construido. No instancia uno propio.
- **`enabled`** — `True` si el `router_manager` fue inyectado, `False` si es `None`. Permite consultar si LAF va a rutar sin acceder al `router_manager` interno.
- **`route(layout)`** — Si está enabled, calcula paths de todas las conexiones. Si no, no-op silencioso (seguro de llamar siempre).

---

## Invocación en el pipeline de LAF

`LAFOptimizer` usa `self.routing` en **dos momentos** del pipeline. Solo uno invoca `.route()`; el otro es un guard.

| # | Momento | Qué hace |
|---|---|---|
| 1 | Fase 10 — Routing | `self.routing.route(layout)` calcula paths. Si el bloque está enabled, también captura snapshot del visualizer y emite log de debug. |
| 2 | Fase 10.5 — Re-optimización de etiquetas contenidas | `if self.routing.enabled:` gatea la sub-fase. Sin routing previo, no tiene sentido re-optimizar labels contra paths. |

Una sola invocación efectiva de `.route()` (vs 4 en AUTO). LAF concentra todo el routing en una pasada al final del pipeline, después de que el grafo ya está completamente layouteado.

---

## Asimetría con AUTO

Misma interfaz pública (`.route()`), pero construcción interna distinta:

| | AUTO (`AutoRoutingPolicy`) | LAF (`LAFRoutingPolicy`) |
|---|---|---|
| Construcción del `router_manager` | Internamente, en `__init__` | Inyectado desde `generator.py` |
| Opcionalidad | Obligatorio | Opcional (`router_manager=None` válido) |
| Property `.enabled` | No la tiene (siempre activo implícito) | Sí, expone si el router fue inyectado |
| Invocaciones por pipeline | 4 (auto-route inicial, routing final, re-route por canvas, re-route por movimiento) | 1 (Fase 10) |

**Por qué la asimetría existe**: síntoma de **WISH-ARCH-001** (`LAFOptimizer` no cumple el contrato `LayoutOptimizer`). Cuando esa deuda se resuelva en una rama aparte, el constructor de `LAFRoutingPolicy` probablemente se uniformará con el de `AutoRoutingPolicy` (auto-construcción del `router_manager`, opcionalidad eliminada o convertida en parámetro explícito).

Ver `../auto/routing.md` para el lado AUTO de la simetría.

---

## Para profundizar

- **Algoritmo LAF**: `LAF.md`
- **Biblioteca de routing**: `../../routing/ROUTING.md`
- **Política simétrica en AUTO**: `../auto/routing.md`
- **WISH-ARCH-001 en TECHNICAL_DEBT**: `../../../../TECHNICAL_DEBT.md`
