"""Fixed display credit plus inert, complete source attribution/disclaimer notices."""
import json
from html import escape

SKYLIT_URL = 'https://skylit.ai/'


def credit(synthetic=False):
    return f'[{"Demo by Skylit (fictional data)" if synthetic else "Data: Skylit"}]({SKYLIT_URL})'


def notice_metadata(payload):
    """Select notices only, never account metadata or arbitrary response contents."""
    notices = {key: payload[key] for key in ('attribution', 'disclaimer', 'disclaimers') if key in payload}
    meta = payload.get('meta')
    if isinstance(meta, dict):
        selected = {key: meta[key] for key in ('attribution', 'disclaimer', 'disclaimers') if key in meta}
        if selected: notices['meta'] = selected
    return notices


def safe_metadata(value):
    """Preserve JSON values as inert text, including Markdown link delimiters."""
    text = escape(json.dumps(value, ensure_ascii=True))
    for char in r'\`*_{}[]()|!:/#':
        text = text.replace(char, f'&#{ord(char)};')
    return text


def notice_line(payload):
    notices = notice_metadata(payload)
    return 'Source notices: ' + safe_metadata(notices) if notices else ''
