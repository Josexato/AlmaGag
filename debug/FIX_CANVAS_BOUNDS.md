# Fix: Elementos Fuera del Canvas en LAF

## Problema Identificado

Al ejecutar el algoritmo LAF con `--visualdebug`, había **19 elementos fuera del canvas**. El SVG generado tenía dimensiones de 1090x3867, pero elementos se extendían hasta 1536x3205.

### Elementos Afectados

- **Etiquetas de elementos contenidos** dentro de contenedores
- Específicamente: `analysis_module-stage`, `draw_module-stage`, `laf_module-stage`, etc.
- **Badge de debug** "Generado: timestamp" en esquina superior derecha

### Impacto

Los elementos fuera del canvas:
- No se muestran correctamente en navegadores
- Se recortan en exportaciones PNG
- Causan problemas de visualización

## Causa Raíz

### Problema 1: `calculate_final_canvas()` Solo Consideraba Elementos Primarios

**Archivo:** `AlmaGag/layout/laf/container_grower.py:707`

```python
for elem_id in structure_info.primary_elements:  # ← PROBLEMA
    # Solo calcula bounds de elementos primarios
```

Los elementos **contenidos** (hijos dentro de contenedores) no se consideraban en el cálculo del canvas, a pesar de tener coordenadas globales después de la Fase 4.

### Problema 2: Canvas Calculado ANTES del Centrado Horizontal

**Archivo:** `AlmaGag/layout/laf_optimizer.py:388-406`

```python
# Fase 4.5:
1. Redistribuir verticalmente
2. Calcular canvas (línea 389) ← ANTES del centrado
3. Centrar horizontalmente (línea 406) ← Mueve elementos DESPUÉS
```

El centrado horizontal movía elementos fuera de los bounds calculados:

```
[CENTRADO] analysis_module-stage: X 0.0 -> 1220.0
Canvas: 1090px  ← ¡Elemento 130px fuera!
```

### Problema 3: Badge de Debug Mal Posicionado

**Archivo:** `AlmaGag/debug.py:47`

```python
badge_x = canvas_width - 200
badge_width = 190  # Pero el texto real necesita ~240px
```

El badge se extendía 42px más allá del canvas.

## Solución Implementada

### Fix 1: Considerar TODOS los Elementos

```python
def calculate_final_canvas(self, structure_info, layout):
    # Recorrer TODOS los elementos (primarios y contenidos)
    for elem in layout.elements:  # ← Cambio de primary_elements a elements
        elem_id = elem['id']

        # Calcular bounds del elemento
        max_x = max(max_x, elem_x + elem_w)
        max_y = max(max_y, elem_y + elem_h)

        # Incluir etiquetas (calculando ancho real con múltiples líneas)
        if elem_id in layout.label_positions:
            lines = label_text.split('\n')
            max_line_len = max(len(line) for line in lines)
            label_w = max_line_len * 8
            # ...
```

**Archivo modificado:** `container_grower.py:688-756`

### Fix 2: Recalcular Canvas DESPUÉS del Centrado

```python
def _redistribute_vertical_after_growth(self, structure_info, layout):
    # 1. Redistribuir verticalmente
    # 2. Calcular canvas inicial
    # 3. Centrar horizontalmente

    # 4. CRÍTICO: Recalcular canvas DESPUÉS del centrado
    canvas_width, canvas_height = self.container_grower.calculate_final_canvas(
        structure_info, layout
    )
    layout.canvas['width'] = canvas_width
    layout.canvas['height'] = canvas_height
```

**Archivo modificado:** `laf_optimizer.py:408-420`

### Fix 3: Aumentar Margen y Ajustar Badge

**Margen aumentado:**
```python
# container_grower.py:749-754
margin = 250  # Aumentado de 50 a 250 para acomodar badge
```

**Badge ajustado:**
```python
# debug.py:46-49
badge_width = 240  # Aumentado de 190 a 240
badge_x = canvas_width - badge_width - 10  # Margen de 10px
```

**Archivos modificados:**
- `container_grower.py:749-754`
- `debug.py:46-49`

## Resultados

### Antes del Fix

```
Canvas: 1090 x 3867
Elementos fuera: 19
Canvas necesario: 1536 x 3205
Overflow máximo: +446px (X), -662px (Y)
```

### Después del Fix

```
Canvas: 1786 x 4067
Elementos fuera: 0
✓ Todos los elementos dentro del canvas
```

## Archivos Modificados

1. **`AlmaGag/layout/laf/container_grower.py`**
   - Método `calculate_final_canvas()` (líneas 688-756)
   - Ahora considera TODOS los elementos (primarios + contenidos)
   - Calcula ancho real de etiquetas multi-línea
   - Margen aumentado a 250px

2. **`AlmaGag/layout/laf_optimizer.py`**
   - Método `_redistribute_vertical_after_growth()` (líneas 408-420)
   - Agrega recálculo de canvas DESPUÉS del centrado horizontal

3. **`AlmaGag/debug.py`**
   - Función `add_debug_badge()` (líneas 46-49)
   - Badge width aumentado a 240px
   - Posicionamiento ajustado con margen

## Verificación

```bash
# Generar diagrama
python -m AlmaGag.main docs/diagrams/gags/05-arquitectura-gag.gag \
  --layout-algorithm=laf --visualdebug --exportpng -o test.svg

# Verificar dimensiones
grep 'width=' test.svg | head -1
# Output: width="1786.0" height="4067.0"

# Resultado: Todos los elementos dentro del canvas ✓
```

## Fecha

2026-01-22
