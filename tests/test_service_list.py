"""`sessionkit service list`: every row of the state table, A-Z, 53 columns.

The rows come from the files (tests/_fakekit.py) joined with a fake
launchctl (tests/_fakelaunchd.py). HOME is a scratch folder: nothing reads
the real home or the real launchd.
"""

from __future__ import annotations

import json

import pytest
from _fakekit import DROP, FakeKit
from _fakelaunchd import FakeLaunchd
from click.testing import CliRunner

from sessionkit import launchd, services
from sessionkit.cli import main

L = "dev.sessionkit."


@pytest.fixture
def kit(tmp_path) -> FakeKit:
    return FakeKit(tmp_path)


@pytest.fixture
def fake(tmp_path) -> FakeLaunchd:
    return FakeLaunchd(tmp_path)


def run(kit: FakeKit, fake: FakeLaunchd, *args: str):
    env = {"HOME": str(kit.home), **fake.env()}
    return CliRunner().invoke(main, ["service", *args], env=env)


def one(kit: FakeKit, jobs: dict | None = None) -> services.Row:
    (row,) = services.survey(kit.home, listed=jobs or {}).rows
    return row


def ls(pid=None, status=0):
    return launchd.Listed(pid, status)


# --- One test per row of the state table -------------------------------------


def test_enabled_and_running_is_up(kit):
    kit.service("voice", "talk")
    row = one(kit, {f"{L}voice.talk": ls(10, -15)})
    assert (row.glyph, row.state, row.note) == ("●", "up", "")


def test_an_on_demand_job_waiting_is_idle(kit):
    kit.service("tools", "default-model", kind="on-demand")
    row = one(kit, {f"{L}tools.default-model": ls(None, 0)})
    assert (row.glyph, row.state, row.note) == ("○", "idle", "")


def test_a_job_its_owner_switched_off_is_off(kit):
    kit.service("voice", "ears-sounds")
    kit.plist(f"{L}voice.ears-sounds", KeepAlive={"SuccessfulExit": False})
    row = one(kit, {f"{L}voice.ears-sounds": ls(None, 0)})
    assert (row.glyph, row.state, row.note) == ("○", "off", "switched off")


@pytest.mark.parametrize(("status", "note"), [(3, "exited 3"), (-9, "signal 9")])
def test_a_job_down_after_a_non_zero_exit_says_why(kit, status, note):
    kit.service("voice", "talk")
    row = one(kit, {f"{L}voice.talk": ls(None, status)})
    assert (row.glyph, row.state, row.note) == ("✕", "down", note)


def test_a_daemon_loaded_and_not_running_after_exit_0_is_down(kit):
    kit.service("voice", "talk")
    kit.plist(f"{L}voice.talk", KeepAlive=True)
    row = one(kit, {f"{L}voice.talk": ls(None, 0)})
    assert (row.glyph, row.state, row.note) == ("○", "down", "")


def test_not_loaded_with_a_plist_is_down_not_loaded(kit):
    kit.service("voice", "talk")
    kit.plist(f"{L}voice.talk")
    row = one(kit)
    assert (row.glyph, row.state, row.note) == ("✕", "down", "not loaded")


def test_not_installed_names_the_install(kit):
    kit.service("voice", "talk", install="voice-tool install --only talk")
    row = one(kit)
    assert (row.glyph, row.state) == ("✕", "down")
    assert row.note == "not installed: voice-tool install --only talk"


@pytest.mark.parametrize("jobs", [{}, {f"{L}voice.talk": ls(None, 0)}])
def test_disabled_and_not_running_is_disabled(kit, jobs):
    kit.service("voice", "talk", enabled=False)
    row = one(kit, jobs)
    assert (row.glyph, row.state, row.note) == ("○", "disabled", "")


def test_disabled_but_running_is_up_with_a_note(kit):
    kit.service("voice", "talk", enabled=False)
    row = one(kit, {f"{L}voice.talk": ls(5, 0)})
    assert (row.glyph, row.state, row.note) == ("●", "up", "file says disabled")


def test_a_run_service_is_manual(kit):
    kit.service("tools", "web", label=DROP, run=["session", "web", "serve"])
    row = one(kit)
    assert (row.glyph, row.state) == ("○", "manual")
    assert row.note == "runs in the foreground: session web serve"


def test_a_bad_file_is_a_row_naming_the_fault(kit):
    kit.raw(kit.root / "voice" / "services" / "talk.json", "{oops")
    row = one(kit)
    assert (row.glyph, row.state, row.note, row.name) == (
        "✕",
        "bad file",
        "not JSON",
        "talk",
    )


def test_a_kit_job_with_no_file_is_listed_in_its_package(kit):
    kit.plist(f"{L}phone.bot.alpha", KeepAlive=True)
    s = services.survey(kit.home, listed={f"{L}phone.bot.alpha": ls(7, 3)})
    (row,) = s.rows
    assert (row.package, row.name, row.state, row.file) == (
        "phone",
        "bot.alpha",
        "up",
        None,
    )
    assert s.transition == 1
    assert s.footer == [
        "1 job has no service file yet.",
        "status NAME says whose install writes it.",
    ]


def test_a_kit_plist_not_loaded_with_no_file_is_listed(kit):
    kit.plist(f"{L}voice.ears-stt", KeepAlive=True)
    (row,) = services.survey(kit.home, listed={}).rows
    assert (row.name, row.glyph, row.state, row.note) == (
        "ears-stt",
        "✕",
        "down",
        "not loaded",
    )


def test_a_loaded_job_with_no_plist_and_no_file_is_stray(kit):
    (row,) = services.survey(kit.home, listed={f"{L}voice.old": ls(3, 0)}).rows
    assert (row.glyph, row.state, row.note) == ("✕", "stray", "no plist on disk")


def test_a_file_claims_its_job_so_no_transition_row(kit):
    kit.service("voice", "talk")
    s = services.survey(
        kit.home, listed={f"{L}voice.talk": ls(1, 0), "com.other.x": ls(2, 0)}
    )
    assert [r.name for r in s.rows] == ["talk"] and s.transition == 0 and s.footer == []


def test_a_json_file_with_no_marker_is_a_footer_line(kit):
    kit.service("voice", "talk")
    kit.raw(kit.root / "voice" / "services" / "readme.json", "{}")
    s = services.survey(kit.home, listed={})
    assert s.footer == ["1 file in voice/services/ is not a service file."]


# --- The view ----------------------------------------------------------------


def test_groups_and_names_are_a_to_z_with_heading_counts(kit, fake):
    kit.service("voice", "talk")
    kit.service("voice", "ears-keeper")
    kit.service("voice", "mlx-audio", enabled=False)
    kit.service(
        "mail", "seat-agent.alpha-chat", agent_dir="seat-agents", agent="alpha-chat"
    )
    kit.service("phone", "bot.beta", agent_dir="bots", agent="beta")
    kit.service("phone", "bot.alpha", agent_dir="bots", agent="alpha")
    for label in ("voice.talk", "voice.ears-keeper", "mail.seat-agent.alpha-chat"):
        fake.job(L + label, 100, 0)
    fake.job(f"{L}phone.bot.alpha", 101, 3).job(f"{L}phone.bot.beta", 102, 0)
    result = run(kit, fake, "list")
    assert result.exit_code == 0, result.output
    assert result.output.splitlines() == [
        "mail  1 up",
        "  ● seat-agent.alpha-chat  up",
        "phone  2 up",
        "  ● bot.alpha              up",
        "  ● bot.beta               up",
        "voice  2 up · 1 disabled",
        "  ● ears-keeper            up",
        "  ○ mlx-audio              disabled",
        "  ● talk                   up",
    ]


def test_an_up_row_shows_no_last_exit(kit, fake):
    kit.service("voice", "talk")
    fake.job(f"{L}voice.talk", 10, -15)
    out = run(kit, fake, "list").output
    assert "15" not in out and "exit" not in out and "signal" not in out


def test_every_line_fits_53_columns(kit, fake):
    long_name = "seat-agent.abcdefghijk"  # 22 characters
    assert len(long_name) == 22
    kit.service("mail", long_name)
    kit.service("voice", "talk", install="x " * 60)
    kit.service("voice", "a-very-long-service-name-beyond-any-column-we-keep-at-all")
    fake.job(f"{L}voice.ears-old", None, 3)  # transition: two footer lines
    lines = run(kit, fake, "list").output.splitlines()
    assert lines and max(len(line) for line in lines) <= services.WIDTH
    talk = next(line for line in lines if " talk " in line)
    assert talk.endswith("…") and "not installed: x x" in talk


def test_json_has_the_same_keys_for_every_row(kit, fake):
    kit.service("voice", "talk", hazard=["call"])
    fake.job(f"{L}voice.talk", 10, 0).job(f"{L}phone.bot.alpha", 11, 0)
    result = run(kit, fake, "list", "--json")
    rows = json.loads(result.output)
    keys = {
        "name", "group", "label", "state", "note", "enabled", "loaded", "pid",
        "last_status", "installed", "kind", "hazard", "file", "plist", "install",
    }  # fmt: skip
    assert [set(r) for r in rows] == [keys, keys]
    talk = next(r for r in rows if r["name"] == "talk")
    assert talk["hazard"] == ["call"] and talk["pid"] == 10 and talk["group"] == "voice"
    bot = next(r for r in rows if r["name"] == "bot.alpha")
    assert bot["file"] is None and bot["hazard"] == ["call"]


@pytest.mark.parametrize("make_root", [True, False])
def test_an_empty_or_missing_tree_says_so_and_exits_0(tmp_path, fake, make_root):
    home = tmp_path / "h"
    if make_root:
        (home / ".sessionkit").mkdir(parents=True)
    env = {"HOME": str(home), **fake.env()}
    result = CliRunner().invoke(main, ["service", "list"], env=env)
    assert result.exit_code == 0
    assert result.output == "No services found under ~/.sessionkit.\n"


def test_error_125_exits_3(kit, fake):
    fake.fail("list", 125)
    result = run(kit, fake, "list")
    assert result.exit_code == 3
    assert "cannot be reached from this shell" in result.output


def test_another_launchctl_failure_exits_1(kit, fake):
    fake.fail("list", 5)
    assert run(kit, fake, "list").exit_code == 1


def test_bare_status_is_list(kit, fake):
    kit.service("voice", "talk")
    fake.job(f"{L}voice.talk", 10, 0)
    assert run(kit, fake, "status").output == run(kit, fake, "list").output


def test_list_help_prints_the_legend(kit, fake):
    out = run(kit, fake, "list", "-h").output
    for line in services.LEGEND:
        assert line in out


def test_list_makes_only_launchctl_list_calls(kit, fake):
    kit.service("voice", "talk")
    fake.job(f"{L}voice.talk", 10, 0)
    run(kit, fake, "list")
    assert fake.calls() == [["list"]]
