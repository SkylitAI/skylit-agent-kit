"""Fixed display credit plus inert, complete source attribution/disclaimer notices."""
import json

SKYLIT_URL = 'https://skylit.ai/'
INERT = {ord(char): f'&#{ord(char)};' for char in '&<>"\'' + r'\`*_{}[]()|!:/#'}


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
    # One pass, so an entity written for one character is never re-escaped by a later one.
    return json.dumps(value, ensure_ascii=True).translate(INERT)


def notice_line(payload):
    notices = notice_metadata(payload)
    return 'Source notices: ' + safe_metadata(notices) if notices else ''
