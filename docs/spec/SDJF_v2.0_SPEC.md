# SDJF v2.0 - Especificación del Estándar

**Simple Diagram JSON Format v2.0**

## Introducción

SDJF v2.0 extiende v1.0 con dos características principales:
1. **Coordenadas opcionales** - Auto-layout automático cuando `x`/`y` no están presentes
2. **Sizing proporcional** - Propiedades `hp` y `wp` para escalar elementos

## Cambios Principales vs v1.0

### Coordenadas Opcionales

En v1.0, `x` e `y` eran **requeridos**. En v2.0 son **opcionales**:

```json
{
  "elements": [
    {
      "id": "server1",
      "type": "server",
      "label": "Auto-positioned"
    }
  ]
}
```

El sistema calcula automáticamente las posiciones usando un algoritmo híbrido basado en prioridades.

### Sizing Proporcional

Nuevas propiedades para controlar el tamaño de elementos:

```json
{
  "id": "big-server",
  "type": "server",
  "hp": 2.0,
  "wp": 1.5,
  "label": "Large Server"
}
```

## Propiedades de Elementos (Actualizadas)

| Propiedad | Tipo | Requerido | Default | Descripción |
|-----------|------|-----------|---------|-------------|
| `id` | string | ✅ Sí | - | Identificador único |
| `x` | integer | ⚠️ Opcional | auto | Coordenada X (si falta, auto-layout calcula) |
| `y` | integer | ⚠️ Opcional | auto | Coordenada Y (si falta, auto-layout calcula) |
| `type` | string | No | fallback | Tipo de ícono |
| `label` | string | No | - | Texto del elemento |
| `label_position` | string | No | auto | Posición del label |
| `label_priority` | string | No | auto | Prioridad manual: `high`, `normal`, `low` |
| `color` | string | No | `gray` | Color CSS o hexadecimal |
| `hp` | float | No | 1.0 | **NUEVO**: Height proportion (multiplicador de altura) |
| `wp` | float | No | 1.0 | **NUEVO**: Width proportion (multiplicador de ancho) |

## Auto-Layout

### Estrategia Híbrida

Cuando elementos no tienen coordenadas, el sistema posiciona automáticamente usando:

**1. Análisis de Prioridades**

Determina la importancia de cada elemento:

| Prioridad | Condición | Posición en Layout |
|-----------|-----------|-------------------|
| HIGH | ≥4 conexiones o `label_priority: "high"` | Centro (grid compacto) |
| NORMAL | 2-3 conexiones o `label_priority: "normal"` | Alrededor del centro (radio 300px) |
| LOW | <2 conexiones o `label_priority: "low"` | Periferia (radio 450px) |

**2. Score de Centralidad**

```
centrality_score = (3 - priority) × hp × wp
```

Elementos con mayor score se posicionan más al centro dentro de su grupo de prioridad.

**3. Algoritmo de Posicionamiento**

```
1. Agrupar elementos por prioridad (HIGH, NORMAL, LOW)
2. Ordenar cada grupo por centrality_score (descendente)
3. Posicionar HIGH en grid compacto centrado
4. Posicionar NORMAL en anillo circular (radio 300px)
5. Posicionar LOW en anillo externo (radio 450px)
```

### Coordenadas Parciales

Puedes especificar solo `x` o solo `y`:

```json
{
  "elements": [
    {
      "id": "server1",
      "y": 300,
      "label": "Fixed Y, auto X"
    },
    {
      "id": "server2",
      "x": 500,
      "label": "Fixed X, auto Y"
    }
  ]
}
```

**Comportamiento:**
- **Sin Y**: Asignado según prioridad (HIGH=top, NORMAL=middle, LOW=bottom)
- **Sin X**: Distribuido horizontalmente entre elementos del mismo nivel

## Proportional Sizing

### Propiedades hp y wp

```json
{
  "id": "element1",
  "hp": 2.0,    // Altura = ICON_HEIGHT × 2.0
  "wp": 1.5     // Ancho = ICON_WIDTH × 1.5
}
```

**Dimensiones Base:**
- `ICON_WIDTH = 80px`
- `ICON_HEIGHT = 50px`

**Cálculo Final:**
```
width = ICON_WIDTH × wp
height = ICON_HEIGHT × hp
```

### Tabla de Ejemplos

| hp | wp | Tamaño Final | Descripción |
|----|----|--------------|-|
| 1.0 | 1.0 | 80×50 | Default (sin hp/wp) |
| 2.0 | 1.0 | 80×100 | Doble altura |
| 1.0 | 1.5 | 120×50 | 1.5× más ancho |
| 2.0 | 2.0 | 160×100 | Doble en ambos |
| 0.8 | 0.8 | 64×40 | 20% más pequeño |

### Efecto en Auto-Layout

**1. Centralidad**

Elementos más grandes obtienen posiciones más centrales:
```
centrality_score = (3 - priority) × hp × wp
```

**2. Peso en Optimización**

Elementos grandes resisten movimiento durante resolución de colisiones:

```
weight = hp × wp
movement_x = original_dx / weight
movement_y = original_dy / weight
```

**Ejemplo:**
- Elemento con `hp=2.0, wp=2.0` → weight = 4.0
- Movimiento de 100px → Movimiento real = 100/4 = 25px

### Prioridad de Resolución

1. **Explícito `width`/`height`** (contenedores) → se usa tal cual
2. **`hp`/`wp` multipliers** → multiplican valores base
3. **Default** → ICON_WIDTH y ICON_HEIGHT

```json
{
  "id": "custom",
  "width": 200,
  "hp": 2.0
}
```
→ Resultado: `width=200` (explícito gana), `height=100` (50 × 2.0)

## Contenedores

**Nota Importante:** Elementos con propiedad `contains` (contenedores) **NO usan hp/wp**.

Los contenedores calculan su tamaño dinámicamente basándose en:
- Elementos contenidos dentro
- Propiedad `aspect_ratio`
- Padding interno

## Ejemplo Completo

```json
{
  "canvas": {"width": 1000, "height": 800},
  "elements": [
    {
      "id": "load-balancer",
      "type": "server",
      "hp": 2.0,
      "wp": 1.5,
      "label": "Load Balancer",
      "label_priority": "high",
      "color": "gold"
    },
    {
      "id": "app-server-1",
      "type": "server",
      "hp": 1.5,
      "label": "App Server 1",
      "color": "lightblue"
    },
    {
      "id": "app-server-2",
      "type": "server",
      "hp": 1.5,
      "label": "App Server 2",
      "color": "lightblue"
    },
    {
      "id": "database",
      "type": "building",
      "hp": 1.8,
      "wp": 1.3,
      "label": "Database",
      "label_priority": "high",
      "color": "orange"
    },
    {
      "id": "cache",
      "type": "cloud",
      "hp": 1.2,
      "label": "Cache",
      "color": "cyan"
    },
    {
      "id": "logger",
      "type": "cloud",
      "hp": 0.8,
      "wp": 0.8,
      "label": "Logger",
      "label_priority": "low",
      "color": "gray"
    }
  ],
  "connections": [
    {"from": "load-balancer", "to": "app-server-1"},
    {"from": "load-balancer", "to": "app-server-2"},
    {"from": "app-server-1", "to": "database"},
    {"from": "app-server-2", "to": "database"},
    {"from": "app-server-1", "to": "cache"},
    {"from": "app-server-1", "to": "logger"}
  ]
}
```

**Resultado esperado:**
- `load-balancer` (HIGH, grande) → Centro, difícil de mover
- `database` (HIGH, grande) → Centro, difícil de mover
- `app-server-1/2` (NORMAL, mediano) → Alrededor del centro
- `cache` (NORMAL, mediano) → Alrededor del centro
- `logger` (LOW, pequeño) → Periferia, fácil de mover

## Compatibilidad con v1.0

**SDJF v2.0 es 100% compatible hacia atrás:**

- ✅ Archivos v1.0 funcionan sin cambios
- ✅ Elementos con `x`, `y` → Posicionados exactamente donde se especifica
- ✅ Elementos sin `hp`, `wp` → Usan tamaño default (80×50)
- ✅ No se rompe funcionalidad existente

## Archivos de Ejemplo

Ver `docs/examples/`:

- **08-auto-layout.gag** - Auto-layout completo (sin coordenadas)
- **09-proportional-sizing.gag** - Varios valores de hp/wp
- **10-hybrid-layout.gag** - Combinado: auto-layout + hp/wp + prioridades

## Detalles Técnicos

### Algoritmo de Auto-Layout

```
FASE 1: Análisis
  1. Construir grafo de adyacencia
  2. Calcular prioridades (manual o automática)
  3. Identificar componentes conectados

FASE 2: Posicionamiento
  1. Agrupar por prioridad (HIGH/NORMAL/LOW)
  2. Calcular centrality_score para cada elemento
  3. Ordenar por score dentro de cada grupo
  4. Posicionar HIGH en grid compacto (centro)
  5. Posicionar NORMAL en anillo (radio 300px)
  6. Posicionar LOW en anillo externo (radio 450px)

FASE 3: Optimización
  1. Detectar colisiones (elementos, labels, conexiones)
  2. Seleccionar víctima ponderada: collisions / weight
  3. Calcular dirección de movimiento
  4. Mover víctima (escalado por 1/weight)
  5. Repetir hasta max_iterations o 0 colisiones
```

### Fórmulas

**Centrality Score:**
```
centrality_score = (3 - priority) × hp × wp

donde:
  priority ∈ {0=HIGH, 1=NORMAL, 2=LOW}
  hp, wp ∈ [0.1, 10.0]
```

**Weight (Resistencia al movimiento):**
```
weight = hp × wp

movement_actual = movement_original / weight
```

**Tamaño Final:**
```
width = ICON_WIDTH × wp    (80px × wp)
height = ICON_HEIGHT × hp  (50px × hp)
```

---

**Versión**: 2.0
**Fecha**: 2026-01-08
**Estado**: Estable
**Cambios desde v1.0**: Coordenadas opcionales + Sizing proporcional
