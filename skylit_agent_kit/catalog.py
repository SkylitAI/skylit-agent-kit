"""Reviewed public endpoint metadata and fictional previews; stdlib only."""
from copy import deepcopy
from functools import lru_cache
import json
from pathlib import Path

CONTRACTS = Path(__file__).resolve().parent / 'contracts'


@lru_cache(maxsize=1)
def _catalog():
    return {item['id']: item for item in json.loads((CONTRACTS / 'endpoints.json').read_text())}


def list_endpoints():
    return deepcopy(list(_catalog().values()))


def get_endpoint(identity):
    try:
        return deepcopy(_catalog()[identity])
    except (KeyError, TypeError):
        raise ValueError('Unknown endpoint ID; run endpoints to list the public catalog.') from None


def get_contract(service):
    if service not in ('heatseeker', 'flowseeker', 'atlas'):
        raise ValueError('Unknown public service')
    return json.loads((CONTRACTS / f'{service}.json').read_text())
