"""Turn-based simulation engine for the Fly-in drone routing system."""

from typing import Dict, List, Optional, Tuple

from fly_in.models import Drone, Network


class SimulationError(RuntimeError):
    """Raised when the simulation encounters an irrecoverable state."""


# ---------------------------------------------------------------------------
# Per-turn movement record
# ---------------------------------------------------------------------------

class Move:
    """Records a single drone movement within one simulation turn.

    Args:
        drone_id: Identifier of the drone that moved.
        from_hub: Hub the drone departed from.
        to_hub: Hub the drone arrived at.
    """

    def __init__(self, drone_id: int, from_hub: str, to_hub: str) -> None:
        """Initialise a Move."""
        self.drone_id = drone_id
        self.from_hub = from_hub
        self.to_hub = to_hub

    def __repr__(self) -> str:
        """Return debug string."""
        return f"Move(D{self.drone_id}: {self.from_hub}->{self.to_hub})"

    def format(self) -> str:
        """Return the canonical output representation of this move.

        Returns:
            String in the form ``D<id>:<from>-><to>``.
        """
        return f"D{self.drone_id}:{self.from_hub}->{self.to_hub}"


# ---------------------------------------------------------------------------
# Simulation state helpers
# ---------------------------------------------------------------------------

class ZoneOccupancy:
    """Tracks how many drones currently occupy each hub zone.

    Args:
        network: The drone network (provides capacity information per hub).
    """

    def __init__(self, network: Network) -> None:
        """Initialise ZoneOccupancy."""
        self._network = network
        self._counts: Dict[str, int] = {}

    def count(self, hub_name: str) -> int:
        """Return current occupant count for *hub_name*.

        Args:
            hub_name: Name of the hub to query.

        Returns:
            Number of drones currently in that hub.
        """
        return self._counts.get(hub_name, 0)

    def has_space(self, hub_name: str) -> bool:
        """Return True when the hub can accept at least one more drone.

        Args:
            hub_name: Name of the hub to check.

        Returns:
            True if capacity is not yet reached.
        """
        hub = self._network.hubs[hub_name]
        return self.count(hub_name) < hub.capacity()

    def add(self, hub_name: str) -> None:
        """Increment the occupant count for *hub_name*.

        Args:
            hub_name: Hub to mark as containing one more drone.
        """
        self._counts[hub_name] = self._counts.get(hub_name, 0) + 1

    def remove(self, hub_name: str) -> None:
        """Decrement the occupant count for *hub_name*.

        Args:
            hub_name: Hub to mark as containing one fewer drone.
        """
        if self._counts.get(hub_name, 0) > 0:
            self._counts[hub_name] -= 1


class LinkUsage:
    """Tracks how many drones have traversed each link in the current turn.

    Args:
        network: The drone network (provides link capacity information).
    """

    def __init__(self, network: Network) -> None:
        """Initialise LinkUsage."""
        self._network = network
        self._counts: Dict[Tuple[str, str], int] = {}

    def _key(self, a: str, b: str) -> Tuple[str, str]:
        """Canonical (sorted) key for a connection.

        Args:
            a: One hub name.
            b: Other hub name.

        Returns:
            Sorted tuple of the two hub names.
        """
        return (min(a, b), max(a, b))

    def has_capacity(self, a: str, b: str) -> bool:
        """Return True when the link a↔b can carry one more drone this turn.

        Args:
            a: First hub name.
            b: Second hub name.

        Returns:
            True if the link has not yet reached its capacity this turn.
        """
        conn = self._network.get_connection(a, b)
        if conn is None:
            return False
        key = self._key(a, b)
        used = self._counts.get(key, 0)
        return used < conn.max_link_capacity

    def use(self, a: str, b: str) -> None:
        """Record one drone traversing the link a↔b this turn.

        Args:
            a: First hub name.
            b: Second hub name.
        """
        key = self._key(a, b)
        self._counts[key] = self._counts.get(key, 0) + 1

    def reset(self) -> None:
        """Clear all per-turn link usage counts."""
        self._counts.clear()


# ---------------------------------------------------------------------------
# Main simulator
# ---------------------------------------------------------------------------

class Simulation:
    """Turn-based simulator that routes a fleet of drones through a network.

    Drones move one zone per turn.  A drone waits when:
    - Its next zone is blocked or at capacity.
    - The link to its next zone is at capacity for this turn.

    Lower drone IDs are given movement priority within the same turn.

    Args:
        network: The drone network.
        drones: Fleet of Drone objects with pre-assigned paths.
    """

    MAX_TURNS: int = 10_000  # safety limit to prevent infinite loops

    def __init__(self, network: Network, drones: List[Drone]) -> None:
        """Initialise the Simulation."""
        self.network = network
        self.drones = list(drones)
        self.turn_log: List[List[Move]] = []  # one list of Moves per turn

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def run(self) -> int:
        """Execute the simulation until all drones reach the end hub.

        Returns:
            Total number of turns taken.

        Raises:
            SimulationError: If drones cannot make progress within MAX_TURNS.
        """
        occupancy = ZoneOccupancy(self.network)
        link_usage = LinkUsage(self.network)

        # Place all drones at the start hub initially
        for drone in self.drones:
            occupancy.add(drone.current)

        turn = 0
        while not self._all_arrived():
            turn += 1
            if turn > self.MAX_TURNS:
                raise SimulationError(
                    f"Simulation did not complete within "
                    f"{self.MAX_TURNS} turns. "
                    "Check for unreachable goals or cyclic blockages."
                )

            link_usage.reset()
            turn_moves: List[Move] = []

            # Sort by drone id for deterministic priority
            for drone in sorted(self.drones, key=lambda d: d.id):
                if drone.arrived:
                    continue

                move = self._try_advance(drone, occupancy, link_usage)
                if move is not None:
                    turn_moves.append(move)

                    if drone.current == self.network.end.name:
                        drone.arrived = True

            self.turn_log.append(turn_moves)

        return turn

    def format_output(self, total_turns: int) -> str:
        """Format the full simulation output string.

        Each turn is represented as one line::

            T<n> D<id>:<from>-><to> D<id>:<from>-><to> ...

        Turns where no drone moved are omitted.

        Args:
            total_turns: The turn count returned by :meth:`run`.

        Returns:
            Human-readable simulation log followed by a summary line.
        """
        lines: List[str] = []
        for turn_no, moves in enumerate(self.turn_log, start=1):
            if not moves:
                continue
            parts = [f"T{turn_no}"] + [m.format() for m in moves]
            lines.append(" ".join(parts))
        lines.append(f"Simulation completed in {total_turns} turns.")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _all_arrived(self) -> bool:
        """Return True when every drone has reached the end hub.

        Returns:
            True if all drones are marked as arrived.
        """
        return all(d.arrived for d in self.drones)

    def _try_advance(
        self,
        drone: Drone,
        occupancy: ZoneOccupancy,
        link_usage: LinkUsage,
    ) -> Optional[Move]:
        """Attempt to advance *drone* one step along its path.

        The drone stays put when:
        - There is no next hub (already at end of path).
        - The next hub is at capacity.
        - The link to the next hub is at capacity for this turn.

        Args:
            drone: The drone to try to advance.
            occupancy: Current zone occupancy tracker.
            link_usage: Current turn's link usage tracker.

        Returns:
            A Move object on success, or None when the drone must wait.
        """
        next_hub = drone.next_hub()
        if next_hub is None:
            return None

        # Check zone capacity
        if not occupancy.has_space(next_hub):
            return None

        # Check link capacity
        if not link_usage.has_capacity(drone.current, next_hub):
            return None

        # Move is valid – commit it
        from_hub = drone.current
        occupancy.remove(from_hub)
        occupancy.add(next_hub)
        link_usage.use(from_hub, next_hub)
        drone.advance()

        return Move(drone.id, from_hub, next_hub)
