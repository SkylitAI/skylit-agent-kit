"""The smallest live result: one heatmap call (1 credit) drawn as a per-strike bar chart."""
import json
import re
import sys
from datetime import datetime, timezone
from html import escape
from pathlib import Path

from .attribution import credit, notice_line
from .endpoint_demo import execute_plan, plan_request, validate_plan_for_live
from .node_tracker import finite, fmt
from .use_case_errors import UseCaseError
from .watchlist_cli import credential, output_path, save_private

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / 'examples' / 'fixtures' / 'first-chart-spy.json'
SYMBOL = re.compile(r'[A-Z][A-Z0-9.]{0,9}')
MAX_STRIKES = 40
WIDTH, ZERO_X, HALF, ROW, TOP = 960, 500, 330, 16, 104
LABEL_X = ZERO_X - HALF - 40  # strike labels, right-aligned
COLORS = {True: '#2563c9', False: '#c2620f'}  # positive, negative


def add_parser(commands):
    parser = commands.add_parser('first-chart', help='Draw one heatmap as a bar chart; offline demo by default, --live costs 1 credit')
    parser.add_argument('--symbol', default='SPY', help='One ticker (default SPY)')
    parser.add_argument('--metric', choices=('gamma', 'vanna'), default='gamma')
    parser.add_argument('--live', action='store_true', help='Send one free account check and one 1-credit heatmap request')
    parser.add_argument('--max-credits', type=float, default=1, help='Credit cap (default 1); never raised automatically')


def load_fixture():
    return json.loads(FIXTURE.read_text(encoding='utf-8'))


def timestamp(value):
    try:
        datetime.fromisoformat(value.replace('Z', '+00:00'))
    except (AttributeError, ValueError):
        raise UseCaseError('Heatmap returned no valid board timestamp; nothing was saved.') from None
    return value


def extract(payload, symbol, metric='gamma'):
    data = payload.get('data') if isinstance(payload, dict) else None
    boards = data.get('symbols') if isinstance(data, dict) else None
    board = next((b for b in boards or [] if isinstance(b, dict) and b.get('symbol') == symbol), None)
    if board is None:
        raise UseCaseError(f'Heatmap returned no board for {symbol}; nothing was saved.')
    if not finite(board.get('spot')):
        raise UseCaseError('Heatmap returned no usable spot price; nothing was saved.')
    nodes, gaps = [], 0
    for node in board.get('strikes') if isinstance(board.get('strikes'), list) else []:
        if not isinstance(node, dict) or not finite(node.get('strike')):
            continue
        if not finite(node.get('value')):
            gaps += 1
            continue
        kind = node.get('nodeType')
        nodes.append({'strike': node['strike'], 'value': node['value'], 'nodeType': kind if isinstance(kind, str) else ''})
    if not nodes:
        raise UseCaseError('Heatmap returned no strikes with usable values; nothing was saved.')
    # Keep the strikes nearest spot so the chart stays readable.
    nodes = sorted(sorted(nodes, key=lambda n: abs(n['strike'] - board['spot']))[:MAX_STRIKES], key=lambda n: n['strike'])
    meta = payload.get('meta') if isinstance(payload.get('meta'), dict) else {}
    expirations = [e for e in board.get('expirations') or [] if isinstance(e, str)]
    return {'symbol': symbol, 'metric': meta.get('metric') if meta.get('metric') in ('gamma', 'vanna') else metric,
            'asOf': timestamp(board.get('asOf')), 'spot': board['spot'], 'expirations': expirations,
            'nodes': nodes, 'gaps': gaps, 'notices': notice_line(payload)}


def scale(view):
    return max(abs(n['value']) for n in view['nodes']) or 1


def bar_geometry(view):
    bars = []
    for row, node in enumerate(reversed(view['nodes'])):  # high strike on top
        width = abs(node['value']) / scale(view) * HALF
        bars.append({**node, 'y': TOP + row * ROW, 'width': width,
                     'x': ZERO_X if node['value'] >= 0 else ZERO_X - width})
    return bars


def spot_y(view, bars):
    ordered = sorted(bars, key=lambda b: b['y'])
    for upper, lower in zip(ordered, ordered[1:]):
        if lower['strike'] <= view['spot'] <= upper['strike']:
            span = upper['strike'] - lower['strike'] or 1
            return upper['y'] + ROW / 2 + (upper['strike'] - view['spot']) / span * ROW
    return None


def chart(view, synthetic=False):
    bars = bar_geometry(view)
    height = TOP + len(bars) * ROW + 70
    title = f'{view["symbol"]} {view["metric"]} by strike' + (' — FICTIONAL demo data' if synthetic else '')
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{height}" viewBox="0 0 {WIDTH} {height}" role="img">',
           f'<title>{escape(title)}</title><desc>Net exposure per strike from one heatmap snapshot; positive right, negative left of zero.</desc>',
           f'<rect width="{WIDTH}" height="{height}" fill="#ffffff"/>',
           '<g font-family="system-ui, sans-serif" fill="#1b1f24">',
           f'<text x="40" y="38" font-size="22">{escape(title)}</text>',
           f'<text x="40" y="62" font-size="12">Board as of {escape(view["asOf"])} · expirations {escape(", ".join(view["expirations"]) or "not listed")}</text>',
           f'<line x1="{ZERO_X}" y1="{TOP - 8}" x2="{ZERO_X}" y2="{TOP + len(bars) * ROW}" stroke="#8b949e"/>',
           f'<text x="{ZERO_X - HALF}" y="{TOP - 12}" font-size="11" fill="#57606a">−{fmt(scale(view))}</text>',
           f'<text x="{ZERO_X}" y="{TOP - 12}" font-size="11" fill="#57606a" text-anchor="middle">0</text>',
           f'<text x="{ZERO_X + HALF}" y="{TOP - 12}" font-size="11" fill="#57606a" text-anchor="end">+{fmt(scale(view))}</text>']
    for bar in bars:
        y = bar['y']
        out.append(f'<text x="{LABEL_X}" y="{y + 12}" font-size="11" font-family="monospace" text-anchor="end">{fmt(bar["strike"])}</text>')
        out.append(f'<rect x="{bar["x"]:.2f}" y="{y + 3}" width="{max(bar["width"], 0.5):.2f}" height="{ROW - 5}" fill="{COLORS[bar["value"] >= 0]}">'
                   f'<title>{fmt(bar["strike"])}: {fmt(bar["value"])}</title></rect>')
        if bar['nodeType'] not in ('', 'normal'):
            out.append(f'<text x="{ZERO_X + HALF + 12}" y="{y + 12}" font-size="11">{escape(bar["nodeType"])}</text>')
    y = spot_y(view, bars)
    if y is not None:
        out.append(f'<line x1="{LABEL_X + 6}" y1="{y:.2f}" x2="{ZERO_X + HALF}" y2="{y:.2f}" stroke="#1b1f24" stroke-dasharray="4 3"/>')
        out.append(f'<text x="40" y="{y + 4:.2f}" font-size="11" font-weight="bold">spot {fmt(view["spot"])}</text>')
    label = 'Demo by Skylit (fictional data)' if synthetic else 'Data: Skylit'
    out.append(f'<text x="40" y="{height - 24}" font-size="12">Blue: positive · orange: negative · {escape(label)} · skylit.ai</text>')
    out.append('</g></svg>')
    return '\n'.join(out) + '\n'


def report(view, svg_path, synthetic=False):
    biggest = sorted(view['nodes'], key=lambda n: abs(n['value']), reverse=True)[:3]
    classified = [n for n in view['nodes'] if n['nodeType'] not in ('', 'normal')]
    lines = [f'# {view["symbol"]} {view["metric"]} by strike' + (' — SYNTHETIC / FICTIONAL' if synthetic else ''), '',
             f'![{view["symbol"]} {view["metric"]} by strike]({svg_path.name})', '',
             f'- Board as of: {view["asOf"]} (source timestamp; spot can be newer than the board)',
             f'- Spot: {fmt(view["spot"])}',
             f'- Expirations: {", ".join(view["expirations"]) or "not listed"}',
             '- Largest by magnitude: ' + '; '.join(f'{fmt(n["strike"])} = {fmt(n["value"])}' for n in biggest)]
    if classified:
        lines.append('- Node labels: ' + '; '.join(f'{n["nodeType"]} {fmt(n["strike"])}' for n in classified))
    if view['gaps']:
        lines.append(f'- Gaps: {view["gaps"]} strike{"s" if view["gaps"] != 1 else ""} without a usable value (not drawn)')
    lines += ['', 'Source values from one snapshot, not signals or advice.', '', credit(synthetic)]
    if view['notices']:
        lines += ['', view['notices']]
    return '\n'.join(lines) + '\n'


def run(args):
    symbol = args.symbol.strip().upper()
    if not SYMBOL.fullmatch(symbol):
        raise UseCaseError('Use one ticker, for example --symbol SPY.')
    plan = plan_request('heatseeker.getHeatmap', {'symbols': symbol, 'metric': args.metric, 'maxStrikes': str(MAX_STRIKES)})
    if args.live:
        if plan['credits'] > args.max_credits:
            raise UseCaseError(f'This chart needs {plan["credits"]:g} credit; --max-credits is {args.max_credits:g}. Nothing was sent.')
        plan = validate_plan_for_live(plan)
        print(f'Live: 1 free account check + 1 heatmap request, {plan["credits"]:g} credit; no retries.', file=sys.stderr)
        response = execute_plan(plan, credential(), max_credits=args.max_credits, max_requests=2, max_seconds=30)
        view, synthetic = extract(response, symbol, args.metric), False
    else:
        fixture = load_fixture()
        view, synthetic = extract(fixture, 'SPY', 'gamma'), True
        print(f'OFFLINE DEMO — fictional SPY data, no key read, no requests sent.')
        print(f'For your live chart (1 credit plus one free account check): '
              f'python3 -m skylit_agent_kit first-chart --live --symbol {symbol} --metric {args.metric}')
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    name = f'first-chart-{"demo" if synthetic else symbol.lower()}-{view["metric"]}-{stamp}'
    svg_path = output_path(str(ROOT / 'reports' / f'{name}.svg'))
    md_path = output_path(str(ROOT / 'reports' / f'{name}.md'))
    content = report(view, svg_path, synthetic)
    save_private(svg_path, chart(view, synthetic))
    save_private(md_path, content)
    print(f'Saved chart: {svg_path}')
    print(f'Saved report: {md_path}')
    print()
    print(content, end='')
    return 0
