"""Data models for the Fly-in drone routing system."""

import sys
from enum import Enum
from typing import Dict, List, Optional, Tuple


class ZoneType(Enum):
    """Possible zone types for a hub."""

    NORMAL = "normal"
    RESTRICTED = "restricted"
    PRIORITY = "priority"
    BLOCKED = "blocked"


class Hub:
    """Represents a zone/hub node in the network.

    Args:
        name: Unique identifier for this hub.
        x: X-coordinate (used as pathfinding heuristic).
        y: Y-coordinate (used as pathfinding heuristic).
        zone_type: The zone classification of this hub.
        color: Display colour (informational only).
        max_drones: Maximum simultaneous drones for PRIORITY zones.
        is_start: True when this hub is the start hub.
        is_end: True when this hub is the end hub.
    """

    def __init__(
        self,
        name: str,
        x: int,
        y: int,
        zone_type: ZoneType = ZoneType.NORMAL,
        color: str = "white",
        max_drones: int = 1,
        is_start: bool = False,
        is_end: bool = False,
    ) -> None:
        """Initialise a Hub."""
        self.name = name
        self.x = x
        self.y = y
        self.zone_type = zone_type
        self.color = color
        self.max_drones = max_drones
        self.is_start = is_start
        self.is_end = is_end

    def capacity(self) -> int:
        """Return the maximum simultaneous drones allowed in this hub.

        Returns:
            0 for BLOCKED zones, unlimited (sys.maxsize) for start/end hubs,
            max_drones for PRIORITY zones, 1 otherwise.
        """
        if self.zone_type == ZoneType.BLOCKED:
            return 0
        if self.is_start or self.is_end:
            return sys.maxsize
        if self.zone_type == ZoneType.PRIORITY:
            return self.max_drones
        return 1

    def is_passable(self) -> bool:
        """Return True when drones are allowed to enter this hub."""
        return self.zone_type != ZoneType.BLOCKED

    def __repr__(self) -> str:
        """Return debug string."""
        return (
            f"Hub(name={self.name!r}, pos=({self.x},{self.y}), "
            f"zone={self.zone_type.value}, cap={self.capacity()})"
        )


class Connection:
    """Represents a directed/undirected link between two hubs.

    Args:
        hub_a: Name of the first hub.
        hub_b: Name of the second hub.
        max_link_capacity: Maximum drones that may traverse this link per turn.
    """

    def __init__(
        self,
        hub_a: str,
        hub_b: str,
        max_link_capacity: int = 1,
    ) -> None:
        """Initialise a Connection."""
        self.hub_a = hub_a
        self.hub_b = hub_b
        self.max_link_capacity = max_link_capacity

    def connects(self, name_a: str, name_b: str) -> bool:
        """Return True when this connection links name_a and name_b.

        The check is order-independent.

        Args:
            name_a: First hub name.
            name_b: Second hub name.

        Returns:
            True if this connection joins those two hubs.
        """
        return (self.hub_a == name_a and self.hub_b == name_b) or (
            self.hub_a == name_b and self.hub_b == name_a
        )

    def other(self, name: str) -> str:
        """Return the hub on the other end of this connection.

        Args:
            name: The hub name on one end.

        Returns:
            The hub name on the other end.
        """
        return self.hub_b if self.hub_a == name else self.hub_a

    def key(self) -> Tuple[str, str]:
        """Return a canonical (sorted) tuple key for this connection.

        Returns:
            Tuple with hub names in lexicographic order.
        """
        a, b = sorted([self.hub_a, self.hub_b])
        return (a, b)

    def __repr__(self) -> str:
        """Return debug string."""
        return (
            f"Connection({self.hub_a!r} <-> {self.hub_b!r}, "
            f"cap={self.max_link_capacity})"
        )


class Network:
    """Represents the complete drone network graph.

    Args:
        nb_drones: Total number of drones to route.
        start: The start hub.
        end: The destination hub.
        hubs: Mapping from hub name to Hub object (includes start and end).
        connections: All connections in the network.
    """

    def __init__(
        self,
        nb_drones: int,
        start: Hub,
        end: Hub,
        hubs: Dict[str, Hub],
        connections: List[Connection],
    ) -> None:
        """Initialise a Network."""
        self.nb_drones = nb_drones
        self.start = start
        self.end = end
        self.hubs = hubs
        self.connections = connections
        self._adjacency: Optional[Dict[str, List[str]]] = None

    def adjacency(self) -> Dict[str, List[str]]:
        """Build (once) and return the adjacency list of passable neighbours.

        Returns:
            Dict mapping each hub name to a list of reachable neighbour names.
        """
        if self._adjacency is None:
            adj: Dict[str, List[str]] = {name: [] for name in self.hubs}
            for conn in self.connections:
                a, b = conn.hub_a, conn.hub_b
                if a in adj and b in adj:
                    if self.hubs[b].is_passable():
                        adj[a].append(b)
                    if self.hubs[a].is_passable():
                        adj[b].append(a)
            self._adjacency = adj
        return self._adjacency

    def get_connection(self, a: str, b: str) -> Optional[Connection]:
        """Return the Connection between hubs a and b, or None.

        Args:
            a: First hub name.
            b: Second hub name.

        Returns:
            The matching Connection, or None if no connection exists.
        """
        for conn in self.connections:
            if conn.connects(a, b):
                return conn
        return None

    def __repr__(self) -> str:
        """Return debug string."""
        return (
            f"Network(drones={self.nb_drones}, "
            f"hubs={len(self.hubs)}, "
            f"connections={len(self.connections)})"
        )


class Drone:
    """Represents a single drone being routed through the network.

    Args:
        drone_id: Unique 1-based integer identifier.
        start: Name of the starting hub.
    """

    def __init__(self, drone_id: int, start: str) -> None:
        """Initialise a Drone."""
        self.id = drone_id
        self.current: str = start
        self.path: List[str] = [start]
        self.path_index: int = 0
        self.arrived: bool = False

    def assign_path(self, path: List[str]) -> None:
        """Assign a full path (list of hub names) to this drone.

        Args:
            path: Ordered list of hub names from start to end.
        """
        self.path = path
        self.path_index = 0
        self.current = path[0]

    def next_hub(self) -> Optional[str]:
        """Return the next hub in the assigned path, or None if at the end.

        Returns:
            Hub name of the next step, or None.
        """
        idx = self.path_index + 1
        if idx < len(self.path):
            return self.path[idx]
        return None

    def advance(self) -> None:
        """Move this drone one step forward along its assigned path."""
        if self.path_index + 1 < len(self.path):
            self.path_index += 1
            self.current = self.path[self.path_index]

    def __repr__(self) -> str:
        """Return debug string."""
        return (
            f"Drone(id={self.id}, current={self.current!r}, "
            f"arrived={self.arrived})"
        )
