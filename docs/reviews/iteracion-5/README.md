# AlmaGag · Revisión de diagramas — iteración 5 (grupo O: emisión y portabilidad)

**Para Claude Design.** Respuesta al grupo O (O50–O58, etapa 12 emit y contrato
con rasterizadores/editores/Office/CI). Todos los criterios implementados, un
commit por criterio, con test de regresión y guarda anti-regresión (probar →
medir → revertir si empeora) cada uno.

- **Rama de trabajo:** `claude/grupo-o-emision-portabilidad-t14i54` (mergeada a `master`) · regenerable con `docs/diagrams/run-review.sh`
- Base raw: `https://raw.githubusercontent.com/Josexato/AlmaGag/master/`
- Suite: `python -m pytest -q --import-mode=importlib` → **380 verdes** (336 al abrir el grupo; +44 nuevos)

## Estado del grupo O

| # | Criterio | Estado | Nota |
|---|----------|--------|------|
| O50 | Halo portable (SVG 1.1, nunca `paint-order`) | ✅ | el halo se materializa al emitir: por cada `<text>` se inyecta una copia inferior con trazo blanco (`class="ag-text-halo"`) en el mismo padre — apilado idéntico al de `paint-order:stroke` pero legible en cairosvg/librsvg/Office. Verificado rasterizando con cairosvg SIN parche (test) y comparando visualmente cairosvg vs Chromium. **El invariante nuevo queda vigilado por `tests/test_halo_portable.py`** |
| O51 | viewBox recortado al bbox + 40px | ✅ | post-proceso de emisión: bbox de TODO lo dibujado (con transforms; paths por anclas + puntos de control) + 40px, regla SÓLO-contraer. Las leyendas de franja inferior (§I30/§N48) van en `<g class="ag-bottom-anchored">`: fuera del bbox vertical y reancladas al nuevo borde. red-minera pasa de 1800×1150 a 1443×823 |
| O52 | Densidad/aspecto en métricas | ✅ | línea extendida: `tinta=X% aspecto=Y`; WARNING con tinta<4% o aspecto fuera de [0.4, 3.0]. `tinta` es un proxy por Σ bboxes de iconos+contenedores+etiquetas sobre la lámina estimada (bbox+margen, espejo del recorte O51) |
| O53 | Precedencia declarada (N46⇄I27) | ✅ v1 | WARNING nombrando la señal anulada: `considerations`/`constraints` anulan `areas`; `contains` anula `areas`; `--view` anula `considerations`. **Pendiente declarado (mediano plazo): que AUTO dibuje cajas de área** |
| O54 | Rótulo de zona AA | ✅ | #6b6558 (5.1:1) en vez de #8a8577 (3.7:1); banda superior de 18px RESERVADA (la caja crece hacia arriba, los miembros no la pisan por construcción); anclado al borde de SU caja; entra al contador labels vía CollisionDetector (geometría única `near_zone_boxes()` compartida render/validador) |
| O55 | `type` sin icono → falla visible | ✅ | `inet`/`wan`/`internet` → alias explícito a `cloud` (y §N45 `HUB_TYPES` se DERIVA del mapa de alias — una sola verdad); lo demás → BWT visible + WARNING §O55 con el tipo, nunca silencioso |
| O56 | Escala tipográfica declarada | ✅ | contrato en config: nodo 14 · conexión 12 (color semántico) · rótulo zona/fase 11 bold; sitios canónicos cableados a las constantes (las etiquetas de nodo del modo agrupado estaban en 11.5 y los rótulos de fase/carril en 12 — unificados) |
| O57 | Tokens de tema | ✅ | sección `theme` top-level + `"color": "<token>"` en elements/connections/areas/lanes/roles; hex literal o nombre CSS no-token sigue válido y gana. Demo: `4-organigrama` (paleta corporativa por tokens) |
| O58 | PNG sin navegador | ✅ | `convert_svg_to_png`: Chrome/Chromium/Edge multiplataforma (`ALMAGAG_CHROME` → PATH → rutas fijas → Chromium de Playwright) con fallback cairosvg (fiel gracias a O50). Los PNG de este paquete están generados con la vía cairosvg — regenerables desde CI sin navegador |

Extra encontrado durante la verificación de O50: los swatches de la leyenda
§N48 se emitían con longitud cero (svgwrite `Line` sobrescribe `x1..y2`
pasados como atributos extra) — corregido con test.

## Diagramas a evaluar (una lámina por clase de emisión)

Cada uno con su PNG generado por la vía SIN navegador (cairosvg, sin parche):

### 1 · Arquitectura (motor `auto`, contenedores)
- [`1-arquitectura.svg`](https://raw.githubusercontent.com/Josexato/AlmaGag/master/docs/reviews/iteracion-5/1-arquitectura.svg) · [`1-arquitectura.png`](https://raw.githubusercontent.com/Josexato/AlmaGag/master/docs/reviews/iteracion-5/1-arquitectura.png)
- Fuente: [`05-arquitectura-gag.gag`](https://raw.githubusercontent.com/Josexato/AlmaGag/master/docs/diagrams/gags/05-arquitectura-gag.gag)
- Métrica: `[auto] cruces=5 arista×nodo=0 labels=7 tinta=26.3% aspecto=1.09`

### 2 · WAN (motor `auto` + §N45, iconos embebidos, zonas near)
- [`2-wan.svg`](https://raw.githubusercontent.com/Josexato/AlmaGag/master/docs/reviews/iteracion-5/2-wan.svg) · [`2-wan.png`](https://raw.githubusercontent.com/Josexato/AlmaGag/master/docs/reviews/iteracion-5/2-wan.png)
- Fuente: [`red-minera-antes.gag`](https://raw.githubusercontent.com/Josexato/AlmaGag/master/docs/diagrams/gags/red-minera-antes.gag)
- Métrica: `[auto] cruces=3 arista×nodo=0 labels=1 tinta=8.5% aspecto=1.90` · recorte 1800×1150 → 1443×823
- Aquí se ven: rótulo de zona AA (O54), leyenda §N48 reanclada tras el recorte (O51), swatches corregidos

### 3 · Flowchart (motor `hier`, rombos de decisión)
- [`3-flowchart.svg`](https://raw.githubusercontent.com/Josexato/AlmaGag/master/docs/reviews/iteracion-5/3-flowchart.svg) · [`3-flowchart.png`](https://raw.githubusercontent.com/Josexato/AlmaGag/master/docs/reviews/iteracion-5/3-flowchart.png)
- Fuente: [`es-primo.gag`](https://raw.githubusercontent.com/Josexato/AlmaGag/master/docs/diagrams/gags/es-primo.gag)
- Métrica: `[hier] cruces=1 arista×nodo=1 labels=0 tinta=9.0% aspecto=1.29`

### 4 · Organigrama (fixture NUEVO, tokens de tema O57)
- [`4-organigrama.svg`](https://raw.githubusercontent.com/Josexato/AlmaGag/master/docs/reviews/iteracion-5/4-organigrama.svg) · [`4-organigrama.png`](https://raw.githubusercontent.com/Josexato/AlmaGag/master/docs/reviews/iteracion-5/4-organigrama.png)
- Fuente: [`organigrama-empresa.sdjf`](https://raw.githubusercontent.com/Josexato/AlmaGag/master/docs/diagrams/gags/organigrama-empresa.sdjf) (empresa ficticia AcmeCorp; 5 tokens de tema → 9 colores resueltos)
- Métrica: `[auto] cruces=0 arista×nodo=0 labels=0 tinta=9.2% aspecto=1.18` · recorte 1400×900 → 976×813

## Pendientes conocidos (declarados para no re-reportar)

1. **O53 mediano plazo**: AUTO todavía NO dibuja cajas de área cuando gana la
   precedencia — hoy sólo el WARNING con la señal anulada (v1 acordada).
2. **Recorte O51 y arcos**: los comandos `A`/`a` de paths aportan sólo su punto
   final al bbox (la panza del arco la absorbe el margen de 40px). El ancho de
   texto se estima (0.62×font-size, generoso): una sobrestimación sólo hace el
   recorte menos agresivo, nunca corta (regla sólo-contraer).
3. **O52 `tinta` es proxy**: Σ de bboxes (iconos+etiquetas), no píxeles reales
   de tinta; sirve como guarda de lámina-vacía, no como medida tipográfica.
4. **Layout de árboles chicos en `auto`** (no es de emisión): al armar el
   organigrama sin coordenadas, `auto` promueve de nivel a un hijo hoja
   (`jsis` quedó en la fila de gerencias) y reparte etiquetas ambiguas en la
   fila inferior; por eso el fixture 4 usa coordenadas manuales. Candidato a
   grupo futuro de layout jerárquico.
5. **Aspecto en topologías anchas**: `red-dual-homing-areas` da aspecto 4.85 →
   WARNING §O52; es inherente al contenido (3 sedes en fila), no un bug.

## Cómo verificar O50 sin parche (reproducible)

```bash
pip install cairosvg
python - <<'EOF'
import cairosvg
cairosvg.svg2png(url='docs/reviews/iteracion-5/2-wan.svg',
                 write_to='/tmp/check.png', background_color='white')
EOF
# /tmp/check.png debe tener TODAS las etiquetas legibles (antes quedaban
# como manchas blancas). El SVG no contiene 'paint-order'.
```
