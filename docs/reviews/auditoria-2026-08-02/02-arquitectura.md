# Auditoría 2/3 — Docs de arquitectura vs código

# Auditoría de congruencia — docs de arquitectura vs código real (AlmaGag)

Árbol real verificado: `AlmaGag/layout/strategies/{auto,hier,legacy}/` + `layout/{engine,semantics,theme,unions,considerations,metrics,epifania,offset_optimizer}.py`. **No existe `AlmaGag/layout/auto/` ni `AlmaGag/layout/laf/`** (renombrados a `strategies/auto/` y `strategies/legacy/`), y **no existe `OPTIMIZERS` en ningún archivo del paquete**.

---

## GRAVEDAD 1 — Arquitectura descrita que ya no existe (falso)

**1.1 · El árbol de módulos de ARCHITECTURE.md describe un paquete que no existe**
`/home/user/AlmaGag/docs/architecture/ARCHITECTURE.md:906-927`
> `│   ├── auto/                        # Algoritmo AUTO` … `│   └── laf/                         # Algoritmo LAF` … `│       ├── visualizer/              #   WISH-ARCH-003: 1 archivo por fase`

Realidad: `AlmaGag/layout/strategies/auto/`, `AlmaGag/layout/strategies/legacy/` (y `strategies/hier/`, inexistente en el doc). El paquete `visualizer/` no existe: sus fases viven en `AlmaGag/layout/strategies/legacy/epifania/phase*.py`.
**Clasificación: falso** (todas las rutas del bloque `layout/` del árbol son inválidas).

**1.2 · La factoría `OPTIMIZERS` no existe; el despacho real es `LayoutEngine`**
`ARCHITECTURE.md:139-142`, repetido en `ARCHITECTURE.md:824-827`, `ARCHITECTURE.md:66-68`, y `docs/architecture/modules/layout/laf/LAF.md:139`
> `OPTIMIZERS = {'auto': AutoLayoutOptimizer, 'laf':  LAFOptimizer,}`

Realidad: `AlmaGag/generator.py:259-269` construye `LayoutEngine(...)`; el registro de estrategias es `_STRATEGIES` en `AlmaGag/layout/engine.py:36-40` con claves `auto|hier|legacy`. `grep -rn OPTIMIZERS AlmaGag/` no devuelve nada.
**Clasificación: falso.**

**1.3 · Import documentado que rompe**
`ARCHITECTURE.md:136`
> `from AlmaGag.layout.laf.optimizer import LAFOptimizer`

Realidad: `AlmaGag/layout/strategies/legacy/optimizer.py:LAFOptimizer` (`AlmaGag/layout/laf/` no existe).
**Clasificación: falso.**

**1.4 · `--layout-algorithm={auto|laf}` — valores que el CLI rechaza**
`ARCHITECTURE.md:14`, `ARCHITECTURE.md:120`, `ARCHITECTURE.md:1110`, `docs/FLUJO_EJECUCION.md:20`, `docs/architecture/modules/layout/auto/AUTO.md:91,109`, `docs/architecture/modules/layout/laf/COMPARISON.md:502`
> `- \`--layout-algorithm={auto|laf}\` - Selección de algoritmo (default: auto)`

Realidad: `AlmaGag/main.py:68` → `choices=['select', 'auto', 'hier', 'legacy'], default='select'`. `laf` es un valor **inválido**: cualquier comando copiado de los docs falla en argparse.
**Clasificación: falso** (documentación ejecutable rota).

**1.5 · "LAF" presentado como algoritmo elegible y recomendado; en el código está congelado y nunca se auto-elige**
`docs/CONCEPTS.md:22-23`; `ARCHITECTURE.md:13`; `docs/architecture/modules/layout/README.md:46-47`; `FLUJO_EJECUCION.md:48` ("Camino A: LAF Optimizer (Recomendado)") y `FLUJO_EJECUCION.md:53` ("Camino B: Auto Optimizer (Legacy)"); `COMPARISON.md:497`
> `**Si tenés un grafo y querés que se vea bien automáticamente** → LAF.`

Realidad: `AlmaGag/layout/engine.py:12-17` — *"`legacy` — motor histórico (ex-LAF), CONGELADO … no se elige nunca automáticamente"*; `DEFAULT_STRATEGY = 'auto'` (`engine.py:35`). AUTO es el motor principal, no el "legacy".
**Clasificación: falso** (la recomendación está exactamente invertida respecto del código).

**1.6 · La selección de estrategia (`select_strategy`) no está documentada en ningún doc auditado**
Realidad: `AlmaGag/generator.py:14-70` implementa `select_strategy(data, view)` con la política contains→auto, areas→hier, decision/diamond→hier, ciclo sin coords→hier, más los WARNINGs §O53. Ni ARCHITECTURE.md, ni FLUJO_EJECUCION.md, ni CONCEPTS.md mencionan `select_strategy`, `engine.py`, `_STRATEGIES`, ni la estrategia `hier`.
**Clasificación: faltante** (el mecanismo central de decisión del pipeline actual no está documentado).

---

## GRAVEDAD 2 — FLUJO_EJECUCION.md no describe el pipeline real

**2.1 · Pasos reales de `generate_diagram` ausentes por completo**
`docs/FLUJO_EJECUCION.md:11-57` describe: main → load_gag_file → Layout → elegir LAF/Auto.
Realidad `AlmaGag/generator.py`: `expand_unions` §H7 (:120-123) → `apply_embedded_semantics` §Q63 (:129-130) → `apply_theme` §O57 (:134-135) → `select_strategy` (:142) → templates sólo si no es hier (:151-168) → `unresolved_icon_types` §Q64 (:179-183) → `areas_to_near_seeds` §O53/§N46 (:238-243) → `extract_considerations` §④ (:244) → `LayoutEngine.optimize` (:283) → métricas `quality_counters`/`emission_metrics` §H6/§O52 (:300-320) → `optimizer.renderer.render` (:349).
Ninguno de estos pasos aparece en el doc.
**Clasificación: desactualizado / faltante.**

**2.2 · Las fases P60/P61 del optimizer AUTO no están documentadas**
Realidad: `AlmaGag/layout/strategies/auto/optimizer.py:239-253` (`apply_zone_banding`, §P60 banda operativa + zonas de servicio), `:173-178` (gate `zones_lack_author_coords`), `:574` (`route_zone_trunks`, troncales inter-zona), `:579-587` (`global_label_anticollision`, §P61), `:501-524` (re-ruteo final obstacle-aware con revert si empeora, H2/H3). Módulos `strategies/auto/zones.py` y `strategies/auto/anticollision.py` no se nombran en ningún doc auditado.
El doc de AUTO más específico (`docs/architecture/modules/layout/auto/AUTO.md:31-70`) sigue describiendo un pipeline de 5 fases que termina en "Fase 5 — Routing final".
**Clasificación: faltante.**

**2.3 · Rutas de archivo del doc que no existen (bloque completo de fases LAF)**
`FLUJO_EJECUCION.md:49,54,64,97,113,124,152,165,177,216,268,331,343,353`
> `**Archivo:** \`AlmaGag/layout/laf/structure_analyzer.py:StructureAnalyzer\``

Realidad: `AlmaGag/layout/strategies/legacy/structure_analyzer.py`; `laf/visualizer.py:GrowthVisualizer` (`:177`, `:268`) no existe — es el paquete `strategies/legacy/epifania/`.
**Clasificación: desactualizado** (14 rutas inválidas en un mismo documento).

**2.4 · Funciones citadas que no existen**
`FLUJO_EJECUCION.md:28` → `AlmaGag/main.py:load_gag_file()`; `FLUJO_EJECUCION.md:240` → `AlmaGag/generator.py:generate_svg()`.
Realidad: `grep -rn "load_gag_file\|def generate_svg" AlmaGag/` → sin resultados. La lectura del JSON es inline en `generator.py:111-112`; el render es `optimizer.renderer.render(...)` (`generator.py:349`).
**Clasificación: falso.**

**2.5 · Directorio de salida de debug equivocado**
`FLUJO_EJECUCION.md:270`, `FLUJO_EJECUCION.md:379`
> `**Genera 10 SVGs** en \`debug/growth/{diagram}/\``

Realidad: `AlmaGag/main.py:91` y `AlmaGag/layout/epifania.py:114` → `debug/epifania/<diagrama>/` (+ `index.html`). El flag además cambió de nombre: `--epifania` con alias `--debug-phases`/`--visualize-growth` (`main.py:86-88`).
**Clasificación: desactualizado.**

**2.6 · Cabecera de versión del doc**
`FLUJO_EJECUCION.md:437-438`
> `**Última actualización:** 2026-03-07` / `**Versión del sistema:** v3.3.0 (LAF 11 fases)`

Realidad: el HEAD del repo trae §P60/§P61/§Q63/§Q64/§Q65 (commits `6f459ad`, `c3e006e`, `97050ef`, `4be209c`, `0e68272`), posteriores a toda reestructuración a `strategies/`.
**Clasificación: desactualizado.**

---

## GRAVEDAD 3 — CONCEPTS.md: conceptos y rutas obsoletos

**3.1 · `--layout-algorithm` / LAF como algoritmo peer**
`docs/CONCEPTS.md:17-23` — sección "Algoritmos de layout" lista sólo **AUTO** y **LAF** con rutas `AlmaGag/layout/auto/optimizer.py` y `AlmaGag/layout/laf/optimizer.py`. Ambas rutas no existen; falta por completo `hier` (`AlmaGag/layout/strategies/hier/optimizer.py:HierLayoutOptimizer`, registrado en `engine.py:38`).
**Clasificación: falso + faltante.**

**3.2 · `AlmaGag/renderer.py` citado como archivo vivo**
`docs/CONCEPTS.md:36`
> `📍 \`AlmaGag/layout/laf/structure_analyzer.py\` · uso en \`AlmaGag/renderer.py\``

Realidad: `AlmaGag/renderer.py` no existe (fue eliminado en WISH-ARCH-002, hecho que el propio `ARCHITECTURE.md:29` documenta — contradicción interna entre docs).
**Clasificación: falso.**

**3.3 · Ruta del icono BWT**
`docs/CONCEPTS.md:50`
> `📍 \`AlmaGag/draw/bwt.py\``

Realidad: `AlmaGag/draw/icons/bwt.py` (movido por WISH-ARCH-003, documentado en `ARCHITECTURE.md:963`).
**Clasificación: desactualizado.**

**3.4 · Rutas de las routing policies**
`docs/CONCEPTS.md:53` → `AlmaGag/layout/auto/routing_policy.py` · `AlmaGag/layout/laf/routing_policy.py`.
Realidad: `AlmaGag/layout/strategies/auto/routing_policy.py:13` y `AlmaGag/layout/strategies/legacy/routing_policy.py:8`.
**Clasificación: desactualizado.**

**3.5 · Vocabulario nuevo del motor ausente del glosario**
El glosario no define ninguno de los conceptos que el código nombra hoy con marcador de sección: `unions` §H7 (`layout/unions.py`), `semantics`/`semantic_type` §Q63 (`layout/semantics.py`), `theme`/tokens §O57 (`layout/theme.py`), `considerations` align/near/avoid §④ (`layout/considerations.py`), zonas near §N46 y banding §P60 (`strategies/auto/zones.py`), anticolisión global §P61 (`strategies/auto/anticollision.py`), Epifanía (`layout/epifania.py`), métricas §H6/§O52 (`layout/metrics.py`).
**Clasificación: faltante.**

---

## GRAVEDAD 4 — Módulos reales ausentes de todos los árboles documentados

Verificado con grep sobre `docs/architecture/**`, `docs/FLUJO_EJECUCION.md`, `docs/CONCEPTS.md`: **cero menciones** de los siguientes archivos existentes.

| Módulo real | Mención en docs auditados |
|---|---|
| `AlmaGag/layout/engine.py` (`LayoutEngine`, registro de estrategias) | NINGUNA |
| `AlmaGag/layout/semantics.py` | NINGUNA |
| `AlmaGag/layout/theme.py` | NINGUNA |
| `AlmaGag/layout/unions.py` | NINGUNA |
| `AlmaGag/layout/considerations.py` | NINGUNA |
| `AlmaGag/layout/metrics.py` | NINGUNA |
| `AlmaGag/layout/epifania.py` | NINGUNA |
| `AlmaGag/layout/offset_optimizer.py` | NINGUNA |
| `AlmaGag/layout/strategies/auto/zones.py` | NINGUNA |
| `AlmaGag/layout/strategies/auto/anticollision.py` | NINGUNA |
| `AlmaGag/layout/strategies/auto/network.py` | NINGUNA |
| `AlmaGag/layout/strategies/hier/**` (12 archivos: arcs, areas, columns, labels, lanes, leveling, matrix, optimizer, routing, scc, shapes) | sólo alusiones en `WISH-ARCH-004-el-mapa.md:157-159` |
| `AlmaGag/draw/primitives/viewbox.py` | NINGUNA |
| `AlmaGag/draw/primitives/phase_areas.py` | NINGUNA |
| `AlmaGag/draw/icons/{decision,diamond}.py` | NINGUNA (el listado de iconos de `ARCHITECTURE.md:588-591` y `:880-883` no los incluye) |
| `AlmaGag/utils.py` | NINGUNA |

**Clasificación: faltante** (el árbol de `ARCHITECTURE.md:862-957` se presenta como "Estructura de Directorios (2026-06-23)", exhaustivo).

Inverso — documentados y ya inexistentes: `layout/auto/*`, `layout/laf/*` (todo el subárbol, `ARCHITECTURE.md:906-927`), `layout/laf/visualizer/` (`:920-925`), `AlmaGag/renderer.py`, `AlmaGag/draw/svg.py`, `AlmaGag/draw/bwt.py`.

---

## GRAVEDAD 5 — `laf/PROGRESS.md` y `laf/COMPARISON.md` presentados como vigentes

**5.1 · PROGRESS.md sin marca de histórico**
`docs/architecture/modules/layout/laf/PROGRESS.md:9`
> `**Estado**: Sprint 10 completado ✅`

y cierre en `PROGRESS.md:742`: `**Última actualización**: 2026-02-27 (Sprint 10 completado - NdPr expansion sin colisiones ✅)`. No hay banner de "congelado/histórico" pese a que `engine.py:16-17` declara el motor CONGELADO. El árbol interno que muestra (`PROGRESS.md:415-430`) describe `layout/laf_optimizer.py`, `layout/auto_positioner.py`, `draw/icons.py`, `draw/connections.py` — ninguno existe hoy.
**Clasificación: desactualizado / falso.**

**5.2 · COMPARISON.md recomienda LAF como default**
`COMPARISON.md:497`
> `**Recomendación**: Usar LAF como sistema por defecto para diagramas complejos (>10 elementos o con contenedores anidados).`

y `COMPARISON.md:502`: `**Herramientas**: AlmaGag CLI con flags \`--debug\` y \`--layout-algorithm=laf\`` (flag inválido, ver 1.4). Título `COMPARISON.md:1` "Sistema Actual vs LAF" — el "sistema actual" ahí es AUTO, que hoy **es** el motor principal.
**Clasificación: falso** (contradice `engine.py:35` `DEFAULT_STRATEGY = 'auto'`).

**5.3 · LAF.md se presenta como doc de un algoritmo activo**
`docs/architecture/modules/layout/laf/LAF.md:5` → `📍 AlmaGag/layout/laf/optimizer.py` (ruta inexistente); `LAF.md:118-121` lista `BUGS-LAF-001` como limitación **Activa** de un motor congelado; `LAF.md:139` repite la factoría `OPTIMIZERS` inexistente.
**Clasificación: desactualizado.**

**5.4 · `laf/routing.md` y `auto/routing.md` con rutas muertas y asimetría ya inexistente**
`docs/architecture/modules/layout/laf/routing.md:5` → `AlmaGag/layout/laf/routing_policy.py` (real: `strategies/legacy/routing_policy.py`); `laf/routing.md:56` afirma que `LAFRoutingPolicy` recibe el `router_manager` "inyectado desde `generator.py`" — `generator.py` ya no instancia routers (sólo `LayoutEngine`).
`docs/architecture/modules/layout/auto/routing.md:5` → `AlmaGag/layout/auto/routing_policy.py` (real: `strategies/auto/routing_policy.py`); `auto/routing.md:44-49` lista 4 invocaciones sin las de §P60 (`route_zone_trunks`, `optimizer.py:574`) ni el re-ruteo con revert (`optimizer.py:505-524`).
**Clasificación: desactualizado.**

**5.5 · `modules/layout/README.md`: el árbol y la guía de elección**
`docs/architecture/modules/layout/README.md:9`
> `El módulo expone **dos algoritmos hermanos**, \`auto/\` y \`laf/\``

y el árbol `README.md:14-31` (mismas rutas muertas), más la tabla de decisión `README.md:35-49` que presupone que el usuario elige el algoritmo. Realidad: `generator.py:14-19` — *"El usuario normalmente NO elige algoritmo"*; son tres estrategias (`auto`/`hier`/`legacy`), no dos hermanas.
**Clasificación: falso.**

**5.6 · `modules/routing/ROUTING.md`**
`ROUTING.md:5` ("AUTO y LAF la usan vía sus respectivas `routing_policy.py`") y `ROUTING.md:29` ("No emite SVG (eso es `renderer.py`)") — `AlmaGag/renderer.py` no existe; falta `hier` (`strategies/hier/routing.py`).
**Clasificación: desactualizado.**

---

## GRAVEDAD 6 — Links cruzados rotos (verificados con `ls`)

| Doc:línea | Target | Estado |
|---|---|---|
| `laf/LAF.md:169` | `../../../../../AlmaGag/layout/laf/README.md` | **MISSING** — el archivo se movió a `AlmaGag/layout/strategies/legacy/README.md` |
| `laf/LAF.md:34` | `laf/README.md` | **MISSING** (mismo caso) |
| `laf/PROGRESS.md:513` | `docs/LAF-COMPARISON.md` | **MISSING** (es `modules/layout/laf/COMPARISON.md`) |
| `laf/PROGRESS.md:514` | `C:\Users\José Cáceres\.claude\plans\nested-enchanting-backus.md` | **MISSING** — ruta local absoluta de otra máquina |
| `laf/PROGRESS.md:515,554,569` | `AlmaGag/layout/laf/README.md` | **MISSING** |
| `laf/PROGRESS.md:436,570` | `LAF-PROGRESS.md` / `docs/LAF-PROGRESS.md` | **MISSING** |
| `laf/PROGRESS.md:551,566` | `explicacion_fase2_topology.md` | **MISSING** |
| `laf/PROGRESS.md:552,567` | `explicacion_fase3_abstract.md` | **MISSING** |

**Clasificación: link roto** (8 targets distintos, todos concentrados en `laf/PROGRESS.md` y `laf/LAF.md`).

---

## GRAVEDAD 7 — Datos numéricos y de test desincronizados

**7.1 · Constantes de `config.py` inventadas**
`ARCHITECTURE.md:192-194`
> `DEFAULT_CANVAS_WIDTH = 1400` / `DEFAULT_CANVAS_HEIGHT = 900`

Realidad `AlmaGag/config.py:2-3`: los nombres son `WIDTH` / `HEIGHT` (así los importa `generator.py:6`). `DEFAULT_CANVAS_WIDTH` sólo existe como alias local en `strategies/legacy/optimizer.py:38`. Además faltan del doc las constantes §O56 de escala tipográfica (`FONT_SIZE_NODE/CONNECTION/ZONE`, `config.py:11-14`).
**Clasificación: falso.**

**7.2 · Conteo de líneas de `generator.py`**
`ARCHITECTURE.md:55` ("generator.py (190 líneas) — Orquestador delgado"), `:132` ("187 líneas"), `:867`, `:966`.
Realidad: `wc -l AlmaGag/generator.py` → **360 líneas**.
**Clasificación: desactualizado.**

**7.3 · Conteo de líneas del optimizer AUTO**
`ARCHITECTURE.md:907` → `AutoLayoutOptimizer (1171 líneas)`. Realidad: **1506** (`AlmaGag/layout/strategies/auto/optimizer.py`).
**Clasificación: desactualizado.**

**7.4 · Inventario de tests**
`ARCHITECTURE.md:1170-1185`
> `**Total: 70 tests passed** (al 2026-06-23)` con 9 archivos listados.

Realidad: `tests/` contiene ~55+ archivos `test_*.py`, incluidos `test_p60_service_zones.py`, `test_p61_global_anticollision.py`, `test_q63_semantics.py`, `test_q65_zone_affinity.py`, `test_strategy_selection.py`, `test_hier_*.py` (8), `test_scc.py`, `test_determinism.py`, `test_epifania_markers.py` — ninguno documentado. Además `test_visual_quality.py`, listado en `:1178`, **no existe** en `tests/`.
**Clasificación: desactualizado + falso** (un archivo listado no existe).

---

## Nota: documento que sí es congruente

`docs/architecture/WISH-ARCH-004-el-mapa.md` está correctamente marcado (`:3` `**Estado**: 🟡 Diseño (en revisión — NO implementado)`) y sus afirmaciones verifican: la fase 1 marcada ✅ (`:165`) corresponde a la bandera real en `AlmaGag/layout/strategies/hier/areas.py:4-10`; la fase 2 ("generalizar `lanes` a `axis`") sigue sin implementar — `grep -n axis AlmaGag/layout/strategies/hier/lanes.py` no devuelve nada. Única salvedad menor: cita rutas como `hier/areas.py` / `hier/lanes.py` / `hier/matrix.py` (`:157-159`) sin el prefijo real `layout/strategies/`.
