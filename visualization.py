import copy
import math
import os
import webcolors  # type: ignore[import-untyped,unused-ignore]
from connection import Connection
from drone import Drone
from zone import Zone

os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "hide"

import pygame  # noqa: E402


class Visualization:
    pygame.init()
    DroneState = dict[str, str]
    Frame = dict[str, DroneState]

    def __init__(
        self,
        zones: dict[str, Zone],
        connections: dict[tuple[str, str], Connection],
        result: list[list[str]],
        drones: list[Drone] | None = None,
        startZone: str = "start"
    ) -> None:
        self.zones = zones
        self.connections = connections
        self.drones = drones if drones else []

        info = pygame.display.Info()
        self.width: int = info.current_w
        self.height: int = info.current_h

        self.screen = pygame.display.set_mode(
            (self.width, self.height),
            pygame.RESIZABLE,
        )

        pygame.display.set_caption("Visualization")

        self.clock = pygame.time.Clock()

        self.zoom: float = 1.0
        self.offset_x: int = 100
        self.offset_y: int = self.height // 2
        self.base_scale: int = 150

        self.title_font = pygame.font.SysFont(
            "arial",
            28,
            bold=True,
        )

        self.name_font = pygame.font.SysFont(
            "arial",
            13,
            bold=True,
        )

        self.ui_font = pygame.font.SysFont(
            "consolas",
            18,
        )

        self.drone_font = pygame.font.SysFont(
            "arial",
            16,
            bold=True,
        )

        self.dragging: bool = False
        self.last_mouse_pos: tuple[int, int] = (0, 0)

        self.step_duration: int = 1
        self.current_step: int = 0
        self.step_progress: float = 0.0
        self.paused: bool = False

        self.spawn_zone: str = startZone

        self.frames = self.parse_result(result)

    def parse_result(
        self,
        result: list[list[str]],
    ) -> list[Frame]:
        frames = []

        current_state = {
            f"D{drone.id}": {
                "type": "zone",
                "zone": self.spawn_zone,
            }
            for drone in self.drones
        }

        frames.append(copy.deepcopy(current_state))

        for line in result:
            frame = copy.deepcopy(current_state)

            for part in line:
                if "-" not in part:
                    continue

                pieces = part.split("-")

                if len(pieces) == 2:
                    drone_id = pieces[0]
                    zone_name = pieces[1]

                    frame[drone_id] = {
                        "type": "zone",
                        "zone": zone_name,
                    }

                elif len(pieces) == 3:
                    drone_id = pieces[0]
                    from_zone = pieces[1]
                    to_zone = pieces[2]

                    frame[drone_id] = {
                        "type": "connection",
                        "from": from_zone,
                        "to": to_zone,
                    }

            frames.append(frame)
            current_state = frame

        return frames

    def _state_to_world_position(
        self,
        state: DroneState | None,
    ) -> tuple[float, float] | None:
        if state is None:
            return None

        state_type = state.get("type")

        if state_type == "zone":
            zone_name = state.get("zone")

            if zone_name is None:
                return None

            zone = self.zones.get(zone_name)

            if zone is None:
                return None

            return float(zone.x), float(zone.y)

        if state_type == "connection":
            from_name = state.get("from")
            to_name = state.get("to")

            if from_name is None or to_name is None:
                return None

            from_zone = self.zones.get(from_name)
            to_zone = self.zones.get(to_name)

            if from_zone is None or to_zone is None:
                return None

            return (
                (from_zone.x + to_zone.x) / 2,
                (from_zone.y + to_zone.y) / 2,
            )

        return None

    def world_to_screen(
        self,
        x: float,
        y: float,
    ) -> tuple[float, float]:
        screen_x = x * self.base_scale * self.zoom + self.offset_x
        screen_y = y * self.base_scale * self.zoom + self.offset_y

        return screen_x, screen_y

    def draw_connections(self) -> None:
        for (z1, z2), conn in self.connections.items():
            start = self.zones[z1]
            end = self.zones[z2]

            x1, y1 = self.world_to_screen(start.x, start.y)
            x2, y2 = self.world_to_screen(end.x, end.y)

            width = max(
                2,
                int(getattr(conn, "max_capacity", 1)),
            )

            pygame.draw.line(
                self.screen,
                webcolors.name_to_rgb("cyan"),
                (x1, y1),
                (x2, y2),
                width,
            )

    def draw_zone(
        self,
        name: str,
        x: float,
        y: float,
        zone_type: str,
        color: str = "default",
    ) -> None:
        ZONE_COLORS: dict[str, tuple[int, int, int]] = {
            "default": (255, 255, 255),
            "restricted": (128, 0, 0),
            "priority": (0, 128, 128),
        }
        outer_radius = max(18, int(24 * self.zoom))
        inner_radius = int(outer_radius * 0.33)

        color_inner = ZONE_COLORS.get(
            zone_type,
            ZONE_COLORS["default"],
        )
        if color == "rainbow":
            pygame.draw.circle(
                self.screen,
                (255, 0, 0),
                (int(x), int(y)),
                outer_radius,
            )

            pygame.draw.circle(
                self.screen,
                (0, 255, 0),
                (int(x), int(y)),
                int(outer_radius * 0.66),
            )

            pygame.draw.circle(
                self.screen,
                webcolors.name_to_rgb("blue"),
                (int(x), int(y)),
                int(outer_radius * 0.33),
            )
        else:
            try:
                color_outer = webcolors.name_to_rgb(color)
            except ValueError:
                color_outer = webcolors.name_to_rgb("white")

            pygame.draw.circle(
                self.screen,
                color_outer,
                (int(x), int(y)),
                outer_radius,
            )

            pygame.draw.circle(
                self.screen,
                color_inner,
                (int(x), int(y)),
                inner_radius,
            )

        text = self.name_font.render(
            name,
            True,
            webcolors.name_to_rgb("white"),
        )

        rect = text.get_rect(
            center=(int(x), int(y - outer_radius - 18)),
        )

        self.screen.blit(text, rect)

    def draw_zones(self) -> None:
        for name, zone in self.zones.items():
            x, y = self.world_to_screen(zone.x, zone.y)

            self.draw_zone(
                name,
                x,
                y,
                zone.zone_type,
                zone.color,
            )

    def draw_drone_at(
        self,
        drone_id: str,
        x: float,
        y: float,
    ) -> None:
        pulse = math.sin(
            pygame.time.get_ticks() * 0.005,
        )

        radius = max(
            12,
            int(14 * self.zoom + pulse * 2),
        )

        pygame.draw.circle(
            self.screen,
            webcolors.name_to_rgb("green"),
            (int(x), int(y)),
            radius,
        )

        pygame.draw.circle(
            self.screen,
            webcolors.name_to_rgb("white"),
            (int(x), int(y)),
            radius // 3,
        )

        label = self.drone_font.render(
            drone_id,
            False,
            webcolors.name_to_rgb("white"),
            webcolors.name_to_rgb("black"),
        )

        label_rect = label.get_rect(
            center=(int(x), int(y - radius - 15)),
        )

        self.screen.blit(label, label_rect)

    def draw_drones(self) -> None:
        if self.current_step >= len(self.frames) - 1:
            return

        current_frame = self.frames[self.current_step]
        next_frame = self.frames[self.current_step + 1]

        drone_ids = set(current_frame) | set(next_frame)

        for drone_id in drone_ids:
            start_state = current_frame.get(drone_id)
            end_state = next_frame.get(drone_id)

            start_pos = self._state_to_world_position(
                start_state,
            )

            end_pos = self._state_to_world_position(
                end_state,
            )

            if start_pos is None or end_pos is None:
                continue

            t = self.step_progress

            world_x = (
                start_pos[0]
                + (end_pos[0] - start_pos[0]) * t
            )

            world_y = (
                start_pos[1]
                + (end_pos[1] - start_pos[1]) * t
            )

            screen_x, screen_y = self.world_to_screen(
                world_x,
                world_y,
            )

            self.draw_drone_at(
                drone_id,
                screen_x,
                screen_y,
            )

    def update_animation(self, dt: float) -> None:
        if self.paused:
            return

        if len(self.frames) == 0:
            return

        self.step_progress += dt / self.step_duration

        if self.step_progress >= 1.0:
            self.step_progress = 0.0

            if self.current_step < len(self.frames) - 1:
                self.current_step += 1

    def handle_events(self) -> bool:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False

            if event.type == pygame.MOUSEWHEEL:
                self.zoom *= (
                    1.1 if event.y > 0 else 0.9
                )

                self.zoom = max(
                    0.25,
                    min(self.zoom, 5),
                )

            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    self.dragging = True
                    self.last_mouse_pos = event.pos

            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:
                    self.dragging = False

            elif event.type == pygame.MOUSEMOTION:
                if self.dragging:
                    dx = (
                        event.pos[0]
                        - self.last_mouse_pos[0]
                    )

                    dy = (
                        event.pos[1]
                        - self.last_mouse_pos[1]
                    )

                    self.offset_x += dx
                    self.offset_y += dy

                    self.last_mouse_pos = event.pos

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    self.paused = not self.paused
                if event.key == pygame.K_x:
                    return False
                elif event.key == pygame.K_RIGHT:
                    if (
                        self.current_step
                        < len(self.frames) - 1
                    ):
                        self.current_step += 1
                        self.step_progress = 0.0

                elif event.key == pygame.K_LEFT:
                    if self.current_step > 0:
                        self.current_step -= 1
                        self.step_progress = 0.0

                elif event.key == pygame.K_r:
                    self.current_step = 0
                    self.step_progress = 0.0

        return True

    def draw_ui(self) -> None:
        panel = pygame.Surface(
            (420, 110),
            pygame.SRCALPHA,
        )

        panel.fill((20, 25, 35, 190))

        self.screen.blit(panel, (15, 15))

        title = self.title_font.render(
            "DRONE NETWORK",
            True,
            webcolors.name_to_rgb("cyan"),
        )

        self.screen.blit(title, (30, 25))

        step_text = (
            f"STEP : {self.current_step}/"
            f"{max(1, len(self.frames) - 1)}"
        )

        state_text = (
            "PAUSED"
            if self.paused
            else "PLAYING"
        )

        t1 = self.ui_font.render(
            step_text,
            True,
            webcolors.name_to_rgb("white"),
        )

        t2 = self.ui_font.render(
            state_text,
            True,
            webcolors.name_to_rgb("green"),
        )

        self.screen.blit(t1, (30, 60))
        self.screen.blit(t2, (30, 85))

        controls = self.ui_font.render(
            "SPACE pause | ← → step | R reset",
            True,
            webcolors.name_to_rgb("whitesmoke"),
        )

        self.screen.blit(
            controls,
            (30, self.height - 35),
        )

    def display_zones(self) -> None:
        running = True

        while running:
            dt = self.clock.tick(60) / 1000.0

            running = self.handle_events()

            self.update_animation(dt)

            self.screen.fill(
                webcolors.name_to_rgb("black")
            )

            self.draw_connections()
            self.draw_zones()
            self.draw_drones()
            self.draw_ui()

            pygame.display.flip()

        pygame.quit()
