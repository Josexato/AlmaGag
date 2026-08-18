# WISH-ARCH-004 — "El Mapa": contenedor · carril · ámbito como capas componibles

**Estado**: 🟡 Diseño (en revisión — NO implementado; ver §10, revisión 2026-08-18)
**Fecha**: 2026-07-16
**Origen**: conversación José + Claude sobre el error conceptual en `areas`/`lanes`.
**Relación**: consolida WISH-ARCH-002 (convergencia a un motor). No agrega deuda:
*ordena* conceptos que ya existían mezclados.

---

## 1. El problema

Al implementar el algoritmo `hier` agregamos `areas` (§I27) y `lanes` (§I28)
como si fueran conceptos nuevos. No lo son: son refinamientos de algo que
AUTO/LAF ya hacían de forma rudimentaria con **contenedores**. Peor: los nombres
quedaron mezclados. Mirando el código hoy:

| Hoy se llama | Qué es realmente | Geometría | Se dimensiona |
|---|---|---|---|
| `contains` (AUTO) | contenedor | rectángulo | crece hacia su contenido |
| `areas` §I27 (hier) | **también un contenedor** (caja 2D que corre layout adentro y se ajusta al contenido) | rectángulo | crece hacia su contenido |
| `lanes` §I28 (hier) | **un carril** (banda de una coordenada) | franja que cruza el diagrama | fija 1 coordenada |

Dos problemas de fondo:

1. **`areas` §I27 no es un "ámbito"; es un contenedor con semántica de fase.** La
   palabra "ámbito" quedó ocupada por algo que no lo es.
2. **`areas`/`lanes`/`matrix` son VISTAS mutuamente excluyentes** (se elige una
   con `--view`). No se pueden combinar. Un diagrama real es un *mapa*: terreno +
   carriles + entidades a la vez.

## 2. Los tres conceptos, limpios

El reframe no agrega un concepto: **reduce y ordena**. Quedan tres, ortogonales:

### Contenedor
Entidad que **agrupa partes y crece para contenerlas** (bottom-up). Es un
elemento en sí mismo (tiene id, label, puede anidarse). Rectangular. **Ya existe**
en AUTO (`contains`); el `areas` §I27 actual se re-lee como un contenedor (o como
carril-por-fase, según el caso).

> *El contenedor abraza a su contenido.*

### Carril (swimlane)
Banda que **cruza el diagrama** para organizar un flujo/proceso por una dimensión
(rol, fase, actor). Fija **una** coordenada (X → carriles verticales; Y →
horizontales) y deja correr el flujo en la otra. Exhaustivo y plano: cruzar de
carril = handoff. **Ya existe** como `lanes` §I28 (hoy sólo vertical).

> *El carril es una franja de responsabilidad; cruzarlo es un traspaso.*

### Ámbito (terreno) — **NUEVO**
Zona semántica / **terreno** sobre el que se posa el layout (top-down). A
diferencia del contenedor, **no crece hacia el contenido: es una forma fija** que
puede ser **arbitraria y cerrada** — círculo, cuadrado, polígono, path Bézier,
silueta. Ejemplos: el *open pit* circular de una mina; la silueta de una oficina;
una región geográfica.

> *El ámbito es el suelo sobre el que se para el contenido.*

**La distinción técnica nítida** entre contenedor y ámbito:

| | Contenedor | Ámbito |
|---|---|---|
| Dirección | bottom-up (crece hacia el contenido) | top-down (el contenido se posa sobre él) |
| Forma | rectángulo | cualquier forma cerrada |
| Tamaño | se ajusta al contenido | fijo / declarado |
| Rol | entidad | terreno / fondo semántico |

## 3. El cambio de fondo: de *vistas* a *capas*

Hoy `areas`/`lanes`/`matrix` son **vistas** (elegís una). El mapa pide que sean
**capas componibles**: un diagrama puede tener ámbitos **y** carriles **y**
contenedores a la vez. Esto:

- termina la convergencia de WISH-ARCH-002: en vez de vistas por-motor, quedan
  **facetas ortogonales de layout** que cualquier diagrama combina;
- convierte `--view` en un caso particular (elegir qué faceta domina el
  posicionamiento), no en un modo excluyente.

Orden de dibujo (de fondo a frente): **ámbitos → carriles → contenedores →
elementos/conexiones**.

## 4. Membership (ubicación declarada)

Un elemento o contenedor puede declarar a qué carril y/o ámbito pertenece; si no
lo dice, cae donde mejor acomode (auto-placement actual).

```json
{ "id": "bomba-1", "lane": "operaciones", "area": "openpit" }
```

Es pariente semántico de las **`considerations`** (rescate ④, `align`/`near`/
`avoid`), pero con intención de agrupación por región/banda, no de geometría
relativa. Probablemente se resuelva con la misma maquinaria de "paso final que
ajusta posiciones respetando intención del usuario".

### Principio: todo es blando (best-effort)

Decisión de diseño (José, 2026-07-16): la ubicación declarada — como las
`considerations` — es **blanda**, no una ley. Se intenta y **sólo se aplica si no
destruye la diagramación**; si no se puede (p.ej. un contenedor no entra en el
ámbito pedido sin romper el resto), **cede** y se informa en el log que no se
pudo cumplir, sin explicar el porqué. Ya implementado para `considerations` (guarda
por colisiones + log `no se pudo cumplir: ...`); el mapa hereda el mismo
principio: `lane`/`area` son *preferencias de ubicación*, no obligaciones.

## 5. Vocabulario / schema propuesto

```jsonc
// CONTENEDOR — ya existe, sin cambios
{ "id": "modulo", "contains": ["a", "b"] }

// CARRIL — generalizar §I28 a H/V
"lanes": [
  { "id": "ops", "label": "Operaciones", "members": ["..."], "axis": "x" }
]

// ÁMBITO — nuevo: forma libre
"areas": [
  { "id": "openpit", "label": "Open Pit", "members": ["..."],
    "shape": "circle" },                        // rect | circle | path
  { "id": "oficina", "shape": "path", "d": "M .. Z" }
]

// MEMBERSHIP — en un elemento/contenedor
{ "id": "bomba", "lane": "ops", "area": "openpit" }
```

Nota de migración: **la palabra `areas` se reasigna al ámbito multiforme**. El
`areas` §I27 actual (cajas de fase que crecen al contenido) se re-lee como
contenedores/carriles-por-fase. Hay que decidir la ruta de compatibilidad
(§7).

## 6. La parte difícil (honestidad)

El ámbito de forma arbitraria tiene una mitad fácil y una difícil:

- **Fácil**: *dibujar* la forma (cualquier path SVG cerrado) y usarla como fondo
  semántico — los elementos se etiquetan como "de este ámbito" y se agrupan cerca
  del centroide de la forma.
- **Difícil de verdad**: hacer **layout DENTRO de una forma no rectangular**
  (point-in-polygon, empacar nodos en un círculo o en una silueta). El rectángulo
  "crece-para-contener" está resuelto; posicionar dentro de una forma libre es un
  problema de layout genuinamente nuevo.

**Recomendación**: separar las dos. El ámbito arranca como **terreno/zona** (forma
libre + membership + agrupación cercana, sin contención estricta garantizada). El
"layout dentro de forma arbitraria" queda como fase posterior opt-in, sólo si se
necesita.

## 7. Mapeo del código actual → modelo nuevo

| Hoy | Pasa a ser | Acción |
|---|---|---|
| `contains` (AUTO) | Contenedor | sin cambios |
| `areas` §I27 (`hier/areas.py`) | Contenedor / carril-por-fase | re-etiquetar; decidir si se mantiene el sub-layout 2D como "contenedor que corre hier adentro" |
| `lanes` §I28 (`hier/lanes.py`) | Carril | generalizar a `axis` H/V |
| `matrix` §I (`hier/matrix.py`) | fase×rol = carril × carril | queda como composición de dos carriles |
| `roles` §I30 | atributo de membership de carril | encaja como caso de `lane` |
| (nada) | **Ámbito** | nuevo módulo `layout/areas_terrain.py` (o similar) |

## 8. Plan por fases (poco a poco, cero regresión por fase)

1. **Reetiquetado + doc** ✅ — reconocido: §I27 "áreas" = contenedor/carril-por-fase
   (caja que crece hacia su contenido), y la palabra "ámbito" queda RESERVADA para
   el terreno de forma arbitraria. Bandera plantada en `hier/areas.py` y en esta
   doc; **sin cambiar renders ni el schema** (la migración de la clave `areas`
   espera la decisión §9.1). *(hecho, bajo riesgo)*
2. **Carriles H/V** — generalizar `lanes` a `axis`. *(bajo riesgo)*
3. **Capas componibles** — permitir carriles + contenedores en el mismo diagrama
   (no excluyentes). Empezar por el motor que ya tiene contenedores (AUTO).
4. **Ámbito como terreno** — forma libre (rect/circle/path) de fondo + membership
   + agrupación cercana. Demo "open pit". *(riesgo medio — geometría de formas)*
5. **(opcional, futuro)** Layout DENTRO de forma arbitraria. *(riesgo alto)*

Cada fase: visible en Epifanía y con tests, como el rescate de LAF.

## 9. Decisiones abiertas (para José)

1. **`areas` reasignada**: ¿romper compat (los pocos `.sdjf` con `areas` §I27 se
   migran a contenedores) o mantener un alias temporal?
2. **¿Un solo motor para el mapa?** Las capas componibles empujan a que
   ámbitos/carriles/contenedores los resuelva UN motor (AUTO, el principal), no
   `hier` como vista. ¿Confirmamos esa dirección?
3. **Alcance del ámbito v1**: ¿sólo `rect`/`circle` primero, y `path` después?
4. **Membership vs considerations**: ¿unificamos `lane`/`area` con la maquinaria
   de `considerations` (misma guarda blanda), o son campos aparte?

---

## 10. Revisión 2026-08-18 — el Mapa se simplifica: de tres conceptos a dos

Revisión de José con la evidencia de las iteraciones 11-13 (macro-grilla,
`canvas.partition`, corredores, roles de banda), que este doc no podía
anticipar porque son posteriores a él. El destino del wish no cambia; la
ruta sí:

1. **El carril es un caso particular de área.** Con `partition`, una celda
   de fila/columna completa ES un carril — demostrado sin buscarlo: las
   bandas hub del showcase del tabernero (LAYOUT-026) son carriles
   horizontales hechos con una celda estirada. La fase 2 («generalizar
   lanes a H/V») deja de ser una obra propia: los carriles H y V salen de
   la macro-grilla que ya existe. La matriz = dos particiones cruzadas.
2. **El ámbito multiforme (fase 4) se re-lee como estrategia de
   partición.** `partition.scheme` hoy vale `'bsp'`; el open pit circular
   o la silueta de oficina no son un constructo nuevo sino `scheme`s
   nuevos (`radial`, `path`). La fase 5 (layout dentro de forma
   arbitraria) sigue siendo la parte genuinamente difícil y sigue siendo
   opt-in posterior.
3. **Quedan DOS constructos, no tres**: el **área** (top-down: se declara
   y el contenido se posa sobre ella — escenografía) y el **contenedor**
   (bottom-up: crece hacia su contenido — profundidad). Regla del autor
   (18-ago-2026): dos niveles bastan; no hay super-zonas de super-zonas.
4. **La decisión §9.2 la resolvió la práctica, al revés de lo sugerido**:
   la capa macro (grilla, partition, corredores, hub) se construyó en
   `hier` durante las iteraciones 11-13; AUTO queda como layout de celda.
   WISH-ARCH-009 (contenedores como miembros de área — la fase 3 de este
   plan) consolida esa dirección.
5. **Método, para el próximo lector**: un WISH fija el *destino*, no la
   *ruta*. La ruta se descubre iterando, y cuando la realidad la mejora,
   este doc se revisa con adenda fechada — no se congela ni se reescribe
   la historia.

*Este documento es diseño en papel. No hay código asociado todavía. Próximo paso:
revisión de José sobre §9 antes de abrir la fase 1.*
