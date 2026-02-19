"""
OrthogonalVisibilityGraph - Obstacle-aware orthogonal routing

Implements a simplified libavoid/Adaptagrams-style approach:
1. Build orthogonal visibility graph from inflated obstacle bounding boxes
2. Inter-level channel lines for clean routing between levels
3. Proximity penalty to push paths away from obstacle edges
4. A* search minimizing path length + bend penalty + proximity penalty

Author: José + ALMA
Version: v3.3
Date: 2026-02-19
"""

import heapq
import math
from typing import List, Tuple, Dict, Optional, Set
from collections import defaultdict
from AlmaGag.routing.router_base import Point
from AlmaGag.config import ICON_WIDTH, ICON_HEIGHT


# Margin around obstacles (px) - must be larger than SEGMENT_SEPARATION_SPACING
OBSTACLE_MARGIN = 25

# Penalty for each 90° bend in the path (in equivalent px of distance)
BEND_PENALTY = 40

# Proximity penalty: edges running within this distance of an obstacle get penalized
PROXIMITY_RANGE = 50.0
# Maximum penalty per unit of edge length for obstacle-hugging edges
PROXIMITY_PENALTY_FACTOR = 0.8


class Rect:
    """Axis-aligned rectangle (obstacle bounding box with margin)."""
    __slots__ = ('x1', 'y1', 'x2', 'y2', 'elem_id')

    def __init__(self, x1: float, y1: float, x2: float, y2: float, elem_id: str = ''):
        self.x1 = min(x1, x2)
        self.y1 = min(y1, y2)
        self.x2 = max(x1, x2)
        self.y2 = max(y1, y2)
        self.elem_id = elem_id

    def contains_point(self, x: float, y: float, tolerance: float = 0.5) -> bool:
        """Check if point is strictly inside the rectangle (not on edge)."""
        return (self.x1 + tolerance < x < self.x2 - tolerance and
                self.y1 + tolerance < y < self.y2 - tolerance)

    def intersects_segment(self, ax: float, ay: float, bx: float, by: float) -> bool:
        """
        Check if an axis-aligned segment (H or V) passes through this rectangle interior.
        """
        if abs(ax - bx) < 0.1:
            x = ax
            if x <= self.x1 or x >= self.x2:
                return False
            seg_y1, seg_y2 = min(ay, by), max(ay, by)
            return seg_y1 < self.y2 and seg_y2 > self.y1
        elif abs(ay - by) < 0.1:
            y = ay
            if y <= self.y1 or y >= self.y2:
                return False
            seg_x1, seg_x2 = min(ax, bx), max(ax, bx)
            return seg_x1 < self.x2 and seg_x2 > self.x1
        return False

    def distance_to_hline(self, y: float) -> float:
        """Minimum perpendicular distance from a horizontal line at y to this rect."""
        if self.y1 <= y <= self.y2:
            return 0.0
        return min(abs(y - self.y1), abs(y - self.y2))

    def distance_to_vline(self, x: float) -> float:
        """Minimum perpendicular distance from a vertical line at x to this rect."""
        if self.x1 <= x <= self.x2:
            return 0.0
        return min(abs(x - self.x1), abs(x - self.x2))


def build_obstacles(layout, from_id: str, to_id: str, sizing_calculator=None) -> List[Rect]:
    """
    Build obstacle rectangles from all positioned elements, excluding source and target.
    """
    obstacles = []
    exclude = {from_id, to_id}

    for elem in layout.elements:
        eid = elem.get('id', '')
        if eid in exclude:
            continue
        x = elem.get('x')
        y = elem.get('y')
        if x is None or y is None:
            continue

        if 'width' in elem and 'height' in elem:
            w, h = elem['width'], elem['height']
        elif sizing_calculator:
            w, h = sizing_calculator.get_element_size(elem)
        else:
            hp = elem.get('hp', 1.0)
            wp = elem.get('wp', 1.0)
            w = ICON_WIDTH * wp
            h = ICON_HEIGHT * hp

        obstacles.append(Rect(
            x - OBSTACLE_MARGIN,
            y - OBSTACLE_MARGIN,
            x + w + OBSTACLE_MARGIN,
            y + h + OBSTACLE_MARGIN,
            elem_id=eid
        ))

    return obstacles


def _compute_channel_lines(layout, sizing_calculator=None) -> Tuple[List[float], List[float]]:
    """
    Compute inter-level channel Y coordinates and inter-group channel X coordinates.

    For each pair of consecutive levels, calculates the midpoint Y between
    the bottom of level N and the top of level N+1. These become preferred
    horizontal routing channels.

    Returns:
        (channel_ys, channel_xs): Lists of Y and X coordinates for channels
    """
    levels = getattr(layout, 'levels', {})
    if not levels:
        return [], []

    # Group elements by level, track Y ranges
    level_y_ranges: Dict[int, Tuple[float, float]] = {}
    for eid, level in levels.items():
        elem = layout.elements_by_id.get(eid, {})
        y = elem.get('y')
        if y is None:
            continue
        if 'height' in elem:
            h = elem['height']
        elif sizing_calculator:
            _, h = sizing_calculator.get_element_size(elem)
        else:
            hp = elem.get('hp', 1.0)
            h = ICON_HEIGHT * hp

        bottom = y + h
        if level not in level_y_ranges:
            level_y_ranges[level] = (y, bottom)
        else:
            cur_top, cur_bottom = level_y_ranges[level]
            level_y_ranges[level] = (min(cur_top, y), max(cur_bottom, bottom))

    # Calculate midpoints between consecutive levels
    channel_ys = []
    sorted_levels = sorted(level_y_ranges.keys())
    for i in range(len(sorted_levels) - 1):
        l1 = sorted_levels[i]
        l2 = sorted_levels[i + 1]
        bottom_l1 = level_y_ranges[l1][1]
        top_l2 = level_y_ranges[l2][0]
        if top_l2 > bottom_l1:
            midpoint = (bottom_l1 + top_l2) / 2
            channel_ys.append(midpoint)

    return channel_ys, []


def _segment_blocked(ax: float, ay: float, bx: float, by: float,
                     obstacles: List[Rect]) -> bool:
    """Check if an axis-aligned segment is blocked by any obstacle."""
    for obs in obstacles:
        if obs.intersects_segment(ax, ay, bx, by):
            return True
    return False


def _min_obstacle_distance_h(y: float, obstacles: List[Rect]) -> float:
    """Minimum distance from a horizontal line at y to any obstacle."""
    if not obstacles:
        return float('inf')
    return min(obs.distance_to_hline(y) for obs in obstacles)


def _min_obstacle_distance_v(x: float, obstacles: List[Rect]) -> float:
    """Minimum distance from a vertical line at x to any obstacle."""
    if not obstacles:
        return float('inf')
    return min(obs.distance_to_vline(x) for obs in obstacles)


def _proximity_penalty(min_dist: float, edge_length: float) -> float:
    """
    Calculate proximity penalty for an edge based on its distance to the nearest obstacle.

    Edges far from obstacles (in channels) get no penalty.
    Edges skirting obstacle boundaries get penalized proportionally.
    """
    if min_dist >= PROXIMITY_RANGE:
        return 0.0
    # Linear penalty: closer to obstacle = higher penalty per unit length
    ratio = 1.0 - (min_dist / PROXIMITY_RANGE)
    return edge_length * PROXIMITY_PENALTY_FACTOR * ratio


def _collect_coordinates(
    obstacles: List[Rect],
    extra_points: List[Tuple[float, float]],
    channel_ys: List[float],
    canvas_w: float,
    canvas_h: float
) -> Tuple[List[float], List[float]]:
    """
    Collect all unique X and Y coordinates for the visibility graph grid.
    """
    xs: Set[float] = set()
    ys: Set[float] = set()

    xs.add(0)
    xs.add(canvas_w)
    ys.add(0)
    ys.add(canvas_h)

    for px, py in extra_points:
        xs.add(px)
        ys.add(py)

    # Channel lines (inter-level midpoints)
    for cy in channel_ys:
        ys.add(cy)

    for obs in obstacles:
        xs.add(obs.x1)
        xs.add(obs.x2)
        ys.add(obs.y1)
        ys.add(obs.y2)

    return sorted(xs), sorted(ys)


def _point_in_any_obstacle(x: float, y: float, obstacles: List[Rect]) -> bool:
    """Check if a point is inside any obstacle."""
    for obs in obstacles:
        if obs.contains_point(x, y):
            return True
    return False


def build_visibility_graph(
    obstacles: List[Rect],
    extra_points: List[Tuple[float, float]],
    channel_ys: List[float],
    canvas_w: float = 2000,
    canvas_h: float = 2000
) -> Dict[Tuple[float, float], List[Tuple[Tuple[float, float], float]]]:
    """
    Build an orthogonal visibility graph with proximity-weighted edges.

    Edges that run close to obstacles get a proximity penalty, pushing
    paths toward the center of free space (inter-level channels).
    """
    xs, ys = _collect_coordinates(obstacles, extra_points, channel_ys, canvas_w, canvas_h)

    valid_nodes: Set[Tuple[float, float]] = set()
    for x in xs:
        for y in ys:
            if not _point_in_any_obstacle(x, y, obstacles):
                valid_nodes.add((x, y))

    for pt in extra_points:
        valid_nodes.add(pt)

    graph: Dict[Tuple[float, float], List[Tuple[Tuple[float, float], float]]] = {
        node: [] for node in valid_nodes
    }

    by_x: Dict[float, List[float]] = {}
    by_y: Dict[float, List[float]] = {}

    for x, y in valid_nodes:
        by_x.setdefault(x, []).append(y)
        by_y.setdefault(y, []).append(x)

    for x in by_x:
        by_x[x].sort()
    for y in by_y:
        by_y[y].sort()

    # Horizontal edges with proximity penalty
    for y, x_list in by_y.items():
        min_dist_h = _min_obstacle_distance_h(y, obstacles)
        for i in range(len(x_list) - 1):
            x1 = x_list[i]
            x2 = x_list[i + 1]
            if not _segment_blocked(x1, y, x2, y, obstacles):
                edge_len = abs(x2 - x1)
                cost = edge_len + _proximity_penalty(min_dist_h, edge_len)
                graph[(x1, y)].append(((x2, y), cost))
                graph[(x2, y)].append(((x1, y), cost))

    # Vertical edges with proximity penalty
    for x, y_list in by_x.items():
        min_dist_v = _min_obstacle_distance_v(x, obstacles)
        for i in range(len(y_list) - 1):
            y1 = y_list[i]
            y2 = y_list[i + 1]
            if not _segment_blocked(x, y1, x, y2, obstacles):
                edge_len = abs(y2 - y1)
                cost = edge_len + _proximity_penalty(min_dist_v, edge_len)
                graph[(x, y1)].append(((x, y2), cost))
                graph[(x, y2)].append(((x, y1), cost))

    return graph


def _direction(from_node: Tuple[float, float], to_node: Tuple[float, float]) -> str:
    """Get direction of movement: 'H' for horizontal, 'V' for vertical."""
    if abs(from_node[1] - to_node[1]) < 0.1:
        return 'H'
    return 'V'


def astar_search(
    graph: Dict[Tuple[float, float], List[Tuple[Tuple[float, float], float]]],
    start: Tuple[float, float],
    end: Tuple[float, float]
) -> Optional[List[Tuple[float, float]]]:
    """
    A* search on the visibility graph minimizing distance + bend penalty + proximity penalty.
    """
    if start == end:
        return [start]

    if start not in graph or end not in graph:
        return None

    def heuristic(node):
        return abs(node[0] - end[0]) + abs(node[1] - end[1])

    OPEN = []
    counter = 0
    g_score = {(start, 'S'): 0.0}
    came_from = {}

    heapq.heappush(OPEN, (heuristic(start), counter, start, 'S'))
    counter += 1

    while OPEN:
        f, _, current, cur_dir = heapq.heappop(OPEN)

        if current == end:
            path = [current]
            state = (current, cur_dir)
            while state in came_from:
                state = came_from[state]
                path.append(state[0])
            path.reverse()
            return path

        current_state = (current, cur_dir)
        current_g = g_score.get(current_state, float('inf'))

        if f > current_g + heuristic(current) + 1:
            continue

        for neighbor, edge_cost in graph.get(current, []):
            new_dir = _direction(current, neighbor)

            bend_cost = 0.0
            if cur_dir != 'S' and cur_dir != new_dir:
                bend_cost = BEND_PENALTY

            new_g = current_g + edge_cost + bend_cost
            new_state = (neighbor, new_dir)

            if new_g < g_score.get(new_state, float('inf')):
                g_score[new_state] = new_g
                came_from[new_state] = current_state
                f_score = new_g + heuristic(neighbor)
                heapq.heappush(OPEN, (f_score, counter, neighbor, new_dir))
                counter += 1

    return None


def simplify_path(path: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
    """Remove redundant collinear points from an orthogonal path."""
    if len(path) <= 2:
        return path

    result = [path[0]]
    for i in range(1, len(path) - 1):
        px, py = path[i - 1]
        cx, cy = path[i]
        nx, ny = path[i + 1]

        same_x = abs(px - cx) < 0.1 and abs(cx - nx) < 0.1
        same_y = abs(py - cy) < 0.1 and abs(cy - ny) < 0.1

        if not same_x and not same_y:
            result.append(path[i])

    result.append(path[-1])
    return result


def find_orthogonal_path(
    start: Point,
    end: Point,
    layout,
    from_id: str,
    to_id: str,
    sizing_calculator=None
) -> Optional[List[Point]]:
    """
    Find an obstacle-avoiding orthogonal path between two points.

    Uses inter-level channel lines and proximity penalties to route
    paths through the center of free space between levels.
    """
    obstacles = build_obstacles(layout, from_id, to_id, sizing_calculator)

    canvas = getattr(layout, 'canvas', {})
    canvas_w = canvas.get('width', 2000)
    canvas_h = canvas.get('height', 2000)

    # Compute inter-level channel lines
    channel_ys, _ = _compute_channel_lines(layout, sizing_calculator)

    extra_points = [(start.x, start.y), (end.x, end.y)]

    graph = build_visibility_graph(obstacles, extra_points, channel_ys, canvas_w, canvas_h)

    sp = (start.x, start.y)
    ep = (end.x, end.y)
    raw_path = astar_search(graph, sp, ep)

    if raw_path is None:
        return None

    simplified = simplify_path(raw_path)

    return [Point(x, y) for x, y in simplified]
