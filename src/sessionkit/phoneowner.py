"""The phone owner's key pin, as sessionphone's own readers answer it.

The kit half of sessionphone's owner-key fix. sessionphone 0.3.3 runs a
one-time key migration on its callers file at the bot's next start: from
then on, a callers line with no `key:` is refused. When the OWNER's line
(the one whose note starts `owner`) is left with no key, the owner can no
longer ring and the bot writes the owner no chat. Before this, the only
notice was the bot's log.

The kit never judges a key. It reads four of sessionphone's readers, by
guarded import, as the doctor's other phone rows do (sessionphone's
maintainers approved these as the interim until its read-only verb lands):

- `sessionphone.bridge.dc_env.callers_file(environ)`: the file the bot reads
- `sessionphone.account.read_owner(path)`: the owner's address, or None
- `sessionphone.account.read_caller_entries(path)`: `.addr`, `.key`, `.note`
- `sessionphone.keygate.is_marked(path)`: has the migration run on it

`read` turns their answers into one state. It never raises: a reader that is
missing, moved or failing reads UNKNOWN, with the reason. Nothing here writes,
and nothing here is ever part of an exit.

Whether the migration WOULD find the owner's key is not answered here:
that needs the Delta Chat account opened, and sessionphone has no dry-run
verb for it yet. PENDING says so, and asks for the pin now.
"""

from __future__ import annotations

import contextlib
import importlib
import io
import textwrap
from collections.abc import Mapping
from dataclasses import dataclass

# The states. Only UNPINNED and PENDING warn.
PINNED = "pinned"  # the owner's line has a key
UNPINNED = "unpinned"  # migrated, and the owner's line has no key
PENDING = "pending"  # not migrated yet, and the owner's line has no key
NO_OWNER = "no owner"  # a callers file with no owner line
NO_FILE = "no file"  # no callers file: no phone linked yet
UNKNOWN = "unknown"  # a reader missing or failing: not checked

WARNS = (UNPINNED, PENDING)

# (module, names) the kit reads from sessionphone. tests/test_phone_owner.py
# pins each against the locked sessionphone.
READS = (
    ("sessionphone.bridge.dc_env", ("callers_file",)),
    ("sessionphone.account", ("read_owner", "read_caller_entries")),
    ("sessionphone.keygate", ("is_marked",)),
)

# The fix, in sessionphone's words: its keygate.PIN_HOW is the same.
PIN_HOW = "sessionphone callers pin {addr} --key FPR"
LINK = "sessionphone link"
FPR_FROM = "FPR: on the owner's phone, the bot's contact, Encryption"

WIDTH = 76

# What each warning says, before its fix lines.
SAYS = {
    UNPINNED: (
        "The phone owner's callers line has no key, so the owner cannot "
        "ring the bot, and the bot writes the owner no chat. Pin the key:"
    ),
    PENDING: (
        "The phone owner's callers line has no key yet. The bot's next "
        "start pins it only if it finds exactly one key for the owner; "
        "if not, the owner cannot ring. Pin it now, while the owner is "
        "at hand:"
    ),
}
# The doctor's short form, under its phone row.
SAYS_SHORT = {
    UNPINNED: "the owner's key: not pinned, so the owner cannot ring",
    PENDING: "the owner's key: not pinned yet; the bot's next start may not find it",
    PINNED: "the owner's key: pinned",
}


@dataclass(frozen=True)
class OwnerPin:
    """The owner's pin state, the owner's address when one was read, and,
    for UNKNOWN, why it could not be told."""

    state: str
    owner: str | None = None
    why: str = ""


def _readers():
    """sessionphone's four readers, or the reason they cannot be had."""
    got = []
    for module, names in READS:
        try:
            mod = importlib.import_module(module)
            got += [getattr(mod, n) for n in names]
        except Exception:  # noqa: BLE001 - missing, moved or failing
            return None, f"sessionphone has no {names[0]} reader"
    return got, ""


def _why(err: BaseException) -> str:
    said = str(err).strip().splitlines()
    return f"{type(err).__name__}: {said[0]}" if said else type(err).__name__


def read(environ: Mapping[str, str]) -> OwnerPin:
    """The owner's pin state for a bot run with ENVIRON. Never raises.

    sessionphone may say a line on stderr as it works out its root (the
    old-root notice); that is its own, so it is held here, never printed
    into setup's or the doctor's output."""
    try:
        with contextlib.redirect_stderr(io.StringIO()):
            return _read(environ)
    except Exception as err:  # noqa: BLE001 - any failure: cannot tell
        return OwnerPin(UNKNOWN, why=_why(err))


def _read(environ: Mapping[str, str]) -> OwnerPin:
    got, why = _readers()
    if got is None:
        return OwnerPin(UNKNOWN, why=why)
    callers_file, read_owner, read_caller_entries, is_marked = got
    path = callers_file(environ)
    entries = read_caller_entries(path)
    if not entries and not path.exists():
        return OwnerPin(NO_FILE)
    owner = read_owner(path)
    if owner is None:
        return OwnerPin(NO_OWNER)
    if any(e.key for e in entries if e.addr == owner):
        return OwnerPin(PINNED, owner)
    return OwnerPin(UNPINNED if is_marked(path) else PENDING, owner)


def _wrap(text: str, indent: str) -> list[str]:
    return textwrap.wrap(
        text,
        WIDTH,
        initial_indent=indent,
        subsequent_indent=indent,
        break_long_words=False,
        break_on_hyphens=False,
    )


def _fix(owner: str | None, indent: str, more: str) -> list[str]:
    """The two fix lines and where FPR comes from. The real address when the
    pin line fits it, else ADDR, with the address on a line of its own."""
    pin = PIN_HOW.format(addr=owner)
    lines = []
    if owner is None or len(indent + pin) > WIDTH:
        lines.append(indent + PIN_HOW.format(addr="ADDR"))
        if owner is not None:
            lines += [f"{more}ADDR: the owner's address,", f"{more}{owner}"]
    else:
        lines.append(indent + pin)
    lines.append(more + FPR_FROM)
    lines.append(f"{indent}or re-link, the owner scanning: {LINK}")
    return lines


def setup_lines(environ: Mapping[str, str]) -> list[str]:
    """What `sessionkit setup` says: the warning and its fix, only for
    UNPINNED or PENDING; nothing otherwise, UNKNOWN included."""
    pin = read(environ)
    if pin.state not in WARNS:
        return []
    return _wrap(SAYS[pin.state], "") + _fix(pin.owner, "  ", "    ")


# The doctor's indents (doctor.NOTE, REMEDY, REMEDY_MORE), kept here so
# this module imports nothing of the kit's.
NOTE = "   "
REMEDY = "    → "
REMEDY_MORE = "      "


def doctor_lines(environ: Mapping[str, str]) -> list[str]:
    """What the doctor says under its phone row: the warning and its fix for
    UNPINNED or PENDING, one line for PINNED, why for UNKNOWN, nothing when
    no phone is linked (no file, no owner)."""
    pin = read(environ)
    if pin.state in WARNS:
        return _wrap(SAYS_SHORT[pin.state], NOTE) + _fix(pin.owner, REMEDY, REMEDY_MORE)
    if pin.state == PINNED:
        return [NOTE + SAYS_SHORT[PINNED]]
    if pin.state == UNKNOWN:
        return _wrap(f"the owner's key: not checked ({pin.why})", NOTE)
    return []
