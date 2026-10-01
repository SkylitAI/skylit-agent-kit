import copy
import io
import json
import socket
import unittest
from datetime import datetime, timezone
from unittest.mock import patch
from urllib.error import HTTPError, URLError
from skylit_agent_kit.catalog import list_endpoints, get_endpoint
from skylit_agent_kit.endpoint_demo import EndpointError, plan_request, preview, execute_plan, execute_plans

ACCOUNT={'data':{'status':'active','apiEligible':True,'creditsBalance':1000,'unlimited':False,
                  'limits':{'requestsPerMinute':120,'symbolsPerHeatmapCall':10,'symbolsPerStream':10}}}

def response(value, plain=False, headers=None):
    result=io.BytesIO(value.encode() if plain else json.dumps(value).encode())
    result.headers={} if headers is None else headers
    return result

class EndpointPlanningTests(unittest.TestCase):
    def test_every_preview_serializes_and_stays_offline(self):
        with patch.object(socket,'socket',side_effect=AssertionError('No network')):
            for endpoint in list_endpoints():
                with self.subTest(endpoint=endpoint['id']):
                    demo=preview(endpoint['id'])
                    self.assertTrue(demo['synthetic'])
                    self.assertEqual(demo['request']['method'],'GET')
                    json.dumps(demo,allow_nan=False)

    def test_required_params_never_come_from_fictional_preview(self):
        for identity in ('flowseeker.getTradeScore','flowseeker.getContractChart','heatseeker.getHeatmap','atlas.getHistory'):
            with self.subTest(identity=identity), self.assertRaisesRegex(EndpointError,'Required'):
                plan_request(identity,{})
        with self.assertRaises(EndpointError): plan_request('heatseeker.getAccount',[])

    def test_unknown_params_injection_enum_bounds_and_formats(self):
        cases=[('flowseeker.getFlow',{'ticker':'../account'}),('heatseeker.getAccount',{'Authorization':'secret'}),
               ('flowseeker.getFlow',{'ticker':'SPY','limit':501}),('flowseeker.getFlow',{'ticker':'SPY','option_type':'evil'}),
               ('flowseeker.getFlow',{'ticker':'SPY','date':'2026-02-30'}),('flowseeker.getFlow',{'ticker':'SPY','min_premium':'nan'}),
               ('flowseeker.getFlow',{'ticker':'SPY','min_premium':10,'max_premium':9}),
               ('flowseeker.getFlow',{'ticker':'SPY','conviction_weights':'{"a":2}'}),
               ('flowseeker.getUnderlyingChain',{'ticker':'SPY','expiration':'2026-09-30\nAuthorization:evil'})]
        for identity,params in cases:
            with self.subTest(identity=identity,params=params), self.assertRaises(EndpointError): plan_request(identity,params)

    def test_serialization_quotes_query_text_and_places_path_and_header_params(self):
        plan=plan_request('atlas.searchSymbols',{'query':'SP&extra=1'})
        self.assertIn('query=SP%26extra%3D1',plan['url'])
        self.assertNotIn('&extra=',plan['url'])
        stream=plan_request('heatseeker.streamHeatmap',{'symbols':'SPY','Last-Event-ID':'SPY:123','includeEmpty':'true'})
        self.assertEqual(stream['headers'],{'Last-Event-ID':'SPY:123'})
        self.assertIn('includeEmpty=true',stream['url'])

    def test_range_price_and_cross_field_guards(self):
        self.assertEqual(plan_request('flowseeker.getAggregate',{'ticker':'SPY','timeframes':'all'})['credits'],15)
        self.assertEqual(plan_request('flowseeker.getMarketTide',{'interval':'360D','bucket':'1d'})['credits'],36)
        self.assertEqual(plan_request('flowseeker.getTopContractsDaily',{'ticker':'SPY'})['credits'],1)
        cases=[('flowseeker.getAggregate',{'ticker':'SPY','timeframes':'unknown'}),
               ('flowseeker.getMarketTide',{'interval':'360D','bucket':'5min'}),
               ('flowseeker.getMarketTide',{'interval':'7D','exclude_deep_itm':True}),
               ('flowseeker.getDarkPoolTrades',{'date_start':'2026-01-01'}),
               ('flowseeker.getDarkPoolTrades',{'date_start':'2026-01-01','date_end':'2026-02-02'}),
               ('heatseeker.getHistoricalRange',{'symbols':'SPY','from':'2026-09-30T14:00:00Z','to':'2026-09-30T14:16:00Z'}),
               ('heatseeker.getDailyStats',{'symbols':'SPY','from':'2026-01-01','to':'2026-02-02'}),
               ('atlas.getHistory',{'symbol':'SPY','resolution':'D','from':100,'to':200,'countback':999999})]
        for identity,params in cases:
            with self.subTest(identity=identity), self.assertRaises(EndpointError): plan_request(identity,params)

    def test_public_metadata_auth_override_and_conflicted_price(self):
        self.assertTrue(plan_request('flowseeker.getOpenAPI')['auth_required'])
        self.assertFalse(get_endpoint('flowseeker.getOpenAPI')['spec_auth_required'])
        self.assertFalse(plan_request('heatseeker.getOpenAPI')['auth_required'])
        self.assertEqual(plan_request('flowseeker.getOpenAPI')['url'],'https://api.skylit.ai/v1/flow/openapi.json')
        self.assertTrue(plan_request('atlas.getOpenAPI')['auth_required'])
        blocked=preview('heatseeker.getVolHistory')['request']
        self.assertIsNone(blocked['credits'])
        with self.assertRaisesRegex(EndpointError,'pricing conflicts'): execute_plan(blocked,'fake')

class EndpointTransportTests(unittest.TestCase):
    @patch('skylit_agent_kit.endpoint_demo.build_opener')
    def test_every_supported_route_serializes_through_real_mock_http_transport(self, factory):
        for entry in list_endpoints():
            if entry['live_blocked']: continue
            factory.reset_mock()
            params=copy.deepcopy(entry['example_params'])
            if 'trade_id' in params: params['trade_id']='flow_caller_selected_1'
            plan=plan_request(entry['id'],params)
            body=entry['example_response']
            replies=[response(body,entry['content_type']!='application/json')]
            if plan['auth_required']: replies.insert(0,response(ACCOUNT))
            factory.return_value.open.side_effect=replies
            with self.subTest(endpoint=entry['id']),patch('skylit_agent_kit.endpoint_demo.datetime',wraps=datetime) as clock:
                clock.now.return_value=datetime(2026,10,1,tzinfo=timezone.utc)
                result=execute_plan(plan,'test-secret' if plan['auth_required'] else None,max_credits=100)
                request=factory.return_value.open.call_args.args[0]
                self.assertEqual(request.full_url,plan['url'])
                self.assertEqual(request.get_method(),'GET')
                self.assertEqual(factory.return_value.open.call_count,2 if plan['auth_required'] else 1)
                self.assertEqual(request.get_header('Authorization'),'Bearer test-secret' if plan['auth_required'] else None)
                self.assertNotIn('test-secret',json.dumps(result))
                if plan['stream']: self.assertIn('server closed',result['stop'])
                else: self.assertEqual(result,body)

    @patch('skylit_agent_kit.endpoint_demo.build_opener')
    def test_complete_batch_cost_and_request_caps_precede_all_network(self,factory):
        plans=[plan_request('flowseeker.getFlow',{'ticker':'SPY'}),plan_request('atlas.resolveSymbol',{'symbol':'SPY'})]
        for limits in ({'max_credits':1},{'max_requests':2}):
            with self.assertRaisesRegex(EndpointError,'Complete plan exceeds'):execute_plans(plans,'test-secret',**limits)
        factory.assert_not_called()

    @patch('skylit_agent_kit.endpoint_demo.build_opener')
    def test_batch_single_account_preflight_order_and_balance_rate_stops(self,factory):
        plans=[plan_request('flowseeker.getFlow',{'ticker':'SPY'}),plan_request('atlas.resolveSymbol',{'symbol':'SPY'})]
        factory.return_value.open.side_effect=[response(ACCOUNT),response({'data':1}),response({'name':'SPY'})]
        self.assertEqual(execute_plans(plans,'test-secret'),[{'data':1},{'name':'SPY'}])
        self.assertEqual(factory.return_value.open.call_count,3)
        for field in ('balance','rate'):
            factory.reset_mock(); account=copy.deepcopy(ACCOUNT)
            headers={}
            if field=='balance':account['data']['creditsBalance']=1
            else:headers={'X-RateLimit-Remaining':'1'}
            factory.return_value.open.side_effect=[response(account,headers=headers)]
            with self.assertRaises(EndpointError):execute_plans(plans,'test-secret')
            self.assertEqual(factory.return_value.open.call_count,1)

    @patch('skylit_agent_kit.endpoint_demo.build_opener')
    def test_failures_never_retry_redirect_or_leak_bodies(self,factory):
        plan=plan_request('atlas.getConfig')
        for status in (301,302,401,402,403,429,503):
            factory.reset_mock()
            factory.return_value.open.side_effect=HTTPError(plan['url'],status,'private test-secret',{},None)
            with self.subTest(status=status),self.assertRaises(EndpointError) as failure: execute_plan(plan,'test-secret')
            self.assertNotIn('private',str(failure.exception)); self.assertNotIn('test-secret',str(failure.exception))
            self.assertEqual(factory.return_value.open.call_count,1)
        handler=factory.call_args.args[0]
        self.assertIsNone(handler.redirect_request(None,None,302,'',{},'https://evil.example'))

    @patch('skylit_agent_kit.endpoint_demo.build_opener')
    def test_tampered_plans_unknown_prices_and_credentials_fail_before_requests(self,factory):
        for field,value in (('url','https://evil.example'),('credits',0),('method','POST')):
            plan=plan_request('atlas.resolveSymbol',{'symbol':'SPY'});plan[field]=value
            with self.assertRaisesRegex(EndpointError,'changed'):execute_plan(plan,'test-secret')
        for key in ('','bad\nheader','bad key'):
            with self.assertRaises(EndpointError): execute_plan(plan_request('atlas.getConfig'),key)
        factory.assert_not_called()

    @patch('skylit_agent_kit.endpoint_demo.build_opener')
    def test_oversized_nonfinite_invalid_timeout_and_redaction(self,factory):
        plan=plan_request('heatseeker.getOpenAPI')
        for body in (b'x'*1048577,b'bad json',b'{"n":NaN}',b'{"n":1e999}'):
            factory.return_value.open.side_effect=[io.BytesIO(body)]
            with self.assertRaises(EndpointError):execute_plan(plan)
        factory.return_value.open.side_effect=URLError('private diagnostics')
        with self.assertRaisesRegex(EndpointError,'Connection failed') as failure:execute_plan(plan)
        self.assertNotIn('private',str(failure.exception))
        secret='test\\"secret'
        factory.return_value.open.side_effect=[response(ACCOUNT),response({secret:'echo '+secret})]
        result=execute_plan(plan_request('atlas.getConfig'),secret)
        self.assertEqual(result,{'[REDACTED]':'echo [REDACTED]'})

    @patch('skylit_agent_kit.endpoint_demo.build_opener')
    def test_future_selector_and_fictional_trade_identifier_never_go_live(self,factory):
        for plan in (plan_request('flowseeker.getFlow',{'ticker':'SPY','date':'2099-01-01'}),preview('flowseeker.getTradeScore')['request']):
            with self.assertRaises(EndpointError):execute_plan(plan,'test-secret')
        factory.assert_not_called()

    @patch('skylit_agent_kit.endpoint_demo.build_opener')
    def test_stream_protocol_limits_and_no_reconnect(self,factory):
        plan=plan_request('heatseeker.streamHeatmap',{'symbols':'SPY,QQQ'})
        self.assertEqual(plan['credits'],4)
        for body,reason in [('event: credits\ndata: {"charged":2,"remaining":100}\n\n','reservation reached'),
                            ('event: reconnect\ndata: {"reason":"max_duration"}\n\n','no reconnection'),
                            ('event: connected\ndata: {"creditsPerMinute":100}\n\n','exceeds reservation'),
                            ('event: snapshot\ndata: {}\n\n'*100,'event cap')]:
            factory.reset_mock();factory.return_value.open.side_effect=[response(ACCOUNT),response(body,True)]
            result=execute_plan(plan,'test-secret')
            self.assertIn(reason,result['stop'])
            self.assertLessEqual(len(result['events']),10)
            self.assertEqual(factory.return_value.open.call_count,2)


    @patch('skylit_agent_kit.endpoint_demo.build_opener')
    def test_unlimited_account_still_obeys_local_caps_but_not_zero_balance_header(self,factory):
        account=copy.deepcopy(ACCOUNT);account['data'].update(unlimited=True,creditsBalance=0)
        plan=plan_request('atlas.resolveSymbol',{'symbol':'SPY'})
        factory.return_value.open.side_effect=[response(account,headers={'X-Credits-Remaining':'0'}),response({'name':'SPY'})]
        self.assertEqual(execute_plan(plan,'test-secret'),{'name':'SPY'})
        factory.reset_mock()
        with self.assertRaises(EndpointError):execute_plan(plan,'test-secret',max_credits=0)
        factory.assert_not_called()

    @patch('skylit_agent_kit.endpoint_demo.build_opener')
    def test_stream_byte_cap_timeout_and_nonfinite_payload(self,factory):
        plan=plan_request('heatseeker.streamHeatmap',{'symbols':'SPY'})
        for body in (':'+('x'*1048576), 'event: snapshot\ndata: {"value":1e999}\n\n'):
            factory.return_value.open.side_effect=[response(ACCOUNT),response(body,True)]
            with self.assertRaises(EndpointError):execute_plan(plan,'test-secret')
        stream=response('',True)
        with patch.object(stream,'read1',side_effect=TimeoutError('private')):
            factory.return_value.open.side_effect=[response(ACCOUNT),stream]
            result=execute_plan(plan,'test-secret')
        self.assertIn('timeout',result['stop'])
        self.assertNotIn('private',json.dumps(result))
