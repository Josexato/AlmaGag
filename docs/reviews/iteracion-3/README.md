# AlmaGag · Revisión de diagramas — iteración 3

**Para Claude Design.** Punto de entrada legible por fetch (raw de GitHub, sin JS).
Cada diagrama expone su **par entrada→salida**: el SDJF de entrada (lo que
esperamos) y el SVG producido (coordenadas en el archivo, para evaluar geometría).

- **Fecha:** 2026-07-17 · **Repo:** Josexato/AlmaGag · **Rama:** `claude/review-phase-0-plan-JJOwz`
- Los `raw.githubusercontent.com/...` de abajo devuelven el contenido crudo (SVG XML / JSON), consumible directo.

## Respuesta a la sección L (iteración 3)

| # | Hallazgo | Estado | Nota |
|---|----------|--------|------|
| L39 | Reproducibilidad: artefactos citados no commiteados | ✅ resuelto | los SVG de esta carpeta ya están commiteados (un `*.svg` en `.gitignore` los tragaba); el canónico `14-stresstest.svg` regenerado es **byte-idéntico** al render fresco desde la fuente |
| L40 | Conectores que atraviesan iconos (ciclo aplanado) | ✅ resuelto | el ciclo I·J·K es pila vertical (no fila aplanada); ida sólida, **retorno K→I punteado** por fuera; ningún path perfora iconos (audit R3=0) |
| L41 | Regresión de niveles (A1/A3) | ✅ resuelto | render hier con 6 niveles staggered (ya no la fila 0 colapsada del viejo AUTO) |
| L42 | Ruteo 100% diagonal (H24 perdido) | ✅ resuelto | 14 conectores son polilíneas ortogonales con codos; 0 rectas centro-a-centro diagonales |

**Causa raíz de L40–L42**: se medían sobre el **canónico auto**, porque
`14-stresstest.sdjf` traía `layout_template: auto` que inyectaba coords y el motor
caía en AUTO. **Corregido de raíz**: un flujo con ciclo y sin coords manuales ahora
se enruta a **hier** por defecto (y se saltea el template). Regla estrecha a ciclos:
los DAG sin ciclo siguen en AUTO (no se regresiona 12/13-custom-icons).

**Nota sobre el audit (L39, verificabilidad)**: el chequeo `validate_gag` medía las
bboxes de iconos con el motor *legacy* para todo algoritmo ≠ auto, mientras el SVG
se rendereaba con el motor real (hier vía `select`) — desajuste que marcaba 33
falsos "colgantes" (R3) en 14-stresstest, contradiciendo que K34 **sí** adjunta a
borde. Corregido: el audit usa el mismo `LayoutEngine`/estrategia que el render.
Ahora 14-stresstest select/auto = **0 violaciones**.

## Estado del veredicto (sección K)

| # | Ítem | Estado | Nota |
|---|------|--------|------|
| K34 | Recorte al borde (clip_to_border compartido) | ✅ hecho | conectores borde a borde en los 3 motores |
| K35 | Labels dentro de contenedores | ✅ hecho | la celda del grid interno se dimensiona al label (no al ícono); el contenedor crece. 05-arquitectura 11→1, 15-arch 4→0, ningún diagrama regresiona |
| K36 | Labels de arista legibles | ✅ hecho | color pleno (antes gris) + halo, sobre su línea |
| K37 | DAG → hier | ❌ descartado | hier deja el árbol como tira ilegible 3880×314; auto es mejor |
| K38 | Tomas cerca del destino | ✅ hecho | a un carril del destino: 403→304px, sin solapes |

## Diagramas

Base raw: `https://raw.githubusercontent.com/Josexato/AlmaGag/claude/review-phase-0-plan-JJOwz/`

### 1 · Arquitectura — motor `auto`
- Salida (SVG): [`docs/reviews/iteracion-3/1-arquitectura.svg`](https://raw.githubusercontent.com/Josexato/AlmaGag/claude/review-phase-0-plan-JJOwz/docs/reviews/iteracion-3/1-arquitectura.svg)
- Entrada (fuente): [`docs/diagrams/gags/05-arquitectura-gag.gag`](https://raw.githubusercontent.com/Josexato/AlmaGag/claude/review-phase-0-plan-JJOwz/docs/diagrams/gags/05-arquitectura-gag.gag)
- K34 y K36 aplicados. Pendiente K35: dentro de «Shared» los labels aún se pisan.

### 2 · Stresstest (criterios A–J) — motor `hier`
- Salida (SVG): [`docs/reviews/iteracion-3/2-stresstest.svg`](https://raw.githubusercontent.com/Josexato/AlmaGag/claude/review-phase-0-plan-JJOwz/docs/reviews/iteracion-3/2-stresstest.svg)
- Entrada (fuente): [`docs/diagrams/gags/14-stresstest.sdjf`](https://raw.githubusercontent.com/Josexato/AlmaGag/claude/review-phase-0-plan-JJOwz/docs/diagrams/gags/14-stresstest.sdjf)
- K38 aplicado: tomas B y C a un carril de E/G (403→304px).
- Sección L resuelta (L39–L42): render hier reproducible, 6 niveles, ruteo ortogonal, ciclo I·J·K con retorno punteado. Audit = 0 violaciones.

### 3 · Árbol genealógico — motor `auto`
- Salida (SVG): [`docs/reviews/iteracion-3/3-genealogico.svg`](https://raw.githubusercontent.com/Josexato/AlmaGag/claude/review-phase-0-plan-JJOwz/docs/reviews/iteracion-3/3-genealogico.svg)
- Entrada (fuente): [`docs/diagrams/gags/11-stresstest.sdjf`](https://raw.githubusercontent.com/Josexato/AlmaGag/claude/review-phase-0-plan-JJOwz/docs/diagrams/gags/11-stresstest.sdjf)
- Ícono de «Silvia» corregido + conectores al borde. K37 descartado.

### 4 · SD-WAN (dual-homing) — motor `auto`
- Salida (SVG): [`docs/reviews/iteracion-3/4-sdwan.svg`](https://raw.githubusercontent.com/Josexato/AlmaGag/claude/review-phase-0-plan-JJOwz/docs/reviews/iteracion-3/4-sdwan.svg)
- Entrada (fuente): [`docs/diagrams/gags/red-dual-homing.sdjf`](https://raw.githubusercontent.com/Josexato/AlmaGag/claude/review-phase-0-plan-JJOwz/docs/diagrams/gags/red-dual-homing.sdjf)
- K34 aplicado: los 14 conectores tocan ambos íconos; punteados de respaldo claros.
