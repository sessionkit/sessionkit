"""`make scan` finds its scanner: SESSIONKIT_SCAN, else release-scan on the PATH.

The scanner is private and never lives in this repo, so these tests run the
real Makefile against a stub. Each run gets a PATH built here and nowhere
else: a stub directory (when the case wants one) and a directory of links to
the few tools the Makefile itself needs. A release-scan installed on the host
can never leak into a case.
"""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
MAKE = shutil.which("make")
# What the Makefile needs to parse and run `scan`: SHELL is `env bash`, and
# SHELLSCRIPTS is computed at parse time with git, xargs, awk and sort.
TOOLS = ("bash", "env", "git", "xargs", "awk", "sort")
MESSAGE = "SESSIONKIT_SCAN is unset and release-scan is not on the PATH"

pytestmark = pytest.mark.skipif(MAKE is None, reason="make is not installed")


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


def stub(directory: Path, name: str, record: Path) -> Path:
    """A scanner that writes its own path and argv to `record`, then exits 0."""
    directory.mkdir(parents=True, exist_ok=True)
    script = directory / name
    script.write_text(f'#!/bin/sh\nprintf "%s\\n" "$0" "$@" > "{record}"\n', encoding="utf-8")
    script.chmod(0o755)
    return script


def run_scan(
    path: list[Path], *make_args: str, scan_env: str | None = None
) -> subprocess.CompletedProcess[str]:
    """`make scan` on PATH `path`; SESSIONKIT_SCAN in the environment only if given."""
    env = {k: v for k, v in os.environ.items() if k != "SESSIONKIT_SCAN"}
    env["PATH"] = os.pathsep.join(str(p) for p in path)
    if scan_env is not None:
        env["SESSIONKIT_SCAN"] = scan_env
    return subprocess.run(
        [str(MAKE), "-C", str(ROOT), "--no-print-directory", "scan", *make_args],
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )


def test_unset_var_falls_back_to_release_scan_on_the_path(tmp_path: Path, tools: Path) -> None:
    record = tmp_path / "argv"
    on_path = stub(tmp_path / "stubs", "release-scan", record)

    result = run_scan([tmp_path / "stubs", tools])

    assert result.returncode == 0, result.stderr
    assert record.read_text(encoding="utf-8").splitlines() == [
        str(on_path),
        "--here",
        "--fail-on",
        "P0",
    ]


def test_explicit_var_beats_the_path(tmp_path: Path, tools: Path) -> None:
    record = tmp_path / "argv"
    stub(tmp_path / "stubs", "release-scan", record)
    chosen = stub(tmp_path / "chosen", "my-scan", record)

    result = run_scan([tmp_path / "stubs", tools], f"SESSIONKIT_SCAN={chosen}")

    assert result.returncode == 0, result.stderr
    assert record.read_text(encoding="utf-8").splitlines()[0] == str(chosen)


def test_explicit_var_from_the_environment_beats_the_path(tmp_path: Path, tools: Path) -> None:
    record = tmp_path / "argv"
    stub(tmp_path / "stubs", "release-scan", record)
    chosen = stub(tmp_path / "chosen", "my-scan", record)

    result = run_scan([tmp_path / "stubs", tools], scan_env=str(chosen))

    assert result.returncode == 0, result.stderr
    assert record.read_text(encoding="utf-8").splitlines()[0] == str(chosen)


def test_neither_exits_2_naming_both_lookups(tmp_path: Path, tools: Path) -> None:
    result = run_scan([tools])

    assert result.returncode == 2, (result.stdout, result.stderr)
    assert MESSAGE in result.stderr


def test_scanner_failure_fails_the_target(tmp_path: Path, tools: Path) -> None:
    stubs = tmp_path / "stubs"
    stubs.mkdir()
    failing = stubs / "release-scan"
    failing.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
    failing.chmod(0o755)

    result = run_scan([stubs, tools])

    assert result.returncode != 0
