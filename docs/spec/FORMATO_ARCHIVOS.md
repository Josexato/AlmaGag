# Formato de Archivos AlmaGag (.sdjf y .gag)

> **Este documento es la referencia definitiva.** Si algo no esta aqui, no existe en el formato.

---

## Que es esto

AlmaGag lee un archivo JSON y genera un diagrama SVG. Ese archivo JSON puede tener dos extensiones:

| Extension | Que contiene | Cuando usarla |
|-----------|-------------|---------------|
| `.sdjf` | JSON puro con elementos y conexiones | Siempre que uses iconos ya incluidos en AlmaGag |
| `.gag` | Mismo JSON pero con una seccion extra `"icons"` donde defines iconos SVG custom | Cuando necesitas iconos que AlmaGag no trae |

**Ambos son JSON valido y el motor los trata IGUAL** (no mira la extension
ni la posicion de las keys): la convencion es usar `.gag` cuando el archivo
embebe iconos custom en `"icons"`, y `.sdjf` cuando no.

---

## Estructura minima (el archivo mas simple que funciona)

```json
{
  "elements": [
    { "id": "a", "type": "server", "label": "Mi Servidor" },
    { "id": "b", "type": "database", "label": "Base de Datos" }
  ],
  "connections": [
    { "from": "a", "to": "b" }
  ]
}
```

Eso es todo. Guardalo como `ejemplo.sdjf`, ejecuta `almagag ejemplo.sdjf` y obtienes un SVG con dos iconos conectados. AlmaGag calcula las posiciones automaticamente.

---

## Las 3 secciones del JSON

Todo archivo `.sdjf` o `.gag` tiene estas secciones:

```json
{
  "canvas": { ... },
  "elements": [ ... ],
  "connections": [ ... ]
}
```

Y opcionalmente (solo `.gag`):

```json
{
  "icons": { ... },
  "canvas": { ... },
  "elements": [ ... ],
  "connections": [ ... ]
}
```

Vamos seccion por seccion.

---

## 0. layout_template (opcional) — Auto-distribución por patrón

**WISH-LAYOUT-004** (2026-06-19, 4 fases): activa un template que asigna coordenadas automaticamente segun la estructura del grafo + hints semanticos. Util cuando no queres escribir `x`/`y` a mano para cada elemento.

Tres modos:

```json
{ "layout_template": "auto", ... }            // auto-detecta el patrón
{ "layout_template": "architecture", ... }    // override manual
// sin "layout_template"                       // fallback a AUTO/LAF
```

Templates disponibles:

| Nombre | Patron | Cuando usarlo |
|---|---|---|
| `"architecture"` | T vertical con shared al centro | Diagramas arquitectonicos con containers y un nodo "compartido" |
| `"steps"` | Cadena vertical centrada | Pipelines, secuencias de pasos (hasta v3.8: `"flow"`) |
| `"hub_and_spoke"` | Hub central + spokes radiales (círculo) | SD-WAN, redes, federacion |
| `"dashboard"` | Grid de containers paralelos | Posters, paneles independientes |
| `"er"` | Radial-concéntrico | Entidades con relaciones (DBs/tablas) |
| `"sequence"` | Swimlanes verticales + mensajes | Diagramas de secuencia UML |
| `"state"` | Estados en círculo | Máquinas de estado con ciclos |

Reglas comunes:
- **No sobreescriben coords manuales**. Si un elemento ya tiene `x`/`y`, el template los respeta.
- El template ajusta el `canvas` automaticamente.
- Es **opcional** — sin declaración, comportamiento actual.

### 0.1. Semantic hints — `role` por elemento (Fase 4)

Cada elemento puede declarar su rol semantico para guiar al clasificador y al template:

```json
{
  "id": "user_input", "label": "Input",
  "role": "entry"
}
```

Valores reconocidos:

| `role` | Significado | Usado por |
|---|---|---|
| `entry` | Punto de entrada (raíz) | architecture |
| `output`, `terminal` | Punto de salida (hoja) | architecture |
| `shared` | Container compartido | architecture |
| `hub` | Nodo central | hub_and_spoke |
| `spoke` | Satelite | hub_and_spoke |
| `abstract` | Clase base abstracta | architecture |
| `state` | Estado de máquina | state |
| `actor` | (reservado — hoy NINGUN template lo lee; declararlo no hace nada) | — |

Los `role` sobreescriben la heuristica por label/topologia. Si no los declaras, la heuristica decide.

### 0.2. Templates anidados — `layout_template` por container (Fase 4)

Un container puede declarar SU PROPIO template, que se aplica a sus hijos antes que el template padre:

```json
{
  "layout_template": "architecture",
  "elements": [
    {
      "id": "main_app",
      "contains": ["s1", "s2", "s3", "s4"],
      "layout_template": "steps"  // estos 4 hijos van en cadena vertical
    },
    {
      "id": "shared_box",
      "contains": ["db", "cache", "queue", "log"],
      "layout_template": "hub_and_spoke",  // estos 4 van radial
      "role": "shared"
    }
  ]
}
```

Procesamiento:
- **Bottom-up**: los containers más anidados se aplican primero.
- El sub-template ve solo los hijos del container + conexiones internas.
- El container queda dimensionado por el bbox de su sub-grafo (`_inner_width`/`_inner_height`).
- El padre adapta su layout a las dimensiones resultantes (politica: el hijo siempre infla).

Ver `tests/test_template_fase4.py` y `AlmaGag/layout/templates/` para detalles.

---

## 0.3. Vistas del algoritmo `hier` — `layout_view`, `areas`, `lanes`, `roles` (§I)

Declarar `areas` ya enruta el archivo a `hier` automaticamente (el default
`select` decide; no hace falta ningun flag). Y si otra señal fuerza `auto`
(p.ej. `considerations`, con WARNING §O53), las areas no se pierden: se
siembran como zonas punteadas §N46 (`areas_to_near_seeds`). Separan **el dato** (qué fase / quién es
responsable de cada nodo) de **la vista** (cómo se agrupa visualmente). Un SDJF
sin estos campos se comporta igual que hoy.

**Principio:** el JSON describe *qué es* (contenido, incluida la metadata
semántica `areas`/`roles`); el algoritmo decide *cómo se ve*. La representación
**sólo se fuerza por parámetro de comando** (`--view`), **nunca por un campo del
archivo** — no hay `layout_view` en el JSON.

```
--view {auto|columns|areas|lanes|matrix}  # override, sólo por CLI
# (default: auto → el algoritmo elige a partir del JSON: areas si las declara)
```

| Vista | Qué hace | Criterio |
|-------|----------|----------|
| `columns` | columnas del grafo dirigido (una tira/mariposa; hasta v3.8: `flow`) | A–H |
| `areas` | una caja por fase, sub-layout A–H interno, a lo ancho | §I27 |
| `lanes` | un carril vertical por rol, flujo en Y | §I28 |
| `matrix` | grilla fase (columna) × rol (fila); flowchart transfuncional | §I |

**`areas`** (top-level) — ámbitos por fase (§I27):
```json
"areas": [
  { "id": "F1", "label": "1 · Contratación", "color": "#2a6fdb",
    "members": ["inicio", "obtiene", "crea_sga"] }
]
```
Cada área corre A–H sobre sus miembros y se dibuja como caja punteada rotulada;
las conexiones inter-área cruzan por el borde (§I29). Un nodo puede no pertenecer
a ningún área.

**`lanes`** (top-level, opcional) — carriles por responsable (§I28):
```json
"lanes": [ { "id": "com", "label": "Consultor Comercial", "members": ["obtiene"] } ]
```
Si NO declaras `lanes`, la vista `lanes` los deriva del campo `role` de cada nodo
(un carril por rol distinto). Todo nodo cae en exactamente un carril.

**`role` + `roles`** — responsable por nodo (§I30). Cada elemento puede llevar
`"role": "com"`; el mapa top-level `roles` da etiqueta y color de la leyenda:
```json
"roles": { "com": { "label": "Consultor Comercial", "color": "#2a6fdb" } }
```
En vista `areas` el rol se muestra como franja de color + leyenda; en vista
`lanes` es el propio carril. (Nota: este `role` de responsable es distinto del
`role` semántico de templates §0.1 — aquél usa palabras clave como `entry`/`hub`;
éste es una clave libre de agrupación.)

Ver `AlmaGag/layout/strategies/hier/areas.py`, `lanes.py` y `tests/test_hier_areas.py`,
`test_hier_lanes.py`.

---

## 0.4. Consideraciones — `considerations` (align / near / avoid)

Array top-level opcional para expresar **intención** de layout: alinear, acercar
o separar elementos. Son **blandas** (por eso "consideraciones", no
"restricciones"): cada una se aplica **sólo si no rompe la diagramación**. Si
cumplirla aumentaría las colisiones, **cede** y se informa en el log
(`[CONSIDERACIONES] no se pudo cumplir: ...`) sin explicar el porqué. Así una
consideración nunca degrada el diagrama. Las aplica el motor **AUTO** (declararlas
enruta el diagrama a AUTO). Si no las declaras, no cambia nada.

```json
"considerations": [
  { "align": ["web1", "web2", "web3"], "axis": "y" },
  { "align": ["db", "cache"], "axis": "x" },
  { "near":  ["api", "db"] },
  { "avoid": ["frontend", "backend"] }
]
```

| Consideración | Efecto | `axis` |
|---|---|---|
| `align` | Lleva los elementos a una coordenada común (la media del grupo) | `"x"` (misma columna, default) o `"y"` (misma fila) |
| `near`  | ZONA por construccion (§N46): los miembros se clusterizan en grilla compacta ANTES del ruteo, con caja punteada; acepta `"label"` opcional para rotular la zona. **Si TODOS los ids son areas top-level** → afinidad entre zonas (§Q65): bloque adyacente en su fila | — |
| `avoid` | Si dos elementos se solapan, los separa por el eje de menor penetración | — |

- Cada consideración necesita **≥2 ids**; las entradas inválidas se descartan con
  un warning (no rompen el render).
- `align`/`avoid` son best-effort y **guardadas** (se conservan solo si no
  suben las colisiones). `near` es DURA desde §N46: se cumple por
  construccion como zona (con expulsion de intrusos). Combínalas: `align`
  para formar una columna, `avoid`
  para que dos cajas no se pisen.
- **`align` entre rangos topológicos distintos es CONTRATO duro** (no
  best-effort): eje `x` = columna (V79: el tronco `dppto/ppto/constr` en
  una vertical); eje `y` = FILA por promoción de rango (WISH-LAYOUT-017:
  la «capa de resúmenes» — cabezales de cadenas de profundidad desigual
  comparten altura; cada miembro sube al rango común factible, con sus
  predecesores por debajo y sucesores por arriba). Si el contrato es
  infactible (un miembro alimenta a otro del grupo; sin hueco en la
  fila), no se fuerza y el **audit lo nombra** — nunca silencio.
- Alias retrocompatible: también se acepta la clave `constraints`.

Ver `AlmaGag/layout/considerations.py`,
`docs/diagrams/gags/considerations-demo.sdjf` y `tests/test_considerations.py`.

---


## Consistencia del termino «flow» (v3.9)

Decision del autor (11-ago-2026): **una palabra = un concepto**. «flow»
quedo reservado para UN solo significado — `canvas.flow`, la direccion de
lectura del grafo dirigido (el unico uso literal de «flujo»). Todo lo
demas se renombro; el nombre viejo NO se acepta (el motor corta con
error/warning que nombra el reemplazo):

| Hasta v3.8 | Desde v3.9 | Concepto |
|---|---|---|
| `flows` (top-level) | `journeys` | Recorrido narrativo resaltado (highlighter) |
| `canvas.flow` | `canvas.flow` (queda) | Direccion de lectura del grafo (up/down) |
| `layout_template: "flow"` | `"steps"` | Cadena vertical de pasos |
| `--view flow` | `--view columns` | Vista plana de hier (columnas, sin agrupar) |
| `data_flow` / `control_flow` | `data_link` / `control_link` | Que viaja por el enlace |

## 1. canvas (opcional)

Define el tamano del area de dibujo en pixeles. Si lo omites, AlmaGag usa 1400x900 y lo expande si hace falta. Si declaras `layout_template`, el template lo calcula automaticamente.

```json
"canvas": {
  "width": 1200,
  "height": 800
}
```

| Campo | Tipo | Default | Que hace |
|-------|------|---------|----------|
| `width` | numero | 1400 | Ancho del SVG en pixeles |
| `height` | numero | 900 | Alto del SVG en pixeles |
| `flow` | string | `"down"` | Orientacion de LECTURA del grafo dirigido (V78). `"down"`: fuentes arriba, sumidero abajo (historico). `"up"`: rangos invertidos — fuentes como cimiento en la banda inferior y el consolidado arriba; es la orientacion natural de los roll-ups/agregaciones («de los recursos al consolidado»). `"left"`/`"right"`: reservados — hoy avisan con WARNING y emiten como `down`. |
| `legend` | array | — | Leyenda LIBRE al pie (V82), apilada con las otras franjas («Enlaces:», «Flujos:»). Entradas: string (solo texto) o `{"label": "...", "color": "#hex"}` (swatch redondo del color + texto). Reemplaza el viejo hack del flow blanco con path degenerado, que hoy es error U74/U77. |

**Nota:** Si tus elementos no caben, AlmaGag agranda el canvas automaticamente.

---

## 2. elements

Es un array de objetos. Cada objeto es un nodo/icono del diagrama.

### Ejemplo con todos los campos

```json
{
  "id": "api",
  "type": "server",
  "label": "REST API\nv2.0",
  "color": "gold",
  "x": 500,
  "y": 100,
  "hp": 1.5,
  "wp": 1.2,
  "label_priority": "high",
  "label_position": "bottom"
}
```

### Tabla de campos

| Campo | Tipo | Obligatorio | Default | Que hace |
|-------|------|:-----------:|---------|----------|
| `id` | string | **SI** | — | Identificador unico. Debe ser unico en todo el archivo. Se usa en `connections` para referenciar este elemento. |
| `type` | string | no | `"unknown"` (banana) | Tipo de icono. Ver "Tipos de iconos". Un tipo inexistente dibuja la banana con cinta ROTULADA con el nombre (§Q64) + WARNING. **Excepcion**: en un elemento con `contains` (contenedor) el default es `building` y un tipo desconocido cae a un rectangulo simple, no a la banana. |
| `label` | string | no | sin texto | Texto que aparece junto al icono. Usa `\n` para salto de linea. Ejemplo: `"Linea 1\nLinea 2"` |
| `color` | string | no | `"gray"` | Color del icono. Acepta nombres CSS (`"gold"`, `"tomato"`) o hexadecimal (`"#3498DB"`). Ver seccion "Colores" mas abajo. |
| `x` | numero | no | automatico | Posicion horizontal en pixeles. **Si lo omites, AlmaGag calcula la posicion automaticamente.** |
| `y` | numero | no | automatico | Posicion vertical en pixeles. **Si lo omites, AlmaGag calcula la posicion automaticamente.** |
| `hp` | numero | no | `1.0` | Multiplicador de altura. El icono base mide 50px de alto. Con `hp: 2.0` medira 100px. |
| `wp` | numero | no | `1.0` | Multiplicador de ancho. El icono base mide 80px de ancho. Con `wp: 1.5` medira 120px. |
| `label_priority` | string | no | automatico | Prioridad del label: `"high"`, `"normal"`, `"low"`. Afecta donde se coloca el elemento en auto-layout: high = centro, low = periferia. |
| `label_position` | string | no | automatico | Donde poner el texto: `"bottom"`, `"top"`, `"left"`, `"right"`. Si lo omites, AlmaGag elige la posicion que no tape otros elementos. |
| `width` / `height` | numero | no | por `hp`/`wp` | Tamano EXPLICITO en px. Si estan ambos, **ganan** sobre `hp`/`wp`. |
| `callout` | booleano | no | automatico | Fuerza (`true`) o desactiva (`false`) el render como callout (caja de texto aparte con linea guia). Sin declarar, se auto-activa con labels de ≥6 lineas o ≥150 caracteres. |
| `status` | string | no | — | Estado del elemento (V82): `"ok"` (◉ verde), `"partial"` (◪ ambar), `"empty"` (▢ gris). El badge se antepone a la ULTIMA linea del label y esa linea toma el color — no pintes el glifo a mano. Combina con `canvas.legend` para explicar los estados al pie. |

### Reglas importantes

- **`id` debe ser unico.** Si dos elementos tienen el mismo `id`, el diagrama se rompe.
- **`x` e `y` son opcionales.** Si los omites en TODOS los elementos, AlmaGag organiza el diagrama solo. Si los pones en algunos si y otros no, AlmaGag respeta los que tienen coordenadas y calcula el resto.
- **`hp` y `wp` no aplican a contenedores** (elementos con `contains`). Los contenedores calculan su tamano segun lo que contienen.

---

## 3. connections (opcional — un archivo solo con elements renderiza)

Es un array de objetos. Cada objeto es una linea que conecta dos elementos.

### Ejemplo con todos los campos

```json
{
  "from": "api",
  "to": "db",
  "label": "SQL queries",
  "direction": "forward",
  "routing": {
    "type": "orthogonal"
  }
}
```

### Tabla de campos

| Campo | Tipo | Obligatorio | Default | Que hace |
|-------|------|:-----------:|---------|----------|
| `from` | string | **SI** | — | `id` del elemento de origen. Debe existir en `elements`. |
| `to` | string | **SI** | — | `id` del elemento de destino. Debe existir en `elements`. Puede ser igual a `from` para crear un self-loop. |
| `label` | string | no | sin texto | Texto que aparece sobre la linea. |
| `direction` | string | no | `"none"` | Tipo de flecha. Ver tabla abajo. |
| `routing` | objeto | no | linea recta | Como se dibuja la linea. Ver seccion "Routing" mas abajo. |
| `semantic_type` | string | no | — | Tipo semantico → color automatico. Ver tabla abajo. |
| `color` | string | no | negro | Color directo (hex o nombre CSS). Tiene precedencia sobre `semantic_type`. |
| `style` | string | no | `"solid"` | Estilo de trazo: `"solid"` (default), `"dashed"` (punteado largo) o `"dotted"` (punteado corto). Útil para enlaces de respaldo/secundarios en topologías de red. Alias: `line_style`. |

### Color por tipo semantico (`semantic_type`)

Asigna color a la linea segun el tipo de relacion, sin tener que elegir el
color a mano. `connection.color` lo sobreescribe si quieres un color exacto.

| `semantic_type` | Color | Uso tipico |
|-----------------|-------|-----------|
| `data_link` | naranja | Datos por el enlace (hasta v3.8: `data_flow`) |
| `control_link` | azul | Control por el enlace (hasta v3.8: `control_flow`) |
| `sync` | verde | Sincronizacion / bidireccional |
| `event` | purpura | Eventos / mensajes |
| `callback` | teal | Callbacks |
| `dependency` | gris | Dependencias |
| `error` | rojo | Caminos de error |

```json
{ "from": "api", "to": "db", "direction": "bidirectional", "semantic_type": "sync" }
{ "from": "b", "to": "c", "direction": "forward", "color": "#ff8800" }
```

Funciona sin el flag `--color-connections` (ese flag colorea cada conexion con

**Clases CUSTOM (§Q63)**: cualquier nombre de clase vale (`backhaul`,
`energia`, `soporte`…). Las custom no traen color de fabrica — darles color
con tokens del `theme` en el campo `color` de la conexion. Con **≥3 clases
distintas** aparece automaticamente la leyenda «Enlaces:» al pie (§N48);
las clases custom se listan con su nombre tal cual. Con menos de 3, no hay
leyenda.

**Seccion `semantics` embebida (§Q63, opcional, top-level)** — el archivo
puede traer su propio mapa texto→clase, como los iconos embebidos:

```json
"semantics": {
  "transporte": {"keywords": ["FO", "MW", "Mbps"], "color": "#1f6fd0"},
  "soporte":    ["soporte", "reposicion", "FAT"]
}
```

El motor lo aplica MECANICAMENTE a conexiones SIN `semantic_type`:
subcadena case-insensitive contra el label, la primera clase del archivo
que matchea gana, `color` opcional (respeta uno ya presente; puede ser
token del theme), WARNING `§Q63 [semantic] … inferido` — nunca en
silencio; sin match → clase neutra; lo declarado jamas se pisa. **El
vocabulario viaja en el archivo, nunca en el codigo del motor.**
un color unico arcoiris; `semantic_type` agrupa por significado). Ver canonical
`docs/diagrams/gags/17-semantic-connections.gag`.

### Valores de `direction`

| Valor | Que dibuja |
|-------|-----------|
| `"forward"` | Circulo en origen, flecha en destino (A o-->  B) |
| `"backward"` | Flecha en origen, circulo en destino (A  <--o B) |
| `"bidirectional"` | Flechas en ambos extremos (A <--> B) |
| `"none"` | Linea sin flechas (A --- B) |

---

## 4. routing (opcional, dentro de una conexion)

Controla la forma de la linea. Si no lo pones, la linea es recta.

### Tipo: straight (default)

Linea recta de A a B. No necesitas poner nada.

```json
{ "from": "a", "to": "b" }
```

### Tipo: orthogonal

Linea con angulos rectos (horizontal-vertical). Ideal para diagramas de arquitectura.

```json
{
  "from": "a",
  "to": "b",
  "routing": {
    "type": "orthogonal",
    "corner_radius": 10,
    "preference": "horizontal"
  }
}
```

| Campo | Tipo | Default | Que hace |
|-------|------|---------|----------|
| `corner_radius` | numero | **25** (`CORNER_RADIUS_DEFAULT`) | Radio de las esquinas en pixeles. Poner `0` explicito para esquinas cuadradas. |
| `preference` | string | `"auto"` | `"auto"` = sale por el eje dominante (horizontal si |dx|>|dy|). `"horizontal"`/`"vertical"` lo fuerzan. |

### Tipo: bezier

Curva suave. Ideal para flujos.

```json
{
  "from": "a",
  "to": "b",
  "routing": {
    "type": "bezier",
    "curvature": 0.5
  }
}
```

| Campo | Tipo | Default | Que hace |
|-------|------|---------|----------|
| `curvature` | numero | 0.5 | Cuanto se curva la linea. 0.0 = casi recta. 1.0 = muy curva. |

### Tipo: arc

Arco circular. Se usa para self-loops (conexion de un elemento a si mismo).

```json
{
  "from": "a",
  "to": "a",
  "routing": {
    "type": "arc",
    "radius": 50,
    "side": "top"
  }
}
```

| Campo | Tipo | Default | Que hace |
|-------|------|---------|----------|
| `radius` | numero | 50 | Radio del arco en pixeles. |
| `side` | string | `"top"` | Por donde sale el arco: `"top"`, `"bottom"`, `"left"`, `"right"`. |

### Tipo: manual

Puntos intermedios explicitos. Tu defines por donde pasa la linea.

```json
{
  "from": "a",
  "to": "b",
  "routing": {
    "type": "manual",
    "waypoints": [
      { "x": 300, "y": 200 },
      { "x": 500, "y": 200 }
    ]
  }
}
```

---

## 5. Contenedores (agrupacion visual)

Un contenedor es un elemento normal que tiene el campo `contains`. Dibuja un rectangulo alrededor de sus hijos.

**Compatibilidad v1.5**: `waypoints` y `routing_type` tambien se aceptan en
la RAIZ de la conexion (sin envolver en `routing`): `waypoints` sueltos se
convierten automaticamente a routing manual, y `routing_type: "X"` equivale
a `routing: {"type": "X"}`.

### Zonas fisicas anidadas (§P59/§P60/§Q65)

Con `type: "area"` + `contains` anidado y SIN coordenadas del autor, el
motor AUTO aplica un macro-layout de zonas:

- **§P59 — contencion real**: la celda de la grilla usa el tamano REAL de
  cada hijo (un edificio ya resuelto no aplasta a sus hermanos); recursivo
  a cualquier profundidad; las cajas son super-nodos rigidos.
- **§P60 — banda/periferia**: las zonas con enlaces inter-zona de
  TRANSPORTE (`direction: "bidirectional"`/`"none"`) van adyacentes a la
  banda principal; las de solo enlaces administrativos (dirigidos) bajan a
  la fila periferica. Los enlaces inter-zona viajan por TRONCALES
  ortogonales (una espina compartida por par de zonas). El `direction` es
  la señal de clasificacion: declararlo bien importa.
- **§Q65 — orden**: `{"near": ["zonaA", "zonaB"]}` en `considerations` con
  ids de AREAS = bloque adyacente (afinidad declarada). Sin declarar, la
  banda se encadena por transporte y la periferia por baricentro;
  desempate por orden de aparicion. Determinista.

### Ejemplo

```json
{
  "elements": [
    {
      "id": "backend",
      "type": "building",
      "label": "Backend Services",
      "color": "lightblue",
      "contains": [
        { "id": "api" },
        { "id": "auth" }
      ]
    },
    {
      "id": "api",
      "type": "server",
      "label": "REST API",
      "color": "gold"
    },
    {
      "id": "auth",
      "type": "server",
      "label": "Auth Service",
      "color": "tomato"
    }
  ],
  "connections": [
    { "from": "api", "to": "auth", "direction": "forward" }
  ]
}
```

### Reglas de contenedores

- Los hijos (`api`, `auth`) deben existir como elementos normales en el mismo array `elements`.
- El contenedor dibuja un rectangulo que envuelve a todos sus hijos.
- El icono del contenedor aparece en la esquina superior izquierda, con su label al lado.
- **No uses `hp`/`wp` en contenedores.** Su tamano se calcula automaticamente.
- Los hijos no necesitan `x`/`y` — AlmaGag los posiciona dentro del contenedor.

### Campo `scope` en hijos (opcional)

```json
"contains": [
  { "id": "api", "scope": "full" },
  { "id": "monitor", "scope": "border" }
]
```

| Valor | Que hace |
|-------|----------|
| `"full"` | El hijo esta completamente dentro del contenedor (default). |
| `"border"` | El hijo se posiciona sobre el borde del contenedor. |

### Campo `shape: "band"` — banda de contrato (WISH-LAYOUT-005)

Un contenedor con `"shape": "band"` se dibuja como una **banda/eje horizontal**
en vez de una caja con título arriba. Sirve para expresar que N elementos son
equivalentes/intercambiables a través de un contrato comun.

```json
{
  "id": "contract", "shape": "band", "label": "Contract",
  "color": "lightblue",
  "contains": ["impl_a", "iface", "impl_b"]
}
```

Diferencias frente a un contenedor normal:
- Los hijos se colocan en **una sola fila** horizontal (no en grid).
- El título va **rotado en el borde izquierdo**, no como header arriba.
- Fondo más sutil y esquinas de barra.

Util como capa media de un diagrama en T: `[endpoint_A, abstract, endpoint_B]`.
Ver canonical `docs/diagrams/gags/16-contract-band.gag`.

---

## 5.8. `journeys` — recorridos narrativos resaltados (WISH-DRAW-002; hasta v3.8: `flows`)

Capa de ANOTACION, no de topologia: un flujo narra un recorrido sobre el
diagrama ya tendido (el camino de un paquete, un tramite, una cadena de
aprobacion) como un trazo de RESALTADOR — ancho, semitransparente, puntas
redondas — sin agregar aristas ni alterar layout ni metricas.

```json
"journeys": [
  {"id": "scada", "label": "Datos SCADA", "color": "#f7e017",
   "path": ["cpe_mina", "est2", "dc_mina", "cco"]}
]
```

| Campo | Tipo | Obligatorio | Que hace |
|-------|------|:-----------:|----------|
| `path` | array de ids | **SI** (≥2) | Recorrido EN ORDEN por elementos existentes. Entre dos consecutivos, si existe una conexion dibujada (en cualquier sentido) el trazo SIGUE su ruta real (troncales §P60 incluidas); si no, tramo directo. |
| `label` | string | no | Con ≥1 label aparece la leyenda «Flujos:» al pie. |
| `color` | string | no | hex/CSS o token §O57; sin declarar, paleta de resaltador (amarillo/verde/rosa/celeste, ciclada). |
| `id` | string | no | Para logs/WARNINGs. |

Ids inexistentes se omiten con WARNING; un flujo con <2 elementos
dibujables no se pinta. Los trazos llevan `class="ag-journey"`: invisibles
para metricas, ruteo y validador (como el halo `ag-text-halo`).

---

## 5.9. `unions` — punto de union (genealogias, §H7)

Seccion top-level opcional para "dos progenitores con hijos comunes": genera
un nodo sintetico de barra (type `union`) y aristas padre→union→hijos — un
tronco por pareja, no un enredo de aristas cruzadas.

```json
"unions": [{"id": "u1", "between": ["jose", "daria"]}]
```

Los hijos se conectan al id de la union (`{"from": "u1", "to": "hijo"}`).
Se expande ANTES de elegir estrategia; sin `unions` es no-op.

---

## 6. Formato .gag (iconos SVG embebidos)

Si necesitas un tipo de icono que AlmaGag no trae, puedes definirlo inline con SVG.

### Ejemplo completo

```json
{
  "icons": {
    "sensor": "<svg viewBox='0 0 80 50'><rect x='10' y='5' width='60' height='40' rx='8' fill='#2E75B6' stroke='black' stroke-width='2'/><circle cx='30' cy='25' r='6' fill='white'/><circle cx='50' cy='25' r='6' fill='white'/></svg>",
    "antena": "<svg viewBox='0 0 80 50'><line x1='40' y1='5' x2='40' y2='35' stroke='black' stroke-width='3'/><circle cx='40' cy='5' r='4' fill='red'/><rect x='20' y='35' width='40' height='12' rx='3' fill='#2E75B6' stroke='black'/></svg>"
  },
  "elements": [
    { "id": "s1", "type": "sensor", "label": "Temp Sensor", "color": "gold" },
    { "id": "s2", "type": "sensor", "label": "Humidity", "color": "lightgreen" },
    { "id": "a1", "type": "antena", "label": "WiFi AP", "color": "lightblue" },
    { "id": "srv", "type": "server", "label": "Servidor", "color": "silver" }
  ],
  "connections": [
    { "from": "s1", "to": "a1", "direction": "forward" },
    { "from": "s2", "to": "a1", "direction": "forward" },
    { "from": "a1", "to": "srv", "direction": "forward", "routing": {"type": "orthogonal"} }
  ]
}
```

### Como funciona

1. Defines un nombre (ej: `"sensor"`) y le asignas un string SVG.
2. Usas ese nombre como `"type"` en tus elementos.
3. AlmaGag renderiza tu SVG custom en vez de un icono built-in.

### Reglas del SVG embebido

| Regla | Detalle |
|-------|---------|
| **viewBox** | Usa `viewBox='0 0 80 50'` para que el icono escale bien al tamano base (80x50 px). |
| **currentColor** | `fill='currentColor'` en el SVG se REEMPLAZA por el `color` del elemento (default `gray`) — un solo icono sirve para todas las variantes de color (BUGS-DRAW-002, 2-ago-2026). Un icono con hex FIJOS se inserta tal cual y el `color` del elemento no lo afecta. |
| **Comillas** | El SVG va entre comillas dobles `"`. Dentro del SVG usa comillas simples `'`. |
| **Sin saltos de linea** | Todo el SVG debe ir en una sola linea (es un string JSON). |
| **Mezcla con built-in** | Puedes usar iconos custom y built-in en el mismo archivo. En el ejemplo, `"sensor"` es custom pero `"server"` es built-in. |

---

## 7. Tipos de iconos built-in

Estos tipos vienen incluidos en AlmaGag. Solo pon el nombre en `"type"`:

| Tipo | Que dibuja | Ejemplo visual |
|------|-----------|----------------|
| `server` | Servidor rack con bahias, LEDs y ventilacion | Rectangulo con 3 secciones |
| `cloud` | Nube (circulos superpuestos) | Forma de nube |
| `building` | Edificio con techo, ventanas y puerta | Casa/edificio |
| `firewall` | Muro de fuego (ladrillos + llamas) | Pared con fuego |
| `database` | Cilindro de base de datos | Cilindro con lineas |
| `router` | Router de red con antenas y puertos | Caja con antenas |
| `laptop` | Laptop con pantalla y teclado | Laptop abierta |
| `computer` | Monitor con base | Pantalla de escritorio |
| `document` | Pagina con esquina doblada | Hoja de papel |
| `user` | Silueta de persona | Cabeza + torso |
| `diamond` | Rombo (abstract/interfaz) | Diamante UML |
| `area` | ZONA fisica (contenedor §P59/§P60) | Caja de zona; ver seccion Contenedores |
| `decision` | Rombo (alias de `diamond`) | Diamante BPMN |

**Si pones un tipo que no existe** (ej: `"type": "xyz"`), AlmaGag dibuja una banana con cinta (BWT) como indicador de tipo no reconocido.

---

### Alias de iconos (§O55)

`inet`, `wan` e `internet` son ALIAS de `cloud`: dibujan la misma nube y
cuentan como hub para la deteccion de topologia §N45. Un `type` realmente
desconocido dibuja la banana con cinta (BWT) **rotulada con el nombre del
type** + WARNING §O55, y el log inventaria los BWT activos (`§Q64: N
type(s) en BWT`). Usar un type nuevo a BWT deliberado es legitimo mientras
el concepto no tiene forma — el nombre debe explicarse solo.

## 8. Colores validos

### Tokens de tema — seccion `theme` (§O57, top-level)

Ademas de nombres CSS y hex, cualquier campo `color` puede referenciar un
TOKEN declarado en la seccion `theme`:

```json
"theme": {"c-backhaul": "#1f6fd0", "acento": "#e8820c"},
"connections": [{"from": "a", "to": "b", "color": "c-backhaul"}]
```

La resolucion es un pre-proceso: un `color` cuyo valor coincida EXACTO con
una clave del theme se sustituye por su hex antes del render. Aplica a
`elements`, `connections`, `areas`, `lanes` y a los valores de `roles`. Un
hex/nombre CSS literal sigue valiendo tal cual (y gana: solo se sustituyen
coincidencias exactas).


### Nombres CSS (puedes usar directamente)

| Nombre | Color | Hex |
|--------|-------|-----|
| `red` | Rojo | #FF0000 |
| `green` | Verde | #008000 |
| `blue` | Azul | #0000FF |
| `yellow` | Amarillo | #FFFF00 |
| `orange` | Naranja | #FFA500 |
| `purple` | Morado | #800080 |
| `pink` | Rosa | #FFC0CB |
| `cyan` | Cian | #00FFFF |
| `gold` | Dorado | #FFD700 |
| `tomato` | Rojo tomate | #FF6347 |
| `lightgreen` | Verde claro | #90EE90 |
| `lightblue` | Azul claro | #ADD8E6 |
| `lightyellow` | Amarillo claro | #FFFFE0 |
| `lavender` | Lavanda | #E6E6FA |
| `gray` / `grey` | Gris | #808080 |
| `silver` | Plateado | #C0C0C0 |
| `white` | Blanco | #FFFFFF |
| `black` | Negro | #000000 |
| `lime` | Lima | #00FF00 |

### Formato hexadecimal

Tambien puedes usar cualquier color hex: `"#3498DB"`, `"#E74C3C"`, `"#2ECC71"`, etc.

---

## 9. Errores comunes

### Error 1: IDs duplicados

```json
"elements": [
  { "id": "srv", "type": "server" },
  { "id": "srv", "type": "cloud" }
]
```
**Problema:** Dos elementos con el mismo `id`. Se dibujan AMBOS
(superpuestos); las conexiones apuntan solo al ultimo — el primero queda
con lineas colgantes. No hay validacion: evitarlo.
**Solucion:** Cada `id` debe ser unico: `"srv1"`, `"srv2"`.

### Error 2: Conexion a un ID que no existe

```json
"connections": [
  { "from": "api", "to": "databse" }
]
```
**Problema:** `"databse"` es un typo, ese `id` no esta en `elements`.
**Solucion:** Verificar que todos los `from` y `to` coincidan exactamente con un `id` de `elements`.

### Error 3: Olvidar las comillas en el JSON

```json
{ id: "api", type: server }
```
**Problema:** JSON invalido. Todas las keys y valores string necesitan comillas dobles.
**Solucion:** `{ "id": "api", "type": "server" }`

### Error 4: Usar comillas dobles dentro del SVG embebido

```json
"icons": {
  "mi_icono": "<svg viewBox="0 0 80 50">...</svg>"
}
```
**Problema:** Las comillas dobles del `viewBox` rompen el string JSON.
**Solucion:** Usar comillas simples dentro del SVG: `viewBox='0 0 80 50'`

### Error 5: Poner `hp`/`wp` en un contenedor

```json
{
  "id": "grupo",
  "type": "building",
  "hp": 3.0,
  "contains": [{"id": "hijo"}]
}
```
**Problema:** `hp` se ignora en contenedores porque su tamano depende de los hijos.
**Solucion:** Quitar `hp` y `wp` de elementos que tengan `contains`.

---

## 10. Ejemplos completos

### Ejemplo basico: 3 elementos, 2 conexiones

```json
{
  "elements": [
    { "id": "web", "type": "computer", "label": "Frontend", "color": "lightblue" },
    { "id": "api", "type": "server", "label": "API", "color": "gold" },
    { "id": "db", "type": "database", "label": "PostgreSQL", "color": "orange" }
  ],
  "connections": [
    { "from": "web", "to": "api", "label": "HTTP", "direction": "forward" },
    { "from": "api", "to": "db", "label": "SQL", "direction": "forward" }
  ]
}
```

### Ejemplo intermedio: con routing y sizing

```json
{
  "canvas": { "width": 1200, "height": 800 },
  "elements": [
    { "id": "lb", "type": "cloud", "label": "Load Balancer", "color": "cyan", "hp": 1.5, "label_priority": "high" },
    { "id": "api1", "type": "server", "label": "API Node 1", "color": "gold" },
    { "id": "api2", "type": "server", "label": "API Node 2", "color": "gold" },
    { "id": "cache", "type": "database", "label": "Redis Cache", "color": "tomato" },
    { "id": "db", "type": "database", "label": "PostgreSQL", "color": "orange", "hp": 1.8 }
  ],
  "connections": [
    { "from": "lb", "to": "api1", "direction": "forward", "routing": {"type": "orthogonal"} },
    { "from": "lb", "to": "api2", "direction": "forward", "routing": {"type": "orthogonal"} },
    { "from": "api1", "to": "cache", "direction": "bidirectional", "label": "get/set", "routing": {"type": "bezier", "curvature": 0.4} },
    { "from": "api2", "to": "cache", "direction": "bidirectional", "label": "get/set", "routing": {"type": "bezier", "curvature": 0.4} },
    { "from": "api1", "to": "db", "direction": "forward", "label": "SQL" },
    { "from": "api2", "to": "db", "direction": "forward", "label": "SQL" }
  ]
}
```

### Ejemplo avanzado: con contenedores

```json
{
  "elements": [
    { "id": "user", "type": "user", "label": "Usuario", "color": "lightblue" },
    {
      "id": "backend",
      "type": "building",
      "label": "Backend",
      "color": "lavender",
      "contains": [
        { "id": "api" },
        { "id": "auth" }
      ]
    },
    { "id": "api", "type": "server", "label": "REST API", "color": "gold" },
    { "id": "auth", "type": "server", "label": "Auth Service", "color": "tomato" },
    {
      "id": "data",
      "type": "building",
      "label": "Data Layer",
      "color": "lightyellow",
      "contains": [
        { "id": "db" },
        { "id": "cache" }
      ]
    },
    { "id": "db", "type": "database", "label": "PostgreSQL", "color": "orange" },
    { "id": "cache", "type": "database", "label": "Redis", "color": "tomato" }
  ],
  "connections": [
    { "from": "user", "to": "api", "direction": "forward", "label": "HTTPS" },
    { "from": "api", "to": "auth", "direction": "forward", "label": "validate" },
    { "from": "api", "to": "db", "direction": "forward", "label": "SQL", "routing": {"type": "orthogonal"} },
    { "from": "api", "to": "cache", "direction": "bidirectional", "label": "cache", "routing": {"type": "bezier", "curvature": 0.5} }
  ]
}
```

### Ejemplo con iconos embebidos (.gag)

```json
{
  "icons": {
    "sensor": "<svg viewBox='0 0 80 50'><rect x='10' y='5' width='60' height='40' rx='8' fill='#2E75B6' stroke='black' stroke-width='2'/><circle cx='30' cy='25' r='6' fill='white'/><circle cx='50' cy='25' r='6' fill='white'/></svg>"
  },
  "elements": [
    { "id": "s1", "type": "sensor", "label": "Temp Sensor", "color": "gold" },
    { "id": "s2", "type": "sensor", "label": "Humidity", "color": "lightgreen" },
    { "id": "srv", "type": "server", "label": "Collector", "color": "silver" }
  ],
  "connections": [
    { "from": "s1", "to": "srv", "direction": "forward" },
    { "from": "s2", "to": "srv", "direction": "forward" }
  ]
}
```

---

## Resumen rapido

```
Archivo .sdjf o .gag
  |
  +-- "canvas" (opcional): { width, height }
  |
  +-- "icons" (solo .gag, opcional): { "nombre": "<svg>...</svg>" }
  |
  +-- "elements": [
  |     {
  |       "id": OBLIGATORIO,
  |       "type": icono a usar,
  |       "label": texto,
  |       "color": color,
  |       "x", "y": posicion (o auto),
  |       "hp", "wp": tamano (o 1.0),
  |       "contains": hijos (lo convierte en contenedor)
  |     }
  |   ]
  |
  +-- "connections" (opcional): [
  |     {
  |       "from": OBLIGATORIO (id origen),
  |       "to": OBLIGATORIO (id destino),
  |       "label": texto,
  |       "direction": forward|backward|bidirectional|none,
  |       "semantic_type": clase del enlace (canonica o custom),
  |       "routing": { "type": straight|orthogonal|bezier|arc|manual, ... }
  |     }
  |   ]
  |
  +-- "icons" (opcional): { "nombre": "<svg …>" }         # iconos embebidos
  +-- "theme" (opcional): { "token": "#hex" }             # §O57
  +-- "semantics" (opcional): { "clase": ["keywords"] }   # §Q63
  +-- "unions" (opcional): [ { "id", "between": [a, b] } ]  # §H7
  +-- "journeys" (opcional): [ { "path": [ids...], "label", "color" } ]  # resaltador
  +-- "considerations" (opcional): [ align | near | avoid ]
  +-- "areas" / "lanes" / "roles" (opcional)              # vistas §I
```

---

## Apendice: flags del CLI

La spec describe el ARCHIVO; el comando se documenta completo en
`docs/guides/CLI-REFERENCE.md`. Resumen real (main.py):

| Flag | Que hace |
|------|----------|
| `-o` / `--output` | Ruta del SVG de salida |
| `--view {auto\|columns\|areas\|lanes\|matrix}` | Forzar REPRESENTACION (hier) |
| `--layout-algorithm {select\|auto\|hier\|legacy}` | Forzar estrategia (debug; default `select` = el motor decide) |
| `--exportpng` | PNG ademas del SVG (§O58: Chrome→cairosvg; `ALMAGAG_CHROME`) |
| `--epifania` (alias `--debug-phases`, `--visualize-growth`) | Un SVG por fase + index.html |
| `--debug` / `--visualdebug` | Logs verbosos / overlay visual de niveles |
| `--dump-iterations` | Snapshots JSON de cada iteracion del optimizador |
| `--guide-lines N,M,…` | Lineas guia horizontales en px |
| `--color-connections` | Paleta arcoiris por conexion (sin semantica) |
| `--centrality-{alpha,beta,gamma,max-score}` | Hiperparametros del scoring de centralidad |
