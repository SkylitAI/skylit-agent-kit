import copy
import unittest
from skylit_agent_kit.node_tracker import track, chart, parse_time


def payload():
    return {'meta': {'metric': 'gamma'}, 'data': {'from': '2026-09-30T14:00:00Z', 'to': '2026-09-30T14:03:00Z', 'symbols': [{'symbol': 'SPY', 'axes': [{'id': 7, 'strikes': [100, 105], 'expirations': ['2026-10-02']}, {'id': 22, 'strikes': [95, 100], 'expirations': ['2026-10-02']}], 'frames': [{'asOf': '2026-09-30T14:00:00Z', 'axis': 7, 'spot': 101, 'values': [-100, 20]}, {'asOf': '2026-09-30T14:03:00Z', 'axis': 22, 'spot': 102, 'values': [30, -60]}]}]}}


class TrackerTests(unittest.TestCase):
    def run_track(self, p): return track(p, 'SPY', 'gamma', [100, 105], ['2026-10-02'])

    def test_negative_and_axis_identity(self):
        r = self.run_track(payload())
        a, b = r['series'][100]
        self.assertEqual((a['value'], b['value'], b['delta'], b['magnitude_delta']), (-100, -60, 40, -40))
        self.assertEqual(b['magnitude_pct'], -40)
        self.assertIsNone(r['series'][105][1]['value'])
        self.assertIn('zero line', chart(r))

    def test_expiry_shift_is_gap_and_breaks_comparison(self):
        p = payload(); p['data']['symbols'][0]['axes'][1]['expirations'] = ['2026-10-09']
        r = self.run_track(p)
        self.assertEqual(r['series'][100][1]['status'], 'incomparable expiry set')
        self.assertIsNone(r['series'][100][1]['delta'])

    def test_duplicates_are_gap_not_last_write_wins(self):
        p = payload(); p['data']['symbols'][0]['frames'].append(copy.deepcopy(p['data']['symbols'][0]['frames'][0]))
        r = self.run_track(p)
        self.assertEqual(r['series'][100][0]['status'], 'duplicate timestamp')
        self.assertIsNone(r['series'][100][1]['delta'])

    def test_chronology_and_timezone(self):
        p = payload(); p['data']['symbols'][0]['frames'].reverse()
        self.assertEqual(self.run_track(p)['series'][100][1]['value'], -60)
        self.assertEqual(parse_time('2026-09-30T07:00:00-07:00'), parse_time('2026-09-30T14:00:00Z'))
        with self.assertRaises(ValueError): parse_time('2026-09-30T14:00:00')

    def test_nonfinite_and_malformed_time_rejected(self):
        p = payload(); p['data']['symbols'][0]['frames'][0]['values'][0] = float('nan')
        with self.assertRaises(ValueError): self.run_track(p)
        p = payload(); p['data']['symbols'][0]['frames'][0]['asOf'] = 'bad'
        with self.assertRaises(ValueError): self.run_track(p)

    def test_zero_has_no_percentage(self):
        p = payload(); p['data']['symbols'][0]['frames'][0]['values'][0] = 0
        self.assertIsNone(self.run_track(p)['series'][100][1]['magnitude_pct'])

    def test_missing_axis_and_duplicate_strikes_rejected(self):
        p = payload(); p['data']['symbols'][0]['frames'][0]['axis'] = 900
        with self.assertRaises(ValueError): self.run_track(p)
        p = payload(); p['data']['symbols'][0]['axes'][0]['strikes'] = [100, 100]
        with self.assertRaises(ValueError): self.run_track(p)

    def test_gap_does_not_bridge(self):
        p = payload(); frame = copy.deepcopy(p['data']['symbols'][0]['frames'][0]); frame['asOf'] = '2026-09-30T14:02:00Z'; frame['axis'] = 22
        p['data']['symbols'][0]['frames'].append(frame)
        r = self.run_track(p)
        self.assertIsNone(r['series'][105][1]['value'])
        self.assertIsNone(r['series'][105][2]['delta'])

    def test_no_frames_explicitly_reports_no_observations(self):
        from skylit_agent_kit.node_tracker import report
        p = payload(); p['data']['symbols'][0]['frames'] = []
        self.assertIn('No observations returned', report(self.run_track(p)))

    def test_huge_integer_and_overflow_float_are_rejected_cleanly(self):
        import json
        for value in (10**400, json.loads('1e999')):
            p = payload(); p['data']['symbols'][0]['frames'][0]['values'][0] = value
            with self.assertRaises(ValueError): self.run_track(p)

    def test_standalone_chart_preserves_credit_notices_and_synthetic_label(self):
        import xml.etree.ElementTree as ET
        from skylit_agent_kit.node_tracker import report
        p = payload()
        p['meta']['attribution'] = {'text': 'Powered by Skylit', 'shareable': False,
            'url': 'javascript:alert(1)'}
        p['disclaimer'] = '<script>source disclaimer</script>'
        result = self.run_track(p)
        svg = chart(result)
        xml = ET.fromstring(svg)
        links = xml.findall('.//{http://www.w3.org/2000/svg}a')
        self.assertEqual([a.get('href') for a in links], ['https://skylit.ai/'])
        visible_text = ' '.join(' '.join(xml.itertext()).split())
        self.assertIn('Data: Skylit', visible_text)
        self.assertIn('source disclaimer', visible_text)
        self.assertIn('Powered by Skylit', visible_text)
        self.assertNotIn('<script>', svg)
        self.assertIn('[Data: Skylit](https://skylit.ai/)', report(result))
        synthetic = chart(result, synthetic=True)
        self.assertIn('SYNTHETIC / FICTIONAL DATA', synthetic)
        self.assertIn('Demo by Skylit', synthetic)
        self.assertNotIn('Data: Skylit', synthetic)
