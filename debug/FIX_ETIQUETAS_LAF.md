# Fix: Etiquetas separadas de íconos en LAF

## Problema Identificado

Las etiquetas de los elementos en los niveles 0, 1 y 2 (`input`, `main`, `generator`)
aparecían separadas de sus íconos después de ejecutar el algoritmo LAF con centrado horizontal.

### Comportamiento Observado

**ANTES del fix:**
- Etiquetas en x=40.0 (posición inicial no centrada)
- Íconos en x=701.0 (centrados correctamente en Fase 4.5)
- Distancia horizontal: ~661px (etiquetas muy separadas a la izquierda)

**DESPUÉS del fix:**
- archivo.gag: x=585.0 (centrada sobre su ícono)
- main.py: x=637.6 (centrada sobre su ícono)
- generator.py: x=637.6 (centrada sobre su ícono)

## Causa Raíz

El problema ocurría en el siguiente flujo:

```
1. Fase 3 (Inflación - inflator.py:165-201):
   - Inflator calcula label_positions para TODOS los elementos
   - input.label_x = 0 + 80/2 = 40.0
   - Se almacena en layout.label_positions

2. Fase 4.5 (Redistribución + Centrado - laf_optimizer.py:258-406):
   - Se centra horizontalmente el ícono: input.x = 701.0
   - Se actualiza layout.label_positions[input] = (741.0, 75.0, ...)

3. Renderizado (generator.py:840-866):
   - Se encuentra elem_id en label_positions
   - Se marca como fixed=True (asumiendo que fue calculada por ContainerGrower)
   - LabelPositionOptimizer usa la posición pero no la recalcula
   - PROBLEMA: La posición actualizada en (2) no se usa correctamente
```

### Código Problemático

En `AlmaGag/layout/laf/inflator.py:175-201`:

```python
# Calcular posiciones para elementos con etiquetas
for elem in layout.elements:
    if not elem.get('label'):
        continue

    # ... código ...

    # PROBLEMA: Calcula para TODOS los elementos (primarios y contenidos)
    label_x = x + width / 2
    label_y = y - 5
    layout.label_positions[elem_id] = (label_x, label_y, 'middle', 'bottom')
```

## Solución Implementada

**Modificar `inflator.py` para que NO calcule `label_positions` para elementos primarios.**

### Razón

Los elementos primarios sufren transformaciones posteriores (centrado horizontal en Fase 4.5),
por lo que no deben tener `label_positions` precalculadas. El `LabelPositionOptimizer` las
calculará correctamente después de todas las transformaciones.

Solo los elementos **contenidos** (dentro de contenedores) necesitan que sus etiquetas se
calculen durante la fase de crecimiento de contenedores, ya que sus posiciones son relativas
al contenedor padre.

### Código Modificado

```python
def _calculate_label_positions(self, layout) -> None:
    """
    Calcula posiciones iniciales de etiquetas para contenedores.

    IMPORTANTE: NO calcular para elementos primarios, ya que sus posiciones
    se ajustarán durante el centrado horizontal en Fase 4.5 y el
    LabelPositionOptimizer las calculará correctamente después.
    """
    if not self.label_optimizer:
        return

    # Solo calcular posiciones para CONTENEDORES
    for elem in layout.elements:
        if not elem.get('label'):
            continue

        elem_id = elem['id']

        # Solo procesar contenedores con dimensiones ya calculadas
        if 'contains' in elem and 'width' in elem:
            x = elem.get('x', 0)
            y = elem.get('y', 0)
            width = elem.get('width', ICON_WIDTH)

            label_x = x + width / 2
            label_y = y - 5
            layout.label_positions[elem_id] = (label_x, label_y, 'middle', 'bottom')
```

## Verificación

### Comando de prueba
```bash
python -m AlmaGag.main docs/diagrams/gags/05-arquitectura-gag.gag \
  --layout-algorithm=laf --visualdebug --exportpng -o test-container-laf.svg
```

### Resultado
- Las etiquetas ahora aparecen correctamente centradas sobre sus íconos
- No hay separación horizontal entre etiquetas e íconos
- El centrado horizontal de Fase 4.5 funciona correctamente

## Archivos Modificados

- `AlmaGag/layout/laf/inflator.py` - Método `_calculate_label_positions()`

## Fecha

2026-01-22
