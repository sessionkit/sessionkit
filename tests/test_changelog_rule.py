"""The CHANGELOG rule, pinned to the words it ships.

docs/family-docs-changelog.md rules that every user-visible
change gets a CHANGELOG bullet, and that every egg label (the ready tag's
message) carries exactly one of two lines, verbatim. These tests keep the
item beside the Keep a Changelog item, keep both lines verbatim, and keep its
Check command accepting those two lines and nothing near them.
"""

from __future__ import annotations

import re

from _tree_shape import family_doc

CONVENTIONS, needs_conventions = family_doc("docs/family-docs-changelog.md")

pytestmark = needs_conventions

LINES = ["Changelog: yes", "Changelog: none, no user-visible change"]


def _items() -> list[str]:
    """Each `- [ ]` item of the doc, from its line to the next item or H2."""
    return re.findall(
        r"^- \[ \] .*?(?=^- \[ \]|^## |\Z)", CONVENTIONS, re.MULTILINE | re.DOTALL
    )


def _rule_index() -> int:
    items = _items()
    for i, item in enumerate(items):
        if item.startswith("- [ ] **A CHANGELOG bullet for every user-visible change"):
            return i
    raise AssertionError("family-docs-changelog.md has no CHANGELOG-rule item")


def _rule() -> str:
    """The item's text, its wrapped lines joined by single spaces."""
    return " ".join(_items()[_rule_index()].split())


def _check_pattern() -> re.Pattern[str]:
    match = re.search(r"grep -E '([^']+)'", _rule())
    assert match, "the item's Check line has no grep -E pattern"
    return re.compile(match.group(1))


def test_rule_sits_beside_the_keep_a_changelog_item() -> None:
    before = _items()[_rule_index() - 1]
    assert before.startswith("- [ ] **CHANGELOG in Keep a Changelog form")


def test_rule_is_ruled_with_a_date() -> None:
    assert "Ruled by the owner, 2030-06-09." in _rule()


def test_rule_names_fixed_and_the_changes_that_skip_it() -> None:
    rule = _rule()
    assert "`### Fixed`" in rule
    for kind in ("test-only", "vendoring", "CI"):
        assert kind in rule, kind


def test_both_egg_label_lines_are_verbatim() -> None:
    rule = _rule()
    for line in LINES:
        assert f"`{line}`" in rule, line
    assert "Silence is a forgetting, not a choice." in rule


def test_meets_today_is_honest_and_names_the_pending_warning() -> None:
    rule = _rule()
    assert "Meets today: none." in rule
    assert "pending: GIT-514" in rule


def test_check_accepts_both_lines() -> None:
    pattern = _check_pattern()
    for line in LINES:
        assert pattern.search(line), line


def test_check_refuses_near_misses() -> None:
    pattern = _check_pattern()
    for line in (
        "Changelog: no",
        "Changelog: none",
        "Changelog: Yes",
        "changelog: yes",
        "Changelog: yes, see CHANGELOG.md",
        " Changelog: yes",
    ):
        assert not pattern.search(line), line
