"""Small stdlib helpers for the schema constructs used in the public snapshots.

This is not a general JSON Schema implementation. Tests inventory every keyword
used by these contracts; generation fails on unresolved external references.
"""
import math
import re
from datetime import date, datetime


def resolve(schema, document):
    if '$ref' not in schema:
        return schema
    reference = schema['$ref']
    if not reference.startswith('#/'):
        raise ValueError('Only local public-contract references are supported')
    result = document
    for part in reference[2:].split('/'):
        result = result[part.replace('~1', '/').replace('~0', '~')]
    return {**resolve(result, document), **{k: v for k, v in schema.items() if k != '$ref'}}


def valid(value, schema, document):
    schema = resolve(schema, document)
    if value is None and schema.get('nullable'):
        return True
    if 'allOf' in schema and not all(valid(value, branch, document) for branch in schema['allOf']): return False
    if 'oneOf' in schema and sum(valid(value, branch, document) for branch in schema['oneOf']) != 1: return False
    if 'anyOf' in schema and not any(valid(value, branch, document) for branch in schema['anyOf']): return False
    if 'enum' in schema and value not in schema['enum']: return False
    if 'const' in schema and value != schema['const']: return False
    kind = schema.get('type')
    if isinstance(kind, list):
        return any(valid(value, {**schema, 'type': item}, document) for item in kind)
    checks = {'object': isinstance(value, dict), 'array': isinstance(value, list),
              'string': isinstance(value, str), 'boolean': type(value) is bool,
              'integer': type(value) is int, 'number': type(value) in (int, float), 'null': value is None}
    if kind in checks and not checks[kind]: return False
    if type(value) in (int, float):
        try:
            if not math.isfinite(value): return False
        except OverflowError: return False
        if 'minimum' in schema and value < schema['minimum']: return False
        if 'maximum' in schema and value > schema['maximum']: return False
    if isinstance(value, dict):
        if any(key not in value for key in schema.get('required', [])): return False
        properties = schema.get('properties', {})
        for key, item in value.items():
            if key in properties:
                if not valid(item, properties[key], document): return False
            elif schema.get('additionalProperties') is False: return False
            elif isinstance(schema.get('additionalProperties'), dict):
                if not valid(item, schema['additionalProperties'], document): return False
    if isinstance(value, list):
        if len(value) < schema.get('minItems', 0) or len(value) > schema.get('maxItems', float('inf')): return False
        if not all(valid(item, schema.get('items', {}), document) for item in value): return False
    if isinstance(value, str):
        if len(value) < schema.get('minLength', 0) or len(value) > schema.get('maxLength', float('inf')): return False
        if 'pattern' in schema and re.search(schema['pattern'], value) is None: return False
        try:
            if schema.get('format') == 'date' and date.fromisoformat(value).isoformat() != value: return False
            if schema.get('format') == 'date-time' and datetime.fromisoformat(value).tzinfo is None: return False
        except ValueError: return False
    return True


def synthetic(schema, document, name='', depth=0):
    """Independently author fictional values from shape; never copy service examples."""
    if depth > 30: raise ValueError('Schema nesting exceeds synthetic generator bound')
    schema = resolve(schema, document)
    if 'allOf' in schema:
        merged = {}
        for branch in schema['allOf']: merged.update(synthetic(branch, document, name, depth + 1))
        merged.update(synthetic({k: v for k, v in schema.items() if k != 'allOf'}, document, name, depth + 1) or {})
        return merged
    if 'oneOf' in schema or 'anyOf' in schema:
        return synthetic(schema.get('oneOf', schema.get('anyOf'))[0], document, name, depth + 1)
    if 'const' in schema: return schema['const']
    if 'enum' in schema: return schema['enum'][0]
    kind = schema.get('type', 'object' if 'properties' in schema else None)
    if isinstance(kind, list): kind = next((item for item in kind if item != 'null'), 'null')
    if kind == 'null': return None
    if kind == 'object':
        properties = schema.get('properties', {})
        return {key: synthetic(child, document, key, depth + 1) for key, child in properties.items()}
    if kind == 'array': return [synthetic(schema.get('items', {}), document, name, depth + 1)] * max(1, schema.get('minItems', 0))
    if kind == 'boolean': return False
    if kind in ('integer', 'number'):
        value = max(schema.get('minimum', 0), min(100, schema.get('maximum', 100)))
        return int(value) if kind == 'integer' else value
    if kind == 'string':
        if schema.get('format') == 'date': return '2026-09-30'
        if schema.get('format') == 'date-time': return '2026-09-30T14:00:00Z'
        if schema.get('pattern') == '^[0-9]+$': return '1790776800'
        if name.lower() in ('symbol', 'ticker', 'name'): return 'SPY'
        return 'synthetic'[:schema.get('maxLength', 9)]
    return {}
