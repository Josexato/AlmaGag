# Roadmap de AlmaGag

**Versión actual**: v3.5.0 · **Actualizado**: 2026-08-02
El backlog VIVO son los tickets de [`TECHNICAL_DEBT.md`](TECHNICAL_DEBT.md)
(BUGS-*/WISH-*); este documento da el mapa de alto nivel. El roadmap
histórico (v1→v2.x, con el plan original de routing) está en
[`architecture/history/ROADMAP-2026-02.md`](architecture/history/ROADMAP-2026-02.md).

---

## Dónde estamos (v3.5, ago-2026)

AlmaGag genera diagramas SVG desde JSON declarativo **sin coordenadas y sin
elegir algoritmo**: el motor decide la estrategia desde el archivo y toda la
geometría es suya (frontera §R). Lo construido, por capas:

- **Motor único** — `select_strategy` (7 reglas, precedencia con WARNING
  §O53) + `LayoutEngine` con estrategias `auto` (principal), `hier`
  (flujos/vistas `areas·lanes·matrix`) y `legacy` (ex-LAF, congelado).
- **Estructura** — contenedores anidados con espacio real §P59; zonas
  operativas/servicio en banda/periferia con troncales ortogonales §P60;
  afinidad y orden derivado entre áreas §Q65; zonas `near` por construcción
  §N46; topología de red hub-and-spoke §N45; `unions` §H7; 10 plantillas
  (`layout_template`) con auto-detección.
- **Semántica** — `semantic_type` declarado + clases custom + leyenda §N48;
  mapa `semantics` embebido §Q63; tokens de tema §O57. **El vocabulario
  nunca vive en el motor** (vigilado por test).
- **Emisión** — halo portable §O50, viewBox al contenido §O51, métricas de
  lámina §O52, escala tipográfica fija §O56, BWT rotulado + alias §O55/§Q64,
  PNG multiplataforma §O58, anticolisión global de etiquetas §P61.
- **Calidad** — línea `[motor] cruces/arista×nodo/labels/tinta/aspecto`,
  guarda anti-regresión (`scripts/measure_fixtures.py`), validador R1/R2/R3,
  Epifanía, ~446 tests, determinismo.

Los reviews de Claude Design (grupos A–R, iteraciones 1–5) están **completos**
— archivo por iteración en `docs/reviews/`.

## Lo siguiente (iteración 6)

| Orden | Qué | Ticket |
|---|---|---|
| 1 ✅ | **Flujos de información resaltados** — HECHO (2-ago): `flows` top-level, trazo semitransparente que sigue las rutas reales, leyenda «Flujos:», invisible para métricas | WISH-DRAW-002 |
| 2 | **Unificar los 3 sistemas de etiquetas** + medición veraz en todo el pipeline — precursor del «0 fusiones» y del pitch label-aware | WISH-LAYOUT-008 |
| 3 | **Guardado H3 justo** — comparar re-ruteos con geometría vigente (hoy compara contra rutas rancias); sesión dedicada con la guarda | BUGS-AUTO-009 |

## Mediano plazo (sin fecha)

- **«El mapa» (WISH-ARCH-004)**: separar mapa (dato) de vista (representación)
  — diseño en revisión, `architecture/WISH-ARCH-004-el-mapa.md`.
- **Clasificador de `select_strategy`** con más señales (mejora continua del
  cierre de WISH-ARCH-002).
- **Catálogo de iconos**: vive y crece en el SKILL, no aquí (decisión §Q64);
  el motor sólo aporta mecanismo (BWT rotulado + inventario).

## Descartado (para que nadie lo resucite sin querer)

- `avoid_elements` (propiedad de routing): la evitación de obstáculos es
  INCONDICIONAL vía visibility graph — decisión del autor, 2026-08-02.
- LAF como algoritmo elegible: congelado como `legacy`, sólo debug.

## Cómo se trabaja

Un criterio por commit · test de regresión + verificación visual PNG antes
de cada commit · guarda anti-regresión (probar → medir → revertir si
empeora) · suite `python -m pytest -q --import-mode=importlib` siempre verde
· flujo commit → push → PR → merge por bloque · reviews externos por
iteración con paquete en `docs/reviews/`.
