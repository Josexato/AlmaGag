# SDJF v1.0 - Especificación del Estándar

**Simple Diagram JSON Format v1.0**

## Introducción

SDJF (Simple Diagram JSON Format) es un formato declarativo basado en JSON para describir diagramas de nodos y conexiones. Diseñado para ser legible, mantenible y extensible.

## Estructura General

```json
{
  "canvas": {
    "width": 1400,
    "height": 900
  },
  "elements": [
    {
      "id": "srv1",
      "type": "server",
      "x": 100,
      "y": 200,
      "label": "Servidor 1\n(Producción)",
      "color": "lightblue"
    }
  ],
  "connections": [
    {
      "from": "srv1",
      "to": "fw1",
      "label": "HTTPS",
      "direction": "forward"
    }
  ]
}
```

## Sección `canvas` (opcional)

Define el tamaño del canvas SVG resultante.

**Propiedades:**

| Propiedad | Tipo | Requerido | Default | Descripción |
|-----------|------|-----------|---------|-------------|
| `width` | integer | No | 1400 | Ancho del canvas en píxeles |
| `height` | integer | No | 900 | Alto del canvas en píxeles |

**Ejemplo:**

```json
{
  "canvas": {
    "width": 1200,
    "height": 800
  }
}
```

## Sección `elements` (requerida)

Array de elementos (nodos) del diagrama.

**Propiedades de cada elemento:**

| Propiedad | Tipo | Requerido | Default | Descripción |
|-----------|------|-----------|---------|-------------|
| `id` | string | ✅ Sí | - | Identificador único del elemento |
| `x` | integer | ✅ Sí | - | Coordenada X (top-left) en píxeles |
| `y` | integer | ✅ Sí | - | Coordenada Y (top-left) en píxeles |
| `type` | string | No | fallback (BWT) | Tipo de ícono: `server`, `firewall`, `building`, `cloud` |
| `label` | string | No | - | Texto del elemento. Soporta `\n` para multilínea |
| `label_position` | string | No | auto | Posición del label: `bottom`, `top`, `left`, `right` |
| `color` | string | No | `gray` | Color CSS o hexadecimal (`lightblue`, `#3498DB`) |

**Notas:**

- Si `type` no existe o no se especifica, se dibuja el **Banana With Tape (BWT)** como fallback visual
- `label_position` en `auto` permite al sistema elegir la mejor posición evitando colisiones

**Ejemplo:**

```json
{
  "elements": [
    {
      "id": "srv1",
      "type": "server",
      "x": 100,
      "y": 200,
      "label": "API Server\n(Production)",
      "label_position": "bottom",
      "color": "lightblue"
    },
    {
      "id": "db1",
      "type": "building",
      "x": 400,
      "y": 200,
      "label": "PostgreSQL",
      "color": "#FF5733"
    }
  ]
}
```

## Sección `connections` (requerida)

Array de conexiones (aristas) entre elementos.

**Propiedades de cada conexión:**

| Propiedad | Tipo | Requerido | Default | Descripción |
|-----------|------|-----------|---------|-------------|
| `from` | string | ✅ Sí | - | ID del elemento origen |
| `to` | string | ✅ Sí | - | ID del elemento destino |
| `label` | string | No | - | Texto en el centro de la línea |
| `direction` | string | No | `none` | Dirección de flechas (ver tabla abajo) |
| `relation` | string | No | - | Tipo semántico (decorativo en v1.0) |

**Valores válidos de `direction`:**

| Valor | Símbolo | Descripción |
|-------|---------|-------------|
| `forward` | A → B | Flecha al final (destino) |
| `backward` | A ← B | Flecha al inicio (origen) |
| `bidirectional` | A ↔ B | Flechas en ambos extremos |
| `none` | A — B | Sin flechas (línea simple) |

**Ejemplo:**

```json
{
  "connections": [
    {
      "from": "srv1",
      "to": "db1",
      "label": "SQL query",
      "direction": "forward"
    },
    {
      "from": "srv1",
      "to": "cache1",
      "label": "read/write",
      "direction": "bidirectional"
    }
  ]
}
```

## Tipos de Íconos Disponibles

| Tipo | Forma | Descripción |
|------|-------|-------------|
| `server` | Rectángulo | Servidor o servicio |
| `building` | Rectángulo | Base de datos o storage |
| `cloud` | Elipse | Servicio cloud o cache |
| `firewall` | Rectángulo | Firewall o gateway |
| *desconocido* | BWT (plátano) | Fallback para tipos no registrados |

## Sistema de Colores

Soporta:
- **Nombres CSS**: `lightblue`, `orange`, `gold`, `tomato`, `cyan`, etc.
- **Hexadecimal**: `#3498DB`, `#FF5733`, etc.

Los colores generan gradientes automáticos (claro → oscuro) para mejor apariencia visual.

## Codificación

Los archivos `.gag` deben estar codificados en **UTF-8 sin BOM**.

## Ejemplo Completo

```json
{
  "canvas": {"width": 1000, "height": 600},
  "elements": [
    {
      "id": "api",
      "type": "server",
      "x": 200,
      "y": 250,
      "label": "REST API",
      "color": "lightblue"
    },
    {
      "id": "db",
      "type": "building",
      "x": 500,
      "y": 250,
      "label": "PostgreSQL",
      "color": "orange"
    },
    {
      "id": "cache",
      "type": "cloud",
      "x": 350,
      "y": 100,
      "label": "Redis",
      "color": "cyan"
    }
  ],
  "connections": [
    {
      "from": "api",
      "to": "db",
      "label": "query",
      "direction": "forward"
    },
    {
      "from": "api",
      "to": "cache",
      "label": "cache",
      "direction": "bidirectional"
    }
  ]
}
```

## Extensiones Futuras

SDJF v1.0 establece la base del formato. Versiones futuras pueden agregar:
- Coordenadas opcionales con auto-layout
- Waypoints para routing complejo
- Contenedores y grupos
- Proporciones de tamaño personalizables
- Estilos y temas

---

**Versión**: 1.0
**Fecha**: 2025-06-22
**Estado**: Estable
