"""scripts/check_agents_archive.py: AGENTS.md ships in the archive and stands alone.

The rule is in docs/family-docs-agents.md. Each test builds a
throwaway git repo, so what is checked is what `git archive HEAD` ships: an
export-ignored path is gone, exactly as in a release. The kit's own
AGENTS.md must pass.
"""

from __future__ import annotations

import importlib.util
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from _tree_shape import family_doc

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "check_agents_archive.py"
CONVENTIONS, needs_conventions = family_doc("docs/family-docs-agents.md")

_spec = importlib.util.spec_from_file_location("check_agents_archive", SCRIPT)
cae = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cae)

pytestmark = pytest.mark.skipif(not shutil.which("git"), reason="git is not installed")


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
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        env=_git_env(),
    )


def make_repo(tmp_path: Path, files: dict[str, str]) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    for name, text in files.items():
        path = repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "fixture")
    return repo


def run(repo: Path, *args: str, capsys) -> tuple[int, str]:
    code = cae.main([str(repo), *args])
    return code, capsys.readouterr().out


GOOD = {
    "AGENTS.md": (
        "# AGENTS.md\n\nRead [the README](README.md) and [docs](docs/guide.md#top).\n"
        "The CLI is `src/pkg/cli.py`; tests are in `tests/`. Run `make test`.\n"
        "Upstream: [site](https://example.com/x.md), [anchor](#rules).\n"
        "Edit `cli.py` and `pyproject.toml`.\n\n"
        "```bash\nls missing/dir/   # code blocks are not checked\n```\n\n"
        "[ref]: docs/guide.md\n"
    ),
    "README.md": "# x\n",
    "docs/guide.md": "# guide\n",
    "src/pkg/cli.py": "",
    "tests/test_x.py": "",
    "pyproject.toml": "",
}


def test_a_standalone_agents_md_passes(tmp_path, capsys) -> None:
    code, out = run(make_repo(tmp_path, GOOD), capsys=capsys)
    assert code == 0, out
    assert "0 dead reference(s)" in out


def test_an_export_ignored_agents_md_fails(tmp_path, capsys) -> None:
    files = {**GOOD, ".gitattributes": "/AGENTS.md export-ignore\n"}
    code, out = run(make_repo(tmp_path, files), capsys=capsys)
    assert code == 1
    assert "export-ignored" in out


def test_no_agents_md_fails(tmp_path, capsys) -> None:
    code, out = run(make_repo(tmp_path, {"README.md": "# x\n"}), capsys=capsys)
    assert code == 1
    assert "no AGENTS.md" in out


def test_a_link_into_an_export_ignored_dir_fails(tmp_path, capsys) -> None:
    files = {
        **GOOD,
        "AGENTS.md": "See [the specs](openspec/specs/) first.\n",
        "openspec/specs/a.md": "x\n",
        ".gitattributes": "/openspec export-ignore\n/openspec/** export-ignore\n",
    }
    code, out = run(make_repo(tmp_path, files), capsys=capsys)
    assert code == 1
    assert "line 1: link openspec/specs/ is not in the archive" in out


def test_the_same_link_passes_when_the_dir_ships(tmp_path, capsys) -> None:
    files = {
        **GOOD,
        "AGENTS.md": "See [the specs](openspec/specs/) first.\n",
        "openspec/specs/a.md": "x\n",
    }
    code, out = run(make_repo(tmp_path, files), capsys=capsys)
    assert code == 0, out


def test_a_backticked_path_the_archive_lacks_fails(tmp_path, capsys) -> None:
    files = {
        **GOOD,
        "AGENTS.md": "`docs/internal/` is build history.\n",
        "docs/internal/x.md": "x\n",
        ".gitattributes": "docs/internal/ export-ignore\n/docs/internal/** export-ignore\n",
    }
    code, out = run(make_repo(tmp_path, files), capsys=capsys)
    assert code == 1
    assert "path `docs/internal/` is not in the archive" in out


def test_reference_style_links_are_checked(tmp_path, capsys) -> None:
    files = {**GOOD, "AGENTS.md": "Read [the record][r].\n\n[r]: gone/RECORD.md\n"}
    code, out = run(make_repo(tmp_path, files), capsys=capsys)
    assert code == 1
    assert "line 3: link gone/RECORD.md is not in the archive" in out


@pytest.mark.parametrize(
    "target", ["../sibling/README.md", "/etc/hosts", "~/notes/note.md"]
)
def test_a_link_out_of_the_archive_fails(tmp_path, capsys, target) -> None:
    files = {**GOOD, "AGENTS.md": f"See [x]({target}).\n"}
    code, out = run(make_repo(tmp_path, files), capsys=capsys)
    assert code == 1
    assert "points outside the archive" in out


def test_fleet_lines_are_listed_not_failed(tmp_path, capsys) -> None:
    files = {**GOOD, "AGENTS.md": "Fixed in ABC-346, on build-01.\nUTF-8 text.\n"}
    code, out = run(make_repo(tmp_path, files), "--host", "build-01", capsys=capsys)
    assert code == 0, out
    assert "LOOK fleet? line 1:" in out
    # A pattern cannot tell a task id from UTF-8: listed for a human, too.
    assert "LOOK fleet? line 2:" in out


def test_strict_fails_on_fleet_lines(tmp_path, capsys) -> None:
    files = {**GOOD, "AGENTS.md": "Ask the build-01 seat.\n"}
    code, out = run(
        make_repo(tmp_path, files), "--host", "build-01", "--strict", capsys=capsys
    )
    assert code == 1
    assert "FAIL fleet? line 1:" in out


def test_no_host_names_ship_in_the_check() -> None:
    # Hosts come from the caller; with none given, a host-only line is clean.
    assert cae.host_pattern([]) is None
    _, fleet = cae.check("Ask the build-01 seat.\n", set())
    assert fleet == []


def test_hosts_come_from_the_flag_and_the_env(tmp_path, capsys, monkeypatch) -> None:
    files = {**GOOD, "AGENTS.md": "On build-01.\nOn ci-runner.\nOn build-010.\n"}
    repo = make_repo(tmp_path, files)
    monkeypatch.setenv(cae.HOSTS_ENV, "ci-runner, unused")
    code, out = run(repo, "--host", "build-01", "--strict", capsys=capsys)
    assert code == 1
    assert "line 1:" in out and "line 2:" in out
    # A host name matches as a whole word: build-010 is not build-01.
    assert "line 3:" not in out


def test_a_path_that_is_not_a_repo_exits_2(tmp_path, capsys) -> None:
    code = cae.main([str(tmp_path)])
    assert code == 2
    assert "check_agents_archive" in capsys.readouterr().err


@pytest.mark.parametrize(
    "span",
    [
        "make test",
        "sessionkit --version",
        "## [Unreleased]",
        "src/<package>/",
        "$HOME/x.md",
        "--ref",
        "0.1.0",
    ],
)
def test_spans_that_are_not_paths_are_skipped(span) -> None:
    assert cae.code_path(span) is None


def test_the_ref_flag_reads_an_older_commit(tmp_path, capsys) -> None:
    repo = make_repo(tmp_path, GOOD)
    (repo / "AGENTS.md").write_text("See [x](gone.md).\n", encoding="utf-8")
    _git(repo, "commit", "-qam", "break it")
    assert run(repo, capsys=capsys)[0] == 1
    assert run(repo, "--ref", "HEAD~1", capsys=capsys)[0] == 0


@pytest.mark.skipif(
    subprocess.run(
        ["git", "-C", str(ROOT), "rev-parse", "--git-dir"],
        capture_output=True,
        check=False,
    ).returncode
    != 0,
    reason="not a git checkout",
)
def test_the_kits_own_agents_md_passes() -> None:
    out = subprocess.run(
        [sys.executable, str(SCRIPT), str(ROOT), "--strict"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert out.returncode == 0, out.stdout + out.stderr


# The rule's item in docs/family-docs-agents.md, pinned to the words it ships.


def _items() -> list[str]:
    """Each `- [ ]` item of the doc, from its line to the next item or H2."""
    return re.findall(
        r"^- \[ \] .*?(?=^- \[ \]|^## |\Z)", CONVENTIONS, re.MULTILINE | re.DOTALL
    )


def _rule_index() -> int:
    for i, item in enumerate(_items()):
        if item.startswith("- [ ] **`AGENTS.md` ships in the release archive"):
            return i
    raise AssertionError("family-docs-agents.md has no AGENTS.md-ships item")


def _rule() -> str:
    return " ".join(_items()[_rule_index()].split())


@needs_conventions
def test_rule_sits_after_the_agents_md_item() -> None:
    before = _items()[_rule_index() - 1]
    assert before.startswith("- [ ] **`AGENTS.md` holds the instructions")


@needs_conventions
def test_rule_says_when_ruled_and_what_confirms_it() -> None:
    assert (
        "Ruled 2030-06-09, building on the owner's "
        "2030-06-07 AGENTS.md ruling; the owner's merge confirms it." in _rule()
    )


@needs_conventions
def test_rule_has_both_halves() -> None:
    rule = _rule()
    assert "AGENTS.md is not export-ignored" in rule
    assert "names no host, task id, person or fleet seat" in rule
    assert "below the `@AGENTS.md` import" in rule


@needs_conventions
def test_rule_check_names_this_script() -> None:
    assert "`python3 scripts/check_agents_archive.py <repo>`" in _rule()
    assert "`--host NAME`" in _rule()
    assert "--strict" in _rule()
