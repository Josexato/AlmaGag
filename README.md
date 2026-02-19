# AlmaGag - Generador Automatico de Grafos

**Proyecto**: ALMA (Almas y Sentidos) | **Version**: v3.2.0

AlmaGag genera diagramas SVG a partir de archivos JSON. Define elementos y conexiones, y AlmaGag los organiza automaticamente en un grafico vectorial.

## Instalacion

```bash
cd AlmaGag
pip install -e .
```

## Uso basico

```bash
almagag mi-diagrama.sdjf                           # Generar SVG
almagag mi-diagrama.sdjf --layout-algorithm=laf     # Layout avanzado (recomendado para diagramas complejos)
almagag mi-diagrama.sdjf -o salida.svg              # Especificar archivo de salida
```

## Ejemplo minimo (.sdjf)

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

```bash
almagag ejemplo.sdjf
```

Resultado: `ejemplo.svg` con auto-layout (sin coordenadas manuales).

## Ejemplo con iconos custom (.gag)

Archivos `.gag` permiten definir iconos SVG inline:

```json
{
  "icons": {
    "sensor": "<svg viewBox='0 0 80 50'><rect x='10' y='5' width='60' height='40' rx='8' fill='currentColor' stroke='black' stroke-width='2'/><circle cx='30' cy='25' r='6' fill='white'/><circle cx='50' cy='25' r='6' fill='white'/></svg>"
  },
  "elements": [
    { "id": "s1", "type": "sensor", "label": "Temp Sensor", "color": "gold" },
    { "id": "srv", "type": "server", "label": "Collector", "color": "silver" }
  ],
  "connections": [
    { "from": "s1", "to": "srv", "direction": "forward" }
  ]
}
```

## Formato de archivos

**Referencia completa con todos los campos, tipos de iconos, colores y ejemplos:**

> **[docs/spec/FORMATO_ARCHIVOS.md](docs/spec/FORMATO_ARCHIVOS.md)**

Resumen rapido:

| Extension | Que es |
|-----------|--------|
| `.sdjf` | JSON con `elements` y `connections`. Formato estandar. |
| `.gag` | Igual que `.sdjf` pero con seccion `"icons"` para iconos SVG custom. |

## Opciones CLI

| Opcion | Descripcion |
|--------|-------------|
| `--layout-algorithm {auto\|laf}` | Algoritmo de layout. `auto` (default) o `laf` (avanzado, menos cruces) |
| `-o, --output <ruta>` | Ruta del SVG de salida |
| `--debug` | Logs detallados |
| `--visualdebug` | Grilla y badge visual en el SVG |
| `--exportpng` | Genera PNG ademas de SVG |
| `--visualize-growth` | SVGs intermedios de cada fase LAF |
| `--color-connections` | Colorea cada conexion distinto |

## Documentacion

| Documento | Contenido |
|-----------|-----------|
| [Formato de Archivos](docs/spec/FORMATO_ARCHIVOS.md) | Referencia completa de .sdjf y .gag |
| [Quickstart](docs/guides/QUICKSTART.md) | Instalacion y primer diagrama |
| [Ejemplos](docs/guides/EXAMPLES.md) | Galeria con 12 ejemplos |
| [CLI Reference](docs/guides/CLI-REFERENCE.md) | Todas las opciones de linea de comandos |
| [Arquitectura](docs/architecture/ARCHITECTURE.md) | Diseno interno del codigo |
| [AUTO vs LAF](docs/guides/LAYOUT-DECISION-GUIDE.md) | Guia para elegir algoritmo de layout |
| [CHANGELOG](docs/CHANGELOG.md) | Historial de cambios |

## Ejemplos incluidos

Los diagramas de ejemplo estan en `docs/diagrams/gags/`:

```bash
# Regenerar todos los ejemplos
python scripts/generate_docs.py

# Generar uno especifico
almagag docs/diagrams/gags/05-arquitectura-gag.sdjf --layout-algorithm=laf -o docs/diagrams/svgs/05-arquitectura-gag.svg
```

## Licencia

MIT License - Copyright 2025 Jose Caceres - ALMA (Almas y Sentidos)
