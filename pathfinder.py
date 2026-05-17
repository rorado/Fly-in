from graph import Graph
from config import Config
import heapq


class Pathfinder:
    """Find candidate paths from the start hub to the end hub."""

    def __init__(self, graph: Graph, conf: Config) -> None:

        self.adj: dict[str, list[str]] = graph.adj
        self.conf: Config = conf

        if (
            conf.start_hub is None
            or conf.start_hub.value is None
        ):
            raise ValueError("start_hub is required")

        if (
            conf.end_hub is None
            or conf.end_hub.value is None
        ):
            raise ValueError("end_hub is required")

        self.start: str = conf.start_hub.value.name
        self.goal: str = conf.end_hub.value.name

    @staticmethod
    def get_zone_cost(conf: Config, node: str) -> float:
        ZONE_COSTS = {
            "normal": 1.0,
            "blocked": float("inf"),
            "restricted": 2.0,
            "priority": 1.0,
        }

        if (
            conf.start_hub is not None
            and conf.start_hub.value is not None
            and node == conf.start_hub.value.name
        ):
            return 0.0

        if conf.hubs is None:
            return 1.0

        hub = conf.hubs.get(node)

        if hub is None:
            return 1.0

        if hub.metadata is None:
            return 1.0

        zone_value = hub.metadata.get("zone", "normal")

        if not isinstance(zone_value, str):
            return 1.0

        return ZONE_COSTS.get(zone_value, 1.0)

    def path_cost(self, path: list[str]) -> float:
        cost = 0.0
        for node in path[1:]:
            step_cost = Pathfinder.get_zone_cost(self.conf, node)
            if step_cost == float("inf"):
                return float("inf")
            cost += step_cost
        return cost

    def priority_count(self, path: list[str]) -> int:

        count = 0

        if self.conf.hubs is None:
            return count

        for node in path:

            hub = self.conf.hubs.get(node)

            if hub is None:
                continue

            if hub.metadata is None:
                continue

            zone_value = hub.metadata.get("zone", "normal")

            if zone_value == "priority":
                count += 1

        return count

    def get_candidate_paths(
        self,
        max_paths: int = 20,
    ) -> list[list[str]]:

        paths = self._enumerate_k_shortest_simple_paths(
            max_paths=max_paths
        )

        if not paths:
            return []

        return paths

    def _enumerate_k_shortest_simple_paths(
        self,
        max_paths: int = 20,
    ) -> list[list[str]]:

        pq: list[tuple[float, list[str]]] = [
            (0.0, [self.start])
        ]

        found: list[list[str]] = []

        while pq and len(found) < max_paths:

            cost, path = heapq.heappop(pq)

            node = path[-1]

            if node == self.goal:
                found.append(path)
                continue

            for nxt in self.adj.get(node, []):

                if nxt in path:
                    continue

                step_cost = Pathfinder.get_zone_cost(
                    self.conf,
                    nxt,
                )

                if step_cost == float("inf"):
                    continue

                new_path = path + [nxt]

                heapq.heappush(
                    pq,
                    (
                        cost + step_cost,
                        new_path,
                    ),
                )

        found.sort(
            key=lambda path: (
                self.path_cost(path),
                -self.priority_count(path),
                len(path),
            )
        )

        return found
