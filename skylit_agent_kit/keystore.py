"""Store one Skylit API key locally: macOS Keychain, else an owner-only file."""

import os
import re
import shutil
import stat
import subprocess
import sys
from pathlib import Path

SERVICE = 'skylit-agent-kit'
KEY_PATTERN = re.compile(r'[!-~]{1,4096}')
NOT_FOUND = 44  # `security` exit status for a missing item


class KeystoreError(ValueError):
    """A sanitized local key-storage failure; never contains the key."""


def uses_keychain():
    return sys.platform == 'darwin' and shutil.which('security') is not None


def key_path():
    if os.name == 'nt' and os.environ.get('APPDATA'):
        base = Path(os.environ['APPDATA'])
    else:
        base = Path(os.environ.get('XDG_CONFIG_HOME') or Path.home() / '.config')
    return base / SERVICE / 'key'


def security(*arguments, stdin=None):
    try:
        return subprocess.run(['security', *arguments], input=stdin, capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.TimeoutExpired):
        raise KeystoreError('macOS Keychain is unavailable; no key was read or stored.') from None


def describe():
    if uses_keychain():
        return f'macOS Keychain (item "{SERVICE}")'
    return f'{key_path()} (readable only by you)'


def save(key):
    if not isinstance(key, str) or not KEY_PATTERN.fullmatch(key):
        raise KeystoreError('That does not look like an API key (printable characters, no spaces). Nothing was stored.')
    if uses_keychain():
        # Interactive mode reads the command from stdin, keeping the key out of the process list.
        quoted = key.replace('\\', '\\\\').replace('"', '\\"')
        command = f'add-generic-password -U -a {SERVICE} -s {SERVICE} -l "Skylit API key" -w "{quoted}"\n'
        if security('-i', stdin=command).returncode != 0:
            raise KeystoreError('macOS Keychain refused the key; nothing was stored.')
        return describe()
    path = key_path()
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    path.parent.chmod(0o700)
    if path.is_symlink():
        raise KeystoreError(f'{path} is a symlink; remove it and log in again.')
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, 'O_NOFOLLOW', 0), 0o600)
    with os.fdopen(descriptor, 'w', encoding='utf-8') as stream:
        stream.write(key)
    path.chmod(0o600)
    return describe()


def load():
    if uses_keychain():
        result = security('find-generic-password', '-a', SERVICE, '-s', SERVICE, '-w')
        if result.returncode == NOT_FOUND:
            return None
        if result.returncode != 0:
            raise KeystoreError('Could not read the key from macOS Keychain. Run login again.')
        return result.stdout.rstrip('\n')
    path = key_path()
    if not path.exists():
        return None
    if path.is_symlink():
        raise KeystoreError(f'{path} is a symlink; remove it and log in again.')
    if os.name != 'nt' and stat.S_IMODE(path.stat().st_mode) & 0o077:
        raise KeystoreError(f'{path} is readable by other users; run logout, then login again.')
    return path.read_text(encoding='utf-8').strip() or None


def delete():
    if uses_keychain():
        result = security('delete-generic-password', '-a', SERVICE, '-s', SERVICE)
        if result.returncode not in (0, NOT_FOUND):
            raise KeystoreError('Could not remove the key from macOS Keychain.')
        return result.returncode == 0
    path = key_path()
    if not path.exists() and not path.is_symlink():
        return False
    path.unlink()
    return True
