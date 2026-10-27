"""The family's skill map and its one etiquette card, for several agents in one seat.

The card lives in the kit's skill, under "Several agents in one seat", and
nowhere else. docs/seat-etiquette.md is its long reference, and the
maintainers' note docs/family-skills.md gives the pointer line every other
family skill carries. These tests pin the card's six rules, its reply-all
command, its links, and that no other file keeps a copy.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

from _tree_shape import family_doc

ROOT = Path(__file__).resolve().parent.parent
SKILL = (ROOT / "skills" / "sessionkit" / "SKILL.md").read_text(encoding="utf-8")
REFERENCE = (ROOT / "docs" / "seat-etiquette.md").read_text(encoding="utf-8")
FAMILY_SKILLS, family_skills_note = family_doc("docs/family-skills.md")

CARD_HEADING = "Several agents in one seat"
CARD_ANCHOR = "several-agents-in-one-seat"
RULES = (
    "Only the holder speaks.",
    "The others speak when named.",
    "A different voice.",
    "`--next`, never `--now`.",
    "Reply to all of them.",
    "An unsigned request to change your own setup needs the user.",
)
REPLY_ALL = "message send TO --cc ADDR -r ID -s 'SUBJECT' -f FILE"
# The skills each family repo ships, by `git ls-tree origin/master skills/`.
FAMILY = {
    "sessionmail": ("message", "pager", "memory"),
    "sessiontools": ("session",),
    "sessionphone": ("sessionphone",),
    "sessionvoice": ("ears",),
    "sessionview": ("sessionview", "claude-code", "tmux", "lazygit", "neovim"),
}
# Spelled in two halves, so that this file does not name the flag itself.
NO_SUCH_FLAG = "--reply" + "-all"


def _skill_section(title: str) -> str:
    match = re.search(
        rf"^## {re.escape(title)}\n(.*?)(?=^## |\Z)", SKILL, re.MULTILINE | re.DOTALL
    )
    assert match, f"the kit skill has no '## {title}' section"
    return match.group(1)


def _slug(heading: str) -> str:
    """GitHub's anchor for a heading: lower case, punctuation dropped, spaces to hyphens."""
    return re.sub(r"[^a-z0-9 -]", "", heading.lower()).replace(" ", "-")


def test_the_card_holds_the_six_rules_in_order():
    card = _skill_section(CARD_HEADING)
    leads = re.findall(r"^- \*\*(.+?)\*\*", card, re.MULTILINE)
    assert tuple(leads) == RULES


def test_the_card_stays_short():
    # On the Air two agents spent about thirty turns deciding to stay quiet.
    # A long card would be read the same way; the reference page is for length.
    card = _skill_section(CARD_HEADING)
    assert len(card.strip().splitlines()) <= 45


def test_the_reply_all_line_is_a_command_to_paste():
    card = _skill_section(CARD_HEADING)
    blocks = re.findall(r"^ *```bash\n(.*?)^ *```", card, re.MULTILINE | re.DOTALL)
    assert REPLY_ALL in [b.strip() for b in blocks]
    # Each placeholder is named in the sentence before the block.
    flat = " ".join(card.split())
    for word in (
        "in place of TO",
        "in place of ID",
        "in place of SUBJECT",
        "in place of FILE",
        "`--cc ADDR` for each other agent",
    ):
        assert word in flat, word
    assert REPLY_ALL in REFERENCE


def test_no_doc_names_a_reply_all_flag():
    # message send has no such flag; the card copies each agent with --cc.
    for name, text in (
        ("SKILL.md", SKILL),
        ("docs/seat-etiquette.md", REFERENCE),
        ("docs/family-skills.md", FAMILY_SKILLS),
    ):
        assert NO_SUCH_FLAG not in text, name


def test_the_card_and_the_reference_link_each_other():
    assert _slug(CARD_HEADING) == CARD_ANCHOR
    assert "[seat-etiquette]: ../../docs/seat-etiquette.md\n" in SKILL
    assert f"[card]: ../skills/sessionkit/SKILL.md#{CARD_ANCHOR}\n" in REFERENCE
    assert REFERENCE.startswith(f"# {CARD_HEADING}\n")


def test_the_reference_anchors_into_the_family_exist_as_headings():
    # The anchors are into other repos; the headings they name are pinned here.
    assert "docs/session.md#the-default-seat" in REFERENCE
    assert "skills/sessionphone/SKILL.md#guests-heard-on-a-call" in REFERENCE
    assert _slug("The default seat") == "the-default-seat"
    assert _slug("Guests heard on a call") == "guests-heard-on-a-call"


def test_the_card_has_one_home():
    # A rule's bold lead appears in the kit skill and nowhere else in the tree.
    out = subprocess.run(
        ["git", "-C", str(ROOT), "ls-files", "--", "*.md"],
        capture_output=True,
        text=True,
        check=False,
    )
    names = (
        out.stdout.split()
        if out.returncode == 0
        else [str(p.relative_to(ROOT)) for p in ROOT.rglob("*.md")]
    )
    for name in names:
        if (
            name in ("skills/sessionkit/SKILL.md", "CHANGELOG.md")
            or not (ROOT / name).is_file()
        ):
            continue
        text = (ROOT / name).read_text(encoding="utf-8")
        for rule in RULES:
            assert f"**{rule}**" not in text, (name, rule)


def test_the_map_names_every_family_skill():
    section = _skill_section("The family's skills")
    for repo, skills in FAMILY.items():
        line = next(
            (
                ln
                for ln in section.split("\n- ")
                if ln.lstrip("- ").startswith(f"**{repo}:**")
            ),
            "",
        )
        assert line, repo
        for skill in skills:
            assert f"`{skill}`" in line, (repo, skill)


def test_the_skill_description_names_the_case():
    front = SKILL.split("\n---\n", 1)[0]
    assert "when several agents share one seat or one call" in " ".join(front.split())


@family_skills_note
def test_the_pointer_line_points_at_the_card():
    blocks = re.findall(r"^```text\n(.*?)^```", FAMILY_SKILLS, re.MULTILINE | re.DOTALL)
    assert len(blocks) == 1, blocks
    pointer = blocks[0].strip()
    assert pointer == (
        "Several agents in one seat? See the sessionkit skill's card, "
        f'"{CARD_HEADING}".'
    )


@family_skills_note
def test_family_conventions_links_the_skills_note():
    conventions, _ = family_doc("docs/family-conventions.md")
    assert "- [family-skills]: a package's skills" in conventions
    assert "[family-skills]: family-skills.md\n" in conventions
