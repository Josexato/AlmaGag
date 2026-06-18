# Benchmark: AlmaGag vs herramientas estándar

Esta carpeta contiene **el mismo diagrama de arquitectura** renderizado con dos motores distintos para comparar capacidades y entender qué características de los diagramas estándar deberíamos esperar en AlmaGag.

## Archivos

| Archivo | Motor | Tamaño | Notas |
|---|---|---:|---|
| `../svgs/05-arquitectura-gag.svg` | **AlmaGag** (AUTO, post-fixes BUGS-DIAG-*) | ~25 KB | Generado desde `../gags/05-arquitectura-gag.gag` (con iconos custom) |
| `architecture.mmd` | Mermaid (fuente) | ~4 KB | Texto declarativo. Renderizable en GitHub directamente. |
| `architecture.svg` | Mermaid (rendered) | ~150 KB | Generado con `mmdc` (mermaid-cli). |
| `architecture.png` | Mermaid (rendered) | ~110 KB | Misma fuente, formato raster. |

Ambos diagramas representan el **mismo grafo de arquitectura**: input → main → generator → algoritmos (AUTO/LAF) → routing → render → draw → output. Los 32 elementos y 5 stages son los mismos.

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

1. **Layout más compacto**: Mermaid usa dagre que minimiza cruces y espacio vacío. AlmaGag (post-fixes) sigue siendo más grande (canvas ~1600×2144 vs Mermaid ~más compacto en aspect ratio similar al diagrama).
2. **Routing de conexiones**: Mermaid usa rutas suaves (curvas o ortogonales bien ajustadas). AlmaGag a veces tiene segmentos no óptimos.
3. **Labels grandes**: Mermaid maneja labels multi-línea sin descalibrar el layout. AlmaGag tiene BUGS-DIAG-002 (label gigante) como deuda recurrente — relacionado con WISH-LAYOUT-003 (auto-callout).
4. **Auto-stagger por niveles**: dagre detecta automáticamente cuántos niveles necesita. AlmaGag (sin coords manuales) puede colapsar muchos hermanos en una sola banda — ese fue BUGS-DIAG-006.

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

## Métricas objetivas medidas

| Métrica | AlmaGag | Mermaid |
|---|---:|---:|
| Líneas de fuente | 340 (SDJF) | 105 (.mmd) |
| Tamaño del SVG | ~100 KB | ~150 KB |
| Densidad max por banda (post-DIAG-006 fix) | 7 elem | (sin "bandas" — usa flow libre) |
| Maneja containers? | ✅ (post-DIAG-001) | ✅ (subgraphs) |
| Maneja labels multi-línea sin colapsar? | ⚠️ parcial | ✅ |
| Iconos visualmente distinguidos por tipo? | ✅ | ❌ |

## Próximos benchmarks candidatos

- **Graphviz DOT** — control granular del layout, otro baseline establecido.
- **D3.js / force-directed** — diagramas dinámicos con interactividad.
- **PlantUML** — popular en docs de software.

Esta comparación informa qué BUGS/WISH del tablero priorizar:
- **WISH-LAYOUT-001** (Sistema de Etiquetas Inteligente) → cerrar gap vs Mermaid en labels.
- **WISH-LAYOUT-003** (Auto-callout) → mejorar manejo de labels grandes.
- **BUGS-LAYOUT-002** (Canvas excesivo) → competir con la compactación de dagre.
