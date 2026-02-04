# Implementación Barycenter Bidireccional para Minimizar Cruces

## Objetivo

Posicionar `analysis_module-stage` EN EL MEDIO entre `optimizer` y `laf_optimizer` para minimizar cruces de conectores.

## Problema Actual

### Orden Actual
```
Nivel 4: laf_optimizer -> optimizer -> analysis_module-stage
```

### Orden Deseado
```
Nivel 4: optimizer -> analysis_module-stage -> laf_optimizer
```

### Por Qué Es Mejor
- `optimizer` y `laf_optimizer` se conectan a `geometry`, `graph`, `collision` (hijos de `analysis_module-stage`)
- Si el contenedor está en el medio, las conexiones desde ambos lados no se cruzan tanto
- Cruces estimados: ~19 con orden actual

## Implementación

### 1. Barycenter Bidireccional con Iteraciones

**Archivo:** `AlmaGag/layout/laf/abstract_placer.py`

```python
def _order_within_layers(self, layers, structure_info, layout):
    iterations = 4  # Múltiples pasadas

    for iteration in range(iterations):
        # Forward pass: considerar capa anterior
        for layer_idx in range(1, len(layers)):
            self._order_layer_barycenter_forward(...)

        # Backward pass: considerar capa siguiente
        for layer_idx in range(len(layers) - 2, 0, -1):
            self._order_layer_barycenter_backward(...)
```

### 2. Barycenter Especial para Contenedores

**Problema:** Las conexiones desde `optimizer`/`laf_optimizer` hacia los hijos de `analysis_module-stage` son del MISMO NIVEL, no de capas anterior/siguiente.

**Solución:** Calcular barycenter del contenedor basándose en conexiones entrantes a sus hijos desde el mismo nivel.

```python
def _calculate_container_barycenter(self, container_id, current_layer, source_barycenters, ...):
    # Encontrar conexiones HACIA los hijos del contenedor
    for conn in layout.connections:
        if to_id in children:  # Si apunta a un hijo
            if from_primary_id in source_barycenters:
                # Usar BARYCENTER de la fuente, no su posición actual
                source_barycenter_values.append(source_barycenters[from_primary_id])

    return sum(source_barycenter_values) / len(source_barycenter_values)
```

## Estado Actual

### Barycenters Calculados (Última Iteración)

```
Nivel 4:
  - optimizer: 1.00
  - laf_optimizer: 1.00
  - analysis_module-stage: 1.00 (promedio de fuentes)

Orden final: analysis_module-stage -> laf_optimizer -> optimizer
```

### Problema Identificado

**Los tres elementos tienen el mismo barycenter (1.00)**, por lo que el sort no puede diferenciarlos.

#### ¿Por qué todos tienen 1.00?

1. **Forward pass:**
   - `layout_module-stage` (nivel 3, posición 1) conecta a `optimizer` y `laf_optimizer`
   - Ambos reciben barycenter = 1.00

2. **Barycenter del contenedor:**
   - `analysis_module-stage` calcula promedio de barycenters de fuentes:
   - Fuentes: `optimizer` (1.00) y `laf_optimizer` (1.00)
   - Promedio: (1.00 + 1.00 + 1.00 + 1.00 + 1.00) / 5 = 1.00

3. **Backward pass:**
   - No está diferenciando a `optimizer` y `laf_optimizer` basándose en sus destinos

## Solución Propuesta

### Opción 1: Usar Tipo de Elemento como Segundo Criterio

Modificar el sort key para usar tipo después del barycenter:

```python
def get_sort_key(elem_id: str) -> Tuple[float, str, str]:
    barycenter = barycenters.get(elem_id, ...)
    elem_type = ...  # 'container', 'element', etc.
    return (barycenter, elem_type, elem_id)
```

**Problema:** No garantiza que el contenedor quede en el medio.

### Opción 2: Ajustar Barycenter de Contenedores con Peso

Dar más peso al barycenter de contenedores para que se "atraiga" hacia el centro:

```python
if container_node and container_node['is_container']:
    # Mezclar con posición central
    barycenter = barycenter * 0.7 + (len(current_layer) / 2) * 0.3
```

### Opción 3: Penalizar Cruces Directamente

Calcular cruces para cada permutación posible y elegir la mejor:

```python
best_order = None
min_crossings = float('inf')

for permutation in permutations(current_layer):
    crossings = count_crossings(permutation, layout.connections)
    if crossings < min_crossings:
        min_crossings = crossings
        best_order = permutation
```

**Problema:** Costoso computacionalmente para capas grandes.

### Opción 4: Backward Pass Más Agresivo

El backward pass debería diferenciar a `optimizer` y `laf_optimizer`:

- `optimizer` conecta a: `geometry`, `graph`, `collision`, `render`, `label_position_optimizer` (posiciones en nivel 5-6)
- `laf_optimizer` conecta a: `geometry`, `graph`, `structure_analyzer`, `render`, `label_position_optimizer` (posiciones en nivel 5-6)

Si sus destinos están en posiciones diferentes, sus barycenters backward deberían ser diferentes.

## Recomendación

Implementar **Opción 4** primero (backward pass más efectivo), y si no funciona, usar **Opción 2** (peso hacia el centro para contenedores).

## Fecha

2026-01-22
