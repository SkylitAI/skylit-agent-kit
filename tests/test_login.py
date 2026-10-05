import contextlib
import io
import os
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from skylit_agent_kit import keystore
from skylit_agent_kit.__main__ import main
from skylit_agent_kit.watchlist import WatchlistError
from skylit_agent_kit.watchlist_cli import credential


def completed(code=0, stdout=''):
    return subprocess.CompletedProcess([], code, stdout=stdout, stderr='')


class FileStore(unittest.TestCase):
    def setUp(self):
        self.home = tempfile.TemporaryDirectory()
        self.addCleanup(self.home.cleanup)
        for active in (patch.dict(os.environ, {'XDG_CONFIG_HOME': self.home.name}),
                       patch('skylit_agent_kit.keystore.uses_keychain', return_value=False)):
            active.start()
            self.addCleanup(active.stop)

    def test_saved_key_round_trips_with_owner_only_permissions(self):
        where = keystore.save('test-placeholder')
        path = Path(self.home.name) / 'skylit-agent-kit' / 'key'
        self.assertIn(str(path), where)
        self.assertEqual(keystore.load(), 'test-placeholder')
        self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(path.parent.stat().st_mode), 0o700)

    def test_saving_again_replaces_the_previous_key(self):
        keystore.save('first-placeholder')
        keystore.save('second-placeholder')
        self.assertEqual(keystore.load(), 'second-placeholder')

    def test_nothing_stored_loads_none(self):
        self.assertIsNone(keystore.load())

    def test_key_readable_by_others_is_refused(self):
        keystore.save('test-placeholder')
        path = Path(self.home.name) / 'skylit-agent-kit' / 'key'
        path.chmod(0o644)
        with self.assertRaises(keystore.KeystoreError) as caught:
            keystore.load()
        self.assertNotIn('test-placeholder', str(caught.exception))

    def test_delete_reports_whether_a_key_was_removed(self):
        keystore.save('test-placeholder')
        self.assertTrue(keystore.delete())
        self.assertIsNone(keystore.load())
        self.assertFalse(keystore.delete())

    def test_invalid_key_is_never_written(self):
        for bad in ('', 'has space', 'line\nbreak', 'x' * 4097):
            with self.subTest(bad=bad), self.assertRaises(keystore.KeystoreError):
                keystore.save(bad)
        self.assertIsNone(keystore.load())


class KeychainStore(unittest.TestCase):
    def setUp(self):
        active = patch('skylit_agent_kit.keystore.uses_keychain', return_value=True)
        active.start()
        self.addCleanup(active.stop)

    def test_key_reaches_keychain_through_stdin_never_arguments(self):
        with patch('subprocess.run', return_value=completed()) as run:
            where = keystore.save('we"ird\\key')
        self.assertIn('Keychain', where)
        arguments, options = run.call_args
        self.assertNotIn('ird', ' '.join(arguments[0]))
        self.assertIn('-w "we\\"ird\\\\key"', options['input'])

    def test_missing_keychain_item_loads_none(self):
        with patch('subprocess.run', return_value=completed(44)):
            self.assertIsNone(keystore.load())

    def test_keychain_item_loads_without_trailing_newline(self):
        with patch('subprocess.run', return_value=completed(0, 'test-placeholder\n')):
            self.assertEqual(keystore.load(), 'test-placeholder')

    def test_keychain_failure_is_reported_without_the_key(self):
        with patch('subprocess.run', return_value=completed(1)), \
                self.assertRaises(keystore.KeystoreError) as caught:
            keystore.save('test-placeholder')
        self.assertNotIn('test-placeholder', str(caught.exception))


class CredentialOrder(unittest.TestCase):
    def test_environment_key_wins_over_stored_key(self):
        with patch.dict(os.environ, {'SKYLIT_API_KEY': 'env-placeholder'}), \
                patch('skylit_agent_kit.keystore.load', return_value='stored-placeholder'):
            self.assertEqual(credential(), 'env-placeholder')

    def test_stored_key_is_used_without_a_terminal(self):
        with patch.dict(os.environ, {'SKYLIT_API_KEY': ''}), \
                patch('sys.stdin.isatty', return_value=False), \
                patch('skylit_agent_kit.keystore.load', return_value='stored-placeholder'):
            self.assertEqual(credential(), 'stored-placeholder')

    def test_no_key_and_no_terminal_points_to_login(self):
        with patch.dict(os.environ, {'SKYLIT_API_KEY': ''}), \
                patch('sys.stdin.isatty', return_value=False), \
                patch('skylit_agent_kit.keystore.load', return_value=None), \
                self.assertRaises(WatchlistError) as caught:
            credential()
        self.assertIn('skylit_agent_kit login', str(caught.exception))


class LoginCommand(unittest.TestCase):
    def run_cli(self, *argv, tty=True, typed='test-placeholder'):
        out, err = io.StringIO(), io.StringIO()
        with patch('sys.argv', ['kit', *argv]), \
                patch('sys.stdin.isatty', return_value=tty), \
                patch('getpass.getpass', return_value=typed) as prompt, \
                patch('skylit_agent_kit.keystore.save', return_value='a test store') as save, \
                patch('skylit_agent_kit.keystore.delete', return_value=True) as delete, \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            status = main()
        return status, out.getvalue(), err.getvalue(), prompt, save, delete

    def test_login_stores_hidden_input_and_never_prints_it(self):
        status, out, err, prompt, save, _ = self.run_cli('login')
        self.assertEqual((status, err), (0, ''))
        prompt.assert_called_once()
        save.assert_called_once_with('test-placeholder')
        self.assertIn('a test store', out)
        self.assertIn('account --welcome', out)
        self.assertNotIn('test-placeholder', out)

    def test_login_without_a_terminal_refuses_and_stores_nothing(self):
        status, out, err, prompt, save, _ = self.run_cli('login', tty=False)
        self.assertEqual((status, out), (1, ''))
        self.assertIn('terminal', err)
        prompt.assert_not_called()
        save.assert_not_called()

    def test_login_with_empty_input_stores_nothing(self):
        status, _, err, _, save, _ = self.run_cli('login', typed='')
        self.assertEqual(status, 1)
        save.assert_not_called()
        self.assertIn('No key entered', err)

    def test_logout_removes_the_stored_key(self):
        status, out, err, _, _, delete = self.run_cli('logout', tty=False)
        self.assertEqual((status, err), (0, ''))
        delete.assert_called_once_with()
        self.assertIn('Removed', out)


if __name__ == '__main__':
    unittest.main()
