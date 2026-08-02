# Auditoría 1/3 — Spec de formato (`docs/spec/FORMATO_ARCHIVOS.md`) vs código

Auditoría completada. Incongruencias verificadas, de mayor a menor gravedad:

---

## 1. La sección top-level `semantics` (§Q63) no está documentada — FALTA DOCUMENTAR (crítica)

- **Spec:** cero ocurrencias de `semantics` en las 840 líneas. Y la línea 3 afirma: *"Si algo no esta aqui, no existe en el formato."*
- **Código:** `/home/user/AlmaGag/AlmaGag/layout/semantics.py:34-74` (`apply_embedded_semantics`), cableado en `/home/user/AlmaGag/AlmaGag/generator.py:129-130`. Formato real (semantics.py:18-22): `"semantics": {"transporte": {"keywords": [...], "color": "#1f6fd0"}, "soporte": ["soporte","FAT"]}` — dos formas por clase, match por subcadena case-insensitive contra el label, primera clase que matchea gana, no pisa `semantic_type` declarado, emite WARNING.
- Existe test versionado: `tests/test_q63_semantics.py`.

## 2. La sección top-level `theme` (§O57) no está documentada — FALTA DOCUMENTAR (crítica)

- **Spec:** cero ocurrencias. La §8 "Colores validos" (líneas 620-648) declara que sólo hay nombres CSS y hex.
- **Código:** `/home/user/AlmaGag/AlmaGag/layout/theme.py:21-52`; generator.py:134-135. Un `"color"` cuyo valor coincida exactamente con una clave de `theme` se sustituye por su hex ANTES del pipeline, y aplica a `elements`, `connections`, `areas`, `lanes` y a los valores de `roles` (theme.py:39-47). Test: `tests/test_theme_tokens.py`.

## 3. `type: "area"` y todo el macro-layout de zonas (§P60/§Q65) no están documentados — FALTA DOCUMENTAR (crítica)

- **Spec:** la §7 (líneas 601-616) lista 12 tipos y cierra con *"Si pones un tipo que no existe (ej: `"type": "xyz"`), AlmaGag dibuja una banana con cinta (BWT)"*. `area` no aparece.
- **Código:** `/home/user/AlmaGag/AlmaGag/layout/strategies/auto/zones.py:50-57` — `top_level_area_zones()` trata los contenedores `type: "area"` sin padre como zonas de primer nivel; zones.py:66-104 los clasifica en operativas vs servicio y zones.py:150-261 reordena banda/periferia y marca troncales `_zone_trunk`. Es un comportamiento de layout mayor disparado por un valor de `type` que la spec presenta como inexistente.

## 4. `corner_radius` por defecto es 25, no 0 — DOC MIENTE

- **Spec, línea 406:** `` | `corner_radius` | numero | 0 | Radio de las esquinas en pixeles. 0 = esquinas cuadradas. | ``
- **Código:** `/home/user/AlmaGag/AlmaGag/routing/orthogonal_router.py:81` → `corner_radius = routing.get('corner_radius', CORNER_RADIUS_DEFAULT)`, y `/home/user/AlmaGag/AlmaGag/config.py:91` → `CORNER_RADIUS_DEFAULT = min(ICON_WIDTH, ICON_HEIGHT) * 0.5  # 25px`. Un `routing: {"type":"orthogonal"}` sin más produce esquinas redondeadas de 25px, no cuadradas.

## 5. `preference` por defecto es `"auto"`, no `"horizontal"` — DOC MIENTE

- **Spec, línea 407:** `` | `preference` | string | `"horizontal"` | `"horizontal"` = sale horizontal primero. ``
- **Código:** `orthogonal_router.py:80` → `preference = routing.get('preference', 'auto')`, resuelto en `orthogonal_router.py:258-259`: `if preference == 'auto': preference = 'horizontal' if abs(dx) > abs(dy) else 'vertical'`. El default depende del eje dominante, no es fijo horizontal.

## 6. `near` con ids de ÁREAS es afinidad de zonas, no acercamiento (§Q65) — DOC DESACTUALIZADA

- **Spec, línea 231:** `` | `near`  | Acerca los elementos hacia su centroide (reduce la caja que los contiene) | — | ``
- **Código:** `/home/user/AlmaGag/AlmaGag/layout/strategies/auto/zones.py:106-121` — si TODOS los ids de un `near` son zonas top-level, se marca `cons['_zone_affinity'] = True` y se consume como bloque indivisible de adyacencia en la fila (zones.py:154-158). Ese `near` entonces se salta explícitamente en `/home/user/AlmaGag/AlmaGag/layout/considerations.py:199-200` y en `/home/user/AlmaGag/AlmaGag/layout/strategies/auto/optimizer.py:552`. Semántica completamente distinta a la documentada. Test: `tests/test_q65_zone_affinity.py`.

## 7. `near` se cumple por CONSTRUCCIÓN (zona clusterizada) y acepta `label` — DOC DESACTUALIZADA

- **Spec, líneas 231 y 236-238:** describe `near` como empujón blando best-effort *"se prueban una por una y sólo se conservan si no suben las colisiones"*.
- **Código:** `considerations.py:173-268` (`cluster_near_groups`, §N46) coloca los miembros en una grilla compacta ANTES del ruteo; `optimizer.py:546-554` lo dice explícito: *"§N46: `near` ya NO pasa por aquí — se cumple por construcción como zona"* — sólo `align`/`avoid` quedan blandas. Además `considerations.py:69-71` acepta `{"near": [...], "label": "..."}` (rótulo de la caja de zona), campo que la spec no menciona; y `considerations.py:320-395` expulsa intrusos del bbox de la zona.

## 8. `areas`/`lanes`/`roles` NO requieren `--layout-algorithm=hier` — DOC DESACTUALIZADA

- **Spec, línea 155:** *"Sólo las usa `--layout-algorithm=hier`."*
- **Código:** `generator.py:57-58` — `if data.get('areas'): return 'hier'`: declarar `areas` ya enruta a hier sin ningún flag (default `select`, main.py:66-74). Y `generator.py:238-243` + `considerations.py:81-121` (`areas_to_near_seeds`) hacen que el motor **AUTO** también consuma `areas`, sembrándolas como zonas `near`. La afirmación "sólo hier" es falsa en ambas direcciones.

## 9. La sección top-level `unions` (§H7) y el `type: "union"` no están documentados — FALTA DOCUMENTAR

- **Spec:** cero ocurrencias.
- **Código:** `/home/user/AlmaGag/AlmaGag/layout/unions.py:26-60` (`expand_unions`), invocado en `generator.py:120-123` ANTES de elegir estrategia. Schema real: `"unions": [{"id": "u1", "between": ["jose","daria"]}]`. Genera un elemento sintético `type: "union"` dibujado como barra corta (`/home/user/AlmaGag/AlmaGag/draw/icons/__init__.py:370-381`), no como icono ni como banana. Test: `tests/test_union.py`.

## 10. Campo `callout` por elemento no documentado — FALTA DOCUMENTAR

- **Spec:** cero ocurrencias; la tabla de campos de `elements` (líneas 289-300) no lo lista.
- **Código:** `/home/user/AlmaGag/AlmaGag/draw/primitives/callout.py:37-38` → `if 'callout' in elem: return bool(elem['callout'])` (override explícito), con auto-activación por umbral en `config.py:131-132` (`CALLOUT_MIN_LINES = 6`, `CALLOUT_MIN_CHARS = 150`). O sea: un label de ≥6 líneas cambia de renderizado sin que la spec lo advierta.

## 11. Campos `width`/`height` por elemento no documentados y tienen precedencia sobre `hp`/`wp` — FALTA DOCUMENTAR

- **Spec, líneas 297-298:** sólo documenta `hp`/`wp` como forma de dimensionar.
- **Código:** `/home/user/AlmaGag/AlmaGag/layout/sizing.py:37-39`: `if 'width' in element and 'height' in element: return (element['width'], element['height'])` — explícito gana sobre hp/wp (documentado en el docstring sizing.py:17-19 como "1. width/height explícitos"). `width`/`height` sueltos también se respetan (sizing.py:45-46).

## 12. Alias de iconos `inet`/`wan`/`internet` → `cloud` no documentados — FALTA DOCUMENTAR

- **Spec, línea 616:** *"Si pones un tipo que no existe (ej: `"type": "xyz"`), AlmaGag dibuja una banana con cinta (BWT)"* — un lector concluiría que `inet` da banana.
- **Código:** `/home/user/AlmaGag/AlmaGag/draw/icons/__init__.py:36-40` → `ICON_TYPE_ALIASES = {'inet': 'cloud', 'wan': 'cloud', 'internet': 'cloud'}`, aplicado en icons/__init__.py:392-399. Test: `tests/test_icon_aliases.py`. (El resto de la tabla §7 sí coincide con los módulos reales de `AlmaGag/draw/icons/`: building, cloud, computer, database, decision, diamond, document, firewall, laptop, router, server, user + bwt como fallback.)

## 13. `semantic_type` admite clases custom y genera leyenda §N48; sólo las 7 canónicas colorean solas — FALTA DOCUMENTAR

- **Spec, líneas 341-355:** presenta una tabla cerrada de 7 tipos, con el título *"Asigna color a la linea segun el tipo de relacion"*.
- **Código:** `/home/user/AlmaGag/AlmaGag/draw/primitives/svg.py:230` → `unknown = sorted(t for t in by_type if t not in SEMANTIC_CONNECTION_COLORS)` — los nombres arbitrarios se aceptan y entran a la leyenda; `semantics.py:64` inyecta nombres libres (p.ej. `"transporte"`). Dos consecuencias no documentadas:
  - `svg.py:260-264` (`resolve_connection_color`): un `semantic_type` fuera de las 7 devuelve `None` → la línea sale negra salvo que se declare `color` (o token de `theme`).
  - `svg.py:210-211`: la leyenda al pie sólo se dibuja con **≥3** `semantic_type` distintos; con menos es no-op silencioso. Test: `tests/test_connection_legend.py`.

## 14. El default de `type` en CONTENEDORES es `building` y el fallback es un rectángulo, no una banana — DOC MIENTE

- **Spec, línea 292:** `` | `type` | string | no | `"unknown"` (banana) | ... Si pones un tipo que no existe, se dibuja una banana con cinta. ``
- **Código:** `/home/user/AlmaGag/AlmaGag/draw/primitives/container.py:219` → `icon_type = container.get('type', 'building')`; y container.py:240-247 el `except (ImportError, AttributeError)` dibuja un **rect simple con gradiente**, nunca el BWT. La regla "tipo desconocido = banana" sólo vale para elementos no-contenedor (icons/__init__.py:398-420).

## 15. `role: "actor"` está documentado pero no lo implementa ningún template — DOC MIENTE

- **Spec, línea 116:** `` | `actor` | Actor de secuencia | sequence | ``
- **Código:** `AlmaGag/layout/templates/sequence.py` no lee `role` en ninguna línea (grep sobre `templates/`: sólo `architecture.py:60-67` usa entry/output/terminal/abstract, `architecture.py:18` shared, `hub_and_spoke.py:68-70,103` hub/spoke, `state.py:63-64` state). `actor` es inerte.

## 16. `connections` (y `elements`) no son obligatorios — DOC MIENTE

- **Spec, líneas 266 y 310:** *"## 2. elements (obligatorio)"* / *"## 3. connections (obligatorio)"*.
- **Código:** `generator.py:207-208` → `all_elements = data.get('elements', [])` / `all_connections = data.get('connections', [])`. No hay validación previa; un archivo sólo con `elements` renderiza sin error (`generate_diagram` retorna True).

## 17. Con IDs duplicados se dibujan AMBOS, no "solo uno" — DOC MIENTE

- **Spec, línea 662:** *"**Problema:** Dos elementos con el mismo `id`. Solo uno se dibuja."*
- **Código:** `/home/user/AlmaGag/AlmaGag/layout/layout.py:68` → `elements_by_id = {e['id']: e for e in self.elements}` (gana el último, sólo para lookups de conexión), pero el renderer itera la **lista**: `/home/user/AlmaGag/AlmaGag/layout/strategies/auto/auto_renderer.py:239-240` `for elem in normal_elements: ... _draw_icon_shape(...)`. Se dibujan los dos, superpuestos; lo que se pierde es el ruteo del primero, no su dibujo.

## 18. `waypoints` y `routing_type` a nivel raíz de la conexión (compat v1.5) no documentados — FALTA DOCUMENTAR

- **Spec, línea 459:** sólo documenta `waypoints` **dentro** de `routing: {"type": "manual", ...}`.
- **Código:** `/home/user/AlmaGag/AlmaGag/routing/router_manager.py:135-147`: `routing_type` en la raíz se traduce a `{'type': ...}`, y `waypoints` en la raíz se convierte automáticamente a routing manual. Son entradas válidas que la spec declara inexistentes.

## 19. Flags CLI: la spec documenta 3 de 13 — FALTA DOCUMENTAR

- **Spec:** sólo menciona `--view` (línea 165), `--color-connections` (línea 361) y `--layout-algorithm=hier` (línea 155).
- **Código, `/home/user/AlmaGag/AlmaGag/main.py:28-127`:** no documentados `--debug`, `--visualdebug`, `--exportpng` (:42-46), `--guide-lines`, `--dump-iterations`, `-o/--output`, `--epifania` / `--debug-phases` / `--visualize-growth` (:86-94) y `--centrality-{alpha,beta,gamma,max-score}`.
- Además la spec presenta `--layout-algorithm=hier` como el modo normal de activar `areas`, cuando el default real es `select` (main.py:66-74) con auto-selección; **no** hay marca de obsolescencia del flag en el código (grep `obsolet|deprecat` en `AlmaGag/` sólo da un comentario no relacionado en `auto/optimizer.py:501`), así que la spec no miente por omisión de deprecación — miente por presentarlo como requisito.

## 20. La extensión y la posición de `icons` son irrelevantes para el motor — DOC MIENTE (menor)

- **Spec, líneas 13-16:** *"La unica diferencia es que `.gag` tiene la key `"icons"` **al inicio**"*, y la tabla asocia cada extensión a un contenido.
- **Código:** `generator.py:110-115` hace `json.load` sobre cualquier ruta sin mirar la extensión, y `generator.py:171` lee `data.get('icons')` sin importar su posición en el objeto. Un `.sdjf` con `icons` funciona idéntico.

---

### Nota sobre los ejemplos JSON de la spec
Ninguno de los ejemplos (líneas 22-32, 272-285, 316-326, 475-505, 559-577, 712-806) sería **rechazado** por el código actual: todos los campos usados existen y se parsean. Las dos desviaciones de interpretación reales son las del punto 4 y 5 — los ejemplos con `routing: {"type": "orthogonal"}` sin `corner_radius`/`preference` (líneas 574, 739-740, 783) se renderizan con esquinas redondeadas de 25px y salida por el eje dominante, no con esquinas cuadradas y salida horizontal como la spec promete.
