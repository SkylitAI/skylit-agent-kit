"""Run from the repository root: python3 -m skylit_agent_kit sample."""

import argparse
import json
import os
import sys

from .account import AccountError, read_account
from .sample import DEFAULT_FIXTURE, load_fixture, render_brief
from .watchlist import WatchlistError
from .watchlist_cli import add_parser, credential, run as run_watchlist_cli
from .endpoint_demo import EndpointError
from . import endpoint_cli, use_cases
from .use_case_errors import UseCaseError
from .welcome import render_welcome


def main():
    parser = argparse.ArgumentParser(description="Skylit Agent Kit: offline-first starter")
    commands = parser.add_subparsers(dest="command", required=True)
    sample = commands.add_parser("sample", help="Render a fictional brief without network access")
    sample.add_argument("--fixture", default=str(DEFAULT_FIXTURE), help="Synthetic JSON fixture")
    account = commands.add_parser("account", help="Explicit live account lookup (one GET, no retries)")
    account.add_argument('--welcome', action='store_true',
                         help='Show a branded connection check instead of account JSON; supports a hidden key prompt')
    add_parser(commands)
    endpoint_cli.add_parser(commands)
    use_cases.add_parser(commands)
    args = parser.parse_args()
    try:
        if args.command in ('endpoints','endpoint'):
            return endpoint_cli.run(args)
        if args.command == 'use-case':
            return use_cases.run(args)
        if args.command == 'watchlist':
            return run_watchlist_cli(args)
        if args.command == "account":
            key = credential() if args.welcome else os.environ.get("SKYLIT_API_KEY", "")
            response = read_account(key)
            print(render_welcome(response) if args.welcome else json.dumps(response, indent=2))
        else:
            source = "examples/fixtures/demo.json" if args.fixture == str(DEFAULT_FIXTURE) else args.fixture
            print(render_brief(load_fixture(args.fixture), source=source), end="")
    except KeyboardInterrupt:
        print("Cancelled. No further requests will be sent.", file=sys.stderr)
        return 130
    except (AccountError, WatchlistError, EndpointError, UseCaseError) as error:
        print(str(error), file=sys.stderr)
        return 1
    except (OSError, ValueError, UnicodeError) as error:
        if args.command in ("watchlist", "endpoints", "endpoint", "use-case"):
            print("Cannot complete command: check local file paths, permissions and input format.", file=sys.stderr)
        else:
            print(f"Cannot render sample: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
