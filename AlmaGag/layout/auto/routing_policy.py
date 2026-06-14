"""
AutoRoutingPolicy — política de routing del algoritmo AUTO.

Encapsula cómo AUTO invoca el router_manager (biblioteca compartida en
AlmaGag/routing/) durante su pipeline de optimización. Centraliza el patrón
"setear sizing en el layout antes de rutar" que aparece en cada invocación
del optimizer y mantiene simetría con laf/routing_policy.py.
"""

from AlmaGag.routing.router_manager import ConnectionRouterManager


class AutoRoutingPolicy:
    """Política de routing para AutoLayoutOptimizer.

    Único método público: route(). Las invocaciones del optimizer (auto-route
    inicial, routing final, re-route tras expansión de canvas, re-route tras
    movimiento) comparten el mismo body — sus diferencias semánticas se
    documentan en los callsites.
    """

    def __init__(self, sizing):
        self._sizing = sizing
        self._router_manager = ConnectionRouterManager()

    def route(self, layout):
        """Calcula paths de todas las conexiones para el layout dado.

        Inyecta el SizingCalculator en el layout (los routers lo necesitan
        para conocer bounding boxes de iconos) y delega el cálculo de paths
        al router_manager compartido.
        """
        layout.sizing = self._sizing
        self._router_manager.calculate_all_paths(layout)
