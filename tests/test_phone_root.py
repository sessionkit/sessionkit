"""The kit's docs name the phone bot's root where sessionphone now keeps it.

From the kit's 0.3.2 the bot's root, which holds its Delta Chat account
and its keys, is `~/.sessionkit/phone/state/`. It was `~/.sessionphone`. A Mac
that has only the old root keeps using it, and says so once on stderr;
nothing moves by itself. `sessionphone bot migrate` moves it, once on each
Mac: stop the bot, a dry run first, the move, a check, then `bot install`.
The keys move by rename, and the old path is left as a symlink, never
deleted.

So the kit's docs name the new root and the old-path fallback, give the move
as sessionphone's own verb in that order, and never tell the reader to move
or delete `~/.sessionphone` by hand.

INSTALL.md section 8 (the uninstall) and docs/uninstall.md are pinned by
tests/test_install_uninstall.py, not here.
"""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path

import pytest
import test_doc_paste
import test_log_paths

ROOT = Path(__file__).resolve().parent.parent
COMPONENTS = ROOT / "docs" / "components.md"
SETTINGS = ROOT / "docs" / "settings.md"
TROUBLESHOOTING = ROOT / "docs" / "troubleshooting.md"
PHONE_PAGE = ROOT / "docs" / "sessionphone.md"

NEW_ROOT = "~/.sessionkit/phone/state/"
OLD_ROOT = "~/.sessionphone"
STEP = "The phone bot still uses the old root"
STEP_LINK = "troubleshooting.md#the-phone-bot-still-uses-the-old-root"
MIGRATE_LINK = "https://github.com/sessionkit/sessionphone#moving-the-root-with-bot-migrate"

# A pasted line that moves, removes or replaces the old root by hand.
HAND_MOVE = re.compile(
    r"\b(?:rm|rmdir|mv|unlink|trash|ln|cp|rsync|ditto)\b[^\n]*\.sessionphone\b"
)


def _flat(text: str) -> str:
    return " ".join(text.split())


def _step() -> str:
    text = TROUBLESHOOTING.read_text(encoding="utf-8")
    start = text.index(f"\n### {STEP}\n")
    end = text.find("\n## ", start + 1)
    return text[start:end]


def _hand_moves(blocks) -> list[str]:
    line = test_log_paths._install_uninstall_line()
    return [
        f"{b.path}:{b.line + i}: {text.strip()}"
        for b in blocks
        if test_log_paths._outside_the_uninstall(b, line)
        for i, text in enumerate(b.lines)
        if HAND_MOVE.search(text)
    ]


# --- docs/settings.md ---------------------------------------------------------------


def test_settings_names_the_new_root_and_the_old_root_fallback():
    row = next(
        line
        for line in SETTINGS.read_text(encoding="utf-8").splitlines()
        if line.startswith("| sessionphone |")
    )
    assert f"the bot's root, `{NEW_ROOT}`" in row, row
    assert f"Before 0.3.2 the root was `{OLD_ROOT}`" in row, row
    assert "a Mac that has only the old one keeps using it" in row, row
    assert "`sessionphone bot migrate`" in row, row
    assert "`~/.sessionkit/phone/settings/phone.json`" in row, row
    assert "its own folder, `~/.sessionphone`" not in row, row


def test_settings_links_the_step():
    assert f"[phone-root]: {STEP_LINK}" in SETTINGS.read_text(encoding="utf-8")


# --- docs/components.md -------------------------------------------------------------


def test_components_folders_names_the_new_root_and_the_old_root_fallback():
    section = test_log_paths._section(COMPONENTS.read_text(encoding="utf-8"), "Folders")
    bullet = _flat(next(b for b in section.split("\n- ") if b.startswith(f"`{NEW_ROOT}`")))
    assert "the phone bot's root, with its Delta Chat account and its keys" in bullet
    assert f"Before 0.3.2 it was `{OLD_ROOT}/`" in bullet
    assert "A Mac that has only the old one keeps using it" in bullet
    assert "nothing moves it by itself" in bullet
    assert "[moving it][phone-root]" in bullet


def test_components_links_the_step():
    assert f"[phone-root]: {STEP_LINK}" in COMPONENTS.read_text(encoding="utf-8")


def test_components_still_says_the_old_phone_logs_were_in_the_old_root():
    section = _flat(test_log_paths._section(COMPONENTS.read_text(encoding="utf-8"), "Logs"))
    assert "Before 0.3.2 these logs were in" in section
    assert f"`{OLD_ROOT}/`" in section


# --- docs/troubleshooting.md, the step ------------------------------------------------


def test_the_step_sits_under_the_steps_an_upgrade_does_not_run():
    text = TROUBLESHOOTING.read_text(encoding="utf-8")
    steps = text.index("\n## Steps an upgrade does not run\n")
    assert steps < text.index(f"\n### {STEP}\n") < text.index("\n## More\n")


def test_the_step_names_the_new_root_the_fallback_and_what_is_never_moved():
    step = _flat(_step())
    assert "its Delta Chat account and its keys" in step
    assert "the root is `~/.sessionkit/phone/state/`" in step
    assert f"before, it was `{OLD_ROOT}`" in step
    assert "A Mac that has only the old root keeps using it" in step
    assert "From 0.3.2 the root is `~/.sessionkit/phone/state/`" in step
    # 0.3.2 is the kit's release. sessionphone's own next number is not
    # settled (its pyproject still says 0.3.1), so the step never names it.
    assert "sessionphone 0.3" not in step
    assert "says so once on stderr. Nothing moves by itself." in step
    assert "is never moved, and this step is not for it" in step
    for root in ("`SESSIONPHONE_ROOT`", "`DC_ROOT`", "`phone.json`"):
        assert root in step, root


def test_the_step_never_moves_or_deletes_the_old_root_by_hand():
    step = _flat(_step())
    assert f"Do not move or delete `{OLD_ROOT}` by hand" in step
    assert "moves the keys by rename" in step
    assert "symlink to the new root, and nothing deletes it" in step
    assert _hand_moves(test_doc_paste.shell_blocks(_step(), "docs/troubleshooting.md")) == []


def test_the_step_runs_phones_own_verbs_in_order_one_to_a_block():
    blocks = test_doc_paste.shell_blocks(_step(), "docs/troubleshooting.md")
    assert [b.lines for b in blocks] == [
        ("sessionphone bot status",),
        ("sessionphone bot uninstall",),
        ("sessionphone bot migrate --dry-run",),
        ("sessionphone bot migrate",),
        ("sessionphone bot status",),
        ("sessionphone bot install",),
    ]


def test_the_step_checks_the_move_before_it_starts_the_bot():
    # Stop, migrate, verify, restart: the reader sees the root has moved
    # before the bot starts on it, not after.
    step = _flat(_step())
    moved = step.index("sessionphone bot migrate ```")
    check = step.index("Check the move before you start the bot.", moved)
    assert check < step.index("sessionphone bot status", check) < step.index("sessionphone bot install", moved)
    assert "If it still does, the move did not happen" in step


def test_the_step_checks_by_the_line_phone_says_and_reads_the_dry_run():
    step = _flat(_step())
    assert "A line that starts `sessionphone: using the old root`" in step
    assert "its `account:` line says where the account will open" in step
    assert "Run the check again." in step


def test_a_refusal_leaves_the_old_root_as_it_was_not_a_symlink():
    # A refused migrate moved nothing: the old root is still the real folder
    # with the keys. Only a move that is done leaves the old path as a symlink.
    step = _flat(_step())
    refused = "When it refuses (exit 2), nothing was moved: the old root is still where it was, with its keys."
    assert refused in step
    assert "Once the move is done, the old path is left as a symlink to the new root" in step
    after = step[step.index(refused) :]
    assert after.index("Once the move is done") < after.index("symlink")


def test_the_step_links_phones_own_rule():
    text = TROUBLESHOOTING.read_text(encoding="utf-8")
    assert "([moving the root][phone-migrate])" in _step()
    assert f"[phone-migrate]: {MIGRATE_LINK}" in text


# --- every pasted block --------------------------------------------------------------


def test_no_pasted_block_outside_the_uninstall_moves_the_old_root_by_hand():
    assert _hand_moves(test_doc_paste._all_blocks()) == []


@pytest.mark.parametrize(
    "line",
    [
        'rm -rf "${HOME:?}/.sessionphone"',
        "mv ~/.sessionphone ~/.sessionkit/phone/state",
        "rmdir ~/.sessionphone",
        "ln -s ~/.sessionkit/phone/state ~/.sessionphone",
        "cp -R ~/.sessionphone ~/.sessionkit/phone/state",
    ],
)
def test_the_hand_move_scan_bites(line):
    block = test_doc_paste.shell_blocks(f"```bash\n{line}\n```\n", "docs/planted.md")
    assert _hand_moves(block) == [f"docs/planted.md:2: {line}"]


@pytest.mark.parametrize(
    "line",
    [
        "sessionphone bot migrate",
        "sessionphone bot migrate --dry-run",
        "ls -ld ~/.sessionphone",
        "rm -f ~/.sessionkit/phone/log/AGENT/bot.log.old",
    ],
)
def test_the_hand_move_scan_lets_the_verb_through(line):
    block = test_doc_paste.shell_blocks(f"```bash\n{line}\n```\n", "docs/planted.md")
    assert _hand_moves(block) == []


def test_the_hand_move_scan_leaves_the_uninstall_to_its_own_tests():
    planted = '```bash\nrm -rf "${HOME:?}/.sessionphone"\n```\n'
    after = test_log_paths._install_uninstall_line() + 10
    install = test_doc_paste.shell_blocks("\n" * after + planted, test_log_paths.INSTALL_DOC)
    uninstall = test_doc_paste.shell_blocks(planted, test_log_paths.UNINSTALL_DOC)
    assert _hand_moves(install + uninstall) == []


# --- docs/sessionphone.md is imported, never hand-written ------------------------------


def _command_docs():
    spec = importlib.util.spec_from_file_location(
        "command_docs", ROOT / "scripts" / "command_docs.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_phone_page_is_the_importers():
    docs = _command_docs()
    text = PHONE_PAGE.read_text(encoding="utf-8")
    footer = docs.FOOTER.format(package="sessionphone", command="sessionphone")
    assert text == docs.stub("sessionphone", "sessionphone") or text.endswith(footer)
