# Skill `almagag-diagramas` — contrato con AlmaGag

El skill de claude.ai que genera diagramas con AlmaGag. Este doc fija el
**contrato** entre el skill y el repo, para mantenerlos sincronizados.

> **Alcance (decisión del autor, 3-ago-2026): esto es una RECOMENDACIÓN NO
> VINCULANTE.** `almagag-diagramas` es la implementación de referencia del
> autor — no "el" skill. Cada usuario que implemente AlmaGag puede definir
> su propio skill con su propio catálogo de iconos, sus clases semánticas y
> sus convenciones, nada de lo cual vive en este repo. **La IA que
> implemente cada skill es la responsable de saber qué iconos tiene
> disponibles** (y de embeberlos en el `.gag` o aceptar el BWT rotulado si
> no los tiene). Lo único que el motor garantiza a cualquier skill es el
> formato de archivo (`docs/spec/FORMATO_ARCHIVOS.md`) y la frontera §R: el
> archivo declara intención y semántica, el motor decide toda la geometría.

## Qué asume el skill del repo (v3.6, iteración 6)

| Capacidad | Cómo la usa el skill |
|---|---|
| Motor único (`select`) | Comando normal SIN `--layout-algorithm`; se influye vía el JSON |
| Reglas `select_strategy` | view→hier · considerations→auto · contains→auto · areas→hier · decision→hier · ciclo sin coords→hier · resto→auto. **§O53**: la señal anulada por la precedencia se nombra en un WARNING |
| **Topología de red (§N45)** | nubes `cloud/inet/wan/internet` grado ≥2 + ≥30% enlaces `bidirectional`/`none`, sin coords → hub-and-spoke (banda «WAN» + sitios) |
| **Zonas `near` (§N46)** | `{"near":[...], "label":"..."}` = caja punteada rotulada; semillas parciales se completan por conectividad; near se cumple por construcción. Rótulo AA #6b6558 en banda reservada de 18px (§O54) |
| **Antes/después (§N47/N49)** | dos archivos con ids compartidos ⇒ misma plantilla de zonas (slots min-hash) |
| Leyenda (§N48) | automática con ≥3 `semantic_type` (clases custom válidas: nombre tal cual + color efectivo) |
| **Semántica de enlaces (§Q63)** | `semantic_type` SE DECLARA por conexión (clases del dominio, colores por tokens `theme`); el vocabulario texto→clase NUNCA vive en el motor. Opcional: sección `semantics` embebida (clase→keywords+color, como `icons{}`) que el motor aplica con WARNING a conexiones sin declarar; sin match → neutra |
| `unions` (§H7) | genealogías: un tronco por hijo |
| Métricas (§H6+§O52) | línea `[motor] cruces=… arista×nodo=… labels=… tinta=X% aspecto=Y` como control de calidad; WARNING con tinta<4% o aspecto fuera de [0.4, 3.0] |
| **Halo portable (§O50)** | el halo de texto es GEOMETRÍA SVG 1.1 (copia con trazo blanco bajo cada `<text>`, `class="ag-text-halo"`), nunca `paint-order`. **El parche cairosvg del skill quedó obsoleto**: rasterizar directo |
| **viewBox al contenido (§O51)** | la lámina emitida se recorta al bbox + 40px (sólo contrae); las leyendas se reanclan al nuevo borde inferior |
| **Alias de iconos (§O55+§Q64)** | `inet`/`wan`/`internet` dibujan `cloud`; un `type` desconocido → BWT visible CON EL NOMBRE DEL TYPE rotulado + WARNING; la línea `§Q64` inventaría los BWT activos. Usar un type nuevo a BWT deliberado es LEGÍTIMO mientras se decide su forma — el nombre debe explicarse solo. **El catálogo de iconos custom vive en el SKILL** (decisión del autor, 2-ago): el motor NO suma built-ins de dominio; un type que recurre en BWT se promueve al catálogo del skill (`references/`) como icono embebido |
| **Zonas anidadas (§P59+§P60)** | `area`+`contains` anidado SIN coordenadas: la contención reserva espacio real a toda profundidad; zonas con transporte inter-zona (`bidirectional`/`none`) van a la banda principal y las de sólo-soporte a la periferia; los enlaces inter-zona viajan por troncales ortogonales (una espina por par origen→destino). El skill declara estructura y `direction`; la geometría es del motor |
| **Afinidad entre áreas (§Q65)** | opcional `{"near": ["areaA", "areaB"]}` en `considerations` con ids de ÁREAS = bloque adyacente en su fila. Sin declarar, el orden se DERIVA: banda encadenada por transporte, periferia por baricentro, desempate por aparición — declarar sólo cuando hay lectura preferida |
| **Frontera motor⇄skill (§R)** | el skill declara intención/semántica; el motor decide TODA la geometría. Prohibido en el skill: coordenadas fijas para compensar defectos de layout (eso es bug del motor), semántica duplicada en el texto del label, types crípticos |
| **Escala tipográfica (§O56)** | nodo 14 · conexión 12 (color semántico) · rótulo zona/fase 11 bold (constantes en `config.py`) |
| **Tokens de tema (§O57)** | sección `theme` top-level + `"color": "<token>"` en elements/connections/areas/lanes/roles; hex literal gana |
| **PNG sin navegador (§O58)** | `--exportpng`: Chrome/Chromium/Edge si hay (multiplataforma), cairosvg si no; `ALMAGAG_CHROME` como override |
| Epifanía | `--epifania`: flipbook por fase con colisiones marcadas |
| **Flujos resaltados (WISH-DRAW-002)** | sección `flows` top-level: recorridos por ids con trazo de resaltador que sigue las rutas reales; `label` → leyenda «Flujos:»; anotación pura (no toca layout/métricas). Usarla para narrar caminos (paquete, trámite, aprobación) |
| **Etiquetas: lo dibujado ES lo medido (WISH-LAYOUT-008)** | UN solo optimizador (pasada global, compartida auto/hier); el renderer dibuja `label_positions`/`connection_labels` tal cual; el contador `labels` es la verdad visual en todo el pipeline. El skill puede confiar en la métrica sin re-inspeccionar posiciones |
| **Pitch label-aware (WISH-LAYOUT-009)** | celdas de grilla y avance de banda dimensionados por `max(icono, etiqueta)` por columna + reserva vertical por fila. Consecuencia de autoría: ACORTAR labels es la palanca #1 del ancho de lámina; no compensar fusiones con coordenadas |
| **Validador sin falsos positivos R3 (VAL-003)** | el histórico del FortiGate/`firewall` quedó resuelto: un R3 es un conector que de verdad cuelga |

## Recomendaciones para construir un skill de Claude sobre AlmaGag

Lo aprendido con `almagag-diagramas`, aplicable a cualquier skill que
genere diagramas con este motor — como guía, no como norma: cada
implementador arma el suyo. Principio rector (§R + Q63/Q64): **el motor
entrega MECANISMO; todo vocabulario de dominio — iconos, clases
semánticas, palabras clave — viaja en el skill o embebido en el archivo,
y es la IA que implementa ese skill quien administra su inventario.**

1. **Iconografía (§Q64 — el catálogo vive en el skill).** El motor trae
   ~12 built-ins genéricos y NO va a sumar iconos de dominio. El skill
   mantiene su catálogo (p. ej. `references/iconos-negocio.md`: 16
   filled-outline, incl. el paquete minero/energía `tower`, `cow`,
   `truck`, `cpe`, `generator`, `powergrid`) y copia a la sección
   `icons{}` de cada .gag SOLO las entradas usadas — los archivos son
   autocontenidos.
2. **Color en los SVG embebidos.** Desde BUGS-DRAW-002 (2-ago) el motor
   SÍ resuelve `currentColor` con el `color` del elemento (default gray):
   un solo icono sirve para todas las variantes — ya no hace falta
   duplicar entradas por color. Un icono con hex FIJOS (como el catálogo
   actual del skill) se inserta tal cual y el `color` no lo afecta;
   ambas formas conviven.
3. **BWT deliberado como etapa legítima.** Un `type` sin icono todavía
   se usa igual: el plátano con el nombre rotulado es un placeholder
   honesto. Regla: el nombre debe explicarse solo. La línea de log
   `§Q64: N type(s) en BWT` es la señal de promoción — al catálogo del
   SKILL, no al motor.
4. **Semántica declarada (§Q63).** El skill declara `semantic_type` por
   conexión (clases del dominio) + colores por tokens `theme`; con ≥3
   clases la leyenda sale sola. Si prefiere inferencia, emite la sección
   `semantics` embebida (clase→keywords) — el motor la aplica con
   WARNING. Jamás pedir/esperar vocabulario dentro del motor.
5. **Geometría: declarar intención, nunca coordenadas.** Estructura con
   `area`+`contains` anidado, `direction` en toda conexión (el
   transporte `bidirectional` manda zonas a la banda §P60), afinidad
   `near` de áreas sólo con lectura preferida (§Q65). Si un diagrama
   "necesita" coords fijas para verse bien, eso es un bug del motor:
   reportarlo, no parchearlo en el skill.
6. **Verificar contra el código, no contra los docs.** Regla de oro
   vigente: ante duda, `main.py`/`select_strategy`/el módulo — este
   contrato se actualiza cuando el motor cambia, y a veces la spec
   miente (caso `currentColor`).
7. **Autoría de HLDs (grupo S del review, ago-2026 — con veredicto A/B
   medido).** Cuatro reglas, dos vigentes hoy y dos en espera de motor:
   - **S67 (vigente, adoptada)**: partir los nodos-servicio compartidos
     por sitio — si el servicio existe físicamente en cada sitio (GEs,
     energía, almacén), un nodo por sitio DENTRO de su zona. Un nodo
     único sólo para servicios realmente centrales (un NOC, una SRA).
   - **S68 (vigente, y suele ser no-op)**: afinidad `near` entre áreas
     sólo con lectura preferida — el A/B mostró que la derivación §Q65
     ya producía ese orden sola.
   - **S66 (EN ESPERA de WISH-ROUTE-001)**: «todo elemento operativo en
     un grupo de primer nivel del principio organizador de la vista»
     (física → zonas geográficas; HLD funcional → capas acceso ·
     transporte · core · gestión; nunca mezclar ambos ejes). El A/B del
     3-ago midió que HOY agrupar degrada (4→13 cruces, 0→6 a×n) porque
     el ruteo hacia contenedores está roto — posponer las cajas hasta
     que T70/T71 aterricen.
   - **S69 (EN ESPERA, misma razón)**: los agrupadores se declaran como
     `area` (caja + rótulo, sin icono — T73 ya no emite el slot), no
     como `building` con `contains`; `building` es para edificios que
     son elementos. El A/B actual favorece building-contenedor (39.2%
     tinta / 1.22 vs 63.6% / 1.91) — se invierte cuando llegue T.

## Mantenimiento
- El skill vive en el perfil de claude.ai del autor (`SKILL.md` + `references/`).
- Última sincronización: **v3.6** (3-ago-2026, iteración 6: `flows`,
  etiquetas unificadas + medición veraz, pitch label-aware, VAL-003).
- Al agregar capacidades al motor: actualizar el skill (paso de diseño +
  debugging + `references/motores-y-vistas.md`) y esta tabla.
- Regla de oro del skill: **el código gana a los docs**; verificar contra
  `main.py`/`select_strategy` antes de documentar.
