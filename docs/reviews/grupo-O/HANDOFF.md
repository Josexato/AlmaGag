# HANDOFF para la sesión que ataque el Grupo O

> **CERRADO (1-ago-2026)**: O50–O58 implementados y mergeados a master
> (rama `claude/grupo-o-emision-portabilidad-t14i54`, PRs #26+). Paquete
> para el revisor: `docs/reviews/iteracion-5/README.md`. El parche
> cairosvg del skill `almagag-diagramas` quedó innecesario (O50+O58).

**Misión**: implementar O50–O58 (ver `PENDIENTE.md` en esta carpeta) en orden
O50 → O58 → O51 → O53 → O54 → resto. O50+O58 juntos eliminan el parche
cairosvg del skill `almagag-diagramas`.

## Contexto del proyecto (2 líneas)
AlmaGag genera SVG desde .sdjf/.gag. Un revisor externo ("Claude Design",
artifact `baa24892-f8a2-4e35-b734-1fcd7ff72970` en claude.ai/code, legible
con WebFetch + desempacado del bundle) mantiene 58 criterios: A–N y QA están
CERRADOS y verificados; el grupo O (emisión/portabilidad) es lo único abierto.

## Convenciones de trabajo (no romper)
- Rama: `claude/review-phase-0-plan-JJOwz`; al terminar un bloque: commit →
  push → PR a `master` → merge (el usuario ya aprobó este flujo).
- Tests: `python -m pytest -q --import-mode=importlib` (¡el flag es
  obligatorio!). Hoy: 336 verdes. Nada se mergea en rojo.
- Regenerar SVGs versionados: `python scripts/generate_docs.py`; paquete de
  revisión: `bash docs/diagrams/run-review.sh`.
- Cada cambio guardado tras una guarda anti-regresión (patrón de la sesión
  anterior: probar → medir → revertir si empeora). Métrica:
  línea `[motor] cruces=… arista×nodo=… labels=…`.
- Preview PNG: Chromium en `/opt/pw-browsers/chromium-*/chrome-linux/chrome`
  (headless --screenshot). MIRAR el render antes de dar por bueno.
- Español neutro. Fixtures anonimizadas (guardia anti-fuga en
  tests/test_near_zones.py — no reintroducir IDs reales).

## Dónde está cada cosa (para O)
- Halo actual (O50): `draw/primitives/svg.py::create_canvas` (<style>
  paint-order) — reemplazar por texto duplicado o rect de fondo (SVG 1.1).
- Canvas/emit (O51): `generator.py` (canvas final) + renderers.
- Métricas (O52): `layout/metrics.py::quality_counters` + log en generator.
- Precedencia (O53): `generator.py::select_strategy` (+ WARNING de señal
  anulada).
- Rótulo de zona (O54): `draw/primitives/phase_areas.py::draw_near_zones`.
- Alias de iconos (O55): `draw/icons/__init__.py::draw_icon_shape` +
  `layout/strategies/auto/network.py::HUB_TYPES`.
- Export PNG (O58): `--exportpng` en `debug.py::convert_svg_to_png`.
- Al cerrar el grupo: actualizar `docs/reviews/` (iteración 5), el skill
  (quitar el parche cairosvg si O50 lo vuelve innecesario) y
  `docs/guides/SKILL-ALMAGAG.md`.

## Bucle con el revisor
Publicar README de revisión en `docs/reviews/iteracion-5/` con URLs raw de
master; el usuario se lo pasa a Claude Design y trae el veredicto (artifact
o texto). Declarar los pendientes conocidos en el README para que no los
re-reporte.
