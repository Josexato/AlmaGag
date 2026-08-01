# Skill `almagag-diagramas` — contrato con AlmaGag

El skill de claude.ai que genera diagramas con AlmaGag. Este doc fija el
**contrato** entre el skill y el repo, para mantenerlos sincronizados.

## Qué asume el skill del repo (v3.4+, grupo N)

| Capacidad | Cómo la usa el skill |
|---|---|
| Motor único (`select`) | Comando normal SIN `--layout-algorithm`; se influye vía el JSON |
| Reglas `select_strategy` | view→hier · considerations→auto · contains→auto · areas→hier · decision→hier · ciclo sin coords→hier · resto→auto |
| **Topología de red (§N45)** | nubes `cloud/inet` grado ≥2 + ≥30% enlaces `bidirectional`/`none`, sin coords → hub-and-spoke (banda «WAN» + sitios) |
| **Zonas `near` (§N46)** | `{"near":[...], "label":"..."}` = caja punteada rotulada; semillas parciales se completan por conectividad; near se cumple por construcción |
| **Antes/después (§N47/N49)** | dos archivos con ids compartidos ⇒ misma plantilla de zonas (slots min-hash) |
| Leyenda (§N48) | automática con ≥3 `semantic_type` |
| `unions` (§H7) | genealogías: un tronco por hijo |
| Métricas (§H6) | línea `[motor] cruces=… arista×nodo=… labels=…` como control de calidad |
| Epifanía | `--epifania`: flipbook por fase con colisiones marcadas |

## Mantenimiento
- El skill vive en el perfil de claude.ai del autor (`SKILL.md` + `references/`).
- Al agregar capacidades al motor: actualizar el skill (paso de diseño +
  debugging + `references/motores-y-vistas.md`) y esta tabla.
- Regla de oro del skill: **el código gana a los docs**; verificar contra
  `main.py`/`select_strategy` antes de documentar.
