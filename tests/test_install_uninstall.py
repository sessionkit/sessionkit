"""INSTALL.md section 8, the uninstall, and its reference, docs/uninstall.md.

Section 8 is the short page: three blocks, stop and remove the jobs, remove the
plugins and the tool, then the opt-in data. docs/uninstall.md carries every
line and the reasons, in the same order: the program first (its steps 1 to 6),
then the user's data only on request (its section 3), then the shared caches
(its section 4). It runs in reverse install order: the phone bot and the voice
jobs run from the plugins' files, so their own uninstall verbs come before the
plugins and the kit command go. Every `rm` on a variable path is written
`"${VAR:?}/..."`, so an empty variable fails loudly instead of deleting from
`/`. `:?` stops an EMPTY variable, not a WRONG one, so the data part never
runs `rm` on a variable the reader sets: only `HOME`, and the loop variables
the doc binds to its own lists. A path that other tools share is never deleted
whole, and nothing deletes from `~/Library/Logs`. Each step says whether it was
MEASURED or is NOT YET, like the rest of the doc.
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
UNINSTALL_DOC = (ROOT / "docs" / "uninstall.md").read_text(encoding="utf-8")

# The short page's three blocks, and the reference's sections.
SHORT_BLOCKS = (
    "### 1. Stop and remove the jobs",
    "### 2. Remove the plugins and the tool",
    "### 3. Your data (opt-in)",
)
PART_A = "## 1. Stop and remove the jobs"
PART_A2 = "## 2. Remove the plugins and the tool"
PART_B = "## 3. Delete your data (USER DATA, opt-in)"
CACHES = "## 4. Caches and tools other programs share (opt-in)"
STAYS = "## 5. What stays"
# Section 3's clone folder, which the data part deletes by its literal name.
CLONES = "${HOME:?}/.local/share/sessionkit/src"

# Roots that other tools keep files in, or that hold more than the kit's.
SHARED = (
    "${HOME:?}",
    "${HOME:?}/",
    "${HOME:?}/.sessionkit",
    "${HOME:?}/.sessionkit/agents",
    "${HOME:?}/.sessionkit/mail",
    "${HOME:?}/.sessionkit/phone",
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
    "${HOME:?}/.cache/huggingface",
    "${HOME:?}/.cache/huggingface/hub",
    "${HOME:?}/.cache/uv",
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
    "${HOME:?}/.claude/plugins/cache",
    "${HOME:?}/.mail",
    "${HOME:?}/.session",
    "${HOME:?}/.session/agents",
    "${HOME:?}/Library",
    "${HOME:?}/Library/Caches",
    "${HOME:?}/Library/LaunchAgents",
    "${HOME:?}/Library/Logs",
    "${hub:?}",
    "${hub:?}/blobs",
)


def _section_8() -> str:
    """The short page: INSTALL.md section 8, to the end of the file's prose."""
    start = INSTALL_DOC.index("## 8. Uninstall")
    end = INSTALL_DOC.find("\n## 9. ", start)
    return INSTALL_DOC[start:end if end != -1 else None]


def _ref() -> str:
    return UNINSTALL_DOC


def _part_a() -> str:
    """The reference's program part: its sections 1 and 2, steps 1 to 6."""
    return _ref().split(PART_B, 1)[0]


def _part_b() -> str:
    """The reference's data part, its section 3."""
    return _ref().split(PART_B, 1)[1].split(CACHES, 1)[0]


def _caches() -> str:
    return _ref().split(CACHES, 1)[1].split(STAYS, 1)[0]


def _stays() -> str:
    return _ref().split(STAYS, 1)[1]


def _both() -> str:
    return _section_8() + "\n" + _ref()


def _rm_commands(text: str) -> list[tuple[str, list[str]]]:
    """Every `rm` in TEXT, as (flags, arguments), the arguments unquoted."""
    found = []
    for line in text.splitlines():
        for match in re.finditer(r"\brm (-[rf]+) ([^`#\n;]+)", line):
            args = re.findall(r'"[^"]*"\S*|\S+', match.group(2).strip())
            found.append((match.group(1), args))
    return found


def _steps(part: str) -> list[str]:
    """The program part's numbered steps, each from its bold `**N.` to the next."""
    return re.split(r"\n(?=\*\*\d+\. )", part)[1:]


def _step(n: int) -> str:
    return next(s for s in _steps(_part_a()) if s.startswith(f"**{n}. "))


def _blocks(text: str) -> list[str]:
    """Every ```bash block in TEXT, each line stripped of its indent."""
    return ["\n".join(line.strip() for line in block.splitlines()) + "\n"
            for block in re.findall(r"```bash\n(.*?)\n\s*```", text, re.DOTALL)]


def _seed(home: Path, files: tuple[str, ...]) -> None:
    for rel in files:
        path = home / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("x\n", encoding="utf-8")


def _run(home: Path, script: str, shell: str = "bash") -> subprocess.CompletedProcess:
    env = {"HOME": str(home), "PATH": os.environ.get("PATH", "/usr/bin:/bin"), "LC_ALL": "C"}
    argv = [shell, "-f", "-c"] if shell == "zsh" else [shell, "-c"]
    return subprocess.run([*argv, script], env=env, cwd=home,
                          capture_output=True, text=True, timeout=30, check=False)


def _files(home: Path) -> set[str]:
    return {str(p.relative_to(home)) for p in home.rglob("*") if p.is_file() or p.is_symlink()}


def _part_b_item(name: str) -> str:
    """One `### NAME` item of the data part, to the next heading."""
    return re.split(r"\n#{2,3} ", _part_b().split(f"\n### {name}\n", 1)[1], maxsplit=1)[0]


def _cache_item(name: str) -> str:
    return re.split(r"\n#{2,3} ", _caches().split(f"\n### {name}", 1)[1], maxsplit=1)[0]


def _part_b_block(name: str) -> str:
    return "".join(_blocks(_part_b_item(name)))


# --- The short page -------------------------------------------------------


def test_section_8_is_three_short_blocks_in_order():
    section = _section_8()
    heads = re.findall(r"^### .+$", section, re.MULTILINE)
    assert tuple(heads) == SHORT_BLOCKS, heads
    # Short: the owner asked for a shorter section. The old one ran ~525 lines.
    assert len(section.splitlines()) < 170, len(section.splitlines())
    assert section.startswith("## 8. Uninstall\n\n**NOT YET** as a whole")


def test_section_8_links_every_block_to_the_reference():
    section = _section_8()
    targets = set(re.findall(r"^\[uninstall-[\w-]+\]: (\S+)$", section, re.MULTILINE))
    assert "docs/uninstall.md" in targets
    anchors = {t.split("#", 1)[1] for t in targets if "#" in t}
    for anchor in ("1-stop-and-remove-the-jobs", "2-remove-the-plugins-and-the-tool",
                   "accounts", "mail", "session-records", "the-kits-home", "voice",
                   "phone", "your-clones", "4-caches-and-tools-other-programs-share-opt-in",
                   "5-what-stays"):
        assert anchor in anchors, anchor
    # Each anchor is a heading in the reference.
    heads = {re.sub(r"[^\w\- ]", "", h.lower()).replace(" ", "-")
             for h in re.findall(r"^#{1,3} (.+)$", UNINSTALL_DOC, re.MULTILINE)}
    assert anchors <= heads, anchors - heads
    # And every label used is defined.
    used = set(re.findall(r"\]\[(uninstall-[\w-]+)\]", section))
    defined = set(re.findall(r"^\[(uninstall-[\w-]+)\]:", section, re.MULTILINE))
    assert used == defined, used ^ defined


def test_the_reference_links_back_to_section_8():
    assert "\n[short]: ../INSTALL.md#8-uninstall\n" in UNINSTALL_DOC
    assert "[INSTALL.md section 8][short]" in UNINSTALL_DOC.split("\n## ", 1)[0]


def test_section_8_runs_the_jobs_then_the_plugins_and_tool():
    section = _section_8()
    jobs, tool, data = (section.index(h) for h in SHORT_BLOCKS)
    bot = section.index("  sessionphone bot uninstall\n")
    dry = section.index("  ears services uninstall --dry-run\n")
    voice = section.index("  ears services uninstall\n")
    market = section.index("  claude plugin marketplace remove sessionkit\n")
    kit = section.index("  uv tool uninstall sessionkit\n")
    assert jobs < bot < dry < voice < tool < market < kit < data
    # The data block has no command of its own: each item links to its lines.
    assert _blocks(section[data:]) == []


def test_section_8_names_both_safety_warnings_with_their_detail():
    flat = " ".join(_section_8().split())
    assert "⚠️ **Account tokens.** `~/.sessionkit/tools/accounts/`" in flat
    assert "[Accounts][uninstall-accounts]" in flat
    assert "⚠️ **VoiceMode shares some of these files**" in flat
    assert "Skip the lines marked \"No VoiceMode\"" in flat
    assert "**Only if you want it gone. This cannot be undone.**" in flat


def test_section_8_look_and_check_find_every_family_job():
    greps = re.findall(r"^ *launchctl list \| grep -E '([^']+)'$", _section_8(), re.MULTILINE)
    assert len(greps) == 2 and greps[0] == greps[1], greps
    assert greps[0].startswith("dev\\.sessionkit\\.|")
    for old in ("sessionvoice", "voicemode\\.ears", "sessionphone", "sessiontools"):
        assert old in greps[0], old


def test_section_8_leftovers_block_is_the_references_step_6():
    # The short page carries the same program leftovers, line for line.
    short = [b for b in _blocks(_section_8()) if ".cache/ears" in b]
    assert short == _blocks(_step(6)), short


def test_no_doc_recommends_wiping_the_mac():
    # Erasing the whole Mac (Erase All Content and Settings) was withdrawn as a step.
    for text in (_section_8(), UNINSTALL_DOC):
        flat = " ".join(text.split()).lower()
        assert "erase all content" not in flat
        assert "wipe" not in flat
        assert "factory reset" not in flat


def test_no_doc_offers_an_uninstall_verb_that_does_not_exist():
    for text in (_section_8(), UNINSTALL_DOC):
        assert "sessionkit uninstall" not in text


# --- ~/Library/Logs: never deleted (the owner's ruling) ---


def test_no_line_deletes_from_library_logs():
    for text in (_section_8(), UNINSTALL_DOC):
        for _, args in _rm_commands(text):
            assert not any("Library/Logs" in a for a in args), args
        for line in text.splitlines():
            if re.match(r"\s*(find|rmdir) ", line):
                assert "Library/Logs" not in line, line


def test_both_pages_say_the_old_logs_in_library_logs_stay():
    assert "The older logs in `~/Library/Logs`: an uninstall never deletes from there." in (
        " ".join(_section_8().split()))
    stays = " ".join(_stays().split())
    assert "**Old logs in `~/Library/Logs`.** An uninstall never deletes from there." in stays
    for old in ("`~/Library/Logs/ears/`", "`~/Library/Logs/sessiontools/`",
                "an older log folder from before the kit"):
        assert old in stays, old
    assert "`~/.sessionkit/<package>/log/`" in stays


# --- The reference: the program part ---------------------------------------


def test_part_a_removes_the_program_before_part_b_deletes_data():
    ref = _ref()
    for head in (PART_A, PART_A2, PART_B, CACHES, STAYS):
        assert ref.count(f"\n{head}\n") == 1, head
    assert ref.index(PART_A) < ref.index(PART_A2) < ref.index(PART_B) < ref.index(CACHES) \
        < ref.index(STAYS)


def test_the_data_part_is_opt_in_and_says_it_cannot_be_undone():
    assert _part_b().startswith("\n\n**Only if you want it gone. This cannot be undone.**")
    assert "Steps 1 to 6 kept all of it" in " ".join(_part_b().split())


def test_part_a_deletes_no_user_data():
    for data in (".mail/agents", ".session/", ".sessionphone", ".sessionview",
                 "Library/Logs", "heard_", ".sessionkit/", "sessionkit/src", ".sessionmail"):
        for _, args in _rm_commands(_part_a()) + _rm_commands(_section_8().split(SHORT_BLOCKS[2])[0]):
            assert not any(data in a for a in args), (data, args)


def test_reverse_order_service_verbs_then_plugins_then_data():
    ref = _ref()
    bot = ref.index("  sessionphone bot uninstall\n")
    voice = ref.index("  ears services uninstall\n")
    plugins = ref.index('    claude plugin marketplace remove "$r"\n')
    kit_plugins = ref.index("  claude plugin marketplace remove sessionkit\n")
    assert voice < kit_plugins < ref.index(PART_B)
    kit = ref.index("  uv tool uninstall sessionkit\n")
    data = ref.index(PART_B)
    assert bot < voice < min(plugins, kit) < data
    # The clones go only after the plugins that were installed from them.
    assert ref.index(f'rm -rf "{CLONES}"') > plugins


def test_the_off_path_verbs_come_before_step_5_removes_the_session_command():
    # `session pane-state agent off` needs the kit's `session`, which step 5's
    # `uv tool uninstall sessionkit` removes; read top to bottom, the reader
    # must meet the off verbs first.
    ref = _ref()
    off_path = ref.index("**Did you go off the install path?**")
    assert ref.index("**4. The voice") < off_path
    assert off_path < ref.index("**5. The plugins and the kit command")
    assert off_path < ref.index("  session pane-state agent off\n")
    # `off` alone keeps the engine binaries it built (PROGRAM files); only
    # `--purge` removes them (sessiontools sound/service.py `cmd_off`).
    assert off_path < ref.index("  session sound engine off --purge\n")
    # The default model's agent has no off verb: its bootout and plist, as
    # sessiontools' own README gives them.
    item = ref.split("- Loaded the default model's agent", 1)[1].split("\n- ", 1)[0]
    assert _blocks(item) == [(
        'launchctl bootout "gui/$(id -u)/dev.sessionkit.tools.default-model"\n'
        'rm -f "${HOME:?}/Library/LaunchAgents/dev.sessionkit.tools.default-model.plist"\n'
    )]
    assert off_path < ref.index("dev.sessionkit.tools.default-model\"") < ref.index(PART_A2)


def test_every_rm_on_a_variable_path_fails_loudly_when_it_is_empty():
    commands = _rm_commands(_both())
    assert len(commands) >= 20, commands
    for flags, args in commands:
        for arg in args:
            assert re.match(r'"\$\{[A-Za-z_]+:\?\}', arg), (flags, arg)
            assert "$" not in re.sub(r"\$\{[A-Za-z_]+:\?\}", "", arg), arg


def test_part_b_runs_no_rm_on_a_variable_the_reader_sets():
    # `"${SRC:?}"` stops an empty SRC, not SRC=~/Code: a variable the reader
    # sets, or one their profile already set, can name any folder they own.
    part_b = _part_b()
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


def test_the_caches_run_rm_only_on_what_the_doc_binds_from_home():
    # The speech weights' lines bind `hub` from HOME, `m` to their own list,
    # and `b` to each path realpath printed under the hub's blobs folder.
    block = _blocks(_cache_item("The speech weights"))[0]
    assert block.startswith('hub=$(realpath "${HOME:?}/.cache/huggingface/hub")\n')
    for _, args in _rm_commands(_caches()):
        for arg in args:
            used = set(re.findall(r"\$\{?([A-Za-z_]\w*)", arg))
            assert used <= {"HOME", "hub", "m", "b"}, (arg, used)


def test_part_b_deletes_the_clones_by_section_3s_literal_path():
    # The folder is the one section 3's loop clones into, spelled out.
    section_3 = INSTALL_DOC.split("## 3. Install the plugins", 1)[1].split("\n## 4. ", 1)[0]
    src = re.search(r"^SRC=(\S+)", section_3, re.MULTILINE).group(1)
    assert src == "~/.local/share/sessionkit/src"
    assert CLONES == src.replace("~", "${HOME:?}", 1)
    part_b = _part_b()
    assert f'rm -rf "{CLONES}"' in part_b
    assert part_b.index(f'rm -rf "{CLONES}"') < part_b.index(
        'rmdir "${HOME:?}/.local/share/sessionkit"')


KIT_HOME = "${HOME:?}/.sessionkit"
# The packages whose folders under the kit's home hold only what the kit
# wrote: their settings, logs and state go whole. phone is among them (the
# walk found phone/settings/phone.json left, so `rmdir ~/.sessionkit` failed).
WHOLE = ("mail", "voice", "view", "phone")
# Each package's folders under the kit's home: the tree spec's settings/,
# and log/ and state/ beside it (the 0.3.2 log moves).
KINDS = ("settings", "log", "state")
# tools/settings also holds claude-code.json, which `session start` reads and
# nothing in the kit writes: the data part removes only the session and sounds
# files there, and what `session statusline install` wrote.
TOOLS_SETTINGS = f"{KIT_HOME}/tools/settings"
# What `session statusline install` writes in tools/settings (sessiontools'
# statusline module: the script, and the drop-in it owns whole), each with a
# `<name>.bak-<date>-<time>` copy beside any file it replaced.
STATUSLINE = ("statusline.sh", "claude-code.d/50-statusline.json")
# The `session` tool's account folder beside tools/settings (the tree spec;
# sessiontools' settings.accounts_dir). Its backups hold account tokens, so
# the data part deletes it only as an item of its own, by its literal path.
ACCOUNTS = f"{KIT_HOME}/tools/accounts"
# The account folder from before it moved into the kit's home (sessiontools'
# registry.OLD_ACCOUNTS_SUBDIR). The kit never writes it, but a host that used
# `session account` before the move may still hold its token backups there.
OLD_ACCOUNTS = "${HOME:?}/.config/sessiontools"
HOME_ITEM = "The kit's home"
WHOLE_LOOP = re.compile(r"for d in ([\w ]+); do rm -rf ((?:\"\$\{HOME:\?\}/\.sessionkit/\$\{d:\?\}/\w+\" ?)+); done")


def _kit_home_rm_args() -> list[str]:
    return [a.replace('"', "") for _, args in _rm_commands(_part_b()) for a in args
            if a.replace('"', "").startswith(KIT_HOME)]


def test_part_b_removes_each_packages_settings_log_and_state_never_its_folder():
    loop = WHOLE_LOOP.search(_part_b())
    assert loop, _part_b()[:60]
    assert tuple(loop.group(1).split()) == WHOLE
    kinds = re.findall(r"\$\{d:\?\}/(\w+)\"", loop.group(2))
    assert tuple(kinds) == KINDS
    assert "tools" not in loop.group(1).split()
    # tools' logs go on their own line; tools' folder is never removed whole.
    assert f'rm -rf "{KIT_HOME}/tools/log"' in _part_b()


def test_part_b_leaves_settings_nothing_in_the_kit_writes():
    part_b = _part_b()
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
    flat = " ".join(part_b.split())
    assert "All of these leave `claude-code.json` there alone" in flat
    assert "nothing in the kit writes it" in flat


def test_part_b_kit_home_lines_stay_inside_a_packages_own_folders():
    # The one rm under the kit's home outside settings/log/state is the
    # Accounts item's, by its literal path (pinned below).
    args = [a for a in _kit_home_rm_args() if a != ACCOUNTS]
    assert args, "no rm under the kit's home"
    for arg in args:
        assert re.match(r"\$\{HOME:\?\}/\.sessionkit/(\w+|\$\{d:\?\})/(settings|log|state)(/|$)", arg), arg


def test_no_rm_deletes_a_shared_root_whole():
    for _, args in _rm_commands(_both()):
        for arg in args:
            path = arg.replace('"', "").rstrip("/")
            assert path not in SHARED, arg


def test_shared_roots_are_only_ever_rmdired():
    part_b = _part_b()
    for root in ("${HOME:?}/.mail", "${HOME:?}/.session", "${HOME:?}/.session/agents", KIT_HOME):
        assert f'rmdir "{root}"' in part_b
    assert f'rmdir "{KIT_HOME}/tools/settings"' in part_b
    assert f'for d in mail voice view phone tools; do rmdir "{KIT_HOME}/${{d:?}}"; done' in part_b


def test_part_b_rmdirs_no_folder_its_own_rm_already_removed():
    # Each package's settings/log/state go with `rm -rf`; an rmdir of any
    # would print `No such file or directory` on every run.
    part_b = _part_b()
    for d in WHOLE:
        for kind in KINDS:
            assert f'rmdir "{KIT_HOME}/{d}/{kind}"' not in part_b, (d, kind)
    assert 'rmdir "${HOME:?}/.sessionkit/${d:?}/settings"' not in part_b


def test_part_b_deletes_the_notmuch_index_only_when_mail_setup_made_it():
    # Mail setup adopts no notmuch database: on a mail folder that already holds
    # `.notmuch` it writes no profile and says MANUAL. That database is the
    # reader's, so the data part never removes it in the same breath as the
    # boxes: its rm is a line of its own, named for the one case it is the kit's.
    mail = _part_b_item("Mail")
    flat = " ".join(mail.split())
    index = '"${HOME:?}/.mail/.notmuch"'
    lines = [line.strip() for line in mail.splitlines() if re.match(r"\s*(rm|rmdir) ", line)]
    [own] = [line for line in lines if index in line]
    assert own == f"rm -rf {index}"
    assert 'rm -rf "${HOME:?}/.mail/agents/mouth"' in lines
    before = flat.split(" ".join(own.split()), 1)[0]
    assert "Delete it only if mail setup made the profile for it" in before
    # Each answer of the profile line is its own labelled bullet, and the
    # block sits under the one that deletes (the family command rule).
    assert "Mail setup's first run said which, on its `notmuch-profile` line" in flat
    assert "- It said `MANUAL`: the database was in the mail folder before the kit" in flat
    assert "- You cannot tell: leave it." in flat
    # Mail setup runs the profile's first `notmuch new` itself, so the reader
    # ran none: the bullet says setup did.
    assert "- It said `wrote`: mail setup then ran `notmuch new` once on that profile" in before
    assert "you then ran section 5's `notmuch new`" not in flat
    assert before.rindex("- It said `wrote`") > before.rindex("- You cannot tell")
    # The mail folder's rmdir comes after the index line, so it can empty it.
    assert lines.index(own) < lines.index('rmdir "${HOME:?}/.mail"')


def test_part_b_explains_each_message_its_rmdir_lines_print():
    # A package the reader never set up (voice, before section 5) has no
    # folder, so its rmdir says `No such file or directory`; one that holds
    # files the kit did not write says `Directory not empty`. Both are named.
    item = _part_b_item(HOME_ITEM)
    assert "`Directory not empty`" in item
    assert "`No such file or directory`" in item
    assert "the phone none until section 6" in " ".join(item.split())


def test_part_b_removes_the_view_settings_in_the_kits_home_not_the_old_one():
    # sessionview's settings moved from its own folder in the home directory
    # to the kit's; the data part removes them with the other packages'.
    # test_configuration_docs scans every file for the old home.
    for _, args in _rm_commands(_both()):
        for arg in args:
            assert ".sessionview" not in arg, arg
    assert "the sidebar's config and state" in _part_b_item(HOME_ITEM)


# The sidebar's old state folder, and the older name it was moved from.
VIEW_STATE = "${HOME:?}/.local/state/sessionview"
OLD_VIEW_STATE = "${HOME:?}/.local/state/herd"


def test_part_a_removes_the_sidebars_old_state_by_its_name_then_its_older_one():
    step_6 = _step(6)
    removed = [line.strip() for line in step_6.splitlines() if line.startswith("rm -rf ")]
    new, old = f'rm -rf "{VIEW_STATE}"', f'rm -rf "{OLD_VIEW_STATE}"'
    assert new in removed and old in removed, removed
    assert removed.index(new) < removed.index(old), removed
    flat = " ".join(step_6.split())
    # Its state is in the kit's home now; the old folder is an upgrade's.
    assert "The sidebar keeps its state in the kit's home now, `~/.sessionkit/view/state`" in flat
    assert "Its older folder, `~/.local/state/sessionview`, is there only on a Mac that ran an earlier release" in flat
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
    # the reader's own. The program part names them and leaves the deleting
    # to the data part.
    off_path = _ref().split("**Did you go off the install path?**", 1)[1].split(PART_A2, 1)[0]
    item = off_path.split("- `session statusline install`:", 1)[1].split("\n- `", 1)[0]
    for name in STATUSLINE:
        assert f"`{name}`" in item, name
    assert "`.bak-<date>-<time>`" in item and "move it back" in item
    assert "leaves\n  `claude-code.json` alone" in item
    # The program part deletes no user data: the files go with the kit's home.
    assert "so [the kit's home][home] deletes them" in item
    assert not _rm_commands(item) and not _statusline_undo_lines(item)
    assert "claude-code.json` by hand" not in _ref()


def test_part_b_also_removes_what_statusline_install_wrote():
    _assert_undoes_the_statusline(_part_b())


# The Mail item's one find: every box but the mouth's, which VoiceMode shares.
MAIL_ALL_BUT_MOUTH = (
    'find "${HOME:?}/.mail/agents" -mindepth 1'
    ' -not -path "${HOME:?}/.mail/agents/mouth"'
    ' -not -path "${HOME:?}/.mail/agents/mouth/*" -delete'
)
# Session records: the agent files setup wrote (and any the reader wrote) in
# the fresh-Mac agents folder; never the links an older host keeps there.
AGENT_FILES = 'find "${HOME:?}/.session/agents" -maxdepth 1 -type f -name \'*.md\' -delete'
# The speech weights: only empty folders left in the hub's blobs folder.
EMPTY_BLOB_DIRS = 'find "${hub:?}/blobs" -mindepth 1 -type d -empty -delete'


def test_every_find_that_deletes_is_one_the_tests_pin():
    for line in _both().splitlines():
        if re.match(r"\s*find ", line) and "-delete" in line:
            line = line.strip()
            if line in (MAIL_ALL_BUT_MOUTH, AGENT_FILES, EMPTY_BLOB_DIRS):
                continue
            assert line.startswith(f'find "{TOOLS_SETTINGS}" '), line


# Every file the kit's packages may leave under ~/.sessionkit, as the kit's
# home block sees them: seeded into a temp HOME and run for real.
KIT_FILES = (
    "mail/settings/mail.json",
    "voice/settings/ears.json", "voice/settings/mouth.json",
    "voice/settings/tts.key", "voice/settings/stt.key",
    "voice/log/ears-keeper.log", "voice/log/install.log", "voice/log/mlx-audio/server.log",
    "view/settings/view.json", "view/settings/neomuttrc",
    "view/settings/config.json.before-a",
    "view/state/recent.tsv", "view/state/mutt/box.rc", "view/log/sessionview.log",
    "phone/settings/phone.json", "phone/settings/phone.d/10-bot.json",
    "phone/log/claude/bot.log", "phone/log/claude/bot.launchd.log",
    "tools/log/pane-state.log", "tools/log/reap.log",
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


def _run_kit_home(home: Path, files: tuple[str, ...], script: str | None = None
                  ) -> subprocess.CompletedProcess:
    for rel in files:
        path = home / ".sessionkit" / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("x\n", encoding="utf-8")
    return _run(home, _part_b_block(HOME_ITEM) if script is None else script)


def _left(home: Path) -> set[str]:
    kit = home / ".sessionkit"
    return {str(p.relative_to(kit)) for p in kit.rglob("*") if p.is_file()} if kit.exists() else set()


def test_part_b_kit_home_block_run_in_a_temp_home_removes_every_kit_file(tmp_path):
    done = _run_kit_home(tmp_path, KIT_FILES)
    assert not (tmp_path / ".sessionkit").exists(), (_left(tmp_path), done.stderr)
    assert done.stderr == "", done.stderr


def test_part_b_kit_home_block_run_in_a_temp_home_keeps_the_readers_files(tmp_path):
    done = _run_kit_home(tmp_path, KIT_FILES + READER_FILES)
    assert _left(tmp_path) == set(READER_FILES), done.stderr
    # Only the `Directory not empty` the text explains, once per kept folder.
    errors = [line for line in done.stderr.splitlines() if line]
    assert errors and all("Directory not empty" in line for line in errors), errors
    assert len(errors) == 4, errors   # claude-code.d, tools/settings, tools, .sessionkit


def test_part_b_kit_home_removes_the_phones_settings(tmp_path):
    # The walk: phone/settings/phone.json stayed, and `rmdir ~/.sessionkit` failed.
    done = _run_kit_home(tmp_path, ("phone/settings/phone.json", "tools/settings/session.json"))
    assert not (tmp_path / ".sessionkit").exists(), (_left(tmp_path), done.stderr)
    errors = [line for line in done.stderr.splitlines() if line]
    # mail, voice and view were never set up here: their rmdir says so.
    assert errors and all("No such file or directory" in line for line in errors), errors


# What `session account` keeps in its folder (sessiontools 66d2454: the
# registry, status's config, use's ledger and both backup folders).
ACCOUNT_FILES = (
    "tools/accounts/accounts.json", "tools/accounts/account-config.json",
    "tools/accounts/host-ledger.jsonl",
    "tools/accounts/token-file-backups/20300609T000000Z.token",
    "tools/accounts/keychain-backups/20300609T000000Z.json",
)


def test_part_b_names_the_account_folder_and_warns_before_its_one_line():
    # The uninstall used to leave tools/accounts/ (account token backups) on
    # disk without a word. The data part names it, says the program part and
    # the kit's home leave it, warns that its line deletes the token backups,
    # and lets the reader skip.
    item = _part_b_item("Accounts")
    flat = " ".join(item.split())
    assert "`~/.sessionkit/tools/accounts/`" in flat
    for name in ("accounts.json", "account-config.json", "host-ledger.jsonl",
                 "token-file-backups/", "keychain-backups/"):
        assert f"`{name}`" in flat, name
    assert "never the token" in flat
    assert "**The backups are your account tokens.**" in flat
    assert "Steps 1 to 6 leave this folder, and so does [the kit's home][home] below" in flat
    assert "the uninstall leaves these tokens on disk until you run this line" in flat
    assert "cannot be undone: to keep your accounts, skip it" in flat
    assert [line.strip() for line in item.splitlines() if re.match(r"\s*(rm|rmdir|find) ", line)] \
        == [f'rm -rf "{ACCOUNTS}"',
            f'rm -rf "{OLD_ACCOUNTS}"']
    # The kit's home points at it, and at the tree spec that puts it beside settings/.
    home = " ".join(_part_b_item(HOME_ITEM).split())
    assert "`openspec/specs/tree/spec.md`" in home
    assert (ROOT / "openspec/specs/tree/spec.md").is_file()
    assert "The account folder beside its settings is the item above" in home
    assert "or the account folder you kept" in home


def test_part_b_deletes_the_account_folder_before_the_kit_home_rmdirs_run():
    # So the kit's home item's rmdir lines can empty tools/ and ~/.sessionkit.
    part_b = _part_b()
    assert part_b.index(f'rm -rf "{ACCOUNTS}"') < part_b.index(f"\n### {HOME_ITEM}\n")
    assert "Accounts comes before the kit's home" in " ".join(part_b.split())
    # The program part deletes nothing under the account folder.
    assert not any("accounts" in a for _, args in _rm_commands(_part_a()) for a in args)


def test_part_b_accounts_then_kit_home_in_a_temp_home_removes_the_kits_home(tmp_path):
    script = _part_b_block("Accounts") + _part_b_block(HOME_ITEM)
    done = _run_kit_home(tmp_path, KIT_FILES + ACCOUNT_FILES, script)
    assert not (tmp_path / ".sessionkit").exists(), (_left(tmp_path), done.stderr)
    assert done.stderr == "", done.stderr


def test_part_b_kit_home_alone_keeps_the_account_folder(tmp_path):
    # A reader who skips Accounts keeps every account file; the only noise is
    # the `Directory not empty` the item explains, for tools/ and ~/.sessionkit.
    done = _run_kit_home(tmp_path, KIT_FILES + ACCOUNT_FILES)
    assert _left(tmp_path) == set(ACCOUNT_FILES), done.stderr
    errors = [line for line in done.stderr.splitlines() if line]
    assert len(errors) == 2 and all("Directory not empty" in line for line in errors), errors


def test_every_step_says_measured_or_not_yet():
    steps = _steps(_part_a())
    assert [s.split(".", 1)[0] for s in steps] == [f"**{n}" for n in range(1, 7)]
    for step in steps:
        assert "**MEASURED**" in step or "**NOT YET" in step, step[:60]
    assert "**NOT YET**: none of these lines has run" in " ".join(_part_b().split())
    assert "**NOT YET**: no walk has run these lines." in " ".join(_caches().split())
    assert _ref().split("\n## ", 1)[0].count("**NOT YET** as a whole") == 1
    for block in _section_8().split("\n### ")[1:]:
        assert "**MEASURED**" in block or "**NOT YET" in block, block[:60]


def test_the_for_loops_name_the_five_children():
    loops = re.findall(r"^ *for r in (.*?); do$", _ref(), re.MULTILINE)
    assert len(loops) == 3, loops   # the marketplaces, their cached copies, the clones
    for loop in loops:
        assert sorted(loop.split()) == sorted(cli.FAMILY)


# The kit floors sessionvoice at 0.2.0 or later, whose uninstall honours
# --dry-run (measured on a temporary home), so 0.1.0's no-dry-run warning goes.
def test_the_voice_uninstall_offers_its_dry_run_first():
    ref = _ref()
    flat = " ".join(ref.split())
    assert "has no dry run" not in ref
    assert ("**Look first with `--dry-run`.** This names each job it would boot out and each "
            "plist it would delete, and changes nothing: ```bash ears services uninstall "
            "--dry-run ```") in flat
    # The look comes before the run it looks at.
    assert ref.index("  ears services uninstall --dry-run\n") < ref.index(
        "  ears services uninstall\n")
    assert "printed `dry run: nothing booted out, nothing deleted`, and exited 0" in flat
    assert "`launchctl` acts on your own user's jobs whatever `HOME` says" in flat
    assert "`ears services status` only reads too" in flat


def test_the_voice_uninstall_uses_the_kits_own_ears():
    ref = _ref()
    flat = " ".join(ref.split())
    assert ("**The voice jobs.** This is the kit's own `ears`, the one that installed them "
            "(section 5 step 2): ```bash ears services uninstall ```") in flat
    assert "**On sessionvoice 0.1.0**" not in ref
    assert not re.search(r"bin/ears(?![-\w])", ref)
    assert "on 0.1.0, the plugin's" not in ref
    # 0.2.0's own are dev.sessionkit.voice.*; it retires both old forms.
    # The kit installs sessionvoice 0.3.0, read in its source for the same labels.
    assert (
        "0.3.0 knows its own labels, `dev.sessionkit.voice.*`, and both old forms it retires: "
        "`com.sessionvoice.*`, and the older `com.voicemode.ears-*` that 0.1.0 used "
        "(read in its 0.3.0 source"
    ) in flat
    assert "0.1.0 knows the older set only" not in flat
    # It unlinks plists only (sessionvoice services.py): no log is deleted.
    assert "It unlinks the plists only: it deletes no log." in flat


def test_the_reference_has_no_0_1_0_branches_left():
    flat = " ".join(_ref().split())
    assert "printed `Uninstalled 14 executables`" in flat
    assert "Uninstalled 9 executables" not in flat
    assert "(sessionphone 0.2.1)" in flat
    assert "any on 0.1.0" not in flat
    assert "newer than 0.1.0" not in flat


def test_the_kept_marketplace_line_is_still_the_plugin_step():
    # The reference keeps section 3's marketplace remove as its plugin step, as
    # test_readme.py's README/INSTALL.md agreement tests expect.
    step_5 = _step(5)
    assert step_5.startswith("**5. The plugins and the kit command")
    assert ("for r in sessionmail sessiontools sessionphone sessionvoice sessionview; do\n"
            '    claude plugin marketplace remove "$r"\n'
            "  done\n") in step_5


# A kit install (section 3's first lines) has ONE marketplace, `sessionkit`,
# and caches all six copies under cache/sessionkit/; the clones route has one
# marketplace and one cache folder per child. Step 5 gives each route its own
# lines, so a kit-route reader no longer misses cache/sessionkit/.
KIT_CACHE_BLOCK = 'rm -rf "${HOME:?}/.claude/plugins/cache/sessionkit"\nclaude plugin list\n'
CLONES_CACHE_BLOCK = (
    "for r in sessionmail sessiontools sessionphone sessionvoice sessionview; do\n"
    'rm -rf "${HOME:?}/.claude/plugins/cache/${r:?}"\n'
    "done\nclaude plugin list\n"
)


def test_step_5_removes_the_kits_marketplace_for_a_kit_install():
    step_5 = _step(5)
    flat = " ".join(step_5.split())
    assert ("- From the kit's marketplace (section 3's first lines). This removes its six "
            "plugins too: ```bash claude plugin marketplace remove sessionkit ```") in flat
    assert "Run the lines for your route, and both sets if you used both." in flat
    # The clones route keeps its per-child marketplace remove.
    assert "- From your own clones (section 3's" in flat
    assert "This removes each of the five marketplaces, and its plugin too" in flat
    assert "[From your own clones][clones-route]" in step_5
    assert ("\n[clones-route]: ../INSTALL.md#from-your-own-clones-to-work-on-the-plugins-optional\n"
            in UNINSTALL_DOC)
    assert "### From your own clones, to work on the plugins (optional)\n" in INSTALL_DOC


def test_step_5_deletes_the_kits_cache_folder_and_each_clones_own():
    step_5 = _step(5)
    blocks = [block for block in _blocks(step_5) if "plugins/cache" in block]
    assert blocks[0] == KIT_CACHE_BLOCK
    assert blocks[1] == CLONES_CACHE_BLOCK
    assert len(blocks) == 2
    # Each block sits under the route it is for.
    kit = step_5.index("From the kit's marketplace, all six copies are in one folder")
    clones = step_5.index("From your own clones, each plugin's copy is in a folder of its own")
    assert kit < step_5.index(KIT_CACHE_BLOCK.splitlines()[0]) < clones
    # The folder named is the one section 3 says a kit install copies to.
    assert "`~/.claude/plugins/cache/sessionkit/<name>/<version>/`" in INSTALL_DOC
    assert "`~/.claude/plugins/cache/sessionkit/`:" in step_5
    # The short page carries the kit route's cache line under its marketplace line.
    assert ('  claude plugin marketplace remove sessionkit\n'
            '  rm -rf "${HOME:?}/.claude/plugins/cache/sessionkit"\n') in _section_8()


def test_step_5_kit_cache_line_in_a_temp_home_removes_only_the_kits_copies(tmp_path):
    names = ("sessionkit", *cli.FAMILY)
    kit = tuple(f".claude/plugins/cache/sessionkit/{n}/0.2.1/{f}"
                for n in names for f in (".orphaned_at", ".claude-plugin/plugin.json"))
    theirs = (".claude/plugins/cache/other/other/1.0.0/plugin.json",
              ".claude/plugins/cache/sessionmail/sessionmail/0.2.1/.orphaned_at",
              ".claude/plugins/installed_plugins.json", ".claude/settings.json")
    _seed(tmp_path, kit + theirs)
    rm_lines = "".join(line + "\n" for line in KIT_CACHE_BLOCK.splitlines() if line.startswith("rm "))
    done = _run(tmp_path, rm_lines)
    assert done.returncode == 0 and done.stderr == "", done.stderr
    assert _files(tmp_path) == set(theirs)
    assert (tmp_path / ".claude/plugins/cache").is_dir()


def test_step_5_clones_loop_in_a_temp_home_removes_only_the_five_copies(tmp_path):
    five = tuple(f".claude/plugins/cache/{r}/{r}/0.2.1/.orphaned_at" for r in cli.FAMILY)
    theirs = (".claude/plugins/cache/sessionkit/sessionkit/0.2.1/.orphaned_at",
              ".claude/plugins/cache/other/other/1.0.0/plugin.json")
    _seed(tmp_path, five + theirs)
    assert CLONES_CACHE_BLOCK in _blocks(_step(5))
    loop = CLONES_CACHE_BLOCK.replace("claude plugin list\n", "")
    done = _run(tmp_path, loop)
    assert done.returncode == 0 and done.stderr == "", done.stderr
    assert _files(tmp_path) == set(theirs)


def test_step_5_kit_route_is_measured_and_names_what_stayed():
    flat = " ".join(_step(5).split())
    assert ("**MEASURED** (Claude Code 2.1.307, the kit's marketplace at 0.2.1, "
            "on a temporary home directory and Claude Code config directory)") in flat
    assert "printed `Also uninstalled 6 plugins from this marketplace`" in flat
    assert "**The six copies stayed** in `~/.claude/plugins/cache/sessionkit/`" in flat
    assert "marked `.orphaned_at`" in flat
    assert "These two lines then ran: the `rm` exited 0" in flat
    # The clones loop's own walk has not run, and still says so.
    assert "**NOT YET**: the loop has not run." in flat
    # Remove-by-name names each route's plugin id.
    assert ("`<name>@sessionkit` from the kit's marketplace, with `sessionkit@sessionkit` "
            "among them, and `<r>@<r>` from a clone") in flat


# The walk: step 4's `find` listed uv's own four links to the kit's
# sessionview commands on a fresh Mac. The line now leaves out every link into
# uv's tool folder, wherever it is run.
SV_FIND = "find ~/.local/bin -type l -lname '*sessionview*' -not -lname '*/uv/tools/*'\n"
UV_LINKS = ("sessionview", "sessionview-config", "sessionview-session", "sessionview-messages")
CHECKOUT_LINKS = ("sessionview-install", "sessionview-frame", "sessionview-app-install",
                  "tmux-sidebar", "sessionview-send")


def test_sessionviews_links_line_leaves_out_uvs_own():
    step_5 = _step(5)
    assert _blocks(step_5.split("**sessionview's own links and app**", 1)[1])[0] == SV_FIND
    flat = " ".join(step_5.split())
    assert "It leaves out every link into uv's tool folder" in flat
    assert "Four of those are sessionview's commands" in flat
    # It comes after the kit command, whose uninstall removes uv's four.
    assert step_5.index("  uv tool uninstall sessionkit\n") < step_5.index(SV_FIND.strip())


@pytest.mark.parametrize("shell", ["bash", "zsh"])
def test_sessionviews_links_line_in_a_temp_home_lists_only_the_checkouts(tmp_path, shell):
    if shutil.which(shell) is None:
        pytest.skip(f"no {shell}")
    uv = tmp_path / ".local/share/uv/tools/sessionkit/bin"
    checkout = tmp_path / "Code/sessionview/bin"
    bin_dir = tmp_path / ".local/bin"
    for d in (uv, checkout, bin_dir):
        d.mkdir(parents=True)
    for name in UV_LINKS:
        (uv / name).write_text("x\n")
        (bin_dir / name).symlink_to(uv / name)
    for name in CHECKOUT_LINKS:
        (checkout / name).write_text("x\n")
        (bin_dir / name).symlink_to(checkout / name)
    (bin_dir / "claude").symlink_to("/usr/bin/true")
    done = _run(tmp_path, SV_FIND, shell)
    assert done.stderr == "", done.stderr
    assert {Path(line).name for line in done.stdout.splitlines()} == set(CHECKOUT_LINKS)


def test_the_voice_jobs_check_says_to_wait_for_jobs_still_exiting():
    # Run at once, the check still lists jobs that are exiting; they clear
    # a few seconds later.
    check = _step(4).split("- **Check.**", 1)[1].split("\n- **", 1)[0]
    flat = " ".join(check.split())
    assert "Wait a few seconds before you run it" in flat
    assert "It printed a line? Wait a few seconds and run it again, until it prints nothing" in flat
    assert "Wait a few seconds, then run the look again" in " ".join(_section_8().split())


def test_the_ride_along_hook_says_how_to_remove_its_empty_folder():
    # The walk found an empty `.claude` left in the folder it launched from.
    hook = _step(4).split("- **The ride-along hook.", 1)[1].split("\n- **", 1)[0]
    assert _blocks(hook) == ["rmdir FOLDER/.claude\n"]
    flat = " ".join(hook.split())
    assert "the folder that holds that `.claude` in place of FOLDER" in flat
    assert "This removes it only if it is empty" in flat


# Program state the voice, mail, the sidebar and the phone leave outside the
# folders the data part names.
PROGRAM_STATE = (
    ".local/state/ears/call-ears/live", ".local/state/ears/call-ears/capture-1.log",
    ".local/state/ears/call-tap/LISTEN-OFF",
    ".cache/session-mail/ext/v1/stamp",
    ".local/state/audio/devices.json",
    ".cache/ears/silero_vad.onnx", ".cache/ears/run/keeper.pid",
    ".local/share/ears/speech/bin/python",
    ".local/state/sessionview/mutt/x", ".local/state/herd/x",
    "Library/Caches/imgtext-1a2b3c4d/com.apple.e5rt.e5bundlecache/x",
)
# Not the program's: user data the program part keeps, and other tools' files.
NOT_PROGRAM = (
    ".local/share/ears/speakers/me/voice.npy",
    ".local/state/claude/lock",
    ".local/state/other/x",
    ".cache/huggingface/hub/model",
    "Library/Caches/com.apple.Safari/x",
    "Library/Logs/ears/ears-keeper.log",
)


@pytest.mark.parametrize("shell", ["bash", "zsh"])
def test_part_a_step_6_removes_the_program_state(tmp_path, shell):
    if shutil.which(shell) is None:
        pytest.skip(f"no {shell}")
    [block] = _blocks(_step(6))
    _seed(tmp_path, PROGRAM_STATE + NOT_PROGRAM)
    done = _run(tmp_path, block, shell)
    assert _files(tmp_path) == set(NOT_PROGRAM), done.stderr
    assert done.stderr == "", done.stderr
    assert not (tmp_path / ".local/state/audio").exists()
    assert not list((tmp_path / "Library/Caches").glob("imgtext-*"))


def test_part_a_step_6_names_the_image_readers_cache():
    flat = " ".join(_step(6).split())
    assert "`~/Library/Caches/imgtext-<hash>`" in flat
    assert "the walk found it empty" in flat
    assert "the `imgtext-*` line prints `no matches found` when there is none" in flat


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


def test_what_stays_names_claude_codes_state_and_launch_agents_as_not_the_kits():
    flat = " ".join(_stays().split())
    assert "`~/.local/state/claude`: leave them" in flat
    # The walk found an empty ~/Library/LaunchAgents: macOS's, so it stays.
    assert "**`~/Library/LaunchAgents`.** macOS's own folder for every user job" in flat
    assert "Leave it." in flat


SESSION_SEED = (
    ".session/agent/config/x", ".session/seats/s/x", ".session/sessions/sid/mail/marks",
    ".session/sessions/sid/log/mail", ".session/mail/x", ".session/state/list/snapshot.json",
    ".session/state/pane-state/watch.lock", ".sessionmail/sessions/x",
    ".session/agents/claude.md",
)


def test_part_b_session_records_remove_the_session_lists_state_and_setups_agent(tmp_path):
    item = _part_b_item("Session records")
    [block] = _blocks(item)
    assert "for d in agent seats sessions mail state; do" in block
    assert AGENT_FILES in block
    _seed(tmp_path, SESSION_SEED)
    done = _run(tmp_path, block)
    assert _files(tmp_path) == set(), done.stderr
    assert not (tmp_path / ".session").exists()
    assert done.stderr == "", done.stderr


def test_part_b_session_records_name_the_agent_file_setup_wrote():
    # sessionkit setup writes NAME.md in ~/.session/agents when
    # ~/.session/agent/config is not a folder (setup.py agents_root): on a
    # fresh Mac, so the walk's `rmdir ~/.session` failed on claude.md.
    from sessionkit import setup

    assert (setup.SESSION_HOME, setup.AGENTS_DIR_NAME) == (".session", "agents")
    flat = " ".join(_part_b_item("Session records").split())
    assert "`sessionkit setup` (section 2) wrote one agent file, `NAME.md`" in flat
    assert "On a fresh Mac that folder is `~/.session/agents`" in flat
    assert "so copy any you want first" in flat


def test_part_b_session_records_leave_the_older_agents_links(tmp_path):
    item = _part_b_item("Session records")
    flat = " ".join(item.split())
    assert "`~/.session/agents` may also still hold a link for each agent" in flat
    assert "`Directory not empty`" in flat
    [block] = _blocks(item)
    (tmp_path / ".session/agents").mkdir(parents=True)
    (tmp_path / ".session/agents/someone").symlink_to(tmp_path / "elsewhere")
    (tmp_path / ".session/agents/claude.md").write_text("x\n")
    done = _run(tmp_path, block)
    assert _files(tmp_path) == {".session/agents/someone"}, done.stderr
    errors = [line for line in done.stderr.splitlines() if line]
    assert len(errors) == 2 and all("Directory not empty" in e for e in errors), errors


def test_part_b_session_records_on_a_host_with_no_agents_folder(tmp_path):
    # The text names the two `No such file or directory` lines, and they are all.
    flat = " ".join(_part_b_item("Session records").split())
    assert ("On a host with no `~/.session/agents`, the second and third lines print "
            "`No such file or directory`: that is fine.") in flat
    _seed(tmp_path, SESSION_SEED[:-1])
    done = _run(tmp_path, _blocks(_part_b_item("Session records"))[0])
    errors = [line for line in done.stderr.splitlines() if line]
    assert len(errors) == 2 and all("No such file or directory" in e for e in errors), errors
    assert not (tmp_path / ".session").exists()


# What sessionvoice writes on a fresh install: everything under its own home,
# ~/.sessionvoice, then ~/.ears and the speakers' home. Its services' logs are
# in ~/.sessionkit/voice/log (the kit's home item); the older ones in
# ~/Library/Logs/ears stay.
VOICE_FRESH = (
    ".sessionvoice/logs/conversations/heard_2030-06-09.jsonl",
    ".sessionvoice/logs/conversations/heard.lock",
    ".sessionvoice/logs/conversations/speakers_2030-06-09.jsonl",
    ".sessionvoice/state/heard-cursor/sid", ".sessionvoice/state/heard-cursor/sid.lock",
    ".sessionvoice/state/missed-reply/clip.wav",
    ".sessionvoice/audio/2030-06-09/120000-000-1.wav",
    ".sessionvoice/mouth/playing.json", ".sessionvoice/mouth/done/x",
    ".sessionvoice/mouth/audio/line.wav",
    ".sessionvoice/talk/token",
    ".ears/heard.state",
    ".local/share/ears/speakers/me/voice.npy",
)
# The files only sessionvoice writes, where an older sessionvoice kept them,
# in ~/.voicemode.
VOICE_LEGACY = (
    ".voicemode/logs/conversations/speakers_2030-06-09.jsonl",
    ".voicemode/talk/token",
    ".voicemode/state/missed-reply/clip.wav",
    ".voicemode/audio/2030-06-09/120000-000-1.wav",
)
# What VoiceMode writes too (its own heard log, the log's lock, its cursors
# and its mouth): deleted only on the reader's word.
VOICE_SHARED = (
    ".voicemode/logs/conversations/heard_2030-06-09.jsonl",
    ".voicemode/logs/conversations/heard.lock",
    ".voicemode/mouth/playing.json", ".voicemode/state/heard-cursor/sid",
)
# VoiceMode's own files, Claude Code's, and the old logs: never touched.
VOICEMODE_OWN = (
    ".voicemode/voicemode.env", ".voicemode/voices/a.pt", ".voicemode/services/whisper/x",
    ".voicemode/logs/conversations/exchanges_2030-06-09.jsonl",
    ".voicemode/audio/2030/06/20300609_120000_tts.wav", ".voicemode/audio/flat.wav",
    ".claude/heard.state.not-ours", ".local/state/claude/lock",
    "Library/Logs/ears/keeper.log",
)


def test_part_b_voice_deletes_the_heard_log_where_a_fresh_install_writes_it():
    item = _part_b_item("Voice")
    flat = " ".join(item.split())
    first = _blocks(item)[0]
    assert first.splitlines() == ['rm -rf "${HOME:?}/.sessionvoice" "${HOME:?}/.ears"',
                                  'rm -rf "${HOME:?}/.local/share/ears"']
    for named in ("`heard_*.jsonl`", "`speakers_*.jsonl`", "`talk/token`",
                  "every line the mouth spoke, which it keeps by default",
                  "If you turned recording on", "`~/.sessionvoice`", "`~/.ears`",
                  "`~/.sessionkit/voice/log/`"):
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
    # Each path is its own labelled bullet; the block sits under the one that deletes.
    before = flat.split(" ".join(shared.splitlines()[0].split()), 1)[0]
    assert "- You use VoiceMode: keep them. The lines below would delete VoiceMode's own" in before
    assert before.rstrip().endswith("- No VoiceMode: delete them: ```bash"), before[-80:]
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


def test_part_b_kit_home_says_the_voices_speech_keys_are_in_its_settings_folder():
    flat = " ".join(_part_b_item(HOME_ITEM).split())
    assert "`stt.key` and `tts.key`, in `~/.sessionkit/voice/settings/` itself" in flat
    assert "this item deletes them with your voice choices" in flat


def test_part_b_kit_home_names_the_new_log_folders():
    # The 0.3.2 log moves: each package logs to ~/.sessionkit/<package>/log/
    # (voice, phone, tools and view merged; mail's still to land). The item
    # deletes them; the older ones in ~/Library/Logs stay.
    flat = " ".join(_part_b_item(HOME_ITEM).split())
    assert "`log/` the package's logs" in flat
    assert "every package's logs" in flat
    assert "A Mac that ran an earlier release keeps its older logs in `~/Library/Logs`" in flat
    phone = " ".join(_part_b_item("Phone").split())
    assert "The bot's logs are in `~/.sessionkit/phone/log/`" in phone


def test_part_b_accounts_names_the_folder_from_before_the_move_and_warns(tmp_path):
    item = _part_b_item("Accounts")
    flat = " ".join(item.split())
    assert "`~/.config/sessiontools/`" in flat
    assert "**Its backups are your account tokens too.**" in flat
    assert "to keep those accounts, skip it" in flat
    assert "It leaves the rest of `~/.config` alone" in flat
    for _, args in _rm_commands(item):
        assert '"${HOME:?}/.config"' not in args, args
    # Each folder is its own block, so a reader who keeps one pastes only the other.
    blocks = _blocks(item)
    assert [b.strip() for b in blocks] == [f'rm -rf "{ACCOUNTS}"', f'rm -rf "{OLD_ACCOUNTS}"']
    block = blocks[1]
    kept = (".config/notmuch/sessionkit/config", ".config/other/x")
    _seed(tmp_path, (".config/sessiontools/accounts.json",
                     ".config/sessiontools/token-file-backups/20300609T000000Z.token") + kept)
    done = _run(tmp_path, block)
    assert done.stderr == "", done.stderr
    assert _files(tmp_path) == set(kept)


def test_no_uninstall_line_carries_a_comment():
    # In zsh, the Mac's own shell, a `#` typed at the prompt is a word, not a
    # comment (`interactivecomments` is off), so a pasted
    # `rm -rf "$x"   # the cache` also deletes `./the` and `./cache`. And a
    # comment's apostrophe opens a quote that swallows the next lines.
    for text in (_section_8(), _ref()):
        blocks = re.findall(r"```bash\n(.*?)\n\s*```", text, re.DOTALL)
        assert len(blocks) >= 8
        commented = [line.strip() for block in blocks for line in block.splitlines() if "#" in line]
        assert commented == [], commented
    assert "a `#` typed at the prompt is not a comment" in " ".join(_ref().split("\n## ", 1)[0].split())
    assert "in zsh a `#` typed at the prompt is not a comment" in " ".join(_section_8().split())


# --- Section 4 of the reference: the caches ---------------------------------

SPEECH_REPOS = ("mlx-community--parakeet-tdt-0.6b-v3", "mlx-community--Kokoro-82M-bf16",
                "prince-canuma--Kokoro-82M")


def test_the_speech_weights_lines_name_the_three_repos_and_never_the_whole_cache():
    item = _cache_item("The speech weights")
    [block] = _blocks(item)
    assert f"for m in {' '.join(SPEECH_REPOS)}; do" in block
    flat = " ".join(item.split())
    assert "Deleting those three folders is not enough." in flat
    assert "`models--NAME/blobs/<sha>` points to `../../blobs/<xx>/<sha256>`" in flat
    assert "The walk deleted the three folders and found the 2.7 GB still there." in flat
    assert "- Another tool uses them: leave them." in flat
    assert "- Nothing else uses them? These lines follow each link" in flat
    assert "Never delete the cache whole." in flat
    for _, args in _rm_commands(block):
        for arg in args:
            assert arg.replace('"', "") not in ("${hub:?}", "${hub:?}/blobs"), arg


def _hf_model(hub: Path, repo: str, shas: tuple[str, ...]) -> None:
    """A model folder in the shared-blob layout the walk measured:
    models--X/blobs/<sha> -> ../../blobs/<xx>/<sha>, and each snapshot file
    -> ../../blobs/<sha>."""
    model = hub / f"models--{repo}"
    (model / "blobs").mkdir(parents=True, exist_ok=True)
    (model / "snapshots/rev1").mkdir(parents=True, exist_ok=True)
    for sha in shas:
        blob = hub / "blobs" / sha[:2] / sha
        blob.parent.mkdir(parents=True, exist_ok=True)
        if not blob.exists():
            blob.write_text(f"{sha}\n")
        (model / "blobs" / sha).symlink_to(f"../../blobs/{sha[:2]}/{sha}")
        (model / "snapshots/rev1" / f"f-{sha}").symlink_to(f"../../blobs/{sha}")


@pytest.mark.parametrize("shell", ["bash", "zsh"])
def test_the_speech_weights_lines_in_a_temp_home_delete_only_the_three_models_blobs(tmp_path, shell):
    if shutil.which(shell) is None:
        pytest.skip(f"no {shell}")
    hub = tmp_path / ".cache/huggingface/hub"
    _hf_model(hub, SPEECH_REPOS[0], ("aa11", "aa12"))
    _hf_model(hub, SPEECH_REPOS[1], ("bb21", "cc31"))
    _hf_model(hub, SPEECH_REPOS[2], ("cc31", "dd41"))        # shares one blob with Kokoro
    _hf_model(hub, "other--model", ("ee51", "ff61"))
    # The older layout: the files sit in the model's own blobs folder.
    (hub / "models--classic/blobs").mkdir(parents=True)
    (hub / "models--classic/blobs/zz").write_text("zz\n")
    [block] = _blocks(_cache_item("The speech weights"))
    done = _run(tmp_path, block, shell)
    assert done.stderr == "", done.stderr
    left = {str(p.relative_to(hub)) for p in hub.rglob("*") if p.is_file() or p.is_symlink()}
    assert left == {
        "blobs/ee/ee51", "blobs/ff/ff61", "models--classic/blobs/zz",
        "models--other--model/blobs/ee51", "models--other--model/blobs/ff61",
        "models--other--model/snapshots/rev1/f-ee51", "models--other--model/snapshots/rev1/f-ff61",
    }, sorted(left)
    # No empty folder is left in blobs, and the other model's links still resolve.
    assert sorted(p.name for p in (hub / "blobs").iterdir()) == ["ee", "ff"]
    assert all(p.resolve().is_file() for p in (hub / "models--other--model").rglob("*") if p.is_symlink())


def test_the_speech_weights_lines_fail_loudly_with_no_cache(tmp_path):
    [block] = _blocks(_cache_item("The speech weights"))
    (tmp_path / "keep").write_text("x\n")
    done = _run(tmp_path, block)
    assert done.returncode != 0
    assert _files(tmp_path) == {"keep"}


def test_uvs_cache_and_pythons_are_each_a_labelled_choice():
    cache = " ".join(_cache_item("uv's cache").split())
    assert "- Other uv tools or projects on this Mac: leave it. `uv cache prune` does not free the kit's packages" in cache
    assert "```bash uv cache prune ```" not in cache
    assert "after step 5 the kit's packages are still pointed to" in cache
    assert _blocks(_cache_item("uv's cache")) == ["uv cache clean\n"]
    assert "- Nothing else of yours uses uv: this empties the cache: ```bash uv cache clean ```" in cache
    pythons = _cache_item("uv's Pythons")
    assert _blocks(pythons) == ["uv python uninstall 3.12\n", "uv python uninstall 3.14\n"]
    flat = " ".join(pythons.split())
    assert "sessionvoice builds them with `uv venv --python 3.12`" in flat
    assert "- Nothing else needs uv's Python 3.12? Remove it:" in flat


def test_homebrews_tools_are_each_a_labelled_choice():
    brew = _cache_item("Homebrew's tools")
    assert _blocks(brew) == [
        "brew uninstall tmux\n", "brew uninstall ffmpeg\n", "brew uninstall notmuch\n",
        "brew uninstall jq\n", "brew autoremove --dry-run\nbrew autoremove\n",
    ]
    flat = " ".join(brew.split())
    for tool in ("tmux", "ffmpeg", "notmuch"):
        assert f"- Nothing else uses {tool}? Remove it:" in flat, tool
    # Each tool the install asks Homebrew for is offered here.
    for tool in ("tmux", "ffmpeg", "notmuch", "jq"):
        assert f"brew install {tool}" in INSTALL_DOC, tool


# The mouth's queue, ~/.mail/agents/mouth, is ONE box for both mouths:
# sessionvoice's (src/mouth/box.py:117, inbox.py:34, maillog.py:52 at
# 6c849c8) and VoiceMode's (voice_mode/mouth/box.py:85, inbox.py:31 at
# e03b5d9). The Mail item deletes every other box, and the mouth's only on
# the reader's word that VoiceMode goes too, as the Voice item does.
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
    # Each path is its own labelled bullet; the block sits under the one that deletes.
    assert ("- You use VoiceMode: keep it. VoiceMode's mouth speaks from it, and the lines"
            " below would delete its queue") in flat
    assert "- No VoiceMode: the mouth's box is the kit's alone. Delete it: ```bash" in flat
    assert "stay in that box, beside VoiceMode's, until you delete it" in flat
    for name in ("`MOUTH_MAILBOX`", "`VOICEMODE_MOUTH_MAILBOX`", "`MOUTH_DIR`",
                 "`VOICEMODE_MOUTH_DIR`"):
        assert name in flat, name
    assert "The `rmdir` prints `Directory not empty`, and the folder stays, if you kept the mouth's box" in flat


@pytest.mark.parametrize("shell", ["bash", "zsh"])
def test_part_b_mail_in_a_temp_home_keeps_the_mouths_box_until_the_reader_chooses(tmp_path, shell):
    if shutil.which(shell) is None:
        pytest.skip(f"no {shell}")
    boxes, mouth, _index = _blocks(_part_b_item("Mail"))
    _seed(tmp_path, MAIL_BOXES + MOUTH_BOX + MAIL_KEPT)
    done = _run(tmp_path, boxes, shell)
    assert done.stderr == "", done.stderr
    assert _files(tmp_path) == set(MOUTH_BOX + MAIL_KEPT)
    assert sorted(p.name for p in (tmp_path / ".mail/agents").iterdir()) == ["mouth"]
    # The mouth's box goes only with the block the reader chooses.
    done = _run(tmp_path, mouth, shell)
    assert done.stderr == "", done.stderr
    assert _files(tmp_path) == set(MAIL_KEPT)
    assert not (tmp_path / ".mail/agents").exists()


# The whole uninstall on one temp HOME, as a reader pastes it: the reference's
# step 6, then every block of its data part in order, each block pasted on its
# own into an interactive shell whose cwd is HOME. The seed is the write-set
# of a fresh install with the 0.3.2 log moves, every path the kit's packages
# write there, plus files the kit never wrote and a file in the cwd for every
# word the reference uses (a `#` pasted at zsh's prompt hands its words to the
# command as paths). A reader who keeps VoiceMode skips each block under a
# "No VoiceMode:" bullet.
E2E_KIT = (
    ".sessionvoice/logs/conversations/heard_2030-12-08.jsonl",
    ".sessionvoice/logs/conversations/heard.lock",
    ".sessionvoice/logs/conversations/speakers_2030-12-08.jsonl",
    ".sessionvoice/state/heard-cursor/sid-1", ".sessionvoice/state/missed-reply/clip.wav",
    ".sessionvoice/audio/2030-12-08/101010-123-1.wav",
    ".sessionvoice/mouth/playing.json", ".sessionvoice/mouth/audio/line.wav",
    ".sessionvoice/talk/token", ".ears/heard.state",
    ".sessionkit/voice/settings/ears.json", ".sessionkit/voice/settings/stt.key",
    ".sessionkit/voice/log/ears-keeper.log", ".sessionkit/voice/log/install.log",
    ".cache/ears/silero_vad.onnx", ".cache/ears/run/keeper.pid",
    ".local/share/ears/speech/bin/python", ".local/share/ears/speakers/me.npy",
    ".local/state/ears/call-ears/live", ".local/state/ears/call-tap/LISTEN-OFF",
    ".local/state/audio/devices.json",
    "Library/Caches/imgtext-1a2b3c4d/x",
    ".mail/agents/operator/new/1", ".mail/agents/operator/cur/2:2,S",
    ".mail/agents/assistant-chat/new/3", ".mail/.notmuch/xapian/db",
    ".config/notmuch/sessionkit/config", ".sessionkit/mail/settings/mail.json",
    ".session/sessions/sid-1/mail/marks", ".session/sessions/sid-1/log/mail",
    ".sessionmail/post-new/state", ".cache/session-mail/ext/v1/stamp",
    ".session/state/list/snapshot.json", ".session/seats/operator/seat.json",
    ".session/agent/config/agent.json", ".session/agents/claude.md",
    ".sessionkit/tools/settings/session.json",
    ".sessionkit/tools/settings/session.d/10-operator.json",
    ".sessionkit/tools/settings/.sounds.schema.json",
    ".sessionkit/tools/settings/statusline.sh.bak-a",
    ".sessionkit/tools/log/pane-state.log",
    ".sessionkit/tools/accounts/token-file-backups/work.token",
    ".config/sessiontools/token-file-backups/work.token",
    ".sessionphone/calls/call-1/audio.wav", ".sessionphone/bot.log",
    ".sessionkit/phone/settings/phone.json", ".sessionkit/phone/log/claude/bot.log",
    ".local/state/sessionview/mutt/x", ".local/state/herd/x",
    ".sessionkit/view/settings/config.json", ".sessionkit/view/state/recent.tsv",
    ".sessionkit/view/log/sessionview.log",
    ".local/share/sessionkit/src/sessionkit/README.md",
)
# Used by VoiceMode too: kept while the reader keeps VoiceMode.
E2E_SHARED = (
    ".mail/agents/mouth/new/to-speak", ".mail/agents/mouth/cur/spoken:2,S",
    ".voicemode/logs/conversations/heard_2030-06-09.jsonl",
    ".voicemode/logs/conversations/heard.lock",
    ".voicemode/state/heard-cursor/vm-1", ".voicemode/mouth/playing.json",
)
# Never the kit's, in either mode. The old logs in ~/Library/Logs stay too.
E2E_THEIRS = (
    ".voicemode/voicemode.env", ".voicemode/voices/v.json",
    ".voicemode/logs/conversations/exchanges_2030-12-08.jsonl",
    ".voicemode/audio/2030/12/x.wav",
    ".notmuch-config", ".config/notmuch/default/config", ".config/other/x",
    ".sessionkit/tools/settings/claude-code.json", ".sessionkit/agents/someone/letter.md",
    ".cache/huggingface/hub/model", ".local/state/claude/lock", ".local/state/x/y",
    ".local/state/audio/other.json", ".claude/settings.json", "Library/Logs/other/x",
    "Library/Logs/ears/ears-keeper.log", "Library/Logs/sessiontools/pane-state.log",
    "Library/Caches/com.apple.Safari/x",
)
# The old logs stay whatever the mode: an uninstall never deletes from there.
E2E_OLD_LOGS = ("Library/Logs/ears/ears-keeper.log",)
# Roots the text never deletes whole: they may stay, empty.
E2E_ROOTS = {".cache", ".config", ".local", ".local/share", ".local/state", "Library",
             "Library/Logs", "Library/Caches"}


def _e2e_blocks(keep_voicemode: bool) -> list[str]:
    blocks = _blocks(_step(6))
    for item in _part_b().split("\n### ")[1:]:
        lead = 0
        for m in re.finditer(r"```bash\n(.*?)\n\s*```", item, re.DOTALL):
            dropping = "- No VoiceMode:" in item[lead:m.start()]
            lead = m.end()
            if not (keep_voicemode and dropping):
                blocks.append("\n".join(x.strip() for x in m.group(1).splitlines()) + "\n")
    return blocks


def _ancestors(paths) -> set[str]:
    return {str(Path(*Path(p).parts[:i])) for p in paths for i in range(1, len(Path(p).parts))}


@pytest.mark.parametrize("mode", ["keep-voicemode", "drop-voicemode", "kit-alone"])
@pytest.mark.parametrize("shell", ["bash", "zsh"])
def test_the_uninstall_in_a_temp_home_leaves_nothing_the_kit_wrote(tmp_path, shell, mode):
    if shutil.which(shell) is None:
        pytest.skip(f"no {shell}")
    home = tmp_path / "home"
    keep = mode == "keep-voicemode"
    if mode == "kit-alone":
        seeded, survivors = E2E_KIT + E2E_SHARED[:2] + E2E_OLD_LOGS, E2E_OLD_LOGS
    else:
        seeded, survivors = E2E_KIT + E2E_SHARED + E2E_THEIRS, E2E_THEIRS
        survivors += E2E_SHARED if keep else ()
    for rel in seeded:
        (home / rel).parent.mkdir(parents=True, exist_ok=True)
        (home / rel).write_text(f"{rel}\n", encoding="utf-8")
    taken = {p.split("/", 1)[0].lower() for p in seeded}
    words = {w for w in re.findall(r"[A-Za-z][A-Za-z0-9_-]+", _ref())
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
