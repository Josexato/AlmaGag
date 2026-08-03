# Arquitectura de AlmaGag (v3.5)

**Actualizado**: 2026-08-02 · verificado contra el código en master.
Versiones anteriores: `history/ARCHITECTURE-2026-06-23.md` (pre-reorg
`strategies/`) y `history/FLUJO_EJECUCION-v3.3.md`.

> Regla de oro: **el código gana a este documento.** Ante duda:
> `AlmaGag/generator.py`, `AlmaGag/layout/engine.py`.

---

## La idea en una frase

Un archivo JSON (`.sdjf`/`.gag`) declara **qué es** el diagrama (nodos,
conexiones, semántica, agrupación); el motor decide **toda la geometría** y
emite un SVG autocontenido. El usuario no elige algoritmo: la estrategia se
selecciona desde el propio JSON (§R: el autor declara intención, el motor
decide forma).

## El pipeline (generator.py::generate_diagram)

```
JSON ──▶ expand_unions §H7        (unions → nodo de barra + aristas)
     ──▶ apply_embedded_semantics §Q63  (mapa `semantics` del archivo, con WARNING)
     ──▶ apply_theme §O57         (tokens de color → hex, pre-proceso)
     ──▶ select_strategy          (¡la decisión central! ver tabla)
     ──▶ layout_template          (sólo si la estrategia no es hier)
     ──▶ unresolved_icon_types §Q64  (inventario de BWT)
     ──▶ areas_to_near_seeds §O53 (areas sobreviven en AUTO como zonas near)
     ──▶ LayoutEngine.optimize    (la estrategia hace el trabajo)
     ──▶ quality_counters §H6 + emission_metrics §O52
         └─ línea `[motor] cruces=… arista×nodo=… labels=… tinta=… aspecto=…`
     ──▶ renderer de la estrategia ──▶ SVG (finalize: crop §O51 + halo §O50)
```

### select_strategy (generator.py) — las 7 reglas, en orden, la primera gana

```
1. --view ≠ auto   → hier      5. decision/diamond → hier
2. considerations  → auto      6. ciclo sin x/y    → hier
3. contains        → auto      7. resto            → auto
4. areas           → hier
```

§O53: cuando una señal anula a otra, un WARNING la NOMBRA.

## Las tres estrategias (layout/engine.py::_STRATEGIES)

| Estrategia | Rol | Módulos |
|---|---|---|
| `auto` | **Principal.** Sugiyama-like + contenedores + zonas + anticolisión | `layout/strategies/auto/` |
| `hier` | Flujo dirigido por niveles; vistas `areas`/`lanes`/`matrix`; SCC | `layout/strategies/hier/` (12 módulos) |
| `legacy` | Ex-LAF, **CONGELADO**, nunca se auto-elige; sólo debug | `layout/strategies/legacy/` |

### El optimizer AUTO por dentro (strategies/auto/optimizer.py)

Orden de fases (los números son los pasos del código):

1. **Posicionamiento** — `positioner.py`: contenedores bottom-up (§P59:
   celdas al tamaño REAL del hijo), niveles topológicos, barycenter.
   `network.py` (§N45): topología de red → hub-and-spoke.
2. **Contenedores** — dimensiones + centrado con etiquetas + redistribución.
3. **Zonas** — `zones.py` (§P60/§Q65): banda operativa / periferia de
   servicio por `direction` inter-zona, troncales ortogonales
   (`_zone_trunk`, recomputadas en cada re-ruteo), afinidad declarada.
   `considerations.py` (§N46): near como zona por construcción.
4. **Canvas + ruteo** — `routing_policy.py` → `AlmaGag/routing/` (puertos
   por sectores, visibility graph, separación de paralelos).
5. **Loop de optimización** — reubicar etiquetas / mover elementos /
   expandir canvas; rescate ① compactación (`offset_optimizer.py`).
6. **Etapas finales** — normalizar, re-ruteo obstacle-aware (H2/H3),
   re-aplicar troncales §P60, y **anticolisión global §P61**
   (`anticollision.py`): última etapa, sólo mueve etiquetas, con medición
   veraz (`_measure_stored_labels`).

## Módulos transversales (layout/)

| Módulo | Qué hace |
|---|---|
| `engine.py` | `LayoutEngine`: despacho de estrategias (reemplazó a la factoría `OPTIMIZERS`) |
| `layout.py` | El dato central; `copy()` preserva `CONTEXT_ATTRS` (BUGS-ARCH-001) |
| `semantics.py` §Q63 | mapa `semantics` embebido → `semantic_type` (nunca vocabulario en el motor) |
| `theme.py` §O57 | tokens de color |
| `unions.py` §H7 | genealogías |
| `considerations.py` | align/near/avoid; near→zona §N46; afinidad de áreas §Q65 |
| `metrics.py` §H6/§O52 | cruces, arista×nodo, labels, tinta, aspecto |
| `collision.py` + `geometry.py` | detector de colisiones (canónico en heurísticas; VERAZ en la etapa final) |
| `label_optimizer.py` | optimizador de etiquetas del renderer (elementos libres + conexiones; recibe las contenidas como obstáculos §P61) |
| `templates/` | 10 plantillas (architecture, flow, hub_and_spoke, dashboard, er, sequence, state…) + auto-detección |
| `epifania.py` | flipbook por fase (`--epifania`), agnóstico del motor |

## Dibujo, ruteo y validación

- **`draw/icons/`** — 13 built-ins + BWT rotulado (§Q64) + alias §O55
  (`inet`/`wan`/`internet`→cloud) + embebidos (resuelven `currentColor`,
  BUGS-DRAW-002). **El catálogo de dominio vive en el skill, no aquí.**
- **`draw/primitives/`** — svg.py (halo §O50, leyenda §N48, canvas),
  viewbox.py (crop §O51), container.py, phase_areas.py, callout.py.
- **`routing/`** — router_manager + straight/orthogonal/bezier/arc/manual,
  port_assignment (12 sectores), visibility_graph (obstacle-aware).
- **`validation/visual_quality.py`** — audit del SVG emitido (R1 etiqueta
  sobre icono, R2 solapes, R3 colgantes); iconos `<path>`-only soportados
  (BUGS-VAL-003).

## Invariantes que protegen la calidad

1. **Guarda anti-regresión**: `scripts/measure_fixtures.py` — una línea
   `[motor]` por fixture; el patrón es *probar → medir → revertir si
   empeora*. Aborta ruidoso si mide 0.
2. **Un criterio por commit** con test de regresión y verificación visual
   PNG (`--exportpng`, §O58).
3. **Nada de vocabulario de dominio en el motor** (§Q63/§Q64): iconos,
   clases semánticas y keywords viajan en el archivo o en el skill —
   vigilado por `tests/test_q63_semantics.py::test_engine_ships_no_vocabulary`.
4. **Determinismo**: mismo archivo → mismo SVG (tests de doble corrida).

## Deuda y diseño abierto

`docs/TECHNICAL_DEBT.md` (tickets BUGS-*/WISH-*; métricas por grep) ·
`docs/architecture/WISH-ARCH-004-el-mapa.md` (separación mapa/vista, en
diseño) · WISH-LAYOUT-008 (unificar los 3 sistemas de etiquetas, iteración
6) · WISH-DRAW-002 (flujos resaltados).

## Historia

La evolución completa (por qué LAF existe, la convergencia WISH-ARCH-002,
la reorg `strategies/`) está en `EVOLUTION.md` y `history/`. Los docs del
motor congelado viven en `modules/layout/laf/` con banner de HISTÓRICO.
