import re
from pathlib import Path
from pydantic import ValidationError

from config import (
    Config,
    Conn,
    ConnValue,
    Hub,
    HubValue,
    StartEndValue,
)


class ParseError(ValueError):
    """Raised when the configuration file is invalid."""


class ConfigParser:

    def __init__(self) -> None:
        self.OPTIONS_METADATA_HUB: set[str] = {
            "zone",
            "color",
            "max_drones",
        }

        self.ZONE_TYPES: set[str] = {
            "normal",
            "blocked",
            "restricted",
            "priority",
        }

        self.REQUIRED_KEYS: set[str] = {
            "nb_drones",
            "start_hub",
            "end_hub",
        }

    @staticmethod
    def is_word(text: str) -> bool:
        return bool(re.fullmatch(r"[a-zA-Z]+", text))

    @staticmethod
    def remove_brackets(text: str) -> str:
        return re.sub(r"\[.*?\]", "", text).strip()

    @staticmethod
    def parse_metadata(text: str) -> dict[str, str]:
        inside: list[str] = re.findall(r"\[(.*?)\]", text)

        if not inside:
            return {}

        if len(inside) > 1:
            raise ParseError("only one metadata block is allowed")

        result: dict[str, str] = {}

        for part in inside[0].split():
            if "=" not in part:
                raise ParseError(f"invalid metadata: {part}")

            key, value = part.split("=", 1)
            result[key.strip().lower()] = value.strip().lower()

        return result

    def validate_metadata_hubs(
        self,
        metadata: dict[str, str],
        *,
        startOrend: bool = False,
    ) -> None:
        for key, value in metadata.items():
            if not value:
                raise ParseError(f"{key} not have value")

            if key not in self.OPTIONS_METADATA_HUB:
                raise ParseError(f"unexpected metadata key: {key}")

            if key == "zone" and value not in self.ZONE_TYPES:
                raise ParseError(f"invalid zone type: {value}")

            elif startOrend:
                if key == "zone" and value == "blocked":
                    raise ParseError(
                        f"zone {value} can't be in start_hub or end_hub"
                    )

            elif key == "color":
                if len(value.split()) != 1:
                    raise ParseError("color must be one word")

                if len(value) <= 1:
                    raise ParseError("color must be at least 1 letter")

                if not self.is_word(value):
                    raise ParseError(f"{value}: invalid word")

            elif key == "max_drones":
                try:
                    number = int(value)
                except ValueError:
                    raise ParseError("max_drones must be integer")

                if number < 1:
                    raise ParseError("max_drones must be >= 1")

    def validate_hub_value(self, text: str) -> tuple[str, HubValue]:
        values = self.remove_brackets(text).split()

        if len(values) != 3:
            raise ParseError(
                f"expected 3 values, got {len(values)}"
            )

        if "-" in values[0]:
            raise ParseError("zone name can't containe (-)")

        try:
            return (
                values[0],
                HubValue(
                    x=int(values[1]),
                    y=int(values[2]),
                ),
            )
        except ValueError as err:
            raise ParseError(str(err))

    def validate_SE_value(self, text: str) -> StartEndValue:
        values = self.remove_brackets(text).split()

        if len(values) != 3:
            raise ParseError(
                f"expected 3 values, got {len(values)}"
            )

        if "-" in values[0]:
            raise ParseError("zone name can't containe (-)")

        try:
            return StartEndValue(
                name=values[0],
                x=int(values[1]),
                y=int(values[2]),
            )
        except ValueError as err:
            raise ParseError(str(err))

    def validate_conn_value(self, text: str) -> ConnValue:
        values = self.remove_brackets(text).split("-")

        if len(values) != 2:
            raise ParseError(
                "expected 2 values (from and to)"
            )

        return ConnValue(
            from_hub=values[0].strip(),
            to_hub=values[1].strip(),
        )

    @staticmethod
    def validate_metadata_conn(
        metadata: dict[str, str],
    ) -> None:
        for key, value in metadata.items():
            if not value:
                raise ParseError(f"{key} not have value")

            if key != "max_link_capacity":
                raise ParseError(
                    f"unexpected metadata key: {key}"
                )

            try:
                number = int(value)
            except ValueError:
                raise ParseError(
                    "max_link_capacity must be integer"
                )

            if number < 1:
                raise ParseError(
                    "max_link_capacity must be >= 1"
                )

    @staticmethod
    def checkduplicitConn(
        conf: Config,
        from_hub: str,
        to_hub: str,
    ) -> bool:
        zone_names: set[str] = set()

        if conf.hubs:
            zone_names.update(conf.hubs.keys())

        if (
            conf.start_hub is not None
            and conf.start_hub.value is not None
        ):
            zone_names.add(conf.start_hub.value.name)

        if (
            conf.end_hub is not None
            and conf.end_hub.value is not None
        ):
            zone_names.add(conf.end_hub.value.name)

        if from_hub not in zone_names:
            raise ParseError(f"{from_hub}: invalid zone")

        if to_hub not in zone_names:
            raise ParseError(f"{to_hub}: invalid zone")

        if not conf.connections:
            return False

        key = (
            (from_hub, to_hub)
            if from_hub < to_hub
            else (to_hub, from_hub)
        )

        for c in conf.connections.values():

            if c.value is None:
                continue

            current_from = c.value.from_hub
            current_to = c.value.to_hub

            if (
                current_from is None
                or current_to is None
            ):
                continue

            current_key = (
                (current_from, current_to)
                if current_from < current_to
                else (current_to, current_from)
            )

            if current_key == key:
                raise ParseError(
                    "The same connection must not "
                    "appear more than once"
                )

        return False

    def parse_file(self, path: str) -> Config:
        p = Path(path)

        if not p.exists():
            raise ParseError(
                f"file not found: {path}"
            )

        if not p.is_file():
            raise ParseError(
                f"path is not a file: {path}"
            )

        try:
            content = p.read_text(
                encoding="utf-8",
            )
        except Exception as err:
            raise ParseError(
                f"cannot read file: {err}"
            )

        return self.parse_kv_lines(
            content.splitlines()
        )

    def parse_kv_lines(
        self,
        lines: list[str],
    ) -> Config:
        try:
            config = Config()

            conn_count = 0
            found_required = set()

            start_hub = 0
            end_hub = 0

            rankedZone = 0

            for idx, raw in enumerate(
                lines,
                start=1,
            ):
                line = raw.split("#")[0].strip()

                if not line:
                    continue

                if ":" not in line:
                    raise ParseError(
                        f"line {idx}: missing ':'"
                    )

                key, value = line.split(":", 1)

                key = key.strip().lower()
                value = value.strip()

                if key in self.REQUIRED_KEYS:
                    found_required.add(key)

                if key == "nb_drones":

                    if rankedZone > 0:
                        raise ParseError(
                            "line "
                            f"{idx}: The first line "
                            "must define the number "
                            "of drones using "
                            "nb_drones: "
                            "<positive_integer> "
                            "NOT HERE !!"
                        )

                    rankedZone += 1
                    # print(value.split()[0])
                    try:
                        config.nb_drones = int(
                            value.strip()
                        )
                    except (
                        IndexError,
                        ValueError,
                    ):
                        raise ParseError(
                            f"line {idx}: "
                            "invalid nb_drones value"
                        )

                    if config.nb_drones < 1:
                        raise ParseError(
                            f"line {idx}: "
                            "nb_drones must be >= 1"
                        )

                elif key in (
                    "start_hub",
                    "end_hub",
                ):
                    rankedZone += 1

                    if key == "start_hub":
                        if start_hub:
                            raise ParseError(
                                f"line{idx}: {key} is duplicate"
                            )

                        start_hub += 1

                    elif key == "end_hub":
                        if end_hub:
                            raise ParseError(
                                f"line{idx}: {key} is duplicate"
                            )

                        end_hub += 1

                    try:
                        hub_data = self.validate_SE_value(
                            value
                        )

                        metadata = self.parse_metadata(
                            value
                        )

                        self.validate_metadata_hubs(
                            metadata,
                            startOrend=True,
                        )

                        hub = Hub(
                            value=hub_data,
                            metadata={
                                **(
                                    Hub().metadata
                                    or {}
                                ),
                                **metadata,
                            },
                        )

                        setattr(
                            config,
                            key,
                            hub,
                        )

                    except ParseError as err:
                        raise ParseError(
                            f"line {idx} "
                            f"{key}: {err}"
                        )

                elif key == "hub":
                    rankedZone += 1

                    try:
                        (
                            name,
                            hub_value,
                        ) = self.validate_hub_value(
                            value
                        )

                        metadata = self.parse_metadata(
                            value
                        )

                        self.validate_metadata_hubs(
                            metadata
                        )

                        if (
                            config.hubs
                            and config.hubs.get(name)
                        ):
                            raise ParseError(
                                f"line {idx}: zone "
                                "must have a unique "
                                f"name got {name}"
                            )

                        elif (
                            (
                                config.start_hub
                                is not None
                                and (
                                    config.start_hub
                                    .value
                                    is not None
                                )
                                and (
                                    config.start_hub
                                    .value.name
                                    == name
                                )
                            )
                            or (
                                config.end_hub
                                is not None
                                and (
                                    config.end_hub
                                    .value
                                    is not None
                                )
                                and (
                                    config.end_hub
                                    .value.name
                                    == name
                                )
                            )
                        ):
                            raise ParseError(
                                f"line {idx}: zone "
                                "must have a unique "
                                f"name got {name}"
                            )

                        if config.hubs is None:
                            config.hubs = {}

                        config.hubs[name] = HubValue(
                            x=hub_value.x,
                            y=hub_value.y,
                            metadata={
                                **(
                                    HubValue()
                                    .metadata
                                    or {}
                                ),
                                **metadata,
                            },
                        )

                    except ParseError as err:
                        raise ParseError(
                            f"line {idx} "
                            f"hub: {err}"
                        )

                elif key == "connection":
                    rankedZone += 1

                    try:
                        conn_data = (
                            self.validate_conn_value(
                                value
                            )
                        )

                        if (
                            conn_data.from_hub
                            == conn_data.to_hub
                        ):
                            raise ParseError(
                                "from_hub and "
                                "to_hub have "
                                "same zone name"
                            )

                        if (
                            conn_data.from_hub
                            is None
                            or conn_data.to_hub
                            is None
                        ):
                            raise ParseError(
                                "connection hubs "
                                "cannot be None"
                            )

                        raw_metadata = (
                            self.parse_metadata(
                                value
                            )
                        )

                        self.validate_metadata_conn(
                            raw_metadata
                        )

                        conn_metadata: dict[
                            str,
                            int,
                        ] = {
                            k: int(v)
                            for k, v
                            in raw_metadata.items()
                        }

                        if not self.checkduplicitConn(
                            config,
                            conn_data.from_hub,
                            conn_data.to_hub,
                        ):
                            conn_count += 1

                            if (
                                config.connections
                                is None
                            ):
                                config.connections = {}

                            base_metadata = (
                                Conn().metadata
                                or {}
                            )

                            config.connections[
                                f"conn{conn_count}"
                            ] = Conn(
                                value=conn_data,
                                metadata={
                                    **base_metadata,
                                    **conn_metadata,
                                },
                            )

                    except ParseError as err:
                        raise ParseError(
                            f"line {idx}: {err}"
                        )

                else:
                    raise ParseError(
                        f"line {idx}: "
                        f"unknown key {key}"
                    )

            missing = (
                self.REQUIRED_KEYS
                - found_required
            )

            if missing:
                raise ParseError(
                    f"Missing required keys: "
                    f"{missing}"
                )

            return config

        except ValidationError as err:
            raise ParseError(
                err.errors()[0]["msg"]
            )
