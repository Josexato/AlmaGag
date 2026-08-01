# Guía de Layout: cómo el motor elige la estrategia (y cómo guiarlo desde el JSON)

En AlmaGag **ya no eliges un algoritmo**. Corres tu diagrama sin flags y el motor
único (`LayoutEngine`) decide la mejor estrategia de layout a partir del contenido
del JSON:

```bash
almagag diagrama.sdjf -o salida.svg
```

Tu palanca real no es un flag: es **cómo diseñas el JSON**. Declarar `areas`,
`contains`, `considerations`, un nodo `decision`, `unions` o un `layout_template`
cambia la estrategia que el motor selecciona. Esta guía explica esa lógica de
decisión y cómo obtener el resultado que quieres.

---

## Las estrategias

El motor reparte el trabajo entre tres estrategias internas:

| Estrategia | Rol | Cuándo la usa el motor |
|-----------|-----|------------------------|
| **`auto`** | Placement general: niveles estilo Sugiyama + resolución de colisiones + contenedores anidados (`contains`) + `considerations` blandas (align/near/avoid). | El default para la mayoría de diagramas: organigramas, arquitecturas con contenedores, DAGs sin ciclo. |
| **`hier`** | Flujo dirigido: niveles/columnas, arcos de ciclo (retorno punteado) y las **vistas** areas/lanes/matrix. | Flowcharts (nodos `decision`), diagramas de fases (`areas`), flujos cíclicos y cuando pides una `--view`. |
| **`legacy`** | Ex-**LAF** congelado (analizador VC/centralidad). | **Nunca se elige automáticamente.** Sólo vía `--layout-algorithm=legacy`, para depuración o la deluxe Epifanía. |

> **Nota sobre "LAF".** El algoritmo histórico llamado LAF fue **renombrado a
> `legacy` y congelado**. Puede que veas "LAF"/"LAFOptimizer" como el nombre
> interno de lo que ejecuta `legacy`, pero **`laf` ya no es un valor de CLI**.

---

## Cómo decide el motor (`select_strategy`)

Cuando corres sin forzar nada (el default `--layout-algorithm=select`), el motor
evalúa estas reglas **en orden** y aplica la primera que coincida:

| # | Condición en el JSON / comando | Estrategia | Por qué |
|---|--------------------------------|-----------|---------|
| 1 | Una `--view` explícita (distinta de `auto`) | **`hier`** | Las vistas areas/lanes/matrix son de hier |
| 2 | Hay `considerations` (align / near / avoid) | **`auto`** | Sólo auto respeta las consideraciones blandas |
| 3 | Algún elemento tiene `contains` (contenedores anidados) | **`auto`** | hier aún no soporta contenedores |
| 4 | Hay `areas` (metadata de fases) | **`hier`** | Flujo por ámbitos / fases |
| 5 | Algún nodo es de tipo `decision` o `diamond` | **`hier`** | Es un flowchart |
| 6 | Flujo dirigido **con ciclo** y **sin** coords `x`/`y` manuales | **`hier`** | Niveles + arcos de retorno para el ciclo |
| 7 | Cualquier otro caso | **`auto`** | Placement general |

El orden importa: por ejemplo, `contains` (regla 3) gana sobre un nodo `decision`
(regla 5), porque hier no puede dibujar contenedores anidados.

---

## Cómo obtener el resultado que quieres (diseña el JSON)

No cambias el layout con un flag; lo cambias declarando la estructura correcta.

- **Quiero un flowchart** (niveles + ramas + retorno) → añade al menos un nodo de
  tipo `decision` (o `diamond`). Dispara la regla 5 → `hier`.
- **Quiero fases / carriles / matriz** → declara `areas` con la metadata de fases.
  Dispara la regla 4 → `hier`.
- **Quiero agrupar elementos en cajas anidadas** → usa `contains` en el contenedor.
  Dispara la regla 3 → `auto` (la única que dibuja contenedores).
- **Quiero un árbol genealógico** → declara `unions` (matrimonios); el motor las
  expande a un nodo de barra con aristas padre→unión antes de posicionar.
- **Quiero pistas de proximidad/alineación** → añade `considerations`
  (align/near/avoid). Dispara la regla 2 → `auto`.
- **Quiero un patrón de posiciones concreto** → declara un `layout_template`
  (`"auto"` para auto-clasificar el grafo, o el nombre de una plantilla).
- **Sólo quiero forzar la representación** (no la estrategia de placement) → usa
  `--view areas|lanes|matrix`. Eso activa la regla 1 → `hier`.

---

## Valores de `--layout-algorithm`

En condiciones normales **no pasas este flag**. Es una palanca avanzada / de debug:

| Valor | Efecto |
|-------|--------|
| `select` | **Default.** El motor auto-elige con `select_strategy` (las reglas de arriba). |
| `auto` | Fuerza la estrategia de placement general. |
| `hier` | Fuerza la estrategia de flujo dirigido. |
| `legacy` | Fuerza el ex-LAF **congelado**. Sólo para depuración o la deluxe Epifanía. |

```bash
# Uso normal — el motor decide:
almagag diagrama.sdjf -o salida.svg

# Forzar una estrategia (avanzado / debug):
almagag diagrama.sdjf --layout-algorithm=hier -o salida.svg

# Ejecutar el motor congelado (Epifanía / depuración):
almagag diagrama.sdjf --layout-algorithm=legacy -o salida.svg
```

---

## Señal de calidad integrada

En **cada** ejecución el motor imprime tres contadores de cruces, prefijados con el
nombre del motor que realmente corrió:

```
[<engine>] cruces(arista×arista)=N arista×nodo=N labels=N
```

- `<engine>` es la estrategia efectiva (`auto`, `hier` o `legacy`).
- Los tres contadores miden solapes: arista contra arista, arista contra nodo, y
  etiquetas superpuestas.
- Si **cualquiera** de los tres es mayor que 0, la línea se emite como **WARNING**
  (indica que el layout tiene solapes que quizá quieras revisar); si todos son 0,
  se emite como INFO.

Úsalo como termómetro rápido: si ves WARNING con cruces, reconsidera la estructura
del JSON (¿deberías declarar `areas`, `contains`, o un `decision`?) antes de tocar
nada más.

---

## Depuración

Si quieres inspeccionar la decisión y la evolución del layout:

```bash
almagag diagrama.sdjf \
  --debug \
  --visualdebug \
  --dump-iterations \
  -o salida.svg
```

El log en `--debug` muestra la línea `Estrategia auto-seleccionada: <estrategia>`,
así ves exactamente qué eligió `select_strategy`. Para comparar contra el motor
congelado, corre además con `--layout-algorithm=legacy`.

---

## Recursos adicionales

- [CLI-REFERENCE.md](./CLI-REFERENCE.md) — Documentación completa de opciones CLI
- [EXAMPLES.md](./EXAMPLES.md) — Ejemplos prácticos
- [QUICKSTART.md](./QUICKSTART.md) — Inicio rápido con AlmaGag

---

**AlmaGag** — Sistema de Diagramas de Arquitectura
