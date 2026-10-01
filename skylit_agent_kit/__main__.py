"""Run from the repository root: python3 -m skylit_agent_kit sample."""

import argparse
import sys

from .sample import DEFAULT_FIXTURE, load_fixture, render_brief


def main():
    parser = argparse.ArgumentParser(description="Skylit Agent Kit: offline-first starter")
    commands = parser.add_subparsers(dest="command", required=True)
    sample = commands.add_parser("sample", help="Render a fictional brief without network access")
    sample.add_argument("--fixture", default=str(DEFAULT_FIXTURE), help="Synthetic JSON fixture")
    args = parser.parse_args()
    try:
        source = "examples/fixtures/demo.json" if args.fixture == str(DEFAULT_FIXTURE) else args.fixture
        print(render_brief(load_fixture(args.fixture), source=source), end="")
    except (OSError, ValueError, UnicodeError) as error:
        print(f"Cannot render sample: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
