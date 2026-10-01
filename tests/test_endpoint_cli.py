import contextlib
import io
import json
import socket
import unittest
from unittest.mock import patch
from skylit_agent_kit.__main__ import main
from skylit_agent_kit.catalog import list_endpoints

class EndpointCliTests(unittest.TestCase):
    def test_all_cli_previews_run_without_secret_or_network(self):
        for endpoint in list_endpoints():
            with self.subTest(endpoint=endpoint['id']),patch('sys.argv',['kit','endpoint',endpoint['id']]), \
                 patch('skylit_agent_kit.endpoint_cli.credential',side_effect=AssertionError('No key')), \
                 patch.object(socket,'socket',side_effect=AssertionError('No network')), \
                 contextlib.redirect_stdout(io.StringIO()) as out:
                self.assertEqual(main(),0)
                result=json.loads(out.getvalue())
                self.assertTrue(result['synthetic'])
                self.assertEqual(result['request']['id'],endpoint['id'])

    def test_live_bad_parameters_prices_and_dates_fail_before_secret_prompt(self):
        inputs=[['flowseeker.getTradeScore'],['atlas.getHistory'],
                ['heatseeker.getVolHistory','--param','symbols=SPY'],
                ['flowseeker.getFlow','--param','ticker=SPY','--param','date=2099-01-01'],
                ['flowseeker.getAggregate','--param','ticker=SPY','--param','timeframes=all'],
                ['heatseeker.getAccount','--param','bad=1'],
                ['heatseeker.getAccount','--max-seconds','nan']]
        for args in inputs:
            with self.subTest(args=args),patch('sys.argv',['kit','endpoint',*args,'--live']), \
                 patch('skylit_agent_kit.endpoint_cli.credential',side_effect=AssertionError('No key')), \
                 patch.object(socket,'socket',side_effect=AssertionError('No network')), \
                 contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(main(),1)

    def test_catalog_service_filter_and_parameter_discovery(self):
        with patch('sys.argv',['kit','endpoints','--service','atlas','--json']),contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(main(),0)
        self.assertEqual(len(json.loads(out.getvalue())),6)
        with patch('sys.argv',['kit','endpoint','flowseeker.getContractChart','--show-parameters']),contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(main(),0)
        required=[p['name'] for p in json.loads(out.getvalue())['parameters'] if p.get('required')]
        self.assertEqual(required,['symbol','interval','bucket'])

    def test_recipe_dispatch_preserves_actionable_budget_error_before_credentials(self):
        args=['kit','use-case','node-tracker','--live','--symbol','SPY',
              '--strikes','100,105','--expirations','2026-10-02',
              '--from','2026-09-30T14:00:00Z','--to','2026-09-30T14:06:00Z']
        with patch('sys.argv',args), \
             patch('skylit_agent_kit.use_cases.credential',side_effect=AssertionError('No key')), \
             patch.object(socket,'socket',side_effect=AssertionError('No network')), \
             contextlib.redirect_stderr(io.StringIO()) as error:
            self.assertEqual(main(),1)
        self.assertIn('25 credits',error.getvalue())
        self.assertNotIn('Cannot complete command',error.getvalue())
