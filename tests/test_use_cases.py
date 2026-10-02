import argparse
import contextlib
import copy
import io
import json
import tempfile
import unittest
from pathlib import Path
from urllib.parse import unquote
from unittest.mock import patch
from skylit_agent_kit import use_cases as u
from skylit_agent_kit.node_tracker import chart, track
from skylit_agent_kit.recipe_reports import render_recipe

START, END = '2026-09-30T14:00:00Z', '2026-09-30T14:06:00Z'


class UseCaseTests(unittest.TestCase):
    def args(self, *args):
        p=argparse.ArgumentParser(); u.add_parser(p.add_subparsers(dest='command'))
        return p.parse_args(['use-case', *args])

    def test_each_offline_workflow_saves_useful_result_without_credentials(self):
        for name in u.NAMES:
            writes=[]
            with patch.object(u, 'output_path', side_effect=lambda x:Path(x)), patch.object(u, 'save_private', side_effect=lambda p,c:writes.append((p,c))), patch.object(u,'credential',side_effect=AssertionError('offline credential read')), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(u.run(self.args(name)),0)
            self.assertTrue(any('SYNTHETIC / FICTIONAL' in c for p,c in writes))
            self.assertIn('Request plan',writes[-1][1]); self.assertIn('Build it yourself',writes[-1][1])
            self.assertIn('|',writes[-1][1])

    def test_nested_reports_link_to_their_chart_and_tutorial(self):
        import re
        import socket
        root = Path(__file__).resolve().parents[1]
        reports = root / 'reports'
        reports.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=reports) as directory:
            destination = Path(directory) / 'nested' / 'my chart (1) #2.md'
            with patch.object(u, 'credential', side_effect=AssertionError('No key')), \
                 patch.object(socket, 'socket', side_effect=AssertionError('No network')), \
                 contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(u.run(self.args('node-tracker', '--output', str(destination))), 0)
            body = destination.read_text(encoding='utf-8')
            chart_link = re.search(r'!\[Signed exposure over actual time\]\(([^)]+)\)', body).group(1)
            tutorial_link = re.search(r'\[the use-case tutorial\]\(([^)]+)\)', body).group(1)
            self.assertNotIn(' ', chart_link)
            self.assertNotIn('#', chart_link)
            self.assertEqual((destination.parent / unquote(chart_link)).resolve(), destination.with_suffix('.svg'))
            self.assertEqual((destination.parent / unquote(tutorial_link)).resolve(), root / 'docs/use-cases.md')

    def test_node_live_budget_stops_before_credentials(self):
        with patch.object(u,'credential',side_effect=AssertionError('key read')):
            with self.assertRaisesRegex(ValueError,'25 credits'):
                u.run(self.args('node-tracker','--strikes','100,105','--live','--symbol','SPY','--from',START,'--to',END,'--expirations','2026-10-02'))

    def test_internal_parent_symlink_prints_canonical_report_with_working_tutorial(self):
        import re
        root = Path(__file__).resolve().parents[1]
        reports = root / 'reports'
        reports.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=reports) as directory:
            folder = Path(directory)
            actual = folder / 'actual' / 'deep'
            actual.mkdir(parents=True)
            alias = folder / 'alias'
            try:
                alias.symlink_to(actual, target_is_directory=True)
            except OSError:
                self.skipTest('Directory symlinks are unavailable on this host')
            with contextlib.redirect_stdout(io.StringIO()) as output:
                self.assertEqual(u.run(self.args('node-tracker', '--output', str(alias / 'report.md'))), 0)
            canonical = actual / 'report.md'
            body = canonical.read_text(encoding='utf-8')
            link = re.search(r'\[the use-case tutorial\]\(([^)]+)\)', body).group(1)
            self.assertEqual((actual / unquote(link)).resolve(), root / 'docs/use-cases.md')
            self.assertIn(f'Saved report: {canonical}', output.getvalue())

    def test_bundled_demo_explains_its_fixed_symbol_and_metric(self):
        for name in u.NAMES:
            with self.subTest(recipe=name), self.assertRaisesRegex(ValueError, 'fictional demo uses SPY.*--input'):
                u.run(self.args(name, '--symbol', 'QQQ'))
        for name in ('node-tracker', 'price-levels'):
            with self.subTest(recipe=name), self.assertRaisesRegex(ValueError, 'fictional demo uses gamma.*--input'):
                u.run(self.args(name, '--metric', 'vanna'))

    def test_dry_run_can_plan_a_different_symbol_and_metric(self):
        with patch.object(u, 'load_json', side_effect=AssertionError('No fixture needed')), \
             patch.object(u, 'credential', side_effect=AssertionError('No key')), \
             contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(u.run(self.args('node-tracker', '--dry-run', '--symbol', 'QQQ', '--metric', 'vanna')), 0)
        self.assertIn('QQQ', output.getvalue())
        self.assertIn('vanna', output.getvalue())

    def test_saved_input_is_not_mislabeled_synthetic(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'saved.json'; path.write_text((u.FIXTURES/'node-tracker.json').read_text()); writes=[]
            with patch.object(u,'save_private',side_effect=lambda p,c:writes.append(c)), patch.object(u,'output_path',side_effect=lambda x:Path(x)), contextlib.redirect_stdout(io.StringIO()):
                u.run(self.args('node-tracker','--strikes','100,105','--input',str(path),'--symbol','SPY','--from',START,'--to',END,'--expirations','2026-10-02'))
            self.assertNotIn('SYNTHETIC',writes[-1]); self.assertIn('User-supplied saved',writes[-1])

    def test_saved_input_requires_explicit_identity_and_window(self):
        with self.assertRaises(ValueError): u.run(self.args('price-levels','--input',str(u.FIXTURES/'price-levels.json')))

    def test_node_window_limit_and_timezone(self):
        with self.assertRaises(ValueError): u.validate_window(START,'2026-09-30T14:16:00Z','node-tracker',False)
        with self.assertRaises(ValueError): u.validate_window(START,'2026-09-30T14:06:00','node-tracker',False)

    def test_saved_response_wrong_coverage_rejected(self):
        with self.assertRaisesRegex(ValueError,'differs'):
            u.run(self.args('node-tracker','--strikes','100,105','--input',str(u.FIXTURES/'node-tracker.json'),'--symbol','SPY','--from',START,'--to','2026-09-30T14:07:00Z','--expirations','2026-10-02'))

    def test_price_metric_and_window_must_match(self):
        data=u.load_json(u.FIXTURES/'price-levels.json')
        with self.assertRaises(ValueError): render_recipe('price-levels',data,'SPY','vanna',START,END)
        with self.assertRaises(ValueError): render_recipe('price-levels',data,'SPY','gamma','2026-09-30T14:01:00Z',END)

    def test_empty_price_history_keeps_missing_context(self):
        data=u.load_json(u.FIXTURES/'price-levels.json');data['atlas.getHistory']={'s':'no_data'}
        self.assertIn('No price observations',render_recipe('price-levels',data,'SPY','gamma',START,END))

    def test_large_finite_chart_has_no_infinite_coordinates(self):
        data=u.load_json(u.FIXTURES/'node-tracker.json'); s=data['data']['symbols'][0]
        s['frames']=s['frames'][:1];s['frames'][0]['values']=[1e308,-1e308]
        svg=chart(track(data,'SPY','gamma',[100,105],['2026-10-02']))
        self.assertNotIn('nan',svg.lower()); self.assertNotIn('inf',svg.lower())

    def test_load_json_size_and_constant_limits(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'bad.json';p.write_text('{"x":NaN}')
            with self.assertRaises(ValueError):u.load_json(p)
            p.write_bytes(b' '* (8*1024*1024+1))
            with self.assertRaisesRegex(ValueError,'8 MiB'):u.load_json(p)

    def test_live_recipe_executes_one_complete_batch_with_user_caps(self):
        from skylit_agent_kit import endpoint_demo
        data=u.load_json(u.FIXTURES/'volatility-context.json')
        with patch.object(endpoint_demo,'execute_plans',create=True,return_value=list(data.values())) as execute, patch.object(u,'credential',return_value='temporary-test-key'), patch.object(u,'output_path',side_effect=lambda x:Path(x)), patch.object(u,'save_private'), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(u.run(self.args('volatility-context','--live','--symbol','SPY','--max-credits','2','--max-requests','3')),0)
        self.assertEqual(execute.call_count,1)
        self.assertEqual(len(execute.call_args.args[0]),2)
        self.assertEqual(execute.call_args.kwargs,{'max_credits':2,'max_requests':3,'max_seconds':30})

    def test_live_node_uses_one_paid_plan_after_explicit_25_credit_budget(self):
        from skylit_agent_kit import endpoint_demo
        data=u.load_json(u.FIXTURES/'node-tracker.json')
        with patch.object(endpoint_demo,'execute_plans',create=True,return_value=[data]) as execute, patch.object(u,'credential',return_value='temporary-test-key'), patch.object(u,'output_path',side_effect=lambda x:Path(x)), patch.object(u,'save_private'), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(u.run(self.args('node-tracker','--live','--symbol','SPY','--strikes','100,105','--expirations','2026-10-02','--from',START,'--to',END,'--max-credits','25','--max-requests','2')),0)
        self.assertEqual(len(execute.call_args.args[0]),1)
        self.assertEqual(execute.call_args.kwargs['max_credits'],25)

    def test_invalid_live_strikes_stop_before_credential_or_network(self):
        with patch.object(u,'credential',side_effect=AssertionError('key read')):
            for extra in ([], ['--strikes','NaN'], ['--strikes','100,100']):
                with self.assertRaises(ValueError):
                    u.run(self.args('node-tracker','--live','--symbol','SPY','--from',START,'--to',END,'--expirations','2026-10-02','--max-credits','25',*extra))

    def test_source_text_cannot_insert_markdown_or_terminal_controls(self):
        from skylit_agent_kit.recipe_reports import cell
        self.assertEqual(cell('<script>|\x1b[31m'), '&lt;script&gt;&#124; [31m')

    def test_all_live_recipes_share_actual_runner_preflight(self):
        from skylit_agent_kit import endpoint_demo
        account={'data':{'status':'active','apiEligible':True,'creditsBalance':100,'unlimited':False,'limits':{'requestsPerMinute':100,'symbolsPerHeatmapCall':10}}}
        for name in u.NAMES:
            data=u.load_json(u.FIXTURES/(name+'.json'))
            payloads=[data] if name=='node-tracker' else list(data.values())
            argv=[name,'--live','--symbol','SPY','--strikes','100,105','--expirations','2026-10-02','--from',START,'--to',END,'--max-credits','25']
            with patch.object(endpoint_demo._Transport,'request',side_effect=[account,*payloads]) as request, patch.object(u,'credential',return_value='temporary-test-key'), patch.object(u,'output_path',side_effect=lambda x:Path(x)), patch.object(u,'save_private'), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(u.run(self.args(*argv)),0)
            self.assertEqual(request.call_count,len(payloads)+1)
            self.assertEqual(request.call_args_list[0].args[0]['id'],'heatseeker.getAccount')

    def test_delay_and_attribution_metadata_remain_visible(self):
        from skylit_agent_kit.node_tracker import report
        data=u.load_json(u.FIXTURES/'node-tracker.json')
        data['meta'].update(delayed=True,delayMinutes=15,attribution={'text':'Data: Skylit'})
        output=report(track(data,'SPY','gamma',[100],['2026-10-02']))
        self.assertIn('delayMinutes',output); self.assertIn('Data: Skylit',output)

    def test_cones_preserve_documented_anchor_and_horizon_fields(self):
        data=u.load_json(u.FIXTURES/'volatility-context.json')
        output=render_recipe('volatility-context',data,'SPY','gamma',START,END)
        self.assertIn('levels[0].priced_at',output);self.assertIn('horizons[0].em1_pct',output)
        self.assertIn('missing',output);self.assertIn('past-close anchor',output)

    def test_independent_fixtures_match_public_response_contracts(self):
        from skylit_agent_kit.catalog import get_endpoint, get_contract
        from skylit_agent_kit.contract_schema import valid
        for name in u.NAMES:
            data=u.load_json(u.FIXTURES/(name+'.json'))
            if name=='node-tracker': data={'heatseeker.getHistoricalRange':data}
            for identity, payload in data.items():
                entry=get_endpoint(identity)
                self.assertTrue(valid(payload,entry['schema'],get_contract(entry['service'])),identity)

    def test_all_recipe_reports_keep_attribution_without_rendering_source_links(self):
        for name in ('price-levels', 'flow-investigator', 'volatility-context'):
            data = u.load_json(u.FIXTURES / (name + '.json'))
            first = next(iter(data.values()))
            first.setdefault('meta', {})['attribution'] = {'text': 'Powered by Skylit', 'url': 'javascript:alert(1)'}
            first['disclaimer'] = '<img src=x onerror=alert(1)> source warning'
            text = render_recipe(name, data, 'SPY', 'gamma', START, END)
            self.assertIn('[Data: Skylit](https://skylit.ai/)', text)
            self.assertIn('Powered by Skylit', text)
            self.assertIn('source warning', text)
            self.assertNotIn('<img', text)
