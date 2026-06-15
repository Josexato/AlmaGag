# Revisión de calidad de diagramas

Checklist vivo de problemas visuales detectados en los SVGs renderizados de AlmaGag. A diferencia de `TECHNICAL_DEBT.md` (que trata bugs del código), este documento trata problemas **específicos del render visual** de cada `.sdjf`/`.gag`.

Sigue la misma convención de códigos que `TECHNICAL_DEBT.md`: `<CATEGORÍA>-DIAG-<NNN>`. Todas las entradas son `BUGS-DIAG-NNN` por definición (un diagrama mal renderizado siempre es "no funciona como debería"). Se resuelven marcando el checkbox.

---

## 05-arquitectura-gag.svg

**Fuente:** `docs/diagrams/gags/05-arquitectura-gag.sdjf`
**Render actual:** AUTO (post-BUGS-LAYOUT-003 fix), sin `--visualdebug`, canvas 2012×2072
**Histórico:** LAF + `--visualdebug` produjo canvas 5230×2360; sin debug LAF produce 11397×2300 (BUGS-LAF-002 manifestándose).
**Última revisión:** 2026-06-15

**Datos base:**
- 32 elementos declarados, 26 conexiones, 0 coordenadas manuales en SDJF.
- 5 stages (containers): `shared_deps`, `auto_path`, `laf_path`, `routing_module`, `draw_module`.

### 🔴 Críticos

- [ ] **BUGS-DIAG-001 — Los stages no se ven como contenedores.**
  El SDJF declara 5 stages con `contains: [...]` pero el SVG no dibuja rectángulos contenedores alrededor de cada grupo. El lector ve una nube de 32 iconos sin agrupación visual.
  **Causa probable:** AUTO con `firewall` icons como stages no rinde bounding rect del container.
  **Fix candidato:** revisar `draw/container.py` o cambiar el `type` de los stages a uno que sí pinte container. La estrategia ya documentada en `spec/CONTAINER_GROUPING_STRATEGY.md` podría aplicarse.

- [ ] **BUGS-DIAG-002 — Label gigante en `laf_pipeline` rompe la cuadrícula.**
  El label tiene 6 líneas describiendo 11 fases: `"LAF Pipeline\n1.Structure → 2.Topology\n3.Centrality → 4.Placement\n5.Optimize → 6.NdPr Expand\n7.Iterative → 8.Inflate\n9.Redistribute → 10.Route\n11.Visualize"`. Sobre un icono de 64×46 px. Desborda el contorno del elemento y descalibra el layout circundante.
  **Fix candidato:** acortar el label a 1-2 líneas en el SDJF; mover el detalle de las 11 fases a `docs/architecture/modules/layout/laf/LAF.md` (ya está ahí).

### 🟠 Importantes

- [ ] **BUGS-DIAG-003 — Asimetría horizontal y peso desequilibrado.**
  `label_optimizer` solo en x=108 (extremo izq), `vis_graph` solo en x=1808 (extremo der). El centro tiene gaps grandes. Visualmente los bordes "pesan" más que el centro.
  **Fix candidato:** coordenadas manuales en SDJF que distribuyan elementos secundarios cerca de sus stages padres.

- [ ] **BUGS-DIAG-004 — `output` aislado de los `draw_*` que lo alimentan.**
  Flujo lógico: `draw_*` → `output`. Pero las coordenadas: `output` @ y=1685, `draw_*` @ y=1745-1815. El output queda **arriba** de sus fuentes. Lectura invertida.
  **Fix candidato:** coords manuales para forzar `output` debajo del cluster `draw_module-stage`.

- [ ] **BUGS-DIAG-005 — Salto vertical desproporcionado.**
  Niveles topológicos en y: 24 → 310 → 600 → 950 → **1391** → 1685. El gap de 441 px entre el cluster routing/draw y `render` crea franjas blancas injustificadas.
  **Fix candidato:** revisar la lógica de espaciado vertical en AUTO; podría correlacionarse con BUGS-LAYOUT-002 (canvas excesivo).

### 🟡 Menores

- [ ] **BUGS-DIAG-006 — Densidad inconsistente entre niveles.**
  y=950-1024 tiene 7-8 elementos apiñados; y=1391 tiene solo `render`. Presión visual desigual.

- [ ] **BUGS-DIAG-007 — Gap vertical de 70 px entre `auto_optimizer` (y=950) y `auto_positioner` (y=1024).**
  Iconos de 46 px de alto con gap 70 → labels casi tocándose. En LAF original había más espacio.

- [ ] **BUGS-DIAG-008 — Elementos huérfanos visuales.**
  `label_optimizer` flotando en esquina izquierda; `growth_visualizer` flotando en (1380, 894) sin un cluster claro. Ambos son hijos lógicos de stages que no se ven dibujados (relacionado con BUGS-DIAG-001).

---

## Hipótesis transversales

Varios BUGS-DIAG arriba comparten causas raíz:

| Si se resuelve... | ...probablemente se resuelven |
|---|---|
| BUGS-DIAG-001 (containers visibles) | BUGS-DIAG-003, BUGS-DIAG-008 |
| Agregar coordenadas manuales en SDJF | BUGS-DIAG-003, BUGS-DIAG-004, BUGS-DIAG-008 |
| BUGS-DIAG-002 (label corto) | mejora BUGS-DIAG-005, BUGS-DIAG-006 |
| BUGS-LAF-002 (dashboard layout) | habilitaría usar LAF, que tenía mejor sense visual en este caso |

---

## Mapeo desde códigos anteriores

| Código anterior | Código actual |
|---|---|
| DIAG-001 | BUGS-DIAG-001 |
| DIAG-002 | BUGS-DIAG-002 |
| DIAG-003 | BUGS-DIAG-003 |
| DIAG-004 | BUGS-DIAG-004 |
| DIAG-005 | BUGS-DIAG-005 |
| DIAG-006 | BUGS-DIAG-006 |
| DIAG-007 | BUGS-DIAG-007 |
| DIAG-008 | BUGS-DIAG-008 |

---

## Para diagramas futuros

Cuando se revise otro diagrama (`continentes-america.sdjf`, `git.sdjf`, etc.), agregar una sección nueva en este documento siguiendo el mismo formato. Numerar las entradas de forma global (`BUGS-DIAG-009`, `BUGS-DIAG-010`...).
