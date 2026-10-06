import contextlib
import html
import io
import json
import os
import socket
import unittest
from unittest.mock import patch
from pathlib import Path
from urllib.error import HTTPError

from skylit_agent_kit import doctor, journey
from skylit_agent_kit.__main__ import main
from skylit_agent_kit.endpoint_demo import plan_request
from skylit_agent_kit.attribution import safe_metadata
from skylit_agent_kit.heatmap_summary import summarize


def run_cli(*argv):
    out, err = io.StringIO(), io.StringIO()
    with patch('sys.argv', ['python3 -m skylit_agent_kit', *argv]), \
            contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            status = main()
        except SystemExit as exit_:
            status = exit_.code
    return status, out.getvalue(), err.getvalue()


class SafeMetadataTests(unittest.TestCase):
    def test_escaped_metadata_decodes_back_to_the_original_json(self):
        value = {'mode': 'historical', 'attribution': {'text': 'Data: Skylit', 'url': 'https://skylit.ai/#a'}}
        text = safe_metadata(value)
        self.assertEqual(html.unescape(text), json.dumps(value, ensure_ascii=True))
        self.assertNotIn('&&', text)

    def test_markdown_delimiters_stay_inert(self):
        text = safe_metadata({'x': '[a](javascript:1) `b` *c* | <d>'})
        for char in '[]()`*|<>':
            self.assertNotIn(char, text)


class CommandEntryTests(unittest.TestCase):
    def test_bare_command_points_to_the_first_steps(self):
        status, out, _ = run_cli()
        self.assertEqual(status, 0)
        self.assertLess(out.index('doctor'), out.index('login'))
        self.assertLess(out.index('login'), out.index('account --welcome'))
        self.assertIn('python3 -m skylit_agent_kit', out)

    def test_help_uses_the_real_command_name_and_lists_first_steps_first(self):
        with patch('sys.argv', ['__main__.py', '--help']), \
                contextlib.redirect_stdout(io.StringIO()) as out, self.assertRaises(SystemExit):
            main()
        text = out.getvalue()
        self.assertIn('usage: python3 -m skylit_agent_kit', text)
        self.assertNotIn('__main__.py', text)
        commands = text[text.index('{') + 1:text.index('}')].split(',')
        self.assertEqual(commands[:3], ['doctor', 'login', 'account'])


class WelcomeGuidanceTests(unittest.TestCase):
    def welcome(self, payload=None, error=None):
        with patch.dict(os.environ, {'SKYLIT_API_KEY': 'test-placeholder'}), \
                patch('skylit_agent_kit.account.build_opener') as opener:
            opener.return_value.open.return_value = io.BytesIO(json.dumps(payload).encode())
            opener.return_value.open.side_effect = error
            return run_cli('account', '--welcome')

    def test_success_names_the_one_credit_next_command(self):
        status, out, _ = self.welcome({'data': {'status': 'active', 'apiEligible': True}})
        self.assertEqual(status, 0)
        self.assertIn('endpoint heatseeker.getHeatmap --param symbols=SPY --param metric=gamma --live', out)
        self.assertIn('1 credit', out)

    def test_rejected_key_points_to_a_new_key_and_login(self):
        for code in (401, 403):
            with self.subTest(code=code):
                error = HTTPError('https://api.skylit.ai/v1/account', code, 'private', {}, None)
                status, out, err = self.welcome(error=error)
                self.assertEqual((status, out), (1, ''))
                self.assertIn(f'HTTP {code}', err)
                self.assertIn('https://app.skylit.ai/developer', err)
                self.assertIn('python3 -m skylit_agent_kit login', err)
                self.assertNotIn('private', err)

    def test_missing_access_points_to_access_and_terms(self):
        status, _, err = self.welcome({'data': {'status': 'active', 'apiEligible': False}})
        self.assertEqual(status, 1)
        self.assertIn('active account with API access', err)
        self.assertIn('API Terms', err)
        self.assertIn('https://app.skylit.ai/developer', err)


BOARD = {
    'data': {'symbols': [{
        'symbol': 'SPY', 'spot': 101.2, 'asOf': '2026-09-30T14:00:00Z',
        'strikes': [{'strike': s, 'value': v} for s, v in
                    [(90, 1), (95, -2), (99, 3), (100, -40), (101, 7), (102, 12), (103, 5), (110, 9)]],
    }]},
    'meta': {'attribution': {'text': 'Data: Skylit'}},
}


class HeatmapSummaryTests(unittest.TestCase):
    def test_lists_strikes_nearest_spot_with_timestamp_and_credit(self):
        text = summarize(BOARD)
        self.assertIn('SPY', text)
        self.assertIn('spot 101.2', text)
        self.assertIn('2026-09-30T14:00:00Z', text)
        self.assertIn('Data: Skylit', text)
        strikes = [line.split()[0] for line in text.splitlines() if line.strip()[:1].isdigit()]
        self.assertEqual(strikes, ['99', '100', '101', '102', '103'])
        self.assertNotIn('110', strikes)

    def test_missing_fields_are_labelled_not_invented(self):
        board = {'data': {'symbols': [{'symbol': 'SPY', 'strikes': [{'strike': 100}]}]}}
        text = summarize(board)
        self.assertIn('spot unavailable', text)
        self.assertIn('as of unavailable', text)
        self.assertIn('unavailable', text.splitlines()[-2])

    def test_unexpected_shape_gives_no_summary(self):
        for payload in ({}, {'data': None}, {'data': {'symbols': 'x'}}, {'data': {'symbols': [None]}}):
            with self.subTest(payload=payload):
                self.assertEqual(summarize(payload), '')

    def test_symbol_text_cannot_inject_terminal_control(self):
        board = json.loads(json.dumps(BOARD))
        board['data']['symbols'][0]['symbol'] = 'SPY\x1b[2J'
        self.assertNotIn('\x1b', summarize(board))

    def test_live_heatmap_prints_summary_on_stderr_and_keeps_json_on_stdout(self):
        args = ('endpoint', 'heatseeker.getHeatmap', '--param', 'symbols=SPY', '--param', 'metric=gamma', '--live')
        with patch('skylit_agent_kit.endpoint_cli.credential', return_value='test-placeholder'), \
                patch('skylit_agent_kit.endpoint_cli.execute_plan', return_value=BOARD), \
                patch.object(socket, 'socket', side_effect=AssertionError('No network')):
            status, out, err = run_cli(*args)
        self.assertEqual(status, 0)
        self.assertEqual(json.loads(out)['response'], BOARD)
        self.assertIn('spot 101.2', err)
        self.assertIn('Data: Skylit', err)

    def test_other_live_endpoints_print_no_summary(self):
        args = ('endpoint', 'heatseeker.getAccount', '--live')
        with patch('skylit_agent_kit.endpoint_cli.credential', return_value='test-placeholder'), \
                patch('skylit_agent_kit.endpoint_cli.execute_plan', return_value=BOARD):
            status, _, err = run_cli(*args)
        self.assertEqual(status, 0)
        self.assertNotIn('nearest spot', err)



ROOT = Path(__file__).resolve().parents[1]


class JourneyTests(unittest.TestCase):
    """What users are told to expect must be exactly what the kit does."""

    def test_five_steps_in_order_with_cost_only_at_the_last(self):
        self.assertEqual([s.title for s in journey.STEPS],
                         ['Check setup', 'Create a key', 'Store the key', 'Prove the connection', 'First live data'])
        self.assertEqual([s.credits for s in journey.STEPS], [0, 0, 0, 0, 1])
        self.assertEqual([s.who for s in journey.STEPS][1:3], ['You', 'You'])

    def test_first_live_step_matches_the_endpoint_price(self):
        plan = plan_request('heatseeker.getHeatmap', {'symbols': 'SPY', 'metric': 'gamma'})
        self.assertEqual(plan['credits'], journey.STEPS[-1].credits)
        self.assertIn(journey.FIRST_LIVE, journey.render_welcome_next())

    def test_readme_block_is_generated_from_the_steps(self):
        readme = (ROOT / 'README.md').read_text(encoding='utf-8')
        self.assertIn(journey.render_markdown(), readme)
        self.assertLess(readme.index('## What to expect'), readme.index('## Prefer the terminal?'))

    def test_start_here_table_lists_the_same_steps_in_order(self):
        text = (ROOT / 'docs' / 'start-here.md').read_text(encoding='utf-8')
        rows = [line for line in text.splitlines() if line.startswith('| ') and line[2:3].isdigit()]
        titles = [row.split('|')[1].strip().split('. ', 1)[1] for row in rows[:5]]
        self.assertEqual(titles, [s.title for s in journey.STEPS])

    def test_progress_marks_done_current_and_upcoming(self):
        lines = journey.render_progress(current=4).splitlines()[1:]
        self.assertEqual([line[:1] for line in lines], ['✓', '✓', '✓', '→', ' '])

    def test_doctor_shows_progress_from_its_checks(self):
        ok = [doctor.Check('ok', 'Python', '3.12.6')]
        cases = [
            (ok + [doctor.Check('ok', 'Skylit key', 'stored')], 4),
            (ok + [doctor.Check('warn', 'Skylit key', 'not stored yet', 'create')], 2),
            ([doctor.Check('fail', 'Python', '3.9', 'install')], 1),
        ]
        for checks, current in cases:
            with self.subTest(current=current):
                with patch('skylit_agent_kit.doctor.run_checks', return_value=checks):
                    _, out, _ = run_cli('doctor')
                self.assertIn(journey.render_progress(current), out)
                self.assertLess(out.index('Your path'), out.index('Next:'))

    def test_bare_command_shows_the_overview(self):
        _, out, _ = run_cli()
        self.assertIn(journey.render_text(), out)


if __name__ == '__main__':
    unittest.main()
