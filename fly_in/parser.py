from pathlib import Path
from typing import Dict, Iterable

class ParseError(ValueError):
    """Raised when the configuration file is invalid."""


def parseFile(path: Path) -> bool:
    p = Path(path)

    if not p.exists():
        raise ParseError(f"File not found: {path}")
    if not p.is_file():
        raise ParseError(f"Config path is not a file: {path}")

    try:
        content = p.read_text(encoding="utf-8")
    except Exception as err:
        raise ParseError(f"Unable to read config file: {err}")

    kv = parse_kv_lines(content.splitlines())

    for section, values in kv.items():

        if isinstance(values, dict):
            for k, v in values.items():
                print(k, ":", v)
        else:
            print(section, ":", values)
        
    return True


def parse_kv_lines(lines: Iterable[str]) -> Dict[str, Dict[str, str]]:
    """Parse KEY:VALUE lines into a dict, ignoring blanks and comment lines."""

    output: Dict[str, Dict[str, str]] = {}
    HUB = 0
    CONNECTION = 0
    for idx, raw in enumerate(lines, start=1):
        line = raw.strip()

        if not line or line.startswith("#"):
            continue

        if ":" not in line:
            raise ParseError(f"Line {idx}: expected KEY:VALUE, got: {raw!r}")


        key, value = line.split(":", 1)
        key = key.strip().upper()
        value = value.strip()

        if not key:
            raise ParseError(f"Line {idx}: empty key in: {raw!r}")
        if value == "":
            raise ParseError(f"Line {idx}: empty value for key {key!r}")

        if key in ("HUB", "CONNECTION"):
            if key == "HUB":
                HUB += 1
                entry_key = f"{key}{HUB}"
            elif key == "CONNECTION":
                CONNECTION += 1
                entry_key = f"{key}{CONNECTION}"

            if key not in output:
                output[key] = {}

            output[key][entry_key] = value
        else:
            if key not in output:
                output[key] = {}

            output[key] = value

    return output

