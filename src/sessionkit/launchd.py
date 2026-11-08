"""What launchd says about the kit's jobs: state, never discovery.

`sessionkit service` finds services from their files (services.py). This
module reads launchd for what runs, and makes the one write `restart`
needs. Every call goes through `launchctl()`, which runs the program named by
SESSIONKIT_LAUNCHCTL, else /bin/launchctl. The tests point that at a fake.

- `listed()` parses `launchctl list`: `PID Status Label`. A `-` PID is
  loaded, not running. A negative Status is a signal (`-15` is SIGTERM).
- `printed(label)` parses `launchctl print gui/<uid>/<label>` for the long
  form. The man page says print "is NOT API", so a field it does not find is
  left out, never an error. A job last stopped by a signal has no `last exit
  code` line; it has `last terminating signal = Terminated: 15` instead.
- `plist(label)` reads ~/Library/LaunchAgents/<label>.plist with plistlib.
- `kickstart(label)` runs `launchctl kickstart -k gui/<uid>/<label>`.

launchctl's error 125 ("Domain does not support specified action") means
this shell cannot reach gui/<uid>, as from an ssh login or a background
session. It is raised as Unreachable, and the CLI exits 3 on it.
"""

from __future__ import annotations

import os
import plistlib
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

LAUNCHCTL_ENV = "SESSIONKIT_LAUNCHCTL"
DEFAULT_LAUNCHCTL = "/bin/launchctl"
PREFIX = "dev.sessionkit."
UNREACHABLE_RC = 125
# The same error, as a failed call words it ("...: 125: Domain does not
# support specified action"). Read only when the call failed: a print that
# succeeds can carry "125: " in its environment or arguments.
_UNREACHABLE = re.compile(r"\b125: ")
TIMEOUT_S = 20


class Unreachable(Exception):
    """launchd's gui/<uid> domain cannot be reached from this shell."""


class Failed(Exception):
    """A launchctl call failed for another reason; its words are the message."""


@dataclass(frozen=True)
class Listed:
    """One `launchctl list` row: the pid (None when not running) and the last
    Status (None when launchctl printed `-`)."""

    pid: int | None
    status: int | None


@dataclass(frozen=True)
class Ran:
    """A finished launchctl call."""

    rc: int
    out: str

    @property
    def words(self) -> str:
        return self.out.strip() or f"launchctl exited {self.rc}"


def uid() -> int:
    return os.getuid()


def domain() -> str:
    return f"gui/{uid()}"


def target(label: str) -> str:
    return f"{domain()}/{label}"


def program() -> str:
    return os.environ.get(LAUNCHCTL_ENV) or DEFAULT_LAUNCHCTL


def launchctl(*args: str) -> Ran:
    """Run launchctl with ARGS; stdout and stderr together. A launchctl that
    is not there (not macOS) is Unreachable, as is its error 125."""
    try:
        done = subprocess.run(
            [program(), *args],
            capture_output=True,
            text=True,
            timeout=TIMEOUT_S,
            check=False,
        )
    except FileNotFoundError:
        raise Unreachable(f"{program()} not found: launchd is macOS only") from None
    except subprocess.TimeoutExpired:
        raise Failed(
            f"launchctl {' '.join(args)} gave no answer in {TIMEOUT_S}s"
        ) from None
    except OSError as e:
        raise Failed(f"{program()}: {e}") from None
    ran = Ran(done.returncode, (done.stdout or "") + (done.stderr or ""))
    if ran.rc == UNREACHABLE_RC or (ran.rc != 0 and _UNREACHABLE.search(ran.out)):
        raise Unreachable(ran.words)
    return ran


def _int(word: str) -> int | None:
    try:
        return int(word)
    except ValueError:
        return None


def parse_list(text: str) -> dict[str, Listed]:
    """`launchctl list` as {label: Listed}. The header and any line that is
    not three columns are skipped."""
    rows: dict[str, Listed] = {}
    for line in text.splitlines():
        parts = line.split(None, 2)
        if len(parts) != 3 or parts[0] == "PID":
            continue
        pid_word, status_word, label = parts
        if pid_word != "-" and _int(pid_word) is None:
            continue
        rows[label.strip()] = Listed(_int(pid_word), _int(status_word))
    return rows


def listed() -> dict[str, Listed]:
    """Every job launchd lists for this shell. Raises Unreachable or Failed."""
    ran = launchctl("list")
    if ran.rc != 0:
        raise Failed(ran.words)
    return parse_list(ran.out)


@dataclass(frozen=True)
class Printed:
    """The fields the long form reads from `launchctl print`. Each is None
    when print did not say it."""

    pid: int | None = None
    state: str | None = None
    runs: int | None = None
    exit_code: int | None = None
    never_exited: bool = False
    signal: int | None = None
    signal_name: str | None = None


_PRINT_FIELDS = {
    "pid": re.compile(r"^\s*pid = (\d+)\s*$", re.MULTILINE),
    "state": re.compile(r"^\s*state = (\S.*?)\s*$", re.MULTILINE),
    "runs": re.compile(r"^\s*runs = (\d+)\s*$", re.MULTILINE),
}
_EXIT = re.compile(r"^\s*last exit code = (.+?)\s*$", re.MULTILINE)
_SIGNAL = re.compile(r"^\s*last terminating signal = (.+?):\s*(\d+)\s*$", re.MULTILINE)


def parse_print(text: str) -> Printed:
    """The three forms of the last exit: `last exit code = N`, `last exit
    code = (never exited)`, and `last terminating signal = <words>: N`. Any
    other form leaves the field out."""
    found: dict = {}
    for key, pattern in _PRINT_FIELDS.items():
        m = pattern.search(text)
        if m:
            found[key] = int(m.group(1)) if key in ("pid", "runs") else m.group(1)
    m = _EXIT.search(text)
    if m:
        value = m.group(1)
        if value == "(never exited)":
            found["never_exited"] = True
        elif _int(value) is not None:
            found["exit_code"] = int(value)
    m = _SIGNAL.search(text)
    if m:
        found["signal_name"] = m.group(1).strip()
        found["signal"] = int(m.group(2))
    return Printed(**found)


def printed(label: str) -> Printed | None:
    """`launchctl print gui/<uid>/<label>`, parsed; None when launchd has no
    such job loaded. Raises Unreachable."""
    ran = launchctl("print", target(label))
    if ran.rc != 0:
        return None
    return parse_print(ran.out)


def agents_dir(home: Path | None = None) -> Path:
    return (home or Path.home()) / "Library" / "LaunchAgents"


def plist_path(label: str, home: Path | None = None) -> Path:
    return agents_dir(home) / f"{label}.plist"


def plist(label: str, home: Path | None = None) -> dict | None:
    """The job's plist on disk, or None when it is not there or not readable."""
    try:
        with plist_path(label, home).open("rb") as f:
            data = plistlib.load(f)
    except (OSError, plistlib.InvalidFileException, ValueError):
        return None
    return data if isinstance(data, dict) else None


def plist_labels(home: Path | None = None) -> list[str]:
    """The labels of every kit plist on disk: ~/Library/LaunchAgents/dev.sessionkit.*.plist."""
    try:
        return sorted(
            p.name[: -len(".plist")] for p in agents_dir(home).glob(f"{PREFIX}*.plist")
        )
    except OSError:
        return []


def kickstart(label: str) -> Ran:
    """`launchctl kickstart -k gui/<uid>/<label>`: stop the job if it runs and
    start it again. Writes no file. Raises Unreachable."""
    return launchctl("kickstart", "-k", target(label))
