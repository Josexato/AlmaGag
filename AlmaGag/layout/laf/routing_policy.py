"""
LAFRoutingPolicy — política de routing del algoritmo LAF.
"""

from AlmaGag.routing.router_manager import ConnectionRouterManager


class LAFRoutingPolicy:
    """Política de routing para LAFOptimizer.

    Misma interfaz pública que AutoRoutingPolicy (.route()). Construcción
    simétrica desde WISH-ARCH-001 resuelto: el optimizer pasa el sizing y
    esta clase instancia su propio ConnectionRouterManager.
    """

    def __init__(self, sizing_or_router_manager=None):
        """
        Args:
            sizing_or_router_manager: nuevo modo — SizingCalculator (preferido).
                Legacy — ConnectionRouterManager (retrocompat con scripts antiguos).
                None: construye router_manager interno con sizing default.
        """
        # Detectar modo: si parece SizingCalculator (tiene get_element_size) o
        # ConnectionRouterManager (tiene calculate_all_paths), o None.
        if sizing_or_router_manager is None:
            self._sizing = None
            self._router_manager = ConnectionRouterManager()
        elif hasattr(sizing_or_router_manager, 'calculate_all_paths'):
            # Legacy: caller pasó un ConnectionRouterManager ya construido
            self._sizing = None
            self._router_manager = sizing_or_router_manager
        else:
            # Nuevo: caller pasó un SizingCalculator
            self._sizing = sizing_or_router_manager
            self._router_manager = ConnectionRouterManager()

    @property
    def enabled(self) -> bool:
        """Compatibilidad: siempre True ahora (router se construye internamente).

        Conservado por uso en optimizer.py:Fase 10.5 (re-optimize_contained_labels).
        Podría eliminarse cuando todos los call-sites se actualicen.
        """
        return self._router_manager is not None

    def route(self, layout):
        """Calcula paths de todas las conexiones del layout."""
        if self._sizing is not None:
            layout.sizing = self._sizing
        self._router_manager.calculate_all_paths(layout)
