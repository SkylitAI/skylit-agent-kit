"""Novice-friendly catalog discovery and explicit endpoint live opt-in."""
import json
import sys
from . import catalog
from .endpoint_demo import EndpointError, execute_plan, plan_request, preview, validate_plan_for_live
from .watchlist import number
from .watchlist_cli import credential, output_path, save_private


def add_parser(commands):
    listing=commands.add_parser('endpoints',help='List all public endpoint demos (offline)')
    listing.add_argument('--service',choices=('heatseeker','flowseeker','atlas'))
    listing.add_argument('--json',action='store_true',help='Machine-readable catalog metadata')
    demo=commands.add_parser('endpoint',help='Preview one fictional request/response; --live opts into bounded requests')
    demo.add_argument('identity',help='Service.operationId from endpoints')
    demo.add_argument('--param',action='append',default=[],metavar='NAME=VALUE')
    demo.add_argument('--live',action='store_true')
    demo.add_argument('--show-parameters',action='store_true',help='Inspect public parameter definitions offline')
    demo.add_argument('--max-credits',type=float,default=10)
    demo.add_argument('--max-requests',type=int,default=2)
    demo.add_argument('--max-seconds',type=float,default=30)
    demo.add_argument('--output',help='Optional private JSON output under ignored reports/; never overwrite')


def run(args):
    if args.command=='endpoints':
        entries=[item for item in catalog.list_endpoints() if args.service is None or item['service']==args.service]
        if args.json: print(json.dumps(entries,indent=2))
        else:
            print(f'{len(entries)} public endpoint demos. Offline by default; authenticated verification pending.')
            for entry in entries:
                print(f'{entry["id"]}: {entry["summary"]}'+(' [live blocked: pricing conflict]' if entry['live_blocked'] else ''))
            print('Try: python3 -m skylit_agent_kit endpoint <ID>')
            print('Inspect inputs: python3 -m skylit_agent_kit endpoint <ID> --show-parameters')
        return 0
    entry=catalog.get_endpoint(args.identity)
    if args.show_parameters:
        if args.live: raise EndpointError('--show-parameters is offline; omit --live.')
        print(json.dumps({'id':entry['id'],'parameters':entry['parameters'],'source':entry['provenance']['source_url']},indent=2))
        return 0
    params={}
    for item in args.param:
        if '=' not in item: raise EndpointError('Use --param name=value.')
        key,value=item.split('=',1)
        if key in params: raise EndpointError('Each parameter may be supplied only once.')
        params[key]=value
    if not number(args.max_credits) or args.max_credits<0 or args.max_requests<1 or not number(args.max_seconds) or not 0<args.max_seconds<=300:
        raise EndpointError('Use finite nonnegative credits, positive requests and 0–300 seconds.')
    destination=output_path(args.output) if args.output else None
    if not args.live:
        result=preview(args.identity,params)
    else:
        plan=validate_plan_for_live(plan_request(args.identity,params))  # No fictional required defaults.
        if plan['live_blocked']: raise EndpointError(plan['live_blocked'])
        if plan['credits'] is None: raise EndpointError('No verified endpoint price; live disabled.')
        requests=2 if plan['auth_required'] else 1
        if plan['credits']>args.max_credits or requests>args.max_requests:
            raise EndpointError(f'Plan needs {requests} requests / {plan["credits"]:g} reserved credits. Caps are not increased automatically.')
        print(f'Live plan: {requests} request(s), {plan["credits"]:g} reserved credits; no retries or polling.',file=sys.stderr)
        key=credential() if plan['auth_required'] else None
        payload=execute_plan(plan,key,args.max_credits,args.max_requests,args.max_seconds)
        result={'synthetic':False,'id':args.identity,'request':plan,'response':payload,
                'next_step':entry['next_step'],'source':entry['provenance']['source_url'],
                'usage_note':'Reservation is conservative, not a billing receipt or shared-account spending lock.'}
    content=json.dumps(result,indent=2,allow_nan=False)+'\n'
    if destination:
        save_private(destination,content)
        print(f'Saved private endpoint output: {destination}')
    else: print(content,end='')
    return 0
