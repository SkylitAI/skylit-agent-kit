"""A branded, account-detail-free result for an explicit connection check."""

from pathlib import Path
from urllib.parse import quote

from .account import AccountError


def render_welcome(response):
    account = response.get('data')
    if not isinstance(account, dict) or account.get('status') != 'active' or account.get('apiEligible') is not True:
        raise AccountError(
            'Could not confirm an active account with API access. '
            'Check access on your Skylit Developer page; no market data was requested.'
        )
    banner = Path(__file__).resolve().parents[1] / 'assets' / 'skylit-banner.png'
    return '\n'.join([
        f'![Skylit]({quote(banner.as_posix(), safe="/:")})',
        '',
        '# Connected to Skylit',
        '',
        'Your API key is verified. Your account is active and API access is enabled.',
        '',
        'One account check completed. No market data was requested.',
        '',
        'What would you like to explore: your watchlist, a strike chart, flow, or volatility?',
    ])
