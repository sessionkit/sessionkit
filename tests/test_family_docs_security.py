"""The family's security-page standard, docs/family-docs-security.md, pinned.

- Its outline lists the six required headings of a `docs/security.md`, in
  order, and the optional headings after them, in the order the page gives.
- It is a draft for a ruling: its Status says so, and every open choice is a
  marked QUESTION with a lean, never a settled promise.
- Its links are reference-style and each resolves to a file in docs/.
- It is listed in docs/family-docs.md. tests/test_agents.py holds it to
  export-ignore.
"""

from __future__ import annotations

import re
from pathlib import Path

from _tree_shape import family_doc

ROOT = Path(__file__).resolve().parent.parent
PAGE = "docs/family-docs-security.md"
TEXT, page_mark = family_doc(PAGE)
INDEX, index_mark = family_doc("docs/family-docs.md")

REQUIRED = (
    "## Reporting a vulnerability",
    "## What to expect",
    "## Scope",
    "## Supported versions",
    "## What it touches",
)
OPTIONAL = (
    "## Signed mail and keys",
    "## Accounts, tokens and credentials",
    "## Recording and consent",
    "## Local mail delivery",
    "## Plugin, hooks and MCP",
    "## Network",
    "## Services and login items",
    "## Known limits",
    "## Advisories",
)


def _flat(text: str) -> str:
    return re.sub(r"\s+", " ", text)


def _outline() -> list[str]:
    block = re.search(r"```markdown\n(.*?)```", TEXT, re.DOTALL)
    assert block, "the page has no outline block"
    return [line for line in block.group(1).splitlines() if line.startswith("#")]


@page_mark
def test_outline_has_the_required_headings_in_order_then_the_optional():
    headings = _outline()
    assert headings[0] == "# <Package> security"
    assert headings[1:] == [*REQUIRED, *OPTIONAL]


@page_mark
def test_each_optional_heading_has_its_rule():
    flat = _flat(TEXT)
    for heading in OPTIONAL:
        assert f"- **`{heading}`:** when the package" in flat, heading


@page_mark
def test_point_is_in_the_first_40_lines():
    head = "\n".join(TEXT.splitlines()[:40])
    assert head.startswith("# Family docs: security\n")
    assert "how to report a vulnerability privately" in _flat(head)
    assert "Part of [family-docs][]." in _flat(head)
    assert "**Status:** DRAFT, for a ruling." in head


@page_mark
def test_every_open_choice_is_a_question_with_a_lean():
    flat = _flat(TEXT)
    questions = flat.count("**QUESTION, the owner's call:**")
    assert questions == 6
    assert flat.count("**Lean:**") == questions
    # The old marker is gone: one form for an open choice.
    assert "Open, the owner's call" not in flat


@page_mark
def test_no_contact_or_private_path_on_the_page():
    assert not re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", TEXT), "an address on the page"
    assert "~/" not in TEXT, "a home-relative path on the page"
    assert not re.search(r"(?<![\w.])/(?:home|Users)/", TEXT), (
        "a home directory on the page"
    )


@page_mark
def test_links_are_reference_style_and_resolve():
    assert not re.search(r"\]\([^)]+\)", TEXT), "an inline link"
    used = set(re.findall(r"\[([a-z-]+)\]\[\]", TEXT))
    defined = dict(re.findall(r"^\[([a-z-]+)\]: (\S+)$", TEXT, re.MULTILINE))
    assert used and used <= set(defined), used - set(defined)
    for label, target in defined.items():
        assert (ROOT / "docs" / target).is_file(), f"{label}: {target}"


@index_mark
def test_family_docs_lists_the_security_page():
    assert "[family-docs-security]: family-docs-security.md" in INDEX
    assert "- [family-docs-security]:" in INDEX
