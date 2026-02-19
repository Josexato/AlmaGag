"""
OrthogonalRouter - Orthogonal (H-V or V-H) line routing

Generates horizontal and vertical lines for architectural-style diagrams.
Uses obstacle-aware visibility graph routing (v3.1) with fallback to
naive midpoint routing.

Author: José + ALMA
Version: v3.1
Date: 2026-02-19
"""

import math
from typing import List
from AlmaGag.routing.router_base import ConnectionRouter, Path, Point
from AlmaGag.config import CORNER_RADIUS_DEFAULT
from AlmaGag.routing.visibility_graph import find_orthogonal_path


class OrthogonalRouter(ConnectionRouter):
    """
    Router that creates orthogonal (H-V or V-H) paths between elements.

    v3.1: Uses orthogonal visibility graph for obstacle avoidance.
    Falls back to naive midpoint routing when visibility graph finds no path.

    Supports:
    - Obstacle-aware routing via visibility graph
    - Auto preference detection (fallback)
    - Manual preference (horizontal/vertical)
    - Corner radius for rounded corners
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

        Strategy:
        1. Try visibility graph routing (obstacle-aware)
        2. Fall back to naive midpoint routing if visibility graph fails

        Args:
            from_elem: Source element
            to_elem: Target element
            connection: Connection dict with optional routing config
            layout: Layout object with all elements for collision detection

        Returns:
            Path: Orthogonal polyline path
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

        # Get routing configuration
        routing = connection.get('routing', {})
        preference = routing.get('preference', 'auto')
        corner_radius = routing.get('corner_radius', CORNER_RADIUS_DEFAULT)

        # v3.0: Detect container boundaries
        from_container = self._find_parent_container(from_elem.get('id'), layout)
        to_container = self._find_parent_container(to_elem.get('id'), layout)

        # For container-crossing connections, use container boundary logic
        if from_container and not to_container:
            exit_point = self._calculate_container_entry_point(
                from_container, to_center, from_center, sizing_calculator
            )
            waypoints = self._calculate_orthogonal_waypoints_with_intermediate(
                from_center, exit_point, to_center, preference
            )
        elif to_container and not from_container:
            entry_point = self._calculate_container_entry_point(
                to_container, from_center, to_center, sizing_calculator
            )
            waypoints = self._calculate_orthogonal_waypoints_with_intermediate(
                from_center, entry_point, to_center, preference
            )
        elif from_container and to_container and from_container.get('id') != to_container.get('id'):
            exit_point = self._calculate_container_entry_point(
                from_container, to_center, from_center, sizing_calculator
            )
            entry_point = self._calculate_container_entry_point(
                to_container, from_center, to_center, sizing_calculator
            )
            waypoints = self._calculate_orthogonal_waypoints_multi(
                [from_center, exit_point, entry_point, to_center], preference
            )
        else:
            # Normal routing: try visibility graph first
            waypoints = self._route_with_visibility_graph(
                from_center, to_center,
                from_elem, to_elem,
                layout, sizing_calculator, preference
            )

        return Path(
            type='polyline',
            points=waypoints,
            corner_radius=corner_radius if corner_radius > 0 else None
        )

    def _route_with_visibility_graph(
        self,
        from_center: Point,
        to_center: Point,
        from_elem: dict,
        to_elem: dict,
        layout,
        sizing_calculator,
        preference: str
    ) -> List[Point]:
        """
        Try visibility graph routing, fall back to naive midpoint.

        Start/end points are pre-assigned ports on element borders
        (distributed by port_assignment across 12 angular sectors).
        """
        from_id = from_elem.get('id', '')
        to_id = to_elem.get('id', '')

        # Only use visibility graph if there are enough elements to warrant it
        if hasattr(layout, 'elements') and len(layout.elements) > 2:
            vg_path = find_orthogonal_path(
                from_center, to_center,
                layout, from_id, to_id,
                sizing_calculator
            )
            if vg_path and len(vg_path) >= 2:
                return vg_path

        # Fallback: naive midpoint routing
        return self._calculate_orthogonal_waypoints(from_center, to_center, preference)

    def _calculate_orthogonal_waypoints(
        self,
        from_point: Point,
        to_point: Point,
        preference: str
    ) -> List[Point]:
        """
        Calculate orthogonal waypoints using naive midpoint strategy (fallback).
        """
        dx = to_point.x - from_point.x
        dy = to_point.y - from_point.y

        if abs(dx) < 1:
            return [from_point, to_point]
        if abs(dy) < 1:
            return [from_point, to_point]

        if preference == 'auto':
            preference = 'horizontal' if abs(dx) > abs(dy) else 'vertical'

        if preference == 'horizontal':
            return self._horizontal_first_waypoints(from_point, to_point, dx, dy)
        else:
            return self._vertical_first_waypoints(from_point, to_point, dx, dy)

    def _horizontal_first_waypoints(
        self,
        from_point: Point,
        to_point: Point,
        dx: float,
        dy: float
    ) -> List[Point]:
        """Generate H-V waypoints (horizontal first, then vertical)."""
        mid_x = from_point.x + dx / 2
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
        """Generate V-H waypoints (vertical first, then horizontal)."""
        mid_y = from_point.y + dy / 2
        waypoint1 = Point(from_point.x, mid_y)
        waypoint2 = Point(to_point.x, mid_y)
        return [from_point, waypoint1, waypoint2, to_point]

    def _calculate_orthogonal_waypoints_with_intermediate(
        self,
        from_point: Point,
        intermediate_point: Point,
        to_point: Point,
        preference: str
    ) -> List[Point]:
        """Calculate orthogonal waypoints through an intermediate point (container border)."""
        segment1 = self._calculate_orthogonal_waypoints(from_point, intermediate_point, preference)
        segment2 = self._calculate_orthogonal_waypoints(intermediate_point, to_point, preference)
        return segment1[:-1] + segment2

    def _calculate_orthogonal_waypoints_multi(
        self,
        points: List[Point],
        preference: str
    ) -> List[Point]:
        """Calculate orthogonal waypoints through multiple required points."""
        if len(points) < 2:
            return points

        all_waypoints = []
        for i in range(len(points) - 1):
            segment = self._calculate_orthogonal_waypoints(points[i], points[i + 1], preference)
            if i == 0:
                all_waypoints.extend(segment)
            else:
                all_waypoints.extend(segment[1:])

        return all_waypoints
