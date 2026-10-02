"""Small evidence reports. Scores/levels remain source outputs, never reconstructed."""
from .use_case_errors import UseCaseError
from .attribution import credit, notice_line, safe_metadata
from datetime import datetime, timezone
import re
from .node_tracker import finite, fmt, parse_time, source_metadata


def cell(value):
    return re.sub(r'[\x00-\x1f\x7f]', ' ', str(value)).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('|', '&#124;').replace('\n', ' ').replace('\r', ' ')[:500]


def table(headers, rows):
    return '\n'.join(['| ' + ' | '.join(headers) + ' |', '|' + '|'.join('---' for _ in headers) + '|'] + ['| ' + ' | '.join(cell(v) for v in row) + ' |' for row in rows])


def exact_symbol(payload, symbol):
    symbols = payload['data']['symbols']
    if not isinstance(symbols, list): raise UseCaseError('Expected a symbol list.')
    found = [s for s in symbols if s.get('symbol') == symbol]
    if len(found) != 1: raise UseCaseError('Expected one exact symbol in this source response.')
    return found[0]


def price_levels(payloads, symbol, metric, start, end):
    h, lev = payloads['atlas.getHistory'], payloads['heatseeker.getLevels']
    board = exact_symbol(lev, symbol); parse_time(board['asOf'])
    if lev['meta']['metric'] != metric: raise UseCaseError('Missing supported level metric.')
    lines = ['# Price + source levels', '', 'Question: where were the returned prices relative to the separately timestamped source levels?', '']
    if h.get('s') == 'no_data': lines += ['**No price observations returned.** Chart context remains missing.', '']
    elif h.get('s') == 'ok':
        columns = [h[k] for k in ('t', 'o', 'h', 'l', 'c', 'v')]
        if any(not isinstance(c, list) for c in columns) or len({len(c) for c in columns}) != 1 or any(not finite(v) for c in columns for v in c): raise UseCaseError('Invalid OHLCV columns.')
        if h['t'] != sorted(set(h['t'])): raise UseCaseError('Duplicate or unordered bar timestamps.')
        if any(not parse_time(start).timestamp() <= t < parse_time(end).timestamp() for t in h['t']): raise UseCaseError('Bar outside requested window.')
        if any(len(c) > 10000 for c in columns): raise UseCaseError('Too many bars for this bounded report.')
        rows = [(datetime.fromtimestamp(t, timezone.utc).isoformat(), fmt(o), fmt(hi), fmt(lo), fmt(c), fmt(v)) for t,o,hi,lo,c,v in list(zip(*columns))[:200]]
        lines += [f"Showing {len(rows)} of {len(h['t'])} returned bars. Atlas does not echo its symbol; for saved JSON, symbol identity depends on your explicit input provenance.", '', table(['Bar UTC', 'Open', 'High', 'Low', 'Close', 'Volume'], rows), '']
        if h['c'] and not finite(h['c'][-1] - h['c'][0]): raise UseCaseError('Price change exceeds finite arithmetic range.')
        if h['c']: lines += [f"Returned close range: {fmt(min(h['c']))}–{fmt(max(h['c']))}. First-to-last close change: {fmt(h['c'][-1] - h['c'][0])}.", '']
        else: lines += ['No bars returned.', '']
    else: raise UseCaseError('Price source did not return bars or no_data.')
    if not finite(board.get('spot')): raise UseCaseError('Invalid source spot.')
    rows = []
    for level in board['levels'][:200]:
        if not all(finite(level[k]) for k in ('strike', 'value', 'distancePct')): raise UseCaseError('Invalid level values.')
        rows.append((fmt(level['strike']), fmt(level['value']), level['nodeType'], fmt(level['distancePct'])))
    lines += [f"Levels asOf: {cell(board['asOf'])}; metric: {cell(lev['meta']['metric'])}; spot: {cell(board.get('spot', 'missing'))}. Showing {len(rows)} of {len(board['levels'])} returned levels.", '', table(['Strike', 'Signed exposure', 'Source classification', 'Distance % (source)'], rows), '',
        f"Source metadata: {source_metadata(lev['meta'])}", '',
        'Coverage: returned levels only; an omitted strike is not zero. The levels endpoint does not return the actual expiry set: requested coverage is in the plan, actual expiry coverage is unverified. Historical bars and current levels are separate observations; this is not a simultaneous replay or an alignment verdict.', '',
        '[Charts First: Market Structure Before Exposure](https://www.skylit.ai/learn/charts-first) motivates beginning with dated prices and a question. [Reading Heatseeker Maps: King Nodes, Gatekeepers, Floors, and Ceilings](https://www.skylit.ai/learn/reading-heatseeker) supplies context for the source labels. No trade recommendation is produced.']
    return '\n'.join(lines)


def flow_investigator(payloads, symbol, metric, start, end):
    feed, rollup = payloads['flowseeker.getFlow'], payloads['flowseeker.getFlowStrikes']
    f, r = feed['data'], rollup['data']
    if f['ticker'] != symbol or r['ticker'] != symbol: raise UseCaseError('Flow symbol mismatch.')
    for time in (feed['meta']['timestamp'], rollup['meta']['timestamp'], r['startTime'], r['endTime']): parse_time(time)
    rows = []
    if parse_time(r['startTime']) != parse_time(start) or parse_time(r['endTime']) != parse_time(end): raise UseCaseError('Flow rollup coverage differs from requested window.')
    for t in f['trades'][:200]:
        if not parse_time(start) <= parse_time(t['timestamp']) <= parse_time(end): raise UseCaseError('Trade outside requested window.')
        if not all(finite(t[k]) for k in ('strike', 'premium')): raise UseCaseError('Invalid trade values.')
        score = t.get('scores', {}).get('flowScore')
        if score is not None and not finite(score): raise UseCaseError('Invalid source score.')
        rows.append((t['timestamp'], t['optionType'], fmt(t['strike']), t['expiration'], fmt(t['premium']), fmt(score)))
    strikes = []
    for s in r['byStrike'][:200]:
        if not all(finite(s[k]) for k in ('strike', 'totalPremium', 'netPremium')): raise UseCaseError('Invalid strike rollup.')
        strikes.append((fmt(s['strike']), s['right'], s['dominantExpiration'], fmt(s['totalPremium']), fmt(s['netPremium'])))
    return '\n'.join(['# Flow investigator', '', 'Question: which strikes appear in the trade sample and in the separately returned window rollup?', '',
        f"Trade response generated: {cell(feed['meta']['timestamp'])}; showing {len(rows)} of {len(f['trades'])} returned trades. Source tradeCount: {cell(f.get('tradeCount', 'missing'))}.", '',
        table(['Trade UTC', 'Type', 'Strike', 'Expiration', 'Premium USD', 'Flow Score (source)'], rows), '',
        f"Rollup window: {cell(r['startTime'])} → {cell(r['endTime'])}; generated: {cell(rollup['meta']['timestamp'])}.", '',
        f"Showing {len(strikes)} of {len(r['byStrike'])} returned strike rollups.", '', table(['Strike', 'Right', 'Dominant expiry', 'Total premium USD', 'Net premium USD (source)'], strikes), '',
        'Coverage: trade list is a limited sample; strike rollup is top-N within its stated window. Empty lists mean no returned observations. Do not substitute the sample sum for the whole-window total. Flow Score is a service output, not a probability; call/put type and premium alone do not establish intent. Scores are displayed without recalculation.', '',
        'Missing evidence: opening/closing intent and a separately dated price chart. Cross-source agreement remains unverified.'])


def leaves(value, prefix='', depth=0):
    if depth > 8: raise UseCaseError('Volatility module nesting exceeds report limit.')
    if isinstance(value, dict):
        for key, child in value.items(): yield from leaves(child, prefix + ('.' if prefix else '') + str(key), depth+1)
    elif isinstance(value, list):
        for i, child in enumerate(value): yield from leaves(child, f'{prefix}[{i}]', depth+1)
    else:
        if isinstance(value, (float, int)) and not isinstance(value, bool) and not finite(value): raise UseCaseError('Nonfinite module value.')
        yield prefix, 'missing' if value is None else value


def volatility_context(payloads, symbol, metric, start, end):
    lines = ['# Volatility context', '', 'Question: what IV and cone data did the service return, and are their timestamps and coverage comparable?', '']
    for endpoint, module in [('heatseeker.getVolIv', 'iv'), ('heatseeker.getVolCones', 'cones')]:
        p = payloads[endpoint]; meta = p['meta']; missing = p['data']['missing']
        found = [s for s in p['data']['symbols'] if s.get('symbol') == symbol]
        lines += [f'## {module.upper()}', '']
        if not found:
            lines += ['No symbol observation returned. Coverage reasons: ' + cell(missing), '']; continue
        if len(found) != 1: raise UseCaseError('Duplicate volatility symbol.')
        s = found[0]; parse_time(s['asOf'])
        if type(s['stale']) is not bool or type(meta['frozen']) is not bool: raise UseCaseError('Invalid volatility freshness fields.')
        lines += [f"Source asOf: {cell(s['asOf'])}; session: {cell(s['sessionDate'])}; stale: {s['stale']}; frozen: {meta['frozen']}; market state: {cell(meta['marketState'])}.", '']
        if s.get(module) is None: lines += ['Module missing; no values inferred.', '']
        else:
            rows = list(leaves(s[module]))
            if len(rows) > 500: raise UseCaseError('Volatility module has too many fields for this report.')
            lines += [table(['Source field', 'Source value'], rows), '']
    lines += ['The public schema leaves module interiors open-ended, and endpoint descriptions document the fields shown here. Field names and units are preserved, not guessed; consult the public service documentation before numeric comparisons. IV fields svx1d/svx9/svx30/svx3m/svx6m use annualized volatility points, as documented publicly. Cones horizons[] are priced from current spot; levels[] carry a past-close anchor. Preserve this distinction and the supplied priced_at/until timestamps. Null optional fields remain missing, never zero. No volatility metric or proprietary cone calculation is reconstructed. Technical source: [public API IV/cones descriptions](https://api.skylit.ai/v1/openapi.json).', '',
        'Coverage and timing must be reviewed before comparing these separate responses. Stale/frozen flags remain visible; they do not by themselves certify current comparability.']
    return '\n'.join(lines)


def render_recipe(name, payloads, symbol, metric, start, end, synthetic=False):
    try:
        body = {'price-levels': price_levels, 'flow-investigator': flow_investigator, 'volatility-context': volatility_context}[name](payloads, symbol, metric, start, end)
        notices = [safe_metadata(endpoint) + ' — ' + notice_line(payload) for endpoint, payload in payloads.items() if notice_line(payload)]
        return body + '\n\n' + credit(synthetic) + '\n\n' + '\n'.join(notices)
    except (KeyError, TypeError, AttributeError, OverflowError, OSError): raise UseCaseError('Saved/source responses do not match this recipe schema.') from None
