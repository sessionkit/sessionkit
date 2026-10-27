"""`sessionkit doctor`: what this Mac is missing for the kit. Read-only.

One source of truth. Every row the installer has comes from the installer
itself: the doctor runs the `install.sh` this package ships with `--check`,
and passes its lines through as they are. That file is the repo's root
`install.sh`; `src/sessionkit/install.sh` is a symlink to it, and the build
turns the link into a copy of the same bytes. So a change to a check reaches
`curl ... | bash -s -- --check`, the installer and the doctor at once.

The doctor then adds the three rows the installer never checks, each read by
the family package that owns the state:

- the mail hooks: sessionmail's own settings reader (REQUIRED);
- the phone bot: sessionphone's bot name and its launchd job (optional);
- the session key: sessionmail's `keyed`, sessiontools' key-init path (info).

Each import is guarded: a family release that moves one reads `not checked`
and the run goes on. tests/test_doctor.py pins the imports against uv.lock.

It writes nothing and starts and stops nothing. The only network it reaches
itself is the speech server on 127.0.0.1:8890, which the installer probes,
and its brew reads download nothing. The tools it asks may use their own
network: claude's plugin reads reach Anthropic's API over HTTPS (measured).
"""

from __future__ import annotations

import importlib
import os
import shutil
import subprocess
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path

# install.sh --check's exits, passed straight through.
EXIT_OK = 0
EXIT_MISSING = 1
# Any other exit of the script is passed through, and the doctor adds nothing:
# usage (2), cannot check here (3: not macOS, or root), an interrupt (130).
EXIT_CANNOT = 3

# The installer's own address, for a Mac without the kit (or with one too
# broken to start this command). install.sh's SCRIPT_URL; its --help names it.
CHECK_ONE_LINER = "curl -fsSL https://sessionkit.ai/install.sh | bash -s -- --check"

REMEDY = "    → "
REMEDY_MORE = "      "
NOTE = "   "


def script_path() -> Path:
    """The install.sh this package ships: in a wheel, a copy of the repo's
    root install.sh; in a checkout, the symlink to it."""
    return Path(__file__).parent / "install.sh"


def bash() -> str | None:
    """A fresh Mac's own bash first: the script is written for bash 3.2."""
    return "/bin/bash" if Path("/bin/bash").exists() else shutil.which("bash")


# --- The rows the installer never checks -------------------------------------


@dataclass
class Row:
    """One row: its line, the lines under it, and whether it fails the run."""

    line: str
    under: list[str] = field(default_factory=list)
    missing: bool = False  # a REQUIRED row that is not there: the exit is 1


def _load(module: str, *names: str):
    """The NAMES from MODULE, or None when this family release lacks any."""
    try:
        mod = importlib.import_module(module)
        return tuple(getattr(mod, n) for n in names)
    except (ImportError, AttributeError):
        return None


def hooks_row(env: Mapping[str, str]) -> Row:
    """The mail hooks: REQUIRED. sessionmail's reader decides, by its own strict
    rule: only `"hooks": true` is on (`"true"` and `1` are off)."""
    what = "📬 Mail hooks"
    got = _load("sessionmail._settings", "read", "ON", "MISSING", "SHOWN")
    if got is None:
        return Row(f"{what}: not checked (sessionmail has no settings reader)")
    read, on, absent, shown = got
    s = read(env)
    if s.state == on:
        return Row(f"{what}: on")
    if s.state == absent:
        state = f"off (no {shown} yet)"
    elif s.why:
        state = f"off ({s.why})"
    else:
        state = "off"
    return Row(
        f"{what}: {state}",
        [
            f'{REMEDY}set "hooks": true in {shown}, and change no other key',
            f'{REMEDY_MORE}the README\'s Installation, "The mail hooks start off", has the lines to paste',
        ],
        missing=True,
    )


def phone_row(env: Mapping[str, str]) -> Row:
    """The phone bot: optional, so it never fails the run. sessionphone names
    the bot as its own install would, and asks launchd, read-only. Never
    `sessionphone bot status`: that sends a clip to the job's speech URL,
    which can be any host."""
    what = "📞 Phone bot (optional, for calls)"
    # The call ear is not checked: sessionphone has no read-only check for it
    # yet. A row for it waits for the release that adds one.
    ear = f"{NOTE}the call ear (DC_EARS): not checked yet: sessionphone has no check for it to ask"
    names = _load("sessionphone.settings", "bot_name", "Bad")
    status = _load("sessionphone.service", "status")
    if names is None or status is None:
        return Row(f"{what}: not checked (sessionphone has no bot reader)", [ear])
    try:
        # verb=None: a refusal says "run it again", naming no phone verb.
        name, _came = names[0](env, verb=None, ask=False)
        st = status[0](name)
    except (names[1], OSError, ValueError) as err:  # Bad: sessionphone's refusal
        return Row(f"{what}: not checked ({err})", [ear])
    if st.get("loaded"):
        pid = f", pid {st['pid']}" if st.get("pid") else ""
        return Row(f"{what}: {name}, running{pid}", [ear])
    if st.get("installed"):
        return Row(
            f"{what}: {name}, installed but not loaded",
            [f"{REMEDY}sessionphone bot install", ear],
        )
    return Row(
        f"{what}: not installed",
        [f"{REMEDY}sessionphone setup --name NAME", f"{REMEDY}sessionphone bot install", ear],
    )


def _tilde(p: str, env: Mapping[str, str]) -> str:
    home = env.get("HOME") or ""
    return "~" + p[len(home) :] if home and p.startswith(home + os.sep) else p


def key_row(env: Mapping[str, str]) -> Row:
    """The session key: info only. No kit launch mints one yet, so a required
    row would fail every kit Mac."""
    what = "🔑 Session key (info)"
    keyed = _load("sessionmail._sender", "keyed")
    init = _load("sessiontools.start.identity", "key_init_path")
    if keyed is None:
        line = f"{what}: not checked (sessionmail has no key reader)"
    else:
        state = "keyed: its mail is signed" if keyed[0](env) else "not keyed: its mail goes unsigned"
        line = f"{what}: this shell is {state}"
    under = []
    if init is None:
        under.append(f"{NOTE}session-key-init: not checked (sessiontools has no key-init path)")
    else:
        p = init[0](env)
        here = "found" if os.access(p, os.X_OK) and Path(p).is_file() else "not found"
        under.append(f"{NOTE}session-key-init: {here}, at {_tilde(p, env)}")
    under.append(f"{NOTE}no kit launch makes a session key yet, so this row never fails")
    return Row(line, under)


ROWS: tuple[Callable[[Mapping[str, str]], Row], ...] = (hooks_row, phone_row, key_row)


# --- The run ----------------------------------------------------------------


def run(
    no_speech: bool = False,
    env: Mapping[str, str] | None = None,
    echo: Callable[[str], None] = print,
) -> int:
    """Run install.sh --check, pass its lines through, then the doctor's own
    rows. The exit: the script's 2, 3 or any other, as it is; else 1 when the
    script or a required row of the doctor's says missing; else 0."""
    env = os.environ if env is None else env
    sh = bash()
    script = script_path()
    if sh is None or not script.is_file():
        what = "no bash on the PATH" if sh is None else f"no install.sh at {script}"
        echo(f"sessionkit doctor: cannot check this Mac: {what}.")
        echo("Check it with the installer itself instead:")
        echo(f"    {CHECK_ONE_LINER}")
        return EXIT_CANNOT
    argv = [sh, str(script), "--check"] + (["--no-speech"] if no_speech else [])
    with subprocess.Popen(
        argv,
        env=dict(env),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    ) as p:
        assert p.stdout is not None
        for line in p.stdout:
            echo(line.rstrip("\n"))
    rc = p.returncode
    if rc not in (EXIT_OK, EXIT_MISSING):
        return rc
    echo("")
    echo("🩺 And what the installer does not check:")
    rows = [row(env) for row in ROWS]
    for r in rows:
        echo(r.line)
        for u in r.under:
            echo(u)
    echo("")
    own = [r for r in rows if r.missing]
    if rc == EXIT_OK and not own:
        echo("✅ sessionkit doctor: nothing the kit needs is missing.")
        return EXIT_OK
    if own:
        n = len(own)
        rows_word = "1 row" if n == 1 else f"{n} rows"
        echo(f"🩺 sessionkit doctor: {rows_word} just above {'is' if n == 1 else 'are'} missing: the → lines say what to do.")
    else:
        echo("🩺 sessionkit doctor: the installer's rows above say what is missing.")
    return EXIT_MISSING
