# Estrategia de Agrupación de Contenedores en Auto-Layout

**Versión**: v2.2
**Fecha**: 2026-01-09
**Problema**: Los contenedores se solapan masivamente en auto-layout

---

## Problema Actual

El auto-layout posiciona elementos sin considerar que algunos pertenecen al mismo contenedor:

```
Flujo actual:
1. Posicionar elementos → distribución libre, sin agrupar
2. Calcular contenedores → se adaptan a posiciones dispersas
3. Resultado: Contenedores ENORMES y superpuestos
```

**Ejemplo real del diagrama de arquitectura:**
- `analysis_container` con 3 elementos: 779px de alto (se extiende por todo el canvas)
- `draw_container` con 4 elementos: se solapa con analysis_container
- Los elementos internos están dispersos por todo el diagrama

---

## Solución Propuesta: Container-Aware Layout

### Estrategia de Agrupación

**Principio**: Elementos del mismo contenedor deben posicionarse **juntos y compactos**.

```
Flujo mejorado:
1. Identificar grupos (elementos por contenedor)
2. Posicionar cada grupo de forma compacta
3. Dejar espacio entre grupos diferentes
4. Calcular contenedores → se adaptan a grupos compactos
5. Resultado: Contenedores bien definidos, sin solapamiento
```

---

## Implementación Técnica

### 1. Detección de Grupos

```python
def _group_elements_by_container(self, layout):
    """
    Agrupa elementos por contenedor.

    Returns:
        {
            'container_id': ['elem1', 'elem2', 'elem3'],
            None: ['elem4', 'elem5']  # elementos sin contenedor
        }
    """
    groups = {None: []}  # elementos libres

    for elem in layout.elements:
        if 'contains' in elem:
            # Este es un contenedor
            groups[elem['id']] = elem['contains']
        elif not self._is_element_in_any_container(elem, layout):
            # Elemento libre (no está en ningún contenedor)
            groups[None].append(elem['id'])

    return groups
```

### 2. Posicionamiento por Grupos

**Estrategia de Layout para cada grupo:**

```python
# Para cada grupo de contenedor:
# 1. Calcular tamaño del grupo (número de elementos)
# 2. Determinar layout interno:
#    - Si <= 3 elementos: vertical (columna)
#    - Si 4-6 elementos: grid 2x3
#    - Si 7-9 elementos: grid 3x3
#    - Si > 9: grid dinámico

# 3. Posicionar elementos del grupo en formación compacta
# 4. Dejar MARGEN entre grupos (ej: 200px)
```

**Configuración de márgenes:**
```python
CONTAINER_SPACING = 200  # Espacio entre contenedores
ELEMENT_SPACING_IN_CONTAINER = 120  # Espacio entre elementos del mismo contenedor
ELEMENT_SPACING_FREE = 150  # Espacio entre elementos libres
```

### 3. Cálculo de Posiciones por Grupo

```python
def _position_container_group(self, container_id, element_ids, layout, start_x, start_y):
    """
    Posiciona elementos de un contenedor de forma compacta.

    Args:
        container_id: ID del contenedor
        element_ids: Lista de IDs de elementos en el contenedor
        layout: Layout actual
        start_x, start_y: Posición inicial del grupo

    Returns:
        (next_x, next_y): Siguiente posición disponible después del grupo
    """
    num_elements = len(element_ids)

    # Determinar configuración de grid
    if num_elements <= 3:
        cols = 1
        rows = num_elements
    elif num_elements <= 6:
        cols = 2
        rows = (num_elements + 1) // 2
    elif num_elements <= 9:
        cols = 3
        rows = (num_elements + 2) // 3
    else:
        cols = 4
        rows = (num_elements + 3) // 4

    # Posicionar elementos en grid
    for i, elem_id in enumerate(element_ids):
        row = i // cols
        col = i % cols

        elem = layout.elements_by_id[elem_id]
        elem['x'] = start_x + (col * ELEMENT_SPACING_IN_CONTAINER)
        elem['y'] = start_y + (row * ELEMENT_SPACING_IN_CONTAINER)

    # Calcular siguiente posición disponible
    group_width = cols * ELEMENT_SPACING_IN_CONTAINER
    group_height = rows * ELEMENT_SPACING_IN_CONTAINER

    return (start_x + group_width + CONTAINER_SPACING, start_y)
```

### 4. Orden de Posicionamiento

**Prioridad de grupos:**
1. Elementos con coordenadas explícitas (skip)
2. Contenedores por orden de aparición en JSON
3. Elementos libres al final

```python
def calculate_missing_positions(self, layout):
    # 1. Identificar grupos
    groups = self._group_elements_by_container(layout)

    # 2. Posicionar grupos de contenedores
    current_x = 100
    current_y = 100

    for container_id, element_ids in groups.items():
        if container_id is None:
            continue  # elementos libres después

        # Posicionar grupo de contenedor
        current_x, current_y = self._position_container_group(
            container_id, element_ids, layout, current_x, current_y
        )

    # 3. Posicionar elementos libres
    if groups[None]:
        self._position_free_elements(groups[None], layout, current_x, current_y)
```

---

## Ejemplo Visual

### Antes (auto-layout sin agrupación):
```
┌────────────────────────────────────────────────┐
│  elem1 (análisis)                             │
│           elem4 (draw)                         │
│  elem2 (análisis)      elem5 (draw)           │
│                 elem6 (routing)                │
│  elem3 (análisis)                             │
│           elem7 (routing)                      │
│  elem8 (draw)          elem9 (draw)           │
└────────────────────────────────────────────────┘

Contenedores calculados:
- analysis_container: abarca todo (elem1, elem2, elem3 dispersos)
- draw_container: abarca todo (elem4, elem5, elem8, elem9 dispersos)
- SOLAPAMIENTO MASIVO
```

### Después (auto-layout con agrupación):
```
┌───────────────┐     ┌───────────────┐     ┌───────────────┐
│ ANÁLISIS      │     │ DRAW          │     │ ROUTING       │
│               │     │               │     │               │
│ elem1         │     │ elem4  elem5  │     │ elem6         │
│ elem2         │     │ elem8  elem9  │     │ elem7         │
│ elem3         │     │               │     │               │
└───────────────┘     └───────────────┘     └───────────────┘
  (compacto)            (compacto)            (compacto)

ESPACIO entre contenedores: 200px
- Contenedores bien definidos
- Sin solapamiento
- Agrupación visual clara
```

---

## Casos Especiales

### 1. Contenedores Anidados
```python
# Contenedor dentro de contenedor
# Prioridad: posicionar contenedor padre primero
# Contenido del hijo se posiciona relativo al padre
```

### 2. Elementos con Coordenadas Parciales
```python
# Si elemento tiene x o y explícita, respetar
# Solo calcular la coordenada faltante
```

### 3. Contenedores Vacíos
```python
# Contenedor sin elementos
# Usar dimensiones por defecto (200x150)
```

---

## Beneficios

1. ✅ **Contenedores Compactos**: Tamaño razonable, no gigantes
2. ✅ **Sin Solapamiento**: Espaciado adecuado entre grupos
3. ✅ **Agrupación Visual**: Elementos relacionados están juntos
4. ✅ **Legibilidad**: Diagramas más claros y organizados
5. ✅ **Automático**: Sin necesidad de coordenadas manuales

---

## Testing

### Test Case 1: Diagrama de Arquitectura
- 4 contenedores (layout, routing, analysis, draw)
- 3-4 elementos por contenedor
- **Esperado**: 4 grupos compactos y separados

### Test Case 2: Contenedor + Elementos Libres
- 1 contenedor con 3 elementos
- 2 elementos libres
- **Esperado**: Grupo compacto + elementos libres separados

### Test Case 3: Solo Elementos Libres
- 10 elementos sin contenedor
- **Esperado**: Comportamiento actual (layout basado en grafo)

---

## Próximos Pasos

1. ✅ Documentar estrategia
2. ⏳ Implementar `_group_elements_by_container()`
3. ⏳ Implementar `_position_container_group()`
4. ⏳ Modificar `calculate_missing_positions()` para usar grupos
5. ⏳ Testing con diagrama de arquitectura
6. ⏳ Ajustar márgenes si es necesario

---

**Estado**: 📋 Diseño completo - Listo para implementar
