# GAG - Generador Automático de Grafos

**Proyecto:** ALMA (Almas y Sentidos)
**Módulo:** GAG - Intérprete de sentidos para Funes

GAG es una herramienta para generar diagramas SVG a partir de archivos JSON en formato SDJF (Simple Diagram JSON Format). Permite describir nodos, conexiones y sus relaciones visuales de forma declarativa.

## Instalación

Asegúrate de tener Python 3 instalado. Instala la dependencia `svgwrite`:

```bash
pip install svgwrite
```

O usando `requirements.txt`:

```bash
pip install -r requirements.txt
```

## Uso

Ejecuta GAG desde el directorio padre del proyecto con:

```bash
python -m AlmaGag.main archivo.gag
```

Esto genera un archivo SVG con el mismo nombre base en el directorio actual.

### Ejemplo:

```bash
python -m AlmaGag.main roadmap-25-06-22.gag
```

Genera: `roadmap-25-06-22.svg`

## Formato de entrada: SDJF v1.0

GAG utiliza archivos `.gag` que contienen JSON en formato SDJF. La estructura básica es:

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

### Sección `canvas` (opcional)

Define el tamaño del SVG resultante:

- `width`: ancho en píxeles (default: 1400)
- `height`: alto en píxeles (default: 900)

### Sección `elements` (requerida)

Define los nodos del diagrama. Cada elemento debe tener:

- **`id`** (requerido): Identificador único
- **`x`, `y`** (requerido): Coordenadas top-left del ícono en píxeles
- **`type`** (opcional): Tipo de ícono a dibujar
  - Tipos disponibles: `server`, `firewall`, `building`, `cloud`
  - Si el tipo no existe o no se especifica, se dibuja un **plátano con cinta** (BWT) como fallback de ambigüedad
- **`label`** (opcional): Texto debajo del ícono. Soporta saltos de línea con `\n`
- **`color`** (opcional): Color de relleno del ícono (default: `gray`)

### Sección `connections` (requerida)

Define las aristas del diagrama. Cada conexión puede tener:

- **`from`** (requerido): ID del nodo origen
- **`to`** (requerido): ID del nodo destino
- **`label`** (opcional): Texto en el centro de la línea
- **`direction`** (opcional): Dirección de la flecha
  - `forward`: flecha al final (A → B)
  - `backward`: flecha al inicio (A ← B)
  - `bidirectional`: flechas en ambos extremos (A ↔ B)
  - `none`: sin flechas (default)
- **`relation`** (opcional): Tipo semántico de relación (decorativo en v1.0)

## Ejemplos incluidos

### roadmap-25-06-22.gag

Diagrama de roadmap de mejoras visuales:

```bash
python -m AlmaGag.main roadmap-25-06-22.gag
```

### data/primos.gag

Diagrama de flujo para calcular números primos:

```bash
python -m AlmaGag.main data/primos.gag
```

## Estructura del proyecto

```
AlmaGag/
├── main.py              # Punto de entrada
├── generator.py         # Lógica de generación SVG y markers de flechas
├── config.py            # Constantes (WIDTH, HEIGHT, ICON_WIDTH, etc.)
└── draw/
    ├── __init__.py
    ├── icons.py         # Lógica de dibujo de íconos
    ├── connections.py   # Lógica de conexiones con offset visual
    ├── bwt.py           # Fallback: Banana With Tape
    ├── server.py        # Ícono tipo server
    ├── firewall.py      # Ícono tipo firewall
    ├── building.py      # Ícono tipo building
    └── cloud.py         # Ícono tipo cloud
```

## Características de la v1.0

✅ Formato SDJF estándar con `elements` y `connections`
✅ Soporte de canvas personalizado
✅ Flechas direccionales (forward, backward, bidirectional, none)
✅ Sistema modular de íconos con importación dinámica
✅ Fallback BWT para tipos desconocidos (explícita ambigüedad)
✅ Etiquetas multilínea en elementos
✅ Codificación UTF-8 sin BOM

## Mejoras v1.1

✅ **Módulo `connections.py` separado**: Lógica de conexiones extraída a su propio módulo para mejor mantenibilidad
✅ **Offset visual en conexiones**: Las líneas de conexión ahora calculan un offset desde el centro del ícono para evitar superposición visual con los elementos. Diferentes tipos de íconos (como `cloud`) tienen offsets adaptados a su forma
✅ **Orden de renderizado optimizado**: Los íconos se dibujan primero y las conexiones después, asegurando que las flechas queden visualmente encima cuando corresponde

## Roadmap futuro

- **Autolayout**: Generación automática de coordenadas
- **Gradientes y sombras**: Mejoras visuales avanzadas
- **Temas**: Estilos predefinidos (Cloud, Tech, Minimal)
- **Animación**: Timeline para aparición secuencial
- **Íconos SVG externos**: Soporte para iconografía personalizada

## Contribuir

Este proyecto es parte de ALMA. Para reportar bugs o sugerir mejoras, abre un issue en el repositorio.

## Licencia

[Especificar licencia aquí]
