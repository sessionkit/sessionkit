"""AGENTS.md holds the instructions; CLAUDE.md only imports it.

The family rule (docs/family-docs-agents.md): Claude Code
skips AGENTS.md when a CLAUDE.md sits in the working directory or above, so
CLAUDE.md's first line must be `@AGENTS.md`. Here it is that line and
nothing else. AGENTS.md names `make` targets; each must be a real one.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from _tree_shape import left_out

ROOT = Path(__file__).resolve().parent.parent
AGENTS = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
MAKEFILE = (ROOT / "Makefile").read_text(encoding="utf-8")
CLAUDE_MD = ROOT / "CLAUDE.md"

# .gitattributes export-ignores /CLAUDE.md, so a release archive (`git archive`,
# the GitHub tarball, the public repo built from one) has no CLAUDE.md. There
# these two tests skip; in a checkout, where it exists, they still assert.
# `lexists`, not `exists`: a dangling symlink is a CLAUDE.md, and must fail.
needs_claude_md = pytest.mark.skipif(
    not os.path.lexists(CLAUDE_MD),
    reason="no CLAUDE.md: .gitattributes export-ignores it, so a release archive leaves it out",
)


@needs_claude_md
def test_claude_md_is_exactly_the_import() -> None:
    assert CLAUDE_MD.read_text(encoding="utf-8") == "@AGENTS.md\n"


@needs_claude_md
def test_claude_md_is_a_file_not_a_symlink() -> None:
    assert not CLAUDE_MD.is_symlink()


# CLAUDE.md stays in the tree and in history, but a release archive
# (`git archive`, the GitHub tarball) leaves it out.
def test_gitattributes_export_ignores_claude_md() -> None:
    lines = (ROOT / ".gitattributes").read_text(encoding="utf-8").splitlines()
    assert "/CLAUDE.md export-ignore" in lines


def _git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, check=False)


@pytest.mark.skipif(
    not shutil.which("git") or _git("rev-parse", "--git-dir").returncode != 0, reason="not a git checkout"
)
def test_git_reads_claude_md_as_export_ignored() -> None:
    out = _git("check-attr", "export-ignore", "--", "CLAUDE.md").stdout.decode()
    assert out.strip() == "CLAUDE.md: export-ignore: set"
    # AGENTS.md is what CLAUDE.md imports, and it ships.
    out = _git("check-attr", "export-ignore", "--", "AGENTS.md").stdout.decode()
    assert out.strip() == "AGENTS.md: export-ignore: unspecified"


def test_every_make_target_agents_md_names_is_in_the_makefile() -> None:
    targets = set(re.findall(r"^([a-zA-Z_-]+):", MAKEFILE, re.MULTILINE))
    named = set(re.findall(r"`?make ([a-z]+)", AGENTS))
    assert named, "AGENTS.md names no make target"
    assert named <= targets, f"not in the Makefile: {sorted(named - targets)}"


def test_agents_md_names_the_check_target() -> None:
    assert "make check" in AGENTS


def test_every_relative_link_in_agents_md_resolves() -> None:
    links = re.findall(r"\]\(([^)#]+)\)", AGENTS)
    assert links
    missing = [link for link in links if not (ROOT / link).exists()]
    assert not missing, f"AGENTS.md links to missing files: {missing}"


# The release-archive case: `make check` in a `git archive` tree must
# not go red on the missing CLAUDE.md. Run the two CLAUDE.md tests in a copy
# of the files this module reads, with CLAUDE.md left out, as the archive does.
def _run_claude_md_tests(tree: Path) -> subprocess.CompletedProcess:
    (tree / "tests").mkdir()
    for name in ("test_agents.py", "_tree_shape.py"):
        shutil.copy(ROOT / "tests" / name, tree / "tests" / name)
    for name in ("AGENTS.md", "Makefile"):
        shutil.copy(ROOT / name, tree / name)
    node = "tests/test_agents.py::"
    tests = [f"{node}test_claude_md_is_exactly_the_import", f"{node}test_claude_md_is_a_file_not_a_symlink"]
    return subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-rs", "-p", "no:cacheprovider", *tests],
        cwd=tree, capture_output=True, text=True, check=False,
    )


def test_claude_md_tests_skip_in_a_tree_without_it(tmp_path: Path) -> None:
    result = _run_claude_md_tests(tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "2 skipped" in result.stdout
    assert "export-ignores it" in result.stdout


# A dangling CLAUDE.md symlink is not an absent CLAUDE.md: it must still fail.
def test_claude_md_tests_still_fail_on_a_dangling_symlink(tmp_path: Path) -> None:
    (tmp_path / "CLAUDE.md").symlink_to(tmp_path / "nowhere.md")
    result = _run_claude_md_tests(tmp_path)
    assert result.returncode == 1, result.stdout + result.stderr
    assert "2 failed" in result.stdout


# The maintainers' notes in docs/ stay in the tree and in history, but a
# release archive leaves them out: they are process, not a user's doc.
MAINTAINER_NOTES = (
    "docs/family-build.md",
    "docs/family-contributing.md",
    "docs/family-conventions.md",
    "docs/family-docs.md",
    "docs/family-docs-agents.md",
    "docs/family-docs-changelog.md",
    "docs/family-docs-license.md",
    "docs/family-docs-readme.md",
    "docs/family-file-structure.md",
    "docs/family-release.md",
    "docs/family-settings.md",
    "docs/family-services.md",
    "docs/family-tests.md",
    "docs/pre-public-checklist.md",
    "docs/release-numbering.md",
)

# An image under docs/images/ that only the notes show is left out with them.
# Shipped alone, it would be a picture from a page the reader never gets.
MAINTAINER_IMAGES = ("docs/images/settings-order.svg",)


def _shipped_docs() -> list[Path]:
    """The Markdown a release archive ships: every doc but the notes."""
    docs = [
        ROOT / "AGENTS.md",
        ROOT / "README.md",
        ROOT / "INSTALL.md",
        *sorted((ROOT / "docs").glob("*.md")),
        *sorted((ROOT / "openspec" / "specs").rglob("*.md")),
    ]
    return [doc for doc in docs if str(doc.relative_to(ROOT)) not in MAINTAINER_NOTES]


def _links(doc: Path) -> list[str]:
    return re.findall(r"\]\(([^)#\s]+)", doc.read_text(encoding="utf-8"))


def test_gitattributes_export_ignores_the_maintainer_notes() -> None:
    lines = (ROOT / ".gitattributes").read_text(encoding="utf-8").splitlines()
    for note in (*MAINTAINER_NOTES, *MAINTAINER_IMAGES):
        assert f"/{note} export-ignore" in lines, note


def test_every_family_doc_is_a_maintainer_note() -> None:
    # A docs/family-*.md added to the tree but not to the list above would
    # ship in the release archive.
    found = sorted(str(p.relative_to(ROOT)) for p in (ROOT / "docs").glob("family-*.md"))
    missing = [doc for doc in found if doc not in MAINTAINER_NOTES]
    assert not missing, missing


@pytest.mark.skipif(
    not shutil.which("git") or _git("rev-parse", "--git-dir").returncode != 0, reason="not a git checkout"
)
def test_git_reads_the_maintainer_notes_as_export_ignored() -> None:
    for note in (*MAINTAINER_NOTES, *MAINTAINER_IMAGES):
        # A clone of the export has a .git but never held the notes; a source
        # checkout's HEAD holds them, so there each must stay in the tree.
        if not left_out(note):
            assert (ROOT / note).is_file(), f"{note} must stay in the tree"
        out = _git("check-attr", "export-ignore", "--", note).stdout.decode()
        assert out.strip() == f"{note}: export-ignore: set"


def test_no_shipped_doc_links_a_maintainer_note() -> None:
    # A maintainer image counts too: the archive leaves it out, so a shipped
    # doc that showed it would show a broken image.
    names = [n.rsplit("/", 1)[1] for n in (*MAINTAINER_NOTES, *MAINTAINER_IMAGES)]
    hits = []
    for doc in _shipped_docs():
        for link in _links(doc):
            if link.rsplit("/", 1)[-1] in names:
                hits.append(f"{doc.name}: {link}")
    assert not hits, hits


def test_every_image_no_shipped_doc_shows_is_a_maintainer_image() -> None:
    # An image added for a maintainer note but not to the list above would
    # ship in the release archive with no page to show it.
    images = sorted(str(p.relative_to(ROOT)) for p in (ROOT / "docs" / "images").glob("*") if p.is_file())
    shown = {link.rsplit("/", 1)[-1] for doc in _shipped_docs() for link in _links(doc)}
    loose = [img for img in images if img.rsplit("/", 1)[1] not in shown and img not in MAINTAINER_IMAGES]
    assert not loose, loose


# The release shapes for the notes: the tests that read
# docs/family-docs-<file>.md skip in a tree with no doc and no .git, as a
# `git archive` tree is, and in a git repo whose HEAD never held the doc, as a
# clone of the export is. They still fail in a checkout that lost the doc.
CONVENTION_TESTS = ("test_changelog_rule.py", "test_readme_template.py", "test_check_agents_archive.py")


def _run_convention_tests(tree: Path) -> subprocess.CompletedProcess:
    (tree / "tests").mkdir()
    for name in (*CONVENTION_TESTS, "_tree_shape.py"):
        shutil.copy(ROOT / "tests" / name, tree / "tests" / name)
    for name in ("templates/README.md", "scripts/check_agents_archive.py"):
        (tree / name).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(ROOT / name, tree / name)
    node = [f"tests/{name}" for name in CONVENTION_TESTS]
    # That test checks the kit's own AGENTS.md at HEAD, which this tree's git
    # (when it has one) does not hold; it reads no doc, so it has no say here.
    own = "tests/test_check_agents_archive.py::test_the_kits_own_agents_md_passes"
    return subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-rs", "-p", "no:cacheprovider", "--deselect", own, *node],
        cwd=tree, capture_output=True, text=True, check=False,
    )


def test_convention_tests_skip_in_a_tree_without_the_doc(tmp_path: Path) -> None:
    result = _run_convention_tests(tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr
    reason = ".gitattributes export-ignores it"  # each doc names itself first
    assert result.stdout.count(reason) == 15, result.stdout
    assert " failed" not in result.stdout, result.stdout


def _git_env() -> dict[str, str]:
    # Every GIT_* variable dropped, then no global or system config: a
    # reader's hooks, commit signing or config variables must not reach
    # this throwaway repo.
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env.update(
        GIT_CONFIG_NOSYSTEM="1",
        GIT_CONFIG_GLOBAL=os.devnull,
        GIT_AUTHOR_NAME="t",
        GIT_AUTHOR_EMAIL="t@example.invalid",
        GIT_COMMITTER_NAME="t",
        GIT_COMMITTER_EMAIL="t@example.invalid",
    )
    return env


def _commit_all(tree: Path) -> None:
    """Make `tree` a git repo of one commit holding every file in it."""
    for args in (["init", "-q"], ["add", "-A"], ["commit", "-q", "-m", "tree"]):
        subprocess.run(["git", "-C", str(tree), *args], capture_output=True, check=True, env=_git_env())


needs_git = pytest.mark.skipif(not shutil.which("git"), reason="git is not installed")


# A clone of the export: a .git, but its one commit never held the doc.
@needs_git
def test_convention_tests_skip_in_a_clone_whose_history_lacks_the_doc(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("export\n", encoding="utf-8")
    _commit_all(tmp_path)
    result = _run_convention_tests(tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr
    reason = ".gitattributes export-ignores it"  # each doc names itself first
    assert result.stdout.count(reason) == 15, result.stdout
    assert " failed" not in result.stdout, result.stdout


# A source checkout that lost the doc: HEAD still holds it, so the tests run
# and fail, and the loss is not skipped over.
@needs_git
def test_convention_tests_still_fail_in_a_checkout_without_the_doc(tmp_path: Path) -> None:
    docs = [tmp_path / "docs" / f"family-docs-{n}.md" for n in ("agents", "changelog", "readme")]
    docs[0].parent.mkdir()
    for doc in docs:
        doc.write_text("# Family docs\n", encoding="utf-8")
    _commit_all(tmp_path)
    for doc in docs:
        doc.unlink()
    result = _run_convention_tests(tmp_path)
    assert result.returncode == 1, result.stdout + result.stderr
    assert "15 failed" in result.stdout, result.stdout
