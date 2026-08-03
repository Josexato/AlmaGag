# Glosario de AlmaGag (v3.5)

**Actualizado**: 2026-08-02, verificado contra el código. El glosario
anterior (era AUTO-vs-LAF) está en
[`architecture/history/CONCEPTS-2026-02.md`](architecture/history/CONCEPTS-2026-02.md).
📍 = dónde vive en el código.

---

## El formato

- **SDJF / `.sdjf`** — el JSON declarativo de diagramas (elements +
  connections + secciones opcionales). 📍 spec viva:
  `docs/spec/FORMATO_ARCHIVOS.md`.
- **GAG / `.gag`** — el mismo JSON con iconos SVG embebidos en `"icons"`.
  El motor trata ambas extensiones igual; es convención de autoría.
- **`direction`** — `forward` · `backward` · `bidirectional` · `none`. No es
  cosmética: `bidirectional`/`none` = TRANSPORTE y clasifica zonas (§P60) y
  detecta topologías de red (§N45).
- **`semantic_type`** — la CLASE de un enlace (canónica o custom del
  dominio). Con ≥3 clases distintas, leyenda automática §N48. 📍
  `draw/primitives/svg.py::SEMANTIC_CONNECTION_COLORS`.
- **`semantics` (§Q63)** — mapa embebido texto→clase que el motor aplica
  con WARNING a conexiones sin declarar. El vocabulario viaja en el archivo
  o en el skill, nunca en el motor. 📍 `layout/semantics.py`.
- **`theme` (§O57)** — tokens de color top-level; cualquier `color` que
  coincida exacto con un token se resuelve a su hex antes del render. 📍
  `layout/theme.py`.
- **`contains`** — convierte un elemento en CONTENEDOR; anidable. Desde
  §P59 la contención reserva espacio real a toda profundidad.
- **`area` (type)** — contenedor de ZONA física. Zonas top-level sin coords
  disparan el macro-layout banda/periferia §P60.
- **`considerations`** — `align` (blanda), `avoid` (blanda), `near` (DURA:
  zona por construcción §N46; con ids de ÁREAS = afinidad §Q65). 📍
  `layout/considerations.py`.
- **`areas` / `lanes` / `roles`** — metadata de fase/responsable para las
  vistas de `hier` (`--view areas|lanes|matrix`). 📍 `strategies/hier/`.
- **`flows` (WISH-DRAW-002)** — flujos de información resaltados: capa
  de anotación tipo resaltador que recorre elementos EN ORDEN siguiendo
  las rutas dibujadas; `class="ag-flow"`, invisible para métricas y
  validador; leyenda «Flujos:». 📍 `draw/primitives/flows.py`.
- **`unions` (§H7)** — pareja → nodo de barra + un tronco por hijo
  (genealogías). 📍 `layout/unions.py`.
- **`layout_template`** — patrón macro (`architecture`, `flow`,
  `hub_and_spoke`, `dashboard`, `er`, `sequence`, `state`, `nested`…) con
  auto-detección; `hier` los ignora. 📍 `layout/templates/`.

## El motor

- **`select_strategy`** — LA decisión central: 7 reglas en orden (view→hier,
  considerations→auto, contains→auto, areas→hier, decision→hier, ciclo sin
  coords→hier, resto→auto); la señal anulada se nombra en WARNING §O53. 📍
  `generator.py`.
- **`LayoutEngine`** — despacho de estrategias (`auto`/`hier`/`legacy`). 📍
  `layout/engine.py::_STRATEGIES`.
- **`auto`** — estrategia principal: niveles topológicos + barycenter +
  contenedores + zonas + loop de optimización + anticolisión. 📍
  `strategies/auto/`.
- **`hier`** — flujo dirigido por niveles/columnas, decisiones, SCC,
  vistas por área/carril/matriz. 📍 `strategies/hier/`.
- **`legacy`** — el ex-LAF, CONGELADO; nunca se auto-elige; conserva la
  Epifanía histórica. 📍 `strategies/legacy/`.
- **Super-nodo rígido (§P59)** — un contenedor resuelto se mueve como
  bloque indivisible (`_shift_container_subtree`); las celdas de su grilla
  usan el tamaño REAL de cada hijo.
- **Banda / periferia (§P60)** — zonas con transporte inter-zona van
  adyacentes a la banda principal; las de sólo-soporte, a la fila
  periférica. 📍 `strategies/auto/zones.py`.
- **Troncal (§I29/§P60)** — los enlaces de un par de zonas comparten UNA
  espina ortogonal en el corredor (`_zone_trunk`, recomputada en cada
  re-ruteo).
- **Zona `near` (§N46)** — cluster compacto por construcción con caja
  punteada rotulada (§O54) y expulsión de intrusos.
- **Anticolisión global (§P61)** — última etapa: reubica etiquetas (toda
  profundidad, deslizamiento por polilínea) sin tocar iconos ni rutas. 📍
  `strategies/auto/anticollision.py`.
- **Medición veraz (`_measure_stored_labels`)** — en la etapa final el
  detector mide las etiquetas donde se DIBUJAN; las heurísticas intermedias
  siguen calibradas con la posición canónica (migración: WISH-LAYOUT-008).
- **Rescates** — ① compactación por offsets de bloque
  (`layout/offset_optimizer.py`), ② contracción SCC (`hier/scc.py`),
  ④ consideraciones blandas guardadas.

## Dibujo y emisión

- **BWT** — Banana With Tape: fallback VISIBLE para un `type` sin icono,
  ROTULADO con el nombre (§Q64) + WARNING §O55 + inventario en el log.
  Usarlo a propósito es legítimo mientras un concepto no tiene forma.
- **Alias de iconos (§O55)** — `inet`/`wan`/`internet` dibujan `cloud` (y
  cuentan como hub §N45).
- **Iconos embebidos** — sección `"icons"`; `currentColor` se resuelve al
  `color` del elemento (BUGS-DRAW-002); hex fijos se insertan tal cual.
  **El catálogo de dominio vive en el skill** (§Q64). 📍 `draw/icons/`.
- **Halo portable (§O50)** — el halo de texto es GEOMETRÍA SVG 1.1 (gemelo
  con trazo blanco, `class="ag-text-halo"`), no CSS: cualquier rasterizador
  es fiel.
- **viewBox al contenido (§O51)** — la lámina se recorta al bbox + 40px
  (sólo contrae); leyendas re-ancladas. 📍 `draw/primitives/viewbox.py`.
- **Leyenda §N48** — «Enlaces:» al pie con ≥3 `semantic_type` distintos.
- **Callout** — labels enormes (≥6 líneas / ≥150 chars) van a caja aparte
  con línea guía; override con `"callout": true|false`.
- **Epifanía** — `--epifania`: un SVG por fase del pipeline + flipbook, con
  colisiones marcadas. 📍 `layout/epifania.py`.
- **`--exportpng` (§O58)** — Chrome/Chromium/Edge headless si hay
  (`ALMAGAG_CHROME` como override), cairosvg si no.

## Calidad y proceso

- **Línea `[motor]`** — `cruces(arista×arista)`, `arista×nodo`, `labels`,
  `tinta` (§O52, <4% avisa), `aspecto` (fuera de [0.4, 3.0] avisa). 📍
  `layout/metrics.py`.
- **Guarda anti-regresión** — `scripts/measure_fixtures.py`: una línea por
  fixture; patrón *probar → medir → revertir si empeora*; aborta ruidoso si
  mide 0.
- **Validador R1/R2/R3** — audit del SVG emitido: etiqueta sobre icono,
  etiquetas solapadas, conector colgante. 📍 `validation/visual_quality.py`.
- **NdDp / NdPr / NdFn** — identificadores de debug de nodos (dato /
  primario / final) para `--visualdebug`; no son parte del formato.
- **Frontera §R** — el archivo/skill declara intención y semántica; el
  motor decide TODA la geometría. Coordenadas fijas para compensar un
  layout feo = bug del motor, se reporta.
- **Tickets** — `BUGS-*` / `WISH-*` en `TECHNICAL_DEBT.md` (métricas por
  grep). Reviews externos por iteración en `docs/reviews/`.
