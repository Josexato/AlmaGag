# Auditoría de congruencia docs⇄código — 2026-08-02

Auditoría completa de la documentación contra el código en master v3.5.0
(post review Claude Design grupos O/P/Q), pedida por el autor: «revisa toda
la documentación completa, valida la arquitectura de GAG y si hay algo
incongruente crea tickets para arreglarlo».

Método: tres barridos exhaustivos en paralelo + revisión arquitectónica del
pipeline hecha a mano durante los grupos P/Q. **Toda incongruencia listada
está verificada contra el código** (archivo:línea); lo que estaba bien no se
lista.

## Reportes

| Reporte | Alcance | Hallazgos |
|---|---|---|
| [01-spec.md](01-spec.md) | `docs/spec/FORMATO_ARCHIVOS.md` vs código | 20 |
| [02-arquitectura.md](02-arquitectura.md) | `docs/architecture/**`, `FLUJO_EJECUCION.md`, `CONCEPTS.md` | 7 grupos (≈25) |
| [03-raiz-guias-estados.md](03-raiz-guias-estados.md) | README, INDEX, ROADMAP, guides/, TECHNICAL_DEBT (estados), DIAGRAM_REVIEW | 32 |

## Tickets creados (en `docs/TECHNICAL_DEBT.md`)

| Ticket | Qué cubre |
|---|---|
| BUGS-DOCS-001 | Spec de formato: secciones sin documentar (semantics, theme, area/P60/Q65, unions, callout, width/height, alias, flags) + defaults falsos (corner_radius, preference, contenedores, actor, obligatorios, ids duplicados) |
| BUGS-DOCS-002 | Docs de arquitectura: paquete inexistente (layout/auto, layout/laf, OPTIMIZERS, renderer.py), LAF recomendado invertido, select_strategy/hier sin documentar, links rotos, conteos falsos |
| BUGS-DOCS-003 | FLUJO_EJECUCION.md: pipeline viejo, 14 rutas inválidas, funciones inexistentes |
| BUGS-DOCS-004 | CONCEPTS/INDEX/ROADMAP fósiles (v3.3), roadmap-futuro ya entregado, `avoid_elements` fantasma |
| BUGS-DOCS-005 | Guías con comandos que fallan: 13× `--layout-algorithm=laf`, `docs/examples/` inexistente, catálogo de 4 iconos (reales 13), deps inventadas |
| BUGS-DOCS-006 | TECHNICAL_DEBT auto-inconsistente: WISH-ARCH-002 duplicado, estados falsos, métricas congeladas; DIAGRAM_REVIEW histórico como vivo |
| BUGS-VAL-003 | `validate_svg` no ve iconos 100% `<path>` (firewall) → falso positivo R3 |
| BUGS-ARCH-001 | `Layout.copy()` pierde los atributos ad-hoc (contrato implícito frágil) |
| BUGS-AUTO-008 | `_compact_horizontal`: doble membresía de contenedores anidados → riesgo de cizalla |
| BUGS-AUTO-009 | Guardado H3 compara rutas frescas contra rutas rancias (medición viciada) |
| BUGS-DRAW-001 | `convert_svg_to_png` + Chrome: ventana a `scale`× sin `--force-device-scale-factor` |
| BUGS-DRAW-002 | `draw_embedded_icon` recibe `color` y no lo usa (currentColor vestigial) |
| WISH-LAYOUT-008 | Unificar los 3 sistemas de etiquetas + medición veraz en todo el pipeline |

## Documentos que SÍ están sanos

`README.md` raíz (v3.5.0, flags correctos), `docs/guides/LAYOUT-DECISION-GUIDE.md`,
`docs/guides/SKILL-ALMAGAG.md`, `docs/reviews/**` (iteraciones 3-5, grupos O/P),
`docs/architecture/WISH-ARCH-004-el-mapa.md` (bien marcado como diseño no
implementado). El patrón: lo escrito de jun-2026 en adelante verifica; lo
anterior a la reorganización `strategies/` (feb-jun) es donde vive casi toda
la incongruencia.
