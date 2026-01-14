"""
BezierRouter - Smooth Bézier curve routing

Generates smooth cubic Bézier curves between elements.
Useful for flow diagrams and organic-looking connections.

Author: José + ALMA
Version: v2.1
Date: 2026-01-08
"""

import math
from AlmaGag.routing.router_base import ConnectionRouter, Path, Point


class BezierRouter(ConnectionRouter):
    """
    Router that creates smooth Bézier curves between elements.

    Uses cubic Bézier curves with control points calculated based
    on the vector between elements and a curvature parameter.

    Supports:
    - Adjustable curvature (0.0 = nearly straight, 1.0 = very curved)
    - Automatic control point calculation
    """

    def calculate_path(
        self,
        from_elem: dict,
        to_elem: dict,
        connection: dict,
        layout
    ) -> Path:
        """
        Calculate Bézier curve path between two elements.

        Args:
            from_elem: Source element
            to_elem: Target element
            connection: Connection dict with optional routing config:
                - curvature: curve intensity [0.0, 1.0] (default: 0.5)
            layout: Layout object

        Returns:
            Path: Bézier path with start, end, and control points
        """
        # Get sizing calculator from layout if available
        sizing_calculator = getattr(layout, 'sizing', None)

        # Calculate connection points (handles containers intelligently)
        # Need to calculate both centers first to determine the other point
        from_center_temp = self.get_element_center(from_elem, sizing_calculator)
        to_center_temp = self.get_element_center(to_elem, sizing_calculator)

        # Now calculate actual connection points (may be on container borders)
        from_center = self.get_connection_point(from_elem, to_center_temp, layout, sizing_calculator)
        to_center = self.get_connection_point(to_elem, from_center_temp, layout, sizing_calculator)

        # Get routing configuration
        routing = connection.get('routing', {})
        curvature = routing.get('curvature', 0.5)

        # Clamp curvature to valid range
        curvature = max(0.0, min(1.0, curvature))

        # Calculate control points
        control_points = self._calculate_bezier_control_points(
            from_center,
            to_center,
            curvature
        )

        # Create path
        return Path(
            type='bezier',
            points=[from_center, to_center],
            control_points=control_points
        )

    def _calculate_bezier_control_points(
        self,
        from_point: Point,
        to_point: Point,
        curvature: float
    ) -> list:
        """
        Calculate control points for cubic Bézier curve.

        Strategy:
        1. Calculate vector from start to end
        2. Calculate perpendicular vector
        3. Place control points along the path, offset perpendicular
        4. Distance of offset = distance(start, end) * curvature

        Args:
            from_point: Start point
            to_point: End point
            curvature: Curve intensity [0.0, 1.0]

        Returns:
            list[Point]: Two control points for cubic Bézier
        """
        # Calculate vector and distance
        dx = to_point.x - from_point.x
        dy = to_point.y - from_point.y
        distance = math.sqrt(dx**2 + dy**2)

        if distance < 1:
            # Points too close, return midpoint controls
            mid = Point(
                (from_point.x + to_point.x) / 2,
                (from_point.y + to_point.y) / 2
            )
            return [mid, mid]

        # Calculate control offset based on curvature
        control_offset = distance * curvature * 0.5

        # Calculate perpendicular vector (rotate 90 degrees)
        perp_x = -dy / distance
        perp_y = dx / distance

        # Place control points along the path, offset perpendicular
        # Control point 1: 1/3 along the path
        control1 = Point(
            from_point.x + dx / 3 + perp_x * control_offset,
            from_point.y + dy / 3 + perp_y * control_offset
        )

        # Control point 2: 2/3 along the path
        control2 = Point(
            from_point.x + 2 * dx / 3 + perp_x * control_offset,
            from_point.y + 2 * dy / 3 + perp_y * control_offset
        )

        return [control1, control2]
