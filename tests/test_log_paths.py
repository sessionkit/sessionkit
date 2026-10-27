"""The kit's docs name each package's log where the package now writes it.

In 0.3.2 the family's logs moved under the kit's folder, one `log/` per
package, beside its `settings/`:

- sessionvoice: `~/.sessionkit/voice/log/` (was `~/Library/Logs/ears/` and
  an older log folder from before the kit);
- sessiontools: `~/.sessionkit/tools/log/` (was `~/Library/Logs/sessiontools/`);
- sessionphone: `~/.sessionkit/phone/log/<agent>/` (was `bot.log` in the
  bot's root, `~/.sessionphone/`);
- sessionview: `~/.sessionkit/view/log/sessionview.log`, and its state in
  `~/.sessionkit/view/state/` (both were `~/.local/state/sessionview/`);
- sessionmail's launch agents: `~/.sessionkit/mail/log/`, a seat agent's
  `seat-agent.<ADDRESS>.log` (was in `~/Library/Logs/`) and the puller's
  `puller.log` (was `<pull.state_dir>/log/puller.log`). The pager log,
  `pager.jsonl`, did not move.

Each package leaves the old files where they are. So a doc may say where an
old log was, and that it is left in place, but a block the reader pastes
reads the new folder, and nothing tells the reader to delete an old one.

INSTALL.md section 8 (the uninstall) and docs/uninstall.md are pinned by
tests/test_install_uninstall.py, not here.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import test_doc_paste

ROOT = Path(__file__).resolve().parent.parent
COMPONENTS = ROOT / "docs" / "components.md"
TROUBLESHOOTING = ROOT / "docs" / "troubleshooting.md"

NEW_LOGS = {
    "sessionmail": "`~/.sessionkit/mail/log/`",
    "sessiontools": "`~/.sessionkit/tools/log/`",
    "sessionphone": "`~/.sessionkit/phone/log/<agent>/`",
    "sessionview": "`~/.sessionkit/view/log/sessionview.log`",
    "sessionvoice": "`~/.sessionkit/voice/log/`",
}
# A log folder (or log file) a package wrote before 0.3.2.
OLD_LOG = re.compile(
    r"Library/Logs"
    r"|\.local/state/sessionview"
    r"|\.sessionphone/(?:[^\s\"']*/)?bot(?:\.launchd)?\.log"
    r"|(?<!\.sessionkit/mail)/log/puller\.log"
)
# The uninstall's own files: another test pins them.
UNINSTALL_DOC = "docs/uninstall.md"
INSTALL_DOC = "INSTALL.md"
INSTALL_UNINSTALL = "## 8. Uninstall"


def _section(text: str, title: str) -> str:
    start = text.index(f"\n## {title}\n")
    end = text.find("\n## ", start + 1)
    return text[start : end if end != -1 else len(text)]


def _install_uninstall_line() -> int:
    lines = (ROOT / INSTALL_DOC).read_text(encoding="utf-8").splitlines()
    return lines.index(INSTALL_UNINSTALL) + 1


def _outside_the_uninstall(block: test_doc_paste.Block, uninstall_line: int) -> bool:
    if block.path == UNINSTALL_DOC:
        return False
    return not (block.path == INSTALL_DOC and block.line > uninstall_line)


def _old_log_reads(blocks, uninstall_line: int) -> list[str]:
    return [
        f"{b.path}:{b.line + i}: {line.strip()}"
        for b in blocks
        if _outside_the_uninstall(b, uninstall_line)
        for i, line in enumerate(b.lines)
        if OLD_LOG.search(line)
    ]


# --- docs/components.md, Logs ---------------------------------------------------


@pytest.mark.parametrize("package", sorted(NEW_LOGS))
def test_components_logs_names_each_packages_new_log(package):
    section = _section(COMPONENTS.read_text(encoding="utf-8"), "Logs")
    bullet = next(
        (b.split("\n\n", 1)[0] for b in section.split("\n- ") if b.startswith(f"**{package}")),
        None,
    )
    assert bullet is not None, package
    assert NEW_LOGS[package] in " ".join(bullet.split()), bullet
    assert not OLD_LOG.search(bullet), bullet


def test_components_logs_says_the_old_logs_are_left_in_place():
    section = " ".join(_section(COMPONENTS.read_text(encoding="utf-8"), "Logs").split())
    for old in ("`~/Library/Logs/`", "`~/.sessionphone/`", "`~/.local/state/sessionview/`"):
        assert old in section, old
    assert "leaves the old files where they are, and nothing deletes them" in section


def test_components_logs_names_mails_launch_agent_logs_and_keeps_the_pager_log():
    section = _section(COMPONENTS.read_text(encoding="utf-8"), "Logs")
    bullet = " ".join(
        next(b for b in section.split("\n- ") if b.startswith("**sessionmail")).split()
    )
    assert "`~/.session/sessions/<session-id>/log/mail/pager.jsonl`" in bullet
    assert "log to `~/.sessionkit/mail/log/`" in bullet
    assert "a seat agent to `seat-agent.<ADDRESS>.log`" in bullet
    assert "the puller to `puller.log`" in bullet
    text = COMPONENTS.read_text(encoding="utf-8")
    assert "docs/message-seat.md#the-log" in text
    assert "docs/pull.md#the-log" in text


def test_components_logs_says_where_mails_old_logs_are_and_what_moves_them():
    section = " ".join(_section(COMPONENTS.read_text(encoding="utf-8"), "Logs").split())
    assert "a seat agent's `seat-agent.<ADDRESS>.log`" in section
    assert "the puller's was `<pull.state_dir>/log/puller.log`" in section
    assert "The pager log has not moved." in section
    assert "**A seat agent:** until it is uninstalled and installed again." in section
    assert "**The puller:** until `message setup --pull` renders its plist again." in section


def test_components_folders_names_the_log_and_view_state_folders():
    section = _section(COMPONENTS.read_text(encoding="utf-8"), "Folders")
    assert "- `~/.sessionkit/<package>/log/`:" in section
    assert "- `~/.sessionkit/view/state/`:" in section


def test_components_tail_example_is_a_block_of_its_own():
    blocks = test_doc_paste.shell_blocks(
        COMPONENTS.read_text(encoding="utf-8"), "docs/components.md"
    )
    assert any(
        b.lines == ("tail -F ~/.sessionkit/phone/log/AGENT/bot.log",) for b in blocks
    ), blocks


# --- docs/troubleshooting.md --------------------------------------------------------


def test_troubleshooting_tails_the_voice_log_folder():
    text = TROUBLESHOOTING.read_text(encoding="utf-8")
    blocks = test_doc_paste.shell_blocks(text, "docs/troubleshooting.md")
    tail = next(b for b in blocks if b.lines[0].startswith("tail -F "))
    assert "  ~/.sessionkit/voice/log/ears-*.log \\" in tail.lines, tail.lines
    flat = " ".join(text.split())
    for line in (
        "`tail -3 ~/.sessionkit/voice/log/ears-mail.log`",
        "`tail ~/.sessionkit/voice/log/ears-keeper-calls.log`",
        "`bot.log` in `~/.sessionkit/phone/log/<agent>/`",
    ):
        assert line in flat, line


def test_troubleshooting_says_where_the_old_ears_logs_are():
    flat = " ".join(TROUBLESHOOTING.read_text(encoding="utf-8").split())
    assert "`~/Library/Logs/ears/` and an older log folder from before the kit." in flat
    assert "old files are left where they are" in flat


# --- every pasted block -------------------------------------------------------------


def test_no_pasted_block_outside_the_uninstall_reads_an_old_log():
    hits = _old_log_reads(test_doc_paste._all_blocks(), _install_uninstall_line())
    assert hits == []


@pytest.mark.parametrize(
    "line",
    [
        "tail -F ~/Library/Logs/ears/ears-keeper.log",
        "grep x ~/Library/Logs/*/ears-*.log",
        "tail ~/.sessionphone/bot.log",
        "tail ~/.sessionphone/work/bot.launchd.log",
        'rm -rf "${HOME:?}/.local/state/sessionview"',
        "tail -F ~/Library/Logs/seat-agent.ADDRESS.log",
        "tail -F ~/.sessionmail/pull/log/puller.log",
    ],
)
def test_the_old_log_scan_bites(line):
    block = test_doc_paste.shell_blocks(f"```bash\n{line}\n```\n", "docs/planted.md")
    assert _old_log_reads(block, _install_uninstall_line()) == [f"docs/planted.md:2: {line}"]


@pytest.mark.parametrize(
    "line",
    [
        "tail -F ~/.sessionkit/voice/log/ears-keeper.log",
        "tail ~/.sessionkit/phone/log/AGENT/bot.log",
        "ls ~/.sessionphone",
        "tail -F ~/.sessionkit/mail/log/puller.log",
        "tail -F ~/.sessionkit/mail/log/seat-agent.ADDRESS.log",
    ],
)
def test_the_old_log_scan_lets_the_new_folders_through(line):
    block = test_doc_paste.shell_blocks(f"```bash\n{line}\n```\n", "docs/planted.md")
    assert _old_log_reads(block, _install_uninstall_line()) == []


def test_the_old_log_scan_leaves_the_uninstall_to_its_own_tests():
    planted = "```bash\nrm -rf \"${HOME:?}/Library/Logs/ears\"\n```\n"
    after = _install_uninstall_line() + 10
    install = test_doc_paste.shell_blocks("\n" * after + planted, INSTALL_DOC)
    uninstall = test_doc_paste.shell_blocks(planted, UNINSTALL_DOC)
    before = test_doc_paste.shell_blocks(planted, INSTALL_DOC)
    assert _old_log_reads(install + uninstall, _install_uninstall_line()) == []
    assert len(_old_log_reads(before, _install_uninstall_line())) == 1
