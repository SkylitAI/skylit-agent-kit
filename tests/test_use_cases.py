import argparse
import contextlib
import copy
import io
import json
import tempfile
import unittest
from pathlib import Path
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

    def test_node_live_budget_stops_before_credentials(self):
        with patch.object(u,'credential',side_effect=AssertionError('key read')):
            with self.assertRaisesRegex(ValueError,'25 credits'):
                u.run(self.args('node-tracker','--strikes','100,105','--live','--symbol','SPY','--from',START,'--to',END,'--expirations','2026-10-02'))

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
