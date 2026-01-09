"""
ConnectionRouterManager - Manages routing for all connections

Coordinates different router types and handles backward compatibility
with SDJF v1.5 waypoints.

Author: José + ALMA
Version: v2.1
Date: 2026-01-08
"""

from typing import Dict
from AlmaGag.routing.router_base import ConnectionRouter
from AlmaGag.routing.straight_router import StraightRouter
from AlmaGag.routing.manual_router import ManualRouter
from AlmaGag.routing.orthogonal_router import OrthogonalRouter
from AlmaGag.routing.bezier_router import BezierRouter
from AlmaGag.routing.arc_router import ArcRouter


class ConnectionRouterManager:
    """
    Manages routing for all connections in a layout.

    Handles:
    - Router type selection
    - Backward compatibility with v1.5 waypoints
    - Default routing when type not specified
    """

    def __init__(self):
        """Initialize router manager with available routers."""
        self.routers: Dict[str, ConnectionRouter] = {
            'straight': StraightRouter(),
            'manual': ManualRouter(),
            'orthogonal': OrthogonalRouter(),
            'bezier': BezierRouter(),
            'arc': ArcRouter(),
        }
        self.default_router = 'straight'

    def register_router(self, name: str, router: ConnectionRouter):
        """
        Register a new router type.

        Args:
            name: Router type name (e.g., 'orthogonal', 'bezier', 'arc')
            router: Router instance
        """
        self.routers[name] = router

    def calculate_all_paths(self, layout):
        """
        Calculate paths for all connections in the layout.

        This modifies each connection dict by adding a 'computed_path' field.

        Args:
            layout: Layout object with connections and elements_by_id
        """
        for connection in layout.connections:
            self._calculate_connection_path(connection, layout)

    def _calculate_connection_path(self, connection: dict, layout):
        """
        Calculate path for a single connection.

        Handles backward compatibility:
        - If connection has 'waypoints' at root level (v1.5), convert to manual routing
        - If connection has 'routing', use specified type
        - Otherwise, use default (straight)

        Args:
            connection: Connection dict
            layout: Layout object
        """
        # Get source and target elements
        from_elem = layout.elements_by_id.get(connection['from'])
        to_elem = layout.elements_by_id.get(connection['to'])

        # Skip if elements don't exist or don't have coordinates
        if not from_elem or not to_elem:
            return
        if from_elem.get('x') is None or from_elem.get('y') is None:
            return
        if to_elem.get('x') is None or to_elem.get('y') is None:
            return

        # Determine routing type
        routing = self._get_routing_config(connection)
        router_type = routing.get('type', self.default_router)

        # Get appropriate router
        router = self.routers.get(router_type, self.routers[self.default_router])

        # Calculate path
        path = router.calculate_path(from_elem, to_elem, connection, layout)

        # Store computed path in connection
        connection['computed_path'] = path.to_dict()

    def _get_routing_config(self, connection: dict) -> dict:
        """
        Get routing configuration from connection.

        Handles backward compatibility with v1.5 waypoints.

        Args:
            connection: Connection dict

        Returns:
            dict: Routing configuration
        """
        # Check if connection has 'routing' property (v2.1+)
        if 'routing' in connection:
            return connection['routing']

        # Check for v1.5 waypoints at root level
        if 'waypoints' in connection:
            # Convert v1.5 format to v2.1 format
            return {
                'type': 'manual',
                'waypoints': connection['waypoints']
            }

        # Default: straight line
        return {'type': self.default_router}
