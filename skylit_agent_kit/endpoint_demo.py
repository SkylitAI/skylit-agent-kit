"""Plan and execute reviewed public GET operations with explicit local limits."""
import json
import math
import re
import time
from datetime import date, datetime, timezone
from http.client import HTTPException
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, build_opener

from . import catalog
from .account import NoRedirect, reject_constant
from .contract_schema import valid
from .watchlist import number, redact

HOSTS = {'heatseeker': 'https://api.skylit.ai', 'flowseeker': 'https://api.skylit.ai', 'atlas': 'https://atlas-api.skylit.ai'}
MAX_BYTES = 1048576
TICKER = re.compile(r'[A-Z^][A-Z0-9.^:-]{0,31}')
OPRA = re.compile(r'[A-Z][A-Z0-9.]{0,11}__[0-9]{6}[CP][0-9]{8}')


class EndpointError(ValueError):
    """Sanitized user-facing planning or transport error."""


def _typed(value, schema):
    if 'oneOf' in schema:
        for branch in schema['oneOf']:
            try: return _typed(value, branch)
            except EndpointError: pass
        raise EndpointError('Value does not match an allowed parameter type.')
    kind = schema.get('type', 'string')
    try:
        if kind == 'integer' and isinstance(value, str) and re.fullmatch(r'-?\d+', value): value = int(value)
        elif kind == 'number' and isinstance(value, str): value = float(value)
        elif kind == 'boolean' and isinstance(value, str):
            if value not in ('true', 'false'): raise ValueError
            value = value == 'true'
    except (ValueError, OverflowError): raise EndpointError('Invalid numeric or boolean parameter.') from None
    if not valid(value, schema, {}): raise EndpointError('Parameter does not match its public type, enum, format or bounds.')
    if isinstance(value, str) and (len(value) > 4096 or any(ord(c) < 32 or ord(c) == 127 for c in value)):
        raise EndpointError('Parameter text contains control characters or exceeds 4096 characters.')
    return value


def _instant(value):
    try:
        if type(value) in (int, float) or (isinstance(value, str) and re.fullmatch(r'\d+(?:\.\d+)?', value)):
            parsed = datetime.fromtimestamp(float(value), timezone.utc)
        elif isinstance(value, str) and re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
            parsed = datetime.combine(date.fromisoformat(value), datetime.min.time(), timezone.utc)
        else:
            if not isinstance(value,str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})',value): raise ValueError
            parsed = datetime.fromisoformat(value)
            if parsed.tzinfo is None: raise ValueError
        return parsed
    except (ValueError, TypeError, OverflowError, OSError):
        raise EndpointError('Use a valid date, timezone-qualified timestamp or Unix seconds.') from None


def _days(value):
    match = re.fullmatch(r'([1-9]\d*)([DdWwHh])', str(value))
    if not match: raise EndpointError('Use an explicit interval such as 1D, 7D or 1W.')
    return int(match[1]) * {'d':1, 'w':7, 'h':1/24}[match[2].lower()]


def _cross_fields(entry, values):
    service, op = entry['service'], entry['operation_id']
    for name, value in list(values.items()):
        if name in ('ticker', 'tickers', 'exclude_tickers', 'sector') or (name in ('symbols','symbol') and not (service == 'flowseeker')):
            items = value.split(',')
            cap = 50 if service == 'flowseeker' or op == 'getDailyStats' else (5 if op == 'getHistoricalRange' else 10)
            if not items or len(items) > cap or any(not TICKER.fullmatch(item) for item in items):
                raise EndpointError(f'{name} requires valid uppercase symbols (maximum {cap}).')
            values[name] = ','.join(dict.fromkeys(items))
        if service == 'flowseeker' and name in ('symbols','symbol'):
            if len(value.split(',')) > 50 or any(not OPRA.fullmatch(item) for item in value.split(',')):
                raise EndpointError('Use explicit URL-safe OPRA contract symbols obtained from actual data.')
            for item in value.split(','):
                try: date.fromisoformat('20'+item.split('__')[1][:2]+'-'+item.split('__')[1][2:4]+'-'+item.split('__')[1][4:6])
                except ValueError: raise EndpointError('OPRA contract expiration is invalid.') from None
        if name == 'trade_id' and not re.fullmatch(r'[A-Za-z0-9_-]{1,160}', value):
            raise EndpointError('trade_id must be an explicit identifier without URL separators.')
        if name == 'strike' and (not re.fullmatch(r'\d+(?:\.\d+)?', value) or float(value) <= 0):
            raise EndpointError('strike must be a positive decimal price.')
        if name in ('time_start','time_end','start_time_of_day','end_time_of_day'):
            if not re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d', value): raise EndpointError('Use HH:MM for time-of-day parameters.')
        if name in ('expirations',):
            dates = value.split(',')
            if len(dates) > 60 or any(not valid(item, {'type':'string','format':'date'}, {}) for item in dates):
                raise EndpointError('expirations must contain at most 60 comma-separated ISO dates.')
        if name in ('start_time','end_time','start','end','as_of'): _instant(value)
        if name.startswith('min_') and 'max_'+name[4:] in values and value > values['max_'+name[4:]]:
            raise EndpointError('Minimum filters must not exceed their matching maximum.')
    for low, high in (('from','to'),('start_time','end_time'),('start','end'),('start_date','end_date'),('date_start','date_end')):
        if low in values and high in values:
            first, last = _instant(values[low]), _instant(values[high])
            if first > last: raise EndpointError('Range start must not be after range end.')
            days = (last-first).total_seconds()/86400
            if service == 'flowseeker' and days > 30:
                raise EndpointError('This demo limits explicit Flowseeker windows to 30 elapsed days (31 inclusive dates).')
    for low, high in (('time_start','time_end'),('start_time_of_day','end_time_of_day')):
        if low in values and high in values and values[low] > values[high]: raise EndpointError('Time-of-day start must not be after end.')
    if op == 'getDarkPoolTrades':
        if ('date_start' in values) != ('date_end' in values): raise EndpointError('Provide both date_start and date_end.')
        if 'date' in values and 'date_start' in values: raise EndpointError('Choose date or a paired date range, not both.')
    if op in ('getUnderlyingTrades','getContractTrades') and (('start' in values) != ('end' in values)):
        raise EndpointError('This demo requires both start and end for explicit trade windows.')
    if values.get('only_multi_leg') is True and values.get('exclude_multi_leg') is True:
        raise EndpointError('only_multi_leg conflicts with exclude_multi_leg.')
    if service == 'atlas' and op == 'getHistory':
        if 'countback' in values: raise EndpointError('countback overrides the explicit window; this bounded demo requires from/to instead.')
        if values['from'] >= values['to']: raise EndpointError('Atlas history requires from < to (exclusive upper bound).')
        cap = 90 if values['resolution'] in ('1','2','3','5','15','30') else (720 if values['resolution'] in ('60','240','480') else 2600)
        # Calendar days are a conservative subset of the published trading-day limit.
        if (values['to']-values['from'])/86400 > cap: raise EndpointError('Atlas demo calendar-day window exceeds the conservative tier limit.')
    if op == 'getHistoricalRange' and (_instant(values['to'])-_instant(values['from'])).total_seconds() > 900:
        raise EndpointError('Historical range is limited to 15 minutes.')
    if op == 'getDailyStats':
        if 'to' not in values: raise EndpointError('This bounded daily-statistics demo requires an explicit to date.')
        days = (_instant(values['to'])-_instant(values['from'])).days+1
        if days > 31 or days * len(values['symbols'].split(',')) > 400: raise EndpointError('Daily statistics allow 31 dates and 400 symbol-days per request.')
        if values['from'] < '2023-03-28': raise EndpointError('Daily statistics history starts at 2023-03-28.')
    if entry['stream']:
        if op == 'streamHeatmap':
            if bool(values.get('symbol')) == bool(values.get('symbols')): raise EndpointError('Choose exactly one of symbol or symbols for the stream.')
            if values.get('format') not in (None,'v2') or 'symbol' in values:
                raise EndpointError('The bounded heatmap demo supports v2 only: use symbols=... and format=v2.')
            values['format'] = 'v2'
        if values.get('modules'):
            if any(item not in ('iv','term','cones','sigma','surface','tilt','events') for item in values['modules'].split(',')):
                raise EndpointError('Unknown Tempest stream module.')
    if 'conviction_weights' in values:
        try:
            weights=json.loads(values['conviction_weights'], parse_constant=reject_constant)
            if not isinstance(weights,dict) or not weights or not all(number(v) and v>=0 for v in weights.values()) or not .95 <= sum(weights.values()) <= 1.05: raise ValueError
        except (ValueError, RecursionError): raise EndpointError('conviction_weights must be a finite nonnegative JSON object summing to 0.95–1.05.') from None


def _pricing(entry, values):
    cost=entry['credits']
    notes=[]
    if entry['live_blocked']: return None,[entry['live_blocked']]
    if not number(cost) or cost<0: return None,['No verified documented cost; live disabled.']
    if entry['stream']:
        symbols=len(values['symbols'].split(','))
        return 2*symbols,['Reserve opening plus one prepaid minute per symbol; Tempest reservation is conservative relative to fixed-price prose.']
    if entry['service']=='flowseeker':
        op=entry['operation_id']
        if op=='getAggregate':
            windows=values.get('timeframes','1d').split(',')
            atoms={'1h':1,'4h':1,'1d':1,'7d':7,'30d':30,'90d':90}
            if windows==['all']: days=130
            elif len(windows)>8 or any(w not in atoms for w in windows): raise EndpointError('timeframes accepts at most 8 documented atoms: 1h,4h,1d,7d,30d,90d, or all.')
            else: days=sum(atoms[w] for w in windows)
            cost=3*math.ceil(days/30)
            notes.append('Aggregate pricing reserves 3 credits per started 30 summed window days.')
        if op in ('getMarketTide','getUnderlyingChart','getContractChart'):
            days=_days(values.get('interval','1D'))
            cap=30 if values.get('bucket') not in ('1d','1w') else (360 if op=='getMarketTide' else 365)
            if days>cap: raise EndpointError('Interval exceeds the public bucket-dependent range cap.')
            if values.get('exclude_deep_itm'):
                if days>5: raise EndpointError('exclude_deep_itm is limited to 5 days.')
                cost=3*math.ceil(days)  # Calendar days conservatively bound billable trading days.
            else: cost=3*math.ceil(days/30)
            notes.append('Range-priced reservation computed from explicit interval; no pagination follows.')
        if op=='getTopContractsDaily' and values.get('ticker'): cost=1
        if op in ('getUnderlyingRvol','getContractRvol'):
            if _days(values.get('interval','1D'))>30 or _days(values.get('avg_period','14d'))>30:
                raise EndpointError('This demo limits relative-volume windows and baselines to 30 days.')
    return cost,notes


def plan_request(identity, params=None):
    try: entry=catalog.get_endpoint(identity)
    except ValueError as error: raise EndpointError(str(error)) from None
    if params is not None and not isinstance(params,dict): raise EndpointError('Parameters must be a name/value object.')
    params={} if params is None else params
    definitions={p['name']:p for p in entry['parameters']}
    if any(name not in definitions for name in params): raise EndpointError('Unknown parameter; inspect endpoint preview for allowed names.')
    values={}
    for name,param in definitions.items():
        schema=param['schema']
        if name in params: raw=params[name]
        elif 'default' in schema: raw=schema['default']
        elif param.get('required'): raise EndpointError(f'Required parameter missing: {name}. Supply it explicitly for live use.')
        else: continue
        if isinstance(raw,str) and ',' in raw and name in ('trade_type','moneyness') and 'comma' in param.get('description','').lower() and schema.get('enum'):
            if any(token not in schema['enum'] for token in raw.split(',')): raise EndpointError('Unknown token in enum list.')
            schema={k:v for k,v in schema.items() if k!='enum'}
        try: values[name]=_typed(raw,schema)
        except EndpointError as error: raise EndpointError(f'{name}: {error}') from None
    _cross_fields(entry,values)
    cost,notes=_pricing(entry,values)
    path=entry['transport_path']; query={}; headers={}
    for name,value in values.items():
        serialized=('true' if value else 'false') if type(value) is bool else str(value)
        location=definitions[name]['in']
        if location=='path':
            if not re.fullmatch(r'[A-Za-z0-9_.:-]+',serialized): raise EndpointError('Path parameters cannot contain URL separators.')
            path=path.replace('{'+name+'}',quote(serialized,safe=''))
        elif location=='query': query[name]=serialized
        elif location=='header' and name=='Last-Event-ID': headers[name]=serialized
        else: raise EndpointError('Unsupported parameter location.')
    if '{' in path: raise EndpointError('Unresolved route parameter.')
    host=HOSTS[entry['service']]
    if host!=entry['host'] or entry['method']!='GET': raise EndpointError('Public host/method requires renewed review.')
    stream={'max_events':10,'max_seconds':20,'max_bytes':MAX_BYTES,'opening_credits':len(values['symbols'].split(','))} if entry['stream'] else None
    return {'id':identity,'method':'GET','host':host,'url':host+path+('?' + urlencode(sorted(query.items())) if query else ''),
        'params':values,'headers':headers,'credits':cost,'credit_notes':notes,'stream':stream,
        'auth_required':entry['auth_required'],'live_blocked':entry['live_blocked']}


def preview(identity, params=None):
    entry=catalog.get_endpoint(identity)
    values={**entry['example_params'],**(params or {})}
    # Bounded examples occasionally require an explicit end even when the server defaults it.
    if entry['operation_id']=='getDailyStats': values.setdefault('to','2026-09-30')
    return {'synthetic':True,'notice':'FICTIONAL fixed schema illustration; the response is not recomputed for changed request parameters. No key, network or model used. Not financial evidence or live certification.',
        'purpose':entry['summary'],'request':plan_request(identity,values),'response':entry['example_response'],
        'schema_note':entry['schema_note'],'next_step':entry['next_step'],'source':entry['provenance']['source_url']}


class _Transport:
    def __init__(self, api_key, max_requests, max_seconds):
        if api_key is not None and (not isinstance(api_key,str) or not re.fullmatch(r'[!-~]{1,4096}',api_key)):
            raise EndpointError('Provide a valid key through the hidden terminal prompt or secure process environment.')
        self.key=api_key
        self.maximum=max_requests
        self.requests=0
        self.deadline=time.monotonic()+max_seconds
        self.rate_remaining=None
        self.credit_remaining=None
        self.unlimited=False

    def request(self, plan):
        remaining=self.deadline-time.monotonic()
        if remaining<=0: raise EndpointError('Elapsed request budget reached; no further request sent.')
        if self.requests>=self.maximum: raise EndpointError('Request budget reached.')
        if self.rate_remaining is not None and self.rate_remaining<=0: raise EndpointError('Server rate allowance exhausted; no retry sent.')
        headers={'Accept':catalog.get_endpoint(plan['id'])['content_type'], 'User-Agent':'skylit-agent-kit/0.1-dev', **plan['headers']}
        if plan['auth_required']:
            if not self.key: raise EndpointError('This endpoint requires an API key; use the hidden prompt or secure environment.')
            headers['Authorization']='Bearer '+self.key
        self.requests+=1
        if self.rate_remaining is not None: self.rate_remaining-=1
        request=Request(plan['url'],headers=headers,method='GET')
        try:
            with build_opener(NoRedirect()).open(request,timeout=min(10,remaining)) as response:
                for header, attr in (('X-RateLimit-Remaining','rate_remaining'),('X-Credits-Remaining','credit_remaining')):
                    raw=getattr(response,'headers',{}).get(header)
                    if raw is not None:
                        try:
                            value=int(raw)
                            if value<0: raise ValueError
                        except (ValueError,TypeError): raise EndpointError('Service returned an invalid remaining-limit header.') from None
                        setattr(self,attr,value)
                if plan['stream']:
                    return _read_stream(response,plan,min(self.deadline,time.monotonic()+plan['stream']['max_seconds']),self.key)
                body=_read_body(response,self.deadline)
        except HTTPError as error:
            error.close()
            raise EndpointError(f'Endpoint stopped (HTTP {error.code}); no retry sent. Check account access, credits, rate limits or service availability.') from None
        except (URLError,OSError,HTTPException):
            raise EndpointError('Connection failed or timed out; no retry sent. Check connectivity and TLS.') from None
        try:
            if catalog.get_endpoint(plan['id'])['content_type']=='text/plain':
                payload=body.decode('utf-8')
                if not re.fullmatch(r'[0-9]+',payload.strip()): raise ValueError
                payload=payload.strip()
            else: payload=json.loads(body,parse_constant=reject_constant,parse_float=_finite_float)
            return redact(payload,self.key) if self.key else payload
        except (ValueError,UnicodeError,RecursionError): raise EndpointError('Endpoint returned invalid response data.') from None


def _finite_float(value):
    parsed=float(value)
    if not math.isfinite(parsed): raise ValueError('Non-finite JSON number')
    return parsed


def _read_body(response,deadline):
    chunks=[]; size=0
    while True:
        if time.monotonic()>=deadline: raise EndpointError('Elapsed budget reached while reading response.')
        chunk=response.read1(min(65536,MAX_BYTES+1-size))
        if not chunk: return b''.join(chunks)
        size+=len(chunk)
        if size>MAX_BYTES: raise EndpointError('Response exceeded 1 MiB; stopped.')
        chunks.append(chunk)


def _read_stream(response,plan,deadline,key):
    """SSE subset: bounded bytes/events/time; protocol messages never trigger reconnect."""
    events=[]; buffer=b''; total=0; charged=plan['stream']['opening_credits']; stop='stream ended'
    def output(reason):
        value={'events':events,'stop':reason,'credits_reserved':plan['credits'],'observed_charged':charged}
        return redact(value,key) if key else value
    while len(events)<plan['stream']['max_events']:
        if time.monotonic()>=deadline: return output('stream time cap reached')
        try: chunk=response.read1(min(4096,plan['stream']['max_bytes']+1-total))
        except (TimeoutError, OSError): return output('stream idle/read timeout; connection closed without retry')
        if not chunk: return output(stop)
        total+=len(chunk)
        if total>plan['stream']['max_bytes']: raise EndpointError('Stream exceeded byte cap; connection closed.')
        buffer+=chunk
        # CRLF frames can split across reads; normalize only complete lines.
        while b'\n\n' in buffer.replace(b'\r\n',b'\n'):
            normalized=buffer.replace(b'\r\n',b'\n')
            frame,buffer=normalized.split(b'\n\n',1)
            event='message'; data=[]; event_id=None
            try:
                for line in frame.decode('utf-8').splitlines():
                    if line.startswith('event:'): event=line[6:].strip()
                    elif line.startswith('data:'): data.append(line[5:].lstrip())
                    elif line.startswith('id:'): event_id=line[3:].strip()
                if not data: continue  # Comment/keepalive; still counted in byte/time budget.
                payload=json.loads('\n'.join(data),parse_constant=reject_constant,parse_float=_finite_float)
            except (ValueError,UnicodeError,RecursionError): raise EndpointError('Stream returned invalid event data; connection closed.') from None
            item={'event':event,'data':payload}
            if event_id is not None: item['id']=event_id
            events.append(item)
            if event in ('closed','reconnect','error'): return output('server '+event+'; no reconnection')
            if event=='connected' and isinstance(payload,dict):
                rate=payload.get('creditsPerMinute')
                if rate is not None and (not number(rate) or rate<0 or rate>plan['credits']-charged):
                    return output('advertised stream price exceeds reservation; connection closed')
                left=payload.get('creditsRemaining')
                if left is not None and (not number(left) or left<0): return output('invalid stream credit balance; connection closed')
            if event in ('credits','charged'):
                if not isinstance(payload,dict) or not number(payload.get('charged')) or payload['charged']<0:
                    return output('unverified stream charge; connection closed')
                charged+=payload['charged']
                if charged>=plan['credits']: return output('stream credit reservation reached; connection closed')
                if not number(payload.get('remaining')) or payload['remaining']<=0: return output('stream balance unavailable or exhausted; connection closed')
            if len(events)>=plan['stream']['max_events']: return output('stream event cap reached')
    return output('stream event cap reached')


def _validate_live(plan):
    if not isinstance(plan,dict) or 'id' not in plan or 'params' not in plan: raise EndpointError('Use plan_request to build a reviewed request plan.')
    canonical=plan_request(plan['id'],plan['params'])
    if canonical!=plan: raise EndpointError('Request plan changed after validation; rebuild it with plan_request.')
    if plan['live_blocked'] or plan['credits'] is None:
        raise EndpointError(plan['live_blocked'] or 'No verified price; live request disabled.')
    if 'trade_id' in plan['params'] and 'synthetic' in plan['params']['trade_id'].lower():
        raise EndpointError('Use a real trade_id from your returned data, not the fictional preview identifier.')
    now=datetime.now(timezone.utc)
    for name in ('from','to','at','start_time','end_time','start','end','start_date','end_date','date_start','date_end','as_of','date','as_of_date'):
        if name in plan['params'] and _instant(plan['params'][name])>now:
            raise EndpointError('Live historical/date selectors must not be in the future.')
    if plan['id']=='heatseeker.getHistoricalRange' and (now-_instant(plan['params']['from'])).total_seconds()>365*86400:
        raise EndpointError('Historical range must start within the last 365 days.')
    return canonical


def execute_plans(plans,api_key=None,max_credits=10,max_requests=3,max_seconds=30):
    """Execute a complete preflighted batch, sequentially; return payloads in order.

    No retry or partial-plan auto-resume occurs. On failure raise EndpointError;
    earlier calls may already be charged. Local caps cannot lock a shared account.
    """
    if type(max_requests) is not int or max_requests<1 or not number(max_credits) or max_credits<0 or not number(max_seconds) or not 0<max_seconds<=300:
        raise EndpointError('Use finite nonnegative credits, positive request count and 0–300 seconds.')
    if not isinstance(plans,list) or not plans: raise EndpointError('Provide a nonempty request-plan list.')
    plans=[_validate_live(plan) for plan in plans]
    if any(p['stream'] for p in plans) and len(plans)>1: raise EndpointError('Stream demos must run alone.')
    needs_auth=any(p['auth_required'] for p in plans)
    required_requests=len(plans)+(1 if needs_auth else 0)
    required_credits=sum(p['credits'] for p in plans)
    if required_requests>max_requests or required_credits>max_credits: raise EndpointError(f'Complete plan exceeds caps: {required_requests} requests / {required_credits:g} reserved credits. Nothing sent.')
    transport=_Transport(api_key if needs_auth else None,max_requests,max_seconds)
    if needs_auth:
        if not api_key: raise EndpointError('Authenticated endpoint requires a key through the hidden prompt or secure environment.')
        account_payload=transport.request(plan_request('heatseeker.getAccount',{}))
        data=account_payload.get('data') if isinstance(account_payload,dict) else None
        if not isinstance(data,dict) or data.get('status')!='active' or data.get('apiEligible') is not True:
            raise EndpointError('Active account access could not be verified; no endpoint requests sent.')
        limits=data.get('limits'); balance=data.get('creditsBalance')
        rpm=limits.get('requestsPerMinute') if isinstance(limits,dict) else None
        if type(rpm) is not int or rpm<required_requests: raise EndpointError('Account request rate cannot cover the complete plan.')
        transport.unlimited=data.get('unlimited') is True
        if not transport.unlimited and (not number(balance) or balance<required_credits): raise EndpointError('Account balance cannot cover the complete plan.')
        if transport.rate_remaining is not None and transport.rate_remaining<len(plans): raise EndpointError('Remaining server rate allowance cannot cover the complete plan.')
        if not transport.unlimited and transport.credit_remaining is not None and transport.credit_remaining<required_credits: raise EndpointError('Remaining server credit allowance cannot cover the complete plan.')
        for plan in plans:
            if plan['id'].startswith('heatseeker.') and 'symbols' in plan['params']:
                field='symbolsPerStream' if plan['stream'] else 'symbolsPerHeatmapCall'
                # Stats have their own public 50-symbol contract; Tempest is capped by its own 10.
                if plan['id'] in ('heatseeker.getDailyStats',) or '/v1/vol/' in plan['url']: continue
                limit=limits.get(field)
                if type(limit) is not int or len(plan['params']['symbols'].split(','))>limit:
                    raise EndpointError('Account symbol limit cannot cover the complete plan.')
    output=[]
    for index,plan in enumerate(plans):
        remaining_cost=sum(p['credits'] for p in plans[index:])
        if not transport.unlimited and transport.credit_remaining is not None and transport.credit_remaining<remaining_cost:
            raise EndpointError('Shared-account credit allowance changed; remaining calls stopped.')
        if transport.rate_remaining is not None and transport.rate_remaining<len(plans)-index:
            raise EndpointError('Shared rate allowance changed; remaining calls stopped.')
        output.append(transport.request(plan))
    return output


def execute_plan(plan,api_key=None,max_credits=10,max_requests=2,max_seconds=30):
    return execute_plans([plan],api_key,max_credits,max_requests,max_seconds)[0]
