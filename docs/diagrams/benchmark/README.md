# Benchmark: AlmaGag vs herramientas estándar

Esta carpeta contiene **el mismo diagrama de arquitectura** renderizado con dos motores distintos para comparar capacidades y entender qué características de los diagramas estándar deberíamos esperar en AlmaGag.

## Archivos

| Archivo | Motor | Tamaño | Notas |
|---|---|---:|---|
| `../svgs/05-arquitectura-gag.svg` | **AlmaGag** (AUTO, post WISH-ARCH-001/002) | ~25 KB | Generado desde `../gags/05-arquitectura-gag.gag` (con 6 iconos custom: factory/gear/brush/pipeline/contract/toolbox) |
| `architecture.mmd` | Mermaid (fuente) | ~4 KB | Texto declarativo. Renderizable en GitHub directamente. Sincronizado con el `.gag` el 2026-06-18 (WISH-DOCS-001). |
| `architecture.svg` | Mermaid (rendered) | ~45 KB | Generado con `mmdc` (mermaid-cli). |
| `architecture.png` | Mermaid (rendered) | ~46 KB | Misma fuente, formato raster. |

Ambos diagramas representan el **mismo grafo de arquitectura post WISH-ARCH-001/002 + BUGS-LAF-002 + BUGS-LAYOUT-001/002**:
input → main → generator (factoría OPTIMIZERS) → AUTO/LAF (cada uno con su renderer) → ConnectionRouterManager → draw/svg.py → output. Heritage punteada de ambos optimizers al contrato `LayoutOptimizer`. 16 elementos en 3 containers (AUTO, LAF, Shared) idénticos en ambas renderizaciones.

## Por qué hacer este benchmark

AlmaGag es un proyecto de generación automática de diagramas. Para evolucionarlo, conviene compararlo contra herramientas establecidas y entender:
- Qué hace bien.
- Qué hace peor.
- Qué features faltan.

Mermaid es un buen baseline porque:
- Es el motor de facto en docs técnicas modernas.
- GitHub lo renderiza nativamente.
- Es text-based como el SDJF de AlmaGag (comparación justa).
- Su motor de layout (dagre) tiene 8+ años de optimización.

## Qué mirar en la comparación

### Donde AlmaGag está **a la par o mejor**

1. **Estética de iconos**: AlmaGag usa íconos de tipos (server, building, cloud, firewall, database, etc.) con gradientes; Mermaid usa solo rectángulos.
2. **Diferenciación visual por tipo**: Mermaid agrupa por subgrafos pero los nodos son visualmente iguales.
3. **Container rendering**: tras BUGS-DIAG-001, los stages de AlmaGag se ven como rectángulos con borde nítido (Mermaid usa subgrafos con fondo gris).
4. **Marcadores de flecha**: AlmaGag tiene flechas estilizadas; Mermaid usa flechas estándar.

### Donde AlmaGag está **peor**

1. **Layout más compacto**: Mermaid usa dagre que minimiza cruces y espacio vacío. AlmaGag (post-fixes) sigue siendo más grande (canvas 2200×1520 con coords manuales vs Mermaid en aspect ratio similar más compacto).
2. **Routing de conexiones**: Mermaid usa rutas suaves (curvas o ortogonales bien ajustadas). AlmaGag a veces tiene segmentos no óptimos.
3. **Labels grandes**: Mermaid maneja labels multi-línea sin descalibrar el layout. AlmaGag mejoró tras BUGS-DIAG-001..008 pero sigue con WISH-LAYOUT-003 (auto-callout) como mejora pendiente.
4. **Auto-stagger por niveles**: dagre detecta automáticamente cuántos niveles necesita. AlmaGag (sin coords manuales) puede colapsar hermanos en una sola banda — mitigado con la nueva Fase 1.5 de LAF (dashboard reflow, BUGS-LAF-002) y con coords manuales en containers padre.

### Donde AlmaGag tiene **features únicas**

1. **Iconos custom por tipo**: building, cloud, firewall, database, queue, redis, server, etc. con representación visual distintiva.
2. **Soporte para SVG embebidos** (formato `.gag`).
3. **Coordenadas manuales mixtas con auto-layout** (lo que permitió resolver BUGS-DIAG-006 con coords parciales).
4. **Sistema de 11 fases LAF** con visualizaciones de cada fase intermedia (debug).
5. **`--visualdebug`** muestra niveles topológicos y grilla.

## Cómo regenerar

### El diagrama de AlmaGag
```bash
almagag docs/diagrams/gags/05-arquitectura-gag.gag \
  -o docs/diagrams/svgs/05-arquitectura-gag.svg
```

### El diagrama de Mermaid
```bash
# Requiere mermaid-cli: npm install -g @mermaid-js/mermaid-cli
mmdc -i docs/diagrams/benchmark/architecture.mmd \
     -o docs/diagrams/benchmark/architecture.svg \
     -t neutral -b transparent --width 2200
```

GitHub también renderiza el `.mmd` directamente en cualquier markdown que lo incluya:
````markdown
```mermaid
flowchart TD
    A --> B
```
````

## Métricas objetivas medidas (2026-06-18)

| Métrica | AlmaGag | Mermaid |
|---|---:|---:|
| Líneas de fuente | ~125 (.gag incluye iconos SVG embebidos) | ~75 (.mmd) |
| Tamaño del SVG | ~25 KB | ~45 KB |
| Canvas (px) | 2200×1520 | (auto) |
| Maneja containers? | ✅ (post-DIAG-001) | ✅ (subgraphs) |
| Maneja labels multi-línea sin colapsar? | ✅ | ✅ |
| Iconos visualmente distinguidos por tipo? | ✅ (6 iconos custom embebidos) | ❌ |
| Refleja heritage abstracta? | ✅ (icono `contract` dedicado) | ✅ (forma `>...]` parallelogram) |

## Próximos benchmarks candidatos

- **Graphviz DOT** — control granular del layout, otro baseline establecido.
- **D3.js / force-directed** — diagramas dinámicos con interactividad.
- **PlantUML** — popular en docs de software.

Esta comparación informa qué WISH del tablero priorizar:
- **WISH-LAYOUT-001** (Sistema de Etiquetas Inteligente) → cerrar el gap residual vs Mermaid en labels.
- **WISH-LAYOUT-003** (Auto-callout) → mejorar manejo de labels grandes (caso `laf_pipe` en el diagrama de arquitectura).
- **WISH-LAF-001** (más optimización de cruces) → competir con dagre en grafos densos.
