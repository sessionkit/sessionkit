"""INSTALL.md section 8, the uninstall, pinned to its shape.

The section removes the program first (part A) and deletes the user's data
only on request (part B). It runs in reverse install order: the phone bot and
the voice jobs run from the plugins' files, so their own uninstall verbs come
before the plugins and the kit command go. Every `rm` on a variable path is
written `"${VAR:?}/..."`, so an empty variable fails loudly instead of
deleting from `/`. `:?` stops an EMPTY variable, not a WRONG one, so part B
never runs `rm` on a variable the reader sets: only `HOME`, and the loop
variables the doc binds to its own lists. A path that other tools share is
never deleted whole. Each step says whether it was MEASURED or is NOT YET,
like the rest of the doc.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from sessionkit import cli

ROOT = Path(__file__).resolve().parent.parent
INSTALL_DOC = (ROOT / "INSTALL.md").read_text(encoding="utf-8")

PART_A = "### A. Remove the program"
PART_B = "### B. Delete your data (USER DATA, opt-in)"
# Section 3's clone folder, which part B deletes by its literal name.
CLONES = "${HOME:?}/.local/share/sessionkit/src"

# Roots that other tools keep files in, or that hold more than the kit's.
SHARED = (
    "${HOME:?}",
    "${HOME:?}/",
    "${HOME:?}/.sessionkit",
    "${HOME:?}/.sessionkit/agents",
    "${HOME:?}/.sessionkit/mail",
    "${HOME:?}/.sessionkit/tools",
    "${HOME:?}/.sessionkit/tools/settings",
    "${HOME:?}/.sessionkit/view",
    "${HOME:?}/.sessionkit/voice",
    "${HOME:?}/.voicemode",
    "${HOME:?}/.voicemode/audio",
    "${HOME:?}/.voicemode/logs",
    "${HOME:?}/.voicemode/logs/conversations",
    "${HOME:?}/.voicemode/state",
    "${HOME:?}/.cache",
    "${HOME:?}/.config",
    "${HOME:?}/.config/notmuch",
    "${HOME:?}/.local",
    "${HOME:?}/.local/bin",
    "${HOME:?}/.local/share",
    "${HOME:?}/.local/share/uv",
    "${HOME:?}/.local/state",
    "${HOME:?}/.local/state/audio",
    "${HOME:?}/.claude",
    "${HOME:?}/.claude/plugins",
    "${HOME:?}/.mail",
    "${HOME:?}/.session",
    "${HOME:?}/Library",
    "${HOME:?}/Library/LaunchAgents",
)


def _section_8() -> str:
    start = INSTALL_DOC.index("## 8. Uninstall")
    end = INSTALL_DOC.find("\n## 9. ", start)
    return INSTALL_DOC[start:end if end != -1 else None]


def _rm_commands(text: str) -> list[tuple[str, list[str]]]:
    """Every `rm` in TEXT, as (flags, arguments), the arguments unquoted."""
    found = []
    for line in text.splitlines():
        for match in re.finditer(r"\brm (-[rf]+) ([^`#\n;]+)", line):
            args = re.findall(r'"[^"]*"\S*|\S+', match.group(2).strip())
            found.append((match.group(1), args))
    return found


def _steps(part: str) -> list[str]:
    """Part A's numbered steps, each from its bold `**N.` to the next."""
    return re.split(r"\n(?=\*\*\d+\. )", part)[1:]


def test_part_a_removes_the_program_before_part_b_deletes_data():
    section = _section_8()
    assert section.count(PART_A) == section.count(PART_B) == 1
    assert section.index(PART_A) < section.index(PART_B)


def test_the_data_part_is_opt_in_and_says_it_cannot_be_undone():
    part_b = _section_8().split(PART_B, 1)[1]
    assert part_b.startswith("\n\n**Only if you want it gone. This cannot be undone.**")
    assert "Part A kept all of it" in part_b


def test_part_a_deletes_no_user_data():
    part_a = _section_8().split(PART_B, 1)[0]
    for data in (".mail/agents", ".session/", ".sessionphone", ".sessionview",
                 "Library/Logs", "heard_", ".sessionkit/", "sessionkit/src", ".sessionmail"):
        for _, args in _rm_commands(part_a):
            assert not any(data in a for a in args), (data, args)


def test_reverse_order_service_verbs_then_plugins_then_data():
    section = _section_8()
    bot = section.index("`sessionphone bot uninstall`")
    voice = section.index("services uninstall`")
    plugins = section.index("- `claude plugin marketplace remove <r>`")
    kit = section.index("- `uv tool uninstall sessionkit`")
    data = section.index(PART_B)
    assert bot < voice < min(plugins, kit) < data
    # The clones go only after the plugins that were installed from them (G36).
    assert section.index(f'rm -rf "{CLONES}"') > plugins


def test_the_off_path_verbs_come_before_step_5_removes_the_session_command():
    # `session pane-state agent off` needs the kit's `session`, which step 5's
    # `uv tool uninstall sessionkit` removes; read top to bottom, the reader
    # must meet the off verbs first.
    section = _section_8()
    off_path = section.index("**Did you go off the install path?**")
    assert section.index("**4. The voice") < off_path
    assert off_path < section.index("**5. The plugins and the kit command")
    assert off_path < section.index("`session pane-state agent off`")
    # `off` alone keeps the engine binaries it built (PROGRAM files); only
    # `--purge` removes them (sessiontools sound/service.py `cmd_off`).
    assert off_path < section.index("`session sound engine off --purge`")


def test_every_rm_on_a_variable_path_fails_loudly_when_it_is_empty():
    commands = _rm_commands(_section_8())
    assert len(commands) >= 10, commands
    for flags, args in commands:
        for arg in args:
            assert re.match(r'"\$\{[A-Z_]+:\?\}', arg), (flags, arg)
            assert "$" not in re.sub(r"\$\{[A-Za-z_]+:\?\}", "", arg), arg


def test_part_b_runs_no_rm_on_a_variable_the_reader_sets():
    # `"${SRC:?}"` stops an empty SRC, not SRC=~/Code: a variable the reader
    # sets, or one their profile already set, can name any folder they own.
    part_b = _section_8().split(PART_B, 1)[1]
    loops = set(re.findall(r"\bfor (\w+) in [\w .-]+; do\b", part_b))
    allowed = {"HOME"} | loops
    commands = _rm_commands(part_b)
    assert commands, part_b[:60]
    for flags, args in commands:
        for arg in args:
            used = set(re.findall(r"\$\{?([A-Za-z_]\w*)", arg))
            assert used <= allowed, (flags, arg, used - allowed)
    # Nor does it ask the reader to set one.
    assert not re.search(r"\b[Ss]et `\$?[A-Z_]+`", part_b)


def test_part_b_deletes_the_clones_by_section_3s_literal_path():
    # The folder is the one section 3's loop clones into, spelled out.
    section_3 = INSTALL_DOC.split("## 3. Install the plugins", 1)[1].split("\n## 4. ", 1)[0]
    src = re.search(r"^SRC=(\S+)", section_3, re.MULTILINE).group(1)
    assert src == "~/.local/share/sessionkit/src"
    assert CLONES == src.replace("~", "${HOME:?}", 1)
    part_b = _section_8().split(PART_B, 1)[1]
    assert f'rm -rf "{CLONES}"' in part_b
    assert part_b.index(f'rm -rf "{CLONES}"') < part_b.index(
        'rmdir "${HOME:?}/.local/share/sessionkit"')


KIT_HOME = "${HOME:?}/.sessionkit"
# The settings folders part B removes whole: every file in them is the kit's.
# sessionview's is view/settings, never its old folder in the home directory.
WHOLE = ("mail", "voice", "view")
# tools/settings also holds claude-code.json, which `session start` reads and
# nothing in the kit writes: part B removes only the session and sounds files
# there, and what `session statusline install` wrote.
TOOLS_SETTINGS = f"{KIT_HOME}/tools/settings"
# What `session statusline install` writes in tools/settings (sessiontools'
# statusline module: the script, and the drop-in it owns whole), each with a
# `<name>.bak-<date>-<time>` copy beside any file it replaced.
STATUSLINE = ("statusline.sh", "claude-code.d/50-statusline.json")
# The `session` tool's account folder beside tools/settings (the tree spec;
# sessiontools' settings.accounts_dir). Its backups hold account tokens, so
# part B deletes it only as an item of its own, by its literal path.
ACCOUNTS = f"{KIT_HOME}/tools/accounts"
# The account folder from before it moved into the kit's home (sessiontools'
# registry.OLD_ACCOUNTS_SUBDIR). The kit never writes it, but a host that used
# `session account` before the move may still hold its token backups there.
OLD_ACCOUNTS = "${HOME:?}/.config/sessiontools"


def _settings_rm_args() -> list[str]:
    part_b = _section_8().split(PART_B, 1)[1]
    return [a.replace('"', "") for _, args in _rm_commands(part_b) for a in args
            if a.replace('"', "").startswith(KIT_HOME)]


def test_part_b_removes_whole_only_the_settings_folders_the_kit_owns():
    part_b = _section_8().split(PART_B, 1)[1]
    loop = re.search(r"for d in ([\w ]+); do rm -rf \"\$\{HOME:\?\}/\.sessionkit/\$\{d:\?\}/settings\"", part_b)
    assert loop, part_b[:60]
    assert tuple(loop.group(1).split()) == WHOLE
    assert "tools" not in loop.group(1).split()


def test_part_b_leaves_settings_nothing_in_the_kit_writes():
    part_b = _section_8().split(PART_B, 1)[1]
    files = []
    for names in re.findall(
        r"for f in ([\w .-]+); do rm -rf \"\$\{HOME:\?\}/\.sessionkit/tools/settings/\$\{f:\?\}\"", part_b
    ):
        files += names.split()
    assert files, part_b[:60]
    assert {f.lstrip(".").split(".", 1)[0] for f in files} == {"session", "sounds"}
    # The schema reader takes the hidden copy first, so both names go.
    for tool in ("session", "sounds"):
        assert {f"{tool}.schema.json", f".{tool}.schema.json"} <= set(files), tool
    assert not any("claude-code" in f for f in files)
    assert "leave `claude-code.json` there alone" in part_b
    assert "nothing in the kit writes it" in part_b


def test_part_b_settings_lines_stay_inside_a_settings_folder():
    # The one rm under the kit's home outside a settings folder is the
    # Accounts item's, by its literal path (pinned below).
    args = [a for a in _settings_rm_args() if a != ACCOUNTS]
    assert args, "no rm under the kit's home"
    for arg in args:
        assert re.match(r"\$\{HOME:\?\}/\.sessionkit/(\w+|\$\{d:\?\})/settings(/|$)", arg), arg


def test_no_rm_deletes_a_shared_root_whole():
    for _, args in _rm_commands(_section_8()):
        for arg in args:
            path = arg.replace('"', "").rstrip("/")
            assert path not in SHARED, arg


def test_shared_roots_are_only_ever_rmdired():
    section = _section_8()
    for root in ("${HOME:?}/.mail", "${HOME:?}/.session", KIT_HOME):
        assert f'rmdir "{root}"' in section
    assert f'rmdir "{KIT_HOME}/tools/settings"' in section
    assert f'rmdir "{KIT_HOME}/${{d:?}}"' in section


def test_part_b_rmdirs_no_folder_its_own_rm_already_removed():
    # mail/settings, voice/settings and view/settings go with `rm -rf`; an
    # rmdir of any would print `No such file or directory` on every run.
    part_b = _section_8().split(PART_B, 1)[1]
    loop = re.search(r"for d in ([\w ]+); do rm -rf \"\$\{HOME:\?\}/\.sessionkit/\$\{d:\?\}/settings\"", part_b)
    assert loop, part_b[:60]
    for d in loop.group(1).split():
        assert f'rmdir "{KIT_HOME}/{d}/settings"' not in part_b, d
    assert 'rmdir "${HOME:?}/.sessionkit/${d:?}/settings"' not in part_b



def test_part_b_deletes_the_notmuch_index_only_when_mail_setup_made_it():
    # Mail setup adopts no notmuch database: on a mail folder that already holds
    # `.notmuch` it writes no profile and says MANUAL. That database is the
    # reader's, so part B never removes it in the same breath as the boxes: its
    # rm is a line of its own, named for the one case it is the kit's.
    part_b = _section_8().split(PART_B, 1)[1]
    mail = part_b.split("- **Mail:**", 1)[1].split("\n- **", 1)[0]
    flat = " ".join(mail.split())
    index = '"${HOME:?}/.mail/.notmuch"'
    lines = [line.strip() for line in mail.splitlines() if re.match(r"\s*(rm|rmdir) ", line)]
    [own] = [line for line in lines if index in line]
    assert own == f"rm -rf {index}"
    assert 'rm -rf "${HOME:?}/.mail/agents/mouth"' in lines
    before = flat.split(" ".join(own.split()), 1)[0]
    assert "Delete it only if mail setup made the profile for it" in before
    assert "its first run said `wrote` on its `notmuch-profile` line" in flat
    assert "If that line said `MANUAL`, the database was in the mail folder before the kit" in flat
    assert "If you cannot tell, leave it" in flat
    # The mail folder's rmdir comes after the index line, so it can empty it.
    assert lines.index(own) < lines.index('rmdir "${HOME:?}/.mail"')


def test_part_b_explains_each_message_its_rmdir_lines_print():
    # A package the reader never set up (voice, before section 5) has no
    # folder, so its rmdir says `No such file or directory`; one that holds
    # files the kit did not write says `Directory not empty`. Both are named.
    part_b = _section_8().split(PART_B, 1)[1]
    settings = part_b.split("- **Settings:**", 1)[1].split("\n- **", 1)[0]
    assert "`Directory not empty`" in settings
    assert "`No such file or directory`" in settings


def test_part_b_removes_the_view_settings_in_the_kits_home_not_the_old_one():
    # sessionview's settings moved from its own folder in the home directory
    # to the kit's; part B removes them with the other packages' folders.
    # test_configuration_docs scans every file for the old home.
    section = _section_8()
    for _, args in _rm_commands(section):
        for arg in args:
            assert ".sessionview" not in arg, arg
    assert "the sidebar's config" in section.split(PART_B, 1)[1]
    assert f'for d in mail voice view tools; do rmdir "{KIT_HOME}/${{d:?}}"; done' in section


# The sidebar's state folder, and the old name it moves that folder from the
# first time it runs.
VIEW_STATE = "${HOME:?}/.local/state/sessionview"
OLD_VIEW_STATE = "${HOME:?}/.local/state/herd"


def test_part_a_removes_the_sidebars_state_by_its_name_then_its_old_one():
    step_6 = next(s for s in _steps(_section_8().split(PART_B, 1)[0])
                  if s.startswith("**6. "))
    removed = [line.split("#", 1)[0].strip() for line in step_6.splitlines()
               if line.startswith("rm -rf ")]
    new, old = f'rm -rf "{VIEW_STATE}"', f'rm -rf "{OLD_VIEW_STATE}"'
    assert new in removed and old in removed, removed
    assert removed.index(new) < removed.index(old), removed
    assert "`~/.local/state/sessionview`" in step_6
    # Each removes one folder, the sidebar's own, never the shared state root.
    for _, args in _rm_commands(step_6):
        assert '"${HOME:?}/.local/state"' not in args, args


def _statusline_undo_lines(text: str) -> list[str]:
    """The rm, find and rmdir lines under tools/settings that undo the status line."""
    return [line.strip() for line in text.splitlines()
            if TOOLS_SETTINGS in line and re.match(r"\s*(rm|find|rmdir) ", line)
            and ("statusline" in line or "claude-code.d" in line)]


def _assert_undoes_the_statusline(text: str) -> None:
    lines = _statusline_undo_lines(text)
    rm = [line for line in lines if line.startswith("rm -f ")]
    assert len(rm) == 1, lines
    for name in STATUSLINE:
        assert f'"{TOOLS_SETTINGS}/{name}"' in rm[0], name
    find = [line for line in lines if line.startswith("find ")]
    assert len(find) == 1, lines
    assert find[0].startswith(f'find "{TOOLS_SETTINGS}" -maxdepth 2 ')
    assert find[0].endswith(" -print -delete")
    for name in STATUSLINE:
        assert f"-name '{name.rsplit('/', 1)[-1]}.bak-*'" in find[0], name
    assert any(line.startswith(f'rmdir "{TOOLS_SETTINGS}/claude-code.d"') for line in lines), lines
    assert not any("claude-code.json" in line for line in lines)


def test_the_statusline_undo_names_what_install_wrote_never_claude_code_json():
    # `session statusline install` writes statusline.sh and the drop-in
    # claude-code.d/50-statusline.json, never claude-code.json: that file is
    # the reader's own. Part A names them and leaves the deleting to part B.
    section = _section_8()
    off_path = section.split("**Did you go off the install path?**", 1)[1].split("**5. ", 1)[0]
    item = off_path.split("- `session statusline install`:", 1)[1].split("\n- `", 1)[0]
    for name in STATUSLINE:
        assert f"`{name}`" in item, name
    assert "`.bak-<date>-<time>`" in item and "move it back" in item
    assert "leaves\n  `claude-code.json` alone" in item
    # Part A deletes no user data: the files go in part B's Settings item.
    assert "part B's **Settings** item deletes them" in item
    assert not _rm_commands(item) and not _statusline_undo_lines(item)
    assert "claude-code.json` by hand" not in section


def test_part_b_also_removes_what_statusline_install_wrote():
    part_b = _section_8().split(PART_B, 1)[1]
    _assert_undoes_the_statusline(part_b)


def test_no_find_deletes_outside_the_kits_settings():
    # One exception, the Mail item's: every box but the mouth's, which
    # VoiceMode shares (its own test pins the line whole).
    for line in _section_8().splitlines():
        if re.match(r"\s*find ", line) and "-delete" in line:
            if line.strip() == MAIL_ALL_BUT_MOUTH:
                continue
            assert line.strip().startswith(f'find "{TOOLS_SETTINGS}" '), line


def _part_b_item(name: str) -> str:
    part_b = _section_8().split(PART_B, 1)[1]
    return part_b.split(f"- **{name}:**", 1)[1].split("\n- **", 1)[0]


def _part_b_block(name: str) -> str:
    item = _part_b_item(name)
    block = re.search(r"```bash\n(.*?)\n\s*```", item, re.DOTALL)
    assert block, item[:80]
    return "\n".join(line.strip() for line in block.group(1).splitlines()) + "\n"


def _part_b_settings_block() -> str:
    return _part_b_block("Settings")


# Every file the kit's packages may leave under ~/.sessionkit, as part B's
# settings block sees them: seeded into a temp HOME and run for real.
KIT_FILES = (
    "mail/settings/mail.json",
    "voice/settings/ears.json", "voice/settings/mouth.json",
    "voice/settings/tts.key", "voice/settings/stt.key",
    "view/settings/view.json", "view/settings/neomuttrc",
    "view/settings/config.json.before-a",
    "tools/settings/session.json", "tools/settings/session.d/10-operator.json",
    "tools/settings/session.template.json", "tools/settings/session.schema.json",
    "tools/settings/.session.schema.json",
    "tools/settings/sounds.json", "tools/settings/sounds.d/10-busy.json",
    "tools/settings/sounds.template.json", "tools/settings/sounds.schema.json",
    "tools/settings/.sounds.schema.json",
    "tools/settings/statusline.sh", "tools/settings/statusline.sh.bak-a",
    "tools/settings/claude-code.d/50-statusline.json",
    "tools/settings/claude-code.d/50-statusline.json.bak-a-2",
)
# What the reader keeps: their own claude-code file and drop-in, an agent.
READER_FILES = (
    "tools/settings/claude-code.json",
    "tools/settings/claude-code.d/60-mine.json",
    "agents/someone/letter.md",
)


def _run_part_b(home: Path, files: tuple[str, ...], script: str | None = None
                ) -> subprocess.CompletedProcess:
    for rel in files:
        path = home / ".sessionkit" / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("x\n", encoding="utf-8")
    env = {"HOME": str(home), "PATH": os.environ.get("PATH", "/usr/bin:/bin"), "LC_ALL": "C"}
    script = _part_b_settings_block() if script is None else script
    return subprocess.run(["bash", "-c", script], env=env, cwd=home,
                          capture_output=True, text=True, timeout=30, check=False)


def _left(home: Path) -> set[str]:
    kit = home / ".sessionkit"
    return {str(p.relative_to(kit)) for p in kit.rglob("*") if p.is_file()} if kit.exists() else set()


def test_part_b_settings_block_run_in_a_temp_home_removes_every_kit_file(tmp_path):
    done = _run_part_b(tmp_path, KIT_FILES)
    assert not (tmp_path / ".sessionkit").exists(), (_left(tmp_path), done.stderr)
    assert done.stderr == "", done.stderr


def test_part_b_settings_block_run_in_a_temp_home_keeps_the_readers_files(tmp_path):
    done = _run_part_b(tmp_path, KIT_FILES + READER_FILES)
    assert _left(tmp_path) == set(READER_FILES), done.stderr
    # Only the `Directory not empty` the text explains, once per kept folder.
    errors = [line for line in done.stderr.splitlines() if line]
    assert errors and all("Directory not empty" in line for line in errors), errors
    assert len(errors) == 4, errors   # claude-code.d, tools/settings, tools, .sessionkit

# What `session account` keeps in its folder (sessiontools 66d2454: the
# registry, status's config, use's ledger and both backup folders).
ACCOUNT_FILES = (
    "tools/accounts/accounts.json", "tools/accounts/account-config.json",
    "tools/accounts/host-ledger.jsonl",
    "tools/accounts/token-file-backups/20301001T000000Z.token",
    "tools/accounts/keychain-backups/20301001T000000Z.json",
)


def test_part_b_names_the_account_folder_and_warns_before_its_one_line():
    # The uninstall used to leave tools/accounts/ (account token backups) on
    # disk without a word. Part B names it, says part A and Settings leave it,
    # warns that its line deletes the token backups, and lets the reader skip.
    item = _part_b_item("Accounts")
    flat = " ".join(item.split())
    assert "`~/.sessionkit/tools/accounts/`" in flat
    for name in ("accounts.json", "account-config.json", "host-ledger.jsonl",
                 "token-file-backups/", "keychain-backups/"):
        assert f"`{name}`" in flat, name
    assert "never the token" in flat
    assert "**The backups are your account tokens.**" in flat
    assert "Part A leaves this folder, and so does the **Settings** item below" in flat
    assert "the uninstall leaves these tokens on disk until you run this line" in flat
    assert "cannot be undone: to keep your accounts, skip it" in flat
    assert [line.strip() for line in item.splitlines() if re.match(r"\s*(rm|rmdir|find) ", line)] \
        == [f'rm -rf "{ACCOUNTS}"',
            f'rm -rf "{OLD_ACCOUNTS}"']
    # Settings points at it, and at the tree spec that puts it beside settings/.
    settings = " ".join(_part_b_item("Settings").split())
    assert "`openspec/specs/tree/spec.md`" in settings
    assert (ROOT / "openspec/specs/tree/spec.md").is_file()
    assert "the account folder, the item above" in settings
    assert "or the account folder you kept" in settings


def test_part_b_deletes_the_account_folder_before_the_settings_rmdirs_run():
    # So the Settings item's rmdir lines can empty tools/ and ~/.sessionkit.
    part_b = _section_8().split(PART_B, 1)[1]
    assert part_b.index(f'rm -rf "{ACCOUNTS}"') < part_b.index("- **Settings:**")
    # Part A deletes nothing under the account folder.
    part_a = _section_8().split(PART_B, 1)[0]
    assert not any("accounts" in a for _, args in _rm_commands(part_a) for a in args)


def test_part_b_accounts_then_settings_in_a_temp_home_removes_the_kits_home(tmp_path):
    script = _part_b_block("Accounts") + _part_b_settings_block()
    done = _run_part_b(tmp_path, KIT_FILES + ACCOUNT_FILES, script)
    assert not (tmp_path / ".sessionkit").exists(), (_left(tmp_path), done.stderr)
    assert done.stderr == "", done.stderr


def test_part_b_settings_alone_keeps_the_account_folder(tmp_path):
    # A reader who skips Accounts keeps every account file; the only noise is
    # the `Directory not empty` the Settings item explains, for tools/ and
    # ~/.sessionkit.
    done = _run_part_b(tmp_path, KIT_FILES + ACCOUNT_FILES)
    assert _left(tmp_path) == set(ACCOUNT_FILES), done.stderr
    errors = [line for line in done.stderr.splitlines() if line]
    assert len(errors) == 2 and all("Directory not empty" in line for line in errors), errors


def test_every_step_says_measured_or_not_yet():
    section = _section_8()
    assert section.startswith("## 8. Uninstall\n\n**NOT YET** as a whole")
    steps = _steps(section.split(PART_B, 1)[0])
    assert [s.split(".", 1)[0] for s in steps] == [f"**{n}" for n in range(1, 8)]
    for step in steps:
        assert "**MEASURED**" in step or "**NOT YET" in step, step[:60]
    assert "**NOT YET**: none of these lines" in section.split(PART_B, 1)[1]


def test_the_plugin_cache_loop_names_the_five_children():
    loops = re.findall(r"^for r in (.*?); do$", _section_8(), re.MULTILINE)
    assert len(loops) == 1
    assert sorted(loops[0].split()) == sorted(cli.FAMILY)


# SK-88 (0.2.1): the kit floors sessionvoice at 0.2.0, whose uninstall honours
# --dry-run (measured on a temporary home), so 0.1.0's no-dry-run warning goes.
def test_the_voice_uninstall_offers_its_dry_run_first():
    section = _section_8()
    flat = " ".join(section.split())
    assert "has no dry run" not in section
    assert "**Look first with `--dry-run`.** `ears services uninstall --dry-run` names each" in flat
    assert "printed `dry run: nothing booted out, nothing deleted`, and exited 0" in flat
    assert "`launchctl` acts on your own user's jobs whatever `HOME` says" in flat
    assert "`ears services status` only reads too" in flat


# SK-74: the kit's own `ears` uninstalls the voice jobs; no plugin bin/ears detour.
# SK-88 (0.2.1): sessionvoice is floored at 0.2.0, so 0.1.0's plugin bin/ears
# bullet goes: the kit's own `ears` (0.2.1) knows every label form.
def test_the_voice_uninstall_uses_the_kits_own_ears():
    section = _section_8()
    assert "Run `ears services uninstall`, the kit's own `ears`" in section
    assert "**On sessionvoice 0.1.0**" not in section
    assert not re.search(r"bin/ears(?![-\w])", section)
    assert "on 0.1.0, the plugin's" not in section
    # SK-137: 0.2.0's own are dev.sessionkit.voice.*; it retires both old forms.
    flat = " ".join(section.split())
    assert (
        "0.2.1 knows its own labels, `dev.sessionkit.voice.*`, and both old forms it retires: "
        "`com.sessionvoice.*`, and the older `com.voicemode.ears-*`"
    ) in flat
    assert "0.1.0 knows the older set only" not in flat


# SK-88 (0.2.1): section 8's other 0.1.0 branches are flipped, each re-measured
# on the 0.2.1 wheel with its five children (14 commands, not 0.1.0's 9).
def test_section_8_has_no_0_1_0_branches_left():
    flat = " ".join(_section_8().split())
    assert "printed `Uninstalled 14 executables`" in flat
    assert "Uninstalled 9 executables" not in flat
    assert "(2030-06-09, sessionphone 0.2.1)" in flat
    assert "any on 0.1.0" not in flat
    assert "newer than 0.1.0" not in flat


def test_the_kept_marketplace_line_is_still_the_plugin_step():
    # Section 8 keeps section 3's marketplace remove as its plugin step, as
    # test_readme.py's README/INSTALL.md agreement tests expect.
    step_5 = _steps(_section_8().split(PART_B, 1)[0])[4]
    assert step_5.startswith("**5. The plugins and the kit command")
    assert "claude plugin marketplace remove <r>` for each of the five" in step_5


# What a fresh install leaves, measured from the packages' source. Each test
# below seeds a temp HOME with those paths, plus files the kit never wrote,
# runs the doc's own lines with bash, and checks what is left.


def _blocks(text: str) -> list[str]:
    """Every ```bash block in TEXT, each line stripped of its indent."""
    return ["\n".join(line.strip() for line in block.splitlines()) + "\n"
            for block in re.findall(r"```bash\n(.*?)\n\s*```", text, re.DOTALL)]


def _seed(home: Path, files: tuple[str, ...]) -> None:
    for rel in files:
        path = home / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("x\n", encoding="utf-8")


def _run(home: Path, script: str) -> subprocess.CompletedProcess:
    env = {"HOME": str(home), "PATH": os.environ.get("PATH", "/usr/bin:/bin"), "LC_ALL": "C"}
    return subprocess.run(["bash", "-c", script], env=env, cwd=home,
                          capture_output=True, text=True, timeout=30, check=False)


def _files(home: Path) -> set[str]:
    return {str(p.relative_to(home)) for p in home.rglob("*") if p.is_file() or p.is_symlink()}


def _step(n: int) -> str:
    return next(s for s in _steps(_section_8().split(PART_B, 1)[0]) if s.startswith(f"**{n}. "))


def test_the_voice_jobs_check_says_to_wait_for_jobs_still_exiting():
    # Run at once, the check still lists jobs that are exiting; they clear
    # a few seconds later.
    check = _step(4).split("- **Check:**", 1)[1].split("\n- **", 1)[0]
    flat = " ".join(check.split())
    assert "Wait a few seconds before you run it" in flat
    assert "wait a few seconds and run it again, until it prints nothing" in flat


# Program state the voice and mail leave outside the folders step 6 already named.
PROGRAM_STATE = (
    ".local/state/ears/call-ears/live", ".local/state/ears/call-ears/capture-1.log",
    ".local/state/ears/call-tap/LISTEN-OFF",
    ".cache/session-mail/ext/v1/stamp",
    ".local/state/audio/devices.json",
    ".cache/ears/silero_vad.onnx", ".cache/ears/run/keeper.pid",
    ".local/share/ears/speech/bin/python",
    ".local/state/sessionview/mutt/x", ".local/state/herd/x",
)
# Not the program's: user data part A keeps, and other tools' files.
NOT_PROGRAM = (
    ".local/share/ears/speakers/me/voice.npy",
    ".local/state/claude/lock",
    ".local/state/other/x",
    ".cache/huggingface/hub/model",
)


def test_part_a_step_6_removes_the_voice_and_mail_program_state(tmp_path):
    [block] = _blocks(_step(6))
    _seed(tmp_path, PROGRAM_STATE + NOT_PROGRAM)
    done = _run(tmp_path, block)
    assert _files(tmp_path) == set(NOT_PROGRAM), done.stderr
    assert done.stderr == "", done.stderr
    assert not (tmp_path / ".local/state/audio").exists()


def test_part_a_step_6_deletes_only_the_voices_file_in_the_shared_audio_folder(tmp_path):
    # The folder's name is generic and its file is read by other tools: the
    # step deletes the voice's file and the folder only when it is empty.
    [block] = _blocks(_step(6))
    for _, args in _rm_commands(block):
        assert '"${HOME:?}/.local/state/audio"' not in args, args
    assert 'rmdir "${HOME:?}/.local/state/audio"' in block
    _seed(tmp_path, PROGRAM_STATE + (".local/state/audio/other.json",))
    done = _run(tmp_path, block)
    assert _files(tmp_path) == {".local/state/audio/other.json"}, done.stderr
    errors = [line for line in done.stderr.splitlines() if line]
    assert len(errors) == 1 and "Directory not empty" in errors[0], errors
    assert "`~/.local/state/audio/devices.json`" in _step(6)


def test_part_a_names_claude_codes_state_as_not_the_kits():
    assert "`~/.local/state/claude`: leave them" in " ".join(_step(7).split())


def test_part_b_session_records_remove_the_session_lists_state(tmp_path):
    item = _part_b_item("Session records")
    [block] = _blocks(item)
    assert "for d in agent seats sessions mail state; do" in block
    _seed(tmp_path, (
        ".session/agent/config/x", ".session/seats/s/x", ".session/sessions/sid/mail/marks",
        ".session/mail/x", ".session/state/list/snapshot.json",
        ".session/state/pane-state/watch.lock", ".sessionmail/sessions/x",
    ))
    done = _run(tmp_path, block)
    assert _files(tmp_path) == set(), done.stderr
    assert not (tmp_path / ".session").exists()
    assert done.stderr == "", done.stderr


def test_part_b_session_records_name_the_older_agents_folder_they_leave(tmp_path):
    item = _part_b_item("Session records")
    flat = " ".join(item.split())
    assert "`~/.session/agents` may still hold a link for each agent" in flat
    assert "`Directory not empty`" in flat
    [block] = _blocks(item)
    (tmp_path / ".session/agents").mkdir(parents=True)
    (tmp_path / ".session/agents/someone").symlink_to(tmp_path / "elsewhere")
    done = _run(tmp_path, block)
    assert _files(tmp_path) == {".session/agents/someone"}, done.stderr
    errors = [line for line in done.stderr.splitlines() if line]
    assert len(errors) == 1 and "Directory not empty" in errors[0], errors


# What sessionvoice writes on a fresh install: everything under its own home,
# ~/.sessionvoice, then ~/.ears, the speakers' home and the service logs.
VOICE_FRESH = (
    ".sessionvoice/logs/conversations/heard_2030-01-01.jsonl",
    ".sessionvoice/logs/conversations/heard.lock",
    ".sessionvoice/logs/conversations/speakers_2030-01-01.jsonl",
    ".sessionvoice/state/heard-cursor/sid", ".sessionvoice/state/heard-cursor/sid.lock",
    ".sessionvoice/state/missed-reply/clip.wav",
    ".sessionvoice/audio/2030-01-01/120000-000-1.wav",
    ".sessionvoice/mouth/playing.json", ".sessionvoice/mouth/done/x",
    ".sessionvoice/mouth/audio/line.wav",
    ".sessionvoice/talk/token",
    ".ears/heard.state",
    ".local/share/ears/speakers/me/voice.npy",
    "Library/Logs/ears/keeper.log",
)
# The files only sessionvoice writes, where an older sessionvoice kept them,
# in ~/.voicemode.
VOICE_LEGACY = (
    ".voicemode/logs/conversations/speakers_2030-01-01.jsonl",
    ".voicemode/talk/token",
    ".voicemode/state/missed-reply/clip.wav",
    ".voicemode/audio/2030-01-01/120000-000-1.wav",
)
# What VoiceMode writes too (its own heard log, the log's lock, its cursors
# and its mouth): deleted only on the reader's word.
VOICE_SHARED = (
    ".voicemode/logs/conversations/heard_2030-01-01.jsonl",
    ".voicemode/logs/conversations/heard.lock",
    ".voicemode/mouth/playing.json", ".voicemode/state/heard-cursor/sid",
)
# VoiceMode's own files, and Claude Code's: never touched.
VOICEMODE_OWN = (
    ".voicemode/voicemode.env", ".voicemode/voices/a.pt", ".voicemode/services/whisper/x",
    ".voicemode/logs/conversations/exchanges_2030-01-01.jsonl",
    ".voicemode/audio/2030/01/20300101_120000_tts.wav", ".voicemode/audio/flat.wav",
    ".claude/heard.state.not-ours", ".local/state/claude/lock",
)


def test_part_b_voice_deletes_the_heard_log_where_a_fresh_install_writes_it():
    item = _part_b_item("Voice")
    flat = " ".join(item.split())
    first = _blocks(item)[0]
    assert 'rm -rf "${HOME:?}/.sessionvoice" "${HOME:?}/.ears"' in first
    for named in ("`heard_*.jsonl`", "`speakers_*.jsonl`", "`talk/token`",
                  "every line the mouth spoke, which it keeps by default",
                  "If you turned recording on", "`~/.sessionvoice`", "`~/.ears`"):
        assert named in flat, named


def test_part_b_voice_in_a_temp_home_removes_what_the_voice_wrote(tmp_path):
    fresh, legacy, shared = _blocks(_part_b_item("Voice"))
    _seed(tmp_path, VOICE_FRESH + VOICE_LEGACY + VOICE_SHARED + VOICEMODE_OWN)
    done = _run(tmp_path, fresh + legacy)
    assert done.stderr == "", done.stderr
    assert _files(tmp_path) == set(VOICE_SHARED + VOICEMODE_OWN)
    assert not (tmp_path / ".sessionvoice").exists() and not (tmp_path / ".ears").exists()
    # The shared folders go only with the line the reader chooses.
    done = _run(tmp_path, shared)
    assert done.stderr == "", done.stderr
    assert _files(tmp_path) == set(VOICEMODE_OWN)


def test_part_b_voice_lines_do_nothing_where_nothing_is_there(tmp_path):
    _seed(tmp_path, VOICEMODE_OWN)
    done = _run(tmp_path, "".join(_blocks(_part_b_item("Voice"))))
    assert done.stderr == "", done.stderr
    assert _files(tmp_path) == set(VOICEMODE_OWN)


def test_part_b_voice_never_deletes_voicemodes_own_files():
    item = _part_b_item("Voice")
    args = [a.replace('"', "") for _, args in _rm_commands(item) for a in args]
    # sessionvoice files its kept turn audio in dated folders; VoiceMode files
    # its own by year, then month. Only the dated folders go.
    dated = "audio/[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]"
    for arg in args:
        if "/.voicemode" in arg:
            rel = arg.split("/.voicemode/", 1)[1]
            assert not rel.startswith(("voicemode.env", "voices", "services", "eval")), arg
            assert "exchanges_" not in rel, arg
            assert not rel.startswith("audio") or rel == dated, arg
    assert f"${{HOME:?}}/.voicemode/{dated}" in args
    assert "never delete it whole" in " ".join(item.split())


def test_part_b_voice_keeps_voicemodes_heard_log_unless_the_reader_drops_voicemode():
    # VoiceMode writes the same heard log, with the same lock, in ~/.voicemode,
    # and keeps its cursors into it. Only the block the reader chooses deletes
    # them, with the mouth.
    item = _part_b_item("Voice")
    fresh, legacy, shared = _blocks(item)
    for block in (fresh, legacy):
        assert "heard_" not in block and "heard.lock" not in block and "heard-cursor" not in block
    assert shared.splitlines() == [
        'rm -f "${HOME:?}"/.voicemode/logs/conversations/heard_*.jsonl',
        'rm -f "${HOME:?}/.voicemode/logs/conversations/heard.lock"',
        'rm -rf "${HOME:?}/.voicemode/mouth" "${HOME:?}/.voicemode/state/heard-cursor"',
    ]
    flat = " ".join(item.split())
    assert "VoiceMode writes the same transcript" in flat
    assert "If you do not use VoiceMode, delete them with the lines below. If you do, keep them" in flat
    assert "stay in that transcript, beside VoiceMode's, until you delete it" in flat


def test_part_b_voice_names_every_home_sessionvoice_may_have_chosen():
    # sessionvoice's home is $SESSIONVOICE_HOME, then $VOICEMODE_BASE_DIR, then
    # ~/.sessionvoice or ~/.voicemode, whichever already holds a heard log. A
    # fresh install adopts ~/.voicemode when VoiceMode's converse wrote first.
    flat = " ".join(_part_b_item("Voice").split())
    assert "If your shell sets `SESSIONVOICE_HOME`, or VoiceMode's `VOICEMODE_BASE_DIR`" in flat
    assert "Nothing in the kit sets either, so if one is set, you set it" in flat
    assert "If it names another folder, these lines miss it" in flat
    assert "an older sessionvoice wrote one there, or VoiceMode's `converse` did" in flat
    assert "the older sessionvoice heard" not in flat


def test_part_b_voice_names_heard_state_in_a_seat_folder_and_never_deletes_that_folder():
    item = _part_b_item("Voice")
    flat = " ".join(item.split())
    assert "`~/.<name>`" in flat and "`heard.state`" in flat
    assert "Delete that one file by hand, never the folder" in flat
    assert not any(".claude" in a for _, args in _rm_commands(item) for a in args)
    # ears-arm's first rule: $EARS_HOME, when set, names the folder instead.
    assert "If your shell sets `EARS_HOME`, `ears-arm` kept its `heard.state`" in flat
    assert not any("EARS_HOME" in a for _, args in _rm_commands(item) for a in args)


def test_the_changelog_keeps_the_shared_voicemode_files_apart_from_the_variables():
    # The bullet's "only if you do not use VoiceMode" sentence names the
    # folder it means, and sits before the sentence about the variables, so
    # it cannot be read as the folder a variable names.
    # The bullet landed in 0.2.0: read that release's section by its heading.
    text = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    release = text.split("\n## [0.2.0]", 1)[1].split("\n## [", 1)[0]
    [bullet] = [b for b in release.split("\n- ") if "deletes the transcript of what the ears heard" in b]
    flat = " ".join(bullet.split())
    shared = flat.index("The transcript in `~/.voicemode`, its lock, and the two folders VoiceMode shares")
    variables = flat.index("`SESSIONVOICE_HOME`, `VOICEMODE_BASE_DIR` or `EARS_HOME` names another folder")
    assert shared < variables
    assert "never VoiceMode's own" not in flat


def test_part_b_settings_says_the_voices_speech_keys_are_in_its_settings_folder():
    flat = " ".join(_part_b_item("Settings").split())
    assert "`stt.key` and `tts.key`, are in `~/.sessionkit/voice/settings/`" in flat
    assert "this item deletes them with your voice choices" in flat


def test_part_b_accounts_names_the_folder_from_before_the_move_and_warns(tmp_path):
    item = _part_b_item("Accounts")
    flat = " ".join(item.split())
    assert "`~/.config/sessiontools/`" in flat
    assert "**Its backups are your account tokens too.**" in flat
    assert "to keep those accounts, skip it" in flat
    assert "It leaves the rest of `~/.config` alone" in flat
    for _, args in _rm_commands(item):
        assert '"${HOME:?}/.config"' not in args, args
    [block] = _blocks(item)
    kept = (".config/notmuch/sessionkit/config", ".config/other/x")
    _seed(tmp_path, (".config/sessiontools/accounts.json",
                     ".config/sessiontools/token-file-backups/20301001T000000Z.token") + kept)
    done = _run(tmp_path, block)
    assert done.stderr == "", done.stderr
    assert _files(tmp_path) == set(kept)


def test_no_uninstall_line_carries_a_comment():
    # In zsh, the Mac's own shell, a `#` typed at the prompt is a word, not a
    # comment (`interactivecomments` is off), so a pasted
    # `rm -rf "$x"   # the cache` also deletes `./the` and `./cache`. And a
    # comment's apostrophe opens a quote that swallows the next lines.
    blocks = re.findall(r"```bash\n(.*?)\n\s*```", _section_8(), re.DOTALL)
    assert len(blocks) > 10
    commented = [line.strip() for block in blocks for line in block.splitlines() if "#" in line]
    assert commented == [], commented
    assert "a `#` typed at the prompt is not a comment" in " ".join(_step(6).split())


# The mouth's queue, ~/.mail/agents/mouth, is ONE box for both mouths:
# sessionvoice's (src/mouth/box.py:117, inbox.py:34, maillog.py:52 at
# 6c849c8) and VoiceMode's (voice_mode/mouth/box.py:85, inbox.py:31 at
# e03b5d9). The Mail item deletes every other box, and the mouth's only on
# the reader's word that VoiceMode goes too, as the Voice item does.
MAIL_ALL_BUT_MOUTH = (
    'find "${HOME:?}/.mail/agents" -mindepth 1'
    ' -not -path "${HOME:?}/.mail/agents/mouth"'
    ' -not -path "${HOME:?}/.mail/agents/mouth/*" -delete'
)
MAIL_BOXES = (
    ".mail/agents/operator/new/1", ".mail/agents/operator/cur/2:2,S",
    ".mail/agents/someone-chat/new/3", ".mail/agents/heard/tmp/4",
    ".mail/agents/.hidden/new/5",
    # Named like the mouth's box, but not it.
    ".mail/agents/mouthpiece/new/6", ".mail/agents/mouth.old/new/7",
    ".config/notmuch/sessionkit/config",
)
MOUTH_BOX = (".mail/agents/mouth/new/to-speak", ".mail/agents/mouth/cur/spoken:2,S")
# The reader's own, and what the third block decides on: never the first two's.
MAIL_KEPT = (".notmuch-config", ".mail/.notmuch/xapian/db")


def test_part_b_mail_keeps_the_mouths_box_unless_the_reader_drops_voicemode():
    item = _part_b_item("Mail")
    boxes, mouth, _index = _blocks(item)
    assert boxes.splitlines()[0] == MAIL_ALL_BUT_MOUTH
    assert mouth.splitlines() == [
        'rm -rf "${HOME:?}/.mail/agents/mouth"',
        'rmdir "${HOME:?}/.mail/agents"',
    ]
    # No line deletes the boxes' folder whole.
    assert not any(a.replace('"', "") == "${HOME:?}/.mail/agents"
                   for _, args in _rm_commands(item) for a in args)
    flat = " ".join(item.split())
    assert "sessionvoice's mouth and VoiceMode's both queue their lines in that one box" in flat
    assert "So the first line deletes every box but that one" in flat
    assert ("If you do not use VoiceMode, the mouth's box is the kit's alone: delete it with"
            " the lines below. If you do, keep it") in flat
    assert "stay in that box, beside VoiceMode's, until you delete it" in flat
    for name in ("`MOUTH_MAILBOX`", "`VOICEMODE_MOUTH_MAILBOX`", "`MOUTH_DIR`",
                 "`VOICEMODE_MOUTH_DIR`"):
        assert name in flat, name
    assert "It prints the same if you kept the mouth's box" in flat


@pytest.mark.parametrize("shell", ["bash", "zsh"])
def test_part_b_mail_in_a_temp_home_keeps_the_mouths_box_until_the_reader_chooses(tmp_path, shell):
    if shutil.which(shell) is None:
        pytest.skip(f"no {shell}")
    boxes, mouth, _index = _blocks(_part_b_item("Mail"))
    _seed(tmp_path, MAIL_BOXES + MOUTH_BOX + MAIL_KEPT)
    env = {"HOME": str(tmp_path), "PATH": os.environ.get("PATH", "/usr/bin:/bin"), "LC_ALL": "C"}
    argv = [shell, "-f", "-c"] if shell == "zsh" else [shell, "-c"]

    def run(script: str) -> subprocess.CompletedProcess:
        return subprocess.run([*argv, script], env=env, cwd=tmp_path, capture_output=True,
                              text=True, timeout=30, check=False)

    done = run(boxes)
    assert done.stderr == "", done.stderr
    assert _files(tmp_path) == set(MOUTH_BOX + MAIL_KEPT)
    assert sorted(p.name for p in (tmp_path / ".mail/agents").iterdir()) == ["mouth"]
    # The mouth's box goes only with the block the reader chooses.
    done = run(mouth)
    assert done.stderr == "", done.stderr
    assert _files(tmp_path) == set(MAIL_KEPT)
    assert not (tmp_path / ".mail/agents").exists()


# The whole of section 8 on one temp HOME, as a reader pastes it: part A step
# 6, then every part B block in order, each block pasted on its own into an
# interactive shell whose cwd is HOME. The seed is the write-set of a fresh
# 0.2.0 install, every path the kit's packages write there, plus files the kit
# never wrote and a file in the cwd for every word section 8 uses (a `#`
# pasted at zsh's prompt hands its words to the command as paths). A reader
# who keeps VoiceMode skips each block whose lead says "If you do not use
# VoiceMode". The task's full proof also seeds a host whose sessionvoice home
# is ~/.voicemode; this pins its result.
E2E_KIT = (
    ".sessionvoice/logs/conversations/heard_2030-01-02.jsonl",
    ".sessionvoice/logs/conversations/heard.lock",
    ".sessionvoice/logs/conversations/speakers_2030-01-02.jsonl",
    ".sessionvoice/state/heard-cursor/sid-1", ".sessionvoice/state/missed-reply/clip.wav",
    ".sessionvoice/audio/2030-01-02/101010-123-1.wav",
    ".sessionvoice/mouth/playing.json", ".sessionvoice/mouth/audio/line.wav",
    ".sessionvoice/talk/token", ".ears/heard.state",
    ".sessionkit/voice/settings/ears.json", ".sessionkit/voice/settings/stt.key",
    ".cache/ears/silero_vad.onnx", ".cache/ears/run/keeper.pid",
    "Library/Logs/ears/keeper.log",
    ".local/share/ears/speech/bin/python", ".local/share/ears/speakers/me.npy",
    ".local/state/ears/call-ears/live", ".local/state/ears/call-tap/LISTEN-OFF",
    ".local/state/audio/devices.json",
    ".mail/agents/operator/new/1", ".mail/agents/operator/cur/2:2,S",
    ".mail/agents/assistant-chat/new/3", ".mail/.notmuch/xapian/db",
    ".config/notmuch/sessionkit/config", ".sessionkit/mail/settings/mail.json",
    ".session/sessions/sid-1/mail/marks", ".session/sessions/sid-1/log/mail",
    ".sessionmail/post-new/state", ".cache/session-mail/ext/v1/stamp",
    ".session/state/list/snapshot.json", ".session/seats/operator/seat.json",
    ".session/agent/config/agent.json",
    ".sessionkit/tools/settings/session.json",
    ".sessionkit/tools/settings/session.d/10-operator.json",
    ".sessionkit/tools/settings/.sounds.schema.json",
    ".sessionkit/tools/settings/statusline.sh.bak-a",
    ".sessionkit/tools/accounts/token-file-backups/work.token",
    ".config/sessiontools/token-file-backups/work.token",
    ".sessionphone/calls/call-1/audio.wav", ".sessionphone/bot.log",
    ".local/state/sessionview/mutt/x", ".local/state/herd/x",
    ".sessionkit/view/settings/config.json",
    ".local/share/sessionkit/src/sessionkit/README.md",
)
# Used by VoiceMode too: kept while the reader keeps VoiceMode.
E2E_SHARED = (
    ".mail/agents/mouth/new/to-speak", ".mail/agents/mouth/cur/spoken:2,S",
    ".voicemode/logs/conversations/heard_2030-01-01.jsonl",
    ".voicemode/logs/conversations/heard.lock",
    ".voicemode/state/heard-cursor/vm-1", ".voicemode/mouth/playing.json",
)
# Never the kit's, in either mode.
E2E_THEIRS = (
    ".voicemode/voicemode.env", ".voicemode/voices/v.json",
    ".voicemode/logs/conversations/exchanges_2030-01-02.jsonl",
    ".voicemode/audio/2030/01/x.wav",
    ".notmuch-config", ".config/notmuch/default/config", ".config/other/x",
    ".sessionkit/tools/settings/claude-code.json", ".sessionkit/agents/someone/letter.md",
    ".cache/huggingface/hub/model", ".local/state/claude/lock", ".local/state/x/y",
    ".local/state/audio/other.json", ".claude/settings.json", "Library/Logs/other/x",
)
# Roots the text never deletes whole: they may stay, empty.
E2E_ROOTS = {".cache", ".config", ".local", ".local/share", ".local/state", "Library",
             "Library/Logs"}


def _e2e_blocks(keep_voicemode: bool) -> list[str]:
    part_b = _section_8().split(PART_B, 1)[1]
    blocks = _blocks(_step(6))
    for item in part_b.split("\n- **")[1:]:
        lead = 0
        for m in re.finditer(r"```bash\n(.*?)\n\s*```", item, re.DOTALL):
            dropping = "If you do not use VoiceMode" in item[lead:m.start()]
            lead = m.end()
            if not (keep_voicemode and dropping):
                blocks.append("\n".join(x.strip() for x in m.group(1).splitlines()) + "\n")
    return blocks


def _ancestors(paths) -> set[str]:
    return {str(Path(*Path(p).parts[:i])) for p in paths for i in range(1, len(Path(p).parts))}


@pytest.mark.parametrize("mode", ["keep-voicemode", "drop-voicemode", "kit-alone"])
@pytest.mark.parametrize("shell", ["bash", "zsh"])
def test_section_8_in_a_temp_home_leaves_nothing_the_kit_wrote(tmp_path, shell, mode):
    if shutil.which(shell) is None:
        pytest.skip(f"no {shell}")
    home = tmp_path / "home"
    keep = mode == "keep-voicemode"
    if mode == "kit-alone":
        seeded, survivors = E2E_KIT + E2E_SHARED[:2], ()
    else:
        seeded, survivors = E2E_KIT + E2E_SHARED + E2E_THEIRS, E2E_THEIRS
        survivors += E2E_SHARED if keep else ()
    for rel in seeded:
        (home / rel).parent.mkdir(parents=True, exist_ok=True)
        (home / rel).write_text(f"{rel}\n", encoding="utf-8")
    taken = {p.split("/", 1)[0].lower() for p in seeded}
    words = {w for w in re.findall(r"[A-Za-z][A-Za-z0-9_-]+", _section_8())
             if w.lower() not in taken}
    words = {w.lower(): w for w in sorted(words)}.values()
    for w in words:
        (home / w).write_text(f"{w}\n", encoding="utf-8")
    env = {"HOME": str(home), "PATH": "/usr/bin:/bin:/usr/sbin:/sbin", "LC_ALL": "C",
           "HISTFILE": str(tmp_path / "history"), "PS1": ""}
    argv = [shell, "-f", "-i", "-s"] if shell == "zsh" else [shell, "--norc", "--noprofile"]
    for block in _e2e_blocks(keep):
        subprocess.run(argv, input=block, env=env, cwd=home, capture_output=True, text=True,
                       timeout=60, check=False)
    want = set(survivors) | set(words)
    assert _files(home) == want, sorted(_files(home) ^ want)
    for rel in want:
        assert (home / rel).read_text(encoding="utf-8") == f"{rel}\n", rel
    dirs = {str(p.relative_to(home)) for p in home.rglob("*") if p.is_dir()}
    stray = dirs - _ancestors(want) - E2E_ROOTS
    # VoiceMode's own folders may stay: the text never deletes them whole.
    assert {d for d in stray if not d.startswith(".voicemode")} == set(), sorted(stray)
