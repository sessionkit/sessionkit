"""`sessionkit service restart`: kickstart -k, the confirm, the call guard.

One name restarts at once. A group, all or several names list every job in
the order they will run and ask y/N; with no terminal they need --yes. A
live call refuses a `hazard: call` service and a job with no file, unless
--force. The call check is a seam (services.live_calls): no phone needed.
"""

from __future__ import annotations

import types

import pytest
from _fakekit import DROP, FakeKit
from _fakelaunchd import FakeLaunchd
from click.testing import CliRunner

from sessionkit import cli, launchd, services
from sessionkit.cli import main

L = "dev.sessionkit."
CALL = "call msg 7 - chat 1 with a caller, up 3 min (/x/call-live.json)"


@pytest.fixture
def kit(tmp_path) -> FakeKit:
    return FakeKit(tmp_path)


@pytest.fixture
def fake(tmp_path) -> FakeLaunchd:
    return FakeLaunchd(tmp_path)


@pytest.fixture
def calls(monkeypatch) -> list[str]:
    """The live calls the guard sees; empty unless a test adds one."""
    live: list[str] = []
    monkeypatch.setattr(services, "live_calls", lambda home=None, loaded=(): list(live))
    return live


@pytest.fixture
def tty(monkeypatch):
    monkeypatch.setattr(cli, "_interactive", lambda: True)


def run(kit, fake, *args, input=None):
    env = {"HOME": str(kit.home), **fake.env()}
    return CliRunner().invoke(main, ["service", "restart", *args], env=env, input=input)


def kicked(fake) -> list[str]:
    return [c[-1].split("/", 2)[-1] for c in fake.verbs("kickstart")]


def voice(kit, fake):
    """Three loaded voice services; speech is order 10, so it goes first."""
    kit.service("voice", "talk")
    kit.service("voice", "ears-keeper", hazard=["call"])
    kit.service("voice", "mlx-audio", order=10)
    for name in ("talk", "ears-keeper", "mlx-audio"):
        fake.job(f"{L}voice.{name}", 100, 0)


def test_one_name_runs_exactly_kickstart_and_asks_nothing(kit, fake, calls):
    kit.service("voice", "talk")
    fake.job(f"{L}voice.talk", 10, 0)
    result = run(kit, fake, "talk")
    assert result.exit_code == 0, result.output
    assert result.output == "restarted voice.talk\n"
    assert fake.verbs("kickstart") == [
        ["kickstart", "-k", f"gui/{launchd.uid()}/{L}voice.talk"]
    ]


def test_not_loaded_and_not_installed_is_refused_naming_the_install(kit, fake, calls):
    kit.service("voice", "talk", install="voice-tool install --only talk")
    result = run(kit, fake, "talk")
    assert result.exit_code == 2
    assert "not installed: voice-tool install --only talk" in result.output
    assert fake.verbs("kickstart") == []


def test_not_loaded_with_a_plist_is_refused_naming_how_to_load_it(kit, fake, calls):
    kit.service("voice", "talk")
    plist = kit.plist(f"{L}voice.talk")
    result = run(kit, fake, "talk")
    assert result.exit_code == 2
    assert f"launchctl bootstrap gui/{launchd.uid()} {plist}" in result.output
    assert fake.verbs("kickstart") == []


def test_a_group_lists_its_jobs_in_order_and_n_runs_nothing(kit, fake, calls, tty):
    voice(kit, fake)
    result = run(kit, fake, "voice", input="n\n")
    assert result.exit_code == 2
    lines = result.output.splitlines()
    assert lines[:4] == [
        "Restart 3 jobs, in this order:",
        f"  voice.mlx-audio  ({L}voice.mlx-audio)",
        f"  voice.ears-keeper  ({L}voice.ears-keeper)",
        f"  voice.talk  ({L}voice.talk)",
    ]
    assert "Nothing restarted." in result.output
    assert fake.verbs("kickstart") == []


def test_a_group_answered_y_runs_in_order(kit, fake, calls, tty):
    voice(kit, fake)
    result = run(kit, fake, "voice", input="y\n")
    assert result.exit_code == 0, result.output
    assert kicked(fake) == [
        f"{L}voice.mlx-audio",
        f"{L}voice.ears-keeper",
        f"{L}voice.talk",
    ]


def test_a_group_with_no_terminal_needs_yes(kit, fake, calls):
    voice(kit, fake)
    result = run(kit, fake, "voice")
    assert result.exit_code == 2 and "give --yes" in result.output
    assert fake.verbs("kickstart") == []
    result = run(kit, fake, "voice", "--yes")
    assert result.exit_code == 0, result.output
    assert len(kicked(fake)) == 3


def test_all_names_every_job_and_skips_the_ones_not_loaded(kit, fake, calls):
    voice(kit, fake)
    kit.service("tools", "pane-state", enabled=False)
    kit.service("tools", "web", label=DROP, run=["session", "web", "serve"])
    result = run(kit, fake, "all", "--yes")
    assert result.exit_code == 0, result.output
    assert "  skipped tools.pane-state: disabled: its file says" in result.output
    assert "  skipped tools.web: runs in the foreground" in result.output
    assert len(kicked(fake)) == 3


def test_two_names_ask_first(kit, fake, calls):
    voice(kit, fake)
    result = run(kit, fake, "talk", "ears-keeper")
    assert result.exit_code == 2 and "give --yes" in result.output


def test_a_live_call_refuses_a_call_hazard(kit, fake, calls):
    calls.append(CALL)
    kit.service("phone", "bot.alpha", agent_dir="bots", agent="alpha", hazard=["call"])
    fake.job(f"{L}phone.bot.alpha", 10, 0)
    result = run(kit, fake, "bot.alpha")
    assert result.exit_code == 2
    assert "a phone call is live; nothing was restarted." in result.output
    assert CALL in result.output and "--force restarts anyway" in result.output
    assert fake.verbs("kickstart") == []
    assert run(kit, fake, "bot.alpha", "--force").exit_code == 0
    assert kicked(fake) == [f"{L}phone.bot.alpha"]


def test_a_live_call_refuses_a_job_with_no_file(kit, fake, calls):
    calls.append(CALL)
    kit.plist(f"{L}voice.ears-mail", KeepAlive=True)
    fake.job(f"{L}voice.ears-mail", 10, 0)
    assert run(kit, fake, "ears-mail").exit_code == 2
    assert fake.verbs("kickstart") == []


def test_a_live_call_refuses_the_whole_group_naming_the_hazards(kit, fake, calls):
    calls.append(CALL)
    voice(kit, fake)
    result = run(kit, fake, "voice", "--yes")
    assert result.exit_code == 2
    assert "A restart of voice.ears-keeper can drop it." in result.output
    assert fake.verbs("kickstart") == []


def test_a_service_with_no_hazard_restarts_during_a_call(kit, fake, calls):
    calls.append(CALL)
    kit.service("voice", "talk")
    fake.job(f"{L}voice.talk", 10, 0)
    assert run(kit, fake, "talk").exit_code == 0
    assert kicked(fake) == [f"{L}voice.talk"]


def test_an_ambiguous_word_is_refused_naming_both(kit, fake, calls):
    kit.plist(f"{L}voice.keeper", KeepAlive=True)
    kit.plist(f"{L}tools.keeper", KeepAlive=True)
    result = run(kit, fake, "keeper")
    assert result.exit_code == 2
    assert "keeper names 2 services" in result.output
    assert "tools.keeper" in result.output and "voice.keeper" in result.output


def test_a_kickstart_failure_is_exit_1_with_launchctls_words(kit, fake, calls):
    kit.service("voice", "talk")
    fake.job(f"{L}voice.talk", 10, 0).kickstart_fails(
        f"{L}voice.talk", 5, "Input/output error"
    )
    result = run(kit, fake, "talk")
    assert result.exit_code == 1
    assert "voice.talk: Input/output error" in result.output


def test_an_unreachable_kickstart_is_exit_3_with_the_line_to_run(kit, fake, calls):
    kit.service("voice", "talk")
    fake.job(f"{L}voice.talk", 10, 0).fail("kickstart", 125)
    result = run(kit, fake, "talk")
    assert result.exit_code == 3
    assert f"launchctl kickstart -k gui/$(id -u)/{L}voice.talk" in result.output


def test_a_bad_file_is_refused(kit, fake, calls):
    kit.raw(kit.root / "voice" / "services" / "talk.json", "{oops")
    result = run(kit, fake, "talk")
    assert result.exit_code == 2 and "bad file (not JSON)" in result.output


def test_a_disabled_job_that_is_not_running_is_refused_and_not_started(
    kit, fake, calls
):
    kit.service("voice", "ears-speakers", enabled=False)
    fake.job(f"{L}voice.ears-speakers", None, 0)
    result = run(kit, fake, "ears-speakers")
    assert result.exit_code == 2
    assert "disabled: its file says enabled: false" in result.output
    assert kicked(fake) == []


def test_a_group_skips_a_disabled_job_and_restarts_the_rest(kit, fake, calls):
    voice(kit, fake)
    kit.service("voice", "ears-speakers", enabled=False)
    fake.job(f"{L}voice.ears-speakers", None, 0)
    result = run(kit, fake, "voice", "--yes")
    assert result.exit_code == 0, result.output
    assert "  skipped voice.ears-speakers: disabled" in result.output
    assert f"{L}voice.ears-speakers" not in kicked(fake)
    assert len(kicked(fake)) == 3


def test_a_disabled_job_that_still_runs_restarts(kit, fake, calls):
    kit.service("voice", "talk", enabled=False)
    fake.job(f"{L}voice.talk", 10, 0)
    result = run(kit, fake, "talk")
    assert result.exit_code == 0, result.output
    assert kicked(fake) == [f"{L}voice.talk"]


def test_restart_needs_a_word(kit, fake):
    assert run(kit, fake).exit_code == 2


# --- The call check itself: sessionphone's live_call, on each bot's plist ----


def _phone(live_call):
    settings = types.SimpleNamespace(Bad=LookupError)
    return types.SimpleNamespace(
        live_call=live_call,
        settings=settings,
        _call_line=lambda c: f"call {c['call_id']}",
    )


def test_no_phone_bot_means_no_call_and_no_import(kit, monkeypatch):
    def boom():
        raise AssertionError("imported")

    monkeypatch.setattr(services, "phone_service", boom)
    assert services.live_calls(kit.home) == []


def test_a_bot_with_a_call_is_named_from_its_plist_env(kit, monkeypatch):
    kit.plist(f"{L}phone.bot.alpha", EnvironmentVariables={"DC_HOME": "/x/alpha"})
    kit.plist(f"{L}phone.bot.beta", EnvironmentVariables={"DC_HOME": "/x/beta"})
    seen = []

    def live_call(env):
        seen.append(env["DC_HOME"])
        return {"call_id": 7} if env["DC_HOME"] == "/x/beta" else None

    monkeypatch.setattr(services, "phone_service", lambda: _phone(live_call))
    assert services.live_calls(kit.home) == ["call 7"]
    assert seen == ["/x/alpha", "/x/beta"]


def test_a_check_that_cannot_run_counts_as_a_call(kit, monkeypatch):
    kit.plist(f"{L}phone.bot.alpha", EnvironmentVariables={"DC_HOME": "/x"})

    def broken():
        raise ImportError("gone")

    monkeypatch.setattr(services, "phone_service", broken)
    assert services.live_calls(kit.home)[0].startswith("cannot check for a call")

    def raises(env):
        raise OSError("disk")

    monkeypatch.setattr(services, "phone_service", lambda: _phone(raises))
    assert services.live_calls(kit.home) == ["cannot check for a call: OSError: disk"]


def test_a_bot_with_no_root_is_no_call(kit, monkeypatch):
    kit.plist(f"{L}phone.bot.alpha", EnvironmentVariables={"DC_HOME": "/x"})

    def no_root(env):
        raise LookupError("no root")

    monkeypatch.setattr(services, "phone_service", lambda: _phone(no_root))
    assert services.live_calls(kit.home) == []


def test_a_bot_with_plists_none_readable_is_checked_on_this_shells_env(
    kit, monkeypatch
):
    kit.plist(f"{L}phone.bot.alpha")
    kit.plist(f"{L}phone.bot.beta", EnvironmentVariables={})
    monkeypatch.setenv("DC_HOME", "/x/shell")
    seen = []

    def live_call(env):
        seen.append(env.get("DC_HOME"))

    monkeypatch.setattr(services, "phone_service", lambda: _phone(live_call))
    assert services.live_calls(kit.home) == []
    assert seen == ["/x/shell"]


def test_this_shells_env_stands_in_only_when_no_bot_plist_reads(kit, monkeypatch):
    kit.plist(f"{L}phone.bot.alpha", EnvironmentVariables={"DC_HOME": "/x/alpha"})
    kit.plist(f"{L}phone.bot.beta")
    monkeypatch.setenv("DC_HOME", "/x/shell")
    seen = []

    def live_call(env):
        seen.append(env.get("DC_HOME"))

    monkeypatch.setattr(services, "phone_service", lambda: _phone(live_call))
    assert services.live_calls(kit.home) == []
    assert seen == ["/x/alpha"]


def test_a_loaded_bot_with_no_plist_is_a_doubt(kit, monkeypatch):
    def boom():
        raise AssertionError("imported")

    monkeypatch.setattr(services, "phone_service", boom)
    stray = f"{L}phone.bot.gamma"
    assert services.live_calls(kit.home, loaded=[stray, f"{L}voice.talk"]) == [
        f"cannot check for a call: {stray} is loaded but its plist is gone"
    ]


def test_a_stray_bot_is_named_beside_the_bots_that_are_checked(kit, monkeypatch):
    kit.plist(f"{L}phone.bot.alpha", EnvironmentVariables={"DC_HOME": "/x/alpha"})
    monkeypatch.setattr(services, "phone_service", lambda: _phone(lambda env: None))
    loaded = [f"{L}phone.bot.alpha", f"{L}phone.bot.gamma"]
    assert services.live_calls(kit.home, loaded=loaded) == [
        f"cannot check for a call: {L}phone.bot.gamma is loaded but its plist is gone"
    ]


def test_restart_hands_the_guard_what_launchd_has_loaded(kit, fake, monkeypatch):
    voice(kit, fake)
    fake.job(f"{L}phone.bot.gamma", 30, 0)
    seen = []

    def live_calls(home=None, loaded=()):
        seen.extend(loaded)
        return []

    monkeypatch.setattr(services, "live_calls", live_calls)
    result = run(kit, fake, "ears-keeper")
    assert result.exit_code == 0, result.output
    assert f"{L}phone.bot.gamma" in seen and f"{L}voice.ears-keeper" in seen


def test_a_stray_bot_blocks_a_hazard_restart_without_force(kit, fake, monkeypatch):
    voice(kit, fake)
    fake.job(f"{L}phone.bot.gamma", 30, 0)
    monkeypatch.setattr(services, "phone_service", lambda: _phone(lambda env: None))
    result = run(kit, fake, "ears-keeper")
    assert result.exit_code == 2
    assert "phone.bot.gamma is loaded but its plist is gone" in result.output
    assert kicked(fake) == []
    assert run(kit, fake, "ears-keeper", "--force").exit_code == 0
    assert kicked(fake) == [f"{L}voice.ears-keeper"]
