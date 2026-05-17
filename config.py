from pydantic import BaseModel, Field


class HubValue(BaseModel):
    x: int | None = None
    y: int | None = None

    metadata: dict[str, str | int | None] = Field(
        default_factory=lambda: {
            "zone": "normal",
            "color": None,
            "max_drones": 1,
        }
    )


class StartEndValue(BaseModel):
    name: str
    x: int
    y: int


class Hub(BaseModel):
    value: StartEndValue | None = None

    metadata: dict[str, str | int | None] = Field(
        default_factory=lambda: {
            "zone": "normal",
            "color": None,
            "max_drones": 1,
        }
    )


class ConnValue(BaseModel):
    from_hub: str | None = Field(
        min_length=1,
        max_length=500,
    )

    to_hub: str | None = Field(
        min_length=1,
        max_length=500,
    )


class Conn(BaseModel):
    value: ConnValue | None = None

    metadata: dict[str, int] = Field(
        default_factory=lambda: {
            "max_link_capacity": 1,
        }
    )


class Config(BaseModel):
    nb_drones: int | None = Field(default=1)

    start_hub: Hub | None = None
    end_hub: Hub | None = None

    hubs: dict[str, HubValue] = Field(
        default_factory=dict
    )

    connections: dict[str, Conn] = Field(
        default_factory=dict
    )
