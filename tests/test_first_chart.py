import argparse
import contextlib
import copy
import io
import unittest
from pathlib import Path
from unittest.mock import patch

from skylit_agent_kit import first_chart as fc
from skylit_agent_kit.use_case_errors import UseCaseError


def payload(strikes=None, symbol='SPY', spot=501.2):
    nodes = strikes if strikes is not None else [
        {'strike': 495, 'value': -2.5e8, 'nodeType': 'gatekeeper'},
        {'strike': 500, 'value': 9.1e8, 'nodeType': 'king'},
        {'strike': 505, 'value': 3.0e8, 'nodeType': 'normal'},
    ]
    return {'data': {'symbols': [{'symbol': symbol, 'asOf': '2026-10-05T19:59:58Z', 'spot': spot,
                                  'previousClose': 498.0, 'priceChange': 3.2, 'priceChangePercent': 0.64,
                                  'expirations': ['2026-10-05', '2026-10-06'], 'strikes': nodes}]},
            'meta': {'metric': 'gamma', 'mode': 'live', 'attribution': {'text': 'Data: Skylit'}}}


class FirstChartCommand(unittest.TestCase):
    def args(self, *argv):
        parser = argparse.ArgumentParser()
        fc.add_parser(parser.add_subparsers(dest='command'))
        return parser.parse_args(['first-chart', *argv])

    def run_cli(self, *argv, response=None, error=None):
        writes, out = [], io.StringIO()
        with patch.object(fc, 'output_path', side_effect=lambda x: Path(x)), \
                patch.object(fc, 'save_private', side_effect=lambda p, c: writes.append((Path(p), c))), \
                patch.object(fc, 'credential', return_value='test-placeholder') as credential, \
                patch.object(fc, 'execute_plan', return_value=response, side_effect=error) as execute, \
                contextlib.redirect_stdout(out):
            status = fc.run(self.args(*argv))
        return status, out.getvalue(), writes, credential, execute

    def test_offline_default_draws_the_fictional_chart_without_a_key(self):
        status, out, writes, credential, execute = self.run_cli()
        self.assertEqual(status, 0)
        credential.assert_not_called()
        execute.assert_not_called()
        svg = next(c for p, c in writes if p.suffix == '.svg')
        report = next(c for p, c in writes if p.suffix == '.md')
        self.assertIn('FICTIONAL', svg)
        self.assertIn('Demo by Skylit (fictional data)', report)
        self.assertIn('1 credit', out)
        self.assertIn('--live', out)

    def test_live_requests_one_heatmap_within_a_one_credit_cap(self):
        status, out, writes, credential, execute = self.run_cli('--live', response=payload())
        self.assertEqual(status, 0)
        credential.assert_called_once_with()
        plan, key = execute.call_args.args[:2]
        self.assertEqual(plan['id'], 'heatseeker.getHeatmap')
        self.assertEqual(plan['params']['symbols'], 'SPY')
        self.assertEqual(plan['params']['metric'], 'gamma')
        self.assertEqual(key, 'test-placeholder')
        self.assertEqual(execute.call_args.kwargs, {'max_credits': 1, 'max_requests': 2, 'max_seconds': 30})
        report = next(c for p, c in writes if p.suffix == '.md')
        self.assertIn('Data: Skylit', report)
        self.assertNotIn('fictional', report.lower())
        self.assertIn('2026-10-05T19:59:58Z', report)
        self.assertIn('500', report)  # king strike named
        self.assertIn('Saved chart', out)

    def test_symbol_and_metric_are_passed_through_uppercased(self):
        _, _, _, _, execute = self.run_cli('--live', '--symbol', 'qqq', '--metric', 'vanna', response=payload(symbol='QQQ'))
        plan = execute.call_args.args[0]
        self.assertEqual((plan['params']['symbols'], plan['params']['metric']), ('QQQ', 'vanna'))

    def test_cap_below_plan_cost_stops_before_reading_a_key(self):
        with self.assertRaises(UseCaseError):
            self.run_cli('--live', '--max-credits', '0')
        with patch.object(fc, 'credential') as credential, patch.object(fc, 'execute_plan') as execute:
            with self.assertRaises(UseCaseError):
                fc.run(self.args('--live', '--max-credits', '0'))
            credential.assert_not_called()
            execute.assert_not_called()

    def test_malformed_live_response_saves_nothing(self):
        broken = [payload(strikes=[]), payload(symbol='QQQ'), {'data': {'symbols': []}},
                  payload(strikes=[{'strike': 500, 'value': float('nan'), 'nodeType': 'king'}])]
        for response in broken:
            with self.subTest(response=str(response)[:80]):
                with self.assertRaises(UseCaseError):
                    self.run_cli('--live', response=response)

    def test_invalid_symbol_is_refused_offline(self):
        with self.assertRaises(UseCaseError):
            self.run_cli('--symbol', 'SPY,QQQ')


class FirstChartRendering(unittest.TestCase):
    def view(self, data=None):
        return fc.extract(data or payload(), 'SPY')

    def test_positive_bars_extend_right_and_negative_left_of_zero(self):
        svg = fc.chart(self.view())
        zero = fc.ZERO_X
        bars = fc.bar_geometry(self.view())
        by_strike = {b['strike']: b for b in bars}
        self.assertGreaterEqual(by_strike[500]['x'], zero)
        self.assertLess(by_strike[495]['x'], zero)
        self.assertIn('<svg', svg)
        self.assertIn('spot 501.2', svg)
        self.assertIn('king', svg)

    def test_rows_are_ordered_high_strike_on_top(self):
        bars = fc.bar_geometry(self.view())
        self.assertEqual([b['strike'] for b in sorted(bars, key=lambda b: b['y'])], [505, 500, 495])

    def test_source_text_is_escaped(self):
        data = payload()
        data['data']['symbols'][0]['asOf'] = '<script>x</script>'
        with self.assertRaises(UseCaseError):
            fc.extract(data, 'SPY')  # asOf must be a timestamp
        data = payload(strikes=[{'strike': 500, 'value': 1.0, 'nodeType': '<b>'}])
        self.assertNotIn('<b>', fc.chart(fc.extract(data, 'SPY')))

    def test_nodes_without_finite_values_are_counted_as_gaps(self):
        data = payload(strikes=[{'strike': 500, 'value': 1.0, 'nodeType': 'king'},
                                {'strike': 505, 'value': None, 'nodeType': 'normal'}])
        view = fc.extract(data, 'SPY')
        self.assertEqual(view['gaps'], 1)
        self.assertIn('1 strike without a usable value', fc.report(view, Path('reports/x.svg')))

    def test_bundled_fixture_is_marked_synthetic(self):
        fixture = fc.load_fixture()
        self.assertTrue(fixture['synthetic'])
        self.assertEqual(fc.extract(copy.deepcopy(fixture), 'SPY')['symbol'], 'SPY')


if __name__ == '__main__':
    unittest.main()
