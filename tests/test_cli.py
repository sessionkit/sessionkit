import re
import tomllib
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

import pytest
from _ruled_deps import APPS as RULED_APPS
from _ruled_deps import FAMILY as RULED_FAMILY
from click.testing import CliRunner
from packaging.requirements import Requirement

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
# prints the kit's installed version, then each family package's, then each
# app's (SK-258: settled), read from the installed metadata; a package that
# is missing says so, no traceback.
@pytest.mark.parametrize("flag", ["--version", "-V"])
def test_version_prints_the_kit_then_each_family_package_then_the_apps(flag: str) -> None:
    result = CliRunner().invoke(main, [flag])
    assert result.exit_code == 0, result.output
    lines = result.output.splitlines()
    assert lines[0] == f"sessionkit, version {version('sessionkit')}"
    assert [line.split()[0] for line in lines[1:]] == [*cli.FAMILY, *cli.APPS]
    assert len(lines) == 1 + len(cli.FAMILY) + len(cli.APPS)
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
        if dist in ("sessionview", "sessionkit", "settled"):
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
    assert lines[-1].split(None, 1) == ["settled", "not installed"]
    assert len(lines) == 1 + len(cli.FAMILY) + len(cli.APPS)


def test_version_lists_exactly_the_family_and_apps_pyproject_depends_on() -> None:
    deps = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["dependencies"]
    # The PEP 508 name only: the release line writes floors and extras
    # (`sessionmail>=0.1.0`, `sessionvoice[capture]>=0.1.0`). Every dependency
    # but click is one --version names, in pyproject order: a new one that is
    # neither family nor app turns this red (SK-258: a `session` prefix filter
    # let settled through unnamed).
    names = [re.match(r"[A-Za-z0-9._-]+", d).group(0) for d in deps]
    assert [*cli.FAMILY, *cli.APPS] == [n for n in names if n != "click"]


def test_the_apps_are_the_ruled_apps_and_not_family() -> None:
    # tests/_ruled_deps.py's APPS rule, by name: settled is not a family
    # package (no plugin, its own version line), so FAMILY, which install.sh's
    # KIT_PLUGINS is held to, stays the five.
    assert list(cli.APPS) == [Requirement(s).name for s in RULED_APPS]
    assert list(cli.FAMILY) == RULED_FAMILY
    assert not set(cli.APPS) & set(cli.FAMILY)


def test_version_lines_keep_the_family_column_install_sh_reads() -> None:
    # install.sh's package_version matches `$1 == NAME` and strips the first
    # field: an app line must be the same two-column shape.
    for line in cli.version_lines()[1:]:
        assert line.startswith("  ")
        assert len(line.split(None, 1)) == 2


def test_help_names_the_version_flag() -> None:
    result = CliRunner().invoke(main, ["--help"])
    assert "-V, --version" in result.output


# `sessionkit hello` was the placeholder verb, a greeting and nothing else.
# It is removed: it is no longer a command, and `-h` does not list it.
def test_hello_is_not_a_command() -> None:
    assert "hello" not in main.commands
    result = CliRunner().invoke(main, ["hello"], prog_name="sessionkit")
    assert result.exit_code == 2
    assert "No such command 'hello'" in result.output


@pytest.mark.parametrize("flag", ["-h", "--help"])
def test_help_does_not_list_hello(flag: str) -> None:
    result = CliRunner().invoke(main, [flag], prog_name="sessionkit")
    assert result.exit_code == 0
    commands = result.output.split("Commands:", 1)[1]
    listed = [line.split()[0] for line in commands.splitlines() if line.strip()]
    assert "hello" not in listed
    assert listed  # the section is still there: the check is not vacuous
    assert "hello" not in result.output.lower()
