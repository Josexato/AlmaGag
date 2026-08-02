# Revisión de calidad de diagramas

> **⚠️ HISTÓRICO (congelado al 2026-06-15).** Este checklist cubrió los
> BUGS-DIAG-001…008, todos resueltos. La actividad de revisión visual
> posterior vive en `docs/reviews/` (iteraciones 3-5, grupos N/O/P/Q y la
> auditoría 2026-08-02). Las métricas de canvas citadas abajo son previas
> al recorte §O51 y las rutas `layout/auto|laf/` previas a la reorg
> `strategies/` — no corresponden al código actual (BUGS-DOCS-006).

Checklist vivo de problemas visuales detectados en los SVGs renderizados de AlmaGag. A diferencia de `TECHNICAL_DEBT.md` (que trata bugs del código), este documento trata problemas **específicos del render visual** de cada `.sdjf`/`.gag`.

Sigue la misma convención de códigos que `TECHNICAL_DEBT.md`: `<CATEGORÍA>-DIAG-<NNN>`. Todas las entradas son `BUGS-DIAG-NNN` por definición (un diagrama mal renderizado siempre es "no funciona como debería"). Se resuelven marcando el checkbox.

---

## 05-arquitectura-gag.svg

**Fuente:** `docs/diagrams/gags/05-arquitectura-gag.gag` (con iconos custom: factory/gear/brush/pipeline/contract/toolbox)
**Render actual:** AUTO (post-BUGS-LAYOUT-003 fix), sin `--visualdebug`, canvas 2012×2072
**Histórico:** LAF + `--visualdebug` produjo canvas 5230×2360; sin debug LAF produce 11397×2300 (BUGS-LAF-002 manifestándose).
**Última revisión:** 2026-06-15

**Datos base:**
- 32 elementos declarados, 26 conexiones, 0 coordenadas manuales en SDJF.
- 5 stages (containers): `shared_deps`, `auto_path`, `laf_path`, `routing_module`, `draw_module`.

### 🔴 Críticos

- [x] **BUGS-DIAG-001 — Los stages no se ven como contenedores.** ✅ RESUELTO (2026-06-15)
  Los rectángulos contenedores **sí se dibujaban**, pero con `opacity=0.3` global que afectaba al stroke también, dejándolo casi invisible.
  **Fix aplicado:** en `AlmaGag/draw/container.py` se separó la opacidad de fill y stroke. Nuevos parámetros configurables en `config.py`:
    - `CONTAINER_FILL_OPACITY = 0.15` (relleno aún transparente para ver hijos detrás).
    - `CONTAINER_STROKE_OPACITY = 0.8` (borde nítido para percibir el agrupamiento).
  **Impacto:** afectó a 5 SVGs en el repo con containers (`05-arquitectura-gag`, `06-flujo-ejecucion`, `07-containers`, `git`, `reference-cheatsheet`); todos regenerados.

- [x] **BUGS-DIAG-002 — Label gigante en `laf_pipeline` rompe la cuadrícula.** ✅ RESUELTO (2026-06-15)
  El label tenía 7 líneas (148 caracteres) describiendo 11 fases sobre un icono de 64×46 px. Descalibraba el layout circundante.
  **Fix aplicado:** acortado a `"LAF Pipeline\n(11 fases)"` (2 líneas, 22 caracteres, −85% caracteres). El detalle de las 11 fases ya vive en `docs/architecture/modules/layout/laf/LAF.md`. Canvas: 2012×2072 → 2012×2052 (−20 px alto).
  **Follow-up:** `WISH-LAYOUT-003` documenta la solución sistémica (auto-callout para labels grandes) en `TECHNICAL_DEBT.md`.

### 🟠 Importantes

- [x] **BUGS-DIAG-003 — Asimetría horizontal y peso desequilibrado.** ✅ RESUELTO (2026-06-15)
  Causa raíz compartida con BUGS-DIAG-008: `growth_visualizer` y `label_optimizer` no estaban en el `contains` de ningún stage, por lo que AUTO los posicionaba sin afinidad y terminaban en los extremos.
  **Fix aplicado:** agregados al `contains` de sus stages naturales en el SDJF:
    - `growth_visualizer` → `laf_path-stage` (es exclusivo de LAF).
    - `label_optimizer` → `draw_module-stage` (rol de presentación visual).
  **Resultado:** canvas 2012×2052 → **1600×2052** (−20% ancho). Ambos elementos ahora aparecen dentro de sus stages.

- [x] **BUGS-DIAG-004 — `output` aislado de los `draw_*` que lo alimentan.** ✅ RESUELTO (2026-06-15)
  Causa real: el SDJF declaraba `render → draw_module-stage` (al contenedor, no a los hijos). Como esa conexión no se propagaba a los `draw_*` individuales, estos quedaban en level=0 (sin entrantes) y AUTO los colocaba arriba sin afinidad.
  **Fix aplicado:** reemplazar la conexión `render → draw_module-stage` por 4 conexiones individuales `render → draw_{containers,icons,connections,labels}` en el SDJF. Ahora los draw_* están en level=5 (junto con `output`) y aparecen agrupados al final del flujo en la banda inferior del diagrama.
  **Nota:** `output` quedó en la misma banda que `render` (ambos level=5). La interpretación final: `render` orquesta usando `draw_*` y produce `output`. Si en el futuro se prefiere forzar output a level=6 (debajo de draw_*), se puede agregar `draw_* → output` en otro fix.

- [x] **BUGS-DIAG-005 — Salto vertical desproporcionado.** ✅ RESUELTO por consecuencia (2026-06-15)
  La queja original era el gap atípico de **441 px** entre el cluster routing/draw y `render` (mientras los otros gaps eran ~290 px).
  **No requirió fix dedicado:** tras resolver BUGS-DIAG-003/004/008 (huérfanos asignados a stages + `render → draw_*` explícitos), los gaps quedaron uniformes en 300-400 px. La asimetría original desapareció.
  **Datos:**
    - Antes: 286 → 290 → 350 → **441** → 294 (un outlier).
    - Después: 300 → 300 → 350 → 400 → 350 (uniformes).
  **Nota:** la magnitud absoluta de cada gap (~300-400 px por nivel) está dictada por la constante `VERTICAL_SPACING = 240 px` en `layout/auto/positioner.py:293`, compartida con LAF. Esto es deuda separada (`BUGS-LAYOUT-002` — canvas excesivo). Reducir el spacing aquí cambiaría TODOS los renders.

### 🟡 Menores

- [x] **BUGS-DIAG-006 — Densidad inconsistente entre niveles.** ✅ RESUELTO (2026-06-15)
  Causa estructural: 4 stages hermanos al mismo level topológico → 13 hijos en la misma banda Y.
  **Fix aplicado:** coordenadas Y manuales en 2 stages para crear 3 sub-bandas con sentido semántico:
    - `shared_deps-stage` → `y=750` (utilidades base, ARRIBA de los algoritmos).
    - `auto_path-stage` + `laf_path-stage` → y=950 (sin cambio, algoritmos en el medio).
    - `routing_module-stage` → `y=1150` (usado por los algoritmos, ABAJO).
  **Resultado:**
    - Banda más densa: 13 → 7 elementos (−46%).
    - Bandas con contenido: 7 → 11 (+57%).
    - Ratio max/min: 13:1 → 7:1.
  **Nota:** las coordenadas Y manuales reflejan honestamente la dirección del flujo (utilities → procesamiento → output). El SDJF ahora tiene 2 elementos con coordenadas explícitas (rompe el patrón "0 coords manuales" del archivo original, pero es necesario para evitar la densidad estructural).

- [x] **BUGS-DIAG-007 — Gap vertical insuficiente entre filas dentro de containers.** ✅ RESUELTO (2026-06-15)
  Causa raíz **sistémica** (no específica de `auto_optimizer/auto_positioner`): en `AlmaGag/layout/auto/positioner.py:990`, el spacing entre filas de un grid dentro de un container era `ICON_HEIGHT + GRID_SPACING_SMALL = 50 + 20 = 70 px`, pero el footprint visual real de un elemento con label de 2 líneas es ~106 px. Resultado: los labels de la fila superior se solapaban con los íconos de la fila inferior (gap efectivo de solo 24 px entre íconos).
  Afectaba a TODOS los containers en TODOS los SVGs (no solo a 05-arquitectura-gag).
  **Fix aplicado:** nueva constante en `config.py`:
    ```python
    CONTAINER_GRID_ROW_SPACING = LABEL_OFFSET_BOTTOM + TEXT_LINE_HEIGHT * 2 + 10  # 66px
    ```
    En `positioner.py:990`, reemplazar `spacing` por `CONTAINER_GRID_ROW_SPACING` para el cálculo de `_local_y`. Row spacing total ahora: `50 + 66 = 116 px`, gap efectivo entre íconos: **70 px** (suficiente para 2 líneas de label + margen).
  **Resultado:** afectó 5 SVGs (los que tienen containers); todos regenerados. Canvas crece ~90 px de alto (esperado).
  **Smoke test:** 23/23 OK. Determinismo: 1 hash único.

- [x] **BUGS-DIAG-008 — Elementos huérfanos visuales.** ✅ RESUELTO (2026-06-15)
  Resuelto junto con BUGS-DIAG-003 (misma causa raíz, mismo fix). `growth_visualizer` y `label_optimizer` ahora están dentro de sus stages naturales en el SDJF.

---

## Hipótesis transversales

Varios BUGS-DIAG arriba comparten causas raíz:

| Si se resuelve... | ...probablemente se resuelven |
|---|---|
| BUGS-DIAG-001 (containers visibles) | BUGS-DIAG-003, BUGS-DIAG-008 |
| Agregar coordenadas manuales en SDJF | BUGS-DIAG-003, BUGS-DIAG-004, BUGS-DIAG-008 |
| BUGS-DIAG-002 (label corto) ✅ | mejoró BUGS-DIAG-005, BUGS-DIAG-006 parcialmente |
| BUGS-LAF-002 (dashboard layout) | habilitaría usar LAF, que tenía mejor sense visual en este caso |
| **WISH-LAYOUT-003** (auto-callout para labels grandes) | resuelve la **familia** de BUGS-DIAG-002 sin editar SDJFs futuros |

---

## Mapeo desde códigos anteriores

| Código anterior | Código actual |
|---|---|
| DIAG-001 | BUGS-DIAG-001 |
| DIAG-002 | BUGS-DIAG-002 |
| DIAG-003 | BUGS-DIAG-003 |
| DIAG-004 | BUGS-DIAG-004 |
| DIAG-005 | BUGS-DIAG-005 |
| DIAG-006 | BUGS-DIAG-006 |
| DIAG-007 | BUGS-DIAG-007 |
| DIAG-008 | BUGS-DIAG-008 |

---

## Para diagramas futuros

Cuando se revise otro diagrama (`continentes-america.sdjf`, `git.sdjf`, etc.), agregar una sección nueva en este documento siguiendo el mismo formato. Numerar las entradas de forma global (`BUGS-DIAG-009`, `BUGS-DIAG-010`...).
