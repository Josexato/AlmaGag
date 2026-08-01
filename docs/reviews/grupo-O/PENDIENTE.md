# Grupo O — Emisión, portabilidad y contrato de estilo (PENDIENTE)

Nueva sección del review (1-ago-2026, aporte del skill creator). Cubre la
etapa 12 (emit) y el contrato con rasterizadores/editores/Office/CI.
**Prioridad sugerida: O50 → O51 → O53 → O54** (los dos primeros son
post-proceso puro, sin riesgo sobre A–N).

| # | Criterio | Resumen |
|---|---|---|
| O50 | Halo portable | `paint-order` es SVG2/navegador-only: cairosvg/librsvg pintan el trazo blanco ENCIMA y las etiquetas desaparecen en PNG. Reemplazar por geometría SVG 1.1: rect blanco (op. 0.85) tras el texto, o texto duplicado (copia stroke blanco debajo). Verifica: rasterizar con cairosvg SIN parche |
| O51 | viewBox recortado | el canvas se expande pero nunca contrae (1400×900 con 1.8% de tinta). Al final de emit: viewBox = bbox de todo lo dibujado + 40px. Verifica: área contenido/viewBox ≥ 0.60 |
| O52 | Densidad/aspecto en métricas | extender la línea: `tinta=X% aspecto=Y`; WARNING con tinta<4% o aspecto <0.4/>3.0 |
| O53 | Precedencia declarada | conflicto N46⇄I27: `considerations`→AUTO gana a `areas`→HIER y las cajas de fase se pierden EN SILENCIO. WARNING nombrando la señal anulada; a mediano plazo AUTO dibuja cajas de área |
| O54 | Rótulo de zona AA | 11px #8a8577 = 3.7:1 (AA pide 4.5): usar #6b6558 (5.1:1); banda superior de 18px reservada; anclado al borde de SU caja; entra al contador labels |
| O55 | type sin icono falla visible | `inet`/`wan` se reconocen para N45 pero draw/icons sólo tiene `cloud`: mapear alias→cloud explícito; lo demás → BWT visible, nunca fallback silencioso |
| O56 | Escala tipográfica | 3 niveles declarados: nodo 14 · conexión 12 (color semántico) · rótulo zona 11 bold; jerarquía por peso y color |
| O57 | Tokens de tema | sección `theme` top-level; `"color":"vp"` en el elemento; hex literal sigue válido y gana |
| O58 | PNG sin navegador | `--exportpng`: Chrome si está, cairosvg si no (requiere O50); PNGs de revisión regenerables desde CI |

Fixtures de emisión nuevos que pide: organigrama, WAN, flowchart, arquitectura.
Nota del cierre del doc: el invariante pasa a ser «halo portable — geometría
SVG 1.1 según O50, nunca paint-order».
