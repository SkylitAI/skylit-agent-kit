import contextlib
import io
import json
import os
import re
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.parse import unquote

from skylit_agent_kit.__main__ import main


class AccountWelcomeTests(unittest.TestCase):
    def run_account(self, *options, payload=None, error=None):
        out, err = io.StringIO(), io.StringIO()
        body = json.dumps(payload).encode()
        with patch.dict(os.environ, {'SKYLIT_API_KEY': 'test-placeholder'}), \
                patch('sys.argv', ['kit', 'account', *options]), \
                patch('skylit_agent_kit.account.build_opener') as opener, \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            opener.return_value.open.return_value = io.BytesIO(body)
            opener.return_value.open.side_effect = error
            status = main()
            requests = opener.return_value.open.call_count
        return status, out.getvalue(), err.getvalue(), requests

    def test_success_shows_brand_and_connection_without_account_details(self):
        account = {'data': {'status': 'active', 'apiEligible': True,
                            'customerId': 'private-customer', 'creditsBalance': 42}}
        status, out, err, requests = self.run_account('--welcome', payload=account)
        self.assertEqual((status, err, requests), (0, '', 1))
        self.assertIn('Connected to Skylit', out)
        self.assertIn('No market data was requested', out)
        self.assertNotIn('private-customer', out)
        self.assertNotIn('creditsBalance', out)
        self.assertNotIn('test-placeholder', out)
        banner = re.search(r'!\[Skylit\]\(([^)]+)\)', out)
        self.assertIsNotNone(banner)
        path = Path(unquote(banner.group(1)))
        self.assertTrue(path.is_absolute())
        self.assertEqual(path.read_bytes()[:8], b'\x89PNG\r\n\x1a\n')

    def test_suspended_ineligible_or_malformed_account_never_celebrates(self):
        for data in ({'status': 'suspended', 'apiEligible': True},
                     {'status': 'active', 'apiEligible': False},
                     {'status': 'active', 'apiEligible': 'true'},
                     {'status': 'active'}, None):
            with self.subTest(data=data):
                status, out, err, requests = self.run_account('--welcome', payload={'data': data})
                self.assertEqual((status, out, requests), (1, '', 1))
                self.assertIn('active account with API access', err)

    def test_failed_authentication_never_shows_a_success_banner(self):
        error = HTTPError('https://api.skylit.ai/v1/account', 401, 'private', {}, None)
        status, out, err, requests = self.run_account('--welcome', error=error)
        self.assertEqual((status, out, requests), (1, '', 1))
        self.assertIn('HTTP 401', err)
        self.assertNotIn('private', err)

    def test_welcome_uses_existing_hidden_prompt_when_environment_key_missing(self):
        with patch.dict(os.environ, {'SKYLIT_API_KEY': ''}), \
                patch('sys.argv', ['kit', 'account', '--welcome']), \
                patch('sys.stdin.isatty', return_value=True), \
                patch('getpass.getpass', return_value='test-placeholder'), \
                patch('skylit_agent_kit.account.build_opener') as opener, \
                contextlib.redirect_stdout(io.StringIO()) as out:
            opener.return_value.open.return_value = io.BytesIO(
                b'{"data":{"status":"active","apiEligible":true}}')
            self.assertEqual(main(), 0)
        self.assertIn('Connected to Skylit', out.getvalue())

    def test_plain_account_keeps_its_json_output(self):
        account = {'data': {'status': 'active', 'apiEligible': True}}
        status, out, err, requests = self.run_account(payload=account)
        self.assertEqual((status, err, requests), (0, '', 1))
        self.assertEqual(json.loads(out), account)

    def test_offline_first_run_does_not_claim_a_connection(self):
        with patch('sys.argv', ['kit', 'watchlist', '--dry-run']), \
                patch('skylit_agent_kit.account.build_opener', side_effect=AssertionError('network')), \
                contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(main(), 0)
        self.assertNotIn('Connected to Skylit', out.getvalue())
        self.assertNotIn('![Skylit]', out.getvalue())


if __name__ == '__main__':
    unittest.main()
