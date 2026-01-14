"""
ManualRouter - Explicit waypoint routing

Supports manual waypoints for full control over path.
Backward compatible with SDJF v1.5.

Author: José + ALMA
Version: v2.1
Date: 2026-01-08
"""

from AlmaGag.routing.router_base import ConnectionRouter, Path, Point


class ManualRouter(ConnectionRouter):
    """
    Router that uses explicitly defined waypoints.

    This provides full manual control over the connection path.
    Backward compatible with SDJF v1.5 waypoints.

    Note: Manual waypoints have fixed coordinates and don't adapt
    if elements are moved by auto-layout.
    """

    def calculate_path(
        self,
        from_elem: dict,
        to_elem: dict,
        connection: dict,
        layout
    ) -> Path:
        """
        Calculate path using manual waypoints.

        Args:
            from_elem: Source element
            to_elem: Target element
            connection: Connection dict with 'routing' containing 'waypoints'
            layout: Layout object (unused for manual routing)

        Returns:
            Path: Polyline path with manual waypoints
        """
        # Get sizing calculator from layout if available
        sizing_calculator = getattr(layout, 'sizing', None)

        # Get waypoints from routing config
        routing = connection.get('routing', {})
        waypoints_data = routing.get('waypoints', [])

        # Convert waypoint dicts to Point objects
        waypoints = [Point.from_dict(wp) for wp in waypoints_data]

        # Calculate connection points (handles containers intelligently)
        # For manual routing, use the first/last waypoint as reference if available
        if waypoints:
            # Use first waypoint as reference for 'from' connection point
            # Use last waypoint as reference for 'to' connection point
            from_center = self.get_connection_point(from_elem, waypoints[0], layout, sizing_calculator)
            to_center = self.get_connection_point(to_elem, waypoints[-1], layout, sizing_calculator)
        else:
            # No waypoints - calculate connection points using each other as reference
            from_center_temp = self.get_element_center(from_elem, sizing_calculator)
            to_center_temp = self.get_element_center(to_elem, sizing_calculator)
            from_center = self.get_connection_point(from_elem, to_center_temp, layout, sizing_calculator)
            to_center = self.get_connection_point(to_elem, from_center_temp, layout, sizing_calculator)

        # Build complete path: start -> waypoints -> end
        points = [from_center] + waypoints + [to_center]

        return Path(
            type='polyline',
            points=points
        )
