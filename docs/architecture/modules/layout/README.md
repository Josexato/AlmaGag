# Módulo `layout/`

Capa responsable de **decidir dónde va cada elemento del diagrama** y **cuándo invocar el routing**. Lee un `Layout` con elementos y conexiones, escribe un `Layout` con coordenadas resueltas y paths calculados.

---

## Decisión arquitectónica: Escuela A pragmática

El módulo expone **dos algoritmos hermanos**, `auto/` y `laf/`, con la misma responsabilidad pero distintas garantías y costos. Comparten infraestructura básica (`layout.py`, `geometry.py`, `collision.py`, `graph_analysis.py`, `label_optimizer.py`, `sizing.py`, `container_calculator.py`) y delegan el cálculo de paths a la biblioteca compartida `AlmaGag/routing/`.

Cada algoritmo tiene su propia **política de routing** (`routing_policy.py`) que encapsula cuándo y cómo invoca al `ConnectionRouterManager`. Esto separa "qué algoritmo decide cuándo rutar" (responsabilidad del optimizer) de "cómo se calculan los paths" (responsabilidad de `routing/`).

```
AlmaGag/layout/
├── auto/                       # Algoritmo AUTO
│   ├── optimizer.py            (AutoLayoutOptimizer)
│   ├── positioner.py           (AutoLayoutPositioner)
│   └── routing_policy.py       (AutoRoutingPolicy)
├── laf/                        # Algoritmo LAF
│   ├── optimizer.py            (LAFOptimizer)
│   ├── routing_policy.py       (LAFRoutingPolicy)
│   └── ...                     (structure_analyzer, abstract_placer, etc.)
├── layout.py                   # Layout (Value Object inmutable)
├── geometry.py                 # GeometryCalculator
├── collision.py                # CollisionDetector
├── graph_analysis.py           # GraphAnalyzer
├── label_optimizer.py          # LabelPositionOptimizer
├── sizing.py                   # SizingCalculator
├── container_calculator.py     # ContainerCalculator
└── optimizer_base.py           # LayoutOptimizer (contrato base)
```

---

## ¿Cuándo usar AUTO vs LAF?

| Criterio | AUTO | LAF |
|---|---|---|
| Respeta coordenadas manuales (`x`/`y`) | **Sí** | No (las ignora) |
| Minimización de cruces estilo Sugiyama | No | **Sí** |
| Grafos densos con muchas conexiones | Aceptable | **Mejor** |
| Posters / dashboards (contenedores sin conexiones inter) | Apto (coords manuales) | **Apto** (grid auto desde 2026-06-18, ver BUGS-LAF-002) |
| Velocidad | Rápido | Más caro |

Resumen pragmático:
- **Si tenés un grafo y querés que se vea bien automáticamente** → LAF.
- **Si querés controlar posiciones manualmente** → AUTO.

Detalles en `auto/AUTO.md` y `laf/LAF.md`.

---

## Para profundizar

- **AUTO en detalle**: `auto/AUTO.md`
- **Política de routing de AUTO**: `auto/routing.md`
- **LAF en detalle**: `laf/LAF.md`
- **Política de routing de LAF**: `laf/routing.md`
- **Biblioteca de routing compartida**: `../routing/ROUTING.md`
- **Conceptos transversales (NdDp, NdPr, NdFn, TOI...)**: `../../../CONCEPTS.md`
- **Deuda técnica del módulo**: `../../../TECHNICAL_DEBT.md` (códigos `BUGS-*` y `WISH-*`)
