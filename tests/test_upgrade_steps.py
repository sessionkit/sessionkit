"""docs/troubleshooting.md names the steps an upgrade does not run.

sessiontools keeps `CLAUDE_CODE_AGENT` out of every launch and out of a tmux
server it starts. A tmux server born inside the default seat before that fix
still holds the word, and only the operator can clear it, on each Mac, by
hand. The upgrade does not. The kit's hub says so, quotes sessiontools'
CHANGELOG, and gives the check before the fix, each command in its own block.

docs/session.md is imported from sessiontools, never hand-edited; the
command_docs check pins it to its source. Here we pin only that the hub's
link lands on the heading that carries the step.
"""

from __future__ import annotations

import re
from pathlib import Path

import test_doc_paste

ROOT = Path(__file__).resolve().parent.parent
TROUBLESHOOTING = ROOT / "docs" / "troubleshooting.md"
SESSION = ROOT / "docs" / "session.md"
DEPENDENCIES = ROOT / "docs" / "dependencies.md"

TITLE = "Steps an upgrade does not run"
CHECK = "tmux show-environment -g CLAUDE_CODE_AGENT"
REMOVE = "tmux set-environment -g -u CLAUDE_CODE_AGENT"
# sessiontools' CHANGELOG, [Unreleased] ### Fixed, word for word.
TOOLS_QUOTE = (
    '"a tmux server born inside a seat before this fix keeps the word for '
    "every pane it makes until it is restarted, or until "
    '`tmux set-environment -g -u CLAUDE_CODE_AGENT` is run on it."'
)


def _section() -> str:
    text = TROUBLESHOOTING.read_text(encoding="utf-8")
    start = text.index(f"\n## {TITLE}\n")
    end = text.find("\n## ", start + 1)
    return text[start : end if end != -1 else len(text)]


def _flat(text: str) -> str:
    return " ".join(text.split())


def test_the_hub_has_the_section_before_more():
    text = TROUBLESHOOTING.read_text(encoding="utf-8")
    assert text.index(f"\n## {TITLE}\n") < text.index("\n## More\n")


def test_the_section_is_a_step_of_its_own_on_each_mac():
    flat = _flat(_section())
    assert "on each Mac, when you choose to" in flat
    assert "not part of the upgrade, and nothing runs it for you" in flat


def test_the_section_quotes_sessiontools_changelog():
    assert TOOLS_QUOTE in _flat(_section())


def test_each_command_is_its_own_block_and_the_check_comes_first():
    blocks = test_doc_paste.shell_blocks(_section(), "docs/troubleshooting.md")
    lines = [b.lines for b in blocks]
    assert (CHECK,) in lines, lines
    assert (REMOVE,) in lines, lines
    assert lines.index((CHECK,)) < lines.index((REMOVE,))
    for block in blocks:
        assert test_doc_paste.paste_problems(block) == [], block


def test_the_section_says_what_the_check_prints():
    flat = _flat(_section())
    assert "`CLAUDE_CODE_AGENT=claude` means it holds the word" in flat
    assert "`unknown variable: CLAUDE_CODE_AGENT` means it does not" in flat


def test_the_section_hands_the_reader_no_kill():
    assert "kill-server" not in _section()
    assert "kill-session" not in _section()


def test_the_link_lands_on_the_imported_default_seat_heading():
    text = TROUBLESHOOTING.read_text(encoding="utf-8")
    assert "[the default seat][session-seat]" in _section()
    assert re.search(
        r"^\[session-seat\]: session\.md#the-default-seat$", text, re.MULTILINE
    )
    session = SESSION.read_text(encoding="utf-8")
    seat = session[session.index("\n## The default seat\n") :]
    seat = seat[: seat.find("\n## ", 1)]
    assert CHECK in seat
    assert REMOVE in seat


def test_the_canary_bites_when_the_check_moves_after_the_fix():
    section = _section()
    swapped = section.replace(CHECK, "@@").replace(REMOVE, CHECK).replace("@@", REMOVE)
    blocks = test_doc_paste.shell_blocks(swapped, "swapped")
    lines = [b.lines for b in blocks]
    assert lines.index((CHECK,)) > lines.index((REMOVE,))


def test_the_dependencies_upgrade_points_at_the_section():
    text = DEPENDENCIES.read_text(encoding="utf-8")
    start = text.index("\n## Upgrade\n")
    end = text.find("\n## ", start + 1)
    upgrade = _flat(text[start : end if end != -1 else len(text)])
    assert "**A tmux server already running** keeps what it had" in upgrade
    assert "[steps an upgrade does not run][upgrade-steps]" in upgrade
    assert re.search(
        r"^\[upgrade-steps\]: troubleshooting\.md#steps-an-upgrade-does-not-run$",
        text,
        re.MULTILINE,
    )
    # The anchor is the heading's GitHub slug.
    slug = re.sub(r"[^a-z0-9 -]", "", TITLE.lower()).replace(" ", "-")
    assert slug == "steps-an-upgrade-does-not-run"
