"""`sessionkit setup` writes the operator from config, never a name (SK-70).

Every test runs in a temp HOME with a PATH holding only two fake programs:

- `session`: a small model of sessiontools' `session operator`. It reads the
  host layer (`session.json`, then `session.d/*.json`), merges `operator`
  maps key by key, reads as NOTHING CONFIGURED when any file there is bad,
  and, like sessiontools, lets AGENT_OPERATOR_ADDR fill the `operator` (ask
  address) field without granting privilege. A mode file switches it to
  absent-verb (exit 2), garbage, "disagree" or slow.
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

import json
import os
import re
import stat
import sys
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
    for var in ("AGENT_OPERATOR_ADDR", "USER", "LOGNAME", "MAIL"):
        monkeypatch.delenv(var, raising=False)
    account = SimpleNamespace(pw_name=STRANGER)
    monkeypatch.setattr(setup_mod, "pwd", SimpleNamespace(getpwuid=lambda uid: account))
    assert Path.home() == home
    return Rig(home=home, bin=bindir, account=account)


def expected(block: dict) -> str:
    return json.dumps({"_about": ABOUT, "operator": block}, indent=2) + "\n"


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
    assert "Would write" not in result.output
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
    assert len(seen) == 1 and not seen[0].endswith(".json")
    assert Path(seen[0]).suffix != ".json"


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
    assert calls[1] == verb  # the run: no --mailbox, so no --box
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
    monkeypatch.setattr(setup_mod, "mail_setup_boxes", lambda m, a: ("one", "two"))
    assert rig.run().exit_code == 0
    assert rig.setup_calls() == [["setup", "--box", "one", "--box", "two"]]


def test_no_mailbox_passes_no_box(rig: Rig) -> None:
    """No --mailbox: no --box, so the verb's floor (the operator's box) is
    all that is made."""
    rig.setup_mode("makes-boxes")
    (rig.bin / "message.account").write_text(STRANGER)
    result = rig.run()
    assert result.exit_code == 0, result.output
    assert rig.setup_calls() == [["setup"]]
    assert setup_mod.mail_setup_boxes(None, None) == ()
    assert setup_mod.mail_setup_boxes(None, "someone@stranger.test") == ()
    assert sorted(p.name for p in (rig.home / ".mail" / "agents").iterdir()) == [
        STRANGER
    ]


def test_a_mailbox_passes_exactly_that_box(rig: Rig) -> None:
    """--mailbox NAME: one --box NAME, so a fresh install makes the named box
    before the operator check looks for it, and does not refuse."""
    rig.setup_mode("makes-boxes")
    (rig.bin / "message.account").write_text(STRANGER)
    result = rig.run("--mailbox", "named")
    assert result.exit_code == 0, result.output
    assert rig.setup_calls() == [["setup", "--box", "named"]]
    assert setup_mod.mail_setup_boxes("named", None) == ("named",)
    assert (rig.home / ".mail" / "agents" / "named" / "new").is_dir()
    assert rig.target.read_text() == expected({"mailbox": "named"})


def test_a_dry_run_with_a_mailbox_passes_the_box_too(rig: Rig) -> None:
    rig.box("named")
    result = rig.run("--dry-run", "--mailbox", "named")
    assert result.exit_code == 0, result.output
    assert rig.setup_calls() == [["setup", "--dry-run", "--box", "named"]]
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
    assert made == [STRANGER]
    assert rig.target.read_text() == expected({"mailbox": made[0]})


def test_the_kit_names_the_operator_box_the_verb_made(rig: Rig) -> None:
    """`operator.mailbox` set: the verb makes that box, not the account's,
    and the operator the kit reports is that same box."""
    rig.seed("session.json", json.dumps({"operator": {"mailbox": "ops"}}))
    rig.setup_mode("makes-boxes")
    (rig.bin / "message.account").write_text(STRANGER)
    result = rig.run()
    assert result.exit_code == 0, result.output
    made = sorted(p.name for p in (rig.home / ".mail" / "agents").iterdir())
    assert made == ["ops"]
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
    assert rig.setup_calls() == [["setup", "--dry-run"]]
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
    assert rig.setup_calls() == [["setup", "--dry-run"]]
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
    assert 'INSTALL.md, "Mail between agents"' in result.output
    assert "run: message setup" in result.output
    # The operator still runs, and is written.
    assert rig.target.read_text() == expected({"mailbox": STRANGER})


def test_no_message_on_the_path_gets_the_step(rig: Rig) -> None:
    rig.remove("message")
    result = rig.run("--address", "someone@stranger.test")
    assert result.exit_code == setup_mod.EXIT_STEPS_LEFT
    assert "`message` is not on the PATH" in result.output
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


def settings_hits(root: Path) -> list[tuple[str, str]]:
    """Every (path, stripped line) under ROOT/src naming `.settings`."""
    return [
        (path.relative_to(root).as_posix(), line.strip())
        for path in sorted((root / "src").rglob("*.py"))
        for line in path.read_text(encoding="utf-8").splitlines()
        if ".settings" in line
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
    ],
)
def test_the_source_check_fails_on_any_other_use(tmp_path: Path, planted: str) -> None:
    pkg = tmp_path / "src" / "sessionkit"
    pkg.mkdir(parents=True)
    (pkg / "setup.py").write_text(LEGACY_LINE[1] + "\n")
    (pkg / "other.py").write_text(planted + "\n")
    assert settings_hits(tmp_path) != [LEGACY_LINE]


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
    # ONCE in the docs: INSTALL.md's "Upgrading from 0.1.0" note.
    hits = []
    for top, dirs, names in os.walk(ROOT):
        dirs[:] = sorted(d for d in dirs if not d.startswith("."))  # .venv, caches
        for name in sorted(n for n in names if n.endswith(".md")):
            rel = (Path(top) / name).relative_to(ROOT).as_posix()
            if rel == "CHANGELOG.md" or rel.startswith("tests/fixtures/changelog_union/"):
                continue  # CHANGELOG history and its copies
            hits += [rel] * len(OLD_ROOT.findall((Path(top) / name).read_text(encoding="utf-8")))
    assert hits == ["INSTALL.md"]
    install = (ROOT / "INSTALL.md").read_text(encoding="utf-8")
    start = install.index("- **Upgrading from 0.1.0.**")
    note = install[start : install.index("\n- ", start + 1)]
    assert f"`~/{OLD_DROP_IN}`" in note
    assert f"`~/{OPERATOR_DROP_IN}`" in note
    assert "exits 1" in note and "--dry-run" in note
