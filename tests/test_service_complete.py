"""TAB completion on service names, and `sessionkit completion SHELL`.

The callback offers the names `list` shows, the groups and `all`. It writes
nothing, and on any error it offers nothing, never a traceback.
"""

from __future__ import annotations

import pytest
from _fakekit import FakeKit
from _fakelaunchd import FakeLaunchd
from click.shell_completion import ShellComplete
from click.testing import CliRunner

from sessionkit import services
from sessionkit.cli import main

L = "dev.sessionkit."


@pytest.fixture
def kit(tmp_path, monkeypatch) -> FakeKit:
    kit = FakeKit(tmp_path)
    monkeypatch.setenv("HOME", str(kit.home))
    return kit


@pytest.fixture
def fake(tmp_path, monkeypatch) -> FakeLaunchd:
    fake = FakeLaunchd(tmp_path)
    monkeypatch.setenv("SESSIONKIT_LAUNCHCTL", str(fake.program))
    return fake


def complete(args: list[str], incomplete: str) -> list[str]:
    comp = ShellComplete(main, {}, "sessionkit", "_SESSIONKIT_COMPLETE")
    return [item.value for item in comp.get_completions(args, incomplete)]


def test_tab_offers_names_groups_and_all(kit, fake):
    kit.service("voice", "talk")
    kit.service("phone", "bot.alpha", agent_dir="bots", agent="alpha")
    fake.job(f"{L}voice.ears-stt", 3, 0)  # a job with no file yet is offered too
    assert complete(["service", "restart"], "") == [
        "bot.alpha",
        "ears-stt",
        "phone",
        "talk",
        "voice",
        "all",
    ]
    assert complete(["service", "status"], "t") == ["talk"]
    assert complete(["service", "restart"], "a") == ["all"]


def test_tab_still_offers_the_files_when_launchctl_fails(kit, fake):
    kit.service("voice", "talk")
    fake.fail("list", 125)
    assert complete(["service", "restart"], "ta") == ["talk"]


def test_tab_offers_nothing_and_raises_nothing_on_an_error(kit, fake, monkeypatch):
    def boom(*_a, **_k):
        raise PermissionError("unreadable")

    monkeypatch.setattr(services, "survey", boom)
    assert complete(["service", "restart"], "") == []


def test_tab_writes_nothing(kit, fake):
    kit.service("voice", "talk")
    before = sorted(p for p in kit.home.rglob("*"))
    complete(["service", "restart"], "")
    assert sorted(p for p in kit.home.rglob("*")) == before
    assert fake.calls() == [["list"]]


@pytest.mark.parametrize(
    ("shell", "marker"), [("zsh", "compdef"), ("fish", "complete")]
)
def test_completion_prints_the_shells_script(shell, marker):
    result = CliRunner().invoke(main, ["completion", shell])
    assert result.exit_code == 0
    assert marker in result.output and "_SESSIONKIT_COMPLETE" in result.output


def test_completion_refuses_another_shell():
    assert CliRunner().invoke(main, ["completion", "tcsh"]).exit_code == 2
