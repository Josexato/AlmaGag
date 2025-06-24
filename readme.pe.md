# Generador de Diagramas SVG

Este repositorio contiene `svg_diagram_generator.py`, un script sencillo que lee una descripción JSON de elementos y sus conexiones y produce un diagrama SVG.

## Instalación

Asegúrate de tener Python 3 instalado. Instala la dependencia requerida `svgwrite`:

```bash
pip install svgwrite
```

## Formato de entrada JSON

El script espera un archivo JSON con dos arreglos principales: `elements` y `connections`.

### `elements`
Cada elemento describe un ícono del diagrama y debe incluir como mínimo los siguientes campos:

- `id`: identificador único usado para referenciar el elemento desde `connections`.
- `x`, `y`: coordenadas de la esquina superior izquierda del ícono dentro del lienzo.
- `label`: texto mostrado debajo del ícono. Puedes incluir `\n` para etiquetas de varias líneas.
- `type` *(opcional)*: uno de `server`, `firewall`, `building`, `cloud`. Un tipo desconocido dibuja el ícono de plátano con cinta adhesiva.
- `color` *(opcional)*: color de relleno usado para el ícono.

### `connections`
Define las líneas que enlazan dos elementos. Cada conexión tiene:

- `from`: `id` del elemento origen.
- `to`: `id` del elemento destino.
- `label` *(opcional)*: texto colocado cerca del centro de la línea.

```
{
  "elements": [
    {"id": "srv1", "x": 100, "y": 50, "label": "Server 1", "type": "server", "color": "lightblue"},
    {"id": "fw1", "x": 300, "y": 50, "label": "Firewall", "type": "firewall", "color": "orange"}
  ],
  "connections": [
    {"from": "srv1", "to": "fw1", "label": "Link"}
  ]
}
```

## Ejemplo de uso

Guarda el JSON en un archivo, por ejemplo `diagram.json`, y ejecuta:

```bash
python3 svg_diagram_generator.py diagram.json
```

Se creará un nuevo archivo llamado `diagram.svg` en el mismo directorio.


## Ejemplo de hoja de ruta

Se incluye el archivo `roadmap-25-06-22.gag` con un roadmap de funcionalidades. Genera su SVG con:

```bash
python3 svg_diagram_generator.py roadmap-25-06-22.gag
```

Fragmento del archivo:

```json
{
  "canvas": {
    "width": 1800,
    "height": 800
  },
  "elements": [
    {
      "id": "mejora1",
      "type": "building",
      "x": 100,
      "y": 200,
      "label": "Mejora de Estilo Básico\n(Formas detalladas: racks, nubes suaves)",
      "color": "lightgreen"
    }
  ]
}
```

El archivo resultante `roadmap-25-06-22.svg` muestra las mejoras planificadas.
