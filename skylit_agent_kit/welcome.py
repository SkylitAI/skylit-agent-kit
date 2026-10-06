"""A branded connection check: balance and rate limit only, no identifiers or raw account JSON."""

from pathlib import Path
from urllib.parse import quote

from .account import AccountError
from .journey import DEVELOPER_PAGE, render_welcome_next


def whole(value):
    return type(value) is int and value >= 0


def usage_lines(account):
    if account.get('unlimited') is True:
        credits = 'unlimited'
    elif whole(account.get('creditsBalance')):
        credits = f"{account['creditsBalance']:,}"
    else:
        credits = 'unavailable'
    lines = [f'Credits remaining: {credits}']
    limits = account.get('limits')
    rate = limits.get('requestsPerMinute') if isinstance(limits, dict) else None
    if whole(rate) and rate > 0:
        lines.append(f'Rate limit: {rate} requests per minute')
    return lines


def render_welcome(response):
    account = response.get('data')
    if not isinstance(account, dict) or account.get('status') != 'active' or account.get('apiEligible') is not True:
        raise AccountError(
            'Could not confirm an active account with API access. '
            f'Open {DEVELOPER_PAGE}: confirm API access is enabled and accept the API Terms under API keys. '
            'No market data was requested.'
        )
    banner = Path(__file__).resolve().parents[1] / 'assets' / 'skylit-banner.png'
    return '\n'.join([
        f'![Skylit]({quote(banner.as_posix(), safe="/:")})',
        '',
        '# Connected to Skylit',
        '',
        'Your API key is verified. Your account is active and API access is enabled.',
        '',
        *(f'- {line}' for line in usage_lines(account)),
        '',
        'One account check completed. No market data was requested.',
        '',
        render_welcome_next(),
        '',
        'Or tell your agent what to explore: your watchlist, a strike chart, flow, or volatility.',
    ])
