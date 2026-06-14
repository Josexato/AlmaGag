# Deuda Técnica - AlmaGag

Este documento registra problemas conocidos, limitaciones y áreas de mejora del proyecto AlmaGag.

**Última actualización**: 2026-01-21

---

## 🔴 Críticos

### LAF-001: Etiquetas de Debug Solapadas en Modo VisualDebug
**Componente**: `generator.py` - Renderizado SVG
**Severidad**: Media
**Reportado**: 2026-01-21

**Descripción**:
Las etiquetas naranjas de debug (que muestran el nivel topológico) en modo `--visualdebug` se solapan con elementos del diagrama, dificultando la lectura.

**Impacto**:
- Dificulta el debugging visual de diagramas complejos
- Las etiquetas pueden ocultar información importante de elementos

**Reproducción**:
```bash
almagag docs/diagrams/gags/05-arquitectura-gag.gag --layout-algorithm=laf --visualdebug --exportpng
```

**Solución Propuesta**:
- Calcular posición automática de etiquetas debug evitando colisiones con elementos
- Alternativamente, usar sistema de capas SVG para overlay con transparencia
- Considerar color de fondo semi-transparente para legibilidad

**Workaround Actual**:
Usar modo normal sin `--visualdebug` para diagramas finales.

---

### LAF-002: Cálculo Excesivo de Altura de Canvas
**Componente**: `AlmaGag/layout/laf/optimizer.py` - Fase 4.5
**Severidad**: Media
**Reportado**: 2026-01-21

**Descripción**:
El canvas final tiene altura excesiva con mucho espacio vacío en la parte inferior. La redistribución vertical calcula correctamente las posiciones Y de los elementos, pero el cálculo de altura total del canvas parece sobrestimado.

**Impacto**:
- Diagramas con ~50% de espacio vacío en la parte inferior
- Archivos SVG/PNG más grandes de lo necesario
- Mala utilización del espacio visual

**Datos**:
```
Canvas calculado: 1402x3807px
Altura utilizada real: ~2000px
Espacio desperdiciado: ~1800px (47%)
```

**Reproducción**:
```bash
almagag docs/diagrams/gags/05-arquitectura-gag.gag --layout-algorithm=laf --debug
```

**Análisis**:
- `container_grower.calculate_final_canvas()` en laf/optimizer.py:388-393
- Posiblemente incluye padding excesivo o calcula basándose en dimensiones intermedias

**Solución Propuesta**:
1. Revisar `calculate_final_canvas()` en ContainerGrower
2. Calcular altura basándose en elemento más bajo + margen (no multiplicadores)
3. Verificar que no se acumulen márgenes de diferentes fases

**Prioridad**: Media (funciona correctamente, solo optimización)

---

## 🟡 Medios

### LAF-003: Distribución Horizontal Asimétrica en Niveles Multi-Elemento
**Componente**: `AlmaGag/layout/laf/optimizer.py` - `_center_elements_horizontally()`
**Severidad**: Baja
**Reportado**: 2026-01-21

**Descripción**:
Aunque los niveles están centrados horizontalmente como conjunto, la distribución interna de elementos individuales puede ser asimétrica debido al uso de spacing fijo (480px).

**Impacto Visual**:
- Algunos elementos quedan muy separados mientras otros están más comprimidos
- El centrado grupal es correcto, pero visualmente puede parecer desbalanceado
- Especialmente notable en niveles con elementos de diferente ancho

**Ejemplo**:
```
Nivel 3: 3 elementos
  Ancho total: 1350.0px
  Canvas: 1402px
  Start X: 100.0px (margen mínimo aplicado)

  optimizer: X 480.0 -> 100.0 (dx=-380.0)
  laf_optimizer: X 960.0 -> 660.0 (dx=-300.0)
  analysis_module-stage: X 0.0 -> 1220.0 (dx=+1220.0)
```

**Solución Propuesta**:
1. Calcular spacing dinámico basado en espacio disponible:
   ```python
   available_space = canvas_width - total_elements_width - 2*MARGIN
   spacing = available_space / (num_elements - 1)
   ```
2. Limitar spacing máximo/mínimo para evitar separaciones extremas
3. Considerar distribución "justificada" para mejor simetría visual

**Prioridad**: Baja (estético, no afecta funcionalidad)

---

### LAF-004: Cruces de Conexiones No Optimizados
**Componente**: `AlmaGag/layout/laf/abstract_placer.py` - Fase 2
**Severidad**: Baja
**Reportado**: 2026-01-21

**Descripción**:
A pesar de implementar optimización de barycenter con conexiones del mismo nivel (peso 30%), aún se observan cruces de conexiones que podrían optimizarse.

**Datos Actuales**:
```
Diagrama: 05-arquitectura-gag.gag
Cruces calculados (Fase 2): 134
```

**Impacto**:
- Diagramas complejos son más difíciles de seguir visualmente
- Reduce claridad de flujos de datos/dependencias

**Análisis**:
La implementación actual usa:
- 70% peso para conexiones verticales (capa anterior)
- 30% peso para conexiones horizontales (mismo nivel)

Estos pesos pueden no ser óptimos para todos los tipos de diagramas.

**Solución Propuesta**:
1. **Ajuste dinámico de pesos**: Analizar proporción de conexiones vertical/horizontal y ajustar pesos automáticamente
2. **Múltiples iteraciones de barycenter**: Actualmente solo 1 pasada, considerar 3-5 iteraciones
3. **Post-procesamiento**: Fase adicional de "edge straightening" para minimizar ángulos
4. **Heurística por tipo de diagrama**: Diferentes pesos para arquitecturas vs flows

**Experimentos Sugeridos**:
```python
# Probar diferentes combinaciones
pesos = [
    (0.7, 0.3),  # Actual
    (0.6, 0.4),  # Más peso horizontal
    (0.5, 0.5),  # Balanceado
]
```

**Prioridad**: Baja (optimización incremental)

---

### LAF-007: Layout Pobre con Contenedores Hermanos sin Conexiones (caso "dashboard")
**Componente**: `AlmaGag/layout/laf/optimizer.py` - Fases 4-5-6 + Fase 8
**Severidad**: Media
**Reportado**: 2026-05-14 (auditoría externa)

**Descripción**:
Cuando hay 3+ contenedores en el mismo nivel sin conexiones explícitas entre ellos (típico de dashboards/posters), LAF los posiciona en fila horizontal y expande el canvas a >20.000 px de ancho.

**Reproducción**:
```bash
# JSON con 4 contenedores agrupando elementos, sin connections inter-contenedor
almagag dashboard.sdjf --layout-algorithm=laf
# Resultado: canvas ~20526 × 463 (rotamente horizontal)
```

**Workaround actual**:
Usar AUTO con coordenadas manuales en los contenedores padre. AUTO respeta `x`/`y` manuales y los hijos se auto-acomodan dentro de cada contenedor. Documentado en `architecture/modules/layout/auto/AUTO.md` (sección "Dashboard layout").

**Solución propuesta**:
Detectar "modo dashboard" (cluster de contenedores sin conexiones inter-cluster) y aplicar layout en grid 2x2, 2x3, o stack vertical según cantidad.

**Prioridad**: Media (afecta usabilidad de un caso de uso específico, no el caso principal de arquitecturas/flows).

---

### LAF-008: LAFOptimizer No Cumple el Contrato LayoutOptimizer
**Componente**: `AlmaGag/layout/laf/optimizer.py` + `AlmaGag/generator.py`
**Severidad**: Media-Alta
**Reportado**: 2026-05-14 (detectado durante refactor de routing_policy)

**Estado actual**:
- `AutoLayoutOptimizer` hereda de `LayoutOptimizer` (clase base en `optimizer_base.py`).
- `LAFOptimizer` no hereda de nadie y tiene firma de `__init__` distinta (recibe colaboradores por inyección).
- `generator.py` usa `if/elif layout_algorithm == ...` para distinguir (líneas ~578, ~625).
- `render_containers()` recibe `layout_algorithm` como parámetro.

**Impacto**:
- Acoplamiento entre algoritmo de layout y fases posteriores del pipeline.
- Imposible agregar un tercer algoritmo sin modificar `generator.py`.
- El Strategy Pattern documentado en `ARCHITECTURE.md` no se cumple en la práctica.
- Es la causa de la asimetría en `routing_policy.py` (AUTO autocontenido, LAF inyectado opcional).

**Solución propuesta**:
- Hacer que `LAFOptimizer` herede de `LayoutOptimizer`.
- Unificar firma `optimize(layout, **kwargs) -> Layout`.
- Eliminar `layout_algorithm` como parámetro propagado a `render_containers`.
- Cuando se resuelva, el constructor de `LAFRoutingPolicy` probablemente se uniformará con el de `AutoRoutingPolicy`.

**Prioridad**: Media-Alta (bloquea extensibilidad; no es bug funcional).

---

### LAF-009: No-Determinismo entre Procesos Python
**Componente**: `AlmaGag/layout/laf/` (causa raíz no investigada)
**Severidad**: Media
**Reportado**: 2026-05-14 (hallazgo lateral durante validación del refactor de routing_policy; no causado por el refactor)

**Descripción**:
LAF produce **distinto resultado** para el mismo input al ejecutarse en procesos Python separados. Determinista dentro del mismo proceso (corridas sucesivas en la misma sesión dan idéntico resultado). Reproducible en código pre-refactor (tag `pre-refactor-fase-1-3.1`).

**Síntoma observado**:
```bash
# Mismo archivo, 3 invocaciones de almagag (3 procesos Python distintos)
# Produce 2 hashes diferentes: 'database' y 'redis' pueden swapearse de posición.
```

**Hipótesis de causa raíz** (no investigada):
`PYTHONHASHSEED` randomization (default en Python 3) afecta el orden de iteración de `set`/`dict` en algún punto del pipeline LAF. Resultado: dos layouts igualmente válidos elegidos no-deterministicamente.

**Workaround temporal**:
```bash
PYTHONHASHSEED=0 almagag arch.sdjf --layout-algorithm=laf
```

**Impacto**:
- Baselines visuales inestables (regresiones falsas en CI/comparación de diffs).
- Difícil revisar PRs con cambios visuales sin fijar el seed.
- No afecta correctness — todos los layouts producidos son válidos.
- AUTO **no** presenta este problema.

**Solución propuesta**:
- Auditar puntos donde el pipeline LAF itera `set`/`dict` y usar `sorted()` con clave estable.
- Candidatos probables: `structure_analyzer.py`, `abstract_placer.py` (orderings).

**Prioridad**: Media (bloquea testing visual reproducible).

---

## 🟢 Mejoras Futuras

### LAF-005: Sistema de Etiquetas Inteligente
**Componente**: Label positioning
**Severidad**: Enhancement
**Reportado**: 2026-01-21

**Descripción**:
Las etiquetas actualmente se posicionan con reglas fijas. Un sistema inteligente podría:
- Detectar colisiones de etiquetas
- Ajustar posición automáticamente (arriba/abajo/laterales)
- Usar "leaders" (líneas guía) cuando es necesario separar etiqueta del elemento

**Beneficios**:
- Diagramas más limpios y profesionales
- Menos intervención manual del usuario
- Mejor densidad de información

**Referencias**:
- Graphviz label placement algorithms
- D3.js force-directed label positioning

---

### LAF-006: Soporte para Restricciones de Posicionamiento
**Componente**: LAF - Fase 2 (Abstract Placement)
**Severidad**: Enhancement
**Reportado**: 2026-01-21

**Descripción**:
Permitir al usuario especificar restricciones de posicionamiento:
```json
{
  "elements": [
    {
      "id": "database",
      "type": "database",
      "constraints": {
        "align": "bottom",
        "near": ["api", "cache"],
        "avoid": ["frontend"]
      }
    }
  ]
}
```

**Beneficios**:
- Mayor control sobre layout final
- Preservar convenciones de arquitectura (ej: DB siempre abajo)
- Respetar agrupamientos semánticos

**Implementación**:
- Extender StructureInfo con constraints
- Modificar barycenter calculation para incluir constraint weights
- Validar constraints no conflictivas

---

## 📊 Métricas de Calidad

### Cobertura de Problemas Conocidos

| Componente | Problemas Críticos | Problemas Medios | Mejoras Futuras |
|------------|-------------------|------------------|-----------------|
| LAF Optimizer | 2 | 5 | 2 |
| Abstract Placer | 0 | 1 | 0 |
| Rendering | 1 | 0 | 1 |
| **TOTAL** | **3** | **6** | **3** |

> Conteo actualizado tras el refactor de Fase 1+3.1 (2026-05-14): se agregaron
> LAF-007 (dashboard layout), LAF-008 (contrato LayoutOptimizer) y LAF-009
> (no-determinismo entre procesos) a la categoría Medios.

### Priorización

**Sprint Próximo (Alta Prioridad)**:
- ❌ Ninguno (todos son media/baja prioridad)

**Backlog (Media Prioridad)**:
- LAF-002: Cálculo de altura de canvas
- LAF-001: Etiquetas debug solapadas

**Mejoras Futuras (Baja Prioridad)**:
- LAF-003: Distribución horizontal asimétrica
- LAF-004: Optimización de cruces
- LAF-005: Sistema de etiquetas inteligente
- LAF-006: Restricciones de posicionamiento

---

## 🔄 Historial de Cambios

### 2026-01-21
- **Documento creado** con 6 issues identificados
- Categorización: 3 críticos/medios, 3 mejoras futuras
- Añadido contexto de implementación de mejoras LAF (centrado horizontal + barycenter intra-nivel)

---

## 📝 Notas para Desarrolladores

### Cómo Reportar Nueva Deuda Técnica

1. Crear entrada en la sección correspondiente (Críticos/Medios/Mejoras)
2. Usar formato:
   ```markdown
   ### COMPONENTE-NNN: Título Descriptivo
   **Componente**: Archivo/módulo afectado
   **Severidad**: Crítica/Media/Baja
   **Reportado**: YYYY-MM-DD

   **Descripción**: ...
   **Impacto**: ...
   **Reproducción**: ...
   **Solución Propuesta**: ...
   ```
3. Actualizar métricas de calidad
4. Actualizar historial de cambios

### Criterios de Severidad

- **Crítica**: Bloquea funcionalidad core, datos incorrectos, crashes
- **Media**: Afecta UX/calidad pero hay workaround, optimizaciones importantes
- **Baja**: Mejoras estéticas, optimizaciones menores, edge cases

---

## 🔗 Enlaces Relacionados

- [LAF Progress](./architecture/modules/layout/laf/PROGRESS.md) - Estado de implementación de sistema LAF
- [LAF Comparison](./architecture/modules/layout/laf/COMPARISON.md) - Comparativa LAF vs AUTO
- [Release Notes v3.0.0](./RELEASE_v3.0.0.md) - Changelog oficial
