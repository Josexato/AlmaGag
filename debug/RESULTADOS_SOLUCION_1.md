# Resultados: Solución 1 - División de Franjas en Sub-Franjas

**Fecha**: 2026-01-16
**Archivo**: docs/diagrams/gags/05-arquitectura-gag.gag
**Implementación**: `AlmaGag/layout/auto_positioner.py:1133-1149`

---

## ✅ Solución Implementada

Se modificó el método `_position_free_elements_by_topology()` para dividir una franja libre única en sub-franjas verticales cuando hay múltiples niveles topológicos.

### Código Agregado

```python
# OPTIMIZACIÓN: Si solo hay 1 franja pero múltiples niveles,
# dividir la franja en sub-franjas verticales (una por nivel)
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

    logger.debug(f"    Dividiendo franja libre [{y_start:.1f} - {y_end:.1f}] en {num_levels} sub-franjas verticales")
    logger.debug(f"    Altura por sub-franja: {level_height:.1f}px")
    free_ranges = sub_franjas
```

---

## 📊 Comparación: Antes vs. Después

### ANTES (con problema)

**Distribución de elementos:**
```
Y = 719.5 (7 elementos TODOS EN LA MISMA FRANJA)
  X=  520.0: input        (Nivel 0)
  X=  600.0: main         (Nivel 1)
  X=  640.0: optimizer    (Nivel 0)  ← OVERLAP con main
  X=  700.0: generator    (Nivel 2)  ← OVERLAP TOTAL
  X=  700.0: svgwrite     (Nivel 3)  ← OVERLAP TOTAL
  X=  720.0: render       (Nivel 1)  ← OVERLAP con generator/svgwrite
  X=  800.0: output       (Nivel 0)
```

**Problemas:**
- ❌ Todos en Y=719.5 (sin separación vertical)
- ❌ generator y svgwrite en (700.0, 719.5) - solapamiento 100%
- ❌ 6 colisiones de iconos
- ❌ Jerarquía topológica invisible

**Colisiones:**
- Iniciales: 127
- Finales: **86**
- Colisiones de iconos: **6**

---

### DESPUÉS (con solución)

**División de franja:**
```
Franja original: [329.0 - 1050.0] (altura: 721.0px)
  ↓
4 sub-franjas de 180.2px cada una:
  Sub-franja 1: [329.0 - 509.2]
  Sub-franja 2: [509.2 - 689.4]
  Sub-franja 3: [689.4 - 869.6]
  Sub-franja 4: [869.6 - 1050.0]
```

**Distribución de elementos:**
```
Y = 419.1 (Nivel 0 - 3 elementos)
  X=  520.0: input
  X=  640.0: optimizer
  X=  800.0: output

Y = 599.4 (Nivel 1 - 2 elementos)
  X=  600.0: main
  X=  720.0: render

Y = 779.6 (Nivel 2 - 1 elemento)
  X=  700.0: generator

Y = 959.9 (Nivel 3 - 1 elemento)
  X=  700.0: svgwrite
```

**Mejoras:**
- ✅ Elementos distribuidos en 4 niveles verticales
- ✅ Separación vertical de ~180px entre niveles
- ✅ 0 colisiones de iconos
- ✅ Jerarquía topológica VISIBLE
- ✅ generator y svgwrite ahora separados 180px verticalmente

**Colisiones:**
- Iniciales: 101
- Finales: **69**
- Colisiones de iconos: **0**

---

## 📈 Impacto de la Solución

### Reducción de Colisiones

| Métrica | Antes | Después | Mejora |
|---------|-------|---------|--------|
| **Colisiones finales** | 86 | 69 | **-17 (-20%)** |
| **Colisiones de iconos** | 6 | 0 | **-6 (-100%)** |
| **Solapamientos totales** | 1 | 0 | **-1 (-100%)** |
| **Elementos en misma Y** | 7 | 3 (máx) | **-4 (-57%)** |

### Distribución Vertical

| Nivel | Elementos | Y (antes) | Y (después) | Separación |
|-------|-----------|-----------|-------------|------------|
| 0 | 3 | 719.5 | 419.1 | - |
| 1 | 2 | 719.5 | 599.4 | 180.3px |
| 2 | 1 | 719.5 | 779.6 | 180.2px |
| 3 | 1 | 719.5 | 959.9 | 180.3px |

**Separación promedio entre niveles**: 180.2px

---

## 🎯 Colisiones Restantes (69)

### Desglose:
- **Contenedor-hijo**: 12 (esperadas, NO deberían contar)
- **Colisiones de iconos**: 0 ✅
- **Colisiones de etiquetas**: ~57 (estimadas)

### Análisis:
Las 69 colisiones restantes se deben principalmente a:
1. **Etiquetas de elementos** (~23 elementos)
2. **Etiquetas de conexiones** (~25 conexiones)
3. **Overlap etiqueta-línea**

Las colisiones contenedor-hijo (12) se resolverán con la **Solución 2** (pendiente).

---

## 🔧 Ajustes Técnicos Realizados

### Canvas Expandido
- Antes: 1479.0 x 1100
- Después: 1479.0 x **1129.875**
- Expansión vertical: +29.875px (automática)

### Posicionamiento
- Todos los contenedores movidos hacia arriba (Y=80 → Y=20)
- Espacio superior liberado para sub-franjas

---

## ✅ Verificación Visual

### Elementos Críticos Resueltos:

1. **generator (Nivel 2)**:
   - Antes: (700.0, 719.5) - solapado con svgwrite
   - Después: (700.0, 779.6) - separado

2. **svgwrite (Nivel 3)**:
   - Antes: (700.0, 719.5) - solapado con generator
   - Después: (700.0, 959.9) - separado

3. **optimizer (Nivel 0)**:
   - Antes: (640.0, 719.5) - overlap con main
   - Después: (640.0, 419.1) - separado

4. **main (Nivel 1)**:
   - Antes: (600.0, 719.5) - overlap con optimizer
   - Después: (600.0, 599.4) - separado

---

## 🚀 Próximos Pasos

### Solución 2: Excluir Colisiones Contenedor-Hijo (pendiente)

Implementar en `AlmaGag/analysis/collision.py` para excluir las 12 colisiones contenedor-hijo del conteo.

**Impacto esperado**:
- Colisiones reportadas: 69 → **57**
- Colisiones reales de iconos: 0 (ya resuelto)
- Métricas más precisas

### Optimización de Etiquetas (opcional)

Si las ~57 colisiones de etiquetas son problemáticas:
- Ajustar `label_optimizer.py`
- Incrementar penalizaciones
- Considerar posiciones alternativas

---

## 📝 Conclusión

La **Solución 1** ha sido exitosa:
- ✅ Solapamiento total eliminado (generator/svgwrite)
- ✅ Colisiones de iconos reducidas a 0
- ✅ Jerarquía topológica visible
- ✅ Distribución vertical correcta
- ✅ 20% de reducción en colisiones totales

El diagrama `05-arquitectura-gag.svg` ahora tiene **0 colisiones de iconos** y una estructura jerárquica clara y legible.

---

**Archivos Modificados:**
- `AlmaGag/layout/auto_positioner.py` (líneas 1133-1149)

**Archivos Generados:**
- `docs/diagrams/svgs/05-arquitectura-gag.svg` (actualizado)
- `debug/outputs/05-arquitectura-gag.png` (actualizado)
- `debug/iterations/05-arquitectura-gag_iterations_20260116_004946.json`
- `debug/test_solucion_subfranjas.txt`
