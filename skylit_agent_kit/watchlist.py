"""Bounded REST watchlist using public OpenAPI fields, never local scoring models."""
import json
import math
import re
import time
from datetime import date, datetime, timezone
from http.client import HTTPException
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, build_opener

from .account import NoRedirect, reject_constant

BASE = 'https://api.skylit.ai'
DEFAULT_SYMBOLS = 'SPXW,SPY,QQQ,TSLA,MSFT,AAPL,AMZN,META'
METRICS = ('gamma', 'vanna')
SYMBOL = re.compile(r'[A-Z][A-Z0-9.-]{0,11}')


class WatchlistError(ValueError):
    def __init__(self, message, status=None):
        super().__init__(message)
        self.status = status


class Client:
    """Sequential, fixed-host, no-redirect transport with conservative attempt accounting."""
    def __init__(self, api_key, max_requests=12, max_credits=10, max_seconds=120):
        if not isinstance(api_key, str) or not re.fullmatch(r'[!-~]{1,4096}', api_key):
            raise WatchlistError('Provide your API key through the secure prompt or SKYLIT_API_KEY environment variable.')
        if type(max_requests) is not int or max_requests < 0 or type(max_credits) is not int or max_credits < 0 or not number(max_seconds) or not 0 < max_seconds <= 3600:
            raise WatchlistError('Invalid request, credit or elapsed-time budget.')
        self._key = api_key
        self.max_requests, self.max_credits = max_requests, max_credits
        self.deadline = time.monotonic() + max_seconds
        self.requests = self.credits = 0
        self.rate_remaining = None

    def get(self, path, params=None, cost=0):
        allowed = path in ('/v1/account', '/v1/symbols', '/v1/heatmap') or re.fullmatch(r'/v1/flow/[A-Z][A-Z0-9.-]{0,11}', path)
        expected_cost = 0 if path in ('/v1/account', '/v1/symbols') else 1
        if not allowed or cost != expected_cost:
            raise WatchlistError('Request destination or documented cost is not allowed.')
        if self.requests + 1 > self.max_requests or self.credits + cost > self.max_credits:
            raise WatchlistError('Request/credit budget reached; no further request sent.')
        if self.rate_remaining is not None and self.rate_remaining <= 0:
            raise WatchlistError('Server rate allowance exhausted; try manually later.')
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            raise WatchlistError('Elapsed-time budget reached; no further request sent.')
        url = BASE + path + ('?' + urlencode(params) if params else '')
        request = Request(url, headers={'Authorization': 'Bearer ' + self._key,
            'Accept': 'application/json', 'User-Agent': 'skylit-agent-kit/0.1-dev'}, method='GET')
        self.requests += 1
        self.credits += cost  # Reserve documented cost even when the outcome is unknown.
        if self.rate_remaining is not None: self.rate_remaining -= 1
        try:
            with build_opener(NoRedirect()).open(request, timeout=min(10, remaining)) as response:
                headers = getattr(response, 'headers', {})
                allowance = headers.get('X-RateLimit-Remaining')
                if allowance is not None:
                    try: self.rate_remaining = max(0, int(allowance))
                    except (ValueError, TypeError):
                        raise WatchlistError('Server rate allowance could not be verified.') from None
                chunks, size = [], 0
                while True:
                    if time.monotonic() >= self.deadline:
                        raise WatchlistError('Elapsed-time budget reached while reading response.')
                    chunk = response.read1(min(65536, 1048577 - size))
                    if not chunk: break
                    size += len(chunk)
                    if size > 1048576: raise WatchlistError('Response exceeded 1 MiB.')
                    chunks.append(chunk)
                body = b''.join(chunks)
        except HTTPError as error:
            error.close()
            messages = {401: 'Check your key.', 402: 'Check credits.', 403: 'Check account access.',
                        404: 'No data or unsupported symbol.', 429: 'Rate limited; try manually later.',
                        503: 'Service unavailable; try manually later.'}
            raise WatchlistError(f'HTTP {error.code}: {messages.get(error.code, "Request stopped.")} No retry sent.', error.code) from None
        except (URLError, OSError, HTTPException):
            raise WatchlistError('Connection failed; no retry sent. Check connectivity and TLS.') from None
        try:
            payload = json.loads(body, parse_constant=reject_constant)
            # A response must never cause an echoed credential to reach reports or saved JSON.
            payload = redact(payload, self._key)
        except (ValueError, UnicodeError, RecursionError):
            raise WatchlistError('Service returned invalid JSON.') from None
        if not isinstance(payload, dict): raise WatchlistError('Service returned an unexpected response shape.')
        return payload


def redact(value, key):
    if isinstance(value, str): return value.replace(key, '[REDACTED]')
    if isinstance(value, list): return [redact(item, key) for item in value]
    if isinstance(value, dict): return {redact(k, key): redact(v, key) for k, v in value.items()}
    return value


def symbols_list(symbols):
    items = symbols.split(',') if isinstance(symbols, str) else symbols
    result = list(dict.fromkeys(item.strip().upper() for item in items))
    if not result or any(not SYMBOL.fullmatch(item) for item in result):
        raise WatchlistError('Use comma-separated ticker symbols such as SPXW,SPY,QQQ.')
    if len(result) > 100: raise WatchlistError('At most 100 unique symbols per run.')
    return result


def make_plan(symbols=DEFAULT_SYMBOLS, batch_size=10, catalog=None):
    symbols = symbols_list(symbols)
    if type(batch_size) is not int or not 1 <= batch_size <= 10:
        raise WatchlistError('Heatmap batch size must be 1–10.')
    calls = []
    for metric in METRICS:
        available = [s for s in symbols if catalog is None or metric in catalog.get(s, ())]
        for start in range(0, len(available), batch_size):
            calls.append({'kind': metric, 'symbols': available[start:start + batch_size]})
    calls.extend({'kind': 'flow', 'symbols': [s]} for s in symbols)
    return {'symbols': symbols, 'calls': calls, 'credits': len(calls), 'requests': len(calls) + 2,
            'batch_size': batch_size}


def number(value):
    try: return type(value) in (int, float) and math.isfinite(value)
    except OverflowError: return False


def stamp(value):
    if not isinstance(value, str): return None
    try:
        parsed = datetime.fromisoformat(value)
        return parsed.isoformat() if parsed.tzinfo else None
    except ValueError: return None


def valid_date(value):
    try: return isinstance(value, str) and date.fromisoformat(value).isoformat() == value
    except ValueError: return False


def missing(reason):
    return {'status': reason}


def parse_heatmap(payload, requested, metric):
    data, meta = payload.get('data'), payload.get('meta')
    if not isinstance(data, dict) or not isinstance(data.get('symbols'), list) or not isinstance(meta, dict) or meta.get('metric') != metric:
        raise WatchlistError('Heatmap response has invalid shape or wrong metric.')
    result = {s: missing('missing from heatmap response') for s in requested}
    seen = set()
    for row in data['symbols']:
        if not isinstance(row, dict) or not isinstance(row.get('symbol'), str) or row['symbol'] not in result: continue
        symbol = row['symbol']
        if symbol in seen:
            result[symbol] = missing('invalid duplicate symbol in response'); continue
        seen.add(symbol)
        if not stamp(row.get('asOf')) or not number(row.get('spot')) or not isinstance(row.get('strikes'), list) or not isinstance(row.get('expirations'), list) or not all(valid_date(e) for e in row['expirations']):
            result[symbol] = missing('invalid or missing heatmap fields'); continue
        strikes, invalid = [], 0
        for node in row['strikes']:
            if not isinstance(node, dict) or not number(node.get('strike')) or not number(node.get('value')) or node.get('nodeType') not in ('king', 'gatekeeper', 'pika', 'barney', 'significant', 'normal'):
                invalid += 1; continue
            strikes.append({k: node[k] for k in ('strike', 'value', 'nodeType')})
        result[symbol] = {'status': f'partial: {invalid} invalid strikes' if invalid else ('available' if strikes else 'no strikes returned'),
            'as_of': stamp(row['asOf']), 'spot': row['spot'], 'expirations': row['expirations'], 'strikes': strikes}
    return result


def parse_flow(payload, symbol):
    data, meta = payload.get('data'), payload.get('meta')
    if not isinstance(data, dict) or data.get('ticker') != symbol or data.get('timeframe') != '1d' or not isinstance(data.get('trades'), list) or not isinstance(meta, dict):
        raise WatchlistError('Flow response has invalid shape or mismatched ticker.')
    trades, invalid = [], 0
    for row in data['trades']:
        if not isinstance(row, dict): invalid += 1; continue
        scores = row.get('scores')
        if not stamp(row.get('timestamp')) or row.get('optionType') not in ('CALL', 'PUT') or not valid_date(row.get('expiration')) or not all(number(row.get(k)) for k in ('strike', 'premium', 'contracts')):
            invalid += 1; continue
        trades.append({'timestamp': stamp(row['timestamp']), **{k: row[k] for k in ('optionType', 'strike', 'expiration', 'premium', 'contracts')},
                       'flowScore': scores.get('flowScore') if isinstance(scores, dict) and number(scores.get('flowScore')) else None,
                       'flowBonus': scores.get('flowBonus') if isinstance(scores, dict) and number(scores.get('flowBonus')) else None})
    trades.sort(key=lambda t: datetime.fromisoformat(t['timestamp']), reverse=True)
    aggregate = data.get('aggregate')
    return {'status': f'partial: {invalid} invalid trades' if invalid else ('available' if trades else 'no trades returned in requested window'),
        'generated_at': stamp(meta.get('timestamp')), 'latest_trade': trades[0]['timestamp'] if trades else None,
        'trades': trades, 'timeframe': data.get('timeframe') if data.get('timeframe') == '1d' else None,
        'aggregate': {k: aggregate.get(k) if isinstance(aggregate, dict) and number(aggregate.get(k)) else None for k in ('vwf', 'sdf', 'fir')},
        **{k: data.get(k) if number(data.get(k)) else None for k in ('tradeCount', 'sweepCount', 'totalPremium')}}


def run_watchlist(client, symbols=DEFAULT_SYMBOLS, max_credits=10, max_requests=12,
                  batch_size=10, flow_limit=10, trading_date=None, save_raw=False):
    symbols = symbols_list(symbols)
    make_plan(symbols, batch_size)  # Validate before any account request.
    if type(max_requests) is not int or max_requests < 2 or type(max_credits) is not int or max_credits < 0:
        raise WatchlistError('Use nonnegative credits and at least 2 requests for discovery.')
    if type(flow_limit) is not int or not 1 <= flow_limit <= 500: raise WatchlistError('Flow limit must be 1–500.')
    if trading_date is not None and not valid_date(trading_date): raise WatchlistError('Use --date YYYY-MM-DD.')
    result = {'symbols': symbols, 'retrieved_at': datetime.now(timezone.utc).isoformat(),
        'rows': {s: {k: missing('not requested: run stopped before this component') for k in (*METRICS, 'flow')} for s in symbols},
        'stop': 'completed', 'sources': [], 'raw': [], 'flow_limit': flow_limit, 'date': trading_date}
    try:
        account = client.get('/v1/account').get('data')
        if not isinstance(account, dict) or account.get('status') != 'active' or account.get('apiEligible') is not True:
            raise WatchlistError('Account access is unavailable or could not be verified; no paid requests sent.')
        limit = account.get('limits', {}).get('symbolsPerHeatmapCall') if isinstance(account.get('limits'), dict) else None
        balance = account.get('creditsBalance')
        rpm = account.get('limits', {}).get('requestsPerMinute') if isinstance(account.get('limits'), dict) else None
        if type(limit) is not int or limit < 1 or type(rpm) is not int or rpm < 1 or (account.get('unlimited') is not True and (type(balance) is not int or balance < 0)):
            raise WatchlistError('Account limits or credit balance could not be verified; no paid requests sent.')
        if max_requests < 2 or rpm < 2:
            raise WatchlistError('Request or account rate budget cannot cover discovery; no paid requests sent.')
        catalog_payload = client.get('/v1/symbols').get('data')
        if not isinstance(catalog_payload, dict) or not isinstance(catalog_payload.get('symbols'), list):
            raise WatchlistError('Symbol catalog could not be verified; no paid requests sent.')
        catalog = {}
        for item in catalog_payload['symbols']:
            if not isinstance(item, dict) or not isinstance(item.get('symbol'), str) or not isinstance(item.get('metrics'), list):
                raise WatchlistError('Symbol catalog contains invalid entries; no paid requests sent.')
            catalog[item['symbol']] = [m for m in item['metrics'] if m in METRICS]
        plan = make_plan(symbols, min(batch_size, limit, 10), catalog)
        result['plan'] = plan
        for symbol in symbols:
            for metric in METRICS:
                if metric not in catalog.get(symbol, ()):
                    result['rows'][symbol][metric] = missing('unsupported by discovered heatmap catalog; no substitution')
        if plan['credits'] > max_credits or plan['requests'] > min(max_requests, rpm):
            raise WatchlistError(f'Plan exceeds budget: requires {plan["requests"]} requests and {plan["credits"]} documented credits; no paid requests sent.')
        allowance = getattr(client, 'rate_remaining', None)
        if allowance is not None and plan['credits'] > allowance:
            raise WatchlistError('Server rate allowance is below the complete plan; no paid requests sent. Try manually later.')
        if account.get('unlimited') is not True and plan['credits'] > balance:
            raise WatchlistError('Account credit balance is below the complete plan; no paid requests sent.')
        for call in plan['calls']:
            kind, batch = call['kind'], call['symbols']
            if kind == 'flow':
                path, params = '/v1/flow/' + batch[0], {'timeframe': '1d', 'limit': flow_limit}
                if trading_date: params['date'] = trading_date
            else:
                path, params = '/v1/heatmap', {'symbols': ','.join(batch), 'metric': kind, 'maxStrikes': 92, 'maxExpirations': 5}
            source = BASE + path + '?' + urlencode(params)
            result['sources'].append(source)
            try:
                for symbol in batch: result['rows'][symbol][kind] = missing('request in progress; result unavailable')
                payload = client.get(path, params, cost=1)
                if save_raw: result['raw'].append({'url': source, 'response': payload})
                if kind == 'flow': result['rows'][batch[0]][kind] = parse_flow(payload, batch[0])
                else:
                    for symbol, parsed in parse_heatmap(payload, batch, kind).items(): result['rows'][symbol][kind] = parsed
            except WatchlistError as error:
                for symbol in batch: result['rows'][symbol][kind] = missing(str(error))
                if error.status != 404: raise
    except WatchlistError as error:
        result['stop'] = str(error)
    result['requests'], result['credits_reserved'] = client.requests, client.credits
    return result


def execute_live(api_key, **options):
    """One bounded sequential run; socket and between-read deadline checks."""
    seconds = options.pop('max_seconds', 120)
    limits = {k: options[k] for k in ('max_requests', 'max_credits') if k in options}
    return run_watchlist(Client(api_key, max_seconds=seconds, **limits), **options)


def fmt(value):
    return f'{value:,.6g}' if number(value) else 'unavailable'


def board_summary(board):
    if not board.get('strikes'): return board['status']
    kings = [node for node in board['strikes'] if node['nodeType'] == 'king']
    node = kings[0] if kings else max(board['strikes'], key=lambda n: abs(n['value']))
    label = 'source king' if kings else 'largest returned magnitude'
    return f"{label}: {fmt(node['strike'])} / {fmt(node['value'])} ({board['status']})"


def flow_summary(flow):
    if 'trades' not in flow: return flow['status']
    return f"{fmt(flow['tradeCount'])} trades; ${fmt(flow['totalPremium'])}; {flow['status']}"


def render_report(result):
    lines = ['# Skylit watchlist · GEX / VEX / recent flow', '',
        f'Retrieval started: {result["retrieved_at"]}', f'Stopping reason: {result["stop"]}', '',
        'Source values from REST (display rounded to six significant digits); no local proprietary calculations or trade recommendation.',
        'GEX = requested gamma; VEX = requested vanna. Each board covers up to 92 strikes and the nearest 5 expirations, not the whole chain.',
        f'Flow window: 1d; date: {result["date"] or "service-selected trading date (may be last session)"}; at most {result["flow_limit"]} recent trades per symbol.',
        'Separate requests are not an atomic snapshot. Compare the board and trade timestamps before use; no freshness guarantee.', '',
        '| Symbol | GEX strike / source value | VEX strike / source value | Flow window |', '|---|---|---|---|']
    for symbol in result['symbols']:
        row = result['rows'][symbol]
        lines.append('| ' + ' | '.join([symbol] + [board_summary(row['gamma']), board_summary(row['vanna']), flow_summary(row['flow'])]) + ' |')
    for symbol in result['symbols']:
        row = result['rows'][symbol]
        lines.extend(['', f'## {symbol}', ''])
        for metric, label in [('gamma', 'GEX'), ('vanna', 'VEX')]:
            board = row[metric]
            lines.extend([f'### {label} · {metric}', '', board['status']])
            if 'strikes' not in board: continue
            lines.extend([f'Board as of: {board["as_of"]}; latest spot: {fmt(board["spot"])}.',
                'Returned expirations: ' + (', '.join(board['expirations']) or 'none'),
                f'Display: up to 3 largest returned strike magnitudes of {len(board["strikes"])} valid nodes; values copied from source.', '',
                '| Strike | Source net exposure | Source node type |', '|---:|---:|---|'])
            lines.extend(f'| {fmt(n["strike"])} | {fmt(n["value"])} | {n["nodeType"]} |' for n in sorted(board['strikes'], key=lambda n: abs(n['value']), reverse=True)[:3])
        flow = row['flow']
        lines.extend(['', '### Recent options flow', '', flow['status']])
        if 'trades' not in flow: continue
        lines.extend([f'Response generated: {flow["generated_at"] or "unavailable"}; latest returned trade: {flow["latest_trade"] or "unavailable"}.',
            f'Source trade count: {fmt(flow["tradeCount"])}; source sweep count: {fmt(flow["sweepCount"])}; source total premium USD: {fmt(flow["totalPremium"])}.',
            'Source aggregate scores: ' + '; '.join(f'{k.upper()} {fmt(v)}' for k, v in flow['aggregate'].items()),
            f'Display: latest {min(3, len(flow["trades"]))} of {len(flow["trades"])} valid returned trades (window counts are source totals).', '',
            '| Trade time | Type | Strike | Expiration | Contracts | Premium USD | Flow Score | FlowBonus |',
            '|---|---|---:|---|---:|---:|---:|---:|'])
        for trade in flow['trades'][:3]:
            lines.append('| ' + ' | '.join([trade['timestamp'], trade['optionType'], fmt(trade['strike']), trade['expiration'], fmt(trade['contracts']), fmt(trade['premium']), fmt(trade['flowScore']), fmt(trade['flowBonus'])]) + ' |')
    lines.extend(['', '## Sources and usage', '', '[Public heatmap contract](https://www.skylit.ai/docs/openapi.yaml) · [Public flow contract](https://www.skylit.ai/docs/flowseeker-openapi.yaml)', ''])
    lines.extend(f'- [{url}]({url})' for url in result['sources'])
    lines.extend(['', f'{result["requests"]} requests attempted; {result["credits_reserved"]} documented credits reserved for attempts; no retries or model calls.',
        'Reserved credits are a conservative estimate, not verified billing or a transactional cap on shared-account spending.', ''])
    return '\n'.join(lines)
