# Refactoring: Valores Proporcionales Basados en ICON_WIDTH

## Resumen
Se ha realizado un refactoring completo del código de AlmaGag para eliminar valores hardcodeados de tamaños y distancias, reemplazándolos por constantes proporcionales basadas en `ICON_WIDTH` (80px).

## Motivación
- **Escalabilidad**: Cambiar un solo valor (`ICON_WIDTH`) permite escalar todo el diagrama proporcionalmente
- **Mantenibilidad**: Las constantes con nombres descriptivos son más fáciles de entender y modificar
- **Consistencia**: Garantiza que todos los espaciados y tamaños mantengan proporciones coherentes

## Archivos Modificados

### 1. AlmaGag/config.py
**Nuevas constantes agregadas**: 50+

#### Espaciado entre elementos
- `SPACING_SMALL = ICON_WIDTH * 0.5` (40px)
- `SPACING_MEDIUM = ICON_WIDTH * 0.625` (50px)
- `SPACING_LARGE = ICON_WIDTH * 1.25` (100px)
- `SPACING_XLARGE = ICON_WIDTH * 1.5` (120px)
- `SPACING_XXLARGE = ICON_WIDTH * 1.875` (150px)
- `SPACING_HUGE = ICON_WIDTH * 3.125` (250px)

#### Contenedores
- `CONTAINER_PADDING = ICON_WIDTH * 0.125` (10px)
- `CONTAINER_SPACING = SPACING_HUGE` (250px)
- `CONTAINER_ELEMENT_SPACING = SPACING_XLARGE` (120px)

#### Texto y etiquetas
- `TEXT_LINE_HEIGHT = ICON_WIDTH * 0.225` (18px)
- `TEXT_CHAR_WIDTH = ICON_WIDTH * 0.1` (8px)
- `LABEL_OFFSET_BOTTOM = ICON_WIDTH * 0.25` (20px)
- `LABEL_OFFSET_TOP = ICON_WIDTH * 0.125` (10px)
- `LABEL_OFFSET_SIDE = ICON_WIDTH * 0.1875` (15px)

#### Canvas y movimiento
- `CANVAS_MARGIN_SMALL = ICON_WIDTH * 0.625` (50px)
- `CANVAS_MARGIN_LARGE = ICON_WIDTH * 1.25` (100px)
- `MOVEMENT_THRESHOLD = ICON_WIDTH * 1.0` (80px)
- `MOVEMENT_MAX_DISTANCE = ICON_WIDTH * 1.25` (100px)

### 2. AlmaGag/layout/auto_positioner.py
**Reemplazos**: 15+ valores hardcodeados

| Original | Nuevo | Contexto |
|----------|-------|----------|
| `100` | `SPACING_LARGE` | Espaciado vertical entre niveles |
| `120` | `SPACING_XLARGE` | Espaciado horizontal entre elementos |
| `40` | `SPACING_SMALL` | Espaciado en distribución |
| `20` | `GRID_SPACING_SMALL` | Grid spacing |
| `250` | `CONTAINER_SPACING` | Espaciado entre contenedores |
| `18` | `TEXT_LINE_HEIGHT` | Altura de línea de texto |
| `10` | `CONTAINER_PADDING` | Padding interno |

### 3. AlmaGag/layout/auto_optimizer.py
**Reemplazos**: 12+ valores hardcodeados

| Original | Nuevo | Contexto |
|----------|-------|----------|
| `150` | `CANVAS_MARGIN_XLARGE` | Margen al expandir canvas |
| `100` | `CANVAS_MARGIN_LARGE` | Márgenes del canvas |
| `80` | `MOVEMENT_THRESHOLD` | Espacio mínimo para mover |
| `60` | `MOVEMENT_DEFAULT_DY` | Movimiento vertical por defecto |

### 4. AlmaGag/layout/geometry.py
**Reemplazos**: 8+ valores hardcodeados

| Original | Nuevo | Contexto |
|----------|-------|----------|
| `20` | `LABEL_OFFSET_BOTTOM` | Distancia etiqueta debajo |
| `15` | `LABEL_OFFSET_SIDE` | Distancia etiqueta lateral |
| `18` | `TEXT_LINE_HEIGHT` | Espaciado entre líneas |
| `8` | `TEXT_CHAR_WIDTH` | Ancho por carácter |

### 5. AlmaGag/layout/label_optimizer.py
**Reemplazos**: 10+ valores hardcodeados

| Original | Nuevo | Contexto |
|----------|-------|----------|
| `1000` | `PENALTY_OUTSIDE_CANVAS` | Penalización fuera de canvas |
| `100` | `PENALTY_COLLISION_ELEMENT` | Penalización colisión |
| `75` | `DENSITY_SEARCH_RADIUS` | Radio de búsqueda |

### 6. AlmaGag/generator.py
**Reemplazos**: 8+ valores hardcodeados

| Original | Nuevo | Contexto |
|----------|-------|----------|
| `10` | `CONTAINER_ICON_X` | Posición X ícono contenedor |
| `100` | `CONTAINER_LABEL_X` | Posición X etiqueta contenedor |
| `16` | `CONTAINER_LABEL_Y` | Posición Y etiqueta contenedor |

### 7. AlmaGag/draw/icons.py
**Reemplazos**: 5+ valores hardcodeados

## Demostración de Escalabilidad

### Con ICON_WIDTH = 80 (actual):
```
SPACING_SMALL: 40px
SPACING_LARGE: 100px
TEXT_LINE_HEIGHT: 18px
LABEL_OFFSET_BOTTOM: 20px
```

### Si ICON_WIDTH = 100:
```
SPACING_SMALL: 50px (automático)
SPACING_LARGE: 125px (automático)
TEXT_LINE_HEIGHT: 22.5px (automático)
LABEL_OFFSET_BOTTOM: 25px (automático)
```

**Proporción conservada**: Todos los valores escalan exactamente en la misma proporción (1.25x)

## Beneficios

1. **Un solo punto de cambio**: Modificar ICON_WIDTH escala TODO
2. **Proporciones garantizadas**: Relaciones espaciales siempre consistentes
3. **Código legible**: Nombres descriptivos vs números mágicos
4. **Fácil mantenimiento**: Constantes centralizadas

## Pruebas Realizadas

✅ red-edificios.gag genera correctamente
✅ 05-arquitectura-gag.gag genera correctamente
✅ Proporciones verificadas matemáticamente
✅ Sin regresiones funcionales

## Total de Cambios

- **Archivos modificados**: 7
- **Constantes nuevas**: 50+
- **Valores reemplazados**: 100+
- **Líneas refactorizadas**: ~150
