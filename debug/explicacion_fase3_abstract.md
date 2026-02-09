# LAF FASE 3: Layout Abstracto

## ¿Qué es?

La **Fase 3: Layout Abstracto** es la fase donde se calculan las **posiciones relativas** de los elementos como si fueran **puntos de 1 pixel**, ignorando completamente sus tamaños reales. El objetivo es **minimizar los cruces** entre las conexiones.

**Nota:** En v3.0 esta fase fue renumerada de Fase 2 → Fase 3 debido a la adición de la nueva Fase 2: Análisis Topológico.

## Algoritmo: Sugiyama (3 pasos)

### 1. **LAYERING** (Asignación a capas)
Agrupa elementos en capas horizontales según su **nivel topológico**:

```
Capa 0 (nivel 0):   input
                      |
Capa 1 (nivel 1):   main
                      |
Capa 2 (nivel 2):   generator ----+
                      |            |
Capa 3 (nivel 3):   svgwrite      |
                                   |
Capa 4 (nivel 4):   layout_container, optimizer
                      |                 |
Capa 5 (nivel 5):   analysis_container, render
                      |                 |
Capa 6 (nivel 6):   draw_container
                      |
Capa 7 (nivel 7):   routing_container
                      |
Capa 8 (nivel 8):   output
```

**Resultado**: 9 capas (niveles topológicos 0-8)

---

### 2. **ORDERING** (Ordenamiento dentro de capas)

Para cada capa, ordena los elementos usando **heurísticas** para minimizar cruces:

#### **Primera capa (capa 0)**:
- Ordena por: `tipo de elemento` + `cantidad de conexiones` (descendente)

#### **Capas siguientes (capas 1-8)**:
- Usa **Barycenter Heuristic**:
  - Para cada elemento, calcula el **promedio de posiciones** de sus vecinos en la capa anterior
  - Ordena por este promedio (barycenter)
  - Elementos con conexiones cercanas en la capa anterior quedan cerca

**Ejemplo: Capa 4**
```
Capa 3:    [svgwrite]
              |
              v
Capa 4:    [layout_container, optimizer]
              ^                ^
              |                |
           barycenter(layout_container) = posición_de(generator)
           barycenter(optimizer) = promedio_de_sus_vecinos_capa_3
```

Si `layout_container` recibe conexión desde `generator` (posición 0 en capa 2),
su barycenter será bajo, colocándolo más a la izquierda.

---

### 3. **POSITIONING** (Asignación de coordenadas abstractas)

Asigna coordenadas enteras `(x, y)` a cada elemento:

- **Y (vertical)**: Índice de la capa = nivel topológico
- **X (horizontal)**: Índice del elemento dentro de su capa (después del ordenamiento)

**Ejemplo**:
```
Capa 0:  input                        → (0, 0)
Capa 1:  main                         → (0, 1)
Capa 2:  generator                    → (0, 2)
Capa 3:  svgwrite                     → (0, 3)
Capa 4:  layout_container, optimizer  → (0, 4), (1, 4)
Capa 5:  analysis_container, render   → (0, 5), (1, 5)
Capa 6:  draw_container               → (0, 6)
Capa 7:  routing_container            → (0, 7)
Capa 8:  output                       → (0, 8)
```

---

## ¿Por qué "Abstracto"?

Las coordenadas son **puramente lógicas** (puntos sin tamaño):
- No considera anchos/altos de elementos
- No considera espaciado real
- Solo optimiza **topología del grafo**

**Ventajas**:
1. **Rápido**: O(n log n) vs exploración completa
2. **Independiente del tamaño**: Funciona igual para 10 o 1000 elementos
3. **Minimiza cruces**: Algoritmo probado (Sugiyama 1981)

---

## Resultado de Fase 2

Después de esta fase, el layout tiene:

```python
abstract_positions = {
    'input': (0, 0),
    'main': (0, 1),
    'generator': (0, 2),
    'svgwrite': (0, 3),
    'layout_container': (0, 4),
    'optimizer': (1, 4),
    'analysis_container': (0, 5),
    'render': (1, 5),
    'draw_container': (0, 6),
    'routing_container': (0, 7),
    'output': (0, 8)
}

crossings = 12  # Número de cruces de conectores
```

---

## ¿Qué sigue?

**FASE 3 - Inflación**: Convertir posiciones abstractas `(0,0), (0,1), (0,2)...`
en posiciones reales con píxeles `(50, 100), (50, 300), (50, 500)...`
considerando tamaños reales de íconos y espaciado.

**FASE 4 - Crecimiento**: Expandir contenedores para que envuelvan sus elementos hijos.

---

## Ejemplo Visual

```
ANTES (Fase 1 - Análisis):
- Tenemos 11 elementos primarios
- Conocemos sus conexiones
- No sabemos dónde ponerlos

DESPUÉS (Fase 2 - Abstracto):
- Sabemos el ORDEN vertical (9 capas)
- Sabemos el ORDEN horizontal (dentro de cada capa)
- Minimizamos cruces (12 cruces en este diagrama)
- Aún no sabemos posiciones reales en pixels

PRÓXIMO (Fase 3):
- Convertir (0,0) → (50px, 100px)
- Considerar tamaños reales
```

---

## Métricas del Diagrama 05-arquitectura-gag

```
Elementos primarios: 11
Capas (niveles): 9
Cruces de conectores: 12
Conexiones totales: 25

Distribución por capa:
  Capa 0: 1 elemento  (input)
  Capa 1: 1 elemento  (main)
  Capa 2: 1 elemento  (generator)
  Capa 3: 1 elemento  (svgwrite)
  Capa 4: 2 elementos (layout_container, optimizer)
  Capa 5: 2 elementos (analysis_container, render)
  Capa 6: 1 elemento  (draw_container)
  Capa 7: 1 elemento  (routing_container)
  Capa 8: 1 elemento  (output)
```
