"""`make validate` runs the strict plugin check on what ships, not on the checkout.

The shipped tree is `git archive HEAD`, and .gitattributes leaves the root
CLAUDE.md out of it. The validator flags that file, so validating the checkout
fails on a file no user receives. Each test copies the real Makefile and
.gitattributes into a throwaway git repo and runs `make validate` there, with
a fake `claude` on a PATH built here and nowhere else. The fake records its
argv and what is in the dir it was given, then exits with the status the case
asks for. A real `claude` on the host can never reach a case.

make itself exits 2 when any recipe line fails, so a non-zero claude status
shows up as make's `Error N` line, and make's own status is non-zero.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
MAKE = shutil.which("make")
# What the Makefile needs to parse and run `validate`: SHELL is `env bash`,
# SHELLSCRIPTS is computed at parse time with git, xargs, awk and sort, and
# the recipe uses mktemp, tar and rm. The fake claude uses ls.
TOOLS = ("bash", "env", "git", "xargs", "awk", "sort", "mktemp", "tar", "rm", "ls")
MISSING = "validate: claude is not on the PATH"

pytestmark = pytest.mark.skipif(
    MAKE is None or not shutil.which("git"), reason="make or git is not installed"
)


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


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(repo), *args], check=True, capture_output=True, env=_git_env()
    )


@pytest.fixture
def tools(tmp_path: Path) -> Path:
    bin_dir = tmp_path / "tools"
    bin_dir.mkdir()
    for name in TOOLS:
        found = shutil.which(name)
        if found is None:
            pytest.skip(f"{name} is not installed")
        (bin_dir / name).symlink_to(found)
    return bin_dir


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A committed repo shaped like the kit's root, plus one untracked file."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    shutil.copy(ROOT / "Makefile", repo / "Makefile")
    shutil.copy(ROOT / ".gitattributes", repo / ".gitattributes")
    (repo / "CLAUDE.md").write_text("@AGENTS.md\n", encoding="utf-8")
    (repo / "AGENTS.md").write_text("# AGENTS.md\n", encoding="utf-8")
    (repo / ".claude-plugin").mkdir()
    (repo / ".claude-plugin" / "plugin.json").write_text(
        '{"name": "x"}\n', encoding="utf-8"
    )
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "fixture")
    # Not committed, so not in HEAD's archive.
    (repo / "untracked.txt").write_text("x\n", encoding="utf-8")
    return repo


@pytest.fixture
def temp_root(tmp_path: Path) -> Path:
    """TMPDIR for the run, so the test can see the recipe's temp dir go."""
    path = tmp_path / "tmp"
    path.mkdir()
    return path


def fake_claude(directory: Path, record: Path, status: int) -> None:
    """A claude that records argv, its dir and that dir's listing, then exits `status`."""
    directory.mkdir(parents=True, exist_ok=True)
    record.mkdir(parents=True, exist_ok=True)
    script = directory / "claude"
    script.write_text(
        "#!/bin/sh\n"
        f'printf "%s\\n" "$@" > "{record}/argv"\n'
        'dir="$3"\n'
        f'printf "%s\\n" "$dir" > "{record}/dir"\n'
        f'ls -A "$dir" > "{record}/listing"\n'
        f"exit {status}\n",
        encoding="utf-8",
    )
    script.chmod(0o755)


def run_validate(
    where: Path, path: list[Path], temp_root: Path
) -> subprocess.CompletedProcess[str]:
    env = _git_env()
    env["PATH"] = os.pathsep.join(str(p) for p in path)
    env["TMPDIR"] = str(temp_root)
    return subprocess.run(
        [str(MAKE), "-C", str(where), "--no-print-directory", "validate"],
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )


def test_it_validates_the_archive_strictly(
    tmp_path: Path, tools: Path, repo: Path, temp_root: Path
) -> None:
    record = tmp_path / "record"
    fake_claude(tmp_path / "fakes", record, 0)

    result = run_validate(repo, [tmp_path / "fakes", tools], temp_root)

    assert result.returncode == 0, result.stdout + result.stderr
    argv = (record / "argv").read_text(encoding="utf-8").splitlines()
    validated = (record / "dir").read_text(encoding="utf-8").strip()
    assert argv == ["plugin", "validate", validated, "--strict"]
    # The validated dir is a fresh temp dir under TMPDIR, not the checkout.
    assert Path(validated).parent == temp_root
    assert Path(validated).name.startswith("sessionkit-validate.")
    listing = (record / "listing").read_text(encoding="utf-8").splitlines()
    assert ".claude-plugin" in listing
    assert "AGENTS.md" in listing and "Makefile" in listing
    # export-ignored, so not in the archive
    assert "CLAUDE.md" not in listing
    # not committed, so not in HEAD's archive
    assert "untracked.txt" not in listing


@pytest.mark.parametrize("status", [0, 1, 3])
def test_claudes_status_is_makes_and_the_temp_dir_goes(
    tmp_path: Path, tools: Path, repo: Path, temp_root: Path, status: int
) -> None:
    fake_claude(tmp_path / "fakes", tmp_path / "record", status)

    result = run_validate(repo, [tmp_path / "fakes", tools], temp_root)

    if status == 0:
        assert result.returncode == 0, result.stdout + result.stderr
    else:
        assert result.returncode != 0
        assert f"[validate] Error {status}" in result.stderr
    assert list(temp_root.iterdir()) == []


def test_no_claude_on_the_path_exits_2_with_a_message(
    tools: Path, repo: Path, temp_root: Path
) -> None:
    result = run_validate(repo, [tools], temp_root)

    assert result.returncode == 2, (result.stdout, result.stderr)
    assert MISSING in result.stderr
    assert list(temp_root.iterdir()) == []


def test_outside_a_git_repo_it_fails_before_claude_and_cleans_up(
    tmp_path: Path, tools: Path, temp_root: Path
) -> None:
    plain = tmp_path / "plain"
    plain.mkdir()
    shutil.copy(ROOT / "Makefile", plain / "Makefile")
    record = tmp_path / "record"
    fake_claude(tmp_path / "fakes", record, 0)

    result = run_validate(plain, [tmp_path / "fakes", tools], temp_root)

    assert result.returncode != 0
    assert "validate: could not extract git archive HEAD" in result.stderr
    assert not (record / "argv").exists()
    assert list(temp_root.iterdir()) == []
