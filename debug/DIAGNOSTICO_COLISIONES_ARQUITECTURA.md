# Diagnóstico Completo: Colisiones en 05-arquitectura-gag.svg

**Fecha**: 2026-01-16
**Analista**: José + Claude
**Archivo**: docs/diagrams/gags/05-arquitectura-gag.gag

---

## Resumen Ejecutivo

El diagrama 05-arquitectura-gag.svg presenta **86 colisiones** después de la optimización, con una reducción desde 127 colisiones iniciales. El análisis revela tres problemas principales:

1. **Solapamiento total** de `generator` y `svgwrite` (misma posición)
2. **Redistribución inadecuada**: 7 elementos en una sola franja horizontal (Y=719.5)
3. **Conteo incorrecto**: 12 colisiones contenedor-hijo se cuentan erróneamente

### Colisiones Reales vs. Reportadas
- **Reportadas**: 86 colisiones
- **Contenedor-hijo** (esperadas): 12 colisiones
- **Colisiones reales de iconos**: 6 colisiones
- **Estimadas por etiquetas**: ~68 colisiones (86 - 12 - 6 = 68)

---

## Problema 1: Solapamiento Total

### Descripción
Los elementos `generator` y `svgwrite` están en exactamente la misma posición:
- **generator**: (700.0, 719.5) size 80x50
- **svgwrite**: (700.0, 719.5) size 80x50
- **Overlap**: 80.0x50.0px (100% solapamiento)

### Causa
Durante la redistribución, el algoritmo asigna la misma posición X a ambos elementos.

### Impacto
- Visualmente invisible: un elemento tapa completamente al otro
- 1 colisión directa de iconos

---

## Problema 2: Redistribución a una Sola Franja

### Elementos Afectados
7 elementos redistribuidos a Y=719.5:

| Elemento    | X     | Nivel | Spacing al siguiente |
|-------------|-------|-------|---------------------|
| input       | 520.0 | 0     | 0px (OK)            |
| main        | 600.0 | 1     | -40px (OVERLAP)     |
| optimizer   | 640.0 | 0     | -20px (OVERLAP)     |
| generator   | 700.0 | 2     | -80px (OVERLAP)     |
| svgwrite    | 700.0 | 3     | -60px (OVERLAP)     |
| render      | 720.0 | 1     | 0px (OK)            |
| output      | 800.0 | 0     | -                   |

### Topología Esperada
Estos elementos deberían distribuirse verticalmente según sus niveles:
- **Nivel 0**: input, optimizer, output
- **Nivel 1**: main, render
- **Nivel 2**: generator
- **Nivel 3**: svgwrite

### Distribución Actual
Todos en Y=719.5 (una sola franja horizontal)

### Causa Raíz
Código en `auto_positioner.py`, línea 1138:
```python
franja_idx = min(level_idx, len(free_ranges) - 1)
```

Cuando `free_ranges` tiene longitud 1 (una sola franja libre):
- Nivel 0 → franja_idx = min(0, 0) = 0
- Nivel 1 → franja_idx = min(1, 0) = 0
- Nivel 2 → franja_idx = min(2, 0) = 0
- Nivel 3 → franja_idx = min(3, 0) = 0

**Todos los niveles se mapean a la misma franja**.

### Análisis de Franjas
```
Franjas libres encontradas: 1
  Franja 1: Y [389.0 - 1050.0] (altura: 661.0)
```

Los contenedores ocupan todo el espacio superior:
- layout_container: Y [80.0 - 321.0]
- routing_container: Y [80.0 - 269.0]
- analysis_container: Y [80.0 - 339.0]
- draw_container: Y [80.0 - 339.0]

Después de la altura máxima (339.0) + padding (50) = 389.0, solo queda una franja libre.

### Impacto
- 6 colisiones de iconos en Y=719.5
- Distribución horizontal insuficiente
- Pérdida de jerarquía visual (niveles topológicos no visibles)

---

## Problema 3: Colisiones Contenedor-Hijo

### Descripción
12 colisiones detectadas entre contenedores y sus elementos contenidos:

**layout_container**:
- layout_container ↔ layout
- layout_container ↔ sizing
- layout_container ↔ positioner

**routing_container**:
- routing_container ↔ router_mgr
- routing_container ↔ routers

**analysis_container**:
- analysis_container ↔ geometry
- analysis_container ↔ graph
- analysis_container ↔ collision

**draw_container**:
- draw_container ↔ icons
- draw_container ↔ connections
- draw_container ↔ labels
- draw_container ↔ containers

### Causa
El detector de colisiones no distingue entre:
1. Elementos independientes (colisión real)
2. Elementos contenidos dentro de sus contenedores (relación esperada)

### Impacto
- Infla el conteo de colisiones
- Genera falsos positivos en métricas de optimización
- Impide alcanzar 0 colisiones (objetivo inalcanzable)

---

## Problema 4: Estimación de Colisiones de Etiquetas

### Cálculo
- Total reportado: 86 colisiones
- Colisiones de iconos (real): 6
- Colisiones contenedor-hijo (erróneas): 12
- **Colisiones de etiquetas estimadas**: 68

### Análisis
Con 23 elementos, cada uno con etiqueta, y múltiples conexiones con etiquetas:
- ~23 etiquetas de elementos
- ~25 etiquetas de conexiones
- **Total**: ~48 etiquetas

68 colisiones entre ~48 etiquetas indica:
- Alta densidad de texto
- Posicionamiento de etiquetas inadecuado
- Posible overlap con líneas de conexión

---

## Soluciones Propuestas

### Solución 1: Dividir Franja Libre en Sub-Franjas

**Objetivo**: Distribuir niveles verticalmente dentro de una sola franja libre.

**Modificación en `auto_positioner.py`**, método `_position_free_elements_by_topology()`:

```python
def _position_free_elements_by_topology(
    self,
    layout: Layout,
    elements: List[dict],
    free_ranges: List[tuple]
):
    """
    Posiciona elementos usando niveles topológicos en franjas libres.
    Si hay una sola franja pero múltiples niveles, divide la franja en sub-franjas.
    """
    # Agrupar elementos por nivel
    by_level = {}
    for elem in elements:
        level = layout.topological_levels.get(elem['id'], 0)
        if level not in by_level:
            by_level[level] = []
        by_level[level].append(elem)

    num_levels = len(by_level)
    center_x = layout.canvas['width'] / 2

    # NUEVO: Si solo hay 1 franja pero múltiples niveles, dividir la franja
    if len(free_ranges) == 1 and num_levels > 1:
        y_start, y_end = free_ranges[0]
        free_height = y_end - y_start
        level_height = free_height / num_levels

        # Crear sub-franjas para cada nivel
        sub_franjas = []
        for i in range(num_levels):
            sub_y_start = y_start + (i * level_height)
            sub_y_end = sub_y_start + level_height
            sub_franjas.append((sub_y_start, sub_y_end))

        logger.debug(f"    Dividiendo franja libre en {num_levels} sub-franjas verticales")
        free_ranges = sub_franjas

    # Asignar cada nivel a una franja (original o sub-franja)
    for level_idx, level_num in enumerate(sorted(by_level.keys())):
        level_elements = by_level[level_num]

        # Seleccionar franja para este nivel
        franja_idx = min(level_idx, len(free_ranges) - 1)
        y_start, y_end = free_ranges[franja_idx]

        # Posicionar en el centro de la franja/sub-franja
        y_position = (y_start + y_end) / 2

        # Distribuir horizontalmente (código existente)
        num_elements = len(level_elements)
        if num_elements == 1:
            level_elements[0]['x'] = center_x
            level_elements[0]['y'] = y_position
        else:
            widths = []
            for elem in level_elements:
                width, height = self.sizing.get_element_size(elem)
                widths.append(width)

            spacing_between = SPACING_SMALL
            total_width = sum(widths) + (num_elements - 1) * spacing_between
            start_x = center_x - (total_width / 2)

            current_x = start_x
            for i, elem in enumerate(level_elements):
                elem['x'] = current_x
                elem['y'] = y_position
                current_x += widths[i] + spacing_between

        logger.debug(f"    Nivel {level_num} → Franja {franja_idx+1}, Y={y_position:.1f}")
```

**Efecto esperado**:
Para arquitectura-gag con 4 niveles en franja [389.0 - 1050.0]:
- Nivel 0 → Y = 554.25 (centro de [389.0, 554.25])
- Nivel 1 → Y = 636.5  (centro de [554.25, 719.5])
- Nivel 2 → Y = 802.0  (centro de [719.5, 884.75])
- Nivel 3 → Y = 967.375 (centro de [884.75, 1050.0])

**Resultado**: Separación vertical entre niveles, eliminando solapamientos horizontales.

---

### Solución 2: Excluir Contenedor-Hijo del Conteo

**Objetivo**: Evitar contar como colisiones las relaciones contenedor-hijo.

**Modificación en `AlmaGag/analysis/collision.py`** (detector de colisiones):

```python
def detect_all(self, layout: Layout) -> List[dict]:
    """Detecta todas las colisiones, excluyendo relaciones contenedor-hijo."""
    collisions = []
    elements = layout.elements

    # Mapear elementos contenidos
    contained_in = {}  # {child_id: parent_id}
    for elem in elements:
        if 'contains' in elem:
            for ref in elem.get('contains', []):
                child_id = ref['id'] if isinstance(ref, dict) else ref
                contained_in[child_id] = elem['id']

    # Detectar colisiones
    for i, elem1 in enumerate(elements):
        bbox1 = self.geometry.get_bbox(elem1)

        for elem2 in elements[i+1:]:
            # NUEVO: Verificar si es relación contenedor-hijo
            id1, id2 = elem1['id'], elem2['id']
            if (contained_in.get(id1) == id2 or
                contained_in.get(id2) == id1):
                continue  # Saltar colisión contenedor-hijo

            bbox2 = self.geometry.get_bbox(elem2)

            if self.geometry.rectangles_intersect(bbox1, bbox2):
                collisions.append({
                    'elem1': elem1['id'],
                    'elem2': elem2['id'],
                    'type': 'element-element'
                })

    return collisions
```

**Resultado**: Conteo real de colisiones (sin inflar con relaciones esperadas).

---

### Solución 3: Mejorar Cálculo de Anchos en Distribución Horizontal

**Objetivo**: Evitar que elementos con anchos mayores a 80px se solapen.

**Problema actual**: En línea 1163 de auto_positioner.py:
```python
current_x += widths[i] + spacing_between
```

Esto funciona si las posiciones se centran correctamente, pero si `elem['x']` se interpreta como esquina superior izquierda, los anchos no se están usando correctamente.

**Verificar**: Asegurar que `elem['x']` corresponde a la esquina superior izquierda del icono, no al centro.

---

### Solución 4: Expandir Canvas Verticalmente (Opcional)

**Objetivo**: Proporcionar más espacio vertical para niveles.

**Trigger**: Si `num_levels > 1` y `free_height / num_levels < 150` (muy poco espacio por nivel).

**Acción**: Expandir canvas verticalmente:
```python
if free_height / num_levels < 150:
    extra_height = (150 * num_levels) - free_height
    layout.canvas['height'] += extra_height
    logger.debug(f"    Expandiendo canvas verticalmente: +{extra_height}px")
```

---

## Métricas de Éxito

### Antes (Actual)
- Colisiones reportadas: 86
- Colisiones de iconos: 6 (real) + 12 (contenedor-hijo)
- Elementos en mismo Y: 7 (todos en Y=719.5)
- Solapamiento total: 1 (generator/svgwrite)

### Después (Esperado)
- Colisiones reportadas: < 20 (solo etiquetas)
- Colisiones de iconos: 0
- Elementos distribuidos en 4 niveles Y
- Solapamiento total: 0
- Jerarquía topológica visible

---

## Próximos Pasos

1. **Implementar Solución 1**: Dividir franja en sub-franjas ✅ (código proporcionado)
2. **Implementar Solución 2**: Excluir contenedor-hijo ✅ (código proporcionado)
3. **Probar con arquitectura-gag**: Verificar reducción de colisiones
4. **Ajustar spacing**: Si aún hay overlap, incrementar `SPACING_SMALL`
5. **Optimizar etiquetas**: Analizar colisiones de etiquetas restantes

---

## Archivos Afectados

### Para Solución 1 (Sub-Franjas)
- `AlmaGag/layout/auto_positioner.py` (líneas 1107-1169)

### Para Solución 2 (Excluir Contenedor-Hijo)
- `AlmaGag/analysis/collision.py` (método `detect_all`)

### Archivos de Debug
- `debug/analisis_colisiones_arquitectura.py` (script de análisis)
- `debug/analisis_arquitectura_output.txt` (output del análisis)
- `debug/iterations/05-arquitectura-gag_iterations_*.json` (dumps)

---

## Conclusión

El problema principal es la **redistribución inadecuada** cuando hay una sola franja libre pero múltiples niveles topológicos. La solución es **dividir la franja en sub-franjas verticales**, garantizando separación visual entre niveles.

El segundo problema es el **conteo incorrecto** de colisiones contenedor-hijo, que se resuelve excluyéndolas del detector.

Con ambas soluciones implementadas, esperamos reducir las colisiones de **86 → ~20** (solo etiquetas) y conseguir **0 colisiones de iconos**.
