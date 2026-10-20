import re
import tomllib
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

import pytest
from click.testing import CliRunner

from sessionkit import cli
from sessionkit.cli import main

ROOT = Path(__file__).resolve().parent.parent


def test_help() -> None:
    # Under its installed name, as `sessionkit --help` runs: the usage line
    # names the command (SK-103: the docstring no longer starts "sessionkit - ").
    result = CliRunner().invoke(main, ["--help"], prog_name="sessionkit")
    assert result.exit_code == 0
    assert "Usage: sessionkit " in result.output


# SK-58: `sessionkit --version` gave "No such option" (exit 2). It
# prints the kit's installed version, then each family package's, read from
# the installed metadata; a package that is missing says so, no traceback.
@pytest.mark.parametrize("flag", ["--version", "-V"])
def test_version_prints_the_kit_then_each_family_package(flag: str) -> None:
    result = CliRunner().invoke(main, [flag])
    assert result.exit_code == 0, result.output
    lines = result.output.splitlines()
    assert lines[0] == f"sessionkit, version {version('sessionkit')}"
    assert [line.split()[0] for line in lines[1:]] == list(cli.FAMILY)
    for line in lines[1:]:
        name, found = line.split(None, 1)
        assert found == version(name)


def test_version_reads_installed_metadata_not_a_string_in_the_source(monkeypatch) -> None:
    monkeypatch.setattr(cli, "version", lambda dist: f"9.{len(dist)}.0")
    result = CliRunner().invoke(main, ["--version"])
    assert result.exit_code == 0
    assert result.output.splitlines()[0] == "sessionkit, version 9.10.0"
    assert "sessionphone  9.12.0" in result.output


def test_a_missing_family_package_is_reported_not_a_traceback(monkeypatch) -> None:
    real = cli.version

    def fake(dist: str) -> str:
        if dist in ("sessionview", "sessionkit"):
            raise PackageNotFoundError(dist)
        return real(dist)

    monkeypatch.setattr(cli, "version", fake)
    result = CliRunner().invoke(main, ["--version"])
    assert result.exit_code == 0
    assert result.exception is None or isinstance(result.exception, SystemExit)
    assert "Traceback" not in result.output
    lines = result.output.splitlines()
    assert lines[0] == "sessionkit, version not installed"
    assert lines[1 + cli.FAMILY.index("sessionview")].split(None, 1) == [
        "sessionview",
        "not installed",
    ]
    assert len(lines) == 1 + len(cli.FAMILY)


def test_version_lists_exactly_the_family_pyproject_depends_on() -> None:
    deps = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["dependencies"]
    # The PEP 508 name only: the release line writes floors and extras
    # (`sessionmail>=0.1.0`, `sessionvoice[capture]>=0.1.0`).
    names = [re.match(r"[A-Za-z0-9._-]+", d).group(0) for d in deps]
    assert list(cli.FAMILY) == [n for n in names if n.startswith("session")]


def test_help_names_the_version_flag() -> None:
    result = CliRunner().invoke(main, ["--help"])
    assert "-V, --version" in result.output
