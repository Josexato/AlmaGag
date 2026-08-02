# Auditoría 3/3 — Docs raíz, guías y estados de tickets vs código

He auditado los documentos contra el código. Working tree limpio en master (`5fcae82`), `pyproject 3.5.0`, `AlmaGag/debug.py:32` devuelve `"3.5.0"`.

---

# Incongruencias verificadas (por gravedad)

## A. BLOQUEANTE — comandos documentados que fallan hoy

**A1. Flag muerto `--layout-algorithm=laf`** (argparse aborta con `SystemExit 2`)

> Realidad: `/home/user/AlmaGag/AlmaGag/main.py:68` → `choices=['select','auto','hier','legacy']`. `laf` NO es valor válido.

| Cita | |
|---|---|
| `docs/guides/QUICKSTART.md:117` | `almagag diagrama.gag --layout-algorithm=laf` |
| `docs/guides/QUICKSTART.md:226` | `` `--layout-algorithm {auto\|laf}` \| Selecciona algoritmo de layout `` |
| `docs/guides/QUICKSTART.md:235`, `:349` | idem (`--layout-algorithm=laf`) |
| `docs/guides/EXAMPLES.md:307`, `:341`, `:378`, `:405` | idem |
| `docs/INDEX.md:107`, `:113`, `:116`, `:119` | idem (bloque "Quick Start LAF") |

Fuera de la lista pedida, mismo defecto en `docs/architecture/modules/layout/laf/PROGRESS.md:284,371,385,398` y `COMPARISON.md:502`, y en `docs/RELEASE_v3.0.0.md:312,383` (este último es histórico fechado, aceptable).
**Clasificación: BLOQUEANTE / flag muerto.**

**A2. Ruta de ejemplos inexistente `docs/examples/`**

- `docs/guides/QUICKSTART.md:261,264,267,270,273` → `almagag docs/examples/01-iconos-registrados.gag`
- `docs/guides/EXAMPLES.md:442,448` → `for file in docs/examples/*.gag`

> Realidad: no existe `docs/examples/`. Los fuentes viven en `docs/diagrams/gags/` y **son `.sdjf`, no `.gag`** (`01-iconos-registrados.sdjf`, `03-conexiones.sdjf`, `08-auto-layout.sdjf`, `09-proportional-sizing.sdjf`, `10-hybrid-layout.sdjf`). Doble fallo: directorio + extensión.
> `docs/guides/EXAMPLES.md:7,33,52,77,103,…` cita todos los fuentes como `.gag` cuando solo 05, 12, 13, 15, 16, 17 lo son.
**Clasificación: BLOQUEANTE / ruta rota.**

---

## B. TECHNICAL_DEBT — estados falsos

**B3. Código de ticket DUPLICADO: dos `WISH-ARCH-002` distintos, con estados opuestos**

- `docs/TECHNICAL_DEBT.md:633` — `### WISH-ARCH-002: Convergencia a un solo algoritmo (auto-selección) 🚧 EN CURSO`
- `docs/TECHNICAL_DEBT.md:837` — `### WISH-ARCH-002: Eliminar layout_algorithm del Renderer ✅ RESUELTO`

Además `:833` remite "Registrado como **WISH-ARCH-002**" apuntando al segundo. El identificador no es único → cualquier referencia externa es ambigua.
**Clasificación: FALSO / colisión de identificador.**

**B4. `WISH-ARCH-002` (convergencia) marcado `🚧 EN CURSO`: todo su alcance declarado ya está en el código**

> Cita `TECHNICAL_DEBT.md:692-694`: «**Pendiente**: afinar el clasificador con más señales…; **opcional: portar las piezas de rescate ①/② desde `legacy` a `hier`**».

Realidad verificada, punto por punto:

| Alcance del ticket | Código |
|---|---|
| `select_strategy` decide desde el JSON | `AlmaGag/generator.py:14-70` (7 reglas, §O53 con WARNING de precedencia) |
| Default `--layout-algorithm=select` | `AlmaGag/main.py:66-74` |
| Motor único `LayoutEngine` que delega | `AlmaGag/layout/engine.py:15-18` |
| Reorg `layout/strategies/{auto,hier,legacy}` | `AlmaGag/layout/strategies/` (existe; `laf/` ya no está bajo `layout/`) |
| `layout_view` fuera del JSON | `main.py:75-85` (`--view` sólo por CLI) |
| ① bisección de layer-offset | `AlmaGag/layout/offset_optimizer.py` — **existe** |
| ② contracción SCC | `AlmaGag/layout/strategies/hier/scc.py` — **existe**, usado por `generator.py:84` |

El propio ticket ya marca ①②③④ como «✅ INTEGRADA» en la tabla `:708-711`, **contradiciendo su línea "Pendiente: opcional portar ①/②"** 14 líneas más arriba. Lo único realmente abierto es "afinar el clasificador", que es un deseo, no un trabajo en curso.
**Clasificación: ESTADO FALSO + CONTRADICCIÓN INTERNA.**

**B5. `WISH-LAYOUT-002` follow-up listado como backlog abierto: `near` y `avoid` YA están implementados**

> Cita `TECHNICAL_DEBT.md:1596`: «Baja | `WISH-LAYOUT-002` follow-up | **Implementar `constraints.near` y `constraints.avoid`** (v1 cerró `align`)».
> Y `:1216-1218`: «`near: [...]` — … **queda como follow-up**» / «`avoid: [...]` — …».

Realidad: `AlmaGag/layout/considerations.py:38` → `_KINDS = ('align', 'near', 'avoid')`; despacho en `:136-141` (`_apply_align` / `_apply_near` / `_apply_avoid`). Más aún, `near` fue promovido a **zona** (§N46): `considerations.py:173 cluster_near_groups()`, `:282 near_zone_boxes()`, `:81 areas_to_near_seeds()` (§O53), y afinidad de áreas §Q65 en `:196`. Tests: `tests/test_near_zones.py`, `tests/test_q65_zone_affinity.py`.
**Clasificación: ESTADO FALSO (ticket cerrado por el código, documentado como pendiente).**

**B6. Bloque "📊 Métricas" desactualizado y desmentido por el propio documento**

> Cita `TECHNICAL_DEBT.md:1574-1586`: tabla con filas sólo LAYOUT/LAF/ARCH/AUTO/DOCS/DIAG, «**Total 30**», «**Al 2026-06-18, 0 BUGS funcionales pendientes**».
> Cita `:1592`: «**Backlog activo (al 2026-06-19)**».

Realidad, en el mismo archivo: existen `BUGS-ROUT-001` (`:399`), `BUGS-TPL-001` (`:477`), `BUGS-VAL-001` (`:539`), `WISH-DRAW-001` (`:1536`) y `WISH-DRAW-002 🆕 ABIERTO` (`:586`, reportado 2026-08-02) — **ninguno aparece en la tabla de conteo ni en el backlog**. El backlog "activo" está congelado en junio y omite el único WISH abierto de agosto.
**Clasificación: OBSOLETO / conteo falso.**

**B7. Cabecera de fecha falsa**

> Cita `TECHNICAL_DEBT.md:5`: «**Última actualización**: 2026-06-15».
> Realidad: `:587` «**Reportado**: 2026-08-02»; commit `5fcae82` (2-ago) toca este archivo.
**Clasificación: OBSOLETO.**

**B8. La tabla de "Componentes" apunta a rutas que ya no existen**

> Cita `TECHNICAL_DEBT.md:21-22`: «`LAF` — Issues exclusivos del algoritmo LAF (`AlmaGag/layout/laf/`)», «`AUTO` — … (`AlmaGag/layout/auto/`)». Idem `:37` (`AlmaGag/layout/laf/optimizer.py`).
> Realidad: `AlmaGag/layout/strategies/legacy/` y `AlmaGag/layout/strategies/auto/`. El propio documento narra el rename en `:666-669`.
**Clasificación: OBSOLETO / auto-contradicción.**

**B9. `BUGS-VAL-001 ✅ RESUELTO` — el icono `firewall` sigue SIN detectarse (falso positivo R3 residual): CONFIRMADO HOY**

> Cita `TECHNICAL_DEBT.md:539` «BUGS-VAL-001 … ✅ RESUELTO»; `:560-563` «`_collect_icon_bboxes` reescrito para reconocer iconos custom»; `:580` la única «Limitación conocida» declarada es la del `connection.color` arbitrario — **el firewall no se menciona**.

Verificación ejecutada sobre `docs/diagrams/svgs/01-iconos-registrados.svg` (11 iconos declarados):

```
server1    -> children_bbox=(50.0,100.0,130.0,150.0)   OK
cloud1     -> children_bbox=(204.0,104.0,276.0,144.0)  OK
router1    -> children_bbox=(802.0,99.5,878.0,150.0)   OK
firewall1  -> transform_bbox=None  children_bbox=None  ← NO DETECTADO
_collect_icon_bboxes(root) = 9 bboxes  (faltan iconos)
```

Causa raíz confirmada en código:
- `AlmaGag/draw/icons/firewall.py:14` emite `g = dwg.g(id=element_id)` **sin `transform`**, y el `transform` real vive en el hijo `hex_group` (`firewall.py:28`) que **no tiene `id`** → `visual_quality.py:248 _is_icon_group_id('')` lo descarta.
- `visual_quality.py:161 _group_transform_bbox` no encuentra `translate(...)` en el `<g>` externo → `None`.
- `visual_quality.py:176 _group_children_bbox` sólo recorre `rect`/`polygon`/`circle`/`ellipse` (`:183-210`); el firewall se dibuja **sólo con `<path>`** (`firewall.py:58`) → `None`.

Impacto real acotado (importante): `validate_gag()` inyecta bboxes desde el optimizer (`visual_quality.py:590-601`), así que el camino de tests no se ve afectado. El falso positivo aparece por el camino `validate_svg(svg, icon_bboxes=None)` (`:504-505`), que es el que documenta su propia advertencia en `:494-497`.
**Clasificación: LIMITACIÓN NO DOCUMENTADA en un ticket cerrado. La nota sobre el falso positivo R3 con firewall SIGUE SIENDO CIERTA hoy.**

---

## C. docs/INDEX.md — desfasado ~5 versiones

**C10. Versión y fecha**
> `INDEX.md:3` y `:342`: «**Versión**: v3.3.0 (código)… **Actualizado**: 2026-02-28».
> Realidad: `pyproject.toml:7` `version = "3.5.0"`; `AlmaGag/debug.py:32` `"3.5.0"`; master al 2-ago-2026.
**Clasificación: OBSOLETO.**

**C11. Modelo mental "AUTO vs LAF" ya no existe**
> `INDEX.md:72` «**Para elegir entre AUTO y LAF** ✨ NUEVO v3.0»; `:87-122` «#### Usa AUTO cuando: … #### Usa LAF cuando: …».
> Realidad: no se elige algoritmo. `AlmaGag/generator.py:14` `select_strategy()`; `AlmaGag/main.py:69` `default='select'`. `docs/guides/LAYOUT-DECISION-GUIDE.md:3` ya lo dice correctamente («**ya no eliges un algoritmo**») — INDEX está en contradicción directa con la guía que enlaza.
**Clasificación: OBSOLETO / contradicción con doc hermano.**

**C12. Resumen de roadmap fósil**
> `INDEX.md:155-157`: «🔄 **En desarrollo**: v2.2 (collision avoidance) · 📅 **Planificado**: v2.3…, **v3.0 (temas)**».
> Realidad: el código va por 3.5.0; los tokens de tema §O57 están implementados (`AlmaGag/layout/theme.py`, invocado en `AlmaGag/generator.py:132-135 apply_theme(data)`).
**Clasificación: OBSOLETO.**

**C13. El árbol "Estructura de Documentación" (`:163-235`) lista archivos inexistentes y omite todo lo nuevo**

Listados que NO existen (verificado con `ls`):
- `docs/diagrams/gags/execution-flow.gag` (`:214`) y `docs/diagrams/svgs/execution-flow.svg` (`:230`)
- `01-iconos-registrados.gag`, `system-architecture.gag`, `roadmap-versions.gag`, `routing-architecture.gag`, `layout-optimization-flow.gag` (`:204-218`) — todos son `.sdjf`

Omitidos del índice (existen en disco):
- `docs/guides/SKILL-ALMAGAG.md`
- `docs/reviews/` completo (grupo-O, **grupo-P**, iteracion-3/4/5)
- `docs/CHANGELOG.md`, `docs/CHANGELOG-2026-01-10.md`, `docs/RELEASE_v3.0.0.md`, `docs/FLUJO_EJECUCION.md`
- `docs/spec/FORMATO_ARCHIVOS.md` (la spec **actualizada el 2-ago**, mtime `Aug 2 17:34`), `SDJF_UNION_TYPE.md`, `CONTAINER_GROUPING_STRATEGY.md`, `SVG_TO_BWT_SPEC.md`
- `docs/architecture/WISH-ARCH-004-el-mapa.md`, `SDJF_v2.1_IMPLEMENTATION_SUMMARY.md`
**Clasificación: ROTO + INCOMPLETO.**

**C14. Conteo de ejemplos inconsistente**
> `INDEX.md:20` y `:56` «10 ejemplos» vs `README.md:100` «Galeria con 12 ejemplos». `docs/guides/EXAMPLES.md` tiene 12 numerados (01–12).
**Clasificación: OBSOLETO (INDEX).**

**C15. Licencia sin especificar**
> `INDEX.md:331` «[Especificar licencia aquí]». Realidad: `LICENSE` (MIT) y `pyproject.toml:11` `license = {text = "MIT"}`.
**Clasificación: OBSOLETO.**

---

## D. docs/ROADMAP.md — habla en futuro de cosas ya hechas

**D16. El "Estado Actual" se detiene en v3.3 / feb-2026**
> `ROADMAP.md:3-4` «**Versión Actual**: v3.3.0… **Actualizado**: 2026-02-27»; `:683` «**Actualizado**: 2026-02-27».
> Realidad: 3.5.0. **No aparece nada** de: motor único / `select_strategy` (`generator.py:14`), `LayoutEngine` (`layout/engine.py`), estrategia `hier` (`layout/strategies/hier/`), vistas `areas|lanes|matrix` (`main.py:78`), `legacy` congelado, `considerations` (`layout/considerations.py`), `unions` (`layout/unions.py`), `templates/` (10 plantillas), zonas §N46/§P60 (`layout/strategies/auto/zones.py`), anticolisión global §P61 (`.../auto/anticollision.py`), semántica §Q63 (`layout/semantics.py`), Epifanía (`layout/epifania.py`).
**Clasificación: OBSOLETO ESTRUCTURAL.**

**D17. "Futuras Versiones" lista features ya entregadas**
> `ROADMAP.md:547-563` «### SDJF v3.0 (Q3-Q4 2026) — Objetivo: Interactividad y **temas** … `"theme": "cloud-architecture"`».
> Realidad: tema implementado hace tiempo — `AlmaGag/layout/theme.py`, `AlmaGag/generator.py:132-135`, contrato §O57 en `docs/guides/SKILL-ALMAGAG.md:26`.
> `ROADMAP.md:602-605` «**Clustering automático**: Detectar grupos y contenedores automáticamente» — realidad: `AlmaGag/layout/templates/` (architecture, flow, hub_and_spoke, dashboard, er, sequence, state, nested) + `layout_template: "auto"` (`validation/visual_quality.py:562 auto_apply_template`).
**Clasificación: FUTURO FALSO.**

**D18. `avoid_elements`: marcado entregado, y contradicho 150 líneas después — y NO existe en el código**
> `ROADMAP.md:364-369` (Fase 5, Entregables): «- [x] Implementación A* básica … - [x] **Propiedad `avoid_elements` funcional** - [x] Tests con casos complejos».
> `ROADMAP.md:519` (Criterios de Éxito): «- [ ] `avoid_elements=true` evita colisiones (>80%) - **Pospuesto para v2.2**».
> Realidad: **cero ocurrencias de `avoid_elements` en todo `AlmaGag/`**. El único obstacle-avoidance es incondicional vía visibility graph (`AlmaGag/routing/visibility_graph.py:535`, `orthogonal_router.py:28`) — no lo gobierna ninguna propiedad del SDJF, pese a que `docs/spec/SDJF_v2.1_PROPOSAL.md:107` la documenta con `default: true`.
**Clasificación: CHECKBOX FALSO + CONTRADICCIÓN INTERNA.**

**D19. Enlaces rotos**
> `ROADMAP.md:664` «Ver [CONTRIBUTING.md](CONTRIBUTING.md)» → no existe ni en `docs/` ni en raíz.
> `ROADMAP.md:99`, `:677-679` enlazan `docs/architecture/…` y `docs/spec/…` **desde dentro de `docs/`** → resuelven a `docs/docs/architecture/…`. Los 3 enlaces del bloque "Referencias" están rotos.
**Clasificación: ROTO.**

---

## E. docs/guides/ — afirmaciones desmentidas por el código

**E20. `CLI-REFERENCE.md`: dependencias inventadas**
> `CLI-REFERENCE.md:673` «Requiere `svgwrite`, **`networkx`**, **`scipy`**».
> Realidad: `pyproject.toml:26-28` → `dependencies = ["svgwrite>=1.4"]`; `requirements.txt` → `svgwrite>=1.4.3` (línea única). `grep "import networkx|import scipy"` sobre `AlmaGag/` → **0 resultados**.
**Clasificación: FALSO.**

**E21. `CLI-REFERENCE.md`: `--exportpng` descrito como cairosvg-only (§O58 ya invirtió el orden)**
> `CLI-REFERENCE.md:323-324` «**Requisitos**: Requiere `cairosvg` instalado»; `:600-613` sección «Error: "cairosvg no encontrado"».
> Realidad: `AlmaGag/debug.py:193` «…Chrome … disponible (en cualquier plataforma) y **cae a cairosvg si no**»; `debug.py:101 _find_chrome_executable()` (orden `ALMAGAG_CHROME` → PATH → rutas fijas → Chromium de Playwright, `:110-131`); `debug.py:218-223` prueba Chrome primero. Consistente con `docs/guides/SKILL-ALMAGAG.md:27` y `docs/reviews/iteracion-5/README.md:38`, que **sí** lo describen bien.
**Clasificación: OBSOLETO / contradicción entre guías.**

**E22. `CLI-REFERENCE.md`: versión en cabecera y pie**
> `:1` «Referencia Completa CLI - AlmaGag **v3.1**»; `:684` «**AlmaGag v3.1.0**». Realidad: 3.5.0. (El cuerpo del doc sí está al día — `select`/`legacy`/`--view` correctos; sólo el envoltorio miente.)
**Clasificación: OBSOLETO.**

**E23. `QUICKSTART.md`: presenta el modelo de dos algoritmos, retirado**
> `:95-132` «### Algoritmos de Layout ✨ NUEVO v3.0 — AlmaGag v3.0 ofrece **dos algoritmos**… #### 🔹 LAF (opcional)»; `:359-361` «Guía de decisión **AUTO vs LAF**»; `:375` «**Versión**: AlmaGag v3.0.0 + SDJF v3.0 · **Actualizado**: 2026-01-21».
> Realidad: `AlmaGag/main.py:66-74` (4 valores, default `select`) y `docs/guides/LAYOUT-DECISION-GUIDE.md:3` («**ya no eliges un algoritmo**»).
**Clasificación: OBSOLETO / contradicción con doc hermano.**

**E24. `QUICKSTART.md`: catálogo de iconos incompleto y warning falso**
> `:280-285` tabla con **4** tipos (`server`, `building`, `cloud`, `firewall`); `:342` «1. Usar un tipo disponible: `server`, `building`, `cloud`, `firewall`» dentro de la sección «Warning: "No se pudo dibujar **'router'**"».
> Realidad: `AlmaGag/draw/icons/` tiene **13** iconos: building, bwt, cloud, **computer**, **database**, **decision**, **diamond**, **document**, firewall, **laptop**, **router**, server, **user**. `router` YA se dibuja → el troubleshooting describe un warning que no ocurre. Confirmado en el fixture: `docs/diagrams/gags/01-iconos-registrados.sdjf` declara `['server','cloud','building','firewall','database','router','computer','laptop','document','user']`.
**Clasificación: FALSO.**

**E25. `EXAMPLES.md`: mismos dos errores, con el fixture desmintiéndolo**
> `:14` «✅ Tipos disponibles: `server`, `building`, `cloud`, `firewall`» — el fixture del propio ejemplo tiene 10 tipos.
> `:40` «⚠️ Tipos no existentes: `router`, `database`, `switch`, `laptop`» — realidad: `docs/diagrams/gags/02-iconos-no-registrados.sdjf` declara `['server','router','database','switch','laptop','building']` y de esos **sólo `switch`** carece de icono hoy (`AlmaGag/draw/icons/router.py`, `database.py`, `laptop.py` existen). El SVG publicado `02-iconos-no-registrados.svg` ya no demuestra lo que el texto afirma.
> `:45` cita el warning `[WARN] No se pudo dibujar 'router'` — no se emite.
> `:462-463` «**Actualizado**: 2026-01-21 · **Versión**: AlmaGag v3.0.0 + SDJF v3.0».
**Clasificación: FALSO / ejemplo que ya no ilustra su punto.**

**E26. `EXAMPLES.md`: la sección 12 documenta un flujo de Epifanía viejo**
> `:333-345` (aprox.) «El algoritmo LAF trabaja en **4 fases** secuenciales … `--layout-algorithm=laf --visualize-growth`».
> Realidad: `--visualize-growth` sigue siendo alias válido (`main.py:87`), pero el algoritmo `laf` no; y la Epifanía es agnóstica del motor desde §(ii-b) (`AlmaGag/layout/epifania.py::PhaseRecorder`, ver `TECHNICAL_DEBT.md:679-690`), con fases distintas a esas 4.
**Clasificación: OBSOLETO.**

> Nota: `docs/guides/LAYOUT-DECISION-GUIDE.md` y `docs/guides/SKILL-ALMAGAG.md` sí están sincronizados con el código (reglas de `select_strategy`, halo §O50 como geometría SVG 1.1 y no `paint-order`, PNG Chrome→cairosvg). El problema es que QUICKSTART/EXAMPLES/CLI-REFERENCE los **contradicen** desde el mismo directorio.

---

## F. docs/DIAGRAM_REVIEW.md — histórico presentado como vigente

**F27. Se autodefine "vivo" pero está congelado en junio con datos que ya no cuadran**
> `DIAGRAM_REVIEW.md:3` «**Checklist vivo** de problemas visuales detectados en los SVGs renderizados»; `:14` «**Última revisión:** 2026-06-15».
> Los 8 BUGS-DIAG están `[x] ✅ RESUELTO (2026-06-15)`; nada del review de iteraciones 3/4/5 ni de los grupos N/O/P/Q entró aquí — esa actividad vive en `docs/reviews/`, no referenciada desde este archivo.
**Clasificación: HISTÓRICO PRESENTADO COMO VIGENTE.**

**F28. Métricas de canvas desmentidas por el SVG actual**
> `DIAGRAM_REVIEW.md:12` «**Render actual:** AUTO …, canvas **2012×2072**»; `:41` «canvas 2012×2052 → **1600×2052**».
> Realidad: `docs/diagrams/svgs/05-arquitectura-gag.svg:2` → `width="1343.5" height="1204.5" viewBox="36.5,20,1343.5,1204.5"` (recorte §O51 mediante). Ninguna cifra del documento corresponde al render vigente.
**Clasificación: FALSO / dato caduco.**

**F29. Rutas de módulo obsoletas en los fixes documentados**
> `:24` «en `AlmaGag/draw/container.py` se separó la opacidad…» → real: `AlmaGag/draw/primitives/container.py`.
> `:54` «la constante `VERTICAL_SPACING = 240 px` en `layout/auto/positioner.py:293`» y `:71,:76` «`AlmaGag/layout/auto/positioner.py:990`» → real: `AlmaGag/layout/strategies/auto/positioner.py`.
**Clasificación: ROTO.**

**F30. Recomienda como acción futura un motor congelado**
> `:95` «BUGS-LAF-002 (dashboard layout) | **habilitaría usar LAF**, que tenía mejor sense visual en este caso».
> Realidad: `laf`→`legacy`, congelado y **nunca auto-elegido** (`AlmaGag/layout/engine.py:15`, `AlmaGag/layout/strategies/__init__.py:14`).
**Clasificación: RECOMENDACIÓN MUERTA.**

---

## G. README.md (raíz) — menor

El README es el documento más sano: versión correcta (`:3` v3.5.0 = `pyproject.toml:7`), nota §v3.x sobre `legacy` correcta (`:22-25`), tabla de flags coincidente con `main.py:66-99`, y `scripts/generate_docs.py` (`:112`) existe. Dos observaciones verificadas:

**G31. Instrucción de instalación ambigua/rompible**
> `README.md:9-12` (y `docs/guides/QUICKSTART.md:12-15`): «```bash \n cd AlmaGag \n pip install -e . \n```».
> Si el lector ya está en el repo (`/home/user/AlmaGag`), `cd AlmaGag` lo lleva al **paquete**, donde no hay `pyproject.toml` ni `setup.py` (verificado: ambos ausentes en `AlmaGag/`) → `pip install -e .` falla. Sólo funciona si se interpreta como "entrar al clon".
**Clasificación: AMBIGÜEDAD que produce fallo.**

**G32. Tabla de opciones incompleta respecto a `main.py`**
> `README.md:83-93` omite `--guide-lines` (`main.py:47`), `--dump-iterations` (`main.py:54`) y los cuatro `--centrality-*` (`main.py:100-127`).
**Clasificación: INCOMPLETO (no falso).**

---

## Resumen ejecutable

| Prioridad | Acción |
|---|---|
| 1 | Purgar `--layout-algorithm=laf` de QUICKSTART, EXAMPLES, INDEX (13 ocurrencias) → `legacy` o eliminar |
| 2 | Corregir `docs/examples/` → `docs/diagrams/gags/` y `.gag` → `.sdjf` (QUICKSTART, EXAMPLES) |
| 3 | Renumerar el `WISH-ARCH-002` duplicado y cerrar/reformular el "EN CURSO" |
| 4 | Cerrar el follow-up de `WISH-LAYOUT-002` (`near`/`avoid` implementados) y rehacer métricas/backlog de TECHNICAL_DEBT |
| 5 | Reescribir el "Estado Actual" de ROADMAP (falta todo v3.4/v3.5) y resolver el checkbox `avoid_elements` |
| 6 | Regenerar el árbol de `INDEX.md` + versión + sección AUTO/LAF |
| 7 | Añadir la limitación `firewall` (path-only) a `BUGS-VAL-001`, o extender `_group_children_bbox` a `<path>` |
| 8 | Marcar `DIAGRAM_REVIEW.md` como histórico (o purgar rutas/cifras caducas) |
