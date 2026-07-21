"""
Estrategias de placement del motor de AlmaGag (WISH-ARCH-002).

El `LayoutEngine` (layout/engine.py) es la puerta única: elige la estrategia a
partir del JSON (o de un override por CLI) y delega en ella. Las estrategias son
intercambiables — todas viven acá — pero hay UNA **principal**:

- `auto`   — **estrategia principal**: placement general (Sugiyama + resolución de
             colisiones + contenedores). Es el default y el caso más amplio.
- `hier`   — estrategia de FLUJO dirigido (niveles/columnas, criterios A–J, y las
             vistas areas/lanes/matrix).
- `legacy` — **motor histórico** (ex-LAF): enfoque "abstracto primero" con la
             abstracción VC/SCC/TOI. CONGELADO — sólo se usa por override de
             debug (`--layout-algorithm=legacy`), nunca se auto-elige. Conserva
             a *Epifanía*, el analizador del proceso de conceptualización (un
             SVG por fase; ver `legacy/epifania/`).

Se puede cambiar de estrategia, pero el motor por defecto es AUTO.
"""
