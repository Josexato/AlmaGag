# Feature: Barycenter Bidireccional con Hub Container Positioning

## Objetivo

Minimizar cruces de conectores en diagramas LAF mediante un algoritmo de barycenter bidireccional que posiciona contenedores "hub" (con múltiples fuentes de conexión) en el centro de su nivel.

## Problema Resuelto

### Caso: Diagrama de Arquitectura 05-arquitectura-gag.gag

**Antes:**
- Nivel 4: `optimizer` - `laf_optimizer` - `analysis_module-stage`
- `analysis_module-stage` contiene `geometry`, `graph`, `collision`
- Tanto `optimizer` como `laf_optimizer` se conectan a estos elementos contenidos
- Cruces estimados: ~19

**Después:**
- Nivel 4: `optimizer` - `analysis_module-stage` - `laf_optimizer` (o variantes)
- El contenedor está en el **CENTRO** (posición 1 de 3)
- Los cruces se minimizan porque las conexiones desde ambos lados no se cruzan tanto

## Implementación

### 1. Barycenter Bidireccional con Múltiples Iteraciones

**Archivo:** `AlmaGag/layout/laf/abstract_placer.py:126-180`

```python
def _order_within_layers(self, layers, structure_info, layout):
    iterations = 4  # Múltiples pasadas para convergencia

    for iteration in range(iterations):
        # Forward pass: barycenter basado en capa anterior
        for layer_idx in range(1, len(layers)):
            self._order_layer_barycenter_forward(...)

        # Backward pass: barycenter basado en capa siguiente
        for layer_idx in range(len(layers) - 2, 0, -1):
            self._order_layer_barycenter_backward(...)
```

### 2. Barycenter Especial para Contenedores

**Archivo:** `AlmaGag/layout/laf/abstract_placer.py:322-381`

Los contenedores calculan su barycenter considerando conexiones **entrantes a sus hijos** desde elementos del mismo nivel:

```python
def _calculate_container_barycenter(self, container_id, ..., source_barycenters, ...):
    # Encontrar elementos que se conectan a los hijos
    for conn in layout.connections:
        if to_id in children:  # Conexión a hijo
            if from_primary_id in source_barycenters:
                # Usar BARYCENTER de la fuente
                source_barycenter_values.append(source_barycenters[from_primary_id])

    avg_barycenter = sum(source_barycenter_values) / len(source_barycenter_values)
    center_position = (len(current_layer) - 1) / 2.0

    # Mezclar: 50% fuentes, 50% centro
    return avg_barycenter * 0.5 + center_position * 0.5
```

### 3. Hub Container Positioning (Post-Procesamiento)

**Archivo:** `AlmaGag/layout/laf/abstract_placer.py:285-320`

Después del ordenamiento por barycenter, detecta contenedores "hub" y los mueve explícitamente al centro:

```python
def _position_hub_containers_in_center(self, current_layer, structure_info, layout):
    for elem_id in current_layer:
        # Verificar si es contenedor con múltiples fuentes
        container_node = structure_info.element_tree.get(elem_id)
        if not (container_node and container_node['is_container']):
            continue

        # Contar fuentes únicas desde el mismo nivel
        sources = set()
        for conn in layout.connections:
            if to_id in children and from_primary_id in current_layer:
                sources.add(from_primary_id)

        # Si tiene 2+ fuentes, moverlo al centro
        if len(sources) >= 2:
            current_idx = current_layer.index(elem_id)
            center_idx = len(current_layer) // 2
            current_layer.pop(current_idx)
            current_layer.insert(center_idx, elem_id)
```

## Resultado

### Output del Debug

```
[HUB] analysis_module-stage: 2 fuentes -> movido a centro (pos 1)
Orden final: optimizer -> analysis_module-stage -> laf_optimizer
```

O alternativamente:

```
[HUB] analysis_module-stage: 2 fuentes -> movido a centro (pos 1)
Orden final: laf_optimizer -> analysis_module-stage -> optimizer
```

En ambos casos, el contenedor queda en la **posición central (1 de 3)**.

### Beneficios

1. **Reducción de cruces:** Contenedores hub en el centro minimizan cruces de conexiones desde múltiples fuentes
2. **Mejora visual:** Diagramas más legibles con conexiones menos enredadas
3. **Escalable:** Funciona para cualquier contenedor con múltiples fuentes de conexión

## Archivos Modificados

1. **`AlmaGag/layout/laf/abstract_placer.py`**
   - Método `_order_within_layers()`: Barycenter bidireccional con iteraciones
   - Método `_order_layer_barycenter_forward()`: Dos pasadas (elementos + contenedores)
   - Método `_calculate_container_barycenter()`: Barycenter especial para contenedores
   - Método `_position_hub_containers_in_center()`: Post-procesamiento de hubs
   - Método `_calculate_barycenter_backward()`: Barycenter basado en capa siguiente

## Casos de Uso

Esta feature se activa automáticamente cuando:
1. Un nivel tiene 3+ elementos
2. Uno de ellos es un contenedor
3. El contenedor recibe conexiones desde 2+ elementos del mismo nivel

## Fecha

2026-01-22
