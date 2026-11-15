"""The family's web note, docs/family-web.md: the `<package>-web` rule.

The note is a maintainer note, so a release archive leaves it out and these
tests skip there; in a checkout they read it, and a missing note fails.
"""

from __future__ import annotations

import re

from _tree_shape import family_doc

FAMILY_WEB, needs_family_web = family_doc("docs/family-web.md")
CONVENTIONS, needs_conventions = family_doc("docs/family-conventions.md")

pytestmark = needs_family_web


def _flat(text: str) -> str:
    return " ".join(text.split())


def _section(heading: str) -> str:
    """The text under `## heading`, up to the next H2."""
    start = FAMILY_WEB.index(f"\n## {heading}\n")
    rest = FAMILY_WEB[start + len(heading) + 5 :]
    return rest.split("\n## ", 1)[0]


def test_the_rule_names_the_command_and_the_front_door():
    rule = _flat(_section("The rule"))
    assert (
        "**A package that serves a page behind the front door ships a command "
        "named `<package>-web`.**"
    ) in rule


def test_the_rule_gives_its_why_and_its_one_example():
    rule = _flat(_section("The rule"))
    assert "a `<package>-web` name cannot collide with a system program." in rule
    assert "`/usr/bin/talk`" in rule
    assert "`sessionvoice-web`, for Talk." in rule
    assert "`sessionvoice-web web-room`" in rule


def test_the_rule_promises_nothing_of_the_talk_command():
    # The fate of the page's own command, `talk`, is open in its package.
    rule = _flat(_section("The rule"))
    assert "this rule says nothing of it." in rule
    for promise in (
        "will be renamed",
        "is retired",
        "is deprecated",
        "becomes an alias",
    ):
        assert promise not in rule, promise


def test_a_page_outside_the_front_door_is_outside_the_rule():
    outside = _flat(_section("A page outside the front door"))
    assert "is outside this rule. Its command keeps its name." in outside
    assert "`sessionphone web`, a subcommand of `sessionphone`" in outside
    assert (
        "If such a page later moves behind the front door, the package ships `<package>-web`"
        in outside
    )


def test_the_note_is_public_neutral():
    # No tracker IDs, no clock times, no host names in the prose.
    assert not re.findall(r"\b[A-Z]{2,}-\d+\b", FAMILY_WEB)
    assert not re.findall(r"\b\d{1,2}:\d{2}\b", FAMILY_WEB)
    assert not re.findall(r"\b[a-z0-9-]+\.(?:ts\.net|local)\b", FAMILY_WEB)


@needs_conventions
def test_family_conventions_links_the_web_note():
    assert "- [family-web]: the web pages a package serves" in CONVENTIONS
    assert "[family-web]: family-web.md\n" in CONVENTIONS
    assert "(scope open)" not in CONVENTIONS
