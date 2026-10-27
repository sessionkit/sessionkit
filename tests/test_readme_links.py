"""The README's link and character rules, as a guard.

The README is the kit's front door, and it reads the same in a checkout, an
editor and a release archive. So:

- **Reference-style links only.** `[text][label]`, with the `[label]: target`
  lines at the bottom. No inline `[text](target)`, no inline image, no HTML
  link, no `<https://...>` autolink.
- **The kit's own files are linked relatively.** No github.com (or
  raw.githubusercontent.com) URL into this repository, in prose or in a link
  line. A `git clone` line in a code block is a command, not a link, and may
  name the repository.
- **No emoji.**
- **Every reference resolves.** Each label used is defined, each definition
  is used, a relative target names a file or directory in this tree (and its
  `#anchor`, if any, a heading there), and an absolute target is https.

Each check is shown to hit on a planted sample: a zero is a receipt only when
the same check can fail. docs/components.md and docs/dependencies.md, written
in the same style, are held to the same rules.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
GUARDED = ("README.md", "docs/components.md", "docs/dependencies.md", "docs/uninstall.md")

FENCE = re.compile(r"^ *(```|~~~).*?^ *\1 *$", re.MULTILINE | re.DOTALL)
CODE_SPAN = re.compile(r"(`+)(?!`).*?(?<!`)\1(?!`)", re.DOTALL)
DEFINITION = re.compile(r"^ {0,3}\[([^\]]+)\]:[ \t]*<?(\S+?)>?(?:[ \t]+.*)?$", re.MULTILINE)
# [text][label] and [label][]; the text may hold one level of brackets
# (an image or code), never a newline-free run of `]`.
FULL_REF = re.compile(r"\[((?:[^\[\]]|\[[^\[\]]*\])*)\]\[([^\[\]]*)\]")
INLINE = re.compile(r"\]\(")
HTML_LINK = re.compile(r"<a\s[^>]*href|<img\s", re.IGNORECASE)
AUTOLINK = re.compile(r"<[a-z][a-z0-9+.-]*:[^>\s]*>", re.IGNORECASE)
SELF_URL = re.compile(
    r"(?:github\.com|raw\.githubusercontent\.com)/sessionkit/session" + r"kit(?![\w-])",
    re.IGNORECASE,
)
SCHEME = re.compile(r"^[a-z][a-z0-9+.-]*:", re.IGNORECASE)
# Emoji and pictographs: the emoji blocks, dingbats, misc symbols and arrows
# used as emoji, regional indicators, keycaps and the variation selector.
EMOJI = re.compile(
    "[\U0001F000-\U0001FAFF\U00002600-\U000027BF\U00002B00-\U00002BFF"
    "\U0001F1E6-\U0001F1FF\U00002300-\U000023FF\U0000FE0F\U000020E3\U0000200D]"
)


def _prose(text: str) -> str:
    """TEXT with fenced blocks and code spans blanked: what renders as prose."""
    text = FENCE.sub(lambda m: "\n" * m.group(0).count("\n"), text)
    return CODE_SPAN.sub("``", text)


def _label(name: str) -> str:
    """A reference label as Markdown matches it: case and runs of space folded."""
    return " ".join(name.split()).lower()


def _definitions(text: str) -> dict[str, str]:
    return {_label(m.group(1)): m.group(2) for m in DEFINITION.finditer(_prose(text))}


def _used_labels(text: str) -> list[str]:
    body = DEFINITION.sub("", _prose(text))
    return [_label(label or ref) for ref, label in FULL_REF.findall(body)]


def _anchors(text: str) -> set[str]:
    """GitHub's anchor for each heading: lower case, punctuation dropped,
    spaces to hyphens."""
    return {re.sub(r"[^a-z0-9 _-]", "", h.strip().lower()).replace(" ", "-")
            for h in re.findall(r"^#{1,6} (.+)$", _strip_fences(text), re.MULTILINE)}


def _strip_fences(text: str) -> str:
    return FENCE.sub("", text)


def _target_problem(target: str, base: Path, root: Path) -> str | None:
    if target.startswith("#"):
        return None if target[1:] in _anchors(base.read_text(encoding="utf-8")) else (
            f"{target}: names no heading here")
    if SCHEME.match(target):
        return None if target.startswith("https://") else f"{target}: not https"
    path, _, anchor = target.partition("#")
    file = (base.parent / path).resolve()
    if not file.is_relative_to(root.resolve()):
        return f"{target}: leaves the repository"
    if not file.exists():
        return f"{target}: names no file or directory"
    if anchor and (file.is_dir() or anchor not in _anchors(file.read_text(encoding="utf-8"))):
        return f"{target}: names no heading there"
    return None


def problems(text: str, base: Path, root: Path = ROOT) -> list[str]:
    """Every rule TEXT breaks, as one line each; [] is clean. BASE is the
    file TEXT stands for, so relative targets resolve from its folder."""
    found = []
    prose = _prose(text)
    for pattern, why in ((INLINE, "inline link"), (HTML_LINK, "HTML link"),
                         (AUTOLINK, "autolink")):
        found += [f"{why}: {line.strip()}" for line in prose.splitlines() if pattern.search(line)]
    found += [f"the kit's own repository by URL: {line.strip()}"
              for line in prose.splitlines() if SELF_URL.search(line)]
    found += [f"emoji: {line.strip()}" for line in text.splitlines() if EMOJI.search(line)]
    defs = _definitions(text)
    used = _used_labels(text)
    found += [f"undefined label: [{label}]" for label in dict.fromkeys(used) if label not in defs]
    found += [f"unused label: [{label}]" for label in defs if label not in used]
    for label, target in defs.items():
        why = _target_problem(target, base, root)
        if why:
            found.append(f"[{label}]: {why}")
    return found


@pytest.mark.parametrize("name", GUARDED)
def test_the_guarded_docs_keep_the_link_and_character_rules(name):
    path = ROOT / name
    text = path.read_text(encoding="utf-8")
    assert _definitions(text), f"{name} has no reference links: the check would pass on nothing"
    assert problems(text, path) == []


def test_the_readme_links_its_neighbours_relatively():
    defs = _definitions((ROOT / "README.md").read_text(encoding="utf-8"))
    assert defs["install"] == "INSTALL.md"
    assert defs["mail"] == "INSTALL.md#mail-between-agents"
    assert not any(SELF_URL.search(t) for t in defs.values())


# --- canaries: each rule, shown to hit -------------------------------------------

README = ROOT / "README.md"
# Built from pieces, so test_readme.py's shipped-file gate, which reads this
# file too, does not trip on the planted self-URLs.
KIT_URL = "https://github.com/sessionkit/session" + "kit"
KIT_RAW = "https://raw.githubusercontent.com/sessionkit/session" + "kit"
CLEAN = "See [the install][install].\n\n[install]: INSTALL.md\n"


def test_a_clean_sample_passes():
    assert problems(CLEAN, README) == []


@pytest.mark.parametrize(("planted", "kind"), [
    ("See [the install](INSTALL.md).\n", "inline link"),
    ("![logo](site/logo.png)\n", "inline link"),
    ("[mail](https://github.com/sessionkit/sessionmail)\n", "inline link"),
    ('<a href="INSTALL.md">install</a>\n', "HTML link"),
    ('<img src="site/logo.png">\n', "HTML link"),
    ("<https://pypi.org/project/sessionkit/>\n", "autolink"),
    (f"Read {KIT_URL}/blob/HEAD/INSTALL.md\n",
     "the kit's own repository by URL"),
    (f"The source: {KIT_URL}.\n",
     "the kit's own repository by URL"),
    (f"Clone {KIT_URL}.git to build it.\n",
     "the kit's own repository by URL"),
    (f"See [x][x].\n\n[x]: {KIT_URL}/tree/HEAD/docs\n",
     "the kit's own repository by URL"),
    (f"curl {KIT_RAW}/HEAD/README.md\n",
     "the kit's own repository by URL"),
    ("Ready \U0001F680\n", "emoji"),
    ("Done ✅\n", "emoji"),
    ("Warning ⚠️\n", "emoji"),
    ("See [the install][nowhere].\n", "undefined label"),
    ("See [nowhere][].\n", "undefined label"),
    (CLEAN + "[spare]: INSTALL.md\n", "unused label"),
    ("See [x][x].\n\n[x]: NO-SUCH-FILE.md\n", "names no file or directory"),
    ("See [x][x].\n\n[x]: INSTALL.md#no-such-heading\n", "names no heading there"),
    ("See [x][x].\n\n[x]: ../README.md\n", "leaves the repository"),
    ("See [x][x].\n\n[x]: #no-such-heading\n", "names no heading here"),
    ("See [x][x].\n\n[x]: http://example.com/\n", "not https"),
])
def test_each_rule_hits_on_a_planted_sample(planted, kind):
    found = problems(planted, README)
    assert any(kind in line for line in found), found


@pytest.mark.parametrize("fine", [
    f"Run `[x](y)` and `{KIT_URL}` in code.\n",
    f"```bash\ngit clone {KIT_URL}\n```\n",
    f"In code, `{KIT_URL}.git` is a command, not a link.\n",
    "```markdown\n[x](INSTALL.md)\n```\n",
    "The family: [mail][pkg-mail].\n\n[pkg-mail]: https://github.com/sessionkit/sessionmail\n",
    f"Also [sessionkit-extras][x].\n\n[x]: {KIT_URL}-extras\n",
    "See [Mail][MAIL].\n\n[mail]: INSTALL.md#mail-between-agents\n",
    "See [up][].\n\n[up]: #installation\n\n## Installation\n",
    "A dash — and quotes “so” are not emoji.\n",
    "Plain [brackets] are text.\n",
])
def test_the_guard_passes_code_family_links_and_plain_text(fine):
    assert problems(fine, README) == []
