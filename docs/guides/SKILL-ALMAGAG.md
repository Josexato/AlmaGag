# Skill `almagag-diagramas` — contrato con AlmaGag

El skill de claude.ai que genera diagramas con AlmaGag. Este doc fija el
**contrato** entre el skill y el repo, para mantenerlos sincronizados.

## Qué asume el skill del repo (v3.5+, grupos N y O)

| Capacidad | Cómo la usa el skill |
|---|---|
| Motor único (`select`) | Comando normal SIN `--layout-algorithm`; se influye vía el JSON |
| Reglas `select_strategy` | view→hier · considerations→auto · contains→auto · areas→hier · decision→hier · ciclo sin coords→hier · resto→auto. **§O53**: la señal anulada por la precedencia se nombra en un WARNING |
| **Topología de red (§N45)** | nubes `cloud/inet/wan/internet` grado ≥2 + ≥30% enlaces `bidirectional`/`none`, sin coords → hub-and-spoke (banda «WAN» + sitios) |
| **Zonas `near` (§N46)** | `{"near":[...], "label":"..."}` = caja punteada rotulada; semillas parciales se completan por conectividad; near se cumple por construcción. Rótulo AA #6b6558 en banda reservada de 18px (§O54) |
| **Antes/después (§N47/N49)** | dos archivos con ids compartidos ⇒ misma plantilla de zonas (slots min-hash) |
| Leyenda (§N48) | automática con ≥3 `semantic_type` (clases custom válidas: nombre tal cual + color efectivo) |
| **Semántica de enlaces (§Q63)** | `semantic_type` SE DECLARA por conexión (clases del dominio, colores por tokens `theme`); el vocabulario texto→clase NUNCA vive en el motor. Opcional: sección `semantics` embebida (clase→keywords+color, como `icons{}`) que el motor aplica con WARNING a conexiones sin declarar; sin match → neutra |
| `unions` (§H7) | genealogías: un tronco por hijo |
| Métricas (§H6+§O52) | línea `[motor] cruces=… arista×nodo=… labels=… tinta=X% aspecto=Y` como control de calidad; WARNING con tinta<4% o aspecto fuera de [0.4, 3.0] |
| **Halo portable (§O50)** | el halo de texto es GEOMETRÍA SVG 1.1 (copia con trazo blanco bajo cada `<text>`, `class="ag-text-halo"`), nunca `paint-order`. **El parche cairosvg del skill quedó obsoleto**: rasterizar directo |
| **viewBox al contenido (§O51)** | la lámina emitida se recorta al bbox + 40px (sólo contrae); las leyendas se reanclan al nuevo borde inferior |
| **Alias de iconos (§O55+§Q64)** | `inet`/`wan`/`internet` dibujan `cloud`; un `type` desconocido → BWT visible CON EL NOMBRE DEL TYPE rotulado + WARNING; la línea `§Q64` inventaría los BWT activos. Usar un type nuevo a BWT deliberado es LEGÍTIMO mientras se decide su forma — el nombre debe explicarse solo |
| **Zonas anidadas (§P59+§P60)** | `area`+`contains` anidado SIN coordenadas: la contención reserva espacio real a toda profundidad; zonas con transporte inter-zona (`bidirectional`/`none`) van a la banda principal y las de sólo-soporte a la periferia; los enlaces inter-zona viajan por troncales ortogonales (una espina por par origen→destino). El skill declara estructura y `direction`; la geometría es del motor |
| **Frontera motor⇄skill (§R)** | el skill declara intención/semántica; el motor decide TODA la geometría. Prohibido en el skill: coordenadas fijas para compensar defectos de layout (eso es bug del motor), semántica duplicada en el texto del label, types crípticos |
| **Escala tipográfica (§O56)** | nodo 14 · conexión 12 (color semántico) · rótulo zona/fase 11 bold (constantes en `config.py`) |
| **Tokens de tema (§O57)** | sección `theme` top-level + `"color": "<token>"` en elements/connections/areas/lanes/roles; hex literal gana |
| **PNG sin navegador (§O58)** | `--exportpng`: Chrome/Chromium/Edge si hay (multiplataforma), cairosvg si no; `ALMAGAG_CHROME` como override |
| Epifanía | `--epifania`: flipbook por fase con colisiones marcadas |

## Mantenimiento
- El skill vive en el perfil de claude.ai del autor (`SKILL.md` + `references/`).
- Al agregar capacidades al motor: actualizar el skill (paso de diseño +
  debugging + `references/motores-y-vistas.md`) y esta tabla.
- Regla de oro del skill: **el código gana a los docs**; verificar contra
  `main.py`/`select_strategy` antes de documentar.
