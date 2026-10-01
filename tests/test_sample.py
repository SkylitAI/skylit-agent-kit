import copy
import json
import socket
import unittest
from pathlib import Path
from unittest.mock import patch

from skylit_agent_kit.sample import load_fixture, render_brief


FIXTURE = Path(__file__).resolve().parents[1] / "examples/fixtures/demo.json"


class SampleTests(unittest.TestCase):
    def setUp(self):
        self.data = load_fixture(FIXTURE)

    def test_sample_is_deterministic_and_network_free(self):
        with patch.object(socket, "socket", side_effect=AssertionError("Network forbidden")):
            report = render_brief(load_fixture(FIXTURE))
            self.assertEqual(report, render_brief(self.data))
        self.assertIn("SYNTHETIC DEMO", report)
        self.assertIn("25.00%", report)
        self.assertIn("60.00%", report)
        self.assertIn("0 network requests", report)
        self.assertIn("examples/fixtures/demo.json", report)

    def test_editing_input_changes_calculation(self):
        self.data["revenue_current_usd"] = 150000000
        self.assertIn("50.00%", render_brief(self.data))

    def test_missing_data_is_explicit(self):
        self.data["revenue_previous_usd"] = None
        self.assertIn("Revenue comparison unavailable", render_brief(self.data))
        self.assertNotIn("25.00%", render_brief(self.data))

    def test_zero_denominators_do_not_invent_a_percentage(self):
        self.data["revenue_previous_usd"] = 0
        self.data["call_premium_usd"] = 0
        self.data["put_premium_usd"] = 0
        report = render_brief(self.data)
        self.assertIn("Revenue comparison unavailable", report)
        self.assertIn("Premium mix unavailable", report)

    def test_live_or_malformed_fixtures_are_rejected(self):
        cases = [("synthetic", False), ("ticker", "<script>"),
                 ("as_of", "yesterday"), ("call_premium_usd", -1),
                 ("revenue_current_usd", True), ("put_premium_usd", float("nan"))]
        for key, value in cases:
            with self.subTest(key=key):
                data = copy.deepcopy(self.data)
                data[key] = value
                with self.assertRaises(ValueError):
                    render_brief(data)

    def test_example_fixture_is_json(self):
        self.assertTrue(json.loads(FIXTURE.read_text())["synthetic"])


if __name__ == "__main__":
    unittest.main()
