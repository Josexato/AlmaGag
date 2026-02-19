"""
PortAssignment - Distributes connection ports across 12 angular sectors

Each element has 12 angular sectors (every 30°). When multiple connections
approach from the same direction, they are distributed across parallel
slots within that sector.

Example: 5 connections arriving from above → 5 evenly-spaced points
within the 90° sector (75°-105°) on the top edge of the icon.

Author: José + ALMA
Version: v3.2
Date: 2026-02-19
"""

import math
from typing import Dict, List, Tuple, Optional
from collections import defaultdict
from AlmaGag.routing.router_base import Point
from AlmaGag.config import ICON_WIDTH, ICON_HEIGHT


# Number of angular sectors (every 30°)
NUM_SECTORS = 12
SECTOR_WIDTH = 360.0 / NUM_SECTORS  # 30°


def _get_element_rect(element: dict, sizing_calculator=None) -> Tuple[float, float, float, float]:
    """Get element center and half-dimensions: (cx, cy, half_w, half_h)."""
    x = element.get('x', 0)
    y = element.get('y', 0)

    if 'width' in element and 'height' in element:
        w, h = element['width'], element['height']
    elif sizing_calculator:
        w, h = sizing_calculator.get_element_size(element)
    else:
        hp = element.get('hp', 1.0)
        wp = element.get('wp', 1.0)
        w = ICON_WIDTH * wp
        h = ICON_HEIGHT * hp

    return (x + w / 2, y + h / 2, w / 2, h / 2)


def _angle_between(cx1: float, cy1: float, cx2: float, cy2: float) -> float:
    """
    Calculate angle in degrees from element 1 center to element 2 center.

    0° = right, 90° = up (SVG), 180° = left, 270° = down (SVG).
    Returns value in [0, 360).
    """
    dx = cx2 - cx1
    dy = cy1 - cy2  # Invert Y for SVG (Y grows downward)
    angle = math.degrees(math.atan2(dy, dx))
    return angle % 360


def _angle_to_sector(angle: float) -> int:
    """Map angle [0,360) to sector index [0,11]. Sector 0 centered at 0° (right)."""
    # Shift by half sector so sector 0 is centered at 0° (i.e., covers -15° to 15°)
    shifted = (angle + SECTOR_WIDTH / 2) % 360
    return int(shifted // SECTOR_WIDTH)


def _sector_to_angle_range(sector: int) -> Tuple[float, float]:
    """Get the angular range for a sector: (start_angle, end_angle) in degrees."""
    center = sector * SECTOR_WIDTH
    start = (center - SECTOR_WIDTH / 2) % 360
    end = (center + SECTOR_WIDTH / 2) % 360
    return start, end


def _ray_rect_intersection(cx: float, cy: float, half_w: float, half_h: float,
                           angle_deg: float) -> Point:
    """
    Calculate the intersection of a ray from center at given angle with the rectangle border.

    Args:
        cx, cy: Center of rectangle
        half_w, half_h: Half-width and half-height
        angle_deg: Angle in degrees (0°=right, 90°=up in SVG)

    Returns:
        Point on the rectangle border
    """
    angle_rad = math.radians(angle_deg)
    dx = math.cos(angle_rad)
    dy = -math.sin(angle_rad)  # SVG Y-axis inverted

    t_values = []

    # Right edge
    if abs(dx) > 1e-9:
        t = half_w / dx
        if t > 0:
            py = cy + t * dy
            if cy - half_h - 0.1 <= py <= cy + half_h + 0.1:
                t_values.append(t)

    # Left edge
    if abs(dx) > 1e-9:
        t = -half_w / dx
        if t > 0:
            py = cy + t * dy
            if cy - half_h - 0.1 <= py <= cy + half_h + 0.1:
                t_values.append(t)

    # Top edge
    if abs(dy) > 1e-9:
        t = -half_h / dy
        if t > 0:
            px = cx + t * dx
            if cx - half_w - 0.1 <= px <= cx + half_w + 0.1:
                t_values.append(t)

    # Bottom edge
    if abs(dy) > 1e-9:
        t = half_h / dy
        if t > 0:
            px = cx + t * dx
            if cx - half_w - 0.1 <= px <= cx + half_w + 0.1:
                t_values.append(t)

    if t_values:
        t_min = min(t_values)
        px = cx + t_min * dx
        py = cy + t_min * dy
        return Point(round(px, 1), round(py, 1))

    # Fallback
    return Point(cx, cy)


def assign_ports(layout, sizing_calculator=None):
    """
    Assign connection ports for all connections in the layout.

    For each element:
    1. Collect all connections involving this element
    2. Calculate angle to the other element → map to sector
    3. Within each sector, distribute N connections across N evenly-spaced slots
    4. Store assigned port points in the connection dict

    Each connection gets two port assignments:
    - '_from_port': Point on the source element's border
    - '_to_port': Point on the target element's border

    Args:
        layout: Layout object with elements_by_id and connections
        sizing_calculator: Optional sizing calculator
    """
    # Phase 1: Collect connections per element, grouped by sector
    # element_id -> sector -> [(connection_index, angle, is_source)]
    element_sectors: Dict[str, Dict[int, List[Tuple[int, float, bool]]]] = defaultdict(
        lambda: defaultdict(list)
    )

    for ci, conn in enumerate(layout.connections):
        from_id = conn['from']
        to_id = conn['to']

        from_elem = layout.elements_by_id.get(from_id)
        to_elem = layout.elements_by_id.get(to_id)

        if not from_elem or not to_elem:
            continue
        if from_elem.get('x') is None or to_elem.get('x') is None:
            continue

        from_cx, from_cy, _, _ = _get_element_rect(from_elem, sizing_calculator)
        to_cx, to_cy, _, _ = _get_element_rect(to_elem, sizing_calculator)

        # Skip self-loops
        if from_id == to_id:
            continue

        # Angle from source to target
        angle_from = _angle_between(from_cx, from_cy, to_cx, to_cy)
        sector_from = _angle_to_sector(angle_from)
        element_sectors[from_id][sector_from].append((ci, angle_from, True))

        # Angle from target to source (opposite direction)
        angle_to = _angle_between(to_cx, to_cy, from_cx, from_cy)
        sector_to = _angle_to_sector(angle_to)
        element_sectors[to_id][sector_to].append((ci, angle_to, False))

    # Phase 2: For each element+sector, distribute connections across slots
    for elem_id, sectors in element_sectors.items():
        elem = layout.elements_by_id.get(elem_id)
        if not elem:
            continue

        cx, cy, half_w, half_h = _get_element_rect(elem, sizing_calculator)

        for sector, entries in sectors.items():
            n = len(entries)

            # Sort by angle for consistent ordering
            entries.sort(key=lambda e: e[1])

            # Calculate slot angles within the sector
            sector_center = sector * SECTOR_WIDTH
            sector_start = sector_center - SECTOR_WIDTH / 2
            # Distribute N slots evenly within the 30° sector
            for i, (ci, angle, is_source) in enumerate(entries):
                slot_angle = sector_start + SECTOR_WIDTH * (i + 1) / (n + 1)
                port = _ray_rect_intersection(cx, cy, half_w, half_h, slot_angle)

                conn = layout.connections[ci]
                if is_source:
                    conn['_from_port'] = port
                else:
                    conn['_to_port'] = port
