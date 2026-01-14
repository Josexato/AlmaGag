"""
OrthogonalRouter - Orthogonal (H-V or V-H) line routing

Generates horizontal and vertical lines for architectural-style diagrams.
Supports automatic preference detection and corner radius.

Author: José + ALMA
Version: v2.1
Date: 2026-01-08
"""

import math
from typing import List
from AlmaGag.routing.router_base import ConnectionRouter, Path, Point


class OrthogonalRouter(ConnectionRouter):
    """
    Router that creates orthogonal (H-V or V-H) paths between elements.

    The router automatically determines whether to go horizontal-first or
    vertical-first based on element positions, or you can specify a preference.

    Supports:
    - Auto preference detection
    - Manual preference (horizontal/vertical)
    - Corner radius for rounded corners
    - avoid_elements (future: collision avoidance)
    """

    def calculate_path(
        self,
        from_elem: dict,
        to_elem: dict,
        connection: dict,
        layout
    ) -> Path:
        """
        Calculate orthogonal path between two elements.

        Args:
            from_elem: Source element
            to_elem: Target element
            connection: Connection dict with optional routing config:
                - preference: 'auto', 'horizontal', or 'vertical'
                - corner_radius: radius for rounded corners (default: 0)
                - avoid_elements: enable collision avoidance (default: false)
            layout: Layout object (for future collision detection)

        Returns:
            Path: Orthogonal polyline path with 2-4 points
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
        preference = routing.get('preference', 'auto')
        corner_radius = routing.get('corner_radius', 0)
        # avoid_elements = routing.get('avoid_elements', False)  # Future: Phase 5

        # Calculate orthogonal waypoints
        waypoints = self._calculate_orthogonal_waypoints(
            from_center,
            to_center,
            preference
        )

        # Create path
        return Path(
            type='polyline',
            points=waypoints,
            corner_radius=corner_radius if corner_radius > 0 else None
        )

    def _calculate_orthogonal_waypoints(
        self,
        from_point: Point,
        to_point: Point,
        preference: str
    ) -> List[Point]:
        """
        Calculate orthogonal waypoints between two points.

        Strategy:
        1. Determine if we should go horizontal-first or vertical-first
        2. Generate 2-4 waypoints creating a right-angle path
        3. Simplify path if possible (e.g., if aligned, use direct line)

        Args:
            from_point: Start point
            to_point: End point
            preference: 'auto', 'horizontal', or 'vertical'

        Returns:
            List[Point]: Waypoints including start and end
        """
        dx = to_point.x - from_point.x
        dy = to_point.y - from_point.y

        # If points are aligned, use direct line
        if abs(dx) < 1:
            # Vertically aligned
            return [from_point, to_point]
        if abs(dy) < 1:
            # Horizontally aligned
            return [from_point, to_point]

        # Determine preference
        if preference == 'auto':
            # Decide based on distance - go in the direction with more distance first
            preference = 'horizontal' if abs(dx) > abs(dy) else 'vertical'

        # Generate waypoints based on preference
        if preference == 'horizontal':
            # Horizontal first: go right/left, then up/down
            waypoints = self._horizontal_first_waypoints(from_point, to_point, dx, dy)
        else:
            # Vertical first: go up/down, then right/left
            waypoints = self._vertical_first_waypoints(from_point, to_point, dx, dy)

        return waypoints

    def _horizontal_first_waypoints(
        self,
        from_point: Point,
        to_point: Point,
        dx: float,
        dy: float
    ) -> List[Point]:
        """
        Generate H-V waypoints (horizontal first, then vertical).

        Path: Start -> (midpoint_x, from_y) -> (midpoint_x, to_y) -> End

        Args:
            from_point: Start point
            to_point: End point
            dx: Horizontal distance
            dy: Vertical distance

        Returns:
            List[Point]: 4 waypoints forming H-V path
        """
        # Calculate midpoint X (where we switch from horizontal to vertical)
        mid_x = from_point.x + dx / 2

        # Create waypoints
        waypoint1 = Point(mid_x, from_point.y)
        waypoint2 = Point(mid_x, to_point.y)

        return [from_point, waypoint1, waypoint2, to_point]

    def _vertical_first_waypoints(
        self,
        from_point: Point,
        to_point: Point,
        dx: float,
        dy: float
    ) -> List[Point]:
        """
        Generate V-H waypoints (vertical first, then horizontal).

        Path: Start -> (from_x, midpoint_y) -> (to_x, midpoint_y) -> End

        Args:
            from_point: Start point
            to_point: End point
            dx: Horizontal distance
            dy: Vertical distance

        Returns:
            List[Point]: 4 waypoints forming V-H path
        """
        # Calculate midpoint Y (where we switch from vertical to horizontal)
        mid_y = from_point.y + dy / 2

        # Create waypoints
        waypoint1 = Point(from_point.x, mid_y)
        waypoint2 = Point(to_point.x, mid_y)

        return [from_point, waypoint1, waypoint2, to_point]
