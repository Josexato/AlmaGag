# Roadmap de AlmaGag

**Versión actual**: v3.11.0 (pyproject; sube con cada iteración del review
cerrada — 6→3.6, 7→3.7, 8→3.8; 3.9 = consistencia del término «flow» —
en sincronía con el skill) · **Actualizado**: 2026-08-11
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
| 3 ✅ | **`align[]` contrato duro** — HECHO (10-ago): eje x entre rangos honrado en el positioner (5/5 aligns; tronco en una columna) + audit `[align]` que nombra toda violación | WISH-LAYOUT-013 |
| 4 ✅ | **`canvas.flow`** — HECHO (10-ago): up/down (left/right reservados con warning); el presupuesto declara `up` y lee como pirámide de agregación; cruces 2→0 | WISH-LAYOUT-012 |
| 5 ✅ | **`canvas.legend[]` + `element.status`** ◉◪▢ — HECHO (10-ago): badge que colorea la línea de estado + leyenda libre apilada; el fixture ya no pinta glifos a mano | WISH-DRAW-004 |

**Iteración 8 COMPLETA (10-ago)** — el presupuesto pasó de 1400×2136 con
2/5 aligns y lectura invertida a una pirámide de agregación 0/0/1 con
5/5 aligns, `flow: "up"`, feeder lateral, puertos ≥18px y estados de
primera clase.

## Iteración 9 — el caso TM en el visor (11-ago): densidad y llegadas

El autor renderizó el presupuesto real en gag-viewer-poc y reportó tres
molestias: letra chica, flechas que doblan justo al llegar al icono, y
distancia vertical excesiva. Diagnóstico medido: las tres nacen en el
motor (el visor es sólo capa de presentación).

| Orden | Qué | Ticket |
|---|---|---|
| 1 ✅ | **Gap vertical medido** — HECHO (11-ago): cada mitad del corredor libra el stack de labels de su lado (+label de conexión si lo hay); TM 1891→1267 de alto (−33%); las pasadas blandas arrastran el label con el icono | WISH-LAYOUT-016 |
| 2 ✅ | **El codo nunca justo en el icono** — HECHO (11-ago): `routing.preference` honrada hasta el final del pipeline; codo terminal a mitad del tramo largo, consciente de obstáculos; llegadas H 9→1 en TM; snap casi-alineados (≤ media ranura) | BUGS-ROUTE-003 |
| 3 ✅ | **Tipografía 16/13/12** — HECHO (11-ago): recalibración O56 con estimaciones veraces (char 9.2, línea 20.6); honor V79 con empuje de vecinos no-contrato; presupuesto 2→0 cruces, labels bajan en cadena | O56 recalibrado |
| 4 ✅ | **Leyendas con franja propia** — HECHO (11-ago): el recorte O51 extiende el borde inferior para alojar la pila completa + 12px | BUGS-DRAW-005 |

**Iteración 9 COMPLETA (11-ago)** — el TM pasó de 1371×1891 con letra de
~7px aparentes, 9 llegadas de codo pegado y leyenda sobre la última fila
a 1483×1391 con letra 16px, llegadas verticales a mitad de corredor y
leyenda en franja propia. Motor v3.10.0.

## Iteración 10 — grupo W del review (11-ago): higiene de bandas y última milla

Claude Design midió el presupuesto v3 (render del motor v3.10) y abrió
W83-W89. Además, la pregunta del autor sobre los tres resúmenes destapó
WISH-LAYOUT-017 (resuelto el mismo día). Todos los W verificados por
ejecución contra master antes de ticketear (W84 refutado en iconos,
W86 matizado — ver TECHNICAL_DEBT).

| Orden | Qué | Ticket |
|---|---|---|
| 1 ✅ | **align y entre rangos = FILA** — HECHO (11-ago): promoción de rango; la «capa de resúmenes» del presupuesto (ring/rproc/constr en una fila) con lo infactible nombrado | WISH-LAYOUT-017 |
| 2 ✅ | **Cero diagonales** — HECHO (11-ago): eran los EMPALMES de las bandas (4→0, codo ortogonal en el nodo intermedio) | BUGS-ROUTE-004 |
| 3 ✅ | **Higiene de bandas** — HECHO (11-ago): encierro ya inexistente (re-medido); audit que nombra bandas sobre iconos ajenos o que pasean >1.25× | WISH-DRAW-006 |
| 4 ✅ | **Labels atravesados por su propia arista** — HECHO (11-ago): los 5 cruces eran PROPIOS; canal label_own_line + score P61 a 0.5; 5→3 con restantes nombrados | WISH-ROUTE-004 |
| 5 ✅ | **Franjas ajenas como zona a evitar** — HECHO (11-ago): labels bajo banda ajena 2→0 | WISH-LAYOUT-018 |
| 6 ✅ | **Journey como primitivo de colocación** — HECHO (11-ago): columnas derivadas (autor gana, empuje en cadena); dispersión 195/94/154 → 0/5/0; bandas rectas como consecuencia | WISH-LAYOUT-019 |

**Mediano plazo del grupo**: WISH-ARCH-006 (derivabilidad W89 — el
presupuesto de ~470 a ~200 líneas; fixture reducido ≡ completo como test
de éxito).

**Iteración 10 COMPLETA (11-ago)** — grupo W cerrado: bandas con
empalmes ortogonales y vigiladas, labels atravesados vistos y resueltos,
franjas ajenas como zona a evitar, y el journey como primitivo de
colocación (las tres cadenas del presupuesto en columnas rectas con los
5 aligns del autor intactos). Motor v3.11.0.

## Iteración 11 — grupo X del review (11-ago): el caso tabernero, áreas a escala

Claude Design corrió un caso NUEVO (tabernero: vitivinícola GAG-WV, 57
elementos, 75 conexiones, 9 áreas con members, SDJF 2.0) y abrió
X90-X93. Todos los claims verificados por ejecución contra master
v3.11.0 antes de ticketear: hier, cruces=247, arista×nodo=37, labels=0,
aspecto=14.36, las 9 áreas en UNA fila (11129×893); el punto ciego X93
resultó PEOR que lo reportado (28 pares título↔label-de-arista con el
contador en cero — causa en `seed_label_truth`, etiquetas estructurales
fuera de `label_positions`). Referencia del artefacto: la misma lámina
en 2600×1700 (aspecto 1.53) con macro-grilla de 3 bandas y bus TI.

| Orden | Qué | Ticket |
|---|---|---|
| 1 ✅ | **Schema que habla** — HECHO (11-ago): audit_schema nombra claves desconocidas + spec_version; destapó claves muertas en fixtures propios | BUGS-VAL-007 |
| 2 ✅ | **Contador labels veraz** — HECHO (11-ago): bbox estructural sintetizado + medición bajo demanda (hier reportaba 0 SIEMPRE); tabernero 0→113 sincerado | BUGS-VAL-008 |
| 3 ✅ | **Área como unidad de layout** — HECHO (11-ago): envoltura 2D al aspecto (jamás 1×N) + area.role + ruteo por eje dominante; tabernero aspecto 14.36→0.75, cruces 247→203 | WISH-LAYOUT-020 |
| 4 ✅ | **`canvas.partition`** — HECHO (11-ago): bsp/grid en proporciones escaladas al contenido; con el plan de 4 bandas cruces 203→125 | WISH-LAYOUT-021 |
| 5 ✅ | **Bus para hubs multi-área** — HECHO (11-ago): troncal + ramales; los 3 hubs TI del tabernero detectados | WISH-ROUTE-005 |
| 6 ✅ | **Labels en cascada** — HECHO (11-ago): anclas §G23 medidas donde se dibujan + cascada perpendicular 14px; activacion 7→2, layout-opt 16→9, tabernero 145→123 | WISH-DRAW-007 |

**Iteración 11 COMPLETA (11-ago)** — grupo X cerrado: el motor ya no
acepta en silencio, ya no miente el contador, y las áreas son unidad
de layout de verdad — macro-grilla 2D derivada o declarada
(`canvas.partition`), buses para hubs multi-área y anclas en cascada.
El tabernero pasó de una cinta 11129×893 ilegible (aspecto 14.36) a una
lámina 2450×3352 en rango con la lectura del render de referencia.
Motor v3.12.0.

**Mediano plazo del grupo (Y94-Y97, requieren decisión de José)**:
WISH-ARCH-007 (SDJF 2.0: JSON Schema en repo, sintaxis canónica,
deprecaciones con aviso), WISH-VAL-001 (audit como COMPUERTA: umbrales
duros → reparación → exit ≠0 + DRAFT; hoy exit 0 con §O52 violado),
WISH-DRAW-008 (journeys = presentación pura: mismo SVG con/sin bandas
salvo membresía W88), WISH-ARCH-008 (parejas mínimo≡completo en CI,
hermano operativo de WISH-ARCH-006).

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
