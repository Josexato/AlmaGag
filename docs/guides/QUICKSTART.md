# Guía de Inicio Rápido - AlmaGag

## Instalación

### Requisitos

- Python 3.8 o superior
- pip (gestor de paquetes de Python)

### Instalar AlmaGag

```bash
cd /ruta/del/clon/AlmaGag   # la RAÍZ del repo (donde está pyproject.toml)
pip install -e .
```

Esto instala:
- El comando `almagag` globalmente
- Todas las dependencias necesarias (`svgwrite`)

## Primer Diagrama

### 1. Crear archivo SDJF

Crea un archivo `mi-diagrama.gag`:

```json
{
  "canvas": {"width": 800, "height": 600},
  "elements": [
    {
      "id": "frontend",
      "type": "cloud",
      "x": 150,
      "y": 250,
      "label": "Frontend",
      "color": "lightblue"
    },
    {
      "id": "api",
      "type": "server",
      "x": 400,
      "y": 250,
      "label": "API Rest",
      "color": "gold"
    },
    {
      "id": "database",
      "type": "building",
      "x": 650,
      "y": 250,
      "label": "PostgreSQL",
      "color": "orange"
    }
  ],
  "connections": [
    {
      "from": "frontend",
      "to": "api",
      "label": "HTTPS",
      "direction": "forward"
    },
    {
      "from": "api",
      "to": "database",
      "label": "SQL",
      "direction": "forward"
    }
  ]
}
```

### 2. Generar SVG

```bash
almagag mi-diagrama.gag
```

**Salida:**
```
[OK] AutoLayout v2.1: 0 colisiones detectadas
     - 1 niveles, 3 grupo(s)
     - Prioridades: 0 high, 3 normal, 0 low
[OK] Diagrama generado exitosamente: mi-diagrama.svg
```

### 3. Ver Resultado

Abre `mi-diagrama.svg` en tu navegador o editor de imágenes.

---

## Uso Avanzado

### Motor de layout (v3.4+: el motor elige solo)

Ya **no se elige algoritmo**. El comando normal no lleva flags de layout: el
motor (`LayoutEngine`) selecciona la estrategia a partir del JSON —
`contains`/`considerations` → `auto`; `areas`, nodos `decision` o un ciclo
sin coordenadas → `hier`; el histórico `legacy` (ex-LAF) está congelado y
sólo sirve para debug.

```bash
almagag diagrama.gag
```

La forma de influir en el resultado es el **JSON** (declarar `areas`,
`contains`, `considerations`, `semantic_type`, `layout_template`), no un
flag. Ver [LAYOUT-DECISION-GUIDE.md](./LAYOUT-DECISION-GUIDE.md).

---

### Auto-Layout (SDJF v2.0)

No necesitas especificar coordenadas:

```json
{
  "elements": [
    {
      "id": "api",
      "type": "server",
      "label": "API",
      "label_priority": "high",
      "hp": 2.0,
      "color": "gold"
    },
    {
      "id": "cache",
      "type": "cloud",
      "label": "Redis",
      "color": "cyan"
    },
    {
      "id": "logger",
      "type": "cloud",
      "label": "Logger",
      "label_priority": "low",
      "hp": 0.8,
      "color": "gray"
    }
  ],
  "connections": [
    {"from": "api", "to": "cache"},
    {"from": "api", "to": "logger"}
  ]
}
```

El sistema posiciona automáticamente:
- `api` (HIGH, grande) → Centro
- `cache` (NORMAL) → Alrededor
- `logger` (LOW, pequeño) → Periferia

### Sizing Proporcional

Controla el tamaño con `hp` (height) y `wp` (width):

```json
{
  "id": "big-server",
  "type": "server",
  "hp": 2.0,
  "wp": 1.5,
  "label": "Large Server"
}
```

- `hp` = 2.0 → Altura doble (100px en vez de 50px)
- `wp` = 1.5 → Ancho 1.5× (120px en vez de 80px)

### Waypoints (Routing Complejo)

Para líneas que deben evitar elementos:

```json
{
  "from": "A",
  "to": "B",
  "waypoints": [
    {"x": 450, "y": 490},
    {"x": 300, "y": 490}
  ],
  "label": "complex route",
  "direction": "forward"
}
```

---

## Opciones de Línea de Comando

### Uso Básico

```bash
almagag archivo.gag
```

### Opciones Principales

| Opción | Descripción |
|--------|-------------|
| `--layout-algorithm {select\|auto\|hier\|legacy}` | Forzar estrategia (debug; el default `select` decide solo) |
| `--debug` | Logs detallados |
| `--visualdebug` | Grilla + badge en SVG |
| `--exportpng` | Genera PNG además de SVG |
| `-o <ruta>` | Especifica archivo de salida |

**Ejemplos**:
```bash
# Layout con LAF
almagag diagrama.gag   # el motor elige la estrategia solo

# Debug completo
almagag diagrama.gag --debug --visualdebug

# Exportar PNG
almagag diagrama.gag --exportpng

# Salida personalizada
almagag diagrama.gag -o output/mi-diagrama.svg
```

Ver [CLI-REFERENCE.md](./CLI-REFERENCE.md) para documentación completa de todas las opciones.

### Uso con Python

```bash
python -m AlmaGag.main archivo.gag
```

---

## Ejemplos Incluidos

```bash
# Íconos disponibles
almagag docs/diagrams/gags/01-iconos-registrados.sdjf

# Tipos de conexiones
almagag docs/diagrams/gags/03-conexiones.sdjf

# Auto-layout completo
almagag docs/diagrams/gags/08-auto-layout.sdjf

# Sizing proporcional
almagag docs/diagrams/gags/09-proportional-sizing.sdjf

# Layout híbrido (auto + manual)
almagag docs/diagrams/gags/10-hybrid-layout.sdjf
```

---

## Tipos de Íconos Disponibles

Built-in (13): `server`, `cloud`, `building`, `firewall`, `database`,
`router`, `laptop`, `computer`, `document`, `user`, `diamond`, `decision`
(+ `bwt`, el fallback). Alias §O55: `inet`/`wan`/`internet` dibujan `cloud`.

| Tipo | Uso típico |
|------|------------|
| `server` | Servidores, APIs, servicios |
| `database` | Bases de datos, storage |
| `cloud` | Internet, WAN, nubes (también `inet`/`wan`/`internet`) |
| `building` | Sedes, datacenters, edificios |
| `firewall` | Seguridad perimetral |
| `router` | Equipos de red |
| `laptop` / `computer` | Puestos de trabajo, terminales |
| `document` | Documentos, equipos agrupados |
| `user` | Personas, roles |
| `diamond` / `decision` | Rombo: interfaz (UML) / decisión (flowchart → fuerza `hier`) |

Un `type` desconocido dibuja la banana con cinta (BWT) **rotulada con el
nombre del type** + WARNING (§O55/§Q64) — usable a propósito mientras un
concepto no tiene forma. Iconos custom: sección `"icons"` en un `.gag`.

## Direcciones de Conexión

```json
{
  "direction": "forward"       // A → B
}
{
  "direction": "backward"      // A ← B
}
{
  "direction": "bidirectional" // A ↔ B
}
{
  "direction": "none"          // A — B (sin flechas)
}
```

---

## Colores

Soporta nombres CSS y hexadecimales:

```json
"color": "lightblue"    // Nombre CSS
"color": "#3498DB"      // Hexadecimal
"color": "gold"         // Nombre CSS
"color": "#FF5733"      // Hexadecimal
```

Todos los colores generan gradientes automáticamente (claro → oscuro).

---

## Solución de Problemas

### Error: "comando no encontrado: almagag"

Instala en modo editable:
```bash
pip install -e .
```

O usa Python directamente:
```bash
python -m AlmaGag.main archivo.gag
```

### Aparece una banana con cinta (BWT)

El `type` no existe — el rótulo sobre la banana dice cuál. Opciones:
1. Usar uno de los 13 built-in (tabla de arriba) o un alias (`inet`→`cloud`)
2. Definir el icono en la sección `"icons"` de un `.gag`
3. Dejar el BWT a propósito (§Q64) mientras el concepto no tiene forma

### Warning: "N colisiones detectadas"

El auto-layout no pudo resolver todas las colisiones. Opciones:
1. **Dejar que el motor elija**: `almagag diagrama.gag` (el default `select` aplica la mejor estrategia)
2. Aumentar tamaño del canvas
3. Especificar coordenadas manualmente para elementos problemáticos
4. Ajustar prioridades con `label_priority`
5. Usar `hp`/`wp` para cambiar tamaños

---

## Siguientes Pasos

### Motor de layout
- **Cómo decide el motor**: Ver `docs/guides/LAYOUT-DECISION-GUIDE.md`
- **Referencia CLI completa**: Ver `docs/guides/CLI-REFERENCE.md`

### Especificaciones SDJF
- **SDJF v3.0**: Ver `docs/RELEASE_v3.0.0.md`
- **SDJF v2.0**: Ver `docs/spec/SDJF_v2.0_SPEC.md`
- **SDJF v2.1**: Ver `docs/spec/SDJF_v2.1_PROPOSAL.md`

### Recursos Adicionales
- **Arquitectura del código**: Ver `docs/architecture/ARCHITECTURE.md`
- **Galería de ejemplos**: Ver `docs/guides/EXAMPLES.md`

---

**Versión**: AlmaGag v3.5.0 · **Actualizado**: 2026-08-02
**Actualizado**: 2026-08-02
