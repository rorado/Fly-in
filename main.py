"""Entry point for the Fly-in drone routing simulator."""

import sys
from typing import List

from fly_in.parser import ParseError, build_drones, parse_file
from fly_in.pathfinding import PathfindingError, plan_routes
from fly_in.simulation import Simulation, SimulationError


def usage() -> str:
    """Return the CLI usage string.

    Returns:
        A human-readable usage hint.
    """
    return "Usage: python3 main.py <config.txt>"


def main(args: List[str]) -> int:
    """Parse, route, simulate and print results for a drone network file.

    Args:
        args: Command-line arguments (sys.argv).

    Returns:
        Exit code: 0 on success, 1 on any error.
    """
    if len(args) != 2:
        print(usage(), file=sys.stderr)
        return 1

    config_path = args[1]

    try:
        network = parse_file(config_path)
    except ParseError as err:
        print(f"Parse error: {err}", file=sys.stderr)
        return 1

    try:
        drone_paths = plan_routes(network)
    except PathfindingError as err:
        print(f"Pathfinding error: {err}", file=sys.stderr)
        return 1

    drones = build_drones(network)
    for drone, path in zip(drones, drone_paths):
        drone.assign_path(path)

    sim = Simulation(network, drones)

    try:
        total_turns = sim.run()
    except SimulationError as err:
        print(f"Simulation error: {err}", file=sys.stderr)
        return 1

    print(sim.format_output(total_turns))
    return 0


try:
    sys.exit(main(sys.argv))
except Exception as err:  # noqa: BLE001
    print(f"Unexpected error: {err}", file=sys.stderr)
    sys.exit(1)
