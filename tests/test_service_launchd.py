"""`sessionkit service`'s launchd reads: `list`, `print` and the seam.

The forms are a real Mac's: `-` for no pid, a Status of `0`, `3` or `-15`,
and print's `last terminating signal = Terminated: 15` with no `last exit
code` line. Every call goes to the fake launchctl (tests/_fakelaunchd.py).
"""

from __future__ import annotations

import pytest
from _fakelaunchd import FakeLaunchd

from sessionkit import launchd

LIST = """PID\tStatus\tLabel
101\t-15\tdev.sessionkit.voice.talk
-\t0\tdev.sessionkit.tools.default-model
202\t3\tdev.sessionkit.phone.bot.alpha
-\t-\tcom.example.other
garbage line
"""


def test_list_parses_pid_and_status_in_every_form():
    rows = launchd.parse_list(LIST)
    assert rows["dev.sessionkit.voice.talk"] == launchd.Listed(101, -15)
    assert rows["dev.sessionkit.tools.default-model"] == launchd.Listed(None, 0)
    assert rows["dev.sessionkit.phone.bot.alpha"] == launchd.Listed(202, 3)
    assert rows["com.example.other"] == launchd.Listed(None, None)
    assert "PID" not in rows and len(rows) == 4


@pytest.mark.parametrize(
    ("text", "want"),
    [
        ("\tlast exit code = 1\n", launchd.Printed(exit_code=1)),
        ("\tlast exit code = (never exited)\n", launchd.Printed(never_exited=True)),
        (
            "\tlast terminating signal = Terminated: 15\n",
            launchd.Printed(signal=15, signal_name="Terminated"),
        ),
        ("\tlast exit reason = something new\n", launchd.Printed()),
        (
            "\tstate = running\n\truns = 4\n\tpid = 777\n",
            launchd.Printed(pid=777, state="running", runs=4),
        ),
    ],
)
def test_print_reads_three_exit_forms_and_leaves_out_others(text, want):
    assert launchd.parse_print(text) == want


def test_the_seam_runs_the_fake_and_logs_argv(tmp_path, monkeypatch):
    fake = FakeLaunchd(tmp_path).job("dev.sessionkit.voice.talk", 9, 0)
    monkeypatch.setenv("SESSIONKIT_LAUNCHCTL", str(fake.program))
    assert launchd.listed() == {"dev.sessionkit.voice.talk": launchd.Listed(9, 0)}
    assert fake.calls() == [["list"]]


def test_error_125_is_unreachable(tmp_path, monkeypatch):
    fake = FakeLaunchd(tmp_path).fail("list", 125)
    monkeypatch.setenv("SESSIONKIT_LAUNCHCTL", str(fake.program))
    with pytest.raises(launchd.Unreachable, match="125"):
        launchd.listed()


def test_a_failed_call_that_says_125_is_unreachable(tmp_path, monkeypatch):
    label = "dev.sessionkit.voice.talk"
    words = (
        'Could not kickstart service "x": 125: Domain does not support specified action'
    )
    fake = FakeLaunchd(tmp_path).kickstart_fails(label, 1, words)
    monkeypatch.setenv("SESSIONKIT_LAUNCHCTL", str(fake.program))
    with pytest.raises(launchd.Unreachable, match="125"):
        launchd.kickstart(label)


def test_a_print_that_succeeds_with_125_in_it_is_read(tmp_path, monkeypatch):
    label = "dev.sessionkit.voice.talk"
    text = "\tpid = 9\n\tenvironment = {\n\t\tNOTE => code 125: fine\n\t}\n"
    fake = FakeLaunchd(tmp_path).printed(label, text)
    monkeypatch.setenv("SESSIONKIT_LAUNCHCTL", str(fake.program))
    assert launchd.printed(label) == launchd.Printed(pid=9)


def test_a_missing_launchctl_is_unreachable(tmp_path, monkeypatch):
    monkeypatch.setenv("SESSIONKIT_LAUNCHCTL", str(tmp_path / "no-such-launchctl"))
    with pytest.raises(launchd.Unreachable, match="macOS only"):
        launchd.listed()


def test_another_failure_is_failed(tmp_path, monkeypatch):
    fake = FakeLaunchd(tmp_path).fail("list", 5)
    monkeypatch.setenv("SESSIONKIT_LAUNCHCTL", str(fake.program))
    with pytest.raises(launchd.Failed):
        launchd.listed()


def test_print_of_an_unloaded_job_is_none(tmp_path, monkeypatch):
    fake = FakeLaunchd(tmp_path)
    monkeypatch.setenv("SESSIONKIT_LAUNCHCTL", str(fake.program))
    assert launchd.printed("dev.sessionkit.voice.talk") is None
    assert fake.calls() == [["print", f"gui/{launchd.uid()}/dev.sessionkit.voice.talk"]]


def test_plist_reads_and_tolerates_a_bad_file(tmp_path):
    agents = tmp_path / "Library" / "LaunchAgents"
    agents.mkdir(parents=True)
    (agents / "dev.sessionkit.voice.bad.plist").write_text("not a plist")
    assert launchd.plist("dev.sessionkit.voice.bad", tmp_path) is None
    assert launchd.plist("dev.sessionkit.voice.none", tmp_path) is None
    assert launchd.plist_labels(tmp_path) == ["dev.sessionkit.voice.bad"]
