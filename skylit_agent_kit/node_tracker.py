"""Fixed-strike observations from public historical/range; ordinary arithmetic only."""
import math
import json
import re
from collections import Counter
from datetime import date, datetime, timezone
from html import escape


def parse_time(value):
    if not isinstance(value, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})', value):
        raise ValueError('Timestamps must be RFC3339 with a timezone.')
    return datetime.fromisoformat(value.replace('Z', '+00:00')).astimezone(timezone.utc)


def finite(value):
    try: return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)
    except OverflowError: return False


def expiries(values):
    if not isinstance(values, list) or not values or not all(isinstance(v, str) and re.fullmatch(r'\d{4}-\d{2}-\d{2}', v) for v in values):
        raise ValueError('An explicit nonempty expiration date set is required.')
    for value in values: date.fromisoformat(value)
    if len(set(values)) != len(values): raise ValueError('Duplicate expirations are ambiguous.')
    return tuple(sorted(values))


def source_metadata(meta):
    selected = {k: meta[k] for k in ('mode', 'resolution', 'delayed', 'delayMinutes', 'attribution') if k in meta}
    return escape(json.dumps(selected, ensure_ascii=True)).replace('|', '&#124;').replace('`', '&#96;')


def track(payload, symbol, metric, strikes, expiration_set):
    """Reject malformed identity/time; represent duplicate times and coverage loss as gaps."""
    expected = expiries(expiration_set)
    if not isinstance(symbol, str) or not re.fullmatch(r'[A-Z0-9][A-Z0-9.:^/_-]{0,31}', symbol):
        raise ValueError('Use one exact uppercase symbol, without markup or whitespace.')
    if not strikes or len(strikes) > 8 or any(not finite(s) for s in strikes) or len(set(strikes)) != len(strikes):
        raise ValueError('Choose 1–8 unique finite strike values.')
    try:
        if metric not in ('gamma', 'vanna') or payload['meta']['metric'] != metric:
            raise ValueError('Response metric does not match the requested metric.')
        data = payload['data']; start, end = parse_time(data['from']), parse_time(data['to'])
        if end < start: raise ValueError('Response window is reversed.')
        symbols = data['symbols']
        if not isinstance(symbols, list) or any(not isinstance(s, dict) for s in symbols): raise ValueError('Invalid symbol list.')
        selected = [s for s in symbols if s.get('symbol') == symbol]
        if len(selected) != 1: raise ValueError('Expected exactly one matching symbol, without alias substitution.')
        selected = selected[0]; axes = {}
        for axis in selected['axes']:
            aid, ss = axis['id'], axis['strikes']
            if type(aid) is not int or aid in axes: raise ValueError('Duplicate or invalid axis ID.')
            if not isinstance(ss, list) or any(not finite(s) for s in ss) or len(set(ss)) != len(ss):
                raise ValueError('Invalid or duplicate axis strikes.')
            axes[aid] = (ss, expiries(axis['expirations']))
        frames = []
        if len(selected['frames']) > 10000: raise ValueError('Too many frames for this bounded report.')
        for f in selected['frames']:
            stamp = parse_time(f['asOf'])
            if not start <= stamp <= end: raise ValueError('Frame falls outside the response window.')
            if type(f['axis']) is not int or f['axis'] not in axes: raise ValueError('Frame references an unknown axis.')
            ss, ex = axes[f['axis']]; vals = f['values']
            if not isinstance(vals, list) or len(vals) != len(ss) or any(not finite(v) for v in vals):
                raise ValueError('Values must be finite and match the referenced axis length.')
            if not finite(f['spot']): raise ValueError('Invalid spot value.')
            frames.append((stamp, f, dict(zip(ss, vals)), ex))
        counts = Counter(f[0] for f in frames); series = {s: [] for s in strikes}; seen = set()
        for stamp, f, values, ex in sorted(frames, key=lambda f: f[0]):
            if stamp in seen: continue
            seen.add(stamp)
            for strike, points in series.items():
                status = 'observed'
                if counts[stamp] > 1: status = 'duplicate timestamp'
                elif ex != expected: status = 'incomparable expiry set'
                elif strike not in values: status = 'strike absent'
                value = values.get(strike) if status == 'observed' else None
                prev = points[-1]['value'] if points else None
                comparable = value is not None and prev is not None
                delta = value - prev if comparable else None
                magnitude_delta = abs(value) - abs(prev) if comparable else None
                pct = 100 * magnitude_delta / abs(prev) if comparable and prev != 0 else None
                if any(v is not None and not finite(v) for v in (delta, magnitude_delta, pct)):
                    raise ValueError('Arithmetic overflow in change calculation.')
                points.append({'asOf': f['asOf'], 'timestamp': stamp.timestamp(), 'axis': f['axis'],
                    'expirations': list(ex), 'spot': f['spot'], 'value': value,
                    'magnitude': abs(value) if value is not None else None, 'delta': delta,
                    'magnitude_delta': magnitude_delta, 'magnitude_pct': pct, 'status': status})
    except (KeyError, TypeError, AttributeError):
        raise ValueError('Invalid historical/range response shape.') from None
    return {'symbol': symbol, 'metric': metric, 'expirations': list(expected), 'series': series,
            'source_meta': source_metadata(payload['meta']), 'from': data['from'], 'to': data['to'], 'frame_count': len(frames), 'unique_times': len(seen)}


def fmt(value):
    return '—' if value is None else f'{value:,.4g}'


def chart(result, synthetic=False):
    """A standalone SVG with actual timestamp spacing and breaks at explicit gaps."""
    points = [p for pp in result['series'].values() for p in pp]
    times = [p['timestamp'] for p in points]
    values = [p['value'] for p in points if p['value'] is not None] + [0]
    xmin, xmax = (min(times), max(times)) if times else (0, 1)
    scale = max(abs(v) for v in values) or 1
    ymin, ymax = min(values) / scale, max(values) / scale
    if ymin == ymax: ymin, ymax = ymin - 1, ymax + 1
    pad = (ymax - ymin) * .1; ymin -= pad; ymax += pad
    x = lambda t: 95 + 730 * (t - xmin) / (xmax - xmin or 1)
    y = lambda v: 345 - 235 * (v / scale - ymin) / (ymax - ymin)
    title = f"{result['symbol']} · {result['metric']} · fixed strikes"
    out = ['<svg xmlns="http://www.w3.org/2000/svg" width="960" height="460" viewBox="0 0 960 460" role="img">',
        f'<title>{escape(title)}</title><desc>Signed exposure; zero line; gaps are not interpolated. Time axis uses actual UTC spacing.</desc>',
        '<rect width="960" height="460" fill="#f7f5f0"/>', '<g font-family="sans-serif" fill="#17292e">',
        f'<text x="45" y="35" font-size="22">{escape(title)}</text>',
        f'<text x="45" y="60" font-size="13">{"SYNTHETIC / FICTIONAL DATA" if synthetic else "SOURCE DATA / freshness not certified"}</text>',
        f'<text x="45" y="82" font-size="12">Expirations: {escape(", ".join(result["expirations"]))}</text>',
        f'<line x1="95" x2="825" y1="{y(0):.2f}" y2="{y(0):.2f}" stroke="#697d83" stroke-dasharray="5 4"/>']
    for v in (min(values), 0, max(values)): out.append(f'<text x="85" y="{y(v)+4:.2f}" text-anchor="end" font-size="11">{fmt(v)}</text>')
    out.append('<text x="840" y="95" font-size="12">Strike</text>')
    colors = ['#076b82', '#b34237', '#6e51a3', '#3e7a47', '#995a13', '#4054b0', '#986178', '#57646a']
    for i, (strike, pp) in enumerate(result['series'].items()):
        color = colors[i]; segment = []
        def flush():
            if len(segment) > 1: out.append(f'<polyline points="{" ".join(segment)}" fill="none" stroke="{color}" stroke-width="2"/>')
            segment.clear()
        for p in pp:
            if p['value'] is None: flush(); continue
            px, py = x(p['timestamp']), y(p['value']); segment.append(f'{px:.2f},{py:.2f}')
            out.append(f'<circle cx="{px:.2f}" cy="{py:.2f}" r="3" fill="{color}"><title>{escape(p["asOf"])} / {fmt(p["value"])}</title></circle>')
        flush()
        out.append(f'<text x="840" y="{115 + 22*i}" fill="{color}" font-size="13">{strike:g}</text>')
    for t, anchor in ((xmin, 'start'), (xmax, 'end')):
        label = datetime.fromtimestamp(t, timezone.utc).isoformat() if times else 'No observations'
        out.append(f'<text x="{x(t):.2f}" y="377" text-anchor="{anchor}" font-size="11">{label}</text>')
    out.append('<text x="45" y="414" font-size="12">Signed source exposure · gaps break lines · no interpolated observations</text></g></svg>')
    return '\n'.join(out)


def report(result, synthetic=False):
    lines = ['# Fixed-strike node tracker', '', '**SYNTHETIC / FICTIONAL DATA**' if synthetic else '**Source data — freshness not certified**', '',
        f"Symbol: {result['symbol']} · metric: {result['metric']} · expirations: {', '.join(result['expirations'])}",
        f"Source metadata: {result['source_meta']}", '',
        f"Requested response coverage: {result['from']} → {result['to']}; {result['frame_count']} frames / {result['unique_times']} unique times.", '',
        ('No observations returned. No changes can be established.' if not result['unique_times'] else 'Observed frames shown below.'), '',
        'Missing strikes, duplicate timestamps and changed expiry sets remain gaps. Tables show at most 200 timestamps per strike; the SVG includes all returned observations. Changes compare adjacent comparable observations only. No value is interpolated. Magnitude % is undefined after zero.', '',
        '| Strike | Source asOf | Signed value | Magnitude | Δ value | Δ magnitude | Magnitude % | Coverage |',
        '|---|---|---:|---:|---:|---:|---:|---|']
    for strike, points in result['series'].items():
        for p in points[:200]:
            lines.append(f'| {strike:g} | {p["asOf"]} | {fmt(p["value"])} | {fmt(p["magnitude"])} | {fmt(p["delta"])} | {fmt(p["magnitude_delta"])} | {fmt(p["magnitude_pct"])} | {p["status"]}; axis {p["axis"]}; {", ".join(p["expirations"])} |')
    lines += ['', 'Exposure changes alone do not establish changes in positioning or their cause. This report does not classify lifecycle stages, count taps, estimate probabilities, or give trade advice.', '',
        'Educational context: [Node Lifecycle: Fresh, Tested, Delivered, and Decaying Levels](https://www.skylit.ai/learn/node-lifecycle) motivates observing a level over time; this demo supplies arithmetic observations only.', '']
    return '\n'.join(lines)
