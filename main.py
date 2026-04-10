import sys
from pathlib import Path
from fly_in.parser import parseFile

def usage() -> str:
    """Return CLI usage string."""
    return "Usage: python3 a_maze_ing.py <config.txt>"

def main(args: list[str]):
    if len(args) != 2:
        print(usage(), file=sys.stderr)
        return 1


    is_valid = parseFile(args[1])
    print(is_valid)

try:
    sys.exit(main(sys.argv))
except Exception as err:
    print(err)



