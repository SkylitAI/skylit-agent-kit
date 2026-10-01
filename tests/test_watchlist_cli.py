import contextlib
import io
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from skylit_agent_kit.__main__ import main
from skylit_agent_kit.watchlist import WatchlistError
from skylit_agent_kit.watchlist_cli import credential, output_path, save_private

class WatchlistCliTests(unittest.TestCase):
    def test_dry_run_never_reads_credentials_or_connects(self):
        with patch('sys.argv', ['kit', 'watchlist', '--dry-run']), \
             patch('skylit_agent_kit.watchlist_cli.credential', side_effect=AssertionError('No credentials')), \
             patch('skylit_agent_kit.watchlist_cli.execute_live', side_effect=AssertionError('No network')), \
             contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(main(), 0)
        self.assertIn('12 requests', out.getvalue())
        self.assertIn('10 documented credits', out.getvalue())

    def test_invalid_args_fail_before_credentials(self):
        for options in (['--max-seconds','nan'], ['--max-seconds','-1'], ['--max-credits','-1'], ['--max-requests','-1'], ['--flow-limit','0'], ['--date','yesterday']):
            with self.subTest(options=options), patch('sys.argv', ['kit','watchlist','--live',*options]), \
                 patch('skylit_agent_kit.watchlist_cli.credential', side_effect=AssertionError('No credentials')), \
                 contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(main(), 1)

    def test_noninteractive_missing_secret_stops_without_echo(self):
        with patch.dict(os.environ, {}, clear=True), patch('sys.stdin.isatty', return_value=False):
            with self.assertRaisesRegex(WatchlistError, 'hidden key prompt'): credential()

    def test_output_cannot_escape_ignored_reports(self):
        with self.assertRaises(WatchlistError): output_path('/private/tmp/escaped-report.md')
        with self.assertRaises(WatchlistError): output_path('README.md')

    def test_saved_files_are_private_and_never_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'report.md'
            save_private(path, 'sample')
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            with self.assertRaises(FileExistsError): save_private(path, 'replacement')
            self.assertEqual(path.read_text(), 'sample')

    def test_cancelled_hidden_prompt_exits_without_traceback(self):
        with patch('sys.argv', ['kit', 'watchlist', '--live']), \
             patch('skylit_agent_kit.watchlist_cli.credential', side_effect=KeyboardInterrupt), \
             contextlib.redirect_stderr(io.StringIO()) as out:
            self.assertEqual(main(), 130)
        self.assertIn('Cancelled', out.getvalue())
        self.assertNotIn('Traceback', out.getvalue())
