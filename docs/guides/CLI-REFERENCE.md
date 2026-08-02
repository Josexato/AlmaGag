# Referencia Completa CLI - AlmaGag v3.5

Esta guía documenta todas las opciones de línea de comandos disponibles en AlmaGag.

## Tabla de Contenidos

- [Sintaxis Básica](#sintaxis-básica)
- [Modelo Mental: el motor elige por ti](#modelo-mental-el-motor-elige-por-ti)
- [Opciones de Layout](#opciones-de-layout)
- [Opciones de Vista](#opciones-de-vista)
- [Opciones de Estilo Visual](#opciones-de-estilo-visual)
- [Parámetros de Centralidad (solo `legacy`)](#parámetros-de-centralidad-solo-legacy)
- [Opciones de Debug](#opciones-de-debug)
- [Opciones de Exportación](#opciones-de-exportación)
- [Opciones de Visualización](#opciones-de-visualización)
- [Señal de Calidad del Layout](#señal-de-calidad-del-layout)
- [Resumen Rápido de Parámetros](#resumen-rápido-de-parámetros)
- [Combinaciones Comunes](#combinaciones-comunes)
- [Troubleshooting](#troubleshooting)

## Sintaxis Básica

```bash
almagag <archivo.sdjf|.gag> [opciones]
```

**Ejemplo mínimo**:
```bash
almagag mi-diagrama.sdjf -o mi-diagrama.svg
```

El archivo de entrada puede ser `.sdjf` (SDJF puro) o `.gag` (SDJF con iconos
embebidos). Si no especificas `-o/--output`, el SVG se genera en el directorio
actual.

## Modelo Mental: el motor elige por ti

La forma normal de usar AlmaGag es **sin pasar ningún flag de algoritmo**:

```bash
almagag archivo.sdjf -o salida.svg
```

El motor de layout (`LayoutEngine`) analiza el JSON y **elige él mismo la mejor
estrategia** mediante `select_strategy`. No necesitas — ni normalmente debes —
pasar `--layout-algorithm`; forzar una estrategia es territorio avanzado/debug.

**Reglas de `select_strategy`** (se evalúan en este orden; la primera que aplica gana):

1. Hay un `--view` explícito (distinto de `auto`) → **hier**
2. El JSON declara `considerations` (align/near/avoid) → **auto**
3. Algún elemento tiene `contains` (contenedores anidados) → **auto** (hier aún no los soporta)
4. El JSON declara `areas` (metadata de fases) → **hier**
5. Hay un nodo `decision`/`diamond` (flowchart) → **hier**
6. Es un flujo dirigido **con ciclo** y **sin coordenadas manuales** (`x`/`y`) → **hier** (niveles + arcos de ciclo)
7. En cualquier otro caso → **auto** (placement general)

En resumen: entrega tu `.sdjf` y deja que el motor decida. Los flags de abajo son
para casos avanzados, comparación y debug.

## Opciones de Layout

### `--layout-algorithm {select|auto|hier|legacy}`

Fuerza la estrategia de posicionamiento automático. **Por defecto es `select`**,
que delega la decisión al motor (ver [Modelo Mental](#modelo-mental-el-motor-elige-por-ti)).

**Valores disponibles**:
- `select` (**por defecto**): el motor elige la estrategia a partir del JSON vía
  `select_strategy`. **Normalmente NO pasas este flag** — es el comportamiento
  automático.
- `auto`: placement general (Sugiyama + resolución de colisiones + contenedores).
  Es la estrategia principal para la mayoría de diagramas.
- `hier`: flujo dirigido (niveles + columnas + arcos de ciclo). Es el motor que
  alimenta las vistas de áreas/carriles/matriz.
- `legacy`: el motor histórico **congelado** (internamente `LAFOptimizer`, el
  ex-`laf`). Solo para debug/Epifanía. No es para uso general.

> Nota: el nombre interno "LAF"/"LAFOptimizer" sigue apareciendo como el nombre
> del algoritmo histórico que ejecuta `legacy`. En la línea de comandos el valor
> es siempre `legacy`, nunca `laf`.

**¿Cuándo pasar un flag explícito?**
- `select` (default): casi siempre. Deja que el motor decida.
- `auto`: para forzar el placement general aunque el JSON sugiera otra cosa.
- `hier`: para forzar el flujo dirigido por niveles.
- `legacy`: solo para debug del motor histórico o para la Epifanía de lujo
  (análisis VC/centralidad).

**Ejemplos**:

```bash
# Uso normal: el motor elige (equivale a --layout-algorithm=select)
almagag arquitectura.sdjf -o arquitectura.svg

# Forzar placement general
almagag arquitectura.sdjf --layout-algorithm=auto -o arquitectura.svg

# Forzar flujo dirigido por niveles
almagag flujo.sdjf --layout-algorithm=hier -o flujo.svg

# Motor histórico congelado (debug / ex-LAF)
almagag arquitectura.sdjf --layout-algorithm=legacy -o arquitectura.svg
```

Para más detalles sobre cómo se decide la estrategia, consulta
[LAYOUT-DECISION-GUIDE.md](./LAYOUT-DECISION-GUIDE.md).

---

## Opciones de Vista

### `--view {auto|flow|areas|lanes|matrix}`

Fuerza la **REPRESENTACIÓN** del diagrama. Esto solo se controla por CLI, **nunca
desde el JSON**. **Por defecto es `auto`** (la representación la decide el
algoritmo a partir del JSON).

Pasar cualquier vista distinta de `auto` **enruta el diagrama a `hier`** (ver la
regla 1 de `select_strategy`).

**Valores disponibles**:
- `auto` (**por defecto**): el algoritmo elige la representación según el JSON
  (por ejemplo `areas` si el archivo declara esa metadata).
- `flow`: columnas por flujo.
- `areas`: cajas por fase (§I27). Es una vista de `hier`.
- `lanes`: carriles por rol (§I28). Es una vista de `hier`.
- `matrix`: matriz fase×rol. Es una vista de `hier`.

**Ejemplos**:
```bash
# Representación por defecto (decide el algoritmo)
almagag proceso.sdjf -o proceso.svg

# Forzar carriles por rol (enruta a hier)
almagag proceso.sdjf --view=lanes -o proceso-lanes.svg

# Forzar matriz fase×rol
almagag proceso.sdjf --view=matrix -o proceso-matrix.svg
```

**Cuándo usar**:
- Cuando quieres una representación específica (fases, carriles, matriz)
  independientemente de lo que el JSON declare.
- Recuerda que cualquier `--view` no-`auto` fuerza la estrategia `hier`.

---

## Opciones de Estilo Visual

### `--color-connections`

Asigna un color distinto a cada conexión del diagrama, facilitando la identificación visual de cada línea.

**Comportamiento**:
- Genera una paleta de colores HSL distribuidos uniformemente (saturation=70%, lightness=45%)
- Cada conexión recibe un color único aplicado a: trazo de la línea, flecha y círculo de origen
- Los markers (flechas y círculos) heredan el color de su conexión

**Markers por dirección** (con o sin `--color-connections`):

| Dirección | Origen | Destino |
|---|---|---|
| `forward` | Círculo | Flecha |
| `backward` | Flecha | Círculo |
| `bidirectional` | Flecha | Flecha |
| `none` | Sin marker | Sin marker |

**Ejemplos**:
```bash
# Conexiones coloreadas para identificación visual
almagag diagrama.sdjf --color-connections -o diagrama.svg

# Combinar con una estrategia forzada
almagag arquitectura.sdjf --layout-algorithm=hier --color-connections -o arquitectura.svg

# Generar versión coloreada para presentaciones
almagag flow.sdjf --color-connections --exportpng -o docs/flow-colored.svg
```

**Cuándo usar**:
- Diagramas con muchas conexiones que se cruzan
- Presentaciones donde necesitas señalar conexiones específicas
- Debugging visual de rutas de conexión
- Documentación educativa

---

## Parámetros de Centralidad (solo `legacy`)

Estos parámetros ajustan cómo el algoritmo histórico calcula la "importancia" de
cada nodo para decidir su posición central o periférica. **Solo aplican con
`--layout-algorithm=legacy`** (el analizador de centralidad ex-LAF); se ignoran
en `select`, `auto` y `hier`.

### `--centrality-alpha F`

Peso por unidad de distancia en skip connections (conexiones que saltan niveles topológicos).

- **Default**: `0.15`
- **Efecto**: Valores mayores penalizan más las conexiones largas, favoreciendo nodos centrales con conexiones cortas.
- **Rango sugerido**: `0.0` - `0.5`

### `--centrality-beta F`

Peso por hijo extra (hub-ness). Controla cuánto se premia a los nodos con muchas conexiones salientes.

- **Default**: `0.10`
- **Efecto**: Valores mayores mueven los nodos hub hacia el centro del diagrama.
- **Rango sugerido**: `0.0` - `0.5`

### `--centrality-gamma F`

Peso por fan-in extra. Controla cuánto se premia a los nodos con muchas conexiones entrantes.

- **Default**: `0.15`
- **Efecto**: `0.0` desactiva el efecto. Valores mayores priorizan nodos con muchas entradas.
- **Rango sugerido**: `0.0` - `0.5`

### `--centrality-max-score F`

Clamp máximo del score de accesibilidad. Limita el valor máximo del score de centralidad para evitar distorsiones.

- **Default**: `100.0`
- **Efecto**: Evita que un solo nodo domine el layout por tener scores extremos.
- **Rango sugerido**: `50.0` - `200.0`

**Ejemplos**:
```bash
# Layout legacy con nodos hub más centrales
almagag arch.sdjf --layout-algorithm=legacy --centrality-beta 0.25

# Desactivar fan-in (solo usar conexiones salientes)
almagag arch.sdjf --layout-algorithm=legacy --centrality-gamma 0.0

# Ajuste fino completo
almagag arch.sdjf --layout-algorithm=legacy \
  --centrality-alpha 0.20 \
  --centrality-beta 0.15 \
  --centrality-gamma 0.10 \
  --centrality-max-score 80.0
```

**Cuándo ajustar**:
- Si los nodos más conectados no están suficientemente centrados, aumentar `--centrality-beta`
- Si las conexiones largas generan muchos cruces, aumentar `--centrality-alpha`
- Si el layout se ve distorsionado por un nodo dominante, bajar `--centrality-max-score`

---

## Opciones de Debug

### `--debug`

Activa logs detallados del proceso de generación.

**¿Qué muestra?**
- Proceso de parsing del archivo de entrada
- Cálculos de dimensiones de elementos
- Estrategia elegida por el motor (`select_strategy`) o forzada por CLI
- Iteraciones del algoritmo de layout
- Detección y resolución de colisiones
- Proceso de routing de conexiones
- Expansión del canvas
- Tiempos de ejecución por fase

**Uso típico**:
```bash
# Debug básico
almagag diagrama.sdjf --debug -o diagrama.svg

# Debug del motor histórico congelado
almagag diagrama.sdjf --layout-algorithm=legacy --debug -o diagrama.svg

# Redirigir debug a archivo
almagag diagrama.sdjf --debug -o diagrama.svg > debug.log 2>&1
```

**Cuándo usar**:
- Debugging de problemas de layout
- Entender qué estrategia eligió el motor y por qué
- Medir performance
- Reportar bugs con información detallada

---

### `--visualdebug`

Añade grilla de coordenadas y badge de debug al SVG generado.

**¿Qué añade al SVG?**
- Grilla de fondo con líneas de referencia
- Etiquetas de coordenadas (0,0 en esquina superior izquierda)
- Badge de debug con información de generación (estrategia usada, dimensiones del
  canvas, etc.)

**Uso típico**:
```bash
# Visual debug simple
almagag diagrama.sdjf --visualdebug -o diagrama.svg

# Combinar con --debug para máxima información
almagag diagrama.sdjf --debug --visualdebug -o diagrama.svg

# Útil para calibrar posiciones manuales
almagag diagrama.sdjf --visualdebug --guide-lines 186 236 -o diagrama.svg
```

**Cuándo usar**:
- Desarrollo y calibración de layouts
- Debugging visual de posiciones
- Documentación de proceso de desarrollo
- Comparar resultados de distintas estrategias visualmente

---

## Opciones de Exportación

### `--exportpng`

Exporta el SVG generado a PNG en la carpeta `debug/outputs/`, además del SVG.

**Requisitos (§O58)**: ninguno si hay Chrome/Chromium/Edge en el sistema
(multiplataforma; override con la variable `ALMAGAG_CHROME`). Sin navegador,
cae a `cairosvg` (`pip install cairosvg`) — fiel desde §O50 (el halo de
texto es geometría SVG, no CSS).

**Salida**:
```bash
almagag diagrama.sdjf --exportpng -o diagrama.svg
# Genera:
# - diagrama.svg (siempre)
# - un PNG en debug/outputs/
```

**Características del PNG**:
- Misma calidad visual que el SVG
- Útil para compartir en plataformas que no soportan SVG

**Uso típico**:
```bash
# PNG simple
almagag diagrama.sdjf --exportpng -o diagrama.svg

# PNG para documentación
almagag flow.sdjf --exportpng -o docs/images/flow.svg
```

**Cuándo usar**:
- Inclusión en documentos de Word/PowerPoint
- Compartir en Slack, Teams, o email
- Thumbnails para repositorios
- Cuando el cliente no puede abrir SVG

---

### `-o, --output FILE`

Especifica la ruta de salida del archivo SVG generado.

**Sintaxis**:
```bash
almagag diagrama.sdjf -o ruta/destino.svg
almagag diagrama.sdjf --output ruta/destino.svg
```

**Comportamiento**:
- Si no se especifica, el SVG se genera en el directorio actual.
- Sobrescribe archivos existentes sin preguntar.
- Con `--exportpng`, el PNG se genera en `debug/outputs/`.

**Ejemplos**:
```bash
# Salida en directorio específico
almagag src/diagrams/arch.sdjf -o docs/images/arquitectura.svg

# Salida con nombre diferente
almagag temp.sdjf -o diagrama-final.svg

# Comparar dos estrategias forzadas
almagag arch.sdjf --layout-algorithm=auto -o output/arch-auto.svg
almagag arch.sdjf --layout-algorithm=hier -o output/arch-hier.svg
```

**Cuándo usar**:
- Organizar outputs en estructura de directorios
- Generar múltiples versiones del mismo diagrama
- Integración en pipelines de build
- Scripts de automatización

---

## Opciones de Visualización

### `--guide-lines Y [Y ...]`

Dibuja líneas horizontales de guía en las posiciones Y especificadas.

**Sintaxis**:
```bash
almagag diagrama.sdjf --guide-lines 186 236 -o diagrama.svg
```

**¿Qué muestra?**
- Una línea horizontal por cada valor Y indicado
- Helpers visuales para verificar alineación de elementos

**Uso típico**:
```bash
# Líneas guía en Y=186 y Y=236
almagag diagrama.sdjf --guide-lines 186 236 -o diagrama.svg

# Combinar con visualdebug para máxima información
almagag diagrama.sdjf --guide-lines 186 236 --visualdebug -o diagrama.svg
```

**Cuándo usar**:
- Verificar alineación de elementos
- Debugging de layouts generados
- Documentación de proceso de desarrollo

---

### `--dump-iterations`

Guarda snapshots JSON de cada iteración del optimizador en `debug/iterations/`.

**Salida**:
Crea archivos JSON en `debug/iterations/` con el estado del layout en cada
iteración del optimizador (posiciones, métricas por iteración, etc.).

**Uso típico**:
```bash
# Dump de iteraciones
almagag diagrama.sdjf --dump-iterations -o diagrama.svg

# Combinar con debug para análisis completo
almagag diagrama.sdjf --dump-iterations --debug -o diagrama.svg
```

**Cuándo usar**:
- Análisis de performance del algoritmo
- Debugging de problemas de convergencia
- Investigación y desarrollo de algoritmos

---

### `--epifania` (aliases `--debug-phases`, `--visualize-growth`)

**Epifanía** — ver cómo NACE la abstracción del layout, paso a paso. Genera un
SVG por fase en `debug/epifania/<diagrama>/` junto con un `index.html` para
navegarlos.

Los tres nombres (`--epifania`, `--debug-phases`, `--visualize-growth`) son
alias del mismo flag.

**Comportamiento según la estrategia**:
- Con `auto`/`hier` (lo normal): es un **flipbook del layout real** naciendo por
  cada etapa del proceso.
- Con `--layout-algorithm=legacy`: usa el **analizador de lujo** (VC/centralidad)
  del motor histórico ex-LAF.

**Salida**:
```
debug/epifania/<diagrama>/
├── index.html          ← navegador de las fases
├── ...                 ← un SVG por fase
```

**Uso típico**:
```bash
# Epifanía: flipbook del layout real por fase
almagag arquitectura.sdjf --epifania -o arquitectura.svg

# Epifanía de lujo (VC/centralidad, solo con legacy)
almagag arquitectura.sdjf --layout-algorithm=legacy --epifania -o arquitectura.svg

# Usando un alias
almagag arquitectura.sdjf --visualize-growth -o arquitectura.svg
```

**Cuándo usar**:
- Entender cómo el motor construye el layout fase a fase
- Presentaciones y documentación educativa
- Debugging de problemas específicos de una fase
- Análisis de centralidad del motor histórico (`legacy`)

---

## Señal de Calidad del Layout

En cada ejecución, AlmaGag imprime una **línea de calidad** que resume los cruces
detectados en el resultado, por ejemplo:

```
[auto] cruces(arista×arista)=5 arista×nodo=0 labels=7
```

- El prefijo (`[auto]`, `[hier]`, `[legacy]`) indica la estrategia efectiva usada.
- `cruces(arista×arista)`: cruces entre conexiones.
- `arista×nodo`: conexiones que atraviesan nodos.
- `labels`: solapamientos de etiquetas.

Si **cualquiera** de esos contadores es mayor que 0, la línea se emite como
**WARNING**; si todos son 0, se emite como **INFO**. Es la señal de calidad
incorporada: úsala para verificar de un vistazo si el layout salió limpio.

---

## Resumen Rápido de Parámetros

| Parámetro | Tipo | Default | Descripción |
|---|---|---|---|
| `input_file` | positional | requerido | Archivo `.sdjf` o `.gag` de entrada |
| `-o, --output FILE` | string | dir. actual | Ruta de salida del SVG |
| `--layout-algorithm` | `select\|auto\|hier\|legacy` | `select` | Estrategia de layout (`select` = el motor elige) |
| `--view` | `auto\|flow\|areas\|lanes\|matrix` | `auto` | Fuerza la representación (no-`auto` enruta a `hier`) |
| `--color-connections` | flag | off | Colorear cada conexión con color distinto |
| `--debug` | flag | off | Logs detallados del procesamiento |
| `--visualdebug` | flag | off | Grilla y badge visual en el SVG |
| `--exportpng` | flag | off | Exportar PNG a `debug/outputs/` |
| `--guide-lines Y [Y...]` | int list | off | Líneas horizontales de guía en posiciones Y |
| `--dump-iterations` | flag | off | Snapshots JSON de iteraciones en `debug/iterations/` |
| `--epifania` (`--debug-phases`, `--visualize-growth`) | flag | off | Un SVG por fase en `debug/epifania/<diagrama>/` |
| `--centrality-alpha F` | float | `0.15` | Peso skip-connections (solo `legacy`) |
| `--centrality-beta F` | float | `0.10` | Peso hub-ness (solo `legacy`) |
| `--centrality-gamma F` | float | `0.15` | Peso fan-in, `0`=off (solo `legacy`) |
| `--centrality-max-score F` | float | `100.0` | Clamp máximo de score (solo `legacy`) |

---

## Combinaciones Comunes

### Uso normal (recomendado)

```bash
# Deja que el motor elija la estrategia
almagag diagrama.sdjf -o diagrama.svg
```

### Desarrollo

```bash
# Máxima información para debugging
almagag diagrama.sdjf --debug --visualdebug --guide-lines 186 236 -o diagrama.svg

# Ver el layout nacer fase a fase
almagag diagrama.sdjf --epifania --debug -o diagrama.svg
```

### Producción

```bash
# Generación limpia (el motor elige)
almagag arquitectura.sdjf -o arquitectura.svg

# Generación con PNG para compartir
almagag flow.sdjf --exportpng -o docs/images/flow.svg

# Versión coloreada para presentaciones
almagag flow.sdjf --color-connections -o docs/flow-colored.svg
```

### Comparar estrategias

```bash
# Forzar placement general
almagag arch.sdjf --layout-algorithm=auto -o output/arch-auto.svg --dump-iterations

# Forzar flujo dirigido por niveles
almagag arch.sdjf --layout-algorithm=hier -o output/arch-hier.svg --dump-iterations
```

### Debug del motor histórico (`legacy`)

```bash
# Máxima visibilidad del motor histórico ex-LAF
almagag complejo.sdjf \
  --layout-algorithm=legacy \
  --debug \
  --visualdebug \
  --dump-iterations \
  --epifania \
  --exportpng \
  -o complejo.svg
```

### Pipeline de Documentación

```bash
# Regenerar todos los diagramas (el motor elige por cada uno)
for file in docs/diagrams/sdjf/*.sdjf; do
  almagag "$file" --exportpng -o "docs/diagrams/svgs/$(basename "$file" .sdjf).svg"
done
```

---

## Troubleshooting

### `--exportpng` no genera PNG

No hay Chrome/Chromium/Edge ni `cairosvg`. Opciones:
1. Instalar cairosvg: `pip install cairosvg` (Linux: antes `sudo apt-get install libcairo2-dev`)
2. Apuntar a un Chrome existente: `export ALMAGAG_CHROME=/ruta/al/chrome`

### El motor eligió una estrategia que no esperaba

El motor decide con `select_strategy` (ver
[Modelo Mental](#modelo-mental-el-motor-elige-por-ti)). Para ver qué eligió y por qué:

```bash
almagag diagrama.sdjf --debug -o diagrama.svg
```

Si necesitas otra estrategia, fuérzala con `--layout-algorithm=auto` o
`--layout-algorithm=hier`. Recuerda que un `--view` no-`auto` fuerza `hier`.

### SVG generado tiene elementos superpuestos

**Solución**:
```bash
# Ver la línea de calidad y el proceso de convergencia
almagag diagrama.sdjf --debug --dump-iterations -o diagrama.svg

# Probar forzando otra estrategia
almagag diagrama.sdjf --layout-algorithm=hier --debug -o diagrama.svg

# Ver posiciones con visualdebug
almagag diagrama.sdjf --visualdebug --guide-lines 186 236 -o diagrama.svg
```

Consulta la [Señal de Calidad del Layout](#señal-de-calidad-del-layout) para
interpretar la línea `cruces(arista×arista)=...`.

### Proceso muy lento (>10 segundos)

**Posibles causas**:
1. Diagrama muy complejo (muchos elementos)
2. Muchas iteraciones por colisiones
3. Routing complejo con muchos obstáculos

**Solución**:
```bash
# Ver dónde se pasa el tiempo
almagag diagrama.sdjf --debug -o diagrama.svg
```

### `--epifania` no genera archivos

**Solución**: verifica que la carpeta `debug/epifania/<diagrama>/` sea escribible
y revisa la salida con `--debug`:

```bash
almagag diagrama.sdjf --epifania --debug -o diagrama.svg
```

---

## Notas Adicionales

### Compatibilidad

- Python 3.8+
- Única dependencia: `svgwrite` (opcional: `cairosvg` para PNG sin navegador)
- Opcionalmente `cairosvg` para `--exportpng`

### Más Información

- [LAYOUT-DECISION-GUIDE.md](./LAYOUT-DECISION-GUIDE.md) - Cómo se decide la estrategia de layout
- [EXAMPLES.md](./EXAMPLES.md) - Ejemplos prácticos de uso
- [QUICKSTART.md](./QUICKSTART.md) - Inicio rápido

---

**AlmaGag v3.5.0** - Sistema de Diagramas de Arquitectura
