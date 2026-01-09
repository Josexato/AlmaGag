"""
AlmaGag.routing - Connection Routing System

This module provides declarative routing for connections between elements.
Supports multiple routing types:
- straight: Direct line (default)
- orthogonal: H-V or V-H lines
- bezier: Smooth curves
- arc: Circular arcs (for self-loops)
- manual: Explicit waypoints (v1.5 compatibility)

Author: José + ALMA
Version: v2.1
Date: 2026-01-08
"""

from AlmaGag.routing.router_base import ConnectionRouter, Path, Point
from AlmaGag.routing.straight_router import StraightRouter
from AlmaGag.routing.manual_router import ManualRouter
from AlmaGag.routing.orthogonal_router import OrthogonalRouter
from AlmaGag.routing.bezier_router import BezierRouter
from AlmaGag.routing.arc_router import ArcRouter
from AlmaGag.routing.router_manager import ConnectionRouterManager

__all__ = [
    'ConnectionRouter',
    'Path',
    'Point',
    'StraightRouter',
    'ManualRouter',
    'OrthogonalRouter',
    'BezierRouter',
    'ArcRouter',
    'ConnectionRouterManager'
]
