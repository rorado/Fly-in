from config import Config


class Drone:
    def __init__(self, drone_id: int, path: list[str]):
        self.id = drone_id
        self.path = path
        self.index = 0
        self.finished = False

        self.in_flight = False
        self.remaining = 0
        self.from_zone: str | None = None
        self.to_zone: str | None = None

    def current(self) -> str:
        return self.path[self.index]

    def next(self) -> str | None:
        if self.index + 1 < len(self.path):
            return self.path[self.index + 1]
        return None

    def move(self) -> str:
        self.index += 1

        if self.index == len(self.path) - 1:
            self.finished = True

        return self.path[self.index]

    def reroute_from_current(self, new_path_from_current: list[str]) -> None:
        if not new_path_from_current:
            return

        if new_path_from_current[0] != self.current():
            return
        self.path = self.path[: self.index + 1] + new_path_from_current[1:]

    def start_flight(self, from_zone: str, to_zone: str, cost: int) -> None:
        self.in_flight = True
        self.remaining = cost
        self.from_zone = from_zone
        self.to_zone = to_zone

    @staticmethod
    def getAllDrones(conf: Config, path: list[str]) -> list["Drone"]:
        if conf.nb_drones is None:
            return []
        return [Drone(i, path) for i in range(1, conf.nb_drones + 1)]
