import io
import unittest
from http.client import IncompleteRead
from urllib.error import HTTPError, URLError
from unittest.mock import patch

from skylit_agent_kit.account import AccountError, NoRedirect, read_account


class AccountTests(unittest.TestCase):
    @patch("skylit_agent_kit.account.build_opener")
    def test_reads_only_the_account_endpoint(self, factory):
        factory.return_value.open.return_value = io.BytesIO(b'{"credits": 42}')
        self.assertEqual(read_account("test-placeholder"), {"credits": 42})
        request = factory.return_value.open.call_args.args[0]
        self.assertEqual(request.full_url, "https://api.skylit.ai/v1/account")
        self.assertEqual(request.get_method(), "GET")
        self.assertEqual(factory.return_value.open.call_count, 1)

    @patch("skylit_agent_kit.account.build_opener")
    def test_missing_or_invalid_key_never_sends_a_request(self, factory):
        for value in ("", "key\nheader", "key with spaces", "é", "x" * 4097):
            with self.subTest(value=value[:20]), self.assertRaises(AccountError):
                read_account(value)
        factory.assert_not_called()

    @patch("skylit_agent_kit.account.build_opener")
    def test_http_errors_stop_without_retry_or_sensitive_output(self, factory):
        for code in (301, 401, 402, 403, 429, 503):
            factory.return_value.open.reset_mock()
            factory.return_value.open.side_effect = HTTPError("https://api.skylit.ai", code, "private-body", {}, None)
            with self.subTest(code=code), self.assertRaises(AccountError) as context:
                read_account("test-placeholder")
            self.assertNotIn("private-body", str(context.exception))
            self.assertNotIn("test-placeholder", str(context.exception))
            self.assertEqual(factory.return_value.open.call_count, 1)

    def test_redirects_cannot_forward_the_credential(self):
        self.assertIsNone(NoRedirect().redirect_request(None, None, 302, "", {}, "https://elsewhere.example"))

    @patch("skylit_agent_kit.account.build_opener")
    def test_rejects_large_malformed_or_nonobject_responses(self, factory):
        for body in (b"x" * 1048577, b"not json", b"[]", b'{"value": NaN}'):
            factory.return_value.open.return_value = io.BytesIO(body)
            with self.subTest(size=len(body)), self.assertRaises(AccountError):
                read_account("test-placeholder")

    @patch("skylit_agent_kit.account.build_opener")
    def test_network_errors_are_sanitized(self, factory):
        factory.return_value.open.side_effect = URLError("private diagnostics")
        with self.assertRaisesRegex(AccountError, "Connection failed") as context:
            read_account("test-placeholder")
        self.assertNotIn("private diagnostics", str(context.exception))

    @patch("skylit_agent_kit.account.build_opener")
    def test_interrupted_response_is_sanitized(self, factory):
        factory.return_value.open.return_value.__enter__.return_value.read.side_effect = IncompleteRead(b"private body")
        with self.assertRaisesRegex(AccountError, "Connection failed") as context:
            read_account("test-placeholder")
        self.assertNotIn("private body", str(context.exception))


if __name__ == "__main__":
    unittest.main()
