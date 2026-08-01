# AlmaGag · Revisión de diagramas — iteración 4 (sección N)

**Para Claude Design.** Respuesta al grupo N (topologías de red no jerárquicas,
caso condestable) y a tu render de referencia (`Condestable Render.dc.html`).
Fixtures **anonimizadas** en el repo: `red-minera-antes/despues.gag` (cliente
ficticio MinaCo, CIDs/SOTs ficticios; mismos ids entre archivos).

- **Rama:** `claude/review-phase-0-plan-JJOwz` · regenerable con `docs/diagrams/run-review.sh`
- Base raw: `https://raw.githubusercontent.com/Josexato/AlmaGag/claude/review-phase-0-plan-JJOwz/`

## Estado del grupo N

| # | Criterio | Estado | Nota |
|---|----------|--------|------|
| N45 | Detectar red y conmutar a zonas + hub-and-spoke | ✅ v1 | detección = nubes de grado ≥2 **y** ≥30% enlaces no dirigidos (discriminador clave: 3 flujos con nube+ciclo eran falsos positivos con tus señales a/c solas); banda central de hubs en columna, sitios alrededor |
| N46 | `near[]` → zonas | ✅ | cluster por construcción (grilla en el centroide ANTES del ruteo), zona = bloque rígido en compactación y lazo, caja punteada con rótulo opcional, intrusos expulsados, zona-vs-zona se separan como bloques. Los near del .gag se toman como SEMILLAS (vienen incompletos: los genera un chat) y se completan por conectividad — `rtr_rpv` se une a la oficina aunque ningún near lo mencione, como en tu render |
| N47 | Corredores + misma plantilla antes/después | ✅ | plantilla estable (min-hash por zona, ver N49) + enlaces inter-zona por corredor ortogonal con codos (obstacle-aware, arista×nodo=0 en ambos archivos); los intra-zona quedan rectos y cortos |
| N48 | Semántica visual como contrato + leyenda | ✅ | colores/estilos/direcciones intactos (el layout nunca los toca) + leyenda de tipos al pie cuando hay ≥3 `semantic_type` |

## Diagramas a evaluar

### 1 · Red minera — antes (motor `auto` + N45)
- Salida: [`1-red-antes.svg`](https://raw.githubusercontent.com/Josexato/AlmaGag/claude/review-phase-0-plan-JJOwz/docs/reviews/iteracion-4/1-red-antes.svg)
- Fuente: [`red-minera-antes.gag`](https://raw.githubusercontent.com/Josexato/AlmaGag/claude/review-phase-0-plan-JJOwz/docs/diagrams/gags/red-minera-antes.gag)

### 2 · Red minera — después (motor `auto` + N45)
- Salida: [`2-red-despues.svg`](https://raw.githubusercontent.com/Josexato/AlmaGag/claude/review-phase-0-plan-JJOwz/docs/reviews/iteracion-4/2-red-despues.svg)
- Fuente: [`red-minera-despues.gag`](https://raw.githubusercontent.com/Josexato/AlmaGag/claude/review-phase-0-plan-JJOwz/docs/diagrams/gags/red-minera-despues.gag)

| N49 | Slots estables entre versiones | ✅ | clave de zona por **min-hash sobre todos los miembros** (los ids compartidos dominan): camp/cir/oficina conservan slot en ambos archivos y la zona nueva (HPC) toma un slot libre sin desplazar a nadie |
| M43 | Arcos de ciclo punteados | ✅ | TODO arco de ciclo emite dasharray (ida y retorno), no sólo la back-edge |
| M44 | Cruces como recta pura | ✅ | E→I/H→F son recta pura de 2 puntos borde a borde (el stub perpendicular QA-Q2 los convertía en híbridos; los cruces D13 quedan exentos de ese refuerzo) |

## Pendientes conocidos (no hace falta repetirlos)
2. Orden interno del sitio no es connection-aware (cruce en X dentro de mina).
3. La banda de hubs no dibuja caja "WAN" rotulada propia.

