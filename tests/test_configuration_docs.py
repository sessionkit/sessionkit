"""The configuration docs, pinned to the README template and to the code.

docs/configuration.md is what the kit itself configures; docs/settings.md is
the family's settings guide and the kit's own keys. The README is short: its
Configuration and Logs sections are one line and a link each. The family's
map is in docs/configuration.md, and the Logs section, ending on the Health
line, is in docs/components.md. A link into another family repository is absolute, on HEAD (its
default branch, so it names no branch), and its text names the package and
the file; a link into this repository is relative, so the docs read in a
checkout or an editor without a browser, and its file and #anchor resolve.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from sessionkit import cli
from sessionkit import setup as operator_setup

ROOT = Path(__file__).resolve().parent.parent
README = (ROOT / "README.md").read_text(encoding="utf-8")
CONFIG_DOC = "docs/configuration.md"
SETTINGS_DOC = "docs/settings.md"
COMPONENTS_DOC = "docs/components.md"
NEW_DOCS = (CONFIG_DOC, SETTINGS_DOC, COMPONENTS_DOC)
KIT = "https://github.com/sessionkit/sessionkit"
SELF_URL = re.compile(r"https?://github\.com/sessionkit/sessionkit(?:/|#|$)")

INLINE_LINK = re.compile(r"\]\(([^)\s]+)\)")
REFERENCE_DEF = re.compile(r"^\[[^\]]+\]:\s*(\S+)", re.MULTILINE)


def _read(name: str) -> str:
    return (ROOT / name).read_text(encoding="utf-8")


def _section(text: str, title: str) -> str:
    """The body of the `## title` section, up to the next `## `."""
    match = re.search(rf"^## {re.escape(title)}\n(.*?)(?=^## |\Z)", text, re.MULTILINE | re.DOTALL)
    assert match, f"no '## {title}' section"
    return match.group(1)


def _refs(text: str) -> dict[str, str]:
    """Each reference label, folded to lower case, and its target."""
    return {m.group(1).lower(): m.group(2)
            for m in re.finditer(r"^\[([^\]]+)\]:\s*(\S+)", text, re.MULTILINE)}


def _section_targets(text: str, title: str) -> list[str]:
    """The targets the links in one section point at: inline ones, and each
    `[text][label]` resolved through the document's own `[label]:` lines."""
    section = _section(text, title)
    refs = _refs(text)
    labels = [(label or ref).lower()
              for ref, label in re.findall(r"\[([^\[\]]+)\]\[([^\[\]]*)\]", section)]
    assert all(label in refs for label in labels), labels
    return _targets(section) + [refs[label] for label in labels]


def _h2s(text: str) -> list[str]:
    return re.findall(r"^## (.+)$", text, re.MULTILINE)


def _targets(text: str) -> list[str]:
    return INLINE_LINK.findall(text) + REFERENCE_DEF.findall(text)


def _slug(heading: str) -> str:
    """GitHub's anchor for a heading: lower case, punctuation dropped,
    spaces to hyphens."""
    return re.sub(r"[^a-z0-9 _-]", "", heading.strip().lower()).replace(" ", "-")


def _anchors(text: str) -> set[str]:
    return {_slug(h) for h in re.findall(r"^#{1,6} (.+)$", text, re.MULTILINE)}


def _is_relative(target: str) -> bool:
    return not re.match(r"^(?:[a-z][a-z0-9+.-]*:|//|#)", target, re.IGNORECASE)


def _unresolved(name: str, target: str) -> str | None:
    """Why a relative `target` in doc `name` does not resolve, else None: the
    file must be in this repository, and an #anchor must be one of its headings."""
    path, _, anchor = target.partition("#")
    file = ((ROOT / name).parent / path).resolve()
    if not file.is_relative_to(ROOT.resolve()):
        return f"{name}: {target} leaves the repository"
    if not file.exists():
        return f"{name}: {target} names no file"
    if anchor and anchor not in _anchors(file.read_text(encoding="utf-8")):
        return f"{name}: {target} names no heading there"
    return None


# --- the README -----------------------------------------------------------------


def test_readme_sections_follow_the_template_order():
    # templates/README.md: Usage, Components, Configuration, Running, Logs,
    # Development. Here "The family" stands where Components does.
    h2s = _h2s(README)
    order = ["Usage", "The family", "Configuration", "Logs", "Development"]
    assert [h for h in h2s if h in order] == order


@pytest.mark.parametrize("repo", cli.FAMILY)
def test_configuration_doc_links_each_family_page_absolutely(repo):
    doc = _read(CONFIG_DOC)
    section = _section(doc, "The family's pages")
    url = f"https://github.com/sessionkit/{repo}/blob/HEAD/docs/configuration.md"
    assert f"{repo}'s docs/configuration.md" in section
    assert url in _section_targets(doc, "The family's pages")


def test_readme_configuration_links_the_kits_page_and_the_guide():
    targets = _section_targets(README, "Configuration")
    assert "docs/configuration.md" in targets
    assert "docs/settings.md" in targets


@pytest.mark.parametrize("title", ["Configuration", "Logs"])
def test_readme_new_sections_link_other_repos_absolutely_and_this_one_relatively(title):
    targets = _section_targets(README, title)
    assert targets, f"README's {title} links nothing: the check would pass on nothing"
    for target in targets:
        if _is_relative(target):
            assert _unresolved("README.md", target) is None, target
        else:
            assert target.startswith("https://"), target
            assert not SELF_URL.match(target), target


def test_readme_logs_points_at_the_components_logs():
    assert "docs/components.md#logs" in _section_targets(README, "Logs")


def test_components_logs_names_each_family_package():
    section = _section(_read(COMPONENTS_DOC), "Logs")
    for repo in cli.FAMILY:
        assert f"**{repo}**" in section or f"**{repo}:**" in section, repo


def test_components_logs_ends_on_the_health_line():
    section = _section(_read(COMPONENTS_DOC), "Logs").rstrip()
    body = section.split("\n\n[", 1)[0].rstrip()
    last = body.splitlines()[-3:]
    assert last[0].startswith("- **Health:** `sessionkit --version`"), last


def test_the_health_line_quotes_what_version_prints_for_a_missing_package():
    section = _section(_read(COMPONENTS_DOC), "Logs")
    assert f"`{cli.NOT_INSTALLED}`" in section


# --- docs/ ------------------------------------------------------------------------


@pytest.mark.parametrize("name", NEW_DOCS)
def test_docs_link_this_repo_relatively_and_others_absolutely(name):
    targets = _targets(_read(name))
    assert targets, f"{name} has no links: the check would pass on nothing"
    assert any(_is_relative(t) for t in targets), f"{name}: no relative link to check"
    for target in targets:
        if _is_relative(target):
            assert _unresolved(name, target) is None
        else:
            assert target.startswith(("https://", "#")), f"{name}: {target}"
            assert not SELF_URL.match(target), f"{name}: {target}"


@pytest.mark.parametrize("name", NEW_DOCS)
def test_docs_use_no_wiki_links(name):
    assert "[[" not in _read(name)


@pytest.mark.parametrize("name", NEW_DOCS)
def test_docs_anchors_resolve(name):
    text = _read(name)
    here = _anchors(text)
    for target in _targets(text):
        if target.startswith("#"):
            assert target[1:] in here, f"{name}: {target}"
        elif _is_relative(target):
            assert _unresolved(name, target) is None


def test_the_anchor_check_can_fail():
    # A zero is a receipt only when the same check is shown to hit.
    assert "no-such-heading" not in _anchors(_read(SETTINGS_DOC))
    assert _slug("The kit's own keys") == "the-kits-own-keys"
    assert _unresolved(CONFIG_DOC, "settings.md#no-such-heading")
    assert _unresolved(CONFIG_DOC, "no-such-file.md")
    assert _unresolved(CONFIG_DOC, "../../outside.md")
    assert _unresolved(CONFIG_DOC, "settings.md#the-kits-own-keys") is None
    assert _unresolved(CONFIG_DOC, "../README.md#configuration") is None
    assert SELF_URL.match(f"{KIT}/blob/HEAD/INSTALL.md")
    assert SELF_URL.match(f"{KIT}#configuration")
    assert not SELF_URL.match("https://github.com/sessionkit/sessionmail/blob/HEAD/x.md")


def test_configuration_settings_h2_is_a_real_link_to_the_guide():
    section = _section(_read(CONFIG_DOC), "Settings")
    assert "coming" not in section.lower()
    assert "[docs/settings.md][settings]" in section
    assert "\n[settings]: settings.md\n" in _read(CONFIG_DOC)


def test_configuration_names_the_file_setup_writes():
    path = f"~/{operator_setup.operator_drop_in(Path()).as_posix()}"
    assert path == "~/.sessionkit/tools/settings/session.d/10-operator.json"
    assert path in _read(CONFIG_DOC)
    assert path in _read(SETTINGS_DOC)


def test_configuration_names_only_make_variables_the_makefile_reads():
    makefile = _read("Makefile")
    table = _section(_read(CONFIG_DOC), "Working on the kit")
    names = re.findall(r"^\| `([A-Z_]+)` \|", table, re.MULTILINE)
    assert names, "the table lists no variables"
    script = _read("scripts/check_agents_archive.py")
    for name in names:
        assert name in makefile or f'"{name}"' in script, name


def test_settings_lists_each_operator_key_setup_and_the_reader_use():
    text = _section(_read(SETTINGS_DOC), "The kit's own keys")
    for key in (operator_setup.MAILBOX_KEY, operator_setup.ADDRESS_KEY, operator_setup.PRIVILEGED_KEY):
        assert f"`{operator_setup.OPERATOR_KEY}.{key}`" in text, key
    assert f"`{operator_setup.ASK_ADDRESS_ENV}`" in text


@pytest.mark.parametrize("repo", cli.FAMILY)
def test_settings_table_links_each_package_page_absolutely(repo):
    text = _read(SETTINGS_DOC)
    section = _section(text, "Each package's settings")
    assert f"| {repo} |" in section
    assert f"https://github.com/sessionkit/{repo}/blob/HEAD/docs/settings.md" in text
    assert f"[{repo}'s docs/settings.md]" in section


SPECS = {"spec-settings": "openspec/specs/settings/spec.md", "spec-tree": "openspec/specs/tree/spec.md"}


@pytest.mark.parametrize("label", SPECS)
def test_settings_links_the_published_spec_relatively(label):
    # The guide names the specification and links it: a relative link to the
    # file in the kit (the docs/ rule), to a spec this tree really holds.
    text = _read(SETTINGS_DOC)
    path = SPECS[label]
    assert f"\n[{label}]: ../{path}\n" in text
    assert f"][{label}]" in _section(text, "The cascade")
    assert (ROOT / path).is_file(), path


def test_settings_no_longer_says_the_spec_is_coming():
    cascade = _section(_read(SETTINGS_DOC), "The cascade")
    lines = [line for line in cascade.splitlines() if "specification" in line]
    assert lines, "the guide no longer names the specification"
    assert "coming" not in cascade.lower()


def test_settings_does_not_say_the_spec_holds_every_rule_it_states():
    # The guide states the cascade as built; the spec states only what is
    # decided and lists the rest as not yet specified. So the guide's link
    # sentence says the spec has such a list, and never that the spec is the
    # cascade written down, and each linked spec really carries the list.
    cascade = " ".join(_section(_read(SETTINGS_DOC), "The cascade").split())
    assert "written down as a specification of its own" not in cascade
    assert "which also lists what it does not yet specify" in cascade
    for path in SPECS.values():
        purpose = _read(path).split("## Requirements", 1)[0]
        assert "Not yet specified" in purpose, path


def test_settings_names_the_five_layers_in_order():
    cascade = _section(_read(SETTINGS_DOC), "The cascade")
    order = re.findall(r"^\d\. \*\*(\w+):\*\*", cascade, re.MULTILINE)
    assert order == ["template", "host", "agent", "seat", "session"]


# sessionview's home file moved into the kit's home; its store and
# project `.sessionview` layer files keep their name. OLD_VIEW_HOME finds the
# old home folder: `~`, `$HOME` or `${HOME...}`, a slash, then the layer name.
OLD_VIEW_HOME = re.compile(r"(~|\$HOME|\$\{HOME[^}]*\})/\.sessionview\b")
SKIP_DIRS = {".git", ".venv", "node_modules", "__pycache__", "dist", "build"}


def test_settings_names_sessionviews_home_file_in_the_kits_home():
    row = next(line for line in _read(SETTINGS_DOC).splitlines()
               if line.startswith("| sessionview |"))
    assert "`~/.sessionkit/view/settings/view.json`" in row
    assert "`.sessionview` files in a store and a project" in row
    assert not OLD_VIEW_HOME.search(row), row


def _text_files(root: Path = ROOT):
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root)
        if any(part in SKIP_DIRS or part.startswith(".") for part in rel.parts[:-1]):
            continue
        if path.is_file():
            try:
                yield rel, path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue


def test_no_file_names_sessionviews_old_home():
    hits = [f"{rel}:{n}" for rel, text in _text_files()
            for n, line in enumerate(text.splitlines(), 1) if OLD_VIEW_HOME.search(line)]
    assert hits == []


def test_the_old_view_home_scan_sees_a_planted_hit(tmp_path):
    # The control is the old home as it was written: the home directory, then
    # the layer name the row keeps. Built at run time, it puts no hit in the tree.
    row = next(line for line in _read(SETTINGS_DOC).splitlines()
               if line.startswith("| sessionview |"))
    layer = re.search(r"`(\.\w+)` files in a store", row).group(1)
    planted = tmp_path / "docs" / "planted.md"
    planted.parent.mkdir()
    planted.write_text(f"~/{layer}/config.json\nrm -rf \"${{HOME:?}}/{layer}\"\n",
                       encoding="utf-8")
    kept = tmp_path / "docs" / "kept.md"
    kept.write_text(f"`{layer}` files\n~/.sessionkit/view/log/sessionview.log\n",
                    encoding="utf-8")
    hits = [f"{rel}:{n}" for rel, text in _text_files(tmp_path)
            for n, line in enumerate(text.splitlines(), 1) if OLD_VIEW_HOME.search(line)]
    assert hits == ["docs/planted.md:1", "docs/planted.md:2"]
