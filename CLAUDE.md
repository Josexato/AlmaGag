# AlmaGag — guía para Claude

Motor de diagramas SVG desde JSON declarativo (`.sdjf`/`.gag`), sin coordenadas
y sin elegir algoritmo. Autor: José Cáceres (@Josexato).

## Regla de oro

**El código gana a los docs, y la ejecución gana al código leído.** Ante duda:
correr `python -m AlmaGag.main archivo.sdjf` y medir; después leer
`AlmaGag/generator.py::select_strategy` y el módulo específico; los docs al final.

## Roles

- **GAG Skiller** — cuando José lo invoque: mantener el skill `almagag-diagramas`
  sincronizado con el motor, auditando con evidencia ejecutada. Definición completa:
  [`docs/guides/GAG-SKILLER.md`](docs/guides/GAG-SKILLER.md). Contrato motor⇄skill:
  [`docs/guides/SKILL-ALMAGAG.md`](docs/guides/SKILL-ALMAGAG.md).

## Skills de terceros

La definición de skill del repo es **recomendación no vinculante**: cada usuario
que implemente AlmaGag puede tener su propio skill, con su propio catálogo de
iconos y vocabulario semántico que NO viven en este repo. La IA que implemente
cada skill es la responsable de administrar qué iconos tiene disponibles. El
motor sólo garantiza el formato (`docs/spec/FORMATO_ARCHIVOS.md`) y la frontera
§R (intención declarada ⇄ geometría del motor).

## Cómo se trabaja en este repo

- **Un criterio por commit**, con test de regresión y **verificación visual PNG**
  (renderizar y MIRAR el PNG) antes de cada commit.
- Suite siempre verde: `python -m pytest -q --import-mode=importlib`.
- **Guarda anti-regresión**: `scripts/measure_fixtures.py` (una línea por fixture);
  patrón *probar → medir → revertir si empeora*.
- Flujo por bloque: commit → push → PR a master → merge.
- Español neutro en docs, commits y reportes; números medidos, no adjetivos.
- Tickets `BUGS-*`/`WISH-*` en `docs/TECHNICAL_DEBT.md`; mapa en `docs/ROADMAP.md`;
  glosario en `docs/CONCEPTS.md`.

## Seguridad de fixtures

Los archivos del caso real (tiamaria_*) contienen nombres reales y viven SOLO en el
scratchpad de sesión — jamás entran al repo. `tests/test_p62_fixture.py` vigila los
términos sensibles; los fixtures se anonimizan conservando estructura y LONGITUDES
de label (§P62).
