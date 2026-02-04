# Fix: Hub Container Positioning - Preservación del Orden Optimizado

## Problema Identificado

El algoritmo de barycenter bidireccional con hub positioning estaba moviendo correctamente los contenedores al centro durante la Fase 2 (Layout Abstracto), pero este orden se **perdía** en la Fase 4.5 (Redistribución Vertical).

### Síntomas

**Orden optimizado en Fase 2:**
```
laf_optimizer -> analysis_module-stage -> optimizer
```

**Orden real en Fase 4.5 (centrado horizontal):**
```
optimizer -> laf_optimizer -> analysis_module-stage
```

**Resultado:** `analysis_module-stage` terminaba a la derecha en lugar de en el centro, causando cruces de conectores.

## Causa Raíz

### Problema 1: Hub Positioning en el Momento Incorrecto

El hub positioning se ejecutaba dentro de `_order_layer_barycenter_forward()`, pero el **backward pass** reordenaba después, deshaciendo el posicionamiento del hub.

**Archivo:** `AlmaGag/layout/laf/abstract_placer.py:126-180`

### Problema 2: Pérdida del Orden en Fase 4.5

En `_redistribute_vertical_after_growth()`, los elementos se agrupaban por nivel usando `structure_info.primary_elements`, que no mantiene ningún orden específico:

```python
# Código anterior (INCORRECTO)
for elem_id in structure_info.primary_elements:  # Sin orden preservado
    level = structure_info.topological_levels.get(elem_id, 0)
    by_level[level].append(elem_id)
```

**Archivo:** `AlmaGag/layout/laf_optimizer.py:288-294`

## Solución Implementada

### Fix 1: Hub Positioning al Final de Cada Iteración

Mover el hub positioning FUERA de los loops de forward/backward para que se ejecute **después** de ambos passes:

```python
def _order_within_layers(self, layers, structure_info, layout):
    for iteration in range(iterations):
        # Forward pass
        for layer_idx in range(1, len(layers)):
            self._order_layer_barycenter_forward(...)  # Sin hub positioning

        # Backward pass
        for layer_idx in range(len(layers) - 2, 0, -1):
            self._order_layer_barycenter_backward(...)

        # Hub positioning DESPUÉS de ambos passes (última palabra)
        for layer_idx in range(len(layers)):
            if len(layers[layer_idx]) >= 3:
                self._position_hub_containers_in_center(
                    layers[layer_idx],
                    structure_info,
                    layout
                )
```

**Archivo:** `AlmaGag/layout/laf/abstract_placer.py:145-167`

### Fix 2: Guardar el Orden Optimizado

Guardar el orden de las capas después de todas las iteraciones para usarlo en Fase 4.5:

```python
# Después de _order_within_layers()
layout.optimized_layer_order = [layer.copy() for layer in layers]
```

**Archivo:** `AlmaGag/layout/laf/abstract_placer.py:73-75`

### Fix 3: Usar el Orden Optimizado en Fase 4.5

Modificar `_redistribute_vertical_after_growth()` para usar el orden guardado:

```python
# Usar orden optimizado de Fase 2
if hasattr(layout, 'optimized_layer_order') and layout.optimized_layer_order:
    for layer_idx, layer_elements in enumerate(layout.optimized_layer_order):
        # Mapear índice de capa a nivel topológico
        first_elem_id = layer_elements[0]
        actual_level = structure_info.topological_levels.get(first_elem_id, layer_idx)
        by_level[actual_level] = layer_elements.copy()
```

**Archivo:** `AlmaGag/layout/laf_optimizer.py:288-316`

## Resultado

### Posiciones Finales

```
Nivel 4:
  laf_optimizer:         X=100.0  (IZQUIERDA)
  analysis_module-stage: X=660.0  (CENTRO) ✓
  optimizer:             X=1370.0 (DERECHA)
```

### Conexiones

- `laf_optimizer` conecta a elementos dentro de `analysis_module-stage`
- `optimizer` conecta a elementos dentro de `analysis_module-stage`
- Con el contenedor EN EL CENTRO, las conexiones desde ambos lados minimizan cruces

### Beneficios

1. **Minimización de cruces:** Contenedores hub posicionados óptimamente
2. **Orden consistente:** El orden optimizado se preserva desde Fase 2 hasta Fase 4.5
3. **Legibilidad:** Diagramas más claros y fáciles de seguir

## Archivos Modificados

1. **`AlmaGag/layout/laf/abstract_placer.py`**
   - Método `_order_within_layers()`: Hub positioning al final de cada iteración
   - Método `place_elements()`: Guardar orden optimizado en `layout.optimized_layer_order`
   - Método `_order_layer_barycenter_forward()`: Eliminar hub positioning interno

2. **`AlmaGag/layout/laf_optimizer.py`**
   - Método `_redistribute_vertical_after_growth()`: Usar orden optimizado guardado
   - Método `_center_elements_horizontally()`: Agregar debug del orden recibido

## Verificación

```bash
python -m AlmaGag.main docs/diagrams/gags/05-arquitectura-gag.gag \
  --layout-algorithm=laf --visualdebug --exportpng --debug \
  -o test-container-laf.svg 2>&1 | grep "CENTRADO.*Nivel: 3" -A 8
```

**Output:**
```
[CENTRADO] Nivel: 3 elementos
           laf_optimizer: X 0.0 -> 100.0
           analysis_module-stage: X 480.0 -> 660.0  # CENTRO ✓
           optimizer: X 960.0 -> 1370.0
```

## Fecha

2026-01-22
