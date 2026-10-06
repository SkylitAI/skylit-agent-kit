"""Offline setup check: one line per prerequisite, then the single next step."""

import os
import subprocess
import sys
from collections import namedtuple
from pathlib import Path

from . import journey, keystore

ROOT = Path(__file__).resolve().parents[1]
AGENT_ALLOW_RULE = 'Bash(python3 -m skylit_agent_kit:*)'
LOGIN = journey.LOGIN
SYMBOLS = {'ok': '✓', 'warn': '•', 'fail': '✗'}

Check = namedtuple('Check', 'status label detail next_step', defaults=('',))


def python_version():
    return tuple(sys.version_info[:3])


def git(*arguments):
    """Run git; None when git is missing or the command fails."""
    try:
        result = subprocess.run(['git', *arguments], capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return result.stdout.strip() if result.returncode == 0 else None


def check_python():
    version = python_version()
    shown = '.'.join(map(str, version))
    if version >= (3, 11):
        return Check('ok', 'Python', f'{shown} (needs 3.11+)')
    return Check('fail', 'Python', f'{shown} found', 'Install Python 3.11 or newer, then run doctor again.')


def check_git():
    version = git('--version')
    if version:
        return Check('ok', 'Git', version.removeprefix('git version '))
    return Check('fail', 'Git', 'not found', 'Install Git, then run doctor again.')


def check_repository(root):
    branch = git('-C', str(root), 'rev-parse', '--abbrev-ref', 'HEAD')
    commit = git('-C', str(root), 'rev-parse', '--short', 'HEAD')
    if branch and commit:
        return Check('ok', 'Repository', f'{branch} @ {commit}')
    return Check('warn', 'Repository', 'not a Git checkout',
                 'Clone https://github.com/SkylitAI/skylit-agent-kit to receive updates.')


def check_agent_access(root):
    settings = root / '.claude' / 'settings.json'
    try:
        allowed = AGENT_ALLOW_RULE in settings.read_text(encoding='utf-8')
    except OSError:
        allowed = False
    if allowed:
        return Check('ok', 'Agent access', 'kit commands allowed by .claude/settings.json')
    return Check('warn', 'Agent access', 'no allow rule for kit commands',
                 'Your agent may ask you to approve each kit command; approve it, or restore .claude/settings.json.')


def check_reports(root):
    reports = root / 'reports'
    if reports.is_symlink() or (reports.exists() and not reports.is_dir()):
        return Check('fail', 'Reports folder', 'reports/ is not a plain folder',
                     'Remove reports/ and run doctor again; reports are saved there.')
    target = reports if reports.exists() else root
    if os.access(target, os.W_OK):
        return Check('ok', 'Reports folder', 'reports/ writable' if reports.exists() else 'reports/ will be created')
    return Check('fail', 'Reports folder', 'not writable', 'Make this checkout writable by your user.')


def check_key():
    if os.environ.get('SKYLIT_API_KEY'):
        return Check('ok', 'Skylit key', 'from SKYLIT_API_KEY (environment)')
    try:
        stored = keystore.load()
    except keystore.KeystoreError as error:
        return Check('fail', 'Skylit key', 'stored key unreadable', str(error))
    if stored:
        return Check('ok', 'Skylit key', f'stored in {keystore.describe()}')
    return Check('warn', 'Skylit key', 'not stored yet',
                 f'Create a key at {journey.DEVELOPER_PAGE} (API keys → New key), '
                 f'then run in your own terminal: {LOGIN}')


def run_checks(root=ROOT):
    return [check_python(), check_git(), check_repository(root), check_agent_access(root),
            check_reports(root), check_key()]


def current_step(checks):
    """Doctor can only see setup and a stored key; the connection is proven by step 4 itself."""
    if any(c.status == 'fail' for c in checks):
        return 1
    key = next((c for c in checks if c.label == 'Skylit key'), None)
    return 4 if key is None or key.status == 'ok' else 2


def render(checks):
    lines = [f'{SYMBOLS[c.status]} {c.label:<15} {c.detail}' for c in checks]
    step = current_step(checks)
    lines += ['', journey.render_progress(step), '']
    blocking = ([c for c in checks if c.status == 'fail']
                or [c for c in checks if step == 2 and c.label == 'Skylit key']
                or [c for c in checks if c.status == 'warn'])
    if blocking:
        lines.append(f'Next: {blocking[0].next_step}')
    else:
        lines.append(f'Ready. Next: {journey.KIT} account --welcome (one free account check)')
    return '\n'.join(lines)


def run():
    checks = run_checks()
    print(render(checks))
    return 1 if any(c.status == 'fail' for c in checks) else 0
