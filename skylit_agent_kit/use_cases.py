"""Offline-first composed workflows, with explicit bounded live opt-in."""
from .use_case_errors import UseCaseError
import argparse
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

from .node_tracker import chart, expiries, parse_time, report, track
from .recipe_reports import render_recipe
from .watchlist_cli import credential, output_path, save_private

FIXTURES = Path(__file__).resolve().parents[1] / 'examples' / 'fixtures' / 'use-cases'
NAMES = ('node-tracker', 'price-levels', 'flow-investigator', 'volatility-context')


def add_parser(commands):
    p = commands.add_parser('use-case', help='Build a useful offline report; optional saved JSON or explicit live mode')
    p.add_argument('recipe', choices=NAMES)
    mode = p.add_mutually_exclusive_group()
    mode.add_argument('--live', action='store_true', help='Authorize this bounded plan only; no retries')
    mode.add_argument('--input', help='Read saved source JSON locally (maximum 8 MiB)')
    mode.add_argument('--dry-run', action='store_true', help='Print exact plans only; no key or network')
    p.add_argument('--symbol', help='One exact uppercase symbol; no aliases are substituted')
    p.add_argument('--metric', choices=['gamma', 'vanna'], default='gamma')
    p.add_argument('--strikes', help='Node tracker: 1–8 fixed strike prices')
    p.add_argument('--expirations', help='Explicit comma-separated YYYY-MM-DD dates')
    p.add_argument('--from', dest='from_time', help='RFC3339 start with timezone')
    p.add_argument('--to', dest='to_time', help='RFC3339 end with timezone; node replay at most 15 minutes')
    p.add_argument('--max-credits', type=int, default=10, help='Total plan cap; node replay requires explicit 25')
    p.add_argument('--max-requests', type=int, default=3, help='Total request cap including one free account preflight')
    p.add_argument('--max-seconds', type=float, default=30)
    p.add_argument('--output', help='New Markdown path inside repository reports/; tracker also saves sibling .svg')


def reject_nonfinite(value):
    raise UseCaseError('Saved JSON contains a nonfinite number.')


def load_json(path):
    try:
        with Path(path).open('rb') as f: raw = f.read(8 * 1024 * 1024 + 1)
        if len(raw) > 8 * 1024 * 1024: raise UseCaseError('Saved JSON exceeds 8 MiB.')
        value = json.loads(raw, parse_constant=reject_nonfinite)
    except (OSError, UnicodeError, RecursionError, json.JSONDecodeError):
        raise UseCaseError('Could not read valid saved JSON.') from None
    if not isinstance(value, dict): raise UseCaseError('Saved JSON must be an object.')
    return value


def request_specs(args, symbol, start, end, expiration_set):
    """Pure parameters. Shared endpoint planner validates names, URLs, types and costs."""
    if args.recipe == 'node-tracker':
        return [('heatseeker.getHistoricalRange', {'symbols': symbol, 'metric': args.metric, 'from': start, 'to': end, 'expirations': ','.join(expiration_set), 'maxStrikes': 92})]
    if args.recipe == 'price-levels':
        return [('atlas.getHistory', {'symbol': symbol, 'resolution': '1', 'from': int(parse_time(start).timestamp()), 'to': int(parse_time(end).timestamp())}),
                ('heatseeker.getLevels', {'symbols': symbol, 'metric': args.metric, 'expirations': ','.join(expiration_set), 'maxStrikes': 92})]
    if args.recipe == 'flow-investigator':
        common = {'ticker': symbol, 'start_time': start, 'end_time': end}
        return [('flowseeker.getFlow', dict(common, timeframe='1d', limit=10)),
                ('flowseeker.getFlowStrikes', dict(common, top_n=10, order_by='total_premium'))]
    return [('heatseeker.getVolIv', {'symbols': symbol}), ('heatseeker.getVolCones', {'symbols': symbol})]


def validate_window(start, end, recipe, live):
    a, b = parse_time(start), parse_time(end)
    if b <= a: raise UseCaseError('--to must be after --from.')
    if recipe == 'node-tracker' and (b-a).total_seconds() > 900: raise UseCaseError('Node replay window must be at most 15 minutes.')
    if recipe != 'node-tracker' and (b-a).total_seconds() > 86400: raise UseCaseError('This recipe uses a bounded window of at most 24 hours.')
    if live and b > datetime.now(timezone.utc): raise UseCaseError('--to must not be in the future.')


def run(args):
    # Import lazily: the tracker and saved-data transforms are independently reusable.
    from .endpoint_demo import plan_request
    synthetic = not args.live and not args.input
    if args.input:
        synthetic = Path(args.input).resolve().parent == FIXTURES.resolve()
    if (args.live or args.input) and not args.symbol: raise UseCaseError('Supply --symbol for source data or a live request.')
    symbol = args.symbol or 'SPY'
    if not re.fullmatch(r'[A-Z0-9][A-Z0-9.:^/_-]{0,31}', symbol): raise UseCaseError('Use one exact uppercase symbol.')
    if (args.live or args.input) and args.recipe != 'volatility-context' and (not args.from_time or not args.to_time):
        raise UseCaseError('Source time-window recipes require explicit --from and --to.')
    if (args.live or args.input) and args.recipe in ('node-tracker', 'price-levels') and not args.expirations:
        raise UseCaseError('Supply an explicit --expirations set for this source-data recipe.')
    expiration_set = list(expiries(args.expirations.split(',') if args.expirations else ['2026-10-02']))
    start, end = args.from_time or '2026-09-30T14:00:00Z', args.to_time or '2026-09-30T14:06:00Z'
    saved = load_json(args.input) if args.input else None
    if saved is not None and args.recipe == 'node-tracker':
        try:
            start = args.from_time or saved['data']['from']; end = args.to_time or saved['data']['to']
        except (KeyError, TypeError): raise UseCaseError('Saved replay lacks response coverage.') from None
    validate_window(start, end, args.recipe, args.live and args.recipe != 'volatility-context')
    if (args.live or args.input) and args.recipe == 'node-tracker' and not args.strikes:
        raise UseCaseError('Supply explicit --strikes for source node tracking; fictional prices are not live defaults.')
    try: strikes = [float(s) for s in (args.strikes or '100,105').split(',')]
    except ValueError: raise UseCaseError('--strikes must be comma-separated numeric prices.') from None
    from .node_tracker import finite
    if args.recipe == 'node-tracker' and (not 1 <= len(strikes) <= 8 or len(set(strikes)) != len(strikes) or any(not finite(s) for s in strikes)):
        raise UseCaseError('Choose 1–8 unique finite strikes.')
    if not finite(args.max_seconds) or not 1 <= args.max_seconds <= 300 or args.max_credits < 0 or args.max_requests < 1:
        raise UseCaseError('Invalid credit, request or elapsed caps.')
    specs = request_specs(args, symbol, start, end, expiration_set)
    plans = [plan_request(endpoint, params) for endpoint, params in specs]
    credits = sum(p['credits'] for p in plans)
    plan_text = json.dumps(plans, indent=2)
    if args.dry_run:
        print(f'DRY RUN — no credentials, network or credits used. Plan: {credits} documented credits; {len(plans)+1} requests including free preflight.\n{plan_text}')
        print(f'Caps: {args.max_credits} credits / {args.max_requests} requests / {args.max_seconds:g} seconds.')
        return 0
    if synthetic and not args.input:
        if symbol != 'SPY':
            raise UseCaseError('The bundled fictional demo uses SPY. Omit --symbol, or supply matching saved data with --input; --dry-run can plan other symbols without data.')
        if args.recipe in ('node-tracker', 'price-levels') and args.metric != 'gamma':
            raise UseCaseError('The bundled fictional demo uses gamma. Omit --metric, or supply matching saved data with --input; --dry-run can plan other metrics without data.')
    # Resolve every destination before network or credentials.
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    root = Path(__file__).resolve().parents[1]
    destination = output_path(args.output or str(root / 'reports' / f'{args.recipe}-{stamp}.md'))
    svg_destination = output_path(str(destination.with_suffix('.svg'))) if args.recipe == 'node-tracker' else None
    if svg_destination == destination: raise UseCaseError('Use a Markdown output filename, not .svg.')
    if args.live:
        if credits > args.max_credits or len(plans)+1 > args.max_requests:
            raise UseCaseError(f'Plan requires {credits} credits and {len(plans)+1} requests including preflight; caps are unchanged. Set an explicit sufficient budget to proceed.')
        print(f'LIVE PLAN — {credits} documented credits; {len(plans)+1} requests including free account preflight.\n{plan_text}')
        from .endpoint_demo import execute_plans, validate_plan_for_live
        for plan in plans: validate_plan_for_live(plan)
        payloads = execute_plans(plans, credential(), max_credits=args.max_credits, max_requests=args.max_requests, max_seconds=args.max_seconds)
        data = payloads[0] if args.recipe == 'node-tracker' else {spec[0]: p for spec, p in zip(specs, payloads)}
    else: data = saved if saved is not None else load_json(FIXTURES / (args.recipe + '.json'))
    if args.recipe == 'node-tracker':
        result = track(data, symbol, args.metric, strikes, expiration_set)
        if parse_time(result['from']) != parse_time(start) or parse_time(result['to']) != parse_time(end):
            raise UseCaseError('Response window differs from the requested comparison window.')
        body = report(result, synthetic)
        svg = chart(result, synthetic)
        body += f'\n![Signed exposure over actual time]({quote(svg_destination.name, safe="")})\n'
    else:
        body = render_recipe(args.recipe, data, symbol, args.metric, start, end, synthetic=synthetic)
        body = ('**SYNTHETIC / FICTIONAL DATA**\n\n' if synthetic else '**User-supplied or live data — authenticity, freshness and comparability unverified.**\n\n') + body
    provenance = 'Bundled independent synthetic fixtures' if synthetic else ('User-supplied saved responses; authenticity/freshness unverified; no new requests' if args.input else 'Explicit live bounded request plan')
    body += f'\n\nProvenance: {provenance}.\n\n## Request plan\n\n{credits} documented credits / {len(plans)+1} requests including one free account preflight if executed live. This run used {"live requests" if args.live else "zero network requests and zero credits"}.\n\n'
    body += 'The plan below records selected parameters; for saved inputs it is a reproduction plan, not proof of how the saved file was acquired.\n\n```json\n' + plan_text + '\n```\n'
    tutorial = Path(os.path.relpath(root / 'docs/use-cases.md', destination.parent)).as_posix()
    body += '\n## Build it yourself\n\n1. Choose one exact symbol and explicit coverage.\n2. Build the endpoint plans shown above with `plan_request`.\n3. Load saved JSON or execute the entire list once with `execute_plans` and explicit caps.\n4. Preserve source timestamps, gaps and labels; render the evidence tables locally.\n\n'
    body += f'See [the use-case tutorial]({quote(tutorial, safe="/")}) for copyable commands and agent prompts.\n'
    if svg_destination: save_private(svg_destination, svg)
    save_private(destination, body)
    print(body)
    print(f'\nSaved report: {destination}')
    if svg_destination: print(f'Saved chart: {svg_destination}')
    return 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); commands = parser.add_subparsers(dest='command', required=True)
    add_parser(commands)
    try: raise SystemExit(run(parser.parse_args()))
    except ValueError as error: parser.exit(2, f'Error: {error}\n')
