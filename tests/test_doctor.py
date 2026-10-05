import contextlib
import io
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from skylit_agent_kit import doctor
from skylit_agent_kit.__main__ import main
from skylit_agent_kit.keystore import KeystoreError

ALLOW = doctor.AGENT_ALLOW_RULE


def git(*outputs):
    """subprocess.run stand-in answering git calls in order; None = git missing."""
    answers = list(outputs)

    def run(arguments, **_):
        answer = answers.pop(0)
        if answer is None:
            raise FileNotFoundError('git')
        code, text = answer
        return subprocess.CompletedProcess(arguments, code, stdout=text, stderr='')
    return run


def healthy_git():
    return git((0, 'git version 2.50.1\n'), (0, 'main\n'), (0, 'c14454d\n'))


class DoctorChecks(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: __import__('shutil').rmtree(self.root))
        (self.root / '.claude').mkdir()
        (self.root / '.claude' / 'settings.json').write_text('{"permissions": {"allow": ["%s"]}}' % ALLOW)

    def checks(self, run=None, version=(3, 12, 6), env_key='', stored='stored-placeholder'):
        load = patch('skylit_agent_kit.keystore.load',
                     side_effect=stored if isinstance(stored, Exception) else None,
                     return_value=None if isinstance(stored, Exception) else stored)
        with patch('subprocess.run', side_effect=run or healthy_git()), \
                patch('skylit_agent_kit.doctor.python_version', return_value=version), \
                patch('skylit_agent_kit.keystore.describe', return_value='macOS Keychain'), \
                patch.dict(os.environ, {'SKYLIT_API_KEY': env_key}), load:
            return {check.label: check for check in doctor.run_checks(self.root)}

    def test_healthy_setup_passes_every_check(self):
        checks = self.checks()
        self.assertEqual({c.status for c in checks.values()}, {'ok'})
        self.assertIn('3.12.6', checks['Python'].detail)
        self.assertIn('2.50.1', checks['Git'].detail)
        self.assertIn('main @ c14454d', checks['Repository'].detail)
        self.assertIn('macOS Keychain', checks['Skylit key'].detail)

    def test_old_python_fails(self):
        check = self.checks(version=(3, 9, 18))['Python']
        self.assertEqual(check.status, 'fail')
        self.assertIn('3.11', check.next_step)

    def test_missing_git_fails_and_repository_is_unknown(self):
        checks = self.checks(run=git(None, None, None))
        self.assertEqual(checks['Git'].status, 'fail')
        self.assertEqual(checks['Repository'].status, 'warn')

    def test_not_a_checkout_warns(self):
        checks = self.checks(run=git((0, 'git version 2.50.1\n'), (128, ''), (128, '')))
        self.assertEqual(checks['Repository'].status, 'warn')

    def test_missing_agent_allow_rule_warns(self):
        (self.root / '.claude' / 'settings.json').unlink()
        check = self.checks()['Agent access']
        self.assertEqual(check.status, 'warn')
        self.assertIn('approve', check.next_step)

    def test_symlinked_reports_folder_fails(self):
        target = Path(tempfile.mkdtemp())
        self.addCleanup(target.rmdir)
        (self.root / 'reports').symlink_to(target)
        self.assertEqual(self.checks()['Reports folder'].status, 'fail')

    def test_environment_key_is_reported_without_its_value(self):
        check = self.checks(env_key='env-placeholder', stored=None)['Skylit key']
        self.assertEqual(check.status, 'ok')
        self.assertIn('SKYLIT_API_KEY', check.detail)
        self.assertNotIn('env-placeholder', check.detail)

    def test_no_key_warns_and_points_to_login(self):
        check = self.checks(stored=None)['Skylit key']
        self.assertEqual(check.status, 'warn')
        self.assertIn('skylit_agent_kit login', check.next_step)

    def test_unreadable_stored_key_fails_with_keystore_guidance(self):
        check = self.checks(stored=KeystoreError('key file is readable by other users; run logout, then login again.'))['Skylit key']
        self.assertEqual(check.status, 'fail')
        self.assertIn('logout', check.next_step)


class DoctorCommand(unittest.TestCase):
    def run_cli(self, checks):
        out = io.StringIO()
        with patch('sys.argv', ['kit', 'doctor']), \
                patch('skylit_agent_kit.doctor.run_checks', return_value=checks), \
                patch('skylit_agent_kit.account.build_opener', side_effect=AssertionError('network')), \
                contextlib.redirect_stdout(out):
            status = main()
        return status, out.getvalue()

    def test_ready_setup_exits_zero_and_points_to_the_welcome_check(self):
        status, out = self.run_cli([doctor.Check('ok', 'Python', '3.12.6')])
        self.assertEqual(status, 0)
        self.assertIn('✓ Python', out)
        self.assertIn('account --welcome', out)

    def test_warning_exits_zero_and_names_the_first_next_step(self):
        status, out = self.run_cli([doctor.Check('ok', 'Python', '3.12.6'),
                                    doctor.Check('warn', 'Skylit key', 'not stored yet', 'run login'),
                                    doctor.Check('warn', 'Agent access', 'no rule', 'approve once')])
        self.assertEqual(status, 0)
        self.assertIn('• Skylit key', out)
        self.assertIn('Next: run login', out)
        self.assertNotIn('Next: approve once', out)

    def test_failure_exits_one_and_its_step_comes_before_warnings(self):
        status, out = self.run_cli([doctor.Check('warn', 'Skylit key', 'not stored yet', 'run login'),
                                    doctor.Check('fail', 'Python', '3.9.18', 'install 3.11+')])
        self.assertEqual(status, 1)
        self.assertIn('✗ Python', out)
        self.assertIn('Next: install 3.11+', out)


if __name__ == '__main__':
    unittest.main()
