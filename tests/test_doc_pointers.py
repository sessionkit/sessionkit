"""Every doc section the installer and the doctor send a reader to exists.

install.sh and src/sessionkit/doctor.py point a reader at INSTALL.md by
section number ("INSTALL.md section 4"), by heading (the end screen's
"INSTALL.md section 2. Install the kit"), and at a step inside a section by
its bold bullet ("INSTALL.md section 4, "Turn the mail hooks on""). A
pointer at the README names a quoted step the same way. When a doc is
reworked, a pointer can outlive what it names: the hooks hint once sent
readers to a README step that a rewrite had removed (SK-287). This reads
every such pointer out of the two sources and resolves it in the doc.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
INSTALL_SH = (ROOT / "install.sh").read_text(encoding="utf-8")
DOCTOR = (ROOT / "src" / "sessionkit" / "doctor.py").read_text(encoding="utf-8")
DOCS = {
    "INSTALL.md": (ROOT / "INSTALL.md").read_text(encoding="utf-8"),
    "README.md": (ROOT / "README.md").read_text(encoding="utf-8"),
}
SOURCES = {"install.sh": INSTALL_SH, "src/sessionkit/doctor.py": DOCTOR}

# A quote in the source may be escaped (install.sh's say "...\"x\"...").
Q = r'\\?"'
# INSTALL.md section N, "Bullet"
INSTALL_STEP = re.compile(rf"INSTALL\.md section (\d+), {Q}([^\"\\]+){Q}")
# INSTALL.md section N (bare, or followed by its heading's words)
INSTALL_SECTION = re.compile(r"INSTALL\.md section (\d+)\b")
# install.sh's step_label: icon|name|doing|N. Heading
STEP_LABEL_SECTION = re.compile(
    r'^\s*\w+\) say "[^"|]*\|[^|]*\|[^|]*\|(\d+\. [^"]+)" ;;$', re.MULTILINE
)
# The README, "Step" / the README's Section, "Step"
README_STEP = re.compile(rf"README(?:\\?'s)?(?: ([A-Z][\w ]*?))?, {Q}([^\"\\]+){Q}")


def _section(doc: str, heading: str) -> str:
    """The body under the `## heading...` line (a prefix of the heading), up
    to the next `## `; empty if no such heading."""
    text = DOCS[doc]
    match = re.search(
        rf"^## {re.escape(heading)}[^\n]*\n(.*?)(?=^## |\Z)",
        text,
        re.MULTILINE | re.DOTALL,
    )
    return match.group(1) if match else ""


def _names_a_step(body: str, name: str) -> bool:
    """NAME is a bold bullet (`- **NAME.` / `- **NAME**`) or a heading."""
    bold = re.search(rf"^\s*- \*\*{re.escape(name)}(?:[.:*])", body, re.MULTILINE)
    heading = re.search(rf"^#+ {re.escape(name)}\s*$", body, re.MULTILINE)
    return bool(bold or heading)


def pointers(source: str) -> list[tuple[str, str, str]]:
    """(doc, section, step) for each pointer in SOURCE; step may be ''."""
    found = []
    for n, step in INSTALL_STEP.findall(source):
        found.append(("INSTALL.md", f"{n}. ", step))
    for n in INSTALL_SECTION.findall(source):
        found.append(("INSTALL.md", f"{n}. ", ""))
    for heading in STEP_LABEL_SECTION.findall(source):
        found.append(("INSTALL.md", heading, ""))
    for section, step in README_STEP.findall(source):
        found.append(("README.md", section, step))
    return found


def unresolved(source: str) -> list[str]:
    bad = []
    for doc, section, step in pointers(source):
        if doc == "README.md" and not section:
            body = DOCS[doc]
        else:
            body = _section(doc, section)
        if not body:
            bad.append(f"{doc}: no section '## {section}'")
        elif step and not _names_a_step(body, step):
            bad.append(f"{doc} '## {section}': no step '{step}'")
    return bad


@pytest.mark.parametrize("name", list(SOURCES))
def test_every_doc_pointer_resolves(name):
    assert unresolved(SOURCES[name]) == []


def test_the_reader_finds_the_pointers_both_sources_give():
    # The resolver is only as good as its reader: it must see the hooks
    # pointer in each source, and install.sh's numbered and headed sections.
    hooks = ("INSTALL.md", "4. ", "Turn the mail hooks on")
    assert hooks in pointers(INSTALL_SH)
    assert hooks in pointers(DOCTOR)
    sh = pointers(INSTALL_SH)
    assert ("INSTALL.md", "2. ", "") in sh
    assert ("INSTALL.md", "2. Install the kit", "") in sh
    assert ("INSTALL.md", "5. Hearing and speaking", "") in sh


@pytest.mark.parametrize(
    "dead",
    [
        'say "  The README, \\"The mail hooks start off\\", has the lines to paste."',
        "HOOKS_SECTION = 'the README\\'s Installation, \"The mail hooks start off\"'",
        'say "  INSTALL.md section 4, \\"The mail hooks start off\\", at:"',
        'say "  INSTALL.md section 3, \\"Turn the mail hooks on\\", at:"',
        'say "See INSTALL.md section 9, at:"',
        '        hooks) say "📬|the mail hooks|turning on|4. Last checks" ;;',
    ],
)
def test_a_dead_pointer_fails(dead):
    # The pointers this test exists for, each in the form its source writes
    # it: a removed README step, a step in the wrong section, a section that
    # is not there.
    assert pointers(dead), dead
    assert unresolved(dead), dead


# INSTALL.md's "starts plain when one does" links the place that says so. It
# once linked the README's Quick start, which a rewrite left without the
# claim; the claim lives on in the session page's default-seat section.
STARTS_PLAIN = re.compile(r"starts plain when one does \(\[[^\]]+\]\(([^)#]+)#([^)]+)\)\)")
HEADING = re.compile(r"^(#{1,6}) (.+)$", re.MULTILINE)


def _slug(heading: str) -> str:
    """A heading's anchor, as GitHub writes it."""
    text = re.sub(r"[^\w\- ]", "", heading.strip().lower())
    return text.replace(" ", "-")


def _anchored(page: str, anchor: str) -> str:
    """The text under the heading whose anchor is `anchor`, to the next one
    of the same or a higher level; empty when no heading has that anchor."""
    found = [m for m in HEADING.finditer(page) if _slug(m.group(2)) == anchor]
    if not found:
        return ""
    level = len(found[0].group(1))
    rest = page[found[0].end():]
    end = next((m.start() for m in HEADING.finditer(rest) if len(m.group(1)) <= level), None)
    return rest[:end]


def _claim_is_made(page_text: str, anchor: str) -> bool:
    body = " ".join(_anchored(page_text, anchor).split()).lower()
    return "runs plain" in body or "starts plain" in body


def test_install_starts_plain_links_where_the_claim_is_made():
    flat = " ".join(DOCS["INSTALL.md"].split())
    (target, anchor), = STARTS_PLAIN.findall(flat)
    assert target != "README.md"
    assert _claim_is_made((ROOT / target).read_text(encoding="utf-8"), anchor), (target, anchor)


def test_a_link_to_a_section_without_the_claim_fails():
    # The old target: the README's Quick start no longer says it.
    assert not _claim_is_made(DOCS["README.md"], "quick-start")
    assert not _claim_is_made(DOCS["README.md"], "no-such-heading")
