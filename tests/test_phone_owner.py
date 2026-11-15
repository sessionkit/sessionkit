"""Setup and the doctor warn when the phone owner is, or would be, unpinned.

The kit half of sessionphone's owner-key fix. sessionphone 0.3.3 runs a
one-time key migration on its callers file the bot's next start: a callers
line with no `key:` is refused from then on. When the owner's line (the
one whose note starts `owner`) is left with no key, the owner can no longer
ring and the bot writes him no chat; the only notice was the bot's log.

The kit never judges a key. It asks sessionphone's own readers, by guarded
import, as the doctor's other phone rows do:

- `sessionphone.bridge.dc_env.callers_file(environ)`: the file the bot reads
- `sessionphone.account.read_owner(path)`: the owner's address, or None
- `sessionphone.account.read_caller_entries(path)`: `.addr`, `.key`, `.note`
- `sessionphone.keygate.is_marked(path)`: has the migration run on it

Two states warn, each with the one fix line (sessionphone's words):

- UNPINNED: the file is marked (the migration ran) and the owner line has
  no key.
- PENDING: the file is not marked yet and the owner line has no key: the
  bot's next start pins him only if it finds exactly one key for him.

The fix: `sessionphone callers pin ADDR --key FPR`, or re-link with
`sessionphone link`. Pinned, no owner and no file say nothing. The warning
is never part of an exit, and every line it prints fits 76 columns.

Every test here runs on a temp phone root: DC_ROOT (callers.txt inside it)
or DC_CALLERS_FILE, holding a real callers.txt in sessionphone 0.3.3's
format, read by the real readers.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
import sessionphone.service
import sessionphone.settings
from sessionphone import account, keygate
from sessionphone.bridge import dc_env

from sessionkit import doctor as kit_doctor
from sessionkit import phoneowner
from sessionkit import setup as setup_mod

OWNER = "ada@example.org"
# A chatmail address as long as they come: the warning must still fit.
LONG_OWNER = "x7k2m9q4w8e1r5t3y6u0i2o4p8a1s3d5f7g9@chatmail.relay-example.org"
FPR = "0123456789ABCDEF0123456789ABCDEF01234567"
OTHER = "bob@example.org"
OWNER_NOTE = "owner, named by `sessionphone bot install --owner`"
WIDTH = 76

FIX_PIN = "sessionphone callers pin {addr} --key FPR"
FIX_LINK = "sessionphone link"


def callers_text(*, migrated: bool, owner_key: str | None, addr: str = OWNER) -> str:
    """A callers.txt as sessionphone 0.3.3 writes it: the keys marker on top
    once the migration has run, the owner's line, and one other caller."""
    lines = [keygate.MARKER + "\n"] if migrated else []
    lines.append(keygate.entry_line(addr, owner_key, OWNER_NOTE))
    lines.append(keygate.entry_line(OTHER, FPR, "a friend"))
    return "".join(lines)


@pytest.fixture(params=["DC_ROOT", "DC_CALLERS_FILE"])
def phone(request, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """(env, callers path): a temp HOME and phone root, the callers file named
    by DC_ROOT (as callers.txt in it) or by DC_CALLERS_FILE."""
    home = tmp_path / "home"
    home.mkdir()
    env = {"HOME": str(home), "PATH": "/usr/bin:/bin"}
    if request.param == "DC_ROOT":
        root = tmp_path / "phone-root"
        root.mkdir()
        env["DC_ROOT"] = str(root)
        path = root / "callers.txt"
    else:
        path = tmp_path / "elsewhere" / "callers.txt"
        path.parent.mkdir()
        env["DC_CALLERS_FILE"] = str(path)
    for k in list(os.environ):
        if k.startswith(("DC_", "SESSIONPHONE_", "PIP_CHAT_")):
            monkeypatch.delenv(k)
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    assert dc_env.callers_file(env) == path
    return env, path


# --- the state is readable with sessionphone's own readers -------------------


def test_readers_see_unpinned(phone):
    env, path = phone
    path.write_text(callers_text(migrated=True, owner_key=None), encoding="utf-8")
    f = dc_env.callers_file(env)
    assert account.read_owner(f) == OWNER
    owner = [e for e in account.read_caller_entries(f) if e.addr == OWNER]
    assert len(owner) == 1 and owner[0].key is None
    assert keygate.is_marked(f) is True


def test_readers_see_pending(phone):
    env, path = phone
    path.write_text(callers_text(migrated=False, owner_key=None), encoding="utf-8")
    f = dc_env.callers_file(env)
    assert account.read_owner(f) == OWNER
    owner = [e for e in account.read_caller_entries(f) if e.addr == OWNER]
    assert len(owner) == 1 and owner[0].key is None
    assert keygate.is_marked(f) is False


def test_readers_see_pinned(phone):
    env, path = phone
    path.write_text(callers_text(migrated=True, owner_key=FPR), encoding="utf-8")
    f = dc_env.callers_file(env)
    owner = [e for e in account.read_caller_entries(f) if e.addr == OWNER]
    assert owner[0].key == FPR


# --- the two surfaces --------------------------------------------------------


def run_setup(env, monkeypatch) -> setup_mod.Outcome:
    """run_setup with every step but the owner check stubbed to a quiet OK:
    no mail verb, no operator, no agent file, no ears, no docs."""
    ok = setup_mod.Outcome(setup_mod.EXIT_OK, [])
    monkeypatch.setattr(setup_mod, "stranded", lambda *a, **k: None)
    monkeypatch.setattr(
        setup_mod, "run_mail_setup", lambda **k: setup_mod.Outcome(0, [])
    )
    monkeypatch.setattr(setup_mod, "run_operator", lambda **k: setup_mod.Outcome(0, []))
    monkeypatch.setattr(setup_mod, "run_agent", lambda **k: ok)
    monkeypatch.setattr(setup_mod, "default_seat", lambda environ: "claude")
    monkeypatch.setattr(setup_mod, "run_wake", lambda **k: [])
    monkeypatch.setattr(setup_mod, "run_docs", lambda **k: [])
    monkeypatch.setattr(setup_mod, "ears_model_missing", lambda environ: False)
    return setup_mod.run_setup(home=Path(env["HOME"]), environ=env)


def doctor_phone(env, monkeypatch) -> kit_doctor.Row:
    """The doctor's phone row, its bot running (launchd never asked)."""
    monkeypatch.setattr(
        sessionphone.settings, "bot_name", lambda *a, **k: ("claude", "test")
    )
    monkeypatch.setattr(
        sessionphone.service, "status", lambda name: {"loaded": True, "pid": 77}
    )
    return kit_doctor.phone_row(env)


def setup_lines(env, monkeypatch) -> list[str]:
    out = run_setup(env, monkeypatch)
    assert out.code == setup_mod.EXIT_OK  # the warning is never the exit
    return list(out.lines)


def doctor_lines(env, monkeypatch) -> list[str]:
    row = doctor_phone(env, monkeypatch)
    assert row.missing is False  # optional row: never fails the run
    return [row.line, *row.under]


SURFACES = {"setup": setup_lines, "doctor": doctor_lines}


def warning_lines(lines: list[str]) -> list[str]:
    """The lines that speak of the owner's pin or name its fix."""
    return [
        ln
        for ln in lines
        if "owner" in ln.lower() or "callers pin" in ln or FIX_LINK in ln
    ]


def assert_warns(lines: list[str], addr: str) -> None:
    text = "\n".join(lines)
    warn = warning_lines(lines)
    assert any("owner" in ln.lower() for ln in warn), text
    assert any(FIX_PIN.format(addr=addr) in ln for ln in warn), text
    assert any(FIX_LINK in ln for ln in warn), text
    too_wide = [ln for ln in warn if len(ln) > WIDTH]
    assert not too_wide, too_wide


def assert_silent(lines: list[str]) -> None:
    assert not [ln for ln in lines if "callers pin" in ln], lines


@pytest.mark.parametrize("surface", SURFACES)
def test_warns_when_owner_unpinned_after_migration(surface, phone, monkeypatch):
    env, path = phone
    path.write_text(callers_text(migrated=True, owner_key=None), encoding="utf-8")
    assert_warns(SURFACES[surface](env, monkeypatch), OWNER)


@pytest.mark.parametrize("surface", SURFACES)
def test_warns_when_owner_would_be_unpinned_before_migration(
    surface, phone, monkeypatch
):
    env, path = phone
    path.write_text(callers_text(migrated=False, owner_key=None), encoding="utf-8")
    assert_warns(SURFACES[surface](env, monkeypatch), OWNER)


@pytest.mark.parametrize("surface", SURFACES)
def test_unpinned_and_pending_say_different_things(surface, phone, monkeypatch):
    env, path = phone
    path.write_text(callers_text(migrated=True, owner_key=None), encoding="utf-8")
    after = warning_lines(SURFACES[surface](env, monkeypatch))
    path.write_text(callers_text(migrated=False, owner_key=None), encoding="utf-8")
    before = warning_lines(SURFACES[surface](env, monkeypatch))
    assert after and before
    assert after != before


@pytest.mark.parametrize("migrated", [True, False], ids=["unpinned", "pending"])
@pytest.mark.parametrize("surface", SURFACES)
def test_a_long_owner_address_still_fits(surface, migrated, phone, monkeypatch):
    env, path = phone
    path.write_text(
        callers_text(migrated=migrated, owner_key=None, addr=LONG_OWNER),
        encoding="utf-8",
    )
    lines = SURFACES[surface](env, monkeypatch)
    warn = warning_lines(lines)
    # The real address when the line fits it, else the placeholder ADDR.
    pin = [ln for ln in warn if "sessionphone callers pin " in ln and "--key FPR" in ln]
    assert pin, lines
    assert any(FIX_LINK in ln for ln in warn), lines
    too_wide = [ln for ln in warn if len(ln) > WIDTH]
    assert not too_wide, too_wide


# --- the controls: nothing to warn about, nothing said -----------------------


@pytest.mark.parametrize("surface", SURFACES)
def test_silent_when_owner_pinned(surface, phone, monkeypatch):
    env, path = phone
    path.write_text(callers_text(migrated=True, owner_key=FPR), encoding="utf-8")
    assert_silent(SURFACES[surface](env, monkeypatch))


@pytest.mark.parametrize("surface", SURFACES)
def test_silent_with_no_callers_file(surface, phone, monkeypatch):
    env, path = phone
    assert not path.exists()
    assert_silent(SURFACES[surface](env, monkeypatch))


@pytest.mark.parametrize("surface", SURFACES)
def test_silent_with_no_owner_line(surface, phone, monkeypatch):
    env, path = phone
    path.write_text(
        keygate.MARKER + "\n" + keygate.entry_line(OTHER, None, "a friend"),
        encoding="utf-8",
    )
    assert account.read_owner(path) is None
    assert_silent(SURFACES[surface](env, monkeypatch))


# --- the reader's states, read by phoneowner ---------------------------------


@pytest.mark.parametrize(
    ("migrated", "key", "state"),
    [
        (True, None, phoneowner.UNPINNED),
        (False, None, phoneowner.PENDING),
        (True, FPR, phoneowner.PINNED),
        (False, FPR, phoneowner.PINNED),
    ],
)
def test_read_names_the_state(phone, migrated, key, state):
    env, path = phone
    path.write_text(callers_text(migrated=migrated, owner_key=key), encoding="utf-8")
    pin = phoneowner.read(env)
    assert (pin.state, pin.owner, pin.why) == (state, OWNER, "")


def test_read_no_file_and_no_owner(phone):
    env, path = phone
    assert phoneowner.read(env).state == phoneowner.NO_FILE
    path.write_text(keygate.entry_line(OTHER, None, "a friend"), encoding="utf-8")
    assert phoneowner.read(env).state == phoneowner.NO_OWNER


def test_the_doctor_says_pinned_in_one_line(phone, monkeypatch):
    env, path = phone
    path.write_text(callers_text(migrated=True, owner_key=FPR), encoding="utf-8")
    lines = doctor_lines(env, monkeypatch)
    assert lines[-1] == "   the owner's key: pinned"


def test_no_phone_linked_adds_nothing_to_the_doctor(phone, monkeypatch):
    # The doctor's own phone tests pin its lines exactly: no file, no line.
    env, _path = phone
    row = doctor_phone(env, monkeypatch)
    assert row.under == [
        "   the call ear (DC_EARS): not checked yet: sessionphone has no check for it to ask"
    ]


# --- sessionphone absent, or a reader failing: cannot tell, never a crash ----


def _unpinned(phone):
    env, path = phone
    path.write_text(callers_text(migrated=True, owner_key=None), encoding="utf-8")
    return env


@pytest.mark.parametrize(("module", "names"), phoneowner.READS)
def test_a_missing_reader_reads_unknown(phone, monkeypatch, module, names):
    env = _unpinned(phone)
    monkeypatch.setitem(sys.modules, module, None)  # `import module` raises
    pin = phoneowner.read(env)
    assert pin.state == phoneowner.UNKNOWN
    assert pin.why == f"sessionphone has no {names[0]} reader"


def test_a_renamed_reader_reads_unknown(phone, monkeypatch):
    env = _unpinned(phone)
    monkeypatch.delattr(keygate, "is_marked")
    pin = phoneowner.read(env)
    assert (pin.state, pin.why) == (phoneowner.UNKNOWN, "sessionphone has no is_marked reader")


@pytest.mark.parametrize("err", [OSError("Permission denied"), RuntimeError("boom"), ValueError()])
def test_a_reader_raising_reads_unknown(phone, monkeypatch, err):
    env = _unpinned(phone)

    def raises(*a, **k):
        raise err

    monkeypatch.setattr(account, "read_caller_entries", raises)
    pin = phoneowner.read(env)
    assert pin.state == phoneowner.UNKNOWN
    assert pin.why.startswith(type(err).__name__)


@pytest.mark.parametrize("surface", SURFACES)
def test_sessionphone_absent_never_crashes_a_surface(surface, phone, monkeypatch):
    env = _unpinned(phone)
    monkeypatch.setitem(sys.modules, "sessionphone.account", None)
    lines = SURFACES[surface](env, monkeypatch)  # asserts the exit is unchanged
    assert_silent(lines)
    if surface == "doctor":
        assert "   the owner's key: not checked (sessionphone has no read_owner reader)" in lines
    else:
        assert not warning_lines(lines)  # setup warns only on what it can tell


@pytest.mark.parametrize("surface", SURFACES)
def test_a_reader_raising_never_crashes_a_surface(surface, phone, monkeypatch):
    env = _unpinned(phone)

    def raises(*a, **k):
        raise OSError("Permission denied: callers.txt")

    monkeypatch.setattr(keygate, "is_marked", raises)
    lines = SURFACES[surface](env, monkeypatch)
    assert_silent(lines)
    too_wide = [ln for ln in lines if "owner" in ln and len(ln) > WIDTH]
    assert not too_wide, too_wide


def test_the_owner_is_read_when_the_bot_reader_is_missing(phone, monkeypatch):
    # No bot reader: the row reads not checked, and still warns of the owner.
    env = _unpinned(phone)
    monkeypatch.setitem(sys.modules, "sessionphone.service", None)
    row = kit_doctor.phone_row(env)
    assert row.missing is False
    assert row.line.endswith("not checked (sessionphone has no bot reader)")
    assert_warns(row.under, OWNER)


def test_sessionphone_stderr_is_held(phone, monkeypatch, capsys):
    # sessionphone may say its old-root notice on stderr as it works out the
    # root; setup and the doctor must not print it as noise.
    env = _unpinned(phone)
    real = dc_env.callers_file

    def noisy(environ=None):
        print("sessionphone: using the old root /x/.sessionphone: ...", file=sys.stderr)
        return real(environ)

    monkeypatch.setattr(dc_env, "callers_file", noisy)
    assert phoneowner.read(env).state == phoneowner.UNPINNED
    phoneowner.setup_lines(env)
    phoneowner.doctor_lines(env)
    assert capsys.readouterr().err == ""


# --- a long chatmail address: the pin line takes ADDR, the address is shown --


@pytest.mark.parametrize("migrated", [True, False], ids=["unpinned", "pending"])
@pytest.mark.parametrize("surface", SURFACES)
def test_a_long_address_is_shown_whole_on_its_own_line(surface, migrated, phone, monkeypatch):
    env, path = phone
    path.write_text(
        callers_text(migrated=migrated, owner_key=None, addr=LONG_OWNER), encoding="utf-8"
    )
    lines = SURFACES[surface](env, monkeypatch)
    assert any(ln.endswith("sessionphone callers pin ADDR --key FPR") for ln in lines), lines
    assert any(ln.strip() == LONG_OWNER for ln in lines), lines
    assert all(len(ln) <= WIDTH for ln in phoneowner.setup_lines(env) + phoneowner.doctor_lines(env))


def test_every_warning_line_fits_with_the_longest_owner_that_fits():
    # The widest owner that keeps the real address on the doctor's pin line.
    room = WIDTH - len(phoneowner.REMEDY + phoneowner.PIN_HOW.format(addr=""))
    addr = "a" * (room - len("@b.org")) + "@b.org"
    lines = phoneowner._fix(addr, phoneowner.REMEDY, phoneowner.REMEDY_MORE)
    assert lines[0] == phoneowner.REMEDY + phoneowner.PIN_HOW.format(addr=addr)
    assert max(map(len, lines)) == WIDTH
    longer = phoneowner._fix(addr + "x", phoneowner.REMEDY, phoneowner.REMEDY_MORE)
    assert "ADDR --key FPR" in longer[0]


# --- the fix's words and the reads, held to sessionphone's -------------------


def test_the_pin_line_is_sessionphones_own():
    assert phoneowner.PIN_HOW == keygate.PIN_HOW


@pytest.mark.parametrize(("module", "names"), phoneowner.READS)
def test_the_owner_reads_import_at_the_locked_sessionphone(module, names):
    # A rename in a sessionphone release turns this red, not the check quiet.
    import importlib

    mod = importlib.import_module(module)
    for n in names:
        assert hasattr(mod, n), f"{module}.{n} is gone in this sessionphone"
