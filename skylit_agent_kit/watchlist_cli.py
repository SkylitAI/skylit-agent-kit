"""Explicit live opt-in, secure credential input, and ignored local reports."""
import getpass
import json
import os
import sys
import warnings
from datetime import datetime, timezone
from pathlib import Path

from .watchlist import DEFAULT_SYMBOLS, WatchlistError, execute_live, make_plan, number, render_report, valid_date


def add_parser(commands):
    parser = commands.add_parser('watchlist', help='Plan GEX/VEX and flow; add --live to send bounded requests')
    parser.add_argument('--symbols', default=DEFAULT_SYMBOLS, help='Comma-separated tickers, deduplicated in order')
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--live', action='store_true', help='Authorize the displayed bounded REST workflow')
    mode.add_argument('--dry-run', action='store_true', help='Plan only (the default); no key or network')
    parser.add_argument('--max-credits', type=int, default=10, help='Documented credit reservation cap (default 10)')
    parser.add_argument('--max-requests', type=int, default=12, help='Includes free discovery requests (default 12)')
    parser.add_argument('--max-seconds', type=float, default=120, help='Elapsed budget checked before/between I/O (default 120)')
    parser.add_argument('--batch-size', type=int, default=10, help='Heatmap symbols per call, bounded further by account')
    parser.add_argument('--flow-limit', type=int, default=10, help='Recent trades fetched per symbol, 1–500; 3 displayed')
    parser.add_argument('--date', help='Explicit flow trading date YYYY-MM-DD; does not change live heatmap date')
    parser.add_argument('--output', help='Save Markdown in this repository\'s ignored reports/ directory')
    parser.add_argument('--save-raw', action='store_true', help='Also save full market responses in ignored reports/; excludes account')


def output_path(name):
    root = Path(__file__).resolve().parents[1] / 'reports'
    # Reject a symlinked reports root and paths escaping it.
    if root.is_symlink(): raise WatchlistError('reports/ must not be a symlink.')
    path = Path(name).absolute()
    if not path.resolve().is_relative_to(root.resolve()) or path.is_symlink():
        raise WatchlistError('Save output inside this repository\'s ignored reports/ directory.')
    if path.exists(): raise WatchlistError('Output file already exists; choose a new name.')
    return path


def save_private(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_NOFOLLOW', 0), 0o600)
    with os.fdopen(descriptor, 'w') as stream: stream.write(content)


def credential():
    key = os.environ.get('SKYLIT_API_KEY')
    if key: return key
    if not sys.stdin.isatty():
        raise WatchlistError('Open a terminal for the hidden key prompt, or provide SKYLIT_API_KEY securely in the process environment. Never paste a key into chat.')
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error', getpass.GetPassWarning)
            return getpass.getpass('Skylit API key (hidden; used for this run only): ')
    except (getpass.GetPassWarning, EOFError):
        raise WatchlistError('A hidden key prompt is unavailable; use a secure process environment.') from None


def run(args):
    plan = make_plan(args.symbols, args.batch_size)
    if args.max_credits < 0 or args.max_requests < 2:
        raise WatchlistError('Use a nonnegative credit cap and at least 2 requests for discovery.')
    if not number(args.max_seconds) or not 1 <= args.max_seconds <= 3600:
        raise WatchlistError('Elapsed budget must be between 1 and 3600 seconds.')
    if not 1 <= args.flow_limit <= 500: raise WatchlistError('Flow limit must be 1–500.')
    if args.date is not None and not valid_date(args.date): raise WatchlistError('Use --date YYYY-MM-DD.')
    destination = output_path(args.output) if args.output else None
    raw_destination = None
    if args.save_raw:
        stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        raw_destination = output_path(str(Path(__file__).resolve().parents[1] / 'reports' / f'watchlist-{stamp}.json'))
    if not args.live:
        print('DRY RUN — no credentials read, no requests sent, no credits used.')
        print('Symbols: ' + ', '.join(plan['symbols']))
        print(f'Assuming heatmap batches of {args.batch_size}: {plan["requests"]} requests including 2 free discovery calls; {plan["credits"]} documented credits.')
        print(f'Your caps: {args.max_requests} requests, {args.max_credits} documented credits, {args.max_seconds:g} seconds.')
        print('Heatmaps: gamma and vanna, up to 92 strikes / nearest 5 expirations. Flow: 1d, up to ' + str(args.flow_limit) + ' trades each.')
        print('Account limits and symbol support are checked before paid calls; a smaller account batch may require a larger plan and stop this run.')
        if plan['requests'] > args.max_requests or plan['credits'] > args.max_credits:
            print('This estimated plan exceeds your caps. No live calls have been made.')
        print('To connect, run again with --live. If needed, create your key at https://app.skylit.ai/developer and enter it only at the hidden terminal prompt.')
        return 0
    print(f'Live caps: {args.max_requests} requests / {args.max_credits} documented credits; one run, no retries.', file=sys.stderr)
    result = execute_live(credential(), symbols=plan['symbols'], max_requests=args.max_requests,
        max_credits=args.max_credits, max_seconds=args.max_seconds, batch_size=args.batch_size,
        flow_limit=args.flow_limit, trading_date=args.date, save_raw=args.save_raw)
    report = render_report(result)
    if destination:
        save_private(destination, report)
        print(f'Saved report: {destination}')
    else: print(report, end='')
    if raw_destination:
        save_private(raw_destination, json.dumps({'retrieved_at': result['retrieved_at'], 'responses': result['raw']}, indent=2) + '\n')
        print(f'Saved private market responses: {raw_destination}', file=sys.stderr)
    return 0 if result['stop'] == 'completed' else 2
