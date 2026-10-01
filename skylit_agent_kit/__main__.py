"""Run from the repository root: python3 -m skylit_agent_kit sample."""

import argparse
import json
import os
import sys

from .account import AccountError, read_account
from .sample import DEFAULT_FIXTURE, load_fixture, render_brief


def main():
    parser = argparse.ArgumentParser(description="Skylit Agent Kit: offline-first starter")
    commands = parser.add_subparsers(dest="command", required=True)
    sample = commands.add_parser("sample", help="Render a fictional brief without network access")
    sample.add_argument("--fixture", default=str(DEFAULT_FIXTURE), help="Synthetic JSON fixture")
    commands.add_parser("account", help="Explicit live account lookup using SKYLIT_API_KEY (one GET, no retries)")
    args = parser.parse_args()
    try:
        if args.command == "account":
            print(json.dumps(read_account(os.environ.get("SKYLIT_API_KEY", "")), indent=2))
        else:
            source = "examples/fixtures/demo.json" if args.fixture == str(DEFAULT_FIXTURE) else args.fixture
            print(render_brief(load_fixture(args.fixture), source=source), end="")
    except AccountError as error:
        print(str(error), file=sys.stderr)
        return 1
    except (OSError, ValueError, UnicodeError) as error:
        print(f"Cannot render sample: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
