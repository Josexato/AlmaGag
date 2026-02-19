"""
ConnectionRouterManager - Manages routing for all connections

Coordinates different router types and handles backward compatibility
with SDJF v1.5 waypoints.

Author: José + ALMA
Version: v2.1
Date: 2026-01-08
"""

from typing import Dict, List, Tuple
from collections import defaultdict
from AlmaGag.routing.router_base import ConnectionRouter
from AlmaGag.config import SEGMENT_SEPARATION_SPACING
from AlmaGag.routing.straight_router import StraightRouter
from AlmaGag.routing.manual_router import ManualRouter
from AlmaGag.routing.orthogonal_router import OrthogonalRouter
from AlmaGag.routing.bezier_router import BezierRouter
from AlmaGag.routing.arc_router import ArcRouter
from AlmaGag.routing.port_assignment import assign_ports


class ConnectionRouterManager:
    """
    Manages routing for all connections in a layout.

    Handles:
    - Router type selection
    - Backward compatibility with v1.5 waypoints
    - Default routing when type not specified
    """

    def __init__(self):
        """Initialize router manager with available routers."""
        self.routers: Dict[str, ConnectionRouter] = {
            'straight': StraightRouter(),
            'manual': ManualRouter(),
            'orthogonal': OrthogonalRouter(),
            'bezier': BezierRouter(),
            'arc': ArcRouter(),
        }
        self.default_router = 'straight'

    def register_router(self, name: str, router: ConnectionRouter):
        """
        Register a new router type.

        Args:
            name: Router type name (e.g., 'orthogonal', 'bezier', 'arc')
            router: Router instance
        """
        self.routers[name] = router

    def calculate_all_paths(self, layout):
        """
        Calculate paths for all connections in the layout.

        Pipeline:
        1. Assign ports: distribute connection points across 12 angular sectors
        2. Calculate individual paths using assigned ports
        3. Post-process: separate parallel orthogonal segments

        Args:
            layout: Layout object with connections and elements_by_id
        """
        # Pre-process: assign connection ports (12 sectors × N slots each)
        sizing = getattr(layout, 'sizing', None)
        assign_ports(layout, sizing)

        for connection in layout.connections:
            self._calculate_connection_path(connection, layout)

        # Post-process: separate parallel orthogonal segments
        self._separate_parallel_segments(layout.connections)

    def _calculate_connection_path(self, connection: dict, layout):
        """
        Calculate path for a single connection.

        Handles backward compatibility:
        - If connection has 'waypoints' at root level (v1.5), convert to manual routing
        - If connection has 'routing', use specified type
        - Otherwise, use default (straight)

        Args:
            connection: Connection dict
            layout: Layout object
        """
        # Get source and target elements
        from_elem = layout.elements_by_id.get(connection['from'])
        to_elem = layout.elements_by_id.get(connection['to'])

        # Skip if elements don't exist or don't have coordinates
        if not from_elem or not to_elem:
            return
        if from_elem.get('x') is None or from_elem.get('y') is None:
            return
        if to_elem.get('x') is None or to_elem.get('y') is None:
            return

        # Determine routing type
        routing = self._get_routing_config(connection)
        router_type = routing.get('type', self.default_router)

        # Self-loops require arc router
        if connection['from'] == connection['to'] and router_type == 'straight':
            router_type = 'arc'

        # Get appropriate router
        router = self.routers.get(router_type, self.routers[self.default_router])

        # Calculate path
        path = router.calculate_path(from_elem, to_elem, connection, layout)

        # Store computed path in connection
        connection['computed_path'] = path.to_dict()

    def _get_routing_config(self, connection: dict) -> dict:
        """
        Get routing configuration from connection.

        Handles backward compatibility with v1.5 waypoints and routing_type.

        Args:
            connection: Connection dict

        Returns:
            dict: Routing configuration
        """
        # Check if connection has 'routing' property (v2.1+)
        if 'routing' in connection:
            return connection['routing']

        # Check for 'routing_type' at root level (legacy format)
        if 'routing_type' in connection:
            return {'type': connection['routing_type']}

        # Check for v1.5 waypoints at root level
        if 'waypoints' in connection:
            # Convert v1.5 format to v2.1 format
            return {
                'type': 'manual',
                'waypoints': connection['waypoints']
            }

        # Default: straight line
        return {'type': self.default_router}

    def _separate_parallel_segments(self, connections: list):
        """
        Detect overlapping orthogonal segments across connections and apply
        perpendicular offsets so parallel lines are visually distinguishable.

        Groups segments by their fixed coordinate (same X for vertical,
        same Y for horizontal) within a tolerance, then offsets each
        connection's waypoints by ±spacing.
        """
        TOLERANCE = 5  # px threshold for "same coordinate"
        spacing = SEGMENT_SEPARATION_SPACING

        # Collect all orthogonal segments: (conn_index, seg_index, orientation, fixed_coord, range_min, range_max)
        segments = []
        for ci, conn in enumerate(connections):
            path = conn.get('computed_path')
            if not path or path.get('type') != 'polyline':
                continue
            points = path.get('points', [])
            if len(points) < 3:
                continue
            for si in range(len(points) - 1):
                x1, y1 = points[si]
                x2, y2 = points[si + 1]
                if abs(x1 - x2) < TOLERANCE and abs(y1 - y2) > TOLERANCE:
                    # Vertical segment (same X)
                    fixed = (x1 + x2) / 2
                    rmin, rmax = min(y1, y2), max(y1, y2)
                    segments.append((ci, si, 'V', fixed, rmin, rmax))
                elif abs(y1 - y2) < TOLERANCE and abs(x1 - x2) > TOLERANCE:
                    # Horizontal segment (same Y)
                    fixed = (y1 + y2) / 2
                    rmin, rmax = min(x1, x2), max(x1, x2)
                    segments.append((ci, si, 'H', fixed, rmin, rmax))

        if not segments:
            return

        # Group segments by orientation and approximate fixed coordinate
        groups = defaultdict(list)
        for seg in segments:
            ci, si, orient, fixed, rmin, rmax = seg
            # Round fixed coordinate to nearest TOLERANCE to group nearby segments
            bucket = round(fixed / TOLERANCE) * TOLERANCE
            groups[(orient, bucket)].append(seg)

        # For each group with overlapping ranges, apply offset
        for key, group in groups.items():
            if len(group) < 2:
                continue

            orient = key[0]

            # Check which segments actually overlap in range
            # Sort by range start
            group.sort(key=lambda s: s[4])

            # Find clusters of overlapping segments
            clusters = []
            current_cluster = [group[0]]
            cluster_max = group[0][5]

            for seg in group[1:]:
                if seg[4] < cluster_max:  # Ranges overlap
                    current_cluster.append(seg)
                    cluster_max = max(cluster_max, seg[5])
                else:
                    if len(current_cluster) > 1:
                        clusters.append(current_cluster)
                    current_cluster = [seg]
                    cluster_max = seg[5]

            if len(current_cluster) > 1:
                clusters.append(current_cluster)

            # Apply offsets to each cluster
            for cluster in clusters:
                n = len(cluster)
                for i, seg in enumerate(cluster):
                    ci, si, _, fixed, _, _ = seg
                    offset = (i - (n - 1) / 2) * spacing

                    path = connections[ci]['computed_path']
                    points = path['points']

                    if orient == 'V':
                        # Offset horizontal for vertical segments
                        x1, y1 = points[si]
                        x2, y2 = points[si + 1]
                        points[si] = (x1 + offset, y1)
                        points[si + 1] = (x2 + offset, y2)
                    else:
                        # Offset vertical for horizontal segments
                        x1, y1 = points[si]
                        x2, y2 = points[si + 1]
                        points[si] = (x1, y1 + offset)
                        points[si + 1] = (x2, y2 + offset)
