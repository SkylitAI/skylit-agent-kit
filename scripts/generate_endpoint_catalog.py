#!/usr/bin/env python3
"""Regenerate catalog/audit from reviewed JSON contract snapshots, without network.

Optional --import-yaml SERVICE=PATH imports a reviewed public YAML snapshot
(requires developer-only PyYAML). Normal generation/tests need only stdlib.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
from datetime import date

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from skylit_agent_kit.contract_schema import resolve, synthetic, valid

CONTRACTS = ROOT / 'skylit_agent_kit/contracts'


def example_params(parameters, operation):
    result = {}
    for param in parameters:
        if not param.get('required'): continue
        name, schema = param['name'], param['schema']
        # Values here are fictional, never supplied to a live request implicitly.
        values = {'symbols':'SPY', 'tickers':'SPY', 'symbol':'SPY', 'ticker':'SPY', 'sector':'XLK',
            'trade_id':'synthetic-trade', 'strike':'100', 'q':'SP', 'query':'SP',
            'interval':'1D', 'bucket':'5min', 'resolution':'D', 'expiration':'2026-10-02',
            'at':'2026-09-30T14:00:00Z', 'start_time':'2026-09-30T14:00:00Z',
            'end_time':'2026-09-30T14:05:00Z', 'start_date':'2026-09-29', 'end_date':'2026-09-30'}
        if name in ('from','to'):
            value = (1790776800 if name == 'from' else 1790777100) if schema.get('type') == 'integer' else (
                ('2026-09-30T14:00:00Z' if name == 'from' else '2026-09-30T14:05:00Z') if schema.get('format') == 'date-time' else ('2026-09-29' if name == 'from' else '2026-09-30'))
        else: value = values.get(name, synthetic(schema, {}, name))
        if name in ('symbol','symbols') and operation['service'] == 'flowseeker':
            value = 'SPY__261002C00100000'
        result[name] = value
    if operation['operation_id'] == 'getDailyStats': result['to']='2026-09-30'
    if operation['operation_id'] == 'streamHeatmap': result.update(symbols='SPY', format='v2')
    return result


def next_step(entry):
    op, path = entry['operation_id'], entry['path']
    if op == 'getOpenAPI': return 'Inspect the returned contract version before changing an integration; this preview is not a full spec response.'
    if entry['stream']: return 'Inspect the first snapshot and credit/closed events; the live demo stops at its caps and never reconnects.'
    if op in ('getAccount',): return 'Check active access, balance and limits locally; do not publish this private response.'
    if op in ('listSymbols','listVolSymbols','searchSymbols','searchUnderlyings','listUnderlyings'):
        return 'Choose one returned supported symbol for a subsequent explicit demo; omitted symbols must stay unavailable.'
    if entry['service'] == 'atlas':
        return {'getHistory':'Inspect aligned t/o/h/l/c/v arrays and no_data before charting these bars locally.',
            'resolveSymbol':'Read session, timezone and supported resolutions before planning an Atlas history request.',
            'getConfig':'Read feed capabilities before choosing a supported price-history resolution.',
            'getServerTime':'Compare this server Unix time with source data timestamps; it is not a market quote.'}[op]
    if op == 'getVolHistory': return 'Preview the columnar sessions; live mode is blocked until the published pricing conflict is resolved.'
    if op == 'getTradeScore': return 'Obtain a real trade_id from a flow response, then inspect the returned score without inferring a probability.'
    if '/contract' in path:
        return 'Select a real OPRA contract from a chain or trade result; inspect this '+entry['summary'].lower().rstrip('.')+' response and its date before comparison.'
    if 'history' in path or 'historical' in path:
        return 'Choose explicit matching historical dates and inspect returned coverage before comparing this '+entry['summary'].lower().rstrip('.')+' result.'
    if 'flow' in path or op in ('getAggregate','getSweepMonitor','getVolOi','getMoneyness','getMarketTide','getMarketOverview'):
        return 'Inspect '+entry['summary'].lower().rstrip('.')+' for one dated window; distinguish returned samples from source aggregates.'
    return 'Inspect '+entry['summary'].lower().rstrip('.')+' and its source timestamp; keep missing values visible before adding this input to a saved report.'


def generate():
    provenance = json.loads((CONTRACTS / 'provenance.json').read_text())
    entries=[]
    for service in ('heatseeker','flowseeker','atlas'):
        document=json.loads((CONTRACTS / f'{service}.json').read_text())
        for path, path_item in document['paths'].items():
            for method, operation in path_item.items():
                if method not in ('get','post','put','patch','delete','head','options'): continue
                if method != 'get': raise ValueError('New non-read operation requires review')
                response=resolve(operation['responses']['200'], document)
                content_type, response_type = next(iter(response['content'].items()))
                parameters=[resolve(param, document) for param in path_item.get('parameters', [])+operation.get('parameters', [])]
                parameters=[{**param, 'schema':resolve(param.get('schema', {}), document)} for param in parameters]
                identity=f'{service}.{operation["operationId"]}'
                entry={'id':identity,'service':service,'operation_id':operation['operationId'], 'method':'GET',
                    'path':path, 'transport_path':'/v1/flow/openapi.json' if identity=='flowseeker.getOpenAPI' else path,
                    'host':document['servers'][0]['url'], 'summary':operation['summary'],
                    'description':operation.get('description',''), 'parameters':parameters,
                    'schema':response_type.get('schema',{}), 'content_type':content_type,
                    'credits':operation.get('x-credits'), 'pricing_extensions':{k:v for k,v in operation.items() if k.startswith('x-credits')},
                    'spec_auth_required':bool(operation.get('security', document.get('security',[]))),
                    'auth_required':True if identity=='flowseeker.getOpenAPI' else bool(operation.get('security', document.get('security',[]))),
                    'transport_override_note':'Flow introduction documents /v1/flow/openapi.json on the unified host; unauthenticated GET returned HTTP401 on 2026-10-01 despite operation security:[]. Preserve schema identity; require authenticated transport until reconciled.' if identity=='flowseeker.getOpenAPI' else None,
                    'stream':content_type=='text/event-stream', 'provenance':provenance[service],
                    'existing_demo':identity in ('heatseeker.getAccount','heatseeker.listSymbols','heatseeker.getHeatmap','flowseeker.getFlow'),
                    'live_blocked':'Published Tempest history pricing conflicts: extension says base 3 + 0.1/symbol-day; prose says ceil(symbol-weekdays/10), minimum 1. Live disabled pending clarification.' if identity=='heatseeker.getVolHistory' else None}
                entry['example_params']=example_params(parameters,entry)
                entry['example_response']=synthetic(entry['schema'],document)
                if entry['stream']:
                    data_schema={'$ref':'#/components/schemas/StreamSnapshot'} if entry['operation_id']=='streamHeatmap' else {'type':'object','properties':{'symbol':{'type':'string'},'asOf':{'type':'string','format':'date-time'}}}
                    data=synthetic(data_schema,document)
                    event='snapshot' if entry['operation_id']=='streamHeatmap' else 'vol'
                    entry['example_response']='event: connected\ndata: {"creditsRemaining":100,"creditsPerMinute":1}\n\nevent: '+event+'\ndata: '+json.dumps(data)+'\n\nevent: closed\ndata: {"reason":"synthetic_demo"}\n\n'
                if not valid(entry['example_response'],entry['schema'],document): raise ValueError('Invalid synthetic response '+identity)
                entry['schema_note']='Structural example only; public Tempest schemas leave module interiors underspecified.' if '/v1/vol/' in path else 'Fictional schema-shaped fields; not necessarily a coherent financial scenario.'
                entry['next_step']=next_step(entry)
                entry['preview_command']='python3 -m skylit_agent_kit endpoint '+identity
                entries.append(entry)
    return entries


def write_catalog(entries):
    (CONTRACTS/'endpoints.json').write_text(json.dumps(entries, indent=2, sort_keys=True)+'\n')
    lines=['# Public endpoint demo audit', '',
        '77 GET operations: Heatseeker/Tempest 24, Flowseeker 47, Atlas 6. Before this change, four route identities had runnable examples. Every row now has an offline synthetic request/response preview; authenticated live verification remains pending.', '',
        'A demo illustrates one request, not a complete research workflow. `endpoint ID` is offline; adding `--live` requires explicit required parameters. See [runner usage and limits](endpoint-demos.md).', '',
        '| Endpoint ID | Method and spec path | Documented base credits | Prior demo | Preview / next step |', '|---|---|---:|---|---|']
    for e in entries:
        price=str(e['credits'])+(' + stream charges' if e['stream'] else '')
        if e['live_blocked']: price+=' (live blocked)'
        lines.append(f'| `{e["id"]}` | `{e["method"]} {e["path"]}` | {price} | {"yes" if e["existing_demo"] else "no"} | `{e["preview_command"]}` — {e["next_step"].replace("|", "/")} |')
    lines.extend(['', 'Each catalog entry also preserves host, purpose, resolved parameter definitions, response schema, source URL/date/hash, exact synthetic preview and live eligibility. Flowseeker getOpenAPI retains spec `/v1/openapi.json` identity but uses the introduction-documented unified-host `/v1/flow/openapi.json` transport route. Its schema declares security:[], but an unauthenticated GET returned HTTP401 on 2026-10-01: the transport explicitly requires a key and account preflight. Range-based prices are computed or conservatively limited by the runner, not inferred from this base-price column.', ''])
    (ROOT/'docs/endpoint-audit.md').write_text('\n'.join(lines))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--import-yaml', action='append', default=[], metavar='SERVICE=PATH')
    args=parser.parse_args()
    if args.import_yaml:
        import yaml  # Optional maintainer import only; not a runtime or test dependency.
        provenance=json.loads((CONTRACTS/'provenance.json').read_text())
        for item in args.import_yaml:
            service,path=item.split('=',1)
            if service not in provenance: parser.error('Unknown service')
            raw=Path(path).read_bytes()
            encoded=json.dumps(yaml.safe_load(raw),indent=2,sort_keys=True)+'\n'
            (CONTRACTS/f'{service}.json').write_text(encoded)
            source_name={'heatseeker':'openapi','flowseeker':'flowseeker-openapi','atlas':'atlas-openapi'}[service]
            provenance[service]={'source_url':f'https://www.skylit.ai/docs/{source_name}.yaml',
                'checked':date.today().isoformat(),'source_yaml_sha256':hashlib.sha256(raw).hexdigest(),
                'snapshot_sha256':hashlib.sha256(encoded.encode()).hexdigest()}
            # A YAML import intentionally replaces, rather than misattributes, a prior live JSON snapshot.
        (CONTRACTS/'provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
    write_catalog(generate())
