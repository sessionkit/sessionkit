"""The published specifications in openspec/specs/, and the archive that ships them.

Each spec is in openspec's spec form: a `## Purpose`, then `## Requirements`,
each `### Requirement:` worded with SHALL or MUST and carrying at least one
`#### Scenario:`. A spec states requirements only: no change-form headings,
no status words, no clock times. The release archive ships openspec/specs/
and leaves out openspec/changes/ and openspec/RATIFICATION.md.
"""
from __future__ import annotations

import io
import os
import re
import shutil
import subprocess
import tarfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SPECS = ("openspec/specs/settings/spec.md", "openspec/specs/tree/spec.md")
LEFT_OUT = ("/openspec/changes", "/openspec/changes/**", "/openspec/RATIFICATION.md")

REQUIREMENT = re.compile(r"^### Requirement: (.+)$", re.MULTILINE)
STATUS_WORDS = re.compile(r"\b(RULED|PROPOSED|OPEN|RATIFIED|DIRECTION)\b")
CLOCK_TIME = re.compile(r"\b[0-2]?[0-9]:[0-5][0-9]\b")
TRACKER_ID = re.compile(r"\b[A-Z]{2,5}-[0-9]+\b")


def _read(name: str) -> str:
    return (ROOT / name).read_text(encoding="utf-8")


def _requirements(text: str) -> list[tuple[str, str]]:
    """Each requirement's title and body, up to the next requirement or `## `."""
    blocks = re.split(r"^(?=### Requirement: |## )", text, flags=re.MULTILINE)
    out = []
    for block in blocks:
        match = REQUIREMENT.match(block)
        if match:
            out.append((match.group(1), block))
    return out


@pytest.mark.parametrize("name", SPECS)
def test_spec_is_in_spec_form_not_change_form(name):
    text = _read(name)
    h2s = re.findall(r"^## (.+)$", text, re.MULTILINE)
    assert h2s == ["Purpose", "Requirements"], h2s
    for form in ("ADDED", "MODIFIED", "REMOVED", "RENAMED"):
        assert f"## {form} Requirements" not in text, form


@pytest.mark.parametrize("name", SPECS)
def test_every_requirement_says_shall_or_must_and_has_a_scenario(name):
    requirements = _requirements(_read(name))
    assert len(requirements) >= 5, f"{name}: only {len(requirements)} requirements"
    for title, body in requirements:
        prose = body.split("#### Scenario:", 1)[0]
        assert re.search(r"\b(SHALL|MUST)\b", prose), f"{name}: {title}"
        assert "#### Scenario:" in body, f"{name}: {title}"


@pytest.mark.parametrize("name", SPECS)
def test_every_scenario_says_when_and_then(name):
    scenarios = re.split(r"^#### Scenario: ", _read(name), flags=re.MULTILINE)[1:]
    assert scenarios
    for scenario in scenarios:
        body = re.split(r"^#{2,3} ", scenario, flags=re.MULTILINE)[0]
        title = scenario.splitlines()[0]
        assert "- **WHEN**" in body and "- **THEN**" in body, f"{name}: {title}"


@pytest.mark.parametrize("name", SPECS)
def test_spec_states_requirements_only(name):
    text = _read(name)
    for pattern in (STATUS_WORDS, CLOCK_TIME, TRACKER_ID):
        assert not pattern.findall(text), f"{name}: {pattern.pattern} {pattern.findall(text)}"


def test_the_requirements_only_check_can_fail():
    # A zero is a receipt only when the same check is shown to hit.
    sample = "### Requirement: Locks (RULED 12:34, AB-12)"
    for pattern in (STATUS_WORDS, CLOCK_TIME, TRACKER_ID):
        assert pattern.findall(sample), pattern.pattern
    assert len(_requirements("### Requirement: a\nx\n### Requirement: b\ny\n")) == 2


def test_no_change_content_is_in_the_tree():
    assert not (ROOT / "openspec" / "changes").exists()
    assert not (ROOT / "openspec" / "RATIFICATION.md").exists()


def test_gitattributes_ships_specs_and_leaves_out_changes():
    lines = _read(".gitattributes").splitlines()
    for path in LEFT_OUT:
        assert f"{path} export-ignore" in lines, path
    assert not [line for line in lines if line.startswith("/openspec/specs")]
    assert "/openspec export-ignore" not in lines
    assert "/openspec/** export-ignore" not in lines


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


@pytest.mark.skipif(not shutil.which("git"), reason="no git")
def test_the_archive_ships_specs_and_drops_changes(tmp_path):
    # A scratch repo with the kit's .gitattributes, the two specs and planted
    # change files: `git archive` must keep the first and drop the second.
    shutil.copy(ROOT / ".gitattributes", tmp_path / ".gitattributes")
    for name in SPECS:
        (tmp_path / name).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(ROOT / name, tmp_path / name)
    planted = ("openspec/changes/x.md", "openspec/changes/y/specs/z/spec.md", "openspec/RATIFICATION.md")
    for name in planted:
        (tmp_path / name).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / name).write_text("planted\n", encoding="utf-8")
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-q", "-m", "scratch")
    archive = _git(tmp_path, "archive", "--format=tar", "HEAD").stdout
    with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
        names = set(tar.getnames())
    for name in SPECS:
        assert name in names, name
    assert not [n for n in names if n.startswith("openspec/changes")], sorted(names)
    assert "openspec/RATIFICATION.md" not in names
    # The control: the same files are in the commit, so the archive dropped them.
    tracked = set(_git(tmp_path, "ls-files").stdout.decode().split())
    assert set(planted) <= tracked
