# Deuda Técnica — AlmaGag

Este documento registra problemas conocidos y áreas de mejora del proyecto.

**Última actualización**: 2026-08-02 (auditoría de congruencia docs⇄código)

---

## Convención de códigos

Cada entrada tiene un código con estructura uniforme `<CATEGORÍA>-<COMPONENTE>-<NNN>`:

### Categorías

- **`BUGS`** — Cosas que no funcionan como deberían. Hay un comportamiento esperado y la implementación lo viola.
- **`WISH`** — Cosas que se desea crear o mejorar. El sistema funciona, pero se podría hacer mejor.

### Componentes

- **`LAYOUT`** — Issues transversales del módulo `AlmaGag/layout/`.
- **`LAF`** — (histórico) issues del ex-algoritmo LAF, hoy congelado como `AlmaGag/layout/strategies/legacy/`.
- **`AUTO`** — Issues exclusivos de la estrategia AUTO (`AlmaGag/layout/strategies/auto/`).
- **`ROUT`** — Issues del módulo de routing (`AlmaGag/routing/`): cálculo de paths, port assignment, visibility graph, simplificación.
- **`TPL`** — Issues del módulo de templates (`AlmaGag/layout/templates/`): detección semántica, scorers, aplicación de patrones, calibración del clasificador.
- **`VAL`** — Issues del módulo de validación (`AlmaGag/validation/`): reglas de calidad visual (R1/R2/R3) y sus heurísticas.
- **`DRAW`** — Issues del módulo de dibujo (`AlmaGag/draw/`): nuevos tipos de iconos/shapes, primitivas SVG, gradientes, markers.
- **`ARCH`** — Issues arquitecturales del sistema (acoplamientos, contratos, extensibilidad).
- **`DOCS`** — Documentación que quedó desincronizada del código o del estado actual del proyecto.
- **`DIAG`** — Problemas visuales en los SVG renderizados. Viven en `docs/DIAGRAM_REVIEW.md`, no aquí.

### ⚠️ Importante: distinción con `LAF_PHASE_N_...`

El código de runtime usa identificadores como `LAF_PHASE_6_NDPR_EXPANDED` para nombrar las fases del pipeline durante el debug (`_dump_layout()`). Estos **no son** los códigos `BUGS-LAF-NNN` de este documento. La distinción:

| Patrón | Dónde vive | Qué identifica |
|---|---|---|
| `LAF_PHASE_N_NOMBRE` | `AlmaGag/layout/laf/optimizer.py` | Fase del pipeline LAF (para snapshots de debug) |
| `BUGS-LAF-NNN` / `WISH-LAF-NNN` | Este documento | Issue específico a corregir |

---

## Diseños abiertos (documentos aparte)

- **WISH-ARCH-004 — "El Mapa"** (🟡 diseño en revisión): separar limpiamente
  **contenedor / carril / ámbito** como capas componibles (hoy `areas`/`lanes`
  son vistas excluyentes y el `areas` §I27 es en realidad un contenedor mal
  nombrado). Introduce el **ámbito de forma arbitraria** (terreno). Ver
  `docs/architecture/WISH-ARCH-004-el-mapa.md`. Pendiente: decisiones de §9.

---

## 🐛 BUGS

> **Tanda 2026-08-02 — auditoría de congruencia docs⇄código** (tres barridos
> completos: spec, arquitectura, docs raíz/guías/estados + revisión
> arquitectónica del pipeline). Todos los hallazgos siguientes están
> VERIFICADOS contra el código en master v3.5.0. Tickets: BUGS-DOCS-001…006,
> BUGS-VAL-003, BUGS-ARCH-001, BUGS-AUTO-008/009, BUGS-DRAW-001/002,
> WISH-LAYOUT-008 (en la sección WISH).

### BUGS-DOCS-001: La spec de formato omite secciones enteras y miente en defaults ✅ RESUELTO (2026-08-02)
**Componente**: `docs/spec/FORMATO_ARCHIVOS.md`
**Reportado**: 2026-08-02 (auditoría)

La spec declara «si algo no está aquí, no existe en el formato» y sin embargo:

**No documenta** (existen y tienen tests): sección `semantics` §Q63
(`layout/semantics.py`), sección `theme` §O57 (`layout/theme.py`),
`type: "area"` + macro-layout banda/periferia §P59/§P60/§Q65
(`strategies/auto/zones.py`), sección `unions` §H7 (`layout/unions.py`),
campo `callout` (override de `draw/primitives/callout.py`), `width`/`height`
explícitos (ganan a `hp`/`wp`, `sizing.py:37`), alias `inet`/`wan`/`internet`
→ `cloud` (§O55), clases CUSTOM de `semantic_type` + leyenda ≥3 (§N48),
`waypoints`/`routing_type` a nivel raíz (compat v1.5,
`router_manager.py:135-147`), `label` en `near` (§N46) y 10 de los 13 flags
del CLI.

**Miente en defaults medibles**: `corner_radius` real = 25 no 0
(`config.py:91`); `preference` real = `auto` por eje dominante, no
`horizontal` (`orthogonal_router.py:80,258`); «`areas` sólo con hier» —
falso en ambas direcciones (`generator.py:57` auto-selección;
`areas_to_near_seeds` §O53 en AUTO); contenedor con `type` desconocido cae a
`building`/rect, no a banana (`container.py:219,240`); `role: "actor"`
inerte (ningún template lo lee); `elements`/`connections` marcados
obligatorios sin validación real; «ids duplicados: sólo uno se dibuja» —
falso, se dibujan ambos superpuestos; «`.gag` = icons al inicio» — la
extensión y posición son irrelevantes (`generator.py:110-115`).

**Fix aplicado**: los 20 hallazgos corregidos en el mismo día — secciones
nuevas (`theme` §O57, `semantics` §Q63, zonas §P59/§P60/§Q65, `unions`
§H7, alias §O55, clases custom + leyenda, waypoints raíz, apéndice CLI,
`width`/`height`, `callout`) y verdades restauradas (corner_radius 25,
preference auto, areas auto-enrutadas, contenedor→building/rect, actor
reservado-inerte, connections opcional, ids duplicados se dibujan ambos,
extensión irrelevante). Árbol-resumen final con todas las secciones
top-level.

---

### BUGS-DOCS-002: Los docs de arquitectura describen un paquete que no existe ✅ RESUELTO (2026-08-02)
**Componente**: `docs/architecture/ARCHITECTURE.md`, `docs/architecture/modules/**`
**Reportado**: 2026-08-02 (auditoría)

- El árbol «Estructura de Directorios» (`ARCHITECTURE.md:862-957`) lista
  `layout/auto/`, `layout/laf/`, `laf/visualizer/`, `renderer.py`,
  `draw/svg.py`, `draw/bwt.py` — ninguno existe; faltan `strategies/{auto,
  hier,legacy}/`, `engine.py`, `zones.py`, `anticollision.py`,
  `semantics.py`, `theme.py`, `unions.py`, `considerations.py`,
  `metrics.py`, `epifania.py`, `viewbox.py` y los 12 módulos de `hier/`.
- La factoría `OPTIMIZERS` citada 4 veces no existe: el despacho real es
  `LayoutEngine` + `_STRATEGIES` (`engine.py:36-40`); el import de ejemplo
  (`from AlmaGag.layout.laf.optimizer import`) rompe.
- `modules/layout/laf/{PROGRESS,COMPARISON,LAF}.md` recomiendan LAF como
  default — **invertido**: `legacy` está congelado y nunca se auto-elige
  (`engine.py:12-17`, `DEFAULT_STRATEGY='auto'`).
- `select_strategy` — el mecanismo central de decisión — no aparece en
  NINGÚN doc de arquitectura; la estrategia `hier` tampoco.
- 8 links rotos (concentrados en `laf/PROGRESS.md` y `laf/LAF.md`, incluida
  una ruta absoluta `C:\Users\…` de otra máquina); conteos falsos
  (`generator.py` «190 líneas» → 360; «70 tests» → ~435;
  `test_visual_quality.py` listado y no existe; constantes
  `DEFAULT_CANVAS_WIDTH` inventadas — reales `WIDTH`/`HEIGHT`).

**Fix aplicado**: `ARCHITECTURE.md` REESCRITO desde el código (pipeline
real con select_strategy/LayoutEngine/estrategias, optimizer AUTO por
fases, módulos transversales, invariantes de calidad); el anterior
archivado en `history/ARCHITECTURE-2026-06-23.md`. Los docs de `laf/`
quedan como HISTÓRICO con banner (por diseño); `modules/layout/README`,
`auto/*` y `routing/ROUTING` conservan banner DESACTUALIZADO — su
refresh fino es mantenimiento continuo, no deuda.

---

### BUGS-DOCS-003: FLUJO_EJECUCION.md narra un pipeline que ya no existe ✅ RESUELTO (2026-08-02)
**Componente**: `docs/FLUJO_EJECUCION.md`
**Reportado**: 2026-08-02 (auditoría)

14 rutas de archivo inválidas (`layout/laf/*`), funciones citadas que no
existen (`main.py:load_gag_file()`, `generator.py:generate_svg()`),
directorio de debug equivocado (`debug/growth/` → real `debug/epifania/`),
y CERO mención de los pasos reales de `generate_diagram`: `expand_unions`
§H7 → `apply_embedded_semantics` §Q63 → `apply_theme` §O57 →
`select_strategy` → templates → `areas_to_near_seeds` §O53 → banding §P60 →
anticolisión global §P61 → re-ruteo final → métricas §H6/§O52. Cabecera
declara «v3.3.0 (LAF 11 fases)».

**Fix aplicado**: archivado como
`architecture/history/FLUJO_EJECUCION-v3.3.md` (decisión del autor,
opción A); el pipeline vigente vive en el `ARCHITECTURE.md` nuevo.

---

### BUGS-DOCS-004: CONCEPTS.md, INDEX.md y ROADMAP.md fósiles (v3.3/feb-2026) ✅ RESUELTO (2026-08-02)
**Componente**: `docs/CONCEPTS.md`, `docs/INDEX.md`, `docs/ROADMAP.md`
**Reportado**: 2026-08-02 (auditoría)

- CONCEPTS: sólo AUTO y LAF como algoritmos (rutas muertas), cita
  `AlmaGag/renderer.py` (eliminado en WISH-ARCH-002 — contradicción entre
  docs), `draw/bwt.py` (movido), y el glosario no define nada del motor
  actual (unions, semantics, theme, considerations, zonas near, banding,
  Epifanía, métricas).
- INDEX: «v3.3.0 · 2026-02-28»; guía «AUTO vs LAF» contradiciendo a
  `LAYOUT-DECISION-GUIDE.md` («ya no eliges algoritmo»); árbol con archivos
  inexistentes (`execution-flow.gag`, extensiones `.gag` que son `.sdjf`) y
  sin nada de `reviews/`, `SKILL-ALMAGAG.md`, spec; «[Especificar licencia
  aquí]» cuando `LICENSE` MIT existe.
- ROADMAP: «Versión actual v3.3.0»; anuncia como futuro lo ya entregado
  (temas §O57, clustering/templates); checkbox `avoid_elements` marcado
  entregado, contradicho 150 líneas después, y **cero ocurrencias en el
  código**; 4 links rotos (`CONTRIBUTING.md`, rutas `docs/docs/…`).

**Fix aplicado (completo)**: INDEX.md refrescado (v3.5, motor único, árbol
real, licencia MIT); **ROADMAP.md REESCRITO** (estado v3.5 por capas,
iteración 6 con orden y tickets, mediano plazo, sección «Descartado» —
avoid_elements y LAF elegible — y el proceso de trabajo); **CONCEPTS.md
REESCRITO** (glosario v3.5 en 4 bloques: formato, motor, dibujo/emisión,
calidad/proceso, con 📍 rutas reales). Cuerpos viejos archivados en
`architecture/history/{ROADMAP,CONCEPTS}-2026-02.md`. `avoid_elements`
DESCARTADA con banner definitivo en `SDJF_v2.1_PROPOSAL.md`.

---

### BUGS-DOCS-005: Guías con comandos que fallan hoy (QUICKSTART/EXAMPLES/CLI-REFERENCE/INDEX) ✅ RESUELTO (2026-08-02)
**Componente**: `docs/guides/QUICKSTART.md`, `docs/guides/EXAMPLES.md`, `docs/guides/CLI-REFERENCE.md`, `docs/INDEX.md`, `README.md`
**Reportado**: 2026-08-02 (auditoría)

- `--layout-algorithm=laf` en **13 lugares** — argparse lo rechaza
  (`main.py:68`: choices `select|auto|hier|legacy`).
- `docs/examples/*.gag` no existe: es `docs/diagrams/gags/` y los fuentes
  citados son `.sdjf` (doble fallo, 7 comandos).
- QUICKSTART/EXAMPLES: catálogo de «4 tipos» de icono (reales: 13) y
  troubleshooting de un warning `'router'` que ya no ocurre (router.py
  existe); EXAMPLES afirma que `router`/`database`/`laptop` «no existen».
- CLI-REFERENCE: dependencias inventadas (`networkx`, `scipy` — la única
  real es `svgwrite`); `--exportpng` descrito cairosvg-only (§O58 prueba
  Chrome primero); cabecera «v3.1».
- QUICKSTART presenta el modelo de dos algoritmos retirado; `cd AlmaGag` +
  `pip install -e .` falla si ya estás en el clon (el paquete no tiene
  pyproject); README omite 6 flags reales.

**Fix aplicado**: 0 ocurrencias de `--layout-algorithm=laf` fuera de docs
históricos con banner; rutas/extensiones de ejemplos corregidas y
verificadas contra disco; catálogo de 13 iconos + alias + BWT rotulado;
deps reales (svgwrite); `--exportpng` según §O58; secciones 11/12 de
EXAMPLES reescritas (legacy congelado, Epifanía real); instalación
desambiguada; comparación AUTO-vs-LAF reemplazada por las reglas de
`select_strategy`.

---

### BUGS-DOCS-006: TECHNICAL_DEBT.md auto-inconsistente (este archivo) ✅ RESUELTO (2026-08-02)
**Componente**: `docs/TECHNICAL_DEBT.md`, `docs/DIAGRAM_REVIEW.md`
**Reportado**: 2026-08-02 (auditoría)

- **Identificador duplicado**: hay DOS `WISH-ARCH-002` («Convergencia a un
  solo algoritmo 🚧 EN CURSO» y «Eliminar layout_algorithm del Renderer ✅
  RESUELTO») — toda referencia externa es ambigua. Renumerar uno y dejar
  nota de mapeo.
- El `WISH-ARCH-002` «EN CURSO» tiene TODO su alcance implementado
  (`select_strategy`, `LayoutEngine`, reorg `strategies/`, ①
  `offset_optimizer.py`, ② `hier/scc.py`) y se contradice: la tabla marca
  ①②③④ «INTEGRADA» y el texto dice «pendiente portar ①/②». Cerrarlo dejando
  «afinar clasificador» como wish aparte si se desea.
- `WISH-LAYOUT-002` follow-up pide implementar `near`/`avoid` — implementados
  hace tiempo (`considerations.py:38 _KINDS`) y `near` promovido a zona §N46.
- Bloque «📊 Métricas» y «Backlog activo» congelados en junio: no cuentan
  BUGS-ROUT/TPL/VAL ni WISH-DRAW-001/002.
- Tabla de componentes con rutas viejas (`layout/laf/`, `layout/auto/`).
- `DIAGRAM_REVIEW.md` se autodefine «checklist vivo» pero está congelado en
  junio, con métricas de canvas desmentidas por los SVG actuales (§O51
  recorta), rutas de módulo viejas y una recomendación de habilitar un motor
  congelado.

**Fix aplicado**: el duplicado del renderer renumerado a **WISH-ARCH-005**
(con nota de mapeo); el de convergencia cerrado ✅ (alcance completo en el
código; «afinar clasificador» queda como mejora continua); follow-up de
WISH-LAYOUT-002 marcado hecho (near/avoid); el bloque de métricas ahora es
un puntero vivo (grep) en vez de tablas que caducan; tabla de componentes
con rutas `strategies/`; banner de HISTÓRICO en DIAGRAM_REVIEW.md.

---

### BUGS-LAYOUT-011: El header no reservaba el espacio real del icono decorativo — primer miembro soldado al icono ✅ RESUELTO (2026-08-05)
**Componente**: `strategies/auto/positioner.py` (`_layout_contained_elements_locally`, re-centrado de miembro único)
**Reportado**: 2026-08-05 (caso telefonía del autor: «Troncal SIP» pegado al edificio de «Claro — Nube del operador»; también en `15-architecture-template.gag`, 3 cajas con hijo a +0px)

El icono decorativo del contenedor se DIBUJA en `[y+padding, y+padding+50]`
(`draw_container`), pero la reserva de header para los miembros era
`max(50, label) + padding` — usaba el padding como aire por encima del
icono y olvidaba que el icono ya lo consumió: el primer miembro arrancaba
en el borde inferior exacto del icono, en su misma columna (x=padding),
soldado. Agravante: sin label la reserva era 0 y los miembros caían
ENCIMA del icono.

**Fix**: `_container_header_height` — para contenedores con icono, el
header llega hasta el borde real del icono (`padding + max(50, label)`),
reservado aunque no haya label; áreas (T73) y bands conservan su cuenta.
La misma función alimenta el re-centrado de miembro único (cuenta
duplicada unificada). **Medido**: labels −4 neto (06 −2, cakephp/git/
cheatsheet −1, fisica +1), cruces −1 neto; costo un a×n en 07-containers
(+1, desvío de ruteo por el corrimiento de 10px). Verificación visual:
telefonía con «Troncal SIP» respirando bajo el edificio. Regresión:
`tests/test_layout011_header_icon_gap.py` (con label, sin label, y área
sin cambio).

---

### BUGS-VAL-004: `validate_gag` sin sección `canvas` revienta con `KeyError: 'width'` ✅ RESUELTO (2026-08-03)
**Componente**: `AlmaGag/validation/visual_quality.py::validate_gag`
**Reportado**: 2026-08-03 (papercut hallado al re-medir la tabla del rol GAG Skiller)

`canvas` es OPCIONAL en el formato: el CLI pone defaults (`generator.py`,
WIDTH×HEIGHT), pero `validate_gag` construía el Layout con el dict vacío y
el positioner reventaba en `layout.canvas['width']`. Reproductor: cualquier
.sdjf sin sección `canvas` vía `validate_gag`.

**Fix aplicado**: mismos defaults que el generator al construir el Layout.
Test: `tests/test_visual_quality.py::test_validate_gag_without_canvas_uses_defaults`.

---

### BUGS-VAL-003: `validate_svg` standalone no ve iconos dibujados sólo con `<path>` (firewall) ✅ RESUELTO (2026-08-02)
**Componente**: `AlmaGag/validation/visual_quality.py`
**Reportado**: 2026-08-02 (auditoría; re-verifica la nota del skill sobre R3/FortiGate)

Verificado hoy sobre `docs/diagrams/svgs/01-iconos-registrados.svg`: de 11
iconos, `_collect_icon_bboxes` devuelve 9 — `firewall1` invisible. Causa
triple: `firewall.py:14` emite el `<g id=…>` SIN transform (el transform
vive en un hijo sin id), `_group_transform_bbox` no encuentra `translate` y
`_group_children_bbox` (`:176-210`) sólo recorre
`rect/polygon/circle/ellipse` — el firewall es 100% `<path>`. Consecuencia:
falso positivo R3 («conector en el aire») en el camino standalone
`validate_svg(svg)`. El camino `validate_gag()` no se afecta (inyecta bboxes
del optimizer), por eso los tests no lo ven. El ticket `BUGS-VAL-001 ✅` no
documenta esta limitación.

**Fix aplicado**: (a) si el `<g id>` no tiene transform, se busca el
translate/scale en un `<g>` DESCENDIENTE (el firewall envuelve así); (b)
`scale(sx, sy)` no uniforme soportado; (c) `_group_children_bbox` ahora
también recorre `<path>` (vía `viewbox._path_points`) y `<line>`.
Verificado: firewall detectado en (500,100)-(625,158). Test:
`tests/test_val003_path_icons.py`.

---

### BUGS-ARCH-001: `Layout.copy()` pierde todos los atributos ad-hoc ✅ RESUELTO (2026-08-02)
**Componente**: `AlmaGag/layout/layout.py:70-96`, `AlmaGag/generator.py:221-252`
**Reportado**: 2026-08-02 (auditoría; mordió en la práctica al implementar §Q65)

El generator cuelga del layout al menos 7 atributos ad-hoc
(`_considerations`, `_areas`, `_roles`, `_lanes`, `_strategy`,
`_diagram_name`, `_layout_view`; más `_measure_stored_labels` del
optimizer) y `Layout.copy()` no copia NINGUNO. El pipeline entero trabaja
sobre copias (`current = layout.copy()`, candidatos del loop), así que todo
consumidor debe acordarse de leer del layout ORIGINAL vía `getattr` con
default — contrato implícito, invisible y fácil de romper (§Q65 falló en el
primer intento exactamente por esto; quedó nota en
`zones.py::zone_affinity_groups`).

**Fix aplicado**: registro explícito `Layout.CONTEXT_ATTRS` (10 atributos)
que `copy()` preserva POR REFERENCIA — contexto compartido, no clonado
(las marcas sobre `_considerations`, p.ej. `_zone_affinity`, se ven en
todas las copias). Todo atributo de contexto nuevo debe registrarse ahí.
Test: `tests/test_arch001_layout_copy.py`. Guarda: 34 fixtures
byte-idénticos (comportamiento neutro; el contrato deja de ser implícito).
La extracción del contexto a un objeto aparte queda para WISH-ARCH-004.

---

### BUGS-AUTO-008: `_compact_horizontal` puede cizallar contenedores anidados (doble membresía) ✅ RESUELTO (2026-08-02)
**Componente**: `AlmaGag/layout/strategies/auto/optimizer.py::_compact_horizontal`
**Reportado**: 2026-08-02 (auditoría arquitectónica)

Los bloques rígidos se arman POR CONTENEDOR con sus hijos DIRECTOS
(`groups[('cont', id)] = [cont] + hijos`). Un contenedor anidado (p.ej.
`dc_mina` dentro de `z_mina`) queda en DOS grupos — el de su padre y el
suyo — y `node_group = {n: k for k, members in …}` resuelve por
último-gana: el contenedor anidado puede recibir un offset distinto al de
sus propios hijos y al del bloque del padre → cizalla que rompe la
contención P59. Hoy no se manifiesta en fixtures (la guarda de adopción lo
enmascara), pero es una bomba latente con P59 fomentando anidamiento.

**Fix aplicado**: membresía por CIERRE transitivo — cada contenedor
TOP-LEVEL forma un solo bloque con su subárbol completo. El test con
offsets forzados (mock) verifica la contención. BONUS descubierto por el
test: `_resolve_container_overlaps` empujaba al contenedor ANIDADO fuera
de su ancestro (el solape ancestro↔descendiente es por diseño) — sólo se
manifestaba con elementos libres presentes; ahora los pares con relación
de ancestría se saltan. Tests: `tests/test_auto008_compaction_blocks.py`.
Guarda: 34 fixtures byte-idénticos.

---

### BUGS-AUTO-009: el guardado del re-ruteo final (H3) compara rutas frescas contra rutas rancias ✅ RESUELTO (2026-08-03, iteración 6)
**Componente**: `AlmaGag/layout/strategies/auto/optimizer.py` (bloque H3)
**Reportado**: 2026-08-02 (hallazgo §P60/§P61, generalización pendiente)

`pre_reroute_conns` conservaba paths calculados ANTES de los últimos
movimientos (stagger, re-resolución de contenedores del loop); el guardado
«revertir si empeora» evaluaba esos paths rancios — que el renderer luego
re-anclaba en los extremos, dibujando diagonales que ningún evaluador
midió. La comparación estaba viciada a favor del material viejo.

**Fix aplicado**: el revert se ELIMINÓ — sobre la geometría final sólo
existe un estado medible, el re-ruteado obstacle-aware, y el re-ruteo H3
es incondicional (el caso especial de troncales §P60 quedó subsumido).
Guarda de fixtures: 37/37 sin cambios (el revert ya no ganaba en ningún
fixture). Test de invariante (`tests/test_auto009_fresh_routes.py`): todo
`computed_path` termina anclado a la geometría vigente de sus extremos.

---

### BUGS-DRAW-001: `convert_svg_to_png` con Chrome captura a `scale`× sin escalar el contenido ✅ RESUELTO (2026-08-02)
**Componente**: `AlmaGag/debug.py::_png_via_chrome`
**Reportado**: 2026-08-02 (observado en toda verificación visual del grupo P)

La ventana se dimensiona `width*scale × height*scale` pero no se pasa
`--force-device-scale-factor={scale}`: el SVG se pinta a 1× en la esquina
superior-izquierda y el resto del PNG queda en blanco (a 2×, tres cuartos
de la imagen son aire). El camino cairosvg escala bien (`scale=scale`).

**Fix aplicado**: ventana al tamaño NATURAL del SVG +
`--force-device-scale-factor={scale}` (la primera variante — escalar la
ventana Y el dsf — cuadruplicaba). Verificado: mina a 2× = 3044×2398 px con
el contenido llenando la lámina (92-95%; resto = margen §O51).

---

### BUGS-DRAW-002: `draw_embedded_icon` recibe `color` y nunca lo usa ✅ RESUELTO (2026-08-02, opción a — decisión del autor)
**Componente**: `AlmaGag/draw/icons/__init__.py::draw_embedded_icon`
**Reportado**: 2026-08-02 (denunciado por el catálogo del skill; spec ya corregida)

La firma acepta `color` (intención original: resolver `currentColor` del
SVG embebido con el color del elemento — así lo prometía la spec) pero el
cuerpo inserta el SVG tal cual: el parámetro es vestigial y `currentColor`
rasteriza negro. La spec ya fue corregida el 2-ago para decir la verdad
(«colores FIJOS»), y el skill duplica entradas de icono por variante de
color como workaround.

**Fix aplicado (opción a, elegida por el autor)**: `currentColor` se
reemplaza por el `color` del elemento (default gray) al insertar; los
iconos con hex fijos se insertan tal cual — ambas formas conviven. Spec y
contrato del skill re-alineados; el skill ya no necesita duplicar iconos
por variante de color. Tests: `tests/test_draw002_currentcolor.py`.
Guarda: 34 fixtures byte-idénticos (ninguno usaba currentColor).

---

### BUGS-LAYOUT-001: Etiquetas de Debug Solapadas en Modo VisualDebug ✅ RESUELTO
**Componente**: `layout/auto/auto_renderer.py` + `layout/laf/laf_renderer.py` — `_render_debug_levels` / `_render_debug_ndfn`
**Severidad**: Media
**Reportado**: 2026-01-21
**Resuelto**: 2026-06-18

**Causa raíz**:
Las etiquetas de debug (nivel topológico en rojo, NdFn en rojo/naranja) se renderizaban DENTRO del bbox de cada elemento primario:
- Nivel: `(elem_x, elem_y + 10)` — encima del ícono.
- NdFn: `(elem_x + 2, elem_y + 8)` — pegada al nivel.
- NdFn icon: `(elem_x + 2, elem_y + 16)` — abajo de NdFn.

Resultado en `--visualdebug`: 36/55 etiquetas (65%) solapadas con íconos en el caso de prueba `05-arquitectura-gag`, ilegibles sobre la mayoría de los elementos.

**Fix aplicado** (replicado en ambos renderers — son independientes desde WISH-ARCH-002):
Posicionamiento de las etiquetas FUERA del bbox, apiladas arriba del elemento:
- Nivel: `(elem_x, elem_y - 8)` — texto baseline 8px arriba del top del bbox.
- NdFn: `(elem_x + 2, elem_y - 24)` — arriba del nivel.
- NdFn icon: `(elem_x + 2, elem_y - 33)` — arriba de NdFn.
- Las tres usan `filter='url(#text-glow)'` para halo blanco que asegura legibilidad sobre fondos arbitrarios (mismo filtro que las etiquetas normales).

Aprovecha el `TOP_MARGIN_DEBUG = 80px` que ya se reservaba arriba del canvas en modo debug — los textos quedan en esa franja sin off-canvas.

**Validación**:
- Solapamientos en `05-arquitectura-gag --laf --visualdebug`: 36/55 → 7/55. Los 7 restantes son **falsos positivos**: 2 dentro del strip de debug del canvas (zona reservada), 5 dentro de un container (arriba de sus hijos, donde el "rect contenedor" cubre toda el área). **Cero solapamientos con íconos reales**.
- Smoke 23/23 LAF + 23/23 AUTO OK.
- Tests 17/2.
- Determinismo sin `--visualdebug`: 1 hash único × 3 seeds × 4 archivos. Con `--visualdebug` sigue no-determinista (causa preexistente: badge usa `datetime.now()`, no introducido por este fix).

---

### BUGS-LAYOUT-002: Cálculo Excesivo de Altura de Canvas ✅ RESUELTO
**Componente**: `AlmaGag/layout/laf/container_grower.py` — `calculate_final_canvas()`
**Severidad**: Media
**Reportado**: 2026-01-21
**Resuelto**: 2026-06-18

**Causa raíz**:
`container_grower.calculate_final_canvas()` aplicaba un margen único de **250px** tanto al ancho como al alto. El margen estaba justificado solo por el **badge de debug** (visible en modo `--visualdebug`), que ocupa ~240px de ancho y vive **en la esquina superior derecha** del canvas. El margen vertical de 250px no tenía justificación y desperdiciaba ~33% del canvas en promedio (78-97% en diagramas pequeños).

**Fix aplicado**:
- Nuevas constantes en `config.py`:
  - `LAF_CANVAS_MARGIN_HORIZONTAL = 250` (protege espacio del badge).
  - `LAF_CANVAS_MARGIN_VERTICAL = 50` (margen visual mínimo abajo).
- `container_grower.calculate_final_canvas()` usa las dos constantes por separado.

**Validación** (23 archivos LAF):
| Métrica | Antes | Después |
|---|---:|---:|
| Waste promedio (px) | 365 | 165 |
| Waste promedio (%) | ~33% | ~18% |
| Archivos con waste >25% | 13 | 6 |
| Determinismo (hashes únicos) | 1 | 1 |
| Smoke render | 23/23 OK | 23/23 OK |

El caso peor restante (`13-stresstest.gag`, ~97%) es por estructura inusual del diagrama, no por margen excesivo. Si se quiere atacar, sería un issue separado de "altura mal estimada por contenido", no del margen.

---

### BUGS-LAYOUT-003: No-Determinismo entre Procesos Python ✅ RESUELTO
**Componente**: `AlmaGag/layout/laf/` + `AlmaGag/layout/auto/` + `AlmaGag/layout/graph_analysis.py`
**Severidad**: Media
**Reportado**: 2026-05-14 (hallazgo lateral durante validación del refactor de routing_policy)
**Resuelto**: 2026-06-14 (rama `claude/laf-009-investigation`)

**Descripción**:
LAF (y en menor medida AUTO sobre archivos con ties) producía resultados distintos para el mismo input en procesos Python separados.

**Causa raíz**: 7 puntos en el pipeline donde iteraciones de `set`/`dict` con orden afectado por `PYTHONHASHSEED`, o sorts sin tie-break, propagaban orden inestable.

1. `structure_analyzer.py:1297` — construcción de `element_tree[vc].children` desde `vc['members']` (set).
2. `structure_analyzer.py:1130-1138` — formación de leaf VCs desde `terminal` (set).
3. `structure_analyzer.py:1229` — `sorted_tois` sin tie-break.
4. `structure_analyzer.py:1371` — conversión `set→list` en `contracted_graph`.
5. `graph_analysis.py:calculate_topological_levels` — iteración de `elem_ids` (set) en fixpoint con ciclos.
6. `auto/positioner.py` + `laf/position_optimizer.py` — suma de floats no-conmutativa.
7. `laf/abstract_placer.py` — 5 sorts sin tie-break por `elem_id`.

**Fix aplicado**: `sorted()` con tie-break por `elem_id` en cada punto.

**Validación**: 23 archivos × 5 seeds × 2 algoritmos = 230 invocaciones. Antes: hasta 5 hashes distintos por archivo. Después: 1 hash por archivo en los 46 casos.

---

### BUGS-LAF-001: Distribución Horizontal Asimétrica en Niveles Multi-Elemento ✅ RESUELTO
**Componente**: `AlmaGag/layout/laf/container_grower.py` — `calculate_final_canvas()`
**Severidad**: Baja
**Reportado**: 2026-01-21
**Resuelto**: 2026-06-18

**Causa raíz**:
Tras BUGS-LAYOUT-002, `calculate_final_canvas()` aplicaba siempre `LAF_CANVAS_MARGIN_HORIZONTAL = 250px` al lado derecho del canvas (para proteger el badge de debug que aparece en la esquina superior derecha cuando `--visualdebug` está activo). Pero `LEFT_MARGIN` en Phase 9 es `CANVAS_MARGIN_LARGE = 100px`. Resultado: cuando **no** estaba activo `--visualdebug`, el canvas terminaba con left=100/right=250, asimétrico (contenido pegado al lado izquierdo). El "spacing fijo de 480px" mencionado en la descripción original era un síntoma; el verdadero gap era con respecto al borde del canvas.

**Ejemplo de reproducción** (3 elementos en mismo nivel, sin `--visualdebug`):
```
Antes: Canvas 1390×700  left_margin=100  right_margin=250  Δ=+150 (asimétrico)
Después: Canvas 1240×700  left_margin=100  right_margin=100  Δ=0   (simétrico)
```

**Fix aplicado**:
- `ContainerGrower.__init__` ahora acepta `visualdebug=False`.
- `LAFOptimizer.__init__` propaga `visualdebug` al `ContainerGrower`.
- `calculate_final_canvas()` usa `LAF_CANVAS_MARGIN_HORIZONTAL` (250px) solo si `visualdebug=True`; en caso contrario usa `CANVAS_MARGIN_LARGE` (100px) — mismo valor que `LEFT_MARGIN`, garantizando simetría.

**Validación** (23 archivos LAF, sin `--visualdebug`):
- 17/23 (74%) **perfectamente simétricos** (left=right=100).
- 6/23 con Δ < 100px residual, atribuible a issues conocidos:
  - `git` (Δ=78): caso documentado de overflow de `legend` en BUGS-LAF-002.
  - `05-arquitectura-gag, 06-flujo, 07-containers, reference-cheatsheet`: contenedores muy disparejos en ancho.
- Smoke 46/46 OK (23 × 2 algoritmos).
- Tests 19 passed.
- Determinismo: 1 hash único × 3 seeds × 2 archivos.
- Con `--visualdebug=True`: el badge sigue protegido (right margin = 250px) ✓.
- Compactación adicional: canvas LAF -150px de ancho por archivo (recuperado del margen innecesario).

---

### BUGS-AUTO-001: Labels Huérfanas en AUTO con Contenedores ✅ RESUELTO
**Componente**: `AlmaGag/layout/auto/optimizer.py` — `optimize()` paso 2.5.6
**Severidad**: **Alta** (visualmente roto en cualquier diagrama AUTO con containers)
**Reportado**: 2026-06-18 (detectado por inspección del usuario sobre `07-containers.svg`)
**Resuelto**: 2026-06-18

**Causa raíz**:
En `AutoLayoutOptimizer.optimize()`, el orden de pasos era:
1. Paso 2 — calcular `label_positions` para todos los elementos según sus coords actuales.
2. Pasos 2.5 / 2.5.4 / 2.5.5 — re-resolver containers, propagar coords locales, redistribuir elementos primarios. **Estos movían los íconos.**
3. ... pero las `label_positions` calculadas en el paso 2 **NUNCA se recalculaban** tras ese movimiento.

Resultado: las etiquetas de los elementos contenidos (api, db, webapp, mobile, …) renderizaban en posiciones donde el ícono **ya no estaba**. En `07-containers.svg` las labels "REST API" y "Database" aparecían al fondo del canvas (y=663) huérfanas, mientras los íconos estaban arriba (y=280).

Reproducción (pre-fix):
```
api icon final position:  (-43, 280)
api label final position: (190, 663)  ← 513px de distancia vertical
```

**Fix aplicado**:
Nuevo paso **2.5.6** en `optimize()`: tras la redistribución (paso 2.5.5), limpiar `label_positions` y `connection_labels`, y volver a llamar `_calculate_initial_positions(current)` con las coords finales de los íconos.

```python
current.label_positions = {}
current.connection_labels = {}
self._calculate_initial_positions(current)
```

Post-fix:
```
api icon:  (-43, 280)
api label: (-3, 350)  ← bottom del ícono ✓
```

**Validación**:
- 2 canonical SVGs regenerados con el fix:
  - `07-containers.svg`: labels REST API/Database/Web App/Mobile App/Redis Cache ahora pegadas a sus íconos.
  - `reference-cheatsheet.svg`: misma causa raíz, también corregido.
- Smoke 46/46 OK, tests 19 passed, determinismo intacto.
- 21/23 canonical SVGs sin cambios (solo los que tienen containers se ven afectados).

**Nota**: el fix no resuelve el problema **separado** de contenido off-canvas. Ese se resolvió en `BUGS-AUTO-002`.

---

### BUGS-AUTO-002: Contenido Cortado por el Borde (coords negativas) en AUTO ✅ RESUELTO
**Componente**: `AlmaGag/layout/auto/optimizer.py` — `optimize()` + `_normalize_to_canvas()`
**Severidad**: **Alta** (contenido visiblemente cortado)
**Reportado**: 2026-06-18 (segunda inspección del usuario sobre `07-containers.svg`)
**Resuelto**: 2026-06-18

**Causa raíz**:
La redistribución de elementos primarios alrededor de contenedores expandidos (`positioner.recalculate_positions_with_expanded_containers`) puede empujar elementos a coordenadas negativas. En `07-containers`, el container `backend-module` terminaba en x=-93 — cortado por el borde izquierdo del canvas. El cálculo de canvas (`_calculate_canvas_from_bounds`) solo miraba `x_max`/`y_max`, nunca los mínimos, así que las coords negativas nunca se compensaban.

**Fix aplicado**:
Nuevo método `_normalize_to_canvas()` llamado al final de `optimize()` (antes del return):
- Calcula `min_x`, `min_y` de todos los elementos posicionados.
- **Solo dispara si `min < 0`** (contenido cortado). No re-centra diagramas que ya caben — eso cambiaría layouts correctos.
- Aplica un shift uniforme a elementos, `label_positions` y `connection_labels` para llevar el mínimo a `CANVAS_MARGIN_SMALL` (50px).
- Re-rutea (regenera `computed_path` desde las nuevas posiciones) y recalcula el canvas.

**Validación**:
- `07-containers`: min_x pasó de **-93 a 50** (dentro del canvas). 0 elementos con x<-5 en el SVG.
- **Solo 1/23 canonical afectado** (`07-containers` — el único con coords negativas). Confirmado que ningún otro diagrama tenía el problema.
- Smoke 46/46 OK, tests 19 passed, determinismo intacto.

---

### BUGS-AUTO-003: Connection Labels Sobre Iconos Dentro de Containers ✅ RESUELTO
**Componente**: `AlmaGag/layout/geometry.py` — `label_intersects_elements()`
**Severidad**: **Alta** (etiquetas ilegibles encimadas con iconos)
**Reportado**: 2026-06-18 (tercera inspección del usuario sobre `07-containers.svg`)
**Resuelto**: 2026-06-18

**Causa raíz**:
`label_intersects_elements()` (usada por `LabelPositionOptimizer.score_position()`) trataba el rect de un **container** como un elemento sólido para detección de colisiones de labels. Como los iconos de un container viven DENTRO de su rect, cualquier posición candidata para el label de una conexión interna (ej: "queries" entre `api` y `db`, ambos dentro de `backend-module`) caía dentro del rect del container → **todos los candidatos sumaban el mismo +100**.

Con todos los candidatos empatados en la penalización de container, el desempate (por distancia/densidad) terminaba eligiendo posiciones que caían **encima de un icono**. La colisión con elementos es booleana (+100 fijo, no cuenta cantidad), así que "label sobre icono" (1 colisión real) puntuaba igual que "label en hueco libre dentro del container" (0 colisiones reales, solo el container).

Reproducción (`07-containers`, pre-fix): "queries" (centro de su línea en x=190) se movía a x=139, **encima del icono REST API** (centro x=140).

**Fix aplicado**:
`label_intersects_elements()` ahora **excluye containers** (`if 'contains' in elem: continue`). Los containers son fondos semi-transparentes — los labels legítimamente viven dentro de ellos. Tras el fix, solo los iconos reales cuentan como colisión, y el optimizer elige posiciones en huecos libres en vez de sobre iconos.

**Validación** (connection-labels sobre icono, antes → después):
- `07-containers`: 1 → **0**.
- `git`: 1 → **0**.
- `reference-cheatsheet`: 2 → **0**.
- `06-flujo-ejecucion`: 0 → 0 (reposicionamiento marginal).
- Total: **4 → 0**.
- 4 canonicals regenerados (los que tienen containers).
- Smoke 46/46 OK, tests 19 passed, determinismo intacto.

---

### BUGS-AUTO-004: Containers Solapados sin Resolución (AUTO) ✅ RESUELTO
**Componente**: `AlmaGag/layout/auto/positioner.py` + `AlmaGag/layout/collision.py`
**Severidad**: **Alta** (solape visible entre containers)
**Reportado**: 2026-06-18 (cuarta inspección del usuario sobre `07-containers.svg`)
**Resuelto**: 2026-06-18

**Causa raíz** (doble):
1. **`recalculate_positions_with_expanded_containers()` solo movía elementos libres**, nunca chequeaba container-vs-container. Frontend (nivel topológico 0, alto=233) y Backend (nivel 1) terminaban solapando 137×65 sin que nadie lo arreglara.
2. **El detector general (`CollisionDetector._collect_all_bboxes`) contaba el rect de cada container como obstáculo sólido** — mismo bug que AUTO-003 pero en otro path. Inflaba colisiones falsas y el hill-climbing reportaba 13 colisiones sin poder bajarlas, así que se rendía.

**Fix aplicado**:
- **`positioner._resolve_container_overlaps()`** (nuevo): tras mover free_elements, ordena containers por `y` e itera cascada de empujones — si dos containers solapan, el de mayor `y` se desplaza debajo del otro (+ margen).
- **`positioner._shift_container_subtree()`** (nuevo): mueve un container y todos sus descendientes por `(dx, dy)` preservando la composición interna.
- **`collision._collect_all_bboxes()`**: excluye TODOS los containers (con o sin `_is_container_calculated`). Son fondos semi-transparentes.

**Validación**:
- `07-containers`: overlap **137×65 → 137×0** (containers separados verticalmente con 40px de gap).
- Colisiones reales: **13 → 4**. Las 4 que quedan son falsos positivos legítimos (conn label cerca de su propia conexión, dos "HTTP requests" solapando entre sí — caso a resolver con repulsión de labels).
- Solo `07-containers` afectado entre canonicals (el único con containers solapados).
- Smoke 46/46 OK, tests 19 passed, determinismo intacto.

---

### BUGS-AUTO-005: Labels de Iconos Contenidos Salen Fuera del Container/Canvas ✅ RESUELTO
**Componente**: `AlmaGag/layout/auto/optimizer.py` — `_find_best_label_position` + `_try_relocate_labels` + `collision.count_element_collisions`
**Severidad**: **Alta** (labels visiblemente cortados / fuera de su container)
**Reportado**: 2026-06-18 (quinta inspección — diagrama de arquitectura tras los 4 AUTO previos)
**Resuelto**: 2026-06-18

**Causa raíz** (triple):
1. **`_find_best_label_position` no verificaba off-canvas**: el primer candidato sin colisión ganaba aunque su bbox quedara con x<0 o x>canvas_w. Caso típico: icono pegado al borde izquierdo del container y label en `left` con anchor=end → texto extendido hacia x negativo (auto_opt label en x=55 con texto de ~150px → empezaba en x=-95).
2. **`_try_relocate_labels` tenía el mismo agujero**: relocaba a `top` cuando `bottom` tenía 1-2 colisiones con líneas, sin importar si `top` salía del container o caía sobre el header del container ancestro.
3. **`count_element_collisions` contaba containers como obstáculos** (mismo path que AUTO-003 y AUTO-004 pero en otra función).

Resultado en `05-arquitectura-gag` antes del fix: `AutoLayoutOptimizer` con label en `left` (anchor=end) cortado fuera del canvas, `LAFOptimizer` en `top` pegado contra el label del container LAF.

**Fix aplicado**:
- **`_get_parent_container()`** + **`_label_inside_container()`** (nuevos): un label de un icono contenido debe quedar dentro del container ancestro y fuera de su header (40px).
- **Chequeo de canvas y container** en `_find_best_label_position` y `_try_relocate_labels`: posiciones que se salen se descartan.
- **`count_element_collisions`** excluye containers como obstáculos, mismo razonamiento que AUTO-003/004.

**Validación** (labels off-canvas, antes → después):
- `05-arquitectura-gag`: 2 → **0**.
- `git`: 11 → **0**.
- `reference-cheatsheet`: 12 → **1**.
- **Total: 25 → 1** en los canonicals afectados.
- Todos los iconos dentro de containers ahora con label en `bottom` dentro del container.
- 9 canonicals regenerados.
- Smoke 46/46, tests 19 passed, determinismo intacto.

---

### BUGS-AUTO-006: Labels Bottom Encimados Horizontalmente Dentro de Containers ✅ RESUELTO
**Componente**: `AlmaGag/layout/auto/optimizer.py` — `_stagger_overlapping_contained_labels` (nuevo)
**Severidad**: **Alta** (labels ilegibles superpuestos)
**Reportado**: 2026-06-18 (sexta inspección — tras AUTO-005 los labels quedaron dentro del container pero solapados entre sí)
**Resuelto**: 2026-06-18

**Causa raíz**:
Tras AUTO-005, todos los labels de iconos contenidos se forzaron a `bottom`. Pero los containers estrechos con iconos juntos (ej: `auto_box` 200px de ancho con dos iconos a 100px center-to-center) tenían labels más anchos que el spacing (`AutoLayoutOptimizer (híbrido + hill climbing)` ~180px). Los bboxes se solapaban horizontalmente.

Medición pre-fix en `05-arquitectura-gag`:
- `auto_opt` ↔ `auto_rend`: overlap 60×36
- `laf_opt` ↔ `laf_pipe`: overlap 88×36
- `layout_obj` ↔ `draw_svg`: overlap 108×36
- `router_mgr` ↔ `geometry_utils`: overlap 88×36

**Fix aplicado**:
Nuevo método `_stagger_overlapping_contained_labels()` llamado al final de `optimize()`. Por cada container:
1. Recolecta labels `bottom` de los hijos directos.
2. Ordena por x del bbox.
3. Para cada label, si su bbox solapa horizontal Y verticalmente con uno previo, lo empuja `y2_anterior + GAP` (escalón).
4. Si el escalón se sale del container, **expande la altura del container** para acomodar.

**Validación**:
- Overlaps entre labels post-fix: **4 → 0** en `05-arquitectura-gag`.
- Containers expandidos automáticamente: `auto_box` 171→196, `shared_box` 305→330.
- 4 canonicals regenerados (05-arq, 06-flujo, git, reference-cheatsheet).
- Smoke 46/46, tests 19 passed, determinismo intacto.

---

### BUGS-AUTO-007: Header Label del Container se Sale por la Derecha ✅ RESUELTO
**Componente**: `AlmaGag/layout/auto/positioner.py::_calculate_container_bounds` + `AlmaGag/layout/container_calculator.py` + `AlmaGag/draw/primitives/container.py`
**Severidad**: **Media** (header del container ilegible cuando es largo)
**Reportado**: 2026-06-19 (inspección del usuario sobre `shared_box`)
**Resuelto**: 2026-06-19

**Causa raíz**:
Las 3 funciones que calculan el `min_width` necesario para que el header quepa usaban `TEXT_CHAR_WIDTH = 8` (estimación para texto regular 14px). Pero el header de containers se renderiza **bold 16px**, que en realidad ocupa ~10px/char. La estimación subestimaba el ancho ~25%.

En `05-arquitectura-gag` el label "Shared (algoritmo-agnóstico)" (28 chars) necesitaba `100 + 28×10 + 10 = 390px`. El cálculo daba `100 + 28×8 + 10 = 334px`. El label se salía 46px por el borde derecho del container.

**Fix**: multiplicar `label_width` por 1.25 (8 × 1.25 = 10) en las 3 funciones.

**Validación** (`05-arquitectura-gag`):
- `shared_box` width: 334 → 390. Header cabe.
- 3 canonicals afectados (05-arq, git, reference-cheatsheet) regenerados.
- Smoke 46/46, tests 19 passed.

---

### BUGS-LAF-002: Layout Pobre con Contenedores Hermanos sin Conexiones (caso "dashboard") ✅ RESUELTO
**Componente**: `AlmaGag/layout/laf/optimizer.py` — Fase 1.5 (dashboard reflow) + Fase 9 (redistribución)
**Severidad**: Media
**Reportado**: 2026-05-14 (auditoría externa)
**Resuelto**: 2026-06-18

**Causa raíz** (doble):
1. Cuando 3+ contenedores root viven en el mismo nivel topológico sin conexiones entre ellos, el pipeline LAF los pone en fila horizontal (todos `abstract_y=0`). El canvas se vuelve extremadamente horizontal (caso de prueba 4 contenedores → 5900×243 px, ratio 24:1).
2. Bug secundario en Fase 9 (`_redistribute_vertical_after_growth`): los hijos de un contenedor aparecían en `optimized_layer_order` y eran reposicionados **dos veces** — una vez con el contenedor (correcto), otra independientemente con su `abstract_x` (incorrecto), terminando fuera del contenedor.

**Fix aplicado**:
- **`config.py`**: nueva constante `LAF_DASHBOARD_MIN_CONTAINERS = 3` (umbral).
- **`optimizer.py::_apply_dashboard_reflow()`** (nuevo método, llamado entre Fase 1 y Fase 2): detecta clusters de dashboard (N≥3 contenedores root en mismo nivel sin conexiones inter-contenedor) y promueve cada contenedor a un nuevo nivel topológico siguiendo grid `ceil(sqrt(N))` columnas × `ceil(N/cols)` filas. Los descendientes heredan el nuevo nivel.
- **`optimizer.py::_redistribute_vertical_after_growth()`**: skip de elementos cuyo padre contenedor está en la misma capa (evita doble movimiento).
- **`optimizer.py::_redistribute_vertical_fallback()`**: mismo skip aplicado al fallback.

**Validación**:
- Caso de prueba dashboard (4 contenedores root sin connections): canvas 5900×243 → 1165×656 (ratio 24:1 → 1.8:1).
- Smoke 23/23 LAF + 23/23 AUTO OK.
- Tests 17 passed, 2 skipped.
- Determinismo: 1 hash único × 5 seeds × 3 archivos.
- Efectos colaterales positivos en LAF: `07-containers` 3116→2614 (-16%), `11-stresstest` 700→410 (-41% alto), `git` 7875→1797 ancho (-77%).
- Canonical SVGs (AUTO) sin cambios.

**Limitaciones conocidas (no bloquean cierre)**:
- En el caso `git.sdjf`, el contenedor `legend` queda ~40px fuera del borde izquierdo del canvas (problema de centrado global cuando el grid tiene contenedores muy disparejos en ancho). Pendiente de evaluar como issue separado si molesta.
- El segundo hijo de cada contenedor puede sobresalir ~35px del borde derecho — bug preexistente del `container_grower` (no introducido por este fix).

---

### BUGS-ROUT-001: Rutas Ortogonales con Bends Innecesarios al Cruzar a Container ✅ RESUELTO (v2)
**Componente**: `AlmaGag/routing/orthogonal_router.py` + `AlmaGag/routing/visibility_graph.py`
**Severidad**: Media (afecta legibilidad visual de cualquier diagrama con containers)
**Reportado**: 2026-06-23 (feedback visual del usuario sobre `05-arquitectura-gag` post-actualización a v3.5)
**Resuelto**: 2026-06-23 (v1: commit `32e82a6`, v2: ventanas 4..7 puntos)

**Causa raíz** (doble):

1. **Routing por intermediate point con segmentos independientes**: cuando una conexión cruza el límite de un container (from fuera, to dentro — o viceversa), `OrthogonalRouter.calculate_path` delega a `_calculate_orthogonal_waypoints_with_intermediate`, que computa **2 segmentos independientes** (from → entry_point del container, entry_point → to), cada uno con su propio naive midpoint H-V o V-H (2 bends c/u). Resultado: hasta 4 bends por conexión aunque la geometría permita 1 bend limpio.

2. **Fallback al naive midpoint cuando A* falla**: `_route_with_visibility_graph` cae a `_calculate_orthogonal_waypoints` cuando A* no encuentra ruta. A* falla cuando alguno de los ports asignados por `port_assignment` cae dentro del bbox inflado (`OBSTACLE_MARGIN=25`) de algún container, lo cual ocurre con frecuencia cuando el target está pegado al borde de su container.

**Caso de prueba reproducible** (antes del fix, commit `e2712e4`):

Diagrama `05-arquitectura-gag.gag` con elementos `templates` (fuera de container, y=440) y `auto_opt` (dentro de `auto_box`, y=630).

| Conexión | Bends antes | Bends ideal |
|---|---:|---:|
| `templates → auto_opt` | 3 | 1 |
| `templates → laf_opt` | 3 | 1 |
| `auto_opt → contract` | 4 | 1 |
| `laf_opt → contract` | 4 | 1 |

**Fix aplicado**:

Nueva función `simplify_orthogonal_zigzag(path, obstacles)` en `visibility_graph.py`. Algoritmo:

```
para cada ventana de N puntos consecutivos [p_i, ..., p_{i+N-1}] en el path:
    para cada esquina candidata corner ∈ {(p_i.x, p_{i+N-1}.y), (p_{i+N-1}.x, p_i.y)}:
        si segmento (p_i → corner) y (corner → p_{i+N-1}) no cruzan obstáculos:
            reemplazar el rango por [p_i, corner, p_{i+N-1}]
            marcar changed
            break
N corre de 4 a 7 (configurable); empezar desde N=4 (más conservador) y subir
si no se encontraron reducciones. Cuando hay reducción, reiniciar al N más
pequeño para permitir cadenas de simplificación.
iterar hasta no haber cambios (acotado por len(path))
limpieza final de puntos colineales
```

Llamada desde `OrthogonalRouter.calculate_path` como post-process, **después** de cualquier estrategia de waypoint computation. Los containers padre de `from`/`to` se excluyen de los obstáculos (no podemos chequearlos como obstáculos porque tenemos que cruzarlos para llegar al destino).

**v1 (commit `32e82a6`)**: ventanas de exactamente 4 puntos.
**v2**: ventanas de 4 a 7 puntos progresivas, mejora `15-architecture-template` (20→18 bends) y casos similares con zig-zags más largos.

**Validación**:

| Métrica | Antes (`e2712e4`) | Después (`32e82a6`) |
|---|---:|---:|
| Bends en `05-arquitectura-gag` (12 conexiones) | 28 total | 16 total (−43%) |
| Conexiones con solo 1 bend | 3/12 | 9/12 |
| Conexiones con ≥3 bends | 8/12 | 1/12 |
| Tests | 70/70 | 70/70 |
| Smoke (canonicals representativos) | OK | OK |
| Determinismo | 1 hash | 1 hash |

**Audit global** sobre los 24 canonicals (regenerando con/sin el fix):

| Diagrama | Bends pre | Bends post | Δ |
|---|---:|---:|---:|
| `05-arquitectura-gag` | 36 | 19 | **−47%** |
| `15-architecture-template` | 37 | 18 | **−51%** |
| `13-stresstest` | 45 | 36 | **−20%** |
| `continentes-america` | 24 | 24 | 0% |
| `svg-to-bwt-flow` | 8 | 8 | 0% |
| `reference-cheatsheet` | 9 | 9 | 0% |
| `git` | 6 | 6 | 0% |
| **TOTAL** (130 conexiones afectadas) | **165** | **120** | **−27%** |

Los otros canonicals no listados (16) no usan routing ortogonal sobre containers, así que no se benefician — pero tampoco se degradan.

**Limitaciones conocidas (no bloquean cierre)**:
- Las 3 conexiones residuales en `05-arquitectura-gag` con 2-4 bends son las que tienen que **cruzar completamente** el `shared_box` (los dos endpoints están en lados opuestos del container y el L-shortcut por encima/debajo del container requeriría puntos que no están en el path original). Resolver eso es re-routing, no simplification — issue distinto.
- La simplificación es **orthogonal-only**. Otros routing types (bezier, arc, straight) no usan este post-process. Si en el futuro vuelven a producir paths con bends innecesarios, mover la simplificación a `router_base.ConnectionRouter`.

---

### BUGS-TPL-001: Architecture Scorer Calibrado Demasiado Conservador ✅ RESUELTO
**Componente**: `AlmaGag/layout/templates/architecture.py` — `ArchitectureTemplate.detect_score`
**Severidad**: Media (arquitecturas claras no reciben el template adecuado y caen al fallback agnóstico)
**Reportado**: 2026-06-23 (test neutro `cakephp-mvc.gag`)
**Resuelto**: 2026-06-23

**Caso de prueba reproducible**:

`docs/diagrams/gags/cakephp-mvc.gag` — arquitectura MVC clásica:
- 3 containers (controllers, models, views) + 1 cross-cutting implícito.
- Entry: `request`. Terminal: `response`. Cadena lineal en medio.
- 19 elementos, 18 conexiones, profundidad topológica 8, sin ciclos.

Es estructuralmente un caso de libro del template `architecture`. Sin embargo, los scores resultantes son:

```
architecture=0.55, er=0.45, sequence=0.40, state=0.40, flow=0.35,
dashboard=0.30, hub_and_spoke=0.25
```

`architecture` queda por debajo del threshold (`0.6`). Cae al fallback agnóstico → canvas alargado 1400×2108 y 6 colisiones.

**Causa raíz**:

El scorer suma:
- `+0.35` por `n_containers >= 2` ✓
- `+0.10` por `n_containers >= 3` ✓
- `+0.20` por keyword `shared`/`compart`/`agnost` ✗ (CakePHP no usa esos términos)
- `+0.10` por DAG ✓
- `+0.15` por depth 3..7 ✗ (depth=8 queda fuera del rango)
- Sin roles declarados (`+0.15` no aplica)

Total: `0.55`. Pierde por dos hilos:
1. La ventana de profundidad `3..7` excluye depth=8, que es perfectamente válido en arquitecturas reales.
2. El bonus por keyword es muy específico a la nomenclatura interna de AlmaGag (`shared (algoritmo-agnóstico)`).

**Diagnóstico**:

El scorer está sobre-ajustado al patrón visual de `05-arquitectura-gag` (que usa la palabra "shared" y tiene depth 5). Cualquier arquitectura sin esa nomenclatura específica o con cadena más larga pierde el template.

**Fix aplicado**:
1. Ventana de depth ampliada `3..7` → `3..10` (arquitecturas reales tienen cadenas más largas).
2. Nuevo bonus por **firma estructural** (`+0.10`): `n_root_nodes_no_incoming == 1` + `n_leaf_nodes_no_outgoing >= 1` + `n_containers >= 2`. Es la señal genérica de arquitectura (entry → containers paralelos → salida), independiente de la nomenclatura.
3. Peso del keyword `shared`/`compart`/`agnost` bajado `0.20` → `0.15` (señal débil, no excluyente).

**Validación** (matriz de scores sobre los 24 canonicals, antes vs después):

| Diagrama | architecture antes | después | winner antes | winner después |
|---|---:|---:|---|---|
| `cakephp-mvc` | 0.55 | **0.80** | —(agnostic) | **architecture** ✓ |
| `05-arquitectura-gag` | 0.75 | 0.95 | architecture | architecture |
| `07-containers` | 0.60 | 0.70 | architecture | architecture |
| `06-flujo-ejecucion` | 0.45 | 0.55 | hub_and_spoke | hub_and_spoke |
| `continentes-america` | 0.20 | 0.35 | —(agnostic) | —(agnostic) |
| resto (21) | — | — | (sin cambios) | (sin cambios) |

**Cero regresiones**: ningún canonical cambió de winner salvo `cakephp-mvc` (el objetivo). `cakephp-mvc.svg` regenerado con architecture: canvas 1400×2108 → 1140×1330 (−58% área).

**Tests**: `tests/test_architecture_scorer_calibration.py` (5 tests: MVC sin keyword supera threshold, cadena profunda ya no descalifica, bonus estructural requiere entry único, canonical cakephp detecta architecture, no-regresión de winners). Suite 84/84.

---

### BUGS-VAL-001: R3 Reporta Falsos Positivos con Conectores Rectos Cortos ✅ RESUELTO
**Componente**: `AlmaGag/validation/visual_quality.py` — `_collect_icon_bboxes`, `check_connections_attached`, `_is_connection_stroke`
**Severidad**: Baja (afecta solo a reportes del validador, no al render)
**Reportado**: 2026-06-23 (test neutro `cakephp-mvc.gag`)
**Resuelto**: 2026-06-23

**Caso de prueba reproducible**:

`docs/diagrams/svgs/cakephp-mvc.svg` — el validador reporta `R3=14` (conectores supuestamente "sueltos"). Inspección visual: los 14 conectores están correctamente atados a sus iconos. Son conexiones rectas (straight routing), porque el `.gag` no declara `routing.type`.

**Causa raíz** (hipótesis):

`check_connections_attached` clasifica como dangling cualquier endpoint cuya distancia a icon_bbox > 20px. Pero:
1. Algunos iconos custom (router, computer, laptop, database) son grupos SVG complejos con `<g transform="translate(x,y)">` en vez de `<rect>` simple. `_extract_icon_bboxes` puede estar derivando bboxes inexactos para estos tipos.
2. La tolerancia de `20px` es razonable para iconos centrados, pero con port_assignment los endpoints caen en bordes del icono. Si el bbox extraído del SVG está desplazado, la distancia queda > 20px aunque visualmente esté atado.

**Validación**:
- En `cakephp-mvc.svg`: 10 iconos detectados por el validador vs 19 elementos en el `.gag` → el validador está perdiendo iconos custom y luego reporta sus conectores como dangling.
- En los canonicals con iconos custom embebidos (`05-arquitectura-gag`), R3 también es alta (30) por el mismo motivo.

**Fix aplicado**:
1. `_collect_icon_bboxes` reescrito para reconocer iconos custom:
   - `_group_transform_bbox`: `<g transform="translate(tx,ty) scale(s)">` → bbox `ICON_W×ICON_H` escalado (factory, gear, contract, iconos SVG embebidos).
   - `_group_children_bbox`: `<g>` con `polygon`/`circle`/`ellipse`/`rect` en coords absolutas → bbox por extensión de hijos (diamond y similares).
   - Mantiene la detección de `<rect>` con gradiente suelto (built-ins) sin duplicar los ya cubiertos por un grupo.
2. Tolerancia R3 `20 → 30px` (port_assignment distribuye los puntos en sectores; offsets de hasta ~25px del centro del lado).
3. `_is_connection_stroke` ahora acepta los colores de la paleta semántica (WISH-LAYOUT-007), que de otro modo dejaban las conexiones coloreadas sin detectar (conns=0).

**Validación** (validador HEAD vs nuevo sobre los mismos 26 SVGs canónicos):

| Métrica | HEAD | Nuevo | Δ |
|---|---:|---:|---:|
| R3 total | 241 | 44 | **−82%** |
| `05-arquitectura-gag` R3 | 30 | 1 | −97% |
| `cakephp-mvc` R3 | 14 | 2 | −86% |
| R1 total | 35 | 51 | +16 (más preciso) |

El alza de R1 es **correcta**: al detectar ahora los iconos custom, el validador captura labels que sí caen sobre ellos (overlaps reales antes invisibles), no falsos positivos.

**Tests**: `tests/test_visual_quality.py` +3 (detección de icono por transform y por polygon, conexión entre custom-icons no es dangling, conexión con color semántico se detecta). Suite 99/99.

**Limitación conocida**: un `connection.color` arbitrario fuera de la paleta semántica (ej. `"color": "red"`) puede no detectarse como conexión por `_is_connection_stroke`. El distinguidor robusto sería "tiene marker" — se deja para v2.

---

## 🌟 WISH

### WISH-DRAW-002: Flujos de información resaltados («highlighter» sobre el diagrama) ✅ RESUELTO (2026-08-02, iteración 6)
**Reportado**: 2026-08-02 (idea del autor, al cierre del review grupos O–R)
**Componente**: formato SDJF/.gag + `draw/` (capa nueva de anotación)

**Idea original (verbatim del autor)**: «aparte de las conexiones hay flujos
de información, me interesa que esos flujos se dibujen como si hubiesen sido
pintados con un resaltador pasando por elementos concretos del diagrama. Sé
que es un feature completamente nuevo, pero es necesario.»

**Concepto**: capa de ANOTACIÓN, no de topología. Un flujo narra un recorrido
sobre el diagrama ya tendido — el camino de un paquete, un trámite, una
cadena de aprobación — sin agregar aristas ni alterar el layout.

Boceto de diseño (a validar cuando se implemente):

- **Formato**: sección top-level `flows`, secuencia ORDENADA de ids
  existentes:
  ```json
  "flows": [
    {"id": "scada", "label": "Datos SCADA", "color": "#f7e017",
     "path": ["cpe_mina", "est2", "dc_mina", "cco"]}
  ]
  ```
- **Render**: trazo ancho (~28px) semitransparente (opacity ~0.3,
  linecap/linejoin round), colores de resaltador (amarillo/verde/rosa/
  celeste), pasando por los CENTROS de los elementos del path. Capa: sobre
  fondos/zonas y bajo iconos+textos (el resaltador real pinta encima, pero
  con alfa debajo se lee mejor — decidir con verificación visual).
- **Ruteo del trazo**: entre dos elementos consecutivos, si existe conexión
  dibujada entre ambos → seguir su `computed_path` (el flujo recorre las
  rutas reales, troncales §P60 incluidas); si no hay arista → tramo directo
  u ortogonal. La geometría es del motor (§R); el skill sólo declara.
- **No es conexión**: no cuenta en cruces/labels (clase `ag-flow` excluida
  de detectores, como `ag-text-halo`), no participa del ruteo ni del
  posicionamiento.
- **Varios flujos**: leyenda propia («Flujos:») análoga a §N48; solapes
  entre flujos legibles por transparencia.
- **Casos de uso**: fixture minero — flujo SCADA cpe→est→DC→CCO, flujo de
  facturación contratista→externos; organigramas — cadena de aprobación.
- **Retos anotados**: legibilidad del alfa sobre zonas coloreadas; flujo
  cruzando flujo; interacción con el recorte §O51 (el trazo entra al bbox);
  esquinas del trazo en las troncales ortogonales.

**Resuelto**: `draw/primitives/flows.py` + gancho en el renderer compartido
(capa entre fondos e iconos — cubre auto Y hier). El trazo sigue los
`computed_path` reales (troncales §P60 incluidas) con fallback recto;
paleta de resaltador; leyenda «Flujos:» apilada con las demás; ids
inexistentes → WARNING; `class="ag-flow"` invisible para métricas y
validador (test diferencial). Fixture minero con 2 flujos de demo (SCADA
y facturación) — línea [motor] intacta. De paso, DRAW-001 v2: algunos
Chromium tratan --window-size como ventana EXTERIOR (~70-90px de UI
fantasma) → holgura + recorte exacto del PNG. Tests:
`tests/test_flows.py` (7).

---

### WISH-LAYOUT-008: Unificar los TRES sistemas de etiquetas + medición veraz total ✅ RESUELTO (2026-08-03, iteración 6)
**Componente**: `layout/label_optimizer.py`, `strategies/auto/{optimizer,anticollision,auto_renderer,positioner}.py`, `layout/collision.py`
**Reportado**: 2026-08-02 (deuda estructural descubierta al cerrar §P61)

Convivían TRES sistemas que colocaban etiquetas sin verse entre sí:
(1) `layout.label_positions` + la pasada global §P61 (verdad para miembros
CONTENIDOS); (2) el stagger de contenedores (BUGS-AUTO-006) dentro del
optimizer; (3) el `LabelPositionOptimizer` del RENDERER, que re-optimizaba
en tiempo de dibujo las etiquetas de elementos LIBRES y las de conexión —
lo dibujado ≠ lo medido para esos casos.

**Resuelto en dos mitades (commits de la iteración 6):**

*Unificación*: la pasada global §P61 es LA única optimización — cubre
elementos libres, siembra la verdad que falte (`seed_label_truth`,
respetando `label_position` §F18) y almacena SIEMPRE el centro elegido de
cada rótulo de conexión. El `AutoSVGRenderer` dibuja
`label_positions`/`connection_labels` TAL CUAL; hier corre la misma pasada
al final de su optimize; el `LabelPositionOptimizer` quedó exclusivo de
`legacy`. Tests: `tests/test_layout008_unified_labels.py`.

*Medición veraz total*: el detector mide SIEMPRE la posición almacenada
(la bifurcación `_measure_stored_labels` desapareció — era sólo-final).
La migración destapó tres bugs latentes que la calibración canónica
ocultaba, todos corregidos: (a) el invariante «contenedores top-level sin
solape» (BUGS-AUTO-004) no sobrevivía a `_compact_horizontal` ni al
stagger — ahora se restaura en ambos y en `_recalculate_structures`;
(b) `_shift_container_subtree` y los offsets de compactación movían
bloques SIN arrastrar sus etiquetas almacenadas → etiquetas huérfanas que
puntuaban «limpias» en el vacío — ahora la etiqueta viaja con su bloque;
(c) guardas de rancidez en la pasada global: una posición almacenada a
>90px de su icono o >60px de su polilínea no es candidata.

Recalibración (guarda de 37 fixtures): git 13→11 cruces con todo adherido
(su aspecto 0.26 es honesto: el 0.44 anterior lo inflaban las huérfanas),
mina 22→19 labels, reference-cheatsheet 23→21 y a×n 3→2, 06-flujo 8→12
(conteo honesto de la congestión que antes escondían dos huérfanas); los
otros 33 fixtures byte-estables. Verificación visual PNG de los 5 casos.

Lo que NO cierra este ticket (sigue en WISH-LAYOUT-009): la congestión de
pitch — filas donde las etiquetas son más anchas que el espaciado de
iconos (fila de torres del minero, contenedor LAF de 06-flujo).

---

### WISH-LAYOUT-009: Pitch label-aware — espaciado consciente del ancho de etiquetas ✅ RESUELTO (2026-08-03, iteración 6 — intento 3)
**Componente**: `strategies/auto/{positioner,optimizer}.py`, `routing/orthogonal_router.py`
**Reportado**: 2026-08-03 (alcance restante al cerrar WISH-LAYOUT-008)

Las fusiones restantes eran todas del mismo tipo: filas/grillas donde el
pitch entre iconos se calculaba por el ancho del ICONO, no de su ETIQUETA.
Dos intentos previos fueron revertidos por la guarda; el tercero prosperó
porque las precondiciones que su diagnóstico pedía ya existían (pasada
global única, medición veraz, invariantes de solape restaurables).

**Aplicado**:
- La celda se ensancha al label más ancho de su columna en TODA grilla
  (antes sólo ≤2 columnas) + reserva vertical por FILA; el avance de una
  band es por hijo (`max(icono, label)`).
- Bugs latentes que el crecimiento destapó, corregidos: el ancho del
  contenedor descartaba el ORIGEN local (el centrado de la primera columna
  dejaba al último hijo fuera del borde — P59 roto en el minero); la
  resolución contenedor-contenedor tenía early-return sin elementos libres
  (un diagrama 100% seccionado — template dashboard — quedaba montado); el
  corredor ortogonal contenedor→contenedor era ciego a ICONOS ajenos (el
  reintento obstacle-aware H2 sólo se gatillaba por contenedores).
- Los invariantes (cajas sin solape, libres fuera de cajas) se restauran
  también tras el stagger post-H3.

Recalibración (vs. cierre de WISH-LAYOUT-008): **labels −35 y a×n −5
netos en 8 fixtures** — mina 19→14 (fila de torres LEGIBLE, el caso
testigo), git 26→12 con cruces 11→5 y aspecto de vuelta en rango
(0.26→0.47), cheatsheet 21→12, 06-flujo 12→8. Costo: cruces +7 netos
(06-flujo +6, cheatsheet +4, mina +3, git −6) — el precio del espacio
honesto, aceptado con verificación visual de los 5 casos. Tests:
`tests/test_layout009_label_pitch.py`.

Residual para «0 fusiones»: racimos de header-vs-miembro en contenedores
densos (CCO del minero) y pares aislados en zonas saturadas — ya no es un
problema de pitch sino de presupuesto de espacio por contenedor.

---

### WISH-ROUTE-001: Ruteo hacia contenedores — puertos de perímetro (grupo T del review) ✅ RESUELTO (2026-08-05, iteración 7)
**Componente**: `routing/container_ports.py` (nuevo), `strategies/auto/routing_policy.py`
**Reportado**: 2026-08-05 (artefacto Claude Design, grupo T — caso HLD zoom; T73 resuelto aparte)

**Implementado** como pasada POST-ruteo (`route_container_ports`, corre en
cada re-ruteo dentro de `AutoRoutingPolicy.route`) que hace cirugía de
extremos conservando el cuerpo del path:

- **T70** ✅: destino contenedor → el path TERMINA en un puerto de su
  perímetro con llegada perpendicular (stub exterior H/V). El icono
  decorativo jamás recibe puertos.
- **T71** ✅: destino hijo → corredor externo (grafo de visibilidad con
  contenedores blandos; fallback codo simple) → cruce H/V puro del borde
  → navegación interna ortogonal hasta el BORDE del hijo. El puerto
  deseado es la proyección del hijo (C9); si el corredor directo cruza
  HERMANOS de la misma fila/columna, se elige un carril libre y el hijo
  se aborda por su lado perpendicular (`_pick_lane`). Borde superior con
  franja de rótulo reservada (TITLE_GUARD).
- **T72** ✅: puertos por (contenedor, lado) repartidos con separación
  mínima 18px (barrido bidireccional que conserva el orden).
- waypoints v1.5 del autor se respetan sólo si conservan puntos
  intermedios reales; degenerados a recta se tratan como default.

**Medido** (vs. baseline post-T73): arista×nodo **−10 neto** — hld 2→0,
git 3→1 (el restante es diagonal intra-contenedor preexistente, familia
K37), cakephp 6→4, físico-v2 8→6, 05/15 en 0; labels −3 neto (mineras
−8, +3 en 15/git por rótulos re-medidos sobre corredores nuevos); cruces
y tinta intactos en 39/39. Verificación visual: HLD con entradas
perpendiculares distribuidas (el pileup de 5-6 flechas murió) y
07-containers sin una sola diagonal de borde. Tests:
`tests/test_route001_container_ports.py` (T70/T71/T72 + audit «cruces
diagonales de perímetro = 0» sobre el HLD).

**Desbloquea**: re-medir S66/S69 (zonas en HLDs) — el A/B del 3-ago
debía repetirse cuando esto aterrizara.

---

### WISH-LAYOUT-015: `align[]` no se honra sobre miembros de ZONAS/grillas ✅ CERRADO — sustituido por BUGS-LAYOUT-012 (2026-08-11)
**Componente**: `strategies/auto/positioner.py` (honor V79), `considerations.py`
**Reportado**: 2026-08-11 (GAG Skiller); **autocorregido por el Skiller en su reporte 2**

El repro original pedía `align` de eje x entre miembros de ZONAS
DISTINTAS colocadas en la banda horizontal §P60 — imposible POR
CONSTRUCCIÓN: la banda coloca las zonas lado a lado, así que sus
miembros nunca pueden compartir columna. Ese límite queda documentado
como contrato: dentro de una zona la grilla alinea lo que su pitch
permite (2/3 medido), entre zonas de banda el align x no aplica, y el
audit V79 NOMBRA toda violación restante (esa mitad siempre funcionó).
La semántica que el autor buscaba de verdad — «miembros equivalentes de
zonas hermanas en la MISMA FILA absoluta» — no se logra extendiendo
`align` sino alineando los techos de las zonas: eso es BUGS-LAYOUT-012,
que lo resuelve.

---

### BUGS-LAYOUT-012: Techos de zonas hermanas desfasados — el centrado vertical en la banda rompía la fila absoluta ✅ RESUELTO (2026-08-11)

> **Causa raíz** (geometría medida): `zones.py` centraba cada caja de
> zona verticalmente en la banda §P60 (`(band_h - h) / 2`). Dos zonas
> hermanas de alto distinto (cajas de 269 y 287 en el repro del Skiller)
> dejaban techos — y por tanto rótulos y PRIMERAS FILAS — desfasados los
> 9px exactos que él midió (rótulos en y=85 vs y=76). **Fix**: las zonas
> operativas se alinean al TECHO de la banda (`ZONE_MARGIN - y1`); los
> miembros equivalentes caen en la misma fila absoluta por construcción
> y la troncal inter-zona sale recta. `band_h` (alto real de la banda)
> se conserva para situar la fila de periferia.

**Componente**: `AlmaGag/layout/strategies/auto/zones.py` (§P60)
**Reportado**: 2026-08-11 (GAG Skiller, reporte 2 — autocorrección de
WISH-LAYOUT-015 con render objetivo)

Verificado: `m_align2` → t1/t2/t3 en y=120 (antes 129/129/120);
mina-arquitectura-fisica → z_mina y z_pila con el mismo techo (y=176).
Recalibración medida y MIRADA en PNG del físico v2: +1 cruce (15→16) y
+1 par sobre icono en z_pila (4→5, emergente del optimizador con las
nuevas coordenadas) a cambio de primeras filas alineadas y troncal de
transporte recta — el render objetivo del Skiller. Regresión:
`tests/test_layout012_zone_band.py` (fixture + sintético con zonas de
alto desigual y periferia bajo la banda completa).

---

### BUGS-VAL-006: R1 falso — el scale normalizador del icono inflaba su bbox (FortiGate 512px²) ✅ RESUELTO (2026-08-11)

> **Causa raíz**: `_group_transform_bbox` devolvía `ranura × scale`
> (80·sx, 50·sy). Pero el `scale()` de los emisores NORMALIZA el viewBox
> intrínseco del icono a la ranura 80×50 (firewall: 51×43 → ×1.57/×1.16;
> embebidos: `min(80/w, 50/h)`) — ningún emisor magnifica más allá de la
> ranura. El firewall quedaba con bbox de 125.5×58 y su PROPIO label
> lateral (x=195, el icono real termina en 180) daba «solapa icono
> (512px²)». **Fix**: el bbox se acota a la ranura nominal
> (`min(80·sx, 80)`, `min(50·sy, 50)`); un scale reductor sí reduce.

**Componente**: `AlmaGag/validation/visual_quality.py` (`_group_transform_bbox`)
**Reportado**: 2026-08-11 (GAG Skiller, reportes 1 y 2: `t6-fw.sdjf`)

Verificado con su repro exacto: 0 violaciones y las 3 conexiones siguen
detectadas (sin regresión R3); control positivo con `<g>` escalado y
texto encima sigue saltando. Guarda 40/40 idéntica (el validador no
mueve geometría). Regresión en `tests/test_visual_quality.py` y contrato
actualizado en `tests/test_val003_path_icons.py`.

---

> **Tanda 2026-08-11 — iteración 9: el caso TM en el visor.** El autor
> renderizó el presupuesto real en gag-viewer-poc y reportó tres molestias:
> letra chica, flechas que doblan justo al llegar al icono, y distancia
> vertical excesiva entre niveles. Diagnóstico medido: las tres nacen en el
> motor. Tickets: WISH-LAYOUT-016, BUGS-ROUTE-003, recalibración O56 (16/13/12)
> y BUGS-DRAW-005 (observada en el mismo PDF).

### WISH-LAYOUT-016: Gap vertical por corredor medido, no constante ✅ RESUELTO (2026-08-11)

> El pitch entre rangos era icono + `LAF_VERTICAL_SPACING` (240 fijo):
> 100-180px de aire puro por corredor. El gap ahora se mide: cada MITAD
> del corredor libra el stack de labels de su lado (label inferior del
> rango de arriba / superior del de abajo + 12 de separación), piso
> `SPACING_MEDIUM`, y el corredor con label de conexión entre rangos
> adyacentes reserva su alto (los labels viven en las conexiones
> ORIGINALES — `resolved_conns` viene sin `label`). Gemelo vertical de
> WISH-LAYOUT-009.

**Componente**: `strategies/auto/positioner.py` (asignación de Y por nivel)
**Reportado**: 2026-08-11 (caso TM en el visor: lámina 1891px de alto →
letra de ~7px aparentes al ajustar a pantalla)

Medido: TM 1891 → 1267 de alto (−33%); tinta sube en toda la lámina
(stresstest 6.7→11.3, presupuesto 11.8→15.7), aspectos hacia 1. Fix
acompañante en `considerations.apply_one`: las pasadas blandas
(align/near/avoid) arrastran el label almacenado junto con el icono —
la compresión expuso el bug latente (align x movía el icono +79 tras el
cálculo de labels y el texto quedaba huérfano ENCIMA del icono nuevo).
Regresión: `tests/test_layout016_vertical_pitch.py`.

---

### BUGS-ROUTE-003: `routing.preference` ignorada — el codo «justo al llegar» ✅ RESUELTO (2026-08-11)

> `routing.preference` sólo vivía en el fallback naive: el grafo de
> visibilidad no la recibía y el simplificador de zigzags colapsaba a L —
> el barrido perpendicular corría PEGADO al borde del icono (9/19
> llegadas H en el TM aunque el autor declaró `vertical` en todas).
> **Fix**: `_reshape_terminal_elbows` como último paso de `route()` —
> el codo terminal se retira a la MITAD del tramo largo (V-H-V), que por
> LAYOUT-016 es la línea libre de labels; consciente de obstáculos (sólo
> se adopta si los tramos nuevos no pisan lo que el A* esquivó). La
> preferencia efectiva: la declarada gana, `auto` toma el eje dominante.
> **Snap casi-alineados**: un extremo cuya única arista queda a ≤ media
> ranura de la columna del otro se alinea aunque salte rangos (hueco en
> su fila + columna libre en filas intermedias).

**Componente**: `routing/orthogonal_router.py`, `strategies/auto/positioner.py`
**Reportado**: 2026-08-11 (caso TM en el visor)

Medido: llegadas H 9→1 en el TM (la restante es un vecino horizontal —
llegada lateral legítima); rproc en la columna exacta de resumen.
Regresión: `tests/test_route003_preference.py`.

---

### BUGS-DRAW-005: El recorte O51 estacionaba las leyendas ENCIMA de la última fila ✅ RESUELTO (2026-08-11)

> El reanclaje de `ag-bottom-anchored` conserva la distancia de cada
> leyenda al borde inferior, pero el borde recortado quedaba a sólo
> `CROP_MARGIN` del contenido: la pila Estados/Recorridos/Enlaces caía
> sobre los labels de la última fila. El borde inferior ahora se
> extiende para alojar la pila completa + 12px de respiro.

**Componente**: `draw/primitives/viewbox.py` (`crop_viewbox`)
**Reportado**: 2026-08-11 (PDF del visor: leyenda sobre 'Ingeniería')

Regresión: `tests/test_draw005_legend_reserve.py` (roja sin el fix).

---

### WISH-LAYOUT-017: `align` de eje y entre rangos = contrato de FILA (promoción de rango) ✅ RESUELTO (2026-08-11)

> En un roll-up con cadenas de profundidad desigual (presupuesto TM:
> 6/4/3 eslabones), los cabezales de disciplina caían en filas distintas
> por rango topológico — y el align y entre rangos sólo se nombraba en
> el audit, sin honrarse. **Fix**: gemelo del V79 para el otro eje — un
> align y cuyos miembros viven en rangos DISTINTOS se honra por
> PROMOCIÓN DE RANGO: cada miembro sube al rango común factible (todos
> sus predecesores por debajo, sucesores por arriba; target = máximo
> entre el rango más profundo y las cotas de predecesores). Si no hay
> rango factible (p.ej. un miembro alimenta a otro del grupo), no se
> toca nada y el audit nombra la violación. La «capa de resúmenes» que
> el autor no podía declarar.

**Componente**: `strategies/auto/positioner.py` (antes de armar `by_level`)
**Reportado**: 2026-08-11 (pregunta del autor sobre los tres resúmenes en
filas distintas; el chat de diseño confirmó el descuido en sus aligns y
re-declaró `{align: [ring, rproc, constr], axis: y}`)

Verificado con la re-declaración exacta del chat de diseño: los tres
cabezales comparten fila a un paso del consolidado (y=413) y el audit
deja de dispararse; sin el align, el rango sigue escalonando (la
profundidad es información). Guarda 40/40 idéntica; suite 541 verde.
Regresión: `tests/test_layout017_row_contract.py` (honra + histórico
intacto + infactible nombrado).

---

> **Tanda 2026-08-11 — grupo W del review («Higiene de bandas y última
> milla», presupuesto v3).** Claude Design midió el render del motor
> v3.10 y abrió W83-W89. Verificado por ejecución contra master antes de
> ticketear: W85 confirmado y superado (4 diagonales, no 3, incluida su
> 335,463→375,415); W83/W87/W88 confirmados en PNG; W84 refutado en
> iconos (gap mo↔dproc 144px ≥ 48) pero válido en labels; W86 matizado
> (los hijos de Indirectos ya salen en grilla 2×2 — gg/sup y=381, seg
> y=502; falta el pulido de labels internos).

### BUGS-ROUTE-004: Diagonales de última milla (W85) ✅ RESUELTO (2026-08-11) — eran los EMPALMES de las bandas de journeys (4→0, empalme ortogonal en build_journey_points; tests/test_journeys.py)
**Componente**: `routing/` (spread de puertos / reconstrucción V80)
**Reportado**: 2026-08-11 (grupo W; verificado: 4 segmentos con Δx>8∧Δy>8
en el presupuesto — p.ej. 335,463→375,415 y 877,463→837,415)

H24 prohíbe diagonales pero el reparto de puertos y las reconexiones
dejan tramos oblicuos cortos cerca de los extremos, pese a
`preference: "vertical"`. **Deseo W85**: toda arista ortogonal entra y
sale perpendicular al borde; el desplazamiento lateral se absorbe en un
codo a ≥14px del borde. Audit H24 extendido: cero segmentos Δx>8∧Δy>8.

---

### WISH-DRAW-006: Higiene de bandas de journeys (W83) ✅ RESUELTO (2026-08-11) — el encierro ya no existía (re-medido: 0 violaciones); longitudes 1.07/1.11/1.20 (el 1.20 = cruces ortogonales legítimos). Residuo: _audit_band_hygiene NOMBRA banda que pisa icono ajeno o pasea >1.25×
**Componente**: `draw/primitives/journeys.py`
**Reportado**: 2026-08-11 (grupo W; verificado en PNG: la banda roja
encierra a Mano de Obra en su arranque)

La banda (a) empieza y termina bajo el icono de su nodo extremo, sin
lazos ni U-turns; (b) entre nodos consecutivos toma el corredor de menor
longitud (la polilínea de SU conexión, U74) sin desvíos; (c) ningún
icono/label ajeno queda dentro del trazo (distancia icono↔eje > ancho/2
+ 8px). Métrica: longitud de banda ≤ 1.15× la suma de sus conexiones.

---

### WISH-ROUTE-004: El tramo que atraviesa el label de su propio extremo se ve y se resuelve (W87) ✅ RESUELTO (2026-08-11) — los 5 cruces eran todos PROPIOS (cero ajenos): exención abierta en detector (canal label_own_line, §H6) y score P61 (peso 0.5); candidatos negativos muertos. 5→3, restantes NOMBRADOS
**Componente**: `routing/visibility_graph.py` (mapa de obstáculos)
**Reportado**: 2026-08-11 (grupo W; verificado en PNG: la dashed
resumen→cron atraviesa «Cron. Val. / desde hitos H1–H7»)

Los bboxes de labels (propios y ajenos) entran al mapa de obstáculos con
margen de 4px; la llegada elige un puerto cuyo tramo final no cruce el
label del propio destino. Métrica de audit nueva: intersecciones
segmento↔bbox de label (hoy no se cuenta).

---

### WISH-LAYOUT-018: La franja del journey es zona a evitar para labels ajenos (W84/W86) ✅ RESUELTO (2026-08-11) — iconos y contenedores ya cumplían (verificado); labels bajo banda ajena 2→0 (P61 puntúa franjas desde _journeys; sin lado limpio se nombra)
**Componente**: `strategies/auto/` (colocación), `container_calculator`
**Reportado**: 2026-08-11 (grupo W, re-medido: los ICONOS ya cumplen —
gap mo↔dproc 144px; los hijos de Indirectos ya salen en grilla 2×2)

Lo que queda de W84/W86 tras la re-medición es de LABELS: el canal
entre la columna de una cadena y la vecina debe quedar libre también de
labels (si el label no cabe, K37 lo recoloca antes de invadir); y los
labels internos de contenedor no deben rozarse entre sí. Métrica:
ningún bbox de label intersecta el canal de otra cadena ni otro label
dentro de un contenedor.

---

### WISH-LAYOUT-019: El journey es primitivo de COLOCACIÓN (W88) ✅ RESUELTO (2026-08-11) — contratos de columna derivados por journey (exclusivos, por-miembro, empuje en cadena, el autor gana); dispersión construcción 195→0 · procura 94→5 · ingeniería 154→0; bandas rectas como consecuencia
**Componente**: `strategies/auto/positioner.py`
**Reportado**: 2026-08-11 (grupo W; verificado: mo —cadena
construcción— colocado junto a la columna de procura)

Cada journey reclama una columna/corredor propio (perpendicular al
flow): miembros exclusivos dentro, ordenados por posición en el path;
nodos compartidos en la confluencia; no-miembros fuera. El orden de
columnas sigue `journeys[]` salvo near/avoid. La banda casi recta (≤2
codos por tramo) sale como CONSECUENCIA, no como parche. Es el cambio
de fondo del grupo W: hoy los journeys pintan sobre un placement que
los ignora.

---

### WISH-ARCH-006: Derivabilidad — el JSON mínimo que debería bastar (W89) 🆕 ABIERTO — mediano plazo
**Componente**: transversal (positioner + router + spec)
**Reportado**: 2026-08-11 (grupo W, referencia orientativa — «la última
palabra la tiene Claude Code al implementar»)

Test de éxito del grupo W: el presupuesto pasaría de ~470 a ~200 líneas
— cada línea restante es una decisión, no un parche. Se derivan:
`canvas.width/height` (O51), `routing{}` ×19 (H24/W85 default),
la leyenda de estados (V82), y 4 de 5 `align[]` (hermanos que convergen
= fila; padres del sumidero = capa de resúmenes vía W88/V80; hijos del
sumidero = salidas; columna del tronco = G21/W88). Queda declarado sólo
lo no-derivable (la fila base que cruza profundidades — preferencia
genuina). Verificación: el fixture reducido y el completo emiten el
MISMO SVG; si difieren, se documenta la derivación faltante o el campo
se declara no-derivable.

---

> **Tanda 2026-08-11 — grupos X e Y del artefacto de Claude Design**
> (caso tabernero, paquete GAG-WV: 57 elementos, 75 conexiones, 9 `areas`
> con `members`, 3 journeys, SDJF 2.0). Todos los claims medibles fueron
> VERIFICADOS por ejecución contra master v3.11.0 antes de ticketear:
> estrategia hier, cruces=247, arista×nodo=37, labels=0, aspecto=14.36,
> lámina 11129×893, 9 títulos de área en y=58 (una sola fila), exit
> code 0 pese a §O52 violado + 8 avisos W83. Referencia visual del
> artefacto: la misma lámina cabe en 2600×1700 (aspecto 1.53) con
> macro-grilla de 3 bandas y bus TI perimetral. Grupo X = iteración 11;
> grupo Y = consolidación arquitectónica (decisión de José pendiente).

### BUGS-VAL-007: Aceptación silenciosa de constructos no soportados (X90) ✅ RESUELTO (2026-08-11) — audit_schema al cargar nombra claves desconocidas por superficie + spec_version; destapó claves MUERTAS en fixtures propios (priority ×7, canvas.background ×3 — quitadas); guarda de falsos positivos sobre los 40 archivos del repo
**Componente**: `generator.py` / validación de entrada (capa nueva)
**Reportado**: 2026-08-11 (grupo X; verificado: 0 menciones en el log)

El tabernero declara `spec_version: 2.0`, `areas[].members`,
`canvas.legend` y prescinde de `canvas.width/height` — y el motor no dijo
UNA palabra sobre qué entendió, qué ignoró y qué hizo a medias (dibujó
las 9 cajas de área pero las tendió en fila; X91). Principio X90:
**constructo declarado = renderizado o error explicable, nunca
silencio**. Falta una pasada de validación de schema al cargar que nombre
cada clave desconocida o no soportada por la estrategia elegida
(`[schema] areas[].members no soportado por strategy=auto` o similar),
y que declare la `spec_version` que el motor entiende.

---

### BUGS-VAL-008: El contador `labels` es CIEGO en vistas agrupadas (X93) ✅ RESUELTO (2026-08-11) — dos mitades: bbox estructural sintetizado en el detector (get_structural_label_bbox espeja draw_area_node_labels) + quality_counters mide bajo demanda cuando nadie pobló _collision_pairs (hier reportaba 0 SIEMPRE); tabernero 0→113 sincerado con geometría idéntica
**Componente**: `layout/collision.py` + `strategies/auto/anticollision.py::seed_label_truth`
**Reportado**: 2026-08-11 (grupo X; verificado: 28 pares reales con labels=0)

El LOG del tabernero reporta `labels=0` mientras el SVG tiene **28 pares
únicos** título-de-nodo ↔ label-de-arista solapados o a <11px (medidos
sobre el SVG emitido; el artefacto contó 19 con otro método — ambos ≫ 0).
Causa localizada: en vistas agrupadas (§I27/§I28) las etiquetas de nodo
son estructurales (`draw_area_node_labels`) y NO viven en
`label_positions` (`anticollision.py:119-125`) — el detector jamás las
ve. La cifra oficial miente exactamente en la vista que más la necesita.
El contador debe medir las etiquetas estructurales como bboxes de
verdad (aunque no sean reubicables) para que `labels` cuente TODO solape
dibujado.

---

### WISH-LAYOUT-020: El ÁREA como unidad de layout — macro-colocación bidimensional (X91) ✅ RESUELTO (2026-08-11) — _macro_rows: fila única sana se queda (fixtures estables); si viola §O52, envoltura a aspecto ~1.5 (jamás 1×N); area.role declara banda; ruteo inter-área por eje dominante; tabernero 14.36→0.75 y cruces 247→203
**Componente**: `strategies/auto/zones.py` + `generator.py::select_strategy`
**Reportado**: 2026-08-11 (grupo X; verificado: 9 áreas en una fila, aspecto 14.36)

Con 57 nodos y 9 áreas el motor tendió las 9 cajas en UNA fila →
11129×893 (aspecto 14.36, §O52 fuera de rango), cruces=247,
arista×nodo=37. Criterio X91: sobre un umbral (~30 nodos o ≥4 áreas) el
layout debe operar en DOS niveles — grafo condensado de áreas (un
nodo por área, aristas ponderadas por conexiones inter-área) y
macro-colocación BIDIMENSIONAL envuelta al aspecto objetivo (jamás
1×N), con sub-layout normal (A–W) dentro de cada caja. `area.role`
(`chain|feeder|control|overlay|external`) orienta la banda: control
arriba, cadena al centro, external abajo. Precedencia: `partition`
declarado (LAYOUT-021) > `role` > derivación. Referencia medida del
artefacto: mismo contenido en 2600×1700 (aspecto 1.53) con 3 bandas.

---

### WISH-LAYOUT-021: `canvas.partition` — macro-plano declarable (X91b) ✅ RESUELTO (2026-08-11) — schemes bsp (base + at/of, proporciones escaladas al contenido §P59) y grid; precedencia partition > role > derivación; plan inválido NOMBRADO con caída al siguiente nivel; tabernero con el plan de 4 bandas: cruces 203→125
**Componente**: formato SDJF + `strategies/auto/zones.py`
**Reportado**: 2026-08-11 (grupo X)

Cuando el autor SABE el plano que quiere, lo declara:
`canvas.partition` con `scheme: "bsp"` y `splits` de la forma
`{area, size, anchor/at, of}` — proporciones, no píxeles. El motor
coloca las áreas según el plano y hace sub-layout dentro. Enchufable
(`bsp` | `grid` | futuros como voronoi). Es la vía declarativa que gana
a la derivación de LAYOUT-020 (precedencia partition > role >
derivación) — mismo espíritu que align/near: contrato del autor.

---

### WISH-ROUTE-005: Hub multi-área = bus ortogonal con troncal y ramales (X92) ✅ RESUELTO (2026-08-11) — _route_bus: hub con destinos en ≥3 áreas sale UNA vez a una troncal en el corredor + ramal vertical por destino, nombrado en el log; los 3 hubs TI del tabernero (wan/erp/observabilidad) detectados y ruteados
**Componente**: `routing/` + troncales §P60
**Reportado**: 2026-08-11 (grupo X)

Un hub con ≥3 destinos en áreas DISTINTAS (en el tabernero: la capa TI
objetivo — ERP, observabilidad, ciberseguridad — con ~15 aristas dashed
que cruzan toda la lámina) debe rutearse como BUS: una troncal ortogonal
única a lo largo del corredor y ramales perpendiculares cortos hacia
cada destino, en vez de N rutas independientes que atraviesan el lienzo.
Referencia del artefacto: troncal única horizontal + ramales
perpendiculares, cero diagonales. Generaliza las troncales §P60 (hoy por
zona destino) al caso hub→multi-área.

---

### WISH-DRAW-007: Labels de aristas paralelas apilados en cascada (X93, mitad visible) ✅ RESUELTO (2026-08-11) — lo dibujado es lo medido (bbox del rótulo anclado EN el ancla); anclas §G23 con obstáculos (títulos estructurales + iconos + anclas ya puestas) y cascada de 14px por la PERPENDICULAR del primer segmento (±6 pasos); activacion 7→2 · ciclo-retrabajo 4→0 · es-primo 4→0 · layout-opt 16→9 · tabernero 145→123
**Componente**: `strategies/auto/anticollision.py` (P61)
**Reportado**: 2026-08-11 (grupo X)

Cuando varias aristas comparten corredor, sus labels deben apilarse en
cascada con separación vertical ≥14px (≈ una línea de 13px + aire), no
superponerse ni pelear el mismo punto medio. Depende de BUGS-VAL-008:
primero el contador tiene que VER los solapes en vistas agrupadas;
después P61 puede resolverlos apilando. Referencia: los labels en
cascada del render del artefacto.

---

### BUGS-LOG-001: `label_own_line` se calculaba pero jamás llegaba al log ✅ RESUELTO (2026-08-12)
**Componente**: `generator.py:360`
**Reportado**: 2026-08-12 (hallazgo del GAG Skiller, reporte v3.12 — verificado:
presupuesto con `label_own_line=4` en `quality_counters` y la línea `[auto]`
imprimiendo solo tres contadores)

`quality_counters` calcula el cuarto contador desde W87 (§H6) y su
docstring lo documenta, pero la línea de métricas armaba solo
`cruces/arista×nodo/labels` — la instrucción «leer 4 contadores» era
imposible desde el log. Fix: `own-line=N` en la línea, como canal de
diagnóstico; NO suma al umbral de WARNING (decisión §H6 intacta: no es
un solape de bboxes). Del mismo reporte: su segundo hallazgo («ni
`partition` ni `role` emiten log alguno» al salir de rango) quedó
REFUTADO por ejecución — §O52 SÍ advierte en sus dos casos (`aspecto
0.23/0.18 fuera de [0.4, 3.0]`); su arnés filtraba los WARNING. Sus
números de aspecto eran exactos y su guía («declarar de más empeora
láminas chicas — medir antes y después») quedó bien escrita en el skill.
Test: `test_emission_metrics.py` exige los 4 contadores en la línea.

---

### WISH-ROUTE-006: Ruteo por corredores de la macro-grilla ✅ RESUELTO (2026-08-12)
**Componente**: `strategies/hier/areas.py`
**Reportado**: 2026-08-12 (autodiagnóstico sobre el paquete GAG-WV del
tabernero: 101 de 123 pares `labels` eran rutas inter-área atravesando
cajas ajenas; los 4 W83 «0px» eran la banda siguiendo esas rutas)

La macro-grilla se descompone en filas y corredores (`_corridor_grid`);
toda ruta inter-área (bus incluido) viaja por los pasillos entre filas
y cruza cada fila intermedia por su hueco vertical (`_corridor_route`)
— jamás a través de una caja ajena. La última milla no atraviesa
hermanos: columna bloqueada → sale/entra por el costado
(`_exit_to_corridor`/`_enter_from_corridor`). Vecinos de la misma fila
sin obstrucción conservan la ruta directa; grilla no descomponible cae
al ruteo de LAYOUT-020. Medido (tabernero): arista×nodo 33→12, labels
123→51, W83 10→6 (los restantes son intra-área, otra causa). Tests:
`test_route006_corridors.py`.

---

### WISH-LAYOUT-022: Paso vertical label-aware en el sub-layout de áreas ✅ RESUELTO (2026-08-12)
**Componente**: `strategies/hier/areas.py::_sub_layout` + `hier/labels.py`
**Reportado**: 2026-08-12 (el amasijo del almacén en el visor GAG-WV:
títulos y ≈70%/≈30% montados — 20 pares intra-área)

Dos mitades: (1) §J30 reserva el corredor — si el subgrafo del área
lleva rótulos de arista, el paso vertical suma su línea (la lección de
LAYOUT-016 en hier/areas); (2) la cascada de anclas §G23 gana la
segunda dimensión — si la perpendicular no escapa de un título ancho,
el ancla se desliza A LO LARGO del segmento de a 14px hacia el aire que
el paso nuevo dejó. Medido: tabernero labels 51→33 (123 al abrir la
iteración 12); layout-optimization-flow 9→7; activacion aspecto
1.95→1.67 con labels igual. PNG verificado: el almacén se lee.

---

### BUGS-LAYOUT-013: El honor V79 rechaza un align x FACTIBLE en grafos chicos densos 🆕 ABIERTO
**Componente**: `strategies/auto/positioner.py` (honor V79 / `_plan_column_entry`)
**Reportado**: 2026-08-12 (vista condensada del tabernero: 9 nodos, 18 aristas)

Repro: grafo de 9 nodos con un hub en nivel 0 que alimenta a casi todos
(la vista condensada por áreas del tabernero). Un `align` x de tres
miembros en rangos DISTINTOS (1-2-3, encadenados A2→A3→A4) — factible en
principio — termina en `[CONSIDERACIONES] no se pudo cumplir` y el audit
nombra los ids desalineados (A2=142 · A3=380 · A4=86). El mismo contrato
funciona en el presupuesto (5/5 aligns, grafos más grandes y ralos).
Sospecha: en grafos chicos y densos el empuje en cadena no encuentra
lugar o el loop de optimización deshace la columna después del honor.
Pendiente de diagnóstico con el repro guardado (scratchpad,
tabernero_areas.sdjf con considerations align x A2/A3/A4).

---

### WISH-LAYOUT-025: Escenografía asistida — la derivación que confiesa su plan ✅ RESUELTO (2026-08-12)
**Componente**: `strategies/hier/escenografia.py` + `main.py` (`--sugerir-escenografia`)
**Reportado**: 2026-08-12 (principio de Escenografía del autor: «las áreas
se definen antes que la historia»)

El motor MIDE el contenido de cada área (sub-layout sobre copias),
CONDENSA el grafo (quién habla con quién y cuánto), LEE las señales
narrativas (roles declarados → bandas; el journey condensado más largo →
columna vertebral; alimentadores arriba y destinos abajo por balanza de
salidas/entradas hacia la columna; hubs ≥3 áreas → bandas de ancho
completo) y emite un `canvas.partition` con proporciones fieles al
contenido (unidad 150px — ninguna celda domina la escala) y las razones
NOMBRADAS. Recomienda, jamás impone (§R): JSON a stdout para
pegar/ajustar/ignorar. Medido: la sugerencia sobre el tabernero rinde
como la escenografía manual (aspecto 1.33 vs 1.32, arista×nodo 11 vs 12)
sin intervención humana. Tests: `test_layout025_escenografia.py`.

---

### WISH-ROUTE-007: Carriles dentro del corredor — las rutas no se montan ✅ RESUELTO (2026-08-12) — v2 mismo día: carriles también en las VERTICALES LATERALES de salida/entrada (el ± AREA_GAP/2 junto al borde era compartido — la mostaza seguía montada) + quiebres CURVOS (corner_radius 12 en rutas de corredor, idea del autor: la curva dice «doblo», el cruce seco dice «cruzo» — el mecanismo _draw_rounded_polyline ya existía y nadie lo pedía)
**Componente**: `strategies/hier/areas.py` (router de corredores)
**Reportado**: 2026-08-12 (el autor, sobre el showcase del tabernero: «las
líneas comparten los mismos carriles exactamente, no permite
diferenciarlas»)

Todas las rutas usaban la línea CENTRAL del pasillo (`corr_ys[i]`) y el
mismo hueco de cruce: las independientes quedaban montadas una sobre
otra. Registro de carriles (_make_lanes): la primera ruta de cada
corredor va al centro y las siguientes alternan ±9px (tope ±27); los
huecos verticales igual. Los ramales de un MISMO bus comparten CLAVE de
carril — la troncal superpuesta sigue siendo adrede (X92). La lección
U75 de los flows aplicada al corredor. PNG verificado: cada línea del
showcase es rastreable. Fixtures: métricas idénticas.

---

### WISH-LAYOUT-026: El hub va al MEDIO — banda central para el que conecta con todo ✅ RESUELTO (2026-08-13)
**Componente**: `strategies/hier/areas.py` (`_ROLE_BAND`) + `strategies/hier/escenografia.py`
**Reportado**: 2026-08-13 (el autor, sobre el PDF del showcase en GAG-WV:
«el área de arquitectura que se conecta con tantas cosas debería estar
al medio»)

La escenografía asistida mandaba los hubs (≥3 áreas destino) al FONDO
como banda de ancho completo: cada ramal cruzaba la lámina entera y el
tráfico se apilaba en los márgenes. Dos cambios: (1) `_ROLE_BAND` gana
`hub: 2` — role declarable que coloca el área en banda MEDIA, entre la
cadena y las externas; (2) `suggest_partition` emite los hubs como
bandas CENTRALES entre la columna vertebral y los destinos, con la
razón nombrada («el hub va al medio, cerca de todo»). Showcase del
tabernero medido: labels 6→4, cruces 15→14, ramales cortos en ambas
direcciones y margen izquierdo descongestionado. Resto honesto: el haz
spine→destinos ahora cruza las bandas centrales por los corredores —
tráfico legítimo, cada línea sigue rastreable por su carril. Fixtures:
métricas idénticas.

---

### WISH-ARCH-009: Contenedores como miembros de área — convergencia áreas⇄contenedores ✅ RESUELTO (2026-08-18, iteración 14)
**Componente**: `generator.py::select_strategy` + `strategies/hier/areas.py`
**Reportado**: 2026-08-18 (el autor: «pensaba usar zonas y los humildes
contenedores que ya tenemos» — dos niveles bastan, sin super-zonas;
fase 3 del Mapa, WISH-ARCH-004 §10)

`contains` forzaba AUTO para todo el archivo y las áreas degradaban a
zonas near — el showcase_v2 (2 zonas + 9 contenedores) rendía sin marcos
y con los grupos entreverados. Tres cambios: (1) precedencia invertida
en `select_strategy` — `areas` + `contains` → hier, nombrado en §O53;
(2) el contenedor se MIDE bottom-up (`_measure_container`: sub-layout de
sus hijos + padding/header, espejo de ContainerCalculator, caja dibujada
= caja reservada vía `_is_container_calculated`) y entra a la grilla del
área como nodo gordo (`_fat_sub_layout`: niveles sobre el grafo
condensado hijo→contenedor, filas por nivel, empaque por anchos reales);
(3) los hijos heredan el área de su contenedor y el ruteo funciona en
los tres niveles: intra-contenedor (A–H local), miembro→miembro dentro
del área (puertos en el hijo real, corredor T71 en miniatura) e
inter-área (corredores/carriles/curvas de ROUTE-006/007 intactos).
Guarda de regresión: un área sin contenedores sigue el camino viejo
byte a byte; fixtures idénticos. Showcase_v2 medido: 2 marcos + 9
contenedores en su zona, aspecto 1.28, labels 4. v1 con límite
nombrado: un nivel de anidamiento (contenedor-en-contenedor cae a
icono con WARNING). Tests: `test_arch009_areas_contains.py` (6).

**v2 mismo día** (el autor, sobre el render en GAG-WV: «mira las rutas
y las distribuciones»): (a) las tomas laterales del condensado (nivel
0.5) comparten fila ENTERA — la fila propia apilaba la cadena en
columna 1×N (tinta 33.1%→40.2%, cadena en 2 columnas); (b) pasada
`_dodge_boxes` tras el ruteo — un segmento que cruza un contenedor
ajeno de lado a lado se desvía por su borde (+12px, iterado), el que
ENTRA a una caja para rematar en su hijo se respeta (T71). Medido:
arista×nodo 8→0, labels 4→0.

**v3 mismo día** (el autor: «la distribución de los contenedores podría
mejorar para que eviten menos cruces»): instrumentado el showcase par a
par — de 13 cruces reales de trazado, 7 los causaba UNA línea
(r_a1→r_a5) bajando por el pasillo central del área. Los enlaces
intra-área que saltan ≥2 filas entre miembros que tocan un mismo borde
van ahora por el CANAL LATERAL del área (margen libre por construcción
del empaque por filas; escalonado 8px si comparten canal). Medido:
cruces reales de trazado 13→6; los 6 restantes son topológicos (la
horizontal 8→3 contra los descensos de 7 y 9 en el corredor). Hallazgo
colateral fichado: BUGS-LOG-002.

---

### BUGS-LOG-002: `cruces(arista×arista)` mide centros, no el trazado dibujado ✅ RESUELTO (2026-08-18)
**Componente**: `layout/metrics.py::count_crossings`
**Reportado**: 2026-08-18 (destapado por ARCH-009 v3: los cruces reales
bajaron 13→6 y la métrica quedó clavada en 27)

`count_crossings` cuenta cruces entre segmentos RECTOS centro-a-centro
de los iconos (herencia del abstract_placer de LAF) — ignora
`computed_path`. Era razonable cuando el trazado seguía al centro; con
corredores, carriles, curvas y canales laterales, lo dibujado ya no se
parece al segmento abstracto: la métrica ni premia el ruteo bueno ni
castiga el malo. Viola «lo dibujado es lo medido» (doctrina VAL-008).
Criterio: cuando una conexión tiene `computed_path`, contar cruces
sobre la polilínea real (compartir extremo sigue sin ser cruce; la
troncal superpuesta de un bus X92 tampoco). Requiere recalibración
única de la línea base de fixtures (patrón It6-2c) — por eso se fichó
en vez de arreglarse al paso: decisión de José sobre cuándo pagar esa
recalibración.

**Resolución** (luz verde de José, mismo día): `count_crossings` mide
el trazado real vía `_conn_segments` (el mismo que usa arista×nodo §H6)
con `_strict_cross` — cruce = intersección INTERIOR de segmentos;
tocarse en extremo, en T o solaparse colineales (carriles, troncal de
bus) no cuentan. Recalibración única medida: 13 fixtures cambian SOLO
el campo cruces, 12 bajan (15→5, 24→7, 36→19, 16→4, cuatro 1→0…) y
UNO sube (git.sdjf 5→6 — un cruce genuino del trazado que el segmento
abstracto no veía: la ceguera denunciada, en la otra dirección). El
showcase_v2 del pipeline real da cruces=0 (con labels envueltos, los 6
«topológicos» de la geometría cruda tampoco ocurren). Suite 634 verde
sin recalibrar ningún test — ninguno fijaba valores absolutos.

---

### WISH-ROUTE-008: Abanicos por origen en la vía directa + desvíos escalonados ✅ RESUELTO (2026-08-18)
**Componente**: `strategies/hier/areas.py` (vía directa L/R·T/B, `_route_fat_conns`, `_dodge_boxes`)
**Reportado**: 2026-08-18 (el autor, con el resaltado de rutas de GAG-WV
sobre el showcase_v2: «los enlaces siguen superponiéndose»)

Tres coladores de superposición que los carriles de ROUTE-007 no
cubrían, medidos con instrumento de solapes colineales (52 pares, hasta
1381px montados): (1) la vía DIRECTA entre cajas enfrentadas (misma
fila / sin grilla) era anterior a los carriles — todas las rutas de un
par de zonas compartían la vertical del corredor; (2) todas las
entradas/salidas de un mismo hijo usaban el MISMO punto de puerto;
(3) dos rutas que rodeaban la misma caja (dodge) caían en la misma
línea de desvío. Política de ABANICO por origen (la del bus X92): las
rutas de un mismo origen comparten troncal (superposición adrede — una
línea que se ramifica; el carril por-ruta las trenzaba: 0→19 cruces
medidos y descartado), orígenes distintos van en carriles distintos,
las entradas a un mismo destino se reparten por origen en el borde del
icono (T72 en miniatura) y los desvíos se escalonan +7px por caja+lado.
Medido en el showcase: superposición entre orígenes distintos 52→6
pares (536px residuales, cortos); los cruces reales suben 0→22 porque
el contador nuevo (BUGS-LOG-002) ya no puede confundir un montón
colineal con «cero cruces» — antes estaban montados, ahora se ven y se
cuentan. Fixtures idénticos (la grilla de corredores no pasa por la vía
directa).

---

### WISH-LAYOUT-027: La tabla de conectividad — el motor confiesa la cohesión ✅ RESUELTO (2026-08-18)
**Componente**: `strategies/hier/escenografia.py` (`connectivity_table`, `_build_area_of`)
**Reportado**: 2026-08-18 (el autor llegó con la tabla armada A MANO en
Excel: enlaces internos | entre áreas | área, por elemento — el análisis
que el motor debería regalar)

Dos piezas: (1) BUG curado — la escenografía asistida era CIEGA al
patrón zona+contenedor (ARCH-009): las conexiones viajan entre HIJOS y
`area_of` sólo mapeaba miembros, así que el grafo condensado quedaba
vacío («G2 alimenta: 0 salidas vs 0 entradas» con 11 enlaces reales);
`_build_area_of` hereda el área del contenedor a sus hijos y la
dirección se mide (11 vs 0). (2) `connectivity_table` emite la tabla
del autor en `--sugerir-escenografia` — por elemento conectado,
internos | entre-áreas | área — con hallazgos nombrados: elemento con 0
internos y ≥3 externos = «hub puro: su membresía es narrativa, no
estructural (candidato a role 'hub' o al borde)»; área con más enlaces
hacia afuera que adentro = «más pasillo que casa». Verificado contra el
Excel del autor: coincidencia 100% en los 9 elementos del showcase_v2
(r_a7: 0|5 hub puro; G2: 1 interno contra 11 afuera). Tests:
`test_layout025_escenografia.py` (+2).

---

### BUGS-ROUTE-005: Entradas al punto idéntico en la vía por corredores ✅ RESUELTO (2026-08-19)
**Componente**: `strategies/hier/areas.py::_enter_from_corridor`
**Reportado**: 2026-08-19 (el GAG Skiller, reporte v3.16, con repro
`abanico.sdjf`: «dos rutas de orígenes distintos llegan al mismo punto
exacto (1302, 314)» — y con la hipótesis correcta: «quizá la política
aplique solo a la vía directa y estas rutas estén tomando corredor»)

CONFIRMADO ejecutando su repro: ROUTE-008 repartió los puertos de
entrada sólo en la vía DIRECTA entre cajas enfrentadas;
`_enter_from_corridor` (la vía por corredores de la macro-grilla,
ROUTE-006) seguía entregando el centro exacto del borde del icono a
toda ruta entrante — D0 recibía O1 y O2 en (102, 314), D3 recibía O2 y
O3 en (1302, 314). Fix: la entrada se desplaza por el carril de la ruta
(canal ('p', hijo), ±30px en T/B, ±18px en entradas laterales) — mismo
contrato T72-en-miniatura de la vía directa. Verificado sobre el repro
del Skiller: 102 vs 111, 1302 vs 1311 — cero puertos duplicados.
Fixtures idénticos (ningún fixture tiene dos orígenes entrando al mismo
hijo por corredor). Test: `test_route006_corridors.py::
test_entries_to_same_node_get_distinct_ports`.

---

### WISH-ARCH-007: SDJF 2.0 — spec formal con una sintaxis canónica (Y94) 🆕 ABIERTO — mediano plazo
**Componente**: formato SDJF + `docs/spec/FORMATO_ARCHIVOS.md`
**Reportado**: 2026-08-11 (grupo Y — requiere decisión de José: hay deprecaciones)

Formalizar el formato: campo `spec_version` reconocido; JSON Schema
versionado EN el repo (validable por terceros); UNA sintaxis canónica
por concepto — `areas[].members` canónico y `element.contains` azúcar
que se normaliza al cargar. Deprecar con aviso `[deprecated]` durante
una versión antes de retirar: `routing{}` por conexión (BUGS-ROUTE-003
la honra, pero la meta es derivarla), `canvas.width/height` (O51 los
deriva), color por conexión (theme §O57 los deriva).

---

### WISH-VAL-001: El audit es COMPUERTA, no comentarista (Y95) 🆕 ABIERTO — mediano plazo
**Componente**: `validation/` + `main.py` (exit codes)
**Reportado**: 2026-08-11 (grupo Y; verificado: exit 0 con §O52 violado + 8 W83)

Hoy el motor emite el SVG y devuelve exit 0 aunque sus propios audits
griten (tabernero: aspecto 14.36 fuera de [0.4, 3.0] y 8 bandas sobre
nodos ajenos). Criterio Y95: umbrales DUROS (aspecto fuera de rango,
arista×nodo>0, banda-sobre-nodo, label-solape, near/align violado,
schema inválido) disparan un bucle de reparación de N intentos; si no
se sanan, exit code ≠0 y SVG marcado DRAFT (visible en la lámina). El
CI del repo falla ante duros nuevos. Requiere decisión de José: cambia
el contrato del CLI para todo usuario.

---

### WISH-DRAW-008: Journeys = capa de presentación pura post-layout (Y96) 🆕 ABIERTO — mediano plazo
**Componente**: `draw/primitives/journeys.py` + `strategies/auto/positioner.py`
**Reportado**: 2026-08-11 (grupo Y)

Contrato de idempotencia: el MISMO archivo con y sin `journeys` produce
la MISMA geometría de iconos y aristas — la única influencia legítima de
un journey sobre el layout es la membresía W88 (columnas derivadas,
LAYOUT-019), y esa influencia debe ser idéntica se dibuje o no la banda.
Test diferencial: render con journeys vs. render sin la sección → los
elementos no se mueven ni un píxel.

---

### WISH-ARCH-008: Parejas de conformidad mínimo≡completo en CI (Y97) 🆕 ABIERTO — mediano plazo
**Componente**: `tests/` + fixtures
**Reportado**: 2026-08-11 (grupo Y; hermano operativo de WISH-ARCH-006/W89)

Por cada fixture de referencia, DOS archivos: el mínimo (solo decisiones)
y el completo (todo explícito). CI verifica que ambos emiten el MISMO
SVG. Es el mecanismo de verificación continua de la derivabilidad
WISH-ARCH-006: cada divergencia es o una derivación faltante o un campo
que debe declararse no-derivable — y el par de archivos lo documenta
solo.

---

### Recalibración O56 (iteración 9): escala tipográfica 14/12/11 → 16/13/12 ✅ (2026-08-11)

Con la lámina ya compacta (LAYOUT-016), el contrato tipográfico sube a
nodo 16 · conexión 13 · rótulo 12 bold; `TEXT_CHAR_WIDTH` (8→9.2) y
`TEXT_LINE_HEIGHT` (18→20.6) escalan para que la estimación de labels
siga siendo VERAZ. Los `11px` hardcodeados en phase_areas/journeys/svg
pasaron a `FONT_SIZE_ZONE` (los cazó el test O56 estricto). Acompañante:
el honor V79 puede APARTAR al vecino que bloquea la columna si no es
contrato (align x/contenedor) y su fila lo permite — el contrato del
autor gana sobre la posición estética del vecino; el honor corre ahora
ANTES de los snaps V80/casi-alineados. Medido: presupuesto 2→0 cruces y
5/5 aligns; labels BAJAN en cadena con la re-medición veraz
(arquitectura 13→8, físico 15→12, git 12→11).

---

### BUGS-VAL-005: Falso positivo R1 en contenedores chicos (zona de 2 miembros) ✅ RESUELTO (2026-08-11)

> **Causa raíz** (geometría medida, no estimada): el rect del contenedor
> se emite con `fill="url(#gradient-<id>)"` — sin la marca `_container`
> que el filtro del validador buscaba — y su único descarte restante era
> el tamaño (>300×200). La zona de 2 miembros mide 200×153: el validador
> la contaba como ICONO y todo texto interior «solapaba un icono» —
> `'Equipo 0'` 64×16.2 ≈ 1035px², exactamente el área reportada. Con 3-4
> miembros la zona supera los 300px y se salvaba por casualidad. El
> Skiller tenía razón: falso positivo, la geometría real deja 6px de
> aire entre label e icono.
> **Fix por contrato, no por heurística**: el rect del contenedor viaja
> con `class="ag-container"` (renderer) y el validador lo excluye;
> fallback para SVGs viejos: rects con `fill-opacity < 0.9` (los
> contenedores dibujan translúcido, los iconos opacos). Verificado con
> control positivo crafteado: un R1 real sigue saltando. Regresión en
> `tests/test_visual_quality.py`.

**Componente**: `AlmaGag/validation/visual_quality.py` (R1)
**Reportado**: 2026-08-03 por el GAG Skiller; re-confirmado 2026-08-11 con motor 3.9.0

Zona near con 2 miembros → 3×R1 (`'Equipo 0'` solapa icono 1035px²,
`'Equipo 1'` 1035px², rótulo `'ZONA'` 583px²); con 3 y 4 miembros → 0
violaciones, con geometría visualmente indistinguible (dato del Skiller:
glifo-icono a 340px con 2 miembros vs 329px con 3). La métrica del motor
da labels=0 en los tres casos — el desacuerdo es del validador sobre el
SVG emitido, probablemente en la estimación de bbox de texto del caso
2-miembros (pitch más angosto). Repro: `zon2.sdjf`/`zon3.sdjf`/
`zon4.sdjf` del inventario del Skiller.

---

### BUGS-ARCH-002: Campos objeto que llegan como string matan la corrida con AttributeError crudo ✅ RESUELTO (2026-08-11)
**Componente**: `AlmaGag/generator.py` (normalización de entrada)
**Reportado**: 2026-08-11 (GAG Skiller: `routing: "orthogonal"` y
`roles: {"soc": "SOC Claro"}` — dos casos, mismo patrón)

Errores naturales de autor: `routing` espera objeto pero el string es la
intención obvia. **Fix**: coerción con aviso en `generate_diagram` —
`routing: "x"` → `{"type": "x"}`, `roles[k]: "x"` → `{"label": "x"}`,
routing de tipo inválido se ignora con aviso nombrando la conexión.
Nunca más un AttributeError sin contexto. **Nota del reporte 2 del
Skiller**: la coerción de `roles` pierde el color en silencio — el aviso
ahora lo NOMBRA («SIN color; declarar {"label", "color"} para
conservarlo»). De paso se migraron las dos
strings «Flujos:» que el rename v3.9 dejó en `journeys.py:194,229`
(mensaje de error y docstring — hallazgo del Skiller). Regresión en
`tests/test_v39_flow_rename.py`.

---

### WISH-ARCH-005: Consistencia del término «flow» — una palabra, un concepto ✅ RESUELTO (2026-08-11)
**Componente**: formato + CLI + `draw/primitives/journeys.py`, `layout/templates/steps.py`, `hier`, `svg.py`
**Reportado**: 2026-08-11 (revisión del autor: «flow» tenía 5 significados de cara al autor)

Decisión del autor (tabla acordada): «flow» queda reservado para
`canvas.flow` (dirección de lectura del grafo — el único uso literal);
todo lo demás se renombró, SIN alias retrocompatible pero con guardas
que ENSEÑAN (error/warning nombrando el reemplazo, centralizadas en
`generate_diagram`):

| Hasta v3.8 | Desde v3.9 | Concepto |
|---|---|---|
| `flows` (top-level) | `journeys` | Recorrido narrativo resaltado — módulo `journeys.py`, clase `ag-journey`, leyenda «Recorridos:» |
| `canvas.flow` | (queda) | Dirección de lectura up/down |
| `layout_template: "flow"` | `"steps"` | Cadena vertical de pasos (`steps.py`, `StepsTemplate`) |
| `--view flow` | `--view columns` | Vista plana de hier |
| `data_flow` / `control_flow` | `data_link` / `control_link` | Clase semántica del enlace (la leyenda ya decía «datos»/«control») |

La keyword `flow` del clasificador de templates NO se toca (lee texto
libre de labels, no es namespace; ganó `steps` como señal). Fixtures,
tests, spec (con tabla de desambiguación), glosario y motor migrados;
guarda 39/39 idéntica (los renames no mueven geometría); motor 3.9.0.
Regresión: `tests/test_v39_flow_rename.py`.

---

### WISH-LAYOUT-012: `canvas.flow` — la orientación cuenta la historia (V78) ✅ RESUELTO (2026-08-10)

> `canvas.flow: "up" | "down"` (default `down`). Con `up` el positioner
> invierte los rangos topológicos: fuentes como cimiento en la banda
> inferior, sumidero arriba, salidas derivadas como remate — la lectura
> natural de los roll-ups. `left`/`right` quedan reservados: WARNING
> honesto y se emite como `down`. El fixture `mina-presupuesto.sdjf`
> declara `up` y quedó como el render objetivo del review (captura
> abajo, consolidado arriba, salidas de presentación como corona) — de
> rebote cruces 2→0 (labels 1→2, texto-texto). Verificación del ticket
> cumplida: invertir `flow` produce el espejo exacto del orden de
> rangos (test diferencial). Espec: `docs/spec/FORMATO_ARCHIVOS.md` §1.
> Regresión: `tests/test_layout012_canvas_flow.py`.
**Componente**: `AlmaGag/layout/` (asignación de niveles), `docs/spec/FORMATO_ARCHIVOS.md`
**Reportado**: 2026-08-10 (artefacto Claude Design, grupo V — caso presupuesto)

El presupuesto se narra «de abajo hacia arriba: de los recursos al
consolidado», pero el motor rinde siempre top-down (fuentes arriba,
sumidero abajo) y no existe forma de declararlo. **Estándar propuesto**:
`canvas.flow: "up" | "down" | "left" | "right"` (default `down`).
Agregaciones/roll-ups usan `up`: banda de captura como cimiento,
consolidado arriba, salidas derivadas como remate. **Verificación**: con
`flow: "up"` las fuentes quedan en la banda inferior y el sumidero
principal arriba; invertir `flow` produce el espejo exacto. Repro:
`mina-presupuesto.sdjf` (hoy: `resumen` en y=1740, fuentes en y=45).

---

### WISH-LAYOUT-013: `align[]` es contrato, como near — audit duro y eje x (V79) ✅ RESUELTO (2026-08-10)

> Dos patas: (1) **honrar el eje x entre rangos** (positioner): un align
> de eje x cuyos miembros viven en rangos distintos es contrato de
> COLUMNA — se honra en el origen (mediana, con hueco label-aware en
> cada fila, todo-o-nada), porque la vía blanda guardada no podía
> moverlo; (2) **audit que nombra**: al final del pipeline, cada grupo
> align con desviación >1px sobre centros de icono se reporta
> `[align] grupo N (axis): ids desalineados — id=coord …` — nunca
> silencio. **Medido** (mina-presupuesto): 5/5 alineaciones cumplidas
> (el artefacto midió 2/5 pre-it7; 4/5 post-it7); el tronco
> dppto/ppto/constr quedó en una sola columna (x=652) con verticales
> puras. Guarda 39/39 intacta. Regresión:
> `tests/test_layout013_align_contract.py`.
**Componente**: `AlmaGag/layout/considerations.py`
**Reportado**: 2026-08-10 (artefacto Claude Design, grupo V)

El autor declaró 5 alineaciones; el motor actual (post-iteración 7)
cumple 4 y viola EN SILENCIO la de eje x (`[dppto, ppto, constr]` →
centros x 569/636/760). Pedido del review: (a) violación = aviso duro
del audit (`[align] grupo N: ids desalineados`), nunca silencio;
(b) si un align cruza cadenas de profundidad distinta, se honra
estirando la cadena corta con verticales limpias por su columna — no se
rechaza; (c) alinear por CENTROS de icono en el eje declarado
(desviación ≤1px). Medido con `mina-presupuesto.sdjf` (4/5; el artefacto
midió 2/5 con el motor previo — la iteración 7 ya mejoró dos).

---

### WISH-ROUTE-002: Convergencia limpia — verticales por columna + puertos T72 en nodos (V80) ✅ RESUELTO (2026-08-10)

> Dos partes: (1) **columnas de eslabones** (positioner): un eslabón 1:1
> entre rangos consecutivos se alinea a la misma columna moviendo el
> extremo de grado 1, sólo si el hueco existe (pitch label-aware) — el
> repro del autor (pulab→mo, 161px de desfase con barrido bajo su propio
> label) quedó en desfase 0 con arista vertical pura y el label de vuelta
> en `bottom`. (2) **puertos T72 en nodos** (`route_node_ports`): cuando
> ≥2 conexiones ORTOGONALES llegan por el mismo lado de un nodo con
> puntas <18px o llegada tangencial, se reparten (≥PORT_MIN_SEP) y el
> tramo final se reescribe perpendicular vía carril a STUB px. Cirugía
> SOLO sobre la violación: grupos ya limpios, paths con diagonales
> (estilo straight legítimo: árboles, hubs) y salidas no se tocan — la
> primera versión sin esas puertas costaba +5 labels y +1 a×n en
> fixtures sanos. **Medido**: resumen recibe sus 3 cadenas con llegadas
> perpendiculares y puntas a 18/36/18px (antes 14/15px con ring
> tangencial barriendo el borde); guarda 39/39 intacta salvo +1 label en
> git (parte 1, caja densa preexistente). Regresión:
> `tests/test_route002_convergence.py`.
**Componente**: `AlmaGag/routing/`, `strategies/auto/`
**Reportado**: 2026-08-10 (artefacto Claude Design, grupo V)

Tres cadenas convergen en `resumen` desde profundidades 5/3/2; `ring`
queda a ~1451px (medido hoy) con su arista cayendo por medio lienzo.
Pedido: cada arista de convergencia viaja como vertical pura por el
corredor de su columna hasta un corredor horizontal corto adyacente al
padre común, y entra por puertos distribuidos en su borde — **T72
aplicado a NODOS, no solo contenedores**. Sin `align[]` declarado, los
padres de un hijo común se alinean al rango adyacente. Verificación:
cero diagonales en aristas de convergencia; puertos ≥18px; ninguna
arista de convergencia cruza otra columna.

**Aplica también a los ESLABONES de cada cadena** (el render objetivo lo
dice: «las cadenas suben por columnas propias con verticales puras»).
Repro concreto señalado por el autor (10-ago): `pulab→mo` — el padre
quedó en x≈311 y el hijo en x≈150 (161px de desfase), la arista sale
del icono, barre 133px horizontal a y=70 POR DEBAJO del propio label de
`pulab` (que el optimizador empujó a `left` por el mismo enredo) y
recién ahí cae. Con columnas alineadas, la arista es una vertical pura
y el label vuelve a su posición natural — los dos defectos son uno.

---

### WISH-LAYOUT-014: Contenedor-feeder = carril lateral, nunca rango del tronco (V81) ✅ RESUELTO (2026-08-10)

> En `_calculate_hierarchical_layout`: un contenedor cuya única relación
> con el grafo es UNA arista hacia un nodo primario no-contenedor se
> aparta del apilado por niveles y, tras el centrado global, se coloca al
> costado del rango de su destino (el lado de la arista más corta, fuera
> de lo ya tendido en su franja vertical, centrado en el destino).
> **Medido** (mina-presupuesto): dppto→ppto 635→290px (pitch normal),
> lienzo 1400×2205→1960, tinta 11.3→12.7%, aspecto 0.58→0.66; la arista
> del feeder quedó con 2 codos. Costo: +2 cruces (la arista lateral
> atraviesa las verticales de procura — territorio de WISH-ROUTE-002) y
> +1 label interno del contenedor. Resto de la guarda intacto (38/38).
> Regresión: `tests/test_layout014_feeder_container.py`.
**Componente**: `strategies/auto/positioner.py` (niveles de contenedores)
**Reportado**: 2026-08-10 (artefacto Claude Design, grupo V)

«Indirectos de obra» (gg/sup/seg → constr) se inserta como rango propio
dentro de la columna del tronco: `dppto→ppto` pasa de un rango a 635px
(medido hoy) con el contenedor en medio, y el lienzo crece a 1400×2205
(aspecto 0.58 — J33/O51). Pedido: un contenedor cuyo único rol es
alimentar a un nodo del tronco se coloca AL COSTADO del rango de su
destino (lado libre), con arista corta perpendicular al borde —
generaliza el carril de feeders a contenedores. Verificación: la
distancia entre rangos consecutivos del tronco no cambia al agregar el
contenedor; su arista al destino tiene ≤2 codos. Repro:
`mina-presupuesto.sdjf`.

---

### WISH-DRAW-004: `canvas.legend[]` y `element.status` como constructos de primera clase (V82) ✅ RESUELTO (2026-08-10)

> `element.status: ok|partial|empty` → badge ◉◪▢ que se antepone a la
> ÚLTIMA línea del label y la colorea (verde/ámbar/gris) en el dibujo —
> el autor ya no pinta glifos a mano (`draw_icon_label`, STATUS_BADGES).
> `canvas.legend[]` → leyenda libre al pie (string o {label, color} con
> swatch redondo), apilada con «Enlaces:»/«Flujos:»
> (`draw_canvas_legend`). El fixture del presupuesto quedó reescrito con
> los constructos (21 status + leyenda de 3 estados, glifos fuera de los
> labels) y emite el mismo visual sin el hack f4 — que la otra mitad del
> ticket (U74/U77, iteración 7) ya cazaba como error. Espec:
> `FORMATO_ARCHIVOS.md` (§1 canvas.legend, §2 element.status). Guarda:
> sólo la línea del presupuesto (labels 2→1: los labels perdieron los
> glifos pintados). Regresión: `tests/test_draw004_legend_status.py`.
**Componente**: `AlmaGag/draw/`, `docs/spec/FORMATO_ARCHIVOS.md`
**Reportado**: 2026-08-10 (artefacto Claude Design, grupo V)

El autor necesitó una leyenda de estados y la metió con un hack: flow
blanco `f4` con `path: [resumen, resumen]`. **La mitad audit YA ESTÁ**:
el contrato U74/U77 (iteración 7) caza el hack con error duro
(verificado ejecutando el archivo original). Falta el estándar que lo
reemplace: `canvas.legend[]` (entradas texto+swatch libres) y
`element.status: "ok" | "partial" | "empty"` con badge ◉◪▢ que colorea
la línea de estado (verde/ámbar/gris) sin que el autor lo pinte a mano.
Verificación: el fixture reescrito con legend+status emite el mismo
visual sin el flow f4.

---

### WISH-DRAW-003: Flows — carriles paralelos y contrato de autoría (grupo U del review) ✅ RESUELTO (2026-08-05)

> Tres commits, uno por criterio:
> **U74/U77** — contrato de autoría: par consecutivo sin conexión
> declarada, id inexistente o flujo sin `label` son ERROR DURO
> (ValueError); color repetido y >4 flujos por lámina, WARNING. La
> conexión declarada que se dibuja recta sigue esa misma recta — cero
> geometría propia. El fixture minero corrigió su flow `facturacion`
> (arrancaba en `cuadrillas` sin arista).
> **U75** — `build_flow_lanes`: tramos compartidos repartidos en
> carriles perpendiculares (paso = FLOW_WIDTH, orden estable por
> aparición, normal canónica por tramo — consistente aunque dos flujos
> recorran el tramo en sentidos opuestos); ninguno tapado.
> **U76/J33** — grafo-cadena (≥5 eslabones, un elemento por nivel)
> plegado en serpentina boustrophedon de ceil(sqrt(2n)) columnas en el
> positioner; se saltan barycenter y layer-offset en ese caso. Cadena de
> 8: 2 filas de 4, apaisada (antes 1×8 vertical).
> Guarda intacta (39/39) en los tres; regresión: `tests/test_flows.py`
> (contrato + carriles) y `tests/test_u76_chain_serpentine.py`.

**Componente**: `draw/primitives/flows.py`, `strategies/auto/positioner.py`
**Reportado**: 2026-08-05 (artefacto Claude Design, grupo U — caso telefonía)

`flows` quedó bien concebido (U76 «no altera el layout» ya está
garantizado por test diferencial) pero el review pide tres refinamientos:

- **U74 — cero geometría propia**: el overlay debe seguir SIEMPRE los
  waypoints de la conexión del par. Hoy un par sin conexión declarada cae
  a tramo recto en silencio — exactamente las «cintas rectas» que el
  review denuncia. Con U77 el fallback deja de ser silencioso.
- **U75 — tramos compartidos = carriles paralelos**: offset perpendicular
  por flujo (±½ ancho por carril, orden estable por aparición); N flujos
  sobre un tramo común se ven lado a lado, ninguno cubierto >10%.
  Hoy los colores se superponen y el de abajo desaparece.
- **U77 — contrato de autoría + audit**: error duro
  `[flows] par (a,b) sin conexión declarada` (hoy: warning sólo por ids
  inexistentes); warning si dos flujos comparten color; `label`
  obligatorio (va a la leyenda). Recomendación de autoría: ≤3-4 flujos
  por lámina.

**Nota U76 (mitad layout)**: el caso telefonía (grafo-camino de 8 nodos)
salió 1080×2400 con ~60% de vacío — el patrón tira-1×N que J33/O51
prohíben. La compactación de cadenas es asunto del layout (ver
WISH-LAYOUT-010/ROADMAP), no de flows.

---

### WISH-LAYOUT-010: Presupuesto de espacio por contenedor — miembros sobre el header y congestión interna ✅ RESUELTO (2026-08-05)

> Resuelto en la pasada anticolisión (§P61), no en el reparto del
> positioner: (a) el TÍTULO del contenedor (icono + texto real, espejo del
> renderer) es zona DURA para las etiquetas de sus propios miembros —
> ningún candidato lo pisa y una posición heredada sobre él se expulsa;
> (b) montarse sobre un ICONO puntúa ×2 frente a rozar otro texto (la
> violación R1 pesa más); (c) la pasada B suma candidatos AL COSTADO del
> conector (offset perpendicular ±26px) para zonas congestas. **Medido**
> (guarda completa): neto −5 labels (git 15→10, 06 −1, 09 1→0, cakephp
> −1; mina-arquitectura-fisica +2 y cheatsheet +1, ambos texto-texto);
> pares «sobre icono» (R1): físico v2 7→4, fisica 1→0, cheatsheet 12→9.
> El header de ZONA PILA quedó limpio (verificado en PNG). La banda dura
> a TODO el ancho se probó y se descartó: +6 en fisica por expulsar
> etiquetas que no pisaban texto visible. Regresión:
> `tests/test_layout010_container_budget.py`.

**Componente**: `strategies/auto/anticollision.py` (zona dura + score + candidatos)
**Reportado**: 2026-08-03 (caso real evolucionado; anonimizado en `mina-fisico-v2.gag`)

Con pitch label-aware y medición veraz cerrados, el residuo hacia
«0 fusiones» es de PRESUPUESTO DE ESPACIO dentro del contenedor. En el
fixture `mina-fisico-v2.gag` (17 cruces / 8 arista×nodo / 17 labels):

- El miembro `cco` (edificio) queda MONTADO sobre el propio header de su
  zona («CCO DC-204…» pisa «ZONA PILA - PAMPA COLORADA»): la banda del
  título no se respeta como zona prohibida para los miembros.
- Racimos internos: «7 estaciones fijas» × rótulo «FO inter-DC», «4
  estaciones fijas» × «energia provisional» — rótulos de conexión cuyo
  deslizamiento §P61 no encuentra hueco dentro de la caja.

**Dato medido clave** (confirma el hallazgo de la sesión externa del
3-ago): acortar TODAS las etiquetas a una línea apenas mueve la aguja
(17/8/17 → 18/7/14) — el cuello NO es ancho de etiqueta sino espacio
interno; la palanca «acortar labels» del skill aplica a grillas/bandas
libres, no a zonas congestionadas.

**Idea**: el alto/reparto interno del contenedor reserva presupuesto para
(a) la banda del header como zona dura, (b) corredores para los rótulos de
conexión que entran/salen de la caja. Medir con la guarda (los dos
fixtures v2 ya están en ella).

**Prioridad**: Alta — es el «lo siguiente» declarado del ROADMAP, ahora
con caso real reproducible.

---

### WISH-AUTO-010: Elemento libre multi-zona queda exiliado con diagonales gigantes ✅ RESUELTO (2026-08-05)

> Nueva pasada `_place_multizone_free_elements` en el ajuste
> post-expansión: un libre cuyos vecinos viven TODOS en contenedores (≥2
> distintos) y que está MAL puesto — pisa una caja, o quedó fuera del
> hull de contenedores a más de media diagonal de sus vecinos — se coloca
> en la periferia del hull, en el lado más cercano al baricentro de sus
> vecinos (espíritu §P60). El bien puesto no se toca (la primera versión
> sin esa puerta reubicaba libres sanos de 05/15 y empeoraba: +1 a×n).
> **Medido**: cruces −6 neto (15-architecture 9→5 y labels −1;
> físico v2 17→15 con labels +1); físico v2 compacto de verdad — tinta
> 36.5→52.8%, aspecto 1.76→1.42; la red eléctrica queda arriba al centro
> con dos bajadas cortas (verificado en PNG), murieron las dos diagonales
> naranjas de lámina completa. Regresión:
> `tests/test_auto010_multizone_free.py`.

**Componente**: `strategies/auto/positioner.py` (colocación de libres)
**Reportado**: 2026-08-03 (caso real evolucionado; anonimizado en `mina-fisico-v2.gag`)

`energia_ext` (red eléctrica, type `powergrid`) sólo conecta con las
fuentes de energía DENTRO de las dos zonas. El ajuste post-expansión lo
empuja debajo de todos los contenedores y termina EXILIADO en la esquina
inferior derecha, con dos diagonales naranjas que cruzan la lámina entera
(y los contenedores de en medio — parte del arista×nodo=8).

**Deseo**: un libre cuyos vecinos viven todos en zonas debería colocarse
en la periferia CERCANA al baricentro de sus destinos (como hace §P60 con
las zonas de servicio), no al final del canvas. Repro:
`mina-fisico-v2.gag`, elemento `energia_ext`.

---

### WISH-ARCH-002: Convergencia a un solo algoritmo (auto-selección) ✅ RESUELTO (cierre 2026-08-02)

> Cerrado por BUGS-DOCS-006: todo el alcance está en el código —
> `select_strategy` (generator.py), `LayoutEngine` + `_STRATEGIES`
> (engine.py), reorg `layout/strategies/{auto,hier,legacy}`, rescates ①
> (`offset_optimizer.py`) y ② (`hier/scc.py`) integrados, default CLI
> `select`. Lo único no hecho — «afinar el clasificador con más señales» —
> es mejora continua, no trabajo en curso.
**Componente**: `AlmaGag/generator.py` (`select_strategy`), `main.py`, `AlmaGag/layout/`
**Contexto**: la intención original del autor NO es tener tres algoritmos (auto/laf/hier).
AUTO fue el algoritmo original; LAF nació como **lente de debug por fases** de AUTO (mismo
algoritmo, con visibilidad), no como uno aparte; `hier` recombinó y mejoró ideas de ambos. El
objetivo es **un único motor** que interprete la mejor representación **a partir del JSON**, y
que la representación sólo se fuerce por **parámetro de comando** (nunca por un campo del JSON).
**Decisión (autor, 1a+2a)**: AUTO absorbe a hier (un motor); `areas`/`roles` quedan como
*contenido* del JSON; se saca `layout_view` del JSON (la representación va por `--view`).
**Hecho hasta ahora**:
- `layout_view` eliminado del JSON — la representación se fuerza sólo por CLI (`--view`).
- `--layout-algorithm` default = `select`: `almagag archivo.json` sin flags corre
  `select_strategy(data, view)` que elige la estrategia desde el JSON. Política conservadora:
  vista explícita→hier · contenedores→AUTO (hier no los soporta) · `areas`→hier · rombos
  (decision)→hier · resto→AUTO. Verificado: sólo 3 canónicos enrutan a hier (es-primo,
  activacion, red-areas); los 28 de arquitectura/topología siguen en AUTO. `auto/laf/hier`
  explícitos quedan como override avanzado/debug.
- **(i) Fusión estructural — `AlmaGag/layout/engine.py` (`LayoutEngine`)**: el generator ve UN
  solo optimizer (el engine). El engine elige la estrategia (override CLI > `layout._strategy` >
  'auto') y DELEGA en el optimizer correspondiente, adoptando su `renderer`. hier/laf dejan de ser
  algoritmos peer expuestos al generator → son estrategias internas. Cero regresión por
  construcción (delega en el mismo código): las 3 rutas a hier (deterministas) quedan
  byte-idénticas; las rutas a AUTO varían sólo por un **no-determinismo** que se investigó y
  **RESOLVIÓ** (ver abajo).
- **Determinismo (RESUELTO)**: el "capricho de AUTO" NO estaba en AUTO sino en los **templates**
  `flow` y `hub_and_spoke`: iteraban un `set` de ids de string (`for eid in root_ids`) para
  ordenar niveles/spokes, y el orden de iteración de un set de strings depende de
  `PYTHONHASHSEED` → el layout cambiaba entre procesos. Fix: iterar la lista de elementos (orden
  del input), no el set (`templates/flow.py:_topological_order`, `templates/hub_and_spoke.py:_find_hub`).
  Verificado: los 31 canónicos rinden byte-idénticos con cualquier hash seed. Regresión:
  `tests/test_determinism.py` (subprocesos con seeds distintos).
- **(i) prolijo — las 3 estrategias juntas bajo un motor**: `layout/hier/`, `layout/auto/` y
  `layout/laf/` → **`layout/strategies/{hier,auto,legacy}/`**. Ya no hay algoritmos peer al lado del
  motor: `layout/` sólo tiene `engine.py` + `strategies/`. Se puede cambiar de estrategia, pero
  **AUTO es la principal** (`_STRATEGIES` marca `kind`: base/flow/frozen + `DEFAULT_STRATEGY='auto'`).
  `laf` **renombrado a `legacy`** (motor histórico): CLI `--layout-algorithm=legacy` (ya no `laf`),
  congelado, nunca auto-elegido. Byte-idéntico tras los moves; 251 tests en verde.
- **(ii) LAF diferenciado en dos**: LAF se separó en (a) el **motor histórico** = estrategia
  `legacy` (el placement abstracto-primero con VC/SCC/TOI, congelado), y (b) **Epifanía**, el
  **analizador del proceso de conceptualización** = clase `Epifania` en
  `layout/strategies/legacy/epifania/` (ex-`ConceptualizationAnalyzer`/`GrowthVisualizer`, ambos
  conservados como alias retrocompat): NO posiciona, emite un SVG por fase del análisis (estructura
  → topología → centralidad → abstracción VC → placement → ruteo) para *ver cómo NACE la
  abstracción*. CLI `--epifania` (alias `--debug-phases`, `--visualize-growth`), salida en
  `debug/epifania/<diagrama>/`, títulos "Epifanía · Fase N". *Nombre elegido por José (sobre
  "Janus").*
- **(ii-b) Epifanía agnóstica del motor (paso 2) ✅**: `--epifania` ya no es exclusiva de `legacy`.
  `layout/epifania.py::PhaseRecorder` es un grabador **agnóstico**: hace `deepcopy` del layout en
  cada frontera de fase y re-renderiza cada foto con el *renderer real* de la estrategia → un
  "flipbook" del layout real naciendo etapa a etapa (la última foto es byte-idéntica al SVG final,
  verificado). Las estrategias emiten fases con `self._capture(label, layout, note)` (helper no-op
  de `LayoutOptimizer`, costo cero si no hay grabador); el `LayoutEngine` conecta el grabador sólo
  con `--epifania` y sólo a estrategias vivas (auto/hier) — `legacy` conserva su Epifanía "de lujo"
  (VC/centralidad) porque dibuja internos que sólo ese motor tiene. Fases instrumentadas: AUTO
  (posicionamiento → contenedores → ruteo-inicial → iteración-N por mejora → final); hier
  (niveles-columnas → ruteo → arcos → etiquetas → final; + final-areas/lanes/matrix). Salida:
  `debug/epifania/<diagrama>/NN_<fase>.svg` + `index.html` (hoja de contacto). Las capturas son
  sólo-lectura: **no alteran salida ni determinismo**; camino normal (sin `--epifania`) byte-idéntico.

**Pendiente**: afinar el clasificador con más señales (hoy es intencionalmente conservador);
opcional: portar las piezas de rescate ①/② desde `legacy` a `hier`. Test:
`tests/test_strategy_selection.py`, `tests/test_determinism.py`.

**Dirección de trabajo adoptada**: **AUTO = motor / puerta de entrada** (es el maduro, ya maneja
contenedores y es la puerta de `select_strategy`); **hier = estrategia de flujo** (sus módulos
limpios se conservan y se invocan como estrategia, no como algoritmo peer); **LAF = congelar**
(no borrar aún) y **rescatar 4 piezas** hacia el motor único. Diagnóstico de tamaños: espina
compartida ~2.750 LOC · AUTO placement ~2.500 · hier ~1.960 · LAF engine-VC ~7.800 (el que más
divergió) · LAF `GrowthVisualizer` ~2.450 (rescatable).

**Notas de rescate desde LAF** (portar a la maquinaria hier/AUTO cuando toque; independientes de
la dirección — le sirven al motor gane quien gane):

| # | Idea a rescatar | Fuente en LAF | Destino |
|---|---|---|---|
| ① | **Optimizador por bisección de layer-offset** — desplazamiento de toda una capa como variable continua; minimiza la distancia ponderada de conectores buscando la raíz de la derivada (convexa, ~48 iter, forward/backward, conv. <0.001). El aporte más original/limpio de LAF. | `AlmaGag/layout/laf/position_optimizer.py:416-520` | ✅ **INTEGRADA en AUTO**. Utilidad agnóstica `AlmaGag/layout/offset_optimizer.py::optimize_group_offsets` (`tests/test_offset_optimizer.py`, 6) + pasada `AutoLayoutOptimizer._compact_horizontal`. **Hallazgo empírico**: inerte en hier (carriles ya empaquetados) y en AUTO sin contenedores (barycenter ya bueno); **rinde en AUTO con contenedores** tratando cada contenedor como bloque rígido + libres por fila visual. **Guardada**: sólo adopta si bajan los cruces sin subir colisiones → cero regresión (32 canónicos: 2 mejoran, 30 igual, 0 peor). Medido: git cruces 14→11 / colis 73→64; reference-cheatsheet 8→4 / 35→32. Visible en Epifanía (fase `compactacion`). `tests/test_compaction.py` (3). |
| ② | **Contracción de SCC para levelizar** — contrae cada ciclo/componente fuerte a un representante para correr longest-path sobre un DAG. Más sólido que la detección de back-edges ad-hoc de hier hoy. | `AlmaGag/layout/laf/structure_analyzer.py:1015,1326` | ✅ **INTEGRADA** → `strategies/hier/scc.py` (Tarjan iterativo canónico) alimenta `leveling.py` §A. Los back-edges ahora salen de un feedback set derivado de los SCC (canónico, no del recorrido). **Cero regresión**: DAGs → ∅, ciclo simple → misma arista (14-stresstest byte-idéntico). Robustez nueva: ciclos entrelazados → un SCC + feedback set válido (probado). `tests/test_scc.py` (7). Demo visible en Epifanía: `docs/diagrams/gags/ciclo-retrabajo.sdjf`. |
| ③ | **`count_crossings` O(n²)** — cuenta cruces reales (intersección de segmentos). Métrica barata; ni AUTO ni hier la tienen. Usar como criterio de calidad y test de regresión. | `AlmaGag/layout/laf/abstract_placer.py:1358` | ✅ **INTEGRADA** → `AlmaGag/layout/metrics.py::count_crossings` (agnóstica del motor, centros de iconos; mejora: pares que comparten nodo no cuentan). Visible en **Epifanía** (chip ✕N + delta por fase) y en `tests/test_crossings.py` (9 tests). Reveló: AUTO=16 vs hier=1 cruces en 14-stresstest. |
| ④ | **Consideraciones declarativas** (`considerations.align/near/avoid`) — idea de producto valiosa y transversal (la impl LAF es un stub: solo `align`). | `AlmaGag/layout/laf/optimizer.py:245-321` | ✅ **INTEGRADA (blanda)**. Schema top-level `considerations: [...]` (alias legacy `constraints`) en `AlmaGag/layout/considerations.py`; AUTO las aplica **guardadas**: cada una sólo si no aumenta colisiones, la que no se puede CEDE y se informa en el log sin el porqué (`no se pudo cumplir: ...`). Son *consideraciones*, no restricciones duras — nunca degradan el diagrama. `select_strategy` enruta a AUTO. Cero regresión (sin `considerations` → no-op). Visible en Epifanía (fase `consideraciones`). Demo `docs/diagrams/gags/considerations-demo.sdjf` (incluye una que cede); `tests/test_considerations.py` (11); `FORMATO_ARCHIVOS.md §0.4`. |

*Bonus menores*: `W_precedence` (peso por skip-connections según distancia de nivel,
`structure_analyzer.py:148-172`); pesos de barycenter dinámicos vert:horiz (`abstract_placer.py:50-89`);
patrón "estimar → medir contenido real → re-expandir" para labels de contenedor
(`container_grower.py:20-33`); snapshots por fase (`GrowthVisualizer`) como práctica de debug al
desarrollar hier.

**Descartado a conciencia** (cubierto por auto/hier o demasiado atado al andamiaje de LAF):
abstracción **VC/TOI** ("tío" — atada al dominio genealógico, y la doc `CONCEPTS.md` la define
distinto que el código → concepto no consolidado; comprimir 11/13 nodos del stresstest en un VC
fue lo que rompió LAF y motivó hier); nomenclatura **NdDp/NdPr/NdFn** (inconsistente); spacing con
constantes mágicas; redistribución half-widths; **dashboard-reflow** (fix reactivo — insight
reutilizable: "componentes desconectados van en grid 2D, no en fila"); iconos-de-contenedor
separados (rendering, no layout). Señales de inmadurez de LAF que refuerzan congelarlo:
hiperparámetros "experimentales" sin defaults, docstrings contradictorios, fases que son fixes
reactivos más que diseño.

---

### WISH-LAF-002: Layout Jerárquico `hier` según Criterios A1–F18 (spec Claude Design) ✅ RESUELTO (v1) (Fases 1-2-3 ✅ — A1–F18 sobre 14-stresstest)
**Componente**: `AlmaGag/layout/hier/` (algoritmo nuevo) — leveling.py (§A), columns.py (§B), optimizer.py; + routing/draw (§C–§F)
**Severidad**: Alta (norte de calidad de layout; caso de regresión `14-stresstest.sdjf`)
**Reportado**: 2026-06-24 (spec "Criterios AlmaGag" generada por el usuario con Claude Design)

**Decisión de enfoque (2026-06-24)**: se implementa como un **algoritmo nuevo `--layout-algorithm=hier`**, NO como retrofit de LAF. Razón: LAF abstrae los nodos en contenedores virtuales (SCC/TOI/loop) — en el stresstest 11/13 nodos colapsan en `_scc_vc_0` y el placement ocurre dentro de esa caja, un modelo incompatible con el "niveles + columnas plano" que asume el spec. Un algoritmo limpio: (a) coincide 1:1 con la referencia, (b) no arriesga los 24 canonicals que usan LAF en CI, (c) reusa la lógica §A. LAF queda intacto.

**Motivación**:

El usuario produjo una especificación completa de layout jerárquico (18 criterios A1–F18, con orden de dependencias y render de referencia) para mejorar la presentación de LAF, usando `14-stresstest.sdjf` como caso de verificación. El render actual dispersa el grafo (canvas 1960×1860), destierra el satélite `L`, mete las tomas `B`/`C` en filas propias y usa 7 niveles donde el spec compacta a 6.

**Gap analysis (estado al abrir el ticket)** — 1 hecho, 6 parciales, 11 ausentes:

| Grupo | Criterios | Estado |
|---|---|---|
| A · Niveles | A1 min-parent · A2 satélites · A3 tomas | A1 **invertido** (usa longest-path/max-parent); A2/A3 parciales |
| B · Columnas | B4 ghosts+barycenter · B5 carriles · B6 alineación · B7 bifurcación · B8 tallo | B7 parcial; B4/B5/B6/B8 ausentes |
| C · Puertos | C9 proyección · C10 lado · C11 tomas | 12 sectores angulares (no proyección); C9/C11 ausentes |
| D · Ruteo | D12 mismo-nivel · D13 cruces · D14 carriles | **D14 hecho**; D12/D13 ausentes |
| E · Arcos | E15 winding · E16 signo · E17 comba | arco no se auto-aplica a ciclos; E16/E17 ausentes |
| F · Etiquetas | F18 lado despejado | parcial |

**Criterios de aceptación**: cada criterio A1–F18 verificado contra `14-stresstest.sdjf` (LAF), tal como describe la sección "verificación" de cada uno en el spec.

**Plan por fases** (respeta el orden de dependencias del spec):
- **Fase 1 — §A+§B** (niveles min-parent, satélites, tomas medio-nivel, ghosts+barycenter, carriles, alineación, bifurcación, tallo). *§A entregada (commit `756a7a0`); §B en progreso.*
  - **§A hecho** (`AlmaGag/layout/hier/leveling.py`): `compute_levels()` puro — min-parent (A1) + satélites (A2, con requisito de padre que continúa el flujo) + tomas a medio-nivel (A3) + back-edges. Verificado contra 14-stresstest: `A=0 D=1 B=1.5 E/H/L=2 F/I=3 C=3.5 G/J=4 K/M=5`.
  - **§B v1 hecho** (`AlmaGag/layout/hier/columns.py`): barycenter (B4) + alineación iterativa al ancestro dominante con sesgo tronco/ciclo (B6) + centrado de bifurcación (B7) + separación mínima por fila + tallo raíz (B8) + satélites al costado / tomas al margen exterior. `14-stresstest` en `hier`: canvas **1380×980** (vs 1960×2150 en LAF), 2 columnas principales limpias, sin solapes.
  - **§B5 hecho** (`columns.py`): carriles cycle-aware — cada componente de ciclo (SCC) recibe un carril propio y los nodos acíclicos se descomponen por spine (DFS de primera visita, hijo de subárbol más profundo continúa el carril). 14-stresstest queda con tronco A·D·E·F·G·M en una columna, ciclo I·J·K en otra, H aparte, satélite L al lado, tomas B/C al margen exterior. Canvas 1480×980.
  - **§B4 hecho** (`columns.py`): nodos fantasma en aristas largas. Hallazgo: bajo min-parent NINGUNA arista forward baja >1 nivel (min-parent garantiza Δ≤1); las largas van de un nodo profundo a uno superficial (Δ negativo), así que la detección es `|Δnivel|>1`. Cada arista larga se parte con un ghost por nivel intermedio; los ghosts entran al barycenter/carriles (reducen cruces) y sus X se exponen como `waypoints` en la conexión para el ruteo (§D).
  - **Fase 1 §A+§B COMPLETA.** Falta la consumación de waypoints por el ruteo (§D, Fase 2).
- **Fase 2 — §C+§D COMPLETA** (`AlmaGag/layout/hier/routing.py`): produce `connection['computed_path']`.
  - C9 puertos por proyección del otro extremo sobre el borde (fracción 0.16–0.84), separados por borde.
  - C10 lado del puerto según eje de flujo + llegada perpendicular.
  - C11 ruteo de tomas (salida lateral → horizontal → bajada vertical, 3 puntos).
  - D12 aristas de mismo nivel en recta; D13 cruces reales en recta (bifurcación/fusión conservan codo); D14 carriles de canal (offset por pista).
  - Consume los waypoints §B4. Las back-edges quedan sin path → arco §E (Fase 3). Conexiones a contenidos (sin posición) se saltan sin romper.
- **Fase 3 — §E+§F COMPLETA**:
  - §E (`AlmaGag/layout/hier/arcs.py`): aristas de ciclo como bezier con winding coherente. E15: signo global sobre la normal de la dirección → ida interior, retorno exterior automáticamente. E16: signo elegido desde la back-edge para que su normal apunte lejos del centroide. E17: comba adaptativa (base 44px, crece para librar nodos con proyección interior a la cuerda y perp<72px del lado de la comba, tope 320px).
  - §F18 (`AlmaGag/layout/hier/labels.py`): etiqueta al borde menos concurrido (cuenta conectores por T/B/L/R, desempate abajo→arriba→exterior→interior); setea `label_position`.
  - **§B7 v2 (simetría)**: se completó el centrado de la bifurcación. El tallo (bifurcación superior + ancestros de hijo único) se separa a su propio carril y se centra entre las columnas hijas; además el nodo de entrada del ciclo (H) se fusiona a la columna del ciclo (H·I·J·K vertical, sin diagonal larga H→I). 14-stresstest queda simétrico: tallo A·D centrado, ciclo a un lado, tronco al otro.

**QA de Claude Design (2026-07-13)** — evaluó el render y aprobó el layout («el layout ya está bien; el bug es uno solo»), detectando un único bug de trazado (etapas 10-11): los conectores quedaban recortados 40px (flujo) / 15px (arcos) antes del borde en vez de tocarlo. Corregido:
- Q1/Q3: los puertos hier (ya sobre el borde) se marcan como `_from_port`/`_to_port` → el renderer NO aplica su offset. Arcos: extremos recortados al borde con `clip_to_border` (función única).
- Q2: `_perp_stubs` garantiza un tramo final perpendicular ≥14px (aun en aristas de cruce/rectas) → flechas derechas.
- Q4: la toma sale por el COSTADO hacia el destino (no por el fondo) → salida horizontal + bajada vertical al borde superior.
- Q5: `tests/test_hier_geometry.py` — asserts geométricos (extremos en borde, llegada perpendicular) sobre el stresstest + 24 canónicos; evasión de obstáculos (d) validada en el stresstest.

**QA de Claude Design (2026-07-14) — evaluación es-primo (extensión G19–G23)**: se generó una POC de flowchart (`¿es n primo?`, con rombos de decisión y bucle `while`) y Claude Design la evaluó, extendiendo el spec con cinco criterios nuevos. Todos resueltos (**Fase G**):
- **G19** (`AlmaGag/layout/hier/shapes.py`): el recorte de puertos respeta el POLÍGONO real de la forma, no su bbox. Rombos (`decision`/`diamond`) usan convención flowchart: entrada por el vértice superior; salidas por izquierdo/derecho/inferior (un puerto por vértice, sin fracciones). `routing.py` snapea los puertos de rombo al vértice según dirección dominante; `arcs.py` recorta contra el rombo (`clip_shape`). Los conectores dejan de "flotar" en las esquinas vacías del bbox.
- **G20** (`leveling.py`): un sumidero (0 salidas, ≥2 padres acíclicos) baja a `max(nivel de padres)+1` en vez de subir por min-parent → los terminales del flowchart (NO es primo / ES PRIMO) caen al fondo, cerca de sus orígenes.
- **G21** (`columns.py`): asignación de carriles reescrita a *spine + hijo primario «menos padres»* con fusión de carriles-singleton hacia el head-child; el carve del tallo y el centrado B7 se restringen a bifurcaciones **reales** (excluyen fantasmas). `es-primo` queda en columna única; `14-stresstest` conserva la mariposa simétrica.
- **G22** (`optimizer.py`): contención del viewBox — se reúne toda la geometría (iconos, polylines, waypoints, control-points de bezier, anclas de rótulo), se traslada al espacio positivo si algo se salió por arriba/izquierda (tomas a medio nivel) y se expande el canvas. `bbox(paths) ⊆ viewBox` verificado sobre todos los canónicos.
- **G23** (`labels.py`): el rótulo de conexión (sí/no/repetir) se ancla a ~14px del puerto de SALIDA sobre el primer segmento; el renderer lo prioriza sobre el optimizador de etiquetas.

**QA de Claude Design (2026-07-14) — evaluación v3 (§H)**: midió el es-primo regenerado. Confirmó Q1–Q3 (borde a borde), G20 (not_prime al fondo), G21 (tronco recto), G22 (dentro del viewBox) y E15–E17 (lazo). Quedaban tres defectos de calidad de ruteo, todos resueltos (**Fase H**):
- **H24** (`routing.py`): ruteo largo ortogonal PURO. Se reemplazó el seguimiento diagonal de waypoints por `_ortho_route(p_from, sf, p_to, st, channel)` — router radial que respeta la dirección del puerto (primer/último tramo perpendicular al borde) y sólo emite codos de 90°. Diagonales permitidas únicamente en rectas de 2 puntos (§D12 mismo nivel / §D13 cruces reales) y arcos de ciclo (§E, bezier). Nuevo test `test_all_canonicals_no_diagonal_elbows`.
- **H25** (`columns.py`): el sumidero compartido (0 hijos, ≥2 padres reales) se reubica en la columna ADYACENTE al baricentro de sus padres, del lado libre (menos poblado), en vez de caer al margen lejano. En es-primo `not_prime` pasa de x=110 (4 carriles) a un carril del tronco → aristas cortas y paralelas. Usa `orig_parents` (padres reales antes de la cirugía de ghosts §B4).
- **H26** (`routing.py`): puertos de rombo estrictamente en el vértice, sin micro-codo. La salida se asigna considerando TODAS las aristas del rombo: la que baja recto (menor |Δx|) toma el vértice inferior; las demás salen por el lateral izq/der → el «sí» ya no roba el vértice inferior al «no», y el primer tramo sale radial (sin quiebre a <15px del puerto).

**Fase I+J (2026-07-14) — áreas, roles y densidad** (spec `Criterios AlmaGag.dc.html`, render de referencia `Activacion DC Render.dc.html`). El caso `activacion-datacenter.sdjf` se emitía como una tira de 980×5060; el spec añadió §I27–§I30 y §J30–§J33 para repartirlo a lo ancho. Implementado:
- **J30** (`optimizer.py`): paso vertical = icono + holgura fija (`ICON_HEIGHT+42` ≈ 92px) en vez de 170. es-primo 980→590, activacion 5060→2798 antes de áreas.
- **J31/J32** (`labels.py::wrap_label`): etiquetas partidas por palabras en ≤3 líneas dentro de un ancho máximo (~180px) con «\n»; truncado con «…» si excede. `apply_label_wrapping` corre en el optimizer.
- **I27** (`AlmaGag/layout/hier/areas.py`, nuevo): si el SDJF trae `areas:[{id,label,members,color?}]`, cada área es un sub-lienzo — corre A–H sobre su subgrafo intra-área (reusa `compute_levels`/`compute_columns`/`route_*`), se dimensiona al contenido + etiquetas (label-aware bbox, paso ampliado §J30) y se empaqueta izquierda→derecha (§J33). `optimizer._optimize_areas` despacha cuando hay `areas`.
- **I29** (`areas.py::_route_inter_area`): una arista entre áreas sale por el borde de la caja origen, cruza el corredor entre cajas y entra por el borde de la caja destino; ningún tramo cruza una 3ª caja.
- **I30** (`draw/primitives/phase_areas.py` + `auto_renderer.py`): cajas de fase punteadas rotuladas (fondo); rol por color (barra lateral en cajas, punto en rombos) desde `role` + `roles:{key:{label,color}}`; leyenda de responsables en la franja inferior. Etiquetas de nodo centradas bajo el icono (placement propio, sin el optimizador AUTO).
- Resultado: `activacion-datacenter.sdjf` pasa de 980×5060 (tira) a **2910×1022** (5 fases a lo ancho, roles por color, aristas inter-área cruzando bordes). Tests `test_hier_density.py` (6) + `test_hier_areas.py` (7).

**§I28 + selección de vista (2026-07-14)** — carriles por rol + sistema de vistas híbrido. Se separó **dato** (fase/rol) de **vista** (cómo se agrupa):
- **Selección híbrida**: prioridad `--view` (CLI) > `layout_view` (campo del SDJF) > `auto` (código decide: `areas` si las hay, si no `flow`). Resuelto en `generator.py`; despachado en `optimizer.optimize` por `_layout_view`. Valores: `flow|areas|lanes|matrix`. `matrix` aún no implementada (cae a `areas` con warning).
- **§I28** (`AlmaGag/layout/hier/lanes.py`, nuevo): carriles verticales por rol. Y = nivel de flujo (reusa §A + ruteo §C–§E), X = banda del carril; si no hay `lanes:[…]` explícito se derivan del campo `role`. Franjas de fondo rotuladas (`draw_lane_strips`); cruzar carril = handoff. Es la vista clásica de swimlanes ("¿quién?").
- La misma `activacion-datacenter.sdjf` rinde ahora en 3 vistas: `areas` 2910×1022 (a lo ancho), `lanes` 1550×2856 (swimlanes), `flow` 980×2798 (tira). `--view` en `main.py`; `layout_view`/`lanes` documentados en `docs/spec/FORMATO_ARCHIVOS.md §0.3`.
- Tests `test_hier_lanes.py` (6).

**Vista `matrix` (fase×rol) (2026-07-14)** — `AlmaGag/layout/hier/matrix.py` + `draw_matrix_grid`. La vista más completa (el spec la ofrecía "solo bajo petición" por lo cara de rutear): grilla con **fase en columnas** y **rol en filas**; cada nodo cae en la celda (fase, rol) y si varios comparten celda se apilan por nivel de flujo. Es el flowchart transfuncional clásico (BPMN cross-functional). Headers de fase arriba, bandas de rol tintadas con rótulo a la izquierda, separadores de columna. Requiere `areas` + `role`. `activacion-datacenter.sdjf` en `--view=matrix` → 5×7 celdas, 1318×2564. Tests `test_hier_matrix.py` (3). Con esto las 4 vistas del sistema §I están completas: `flow` | `areas` | `lanes` | `matrix`.

**Bugfix etiquetas agrupadas (2026-07-14)**: `apply_label_wrapping` exigía `x` en el elemento → en áreas/carriles/matriz (que envuelven antes de posicionar) las etiquetas no se partían. Quitado el guard (envolver un string no necesita coords). Además en `lanes` el ancho de carril se hizo proporcional al máximo de nodos por nivel para que dos etiquetas centradas (satélite + padre) no se solapen. §J32 sólo trunca, no maqueta notas externas.

Registro: `--layout-algorithm=hier` en `main.py` + `generator.OPTIMIZERS`. Reusa `AutoSVGRenderer` para el dibujo. Tests en `tests/test_hier_layout.py`, `test_hier_routing.py`, `test_hier_arcs_labels.py`, `test_hier_geometry.py` (210 en total con la Fase H). LAF y sus 24 canonicals quedan intactos. Limitación Fase 1: `hier` posiciona sólo elementos root (grafos planos); el soporte de containers vendrá después.

---

### WISH-ARCH-001: LAFOptimizer Cumpla el Contrato LayoutOptimizer ✅ RESUELTO
**Componente**: `AlmaGag/layout/laf/optimizer.py` + `AlmaGag/generator.py`
**Severidad**: Media-Alta
**Reportado**: 2026-05-14 (detectado durante refactor de routing_policy)
**Resuelto**: 2026-06-18

**Estado anterior**:
- `AutoLayoutOptimizer` hereda de `LayoutOptimizer` (clase base en `optimizer_base.py`).
- `LAFOptimizer` no hereda de nadie y tiene firma de `__init__` distinta (recibe colaboradores por inyección).
- `generator.py` usa `if/elif layout_algorithm == ...` para distinguir (líneas ~578, ~625).
- `render_containers()` recibe `layout_algorithm` como parámetro.

**Fix aplicado** (Tier 1):
1. `LAFOptimizer` ahora hereda de `LayoutOptimizer`.
2. `__init__` self-contained: construye sus deps internamente. Acepta inyección opcional (retrocompat).
3. `optimize()` firma unificada: `(layout, max_iterations=10, dump_iterations=False, input_file=None)`. LAF ignora los kwargs que no aplican.
4. `LAFRoutingPolicy` se uniformó con `AutoRoutingPolicy` — acepta `sizing` y construye `router_manager` internamente. Modo legacy preservado.
5. `generator.py` ahora usa **factoría** (`OPTIMIZERS = {'auto': ..., 'laf': ...}`) en lugar de `if/elif`. Una sola llamada a `optimizer.optimize(...)` para ambos.

**Lo que NO se hizo en este fix** (queda como deuda separada):
- `layout_algorithm` sigue propagándose a `render_containers()` y `draw_container()` para decidir si dibujar el icono inline (AUTO) o como elemento separado (LAF). Es una decisión de **renderizado**, no de optimizer. Registrado como **WISH-ARCH-005**.

---

### WISH-ARCH-005: Eliminar `layout_algorithm` del Renderer ✅ RESUELTO

> (Renumerado el 2026-08-02 — era un `WISH-ARCH-002` DUPLICADO, colisión con
> el ticket de convergencia. Referencias históricas a «WISH-ARCH-002 del
> renderer» apuntan aquí; BUGS-DOCS-006.)
**Componente**: `AlmaGag/renderer.py` (eliminado) → `layout/auto/renderer.py` + `layout/laf/renderer.py`
**Severidad**: Media
**Reportado**: 2026-06-18 (follow-up explícito de WISH-ARCH-001)
**Resuelto**: 2026-06-18

**Fix aplicado** — separación total entre algoritmos (más fuerte que la Opción A original):
- `AlmaGag/renderer.py` (509 líneas, compartido) **eliminado**.
- `AlmaGag/draw/svg.py` **NUEVO**: primitivas SVG agnósticas (create_canvas, setup_arrow_markers, draw_connections, ndfn_wrap, etc.).
- `AlmaGag/layout/auto/renderer.py` **NUEVO**: clase `AutoSVGRenderer` con toda la orquestación AUTO (no sabe que LAF existe).
- `AlmaGag/layout/laf/renderer.py` **NUEVO**: clase `LAFSVGRenderer` con toda la orquestación LAF, incluyendo `_render_container_icons` (LAF-only).
- Cada optimizer expone `self.renderer` en `__init__`.
- `generator.py` ahora llama `optimizer.renderer.render(layout, output_svg, ...)`.

**Principio aplicado**: "un algoritmo no sabe que el otro existe". Los renderers solo dependen de:
- `AlmaGag/draw/` (primitivas de íconos compartidas)
- `AlmaGag/debug.py` (helpers de debug compartidos)
- `AlmaGag/layout/label_optimizer.py` (optimizador de labels compartido)

**Estructura final**:
```
AlmaGag/
├── draw/
│   ├── svg.py           ← primitivas SVG agnósticas
│   ├── connections.py   (compartido)
│   ├── container.py     (compartido)
│   └── icons.py + 12 tipos
└── layout/
    ├── auto/
    │   ├── optimizer.py
    │   ├── routing_policy.py
    │   └── renderer.py  ← AutoSVGRenderer
    └── laf/
        ├── optimizer.py
        ├── routing_policy.py
        └── renderer.py  ← LAFSVGRenderer
```

**Validación**: smoke 46/46 SVGs, determinismo 3/3 archivos × 3 seeds = 1 hash único, tests 17 passed.

**Descripción**:
Tras resolver WISH-ARCH-001 (contrato del optimizer unificado), queda un residuo de la asimetría AUTO/LAF **en la capa de renderizado**: el parámetro `layout_algorithm` se sigue pasando a `render_containers()` y `draw_container()` para decidir cómo dibujar el icono del container.

**Comportamiento actual**:
- **AUTO**: el icono del container se pinta **inline**, en la esquina superior izquierda del rect del container.
- **LAF**: el icono del container se pinta como **elemento separado**, con su propia (x, y) en el grid del SVG.

El renderer necesita saber qué algoritmo produjo el layout para elegir el modo. Eso es:
1. **Acoplamiento innecesario**: el renderer está atado a los nombres `'auto'` / `'laf'`.
2. **Falsa extensibilidad**: agregar un tercer algoritmo requeriría tocar el renderer.
3. **Decisión en el lugar equivocado**: "¿el icono va inline o separado?" es info del **layout** (cómo se posicionaron los containers), no del **algoritmo** abstracto.

**Por qué es WISH y no BUGS**:
El código **funciona correctamente** — ambos modos producen renders válidos. Es asimetría arquitectural que querrías limpiar, no un bug funcional.

**Solución propuesta — Opción A (recomendada): Flag en el container**

Cada optimizer marca los containers con cómo deben renderizarse:

```python
# AutoLayoutOptimizer.optimize() antes de retornar:
for container in containers:
    container['_icon_inline'] = True

# LAFOptimizer.optimize() antes de retornar:
for container in containers:
    container['_icon_inline'] = False  # el icono es elemento separado
```

Renderer queda agnóstico:
```python
def draw_container(dwg, container, elements_by_id, draw_label=True, draw_icon=True):
    # Ya no recibe layout_algorithm
    if draw_icon and container.get('_icon_inline', True):
        # dibuja el icono en la esquina
```

**Soluciones alternativas**:
- **B**: Unificar comportamiento (ambos algoritmos rinden inline, o ambos separado). Cambio visual visible en SVGs existentes.
- **C**: Strategy pattern en el renderer (`InlineIconContainerRenderer` / `SeparateIconContainerRenderer`). Más OOP pero overkill.

**Impacto del fix**:
- Cambio: ~3-5 líneas en cada optimizer + simplificación en `draw/container.py` y `renderer.py`.
- Re-render afectado: 5 SVGs con containers, deberían quedar visualmente idénticos.
- Riesgo: bajo. Cambio puramente refactorial.

**Estimación**: ~30 min de implementación + 15 min de validación visual.

**Prioridad**: Media (deuda residual de WISH-ARCH-001; mejora cosmética del código).

**Validación**: 46/46 SVGs smoke OK; determinismo 3/3 archivos × 3 seeds intacto; tests 17/2.

**Por qué es WISH y no BUGS**:
El código **funciona**: LAF corre OK, los renders son válidos. Es asimetría arquitectural que querrías limpiar, no un crash o resultado incorrecto.

**Impacto**:
- Acoplamiento entre algoritmo de layout y fases posteriores.
- Imposible agregar un tercer algoritmo sin modificar `generator.py`.
- El Strategy Pattern documentado en `ARCHITECTURE.md` no se cumple en la práctica.
- Es la causa de la asimetría en `routing_policy.py`.

**Solución propuesta**:
- Hacer que `LAFOptimizer` herede de `LayoutOptimizer`.
- Unificar firma `optimize(layout, **kwargs) -> Layout`.
- Eliminar `layout_algorithm` como parámetro propagado a `render_containers`.
- Cuando se resuelva, el constructor de `LAFRoutingPolicy` probablemente se uniformará con el de `AutoRoutingPolicy`.

---

### WISH-ARCH-003: Tier 2 Refactor — Reorganizar `draw/` + Split de `visualizer.py` ✅ RESUELTO
**Componente**: `AlmaGag/draw/` + `AlmaGag/layout/laf/visualizer.py`
**Severidad**: Media (deuda estructural, no funcional)
**Reportado**: 2026-06-18
**Resuelto**: 2026-06-18

**Fix aplicado**:

**Sub-tarea A — Reorganizar `draw/`** (commit `f51794f`):
```
draw/
├── primitives/                  ← svg, container, connections, callout
└── icons/                       ← __init__ (dispatcher) + 11 tipos
```
- 11 iconos movidos a `draw/icons/` vía `git mv` (historia preservada).
- 4 primitivas movidas a `draw/primitives/` vía `git mv`.
- Dispatcher renombrado: `draw/icons.py` → `draw/icons/__init__.py`.
- 3 dynamic imports actualizados, imports estáticos en renderers actualizados.

**Sub-tarea B — Split de `visualizer.py`**:
Antes: 1 archivo de 2876 líneas con `GrowthVisualizer` + 10 `_generate_phaseN_svg`.
Después: paquete `visualizer/` con 1 archivo por fase + class slim.

```
laf/visualizer/
├── __init__.py              (862 líneas, class GrowthVisualizer + helpers + thin wrappers)
├── phase1.py                (322 líneas)
├── phase2_topology.py       (555 líneas)
├── phase3_centrality.py     (298 líneas)
├── phase4_abstract.py       (245 líneas)
├── phase5_optimized.py      (212 líneas)
├── phase7_iterative.py      (373 líneas)
├── phase8_inflated.py       (53 líneas)
├── phase9_redistributed.py  (48 líneas)
├── phase10_routed.py        (48 líneas)
└── phase11_final.py         (48 líneas)
```

Cada `phaseN_*.py` expone `def generate(viz, output_path)` con el body original (self → viz transformados). Los `_generate_phaseN_svg` de la clase quedan como thin wrappers de 3 líneas:
```python
def _generate_phase1_svg(self, output_path: str) -> None:
    from AlmaGag.layout.laf.visualizer import phase1
    phase1.generate(self, output_path)
```

Helpers internos (`_draw_colored_connections`, `_segments_intersect`, `_are_collinear`, `_build_ndpr_positions`, `_draw_ndpr_node`, `_build_ndfn_labels`, `_draw_elements_with_ndfn`, `_draw_straight_connections`, `_draw_routed_connections`) quedaron en la clase para acceso vía `viz.X` desde cualquier fase.

Refactor mecánico: script `split_visualizer.py` extrajo cada fase + script `fix_helpers.py` reubicó helpers misplaced.

**Validación**:
- Smoke 46/46 OK (23 × 2 algoritmos).
- Tests 19 passed.
- `--visualize-growth` genera las 10 fases SVG correctamente.
- 0/23 canonical SVGs afectados.
- Refactor puro, sin cambios funcionales. (durante el ciclo Tier 1)

**Estado actual**:
1. **`AlmaGag/draw/` plano con 16+ módulos mezclados**:
   ```
   draw/
   ├── svg.py            ← primitivas SVG agnósticas (creado en WISH-ARCH-002)
   ├── icons.py          ← dispatcher de iconos
   ├── container.py
   ├── connections.py
   ├── bwt.py            ← banana with tape (fallback)
   ├── server.py, cloud.py, building.py, database.py, ...  ← tipos de iconos
   └── ...
   ```
   La mezcla de "primitivas + dispatcher + tipos concretos + utils" en un mismo paquete dificulta navegar y agregar nuevos tipos sin tocar todo.

2. **`AlmaGag/layout/laf/visualizer.py` con ~2900 líneas**: contiene `GrowthVisualizer` que captura snapshots SVG de cada fase del pipeline LAF para `--visualize-growth`. Una sola clase con 11 métodos `capture_phaseN_*`, cada uno con lógica de renderizado específica (muchas duplicaciones del renderer principal).

**Solución propuesta**:

Sub-tarea **A — Reorganizar `draw/`**:
```
draw/
├── primitives/
│   ├── svg.py           ← create_canvas, markers, ndfn_wrap, draw_connections
│   ├── container.py
│   └── connections.py
├── icons/
│   ├── __init__.py      ← dispatcher (importlib)
│   ├── server.py
│   ├── cloud.py
│   ├── ... (1 archivo por tipo)
│   └── bwt.py           ← fallback
└── __init__.py
```

Sub-tarea **B — Split de `visualizer.py`**:
```
laf/
├── visualizer/
│   ├── __init__.py            ← exports GrowthVisualizer
│   ├── base.py                ← clase + utils compartidos
│   ├── phase1_structure.py
│   ├── phase2_topology.py
│   ├── phase3_centrality.py
│   ├── phase4_abstract.py
│   ├── phase5_optimized.py
│   ├── phase6_ndpr_expanded.py
│   ├── phase7_iterative.py
│   ├── phase8_inflated.py
│   ├── phase9_redistributed.py
│   ├── phase10_routed.py
│   └── phase11_final.py
```

Cada `phaseN_*.py` expone una función `capture(visualizer, ...args)` que el `GrowthVisualizer` invoca. Reduce el tamaño de cada archivo a 200-400 líneas y permite testear fases individualmente.

**Por qué es WISH y no BUGS**:
El código funciona correctamente. Es organización del código, no corrección de comportamiento.

**Impacto del fix**:
- Sub-tarea A: ~30 min, sin cambios funcionales, solo `git mv` + actualizar imports.
- Sub-tarea B: 2-3 horas, mayor riesgo por el tamaño (~2900 líneas), pero el resultado deja cada fase auto-contenida.
- Re-render afectado: ninguno (refactor puro).

**Estimación**: 1 día (medio refactor + medio validación visual).

**Prioridad**: Media-baja. No bloquea features pero mejora mucho la mantenibilidad del módulo de visualización.

---

### WISH-LAF-001: Más Optimización de Cruces de Conexiones ✅ RESUELTO (v1: pesos dinámicos)
**Componente**: `AlmaGag/layout/laf/abstract_placer.py` — Fase 4 (barycenter)
**Severidad**: Baja
**Reportado**: 2026-01-21
**Resuelto**: 2026-06-18

**Fix v1 aplicado** — propuesta #1 del ticket original (ajuste dinámico de pesos):

- **`config.py`** — 2 constantes nuevas: `BARYCENTER_PREV_WEIGHT_MIN = 0.5`, `BARYCENTER_PREV_WEIGHT_MAX = 0.85`.
- **`AbstractPlacer._compute_barycenter_weights(structure_info)`** — calcula `(prev_w, same_w)` según la proporción vertical:horizontal del grafo:
  - Grafo puramente vertical (ratio=1.0) → `prev_w = 0.85`.
  - Grafo balanceado (ratio≈0.5) → `prev_w ≈ 0.675`.
  - Grafo con muchas same-layer connections (ratio=0.0) → `prev_w = 0.5`.
- Pesos cacheados en `self._prev_weight`, `self._same_weight` durante `place_elements()`.
- Reemplazan los 4 hardcoded `0.7` / `0.3` en `_calculate_barycenter`, `_calculate_barycenter_backward`, `_calculate_barycenter_from_graph`, `_calculate_barycenter_backward_from_graph`.

**Distribución observada** en las 23 fuentes:
- 16 archivos: `prev_w=0.85` (grafos verticales puros — arquitecturas, flujos).
- 5 archivos: `prev_w` entre 0.69-0.83 (grafos mixtos).
- 2 archivos: `prev_w` entre 0.64-0.69 (`git`, `roadmap-versions` — más same-layer).

**Métrica de cruces (Fase 5)**: idéntica antes y después del fix (787 cruces totales en 23 archivos).

**¿Por qué no bajan los cruces?** En la práctica el orden topológico domina: dentro de cada capa los elementos se ordenan por barycenter, y el cambio de pesos modifica el VALOR pero rara vez el ORDEN relativo. Para reducir cruces hace falta atacar el problema con otras técnicas (propuestas #2 y #3 del ticket original).

**Lo que NO se hizo en v1 (queda como follow-ups)**:
- **Edge straightening post-procesamiento**: nueva sub-fase después de Fase 5 que mueve nodos en pequeñas magnitudes para enderezar líneas que cruzan tangencialmente. Requiere modificar `position_optimizer.py`.
- **Heurística por tipo de diagrama**: aprender de un corpus de SDJF qué tipo de layout (architecture/flow/poster) se beneficia de qué presets.

Estos follow-ups se registran agrupados como `WISH-LAF-001 follow-up`.

---

### WISH-LAYOUT-001: Sistema de Etiquetas Inteligente ✅ RESUELTO (cerrado por implementaciones existentes + follow-ups específicos)
**Componente**: Label positioning (transversal)
**Severidad**: Enhancement
**Reportado**: 2026-01-21
**Resuelto**: 2026-06-18

**Por qué se cierra**:
El ticket original era un paraguas vago. Al auditar el código, los 3 sub-objetivos están cubiertos por implementaciones existentes o por tickets más específicos.

**Mapeo bullet-a-implementación**:

| Sub-objetivo original | Estado | Implementación |
|---|---|---|
| Detectar colisiones de etiquetas entre sí y con elementos | ✅ Cubierto | `AlmaGag/layout/label_optimizer.py::LabelPositionOptimizer` con penalty system (`PENALTY_COLLISION_ELEMENT=100`, `PENALTY_COLLISION_LABEL=50`, `PENALTY_COLLISION_LINE=75`). Detección activa en cada render. |
| Ajustar posición automáticamente (arriba/abajo/laterales) | ✅ Cubierto | `LabelPositionOptimizer.optimize_labels()` prueba posiciones canónicas en orden (`bottom`, `right`, `top`, `left`) eligiendo la de menor score combinado (colisiones + densidad local + bounds). |
| Usar "leaders" (líneas guía) cuando se separa etiqueta del elemento | ✅ Cubierto | `WISH-LAYOUT-003` resuelto al 2026-06-18: `AlmaGag/draw/primitives/callout.py::draw_callout()` dibuja un leader line semipunteado desde el centro del icono al callout box. |

**Lo que sigue siendo deuda** (registrado como follow-ups específicos, no parte del paraguas original):

- **`WISH-LAYOUT-002` follow-up** (`constraints.near` / `constraints.avoid`): integración de proximidad/alejamiento en el barycenter de Fase 4. NO es de etiquetas; lo agrupé acá al cerrar v1 porque ambos tocan posicionamiento, pero conceptualmente no pertenece a este paraguas.
- **`WISH-LAF-001` follow-up** (edge straightening + heurística por tipo): optimización de cruces en Fase 5. NO es de etiquetas; misma razón.
- **Mejora del placement de callouts** (smart placement vía `CollisionDetector` en lugar del fallback derecha→abajo actual): es una mejora natural del callout v1 pero queda fuera de este paraguas — abrir si hace falta como `WISH-LAYOUT-003` v2.

**Referencias originales** (mantenidas como inspiración para futuros tickets de este área):
- Graphviz label placement algorithms.
- D3.js force-directed label positioning.

---

### WISH-LAYOUT-003: Auto-Callout para Labels Grandes ✅ RESUELTO (v1)
**Componente**: `AlmaGag/draw/callout.py` (nuevo) + ambos renderers
**Severidad**: Media
**Reportado**: 2026-06-15
**Resuelto**: 2026-06-18

**Fix v1 aplicado**:

- **`config.py`** — 6 constantes nuevas:
  - `CALLOUT_MIN_LINES = 6` (umbral conservador para no afectar diagramas existentes).
  - `CALLOUT_MIN_CHARS = 150`.
  - `CALLOUT_BOX_PADDING = 10`.
  - `CALLOUT_LEADER_OFFSET = 40` (gap entre icono y callout box).
  - `CALLOUT_BOX_FILL_OPACITY = 0.85`.
  - `CALLOUT_LEADER_DASHARRAY = "4,3"` (línea semipunteada).

- **`AlmaGag/draw/callout.py`** (nuevo, ~135 líneas) — API:
  - `should_use_callout(elem, label_text)` — detección con override `"callout": true/false` en SDJF.
  - `get_canonical_label(label)` — primera línea como label visible adyacente al icono.
  - `calculate_callout_position(elem, canvas_w, canvas_h)` — v1: derecha del icono con fallback a abajo si overflow.
  - `draw_callout(dwg, elem, full_text, canvas_w, canvas_h)` — renderiza rect + text multilínea + leader line.

- **`auto_renderer.py` + `laf_renderer.py`** — `_render_element_labels()` modificado:
  - Detecta callout, renderiza label canónico en el icono, dibuja callout box.
  - Cambio replicado en ambos renderers (siguen independientes desde WISH-ARCH-002).

**Override explícito**: SDJF puede forzar/desactivar con `"callout": true/false` por elemento (gana sobre umbrales).

**Validación**:
- Caso sintético `callout_test.sdjf` con label de 12 líneas (Pipeline LAF 11 fases): callout box renderizado + leader line ✓.
- **0/23 canonical SVGs afectados** (umbral conservador deja diagramas existentes intactos).
- Smoke 46/46 OK.
- Tests 19 passed.
- Determinismo: 1 hash único × 3 seeds × 3 archivos.

**Limitaciones de v1 (follow-ups documentados como parte de `WISH-LAYOUT-001`)**:
- Placement naive (derecha con fallback a abajo). No usa `CollisionDetector` para evitar solapamientos con otros elementos.
- No participa del collision detection del `LabelPositionOptimizer`.
- Si hay múltiples callouts en el mismo cuadrante, se solapan.

Estas mejoras se integran al sistema más amplio de etiquetas inteligente (WISH-LAYOUT-001).

---

### WISH-LAYOUT-002: Soporte para Restricciones de Posicionamiento ✅ RESUELTO (v1: solo `align`)
**Componente**: `AlmaGag/layout/laf/optimizer.py` — nueva Fase 1.4
**Severidad**: Enhancement
**Reportado**: 2026-01-21
**Resuelto**: 2026-06-18

**Fix v1 aplicado**: soporte para `constraints.align` en SDJF.

```json
{
  "elements": [
    {
      "id": "database",
      "type": "database",
      "constraints": {"align": "bottom"}
    }
  ]
}
```

Valores soportados:
- `"top"` → fuerza nivel topológico 0.
- `"bottom"` → fuerza nivel topológico max (=N-1 niveles).
- `"center"` → fuerza nivel topológico max // 2.

**Implementación**:
- Nuevo método `LAFOptimizer._apply_alignment_constraints()`.
- Llamado entre Fase 1.5 (dashboard reflow) y Fase 2 (topology display).
- Modifica `structure_info.topological_levels` Y `ndpr_topological_levels` (este último es lo que usa la fase iterativa 4-5-6 vía NdPr; sin actualizarlo el constraint se ignoraba).
- Descendientes heredan el nivel del ancestro alineado.

**Validación**:
- Caso `legend con align:bottom`: elemento sin conexiones bajaba a nivel 0 → ahora va a nivel max. ✓
- Caso `trigger con align:top`: ya estaba en nivel 0, no movement (comportamiento correcto). ✓
- Caso `trigger con align:center` en grafo de 5 niveles: trigger pasa de nivel 0 a un nivel medio. ✓
- Smoke 46/46 OK, tests 19 passed, determinismo intacto.
- 0/23 canonical SVGs afectados (los canonical no usan `constraints`).

**Lo que NO se implementó en v1 (queda como deuda separada)**:

- **`near: ["api", "cache"]`** — agruparía elementos por proximidad horizontal. Requeriría integrar pesos en el barycenter de Fase 4 (`abstract_placer.py`). Más complejo porque hay que balancear con la minimización de cruces.
- **`avoid: ["frontend"]`** — alejaría elementos. Mismo nivel de complejidad que `near` pero con peso negativo.

Estas dos quedan como **follow-up de WISH-LAYOUT-002**: requieren entender la interacción con cruces/Sugiyama y probablemente merecen un sub-ticket o entrada en `WISH-LAYOUT-001` (etiquetas inteligentes ↔ posicionamiento inteligente).

---

### WISH-LAYOUT-004: Auto-Detección Semántica de la Distribución Óptima (NORTE del proyecto) ✅ RESUELTO (4 fases entregadas)
**Componente**: `AlmaGag/layout/templates/` (nuevo) + `AlmaGag/generator.py`
**Severidad**: **Alta** (núcleo de la propuesta de valor de AlmaGag)
**Reportado**: 2026-06-19 (inspección del diagrama de arquitectura)
**Fase 1 resuelta**: 2026-06-19

**Estado por fase**:

**✅ Fase 1 — Template 'architecture'** (2026-06-19):
- Nuevo módulo `AlmaGag/layout/templates/` con framework de templates.
- Template `architecture`: layout en T (entry vertical → containers en fila con shared al centro → contract → terminals).
- Heurística de categorización por rol topológico.
- Opt-in vía `"layout_template": "architecture"` en SDJF.
- Respeta coords manuales. Calcula canvas automáticamente.
- 8 tests + ejemplo `15-architecture-template.gag`.

**✅ Fase 2 — Framework de auto-detección + 2 templates más** (2026-06-19):

Replanteo: en lugar de "catálogo opt-in" (que sería declarativo, no inferencial), Fase 2 ahora es **clasificador automático del grafo** + **scorers por template**.

- **`GraphFeatures`** (`templates/features.py`): extrae 15+ métricas del grafo (n_root, degrees, max_degree_ratio, topological_depth, ciclos, branching_factor, pct_inter_container_connections, keywords semánticas).
- **`BaseTemplate`** + **`TemplateClassifier`** (`templates/base.py`): interfaz + clasificador con threshold (0.6) y min_lead (0.05) configurables.
- **3 templates** con sus respectivos `detect_score()`:
  - `architecture`: containers ≥ 2, keyword shared, DAG, depth 3-7.
  - `flow`: depth ≥ 4, branching ~1, sin containers, sin ciclos.
  - `hub_and_spoke`: max_degree_ratio ≥ 2.5, depth ≤ 2, pocos containers. Layout circular (n<8) o columnas izq/der (n≥8 estilo SD-WAN).
- **`generator.py`**:
  - `"layout_template": "auto"` → clasificador (Fase 2).
  - `"layout_template": "<name>"` → override manual.
  - Sin declaración → comportamiento agnóstico (AUTO/LAF normal).
- **16 tests** del clasificador (`tests/test_template_classifier.py`).

Resultados del clasificador sobre los 23 canonicals:
- Aciertos claros: `05-arq` / `15-template` → architecture (0.75); `svg-to-bwt-flow`, `03-conexiones` → flow (0.90); `system-architecture` → hub_and_spoke (0.85).
- Casos ambiguos / catálogos visuales → None (fallback agnóstico) — comportamiento correcto.

**✅ Fase 3 — Templates adicionales + calibración** (2026-06-19):

4 templates nuevos con sus detectores + layouts:
- `dashboard` (`templates/dashboard.py`): containers paralelos sin conexiones inter → grid `ceil(sqrt(N))` × `ceil(N/cols)`.
- `er` (`templates/er.py`): Entity-Relationship → distribución radial-concéntrica (entidades más conectadas al centro).
- `sequence` (`templates/sequence.py`): swimlanes verticales en columnas + mensajes ordenados temporalmente.
- `state` (`templates/state.py`): estados en distribución circular (uniforme).

Calibración con los 23 canonicals:
- 3 architecture (05-arq, 07-containers, 15-template).
- 6 flow (03-conexiones, 12-custom, 14-stresstest, layout-opt, routing-arch, svg-to-bwt-flow).
- 3 hub_and_spoke (06-flujo, 13-stresstest, system-arch).
- 1 dashboard (reference-cheatsheet).
- 1 er (10-hybrid-layout).
- 10 `(ninguno)` — catálogos visuales y casos ambiguos, fallback correcto a algoritmo agnóstico.

Ajustes de calibración aplicados:
- ER scorer: cortocircuito a 0 si `n_connections < 3` (sin relaciones no hay ER).
- ER scorer: penalty fuerte (-0.45) si hay containers (no es ER puro entonces).
- Keywords semánticos: agregados `entity`, `table`, `database` a `SEMANTIC_TOKENS`.

11 tests nuevos en `tests/test_template_fase3.py`. Total: 54 (era 43).

**✅ Fase 4 — Semantic hints + templates anidados** (2026-06-19):

(a) Semantic hints (`role` por elemento):
- Campo `"role"` opcional con valores: entry, output, shared, hub, spoke, abstract, state, actor, terminal.
- `GraphFeatures.declared_roles` mapea elem_id → role.
- Roles sobreescriben heurística por label/topología (architecture/hub_and_spoke/state).
- Scorers dan bonus por roles consistentes con el patrón.

(b) Templates anidados por container:
- Campo `"layout_template"` opcional en cualquier container.
- Nuevo módulo `templates/nested.py` con procesamiento bottom-up.
- `apply_sub_templates` se llama SIEMPRE (independiente del template padre).
- Containers guardan `_inner_width`/`_inner_height` desde su sub-grafo.
- `offset_nested_children` ajusta hijos a coords globales después del padre.
- Política: el hijo siempre infla; el padre se adapta.

10 tests nuevos. Total 54 → 64. WISH-LAYOUT-004 cerrado integralmente.

**✅ Fase 4 — Semantic hints + templates anidados** (2026-06-19):

(a) Semantic hints (`role` por elemento):
- Campo `"role"` opcional con valores: entry, output, shared, hub, spoke, abstract, state, actor, terminal.
- `GraphFeatures.declared_roles` mapea elem_id → role.
- Roles sobreescriben heurística por label/topología (architecture/hub_and_spoke/state).
- Scorers dan bonus por roles consistentes con el patrón.

(b) Templates anidados por container:
- Campo `"layout_template"` opcional en cualquier container.
- Nuevo módulo `templates/nested.py` con procesamiento bottom-up.
- `apply_sub_templates` se llama SIEMPRE (independiente del template padre).
- Containers guardan `_inner_width`/`_inner_height` desde su sub-grafo.
- `offset_nested_children` ajusta hijos a coords globales después del padre.
- Política: el hijo siempre infla; el padre se adapta.

10 tests nuevos. Total 54 → 64. WISH-LAYOUT-004 cerrado integralmente.

**Reportado originalmente**: 2026-06-19 (inspección del diagrama de arquitectura)

**Descripción**:
AlmaGag se vende como "generador automático de diagramas SVG desde JSON descriptivo". Pero en la práctica, para diagramas con estructura específica (arquitectura, flow, dashboard, ER, secuencia, etc.) el sistema **necesita coords manuales** para producir un layout legible. AUTO sin coords pone los elementos pero el resultado raramente es lo que un humano dibujaría; LAF distribuye por topología pero a costa de canvas excesivos.

**Reproducción concreta** (`05-arquitectura-gag.gag` sin coords manuales):
- AUTO: 1400×1872 — sin la lógica "shared al medio entre algoritmos"; queda alto y sin balance.
- LAF: 3230×1908 — distribuye horizontal por topología, canvas excesivo.
- AUTO + coords manuales (estado actual): 1200×1180, layout en T balanceado — **pero las 8 posiciones hardcodeadas son trabajo manual**.

**Lo que se desea**:
Que el algoritmo **infiera la intención del diagrama** y elija la distribución apropiada sin que el usuario tenga que escribir coords. Algunos patrones reconocibles:

| Patrón | Pista de detección | Layout ideal |
|---|---|---|
| Arquitectura jerárquica | Pocos nodos raíz, varios niveles, containers como agrupadores | Top-down con shared al centro entre alternativas |
| Flow / pipeline | Cadena lineal de pasos | Horizontal o vertical recto |
| Dashboard / poster | Containers paralelos sin conexiones entre sí | Grid (ya parcialmente resuelto en LAF Fase 1.5) |
| ER / clases | Nodos con relaciones múltiples | Force-directed o circular |
| Secuencia | Conexiones con orden temporal | Swimlanes |
| Estado | Self-loops y ciclos | Estados como nodos, transiciones como aristas |

**Posibles enfoques** (a explorar en sub-tareas):

1. **Detección de patrones por heurística**: clasificar el grafo por número de niveles topológicos, fan-out del nodo raíz, ratio cross-level vs same-level connections, presencia/ausencia de containers, ciclos, etc.
2. **Templates pre-definidos**: bibliotecas de layouts (arch, flow, dashboard, sequence, etc.) que el usuario seleccione vía `"layout_template": "architecture"` en el SDJF.
3. **Semantic hints en el SDJF**: tags por elemento (`"role": "entry"`, `"role": "shared"`, `"role": "output"`) que ayuden al algoritmo.
4. **ML / LLM-assisted layout**: usar un modelo para inferir la mejor disposición a partir de la estructura del grafo y las etiquetas semánticas de los elementos.
5. **Constraint solver**: extensión de `WISH-LAYOUT-002` con más constraints (`above`, `below`, `between`, `inside_group`) y un solver que satisfaga el máximo número.

**Por qué es importante**:
Es el **norte del proyecto**. AlmaGag deja de ser un "generador" y se convierte en un "asistente con coords manuales" si los usuarios tienen que escribir 8-30 posiciones para cada diagrama complejo. Resolver esto convierte AlmaGag en una herramienta competitiva con Mermaid/Graphviz/D3 que infieren bastante por sí solas.

**Relación con tickets existentes**:
- **Subsume** los follow-ups de `WISH-LAYOUT-002` (`constraints.near` / `constraints.avoid`) y `WISH-LAF-001` (heurística por tipo de diagrama).
- **Habilita** que el diagrama de arquitectura del propio proyecto se genere sin las 8 coords manuales actuales.
- **Refuerza** el benchmark contra Mermaid (`docs/diagrams/benchmark/`).

**Estimación**: trabajo grande, no acotable en una iteración. Mínimo:
- Fase 1 (1-2 días): heurística para reconocer "arquitectura jerárquica" + template top-down con shared al centro.
- Fase 2 (1 semana): catalogar 5-6 patrones más comunes y sus templates.
- Fase 3 (continua): semantic hints en SDJF + constraint solver extendido.

**Prioridad**: **Alta a largo plazo**. No bloquea features inmediatas pero es la diferencia entre "herramienta de nicho" y "herramienta competitiva". Mantener visible como el norte del proyecto.

---

### WISH-DOCS-001: Sincronizar `architecture.mmd` Benchmark con el Nuevo `.gag` ✅ RESUELTO
**Componente**: `docs/diagrams/benchmark/architecture.mmd`
**Severidad**: Baja
**Reportado**: 2026-06-18
**Resuelto**: 2026-06-18

**Causa**: `architecture.mmd` representaba la arquitectura pre-ciclo (con `auto_optimizer v2.1`, `laf_optimizer v1.8`, `renderer.py` único, módulo `Routing` granular). El nuevo `05-arquitectura-gag.gag` ya reflejaba post WISH-ARCH-001/002 + BUGS-LAF-002 con factoría OPTIMIZERS, renderers separados y `draw/svg.py`. El benchmark seguía corriendo pero comparaba grafos distintos.

**Fix aplicado**:
- `architecture.mmd` reescrito: mismos 16 elementos en 3 containers (AUTO, LAF, Shared) que el `.gag`. Heritage de optimizers al contrato `LayoutOptimizer` representada con flechas punteadas (`-. "hereda" .->`). Forma `>...]` (parallelogram-asymmetric) para distinguir la clase abstracta.
- `architecture.svg` y `architecture.png` regenerados con `mmdc` (puppeteer config con `--no-sandbox`).
- `benchmark/README.md` actualizado: tabla de archivos, métricas objetivas (canvas, tamaños, líneas), próximos benchmarks. Mencionado explícitamente WISH-DOCS-001 como ancla de sync.

**Validación**: ambos diagramas representan ahora el mismo grafo (16 elementos × 3 containers × ~15 conexiones).

---

### WISH-DOCS-002: Actualizar `EVOLUTION.md` con el Ciclo Actual ✅ RESUELTO
**Componente**: `docs/architecture/EVOLUTION.md`
**Severidad**: Baja
**Reportado**: 2026-06-18
**Resuelto**: 2026-06-18

**Fix aplicado**:
Reemplazado el placeholder "v2.2 - (Futuro)" por 3 entradas nuevas que cubren ~18 meses faltantes:

- **v3.0 — LAF (Sprints 1-11)** — introducción del pipeline LAF de 11 fases inspirado en Sugiyama. Tabla con la responsabilidad de cada fase. Métricas vs AUTO sobre `05-arquitectura-gag`: cruces -87%, colisiones -80%.

- **v3.3 — SDJF v2.1 + BUGS-DIAG-* (8 fixes visuales)** — pulido visual del set canonical (containers semi-transparentes, labels gigantes, bandas densas, grid spacing).

- **v3.4 — Ciclo "13 items en un sprint" (2026-06-18)** — entrada extensa del ciclo actual, con tablas separadas por categoría:
  - Refactores: Tier 1 (WISH-ARCH-001/002, `generator.py` 838→187 líneas) + Tier 2 (WISH-ARCH-003, `visualizer.py` 2876→11 archivos).
  - Fixes funcionales: tabla con las 5 BUGS resueltas (LAYOUT-001/002/003 + LAF-001/002) y sus métricas clave.
  - Features: WISH-LAYOUT-003 callouts.
  - Documentación: WISH-DOCS-001/002.
  - Métricas globales: antes/después en una tabla.
  - Diagrama de arquitectura: descripción del nuevo `.gag` con iconos custom.

**Validación**: doc renderiza correctamente en GitHub markdown.

---

### WISH-LAYOUT-005: Container Especial "Contract Band" Envolvente ✅ RESUELTO (v1)
**Componente**: SDJF spec + `AlmaGag/draw/primitives/container.py` + `AlmaGag/layout/container_calculator.py` + `AlmaGag/layout/auto/positioner.py` + `AlmaGag/layout/auto/auto_renderer.py`
**Severidad**: Media (mejora expresividad de diagramas arquitectónicos)
**Reportado**: 2026-06-23 (feedback visual del usuario sobre diagrama manual)
**Resuelto**: 2026-06-23

**Motivación**:

En diagramas arquitectónicos es común expresar "estos N elementos son intercambiables a través de este contrato" con una **banda horizontal** que envuelve un grupo `[endpoint_A, abstract, endpoint_B]`. Visualmente la banda comunica que es un eje único de simetría, no un container jerárquico clásico.

AlmaGag hoy solo tiene containers tipo "caja con título": el background rectangular agrupa pero no transmite el sentido de banda/eje.

**Caso de prueba**:
Diagrama manual del usuario (2026-06-23): banda horizontal azul claro envuelve `[green-rect-izq, yellow-diamond, green-rect-der]` haciendo evidente la equivalencia funcional.

**Propuesta**:
- Nuevo tipo de container en SDJF: `"type": "band"` o `"shape": "band"` (compatible con `"contains": [...]`).
- Render: rect muy ancho y bajo (alto = max height de hijos + padding), sin título arriba sino lateral. Color de fondo más sutil que un container normal.
- Comportamiento de layout: hijos en fila horizontal con padding uniforme, no en grid.
- Compatible con el `architecture` template (banda = capa del medio en la T).

**Fix aplicado (v1)**:

Un container con `"shape": "band"` (cualquier container con `contains` puede llevarlo) se comporta distinto:

1. **Layout de hijos** (`positioner._layout_contained_elements_locally`): todos los hijos en **una sola fila** horizontal (`cols = n`), con offset lateral izquierdo para el título y sin reserva de header arriba. Es el eje de equivalencia.
2. **Bounds** (`container_calculator.calculate_container_bounds` + `positioner._calculate_container_bounds`, ambos band-aware vía helper `is_band` / `band_label_margin`): reservan margen lateral izquierdo (`band_label_margin = n_líneas*18 + 16`) en vez de header arriba; alto = hijos + 2·padding (hug vertical).
3. **Render del rect** (`draw/primitives/container.py`): fondo más sutil (`CONTAINER_FILL_OPACITY * 0.6`), esquinas de barra (`radius = min(height/2, 24)`), sin icono superior.
4. **Título** (`auto_renderer._render_container_labels`): rotado -90° sobre el borde izquierdo, centrado verticalmente.

**Validación**:
- Canonical `16-contract-band.gag` — banda envuelve `[server, diamond, server]` en fila, 0 colisiones.
- `tests/test_band_container.py` — 5 tests (detección, margen por líneas, hijos en fila única, sin overflow horizontal, label rotado en SVG).
- Regresión: containers normales (`05-arquitectura-gag`, `07-containers`, `reference-cheatsheet`) byte-idénticos vs HEAD.
- Tests 79/79 passed.

**Follow-up (2026-06-23, mismo ticket)** — feedback visual del usuario:
1. **Icono en cada container**: se detectó que el renderer AUTO pasaba `draw_icon=False` y por eso **ningún** container AUTO mostraba su icono de tipo (aunque el label ya venía offseteado `x + 10 + ICON_WIDTH + 10` dejando el hueco). Se activó `draw_icon=True`: containers normales dibujan el icono en la esquina superior izquierda; las bands lo dibujan tras el título rotado, alineado con la fila de hijos (`band_left_region = título + ICON_WIDTH + gap`). Regenerados todos los canonicals con containers.
2. **Centrado**: el eje del band demo se alineó (Entry, hijo central y Output centrados en la misma X).

**Pendiente (v2, no bloquea)**:
- Soporte en el renderer LAF (hoy solo AUTO maneja el título lateral; LAF dibujaría el label como header normal).
- Integración con el `architecture` template (auto-detectar la capa media como band).

---

### WISH-LAYOUT-006: Auto Label-Position por Geometría del Container ✅ RESUELTO (v1)
**Componente**: `AlmaGag/layout/auto/optimizer.py`
**Severidad**: Media (mejora legibilidad de diagramas con containers anchos/estrechos)
**Reportado**: 2026-06-23 (feedback visual del usuario sobre diagrama manual)
**Resuelto**: 2026-06-23

**Motivación**:

El usuario en su diagrama manual posiciona los labels de iconos contenidos **hacia afuera del centro del container**: icono izquierdo → label a la izquierda; icono derecho → label a la derecha. Esa heurística:
- Evita solape entre labels de hermanos adyacentes (problema BUGS-AUTO-006 que ya parchamos con stagger).
- Aprovecha el espacio libre fuera del container.

AlmaGag hoy elige label_position con un default global (`bottom`) o con `_find_best_label_position` que prueba 4 lados en orden fijo. No considera la geometría del container padre.

**Propuesta**:
- En `_find_best_label_position`, cuando el elemento tiene un container padre, sesgar la preferencia hacia el lado **lejano** del centro del container.
- Para containers row (hijos alineados horizontalmente): preferir `left` para el primer hijo, `right` para el último, `bottom`/`top` para los del medio.
- Para containers column: análogo con `top`/`bottom`.
- Reduce dependencia del stagger horizontal (BUGS-AUTO-006).

**Fix aplicado (v1)**:

Nuevo helper `_outward_label_preference(layout, element, parent_container)`:
- Devuelve `'left'` para el hijo **más a la izquierda** de su fila, `'right'` para el **más a la derecha**, `None` para los internos o únicos.
- **Gate single-row**: solo sesga si todos los hijos del container están en una sola fila (`max(y)-min(y) <= 0.6·icon_h`). En grids multi-fila devuelve `None` — sesgar un extremo pondría su label sobre vecinos de otra fila (medido: empeoraba R1 en `reference-cheatsheet`).

Integración como **reordenamiento del fallback** en `_find_best_label_position`: la posición preferida (`bottom` o la del usuario) se mantiene primera; el lado outward se inserta en 2º lugar, antes del resto. Así, cuando `bottom` colisiona, el extremo prueba su lado externo antes que los demás — sin forzar el cambio cuando `bottom` ya funciona (cero regresiones en los canonicals deterministas).

Bug colateral corregido: `_label_inside_container` reservaba una franja superior de 40px (header) también en bands, que **no tienen header** (el título va lateral). Ahora `header_h=0` para bands, permitiendo labels en su parte alta.

**Validación**:
- `tests/test_outward_labels.py` — 5 tests (helper: leftmost→left, rightmost→right, middle→None, multi-fila→None, sin-container→None; + band sin franja superior).
- Balance R1/R2 sobre canonicals deterministas (excluyendo `06-flujo-ejecucion`, que tiene no-determinismo **preexistente** en placement de labels): **sin cambios** (31/83 → 31/83). El efecto aparece solo cuando `bottom` colisiona, sin degradar lo que ya funcionaba.
- Suite 89/89.

**Pendiente (v2, no bloquea)**:
- Forzar outward como preferida en bands requiere reservar margen lateral **simétrico** (hoy solo el lado izquierdo tiene espacio: título + icono; el label `right` del último hijo se sale y cae a `bottom`). Necesita que el bounds-calc de la band reserve sitio para los labels de los extremos.
- Soporte para containers column (sesgo vertical `top`/`bottom`).
- Investigar/abrir ticket para el no-determinismo de `06-flujo-ejecucion` (label placement varía entre corridas; remanente de BUGS-LAYOUT-003).

---

### WISH-LAYOUT-007: Color Semántico por Tipo de Conexión ✅ RESUELTO (v1)
**Componente**: SDJF spec + `AlmaGag/draw/primitives/svg.py` + renderers
**Severidad**: Baja (mejora expresividad de diagramas con múltiples tipos de relación)
**Reportado**: 2026-06-23 (feedback visual del usuario sobre diagrama manual)
**Resuelto**: 2026-06-23

**Motivación**:

En diagramas con múltiples tipos de relación (data flow, control flow, sync, callback, event), el color del conector codifica la semántica de un vistazo. El usuario lo hizo manualmente: 17 conexiones naranja (data flow) + 1 verde bidireccional (sync de estado).

AlmaGag hoy:
- `color_connections=True` → colorea cada conexión con un color único determinado por id (no semántico).
- Si `color_connections=False`, todas en negro.
- `connection.color` no existe en SDJF.

**Propuesta**:
1. **Campo nuevo en SDJF**: `connection.semantic_type` (string libre) o `connection.color` (hex/nombre).
2. **Mapeo automático**: si `semantic_type` está presente, asignar color de paleta predefinida (`data_flow=orange`, `control_flow=blue`, `sync=green`, `event=purple`, `callback=teal`).
3. **Override directo**: `connection.color` tiene precedencia sobre `semantic_type`.
4. **Compatibilidad**: si nada de esto se declara, comportamiento actual (negro o `color_connections`).
5. Bonus: leyenda automática si hay 2+ `semantic_type` distintos en el diagrama.

**Fix aplicado (v1)**:

- `AlmaGag/draw/primitives/svg.py`:
  - `SEMANTIC_CONNECTION_COLORS`: paleta `data_flow`(naranja), `control_flow`(azul), `sync`(verde), `event`(púrpura), `callback`(teal), `dependency`(gris), `error`(rojo).
  - `resolve_connection_color(conn)`: `conn['color']` (override) → `SEMANTIC_CONNECTION_COLORS[conn['semantic_type']]` → `None`.
  - `setup_arrow_markers` refactorizado: si `color_connections` → arcoíris (como antes); si no, calcula color por `resolve_connection_color`; si **alguna** conexión declara color/tipo, devuelve per-connection styles (las sin tipo quedan negras); si ninguna → markers planos (comportamiento clásico intacto).
- Renderers (`auto_renderer.py`, `laf_renderer.py`): manejan el tuple per-connection independientemente del flag `color_connections`.

**Validación**:
- `tests/test_semantic_connection_colors.py` — 7 tests (precedencia color>semantic, mapeo por tipo, None sin declarar, markers planos sin semantic, per-connection con semantic, arcoíris intacto).
- Canonical `17-semantic-connections.gag` (data_flow/sync/event/callback) — 0 colisiones.
- Regresión: canonicals sin `semantic_type` byte-idénticos (05-arquitectura, 07-containers). Suite 96/96.

**Pendiente (v2, no bloquea)**:
- Leyenda automática (swatch + etiqueta por `semantic_type` presente). Requiere reservar área sin solapar contenido (placement no trivial); se deja como incremento.

---

### WISH-DRAW-001: Shape `diamond` (abstract/decision) como Icono Nativo ✅ RESUELTO
**Componente**: `AlmaGag/draw/icons/` — nuevo módulo `diamond.py` + alias `decision.py`
**Severidad**: Baja (cosmético, mejora claridad visual)
**Reportado**: 2026-06-23 (feedback visual del usuario sobre diagrama manual)
**Resuelto**: 2026-06-23

**Motivación**:

El usuario usa un diamante amarillo para el nodo abstracto/contrato en el centro de la banda. El diamante es convención UML/BPMN para "decision" o "interface", y comunica el rol abstracto al instante. AlmaGag hoy:
- `type: "contract"` renderiza un rect dashed con texto `«abstract»` (estilo UML clase abstracta).
- No hay shape `diamond` registrado.

Ambos son válidos UML pero el diamante es más universal en diagramas arquitectónicos (no solo de clases). Vale tenerlo disponible.

**Propuesta**:
1. Crear `AlmaGag/draw/icons/diamond.py` con `draw_diamond(dwg, x, y, color, element_id)`:
   - Polígono rombo (4 puntos) en gradiente.
   - Tamaño base ICON_WIDTH × ICON_HEIGHT, ajustable con `wp`/`hp`.
2. Registrar en el dispatcher (`AlmaGag/draw/icons/__init__.py`).
3. Disponible como `"type": "diamond"` en cualquier SDJF.
4. **Opcional**: añadir `"type": "decision"` como alias semántico.

**Fix aplicado**:
- `AlmaGag/draw/icons/diamond.py` — `draw_diamond(dwg, x, y, color, element_id)`: polígono rombo con sus 4 vértices en los puntos medios del bbox `ICON_WIDTH × ICON_HEIGHT`. El centro y los anclajes de conexión coinciden con los de cualquier icono rectangular (port_assignment funciona sin cambios). Gradiente + línea de realce diagonal sutil.
- `AlmaGag/draw/icons/decision.py` — alias: `"type": "decision"` renderiza el mismo rombo (el dispatcher importa por nombre de módulo, así que necesita su propio archivo).
- Compatible con `wp`/`hp` (vía bbox), gradientes y todos los routing types.

**Validación**:
- `tests/test_diamond_icon.py` — 4 tests (render del polígono, alias decision==diamond, dispatcher resuelve ambos tipos sin caer al fallback bwt).
- Tests 74/74 passed.
- Render de prueba: rombos correctos en `diamond` y `decision`, sin warnings de ícono por defecto.

---

## 📊 Métricas

Los conteos por categoría se sacan grep-eando este archivo (`grep -c '^### BUGS-'`
/ `'^### WISH-'`) — las tablas estáticas de conteo quedaban obsoletas al primer
ticket nuevo (BUGS-DOCS-006). Estado al 2026-08-03: la tanda de auditoría
2026-08-02 quedó COMPLETA (BUGS-DOCS-001…006, BUGS-VAL-003, BUGS-ARCH-001,
BUGS-AUTO-008/009, BUGS-DRAW-001/002 — todos ✅) y la iteración 6 cerró
WISH-DRAW-002 (flujos resaltados) y WISH-LAYOUT-008 (unificación de
etiquetas + medición veraz total). WISH abierto más reciente:
WISH-LAYOUT-009 (pitch label-aware).


## Mapeo desde códigos anteriores

Para referencias históricas (commits, PRs, comentarios), este es el mapeo desde los códigos `LAF-NNN` previos a la convención actual:

| Código anterior | Código actual |
|---|---|
| LAF-001 | BUGS-LAYOUT-001 |
| LAF-002 | BUGS-LAYOUT-002 |
| LAF-003 | BUGS-LAF-001 |
| LAF-004 | WISH-LAF-001 |
| LAF-005 | WISH-LAYOUT-001 |
| LAF-006 | WISH-LAYOUT-002 |
| LAF-007 | BUGS-LAF-002 |
| LAF-008 | WISH-ARCH-001 |
| LAF-009 | BUGS-LAYOUT-003 ✅ |

---

## 🔗 Enlaces relacionados

- [LAF Progress](./architecture/modules/layout/laf/PROGRESS.md) — Estado de implementación de sistema LAF.
- [LAF Comparison](./architecture/modules/layout/laf/COMPARISON.md) — Comparativa LAF vs AUTO.
- [DIAGRAM_REVIEW.md](./DIAGRAM_REVIEW.md) — Issues visuales en SVGs (códigos `BUGS-DIAG-NNN`).
