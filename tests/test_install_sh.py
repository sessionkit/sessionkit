"""install.sh, the one-line installer, run against a fake Mac.

The fake Mac (a scratch HOME, stub tools, calls.log) lives in
tests/_fakemac.py, shared with the doctor's tests; read its docstring first.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import unicodedata
from pathlib import Path

import pytest
from _fakemac import (
    BASH,
    HOOKS_FILE,
    HOOKS_ON_TEXT,
    INSTALL_VERB,
    SCRIPT,
    SOURCE,
    SPEECH_PROBE_URL,
    FakeMac,
)
from _printed import WIDTH, Script, display_width

FRESH_LIST = [
    "🍺 Homebrew",
    "🐍 uv",
    "🤖 Claude Code",
    "🍻 tmux, ffmpeg and notmuch",
    "📦 Session Kit",
    "🧩 the plugins",
    "🎤 ears install",
    "👂 the speech server and the ears",
    "📝 sessionkit setup",
    "📬 turn on the mail hooks",
]

HOOKS_STEP = "📬 turn on the mail hooks (so a seat hears mail while idle):"
HOOKS_STEP_RUNS = "         pager settings hooks on"
HOOKS_ROW = "📬 Mail hooks (so a seat hears mail while idle)"
REPO_URL = re.search(r"^REPO_URL=(\S+)$", SOURCE, re.MULTILINE).group(1)
HOOKS_BY_HAND = (
    '    set "hooks": true in ~/.sessionkit/mail/settings/mail.json,\n'
    "    and change no other key\n"
    '  INSTALL.md section 4, "Turn the mail hooks on", has the command, at:\n'
    f"    {REPO_URL}\n"
)


@pytest.fixture
def mac(tmp_path: Path) -> FakeMac:
    return FakeMac(tmp_path)


# --- The copy under test --------------------------------------------------------


def test_the_copy_differs_only_in_brew_paths(mac: FakeMac):
    ours = mac.script.read_text(encoding="utf-8").splitlines()
    theirs = SOURCE.splitlines()
    diff = [(a, b) for a, b in zip(ours, theirs) if a != b]
    assert len(ours) == len(theirs)
    assert len(diff) == 1 and diff[0][1].startswith("BREW_PATHS=")


# --- A fresh Mac -----------------------------------------------------------------


def test_fresh_dry_run_lists_the_ten_in_order_and_installs_nothing(mac: FakeMac):
    r = mac.run("--dry-run")
    assert r.rc == 0, r.out
    listed = r.listed()
    assert len(listed) == 10, listed
    for item, want in zip(listed, FRESH_LIST):
        assert item.startswith(want), (item, want)
    assert "It will install these 10, in this order:" in r.out
    assert "🔐 asks for your Mac password, and its own [Enter]" in r.out
    assert '📄 adds 1 line to ~/.zprofile:\n            eval "$(' in r.out
    assert (
        "📄 adds 1 line to ~/.zshrc and to ~/.profile:\n"
        '            . "$HOME/.local/bin/env"\n' in r.out
    )
    assert "~/.config/fish/conf.d/uv.env.fish" in r.out
    assert "🧪 Dry run: nothing was installed." in r.out
    assert r.installs == []


def test_the_front_says_the_fast_track_the_question_and_the_long_way(mac: FakeMac):
    r = mac.run("--dry-run")
    front = r.out.split("🔍")[0]
    assert "This is the fast track." in front
    assert "asks you before it installs anything" in front
    assert "INSTALL.md" in front
    assert "Press [Ctrl-C] at any time to stop." in front
    assert (
        "\n    curl -fsSL https://sessionkit.ai/install.sh | bash -s -- --yes\n"
        in front
    )


def test_every_check_line_shows_on_a_fresh_mac(mac: FakeMac):
    r = mac.run("--dry-run")
    for line in (
        "🍎 macOS: 27.0 on Apple silicon",
        "👤 Administrator: yes",
        "🍺 Homebrew: missing",
        "🐍 uv: missing",
        "🤖 Claude Code: missing",
        "🪟 tmux: missing",
        "🎧 ffmpeg: missing",
        "📨 notmuch: missing",
        "📦 Session Kit: missing",
        "📝 Session Kit setup (your mail box, you as operator): not done",
        "🧩 Claude Code plugins: missing",
        "🧠 Ears voice model: missing",
        "👂 Speech server and ears: missing",
        "🔌 Port 8890 (the speech server's): free",
        f"{HOOKS_ROW}: not checked yet\n   (the kit brings the pager that turns them on)",
    ):
        assert line in r.out, line


def test_no_terminal_and_no_yes_refuses_after_the_list(mac: FakeMac):
    r = mac.run()
    assert r.rc == 3, r.out
    assert "🛑 No terminal to ask on, so nothing was installed." in r.out
    assert (
        "\n    curl -fsSL https://sessionkit.ai/install.sh | bash -s -- --yes\n"
        in r.out
    )
    assert len(r.listed()) == 10
    assert r.installs == []


def test_yes_with_no_terminal_installs_in_order_when_homebrew_is_here(mac: FakeMac):
    mac.with_brew()
    r = mac.run("--yes")
    assert r.rc == 0, r.out
    assert r.installs == [
        "curl -LsSf https://astral.sh/uv/install.sh",
        "installer uv PATH=" + r.installs[1].split("PATH=", 1)[1],
        "curl -fsSL https://claude.ai/install.sh",
        "installer claude",
        "brew install tmux ffmpeg notmuch",
        "uv tool install --python 3.14 sessionkit",
        "claude plugin marketplace add sessionkit/sessionkit",
        "claude plugin install sessionkit@sessionkit",
        "ears install",
        "ears services install --agent claude",
        "sessionkit setup",
        "pager settings hooks on",
    ]
    assert "❓ Install these 9? yes (--yes)" in r.out
    assert "✅ Session Kit is installed." in r.out


def test_yes_with_no_terminal_refuses_when_homebrew_must_ask_a_password(mac: FakeMac):
    r = mac.run("--yes")
    assert r.rc == 3, r.out
    assert "🛑 Homebrew asks for your password at a terminal" in r.out
    assert r.installs == []


def test_homebrew_missing_and_no_administrator_refuses(mac: FakeMac):
    mac.flag("not_admin")
    r = mac.run_tty(answers=("y",))
    assert r.rc == 3, r.out
    assert "👤 Administrator: no" in r.out
    assert "🛑 Homebrew's installer needs an administrator account" in r.out
    assert "[Y/n]" not in r.out
    assert r.installs == []


# --- The question ----------------------------------------------------------------


def test_answer_no_installs_nothing(mac: FakeMac):
    r = mac.run_tty(answers=("n",))
    assert r.rc == 4, r.out
    assert "👋 Nothing was installed." in r.out
    assert r.installs == []


def test_only_probes_run_before_the_question(mac: FakeMac):
    r = mac.run_tty(answers=("n",))
    assert r.at_prompt is not None
    assert r.at_prompt, "the checks ran no probe at all"
    assert [c for c in r.at_prompt if INSTALL_VERB.match(c)] == []


def test_bare_enter_installs_everything_and_homebrew_gets_the_terminal(mac: FakeMac):
    r = mac.run_tty(answers=("",))
    assert r.rc == 0, r.out
    assert "❓ Install these 10? yes" in r.out
    assert r.installs[0] == (
        "curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh"
    )
    assert r.installs[1] == "installer homebrew tty=yes"
    assert r.installs[-2:] == ["sessionkit setup", "pager settings hooks on"]
    zprofile = (mac.home / ".zprofile").read_text(encoding="utf-8")
    assert zprofile.count("brew shellenv") == 1
    assert (
        "📄 added Homebrew to ~/.zprofile (Homebrew's next steps are done)\n" in r.out
    )
    assert "✅ Session Kit is installed." in r.out


def test_an_answer_it_cannot_read_asks_again(mac: FakeMac):
    r = mac.run_tty(answers=("maybe", "No"))
    assert r.rc == 4, r.out
    assert "Type y for yes or n for no." in r.out
    assert r.installs == []


def test_the_confirm_and_speech_defaults_are_one_constant_each():
    assert re.findall(r"^CONFIRM_DEFAULT=(\w+)$", SOURCE, re.MULTILINE) == ["yes"]
    assert re.findall(r"^SPEECH_DEFAULT=(\w+)$", SOURCE, re.MULTILINE) == ["yes"]
    assert re.findall(r"^SPEECH_ARGV=\((.+)\)$", SOURCE, re.MULTILINE) == [
        "services install --agent claude"
    ]
    assert "--only speech" not in SOURCE


# --- A re-run --------------------------------------------------------------------


def test_everything_here_installs_nothing_and_asks_nothing(mac: FakeMac):
    mac.everything()
    r = mac.run()
    assert r.rc == 0, r.out
    assert "✅ Nothing to install: Session Kit is all here." in r.out
    assert "\n    uv tool upgrade sessionkit\n" in r.out
    assert "❓" not in r.out
    assert r.installs == []


def test_a_rerun_after_an_install_installs_nothing(mac: FakeMac):
    mac.with_brew()
    first = mac.run("--yes")
    assert first.rc == 0, first.out
    mac.local_bin_on_path = True  # a new terminal, as the end screen asks
    again = mac.run()
    assert again.rc == 0, again.out
    assert "Nothing to install" in again.out
    assert again.installs == []


def test_some_present_lists_only_the_missing_numbered_from_one(mac: FakeMac):
    mac.everything()
    for f in ("plugin", "speech"):
        (mac.state / f).unlink()
    r = mac.run("--dry-run")
    assert r.rc == 0
    assert "It will install these 2, in this order:" in r.out
    assert [i.split(":")[0] for i in r.listed()] == [
        "🧩 the plugins",
        "👂 the speech server and the ears",
    ]


def test_brew_that_prints_its_version_and_exits_1_is_found(mac: FakeMac):
    mac.everything()
    mac.flag("brew_list_fails")
    r = mac.run()
    assert "🪟 tmux: found, 1.0" in r.out
    assert "Nothing to install" in r.out


# --- Shell files and the PATH ----------------------------------------------


def test_uv_installer_runs_with_local_bin_off_the_path(mac: FakeMac):
    mac.with_brew()
    r = mac.run("--yes")
    seen = next(c for c in r.calls if c.startswith("installer uv PATH="))
    assert str(mac.home / ".local" / "bin") not in seen.split(":")
    assert '. "$HOME/.local/bin/env"' in (mac.home / ".zshrc").read_text(
        encoding="utf-8"
    )


def test_uv_lines_name_every_shell_file_it_writes_on_this_mac(mac: FakeMac):
    (mac.home / ".bash_profile").write_text("# mine\n", encoding="utf-8")
    r = mac.run("--dry-run")
    # More than two files: one to a line, under the line it adds.
    assert (
        '📄 adds 1 line to each of 3 files: . "$HOME/.local/bin/env"\n'
        "            ~/.zshrc\n"
        "            ~/.profile\n"
        "            ~/.bash_profile\n"
    ) in r.out
    assert "~/.bashrc" not in r.out and "~/.bash_login" not in r.out


def test_zshenv_alone_takes_the_zsh_line(mac: FakeMac):
    (mac.home / ".zshenv").write_text("", encoding="utf-8")
    r = mac.run("--dry-run")
    assert "adds 1 line to ~/.zshenv and to ~/.profile" in r.out


def test_zdotdir_moves_the_zsh_files(mac: FakeMac):
    mac.extra_env["ZDOTDIR"] = str(mac.home / ".config" / "zsh")
    r = mac.run("--dry-run")
    assert "adds 1 line to ~/.config/zsh/.zprofile:" in r.out
    assert "adds 1 line to ~/.config/zsh/.zshrc and to ~/.profile" in r.out


def test_local_bin_already_on_path_means_uv_writes_no_shell_file(mac: FakeMac):
    mac.local_bin_on_path = True
    r = mac.run("--dry-run")
    assert "📄 no shell file: ~/.local/bin is on your PATH already" in r.out
    assert "~/.zshrc" not in r.out


def test_homebrew_off_the_path_is_listed_written_once_and_not_again(mac: FakeMac):
    mac.everything()
    mac.brew_on_path = False
    r = mac.run("--dry-run")
    assert "🍺 Homebrew: found, not on your PATH" in r.out
    assert r.listed()[0].startswith("🍺 Homebrew on your PATH")
    assert "adds 1 line to ~/.zprofile" in r.out
    r = mac.run("--yes")
    assert r.rc == 0, r.out
    zprofile = (mac.home / ".zprofile").read_text(encoding="utf-8")
    assert zprofile.count(f'eval "$({mac.brew_dir}/brew shellenv)"') == 1
    added = "📄 added Homebrew to ~/.zprofile (Homebrew's next steps are done)"
    assert r.out.count(added) == 1
    again = mac.run()
    assert again.rc == 0, again.out
    assert "Nothing to install" in again.out
    assert "added Homebrew" not in again.out
    assert (mac.home / ".zprofile").read_text(encoding="utf-8") == zprofile


# --- Refusals and flags ------------------------------------------------------


@pytest.mark.parametrize(
    ("flag", "content", "env", "line"),
    [
        ("uid", "0", {}, "🛑 Run this as yourself, without sudo."),
        (None, "", {"SUDO_USER": "someone"}, "🛑 Run this as yourself, without sudo."),
        ("os", "Linux", {}, "🛑 Session Kit's installer is for macOS."),
    ],
)
def test_refused_before_the_checks(mac: FakeMac, flag, content, env, line):
    if flag:
        mac.flag(flag, content)
    mac.extra_env.update(env)
    r = mac.run("--dry-run")
    assert r.rc == 3, r.out
    assert line in r.out
    assert "🔍" not in r.out
    assert r.installs == []


def test_an_unknown_flag_is_usage(mac: FakeMac):
    r = mac.run("--yse")
    assert r.rc == 2
    assert "unknown option: --yse" in r.out
    assert r.calls == []


def test_help_lists_the_flags_and_exits_0(mac: FakeMac):
    r = mac.run("--help")
    assert r.rc == 0
    for flag in ("--yes", "--dry-run", "--no-speech", "--help"):
        assert flag in r.out
    assert r.calls == []


def test_no_speech_leaves_item_9_out_and_names_it_for_later(mac: FakeMac):
    r = mac.run("--dry-run", "--no-speech")
    assert r.rc == 0
    listed = r.listed()
    assert len(listed) == 9
    assert not any("speech server" in item for item in listed)
    assert "👂 Speech server and ears: missing (left out: --no-speech)" in r.out
    assert "\n    ears services install --agent claude\n" in r.out


def test_no_speech_install_skips_it_and_the_end_screen_names_it(mac: FakeMac):
    mac.with_brew()
    r = mac.run("--yes", "--no-speech")
    assert r.rc == 0, r.out
    assert not any(c.startswith("ears services install") for c in r.calls)
    end = r.out.split("✅ Session Kit is installed.")[1]
    assert "install the speech server and\n  the ears (about 4.1 GB):" in end
    assert "\n    ears services install --agent claude\n" in end


def test_no_color_and_a_plain_pipe_print_no_escape_codes(mac: FakeMac):
    r = mac.run("--dry-run")
    assert "\x1b[" not in r.out


def test_colour_on_a_terminal_unless_no_color(mac: FakeMac):
    mac.everything()
    plain = mac.run_tty()  # NO_COLOR=1, as every run here
    assert "\x1b[32m" not in plain.out
    mac.extra_env["NO_COLOR"] = ""  # empty is unset, as no-color.org says
    coloured = mac.run_tty()
    assert "\x1b[32mfound" in coloured.out


# --- The speech server, its port, and setup last -----------------------------------


def test_the_speech_step_runs_the_one_argv(mac: FakeMac):
    mac.with_brew()
    r = mac.run("--yes")
    speech = [c for c in r.calls if c.startswith("ears services install")]
    assert speech == ["ears services install --agent claude"]


def test_the_speech_step_alone_runs_with_the_mic_check_off(mac: FakeMac):
    # The installer runs unattended: the speech step turns the microphone
    # check off for its one command. Nothing else sees the switch, so it is
    # not exported, and nothing the installer prints names it.
    mac.with_brew()
    mac.flag("port_holder", "python3.1")  # so the steps ask ears its status
    r = mac.run("--yes")
    assert r.rc == 0, r.out
    assert "EARS_MIC_CHECK_S" not in r.out
    seen = mac.mic_env_calls()
    assert ("0", "ears services install --agent claude") in seen
    assert [(v, c) for v, c in seen if v != "unset"] == [
        ("0", "ears services install --agent claude")
    ]
    calls = [c for _, c in seen]
    for other in ("ears install", "ears services status", "sessionkit setup"):
        assert other in calls, calls
    assert any(c.startswith("claude ") for c in calls), calls
    assert "export EARS_MIC_CHECK_S" not in SOURCE


def test_a_held_port_is_named_in_the_checks_and_the_list(mac: FakeMac):
    mac.with_brew()
    mac.flag("port_holder", "python3.1")
    r = mac.run("--yes")
    assert r.rc == 0, r.out
    assert "🔌 Port 8890 (the speech server's): held by python3.1 (pid 4242)" in r.out
    assert (
        "port 8890 is held by python3.1 (pid 4242):\n"
        "         used if it is mlx-audio, else this step stops\n"
    ) in r.out


def test_the_kits_own_speech_server_on_the_port_is_no_fault_at_the_end(
    mac: FakeMac,
):
    # SK-272: the holder was mlx-audio, the server the speech step adopts;
    # after the steps, ears says mlx-audio serves the port. Not a fault.
    mac.with_brew()
    mac.flag("port_holder", "python3.1")
    r = mac.run("--yes")
    assert r.rc == 0, r.out
    end = r.out.split("✅ Session Kit is installed.")[1]
    assert "Port 8890" not in end
    assert "ears services status" not in end
    assert r.calls[-1] == "ears services status"  # asked after the steps


def test_the_kits_own_speech_server_on_an_existing_install_is_no_fault(
    mac: FakeMac,
):
    # A re-run over an existing install: the speech server was already
    # the kit's, and only setup was left to do.
    _all_here_but(mac, "setup")
    mac.flag("port_holder", "python3.1")
    mac.flag("port_holder_full", "/opt/speech/.venv/bin/python3.12\n")
    r = mac.run("--yes")
    assert r.rc == 0, r.out
    assert "held by python3.12 (pid 4242)" in r.out  # the checks still say it
    end = r.out.split("✅ Session Kit is installed.")[1]
    assert "Port 8890" not in end


def test_a_foreign_port_holder_is_still_named_at_the_end(mac: FakeMac):
    mac.with_brew()
    mac.flag("port_holder", "cupsd")
    mac.flag("port_foreign")
    r = mac.run("--yes")
    assert r.rc == 0, r.out
    end = r.out.split("✅ Session Kit is installed.")[1]
    assert (
        "- Port 8890 was held by cupsd (pid 4242) before this ran.\n"
        "  Check what serves it:\n"
        "    ears services status\n"
    ) in end


def test_a_held_port_with_no_speech_server_installed_is_still_named(mac: FakeMac):
    # --no-speech: ears is there but serves nothing, so nothing says the
    # holder is the kit's own.
    mac.with_brew()
    mac.flag("port_holder", "python3.1")
    r = mac.run("--yes", "--no-speech")
    assert r.rc == 0, r.out
    end = r.out.split("✅ Session Kit is installed.")[1]
    assert "- Port 8890 was held by python3.1 (pid 4242) before this ran." in end


def test_the_port_holder_is_named_in_full_not_lsofs_9_characters(mac: FakeMac):
    # A fresh-Mac walk's re-run read "held by python3.1": lsof's cut of python3.12.
    mac.everything()
    mac.flag("port_holder", "python3.1")
    mac.flag("port_holder_full", "/opt/speech/.venv/bin/python3.12\n")
    r = mac.run()
    assert r.rc == 0, r.out
    assert "🔌 Port 8890 (the speech server's): held by python3.12 (pid 4242)" in r.out
    assert "ps -o comm= -p 4242" in r.calls


def test_a_ps_name_longer_than_its_room_is_cut_to_it(mac: FakeMac):
    # The holder's line has room for HOLDER_NAME_MAX characters of its name.
    mac.everything()
    mac.flag("port_holder", "com.docke")
    mac.flag("port_holder_full", "/Applications/x/com.docker.backend.helper.app\n")
    r = mac.run()
    assert r.rc == 0, r.out
    assert "held by com.docker.backend.h (pid 4242)" in r.out


def test_a_ps_name_that_is_not_lsofs_keeps_lsofs(mac: FakeMac):
    # The pid was reused between lsof and ps, or ps knows no such pid.
    mac.everything()
    mac.flag("port_holder", "python3.1")
    mac.flag("port_holder_full", "/usr/sbin/cupsd\n")
    r = mac.run()
    assert "held by python3.1 (pid 4242)" in r.out
    (mac.state / "port_holder_full").unlink()
    r = mac.run()
    assert "held by python3.1 (pid 4242)" in r.out


def test_a_port_lsof_cannot_see_still_reads_as_held(mac: FakeMac):
    # Another account's server: this account's lsof shows nothing, but the
    # port answers a connection. It must not read as free.
    mac.with_brew()
    mac.flag("port_open")
    r = mac.run("--yes")
    assert r.rc == 0, r.out
    held = "held by another account's server"
    assert f"🔌 Port 8890 (the speech server's): {held}" in r.out
    assert f"port 8890 is {held}:\n         used if it is mlx-audio" in r.out
    # The speech step adopted it: ears says mlx-audio serves the port now.
    end = r.out.split("✅ Session Kit is installed.")[1]
    assert "Port 8890" not in end


def test_a_port_lsof_cannot_see_with_no_speech_server_is_named_at_the_end(
    mac: FakeMac,
):
    # With no speech server installed, nothing says whose it is: named.
    mac.with_brew()
    mac.flag("port_open")
    r = mac.run("--yes", "--no-speech")
    assert r.rc == 0, r.out
    end = r.out.split("✅ Session Kit is installed.")[1]
    assert "- Port 8890 was held by another account's server before this ran." in end


def test_a_port_neither_lsof_nor_a_connection_finds_is_free(mac: FakeMac):
    r = mac.run("--dry-run")
    assert "🔌 Port 8890 (the speech server's): free" in r.out
    assert "nc -z 127.0.0.1 8890" in r.calls


def test_setup_runs_after_the_rest_and_the_hooks_after_setup(mac: FakeMac):
    mac.with_brew()
    r = mac.run("--yes")
    assert r.installs[-2:] == ["sessionkit setup", "pager settings hooks on"]
    assert (
        r.installs.index("ears services install --agent claude") < len(r.installs) - 2
    )


def test_setup_whose_dry_run_exits_4_is_in_the_list(mac: FakeMac):
    mac.everything()
    (mac.state / "setup").unlink()
    mac.flag("setup_dry_rc", "4")
    r = mac.run("--dry-run")
    assert (
        "📝 Session Kit setup (your mail box, you as operator): mail steps left"
        in r.out
    )
    assert [i.split(":")[0] for i in r.listed()] == ["📝 sessionkit setup"]


def test_setup_that_leaves_mail_steps_is_a_success_that_names_them(mac: FakeMac):
    # Exit 4: the operator is set, and mail steps are left for you. For the
    # installer that is a success, not a failure (design s1).
    mac.everything()
    (mac.state / "setup").unlink()
    mac.flag("setup_dry_rc", "4")
    mac.flag("setup_run_rc", "4")
    r = mac.run("--yes")
    assert r.rc == 0, r.out
    assert "📝 sessionkit setup: done, mail steps left for you (" in r.out
    assert "did not finish" not in r.out
    end = r.out.split("✅ Session Kit is installed.")[1]
    # Setup printed no next-steps block here: its lines above are the list.
    bullet = (
        "- Do the mail steps sessionkit setup named above, then run it again:\n"
        "    sessionkit setup\n"
    )
    assert bullet in end
    assert end.count("\n- ") == 5  # the four every install shows, and this one
    # SK-272: the end screen never runs setup's dry run again.
    after = r.calls[r.calls.index("sessionkit setup") :]
    assert "sessionkit setup --dry-run" not in after
    assert "TODO notmuch: index the mail" not in end


# What mail setup prints when it leaves steps (sessionmail's next_steps): the
# BLOCKED hook link of a re-run over an existing install, which nothing
# waits on, a BLOCKED pair where one waits on the other (INSTALL.md section 2),
# and a sudo line it could not run without a terminal.
LEFT_BLOCKED = (
    "message setup: done what it can; 1 step(s) left for you:\n"
    "  1. notmuch-hook-post-insert (BLOCKED): /Volumes/Mac/account/.sessionkit/"
    "mail/.notmuch/hooks/post-insert links to ../../hooks/post-insert, not a "
    "sessionmail hook: setup never replaces it\n"
    "then run `message setup` again.\n"
)
LEFT_WAITS = (
    "message setup: done what it can; 2 step(s) left for you:\n"
    "  1. notmuch-index (BLOCKED): notmuch: 'notmuch' not found, so the index "
    "and hook steps are left\n"
    "  2. notmuch-hook (BLOCKED): waits on notmuch-index\n"
    "then run `message setup` again.\n"
)
LEFT_SUDO = (
    "message setup: done what it can; 1 step(s) left for you:\n"
    "  1. maps (TODO): NOT RUN (no tty to ask for a password): run it yourself: "
    "sudo -- postmap /etc/postfix/virtual\n"
    "then run `message setup` again.\n"
)


def _setup_left(mac: FakeMac, text: str) -> FakeMac:
    _all_here_but(mac, "setup")
    mac.flag("setup_dry_rc", "4")
    mac.flag("setup_run_rc", "4")
    mac.flag("setup_left", text)
    return mac


def _end(r) -> str:
    assert r.rc == 0, r.out
    return r.out.split("✅ Session Kit is installed.")[1]


def test_existing_install_end_screen_names_each_step_left_once(mac: FakeMac):
    # A re-run over an existing install once printed
    # 40+ lines. The end screen names only what to do, never setup's plan or
    # dry run again, and nothing says "Left for you".
    _setup_left(mac, LEFT_BLOCKED)
    r = mac.run("--yes")
    end = _end(r)
    assert end.count("notmuch-hook-post-insert") == 1
    assert (
        "\n- notmuch-hook-post-insert:\n"
        "  /Volumes/Mac/account/.sessionkit/mail/.notmuch/hooks/post-insert links\n"
        "  to ../../hooks/post-insert, not a sessionmail hook: setup never\n"
        "  replaces it\n"
    ) in _normal(mac, end)
    assert "Left for you" not in r.out.split("📝 sessionkit setup: running")[1]
    assert "dry run" not in end.lower()
    assert "message setup" not in end
    assert "(BLOCKED)" not in end
    after = r.calls[r.calls.index("sessionkit setup") :]
    assert "sessionkit setup --dry-run" not in after


def test_a_step_setup_never_fixes_gets_no_re_run_hint(mac: FakeMac):
    _setup_left(mac, LEFT_BLOCKED)
    end = _end(mac.run("--yes"))
    assert "again" not in end
    assert "re-run" not in end


@pytest.mark.parametrize("text", [LEFT_WAITS, LEFT_SUDO], ids=["waits-on", "sudo"])
def test_a_step_a_re_run_applies_gets_the_re_run_line_once(mac: FakeMac, text: str):
    _setup_left(mac, text)
    end = _end(mac.run("--yes"))
    assert end.count("- Then run sessionkit setup again.\n") == 1
    assert end.count("sessionkit setup") == 1


def test_the_steps_left_are_one_dash_each(mac: FakeMac):
    _setup_left(mac, LEFT_WAITS)
    end = _end(mac.run("--yes"))
    assert (
        "- notmuch-index: notmuch: 'notmuch' not found, so the index and hook\n"
        "  steps are left\n"
        "- notmuch-hook: waits on notmuch-index\n"
        "- Then run sessionkit setup again.\n"
    ) in end


def test_session_start_is_said_once_and_no_mkdir(mac: FakeMac):
    # Setup's "To hear Delta messages, start Claude with:
    # session start" above "Session Kit is installed" repeated the last step;
    # and session start offers ~/work itself (README 040df27).
    mac.with_brew()
    r = mac.run("--yes")
    assert r.rc == 0, r.out
    assert "To hear Delta messages" not in r.out
    assert r.out.count("session start") == 1
    end = r.out.split("✅ Session Kit is installed.")[1]
    assert end.endswith("- Then start your first session:\n    session start\n")
    assert "mkdir" not in r.out
    assert "~/work" not in r.out
    assert "Left for you" not in r.out


def test_the_launch_step_setup_names_is_the_one_on_the_end_screen(mac: FakeMac):
    # An agent that is not the default seat: setup names it, and so does the end.
    mac.with_brew()
    mac.flag("launch", "session start claude")
    r = mac.run("--yes")
    assert r.rc == 0, r.out
    assert r.out.count("session start") == 1
    assert "- Then start your first session:\n    session start claude\n" in r.out


@pytest.mark.parametrize("gone", ["plugin", "ears_model"])
def test_the_launch_step_is_named_when_setup_is_not_in_the_run(
    mac: FakeMac, gone: str
):
    # An existing install where setup ran before: no launch line to read, so
    # the end screen gives the default, never an empty line.
    _all_here_but(mac, gone)
    r = mac.run("--yes")
    assert "sessionkit setup: running" not in r.out  # not in this run
    end = _end(r)
    assert end.endswith("- Then start your first session:\n    session start\n")


def test_session_start_is_said_once_when_setup_leaves_steps(mac: FakeMac):
    _setup_left(mac, LEFT_WAITS)
    r = mac.run("--yes")
    assert r.out.count("session start") == 1
    assert "To hear Delta messages" not in r.out


def test_setup_leaving_steps_keeps_its_own_lines_on_screen(mac: FakeMac):
    # Only the launch step is kept back: setup's plan still prints as it runs.
    _setup_left(mac, LEFT_BLOCKED)
    r = mac.run("--yes")
    during = r.out.split("📝 sessionkit setup: running")[1]
    during = during.split("📝 sessionkit setup: done")[0]
    assert "setup ran\n" in during
    assert "  1. notmuch-hook-post-insert (BLOCKED): " in during


def test_setup_that_finishes_shows_no_steps_left_bullet(mac: FakeMac):
    mac.everything()
    (mac.state / "setup").unlink()
    r = mac.run("--yes")
    assert r.rc == 0, r.out
    assert "mail steps left" not in r.out
    assert r.calls[-1] == "sessionkit setup"


@pytest.mark.parametrize("rc", ["1", "2"])
def test_setup_that_does_not_finish_fails_loudly(mac: FakeMac, rc: str):
    mac.everything()
    (mac.state / "setup").unlink()
    mac.flag("setup_run_rc", rc)
    r = mac.run("--yes")
    assert r.rc == 1, r.out
    assert (
        f"🛑 sessionkit setup did not finish (exit {rc}). Session Kit is not ready yet."
        in r.out
    )
    assert "What its dry run says is left:" in r.out
    assert "    TODO operator: make the box" in r.out
    assert "Session Kit is installed" not in r.out
    assert "pager settings hooks on" not in r.calls  # only after setup succeeds


def test_a_failed_step_stops_there_and_names_its_section(mac: FakeMac):
    mac.with_brew()
    mac.flag("kit_fails")
    r = mac.run("--yes")
    assert r.rc == 1, r.out
    assert "🛑 Session Kit failed (exit 1).\nNothing after it was installed.\n" in r.out
    assert "INSTALL.md section 2. Install the kit" in r.out
    assert not any(c.startswith("claude plugin") for c in r.calls)
    assert "Session Kit is installed" not in r.out


# --- The mail hooks (SK-236) -----------------------------------------------------


def test_the_plan_lists_the_hooks_step_last_before_the_one_question(mac: FakeMac):
    r = mac.run_tty(answers=("n",))
    assert r.rc == 4, r.out
    assert r.listed()[-1] == HOOKS_STEP
    assert f"{HOOKS_STEP}\n{HOOKS_STEP_RUNS}\n" in r.out
    assert (
        "         if the kit's pager has no hooks verb yet,\n"
        "         the end screen names the one setting instead\n"
    ) in r.out
    before = r.out.split("[Y/n]")[0]
    assert HOOKS_STEP in before
    assert r.installs == []


def test_a_fresh_install_turns_the_hooks_on_with_sessionmails_verb(mac: FakeMac):
    mac.with_brew()
    r = mac.run("--yes")
    assert r.rc == 0, r.out
    assert r.installs[-1] == "pager settings hooks on"
    assert "pager settings --help" in r.calls  # found by its help text
    assert mac.hooks_on()
    assert "pager settings hooks: on - " in r.out  # the verb's own line
    assert "📬 the mail hooks: done (" in r.out
    end = r.out.split("✅ Session Kit is installed.")[1]
    assert "mail hooks" not in end
    assert end.count("\n- ") == 4


@pytest.mark.parametrize("rc", ["2", "3"])
def test_a_refused_hooks_verb_names_the_step_and_the_install_still_succeeds(
    mac: FakeMac, rc: str
):
    mac.with_brew()
    mac.flag("pager_on_rc", rc)
    r = mac.run("--yes")
    assert r.rc == 0, r.out
    assert r.installs[-1] == "pager settings hooks on"
    why = f"pager settings hooks on refused (exit {rc})"
    err = (
        f"pager settings hooks: refused - {mac.home}/{HOOKS_FILE}"
        " is not a JSON object; fix it by hand"
    )
    lines = r.out.splitlines()
    at = next(
        i
        for i, ln in enumerate(lines)
        if ln.startswith("📬 the mail hooks: left for you (")
    )
    assert lines[at + 1] == f"   {why}"
    # The refusal's first line, every word, folded under it.
    told = []
    for ln in lines[at + 2 :]:
        if not ln.startswith("   "):
            break
        told.append(ln[3:])
    assert "".join(told) == err  # fold -s keeps each space at its line's end
    assert all(len(t) <= 72 for t in told)
    assert "a second line the installer does not show" not in r.out
    end = r.out.split("✅ Session Kit is installed.")[1]
    assert (
        "- Turn the mail hooks on, so a seat hears mail while idle\n"
        f"  ({why}):\n" + HOOKS_BY_HAND
    ) in end
    assert not (mac.home / HOOKS_FILE).exists()  # nothing written, by anyone


def test_a_pager_with_no_hooks_verb_leaves_the_step_to_the_end_screen(mac: FakeMac):
    mac.with_brew()
    mac.flag("pager_old")
    r = mac.run("--yes")
    assert r.rc == 0, r.out
    assert "pager settings --help" in r.calls
    assert not any(c.startswith("pager settings hooks") for c in r.calls)
    assert r.installs[-1] == "sessionkit setup"
    assert re.search(
        r"^📬 the mail hooks: left for you \(\d+ s\)\n   this pager has no hooks verb yet\n",
        r.out,
        re.MULTILINE,
    ), r.out
    end = r.out.split("✅ Session Kit is installed.")[1]
    assert (
        "- Turn the mail hooks on, so a seat hears mail while idle\n"
        "  (this pager has no hooks verb yet):\n" + HOOKS_BY_HAND
    ) in end
    assert not (mac.home / HOOKS_FILE).exists()


def test_a_rerun_after_the_hooks_went_on_changes_nothing(mac: FakeMac):
    mac.with_brew()
    first = mac.run("--yes")
    assert first.rc == 0, first.out
    mac.local_bin_on_path = True
    before = mac.tree()
    again = mac.run()
    assert again.rc == 0, again.out
    assert f"{HOOKS_ROW}: on" in again.out
    assert "Nothing to install" in again.out
    assert "pager settings hooks" in again.calls  # the bare read, writing nothing
    assert again.installs == []
    assert mac.tree() == before


def test_a_rerun_with_a_pager_with_no_verb_changes_nothing_and_names_the_step(
    mac: FakeMac,
):
    mac.everything()
    mac.flag("pager_old")
    (mac.home / HOOKS_FILE).unlink()
    before = mac.tree()
    r = mac.run()
    assert r.rc == 0, r.out
    assert f"{HOOKS_ROW}: not checked\n   (this pager has no hooks verb yet)" in r.out
    assert "✅ Nothing to install: Session Kit is all here." in r.out
    assert (
        "The mail hooks were not checked (this pager has no hooks verb yet).\n"
        "If they are not on yet, so a seat hears mail while idle:\n" + HOOKS_BY_HAND
    ) in r.out
    assert "❓" not in r.out
    assert r.installs == []
    assert mac.tree() == before


def test_hooks_off_alone_lists_only_the_hooks_step(mac: FakeMac):
    mac.everything()
    (mac.home / HOOKS_FILE).write_text(
        '{"version": 1, "hooks": false}\n', encoding="utf-8"
    )
    r = mac.run("--yes")
    assert r.rc == 0, r.out
    assert f"{HOOKS_ROW}: off" in r.out
    assert r.listed() == [HOOKS_STEP]
    assert "if the kit's pager has no hooks verb yet" not in r.out  # its help was read
    assert r.installs == ["pager settings hooks on"]
    assert mac.hooks_on()


def test_check_leaves_the_hooks_to_the_doctors_row_and_never_asks_the_pager(
    mac: FakeMac,
):
    mac.everything()
    (mac.home / HOOKS_FILE).unlink()
    r = mac.run("--check")
    assert r.rc == 0, r.out
    assert "Mail hooks" not in r.out
    assert not any(c.startswith("pager") for c in r.calls)


@pytest.mark.parametrize("pager", ["less -R", None])
def test_finding_the_mail_pager_leaves_the_users_pager_variable_alone(
    mac: FakeMac, pager: str | None
):
    # PAGER is the variable git and man read. The checks find sessionmail's
    # `pager` before any step runs, so a global of that name would reach
    # every step after them, setup included.
    mac.with_brew()
    if pager is not None:
        mac.extra_env["PAGER"] = pager
    r = mac.run("--yes")
    assert r.rc == 0, r.out
    assert "pager settings hooks on" in r.calls
    saw = (mac.state / "setup_saw_pager").read_text(encoding="utf-8")
    assert saw == (pager if pager is not None else "unset")


def test_the_installer_never_writes_the_hooks_file_itself():
    assert not re.search(r">\s*\S*mail\.json", SOURCE)
    assert re.findall(r"^HOOKS_ARGV=\((.+)\)$", SOURCE, re.MULTILINE) == [
        "settings hooks on"
    ]
    assert HOOKS_ON_TEXT not in SOURCE


# --- --check: the doctor -------------------------------------------------------

CHECK_HEADER = "🩺 Checking this Mac (read-only): nothing is installed"
PROBE = f"curl -fsS --noproxy 127.0.0.1 -m 3 -o /dev/null -w %{{http_code}} {SPEECH_PROBE_URL}"
EARS_ROW = "👂 Ears services (mouth, keeper, mail, speech job)"
SERVER_ROW = "💬 Speech server on port 8890"


def _remedies(out: str) -> list[str]:
    return [
        line[len("    → ") :] for line in out.splitlines() if line.startswith("    → ")
    ]


def _no_curl_but_the_probe(r) -> None:
    curls = [c for c in r.calls if c.startswith("curl ")]
    assert all(c == PROBE for c in curls), curls


def test_check_on_a_mac_with_everything_exits_0_with_a_found_line_per_row(mac: FakeMac):
    mac.everything()
    r = mac.run("--check")
    assert r.rc == 0, r.out
    for line in (
        "🍺 Homebrew: found, 4.6.1",
        "🐍 uv: found",
        "🤖 Claude Code: found",
        "🪟 tmux: found",
        "🎧 ffmpeg: found",
        "📨 notmuch: found",
        "📦 Session Kit: found",
        "📝 Session Kit setup (your mail box, you as operator): done",
        "🧩 Claude Code plugins: found",
        "🧠 Ears voice model: found",
        f"{EARS_ROW}: found",
        f"{SERVER_ROW}: serving",
        "🔌 Port 8890 (the speech server's): free",
    ):
        assert line in r.out, line
    assert "✅ Nothing is missing: Session Kit is all here." in r.out
    assert "→" not in r.out
    assert r.installs == []


def test_check_has_its_own_header_not_the_installers_front(mac: FakeMac):
    r = mac.run("--check")
    assert r.out.splitlines()[0] == CHECK_HEADER
    assert "Let's install" not in r.out
    assert "🔍" not in r.out
    assert "📋" not in r.out  # no list
    assert "❓" not in r.out  # no question


# One required row missing from a Mac that has everything. `rows` is how many
# rows read missing: some rows hang off another (no uv, so no Session Kit).
_brew_off = "echo 'eval \"$({brew} shellenv)\"' >> ~/.zprofile"
ONE_MISSING = [
    ("brewpath", "🍺 Homebrew: found, not on your PATH", _brew_off, 1),
    ("uv", "🐍 uv: missing", "curl -LsSf https://astral.sh/uv/install.sh | sh", 3),
    (
        "claude",
        "🤖 Claude Code: missing",
        "curl -fsSL https://claude.ai/install.sh | bash",
        2,
    ),
    ("tmux", "🪟 tmux: missing", "brew install tmux", 1),
    ("ffmpeg", "🎧 ffmpeg: missing", "brew install ffmpeg", 1),
    ("notmuch", "📨 notmuch: missing", "brew install notmuch", 1),
    ("kit", "📦 Session Kit: missing", "uv tool install --python 3.14 sessionkit", 2),
    (
        "setup",
        "📝 Session Kit setup (your mail box, you as operator): not done",
        "sessionkit setup",
        1,
    ),
    (
        "plugin",
        "🧩 Claude Code plugins: missing",
        "claude plugin install sessionkit@sessionkit",
        1,
    ),
    ("ears_model", "🧠 Ears voice model: missing", "ears install", 1),
    ("speech", f"{EARS_ROW}: missing", "ears services install --agent claude", 1),
    ("speech_serving", f"{SERVER_ROW}: not answering", "ears services status", 1),
]


def _take_away(mac: FakeMac, what: str) -> None:
    if what == "brewpath":
        mac.brew_on_path = False
    elif what in ("uv", "claude"):
        (mac.home / ".local" / "bin" / what).unlink()
    elif what in ("tmux", "ffmpeg", "notmuch"):
        (mac.state / "brew" / what).unlink()
    else:
        (mac.state / what).unlink()


@pytest.mark.parametrize(
    ("what", "row", "fix", "rows"), ONE_MISSING, ids=[m[0] for m in ONE_MISSING]
)
def test_check_with_one_thing_missing_exits_1_and_names_its_fix(
    mac: FakeMac, what, row, fix, rows
):
    mac.everything()
    _take_away(mac, what)
    fix = fix.replace("{brew}", f"{mac.brew_dir}/brew")
    r = mac.run("--check")
    assert r.rc == 1, r.out
    # The remedy is the line right under the row.
    lines = r.out.splitlines()
    at = lines.index(row)
    assert lines[at + 1] == f"    → {fix}", lines[at : at + 3]
    if rows == 1:
        assert (
            "🩺 1 row above is missing: the → line under it says what to run." in r.out
        )
    else:
        assert f"🩺 {rows} rows above are missing:" in r.out
    assert "Nothing is missing" not in r.out
    assert r.installs == []
    _no_curl_but_the_probe(r)


def test_every_missing_row_on_a_fresh_mac_has_its_fix_under_it(mac: FakeMac):
    r = mac.run("--check")
    assert r.rc == 1, r.out
    lines = r.out.splitlines()
    rows = [
        i
        for i, line in enumerate(lines)
        if line.endswith((": missing", ": not done", ": not answering"))
    ]
    assert len(rows) == 12, rows
    for i in rows:
        assert lines[i + 1].startswith("    → "), lines[i : i + 2]
    assert "🩺 12 rows above are missing:" in r.out
    assert "\n    curl -fsSL https://sessionkit.ai/install.sh | bash\n" in r.out
    assert r.installs == []


def test_homebrews_fix_is_its_own_installer_and_says_it_needs_an_admin(mac: FakeMac):
    mac.flag("not_admin")
    r = mac.run("--check")
    url = re.search(r"^BREW_INSTALLER_URL=(\S+)$", SOURCE, re.MULTILINE).group(1)
    lines = r.out.splitlines()
    at = lines.index("🍺 Homebrew: missing")
    # Two lines, joined by the backslash: pasted, they are the one command.
    assert lines[at + 1] == '    → /bin/bash -c "$(curl -fsSL \\'
    assert lines[at + 2] == f'      {url})"'
    assert "needs an administrator account" in lines[at + 3]


def test_setup_with_mail_steps_left_points_at_its_dry_run(mac: FakeMac):
    mac.everything()
    (mac.state / "setup").unlink()
    mac.flag("setup_dry_rc", "4")
    r = mac.run("--check")
    assert r.rc == 1, r.out
    assert (
        "): mail steps left\n    → sessionkit setup --dry-run\n"
        "      it names the mail steps left" in r.out
    )


def test_the_plugin_fix_adds_the_marketplace_only_when_it_is_not_there(mac: FakeMac):
    mac.everything()
    for f in ("plugin", "market"):
        (mac.state / f).unlink()
    assert _remedies(mac.run("--check").out) == [
        "claude plugin marketplace add sessionkit/sessionkit",
        "claude plugin install sessionkit@sessionkit",
    ]
    mac.flag("market")
    assert _remedies(mac.run("--check").out) == [
        "claude plugin install sessionkit@sessionkit"
    ]


# --- --check: each plugin's version against its package's (SK-244) ----------

VERSIONS_ROW = "🧩 Plugin versions"
VERSIONS_FOUND = "🧩 Plugin versions: found, each at its package's version"
VERSIONS_SPLIT = "🧩 Plugin versions: not at their packages' versions:"
VERSIONS_WARN = (
    "🔶 A plugin is not at its package's version:\n"
    "   the → lines under the plugin versions row bring it level."
)
RESTART = "      then restart Claude Code: a plugin update applies at its next start"


def _array(name: str) -> list[str]:
    m = re.search(rf"^{name}=\(([^)]*)\)$", SOURCE, re.MULTILINE)
    assert m, name
    return m.group(1).split()


def _versions_row(out: str) -> tuple[str, list[str]]:
    """The plugin versions row, and the indented lines under it. Each split
    is a line of its own, so the row stays in 76 columns."""
    lines = out.splitlines()
    at = next(i for i, ln in enumerate(lines) if ln.startswith(VERSIONS_ROW))
    under = []
    for ln in lines[at + 1 :]:
        if not ln.startswith(" "):
            break
        under.append(ln)
    return lines[at], under


def _split(*names: str) -> list[str]:
    """The split lines under the row, one per plugin."""
    return [f"      {n}" for n in names]


def test_the_six_plugins_are_the_kit_then_cli_family():
    from sessionkit import cli

    assert tuple(_array("KIT_PLUGINS")) == ("sessionkit", *cli.FAMILY)
    plugin = re.search(r"^PLUGIN=(\S+)$", SOURCE, re.MULTILINE).group(1)
    assert plugin == "sessionkit@sessionkit"


def test_every_plugin_at_its_packages_version_is_one_found_line(mac: FakeMac):
    mac.everything()
    r = mac.run("--check")
    assert r.rc == 0, r.out
    row, under = _versions_row(r.out)
    assert row == VERSIONS_FOUND
    assert under == []
    assert VERSIONS_WARN not in r.out
    assert "claude plugin list --json" in r.calls
    assert "sessionkit --version" in r.calls


def test_the_versions_row_follows_the_plugins_row(mac: FakeMac):
    mac.everything()
    lines = mac.run("--check").out.splitlines()
    at = lines.index("🧩 Claude Code plugins: found")
    assert lines[at + 1] == VERSIONS_FOUND


def test_one_plugin_behind_names_it_and_its_update_and_still_exits_0(mac: FakeMac):
    # The Air (K2): the package upgraded to 0.3.2, its plugin left at 0.3.1.
    mac.everything()
    mac.flag("pkg_ver.sessionmail", "0.3.2")
    r = mac.run("--check")
    assert r.rc == 0, r.out
    row, under = _versions_row(r.out)
    assert row == VERSIONS_SPLIT
    assert under == [
        *_split("sessionmail plugin 0.3.1, package 0.3.2"),
        "    → claude plugin marketplace update sessionkit",
        "    → claude plugin update sessionmail@sessionkit",
        RESTART,
    ]
    assert VERSIONS_WARN in r.out
    assert "✅ Nothing is missing: Session Kit is all here." in r.out
    assert "rows above are missing" not in r.out
    assert "row above is missing" not in r.out
    assert r.installs == []


def test_several_plugins_behind_are_one_row_naming_each(mac: FakeMac):
    # The Air's whole split: the kit and its five at 0.3.2, every plugin 0.3.1.
    mac.everything()
    for n in _array("KIT_PLUGINS"):
        mac.flag(f"pkg_ver.{n}", "0.3.2")
    r = mac.run("--check")
    assert r.rc == 0, r.out
    row, under = _versions_row(r.out)
    names = _array("KIT_PLUGINS")
    assert row == VERSIONS_SPLIT
    assert under == [
        *_split(*(f"{n} plugin 0.3.1, package 0.3.2" for n in names)),
        "    → claude plugin marketplace update sessionkit",
        *(f"    → claude plugin update {n}@sessionkit" for n in names),
        RESTART,
    ]
    assert sum(ln.startswith(VERSIONS_ROW) for ln in r.out.splitlines()) == 1


def test_a_plugin_ahead_of_its_package_is_a_split_too(mac: FakeMac):
    mac.everything()
    mac.flag("plugin_ver.sessionview", "0.3.2")
    row, under = _versions_row(mac.run("--check").out)
    assert row == VERSIONS_SPLIT
    assert under[0] == _split("sessionview plugin 0.3.2, package 0.3.1")[0]
    assert "    → claude plugin update sessionview@sessionkit" in under


def test_a_family_plugin_not_installed_gets_its_install_line(mac: FakeMac):
    mac.everything()
    mac.flag("plugin_absent.sessionphone")
    r = mac.run("--check")
    assert r.rc == 0, r.out
    row, under = _versions_row(r.out)
    assert row == VERSIONS_SPLIT
    assert under == [
        *_split("sessionphone plugin not installed, package 0.3.1"),
        "    → claude plugin marketplace update sessionkit",
        "    → claude plugin install sessionphone@sessionkit",
        RESTART,
    ]
    assert r.installs == []


def test_a_package_not_installed_gets_the_kits_reinstall_not_a_plugin_update(
    mac: FakeMac,
):
    mac.everything()
    mac.flag("pkg_ver.sessiontools", "not installed")
    r = mac.run("--check")
    assert r.rc == 0, r.out
    row, under = _versions_row(r.out)
    assert row == VERSIONS_SPLIT
    assert under == [
        *_split("sessiontools plugin 0.3.1, package not installed"),
        "    → uv tool install --python 3.14 --reinstall sessionkit",
        "      it puts back a package the kit installs that its tool has lost",
    ]


def test_no_sessionkit_command_says_nothing_about_versions(mac: FakeMac):
    mac.everything()
    (mac.home / ".local" / "bin" / "sessionkit").unlink()
    r = mac.run("--check")
    assert VERSIONS_ROW not in r.out
    assert "claude plugin list --json" not in r.calls


def test_a_sessionkit_that_does_not_answer_its_version_says_nothing(mac: FakeMac):
    mac.everything()
    mac.flag("sk_version_fails")
    r = mac.run("--check")
    assert r.rc == 0, r.out
    assert VERSIONS_ROW not in r.out


def test_the_kit_plugin_missing_leaves_the_plugins_row_to_say_it(mac: FakeMac):
    mac.everything()
    (mac.state / "plugin").unlink()
    r = mac.run("--check")
    assert "🧩 Claude Code plugins: missing" in r.out
    assert VERSIONS_ROW not in r.out
    assert "🩺 1 row above is missing" in r.out


def test_a_claude_with_no_json_list_reads_not_checked(mac: FakeMac):
    mac.everything()
    mac.flag("plugin_json_fails")
    r = mac.run("--check")
    assert r.rc == 0, r.out
    row, under = _versions_row(r.out)
    assert row == "🧩 Plugin versions: not checked"
    assert under == [
        "   (claude plugin list --json does not list sessionkit@sessionkit)"
    ]


@pytest.mark.parametrize("shape", ["pretty", "minified"])
def test_pretty_and_minified_json_read_alike(mac: FakeMac, shape):
    # The fake's entries carry a nested "version" after the plugin's own.
    mac.everything()
    if shape == "minified":
        mac.flag("plugin_json_min")
    mac.flag("plugin_ver.sessionvoice", "0.3.0")
    row, under = _versions_row(mac.run("--check").out)
    assert row == VERSIONS_SPLIT
    assert under[0] == _split("sessionvoice plugin 0.3.0, package 0.3.1")[0]


def test_a_split_leaves_the_missing_count_and_the_exit_alone(mac: FakeMac):
    mac.everything()
    (mac.state / "ears_model").unlink()
    level = mac.run("--check")
    mac.flag("pkg_ver.sessionmail", "0.3.2")
    split = mac.run("--check")
    assert level.rc == split.rc == 1
    for r in (level, split):
        assert "🩺 1 row above is missing: the → line under it says what to run." in r.out
    assert VERSIONS_WARN in split.out and VERSIONS_WARN not in level.out


def test_the_installer_itself_does_not_read_plugin_versions(mac: FakeMac):
    mac.everything()
    mac.flag("pkg_ver.sessionmail", "0.3.2")
    r = mac.run("--dry-run")
    assert VERSIONS_ROW not in r.out
    assert "claude plugin list --json" not in r.calls
    assert "sessionkit --version" not in r.calls


def test_each_fix_is_the_command_its_install_step_runs(tmp_path: Path):
    # The same Mac twice: --check's fixes, then what --yes really runs.
    checked = FakeMac(tmp_path / "a").with_brew()
    installed = FakeMac(tmp_path / "b").with_brew()
    fixes = _remedies(checked.run("--check").out)
    runs = installed.run("--yes")
    assert runs.rc == 0, runs.out
    calls = runs.installs
    brew_names = next(c for c in calls if c.startswith("brew install")).split()[2:]
    assert [f.split()[2] for f in fixes if f.startswith("brew install")] == brew_names
    for fix in fixes:
        if fix.startswith("brew install"):
            continue
        # A curl fix pipes the installer it fetches into a shell, as its step does.
        assert any(fix == c or fix.startswith(c + " | ") for c in calls), (fix, calls)


def test_the_speech_server_is_asked_on_its_port_not_read_off_the_stt_line(
    mac: FakeMac,
):
    # EARS-488: `ears services status` says "stt not installed" while the
    # server serves. The row asks the server, so it reads serving.
    mac.everything()
    mac.flag("stt_not_installed")
    r = mac.run("--check")
    assert r.rc == 0, r.out
    assert f"{SERVER_ROW}: serving" in r.out
    assert PROBE in r.calls


def test_a_silent_server_fails_the_check_though_the_installer_has_nothing_to_do(
    mac: FakeMac,
):
    # The one row with no plan() step (design review finding 1): the jobs are
    # installed, :8890 does not answer. The installer's plan is empty, and
    # --check still exits 1.
    mac.everything()
    (mac.state / "speech_serving").unlink()
    r = mac.run("--check")
    assert r.rc == 1, r.out
    assert f"{EARS_ROW}: found" in r.out
    assert f"{SERVER_ROW}: not answering\n    → ears services status\n" in r.out
    assert "curl -fsSL https://sessionkit.ai/install.sh | bash" not in r.out
    plan = mac.run("--dry-run")
    assert "Nothing to install: Session Kit is all here." in plan.out


def test_no_speech_leaves_both_speech_rows_out_and_does_not_fail(mac: FakeMac):
    mac.everything()
    for f in ("speech", "speech_serving"):
        (mac.state / f).unlink()
    r = mac.run("--check", "--no-speech")
    assert r.rc == 0, r.out
    assert f"{EARS_ROW}: left out (--no-speech)" in r.out
    assert f"{SERVER_ROW}: not checked (left out: --no-speech)" in r.out
    assert not any(c.startswith("curl") for c in r.calls)
    assert "\n    ears services install --agent claude\n" in r.out  # for later


@pytest.mark.parametrize("dressed", ["fresh", "everything"])
def test_check_writes_nothing_and_runs_no_install(mac: FakeMac, dressed: str):
    if dressed == "everything":
        mac.everything()
    before = mac.tree()
    r = mac.run("--check")
    assert r.rc in (0, 1), r.out
    assert mac.tree() == before
    assert r.calls, "the check ran no probe at all"
    assert r.installs == []
    _no_curl_but_the_probe(r)


# With no Homebrew cache yet, a bare `brew list` downloads Homebrew's package
# list and takes a lock under its prefix (SK-229 verify-001, measured on
# macOS 27). The check's read carries HOMEBREW_NO_INSTALL_FROM_API=1 so it
# stays local; an install step never does.
BREW_SET_READS = [f"list --versions {n}" for n in ("tmux", "ffmpeg", "notmuch")]


@pytest.mark.parametrize("args", [("--check",), ("--dry-run",)])
def test_the_checks_brew_reads_stay_local(mac: FakeMac, args):
    mac.everything()
    r = mac.run(*args)
    assert r.rc == 0, r.out
    seen = mac.brew_env_calls()
    # Every brew call of a check is a read, and each carries the switch.
    assert seen == [("1", "--version")] + [("1", a) for a in BREW_SET_READS]


def test_brew_install_does_not_carry_the_checks_local_switch(mac: FakeMac):
    mac.with_brew()
    r = mac.run("--yes")
    assert r.rc == 0, r.out
    seen = mac.brew_env_calls()
    assert ("unset", "install tmux ffmpeg notmuch") in seen
    # The checks' reads carry it, one command at a time; nothing else does.
    reads = [a for v, a in seen if a == "--version" or a.startswith("list ")]
    assert [(v, a) for v, a in seen if v != "unset"] == [("1", a) for a in reads]
    assert all(v == "unset" for v, a in seen if a not in reads)
    assert "export HOMEBREW_NO_INSTALL_FROM_API" not in SOURCE


def test_check_piped_on_stdin_with_no_terminal_is_read_only(mac: FakeMac):
    # `curl ... | bash -s -- --check`: the script is bash's stdin and no
    # /dev/tty opens. Without --check that pipe refuses for want of a
    # terminal, which proves the harness has none.
    assert "🛑 No terminal to ask on" in mac.run_stdin().out
    before = mac.tree()
    r = mac.run_stdin("--check")
    assert r.rc == 1, r.out
    assert r.out.splitlines()[0] == CHECK_HEADER
    assert "🩺 12 rows above are missing:" in r.out
    assert "❓" not in r.out and "No terminal" not in r.out
    assert mac.tree() == before
    assert r.installs == []
    _no_curl_but_the_probe(r)
    mac.everything()
    r = mac.run_stdin("--check")
    assert r.rc == 0, r.out


@pytest.mark.parametrize("args", [("--check", "--yes"), ("-y", "--check")])
def test_check_with_yes_is_usage(mac: FakeMac, args):
    r = mac.run(*args)
    assert r.rc == 2, r.out
    assert "--check installs nothing, so --yes does not go with it." in r.out
    assert r.calls == []


@pytest.mark.parametrize(
    ("flag", "content", "line"),
    [
        ("uid", "0", "🛑 Run this as yourself, without sudo."),
        ("os", "Linux", "🛑 Session Kit's installer is for macOS."),
    ],
)
def test_check_cannot_check_here_exits_3(mac: FakeMac, flag, content, line):
    mac.flag(flag, content)
    r = mac.run("--check")
    assert r.rc == 3, r.out
    assert line in r.out
    assert r.installs == []


def test_help_names_check_and_its_exits(mac: FakeMac):
    r = mac.run("--help")
    assert "--check" in r.out
    assert "| bash -s -- --check" in r.out
    assert "With --check: 0 nothing is missing; 1 something is missing" in r.out


def test_the_installer_itself_never_probes_the_speech_server(mac: FakeMac):
    # SK-226's path is unchanged: the probe is --check's alone.
    for args in (("--dry-run",), ("--yes",)):
        mac.with_brew()
        r = mac.run(*args)
        assert not any(SPEECH_PROBE_URL in c for c in r.calls), r.calls


# --- Every line fits in 76 columns, and every emoji keeps its space (SK-272) -------
#
# The rule, from the 0.3.3 walk: every line install.sh prints is 76 display
# columns or less, an emoji counted at its width. tests/_printed.py reads every
# line from the source at its widest; the runs below measure what each path
# really prints.


def test_every_line_the_source_can_print_fits_in_76_columns():
    rows = Script(SOURCE).printed()
    assert len(rows) > 250  # every say, the printfs and the usage text
    wide = [
        f"{n}: {func}: {display_width(t)}: {t}"
        for n, func, t in rows
        if display_width(t) > WIDTH
    ]
    assert wide == [], "\n".join(wide)


def test_the_static_read_sees_the_lines_that_once_wrapped():
    # The two that once wrapped, as they now read: the speech row and the
    # disk line.
    lines = [t for _, _, t in Script(SOURCE).printed()]
    assert any(
        t.endswith("👂 the speech server and the ears: calls and hearing you")
        for t in lines
    )
    assert any(t.startswith("   Disk: about 8 GB") for t in lines)


def test_an_expansion_with_no_bound_fails_the_static_read():
    import _printed

    with pytest.raises(_printed.Unbounded):
        Script(
            SOURCE.replace('say "🧪 Dry run', 'say "$SOMETHING_NEW 🧪 Dry run')
        ).printed()


def test_display_width_counts_an_emoji_as_two_and_a_selector_as_none():
    assert display_width("🎤 ears") == 7
    # The walk's 🎙️: its base is narrow by Unicode and the selector asks for
    # wide, so terminals disagree. Counted here as Unicode has it: 1.
    assert display_width("🎙️ ears") == 6
    assert display_width("\x1b[32mfound\x1b[0m") == 5
    assert display_width("→ x") == 3


def _normal(mac: FakeMac, out: str) -> str:
    """The fake Mac's scratch paths, as long as a real Mac's are."""
    root = str(mac.root)
    return (
        out.replace(f"{root}/opt/homebrew", "/opt/homebrew")
        .replace(f"{root}/usr/local", "/usr/local")
        .replace(str(mac.home), "/Volumes/Mac/account")
        .replace(root, "/Volumes/Mac/account/Downloads")
    )


def _all_here_but(mac: FakeMac, *gone: str) -> FakeMac:
    mac.everything()
    for f in gone:
        (mac.state / f).unlink()
    return mac


# Each path the harness can drive: (name, set the Mac up, run it).
RUNS = {
    "fresh dry run": (lambda m: m, lambda m: m.run("--dry-run")),
    "fresh dry run, no speech": (
        lambda m: m,
        lambda m: m.run("--dry-run", "--no-speech"),
    ),
    "help": (lambda m: m, lambda m: m.run("--help")),
    "unknown option": (lambda m: m, lambda m: m.run("--an-unknown-option")),
    "check with yes": (lambda m: m, lambda m: m.run("--check", "--yes")),
    "no terminal": (lambda m: m, lambda m: m.run()),
    "no terminal, piped": (lambda m: m, lambda m: m.run_stdin()),
    "yes, Homebrew needs a password": (lambda m: m, lambda m: m.run("--yes")),
    "not an administrator": (
        lambda m: (m.flag("not_admin"), m)[1],
        lambda m: m.run_tty(answers=("y",)),
    ),
    "answer no, after one it cannot read": (
        lambda m: m,
        lambda m: m.run_tty(answers=("maybe", "n")),
    ),
    "a full install": (lambda m: m.with_brew(), lambda m: m.run("--yes")),
    "a full install, no speech": (
        lambda m: m.with_brew(),
        lambda m: m.run("--yes", "--no-speech"),
    ),
    "Homebrew installed at the terminal": (
        lambda m: m,
        lambda m: m.run_tty(answers=("",)),
    ),
    "a held port": (
        lambda m: (m.flag("port_holder", "python3.1"), m.with_brew())[1],
        lambda m: m.run("--yes"),
    ),
    "a port lsof cannot see": (
        lambda m: (m.flag("port_open"), m.with_brew())[1],
        lambda m: m.run("--yes"),
    ),
    "setup leaves mail steps": (
        lambda m: (
            _all_here_but(m, "setup"),
            m.flag("setup_dry_rc", "4"),
            m.flag("setup_run_rc", "4"),
        )[0],
        lambda m: m.run("--yes"),
    ),
    "setup leaves a step it never fixes": (
        lambda m: _setup_left(m, LEFT_BLOCKED),
        lambda m: m.run("--yes"),
    ),
    "setup leaves a step that waits on another": (
        lambda m: _setup_left(m, LEFT_WAITS),
        lambda m: m.run("--yes"),
    ),
    "setup leaves a sudo line": (
        lambda m: _setup_left(m, LEFT_SUDO),
        lambda m: m.run("--yes"),
    ),
    "a foreign port holder": (
        lambda m: (
            m.flag("port_holder", "cupsd"),
            m.flag("port_foreign"),
            m.with_brew(),
        )[2],
        lambda m: m.run("--yes"),
    ),
    "setup fails": (
        lambda m: (_all_here_but(m, "setup"), m.flag("setup_run_rc", "1"))[0],
        lambda m: m.run("--yes"),
    ),
    "a step fails": (
        lambda m: (m.flag("kit_fails"), m.with_brew())[1],
        lambda m: m.run("--yes"),
    ),
    "the hooks refused": (
        lambda m: (m.flag("pager_on_rc", "2"), m.with_brew())[1],
        lambda m: m.run("--yes"),
    ),
    "a pager with no hooks verb": (
        lambda m: (m.flag("pager_old"), m.with_brew())[1],
        lambda m: m.run("--yes"),
    ),
    "nothing to do": (lambda m: m.everything(), lambda m: m.run()),
    "nothing to do, a pager with no verb": (
        lambda m: (m.everything(), m.flag("pager_old"), (m.home / HOOKS_FILE).unlink())[
            0
        ],
        lambda m: m.run("--no-speech"),
    ),
    "Homebrew off the PATH, five shell files": (
        lambda m: (
            [
                (m.home / f).write_text("", encoding="utf-8")
                for f in (".bashrc", ".bash_profile", ".bash_login")
            ],
            m.with_brew(on_path=False),
        )[1],
        lambda m: m.run("--dry-run"),
    ),
    "an Intel Mac, local bin on the PATH": (
        lambda m: (m.flag("arch", "x86_64"), setattr(m, "local_bin_on_path", True), m)[
            2
        ],
        lambda m: m.run("--dry-run"),
    ),
    "check, fresh": (lambda m: m, lambda m: m.run("--check")),
    "check, fresh, no speech": (lambda m: m, lambda m: m.run("--check", "--no-speech")),
    "check, not an administrator": (
        lambda m: (m.flag("not_admin"), m)[1],
        lambda m: m.run("--check"),
    ),
    "check, everything": (lambda m: m.everything(), lambda m: m.run("--check")),
    "check, every plugin behind": (
        lambda m: (
            m.everything(),
            [m.flag(f"pkg_ver.{n}", "0.3.2") for n in _array("KIT_PLUGINS")],
        )[0],
        lambda m: m.run("--check"),
    ),
    "check, a package gone, a plugin absent": (
        lambda m: (
            m.everything(),
            m.flag("pkg_ver.sessiontools", "not installed"),
            m.flag("plugin_absent.sessionphone"),
        )[0],
        lambda m: m.run("--check"),
    ),
    "check, no json plugin list": (
        lambda m: (m.everything(), m.flag("plugin_json_fails"))[0],
        lambda m: m.run("--check"),
    ),
    "check, setup with mail steps left": (
        lambda m: (_all_here_but(m, "setup"), m.flag("setup_dry_rc", "4"))[0],
        lambda m: m.run("--check"),
    ),
    "check, a silent speech server": (
        lambda m: _all_here_but(m, "speech_serving"),
        lambda m: m.run("--check"),
    ),
    "check, the speech jobs gone": (
        lambda m: _all_here_but(m, "speech", "speech_serving"),
        lambda m: m.run("--check"),
    ),
    "not macOS": (lambda m: (m.flag("os", "Linux"), m)[1], lambda m: m.run()),
    "as root": (lambda m: (m.flag("uid", "0"), m)[1], lambda m: m.run()),
    "check, not macOS": (
        lambda m: (m.flag("os", "Linux"), m)[1],
        lambda m: m.run("--check"),
    ),
}


# What the fake Mac's own tools print, not install.sh: the rule is the
# script's lines. A child's output (pager's line, setup's dry run, which the
# script indents) is the child's to keep in its width.
CHILD_OUTPUT = re.compile(
    r"^(pager settings hooks: |setup ran$|done$|error: |    TODO |"
    r"message setup: |  \d+\. \S+ \([A-Z]+\): |then run `message setup`)"
)


@pytest.mark.parametrize("name", list(RUNS))
def test_every_line_a_run_prints_fits_in_76_columns(mac: FakeMac, name: str):
    dress, run = RUNS[name]
    dress(mac)
    r = run(mac)
    assert r.out.strip(), r.out
    wide = [
        f"{display_width(ln)}: {ln}"
        for ln in _normal(mac, r.out).splitlines()
        if display_width(ln) > WIDTH and not CHILD_OUTPUT.match(ln)
    ]
    assert wide == [], "\n".join(wide)


def test_no_emoji_uses_a_variation_selector_and_every_one_is_wide():
    # A VS16 emoji (a base that is text by default, + U+FE0F) is 1 column or
    # 2 as each terminal decides, so the next character can land on it: the
    # 🎙️ and ⚙️ of the 0.3.3 walk. An emoji of East Asian Width W is 2 everywhere.
    assert "\ufe0f" not in SOURCE
    narrow = sorted(
        {
            f"U+{ord(c):04X}"
            for c in SOURCE
            if unicodedata.category(c) == "So"
            and unicodedata.east_asian_width(c) != "W"
        }
    )
    assert narrow == []


def test_the_ears_install_and_setup_rows_use_wide_emoji(mac: FakeMac):
    listed = mac.run("--dry-run").listed()
    ears = next(i for i in listed if "ears install" in i)
    setup = next(i for i in listed if "sessionkit setup" in i)
    assert ears.startswith("🎤 ears install")  # a microphone, as asked
    assert setup.startswith("📝 sessionkit setup")
    for item in (ears, setup):
        assert unicodedata.east_asian_width(item[0]) == "W" and item[1] == " "


# --- The script itself --------------------------------------------------------------


def test_the_last_line_calls_main():
    assert SOURCE.rstrip("\n").splitlines()[-1] == 'main "$@"'


def test_sudo_is_only_ever_words_never_run():
    for n, line in enumerate(SOURCE.splitlines(), 1):
        if "sudo" not in line:
            continue
        code = line.strip()
        assert code.startswith(("#", "say ", 'say "')) or "SUDO_USER" in code, (n, line)


def test_every_child_but_homebrew_reads_dev_null_not_the_script():
    body = SOURCE.split("# --- The steps, in their order", 1)[1].split(
        "step_label()", 1
    )[0]
    assert body.count("</dev/tty") == 1
    assert '/bin/bash -c "$script" </dev/tty' in body
    for verb in (
        "brew install",
        "uv tool install",
        "claude plugin install",
        "ears install",
        "sessionkit setup",
    ):
        line = next(x for x in body.splitlines() if verb in x)
        assert "</dev/null" in line, line


def test_no_variable_runs_into_a_non_ascii_character():
    # bash 3.2 reads "$doing…" as a variable named doing plus the ellipsis's
    # first byte: empty, and the rest of the character is printed broken.
    hits = re.findall(r"\$[A-Za-z_][A-Za-z_0-9]*[^\x00-\x7f]", SOURCE)
    assert hits == []


def test_bash_parses_it():
    subprocess.run([BASH, "-n", str(SCRIPT)], check=True)


@pytest.mark.skipif(
    shutil.which("shellcheck") is None, reason="shellcheck is not installed"
)
def test_shellcheck_is_clean():
    p = subprocess.run(
        ["shellcheck", str(SCRIPT)], capture_output=True, text=True, check=False
    )
    assert p.returncode == 0, p.stdout
