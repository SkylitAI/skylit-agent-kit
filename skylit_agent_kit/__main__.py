"""Run from the repository root: python3 -m skylit_agent_kit sample."""

import argparse
import getpass
import json
import os
import sys

from .account import AccountError, read_account
from . import doctor, journey, keystore
from .keystore import KeystoreError
from .sample import DEFAULT_FIXTURE, load_fixture, render_brief
from .watchlist import WatchlistError
from .watchlist_cli import add_parser, credential, run as run_watchlist_cli
from .endpoint_demo import EndpointError
from . import endpoint_cli, use_cases
from .use_case_errors import UseCaseError
from .welcome import render_welcome


def login():
    if not sys.stdin.isatty():
        print('login needs an interactive terminal for the hidden prompt. Run it in a terminal, not through an agent.', file=sys.stderr)
        return 1
    key = getpass.getpass('Paste your Skylit API key (input hidden): ').strip()
    if not key:
        print('No key entered; nothing was stored.', file=sys.stderr)
        return 1
    where = keystore.save(key)
    print(f'Stored your key in {where}. It was not checked with Skylit yet.')
    print(f'Next (step 4): {journey.KIT} account --welcome   (or tell your agent "done")')
    print(f'Remove it any time: {journey.KIT} logout')
    return 0


def main():
    parser = argparse.ArgumentParser(
        prog=journey.KIT, formatter_class=argparse.RawDescriptionHelpFormatter,
        description='Connect your Skylit account, then explore live data.\n\n' + journey.render_text())
    commands = parser.add_subparsers(dest="command", metavar='{doctor,login,account,...}')
    commands.add_parser('doctor', help='Step 1: check setup offline and print the next step (no key, no network)')
    commands.add_parser('login', help='Step 3: store your Skylit API key from a hidden prompt in your own terminal')
    account = commands.add_parser("account", help="Step 4: account check; add --welcome for the connection proof (free)")
    account.add_argument('--welcome', action='store_true',
                         help='Show a branded connection check instead of account JSON; supports a hidden key prompt')
    commands.add_parser('logout', help='Remove the locally stored Skylit API key')
    sample = commands.add_parser("sample", help="Render a fictional brief without network access")
    sample.add_argument("--fixture", default=str(DEFAULT_FIXTURE), help="Synthetic JSON fixture")
    add_parser(commands)
    endpoint_cli.add_parser(commands)
    use_cases.add_parser(commands)
    args = parser.parse_args()
    if args.command is None:
        print(journey.render_start())
        return 0
    try:
        if args.command == 'doctor':
            return doctor.run()
        if args.command == 'login':
            return login()
        if args.command == 'logout':
            print('Removed the stored Skylit API key.' if keystore.delete() else 'No stored Skylit API key was found.')
            return 0
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
    except (AccountError, KeystoreError, WatchlistError, EndpointError, UseCaseError) as error:
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
