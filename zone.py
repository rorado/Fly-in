from dataclasses import dataclass, field


@dataclass
class Zone:
    x: int
    y: int
    name: str
    color: str
    zone_type: str = field(default="normal")
    max_drones: int = 1
    allowed_multiples: bool = False
    drones_inside: list[int] = field(default_factory=list)

    def can_enter(self) -> bool:
        if self.zone_type == "blocked":
            return False
        if self.allowed_multiples:
            return True
        return len(self.drones_inside) < self.max_drones

    def enter(self, drone_id: int) -> None:
        if drone_id not in self.drones_inside:
            self.drones_inside.append(drone_id)

    def leave(self, drone_id: int) -> None:
        if drone_id in self.drones_inside:
            self.drones_inside.remove(drone_id)
