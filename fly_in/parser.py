"""Parser for Fly-in drone network configuration files."""

import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

from fly_in.models import Connection, Drone, Hub, Network, ZoneType


class ParseError(ValueError):
    """Raised when the configuration file is malformed or invalid."""


# ---------------------------------------------------------------------------
# Low-level helpers
# ---------------------------------------------------------------------------

def _parse_attributes(attr_str: str) -> Dict[str, str]:
    """Parse a bracketed attribute string into a key→value mapping.

    Expects the form ``[key=value key=value ...]``.  Unknown or missing
    brackets are tolerated.

    Args:
        attr_str: Raw attribute string, with or without enclosing ``[...]``.

    Returns:
        Dict mapping attribute names to their string values.
    """
    s = attr_str.strip()
    if s.startswith("["):
        s = s[1:]
    if s.endswith("]"):
        s = s[:-1]

    attrs: Dict[str, str] = {}
    for token in s.split():
        if "=" in token:
            k, v = token.split("=", 1)
            attrs[k.strip()] = v.strip()
    return attrs


def _parse_hub_value(
    value: str,
    line_no: int,
) -> Tuple[str, int, int, Dict[str, str]]:
    """Parse the value portion of a hub/start_hub/end_hub line.

    Expected format: ``name x y [key=val ...]``

    Args:
        value: Everything after the key colon on a hub line.
        line_no: Source line number (for error messages).

    Returns:
        Tuple of (name, x, y, attributes_dict).

    Raises:
        ParseError: If the format is invalid.
    """
    m = re.match(r"^(\S+)\s+(-?\d+)\s+(-?\d+)(?:\s+(\[.*\]))?$", value.strip())
    if not m:
        raise ParseError(
            f"Line {line_no}: invalid hub definition: {value!r}"
        )
    name = m.group(1)
    x = int(m.group(2))
    y = int(m.group(3))
    attrs = _parse_attributes(m.group(4) or "")
    return name, x, y, attrs


def _parse_connection_value(
    value: str,
    line_no: int,
) -> Tuple[str, str, Dict[str, str]]:
    """Parse the value portion of a connection line.

    Expected format: ``hubA-hubB [key=val ...]``

    Args:
        value: Everything after the key colon on a connection line.
        line_no: Source line number (for error messages).

    Returns:
        Tuple of (hub_a, hub_b, attributes_dict).

    Raises:
        ParseError: If the format is invalid.
    """
    m = re.match(r"^(\S+)-(\S+)(?:\s+(\[.*\]))?$", value.strip())
    if not m:
        raise ParseError(
            f"Line {line_no}: invalid connection definition: {value!r}"
        )
    hub_a = m.group(1)
    hub_b = m.group(2)
    attrs = _parse_attributes(m.group(3) or "")
    return hub_a, hub_b, attrs


def _build_hub(
    name: str,
    x: int,
    y: int,
    attrs: Dict[str, str],
    is_start: bool = False,
    is_end: bool = False,
) -> Hub:
    """Construct a Hub from parsed fields.

    Args:
        name: Hub identifier.
        x: X-coordinate.
        y: Y-coordinate.
        attrs: Raw attribute dict from the config file.
        is_start: Mark this hub as the simulation start.
        is_end: Mark this hub as the simulation end.

    Returns:
        A fully constructed Hub instance.
    """
    zone_str = attrs.get("zone", "normal").lower()
    try:
        zone_type = ZoneType(zone_str)
    except ValueError:
        zone_type = ZoneType.NORMAL

    color = attrs.get("color", "white")

    max_drones = 1
    if "max_drones" in attrs:
        try:
            max_drones = int(attrs["max_drones"])
        except ValueError:
            max_drones = 1

    return Hub(
        name=name,
        x=x,
        y=y,
        zone_type=zone_type,
        color=color,
        max_drones=max_drones,
        is_start=is_start,
        is_end=is_end,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse_network(lines: List[str]) -> Network:
    """Parse a list of configuration lines into a Network object.

    Args:
        lines: Raw text lines from the configuration file.

    Returns:
        A fully constructed Network ready for simulation.

    Raises:
        ParseError: If the input is structurally invalid.
    """
    nb_drones: Optional[int] = None
    start_hub: Optional[Hub] = None
    end_hub: Optional[Hub] = None
    hubs: Dict[str, Hub] = {}
    connections: List[Connection] = []

    for line_no, raw in enumerate(lines, start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue

        if ":" not in line:
            raise ParseError(
                f"Line {line_no}: expected KEY: VALUE, got: {raw!r}"
            )

        key, value = line.split(":", 1)
        key = key.strip().lower()
        value = value.strip()

        if not key:
            raise ParseError(f"Line {line_no}: empty key in: {raw!r}")

        if key == "nb_drones":
            try:
                nb_drones = int(value)
            except ValueError:
                raise ParseError(
                    f"Line {line_no}: nb_drones must be an integer, "
                    f"got {value!r}"
                )
            if nb_drones < 1:
                raise ParseError(
                    f"Line {line_no}: nb_drones must be >= 1, got {nb_drones}"
                )

        elif key == "start_hub":
            name, x, y, attrs = _parse_hub_value(value, line_no)
            hub = _build_hub(name, x, y, attrs, is_start=True)
            start_hub = hub
            hubs[name] = hub

        elif key == "end_hub":
            name, x, y, attrs = _parse_hub_value(value, line_no)
            hub = _build_hub(name, x, y, attrs, is_end=True)
            end_hub = hub
            hubs[name] = hub

        elif key == "hub":
            name, x, y, attrs = _parse_hub_value(value, line_no)
            if name in hubs:
                raise ParseError(
                    f"Line {line_no}: duplicate hub name {name!r}"
                )
            hubs[name] = _build_hub(name, x, y, attrs)

        elif key == "connection":
            hub_a, hub_b, attrs = _parse_connection_value(value, line_no)
            cap_str = attrs.get("max_link_capacity", "1")
            try:
                cap = int(cap_str)
            except ValueError:
                cap = 1
            connections.append(Connection(hub_a, hub_b, cap))

        else:
            # Unknown keys are silently ignored to allow forward compatibility.
            pass

    # Validate mandatory fields
    if nb_drones is None:
        raise ParseError("Missing required field: nb_drones")
    if start_hub is None:
        raise ParseError("Missing required field: start_hub")
    if end_hub is None:
        raise ParseError("Missing required field: end_hub")

    # Validate connection endpoints exist
    for conn in connections:
        for hub_name in (conn.hub_a, conn.hub_b):
            if hub_name not in hubs:
                raise ParseError(
                    f"Connection references unknown hub: {hub_name!r}"
                )

    return Network(
        nb_drones=nb_drones,
        start=start_hub,
        end=end_hub,
        hubs=hubs,
        connections=connections,
    )


def parse_file(path: Union[str, Path]) -> Network:
    """Parse a drone network configuration file.

    Args:
        path: Path to the configuration file.

    Returns:
        The parsed Network.

    Raises:
        ParseError: If the file cannot be read or its contents are invalid.
    """
    p = Path(path)
    if not p.exists():
        raise ParseError(f"File not found: {path}")
    if not p.is_file():
        raise ParseError(f"Path is not a file: {path}")

    try:
        content = p.read_text(encoding="utf-8")
    except OSError as err:
        raise ParseError(f"Cannot read file {path}: {err}") from err

    return parse_network(content.splitlines())


def build_drones(network: Network) -> List[Drone]:
    """Create the fleet of Drone objects for the given network.

    Args:
        network: The parsed Network (provides nb_drones and start hub).

    Returns:
        List of Drone objects, IDs starting at 1.
    """
    return [
        Drone(i, network.start.name) for i in range(1, network.nb_drones + 1)
    ]


# Keep old name for backwards compatibility
def parseFile(path: Union[str, Path]) -> Network:  # noqa: N802
    """Alias for parse_file (legacy entry point).

    Args:
        path: Path to the configuration file.

    Returns:
        The parsed Network.
    """
    return parse_file(path)
