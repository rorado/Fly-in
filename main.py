import sys
import importlib.util


class Start:
    @staticmethod
    def usage() -> str:
        """Return CLI usage string."""
        return ("Usage: python3 main.py <map.txt>")

    @staticmethod
    def check_packages() -> None:
        packages = ["pydantic", "webcolors", "pygame"]

        missing: list[str] = []

        for package in packages:
            if importlib.util.find_spec(package) is None:
                missing.append(package)

        if missing:
            raise ImportError(
                "Missing important packages: "
                + ", ".join(missing)
                + "\nTo run the program without issues, run: make install"
            )

    def main(self, args: list[str]) -> int:
        self.check_packages()

        from file_parser import ConfigParser
        from config import Config
        from graph import Graph
        from pathfinder import Pathfinder
        from drone import Drone
        from simulation import Simulation

        if len(args) != 2:
            print(self.usage(), file=sys.stderr)
            return 1
        parser = ConfigParser()

        config: Config = parser.parse_file(args[1])

        gr = Graph(config)

        pathfinder = Pathfinder(gr, config)

        candidate_paths = pathfinder.get_candidate_paths(
            max_paths=8
        )

        if not candidate_paths:
            raise ValueError(
                "No valid path from start_hub to end_hub"
            )

        path = (
            candidate_paths[0],
            pathfinder.path_cost(candidate_paths[0])
        )

        drones = Drone.getAllDrones(config, path[0])
        simulation = Simulation(
            config,
            drones,
            path[0],
            candidate_paths=candidate_paths,
        )

        simulation.run()
        simulation.visualization()
        return 0


try:
    start = Start()
    sys.exit(start.main(sys.argv))

except KeyboardInterrupt:
    print("\nProgram interrupted")

except SystemExit:
    raise

except Exception as err:
    print(err)
