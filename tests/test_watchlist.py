"""Synthetic fixtures shaped from the two official public OpenAPI specs."""
import io
import json
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from skylit_agent_kit.watchlist import (Client, WatchlistError, make_plan, run_watchlist,
                                       render_report, parse_heatmap, parse_flow)

ACCOUNT = {'data': {'status': 'active', 'apiEligible': True, 'unlimited': False,
                   'creditsBalance': 100, 'limits': {'symbolsPerHeatmapCall': 10, 'requestsPerMinute': 120}}}
CATALOG = {'data': {'symbols': [{'symbol': s, 'metrics': ['gamma', 'vanna'],
                               'isIndex': s == 'SPXW', 'history': None}
                              for s in ['SPXW', 'SPY', 'QQQ', 'TSLA', 'MSFT', 'AAPL', 'AMZN', 'META']]}}

def heat(symbol='SPY', metric='gamma'):
    return {'data': {'symbols': [{'symbol': symbol, 'asOf': '2026-10-01T14:00:00Z',
        'spot': 100, 'previousClose': 99, 'priceChange': 1, 'priceChangePercent': 1,
        'expirations': ['2026-10-02'], 'strikes': [{'strike': 100, 'value': -12345,
         'nodeType': 'king', 'velocityPct': 2}]}]},
        'meta': {'metric': metric, 'resolution': '1s', 'mode': 'live', 'cached': False}}

def flow(symbol='SPY'):
    return {'data': {'ticker': symbol, 'timeframe': '1d', 'trades': [
        {'timestamp': '2026-10-01T13:58:00Z', 'tradeId': 'fictional', 'optionType': 'CALL',
         'strike': 100, 'expiration': '2026-10-02', 'dte': 1, 'contracts': 2,
         'premium': 500, 'price': 2.5, 'bid': 2.4, 'ask': 2.5, 'mid': 2.45,
         'underlyingPrice': 100, 'isSweep': True, 'isMultiLeg': False, 'moneyness': 'ATM',
         'scores': {'flowScore': 35, 'flowBonus': 20, 'flowScoreInterpretation': 'bullish',
                    'flowBonusInterpretation': 'low_conviction', 'baseDirection': 30,
                    'convictionMultiplier': 1.1}}],
        'aggregate': {'vwf': 20, 'sdf': 30, 'fir': 10}, 'tradeCount': 1,
        'sweepCount': 1, 'totalPremium': 500, 'queryTimeMs': 5},
        'meta': {'timestamp': '2026-10-01T14:00:00Z', 'requestId': 'synthetic'}}

class FakeClient:
    def __init__(self, replies): self.replies, self.requests, self.credits = iter(replies), 0, 0
    def get(self, path, params=None, cost=0):
        self.requests += 1; self.credits += cost
        response = next(self.replies)
        if isinstance(response, Exception): raise response
        return response

class WatchlistTests(unittest.TestCase):
    def test_default_deduplicated_plan_costs_ten_credits_twelve_requests(self):
        plan = make_plan('SPXW,SPY,QQQ,TSLA,MSFT,AAPL,AMZN,META,MSFT')
        self.assertEqual(len(plan['symbols']), 8)
        self.assertEqual((plan['credits'], plan['requests']), (10, 12))
        self.assertEqual(plan['calls'][0]['symbols'][0], 'SPXW')

    def test_batching_and_no_symbol_substitution(self):
        plan = make_plan('SPXW,SPY,QQQ', batch_size=2)
        self.assertEqual(plan['credits'], 7)
        self.assertNotIn('SPX', plan['symbols'])
        with self.assertRaises(WatchlistError): make_plan('SPY,https://evil')

    def test_budget_blocks_before_paid_calls(self):
        client = FakeClient([ACCOUNT, CATALOG])
        result = run_watchlist(client, 'SPY', max_credits=2)
        self.assertIn('budget', result['stop'].lower())
        self.assertEqual(client.credits, 0)

    def test_account_balance_blocks_before_paid_calls(self):
        account = json.loads(json.dumps(ACCOUNT)); account['data']['creditsBalance'] = 0
        client = FakeClient([account, CATALOG])
        result = run_watchlist(client, 'SPY')
        self.assertIn('balance', result['stop'])
        self.assertEqual(client.credits, 0)

    def test_lower_account_batch_limit_replans_before_paid_calls(self):
        account = json.loads(json.dumps(ACCOUNT)); account['data']['limits']['symbolsPerHeatmapCall'] = 1
        client = FakeClient([account, CATALOG])
        result = run_watchlist(client, 'SPY,QQQ', max_credits=5)
        self.assertIn('budget', result['stop'].lower())
        self.assertEqual(client.credits, 0)

    def test_missing_spxw_is_not_replaced_and_flow_still_attempted(self):
        catalog = {'data': {'symbols': [{'symbol': 'SPX', 'metrics': ['gamma', 'vanna']}]}}
        client = FakeClient([ACCOUNT, catalog, WatchlistError('No data (HTTP 404).', status=404)])
        result = run_watchlist(client, 'SPXW')
        self.assertIn('unsupported', result['rows']['SPXW']['gamma']['status'])
        self.assertIn('404', result['rows']['SPXW']['flow']['status'])
        self.assertEqual(client.credits, 1)

    def test_global_failure_stops_and_marks_remaining(self):
        client = FakeClient([ACCOUNT, CATALOG, WatchlistError('Access stopped (HTTP 403).', status=403)])
        result = run_watchlist(client, 'SPY,QQQ')
        self.assertEqual(client.requests, 3)
        self.assertIn('403', result['stop'])
        self.assertIn('not requested', result['rows']['QQQ']['flow']['status'])

    def test_partial_heatmap_and_missing_fields_are_explicit(self):
        values = parse_heatmap(heat(), ['SPY', 'QQQ'], 'gamma')
        self.assertEqual(values['SPY']['strikes'][0]['value'], -12345)
        self.assertIn('missing', values['QQQ']['status'])
        malformed = heat(); malformed['data']['symbols'][0]['strikes'][0]['value'] = None
        self.assertIn('invalid', parse_heatmap(malformed, ['SPY'], 'gamma')['SPY']['status'])
        with self.assertRaises(WatchlistError): parse_heatmap(heat(metric='vanna'), ['SPY'], 'gamma')

    def test_flow_uses_exact_fields_and_distinguishes_timestamps(self):
        parsed = parse_flow(flow(), 'SPY')
        self.assertEqual(parsed['aggregate']['vwf'], 20)
        self.assertEqual(parsed['latest_trade'], '2026-10-01T13:58:00+00:00')
        self.assertNotEqual(parsed['latest_trade'], parsed['generated_at'])
        with self.assertRaises(WatchlistError): parse_flow(flow('SPX'), 'SPXW')
        empty = flow(); empty['data']['trades'] = []
        self.assertIn('no trades', parse_flow(empty, 'SPY')['status'])

    def test_report_displays_source_values_without_recalculating(self):
        client = FakeClient([ACCOUNT, CATALOG, heat(), heat(metric='vanna'), flow()])
        result = run_watchlist(client, 'SPY')
        report = render_report(result)
        for expected in ('-12,345', 'gamma', 'vanna', '35', '500', '2026-10-01T13:58'):
            self.assertIn(expected, report)
        self.assertNotIn('customerId', report)
        self.assertEqual(client.credits, 3)

    @patch('skylit_agent_kit.watchlist.build_opener')
    def test_transport_fixed_host_no_retry_and_sanitized_errors(self, opener):
        client = Client('test-secret')
        opener.return_value.open.side_effect = HTTPError('https://api.skylit.ai', 429, 'test-secret private', {}, None)
        with self.assertRaises(WatchlistError) as error: client.get('/v1/flow/SPY', cost=1)
        self.assertNotIn('test-secret', str(error.exception))
        self.assertEqual(opener.return_value.open.call_count, 1)
        self.assertEqual(client.credits, 1)
        with self.assertRaises(WatchlistError): client.get('https://evil.example')
        self.assertEqual(opener.return_value.open.call_count, 1)

    @patch('skylit_agent_kit.watchlist.build_opener')
    def test_transport_rejects_invalid_credentials_shapes_and_large_bodies(self, opener):
        for key in ('', 'key\nheader', 'key with spaces'):
            with self.assertRaises(WatchlistError): Client(key)
        opener.assert_not_called()
        for body in (b'[]', b'{"n":NaN}', b'x'*1048577):
            opener.return_value.open.return_value = io.BytesIO(body)
            with self.assertRaises(WatchlistError): Client('test-secret').get('/v1/account')

    @patch('skylit_agent_kit.watchlist.build_opener')
    def test_transport_redacts_echoed_credentials(self, opener):
        opener.return_value.open.return_value = io.BytesIO(b'{"message":"test-secret"}')
        self.assertNotIn('test-secret', json.dumps(Client('test-secret').get('/v1/account')))

    def test_transport_limits_hold_even_without_workflow(self):
        client = Client('test-secret', max_requests=0)
        with self.assertRaises(WatchlistError): client.get('/v1/account')
        self.assertEqual(client.requests, 0)

class AdditionalWatchlistTests(unittest.TestCase):
    def test_all_eight_success_exact_paths_and_query_parameters(self):
        calls = []
        class RecordingClient(FakeClient):
            def get(self, path, params=None, cost=0):
                calls.append((path, params, cost))
                return super().get(path, params, cost)
        symbols = ['SPXW','SPY','QQQ','TSLA','MSFT','AAPL','AMZN','META']
        boards = []
        for metric in ('gamma','vanna'):
            payload = heat(metric=metric)
            payload['data']['symbols'] = [heat(symbol, metric)['data']['symbols'][0] for symbol in symbols]
            boards.append(payload)
        client = RecordingClient([ACCOUNT, CATALOG, *boards, *[flow(s) for s in symbols]])
        result = run_watchlist(client, ','.join(symbols + ['MSFT']), trading_date='2026-10-01')
        self.assertEqual(result['stop'], 'completed')
        self.assertEqual(result['symbols'], symbols)
        self.assertEqual((result['requests'], result['credits_reserved']), (12, 10))
        self.assertEqual(calls[2], ('/v1/heatmap', {'symbols': ','.join(symbols), 'metric': 'gamma', 'maxStrikes': 92, 'maxExpirations': 5}, 1))
        self.assertEqual(calls[3][1]['metric'], 'vanna')
        self.assertEqual([c[0] for c in calls[4:]], ['/v1/flow/' + s for s in symbols])
        self.assertEqual(calls[4][1], {'timeframe': '1d', 'limit': 10, 'date': '2026-10-01'})
        self.assertTrue(all(component['status'] == 'available' for row in result['rows'].values() for component in row.values()))
        self.assertEqual(result['raw'], [])

    def test_all_global_failure_statuses_stop_remaining_requests(self):
        for status in (401,402,403,429,500,503,504,None):
            with self.subTest(status=status):
                client = FakeClient([ACCOUNT, CATALOG, WatchlistError('sanitized failure', status)])
                result = run_watchlist(client, 'SPY,QQQ')
                self.assertEqual(client.requests, 3)
                self.assertEqual(result['stop'], 'sanitized failure')

    def test_account_invalid_limits_fail_before_discovery_or_paid_requests(self):
        for field in ('requestsPerMinute', 'symbolsPerHeatmapCall'):
            for value in (None, 0, -1, True, float('nan'), float('inf'), '10'):
                with self.subTest(field=field, value=value):
                    account = json.loads(json.dumps(ACCOUNT)); account['data']['limits'][field] = value
                    client = FakeClient([account])
                    result = run_watchlist(client, 'SPY')
                    self.assertEqual(client.requests, 1)
                    self.assertEqual(client.credits, 0)
                    self.assertIn('could not be verified', result['stop'])

    def test_rate_limit_cannot_cover_plan(self):
        account = json.loads(json.dumps(ACCOUNT)); account['data']['limits']['requestsPerMinute'] = 3
        result = run_watchlist(FakeClient([account, CATALOG]), 'SPY')
        self.assertIn('budget', result['stop'])

    def test_current_rate_header_prevents_partial_paid_run(self):
        client = FakeClient([ACCOUNT, CATALOG]); client.rate_remaining = 2
        result = run_watchlist(client, 'SPY')
        self.assertIn('rate allowance', result['stop'])
        self.assertEqual(client.credits, 0)

    def test_malformed_fields_do_not_crash_or_claim_wrong_timeframe(self):
        malformed = heat(); malformed['data']['symbols'][0]['symbol'] = []
        self.assertIn('missing', parse_heatmap(malformed, ['SPY'], 'gamma')['SPY']['status'])
        malformed = heat(); malformed['data']['symbols'][0]['strikes'][0]['value'] = 10**400
        self.assertIn('invalid', parse_heatmap(malformed, ['SPY'], 'gamma')['SPY']['status'])
        malformed = flow(); malformed['data']['timeframe'] = '1h'
        with self.assertRaises(WatchlistError): parse_flow(malformed, 'SPY')

    @patch('skylit_agent_kit.watchlist.build_opener')
    def test_escaped_credentials_never_reach_returned_data(self, opener):
        key = 'secret\\"key'
        opener.return_value.open.return_value = io.BytesIO(json.dumps({key: 'echo ' + key}).encode())
        value = Client(key).get('/v1/account')
        self.assertEqual(value, {'[REDACTED]': 'echo [REDACTED]'})

    @patch('skylit_agent_kit.watchlist.build_opener')
    def test_timeout_and_deadline_errors_are_sanitized(self, opener):
        opener.return_value.open.side_effect = TimeoutError('secret details')
        with self.assertRaises(WatchlistError) as error: Client('test-secret').get('/v1/account')
        self.assertNotIn('secret details', str(error.exception))
        client = Client('test-secret'); client.deadline = 0
        with self.assertRaisesRegex(WatchlistError, 'Elapsed-time'): client.get('/v1/account')
        self.assertEqual(client.requests, 0)

    @patch('skylit_agent_kit.watchlist.build_opener')
    def test_headers_exhaust_rate_and_next_request_is_not_sent(self, opener):
        response = io.BytesIO(b'{}'); response.headers = {'X-RateLimit-Remaining': '0'}
        opener.return_value.open.return_value = response
        client = Client('test-secret'); client.get('/v1/account')
        with self.assertRaisesRegex(WatchlistError, 'rate allowance'): client.get('/v1/symbols')
        self.assertEqual(opener.return_value.open.call_count, 1)

    def test_invalid_budgets_never_start_transport(self):
        for field, value in (('max_seconds', float('nan')), ('max_seconds', -1), ('max_requests', -1), ('max_credits', -1)):
            with self.subTest(field=field), self.assertRaises(WatchlistError): Client('test-secret', **{field:value})

    def test_compact_report_caps_display_and_preserves_full_raw_only_on_request(self):
        board = heat()
        board['data']['symbols'][0]['strikes'] = [{'strike': n, 'value': n*100, 'nodeType': 'normal'} for n in range(92)]
        vanna = json.loads(json.dumps(board)); vanna['meta']['metric'] = 'vanna'
        client = FakeClient([ACCOUNT, CATALOG, board, vanna, flow()])
        result = run_watchlist(client, 'SPY', save_raw=True)
        report = render_report(result)
        self.assertIn('3 largest returned strike magnitudes of 92', report)
        self.assertLess(len(report.splitlines()), 70)
        self.assertEqual(len(result['raw'][0]['response']['data']['symbols'][0]['strikes']), 92)


    @patch('skylit_agent_kit.watchlist.build_opener')
    def test_default_plan_requires_all_ten_paid_calls_in_current_rate_allowance(self, opener):
        account_response = io.BytesIO(json.dumps(ACCOUNT).encode())
        account_response.headers = {'X-RateLimit-Remaining': '6'}
        catalog_response = io.BytesIO(json.dumps(CATALOG).encode())
        catalog_response.headers = {'X-RateLimit-Remaining': '5'}
        opener.return_value.open.side_effect = [account_response, catalog_response]
        client = Client('synthetic-key')
        result = run_watchlist(client)
        self.assertEqual(len(result['symbols']), 8)
        self.assertEqual(len(result['plan']['calls']), 10)
        self.assertIn('rate allowance is below the complete plan', result['stop'])
        self.assertEqual((client.requests, client.credits), (2, 0))
        self.assertEqual(opener.return_value.open.call_count, 2)
        paths = [call.args[0].full_url for call in opener.return_value.open.call_args_list]
        self.assertEqual(paths, ['https://api.skylit.ai/v1/account', 'https://api.skylit.ai/v1/symbols'])
