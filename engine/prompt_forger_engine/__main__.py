"""Entry point.

  prompt-forger-engine              -> run the JSON-lines server (used by the desktop app)
  prompt-forger-engine --form F.json -> forge once from a JSON file and print the result
  prompt-forger-engine --version
"""

from __future__ import annotations

import argparse
import json
import sys

from . import __version__
from .forge import forge
from .server import run


def main() -> None:
    parser = argparse.ArgumentParser(prog="prompt-forger-engine", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--form", help="Forge once from this JSON form file and print the result.")
    parser.add_argument("--version", action="version", version=__version__)
    args = parser.parse_args()

    if args.form:
        with open(args.form, encoding="utf-8") as fh:
            result = forge(json.load(fh))
        json.dump(result, sys.stdout, indent=2, ensure_ascii=False)
        sys.stdout.write("\n")
        sys.exit(0 if result["ok"] else 2)
    run()


if __name__ == "__main__":
    main()
