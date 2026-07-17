# AlmaGag · Revisión de diagramas — iteración 3

**Para Claude Design.** Punto de entrada legible por fetch (raw de GitHub, sin JS).
Cada diagrama expone su **par entrada→salida**: el SDJF de entrada (lo que
esperamos) y el SVG producido (coordenadas en el archivo, para evaluar geometría).

- **Fecha:** 2026-07-17 · **Repo:** Josexato/AlmaGag · **Rama:** `claude/review-phase-0-plan-JJOwz`
- Los `raw.githubusercontent.com/...` de abajo devuelven el contenido crudo (SVG XML / JSON), consumible directo.

## Estado del veredicto (sección K)

| # | Ítem | Estado | Nota |
|---|------|--------|------|
| K34 | Recorte al borde (clip_to_border compartido) | ✅ hecho | conectores borde a borde en los 3 motores |
| K35 | Labels dentro de contenedores | ⏳ pendiente | los íconos internos están muy juntos y sus labels se pisan; pase dedicado |
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

### 3 · Árbol genealógico — motor `auto`
- Salida (SVG): [`docs/reviews/iteracion-3/3-genealogico.svg`](https://raw.githubusercontent.com/Josexato/AlmaGag/claude/review-phase-0-plan-JJOwz/docs/reviews/iteracion-3/3-genealogico.svg)
- Entrada (fuente): [`docs/diagrams/gags/11-stresstest.sdjf`](https://raw.githubusercontent.com/Josexato/AlmaGag/claude/review-phase-0-plan-JJOwz/docs/diagrams/gags/11-stresstest.sdjf)
- Ícono de «Silvia» corregido + conectores al borde. K37 descartado.

### 4 · SD-WAN (dual-homing) — motor `auto`
- Salida (SVG): [`docs/reviews/iteracion-3/4-sdwan.svg`](https://raw.githubusercontent.com/Josexato/AlmaGag/claude/review-phase-0-plan-JJOwz/docs/reviews/iteracion-3/4-sdwan.svg)
- Entrada (fuente): [`docs/diagrams/gags/red-dual-homing.sdjf`](https://raw.githubusercontent.com/Josexato/AlmaGag/claude/review-phase-0-plan-JJOwz/docs/diagrams/gags/red-dual-homing.sdjf)
- K34 aplicado: los 14 conectores tocan ambos íconos; punteados de respaldo claros.
