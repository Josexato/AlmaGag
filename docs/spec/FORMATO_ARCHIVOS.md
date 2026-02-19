# Formato de Archivos AlmaGag (.sdjf y .gag)

> **Este documento es la referencia definitiva.** Si algo no esta aqui, no existe en el formato.

---

## Que es esto

AlmaGag lee un archivo JSON y genera un diagrama SVG. Ese archivo JSON puede tener dos extensiones:

| Extension | Que contiene | Cuando usarla |
|-----------|-------------|---------------|
| `.sdjf` | JSON puro con elementos y conexiones | Siempre que uses iconos ya incluidos en AlmaGag |
| `.gag` | Mismo JSON pero con una seccion extra `"icons"` donde defines iconos SVG custom | Cuando necesitas iconos que AlmaGag no trae |

**Ambos son JSON valido.** La unica diferencia es que `.gag` tiene la key `"icons"` al inicio.

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

## 1. canvas (opcional)

Define el tamano del area de dibujo en pixeles. Si lo omites, AlmaGag usa 1400x900 y lo expande si hace falta.

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

**Nota:** Si tus elementos no caben, AlmaGag agranda el canvas automaticamente.

---

## 2. elements (obligatorio)

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
| `type` | string | no | `"unknown"` (banana) | Tipo de icono a dibujar. Ver seccion "Tipos de iconos" mas abajo. Si pones un tipo que no existe, se dibuja una banana con cinta. |
| `label` | string | no | sin texto | Texto que aparece junto al icono. Usa `\n` para salto de linea. Ejemplo: `"Linea 1\nLinea 2"` |
| `color` | string | no | `"gray"` | Color del icono. Acepta nombres CSS (`"gold"`, `"tomato"`) o hexadecimal (`"#3498DB"`). Ver seccion "Colores" mas abajo. |
| `x` | numero | no | automatico | Posicion horizontal en pixeles. **Si lo omites, AlmaGag calcula la posicion automaticamente.** |
| `y` | numero | no | automatico | Posicion vertical en pixeles. **Si lo omites, AlmaGag calcula la posicion automaticamente.** |
| `hp` | numero | no | `1.0` | Multiplicador de altura. El icono base mide 50px de alto. Con `hp: 2.0` medira 100px. |
| `wp` | numero | no | `1.0` | Multiplicador de ancho. El icono base mide 80px de ancho. Con `wp: 1.5` medira 120px. |
| `label_priority` | string | no | automatico | Prioridad del label: `"high"`, `"normal"`, `"low"`. Afecta donde se coloca el elemento en auto-layout: high = centro, low = periferia. |
| `label_position` | string | no | automatico | Donde poner el texto: `"bottom"`, `"top"`, `"left"`, `"right"`. Si lo omites, AlmaGag elige la posicion que no tape otros elementos. |

### Reglas importantes

- **`id` debe ser unico.** Si dos elementos tienen el mismo `id`, el diagrama se rompe.
- **`x` e `y` son opcionales.** Si los omites en TODOS los elementos, AlmaGag organiza el diagrama solo. Si los pones en algunos si y otros no, AlmaGag respeta los que tienen coordenadas y calcula el resto.
- **`hp` y `wp` no aplican a contenedores** (elementos con `contains`). Los contenedores calculan su tamano segun lo que contienen.

---

## 3. connections (obligatorio)

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
| `corner_radius` | numero | 0 | Radio de las esquinas en pixeles. 0 = esquinas cuadradas. |
| `preference` | string | `"horizontal"` | `"horizontal"` = sale horizontal primero. `"vertical"` = sale vertical primero. |

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

---

## 6. Formato .gag (iconos SVG embebidos)

Si necesitas un tipo de icono que AlmaGag no trae, puedes definirlo inline con SVG.

### Ejemplo completo

```json
{
  "icons": {
    "sensor": "<svg viewBox='0 0 80 50'><rect x='10' y='5' width='60' height='40' rx='8' fill='currentColor' stroke='black' stroke-width='2'/><circle cx='30' cy='25' r='6' fill='white'/><circle cx='50' cy='25' r='6' fill='white'/></svg>",
    "antena": "<svg viewBox='0 0 80 50'><line x1='40' y1='5' x2='40' y2='35' stroke='black' stroke-width='3'/><circle cx='40' cy='5' r='4' fill='red'/><rect x='20' y='35' width='40' height='12' rx='3' fill='currentColor' stroke='black'/></svg>"
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
| **currentColor** | Usa `fill='currentColor'` en tu SVG. AlmaGag lo reemplaza con el `color` del elemento. |
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

**Si pones un tipo que no existe** (ej: `"type": "xyz"`), AlmaGag dibuja una banana con cinta (BWT) como indicador de tipo no reconocido.

---

## 8. Colores validos

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
**Problema:** Dos elementos con el mismo `id`. Solo uno se dibuja.
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
    "sensor": "<svg viewBox='0 0 80 50'><rect x='10' y='5' width='60' height='40' rx='8' fill='currentColor' stroke='black' stroke-width='2'/><circle cx='30' cy='25' r='6' fill='white'/><circle cx='50' cy='25' r='6' fill='white'/></svg>"
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
  +-- "elements" (obligatorio): [
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
  +-- "connections" (obligatorio): [
        {
          "from": OBLIGATORIO (id origen),
          "to": OBLIGATORIO (id destino),
          "label": texto,
          "direction": forward|backward|bidirectional|none,
          "routing": { "type": straight|orthogonal|bezier|arc|manual, ... }
        }
      ]
```
