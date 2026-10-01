import hashlib
import importlib.util
import json
import socket
import unittest
from pathlib import Path
from unittest.mock import patch
from skylit_agent_kit import catalog
from skylit_agent_kit.contract_schema import valid

ROOT=Path(__file__).resolve().parents[1]

class CatalogTests(unittest.TestCase):
    def test_catalog_covers_exact_public_operations_and_provenance(self):
        expected=set()
        manifest=json.loads((catalog.CONTRACTS/'provenance.json').read_text())
        for service in manifest:
            raw=(catalog.CONTRACTS/f'{service}.json').read_bytes()
            self.assertEqual(hashlib.sha256(raw).hexdigest(),manifest[service]['snapshot_sha256'])
            document=json.loads(raw)
            for path, item in document['paths'].items():
                for method, operation in item.items():
                    if method in ('get','post','put','patch','delete','head','options'):
                        expected.add((service,operation['operationId'],method.upper(),path))
        actual={(e['service'],e['operation_id'],e['method'],e['path']) for e in catalog.list_endpoints()}
        self.assertEqual(actual, expected)
        self.assertEqual(len(actual),77)
        self.assertEqual(sum(e['existing_demo'] for e in catalog.list_endpoints()),4)

    def test_every_independently_generated_preview_matches_public_response_schema(self):
        with patch.object(socket,'socket',side_effect=AssertionError('Network forbidden')):
            for endpoint in catalog.list_endpoints():
                with self.subTest(endpoint=endpoint['id']):
                    self.assertTrue(valid(endpoint['example_response'],endpoint['schema'],catalog.get_contract(endpoint['service'])))
                    self.assertTrue(endpoint['summary'])
                    self.assertTrue(endpoint['next_step'])
                    self.assertIn(endpoint['id'],endpoint['preview_command'])

    def test_regeneration_is_reproducible_without_yaml_or_network(self):
        spec=importlib.util.spec_from_file_location('generate_catalog',ROOT/'scripts/generate_endpoint_catalog.py')
        module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        with patch.object(socket,'socket',side_effect=AssertionError('Network forbidden')):
            self.assertEqual(module.generate(),catalog.list_endpoints())

    def test_mutation_cannot_change_catalog_or_bypass_transport_route(self):
        first=catalog.get_endpoint('flowseeker.getOpenAPI')
        self.assertEqual(first['path'],'/v1/openapi.json')
        self.assertEqual(first['transport_path'],'/v1/flow/openapi.json')
        first['host']='https://evil.invalid'
        self.assertEqual(catalog.get_endpoint('flowseeker.getOpenAPI')['host'],'https://api.skylit.ai')
