"""The README template, pinned to the README shape it ships.

docs/family-docs-readme.md ("README in the family's
12-section shape") lists the sections in order; templates/README.md is that
shape as a file to copy. These tests keep the two in step: the same sections,
in the same order, each with a one-line comment saying what goes there.
"""

from __future__ import annotations

import re
from pathlib import Path

from _tree_shape import family_doc

CONVENTIONS, needs_conventions = family_doc("docs/family-docs-readme.md")

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_PATH = ROOT / "templates" / "README.md"
TEMPLATE = TEMPLATE_PATH.read_text(encoding="utf-8")

# The ruled shape after the H1 and its lead, in order.
SHAPE = [
    "Features",
    "Quick start",
    "Requirements",
    "Installation",
    "Usage",
    "Components",
    "Configuration",
    "Running",
    "Logs",
    "Development",
    "Status",
]
NEWT_FIVE = ["Quick start", "Installation", "Usage", "Development", "Status"]
COMMENT = re.compile(r"^<!-- .+ -->$")


def _h2s(text: str) -> list[str]:
    return re.findall(r"^## (.+)$", text, re.MULTILINE)


def _sections(text: str) -> dict[str, list[str]]:
    """Each heading (H1 and H2) mapped to its non-blank lines."""
    out: dict[str, list[str]] = {}
    current = None
    for line in text.splitlines():
        if re.match(r"^#{1,2} ", line):
            current = line
            out[current] = []
        elif current is not None and line.strip():
            out[current].append(line)
    return out


def _shape_item() -> str:
    match = re.search(
        r"^- \[ \] \*\*README in the family's 12-section shape\.\*\*.*?(?=^- \[ \]|^## |\Z)",
        CONVENTIONS,
        re.MULTILINE | re.DOTALL,
    )
    assert match, "family-docs-readme.md has no README-shape item"
    return match.group(0)


def test_template_has_the_twelve_sections_in_order() -> None:
    assert re.search(r"^# \S", TEMPLATE, re.MULTILINE), "no H1"
    assert _h2s(TEMPLATE) == SHAPE


def test_template_keeps_newts_five_in_newts_order() -> None:
    assert [h for h in _h2s(TEMPLATE) if h in NEWT_FIVE] == NEWT_FIVE


def test_each_section_opens_with_a_one_line_comment() -> None:
    sections = _sections(TEMPLATE)
    assert len(sections) == 12  # the H1 (with its lead) and the 11 H2s
    for heading, lines in sections.items():
        assert lines, f"{heading!r} is empty"
        assert COMMENT.match(lines[0]), (
            f"{heading!r} does not open with a one-line comment"
        )


def test_the_lead_comment_states_the_limit() -> None:
    h1 = next(h for h in _sections(TEMPLATE) if h.startswith("# "))
    assert "25 words or fewer" in _sections(TEMPLATE)[h1][0]


def test_running_is_marked_only_if_it_runs_something() -> None:
    assert "Only if it runs something" in _sections(TEMPLATE)["## Running"][0]


def test_configuration_and_logs_are_marked_must_have() -> None:
    sections = _sections(TEMPLATE)
    for name in ("Configuration", "Logs"):
        assert "MUST-HAVE" in sections[f"## {name}"][0], name


def test_logs_carries_the_health_line() -> None:
    assert any("Health" in line for line in _sections(TEMPLATE)["## Logs"])


@needs_conventions
def test_conventions_list_the_same_shape_in_the_same_order() -> None:
    item = _shape_item()
    listed = re.findall(r"^ {2}\d+\. `## ([^`]+)`", item, re.MULTILINE)
    assert listed == SHAPE


@needs_conventions
def test_conventions_link_the_template_and_the_link_resolves() -> None:
    item = _shape_item()
    links = re.findall(r"\]\(([^)#]+)\)", item)
    assert "../templates/README.md" in links
    assert (
        ROOT / "docs" / "../templates/README.md"
    ).resolve() == TEMPLATE_PATH.resolve()


@needs_conventions
def test_conventions_mark_both_calls_open() -> None:
    item = _shape_item()
    assert "Open, the owner's call" in item
    assert "(a) Does monitoring earn its own section?" in item
    assert '(b) The name "Running"' in item


@needs_conventions
def test_newt_five_item_stays() -> None:
    assert "**README with newt's five H2s:**" in CONVENTIONS
