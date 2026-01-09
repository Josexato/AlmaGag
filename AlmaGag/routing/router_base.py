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
            element: Element with optionally 'hp', 'wp'
            sizing_calculator: Optional SizingCalculator for proportional sizing

        Returns:
            Tuple[float, float]: (width, height)
        """
        from AlmaGag.config import ICON_WIDTH, ICON_HEIGHT

        if sizing_calculator:
            return sizing_calculator.get_element_size(element)
        return (ICON_WIDTH, ICON_HEIGHT)
