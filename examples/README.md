# Examples

Esta carpeta contiene archivos `.gag` de ejemplo que demuestran las características de AlmaGag.

## Catálogo de ejemplos

| Archivo | Descripción |
|---------|-------------|
| `01-iconos-registrados.gag` | Muestra los 4 tipos de iconos registrados |
| `02-iconos-no-registrados.gag` | Uso de SVG externo (BWT) para iconos custom |
| `03-conexiones.gag` | Tipos de routing: straight, orthogonal, bezier, arc |
| `04-gradientes-colores.gag` | Sistema de colores y gradientes |
| `05-arquitectura-gag.gag` | Arquitectura interna de AlmaGag (v3.0) |
| `06-waypoints.gag` | Routing manual con waypoints |
| `07-containers.gag` | Agrupación de elementos con `contains` |
| `08-auto-layout.gag` | Layout automático jerárquico |
| `09-proportional-sizing.gag` | Sizing proporcional con `hp`/`wp` |
| `10-hybrid-layout.gag` | Combinación de posiciones fijas y auto-layout |
| `continentes-america.gag` | Ejemplo complejo de mapa con contenedores |

## Uso

Para generar el SVG de cualquier ejemplo:

```bash
almagag examples/01-iconos-registrados.gag
```

O con Python:

```bash
python -m AlmaGag.main examples/01-iconos-registrados.gag
```

Los SVG generados se crean en la misma ubicación que el `.gag` de entrada.

## Regenerar todos los ejemplos

Usa el script de utilidad:

```bash
python scripts/generate_examples.py
```
