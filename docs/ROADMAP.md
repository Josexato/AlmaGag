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

## Iteración 6 — COMPLETA (2/3-ago-2026)

| Orden | Qué | Ticket |
|---|---|---|
| 1 ✅ | **Flujos de información resaltados** — `flows` top-level, trazo semitransparente que sigue las rutas reales, leyenda «Flujos:», invisible para métricas | WISH-DRAW-002 |
| 2 ✅ | **Unificar los 3 sistemas de etiquetas** + medición veraz en TODO el pipeline — un solo optimizador (pasada global, compartida auto/hier); el renderer dibuja la verdad; destapó y corrigió 3 bugs latentes (solape de contenedores post-loop, etiquetas que no viajaban con su bloque, posiciones rancias) | WISH-LAYOUT-008 |
| 3 ✅ | **Guardado H3 justo** — el revert viciado se eliminó: re-ruteo obstacle-aware incondicional; invariante «rutas ancladas a geometría vigente» con test | BUGS-AUTO-009 |
| 4 ✅ | **Pitch label-aware** — celdas/bandas al ancho de la ETIQUETA en toda grilla; labels −35 y a×n −5 netos (fila de torres del minero legible, git 26→12) | WISH-LAYOUT-009 |

## Lo siguiente (iteración 7 — grupos T y U del review, 5-ago)

El artefacto de Claude Design incorporó el A/B del 3-ago y abrió tres
grupos: S (autoría/skill — S67 adoptada, S66/S69 re-alcance esperando T),
T (motor: ruteo hacia contenedores) y U (motor: refinamiento de flows).
T73 (áreas sin slot de icono) ya quedó resuelto el mismo día.

| Orden | Qué | Ticket |
|---|---|---|
| 1 ✅ | **Ruteo hacia contenedores** — HECHO (5-ago): puertos de perímetro con llegada perpendicular, tres tramos con carriles anti-hermanos, reparto ≥18px. a×n −10 neto; hld y 07-containers sin diagonales de borde. **Desbloquea re-medir S66/S69** | WISH-ROUTE-001 |
| 2 ✅ | **Presupuesto de espacio por contenedor** — HECHO (5-ago): título como zona dura para miembros, iconos pesan ×2 en el score, candidatos al costado del conector. Neto −5 labels; pares sobre icono: físico v2 7→4, cheatsheet 12→9; header de ZONA PILA limpio | WISH-LAYOUT-010 |
| 3 ✅ | **Flows: carriles paralelos + contrato** — HECHO (5-ago): U74/U77 error duro por par sin conexión, label obligatorio, warning color repetido; U75 tramos compartidos en carriles (paso = ancho, sin taparse); U76/J33 cadenas ≥5 plegadas en serpentina apaisada | WISH-DRAW-003 |
| 4 ✅ | **Libres multi-zona** — HECHO (5-ago): el mal puesto va a la periferia del hull por el lado del baricentro de sus vecinos. Cruces −6 neto; físico v2 con tinta 36.5→52.8% y aspecto 1.42 | WISH-AUTO-010 |

> Fixtures del caso real evolucionado (3-ago, anonimizados §P62):
> `mina-fisico-v2.gag` (17/8/17) y `mina-hld.gag` (4/0/1, el adoptado).
> Nota del review: la numeración del artefacto (I27/Q65…) no coincide con
> los §§ del contrato del skill — al citar entre equipos, usar el id del
> contrato (`SKILL-ALMAGAG.md`).

## Iteración 8 — grupo V del review (10-ago): el caso presupuesto

El artefacto de Claude Design incorporó el formato de presupuesto (22
hojas, pirámide de agregación) y abrió el grupo V. Fixture anonimizado:
`mina-presupuesto.gag` → `docs/diagrams/gags/mina-presupuesto.sdjf`
(23/19, 5 `align[]`, 3 flows, 1 contenedor-feeder). Verificado por
ejecución el 10-ago: 4/5 aligns ya se cumplen (el artefacto midió 2/5
pre-iteración 7) y el hack f4 ya lo caza U74/U77 con error duro.

| Orden | Qué | Ticket |
|---|---|---|
| 1 ✅ | **Contenedor-feeder al carril lateral** — HECHO (10-ago): dppto→ppto 635→290, lienzo 2205→1960, arista 2 codos | WISH-LAYOUT-014 |
| 2 ✅ | **Convergencia limpia** — HECHO (10-ago): eslabones 1:1 en la misma columna (pulab→mo vertical pura) + puertos T72 en nodos (llegadas perpendiculares, puntas ≥18px) | WISH-ROUTE-002 |
| 3 | **`align[]` contrato duro** — audit que nombra la violación + caso eje x + estirar cadena corta | WISH-LAYOUT-013 |
| 4 | **`canvas.flow`** — orientación de lectura up/down/left/right (roll-ups leen de abajo hacia arriba) | WISH-LAYOUT-012 |
| 5 | **`canvas.legend[]` + `element.status`** ◉◪▢ — reemplazo de primera clase del hack f4 (la mitad audit ya está) | WISH-DRAW-004 |

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
