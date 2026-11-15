"""openspec/ in the kit is a pointer to the project's OpenSpec store.

The specifications (settings, tree) live in the store, not in this repo.
openspec/ holds exactly one file, config.yaml, whose one line is
`store: sessionkit`: the openspec CLI, run in a checkout, follows it to the
store. The store is private, so the release archive leaves openspec/ out.

The spec-form checks (Purpose and Requirements, SHALL or MUST, a scenario
for each requirement, no status words) went with the specs to the store;
the kit does not run them.

The release archive has no openspec/, so the tests that read the pointer
skip there (tests/_tree_shape.py); in a checkout they always run.
"""
from __future__ import annotations

import io
import os
import shutil
import subprocess
import tarfile
from pathlib import Path

import pytest
from _tree_shape import left_out

ROOT = Path(__file__).resolve().parent.parent
POINTER = "openspec/config.yaml"
LEFT_OUT = ("/openspec", "/openspec/**")

needs_pointer = pytest.mark.skipif(
    left_out(POINTER),
    reason=f"no {POINTER}: .gitattributes export-ignores openspec/, so a release archive leaves it out",
)


def _read(name: str) -> str:
    return (ROOT / name).read_text(encoding="utf-8")


@needs_pointer
def test_openspec_holds_only_the_pointer():
    found = sorted(str(p.relative_to(ROOT)) for p in (ROOT / "openspec").rglob("*") if p.is_file())
    assert found == [POINTER], found


@needs_pointer
def test_the_pointer_names_the_sessionkit_store_and_nothing_else():
    assert _read(POINTER) == "store: sessionkit\n"


def test_no_spec_or_change_content_is_in_the_tree():
    for name in ("specs", "changes", "RATIFICATION.md"):
        assert not (ROOT / "openspec" / name).exists(), name


def test_gitattributes_leaves_openspec_out_of_the_archive():
    lines = _read(".gitattributes").splitlines()
    for path in LEFT_OUT:
        assert f"{path} export-ignore" in lines, path
    # The old per-path lines went with the specs.
    assert not [line for line in lines if line.startswith(("/openspec/specs", "/openspec/changes"))]


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


def _git(cwd: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(cwd), *args],
        capture_output=True,
        check=True,
        env=_git_env(),
    )


@needs_pointer
@pytest.mark.skipif(not shutil.which("git"), reason="no git")
def test_the_archive_leaves_openspec_out(tmp_path):
    # A scratch repo with the kit's .gitattributes, the pointer and a README:
    # `git archive` must keep the README and drop every openspec/ path.
    shutil.copy(ROOT / ".gitattributes", tmp_path / ".gitattributes")
    (tmp_path / "openspec").mkdir()
    shutil.copy(ROOT / POINTER, tmp_path / POINTER)
    (tmp_path / "README.md").write_text("kept\n", encoding="utf-8")
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-q", "-m", "scratch")
    archive = _git(tmp_path, "archive", "--format=tar", "HEAD").stdout
    with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
        names = set(tar.getnames())
    assert "README.md" in names
    assert not [n for n in names if n.startswith("openspec")], sorted(names)
    # The control: the pointer is in the commit, so the archive dropped it.
    tracked = set(_git(tmp_path, "ls-files").stdout.decode().split())
    assert POINTER in tracked
