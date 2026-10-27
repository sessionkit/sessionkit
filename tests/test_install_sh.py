"""install.sh, the one-line installer, run against a fake Mac.

The fake Mac (a scratch HOME, stub tools, calls.log) lives in
tests/_fakemac.py, shared with the doctor's tests; read its docstring first.
"""

from __future__ import annotations

import re
import shutil
import subprocess
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

FRESH_LIST = [
    "🍺 Homebrew",
    "🐍 uv",
    "🤖 Claude Code",
    "🍻 tmux, ffmpeg and notmuch",
    "📦 Session Kit",
    "🧩 the plugins",
    "🎙️ ears install",
    "👂 the speech server and the ears",
    "⚙️ sessionkit setup",
    "📬 turn on the mail hooks",
]

HOOKS_STEP = "📬 turn on the mail hooks (so a seat hears mail while idle): pager settings hooks on"
HOOKS_ROW = "📬 Mail hooks (so a seat hears mail while idle)"
HOOKS_BY_HAND = (
    '    set "hooks": true in ~/.sessionkit/mail/settings/mail.json, and change no other key\n'
    '  The README\'s Installation, "The mail hooks start off", has the lines to paste.\n'
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
    assert 'adds 1 line to ~/.zprofile: eval "$(' in r.out
    assert (
        'adds 1 line to ~/.zshrc and to ~/.profile: . "$HOME/.local/bin/env"' in r.out
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
        "🖥️ tmux: missing",
        "🎞️ ffmpeg: missing",
        "📨 notmuch: missing",
        "📦 Session Kit: missing",
        "⚙️ Session Kit setup (your mail box, you as operator): not done",
        "🧩 Claude Code plugins: missing",
        "🎙️ Ears voice model: missing",
        "👂 Speech server and ears: missing",
        "🔌 Port 8890 (the speech server's): free",
        f"{HOOKS_ROW}: not checked yet (the kit brings the pager that turns them on)",
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
        "✏️  added Homebrew to ~/.zprofile (Homebrew's next steps are done)\n" in r.out
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
    assert "🖥️ tmux: found, 1.0" in r.out
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
    uv_line = next(
        line for line in r.out.splitlines() if "adds 1 line to each of" in line
    )
    assert "~/.zshrc, ~/.profile and ~/.bash_profile:" in uv_line
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
    assert (
        "none: ~/.local/bin is on your PATH already, so it changes no shell file"
        in r.out
    )
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
    added = "✏️  added Homebrew to ~/.zprofile (Homebrew's next steps are done)"
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
    assert "install the speech server and the ears" in end
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


def test_a_held_port_is_named_in_the_checks_the_list_and_the_end(mac: FakeMac):
    mac.with_brew()
    mac.flag("port_holder", "python3.1")
    r = mac.run("--yes")
    assert r.rc == 0, r.out
    assert "🔌 Port 8890 (the speech server's): held by python3.1 (pid 4242)" in r.out
    assert "port 8890 is held by python3.1 (pid 4242): used if it is mlx-audio" in r.out
    end = r.out.split("✅ Session Kit is installed.")[1]
    assert "Port 8890 was held by python3.1 (pid 4242)" in end
    assert "\n    ears services status\n" in end


def test_the_port_holder_is_named_in_full_not_lsofs_9_characters(mac: FakeMac):
    # A fresh-Mac walk's re-run read "held by python3.1": lsof's cut of python3.12.
    mac.everything()
    mac.flag("port_holder", "python3.1")
    mac.flag("port_holder_full", "/opt/speech/.venv/bin/python3.12\n")
    r = mac.run()
    assert r.rc == 0, r.out
    assert "🔌 Port 8890 (the speech server's): held by python3.12 (pid 4242)" in r.out
    assert "ps -o comm= -p 4242" in r.calls


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
    held = "held by a server lsof does not show (another account's)"
    assert f"🔌 Port 8890 (the speech server's): {held}" in r.out
    assert f"port 8890 is {held}: used if it is mlx-audio" in r.out
    end = r.out.split("✅ Session Kit is installed.")[1]
    assert f"Port 8890 was {held} before this ran" in end


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
        "⚙️ Session Kit setup (your mail box, you as operator): not done, mail steps left"
        in r.out
    )
    assert [i.split(":")[0] for i in r.listed()] == ["⚙️ sessionkit setup"]


def test_setup_that_leaves_mail_steps_is_a_success_that_names_them(mac: FakeMac):
    # Exit 4: the operator is set, and mail steps are left for you. For the
    # installer that is a success, not a failure (design s1).
    mac.everything()
    (mac.state / "setup").unlink()
    mac.flag("setup_dry_rc", "4")
    mac.flag("setup_run_rc", "4")
    r = mac.run("--yes")
    assert r.rc == 0, r.out
    assert "⚙️ sessionkit setup: done, mail steps left for you (" in r.out
    assert "did not finish" not in r.out
    end = r.out.split("✅ Session Kit is installed.")[1]
    bullet = (
        "- sessionkit setup set you as operator and left mail steps for you."
        " Its dry run names them:\n"
        "    TODO notmuch: index the mail\n"
        "  Do them, then run it again; it keeps the operator it wrote"
        " (INSTALL.md section 2):\n"
        "    sessionkit setup\n"
    )
    assert bullet in end
    assert end.count("\n- ") == 5  # the four every install shows, and this one
    assert r.calls[-1] == "sessionkit setup --dry-run"


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
    assert "🛑 Session Kit failed (exit 1). Nothing after it was installed." in r.out
    assert "INSTALL.md section 2. Install the kit" in r.out
    assert not any(c.startswith("claude plugin") for c in r.calls)
    assert "Session Kit is installed" not in r.out


# --- The mail hooks (SK-236) -----------------------------------------------------


def test_the_plan_lists_the_hooks_step_last_before_the_one_question(mac: FakeMac):
    r = mac.run_tty(answers=("n",))
    assert r.rc == 4, r.out
    assert r.listed()[-1] == HOOKS_STEP
    assert "if the kit's pager has no hooks verb yet, the end screen names" in r.out
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
    why = (
        f"pager settings hooks on refused (exit {rc}): pager settings hooks: refused"
        f" - {mac.home}/{HOOKS_FILE} is not a JSON object; fix it by hand"
    )
    assert f"📬 the mail hooks: left for you: {why} (" in r.out
    assert "a second line the installer does not show" not in r.out
    end = r.out.split("✅ Session Kit is installed.")[1]
    assert (
        f"- Turn the mail hooks on, so a seat hears mail while idle ({why}):\n"
        + HOOKS_BY_HAND
        in end
    )
    assert not (mac.home / HOOKS_FILE).exists()  # nothing written, by anyone


def test_a_pager_with_no_hooks_verb_leaves_the_step_to_the_end_screen(mac: FakeMac):
    mac.with_brew()
    mac.flag("pager_old")
    r = mac.run("--yes")
    assert r.rc == 0, r.out
    assert "pager settings --help" in r.calls
    assert not any(c.startswith("pager settings hooks") for c in r.calls)
    assert r.installs[-1] == "sessionkit setup"
    assert (
        "📬 the mail hooks: left for you: this pager has no hooks verb yet (" in r.out
    )
    end = r.out.split("✅ Session Kit is installed.")[1]
    assert (
        "- Turn the mail hooks on, so a seat hears mail while idle"
        " (this pager has no hooks verb yet):\n" + HOOKS_BY_HAND
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
    assert f"{HOOKS_ROW}: not checked (this pager has no hooks verb yet)" in r.out
    assert "✅ Nothing to install: Session Kit is all here." in r.out
    assert (
        "The mail hooks were not checked (this pager has no hooks verb yet)."
        " If they are not on yet, so a seat hears mail while idle:\n" + HOOKS_BY_HAND
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
EARS_ROW = "👂 Ears services (mouth, keeper, mail, the speech job)"
SERVER_ROW = "🗣️ Speech server on port 8890"


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
        "🖥️ tmux: found",
        "🎞️ ffmpeg: found",
        "📨 notmuch: found",
        "📦 Session Kit: found",
        "⚙️ Session Kit setup (your mail box, you as operator): done",
        "🧩 Claude Code plugins: found",
        "🎙️ Ears voice model: found",
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
    ("tmux", "🖥️ tmux: missing", "brew install tmux", 1),
    ("ffmpeg", "🎞️ ffmpeg: missing", "brew install ffmpeg", 1),
    ("notmuch", "📨 notmuch: missing", "brew install notmuch", 1),
    ("kit", "📦 Session Kit: missing", "uv tool install --python 3.14 sessionkit", 2),
    (
        "setup",
        "⚙️ Session Kit setup (your mail box, you as operator): not done",
        "sessionkit setup",
        1,
    ),
    (
        "plugin",
        "🧩 Claude Code plugins: missing",
        "claude plugin install sessionkit@sessionkit",
        1,
    ),
    ("ears_model", "🎙️ Ears voice model: missing", "ears install", 1),
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
    assert lines[at + 1] == f'    → /bin/bash -c "$(curl -fsSL {url})"'
    assert "needs an administrator account" in lines[at + 2]


def test_setup_with_mail_steps_left_points_at_its_dry_run(mac: FakeMac):
    mac.everything()
    (mac.state / "setup").unlink()
    mac.flag("setup_dry_rc", "4")
    r = mac.run("--check")
    assert r.rc == 1, r.out
    assert (
        "not done, mail steps left\n    → sessionkit setup --dry-run\n"
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
    assert f"{EARS_ROW}: missing (left out: --no-speech)" in r.out
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
