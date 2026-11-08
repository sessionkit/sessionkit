"""`sessionkit service`: the kit's services, found from their files.

A service is a JSON file under ~/.sessionkit/<package>/services/, at one of
two depths: `<name>.json`, or `<group>/<agent>.json` for one per agent. Its
top-level `"service"` key is an integer, the marker no other settings file
carries. The kit walks the tree and keeps no list of what is in or out: a
package adds a service by writing a file. Each package's own install writes
its files; the kit writes none.

launchd adds state, never discovery (launchd.py). The one use of the
`dev.sessionkit.` prefix is the transition: a kit job that no file claims
yet is still listed in its package's group, and a footer counts such jobs.

Everything here reads. The one write `sessionkit service` makes is
`launchctl kickstart -k` (restart), which changes what runs, not any file.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from pathlib import Path

from sessionkit import launchd

SCHEMA_VERSION = 1
PACKAGES = ("kit", "mail", "phone", "tools", "view", "voice")
REQUIRED = ("service", "name", "enabled", "install")
KINDS = ("daemon", "on-demand")
DEFAULT_ORDER = 50
WIDTH = 53

UP, IDLE, OFF, DOWN, DISABLED, MANUAL, BAD, STRAY = (
    "up",
    "idle",
    "off",
    "down",
    "disabled",
    "manual",
    "bad file",
    "stray",
)
STATE_ORDER = (UP, IDLE, OFF, MANUAL, DOWN, DISABLED, STRAY, BAD)
GLYPH_UP, GLYPH_REST, GLYPH_FAULT = "●", "○", "✕"

LEGEND = (
    "● up: running",
    "○ idle: an on-demand job, waiting (healthy)",
    "○ off: switched off by its owner",
    "○ down: loaded, not running, last exit 0",
    "○ disabled: its file says enabled: false",
    "○ manual: runs in the foreground; the kit never starts it",
    "✕ down: not running after a non-zero exit, not loaded, or not installed",
    "✕ stray: loaded, with no plist on disk",
    "✕ bad file: a service file the kit cannot use",
)


def root(home: Path | None = None) -> Path:
    """The kit's tree. Fixed at ~/.sessionkit: no variable moves it."""
    return (home or Path.home()) / ".sessionkit"


# --- The files ---------------------------------------------------------------


def walk(base: Path) -> list[Path]:
    """Every .json file at the two depths under BASE/<package>/services/.
    Reads nothing else: settings/, deeper folders and other names are skipped."""
    try:
        found = list(base.glob("*/services/*.json")) + list(
            base.glob("*/services/*/*.json")
        )
    except OSError:
        return []
    return sorted(p for p in found if p.is_file())


def _is_marker(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def check(data, package: str) -> list[str]:
    """What is wrong with a service file's DATA, read from PACKAGE's folder.
    An empty list means the file can be used. Never raises."""
    if not isinstance(data, dict):
        return ["not a JSON object"]
    problems = [f"no `{key}`" for key in REQUIRED if key not in data]
    name = data.get("name")
    if "name" in data and (not isinstance(name, str) or not name.strip()):
        problems.append("`name` is not a word")
    elif isinstance(name, str) and name in PACKAGES:
        problems.append(f"`name` is a group's name: {name}")
    if "enabled" in data and not isinstance(data["enabled"], bool):
        problems.append("`enabled` is not true or false")
    if "install" in data and not isinstance(data["install"], str):
        problems.append("`install` is not a string")
    has_label, has_run = "label" in data, "run" in data
    if has_label and has_run:
        problems.append("both `label` and `run`")
    elif not has_label and not has_run:
        problems.append("no `label` or `run`")
    elif has_label:
        label = data["label"]
        prefix = f"{launchd.PREFIX}{package}."
        if (
            not isinstance(label, str)
            or not label.startswith(prefix)
            or label == prefix
        ):
            problems.append(f"`label` is not under {prefix}")
    else:
        run = data["run"]
        if (
            not isinstance(run, list)
            or not run
            or not all(isinstance(w, str) for w in run)
        ):
            problems.append("`run` is not a list of words")
    return problems


@dataclass
class ServiceFile:
    """One file found by the walk."""

    path: Path
    package: str
    data: dict = field(default_factory=dict)
    problems: list[str] = field(default_factory=list)
    marked: bool = True  # carries the "service" marker (or could not be read)
    notes: list[str] = field(default_factory=list)

    @property
    def name(self) -> str:
        name = self.data.get("name")
        return name if isinstance(name, str) and name.strip() else self.path.stem

    @property
    def label(self) -> str | None:
        label = self.data.get("label")
        return label if isinstance(label, str) else None


def load(path: Path, base: Path) -> ServiceFile:
    """Read one file. Never raises: a file the kit cannot use carries its
    problems, and a JSON file with no marker is `marked=False`."""
    package = path.relative_to(base).parts[0]
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError):
        return ServiceFile(path, package, problems=["cannot be read"])
    except ValueError:
        return ServiceFile(path, package, problems=["not JSON"])
    if not isinstance(data, dict) or not _is_marker(data.get("service")):
        return ServiceFile(
            path, package, data if isinstance(data, dict) else {}, marked=False
        )
    sf = ServiceFile(path, package, data, check(data, package))
    if data["service"] != SCHEMA_VERSION:
        sf.notes.append(f"schema {data['service']}, read as {SCHEMA_VERSION}")
    label = sf.label
    if not sf.problems and label and label != f"{launchd.PREFIX}{package}.{sf.name}":
        sf.notes.append("name is not its label's tail")
    return sf


def load_all(base: Path) -> list[ServiceFile]:
    """Every file under BASE, read. Two files that declare one name are both
    bad, each naming the other."""
    files = [load(p, base) for p in walk(base)]
    by_name: dict[str, list[ServiceFile]] = {}
    for sf in files:
        if sf.marked and "name" in sf.data:
            by_name.setdefault(sf.name, []).append(sf)
    for same in by_name.values():
        if len(same) > 1:
            for sf in same:
                others = ", ".join(str(o.path) for o in same if o is not sf)
                sf.problems.append(f"name also in {others}")
    return files


# --- Rows: a file joined with launchd ----------------------------------------


@dataclass
class Row:
    """One service as `list` shows it."""

    name: str
    package: str
    state: str
    glyph: str
    note: str = ""
    label: str | None = None
    file: Path | None = None
    data: dict = field(default_factory=dict)
    enabled: bool | None = None
    loaded: bool = False
    pid: int | None = None
    status: int | None = None
    plist: Path | None = None
    installed: bool = False
    kind: str = "daemon"

    @property
    def order(self) -> int:
        order = self.data.get("order", DEFAULT_ORDER)
        return order if _is_marker(order) else DEFAULT_ORDER

    @property
    def hazard(self) -> bool:
        """A stop or restart could drop a live call. A job with no file
        counts as one: the doubt refuses."""
        if self.file is None:
            return True
        hazard = self.data.get("hazard")
        return isinstance(hazard, list) and "call" in hazard

    @property
    def fullname(self) -> str:
        return f"{self.package}.{self.name}"


def _exit_words(status: int | None) -> str:
    if status is None:
        return ""
    return f"signal {-status}" if status < 0 else f"exited {status}"


def _switched_off(plist: dict | None) -> bool:
    keep = (plist or {}).get("KeepAlive")
    return isinstance(keep, dict) and keep.get("SuccessfulExit") is False


def _plist_kind(plist: dict | None) -> str:
    return "daemon" if plist and "KeepAlive" in plist else "on-demand"


def _launchd_state(
    listed: launchd.Listed | None,
    plist: dict | None,
    kind: str,
    enabled: bool,
    hint: str,
) -> tuple[str, str, str]:
    """(glyph, state, note) for a job launchd may have, from the §1.5 table."""
    if listed and listed.pid is not None:
        return GLYPH_UP, UP, "" if enabled else "file says disabled"
    if not enabled:
        return GLYPH_REST, DISABLED, ""
    if listed:
        if listed.status:
            return GLYPH_FAULT, DOWN, _exit_words(listed.status)
        if kind == "on-demand":
            return GLYPH_REST, IDLE, ""
        if _switched_off(plist):
            return GLYPH_REST, OFF, "switched off"
        return GLYPH_REST, DOWN, ""
    if plist is not None:
        return GLYPH_FAULT, DOWN, "not loaded"
    return GLYPH_FAULT, DOWN, hint


def file_row(
    sf: ServiceFile, listed: dict[str, launchd.Listed], home: Path | None
) -> Row:
    row = Row(sf.name, sf.package, BAD, GLYPH_FAULT, file=sf.path, data=sf.data)
    if sf.problems:
        row.note = sf.problems[0]
        return row
    row.enabled = sf.data["enabled"]
    kind = sf.data.get("kind")
    row.kind = kind if kind in KINDS else "daemon"
    if "run" in sf.data:
        row.glyph, row.state = GLYPH_REST, MANUAL
        row.note = "runs in the foreground: " + " ".join(sf.data["run"])
        return row
    label = sf.label
    row.label = label
    job = listed.get(label)
    row.loaded = job is not None
    row.pid, row.status = (job.pid, job.status) if job else (None, None)
    row.plist = launchd.plist_path(label, home)
    plist = launchd.plist(label, home)
    row.installed = plist is not None or row.plist.exists()
    hint = f"not installed: {sf.data['install']}"
    row.glyph, row.state, row.note = _launchd_state(
        job, plist, row.kind, row.enabled, hint
    )
    if not row.note and sf.notes:
        row.note = sf.notes[0]
    return row


def split_label(label: str) -> tuple[str, str]:
    """(package, name) from a kit label: dev.sessionkit.<package>.<name>."""
    rest = label[len(launchd.PREFIX) :]
    package, _, name = rest.partition(".")
    return (package, name) if name else ("kit", rest)


def transition_row(label: str, job: launchd.Listed | None, home: Path | None) -> Row:
    """A kit job that no file claims yet: listed from launchd alone."""
    package, name = split_label(label)
    plist = launchd.plist(label, home)
    path = launchd.plist_path(label, home)
    row = Row(name, package, DOWN, GLYPH_FAULT, label=label, plist=path)
    row.loaded = job is not None
    row.pid, row.status = (job.pid, job.status) if job else (None, None)
    row.installed = plist is not None or path.exists()
    row.kind = _plist_kind(plist)
    if job is not None and not row.installed:
        row.glyph, row.state, row.note = GLYPH_FAULT, STRAY, "no plist on disk"
        return row
    row.glyph, row.state, row.note = _launchd_state(
        job, plist, row.kind, True, "not installed"
    )
    return row


@dataclass
class Survey:
    """Everything `list` shows: the rows, and the footer's two counts."""

    rows: list[Row]
    unmarked: dict[str, int]  # package -> JSON files in services/ with no marker
    transition: int  # kit jobs with no file yet

    @property
    def footer(self) -> list[str]:
        lines = []
        for package, n in sorted(self.unmarked.items()):
            files = "1 file" if n == 1 else f"{n} files"
            verb = "is not a service file" if n == 1 else "are not service files"
            lines.append(f"{files} in {package}/services/ {verb}.")
        if self.transition:
            jobs = (
                "1 job has" if self.transition == 1 else f"{self.transition} jobs have"
            )
            lines += [
                f"{jobs} no service file yet.",
                "status NAME says whose install writes it.",
            ]
        return lines


def sort_key(row: Row) -> tuple:
    return (row.package, row.name)


def survey(
    home: Path | None = None, listed: dict[str, launchd.Listed] | None = None
) -> Survey:
    """The rows `list` shows. LISTED is `launchctl list` (read here when
    None; raises launchd.Unreachable or launchd.Failed)."""
    if listed is None:
        listed = launchd.listed()
    files = load_all(root(home))
    rows, unmarked, claimed = [], {}, set()
    for sf in files:
        if not sf.marked:
            unmarked[sf.package] = unmarked.get(sf.package, 0) + 1
            continue
        if sf.label:
            claimed.add(sf.label)
        rows.append(file_row(sf, listed, home))
    kit_jobs = {label for label in listed if label.startswith(launchd.PREFIX)}
    kit_jobs |= set(launchd.plist_labels(home))
    loose = sorted(kit_jobs - claimed)
    rows += [transition_row(label, listed.get(label), home) for label in loose]
    rows.sort(key=sort_key)
    return Survey(rows, unmarked, len(loose))


# --- Names, groups and `all` -------------------------------------------------


class Ambiguous(Exception):
    """A word that names more than one service."""


class Unknown(Exception):
    """A word that names no service and no group."""


def groups(rows: Iterable[Row]) -> list[str]:
    return sorted({r.package for r in rows})


def resolve(words: Iterable[str], rows: list[Row]) -> list[Row]:
    """The rows WORDS name, each once, in the order first named. A word is,
    in this order: `all`, a full label, a group (a package), a name, or
    `<package>.<name>`. Raises Unknown or Ambiguous."""
    chosen: list[Row] = []

    def take(found: Iterable[Row]) -> None:
        for row in found:
            if not any(row is c for c in chosen):
                chosen.append(row)

    for word in words:
        if word == "all":
            take(rows)
            continue
        for key in ("label", "package", "name", "fullname"):
            found = [r for r in rows if getattr(r, key) == word]
            if found:
                break
        else:
            raise Unknown(word)
        is_group = all(r.package == word for r in found)
        if len(found) > 1 and not is_group:
            where = "; ".join(f"{r.fullname} ({r.file or r.label})" for r in found)
            raise Ambiguous(f"{word} names {len(found)} services: {where}")
        take(found)
    return chosen


def candidates(rows: list[Row]) -> list[str]:
    """Every word a verb takes, for completion: names, groups and `all`."""
    return sorted({r.name for r in rows} | set(groups(rows))) + ["all"]


# --- Rendering ---------------------------------------------------------------


def _cut(text: str, room: int) -> str:
    if room <= 0:
        return ""
    return text if len(text) <= room else text[: room - 1] + "…"


def heading(package: str, rows: list[Row]) -> str:
    counts = {s: sum(1 for r in rows if r.state == s) for s in STATE_ORDER}
    parts = [f"{n} {s}" for s, n in counts.items() if n]
    return f"{package}  " + " · ".join(parts)


def render(survey: Survey, width: int = WIDTH) -> list[str]:
    """`list`, grouped by package, A-Z, every line at most WIDTH columns."""
    if not survey.rows:
        lines = ["No services found under ~/.sessionkit."]
        return lines + survey.footer
    namew = max(len(r.name) for r in survey.rows)
    statew = max(len(r.state) for r in survey.rows)
    lines: list[str] = []
    for package in groups(survey.rows):
        rows = [r for r in survey.rows if r.package == package]
        lines.append(_cut(heading(package, rows), width))
        for r in rows:
            name = r.name if 4 + len(r.name) <= width else _cut(r.name, width - 4)
            line = f"  {r.glyph} {name:<{max(namew, len(name))}}  {r.state:<{statew}}"
            if len(line) > width:  # a name too long for the columns: no padding
                line = f"  {r.glyph} {name}  {r.state}"
            line = _cut(line.rstrip(), width)
            if r.note:
                room = width - len(line) - 2
                if room >= 4:
                    line = f"{line}  {_cut(r.note, room)}"
            lines.append(line)
    return lines + survey.footer


def as_json(rows: list[Row]) -> list[dict]:
    """One object per row, the same fields for every row."""
    out = []
    for r in rows:
        out.append(
            {
                "name": r.name,
                "group": r.package,
                "label": r.label,
                "state": r.state,
                "note": r.note,
                "enabled": r.enabled,
                "loaded": r.loaded,
                "pid": r.pid,
                "last_status": r.status,
                "installed": r.installed,
                "kind": r.kind,
                "hazard": ["call"] if r.hazard else [],
                "file": str(r.file) if r.file else None,
                "plist": str(r.plist) if r.plist else None,
                "install": r.data.get("install") if r.file else None,
            }
        )
    return out


# --- The long form -----------------------------------------------------------


def last_exit(printed: launchd.Printed | None, status: int | None) -> str:
    """The last exit in words, from `print` first, else from `list`'s Status."""
    if printed is not None:
        if printed.signal is not None:
            name = f" ({printed.signal_name})" if printed.signal_name else ""
            return f"signal {printed.signal}{name}"
        if printed.exit_code is not None:
            return str(printed.exit_code)
        if printed.never_exited:
            return "never exited"
    if status is None:
        return ""
    return f"signal {-status}" if status < 0 else str(status)


Listen = Callable[[int, str], list[str] | None]


def lsof_listen(port: int, protocol: str = "tcp") -> list[str] | None:
    """The addresses something listens on at PORT, from lsof; None when lsof
    cannot say. Read-only."""
    lsof = shutil.which("lsof")
    if not lsof:
        return None
    args = [lsof, "-nP", f"-i{protocol.upper()}:{port}"]
    if protocol == "tcp":
        args.append("-sTCP:LISTEN")
    try:
        done = subprocess.run(
            args, capture_output=True, text=True, timeout=10, check=False
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    found = []
    for line in done.stdout.splitlines()[1:]:
        parts = line.split()
        address = next((p for p in parts if p.endswith(f":{port}")), None)
        if address and address not in found:
            found.append(address)
    return found


def _logs(row: Row, plist: dict | None) -> list[str]:
    paths = []
    for key in ("StandardOutPath", "StandardErrorPath"):
        p = (plist or {}).get(key)
        if isinstance(p, str) and p not in paths:
            paths.append(p)
    extra = row.data.get("logs")
    if isinstance(extra, list):
        paths += [str(p) for p in extra if isinstance(p, str) and str(p) not in paths]
    return paths


def long_form(
    row: Row,
    printed: launchd.Printed | None = None,
    home: Path | None = None,
    listen: Listen | None = None,
) -> list[str]:
    """`status NAME`: one field per line. LISTEN finds who listens on a
    port (default: lsof)."""
    listen = listen or lsof_listen
    lines = [f"name: {row.fullname}"]
    if row.label:
        lines.append(f"label: {row.label}")
    if row.file:
        lines.append(f"file: {row.file}")
    else:
        lines.append(f"file: none yet ({row.package}'s install writes it)")
    if row.enabled is not None:
        lines.append(f"enabled: {'yes' if row.enabled else 'no'}")
    state = f"state: {row.glyph} {row.state}"
    lines.append(f"{state} ({row.note})" if row.note else state)
    if row.label:
        lines.append(f"kind: {row.kind}")
        pid = printed.pid if printed and printed.pid else row.pid
        lines.append(f"pid: {pid if pid else '-'}")
        exit_words = last_exit(printed, row.status)
        if exit_words:
            lines.append(f"last exit: {exit_words}")
        if printed and printed.runs is not None:
            lines.append(f"runs: {printed.runs}")
    port = row.data.get("port")
    if _is_marker(port):
        protocol = row.data.get("protocol", "tcp")
        protocol = protocol if protocol in ("tcp", "udp") else "tcp"
        bind = row.data.get("bind", "127.0.0.1")
        lines.append(f"port: {port}/{protocol}, bind {bind}")
        heard = listen(port, protocol)
        if heard is not None:
            lines.append(
                f"listening: {', '.join(heard) if heard else 'nothing on that port'}"
            )
    if row.plist:
        lines.append(f"plist: {row.plist}{'' if row.installed else ' (not on disk)'}")
    plist = launchd.plist(row.label, home) if row.label else None
    for path in _logs(row, plist):
        lines.append(f"log: {path}")
    for key in ("install", "uninstall", "description", "note"):
        value = row.data.get(key) if row.file else None
        if isinstance(value, str) and value:
            lines.append(f"{key}: {value}")
    if row.file is None and row.label:
        lines.append(f"owner: the {row.package} package")
    return lines


# --- The call guard ----------------------------------------------------------


def phone_bot_envs(
    home: Path | None = None, loaded: Iterable[str] = ()
) -> tuple[list[dict], list[str]]:
    """(envs, strays) for the phone bots of this Mac. ENVS is the environment
    each bot runs with: its plist's EnvironmentVariables, read from
    ~/Library/LaunchAgents, which the running bot read at its start. As in
    sessionphone's own guard, this shell's environment stands in only when
    bot plists are there and not one of them reads. STRAYS are the LOADED
    labels (launchd lists them) with no plist on disk: their environment
    cannot be read at all."""
    bot = f"{launchd.PREFIX}phone.bot."
    on_disk = [label for label in launchd.plist_labels(home) if label.startswith(bot)]
    envs = []
    for label in on_disk:
        env = (launchd.plist(label, home) or {}).get("EnvironmentVariables")
        if isinstance(env, dict) and env:
            envs.append(env)
    if on_disk and not envs:
        envs = [dict(os.environ)]
    strays = sorted({label for label in loaded if label.startswith(bot)} - set(on_disk))
    return envs, strays


def phone_service():
    """sessionphone's service module, imported only when a phone bot exists.
    Its `live_call(env)` is the read-only check sessionphone's own uninstall
    runs; the tests replace this function."""
    from sessionphone import service

    return service


def live_calls(home: Path | None = None, loaded: Iterable[str] = ()) -> list[str]:
    """One line per live call on a phone bot of this Mac, by sessionphone's
    own read-only check. A check that cannot run counts as a call: dropping
    a call is the harm, so the doubt refuses. So does a bot launchd has
    loaded (LOADED, the labels it lists) whose plist is gone: its
    environment cannot be read. No phone bot, no call."""
    envs, strays = phone_bot_envs(home, loaded)
    doubts = [
        f"cannot check for a call: {label} is loaded but its plist is gone"
        for label in strays
    ]
    if not envs:
        return doubts
    try:
        phone = phone_service()
    except Exception as e:  # noqa: BLE001 - any failure is a doubt
        return doubts + [
            f"cannot check for a call: sessionphone does not load ({e.__class__.__name__})"
        ]
    bad = getattr(getattr(phone, "settings", None), "Bad", ())
    calls = doubts
    for env in envs:
        try:
            call = phone.live_call(env)
        except Exception as e:  # noqa: BLE001
            if bad and isinstance(e, bad):
                continue  # no root to look in: no bot of this job's runs there
            calls.append(f"cannot check for a call: {e.__class__.__name__}: {e}")
            continue
        if call is not None:
            line = getattr(phone, "_call_line", None)
            calls.append(line(call) if line else f"a call is live ({call.get('path')})")
    return calls
