# Algoritmo AUTO

Algoritmo de layout original de AlmaGag. Respeta coordenadas manuales del usuario y resuelve el resto vía auto-positioning + optimización iterativa de colisiones.

📍 `AlmaGag/layout/auto/optimizer.py` · clase `AutoLayoutOptimizer`

---

## ¿Qué es AUTO?

AUTO es un optimizador de layout **híbrido**: si el SDJF trae coordenadas explícitas (`x`/`y`) en algunos elementos, las respeta; los elementos sin coordenadas los posiciona automáticamente. Después corre un loop de optimización que reubica labels y mueve elementos hasta minimizar colisiones.

Característica clave: AUTO **no impone una estructura jerárquica**. Es adecuado cuando el usuario sabe dónde quiere los elementos y solo necesita auto-completado.

---

## ¿Cuándo usar AUTO vs LAF?

| Caso de uso | Recomendación |
|---|---|
| Tenés coordenadas manuales que querés respetar | **AUTO** |
| Querés layout completamente automático para un grafo denso | **LAF** |
| Dashboard / poster: contenedores agrupando contenido sin conexiones inter-contenedor | **AUTO + coords manuales en contenedores** (workaround a BUGS-LAF-002) |
| Diagrama de arquitectura / flow con muchas conexiones | **LAF** |
| Velocidad de render importa más que minimizar cruces | **AUTO** |

---

## Flujo principal

`AutoLayoutOptimizer.optimize(layout)` ejecuta el pipeline en estas fases conceptuales:

### Fase 0 — Auto-positioning de coordenadas faltantes

Si el SDJF trae elementos sin `x` o sin `y`, `AutoLayoutPositioner` los completa. Estrategia:

- **HIGH priority** → grid compacto en el centro del canvas
- **NORMAL priority** → anillo a radio medio
- **LOW priority** → anillo externo
- **Centralidad** → elementos con más conexiones más cerca del centro

📍 `AlmaGag/layout/auto/positioner.py`

### Fase 1 — Análisis del grafo

`GraphAnalyzer` construye adyacencia, calcula niveles topológicos, identifica grupos conexos y prioridades. Los resultados se escriben en el `Layout` (atributos `graph`, `levels`, `groups`, `priorities`).

### Fase 2 — Routing inicial

`AutoRoutingPolicy.route()` calcula paths preliminares de todas las conexiones. Necesario antes de posicionar labels porque las labels se posicionan **relativas a las conexiones**.

📍 `AlmaGag/layout/auto/routing_policy.py` · doc: `routing.md`

### Fase 3 — Posicionamiento inicial de labels

`LabelPositionOptimizer` decide ubicación inicial de cada label probando posiciones canónicas: `bottom` → `right` → `top` → `left`.

### Fase 4 — Optimización iterativa (hill climbing)

Loop de hasta 10 iteraciones. En cada iteración el optimizer intenta reducir colisiones aplicando una de tres estrategias en orden:

1. **Reubicar labels** — mover labels a posiciones alternativas.
2. **Mover elementos** — desplazar el elemento "víctima" en dirección que reduzca colisiones. Movimiento escalado por peso inverso (elementos grandes se mueven menos).
3. **Expandir canvas** — última resort: si nada cabe, ampliar `canvas.width`/`canvas.height`.

Solo se aceptan candidatos que reduzcan el conteo de colisiones (hill climbing puro, no simulated annealing).

### Fase 5 — Routing final + re-evaluación

Tras movimientos, `AutoRoutingPolicy.route()` se invoca de nuevo para recalcular paths con las posiciones finales. El `Layout` resultante es lo que `renderer.py` consume.

---

## Respeto de coordenadas manuales

Distintivo de AUTO frente a LAF:

- Si el SDJF dice `{"id": "X", "x": 100, "y": 200}`, AUTO **nunca mueve `X` durante Fase 0** — esas coordenadas son sagradas.
- En Fase 4 (optimización), AUTO **sí puede mover elementos** con coordenadas manuales si causan colisiones. Si querés que un elemento no se mueva nunca, marcalo con `"priority": "HIGH"` y AUTO lo va a tratar como ancla preferida.

Esto habilita un patrón muy usado: **definir coordenadas solo en los contenedores padre** y dejar que los hijos se auto-acomoden dentro. Ver "Workaround BUGS-LAF-002" abajo.

---

## ~~Limitación conocida: BUGS-LAF-002~~ (RESUELTO 2026-06-18)

> Anterior a 2026-06-18, LAF manejaba mal el caso "dashboard" (3+ contenedores en el mismo nivel sin conexiones inter-contenedor): los ponía en fila horizontal con canvas >20.000px de ancho. **Resuelto** en LAFOptimizer con el reflow de dashboard en Fase 1.5 — ahora LAF distribuye automáticamente esos clusters en grid 2D.
>
> El workaround AUTO descrito abajo sigue siendo válido y útil cuando se quiere control manual sobre la disposición de los contenedores en un poster.

**Workaround opcional con AUTO** (para layouts manuales/posters): definir coordenadas manuales en los **contenedores padre**, dejar los hijos sin coordenadas, usar `--layout-algorithm=auto`. AUTO respeta las coords de los contenedores y los hijos se auto-acomodan dentro.

```json
{
  "canvas": {"width": 2200, "height": 1100},
  "elements": [
    {
      "id": "zona_a", "type": "building", "label": "Zona A",
      "x": 200, "y": 150,
      "contains": [{"id": "hijo1"}, {"id": "hijo2"}]
    },
    {"id": "hijo1", "type": "document", "label": "..."},
    {"id": "hijo2", "type": "document", "label": "..."}
  ],
  "connections": []
}
```

Comando: `almagag dashboard.sdjf --layout-algorithm=auto`

Ver `docs/guides/EXAMPLES.md` (sección "Dashboard layout") para más patrones.

---

## Atributos del optimizer

- `sizing` — `SizingCalculator` (dimensiones desde hp/wp).
- `geometry` — `GeometryCalculator` (bounding boxes, intersecciones).
- `collision_detector` — `CollisionDetector`.
- `graph_analyzer` — `GraphAnalyzer`.
- `positioner` — `AutoLayoutPositioner`.
- `container_calculator` — `ContainerCalculator`.
- `routing` — `AutoRoutingPolicy`.

---

## Para profundizar

- **Política de routing**: `routing.md`
- **Conceptos transversales**: `../../../../CONCEPTS.md`
- **Comparación cuantitativa con LAF**: `../laf/COMPARISON.md`
- **Deuda técnica**: `../../../../TECHNICAL_DEBT.md`
