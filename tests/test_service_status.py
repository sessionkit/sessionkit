"""`sessionkit service status NAME|GROUP|all`: the long form.

One field per line. The last exit is read from `launchctl print` in each of
its forms, else from `launchctl list`'s Status. A job with no file says
whose install writes it.
"""

from __future__ import annotations

import pytest
from _fakekit import FakeKit
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


@pytest.fixture(autouse=True)
def no_lsof(monkeypatch):
    """The bind check asks lsof; here it answers from a table, never the Mac."""
    monkeypatch.setattr(services, "lsof_listen", lambda port, proto: ["127.0.0.1:8780"])


def run(kit, fake, *args):
    env = {"HOME": str(kit.home), **fake.env()}
    return CliRunner().invoke(main, ["service", "status", *args], env=env)


def test_the_long_form_of_a_file_row(kit, fake):
    kit.service(
        "voice",
        "talk",
        port=8780,
        install="voice-tool install --only talk",
        uninstall="voice-tool uninstall --only talk",
        description="the live view in a browser",
        logs=["/var/log/extra.log"],
    )
    kit.plist(
        f"{L}voice.talk",
        KeepAlive=True,
        StandardOutPath="/var/log/talk.out",
        StandardErrorPath="/var/log/talk.err",
    )
    fake.job(f"{L}voice.talk", 4242, -15)
    fake.printed(
        f"{L}voice.talk",
        "\tstate = running\n\truns = 3\n\tpid = 4242\n"
        "\tlast terminating signal = Terminated: 15\n",
    )
    result = run(kit, fake, "talk")
    assert result.exit_code == 0, result.output
    assert result.output.splitlines() == [
        "name: voice.talk",
        f"label: {L}voice.talk",
        f"file: {kit.root / 'voice' / 'services' / 'talk.json'}",
        "enabled: yes",
        "state: ● up",
        "kind: daemon",
        "pid: 4242",
        "last exit: signal 15 (Terminated)",
        "runs: 3",
        "port: 8780/tcp, bind 127.0.0.1",
        "listening: 127.0.0.1:8780",
        f"plist: {kit.agents / (L + 'voice.talk.plist')}",
        "log: /var/log/talk.out",
        "log: /var/log/talk.err",
        "log: /var/log/extra.log",
        "install: voice-tool install --only talk",
        "uninstall: voice-tool uninstall --only talk",
        "description: the live view in a browser",
    ]
    assert fake.verbs("print") == [["print", f"gui/{launchd.uid()}/{L}voice.talk"]]


def test_the_long_form_of_a_transition_row(kit, fake):
    kit.plist(f"{L}phone.bot.alpha", KeepAlive=True)
    fake.job(f"{L}phone.bot.alpha", None, 3)
    fake.printed(f"{L}phone.bot.alpha", "\tlast exit code = 3\n")
    out = run(kit, fake, "bot.alpha").output.splitlines()
    assert "file: none yet (phone's install writes it)" in out
    assert "state: ✕ down (exited 3)" in out
    assert "last exit: 3" in out and "pid: -" in out
    assert "owner: the phone package" in out


@pytest.mark.parametrize(
    ("printed", "status", "want"),
    [
        ("\tlast exit code = 1\n", 1, "last exit: 1"),
        ("\tlast exit code = (never exited)\n", None, "last exit: never exited"),
        ("\tlast terminating signal = Killed: 9\n", -9, "last exit: signal 9 (Killed)"),
        (None, -15, "last exit: signal 15"),  # print not available: list's Status
        (None, 0, "last exit: 0"),
    ],
)
def test_each_last_exit_form_is_rendered(kit, fake, printed, status, want):
    kit.service("voice", "talk")
    fake.job(f"{L}voice.talk", 5, status)
    if printed:
        fake.printed(f"{L}voice.talk", printed)
    assert want in run(kit, fake, "talk").output.splitlines()


def test_a_group_prints_each_long_form_a_to_z(kit, fake):
    kit.service("voice", "talk")
    kit.service("voice", "ears-stt")
    kit.service("tools", "default-model", kind="on-demand")
    out = run(kit, fake, "voice").output
    assert out.index("name: voice.ears-stt") < out.index("name: voice.talk")
    assert "default-model" not in out
    assert "default-model" in run(kit, fake, "all").output


def test_every_spelling_of_a_name_works(kit, fake):
    kit.service("phone", "bot.alpha", agent_dir="bots", agent="alpha")
    for word in ("bot.alpha", "phone.bot.alpha", f"{L}phone.bot.alpha"):
        assert "name: phone.bot.alpha" in run(kit, fake, word).output


def test_an_unknown_name_is_exit_2(kit, fake):
    result = run(kit, fake, "nothing")
    assert (
        result.exit_code == 2 and "no service or group named nothing" in result.output
    )


def test_a_run_service_has_no_launchd_fields(kit, fake):
    from _fakekit import DROP

    kit.service("tools", "web", label=DROP, run=["session", "web", "serve"])
    out = run(kit, fake, "web").output.splitlines()
    assert "state: ○ manual (runs in the foreground: session web serve)" in out
    assert not any(line.startswith(("pid:", "label:", "plist:")) for line in out)


def test_print_unreachable_still_prints_and_exits_3(kit, fake):
    kit.service("voice", "talk")
    fake.job(f"{L}voice.talk", 5, 0).fail("print", 125)
    result = run(kit, fake, "talk")
    assert result.exit_code == 3
    assert "name: voice.talk" in result.output and "last exit: 0" in result.output


def test_status_json(kit, fake):
    kit.service("voice", "talk")
    result = run(kit, fake, "talk", "--json")
    assert result.exit_code == 0
    assert '"name": "talk"' in result.output
