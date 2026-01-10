# Especificación: SVG to BWT Converter

**Versión**: v2.2 (Propuesta)
**Fecha**: 2026-01-09
**Autor**: José + ALMA

---

## 1. Objetivo

Crear una herramienta que convierta archivos SVG arbitrarios en código Python hardcodeado compatible con el sistema de íconos BWT (Black/White/Transparent) de AlmaGag.

### ¿Por qué?

Actualmente, agregar un nuevo ícono complejo requiere:
1. Diseñar el SVG en un editor (Inkscape, Illustrator, etc.)
2. Extraer manualmente los paths SVG del XML
3. Escribir código Python manualmente con los paths
4. Ajustar escalado y transformaciones

Este proceso es tedioso, propenso a errores y dificulta la expansión del catálogo de íconos.

### Beneficios

- ✅ **Automatización**: Convierte SVG → Python en un comando
- ✅ **Reutilización**: Permite importar íconos de librerías externas (Font Awesome SVG, etc.)
- ✅ **Estandarización**: Código generado sigue el patrón BWT existente
- ✅ **Escalabilidad**: Facilita agregar cientos de íconos nuevos

---

## 2. Diagrama de Flujo

```
┌──────────────────┐
│  INPUT:          │
│  archivo.svg     │
│  (vectorial)     │
└────────┬─────────┘
         │
         ▼
┌─────────────────────────────────────┐
│ FASE 1: Parsing del SVG             │
├─────────────────────────────────────┤
│ 1. Leer archivo SVG                 │
│ 2. Parsear XML (xml.etree/lxml)     │
│ 3. Extraer dimensiones (viewBox)    │
│ 4. Identificar elementos gráficos:  │
│    - <path>                          │
│    - <rect>                          │
│    - <circle>                        │
│    - <ellipse>                       │
│    - <polygon>                       │
│    - <polyline>                      │
│ 5. Extraer atributos:                │
│    - d (path data)                   │
│    - fill, stroke, stroke-width     │
│    - transform (si existe)           │
└────────┬────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│ FASE 2: Normalización               │
├─────────────────────────────────────┤
│ 1. Calcular bounding box del SVG    │
│ 2. Normalizar coordenadas a 0,0     │
│ 3. Calcular factor de escala:       │
│    scale_x = ICON_WIDTH / svg_width │
│    scale_y = ICON_HEIGHT / svg_height│
│ 4. Decidir estrategia de escala:    │
│    - uniform: min(scale_x, scale_y) │
│    - stretch: scale_x, scale_y      │
│ 5. Agrupar elementos por capa/tipo  │
└────────┬────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│ FASE 3: Simplificación (Opcional)   │
├─────────────────────────────────────┤
│ 1. Combinar paths similares          │
│ 2. Eliminar elementos invisibles:    │
│    - opacity="0"                     │
│    - fill="none" y stroke="none"    │
│ 3. Simplificar transformaciones:     │
│    - Aplicar matrices al path data   │
│ 4. Optimizar path data:              │
│    - Reducir decimales               │
│    - Comandos relativos vs absolutos │
└────────┬────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│ FASE 4: Generación de Código Python │
├─────────────────────────────────────┤
│ 1. Crear función draw_<nombre>()    │
│ 2. Generar docstring                 │
│ 3. Para cada elemento SVG:           │
│    - dwg.add(dwg.path(...))          │
│    - dwg.add(dwg.rect(...))          │
│    - etc.                             │
│ 4. Configurar atributos:             │
│    - fill, stroke, stroke_width      │
│    - transform con scale calculado   │
│ 5. Agregar imports necesarios        │
│ 6. Formatear código (PEP8)           │
└────────┬────────────────────────────┘
         │
         ▼
┌──────────────────────────┐
│  OUTPUT:                 │
│  draw_<nombre>.py        │
│  (código Python listo)   │
└──────────────────────────┘
```

---

## 3. Estructura de Salida

### 3.1. Formato del Código Generado

El código debe seguir el patrón de `draw/bwt.py`:

```python
"""
Ícono <nombre> - Generado automáticamente desde SVG
Fecha: <timestamp>
SVG original: <ruta_archivo_svg>
"""
from AlmaGag.config import ICON_WIDTH, ICON_HEIGHT

def draw_<nombre>(dwg, x, y):
    """
    Dibuja el ícono '<nombre>' ajustado a ICON_WIDTH x ICON_HEIGHT.

    Componentes:
    - <lista de elementos>
    """

    # Dimensiones originales del SVG
    svg_width = <ancho>
    svg_height = <alto>

    # Factor de escala para ajustar a ICON_WIDTH x ICON_HEIGHT
    scale_x = ICON_WIDTH / svg_width
    scale_y = ICON_HEIGHT / svg_height
    scale = min(scale_x, scale_y)  # Mantener aspect ratio

    # Elemento 1: <descripción>
    dwg.add(dwg.path(
        d="<path_data>",
        fill="<color>",
        stroke="<color>",
        stroke_width=<valor>,
        transform=f"translate({x},{y}) scale({scale})"
    ))

    # Elemento 2: <descripción>
    dwg.add(dwg.rect(
        insert=(x + <offset_x> * scale, y + <offset_y> * scale),
        size=(<width> * scale, <height> * scale),
        fill="<color>",
        stroke="<color>",
        stroke_width=<valor>
    ))

    # ... más elementos
```

### 3.2. Estructura de Datos Intermedia

Durante el procesamiento, mantener estructura:

```python
{
    "name": "icon_name",
    "original_size": (width, height),
    "viewBox": "0 0 100 100",
    "scale_strategy": "uniform",  # o "stretch"
    "elements": [
        {
            "type": "path",
            "d": "M 10,10 L 20,20 ...",
            "fill": "#000000",
            "stroke": "#FFFFFF",
            "stroke_width": 1.0,
            "transform": "translate(5,5)",
            "layer": "background"
        },
        {
            "type": "rect",
            "x": 10,
            "y": 10,
            "width": 50,
            "height": 30,
            "fill": "#FF0000",
            "stroke": "none",
            "layer": "foreground"
        }
        # ... más elementos
    ]
}
```

---

## 4. Casos de Uso

### 4.1. Caso Básico
```bash
# Convertir SVG simple
python -m AlmaGag.tools.svg2bwt icon.svg

# Output: draw/icon.py
```

### 4.2. Con Opciones
```bash
# Especificar nombre de función
python -m AlmaGag.tools.svg2bwt icon.svg --name custom_icon

# Mantener colores originales vs convertir a blanco/negro
python -m AlmaGag.tools.svg2bwt icon.svg --preserve-colors

# Estrategia de escalado
python -m AlmaGag.tools.svg2bwt icon.svg --scale uniform  # mantener ratio
python -m AlmaGag.tools.svg2bwt icon.svg --scale stretch  # llenar espacio

# Simplificar paths (reducir precisión)
python -m AlmaGag.tools.svg2bwt icon.svg --simplify --precision 2
```

### 4.3. Batch Processing
```bash
# Convertir múltiples SVG
python -m AlmaGag.tools.svg2bwt icons/*.svg --output-dir draw/
```

---

## 5. Validaciones y Restricciones

### 5.1. SVG Compatible

✅ **Soportado:**
- Elementos básicos: path, rect, circle, ellipse, polygon, polyline
- Atributos: fill, stroke, stroke-width, opacity
- Transformaciones: translate, scale, rotate, matrix
- ViewBox y dimensiones explícitas

❌ **No Soportado (versión inicial):**
- Gradientes complejos (convertir a color sólido)
- Filtros y efectos (ignorar)
- Animaciones (ignorar)
- Imágenes embebidas (advertir y omitir)
- Texto como `<text>` (convertir a path primero en editor)
- Máscaras y clipping paths (simplificar o advertir)

### 5.2. Validaciones Pre-Procesamiento

1. **Formato válido**: XML bien formado
2. **Tamaño razonable**: < 1MB (paths muy complejos pueden ralentizar)
3. **Elementos reconocidos**: Al menos 1 elemento gráfico extraíble
4. **Coordenadas válidas**: Números finitos, no NaN/Infinity

### 5.3. Advertencias

- Si SVG tiene gradientes complejos → advertir que se convertirán a color sólido
- Si SVG tiene texto → advertir que debe convertirse a paths primero
- Si SVG usa masks → advertir que puede perder detalles

---

## 6. Integración con AlmaGag

### 6.1. Registro Automático (Opcional)

Después de generar `draw/icon_name.py`, el script puede:

1. **Opción manual**: Imprimir instrucciones para registrar en `draw/icons.py`
   ```
   [INFO] Archivo generado: draw/icon_name.py
   [TODO] Agregar a draw/icons.py:

   from AlmaGag.draw.icon_name import draw_icon_name

   ICON_TYPES['icon_name'] = draw_icon_name
   ```

2. **Opción automática** (con flag `--register`): Modificar `draw/icons.py` automáticamente

### 6.2. Uso Inmediato

```json
{
  "elements": [
    {
      "id": "custom",
      "type": "icon_name",
      "x": 100,
      "y": 100,
      "label": "Nuevo Ícono"
    }
  ]
}
```

---

## 7. Arquitectura Propuesta

### 7.1. Módulos

```
AlmaGag/tools/
├── __init__.py
├── svg2bwt/
│   ├── __init__.py
│   ├── parser.py          # Fase 1: SVG parsing
│   ├── normalizer.py      # Fase 2: Normalización
│   ├── simplifier.py      # Fase 3: Simplificación
│   ├── codegen.py         # Fase 4: Generación código
│   └── cli.py             # Interfaz de línea de comandos
```

### 7.2. Clases Principales

```python
# parser.py
class SVGParser:
    def parse(self, svg_path: str) -> SVGDocument:
        """Parsea SVG y extrae elementos gráficos"""
        pass

# normalizer.py
class SVGNormalizer:
    def normalize(self, doc: SVGDocument) -> NormalizedSVG:
        """Normaliza coordenadas y calcula escalado"""
        pass

# simplifier.py
class SVGSimplifier:
    def simplify(self, doc: NormalizedSVG, options: dict) -> SimplifiedSVG:
        """Optimiza y simplifica elementos"""
        pass

# codegen.py
class PythonCodeGenerator:
    def generate(self, doc: SimplifiedSVG, name: str) -> str:
        """Genera código Python funcional"""
        pass
```

---

## 8. Ejemplos de Transformación

### 8.1. Input SVG Simple
```xml
<svg width="100" height="100" viewBox="0 0 100 100">
  <rect x="10" y="10" width="80" height="80" fill="#FF0000" stroke="#000000" stroke-width="2"/>
  <circle cx="50" cy="50" r="30" fill="#0000FF"/>
</svg>
```

### 8.2. Output Python Generado
```python
from AlmaGag.config import ICON_WIDTH, ICON_HEIGHT

def draw_simple(dwg, x, y):
    """
    Ícono simple - Generado desde SVG
    Componentes: 1 rect, 1 circle
    """
    svg_width = 100
    svg_height = 100
    scale = min(ICON_WIDTH / svg_width, ICON_HEIGHT / svg_height)

    # Rectángulo rojo
    dwg.add(dwg.rect(
        insert=(x + 10 * scale, y + 10 * scale),
        size=(80 * scale, 80 * scale),
        fill="#FF0000",
        stroke="#000000",
        stroke_width=2 * scale
    ))

    # Círculo azul
    dwg.add(dwg.circle(
        center=(x + 50 * scale, y + 50 * scale),
        r=30 * scale,
        fill="#0000FF"
    ))
```

---

## 9. Roadmap de Implementación

### Fase 1: MVP (Minimum Viable Product)
- ✅ Parser básico para `<path>`, `<rect>`, `<circle>`
- ✅ Normalización de coordenadas
- ✅ Generación de código Python funcional
- ✅ CLI básico con un archivo de entrada

### Fase 2: Mejoras
- Soporte para más elementos SVG (ellipse, polygon, polyline)
- Simplificación de paths
- Opciones de línea de comandos
- Batch processing

### Fase 3: Avanzado
- Conversión de gradientes a degradados AlmaGag
- Manejo de transformaciones complejas (matrix)
- Registro automático en ICON_TYPES
- Validación y testing automático del código generado

---

## 10. Testing

### 10.1. Test Cases

1. **SVG Simple** (1 path): BWT actual → reconstruir y comparar
2. **SVG Complejo** (múltiples elementos): Logo complejo
3. **SVG con Transformaciones**: rotate, scale, translate
4. **SVG con ViewBox**: diferentes aspectos ratios
5. **SVG inválido**: XML malformado, elementos vacíos

### 10.2. Validación de Output

1. **Sintaxis Python**: Código generado debe ejecutarse sin errores
2. **Renderizado**: SVG generado debe verse igual al original
3. **Escalado**: Debe ajustarse correctamente a ICON_WIDTH/HEIGHT

---

## 11. Dependencias

### Necesarias
- `xml.etree.ElementTree` (built-in Python)
- `svgwrite` (ya incluido en AlmaGag)

### Opcionales
- `lxml` (para SVG complejos, mejor performance)
- `svgpathtools` (para manipulación avanzada de paths)
- `Pillow` (para preview raster del resultado)

---

## 12. Limitaciones Conocidas

1. **Gradientes complejos**: Se convertirán a color sólido
2. **Texto SVG**: Debe convertirse a paths manualmente antes
3. **Filtros/Efectos**: Se ignorarán
4. **Precisión**: Paths muy complejos pueden generar código largo

---

## 13. Próximos Pasos

1. ✅ **Documentar especificación** (este archivo)
2. ⏳ **Crear estructura de módulos** `AlmaGag/tools/svg2bwt/`
3. ⏳ **Implementar parser básico** (Fase 1 del diagrama)
4. ⏳ **Implementar normalizer** (Fase 2)
5. ⏳ **Implementar code generator** (Fase 4)
6. ⏳ **Crear CLI** con argumentos básicos
7. ⏳ **Testing** con BWT actual como test case

---

**Estado**: 📋 Especificación completa - Listo para implementación
