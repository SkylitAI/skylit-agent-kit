"""A few readable lines for a live heatmap: strikes nearest spot, the board timestamp and the data credit."""

import math
import re

NEAREST = 5
CREDIT = 'Data: Skylit (https://skylit.ai/)'


def number(value):
    return type(value) in (int, float) and math.isfinite(value)


def text(value, fallback='unavailable'):
    """Printable ASCII only, so returned text cannot drive the terminal."""
    if not isinstance(value, str) or not value:
        return fallback
    return re.sub(r'[^ -~]', '', value)[:40] or fallback


def nearest(strikes, spot):
    rows = [row for row in strikes if isinstance(row, dict) and number(row.get('strike'))]
    if number(spot):
        rows = sorted(rows, key=lambda row: abs(row['strike'] - spot))
    return sorted(rows[:NEAREST], key=lambda row: row['strike'])


def board_lines(board, metric):
    spot = board.get('spot')
    header = ' · '.join([f'{text(board.get("symbol"))} {metric} heatmap'.replace('  ', ' '),
                         f'spot {spot:g}' if number(spot) else 'spot unavailable',
                         f'as of {text(board.get("asOf"))}'])
    strikes = board.get('strikes')
    rows = nearest(strikes if isinstance(strikes, list) else [], spot)
    if not rows:
        return [header, '  No strikes returned.']
    label = 'Strikes nearest spot (net value):' if number(spot) else 'First strikes returned (spot unavailable):'
    lines = [header, label]
    for row in rows:
        value = row.get('value')
        lines.append(f'  {row["strike"]:>8g}  {f"{value:,.6g}" if number(value) else "unavailable":>12}')
    return lines


def summarize(payload, metric=''):
    """Return '' when the response does not have the documented heatmap shape."""
    data = payload.get('data') if isinstance(payload, dict) else None
    boards = data.get('symbols') if isinstance(data, dict) else None
    if not isinstance(boards, list) or not boards or not all(isinstance(b, dict) for b in boards):
        return ''
    blocks = ['\n'.join(board_lines(board, text(metric, ''))) for board in boards]
    return '\n\n'.join(blocks) + '\n' + CREDIT
