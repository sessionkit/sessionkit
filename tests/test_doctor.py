"""`sessionkit doctor`, run against a fake Mac.

The fake Mac is tests/_fakemac.py's: a scratch HOME, stub tools first on
PATH, and calls.log. The doctor runs in this process, under click's runner,
with os.environ swapped for the fake Mac's and its script_path() pointed at
the FakeMac's copy of install.sh (the copy differs only in BREW_PATHS; see
test_install_sh.py). Nothing here writes outside the scratch folder.
"""

from __future__ import annotations

import importlib
import json
import os
import re
import shutil
import sys
import tomllib
from importlib.metadata import version
from pathlib import Path

import pytest

# The family modules the doctor reads, imported here with the real
# environment: none bakes a scratch HOME into a module constant.
import sessionmail._sender
import sessionmail._settings  # noqa: F401
import sessionphone.service
import sessionphone.settings  # noqa: F401
import sessiontools.start.identity  # noqa: F401
from _fakemac import INSTALL_VERB, SPEECH_PROBE_URL, FakeMac
from click.testing import CliRunner

from sessionkit import doctor as kit_doctor
from sessionkit.cli import main

ROOT = Path(__file__).resolve().parent.parent
PACKAGED = ROOT / "src" / "sessionkit" / "install.sh"
HOOKS = Path(".sessionkit/mail/settings/mail.json")
PHONE = Path(".sessionkit/phone/settings/phone.json")
PLIST = Path("Library/LaunchAgents/dev.sessionkit.phone.bot.claude.plist")
KEY_INIT = Path(".claude/agents/lib/session-keys/session-key-init")
REMEDY = "    → "


class Doc:
    def __init__(self, rc: int, out: str, calls: list[str]):
        self.rc = rc
        self.out = out
        self.lines = out.splitlines()
        self.calls = calls

    def row(self, prefix: str) -> str:
        hits = [ln for ln in self.lines if ln.startswith(prefix)]
        assert len(hits) == 1, (prefix, self.out)
        return hits[0]

    def under(self, prefix: str) -> list[str]:
        """The indented lines right under the row PREFIX."""
        i = self.lines.index(self.row(prefix))
        out = []
        for ln in self.lines[i + 1 :]:
            if not ln.startswith(" "):
                break
            out.append(ln)
        return out


@pytest.fixture
def mac(tmp_path: Path) -> FakeMac:
    return FakeMac(tmp_path)


def hooks(mac: FakeMac, text: str | None) -> None:
    p = mac.home / HOOKS
    if text is None:
        p.unlink(missing_ok=True)
        return
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def all_here(mac: FakeMac) -> FakeMac:
    mac.everything()
    hooks(mac, '{"version": 1, "hooks": true, "sendmail": "drop"}')
    return mac


def doctor(mac: FakeMac, monkeypatch, *args: str, env: dict[str, str] | None = None) -> Doc:
    """`sessionkit doctor ARGS` on MAC: os.environ is the fake Mac's alone."""
    monkeypatch.setattr(kit_doctor, "script_path", lambda: mac.script)
    for k in list(os.environ):
        monkeypatch.delenv(k)
    for k, v in (env or mac.env()).items():
        monkeypatch.setenv(k, v)
    start = len(mac._calls())
    r = CliRunner().invoke(main, ["doctor", *args])
    if r.exception and not isinstance(r.exception, SystemExit):
        raise r.exception
    return Doc(r.exit_code, r.output, mac._calls()[start:])


# --- All here ---------------------------------------------------------------

ROWS = (
    "🍎 macOS:",
    "👤 Administrator:",
    "🍺 Homebrew:",
    "🐍 uv:",
    "🤖 Claude Code:",
    "🖥️ tmux:",
    "🎞️ ffmpeg:",
    "📨 notmuch:",
    "📦 Session Kit:",
    "⚙️ Session Kit setup",
    "🧩 Claude Code plugins:",
    "🎙️ Ears voice model:",
    "👂 Ears services",
    "🗣️ Speech server on port 8890:",
    "🔌 Port 8890",
    "📬 Mail hooks:",
    "📞 Phone bot",
    "🔑 Session key",
)


def test_all_here_exits_0_with_one_line_per_row(mac, monkeypatch):
    all_here(mac).flag("phone_loaded")  # the optional bot too: no → line at all
    d = doctor(mac, monkeypatch)
    assert d.rc == 0, d.out
    for prefix in ROWS:
        d.row(prefix)  # exactly one each
    assert REMEDY not in d.out
    assert d.row("📬 Mail hooks:") == "📬 Mail hooks: on"
    assert d.row("🗣️ Speech server on port 8890:").endswith("serving")
    assert d.lines[-1] == "✅ sessionkit doctor: nothing the kit needs is missing."
    # The rows come in the design's order: the installer's, then the doctor's.
    at = [d.lines.index(d.row(p)) for p in ROWS]
    assert at == sorted(at)


# --- Each one missing -------------------------------------------------------


def _rm(p: Path) -> None:
    p.unlink()


MISSING = {
    "🍺 Homebrew:": lambda m: (_rm(m.brew_dir / "brew"), setattr(m, "brew_on_path", False)),
    "🐍 uv:": lambda m: _rm(m.home / ".local/bin/uv"),
    "🤖 Claude Code:": lambda m: _rm(m.home / ".local/bin/claude"),
    "🖥️ tmux:": lambda m: _rm(m.state / "brew/tmux"),
    "🎞️ ffmpeg:": lambda m: _rm(m.state / "brew/ffmpeg"),
    "📨 notmuch:": lambda m: _rm(m.state / "brew/notmuch"),
    "📦 Session Kit:": lambda m: _rm(m.state / "kit"),
    "⚙️ Session Kit setup": lambda m: _rm(m.state / "setup"),
    "🧩 Claude Code plugins:": lambda m: _rm(m.state / "plugin"),
    "🎙️ Ears voice model:": lambda m: _rm(m.state / "ears_model"),
    "👂 Ears services": lambda m: _rm(m.state / "speech"),
    "🗣️ Speech server on port 8890:": lambda m: _rm(m.state / "speech_serving"),
    "📬 Mail hooks:": lambda m: hooks(m, None),
}


@pytest.mark.parametrize("prefix", list(MISSING))
def test_each_required_row_missing_flips_to_missing_with_a_remedy_and_exit_1(
    mac, monkeypatch, prefix
):
    all_here(mac)
    MISSING[prefix](mac)
    d = doctor(mac, monkeypatch)
    assert d.rc == 1, d.out
    assert d.under(prefix), f"no → line under {prefix!r}:\n{d.out}"
    assert d.under(prefix)[0].startswith(REMEDY), d.out
    assert not d.lines[-1].startswith("✅"), d.out


def test_no_speech_leaves_the_speech_rows_out_and_does_not_fail(mac, monkeypatch):
    all_here(mac)
    _rm(mac.state / "speech")
    _rm(mac.state / "speech_serving")
    d = doctor(mac, monkeypatch, "--no-speech")
    assert d.rc == 0, d.out
    assert "(left out: --no-speech)" in d.row("👂 Ears services")
    assert d.row("🗣️ Speech server on port 8890:").endswith("not checked (left out: --no-speech)")
    assert not any(c.startswith("curl") for c in d.calls)


def test_the_optional_and_info_rows_never_fail(mac, monkeypatch):
    # No phone bot and an unkeyed shell, everything else here: exit 0.
    d = doctor(all_here(mac), monkeypatch)
    assert d.rc == 0, d.out
    assert d.row("📞 Phone bot").endswith(": not installed")
    assert "not keyed" in d.row("🔑 Session key")


def test_the_installer_missing_and_the_hooks_off_say_both(mac, monkeypatch):
    all_here(mac)
    _rm(mac.state / "plugin")
    hooks(mac, None)
    d = doctor(mac, monkeypatch)
    assert d.rc == 1
    assert "1 row above is missing" in d.out  # the installer's own verdict
    assert d.lines[-1].startswith("🩺 sessionkit doctor: 1 row just above is missing")


def test_installer_rows_missing_alone_ends_on_the_doctors_verdict(mac, monkeypatch):
    all_here(mac)
    _rm(mac.state / "plugin")
    d = doctor(mac, monkeypatch)
    assert d.rc == 1
    assert d.lines[-1] == "🩺 sessionkit doctor: the installer's rows above say what is missing."


# --- One source of truth ------------------------------------------------------


def test_a_the_packaged_script_is_a_symlink_to_the_root_install_sh():
    assert PACKAGED.is_symlink()
    assert os.readlink(PACKAGED) == "../../install.sh"  # inside the repo
    assert PACKAGED.samefile(ROOT / "install.sh")


def test_c_script_path_is_the_packaged_file():
    p = kit_doctor.script_path()
    assert p == Path(kit_doctor.__file__).parent / "install.sh"
    assert p.is_file()
    assert p.read_bytes() == (ROOT / "install.sh").read_bytes()


def test_d_doctor_output_starts_with_exactly_the_check_lines(mac, monkeypatch):
    all_here(mac)
    _rm(mac.state / "plugin")  # a missing row, so a remedy is in the prefix too
    check = mac.run("--check")
    d = doctor(mac, monkeypatch)
    assert check.rc == 1
    assert d.out.startswith(check.out), (check.out, d.out)
    assert "🩺 And what the installer does not check:" in d.out[len(check.out) :]


def test_d_no_speech_reaches_the_script(mac, monkeypatch):
    all_here(mac)
    check = mac.run("--check", "--no-speech")
    d = doctor(mac, monkeypatch, "--no-speech")
    assert d.out.startswith(check.out)


# Each shared probe lives in install.sh alone; the doctor holds none of them.
# Each is written as install.sh writes it: `"$BREW" list --versions`,
# `"$UV" tool list`, the speech URL's path.
SHARED_PROBES = ("list --versions", "tool list", "plugin list", "backends", "services status", "/v1/models")


@pytest.mark.parametrize("probe", SHARED_PROBES)
def test_e_doctor_py_holds_none_of_the_shared_probes(probe):
    src = Path(kit_doctor.__file__).read_text(encoding="utf-8")
    assert probe not in src
    assert probe in (ROOT / "install.sh").read_text(encoding="utf-8")


# --- Read-only ----------------------------------------------------------------


@pytest.mark.parametrize("state", ["all_here", "fresh"])
def test_the_run_is_read_only(mac, monkeypatch, state):
    if state == "all_here":
        all_here(mac)
        (mac.home / PLIST).parent.mkdir(parents=True)
        (mac.home / PLIST).write_text("<plist/>", encoding="utf-8")
        mac.flag("phone_loaded")
    before = mac.tree()
    d = doctor(mac, monkeypatch)
    assert mac.tree() == before
    assert d.calls, "the stubs were asked nothing"
    assert not [c for c in d.calls if INSTALL_VERB.match(c)], d.calls
    curls = [c for c in d.calls if c.startswith("curl ")]
    assert curls and all(c.endswith(SPEECH_PROBE_URL) for c in curls), curls
    assert all(c.split()[1] == "print" for c in d.calls if c.startswith("launchctl "))


def test_the_speech_row_asks_the_server_not_the_stt_line(mac, monkeypatch):
    # EARS-488: `ears services status` says stt not installed while :8890 serves.
    all_here(mac)
    mac.flag("stt_not_installed")
    d = doctor(mac, monkeypatch)
    assert d.rc == 0, d.out
    assert d.row("🗣️ Speech server on port 8890:").endswith("serving")
    assert "stt" not in d.out


# --- The doctor's own rows ------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "state"),
    [
        (None, "off (no ~/.sessionkit/mail/settings/mail.json yet)"),
        ('{"hooks": false}', "off"),
        ('{"hooks": "true"}', 'off (`hooks` is "true", not true or false)'),
        ('{"hooks": true}', "on"),
    ],
)
def test_hooks_row(mac, monkeypatch, text, state):
    all_here(mac)
    hooks(mac, text)
    d = doctor(mac, monkeypatch)
    assert d.row("📬 Mail hooks:") == f"📬 Mail hooks: {state}"
    if state == "on":
        assert d.rc == 0 and d.under("📬 Mail hooks:") == []
    else:
        assert d.rc == 1
        assert d.under("📬 Mail hooks:")[0] == (
            f'{REMEDY}set "hooks": true in ~/.sessionkit/mail/settings/mail.json, and change no other key'
        )


def test_a_fresh_install_reads_green_on_the_hooks_row(mac, monkeypatch):
    # SK-236: install.sh turns the hooks on with sessionmail's verb (route a),
    # so the doctor on a Mac fresh from the installer exits 0.
    mac.with_brew()
    first = mac.run("--yes")
    assert first.rc == 0, first.out
    assert "pager settings hooks on" in first.calls
    mac.local_bin_on_path = True  # a new terminal, as the end screen asks
    mac.flag("speech_serving")  # the server, done loading its model
    d = doctor(mac, monkeypatch)
    assert d.row("📬 Mail hooks:") == "📬 Mail hooks: on"
    assert d.rc == 0, d.out


def test_the_installers_hooks_step_by_hand_is_the_doctors_remedy_word_for_word():
    by_hand = re.findall(r"^HOOKS_BY_HAND='(.+)'$", PACKAGED.read_text(encoding="utf-8"), re.MULTILINE)
    row = kit_doctor.hooks_row({"HOME": "/nonexistent-home"})
    assert by_hand and row.under[0] == f"{REMEDY}{by_hand[0]}"


def test_phone_row_loaded(mac, monkeypatch):
    all_here(mac)
    mac.flag("phone_loaded")
    d = doctor(mac, monkeypatch)
    assert d.row("📞 Phone bot") == "📞 Phone bot (optional, for calls): claude, running, pid 77"
    assert d.under("📞 Phone bot") == [
        "   the call ear (DC_EARS): not checked yet: sessionphone has no check for it to ask"
    ]
    assert d.rc == 0


def test_phone_row_installed_not_loaded(mac, monkeypatch):
    all_here(mac)
    (mac.home / PLIST).parent.mkdir(parents=True)
    (mac.home / PLIST).write_text("<plist/>", encoding="utf-8")
    d = doctor(mac, monkeypatch)
    assert d.row("📞 Phone bot").endswith(": claude, installed but not loaded")
    assert d.under("📞 Phone bot")[0] == f"{REMEDY}sessionphone bot install"
    assert d.rc == 0


def test_phone_row_not_installed_names_both_steps(mac, monkeypatch):
    d = doctor(all_here(mac), monkeypatch)
    assert d.under("📞 Phone bot")[:2] == [
        f"{REMEDY}sessionphone setup --name NAME",
        f"{REMEDY}sessionphone bot install",
    ]


def test_phone_row_reads_not_checked_on_a_bot_name_refusal(mac, monkeypatch):
    # Two bots recorded and none named: sessionphone refuses to guess.
    all_here(mac)
    p = mac.home / PHONE
    p.parent.mkdir(parents=True)
    p.write_text(json.dumps({"bots": {"ada": {}, "bob": {}}}), encoding="utf-8")
    d = doctor(mac, monkeypatch)
    row = d.row("📞 Phone bot")
    assert row.startswith("📞 Phone bot (optional, for calls): not checked (")
    assert "records 2 bots (ada, bob)" in row
    assert "sessionphone bot install" not in row  # verb=None: no phone verb named
    assert d.rc == 0


def test_key_row_unkeyed(mac, monkeypatch):
    d = doctor(all_here(mac), monkeypatch)
    assert d.row("🔑 Session key") == "🔑 Session key (info): this shell is not keyed: its mail goes unsigned"
    assert d.under("🔑 Session key") == [
        "   session-key-init: not found, at ~/.claude/agents/lib/session-keys/session-key-init",
        "   no kit launch makes a session key yet, so this row never fails",
    ]


def test_key_row_keyed(mac, monkeypatch):
    all_here(mac)
    pub = mac.home / "pub.key"
    pub.write_text("k", encoding="utf-8")
    init = mac.home / KEY_INIT
    init.parent.mkdir(parents=True)
    init.write_text("#!/bin/sh\n", encoding="utf-8")
    init.chmod(0o755)
    env = mac.env() | {"CLAUDE_SESSION_AGENT_SOCK": str(mac.home / "s.sock"), "CLAUDE_SESSION_PUB": str(pub)}
    d = doctor(mac, monkeypatch, env=env)
    assert d.row("🔑 Session key") == "🔑 Session key (info): this shell is keyed: its mail is signed"
    assert d.under("🔑 Session key")[0] == (
        "   session-key-init: found, at ~/.claude/agents/lib/session-keys/session-key-init"
    )
    assert d.rc == 0


# --- Import guards and the family pins ---------------------------------------

# (module, names the doctor takes from it, distribution, the row's word)
FAMILY_READS = (
    ("sessionmail._settings", ("read", "ON", "MISSING", "SHOWN"), "sessionmail", "📬 Mail hooks: not checked"),
    ("sessionphone.settings", ("bot_name", "Bad"), "sessionphone", "📞 Phone bot (optional, for calls): not checked"),
    ("sessionphone.service", ("status",), "sessionphone", "📞 Phone bot (optional, for calls): not checked"),
    ("sessionmail._sender", ("keyed",), "sessionmail", "🔑 Session key (info): not checked"),
    ("sessiontools.start.identity", ("key_init_path",), "sessiontools", "   session-key-init: not checked"),
)


@pytest.mark.parametrize(("module", "names", "dist", "word"), FAMILY_READS)
def test_each_import_guard_failing_reads_not_checked(mac, monkeypatch, module, names, dist, word):
    monkeypatch.setitem(sys.modules, module, None)  # `import module` now raises ImportError
    d = doctor(all_here(mac), monkeypatch)
    assert any(ln.startswith(word) for ln in d.lines), d.out
    # A guard that trips is not a missing row, except the hooks', which then
    # cannot say on: it reads not checked, and never fails the run.
    assert d.rc == 0, d.out


def _locked_version(dist: str) -> str:
    lock = tomllib.loads((ROOT / "uv.lock").read_text(encoding="utf-8"))
    (pkg,) = [p for p in lock["package"] if p["name"] == dist]
    return pkg["version"]


@pytest.mark.parametrize(("module", "names", "dist", "word"), FAMILY_READS)
def test_the_family_reads_import_at_the_locked_versions(module, names, dist, word):
    # A rename in a family release turns this red, not the row silently quiet.
    assert version(dist) == _locked_version(dist), f"{dist} is not the locked version: re-sync"
    mod = importlib.import_module(module)
    for n in names:
        assert hasattr(mod, n), f"{module}.{n} is gone in {dist} {version(dist)}"


# --- Exits the doctor passes through ------------------------------------------


def test_not_macos_passes_exit_3_through_and_adds_no_rows(mac, monkeypatch):
    all_here(mac)
    mac.flag("os", "Linux")
    d = doctor(mac, monkeypatch)
    assert d.rc == 3, d.out
    assert "🩺 And what the installer does not check:" not in d.out


def test_a_usage_exit_passes_through(tmp_path, monkeypatch):
    script = tmp_path / "install.sh"
    script.write_text('echo "install.sh: unknown option" >&2\nexit 2\n', encoding="utf-8")
    monkeypatch.setattr(kit_doctor, "script_path", lambda: script)
    lines: list[str] = []
    assert kit_doctor.run(echo=lines.append) == 2
    assert lines == ["install.sh: unknown option"]


def test_no_script_names_the_one_line_check(tmp_path, monkeypatch):
    monkeypatch.setattr(kit_doctor, "script_path", lambda: tmp_path / "gone.sh")
    lines: list[str] = []
    assert kit_doctor.run(echo=lines.append) == 3
    assert "    curl -fsSL https://sessionkit.ai/install.sh | bash -s -- --check" in lines


def test_the_one_line_check_is_the_installers_own_url():
    src = (ROOT / "install.sh").read_text(encoding="utf-8")
    url = re.search(r"^SCRIPT_URL=(\S+)$", src, re.MULTILINE).group(1)
    assert kit_doctor.CHECK_ONE_LINER == f"curl -fsSL {url} | bash -s -- --check"


def test_help_names_the_check_for_a_mac_without_the_kit():
    out = CliRunner().invoke(main, ["doctor", "--help"]).output
    assert kit_doctor.CHECK_ONE_LINER in out
    assert "bash install.sh --check" in out
    assert "--no-speech" in out
    assert "doctor" in CliRunner().invoke(main, ["--help"]).output


def test_help_says_the_tools_it_asks_keep_their_own_files():
    # A scratch-HOME run on a build host: in an empty home, brew, uv
    # and claude made their caches. The doctor writes none, and says so.
    flat = " ".join(CliRunner().invoke(main, ["doctor", "--help"]).output.split())
    assert "it writes no file of its own" in flat
    assert "brew, uv and claude make their caches" in flat
    # verify-002 measured claude's plugin reads opening HTTPS to Anthropic's
    # API: the help scopes "network" to the doctor's own probes and says so.
    assert "The only network it reaches itself is the speech server on 127.0.0.1:8890, which it probes" in flat
    # Not one call: the port check (nc -z) and the probe (curl) both reach :8890.
    assert "one network call" not in flat
    assert "its brew reads download nothing" in flat
    assert "claude, asked for its plugins, reaches Anthropic's API over HTTPS" in flat
    assert "its only network is" not in flat
    assert "package list" not in flat
    assert "INSTALL.md section 4, in https://github.com/sessionkit/sessionkit, names each file" in flat


def test_bash_is_the_macs_own_first():
    assert kit_doctor.bash() == ("/bin/bash" if Path("/bin/bash").exists() else shutil.which("bash"))
