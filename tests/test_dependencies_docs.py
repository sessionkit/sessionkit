"""The dependencies docs, pinned to the repo they describe.

- The README's `## Requirements` is the operating systems and a link to
  docs/dependencies.md: no Required or Optional list, and none of the tools
  pending a ruling named anywhere in it.
- docs/dependencies.md names every ruled family package with its extras, and
  the outside tools a default command fails without. The tools pending a
  ruling get no class and no install step: each says `Status: pending a
  ruling` and what uses it, what happens without it, where it comes from.
  One cut is ruled: on a Mac, a call needs Homebrew, then ffmpeg from it.
  Those two get one class, "For calls on a Mac", and stay pending for
  everything else. tmux and notmuch get no class at all.
- .github/dependabot.yml parses, looks daily, and names exactly the
  ecosystems the repo has: `uv` for uv.lock, `github-actions` only with a
  .github/workflows folder.
- docs/dependencies.md says, on its first screen, that the full resolved
  set is in uv.lock, and links ../uv.lock: the family rule's one sentence.
- The family rule, docs/family-docs-dependencies.md, is listed in
  docs/family-docs.md. tests/test_agents.py holds it to export-ignore.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml
from _ruled_deps import RULED
from _tree_shape import family_doc
from packaging.requirements import Requirement

ROOT = Path(__file__).resolve().parent.parent
README = (ROOT / "README.md").read_text(encoding="utf-8")
DEPS = (ROOT / "docs" / "dependencies.md").read_text(encoding="utf-8")
DEPENDABOT = ROOT / ".github" / "dependabot.yml"

FAMILY_PAGE = "docs/family-docs-dependencies.md"
FAMILY_TEXT, family_mark = family_doc(FAMILY_PAGE)
FAMILY_INDEX, index_mark = family_doc("docs/family-docs.md")
FAMILY_README, readme_mark = family_doc("docs/family-docs-readme.md")

# The outside tools a default command fails without, as docs/dependencies.md
# measured them. A new one belongs here and on the page together.
REQUIRED_TOOLS = ("Claude Code", "uv", "Python 3.14", "Command Line Tools", "jq")

# The tools whose class is held for a ruling. The pages state facts about
# them, never "required" or "optional", and never tell a reader to install
# one. A ruling moves a name from here into a class, on the page and here.
PENDING_TOOLS = ("Homebrew", "tmux", "notmuch", "ffmpeg")

# The ruling's narrow cut: on a Mac, a call needs Homebrew, then ffmpeg from
# it. These two leave "pending" for a call only, and their entries say so;
# everything else about them stays pending. The held two get no class at all.
CALL_TOOLS = ("Homebrew", "ffmpeg")
HELD_TOOLS = ("tmux", "notmuch")
CALLS = "For calls on a Mac"
CALLS_STATUS = "Status: pending a ruling, except for calls on a Mac ([for calls on a Mac][calls])."
H2S = ["Required", "Optional", CALLS, "Pending a ruling", "Upgrade"]
PENDING_FACTS = ("**What uses it:**", "**Without it:**", "**Where it comes from today:**")


def _section(text: str, title: str, level: str = "##") -> str:
    match = re.search(
        rf"^{level} {re.escape(title)}\n(.*?)(?=^{level} |\Z)", text, re.MULTILINE | re.DOTALL
    )
    assert match, f"no '{level} {title}' section"
    return match.group(1)


def _flat(text: str) -> str:
    return " ".join(text.split())


def test_readme_requirements_is_the_systems_and_a_link():
    req = _flat(_section(README, "Requirements"))
    for system in ("- [x] macOS", "- [ ] Linux", "- [ ] WSL", "- [ ] Windows"):
        assert system in req, system
    assert "[dependencies][dependencies]" in req
    assert re.search(r"^\[dependencies\]: docs/dependencies\.md$", README, re.MULTILINE)
    # No prerequisites list: what the kit needs is on docs/dependencies.md.
    for word in ("**Required:**", "**Optional:**", "needs:"):
        assert word not in req, word
    for tool in PENDING_TOOLS:
        assert tool.lower() not in req.lower(), tool


def test_readme_says_nowhere_that_the_kit_needs_a_pending_tool():
    flat = _flat(README)
    for line in ("also needs tmux", "tmux and notmuch from Homebrew", "[requirements][requirements]"):
        assert line not in flat, line
    assert not re.search(r"^\[requirements\]:", README, re.MULTILINE)


def test_readme_uses_one_name_for_the_list():
    # "Requirements" is the README section; there is no second name for it.
    h2s = re.findall(r"^## (.+)$", README, re.MULTILINE)
    assert "Requirements" in h2s
    assert "Dependencies" not in h2s


def test_dependencies_page_names_every_ruled_package_and_its_extras():
    required = _section(DEPS, "Required")
    for spec in RULED:
        req = Requirement(spec)
        floor = str(req.specifier).removeprefix(">=")
        line = next((ln for ln in required.splitlines() if f"[{req.name}]" in ln), "")
        assert line, f"{req.name} is not listed"
        assert f"{floor} or later" in line, (req.name, line)
        for extra in req.extras:
            assert f"`{extra}` extra" in line, (req.name, extra)


def test_dependencies_page_tables_say_need_install_and_upgrade():
    for title in ("Required", "Optional"):
        header = next(ln for ln in _section(DEPS, title).splitlines() if ln.startswith("| Dependency"))
        for column in ("What needs it", "How you get it", "How you upgrade it"):
            assert column in header, (title, column)
    required = _section(DEPS, "Required")
    for tool in REQUIRED_TOOLS:
        assert tool in required, tool


def _pending_entries() -> dict[str, str]:
    pending = _section(DEPS, "Pending a ruling")
    parts = re.split(r"^### \[([^\]]+)\]\[[^\]]+\]\n", pending, flags=re.MULTILINE)
    return dict(zip(parts[1::2], parts[2::2]))


def test_dependencies_page_holds_the_pending_tools_unclassed():
    entries = _pending_entries()
    assert sorted(entries) == sorted(PENDING_TOOLS)
    for tool, body in entries.items():
        flat = _flat(body)
        status = CALLS_STATUS if tool in CALL_TOOLS else "Status: pending a ruling."
        assert flat.startswith(status), tool
        for fact in PENDING_FACTS:
            assert fact in flat, (tool, fact)
        assert not re.search(r"\b(required|optional)\b", flat, re.IGNORECASE), tool
        assert not re.search(r"\bbrew (install|upgrade)\b", flat), tool


def test_dependencies_page_classes_no_pending_tool():
    # Not a row of either table, not named on the first screen's class lines.
    for title in ("Required", "Optional"):
        names = [ln.split("|")[1] for ln in _section(DEPS, title).splitlines() if ln.startswith("| ")]
        for tool in PENDING_TOOLS:
            assert not any(tool.lower() in name.lower() for name in names), (title, tool)
    first = DEPS.split("\n## ", 1)[0]
    lines = dict(re.findall(r"^- \*\*([^*]+):\*\* (.*?)(?=^- |^$)", first, re.MULTILINE | re.DOTALL))
    assert sorted(lines) == sorted([CALLS, "Optional", "Pending a ruling", "Required", "Upgrade"]), sorted(lines)
    for label in ("Required", "Optional", "Upgrade"):
        for tool in PENDING_TOOLS:
            assert tool.lower() not in lines[label].lower(), (label, tool)
    for tool in CALL_TOOLS:
        assert tool in lines[CALLS], tool
    for tool in HELD_TOOLS:
        assert tool not in lines[CALLS], tool
    for tool in PENDING_TOOLS:
        assert tool in lines["Pending a ruling"], tool
    for tool in HELD_TOOLS:
        assert f"brew install {tool}" not in DEPS, tool
    for tool in ("tmux", "notmuch", "ffmpeg"):
        assert f"brew upgrade {tool}" not in DEPS, tool


def test_dependencies_page_has_one_class_for_calls_and_none_for_the_held_tools():
    # A class is a `## ` section. The ruling added one, for calls on a Mac;
    # a section for tmux or notmuch, or any other, fails here.
    assert re.findall(r"^## (.+)$", DEPS, re.MULTILINE) == H2S


def test_calls_class_is_homebrew_then_ffmpeg_then_the_speech_server():
    calls = _section(DEPS, CALLS)
    flat = _flat(calls)
    blocks = re.findall(r"^ *```bash\n(.*?)^ *```", calls, re.MULTILINE | re.DOTALL)
    assert [b.strip() for b in blocks] == ["brew install ffmpeg"]
    # The one install step on the page, and only here.
    assert DEPS.count("brew install ffmpeg") == 1
    assert calls.index("[Homebrew][brew]") < calls.index("brew install ffmpeg") < calls.index("speech server")
    assert "Homebrew is the default way to get a call's ffmpeg." in flat
    # The no-Homebrew case is one neutral line, and it teaches nothing.
    assert flat.count("workaround") == 1
    assert "A call without Homebrew is the workaround case. This page does not cover it." in flat
    for tool in HELD_TOOLS:
        assert tool not in calls, tool


def test_dependencies_page_upgrade_keeps_the_python_pin():
    upgrade = _section(DEPS, "Upgrade")
    block = re.search(r"```bash\n(.*?)```", upgrade, re.DOTALL).group(1).splitlines()
    assert block[0] == "uv tool upgrade sessionkit"
    assert "claude plugin update sessionkit@sessionkit" in block
    assert "keeps the Python 3.14" in _flat(upgrade)


# The one line the family rule asks every docs/dependencies.md to carry.
LOCK_LINE = (
    "The full resolved set, every package at the version this repo is tested with, "
    "is in [`uv.lock`][uv-lock]."
)


def test_dependencies_page_links_the_lock_on_its_first_screen():
    assert (ROOT / "uv.lock").is_file()
    first = _flat(DEPS.split("\n## ", 1)[0])
    assert LOCK_LINE in first
    assert re.search(r"^\[uv-lock\]: \.\./uv\.lock$", DEPS, re.MULTILINE)


def test_dependabot_parses_and_looks_daily():
    config = yaml.safe_load(DEPENDABOT.read_text(encoding="utf-8"))
    assert config["version"] == 2
    assert config["updates"], "no update entries"
    for entry in config["updates"]:
        assert entry["schedule"]["interval"] == "daily", entry
        assert entry["directory"] == "/", entry


def test_dependabot_names_exactly_the_ecosystems_the_repo_has():
    config = yaml.safe_load(DEPENDABOT.read_text(encoding="utf-8"))
    named = sorted(entry["package-ecosystem"] for entry in config["updates"])
    present = []
    if (ROOT / "uv.lock").is_file():
        present.append("uv")
    if (ROOT / ".github" / "workflows").is_dir():
        present.append("github-actions")
    assert named == sorted(present)


@family_mark
def test_family_page_names_the_list_and_gives_the_reason():
    flat = _flat(FAMILY_TEXT)
    assert '**The README\'s list is called "Requirements".**' in flat
    assert "an operating system is not a dependency" in flat
    for thing in ("`## Requirements`", "`docs/dependencies.md`", "`.github/dependabot.yml`"):
        assert thing in flat, thing
    assert "Kept current, three ways." in flat
    # The README rule is the systems and a link, never a prerequisites list,
    # and a class not yet decided is written as pending, with no install step.
    assert "**`## Requirements` is short: the operating systems, then a link to `docs/dependencies.md`.**" in flat
    assert "It lists no prerequisites itself" in flat
    assert "`Status: pending a ruling`" in flat


@family_mark
def test_family_page_puts_the_full_set_in_the_lock():
    flat = _flat(FAMILY_TEXT)
    # The rule's sentence is the kit's, word for word: the crews copy it.
    assert LOCK_LINE in flat
    assert "`[uv-lock]: ../uv.lock`" in flat
    assert "**The full resolved set is in `uv.lock`, and `docs/dependencies.md` links it.**" in flat
    # The page no longer calls docs/dependencies.md the full or complete list.
    for claim in ("the full list", "complete list"):
        assert claim not in flat.lower(), claim


@readme_mark
def test_family_readme_page_does_not_call_the_page_the_full_list():
    # The README rule links docs/dependencies.md too; the full set is uv.lock's.
    flat = _flat(FAMILY_README).lower()
    for claim in ("the full list", "complete list"):
        assert claim not in flat, claim


@family_mark
def test_family_page_standard_file_matches_the_kits():
    block = re.search(r"```yaml\n(.*?)```", FAMILY_TEXT, re.DOTALL).group(1)
    standard = yaml.safe_load("\n".join(line[2:] for line in block.splitlines()))
    kit = yaml.safe_load(DEPENDABOT.read_text(encoding="utf-8"))
    assert standard == kit


@index_mark
def test_family_docs_lists_the_dependencies_page():
    assert "[family-docs-dependencies]: family-docs-dependencies.md" in FAMILY_INDEX
    assert "- [family-docs-dependencies]:" in FAMILY_INDEX

