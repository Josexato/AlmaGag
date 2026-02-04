# Cálculo de Dimensiones del SVG Final en LAF

## Resumen Ejecutivo

Las dimensiones del canvas SVG se calculan **DOS veces** durante el flujo LAF:

1. **Primera vez:** Después de la Fase 4 (Crecimiento de Contenedores)
2. **Segunda vez (FINAL):** Después de la Fase 4.5 (Redistribución Vertical)

## Flujo Temporal Detallado

```
┌─────────────────────────────────────────────────────────────────┐
│ FASE 1: Análisis de Estructura                                 │
│ - NO calcula canvas                                             │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ FASE 2: Layout Abstracto                                        │
│ - NO calcula canvas                                             │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ FASE 3: Inflación de Elementos                                  │
│ - NO calcula canvas                                             │
│ - Usa canvas del JSON inicial (1400x1100)                       │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ FASE 4: Crecimiento de Contenedores                             │
│ - Expande contenedores bottom-up                                │
│ - 📏 CALCULA CANVAS #1 (laf_optimizer.py:616-621)              │
│   Método: container_grower.calculate_final_canvas()             │
│   Algoritmo:                                                     │
│   - Recorre todos los elementos primarios                       │
│   - max_x = max(elem.x + elem.width)                            │
│   - max_y = max(elem.y + elem.height)                           │
│   - Incluye dimensiones de etiquetas                            │
│   - Agrega margen de 50px                                       │
│   Canvas: ~1402x3867px (aproximado)                             │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ FASE 4.5: Redistribución Vertical + Centrado Horizontal         │
│ - Reposiciona elementos verticalmente (respeta alturas reales)  │
│ - 📏 CALCULA CANVAS #2 - FINAL (laf_optimizer.py:389-394)      │
│   Método: container_grower.calculate_final_canvas() (mismo)     │
│   ⚠️  PROBLEMA POTENCIAL: Se calcula ANTES del centrado         │
│   Canvas: ~1402x3867px                                           │
│                                                                  │
│ - Centra elementos horizontalmente (laf_optimizer.py:406)       │
│   ⚠️  Las posiciones X cambian DESPUÉS del cálculo del canvas   │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ Routing + Renderizado                                            │
│ - Usa layout.canvas['width'] y layout.canvas['height']          │
│ - SVG final: <svg width="1402.0" height="3867.0">               │
└─────────────────────────────────────────────────────────────────┘
```

## Implementación: `calculate_final_canvas()`

**Archivo:** `AlmaGag/layout/laf/container_grower.py:688-735`

### Algoritmo

```python
def calculate_final_canvas(self, structure_info, layout):
    max_x = 0
    max_y = 0

    # Recorrer solo elementos primarios
    for elem_id in structure_info.primary_elements:
        elem = layout.elements_by_id.get(elem_id)

        # Calcular bounds del elemento
        elem_x = elem['x']
        elem_y = elem['y']
        elem_w = elem.get('width', ICON_WIDTH)
        elem_h = elem.get('height', ICON_HEIGHT)

        max_x = max(max_x, elem_x + elem_w)
        max_y = max(max_y, elem_y + elem_h)

        # Incluir bounds de la etiqueta si existe
        if elem_id in layout.label_positions:
            label_x, label_y, _, _ = layout.label_positions[elem_id]
            label_text = elem.get('label', '')
            label_w = len(label_text) * 8  # Estimación: 8px por carácter
            label_h = 18                    # Altura de línea

            max_x = max(max_x, label_x + label_w)
            max_y = max(max_y, label_y + label_h)

    # Agregar margen de 50px
    margin = 50
    canvas_width = max_x + margin
    canvas_height = max_y + margin

    return (canvas_width, canvas_height)
```

### Características

- ✓ Solo considera **elementos primarios** (no elementos contenidos)
- ✓ Incluye dimensiones de **contenedores expandidos**
- ✓ Incluye dimensiones de **etiquetas** (usando `label_positions`)
- ✓ Agrega **margen de 50px**
- ⚠️ Usa **estimación simple** para ancho de etiquetas (8px/char)

## ⚠️ Problema Potencial Identificado

### Secuencia Actual

```
Fase 4.5:
  1. Redistribuir verticalmente elementos
  2. 📏 Calcular canvas (laf_optimizer.py:389)
  3. Centrar horizontalmente elementos (laf_optimizer.py:406)
```

**Problema:** El canvas se calcula **ANTES** del centrado horizontal.

Si el centrado mueve elementos hacia la derecha, el canvas podría quedarse **más pequeño** de lo necesario.

### ¿Por qué no es un problema actualmente?

El centrado usa `canvas['width']` para calcular posiciones:

```python
# _center_elements_horizontally (línea 434, 453)
elem['x'] = layout.canvas['width'] / 2  # Para un solo elemento
start_x = (canvas_width - total_width) / 2  # Para múltiples elementos
```

Por lo tanto:
- Los elementos **nunca exceden** el canvas actual
- El centrado trabaja **dentro** del espacio ya calculado

### ¿Cuándo podría fallar?

Si en el futuro se agregan transformaciones después del cálculo final del canvas que **aumenten** las posiciones X o Y más allá de los bounds actuales.

## Ubicaciones en el Código

### Cálculo del Canvas

1. **Primera llamada (Fase 4):**
   - `AlmaGag/layout/laf_optimizer.py:616-621`
   - Después de `grow_containers()`

2. **Segunda llamada FINAL (Fase 4.5):**
   - `AlmaGag/layout/laf_optimizer.py:389-394`
   - Durante `_redistribute_vertical_after_growth()`
   - **ANTES** del centrado horizontal

### Método de Cálculo

- `AlmaGag/layout/laf/container_grower.py:688-735`
- Método: `calculate_final_canvas()`

## Orden de Ejecución (Fase 4.5)

```python
# laf_optimizer.py:258-406
def _redistribute_vertical_after_growth(self, structure_info, layout):
    # 1. Redistribuir Y de elementos por nivel
    for level_num in sorted(by_level.keys()):
        # ... ajustar posiciones Y ...

    # 2. Calcular canvas FINAL
    canvas_width, canvas_height = self.container_grower.calculate_final_canvas(
        structure_info, layout
    )
    layout.canvas['width'] = canvas_width
    layout.canvas['height'] = canvas_height

    # 3. Centrar horizontalmente (usa canvas calculado arriba)
    for level_num in sorted(by_level.keys()):
        self._center_elements_horizontally(level_elements, layout, ...)
```

## Verificación

Para verificar las dimensiones finales:

```bash
grep 'width=' test-container-laf.svg | head -1
# Output: <svg ... width="1402.0" height="3867.0" ...>
```

## Fecha

2026-01-22
