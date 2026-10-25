"""scripts/release.py never re-locks (SK-180).

A plain `uv version X` re-locks the project, and the release commits
uv.lock, so a cut before the deps are on PyPI failed, or committed a
local-path lock. These tests pin the fix:

- `uv version` carries --frozen, on the real path and the dry path alike;
- a REAL release, in a throwaway git clone, leaves every line of uv.lock as
  it was except the root `sessionkit` version line, and `uv lock --check`
  (offline) passes after it;
- the root-line edit fails closed: no root block, two, or two version lines
  in it, and the release refuses before `uv version` writes anything;
- `make release` runs the script with python3, never a re-locking `uv run`.

A dry run cannot catch the bug (`uv version --dry-run` never locks), so the
release test is a real one. Every uv call here runs offline (UV_OFFLINE=1)
against an EMPTY cache of its own, so any resolve fails: an offline re-lock
from a warm cache writes the same bytes as the fix when the deps are
unchanged, and would pass unseen. One case also floors a dependency at a
version PyPI does not have, the family-cut case the bug broke.
"""

from __future__ import annotations

import importlib.util
import os
import re
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "release.py"
UV = shutil.which("uv")
GIT = shutil.which("git")
MAKE = shutil.which("make")
# The working-tree files a release reads or writes: the clone gets these as
# they are on disk, so the test checks the code under test, not HEAD's.
OVERLAY = ("scripts/release.py", "pyproject.toml", "uv.lock", "CHANGELOG.md", ".claude-plugin")

needs_uv_git = pytest.mark.skipif(UV is None or GIT is None, reason="uv and git are needed")


def load_release():
    spec = importlib.util.spec_from_file_location("release_under_test", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def env(cwd: Path) -> dict[str, str]:
    """No UV_* from the host (a UV_FROZEN would hide the bug), offline, an
    empty uv cache beside the clone, and a git with no user or system config
    (no signing, no hooks), named here."""
    out = {k: v for k, v in os.environ.items() if not k.startswith(("UV_", "GIT_", "VIRTUAL_ENV"))}
    out.update(
        UV_OFFLINE="1",
        UV_CACHE_DIR=str(cwd.parent / "uv-cache"),
        UV_PYTHON_DOWNLOADS="never",
        GIT_CONFIG_GLOBAL=os.devnull,
        GIT_CONFIG_NOSYSTEM="1",
        GIT_AUTHOR_NAME="release test",
        GIT_AUTHOR_EMAIL="release-test@example.invalid",
        GIT_COMMITTER_NAME="release test",
        GIT_COMMITTER_EMAIL="release-test@example.invalid",
    )
    return out


def run(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=cwd, env=env(cwd), capture_output=True, text=True, check=False)


def git(cwd: Path, *args: str) -> str:
    out = run(cwd, "git", *args)
    assert out.returncode == 0, out.stderr
    return out.stdout


@pytest.fixture
def clone(tmp_path: Path) -> Path:
    """A git clone of this repo with the working tree's release files laid
    over it and committed, so the tree is clean for release.py."""
    repo = tmp_path / "repo"
    git(tmp_path, "clone", "-q", "--no-hardlinks", str(ROOT), str(repo))
    for rel in OVERLAY:
        src, dst = ROOT / rel, repo / rel
        if src.is_dir():
            shutil.rmtree(dst, ignore_errors=True)
            shutil.copytree(src, dst)
        elif src.exists():
            shutil.copy2(src, dst)
    git(repo, "add", "-A", "--", *[r for r in OVERLAY if (repo / r).exists()])
    if git(repo, "status", "--porcelain").strip():
        git(repo, "commit", "-q", "-m", "test: the working tree's release files")
    for tag in git(repo, "tag", "-l").split():
        git(repo, "tag", "-d", tag)
    return repo


def version_of(repo: Path) -> str:
    return tomllib.loads((repo / "pyproject.toml").read_text())["project"]["version"]


def root_line(lock: str) -> str:
    m = re.search(r'^\[\[package\]\]\nname = "sessionkit"\n(version = "[^"]*")\n', lock, re.MULTILINE)
    assert m, "no root sessionkit block in uv.lock"
    return m.group(1)


def with_root(lock: str, old: str, new: str) -> str:
    """`lock` with the root sessionkit version line, and only it, moved to `new`."""
    head = '[[package]]\nname = "sessionkit"\nversion = '
    assert lock.count(f'{head}"{old}"\n') == 1
    return lock.replace(f'{head}"{old}"\n', f'{head}"{new}"\n')


def next_patch(version: str) -> str:
    major, minor, patch = version.split(".")
    return f"{major}.{minor}.{int(patch) + 1}"


# --- the uv call carries --frozen --------------------------------------------


@pytest.mark.parametrize("spec", ["patch", "minor", "major", "9.8.7"])
@pytest.mark.parametrize("dry", [False, True])
def test_uv_version_is_frozen_on_both_paths(monkeypatch, spec: str, dry: bool) -> None:
    release = load_release()
    calls: list[list[str]] = []

    def fake_run(args, **kwargs):
        calls.append(list(args))
        return subprocess.CompletedProcess(args, 0, stdout="sessionkit 0.3.0 => 9.8.7\n", stderr="")

    monkeypatch.setattr(release.subprocess, "run", fake_run)
    assert release.bump(spec, dry) == "9.8.7"
    (argv,) = calls
    assert argv[:2] == ["uv", "version"]
    assert "--frozen" in argv
    assert ("--dry-run" in argv) is dry
    # The dry argv is the real argv plus --dry-run: a rehearsal runs the same call.
    assert [a for a in argv if a != "--dry-run"] == (
        ["uv", "version", "--bump", spec, "--frozen"] if spec in ("patch", "minor", "major")
        else ["uv", "version", spec, "--frozen"]
    )


# --- a real release ------------------------------------------------------------


@needs_uv_git
def test_real_release_changes_only_the_root_lock_line(clone: Path) -> None:
    before = (clone / "uv.lock").read_text()
    old = version_of(clone)
    new = next_patch(old)

    out = run(clone, sys.executable, "scripts/release.py", "patch")
    assert out.returncode == 0, out.stdout + out.stderr

    assert version_of(clone) == new
    after = (clone / "uv.lock").read_text()
    a, b = before.splitlines(keepends=True), after.splitlines(keepends=True)
    assert len(a) == len(b), "uv.lock gained or lost lines: something re-locked"
    changed = [(x, y) for x, y in zip(a, b) if x != y]
    assert changed == [(f'version = "{old}"\n', f'version = "{new}"\n')]
    assert root_line(after) == f'version = "{new}"'  # the changed line IS the root line
    # Nothing resolved: no uv.lock written by uv, so nothing else moved either.
    assert after == with_root(before, old, new)

    # The release committed it and tagged it, and left the tree clean.
    assert git(clone, "status", "--porcelain").strip() == ""
    assert git(clone, "log", "-1", "--format=%s").strip() == f"chore: release v{new}"
    assert git(clone, "tag", "-l", f"v{new}").strip() == f"v{new}"
    assert root_line(git(clone, "show", f"v{new}:uv.lock")) == f'version = "{new}"'
    assert not (clone / ".venv").exists(), "something synced an environment"


@needs_uv_git
def test_release_with_a_floor_pypi_does_not_have(clone: Path) -> None:
    """The family cut: a dependency floored at a release not yet on PyPI. A
    re-lock is unsatisfiable here; the release must not need one."""
    pyproject = clone / "pyproject.toml"
    text = pyproject.read_text()
    floored = re.sub(r'"sessionphone\[media\]>=[^"]+"', '"sessionphone[media]>=99.0.0"', text, count=1)
    assert floored != text
    pyproject.write_text(floored)
    git(clone, "commit", "-q", "-am", "test: floor a dep at an unreleased version")
    before = (clone / "uv.lock").read_text()
    old = version_of(clone)
    new = next_patch(old)

    out = run(clone, sys.executable, "scripts/release.py", "patch")
    assert out.returncode == 0, out.stdout + out.stderr

    assert (clone / "uv.lock").read_text() == with_root(before, old, new)
    assert root_line((clone / "uv.lock").read_text()) == f'version = "{new}"'
    assert git(clone, "status", "--porcelain").strip() == ""
    assert not (clone / ".venv").exists(), "something synced an environment"


@needs_uv_git
def test_lock_check_passes_offline_after_the_release(clone: Path) -> None:
    pre = run(clone, "uv", "lock", "--check")
    if pre.returncode != 0:
        pytest.skip(f"uv lock --check does not pass offline before the release: {pre.stderr.strip()}")
    out = run(clone, sys.executable, "scripts/release.py", "patch")
    assert out.returncode == 0, out.stdout + out.stderr
    check = run(clone, "uv", "lock", "--check")
    assert check.returncode == 0, check.stderr
    assert git(clone, "status", "--porcelain").strip() == ""


@needs_uv_git
def test_dry_run_reports_the_lock_edit_and_writes_nothing(clone: Path) -> None:
    files = ("pyproject.toml", "uv.lock", "CHANGELOG.md")
    before = {f: (clone / f).read_bytes() for f in files}
    old = version_of(clone)
    new = next_patch(old)

    out = run(clone, sys.executable, "scripts/release.py", "patch", "--dry-run")
    assert out.returncode == 0, out.stdout + out.stderr
    assert "--frozen" in out.stdout
    assert f"uv.lock: root version {old} -> {new}" in out.stdout
    assert {f: (clone / f).read_bytes() for f in files} == before
    assert git(clone, "status", "--porcelain").strip() == ""
    assert git(clone, "tag", "-l").strip() == ""


# --- the root-line edit fails closed -------------------------------------------

ROOT_BLOCK = re.compile(r'^\[\[package\]\]\nname = "sessionkit"\n.*?(?=^\[\[package\]\]$|\Z)', re.MULTILINE | re.DOTALL)


def no_root(lock: str) -> str:
    return ROOT_BLOCK.sub("", lock, count=1)


def two_roots(lock: str) -> str:
    block = ROOT_BLOCK.search(lock).group(0)
    return lock + "\n" + block


def two_versions(lock: str) -> str:
    return re.sub(r'^(name = "sessionkit"\nversion = "[^"]*"\n)', r'\1version = "0.0.0"\n', lock, count=1, flags=re.MULTILINE)


def not_the_root_source(lock: str) -> str:
    """The sessionkit block present, but sourced from an index: not the project."""
    return re.sub(
        r'^(name = "sessionkit"\nversion = "[^"]*"\n)source = \{ editable = "\." \}$',
        r'\1source = { registry = "https://pypi.org/simple" }',
        lock,
        count=1,
        flags=re.MULTILINE,
    )


@pytest.mark.parametrize(
    "mangle, says",
    [
        (no_root, "has 0 root [[package]] blocks"),
        (two_roots, "has 2 root [[package]] blocks"),
        (two_versions, "has 2 version lines"),
        (not_the_root_source, "has 0 root [[package]] blocks"),
    ],
)
@pytest.mark.parametrize("dry", [False, True])
@needs_uv_git
def test_a_bad_lock_is_refused_before_anything_is_written(clone: Path, mangle, says: str, dry: bool) -> None:
    lock = clone / "uv.lock"
    mangled = mangle(lock.read_text())
    assert mangled != lock.read_text()
    lock.write_text(mangled)
    git(clone, "commit", "-q", "-am", "test: a lock release.py must refuse")
    files = ("pyproject.toml", "uv.lock", "CHANGELOG.md", ".claude-plugin/plugin.json")
    before = {f: (clone / f).read_bytes() for f in files if (clone / f).exists()}
    head = git(clone, "rev-parse", "HEAD")

    out = run(clone, sys.executable, "scripts/release.py", "patch", *(["--dry-run"] if dry else []))

    assert out.returncode != 0
    assert says in out.stderr
    assert "nothing was written" in out.stderr
    assert "uv version" not in out.stdout  # refused BEFORE uv ran
    assert {f: (clone / f).read_bytes() for f in before} == before
    assert git(clone, "status", "--porcelain").strip() == ""
    assert git(clone, "rev-parse", "HEAD") == head
    assert git(clone, "tag", "-l").strip() == ""


def test_lock_root_finds_the_one_version_value() -> None:
    release = load_release()
    lock = (ROOT / "uv.lock").read_text()
    start, end = release.lock_root(lock, "sessionkit")
    assert lock[start:end] == version_of(ROOT)
    assert lock[:start].endswith('[[package]]\nname = "sessionkit"\nversion = "')


def test_missing_lock_is_refused(tmp_path: Path, monkeypatch) -> None:
    release = load_release()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["release.py", "patch"])
    real_run = subprocess.run
    monkeypatch.setattr(
        release.subprocess,
        "run",
        lambda args, **kw: subprocess.CompletedProcess(args, 0, stdout="", stderr="")
        if args[:2] == ["git", "status"]
        else real_run(args, **kw),
    )
    with pytest.raises(SystemExit, match="uv.lock not found"):
        release.main()


# --- make release ----------------------------------------------------------------


def release_recipe() -> list[str]:
    lines = (ROOT / "Makefile").read_text().splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith("release:"))
    recipe = []
    for line in lines[start + 1 :]:
        if not line.startswith("\t"):
            break
        recipe.append(line)
    return recipe


def test_make_release_recipe_has_no_relocking_uv_run() -> None:
    recipe = release_recipe()
    assert recipe, "Makefile has no release: recipe"
    for line in recipe:
        assert not re.search(r"\buv\s+run\b(?!.*--no-project)", line), line
    assert any("scripts/release.py" in line for line in recipe)


@pytest.mark.skipif(MAKE is None, reason="make is not installed")
def test_make_release_expands_to_python3() -> None:
    out = subprocess.run(
        [str(MAKE), "-C", str(ROOT), "--no-print-directory", "-n", "release", "VERSION=9.9.9"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert out.returncode == 0, out.stderr
    assert out.stdout.strip() == "python3 scripts/release.py 9.9.9"
