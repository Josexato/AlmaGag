"""
Estrategias de placement del motor de AlmaGag (WISH-ARCH-002).

El `LayoutEngine` (layout/engine.py) es la puerta única; cada estrategia resuelve
el *cómo* del layout para una clase de diagrama. `AUTO` (layout/auto/) es la
estrategia base/general; `hier` (aquí) es la estrategia de FLUJO dirigido
(pipeline por niveles/columnas, criterios A–J, vistas areas/lanes/matrix). Ya no
son algoritmos peer: son estrategias que el motor elige a partir del JSON.
"""
