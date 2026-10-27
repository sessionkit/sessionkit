"""`sessionkit setup` writes the operator from config, never a name (SK-70).

Every test runs in a temp HOME with a PATH holding only two fake programs:

- `session`: a small model of sessiontools' `session operator`. It reads the
  host layer (`session.json`, then `session.d/*.json`), merges `operator`
  maps key by key, reads as NOTHING CONFIGURED when any file there is bad,
  and, like sessiontools, lets AGENT_OPERATOR_ADDR fill the `operator` (ask
  address) field without granting privilege. A mode file switches it to
  absent-verb (exit 2), garbage, "disagree" or slow. It also answers
  `session start --list-agents` by sessiontools' agents-folder rule; a
  `session.agents` file switches that to `absent` (exit 2) or `empty`.
  `session agent default` prints the default seat's name, as sessiontools'
  verb does (one word, a newline, exit 0): `claude`, or the word in a
  `session.seat` file; `absent` (exit 2), `error` (exit 1), `garbage` (two
  lines) and `slow` switch it.
- `message`: `message box path NAME` exits 0 when `$HOME/.mail/agents/NAME`
  is a maildir (`new/`, `cur/`, `tmp/`: a bare directory is no box to the
  real `message`), else 2. A mode file switches it to exit 3 or slow.
  `message setup` is a FAKE of sessionmail's mail setup verb: by default it
  answers `--help`, prints one DONE line and exits 0, making nothing. A
  `message.setup` file switches it: `absent` (0.1.0: "No such command",
  exit 2, `--help` too), `left` (4), `failed` (1), `refused` (2), `weird`
  (9), `slow`, or `makes-boxes` (makes the root, the account's box named in
  `message.account` (or `operator.mailbox` when the host layer sets it),
  and each `--box`, like the real verb). Every call's
  argv is logged, one JSON list a line, to `message.calls`.

Setup is never run against a real HOME (S7).
"""

from __future__ import annotations

import ast
import json
import os
import re
import stat
import sys
import time
import tomllib
from pathlib import Path
from types import SimpleNamespace

import _scanlist
import pytest
from click.testing import CliRunner

from sessionkit import setup as setup_mod
from sessionkit.cli import main

ROOT = Path(__file__).resolve().parent.parent

FAKE_SESSION = r"""
import json, os, sys, time
from pathlib import Path
mode_file = Path(__file__).with_name("session.mode")
mode = mode_file.read_text().strip() if mode_file.exists() else "model"
if sys.argv[1:] == ["agent", "default"]:
    seat_file = Path(__file__).with_name("session.seat")
    seat = seat_file.read_text().strip() if seat_file.exists() else "claude"
    if seat == "absent":
        print("session: unknown verb 'agent'", file=sys.stderr)
        sys.exit(2)
    if seat == "error":
        print("session agent: broken install", file=sys.stderr)
        sys.exit(1)
    if seat == "garbage":
        print("claude\nclaude")
        sys.exit(0)
    if seat == "slow":
        time.sleep(30)
    print(seat)
    sys.exit(0)
if sys.argv[1:] == ["start", "--list-agents"]:
    agents_file = Path(__file__).with_name("session.agents")
    agents = agents_file.read_text().strip() if agents_file.exists() else "model"
    if agents == "absent":
        print("session: unknown verb 'start'", file=sys.stderr)
        sys.exit(2)
    if agents == "empty":
        sys.exit(0)
    dot = Path(os.environ["HOME"]) / ".session"
    if os.environ.get("AGENTS_DIR"):
        root = Path(os.path.expanduser(os.environ["AGENTS_DIR"]))
    elif (dot / "agent" / "config").is_dir():
        root = dot / "agent" / "config"
    else:
        root = dot / "agents"
    names = set()
    for entry in (root.iterdir() if root.is_dir() else ()):
        if entry.name.startswith("."):
            continue
        if entry.is_dir() and (entry / (entry.name + ".md")).is_file():
            names.add(entry.name)
        elif not entry.is_dir() and entry.name.endswith(".md"):
            names.add(entry.name[:-3])
    print("\n".join(sorted(names)))
    sys.exit(0)
if sys.argv[1:] != ["operator"] or mode == "exit2":
    print("session: unknown verb 'operator'", file=sys.stderr)
    sys.exit(2)
if mode == "garbage":
    print("not json")
    sys.exit(0)
if mode == "slow":
    time.sleep(5)
nothing = {"operator": None, "mailbox": None, "privileged": []}
if mode == "disagree":
    print(json.dumps(nothing))
    sys.exit(0)
tool = Path(os.environ["HOME"]) / ".sessionkit" / "tools" / "settings"
files = [tool / "session.json"] if (tool / "session.json").is_file() else []
if (tool / "session.d").is_dir():
    files += sorted(p for p in (tool / "session.d").iterdir()
                    if p.is_file() and p.suffix == ".json")
def merge(into, more):
    for k, v in more.items():
        if isinstance(v, dict) and isinstance(into.get(k), dict):
            merge(into[k], v)
        else:
            into[k] = v
block = {}
try:
    for f in files:
        data = json.loads(f.read_text())
        if not isinstance(data, dict):
            raise ValueError(f)
        if isinstance(data.get("operator"), dict):
            merge(block, data["operator"])
except Exception:
    block = {}
mailbox = block.get("mailbox") or None
address = block.get("address") or None
privileged = set(block.get("privileged") or [])
privileged.update(n for n in (address, mailbox) if n)
override = os.environ.get("AGENT_OPERATOR_ADDR") or None
print(json.dumps({"operator": override or address, "mailbox": mailbox,
                  "privileged": sorted(privileged)}))
"""

FAKE_MESSAGE = r"""
import json, os, sys, time
from pathlib import Path
here = Path(__file__)
with open(here.with_name("message.calls"), "a") as log:
    log.write(json.dumps(sys.argv[1:]) + "\n")
mode_file = here.with_name("message.mode")
mode = mode_file.read_text().strip() if mode_file.exists() else "real"
if mode == "exit3":
    sys.exit(3)
if mode == "slow":
    time.sleep(5)
if sys.argv[1:2] == ["setup"]:
    setup_file = here.with_name("message.setup")
    setup = setup_file.read_text().strip() if setup_file.exists() else "done"
    if setup == "absent":
        print("Error: No such command 'setup'.", file=sys.stderr)
        sys.exit(2)
    if sys.argv[2:] == ["--help"]:
        print("Usage: message setup [--box NAME]... [--dry-run]")
        sys.exit(0)
    if setup == "slow":
        time.sleep(5)
    if setup == "left":
        print("  notmuch-hook  BLOCKED  run notmuch new once")
        print("message setup: done what it can; 1 step(s) left for you", file=sys.stderr)
        sys.exit(4)
    if setup == "failed":
        print("message setup: box:x failed", file=sys.stderr)
        sys.exit(1)
    if setup == "refused":
        print("message setup: REFUSED - nothing was applied", file=sys.stderr)
        sys.exit(2)
    if setup == "weird":
        sys.exit(9)
    if setup == "makes-boxes" and "--dry-run" in sys.argv:
        # A fresh host, as measured on the real verb: a dry run applies
        # nothing and exits 4 while any step is still to do.
        print("  box:" + here.with_name("message.account").read_text().strip()
              + "  TODO  make the box")
        print("dry run: nothing applied (1 step(s) TODO)")
        sys.exit(4)
    if setup == "makes-boxes":
        # The operator's box as the real verb picks it: `operator.mailbox`
        # from the host layer, else (no `operator` key at all) the account's
        # name, case-folded.
        tool = Path(os.environ["HOME"]) / ".sessionkit" / "tools" / "settings"
        layers = [tool / "session.json"] if (tool / "session.json").is_file() else []
        if (tool / "session.d").is_dir():
            layers += sorted(p for p in (tool / "session.d").iterdir()
                             if p.is_file() and p.suffix == ".json")
        blocks = [json.loads(f.read_text()) for f in layers]
        blocks = [b["operator"] for b in blocks if "operator" in b]
        if blocks:
            mailbox = None
            for b in blocks:
                if isinstance(b, dict) and b.get("mailbox"):
                    mailbox = b["mailbox"].strip()
            boxes = [mailbox] if mailbox else []
        else:
            boxes = [here.with_name("message.account").read_text().strip().casefold()]
        args = sys.argv[2:]
        boxes += [args[i + 1] for i, a in enumerate(args) if a == "--box"]
        for name in boxes:
            for sub in ("new", "cur", "tmp"):
                (Path(os.environ["HOME"]) / ".mail" / "agents" / name / sub).mkdir(
                    parents=True, exist_ok=True)
    print("message setup: every step DONE")
    sys.exit(0)
if sys.argv[1:3] != ["box", "path"] or len(sys.argv) != 4:
    sys.exit(2)
box = Path(os.environ["HOME"]) / ".mail" / "agents" / sys.argv[3]
if all((box / sub).is_dir() for sub in ("new", "cur", "tmp")):
    print(box)
    sys.exit(0)
print(f"message box path: no box {sys.argv[3]!r}", file=sys.stderr)
sys.exit(2)
"""

STRANGER = "stranger"
ABOUT = setup_mod.ABOUT


class Rig(SimpleNamespace):
    """The temp HOME, the fake bin dir, and helpers over them."""

    def box(self, name: str) -> None:
        for sub in ("new", "cur", "tmp"):
            (self.home / ".mail" / "agents" / name / sub).mkdir(parents=True)

    def mode(self, program: str, mode: str) -> None:
        (self.bin / f"{program}.mode").write_text(mode)

    def remove(self, program: str) -> None:
        (self.bin / program).unlink()

    def seat(self, word: str) -> None:
        """What the fake `session agent default` answers (module docstring)."""
        (self.bin / "session.seat").write_text(word)

    def setup_mode(self, mode: str) -> None:
        """Switch the fake `message setup` (see the module docstring)."""
        (self.bin / "message.setup").write_text(mode)

    def calls(self) -> list[list[str]]:
        """Every argv the fake `message` was called with, in order."""
        log = self.bin / "message.calls"
        if not log.exists():
            return []
        return [json.loads(line) for line in log.read_text().splitlines()]

    def setup_calls(self) -> list[list[str]]:
        """The fake verb's runs, its `--help` probes left out."""
        return [c for c in self.calls() if c[:1] == ["setup"] and c[1:] != ["--help"]]

    @property
    def settings(self) -> Path:
        return setup_mod.settings_dir_for(self.home)

    @property
    def target(self) -> Path:
        return setup_mod.operator_drop_in(self.home)

    def seed(self, relpath: str, text: str) -> Path:
        path = self.settings / relpath
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        return path

    def files(self) -> list[Path]:
        """Every file under the temp HOME's settings dir."""
        if not self.settings.exists():
            return []
        return sorted(p for p in self.settings.rglob("*") if p.is_file())

    def run(self, *args: str):
        return CliRunner().invoke(main, ["setup", *args])

    @property
    def agents(self) -> Path:
        """The agents folder `session start` reads, under the temp HOME."""
        return setup_mod.agents_root(self.home, os.environ)

    def agent(self, name: str = setup_mod.DEFAULT_AGENT) -> Path:
        """NAME's agent file, flat layout: the one setup writes."""
        return self.agents / f"{name}.md"


@pytest.fixture
def rig(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Rig:
    home = tmp_path / "home"
    home.mkdir()
    bindir = tmp_path / "bin"
    bindir.mkdir()
    for name, body in (("session", FAKE_SESSION), ("message", FAKE_MESSAGE)):
        script = bindir / name
        script.write_text(f"#!{sys.executable}\n{body}")
        script.chmod(0o755)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("PATH", str(bindir))
    for var in ("AGENT_OPERATOR_ADDR", "USER", "LOGNAME", "MAIL", "AGENTS_DIR"):
        monkeypatch.delenv(var, raising=False)
    account = SimpleNamespace(pw_name=STRANGER)
    monkeypatch.setattr(setup_mod, "pwd", SimpleNamespace(getpwuid=lambda uid: account))
    assert Path.home() == home
    return Rig(home=home, bin=bindir, account=account)


def expected(block: dict) -> str:
    return json.dumps({"_about": ABOUT, "operator": block}, indent=2) + "\n"


def agent_step_lines(
    rig: Rig, name: str = setup_mod.DEFAULT_AGENT, seat: str | None = "claude"
) -> list[str]:
    """What a real run's agent half prints on a fresh home: the write, the
    verify, the launch step (bare when NAME is the rig's seat, `claude`)."""
    return [
        f"Wrote {rig.agent(name)}: the agent {name!r}, not keyed.",
        f"session start --list-agents: lists {name!r}.",
        setup_mod.launch_sentence(name, seat),
    ]


def no_ears_line(name: str) -> str:
    """The wake seat's one line when `ears` is not on the PATH."""
    return (
        "No wake seat added: `ears` is not on the PATH. "
        f"Once it is, run: ears wake add {name}"
    )


def assert_nothing_written(rig: Rig, before: list[Path] | None = None) -> None:
    assert rig.files() == (before or [])
    assert not rig.target.exists()


def assert_no_stray_json(rig: Rig) -> list[str]:
    """F2: no temp file is left in session.d; returns what IS there."""
    drop_ins = rig.settings / setup_mod.DROP_IN_DIR
    if not drop_ins.exists():
        return []
    names = sorted(p.name for p in drop_ins.iterdir())
    assert [n for n in names if ".tmp-" in n] == []
    return names


# --- S1: a stranger who names themselves gets exactly that operator ----------


def test_the_account_box_that_exists_is_written_exactly(rig: Rig) -> None:
    rig.box(STRANGER)
    result = rig.run()
    assert result.exit_code == 0, result.output
    assert rig.files() == [rig.target]
    assert rig.target.read_text() == expected({"mailbox": STRANGER})
    data = json.loads(rig.target.read_text())
    assert "privileged" not in data["operator"]  # R2
    assert "session operator:" in result.output  # verified through the model
    assert assert_no_stray_json(rig) == ["10-operator.json"]


def test_a_named_box_that_exists_is_written(rig: Rig) -> None:
    rig.box("someone")
    result = rig.run("--mailbox", "someone")
    assert result.exit_code == 0, result.output
    assert rig.target.read_text() == expected({"mailbox": "someone"})


def test_an_address_is_written_and_needs_no_box(rig: Rig) -> None:
    result = rig.run("--address", "someone@stranger.test")
    assert result.exit_code == 0, result.output
    assert rig.target.read_text() == expected({"address": "someone@stranger.test"})


def test_no_flag_and_no_box_writes_nothing_and_says_how(rig: Rig) -> None:
    result = rig.run()
    assert result.exit_code == 1
    assert_nothing_written(rig)
    assert "Traceback" not in result.output
    lines = [
        line
        for line in result.output.strip().splitlines()
        if not line.startswith("message setup:")  # the fake verb's DONE line
        and line not in agent_step_lines(rig)  # the agent half, its own lines
        and line != no_ears_line("claude")  # the wake seat's one line
    ]
    assert len(lines) <= 2
    assert "sessionkit setup --address" in result.output
    assert "--mailbox NAME" in result.output


def test_the_m5_shape_an_account_with_no_box_is_refused(rig: Rig) -> None:
    """S2b: the account is `admin`, the human's box is another name."""
    rig.account.pw_name = "admin"
    rig.box("human")
    result = rig.run()
    assert result.exit_code == 1
    assert_nothing_written(rig)
    assert "'admin'" in result.output
    assert "--mailbox NAME" in result.output


def test_a_named_box_that_does_not_exist_is_refused(rig: Rig) -> None:
    result = rig.run("--mailbox", "nobody")
    assert result.exit_code == 1
    assert_nothing_written(rig)


@pytest.mark.parametrize("mode", ["exit3", "slow", "absent"])
def test_a_box_sessionmail_cannot_confirm_is_refused(
    rig: Rig, mode: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    rig.box(STRANGER)
    monkeypatch.setattr(setup_mod, "SUBPROCESS_TIMEOUT", 0.5)
    if mode == "absent":
        rig.remove("message")
    else:
        rig.mode("message", mode)
    result = rig.run()
    assert result.exit_code == 1
    assert_nothing_written(rig)
    assert "--mailbox NAME" in result.output


# --- S2 / R4: never overwrite; a re-run writes nothing ------------------------


@pytest.mark.parametrize("session", ["model", "absent"])
def test_a_second_run_writes_nothing(rig: Rig, session: str) -> None:
    if session == "absent":
        rig.remove("session")
    rig.box(STRANGER)
    assert rig.run().exit_code == 0
    first = rig.target.read_bytes(), rig.target.stat().st_mtime_ns
    again = rig.run()
    assert again.exit_code == 0, again.output
    assert (rig.target.read_bytes(), rig.target.stat().st_mtime_ns) == first
    assert "nothing written" in again.output
    if session == "absent":
        assert str(rig.target) in again.output  # step 2 names the path


@pytest.mark.parametrize("session", ["model", "absent", "exit2"])
def test_the_m5_host_block_is_already_configured(rig: Rig, session: str) -> None:
    """A shared-host shape: `session.json` holds an operator mailbox, no privileged."""
    if session == "absent":
        rig.remove("session")
    else:
        rig.mode("session", session)
    seeded = rig.seed("session.json", json.dumps({"operator": {"mailbox": "human"}}))
    rig.box(STRANGER)
    result = rig.run()
    assert result.exit_code == 0, result.output
    assert "already" in result.output and "nothing written" in result.output
    assert_nothing_written(rig, [seeded])


def test_an_operator_in_a_drop_in_is_left_alone(rig: Rig) -> None:
    rig.mode("session", "exit2")
    seeded = rig.seed(
        "session.d/50-x.json", json.dumps({"operator": {"privileged": []}})
    )
    rig.box(STRANGER)
    result = rig.run()
    assert result.exit_code == 0
    assert str(seeded) in result.output
    assert_nothing_written(rig, [seeded])


def test_session_reporting_privileged_only_counts_as_configured(rig: Rig) -> None:
    seeded = rig.seed("session.json", json.dumps({"operator": {"privileged": ["x"]}}))
    rig.box(STRANGER)
    result = rig.run()
    assert result.exit_code == 0
    assert "already configured" in result.output
    assert_nothing_written(rig, [seeded])


def test_other_settings_in_session_json_are_untouched(rig: Rig) -> None:
    seeded = rig.seed("session.json", json.dumps({"busy": {"sound": True}}))
    before = seeded.read_bytes()
    rig.box(STRANGER)
    result = rig.run()
    assert result.exit_code == 0, result.output
    assert seeded.read_bytes() == before
    assert rig.files() == sorted([seeded, rig.target])


@pytest.mark.parametrize(
    "relpath, text, why",
    [
        ("session.json", "{not json", "not JSON"),
        ("session.d/20-x.json", "[1, 2]", "not a JSON object"),
        ("session.json", "unreadable", "cannot read"),
    ],
)
def test_a_host_file_we_cannot_read_stops_the_write(
    rig: Rig, relpath: str, text: str, why: str
) -> None:
    seeded = rig.seed(relpath, text)
    if why == "cannot read":
        if os.geteuid() == 0:
            pytest.skip("root reads a mode-000 file")
        seeded.chmod(0)
    rig.box(STRANGER)
    try:
        result = rig.run()
    finally:
        seeded.chmod(stat.S_IRUSR | stat.S_IWUSR)
    assert result.exit_code == 1
    assert str(seeded) in result.output and why in result.output
    assert_nothing_written(rig, [seeded])


# --- R6 / F1: no environment variable changes the outcome ---------------------


def test_the_ask_address_env_does_not_read_as_configured(
    rig: Rig, monkeypatch: pytest.MonkeyPatch
) -> None:
    """sessiontools fills `operator` from AGENT_OPERATOR_ADDR. Setup must still
    write, and the variable never reaches `session operator`."""
    rig.box(STRANGER)
    monkeypatch.setenv("AGENT_OPERATOR_ADDR", "asker@elsewhere.test")
    result = rig.run()
    assert result.exit_code == 0, result.output
    assert rig.target.read_text() == expected({"mailbox": STRANGER})
    assert "asker@elsewhere.test" not in result.output


def test_user_mail_and_ask_address_do_not_change_the_output(
    rig: Rig, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rig.box(STRANGER)
    baseline = rig.run()
    written = rig.target.read_bytes()
    rig.target.unlink()
    rig.agent().unlink()  # so the agent half writes again, as the baseline did
    monkeypatch.setenv("USER", "someone-else")
    monkeypatch.setenv("LOGNAME", "someone-else")
    monkeypatch.setenv("MAIL", str(tmp_path / "someone-else"))
    monkeypatch.setenv("AGENT_OPERATOR_ADDR", "someone-else@elsewhere.test")
    again = rig.run()
    assert (again.exit_code, again.output) == (baseline.exit_code, baseline.output)
    assert rig.target.read_bytes() == written


def test_configured_never_reads_the_ask_address_alone() -> None:
    assert not setup_mod.configured(
        {"operator": "x@y.test", "mailbox": None, "privileged": []}
    )
    assert setup_mod.configured({"operator": None, "mailbox": "x", "privileged": []})
    assert setup_mod.configured(
        {"operator": None, "mailbox": None, "privileged": ["x"]}
    )
    assert not setup_mod.configured(None)


def test_the_child_environment_drops_only_the_ask_address() -> None:
    env = {"PATH": "/bin", "HOME": "/h", "AGENT_OPERATOR_ADDR": "a@b.test"}
    assert setup_mod._child_env(env) == {"PATH": "/bin", "HOME": "/h"}


# --- F2: the write leaves nothing the cascade could misread -------------------


def test_a_target_that_appears_mid_run_is_left_alone(
    rig: Rig, monkeypatch: pytest.MonkeyPatch
) -> None:
    rig.box(STRANGER)
    real_link = os.link

    def racing(src, dst):
        # Another run lands its file after every check, just before our link.
        rig.seed("session.d/10-operator.json", '{"operator": {"mailbox": "first"}}')
        return real_link(src, dst)

    monkeypatch.setattr(setup_mod.os, "link", racing)
    result = rig.run()
    assert result.exit_code == 1
    assert "left it alone" in result.output
    assert json.loads(rig.target.read_text()) == {"operator": {"mailbox": "first"}}
    assert assert_no_stray_json(rig) == ["10-operator.json"]


@pytest.mark.parametrize("dry_run", [False, True])
def test_our_drop_in_emptied_by_hand_is_refused_not_raced(
    rig: Rig, dry_run: bool
) -> None:
    """The target exists with no `operator` (step 2 finds no key): refuse
    and name it, and a dry run exits as the real run does (Q3)."""
    seeded = rig.seed("session.d/10-operator.json", "{}\n")
    rig.box(STRANGER)
    result = rig.run(*(["--dry-run"] if dry_run else []))
    assert result.exit_code == 1, result.output
    assert "exists and holds no operator" in result.output
    assert "appeared while this ran" not in result.output
    assert f"Would write {rig.target}" not in result.output
    assert seeded.read_text() == "{}\n"
    assert assert_no_stray_json(rig) == ["10-operator.json"]


def test_a_dead_runs_temp_file_does_not_block_the_write(rig: Rig) -> None:
    """A crash leaves `.10-operator.json.tmp-<pid>`; a later run that gets
    the same pid clears it and writes (CliRunner runs in this process)."""
    stale = rig.seed(f"session.d/.10-operator.json.tmp-{os.getpid()}", "{partial")
    rig.box(STRANGER)
    result = rig.run()
    assert result.exit_code == 0, result.output
    assert rig.target.read_text() == expected({"mailbox": STRANGER})
    assert not stale.exists()
    assert assert_no_stray_json(rig) == ["10-operator.json"]


def test_a_filesystem_without_hard_links_writes_nothing(
    rig: Rig, monkeypatch: pytest.MonkeyPatch
) -> None:
    rig.box(STRANGER)

    def no_links(src, dst):
        raise PermissionError(1, "Operation not permitted")

    monkeypatch.setattr(setup_mod.os, "link", no_links)
    result = rig.run()
    assert result.exit_code == 1
    assert "could not write" in result.output
    assert not rig.target.exists()
    assert assert_no_stray_json(rig) == []


def test_the_temp_file_name_is_never_read_by_the_cascade(rig: Rig) -> None:
    seen: list[str] = []
    real_link = os.link

    def watching(src, dst):
        seen.append(Path(src).name)
        return real_link(src, dst)

    rig.box(STRANGER)
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(setup_mod.os, "link", watching)
        assert rig.run().exit_code == 0
    ours = [name for name in seen if setup_mod.DROP_IN_NAME in name]
    assert len(ours) == 1 and not ours[0].endswith(".json")
    assert Path(ours[0]).suffix != ".json"


# --- Q3: --dry-run runs steps 1-3, same exits, writes nothing ------------------


def test_dry_run_prints_the_file_and_writes_nothing(rig: Rig) -> None:
    rig.box(STRANGER)
    result = rig.run("--dry-run")
    assert result.exit_code == 0, result.output
    assert f"Would write {rig.target}:" in result.output
    assert expected({"mailbox": STRANGER}).strip() in result.output
    assert_nothing_written(rig)


def test_dry_run_refuses_like_a_real_run(rig: Rig) -> None:
    result = rig.run("--dry-run")
    assert result.exit_code == 1
    assert "--mailbox NAME" in result.output
    assert_nothing_written(rig)


def test_dry_run_reports_an_operator_already_set(rig: Rig) -> None:
    seeded = rig.seed("session.json", json.dumps({"operator": {"mailbox": "human"}}))
    rig.box(STRANGER)
    result = rig.run("--dry-run")
    assert result.exit_code == 0
    assert "nothing written" in result.output
    assert_nothing_written(rig, [seeded])


# --- Q4 and usage: shapes that can never be an operator are usage errors ------


@pytest.mark.parametrize("name", ["a/b", "x@y", "..", ".", "-x", "a b", ""])
def test_a_mailbox_that_is_not_one_plain_name_is_a_usage_error(
    rig: Rig, name: str
) -> None:
    rig.box("x")
    result = rig.run("--mailbox", name)
    assert result.exit_code == 2, result.output
    assert_nothing_written(rig)


@pytest.mark.parametrize(
    "address",
    [
        "noat",
        "a@b@c",
        "@host.test",
        "you@",
        "you @host.test",
        "you@example.com",
        "you@EXAMPLE.org",
        "you@host.example",
        "you@your-host",
    ],
)
def test_an_address_that_is_not_one_is_a_usage_error(rig: Rig, address: str) -> None:
    result = rig.run("--address", address)
    assert result.exit_code == 2, result.output
    assert_nothing_written(rig)


def test_mailbox_and_address_together_is_a_usage_error(rig: Rig) -> None:
    rig.box("x")
    result = rig.run("--mailbox", "x", "--address", "x@host.test")
    assert result.exit_code == 2
    assert_nothing_written(rig)


def test_an_account_name_of_the_wrong_shape_is_refused_not_written(rig: Rig) -> None:
    rig.account.pw_name = "-weird"
    result = rig.run()
    assert result.exit_code == 1
    assert "--mailbox NAME" in result.output
    assert_nothing_written(rig)


# --- step 5: verify through the reader ----------------------------------------


@pytest.mark.parametrize("mode", ["absent", "exit2", "garbage"])
def test_a_reader_that_does_not_answer_is_written_not_verified(
    rig: Rig, mode: str
) -> None:
    if mode == "absent":
        rig.remove("session")
    else:
        rig.mode("session", mode)
    rig.box(STRANGER)
    result = rig.run()
    assert result.exit_code == 0, result.output
    assert rig.target.exists()
    assert "not verified" in result.output and "newer sessiontools" in result.output


def test_a_reader_that_disagrees_after_the_write_is_loud(rig: Rig) -> None:
    rig.mode("session", "disagree")
    rig.box(STRANGER)
    result = rig.run()
    assert result.exit_code == 1
    assert rig.target.exists()
    assert "WARNING" in result.output and "overrides it" in result.output


def test_a_slow_reader_reads_as_nothing_configured(
    rig: Rig, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(setup_mod, "SUBPROCESS_TIMEOUT", 0.5)
    rig.mode("session", "slow")
    rig.box(STRANGER)
    result = rig.run()
    assert result.exit_code == 0, result.output
    assert "not verified" in result.output


def test_a_bad_file_elsewhere_in_the_cascade_is_caught_by_verify() -> None:
    answer = {"operator": None, "mailbox": None, "privileged": []}
    assert not setup_mod.holds(answer, {"mailbox": "x"})
    good = {"operator": None, "mailbox": "x", "privileged": ["x"]}
    assert setup_mod.holds(good, {"mailbox": "x"})
    addr = {"operator": "x@h.test", "mailbox": None, "privileged": ["x@h.test"]}
    assert setup_mod.holds(addr, {"address": "x@h.test"})


# --- R3: no name of ours, written or in the source ------------------------------
# The words are private, so they are not spelt out here: each guard reads every
# row of the private scan list that SESSIONKIT_SCRUB_RULES names, and skips,
# loudly and counted, without it (tests/_scanlist.py). A guard reports a row by
# its name only, and hits() is called outside the assert, so a red run prints no
# private word. Each guard has a positive control: a word planted from every row
# of the list, through the same read the guard makes, must fire.


def _written_hits(rig: Rig, rows: list[_scanlist.Row]) -> dict[str, list[str]]:
    """{file under the settings dir: the names of the rows its text hits}, for
    the files that hit any."""
    found = {}
    for path in rig.files():
        names = _scanlist.hits(path.read_text(), rows)
        if names:
            found[str(path.relative_to(rig.settings))] = names
    return found


def test_the_written_tree_holds_no_name_of_ours(rig: Rig) -> None:
    rows = _scanlist.rows()
    rig.box(STRANGER)
    assert rig.run().exit_code == 0
    written = rig.files()
    assert written, "setup wrote nothing, so the guard scanned nothing"
    found = _written_hits(rig, rows)
    assert found == {}, f"setup wrote a word of row(s) {found}"
    # the control: a word planted from each row into the file setup wrote
    target = rig.target
    assert target in written
    key = str(target.relative_to(rig.settings))
    text = target.read_text()
    missed = []
    for name, word in _scanlist.controls(rows):
        target.write_text(f"{text}{word}\n")
        if name not in _written_hits(rig, rows).get(key, []):
            missed.append(name)
    target.write_text(text)
    assert missed == [], f"the scan missed a word planted from row(s) {missed}"


@pytest.mark.parametrize("source", ["setup.py", "cli.py"])
def test_the_source_holds_no_name_of_ours(source: str, tmp_path: Path) -> None:
    rows = _scanlist.rows()
    path = ROOT / "src" / "sessionkit" / source
    found = _scanlist.hits(path.read_text(), rows)
    assert found == [], f"{source} holds a word of row(s) {found}"
    # the control: a word planted from each row into a copy of the source
    copy = tmp_path / source
    missed = []
    for name, word in _scanlist.controls(rows):
        copy.write_text(f"{path.read_text()}# {word}\n")
        if name not in _scanlist.hits(copy.read_text(), rows):
            missed.append(name)
    assert missed == [], f"the scan missed a word planted from row(s) {missed}"


def test_help_names_the_flags_and_the_file() -> None:
    result = CliRunner().invoke(main, ["setup", "--help"])
    assert result.exit_code == 0
    for word in ("--mailbox", "--address", "--dry-run", "10-operator.json"):
        assert word in result.output


# INSTALL.md ships in neither the wheel nor the sdist, so every pointer the
# installed kit prints to it names the repository it lives in: pyproject's
# Repository URL, which a wheel-installed user can open.


def test_the_repository_is_pyprojects() -> None:
    urls = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["urls"]
    assert setup_mod.REPOSITORY == urls["Repository"]


def test_every_pointer_to_install_md_names_the_repository() -> None:
    help_text = " ".join(CliRunner().invoke(main, ["setup", "--help"]).output.split())
    assert ('See INSTALL.md, "Operator and administrators" and "Mail between agents", '
            f"in {setup_mod.REPOSITORY}.") in help_text
    assert setup_mod.ABOUT.endswith(f"See INSTALL.md, in {setup_mod.REPOSITORY}.")
    assert setup_mod.MAIL_DOC == f'INSTALL.md, "Mail between agents", in {setup_mod.REPOSITORY}'
    # The headings the pointers name are INSTALL.md's own.
    install = (ROOT / "INSTALL.md").read_text(encoding="utf-8")
    for heading in ("### Operator and administrators\n", "### Mail between agents\n"):
        assert heading in install


def _install_md_pointers(source: str):
    """(text, names the repository) for each string in SOURCE naming INSTALL.md:
    docstrings and plain strings by their words, f-strings by their REPOSITORY."""
    tree = ast.parse(source)
    inside = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.JoinedStr):
            inside.update(id(v) for v in node.values)
            text = "".join(v.value for v in node.values if isinstance(v, ast.Constant))
            names = {n.id for n in ast.walk(node) if isinstance(n, ast.Name)}
            if "INSTALL.md" in text:
                yield text, "REPOSITORY" in names
    for node in ast.walk(tree):
        if (isinstance(node, ast.Constant) and isinstance(node.value, str)
                and id(node) not in inside and "INSTALL.md" in node.value):
            yield node.value, setup_mod.REPOSITORY in " ".join(node.value.split())


def test_no_pointer_to_install_md_is_bare() -> None:
    # A bare "See INSTALL.md." names a file the installed kit does not have:
    # every string in the kit's source that names INSTALL.md names the
    # repository too.
    seen = 0
    for path in sorted((ROOT / "src" / "sessionkit").glob("*.py")):
        for text, named in _install_md_pointers(path.read_text(encoding="utf-8")):
            seen += 1
            assert named, (path.name, text)
    assert seen >= 3  # the setup help, ABOUT and MAIL_DOC at least


def test_the_bare_pointer_guard_hits() -> None:
    # A zero is a receipt only when the same guard is shown to hit.
    planted = (
        'def f():\n    """See INSTALL.md."""\n'
        "A = 'See INSTALL.md.'\n"
        "B = f'See INSTALL.md, {OTHER}'\n"
        f"C = 'See INSTALL.md, in {setup_mod.REPOSITORY}.'\n"
        "D = f'See INSTALL.md, in {REPOSITORY}.'\n"
    )
    assert dict(_install_md_pointers(planted)) == {
        "See INSTALL.md.": False,                               # docstring and A
        "See INSTALL.md, ": False,                              # B: another name
        f"See INSTALL.md, in {setup_mod.REPOSITORY}.": True,    # C
        "See INSTALL.md, in .": True,                           # D
    }
    assert len(list(_install_md_pointers(planted))) == 5


# --- mail first: sessionmail's setup verb, a FAKE here ------------------------
# The verb is called by the argv in setup_mod.MAIL_SETUP_ARGV (sessionmail's
# `message setup`), before the operator, and its exits are read:
# 0 done, 4 steps left, 1 failed, 2 refused. No real mail root is touched: the
# fake verb runs under the temp HOME, and makes boxes only in `makes-boxes`.


def test_mail_setup_runs_first_by_the_one_argv(rig: Rig) -> None:
    rig.box(STRANGER)
    result = rig.run()
    assert result.exit_code == 0, result.output
    calls = rig.calls()
    verb = list(setup_mod.MAIL_SETUP_ARGV[1:])
    assert calls[0] == [*verb, "--help"]  # the probe
    assert calls[1] == [*verb, "--box", "claude"]  # the run: the agent's box only
    assert calls[2][:2] == ["box", "path"]  # the operator's box check, after
    assert "message setup: every step DONE" in result.output
    assert rig.target.read_text() == expected({"mailbox": STRANGER})


def test_the_verb_name_lives_in_one_constant(
    rig: Rig, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A renamed verb is a one-line change: every call is built from it."""
    rig.box(STRANGER)
    monkeypatch.setattr(setup_mod, "MAIL_SETUP_ARGV", ("message", "renamed"))
    result = rig.run()
    assert ["renamed", "--help"] in rig.calls()
    assert not rig.setup_calls()
    # The fake has no `renamed`, so it reads as a sessionmail without the verb.
    assert "run: message renamed" in result.output
    assert result.exit_code == setup_mod.EXIT_STEPS_LEFT


@pytest.mark.parametrize(
    "args", [(), ("--dry-run",), ("--mailbox", STRANGER), ("--address", "a@host.test")]
)
def test_setup_never_asks_the_verb_to_write_maps(rig: Rig, args) -> None:
    """Writing postfix maps is the user's opt-in (`message setup
    --write-maps`), and no flag of the kit's passes it; the verb gets only the
    flags it ships: `--dry-run` and `--box NAME`."""
    rig.box(STRANGER)
    rig.run(*args)
    runs = rig.setup_calls()
    assert runs, "the verb ran"
    for argv in runs:
        assert "--write-maps" not in argv
        rest = argv[1:]
        while rest:
            flag = rest.pop(0)
            assert flag in ("--dry-run", "--box"), argv
            if flag == "--box":
                rest.pop(0)


def test_the_box_set_hook_feeds_the_argv(
    rig: Rig, monkeypatch: pytest.MonkeyPatch
) -> None:
    rig.box(STRANGER)
    monkeypatch.setattr(
        setup_mod, "mail_setup_boxes", lambda m, a, agent, seat: ("one", "two")
    )
    assert rig.run().exit_code == 0
    assert rig.setup_calls() == [["setup", "--box", "one", "--box", "two"]]


def test_no_mailbox_passes_only_the_agents_box(rig: Rig) -> None:
    """No --mailbox: one --box, the agent's (default claude); the verb's
    floor (the operator's box) is made besides."""
    rig.setup_mode("makes-boxes")
    (rig.bin / "message.account").write_text(STRANGER)
    result = rig.run()
    assert result.exit_code == 0, result.output
    assert rig.setup_calls() == [["setup", "--box", "claude"]]
    # The default seat's box rides every run, even with no agent named.
    assert setup_mod.mail_setup_boxes(None, None, None, "claude") == ("claude",)
    assert setup_mod.mail_setup_boxes(
        None, "someone@stranger.test", None, "claude"
    ) == ("claude",)
    assert setup_mod.mail_setup_boxes(None, "a@host.test", "claude", "claude") == (
        "claude",
    )
    assert sorted(p.name for p in (rig.home / ".mail" / "agents").iterdir()) == [
        "claude",
        STRANGER,
    ]


def test_a_mailbox_passes_exactly_that_box(rig: Rig) -> None:
    """--mailbox NAME: one --box NAME, so a fresh install makes the named box
    before the operator check looks for it, and does not refuse."""
    rig.setup_mode("makes-boxes")
    (rig.bin / "message.account").write_text(STRANGER)
    result = rig.run("--mailbox", "named")
    assert result.exit_code == 0, result.output
    assert rig.setup_calls() == [["setup", "--box", "named", "--box", "claude"]]
    assert setup_mod.mail_setup_boxes("named", None, "claude", "claude") == (
        "named",
        "claude",
    )
    assert setup_mod.mail_setup_boxes("same", None, "same", "claude") == (
        "same",
        "claude",
    )
    assert (rig.home / ".mail" / "agents" / "named" / "new").is_dir()
    assert rig.target.read_text() == expected({"mailbox": "named"})


def test_a_dry_run_with_a_mailbox_passes_the_box_too(rig: Rig) -> None:
    rig.box("named")
    result = rig.run("--dry-run", "--mailbox", "named")
    assert result.exit_code == 0, result.output
    assert rig.setup_calls() == [
        ["setup", "--dry-run", "--box", "named", "--box", "claude"]
    ]
    assert_nothing_written(rig)


def test_the_kit_names_the_account_box_the_verb_made(rig: Rig) -> None:
    """No operator set: the verb makes the account's box, its name
    case-folded, and the operator the kit writes is that same box."""
    rig.account.pw_name = "Stranger"
    rig.setup_mode("makes-boxes")
    (rig.bin / "message.account").write_text("Stranger")
    result = rig.run()
    assert result.exit_code == 0, result.output
    made = sorted(p.name for p in (rig.home / ".mail" / "agents").iterdir())
    assert made == ["claude", STRANGER]  # the agent's box, and the account's
    assert rig.target.read_text() == expected({"mailbox": STRANGER})


def test_the_kit_names_the_operator_box_the_verb_made(rig: Rig) -> None:
    """`operator.mailbox` set: the verb makes that box, not the account's,
    and the operator the kit reports is that same box."""
    rig.seed("session.json", json.dumps({"operator": {"mailbox": "ops"}}))
    rig.setup_mode("makes-boxes")
    (rig.bin / "message.account").write_text(STRANGER)
    result = rig.run()
    assert result.exit_code == 0, result.output
    made = sorted(p.name for p in (rig.home / ".mail" / "agents").iterdir())
    assert made == ["claude", "ops"]  # the agent's box, and the operator's
    assert "An operator is already configured (ops); nothing written." in result.output
    assert not rig.target.exists()


def test_a_dry_run_passes_dry_run_and_writes_nothing(rig: Rig) -> None:
    """The real verb's dry run on a fresh host exits 4 (steps still to do),
    makes nothing, and the kit says the real run does them."""
    rig.box(STRANGER)
    rig.setup_mode("makes-boxes")
    (rig.bin / "message.account").write_text("made-by-setup")
    result = rig.run("--dry-run")
    assert result.exit_code == setup_mod.EXIT_STEPS_LEFT, result.output
    assert rig.setup_calls() == [["setup", "--dry-run", "--box", "claude"]]
    assert "dry run: nothing applied (1 step(s) TODO)" in result.output
    assert "Dry run: mail setup has steps still to do (above)." in result.output
    assert "Without --dry-run it does what it can and names the rest." in result.output
    assert "left steps for you" not in result.output
    assert not (rig.home / ".mail" / "agents" / "made-by-setup").exists()
    assert_nothing_written(rig)


def test_a_dry_run_on_a_done_host_exits_0(rig: Rig) -> None:
    """Every step DONE: the real verb's dry run exits 0, and so does the kit's."""
    rig.box(STRANGER)
    result = rig.run("--dry-run")
    assert result.exit_code == 0, result.output
    assert rig.setup_calls() == [["setup", "--dry-run", "--box", "claude"]]
    assert_nothing_written(rig)


def test_a_dry_run_on_a_fresh_host_exits_1_for_the_box_not_made_yet(rig: Rig) -> None:
    """Measured on the real verb: a fresh host's dry run makes no box, so the
    operator check that follows finds none and refuses. Exit 1, nothing made."""
    rig.setup_mode("makes-boxes")
    (rig.bin / "message.account").write_text(STRANGER)
    result = rig.run("--dry-run")
    assert result.exit_code == setup_mod.EXIT_REFUSED, result.output
    assert "Dry run: mail setup has steps still to do (above)." in result.output
    assert f"No operator written: sessionmail has no box named '{STRANGER}'." in (
        result.output
    )
    assert not (rig.home / ".mail" / "agents" / STRANGER).exists()
    assert_nothing_written(rig)


def test_a_sessionmail_without_the_verb_gets_the_exact_step(rig: Rig) -> None:
    """0.1.0 answers `message setup --help` with "No such command", exit 2."""
    rig.box(STRANGER)
    rig.setup_mode("absent")
    result = rig.run()
    assert result.exit_code == setup_mod.EXIT_STEPS_LEFT
    assert rig.setup_calls() == []  # probed, never run
    assert "this sessionmail has no `message setup`" in result.output
    assert "exited 2" in result.output
    assert f'INSTALL.md, "Mail between agents", in {setup_mod.REPOSITORY}' in result.output
    assert "run: message setup --box claude" in result.output  # the agent's box
    # The operator still runs, and is written.
    assert rig.target.read_text() == expected({"mailbox": STRANGER})


@pytest.mark.parametrize(
    ("args", "step"),
    [
        ((), "message setup --box claude"),
        (("--agent", "alice"), "message setup --box alice --box claude"),
        (("--mailbox", "named"), "message setup --box named --box claude"),
        (
            ("--mailbox", "named", "--agent", "other"),
            "message setup --box named --box other --box claude",
        ),
        (("--agent", "other", "--dry-run"), "message setup --box other --box claude"),
        (("--dry-run",), "message setup --box claude"),  # the step to run is the real one
    ],
)
def test_the_printed_step_carries_the_boxes_setup_would_ask_for(
    rig: Rig, args: tuple[str, ...], step: str
) -> None:
    """SK-153: the sessionmail this kit installs today has no `message setup`,
    so this printed step is how a stranger's agent box gets made. Without
    `--box NAME` it would make only the account's box, and `session start
    NAME` would hear a box that does not exist."""
    rig.box(STRANGER)
    rig.box("named")
    rig.setup_mode("absent")
    result = rig.run(*args)
    assert result.exit_code == setup_mod.EXIT_STEPS_LEFT, result.output
    assert result.output.count(f"once you do, run: {step}\n") == 1, result.output


def test_no_message_on_the_path_gets_the_step(rig: Rig) -> None:
    rig.remove("message")
    result = rig.run("--address", "someone@stranger.test")
    assert result.exit_code == setup_mod.EXIT_STEPS_LEFT
    assert "`message` is not on the PATH" in result.output
    assert "run: message setup --box claude" in result.output
    assert rig.target.read_text() == expected({"address": "someone@stranger.test"})


def test_steps_left_is_exit_4_and_passes_the_verbs_lines(rig: Rig) -> None:
    rig.box(STRANGER)
    rig.setup_mode("left")
    result = rig.run()
    assert result.exit_code == setup_mod.EXIT_STEPS_LEFT
    assert "notmuch-hook  BLOCKED" in result.output
    assert "1 step(s) left for you" in result.output
    assert "re-run sessionkit setup" in result.output
    assert rig.target.read_text() == expected({"mailbox": STRANGER})


@pytest.mark.parametrize(
    ("mode", "says"),
    [
        ("failed", "A mail setup step failed"),
        ("refused", "Mail setup refused; nothing was applied"),
        ("weird", "Mail setup exited 9"),
    ],
)
def test_a_failed_or_refused_verb_is_exit_1(rig: Rig, mode: str, says: str) -> None:
    rig.box(STRANGER)
    rig.setup_mode(mode)
    result = rig.run()
    assert result.exit_code == 1
    assert says in result.output
    # The operator half still ran: one refusal does not hide the other's work.
    assert rig.target.read_text() == expected({"mailbox": STRANGER})


def test_a_verb_that_does_not_answer_is_exit_1(
    rig: Rig, monkeypatch: pytest.MonkeyPatch
) -> None:
    rig.box(STRANGER)
    rig.setup_mode("slow")
    monkeypatch.setattr(setup_mod, "MAIL_SETUP_TIMEOUT", 0.5)
    result = rig.run()
    assert result.exit_code == 1
    assert "did not answer within 0.5s" in result.output


def test_an_operator_refusal_beats_mail_steps_left(rig: Rig) -> None:
    rig.setup_mode("left")
    result = rig.run("--mailbox", "nobody")
    assert result.exit_code == 1
    assert_nothing_written(rig)


def test_the_box_the_verb_makes_lets_a_fresh_home_write_the_operator(rig: Rig) -> None:
    """Why mail goes first: on a fresh home no box exists, the verb makes the
    account's box, and the operator check after it finds that box."""
    rig.setup_mode("makes-boxes")
    (rig.bin / "message.account").write_text(STRANGER)
    result = rig.run()
    assert result.exit_code == 0, result.output
    assert rig.target.read_text() == expected({"mailbox": STRANGER})


def test_run_mail_setup_directly_reads_each_exit(rig: Rig) -> None:
    env = dict(os.environ)
    for mode, code in (("done", 0), ("left", 4), ("failed", 1), ("refused", 1)):
        rig.setup_mode(mode)
        assert setup_mod.run_mail_setup(environ=env).code == code, mode


# The literal path sessiontools reads the operator from. Spelled out, not built
# from setup's constants, so a change to them that moves the file fails here.
OPERATOR_DROP_IN = ".sessionkit/tools/settings/session.d/10-operator.json"


def test_setup_writes_the_operator_at_the_literal_path(rig: Rig) -> None:
    rig.box(STRANGER)
    assert rig.run().exit_code == 0
    assert rig.files() == [rig.home / OPERATOR_DROP_IN]
    assert setup_mod.operator_drop_in(rig.home) == rig.home / OPERATOR_DROP_IN
    assert setup_mod.settings_dir_for(rig.home) == rig.home / ".sessionkit/tools/settings"


@pytest.mark.parametrize(
    "var",
    ["SESSIONKIT_HOME", "SESSIONKIT_SETTINGS", "SETTINGS_HOME", "SETTINGS_DIR",
     "XDG_CONFIG_HOME", "SESSION_SETTINGS", "SESSIONTOOLS_SETTINGS"],
)
def test_no_environment_variable_moves_the_settings_root(
    rig: Rig, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, var: str
) -> None:
    elsewhere = tmp_path / "elsewhere"
    monkeypatch.setenv(var, str(elsewhere))
    rig.box(STRANGER)
    assert rig.run().exit_code == 0
    assert rig.files() == [rig.home / OPERATOR_DROP_IN]
    assert not elsewhere.exists()


# --- the old root: named once, for the stranded-file check only -------------

# The ONE line in src/ allowed to name the old root: the stranded-detection
# constant. Any other `.settings` in src/ fails, and so does this one missing.
LEGACY_LINE = (
    "src/sessionkit/setup.py",
    'LEGACY_OPERATOR_FILE = "~/.settings/session/session.d/10-operator.json"',
)
# Where sessionkit 0.1.0 wrote the operator, under HOME. Spelled out, as above.
OLD_DROP_IN = ".settings/session/session.d/10-operator.json"


# `.settings` as a folder: not right after a name's letter, so a module path
# such as `sessionphone.settings` (the doctor imports it) is not the old root.
OLD_ROOT_WORD = re.compile(r"(?<![A-Za-z0-9_])\.settings")


def settings_hits(root: Path) -> list[tuple[str, str]]:
    """Every (path, stripped line) under ROOT/src naming the `.settings` folder."""
    return [
        (path.relative_to(root).as_posix(), line.strip())
        for path in sorted((root / "src").rglob("*.py"))
        for line in path.read_text(encoding="utf-8").splitlines()
        if OLD_ROOT_WORD.search(line)
    ]


def test_the_source_names_the_old_root_only_in_the_stranded_constant() -> None:
    # No fallback: the old root is named once, by the detection-only constant.
    assert settings_hits(ROOT) == [LEGACY_LINE]


@pytest.mark.parametrize(
    "planted",
    [
        'OLD = Path.home() / ".settings" / "session"',
        'FALLBACK = "~/.settings/session/session.json"',
        "# reads ~/.settings/session first",
        "p = HOME + '/.settings/session'",
    ],
)
def test_the_source_check_fails_on_any_other_use(tmp_path: Path, planted: str) -> None:
    pkg = tmp_path / "src" / "sessionkit"
    pkg.mkdir(parents=True)
    (pkg / "setup.py").write_text(LEGACY_LINE[1] + "\n")
    (pkg / "other.py").write_text(planted + "\n")
    assert settings_hits(tmp_path) != [LEGACY_LINE]


def test_the_source_check_passes_a_module_path(tmp_path: Path) -> None:
    pkg = tmp_path / "src" / "sessionkit"
    pkg.mkdir(parents=True)
    (pkg / "setup.py").write_text(LEGACY_LINE[1] + "\n")
    (pkg / "other.py").write_text('import sessionphone.settings\n_load("sessionphone.settings")\n')
    assert settings_hits(tmp_path) == [LEGACY_LINE]


def test_the_source_check_fails_when_the_constant_is_gone(tmp_path: Path) -> None:
    pkg = tmp_path / "src" / "sessionkit"
    pkg.mkdir(parents=True)
    (pkg / "setup.py").write_text('NEW = "~/.sessionkit/tools/settings"\n')
    assert settings_hits(tmp_path) != [LEGACY_LINE]


def test_the_legacy_constant_is_the_old_drop_in() -> None:
    assert setup_mod.LEGACY_OPERATOR_FILE == f"~/{OLD_DROP_IN}"
    home = Path("/h")
    assert setup_mod.legacy_operator_file(home) == home / OLD_DROP_IN


# --- the stranded-file rule (HOME is the temp HOME; the old path is test data) --


def tree(home: Path) -> list[tuple[str, str]]:
    """Every path under HOME with its kind and, for a file, its bytes."""
    out = []
    for p in sorted(home.rglob("*")):
        rel = p.relative_to(home).as_posix()
        if p.is_symlink():
            out.append((rel, f"link:{os.readlink(p)}"))
        elif p.is_dir():
            out.append((rel, "dir"))
        else:
            out.append((rel, "file"))
    return out


def plant_old(rig: Rig, text: str | None = None) -> Path:
    """The 0.1.0 operator file, holding a box that EXISTS: were setup to use
    any value from it, that box would be written."""
    old = rig.home / OLD_DROP_IN
    old.parent.mkdir(parents=True)
    old.write_text(text if text is not None else expected({"mailbox": "oldbox"}))
    rig.box("oldbox")
    return old


def assert_stranded(rig: Rig, result, old: Path) -> None:
    assert result.exit_code == 1, result.output
    lines = result.output.splitlines()
    assert len(lines) == 1, lines
    line = lines[0]
    assert str(old) in line and str(rig.home / OPERATOR_DROP_IN) in line
    assert OLD_DROP_IN in line and OPERATOR_DROP_IN in line
    assert "Move that file" in line and "remove it" in line
    assert "oldbox" not in line  # nothing from the old file is printed


@pytest.mark.parametrize(
    "args",
    [(), ("--dry-run",), ("--mailbox", "oldbox"), ("--address", "a@host.test")],
)
def test_stranded_old_file_writes_nothing_and_names_both(rig: Rig, args) -> None:
    old = plant_old(rig)
    rig.box(STRANGER)  # a normal run WOULD write
    before = tree(rig.home)
    result = rig.run(*args)
    assert_stranded(rig, result, old)
    assert tree(rig.home) == before
    assert not rig.settings.exists()


def test_stranded_old_file_is_never_read(rig: Rig) -> None:
    # Unreadable: a read would raise. The rule needs only that it exists.
    old = plant_old(rig, "not json, and nobody reads it")
    old.chmod(0)
    try:
        before = tree(rig.home)
        result = rig.run()
        assert_stranded(rig, result, old)
        assert tree(rig.home) == before
    finally:
        old.chmod(0o644)
    assert old.read_text() == "not json, and nobody reads it"


def test_stranded_old_file_as_a_dangling_link_still_counts(rig: Rig) -> None:
    old = rig.home / OLD_DROP_IN
    old.parent.mkdir(parents=True)
    old.symlink_to(rig.home / "gone.json")
    rig.box(STRANGER)
    before = tree(rig.home)
    assert_stranded(rig, rig.run(), old)
    assert tree(rig.home) == before


def test_stranded_first_even_when_session_operator_answers(rig: Rig) -> None:
    # A reader of the old place may say "configured"; the old file is still
    # stranded, and setup says so instead of "already configured".
    old = plant_old(rig)
    (rig.bin / "session").write_text(
        f"#!{sys.executable}\nimport json\n"
        'print(json.dumps({"operator": None, "mailbox": "oldbox", '
        '"privileged": ["oldbox"]}))\n'
    )
    before = tree(rig.home)
    assert_stranded(rig, rig.run(), old)
    assert tree(rig.home) == before


@pytest.mark.parametrize("args", [(), ("--dry-run",), ("--mailbox", "oldbox")])
def test_stranded_stops_before_mail_setup(rig: Rig, args) -> None:
    """The verb would make boxes from settings that cannot see the old file,
    so a stranded file stops the run before the verb is even probed."""
    old = plant_old(rig)
    rig.setup_mode("makes-boxes")
    (rig.bin / "message.account").write_text(STRANGER)
    before = tree(rig.home)
    assert_stranded(rig, rig.run(*args), old)
    assert tree(rig.home) == before
    assert not any(c[:1] == ["setup"] for c in rig.calls())


def test_neither_present_is_normal_setup(rig: Rig) -> None:
    rig.box(STRANGER)
    result = rig.run()
    assert result.exit_code == 0, result.output
    assert rig.files() == [rig.home / OPERATOR_DROP_IN]
    assert ".settings" not in result.output


@pytest.mark.parametrize(
    "relpath",
    ["session.d/10-operator.json", "session.json", "session.d/05-mine.json"],
)
def test_both_present_new_wins_with_no_message(rig: Rig, relpath: str) -> None:
    plant_old(rig)
    rig.seed(relpath, json.dumps({"operator": {"mailbox": "newbox"}}))
    files = rig.files()
    result = rig.run()
    assert result.exit_code == 0, result.output
    assert ".settings" not in result.output
    assert "already" in result.output
    assert rig.files() == files
    assert json.loads((rig.settings / relpath).read_text()) == {
        "operator": {"mailbox": "newbox"}
    }


def test_new_drop_in_without_operator_is_the_new_sides_refusal(rig: Rig) -> None:
    plant_old(rig)
    rig.box(STRANGER)
    rig.seed("session.d/10-operator.json", json.dumps({"_about": "mine"}))
    result = rig.run()
    assert result.exit_code == 1
    assert "holds no operator" in result.output
    assert ".settings" not in result.output


def test_an_unreadable_new_file_is_named_before_the_old_one(rig: Rig) -> None:
    plant_old(rig)
    bad = rig.seed("session.json", "{not json")
    result = rig.run()
    assert result.exit_code == 1
    assert f"Cannot use {bad}" in result.output
    assert ".settings" not in result.output


@pytest.mark.parametrize("relpath", ["session.json", "session.d/20-x.json"])
def test_an_operator_key_in_old_session_files_is_not_this_check(
    rig: Rig, relpath: str
) -> None:
    # Only the kit's own old drop-in is detected; the old session.json and
    # session.d/ belong to the session tool, which handles them itself.
    old = rig.home / ".settings/session" / relpath
    old.parent.mkdir(parents=True)
    old.write_text(json.dumps({"operator": {"mailbox": "oldbox"}}))
    rig.box(STRANGER)
    result = rig.run()
    assert result.exit_code == 0, result.output
    assert rig.files() == [rig.home / OPERATOR_DROP_IN]
    assert json.loads(rig.target.read_text())["operator"] == {"mailbox": STRANGER}


# The old root, `~/.settings`: a dot that starts a name, so a dotted Python
# name such as `sessiontools.settings` is not the old root.
OLD_ROOT = re.compile(r"(?<!\w)\.settings\b")


def test_the_old_root_pattern_tells_the_root_from_a_dotted_name() -> None:
    assert OLD_ROOT.findall("`~/.settings/session/x.json` and `.settings/`") == [".settings", ".settings"]
    assert not OLD_ROOT.findall("`sessiontools.settings.resolve`")


def test_the_docs_name_the_old_file_once_in_the_upgrade_note() -> None:
    # Outside CHANGELOG history and its union fixtures, the old root appears
    # only in INSTALL.md's "Upgrading from 0.1.0" note: its prose and the move
    # and remove blocks under it.
    hits = []
    for top, dirs, names in os.walk(ROOT):
        dirs[:] = sorted(d for d in dirs if not d.startswith("."))  # .venv, caches
        for name in sorted(n for n in names if n.endswith(".md")):
            rel = (Path(top) / name).relative_to(ROOT).as_posix()
            if rel == "CHANGELOG.md" or rel.startswith("tests/fixtures/changelog_union/"):
                continue  # CHANGELOG history and its copies
            hits += [rel] * len(OLD_ROOT.findall((Path(top) / name).read_text(encoding="utf-8")))
    assert set(hits) == {"INSTALL.md"}
    install = (ROOT / "INSTALL.md").read_text(encoding="utf-8")
    start = install.index("- **Upgrading from 0.1.0.**")
    note = install[start : install.index("\n## 3. ", start)]
    assert len(OLD_ROOT.findall(note)) == len(hits) == 3
    assert f"`~/{OLD_DROP_IN}`" in note
    assert f"`~/{OPERATOR_DROP_IN}`" in note
    assert "exits 1" in note and "--dry-run" in note


# --- the agent: `sessionkit setup --agent NAME` (SK-153) -----------------------
# Setup writes NAME's agent file where `session start NAME` resolves it, NOT
# keyed, never over a file already there; asks the mail verb for the box NAME;
# and ends on the one launch step. The fake `session` answers `start
# --list-agents` by sessiontools' rule; the drift test below holds the kit's
# rule to the INSTALLED sessiontools' own.

# The literal file, spelled out, not built from setup's constants: a change to
# what setup writes fails here.
CLAUDE_AGENT_FILE = """\
You are claude, a Claude Code assistant.

Written by `sessionkit setup`. `session start claude` starts Claude as
claude, so the session hears mail to the box claude. Edit this file as you
like: setup never writes over it.
"""
SENTENCE = "To hear Delta messages, start Claude with: session start {}"
# The bare form: when setup's agent IS the default seat, a bare `session start`
# takes it (SK-206 do-004). The rig's seat is `claude` unless a test says so.
SEAT_SENTENCE = "To hear Delta messages, start Claude with: session start"


def keyed(text: str) -> bool:
    """TEXT asks for a keyed launch: any `keyed:` key, at any depth."""
    return re.search(r"(?m)^\s*keyed\s*:", text) is not None


def test_keyed_grep_fires_on_a_keyed_file() -> None:
    """The control for every `not keyed(...)` below."""
    assert keyed("---\nstart:\n  keyed: true\n---\nbody\n")
    assert keyed("---\nkeyed: false\n---\n")
    assert not keyed(CLAUDE_AGENT_FILE)


def test_setup_writes_the_default_agent_exactly(rig: Rig) -> None:
    rig.box(STRANGER)
    result = rig.run()
    assert result.exit_code == 0, result.output
    path = rig.home / ".session/agents/claude.md"
    assert path.read_text() == CLAUDE_AGENT_FILE
    assert not keyed(path.read_text())
    assert "start:" not in path.read_text()
    assert f"Wrote {path}: the agent 'claude', not keyed." in result.output
    assert "session start --list-agents: lists 'claude'." in result.output
    assert [p.name for p in path.parent.iterdir()] == ["claude.md"]  # no temp left


def test_a_named_agent_is_written_by_its_name(rig: Rig) -> None:
    rig.box(STRANGER)
    result = rig.run("--agent", "alice")
    assert result.exit_code == 0, result.output
    path = rig.home / ".session/agents/alice.md"
    assert path.read_text() == CLAUDE_AGENT_FILE.replace("claude,", "alice,").replace(
        "start claude", "start alice"
    ).replace("box claude", "box alice")
    assert not (rig.home / ".session/agents/claude.md").exists()
    assert result.output.strip().splitlines()[-1] == SENTENCE.format("alice")


def test_the_file_is_one_sessiontools_reads_with_no_key(rig: Rig) -> None:
    """The real parser (sessiontools' agentfile): a valid file, no front
    matter, so no `start:` switch at all and `keyed` stays its default, false."""
    agentfile = pytest.importorskip("sessiontools.start.agentfile")
    rig.box(STRANGER)
    assert rig.run().exit_code == 0
    front, body = agentfile.parse_agent_markdown(rig.agent().read_text())
    assert front == {}
    assert "You are claude" in body


# --- the agents folder: the three roots `session start` reads -------------------


def test_root_one_the_default_is_dot_session_agents(rig: Rig) -> None:
    rig.box(STRANGER)
    assert rig.run().exit_code == 0
    assert (rig.home / ".session/agents/claude.md").is_file()
    assert setup_mod.agents_root(rig.home, {}) == rig.home / ".session/agents"


def test_root_two_agent_config_once_it_is_a_folder(rig: Rig) -> None:
    (rig.home / ".session/agent/config").mkdir(parents=True)
    rig.box(STRANGER)
    result = rig.run()
    assert result.exit_code == 0, result.output
    assert (rig.home / ".session/agent/config/claude.md").read_text() == CLAUDE_AGENT_FILE
    assert not (rig.home / ".session/agents").exists()
    assert "lists 'claude'" in result.output  # the fake reader looked there too


def test_root_two_is_not_taken_when_it_is_a_file(rig: Rig) -> None:
    (rig.home / ".session/agent").mkdir(parents=True)
    (rig.home / ".session/agent/config").write_text("not a folder\n")
    rig.box(STRANGER)
    assert rig.run().exit_code == 0
    assert (rig.home / ".session/agents/claude.md").is_file()


@pytest.mark.parametrize("config", [False, True])
def test_root_three_agents_dir_wins(
    rig: Rig, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, config: bool
) -> None:
    if config:
        (rig.home / ".session/agent/config").mkdir(parents=True)
    elsewhere = tmp_path / "elsewhere-agents"
    monkeypatch.setenv("AGENTS_DIR", str(elsewhere))
    rig.box(STRANGER)
    result = rig.run()
    assert result.exit_code == 0, result.output
    assert (elsewhere / "claude.md").read_text() == CLAUDE_AGENT_FILE
    assert not (rig.home / ".session/agents").exists()
    assert not (rig.home / ".session/agent/config/claude.md").exists()


def test_agents_dir_expands_a_tilde(rig: Rig, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AGENTS_DIR", "~/my-agents")
    rig.box(STRANGER)
    assert rig.run().exit_code == 0
    assert (rig.home / "my-agents/claude.md").is_file()


def test_an_empty_agents_dir_is_unset(rig: Rig, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AGENTS_DIR", "")
    rig.box(STRANGER)
    assert rig.run().exit_code == 0
    assert (rig.home / ".session/agents/claude.md").is_file()


@pytest.mark.parametrize("case", ["default", "config", "config-file", "env", "env-empty"])
def test_the_rule_matches_the_installed_sessiontools(tmp_path: Path, case: str) -> None:
    """Drift: the kit mirrors sessiontools' `agents_root`; hold it to the one
    installed, for each root."""
    agents = pytest.importorskip("sessiontools.start.agents")
    home = tmp_path / "home"
    home.mkdir()
    env = {"HOME": str(home)}
    if case in ("config", "env"):
        (home / ".session/agent/config").mkdir(parents=True)
    if case == "config-file":
        (home / ".session/agent").mkdir(parents=True)
        (home / ".session/agent/config").write_text("")
    if case == "env":
        env["AGENTS_DIR"] = str(tmp_path / "named")
    if case == "env-empty":
        env["AGENTS_DIR"] = ""
    assert setup_mod.agents_root(home, env) == Path(agents.agents_root(env))


# --- never clobber, either layout; a re-run writes nothing ---------------------


def test_a_flat_file_already_there_is_left_alone(rig: Rig) -> None:
    mine = rig.home / ".session/agents/claude.md"
    mine.parent.mkdir(parents=True)
    mine.write_text("---\nmodel: opus\n---\nMine.\n")
    before = mine.stat().st_mtime_ns
    rig.box(STRANGER)
    result = rig.run()
    assert result.exit_code == 0, result.output
    assert mine.read_text() == "---\nmodel: opus\n---\nMine.\n"
    assert mine.stat().st_mtime_ns == before
    assert f"Agent 'claude' is already in {mine}; left as it is." in result.output
    assert result.output.strip().splitlines()[-1] == SEAT_SENTENCE


def test_a_directory_agent_already_there_is_left_alone(rig: Rig) -> None:
    mine = rig.home / ".session/agents/claude/claude.md"
    mine.parent.mkdir(parents=True)
    mine.write_text("Mine.\n")
    rig.box(STRANGER)
    result = rig.run()
    assert result.exit_code == 0, result.output
    assert mine.read_text() == "Mine.\n"
    assert not (rig.home / ".session/agents/claude.md").exists()  # no flat beside it
    assert f"Agent 'claude' is already in {mine}; left as it is." in result.output


def test_a_folder_without_its_file_is_refused(rig: Rig) -> None:
    """`session start claude` refuses that folder (the directory layout wins),
    so a flat file beside it would never be read: refuse, write nothing."""
    folder = rig.home / ".session/agents/claude"
    folder.mkdir(parents=True)
    rig.box(STRANGER)
    result = rig.run()
    assert result.exit_code == 1
    assert sorted(p.name for p in folder.parent.iterdir()) == ["claude"]
    assert list(folder.iterdir()) == []
    assert f"{folder} exists without claude.md in it" in result.output
    assert "start Claude with" not in result.output  # no launch step that fails
    assert rig.target.read_text() == expected({"mailbox": STRANGER})  # operator still ran


def test_a_dangling_link_at_the_flat_path_is_refused(rig: Rig) -> None:
    link = rig.home / ".session/agents/claude.md"
    link.parent.mkdir(parents=True)
    link.symlink_to(rig.home / "nowhere.md")
    rig.box(STRANGER)
    result = rig.run()
    assert result.exit_code == 1
    assert link.is_symlink() and not (rig.home / "nowhere.md").exists()
    assert "is not a file session start can read" in result.output


@pytest.mark.parametrize("case", ["session-is-a-file", "agents-is-a-file", "read-only"])
def test_an_agents_folder_that_cannot_be_made_is_refused_not_a_traceback(
    rig: Rig, case: str
) -> None:
    """The write comes last, after mail and the operator have run: a folder
    it cannot make must be a refusal that prints, so their lines print too."""
    session = rig.home / ".session"
    if case == "session-is-a-file":
        session.write_text("x")
    elif case == "agents-is-a-file":
        session.mkdir()
        (session / "agents").write_text("x")
    else:
        session.mkdir()
        session.chmod(0o500)
    rig.box(STRANGER)
    try:
        result = rig.run()
    finally:
        if session.is_dir():
            session.chmod(0o700)
    assert result.exception is None or isinstance(result.exception, SystemExit), (
        result.exception
    )
    assert result.exit_code == 1, result.output
    assert f"No agent file written: could not make {session / 'agents'} (" in (
        result.output
    )
    assert "start Claude with" not in result.output  # no launch step that fails
    assert rig.target.read_text() == expected({"mailbox": STRANGER})  # operator ran


def test_a_second_run_writes_no_agent_and_exits_as_the_first(rig: Rig) -> None:
    rig.box(STRANGER)
    first = rig.run()
    assert first.exit_code == 0, first.output
    path = rig.agent()
    stamp = path.read_bytes(), path.stat().st_mtime_ns
    again = rig.run()
    assert again.exit_code == first.exit_code
    assert (path.read_bytes(), path.stat().st_mtime_ns) == stamp
    assert f"Agent 'claude' is already in {path}; left as it is." in again.output
    assert again.output.strip().splitlines()[-1] == SEAT_SENTENCE


# --- the box: `--box NAME` to the mail verb ---------------------------------------


@pytest.mark.parametrize(
    ("args", "boxes"),
    [
        ((), ["claude"]),
        (("--agent", "alice"), ["alice", "claude"]),
        (("--mailbox", "named", "--agent", "alice"), ["named", "alice", "claude"]),
        (("--address", "a@host.test", "--agent", "alice"), ["alice", "claude"]),
        (("--mailbox", "alice", "--agent", "alice"), ["alice", "claude"]),
        (("--mailbox", "claude", "--agent", "other"), ["claude", "other"]),
        (("--mailbox", "claude"), ["claude"]),
    ],
)
def test_the_agents_box_rides_the_verbs_argv(rig: Rig, args, boxes) -> None:
    rig.box(STRANGER)
    rig.box("named")
    rig.box("alice")
    rig.run(*args)
    argv = ["setup"]
    for box in boxes:
        argv += ["--box", box]
    assert rig.setup_calls() == [argv]


def test_the_verb_makes_the_agents_box(rig: Rig) -> None:
    rig.setup_mode("makes-boxes")
    (rig.bin / "message.account").write_text(STRANGER)
    result = rig.run("--agent", "alice")
    assert result.exit_code == 0, result.output
    assert (rig.home / ".mail/agents/alice/new").is_dir()


# --- the default seat's box: asked for on every run, whatever --agent names -----


def test_the_default_seat_is_read_from_session_agent_default() -> None:
    assert setup_mod.DEFAULT_SEAT_ARGV == ("session", "agent", "default")
    assert not hasattr(setup_mod, "DEFAULT_SEAT"), "the seat's name is never a literal"


def test_the_default_seat_follows_the_verb(rig: Rig) -> None:
    """The box, the wake seat and the seat are one word from one place: the
    word `session agent default` prints, whatever it is."""
    rig.box(STRANGER)
    rig.seat("other")
    assert setup_mod.default_seat(os.environ) == "other"
    add_ears(rig)
    result = rig.run()
    assert result.exit_code == 0, result.output
    assert rig.setup_calls() == [["setup", "--box", "claude", "--box", "other"]]
    assert ears_calls(rig)[0] == ["wake", "add", "other"]
    assert list(wake_seats(rig)) == ["other"]


@pytest.mark.parametrize("answer", ["absent", "error", "garbage", "Not A Name"])
def test_a_verb_that_does_not_answer_names_no_seat(rig: Rig, answer: str) -> None:
    """No literal stands in: no seat name means no default seat's box, no
    wake seat, one line, and the exit a run would have had anyway."""
    rig.box(STRANGER)
    rig.seat(answer)
    add_ears(rig)
    assert setup_mod.default_seat(os.environ) is None
    result = rig.run("--agent", "other")
    assert result.exit_code == 0, result.output
    assert rig.setup_calls() == [["setup", "--box", "other"]]
    unknown = setup_mod.SEAT_UNKNOWN_LINE.format(verb="session agent default")
    assert result.output.splitlines().count(unknown) == 1
    # --agent names the wake seat; it needs no verb.
    assert ears_calls(rig)[0] == ["wake", "add", "other"]


def test_no_seat_and_no_agent_adds_no_wake_seat(rig: Rig) -> None:
    rig.box(STRANGER)
    rig.seat("absent")
    add_ears(rig)
    result = rig.run()
    assert result.exit_code == 0, result.output
    assert rig.setup_calls() == [["setup", "--box", "claude"]]
    assert ["wake", "add", "claude"] not in ears_calls(rig)
    assert not wake_file(rig).exists()


def test_a_slow_seat_verb_is_not_waited_on(
    rig: Rig, monkeypatch: pytest.MonkeyPatch
) -> None:
    rig.seat("slow")
    monkeypatch.setattr(setup_mod, "DEFAULT_SEAT_TIMEOUT", 0.5)
    start = time.monotonic()
    assert setup_mod.default_seat(os.environ) is None
    assert time.monotonic() - start < 10


@pytest.mark.parametrize(
    ("mailbox", "address", "agent"),
    [
        (None, None, None),
        (None, None, "claude"),
        (None, None, "other"),
        ("named", None, "other"),
        (None, "a@host.test", "other"),
        ("claude", None, "claude"),
    ],
)
def test_every_box_set_holds_the_default_seat_once(mailbox, address, agent) -> None:
    boxes = setup_mod.mail_setup_boxes(mailbox, address, agent, "claude")
    assert boxes.count("claude") == 1, boxes
    assert len(boxes) == len(set(boxes)), boxes
    if agent is not None:
        assert agent in boxes


def test_another_agent_still_makes_the_default_seats_box(rig: Rig) -> None:
    """A fresh install with `--agent other` makes the box `other` and the
    default seat's box `claude`: a session started as `claude` is not deaf."""
    rig.setup_mode("makes-boxes")
    (rig.bin / "message.account").write_text(STRANGER)
    result = rig.run("--agent", "other")
    assert result.exit_code == 0, result.output
    assert rig.setup_calls() == [["setup", "--box", "other", "--box", "claude"]]
    agents = rig.home / ".mail" / "agents"
    assert sorted(p.name for p in agents.iterdir()) == ["claude", "other", STRANGER]
    assert (agents / "claude" / "new").is_dir()


def test_a_rerun_with_another_agent_changes_no_box(rig: Rig) -> None:
    rig.setup_mode("makes-boxes")
    (rig.bin / "message.account").write_text(STRANGER)
    assert rig.run("--agent", "other").exit_code == 0
    agents = rig.home / ".mail" / "agents"
    before = sorted(str(p.relative_to(agents)) for p in agents.rglob("*"))
    again = rig.run("--agent", "other")
    assert again.exit_code == 0, again.output
    assert sorted(str(p.relative_to(agents)) for p in agents.rglob("*")) == before


def test_a_dry_run_with_another_agent_names_the_default_seats_box(rig: Rig) -> None:
    rig.box(STRANGER)
    result = rig.run("--dry-run", "--agent", "other")
    assert result.exit_code == 0, result.output
    assert rig.setup_calls() == [
        ["setup", "--dry-run", "--box", "other", "--box", "claude"]
    ]
    assert "Would ask `message setup` for the agent's box 'other' (--box other)." in (
        result.output
    )
    assert (
        "Would ask `message setup` for the default seat's box 'claude' "
        "(--box claude) too."
    ) in result.output
    assert_nothing_written(rig)


def test_a_dry_run_for_the_default_agent_names_its_box_once(rig: Rig) -> None:
    rig.box(STRANGER)
    result = rig.run("--dry-run")
    assert result.exit_code == 0, result.output
    assert "default seat's box" not in result.output
    assert result.output.count("(--box claude)") == 1


# --- dry run: prints the file and the box; writes nothing -----------------------


def test_a_dry_run_prints_the_agent_file_and_box_and_writes_nothing(rig: Rig) -> None:
    rig.box(STRANGER)
    result = rig.run("--dry-run")
    assert result.exit_code == 0, result.output
    path = rig.home / ".session/agents/claude.md"
    assert f"Would write {path}:\n{CLAUDE_AGENT_FILE}" in result.output
    assert "Would ask `message setup` for the agent's box 'claude' (--box claude)." in (
        result.output
    )
    assert not (rig.home / ".session").exists()
    assert result.output.strip().splitlines()[-1] == SEAT_SENTENCE


def test_a_dry_run_over_an_existing_file_says_so(rig: Rig) -> None:
    mine = rig.home / ".session/agents/claude.md"
    mine.parent.mkdir(parents=True)
    mine.write_text("Mine.\n")
    rig.box(STRANGER)
    result = rig.run("--dry-run")
    assert result.exit_code == 0
    assert "Would write" not in result.output.replace(f"Would write {rig.target}", "")
    assert "already in" in result.output
    assert mine.read_text() == "Mine.\n"


def test_a_stranded_run_writes_no_agent(rig: Rig) -> None:
    old = rig.home / setup_mod.LEGACY_OPERATOR_FILE.removeprefix("~/")
    old.parent.mkdir(parents=True)
    old.write_text("{}")
    rig.box(STRANGER)
    result = rig.run()
    assert result.exit_code == 1
    assert not (rig.home / ".session").exists()
    assert "start Claude with" not in result.output


# --- verify through the reader: `session start --list-agents` -------------------


def test_an_agents_reader_that_does_not_answer_is_written_not_verified(rig: Rig) -> None:
    (rig.bin / "session.agents").write_text("absent")
    rig.box(STRANGER)
    result = rig.run()
    assert result.exit_code == 0, result.output
    assert rig.agent().is_file()
    assert "Written; not verified: `session start --list-agents` did not answer." in (
        result.output
    )


def test_an_agents_reader_that_does_not_list_the_agent_is_loud(rig: Rig) -> None:
    (rig.bin / "session.agents").write_text("empty")
    rig.box(STRANGER)
    result = rig.run()
    assert result.exit_code == 1
    assert "WARNING: `session start --list-agents` does not list 'claude'" in result.output


# --- the printed launch step ------------------------------------------------------


def test_the_launch_step_is_the_shared_sentence_last(rig: Rig) -> None:
    rig.box(STRANGER)
    result = rig.run()
    assert result.exit_code == 0
    assert result.output.strip().splitlines()[-1] == (
        "To hear Delta messages, start Claude with: session start"
    )
    assert setup_mod.launch_sentence("x") == SENTENCE.format("x")
    assert setup_mod.launch_sentence("x", "x") == SEAT_SENTENCE
    assert setup_mod.launch_sentence("x", "y") == SENTENCE.format("x")


# The default seat (SK-206 do-004, measured at sessiontools 1ba50f6): a bare
# `session start` takes the seat `session agent default` names, so the step is
# bare only when setup's agent IS that seat. After `--agent other` a bare start
# took `claude`, not `other`; a sessiontools without the verb (0.3.0) started
# a bare start plain. Both keep the named form.
@pytest.mark.parametrize(
    "seat, args, last",
    [
        ("claude", (), SEAT_SENTENCE),  # no --agent: the agent is the seat
        ("claude", ("--agent", "claude"), SEAT_SENTENCE),  # named, the seat's word
        ("claude", ("--agent", "other"), SENTENCE.format("other")),  # another agent
        ("absent", (), SENTENCE.format("claude")),  # no verb: no seat known
        ("other", (), SENTENCE.format("claude")),  # the seat is not setup's agent
    ],
)
def test_the_launch_step_is_bare_only_for_the_default_seat(
    rig: Rig, seat: str, args: tuple[str, ...], last: str
) -> None:
    rig.box(STRANGER)
    if seat != "claude":
        rig.seat(seat)
    result = rig.run(*args)
    assert result.exit_code == 0, result.output
    assert result.output.strip().splitlines()[-1] == last


def test_the_launch_step_prints_when_the_operator_refuses(rig: Rig) -> None:
    """The operator and the agent are separate halves: an operator refusal
    (no box for the account) does not hide the launch step."""
    result = rig.run()
    assert result.exit_code == 1
    assert rig.agent().is_file()
    assert result.output.strip().splitlines()[-1] == SEAT_SENTENCE


# --- --agent shape: a usage error, nothing run, nothing written -----------------


@pytest.mark.parametrize(
    "name", ["", ".", "..", ".hidden", "a/b", "a\\b", "a@b", "-x", "a b", "tab\there"]
)
def test_an_agent_name_of_the_wrong_shape_is_a_usage_error(rig: Rig, name: str) -> None:
    rig.box(STRANGER)
    result = rig.run("--agent", name)
    assert result.exit_code == 2, result.output
    assert "Traceback" not in result.output
    assert "is not an agent name" in result.output
    assert rig.calls() == []  # mail never ran
    assert not (rig.home / ".session").exists()
    assert_nothing_written(rig)


def test_help_names_the_agent_flag_and_its_default() -> None:
    result = CliRunner().invoke(main, ["setup", "--help"])
    assert result.exit_code == 0
    assert "--agent NAME" in result.output
    assert "[default: claude]" in result.output
    assert "session start NAME" in result.output


# --- R3 for the agent file: no name of ours in it, with its control --------------


def test_the_agent_file_holds_no_name_of_ours(rig: Rig) -> None:
    rows = _scanlist.rows()
    rig.box(STRANGER)
    assert rig.run().exit_code == 0
    path = rig.agent()
    text = path.read_text()
    found = _scanlist.hits(text, rows)
    assert found == [], f"the agent file holds a word of row(s) {found}"
    missed = []
    for name, word in _scanlist.controls(rows):
        planted = f"{text}{word}\n"
        if name not in _scanlist.hits(planted, rows):
            missed.append(name)
    assert missed == [], f"the scan missed a word planted from row(s) {missed}"


# --- the ears' model: setup reads `ears backends`, never fetches -----------------

# A stand-in for sessionvoice 0.2.1's `ears backends` (its src/ears/cli.py):
# one line a backend, then `silero    ok: PATH` or `silero    no model: ears
# install`, exit 0. A `ears.mode` file switches it: `ok` (the default),
# `missing`, `slow`, `error` (exit 1) or `garbage`. Every argv is logged, one
# JSON list a line, to `ears.calls`, so a test can see `ears install` never ran.
#
# `ears wake add SEAT` / `ears wake list` model sessionvoice's wake verbs
# (src/ears/wake.py): the wake file is $EARS_WAKE, else
# ~/.sessionkit/voice/settings/wake.json; add lower-cases the key, keeps the
# seat's names with the key moved first, writes atomically (indent 2, one
# newline) and exits 0 when the seat is already there; list is read only,
# exit 0 either way. An `ears.wake` file switches them: `refuse` (exit 1,
# `ears wake: <reason>` on stderr) or `slow`.
FAKE_EARS = r"""
import json, os, sys, tempfile, time
from pathlib import Path
here = Path(__file__)
with here.with_name("ears.calls").open("a") as log:
    log.write(json.dumps(sys.argv[1:]) + "\n")
mode_file = here.with_name("ears.mode")
mode = mode_file.read_text().strip() if mode_file.exists() else "ok"
args = sys.argv[1:]
if args[:1] == ["wake"]:
    wake_file = here.with_name("ears.wake")
    wake = wake_file.read_text().strip() if wake_file.exists() else "real"
    if wake == "refuse":
        print("ears wake: the wake file was left at the old place.", file=sys.stderr)
        sys.exit(1)
    if wake == "slow":
        time.sleep(30)
    target = Path(os.environ.get("EARS_WAKE")
                  or Path(os.environ["HOME"]) / ".sessionkit/voice/settings/wake.json")
    conf = json.loads(target.read_text()) if target.is_file() else {}
    if args[1:] == ["list"]:
        found = conf.get("seats") or {}
        if not found:
            print(f"no seats in {target}", file=sys.stderr)
        for key, entry in sorted(found.items()):
            print(f"{key}: {'|'.join(entry.get('names') or [key])}")
        sys.exit(0)
    if args[1:2] == ["add"] and len(args) == 3:
        key = args[2].strip().lower()
        seats = conf.setdefault("seats", {})
        entry = seats.get(key) or {}
        entry["names"] = [key] + [n for n in entry.get("names") or [] if n != key]
        seats[key] = entry
        target.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=target.parent, suffix=".tmp")
        with os.fdopen(fd, "w") as f:
            json.dump(conf, f, indent=2)
            f.write("\n")
        os.replace(tmp, target)
        print(f"{key}: {'|'.join(entry['names'])}  ({target})")
        sys.exit(0)
    sys.exit(2)
if args != ["backends"]:
    sys.exit(2)
if mode == "slow":
    time.sleep(30)
if mode == "error":
    print("ears: something broke", file=sys.stderr)
    sys.exit(1)
if mode == "garbage":
    print("nothing like a backend list")
    sys.exit(0)
print("apple     no: no apple-speech helper: `ears install --apple` builds it")
print("whisper   no: nothing at http://127.0.0.1:2022/v1/audio/transcriptions (URLError)")
if mode == "missing":
    print("silero    no model: ears install")
else:
    print("silero    ok: /tmp/home/.cache/ears/silero_vad.onnx")
sys.exit(0)
"""


def add_ears(rig: Rig, mode: str = "ok") -> None:
    script = rig.bin / "ears"
    script.write_text(f"#!{sys.executable}\n{FAKE_EARS}")
    script.chmod(0o755)
    (rig.bin / "ears.mode").write_text(mode)


def ears_calls(rig: Rig) -> list[list[str]]:
    log = rig.bin / "ears.calls"
    if not log.exists():
        return []
    return [json.loads(line) for line in log.read_text().splitlines()]


def test_a_present_model_adds_no_line(rig: Rig) -> None:
    rig.box(STRANGER)
    add_ears(rig, "ok")
    result = rig.run()
    assert result.exit_code == 0, result.output
    assert setup_mod.EARS_MODEL_LINE not in result.output
    assert "ears install" not in result.output
    assert ears_calls(rig) == [["wake", "add", "claude"], ["backends"]]


@pytest.mark.parametrize("verb_mode, code", [(None, 0), ("left", 4)])
def test_a_missing_model_says_one_line_and_keeps_the_exit(
    rig: Rig, verb_mode: str | None, code: int
) -> None:
    rig.box(STRANGER)
    if verb_mode:
        rig.setup_mode(verb_mode)
    add_ears(rig, "missing")
    result = rig.run()
    assert result.exit_code == code, result.output
    lines = result.output.splitlines()
    assert lines.count(setup_mod.EARS_MODEL_LINE) == 1
    # Just before the launch step, which stays the run's last line.
    assert lines[-1] == SEAT_SENTENCE
    assert lines[-2] == setup_mod.EARS_MODEL_LINE
    # Read only: setup asked, and never ran `ears install`.
    assert ears_calls(rig) == [["wake", "add", "claude"], ["backends"]]


def test_the_model_line_names_ears_install_and_why() -> None:
    line = setup_mod.EARS_MODEL_LINE
    assert "`ears install`" in line
    assert "cannot hear you" in line
    assert "\n" not in line


def test_a_missing_model_on_a_refused_run_keeps_exit_1(rig: Rig) -> None:
    add_ears(rig, "missing")
    result = rig.run("--mailbox", "nobody")
    assert result.exit_code == 1
    assert setup_mod.EARS_MODEL_LINE in result.output


def test_a_dry_run_asks_too_and_writes_nothing(rig: Rig) -> None:
    rig.box(STRANGER)
    add_ears(rig, "missing")
    result = rig.run("--dry-run")
    assert setup_mod.EARS_MODEL_LINE in result.output
    assert ears_calls(rig) == [["wake", "list"], ["backends"]]
    assert_nothing_written(rig)


def test_no_ears_on_the_path_says_nothing_about_the_model(rig: Rig) -> None:
    rig.box(STRANGER)
    assert not (rig.bin / "ears").exists()
    result = rig.run()
    assert result.exit_code == 0, result.output
    assert setup_mod.EARS_MODEL_LINE not in result.output
    assert "ears install" not in result.output


@pytest.mark.parametrize("mode", ["error", "garbage"])
def test_a_failing_probe_says_nothing_and_keeps_the_exit(rig: Rig, mode: str) -> None:
    rig.box(STRANGER)
    add_ears(rig, mode)
    result = rig.run()
    assert result.exit_code == 0, result.output
    assert setup_mod.EARS_MODEL_LINE not in result.output


def test_a_slow_probe_is_not_waited_on(rig: Rig, monkeypatch: pytest.MonkeyPatch) -> None:
    rig.box(STRANGER)
    add_ears(rig, "slow")
    monkeypatch.setattr(setup_mod, "EARS_PROBE_TIMEOUT", 0.5)
    start = time.monotonic()
    result = rig.run()
    elapsed = time.monotonic() - start
    assert result.exit_code == 0, result.output
    assert setup_mod.EARS_MODEL_LINE not in result.output
    assert elapsed < 10, f"setup waited {elapsed:.1f}s on a probe that sleeps 30s"


def test_the_probe_timeout_is_short() -> None:
    assert 0 < setup_mod.EARS_PROBE_TIMEOUT <= 5


def test_the_install_doc_quotes_the_model_line() -> None:
    install = (ROOT / "INSTALL.md").read_text(encoding="utf-8")
    flat = " ".join(install.split())
    assert f"``{setup_mod.EARS_MODEL_LINE}``" in flat
    assert "It never runs `ears install` itself, and the line never changes its exit." in flat


# --- the wake seat: `ears wake add NAME`, so "hey NAME" wakes the seat ----------


def wake_file(rig: Rig) -> Path:
    """The wake file the fake `ears wake` writes: the user file under HOME."""
    return rig.home / ".sessionkit" / "voice" / "settings" / "wake.json"


def wake_seats(rig: Rig) -> dict:
    return json.loads(wake_file(rig).read_text())["seats"]


WAKE_PREFIXES = ("No wake seat added", "Wake seat ", "Would add wake seat ")


def wake_lines(output: str) -> list[str]:
    """The wake seat's lines in a run's output."""
    return [line for line in output.splitlines() if line.startswith(WAKE_PREFIXES)]


def wake_mode(rig: Rig, mode: str) -> None:
    (rig.bin / "ears.wake").write_text(mode)


def test_a_fresh_home_gets_the_default_seat_as_its_wake_seat(rig: Rig) -> None:
    rig.box(STRANGER)
    add_ears(rig)
    assert not wake_file(rig).exists()
    result = rig.run()
    assert result.exit_code == 0, result.output
    assert wake_seats(rig) == {"claude": {"names": ["claude"]}}
    assert "Wake seat 'claude': \"hey claude\" wakes it." in result.output.splitlines()


def test_a_rerun_leaves_the_wake_file_byte_identical(rig: Rig) -> None:
    """The verb rewrites atomically, so its mtime moves: compare bytes."""
    rig.box(STRANGER)
    add_ears(rig)
    assert rig.run().exit_code == 0
    before = wake_file(rig).read_bytes()
    again = rig.run()
    assert again.exit_code == 0, again.output
    assert wake_file(rig).read_bytes() == before


def test_a_seat_already_there_keeps_its_names(rig: Rig) -> None:
    rig.box(STRANGER)
    add_ears(rig)
    wake_file(rig).parent.mkdir(parents=True)
    wake_file(rig).write_text(
        json.dumps(
            {
                "seats": {
                    "claude": {"names": ["clawed", "claude"], "hint": "Claude"},
                    "dave": {"names": ["dave"]},
                }
            }
        )
    )
    result = rig.run()
    assert result.exit_code == 0, result.output
    seats = wake_seats(rig)
    assert seats["claude"] == {"names": ["claude", "clawed"], "hint": "Claude"}
    assert seats["dave"] == {"names": ["dave"]}


def test_agent_names_the_wake_seat(rig: Rig) -> None:
    rig.box(STRANGER)
    add_ears(rig)
    result = rig.run("--agent", "alice")
    assert result.exit_code == 0, result.output
    assert list(wake_seats(rig)) == ["alice"]
    assert ["wake", "add", "claude"] not in ears_calls(rig)


def test_setup_never_runs_ears_services_install(rig: Rig) -> None:
    """The ORDER: no `ears services install`, ever, so `ears wake add` is the
    first thing setup asks of the ears (the model probe comes after it)."""
    rig.box(STRANGER)
    add_ears(rig, "missing")
    for args in ((), ("--agent", "alice"), ("--dry-run",)):
        (rig.bin / "ears.calls").unlink(missing_ok=True)
        rig.run(*args)
        calls = ears_calls(rig)
        assert all(call[:1] != ["services"] for call in calls), calls
        assert calls[0][:2] in (["wake", "add"], ["wake", "list"]), calls
        assert calls[-1] == ["backends"], calls
    assert '"services"' not in (ROOT / "src/sessionkit/setup.py").read_text()


@pytest.mark.parametrize(
    ("args", "code"), [((), 0), (("--mailbox", "nobody"), 1), ((), 4)]
)
def test_no_ears_is_one_line_and_keeps_the_exit(rig: Rig, args, code: int) -> None:
    rig.box(STRANGER)
    if code == 4:
        rig.setup_mode("left")
    assert not (rig.bin / "ears").exists()
    result = rig.run(*args)
    assert result.exit_code == code, result.output
    lines = result.output.splitlines()
    assert lines.count(no_ears_line("claude")) == 1
    assert wake_lines(result.output) == [no_ears_line("claude")]


@pytest.mark.parametrize("code", [0, 4])
def test_a_refusal_is_one_line_and_keeps_the_exit(rig: Rig, code: int) -> None:
    rig.box(STRANGER)
    if code == 4:
        rig.setup_mode("left")
    add_ears(rig)
    wake_mode(rig, "refuse")
    result = rig.run()
    assert result.exit_code == code, result.output
    wake = wake_lines(result.output)
    assert wake == [
        (
            "No wake seat added (ears wake: the wake file was left at the old "
            "place). Fix that, then run: ears wake add claude"
        )
    ]
    assert not wake_file(rig).exists()


def test_a_slow_wake_add_is_one_line_and_not_waited_on(
    rig: Rig, monkeypatch: pytest.MonkeyPatch
) -> None:
    rig.box(STRANGER)
    add_ears(rig)
    wake_mode(rig, "slow")
    monkeypatch.setattr(setup_mod, "WAKE_TIMEOUT", 0.5)
    start = time.monotonic()
    result = rig.run()
    assert time.monotonic() - start < 10
    assert result.exit_code == 0, result.output
    wake = wake_lines(result.output)
    assert wake == [
        (
            "No wake seat added: `ears wake add claude` did not answer. "
            "Run it yourself: ears wake add claude"
        )
    ]


def test_the_wake_line_comes_before_the_model_line_and_the_launch_step(
    rig: Rig,
) -> None:
    rig.box(STRANGER)
    add_ears(rig, "missing")
    lines = rig.run().output.splitlines()
    assert lines[-3:] == [
        "Wake seat 'claude': \"hey claude\" wakes it.",
        setup_mod.EARS_MODEL_LINE,
        SEAT_SENTENCE,
    ]


def test_a_dry_run_lists_and_writes_no_wake_seat(rig: Rig) -> None:
    rig.box(STRANGER)
    add_ears(rig)
    result = rig.run("--dry-run")
    assert result.exit_code == 0, result.output
    assert "Would add wake seat 'claude': ears wake add claude" in result.output
    assert ears_calls(rig) == [["wake", "list"], ["backends"]]
    assert not wake_file(rig).exists()
    assert_nothing_written(rig)


def test_a_dry_run_with_the_seat_there_says_so_and_writes_nothing(rig: Rig) -> None:
    rig.box(STRANGER)
    add_ears(rig)
    wake_file(rig).parent.mkdir(parents=True)
    wake_file(rig).write_text(json.dumps({"seats": {"claude": {"names": ["claude"]}}}))
    before = wake_file(rig).read_bytes()
    result = rig.run("--dry-run")
    assert result.exit_code == 0, result.output
    assert (
        "Wake seat 'claude' is already there; a real run leaves its names as they are."
    ) in result.output
    assert wake_file(rig).read_bytes() == before
    assert ["wake", "add", "claude"] not in ears_calls(rig)


def test_a_dry_run_without_ears_is_the_same_one_line(rig: Rig) -> None:
    rig.box(STRANGER)
    result = rig.run("--dry-run")
    assert result.exit_code == 0, result.output
    assert result.output.splitlines().count(no_ears_line("claude")) == 1
