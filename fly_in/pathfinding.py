"""Pathfinding algorithms for the Fly-in drone routing system.

All graph traversal is implemented from scratch; no external graph libraries
(e.g. networkx, graphlib) are used.
"""

import heapq
import math
from typing import Dict, List, Optional

from fly_in.models import Network


class PathfindingError(RuntimeError):
    """Raised when no valid path can be found in the network."""


# ---------------------------------------------------------------------------
# A* search
# ---------------------------------------------------------------------------

def heuristic(network: Network, a: str, b: str) -> float:
    """Euclidean distance heuristic between two hubs.

    Args:
        network: The drone network (provides hub coordinates).
        a: Name of the source hub.
        b: Name of the destination hub.

    Returns:
        Straight-line distance between the two hub positions.
    """
    ha = network.hubs[a]
    hb = network.hubs[b]
    return math.hypot(ha.x - hb.x, ha.y - hb.y)


def astar(
    network: Network,
    start: str,
    end: str,
) -> Optional[List[str]]:
    """Find the shortest path from *start* to *end* using A*.

    Blocked zones are excluded from the search.  The heuristic is Euclidean
    distance between hub coordinates.

    Args:
        network: The drone network graph.
        start: Name of the start hub.
        end: Name of the destination hub.

    Returns:
        Ordered list of hub names from start to end (inclusive), or None
        if no path exists.
    """
    adj = network.adjacency()

    # g_score[n] = cost of cheapest known path from start to n
    g_score: Dict[str, float] = {start: 0.0}
    # f_score[n] = g_score[n] + heuristic(n, end)
    f_score: Dict[str, float] = {start: heuristic(network, start, end)}
    # came_from[n] = predecessor on cheapest path
    came_from: Dict[str, str] = {}

    # Priority queue entries: (f_score, hub_name)
    open_heap: List[tuple] = [(f_score[start], start)]

    while open_heap:
        _, current = heapq.heappop(open_heap)

        if current == end:
            return _reconstruct_path(came_from, current)

        for neighbour in adj.get(current, []):
            tentative_g = g_score.get(current, math.inf) + 1.0
            if tentative_g < g_score.get(neighbour, math.inf):
                came_from[neighbour] = current
                g_score[neighbour] = tentative_g
                f = tentative_g + heuristic(network, neighbour, end)
                f_score[neighbour] = f
                heapq.heappush(open_heap, (f, neighbour))

    return None


def _reconstruct_path(came_from: Dict[str, str], current: str) -> List[str]:
    """Reconstruct the path by following came_from back to the start.

    Args:
        came_from: Predecessor map built during A* search.
        current: The node at which to end reconstruction (typically the goal).

    Returns:
        Ordered list of hub names from start to current.
    """
    path = [current]
    while current in came_from:
        current = came_from[current]
        path.append(current)
    path.reverse()
    return path


# ---------------------------------------------------------------------------
# BFS (unweighted shortest path)
# ---------------------------------------------------------------------------

def bfs(
    network: Network,
    start: str,
    end: str,
) -> Optional[List[str]]:
    """Find the shortest path (fewest hops) from *start* to *end* via BFS.

    Blocked zones are not traversed.

    Args:
        network: The drone network graph.
        start: Name of the start hub.
        end: Name of the destination hub.

    Returns:
        Ordered list of hub names from start to end (inclusive), or None
        if no path exists.
    """
    adj = network.adjacency()
    queue: List[List[str]] = [[start]]
    visited = {start}

    while queue:
        path = queue.pop(0)
        node = path[-1]

        if node == end:
            return path

        for neighbour in adj.get(node, []):
            if neighbour not in visited:
                visited.add(neighbour)
                queue.append(path + [neighbour])

    return None


# ---------------------------------------------------------------------------
# Multiple distinct shortest paths (used for multi-drone routing)
# ---------------------------------------------------------------------------

def find_all_shortest_paths(
    network: Network,
    start: str,
    end: str,
) -> List[List[str]]:
    """Return all simple paths of minimum length from start to end.

    Blocked zones are excluded.  The search is bounded to paths no longer
    than the shortest path found.

    Args:
        network: The drone network graph.
        start: Name of the start hub.
        end: Name of the destination hub.

    Returns:
        List of all shortest paths (each path is a list of hub names).
        Returns an empty list when no path exists.
    """
    adj = network.adjacency()
    best_len: Optional[int] = None
    all_paths: List[List[str]] = []

    # BFS that keeps track of the full path to avoid revisiting nodes
    # within a single path (simple-path constraint).
    queue: List[List[str]] = [[start]]

    while queue:
        path = queue.pop(0)

        # Prune if already longer than known best
        if best_len is not None and len(path) > best_len:
            continue

        node = path[-1]

        if node == end:
            best_len = len(path)
            all_paths.append(path)
            continue

        visited_in_path = set(path)
        for neighbour in adj.get(node, []):
            if neighbour not in visited_in_path:
                queue.append(path + [neighbour])

    return all_paths


# ---------------------------------------------------------------------------
# Optimal path assignment for a drone fleet
# ---------------------------------------------------------------------------

def assign_paths(
    network: Network,
    paths: List[List[str]],
) -> List[List[str]]:
    """Assign one path per drone to minimise total simulation turns.

    The strategy distributes drones across available paths so that the
    slowest path (number of turns = path_length + drones_on_path - 1)
    is minimised.

    Args:
        network: The drone network (provides nb_drones).
        paths: Available paths, already filtered to shortest length.

    Returns:
        List of length nb_drones, where entry i is the path assigned to
        drone (i+1).

    Raises:
        PathfindingError: When *paths* is empty (no route to goal).
    """
    if not paths:
        raise PathfindingError(
            f"No path from {network.start.name!r} to {network.end.name!r}"
        )

    nb_drones = network.nb_drones
    num_paths = len(paths)

    # Determine the best number of drones to place on each path such that
    # max(path_length + drones_on_path - 1) is minimised.
    # With equal-length paths the optimal split assigns ceil/floor.
    if num_paths == 1 or nb_drones <= num_paths:
        # Simple round-robin
        return [paths[i % num_paths] for i in range(nb_drones)]

    # Binary-search for the minimum number of turns T such that all drones
    # can be assigned with at most (T - path_length + 1) drones per path.
    path_len = len(paths[0])  # all paths have the same length

    lo, hi = path_len, path_len + nb_drones - 1

    while lo < hi:
        mid = (lo + hi) // 2
        capacity = sum(max(0, mid - len(p) + 1) for p in paths)
        if capacity >= nb_drones:
            hi = mid
        else:
            lo = mid + 1

    best_turns = lo
    assigned: List[List[str]] = []
    remaining = nb_drones

    for p in paths:
        slots = max(0, best_turns - len(p) + 1)
        take = min(slots, remaining)
        assigned.extend([p] * take)
        remaining -= take
        if remaining == 0:
            break

    # Fallback: if rounding left some drones unassigned, put them on path 0
    while len(assigned) < nb_drones:
        assigned.append(paths[0])

    return assigned


def plan_routes(network: Network) -> List[List[str]]:
    """Compute path assignments for the full drone fleet.

    Tries all shortest paths first; falls back to any A* path when none are
    found via BFS.

    Args:
        network: The drone network.

    Returns:
        List of nb_drones paths (each a list of hub names).

    Raises:
        PathfindingError: When the goal is completely unreachable.
    """
    paths = find_all_shortest_paths(
        network, network.start.name, network.end.name
    )

    if not paths:
        # BFS-derived paths failed; attempt A* as a secondary route finder
        path = astar(network, network.start.name, network.end.name)
        if path is None:
            raise PathfindingError(
                f"No path from {network.start.name!r} to {network.end.name!r}"
            )
        paths = [path]

    return assign_paths(network, paths)
