"""
LAFRoutingPolicy — política de routing del algoritmo LAF.
"""


class LAFRoutingPolicy:
    """Política de routing para LAFOptimizer.

    Esta clase tiene la misma interfaz pública que AutoRoutingPolicy
    (.route() y .enabled) pero difiere en construcción interna:

    - Recibe router_manager por inyección desde generator.py, no lo
      construye internamente.
    - Permite operar con router_manager=None (LAF puede correr sin
      routing para debug parcial del pipeline).

    Esta asimetría con AutoRoutingPolicy es síntoma de WISH-ARCH-001
    (LAFOptimizer no cumple el contrato LayoutOptimizer). Cuando se
    resuelva esa deuda en rama aparte, el constructor de
    LAFRoutingPolicy probablemente se uniformará con el de
    AutoRoutingPolicy.
    """

    def __init__(self, router_manager=None):
        self._router_manager = router_manager

    @property
    def enabled(self) -> bool:
        return self._router_manager is not None

    def route(self, layout):
        if self._router_manager:
            self._router_manager.calculate_all_paths(layout)
