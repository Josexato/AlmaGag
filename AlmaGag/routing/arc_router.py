"""
ArcRouter - Circular arc routing

Generates circular arcs, primarily for self-loops and feedback connections.
Useful for showing recursive relationships or loops.

Author: José + ALMA
Version: v2.1
Date: 2026-01-08
"""

import math
from AlmaGag.routing.router_base import ConnectionRouter, Path, Point


class ArcRouter(ConnectionRouter):
    """
    Router that creates circular arcs between elements.

    Particularly useful for self-loops (element connecting to itself).
    Can also be used for regular connections to create curved paths.

    Supports:
    - Self-loops with customizable side
    - Adjustable arc radius
    - Automatic arc calculation for regular connections
    """

    def calculate_path(
        self,
        from_elem: dict,
        to_elem: dict,
        connection: dict,
        layout
    ) -> Path:
        """
        Calculate arc path between two elements.

        Args:
            from_elem: Source element
            to_elem: Target element
            connection: Connection dict with optional routing config:
                - radius: arc radius in pixels (default: 50)
                - side: side of element for self-loops - 'top', 'bottom', 'left', 'right' (default: 'top')
            layout: Layout object

        Returns:
            Path: Arc path with start, end, arc center, and radius
        """
        # Get sizing calculator from layout if available
        sizing_calculator = getattr(layout, 'sizing', None)

        # Calculate centers and sizes
        from_center = self.get_element_center(from_elem, sizing_calculator)
        to_center = self.get_element_center(to_elem, sizing_calculator)

        # Get routing configuration
        routing = connection.get('routing', {})
        radius = routing.get('radius', 50)
        side = routing.get('side', 'top')

        # Check if this is a self-loop
        if from_elem['id'] == to_elem['id']:
            # Self-loop
            return self._calculate_self_loop_arc(
                from_center,
                from_elem,
                radius,
                side,
                sizing_calculator
            )
        else:
            # Regular connection with arc
            return self._calculate_connection_arc(
                from_center,
                to_center,
                radius
            )

    def _calculate_self_loop_arc(
        self,
        center: Point,
        element: dict,
        radius: float,
        side: str,
        sizing_calculator
    ) -> Path:
        """
        Calculate arc for self-loop.

        Creates an arc that starts from one edge of the element,
        loops around, and returns to a nearby point on the same edge.

        Args:
            center: Center of element
            element: Element dict
            radius: Arc radius
            side: Which side to place the loop ('top', 'bottom', 'left', 'right')
            sizing_calculator: Optional sizing calculator

        Returns:
            Path: Arc path for self-loop
        """
        # Get element size
        if sizing_calculator:
            width, height = sizing_calculator.get_element_size(element)
        else:
            from AlmaGag.config import ICON_WIDTH, ICON_HEIGHT
            width, height = ICON_WIDTH, ICON_HEIGHT

        # Calculate start and end points based on side
        offset = 20  # Distance between start and end points

        if side == 'top':
            start = Point(center.x - offset, center.y - height / 2)
            end = Point(center.x + offset, center.y - height / 2)
            arc_center = Point(center.x, center.y - height / 2 - radius)
        elif side == 'bottom':
            start = Point(center.x - offset, center.y + height / 2)
            end = Point(center.x + offset, center.y + height / 2)
            arc_center = Point(center.x, center.y + height / 2 + radius)
        elif side == 'left':
            start = Point(center.x - width / 2, center.y - offset)
            end = Point(center.x - width / 2, center.y + offset)
            arc_center = Point(center.x - width / 2 - radius, center.y)
        else:  # right
            start = Point(center.x + width / 2, center.y - offset)
            end = Point(center.x + width / 2, center.y + offset)
            arc_center = Point(center.x + width / 2 + radius, center.y)

        return Path(
            type='arc',
            points=[start, end],
            arc_center=arc_center,
            radius=radius
        )

    def _calculate_connection_arc(
        self,
        from_point: Point,
        to_point: Point,
        radius: float
    ) -> Path:
        """
        Calculate arc for regular connection (not self-loop).

        Creates an arc path between two different elements.
        The arc center is calculated perpendicular to the line between points.

        Args:
            from_point: Start point
            to_point: End point
            radius: Arc radius

        Returns:
            Path: Arc path for connection
        """
        # Calculate midpoint
        mid_x = (from_point.x + to_point.x) / 2
        mid_y = (from_point.y + to_point.y) / 2

        # Calculate vector and perpendicular
        dx = to_point.x - from_point.x
        dy = to_point.y - from_point.y
        distance = math.sqrt(dx**2 + dy**2)

        if distance < 1:
            # Points too close, return simple arc
            return Path(
                type='arc',
                points=[from_point, to_point],
                arc_center=Point(mid_x, mid_y),
                radius=radius
            )

        # Perpendicular vector
        perp_x = -dy / distance
        perp_y = dx / distance

        # Arc center offset from midpoint
        arc_center = Point(
            mid_x + perp_x * radius,
            mid_y + perp_y * radius
        )

        return Path(
            type='arc',
            points=[from_point, to_point],
            arc_center=arc_center,
            radius=radius
        )
