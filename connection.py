
class Connection:
    def __init__(self, zone1: str, zone2: str, max_capacity: int = 1):
        self.zone1 = zone1
        self.zone2 = zone2
        self.max_capacity = max_capacity
        self.drones_inside: list[int] = []

    def can_enter(self) -> bool:
        return len(self.drones_inside) < self.max_capacity

    def enter(self, drone_id: int) -> None:
        if drone_id not in self.drones_inside:
            self.drones_inside.append(drone_id)

    def leave(self, drone_id: int) -> None:
        if drone_id in self.drones_inside:
            self.drones_inside.remove(drone_id)

    def clear(self) -> None:
        self.drones_inside.clear()
