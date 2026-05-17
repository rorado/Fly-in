from zone import Zone
from drone import Drone
from connection import Connection
from config import Config
from pathfinder import Pathfinder
from visualization import Visualization


class Simulation:
    def __init__(
        self,
        conf: Config,
        drones: list[Drone],
        path: list[str],
        candidate_paths: list[list[str]] | None = None,
    ):
        self.conf = conf
        self.drones = drones
        self.path = path
        self.candidate_paths = candidate_paths or [path]
        if conf.start_hub is None or conf.start_hub.value is None:
            raise ValueError("start_hub is not defined")

        if conf.end_hub is None or conf.end_hub.value is None:
            raise ValueError("end_hub is not defined")

        self.start = conf.start_hub.value.name
        self.goal = conf.end_hub.value.name
        self.output: list[list[str]] = []

        self.zones: dict[str, Zone] = {
            name: Zone(
                x=int(v.x or 0),
                y=int(v.y or 0),
                name=name,
                zone_type=str((v.metadata or {}).get("zone", "normal")),
                max_drones=int((v.metadata or {}).get("max_drones", 1) or 1),
                color=str((v.metadata or {}).get("color", "default")),
            )
            for name, v in (conf.hubs or {}).items()
        }

        start_md = conf.start_hub.metadata or {}

        start_zone = str(start_md.get("zone", "normal"))

        self.zones[self.start] = Zone(
            x=conf.start_hub.value.x,
            y=conf.start_hub.value.y,
            color=str(start_md.get("color", "default")),
            name=self.start,
            zone_type=start_zone,
            max_drones=int(start_md.get("max_drones", 1) or 1),
            allowed_multiples=True,
        )

        end_md = conf.end_hub.metadata or {}

        end_zone = str(end_md.get("zone", "normal"))

        self.zones[self.goal] = Zone(
            x=conf.end_hub.value.x,
            y=conf.end_hub.value.y,
            color=str(end_md.get("color", "default")),
            name=self.goal,
            zone_type=end_zone,
            max_drones=int(end_md.get("max_drones", 1) or 1),
            allowed_multiples=True
        )

        for d in drones:
            self.zones[self.start].enter(d.id)

        self.connections: dict[tuple[str, str], Connection] = {}

        for conn in (conf.connections or {}).values():
            if conn.value is None:
                continue
            if conn.value.from_hub is None or conn.value.to_hub is None:
                continue
            a = conn.value.from_hub
            b = conn.value.to_hub
            md = conn.metadata or {}
            max_cap_raw = md.get("max_link_capacity", 1)
            max_cap = max_cap_raw if max_cap_raw is not None else 1
            key: tuple[str, str]
            if a < b:
                key = (a, b)
            else:
                key = (b, a)

            self.connections[key] = Connection(a, b, max_cap)

    def _best_alternative_next(
        self,
        drone: Drone,
        current: str
    ) -> str | None:

        current_next = drone.next()

        candidates: list[tuple[float, list[str], int]] = []

        for path in self.candidate_paths:

            if current not in path:
                continue

            idx = path.index(current)

            if idx >= len(path) - 1:
                continue

            suffix = path[idx:]

            remaining_cost = 0.0

            for node in suffix[1:]:
                remaining_cost += float(
                    Pathfinder.get_zone_cost(self.conf, node)
                )

            candidates.append((remaining_cost, path, idx))

        candidates.sort(key=lambda item: item[0])

        for _, path, idx in candidates:

            candidate_next = path[idx + 1]

            if candidate_next == current_next:
                continue

            if current < candidate_next:
                key = (current, candidate_next)
            else:
                key = (candidate_next, current)

            conn = self.connections.get(key)
            zone = self.zones.get(candidate_next)

            if conn is None or zone is None:
                continue

            if zone.can_enter() and conn.can_enter():
                drone.reroute_from_current(path[idx:])
                return candidate_next

        return None

    def run(self) -> None:

        turns = 0

        while True:
            turn_output: list[str] = []
            moved_this_turn = set()

            all_finished = True
            for d in self.drones:

                if d.finished:
                    continue

                all_finished = False

                if d.in_flight:
                    d.remaining -= 1
                    if d.remaining == 0:
                        to_zone = d.to_zone
                        if to_zone is None:
                            continue
                        target_zone = self.zones[to_zone]
                        target_zone.enter(d.id)
                        d.in_flight = False
                        d.index += 1

                        if d.to_zone == self.goal:
                            d.finished = True

                        turn_output.append(
                            f"D{d.id}-{d.to_zone}"
                        )
                    else:
                        turn_output.append(
                            f"D{d.id}-{d.from_zone}-{d.to_zone}"
                        )
                    moved_this_turn.add(d.id)

            for d in self.drones:
                if (
                    d.finished
                    or d.in_flight
                    or d.id in moved_this_turn
                ):
                    continue

                current = d.current()

                next_zone = d.next()

                if next_zone is None:
                    d.finished = True
                    continue

                if current < next_zone:
                    key = (current, next_zone)
                else:
                    key = (next_zone, current)

                if key not in self.connections:
                    continue

                current_zone = self.zones[current]
                target_zone = self.zones[next_zone]
                conn = self.connections[key]

                if (
                    not target_zone.can_enter()
                    or not conn.can_enter()
                ):
                    rerouted_next = self._best_alternative_next(
                        d,
                        current
                    )

                    if rerouted_next is None:
                        continue

                    next_zone = rerouted_next

                    if current < next_zone:
                        key = (current, next_zone)
                    else:
                        key = (next_zone, current)

                    target_zone = self.zones[next_zone]
                    conn = self.connections[key]

                current_zone.leave(d.id)
                conn.enter(d.id)
                if target_zone.zone_type == "restricted":
                    d.start_flight(
                        current,
                        next_zone,
                        cost=1
                    )
                    turn_output.append(
                        f"D{d.id}-{current}-{next_zone}"
                    )
                else:
                    d.move()
                    target_zone.enter(d.id)
                    turn_output.append(
                        f"D{d.id}-{next_zone}"
                    )

                if next_zone == self.goal:
                    d.finished = True

                moved_this_turn.add(d.id)

            if turn_output:
                print(" ".join(turn_output))
                self.output.append(turn_output)

                turns += 1

            for conn in self.connections.values():
                conn.clear()

            if not turn_output and not all_finished:
                print("Deadlock detected")
                break

            if all_finished:
                break

        print("\nturns:", turns)

    def visualization(self) -> None:

        vis = Visualization(
            self.zones,
            self.connections,
            self.output,
            self.drones,
            self.start
        )

        vis.display_zones()
