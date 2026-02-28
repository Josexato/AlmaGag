"""
StraightRouter - Simple straight line routing

Generates direct line between two elements.
This is the default routing type (backward compatible with v1.0/v2.0).

Author: José + ALMA
Version: v2.1
Date: 2026-01-08
"""

from AlmaGag.routing.router_base import ConnectionRouter, Path, Point


class StraightRouter(ConnectionRouter):
    """
    Router that creates straight lines between elements.

    This is the simplest and fastest routing method.
    Compatible with SDJF v1.0 and v2.0.
    """

    def calculate_path(
        self,
        from_elem: dict,
        to_elem: dict,
        connection: dict,
        layout
    ) -> Path:
        """
        Calculate a straight line path between two elements.

        Args:
            from_elem: Source element
            to_elem: Target element
            connection: Connection dict (routing options ignored for straight lines)
            layout: Layout object (unused for straight routing)

        Returns:
            Path: Straight line path with two points
        """
        # Get sizing calculator from layout if available
        sizing_calculator = getattr(layout, 'sizing', None)

        # Use assigned ports if available (from port_assignment pre-step)
        from_port = connection.get('_from_port')
        to_port = connection.get('_to_port')

        if from_port and to_port:
            from_center = from_port
            to_center = to_port
        else:
            # Fallback: calculate connection points traditionally
            from_center_temp = self.get_element_center(from_elem, sizing_calculator)
            to_center_temp = self.get_element_center(to_elem, sizing_calculator)
            from_center = self.get_connection_point(from_elem, to_center_temp, layout, sizing_calculator)
            to_center = self.get_connection_point(to_elem, from_center_temp, layout, sizing_calculator)

        # Create simple line path
        return Path(
            type='line',
            points=[from_center, to_center]
        )
