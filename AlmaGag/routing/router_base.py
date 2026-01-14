"""
ConnectionRouter - Base class for connection routing

Defines the interface and data structures for all routing types.

Author: José + ALMA
Version: v2.1
Date: 2026-01-08
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional, Tuple, Any


@dataclass
class Point:
    """Represents a 2D point."""
    x: float
    y: float

    def to_tuple(self) -> Tuple[float, float]:
        """Convert to (x, y) tuple."""
        return (self.x, self.y)

    @classmethod
    def from_dict(cls, data: dict) -> 'Point':
        """Create Point from dict with 'x' and 'y' keys."""
        return cls(x=data['x'], y=data['y'])

    @classmethod
    def from_tuple(cls, data: Tuple[float, float]) -> 'Point':
        """Create Point from (x, y) tuple."""
        return cls(x=data[0], y=data[1])


@dataclass
class Path:
    """
    Represents a computed path for a connection.

    Attributes:
        type: Type of path ('line', 'polyline', 'bezier', 'arc')
        points: Main points of the path
        control_points: Control points for bezier curves (optional)
        arc_center: Center point for arcs (optional)
        radius: Radius for arcs (optional)
        corner_radius: Radius for rounded corners in polylines (optional)
    """
    type: str
    points: List[Point]
    control_points: Optional[List[Point]] = None
    arc_center: Optional[Point] = None
    radius: Optional[float] = None
    corner_radius: Optional[float] = None

    def to_dict(self) -> dict:
        """Convert Path to dictionary for storage in connection."""
        result = {
            'type': self.type,
            'points': [p.to_tuple() for p in self.points]
        }

        if self.control_points:
            result['control_points'] = [p.to_tuple() for p in self.control_points]
        if self.arc_center:
            result['arc_center'] = self.arc_center.to_tuple()
        if self.radius is not None:
            result['radius'] = self.radius
        if self.corner_radius is not None:
            result['corner_radius'] = self.corner_radius

        return result


class ConnectionRouter(ABC):
    """
    Abstract base class for connection routers.

    Each router type (straight, orthogonal, bezier, arc) implements
    the calculate_path method to compute waypoints and path geometry.
    """

    @abstractmethod
    def calculate_path(
        self,
        from_elem: dict,
        to_elem: dict,
        connection: dict,
        layout: Any
    ) -> Path:
        """
        Calculate the path for a connection between two elements.

        Args:
            from_elem: Source element (dict with at least 'x', 'y', 'type')
            to_elem: Target element (dict with at least 'x', 'y', 'type')
            connection: Connection dict (may contain 'routing' with type-specific options)
            layout: Layout object containing all elements (for collision detection)

        Returns:
            Path: Computed path with waypoints and geometry
        """
        pass

    def get_element_center(self, element: dict, sizing_calculator=None) -> Point:
        """
        Calculate the center point of an element.

        Args:
            element: Element with 'x', 'y', and optionally 'hp', 'wp'
            sizing_calculator: Optional SizingCalculator for proportional sizing

        Returns:
            Point: Center coordinates of the element
        """
        from AlmaGag.config import ICON_WIDTH, ICON_HEIGHT

        x = element.get('x', 0)
        y = element.get('y', 0)

        # Use sizing calculator if available
        if sizing_calculator:
            width, height = sizing_calculator.get_element_size(element)
        else:
            width, height = ICON_WIDTH, ICON_HEIGHT

        return Point(
            x=x + width / 2,
            y=y + height / 2
        )

    def get_element_size(self, element: dict, sizing_calculator=None) -> Tuple[float, float]:
        """
        Get the size of an element.

        Args:
            element: Element with optionally 'hp', 'wp', 'width', 'height'
            sizing_calculator: Optional SizingCalculator for proportional sizing

        Returns:
            Tuple[float, float]: (width, height)
        """
        from AlmaGag.config import ICON_WIDTH, ICON_HEIGHT

        if sizing_calculator:
            return sizing_calculator.get_element_size(element)
        return (ICON_WIDTH, ICON_HEIGHT)

    def get_connection_point(
        self,
        element: dict,
        other_point: Point,
        layout: Any,
        sizing_calculator=None
    ) -> Point:
        """
        Calculate the connection point for an element.

        Logic:
        1. If element is a container:
           - Check if user specified a border element in the connection (future)
           - If container has border elements, use the closest one
           - Otherwise, calculate intersection with container border (shortest line)
        2. If element is not a container:
           - Return center of the element

        Args:
            element: Element to connect to
            other_point: The point on the other end of the connection
            layout: Layout object with elements_by_id
            sizing_calculator: Optional SizingCalculator for proportional sizing

        Returns:
            Point: Connection point
        """
        # Check if element is a container
        if 'contains' in element and element.get('contains'):
            # It's a container - find border elements
            border_elements = []
            for contained in element['contains']:
                if isinstance(contained, dict) and contained.get('scope') == 'border':
                    # Find the actual element
                    contained_id = contained['id']
                    contained_elem = layout.elements_by_id.get(contained_id)
                    if contained_elem and contained_elem.get('x') is not None:
                        border_elements.append(contained_elem)

            if border_elements:
                # Use the closest border element to the other point
                closest = min(
                    border_elements,
                    key=lambda e: self._distance_to_point(e, other_point, sizing_calculator)
                )
                return self.get_element_center(closest, sizing_calculator)
            else:
                # No border elements - calculate intersection with container border
                container_center = self.get_element_center(element, sizing_calculator)
                width, height = self.get_element_size(element, sizing_calculator)

                return self._calculate_border_intersection(
                    container_center,
                    width,
                    height,
                    other_point
                )
        else:
            # Not a container - return center
            return self.get_element_center(element, sizing_calculator)

    def _distance_to_point(
        self,
        element: dict,
        point: Point,
        sizing_calculator=None
    ) -> float:
        """
        Calculate distance from element center to a point.

        Args:
            element: Element with 'x', 'y'
            point: Point to measure distance to
            sizing_calculator: Optional SizingCalculator

        Returns:
            float: Distance
        """
        center = self.get_element_center(element, sizing_calculator)
        dx = center.x - point.x
        dy = center.y - point.y
        return (dx**2 + dy**2)**0.5

    def _calculate_border_intersection(
        self,
        center: Point,
        width: float,
        height: float,
        external_point: Point,
        extend_by: float = 15.0
    ) -> Point:
        """
        Calculate intersection point between a line from center to external_point
        and the border of a rectangle.

        Args:
            center: Center of the rectangle
            width: Width of the rectangle
            height: Height of the rectangle
            external_point: Point outside the rectangle
            extend_by: Extra pixels to extend beyond border (to compensate for arrow marker size)

        Returns:
            Point: Intersection point on the rectangle border (extended slightly beyond)
        """
        # Rectangle bounds
        x1 = center.x - width / 2
        y1 = center.y - height / 2
        x2 = center.x + width / 2
        y2 = center.y + height / 2

        # Direction vector from center to external point
        dx = external_point.x - center.x
        dy = external_point.y - center.y

        # Handle case where external point is at center
        if abs(dx) < 0.1 and abs(dy) < 0.1:
            # Return top center of rectangle as default
            return Point(center.x, y1)

        # Normalize direction vector
        length = (dx**2 + dy**2)**0.5
        if length > 0:
            dx_norm = dx / length
            dy_norm = dy / length
        else:
            dx_norm = 0
            dy_norm = -1

        # Calculate which edge the line intersects
        # Using parametric line equation: P = center + t * (dx, dy)
        # Find t where P intersects rectangle border

        t_values = []

        # Left edge (x = x1)
        if abs(dx) > 0.1:
            t = (x1 - center.x) / dx
            if t > 0:
                py = center.y + t * dy
                if y1 <= py <= y2:
                    t_values.append((t, Point(x1, py)))

        # Right edge (x = x2)
        if abs(dx) > 0.1:
            t = (x2 - center.x) / dx
            if t > 0:
                py = center.y + t * dy
                if y1 <= py <= y2:
                    t_values.append((t, Point(x2, py)))

        # Top edge (y = y1)
        if abs(dy) > 0.1:
            t = (y1 - center.y) / dy
            if t > 0:
                px = center.x + t * dx
                if x1 <= px <= x2:
                    t_values.append((t, Point(px, y1)))

        # Bottom edge (y = y2)
        if abs(dy) > 0.1:
            t = (y2 - center.y) / dy
            if t > 0:
                px = center.x + t * dx
                if x1 <= px <= x2:
                    t_values.append((t, Point(px, y2)))

        # Get the closest intersection (smallest t > 0)
        if t_values:
            t_values.sort(key=lambda x: x[0])
            intersection = t_values[0][1]

            # Extend the point slightly beyond the border to compensate for arrow marker
            # This ensures the arrow visually reaches the border
            # SUBTRACT to extend AWAY from center (outward), not inward
            extended_x = intersection.x - dx_norm * extend_by
            extended_y = intersection.y - dy_norm * extend_by

            return Point(extended_x, extended_y)

        # Fallback: return center if no intersection found
        return center
