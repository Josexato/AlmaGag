# Referencia Completa CLI - AlmaGag v3.0

Esta guía documenta todas las opciones de línea de comandos disponibles en AlmaGag v3.0.

## Tabla de Contenidos

- [Sintaxis Básica](#sintaxis-básica)
- [Opciones de Layout](#opciones-de-layout)
- [Opciones de Debug](#opciones-de-debug)
- [Opciones de Exportación](#opciones-de-exportación)
- [Opciones de Visualización](#opciones-de-visualización)
- [Combinaciones Comunes](#combinaciones-comunes)
- [Troubleshooting](#troubleshooting)

## Sintaxis Básica

```bash
almagag <archivo.gag> [opciones]
```

**Ejemplo mínimo**:
```bash
almagag mi-diagrama.gag
```

Esto genera `mi-diagrama.svg` en el mismo directorio usando el algoritmo AUTO (por defecto).

## Opciones de Layout

### `--layout-algorithm {auto|laf}`

Selecciona el algoritmo de posicionamiento automático.

**Valores disponibles**:
- `auto` (por defecto): Algoritmo AutoLayoutOptimizer v3.0 jerárquico iterativo
- `laf`: Algoritmo LAFOptimizer v1.3 con minimización de cruces

**¿Cuándo usar AUTO?**
- Diagramas pequeños (<10 elementos)
- Cuando tienes coordenadas manuales que quieres preservar
- Diagramas simples sin muchas conexiones
- Prototipado rápido

**¿Cuándo usar LAF?**
- Diagramas complejos (>20 elementos)
- Contenedores anidados (3+ niveles)
- Muchas conexiones (>20 aristas)
- Cuando minimizar cruces de conexiones es crítico
- Arquitecturas de microservicios

**Ejemplos**:

```bash
# Usar algoritmo AUTO (default)
almagag arquitectura.gag

# Usar algoritmo LAF
almagag arquitectura.gag --layout-algorithm=laf

# LAF es especialmente útil para diagramas complejos
almagag microservices-architecture.gag --layout-algorithm=laf
```

**Mejoras de LAF vs AUTO**:
- 87% menos cruces de conexiones
- 24% menos colisiones
- 80% menos llamadas a routing
- 87% menos expansiones de canvas

Para más detalles sobre la decisión AUTO vs LAF, consulta [LAYOUT-DECISION-GUIDE.md](./LAYOUT-DECISION-GUIDE.md).

---

## Opciones de Debug

### `--debug`

Activa logs detallados del proceso de generación.

**¿Qué muestra?**
- Proceso de parsing del archivo .gag
- Cálculos de dimensiones de elementos
- Iteraciones del algoritmo de layout
- Detección y resolución de colisiones
- Proceso de routing de conexiones
- Expansión del canvas
- Tiempos de ejecución por fase

**Ejemplo de salida**:
```
[DEBUG] Parsing file: arquitectura.gag
[DEBUG] Found 15 elements, 12 connections
[DEBUG] Layout algorithm: LAF
[DEBUG] Phase 1: Structure analysis... OK (0.05s)
[DEBUG] Phase 2: Abstract placement... 3 cruces detectados (0.12s)
[DEBUG] Phase 3: Inflation... OK (0.08s)
[DEBUG] Phase 4: Container growth... 2 iteraciones (0.15s)
[DEBUG] Routing connections... 12 paths (0.20s)
[DEBUG] Final canvas: 1200x800
[DEBUG] Total time: 0.60s
```

**Uso típico**:
```bash
# Debug básico
almagag diagrama.gag --debug

# Debug con LAF para ver las 4 fases
almagag diagrama.gag --layout-algorithm=laf --debug

# Redirigir debug a archivo
almagag diagrama.gag --debug > debug.log 2>&1
```

**Cuándo usar**:
- Debugging de problemas de layout
- Entender por qué el algoritmo tomó ciertas decisiones
- Medir performance
- Reportar bugs con información detallada

---

### `--visualdebug`

Añade grilla de coordenadas y badge de debug al SVG generado.

**¿Qué añade al SVG?**
- Grilla de fondo con líneas cada 100px
- Etiquetas de coordenadas (0,0 en esquina superior izquierda)
- Badge en esquina superior derecha mostrando:
  - Algoritmo usado (AUTO/LAF)
  - Versión de AlmaGag
  - Dimensiones del canvas
  - Timestamp de generación

**Ejemplo visual**:
```
┌─────────────────────────────────────┐
│ LAF v3.0 | 1200x800 | 2026-01-21   │ ← Badge
├─────────────────────────────────────┤
│ 0   100  200  300  400  500  600   │ ← Grilla
│ │   │    │    │    │    │    │     │
│ 0 ┌─────────┐                       │
│   │ Server  │                       │
│ 100 └─────────┘                     │
│ 200                                 │
```

**Uso típico**:
```bash
# Visual debug simple
almagag diagrama.gag --visualdebug

# Combinar con --debug para máxima información
almagag diagrama.gag --debug --visualdebug

# Útil para calibrar posiciones manuales
almagag diagrama.gag --visualdebug --guide-lines
```

**Cuándo usar**:
- Desarrollo y calibración de layouts
- Debugging visual de posiciones
- Documentación de proceso de desarrollo
- Comparar resultados de AUTO vs LAF visualmente

---

## Opciones de Exportación

### `--exportpng`

Genera automáticamente una versión PNG del diagrama además del SVG.

**Requisitos**:
- Requiere `cairosvg` instalado: `pip install cairosvg`
- En Windows, puede requerir dependencias adicionales de Cairo

**Salida**:
```bash
almagag diagrama.gag --exportpng
# Genera:
# - diagrama.svg (siempre)
# - diagrama.png (adicional)
```

**Características del PNG**:
- Resolución 1:1 (1px SVG = 1px PNG)
- Fondo transparente por defecto
- Misma calidad visual que el SVG
- Útil para compartir en plataformas que no soportan SVG

**Uso típico**:
```bash
# PNG simple
almagag diagrama.gag --exportpng

# PNG de alta calidad con LAF
almagag arquitectura.gag --layout-algorithm=laf --exportpng

# PNG para documentación
almagag flow.gag --exportpng -o docs/images/flow.svg
```

**Cuándo usar**:
- Inclusión en documentos de Word/PowerPoint
- Compartir en Slack, Teams, o email
- Thumbnails para repositorios
- Cuando el cliente no puede abrir SVG

---

### `-o, --output <ruta>`

Especifica la ruta de salida del archivo SVG generado.

**Sintaxis**:
```bash
almagag diagrama.gag -o ruta/destino.svg
almagag diagrama.gag --output ruta/destino.svg
```

**Comportamiento**:
- Si no se especifica, usa el nombre del archivo .gag con extensión .svg
- Crea directorios intermedios si no existen
- Sobrescribe archivos existentes sin preguntar
- Si se usa `--exportpng`, el PNG se genera en el mismo directorio con el mismo nombre base

**Ejemplos**:
```bash
# Salida en directorio específico
almagag src/diagrams/arch.gag -o docs/images/arquitectura.svg

# Salida con nombre diferente
almagag temp.gag -o diagrama-final.svg

# Combinar con exportpng
almagag diagrama.gag --exportpng -o output/final.svg
# Genera:
# - output/final.svg
# - output/final.png

# Múltiples versiones
almagag arch.gag --layout-algorithm=auto -o output/arch-auto.svg
almagag arch.gag --layout-algorithm=laf -o output/arch-laf.svg
```

**Cuándo usar**:
- Organizar outputs en estructura de directorios
- Generar múltiples versiones del mismo diagrama
- Integración en pipelines de build
- Scripts de automatización

---

## Opciones de Visualización

### `--guide-lines`

Añade líneas guía horizontales y verticales al canvas del SVG.

**¿Qué muestra?**
- Líneas guía de alineación de elementos
- Bordes del canvas
- Helpers visuales para debugging de layout

**Diferencia con `--visualdebug`**:
- `--visualdebug`: Grilla fija + badge
- `--guide-lines`: Líneas guía específicas del layout generado

**Uso típico**:
```bash
# Líneas guía simples
almagag diagrama.gag --guide-lines

# Combinar con visualdebug para máxima información
almagag diagrama.gag --guide-lines --visualdebug

# Útil durante desarrollo
almagag diagrama.gag --guide-lines --debug
```

**Cuándo usar**:
- Verificar alineación de elementos
- Debugging de layouts generados
- Documentación de proceso de desarrollo

---

### `--dump-iterations`

Exporta información de cada iteración del algoritmo de layout a archivos JSON.

**Salida**:
Crea archivo `debug/layout_evolution_TIMESTAMP.csv` con:
- Número de iteración
- Score total
- Colisiones detectadas
- Cruces de conexiones
- Overlap area
- Llamadas a routing
- Expansiones de canvas

**Ejemplo de salida CSV**:
```csv
iteration,score,collisions,crossings,overlap_area,routing_calls,expansions
0,1000,5,8,1200,15,2
1,800,3,6,800,12,1
2,600,1,4,200,10,0
3,400,0,2,0,8,0
```

**Uso típico**:
```bash
# Dump de iteraciones
almagag diagrama.gag --dump-iterations

# Combinar con debug para análisis completo
almagag diagrama.gag --layout-algorithm=laf --dump-iterations --debug

# Análisis de convergencia
almagag complejo.gag --dump-iterations
# Luego analizar con: python analizar_convergencia.py debug/layout_evolution_*.csv
```

**Cuándo usar**:
- Análisis de performance del algoritmo
- Debugging de problemas de convergencia
- Investigación y desarrollo de algoritmos
- Comparación de AUTO vs LAF con datos cuantitativos

---

### `--visualize-growth`

Genera SVGs intermedios mostrando cada fase del proceso LAF (solo para `--layout-algorithm=laf`).

**Requisito**: Solo funciona con `--layout-algorithm=laf`

**Salida**:
Crea archivos en `debug/iterations/`:
- `fase1_structure_TIMESTAMP.svg`: Topología y jerarquía
- `fase2_abstract_TIMESTAMP.svg`: Posicionamiento abstracto minimizando cruces
- `fase3_inflate_TIMESTAMP.svg`: Dimensiones reales aplicadas
- `fase4_grow_TIMESTAMP.svg`: Contenedores expandidos bottom-up
- `final_TIMESTAMP.svg`: Resultado final con routing

**Ejemplo de uso educativo**:
```bash
# Visualizar proceso LAF
almagag arquitectura.gag --layout-algorithm=laf --visualize-growth

# Se generan 5 SVGs mostrando evolución:
# debug/iterations/fase1_structure_20260121_143022.svg
# debug/iterations/fase2_abstract_20260121_143022.svg
# debug/iterations/fase3_inflate_20260121_143022.svg
# debug/iterations/fase4_grow_20260121_143022.svg
# debug/iterations/final_20260121_143022.svg
```

**Uso típico**:
```bash
# Visualización educativa del proceso LAF
almagag microservices.gag --layout-algorithm=laf --visualize-growth

# Combinar con debug para documentación completa
almagag arch.gag --layout-algorithm=laf --visualize-growth --debug

# Presentaciones mostrando "cómo funciona LAF"
almagag ejemplo.gag --layout-algorithm=laf --visualize-growth --exportpng
```

**Cuándo usar**:
- Entender cómo funciona el algoritmo LAF
- Presentaciones y documentación educativa
- Debugging de problemas específicos de una fase LAF
- Comparar estrategias de minimización de cruces

---

## Combinaciones Comunes

### Desarrollo

```bash
# Máxima información para debugging
almagag diagrama.gag --debug --visualdebug --guide-lines

# Testing de LAF con análisis completo
almagag diagrama.gag --layout-algorithm=laf --debug --dump-iterations --visualize-growth
```

### Producción

```bash
# Generación limpia con LAF
almagag arquitectura.gag --layout-algorithm=laf

# Generación con PNG para compartir
almagag flow.gag --layout-algorithm=laf --exportpng -o docs/images/flow.svg
```

### Comparación AUTO vs LAF

```bash
# Generar versión AUTO
almagag arch.gag --layout-algorithm=auto -o output/arch-auto.svg --dump-iterations

# Generar versión LAF
almagag arch.gag --layout-algorithm=laf -o output/arch-laf.svg --dump-iterations

# Comparar CSVs de iteraciones
diff debug/layout_evolution_*.csv
```

### Debug LAF Profundo

```bash
# Máxima visibilidad del proceso LAF
almagag complejo.gag \
  --layout-algorithm=laf \
  --debug \
  --visualdebug \
  --dump-iterations \
  --visualize-growth \
  --exportpng
```

### Pipeline de Documentación

```bash
# Regenerar todos los diagramas con LAF
for file in docs/diagrams/gags/*.gag; do
  almagag "$file" --layout-algorithm=laf --exportpng -o "docs/diagrams/svgs/$(basename "$file" .gag).svg"
done
```

---

## Troubleshooting

### Error: "cairosvg no encontrado"

```bash
# Windows
pip install cairosvg

# Linux (Ubuntu/Debian)
sudo apt-get install libcairo2-dev
pip install cairosvg

# macOS
brew install cairo
pip install cairosvg
```

### El algoritmo LAF no mejora mi diagrama

**Posibles causas**:
1. **Diagrama muy pequeño** (<10 elementos): AUTO puede ser suficiente
2. **Coordenadas manuales**: LAF las ignora; si las necesitas, usa AUTO
3. **Pocas conexiones**: LAF optimiza cruces; si no hay cruces, no hay mucha mejora

**Solución**:
- Usa `--dump-iterations` para ver métricas
- Compara visualmente AUTO vs LAF con `--visualdebug`
- Consulta [LAYOUT-DECISION-GUIDE.md](./LAYOUT-DECISION-GUIDE.md)

### SVG generado tiene elementos superpuestos

**Posibles causas**:
1. Algoritmo no convergió (rare en v3.0)
2. Elementos muy grandes para el canvas
3. Demasiadas restricciones de layout

**Solución**:
```bash
# Ver proceso de convergencia
almagag diagrama.gag --debug --dump-iterations

# Intentar con LAF
almagag diagrama.gag --layout-algorithm=laf --debug

# Ver iteraciones con visualdebug
almagag diagrama.gag --visualdebug --guide-lines
```

### Proceso muy lento (>10 segundos)

**Posibles causas**:
1. Diagrama muy complejo (>50 elementos)
2. Muchas iteraciones por colisiones
3. Routing complejo con muchos obstáculos

**Solución**:
```bash
# Ver dónde se pasa el tiempo
almagag diagrama.gag --debug

# LAF puede ser MÁS RÁPIDO en diagramas complejos (menos routing calls)
almagag diagrama.gag --layout-algorithm=laf --debug
```

### `--visualize-growth` no genera archivos

**Causa**: Solo funciona con `--layout-algorithm=laf`

**Solución**:
```bash
# Correcto
almagag diagrama.gag --layout-algorithm=laf --visualize-growth

# Incorrecto (no hace nada)
almagag diagrama.gag --visualize-growth
```

---

## Notas Adicionales

### Performance

**AUTO**:
- Rápido para diagramas pequeños (<10 elementos)
- Tiempo crecelinealmente con número de elementos
- Múltiples llamadas a routing pueden ralentizar

**LAF**:
- Overhead inicial en análisis de estructura
- Más eficiente para diagramas complejos (>20 elementos)
- 80% menos llamadas a routing = más rápido en casos complejos

### Compatibilidad

- Python 3.8+
- Requiere `svgwrite`, `networkx`, `scipy`
- Opcionalmente `cairosvg` para `--exportpng`

### Más Información

- [LAYOUT-DECISION-GUIDE.md](./LAYOUT-DECISION-GUIDE.md) - Guía para elegir AUTO vs LAF
- [LAF-COMPARISON.md](../LAF-COMPARISON.md) - Comparación técnica detallada
- [LAF-PROGRESS.md](../LAF-PROGRESS.md) - Historia de desarrollo de LAF
- [EXAMPLES.md](./EXAMPLES.md) - Ejemplos prácticos de uso
- [QUICKSTART.md](./QUICKSTART.md) - Inicio rápido

---

**AlmaGag v3.0.0** - Sistema de Diagramas de Arquitectura
