"""`make install-dev`: the whole kit from the checkouts beside it.

scripts/install_dev.py builds ONE `uv tool install`: this checkout
--editable, four siblings --with-editable, sessionview --with (built), each an
absolute path, the extras as the kit's pyproject names them, always
--reinstall and --python. It checks every sibling before uv runs, and after a
real install reads the env to say where each package came from.

Every case runs against fake sibling checkouts in tmp_path, with a fake `uv`
first on a PATH built here. The fake logs each call to a file, so "uv was
never called" is a file that does not exist. On `uv tool install` it writes a
fake tool env shaped like uv's (dist-info and direct_url.json per package),
from the flags it was given, so the report is read from an env, not the plan.
A real uv, and a real tool env, can never be reached from these tests.
"""

from __future__ import annotations

import importlib.util
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "install_dev.py"
SIBLINGS = [
    "sessionmail",
    "sessiontools",
    "sessionphone",
    "sessionvoice",
    "sessionview",
]
SIX = ["sessionkit", *SIBLINGS]

_spec = importlib.util.spec_from_file_location("install_dev", SCRIPT)
install_dev = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(install_dev)

FAKE_UV = r'''#!PYTHON
"""A fake uv: logs argv; `tool dir` prints FAKE_TOOL_DIR; `tool install` writes a fake env."""
import json, os, re, sys, tomllib
from pathlib import Path

with open(os.environ["FAKE_UV_LOG"], "a", encoding="utf-8") as log:
    log.write(json.dumps(sys.argv[1:]) + "\n")
args = sys.argv[1:]
tools = Path(os.environ["FAKE_TOOL_DIR"])
if args[:2] == ["tool", "dir"]:
    print(tools)
    sys.exit(0)
if args[:2] == ["tool", "install"]:
    status = int(os.environ.get("FAKE_UV_EXIT", "0"))
    if status:
        sys.exit(status)
    site = tools / "sessionkit" / "lib" / "python3.14" / "site-packages"
    site.mkdir(parents=True, exist_ok=True)
    flags = {"--editable": True, "--with-editable": True, "--with": False}
    for flag, value in zip(args, args[1:]):
        if flag not in flags:
            continue
        path = Path(re.sub(r"\[[^\]]*\]$", "", value))
        name = tomllib.loads((path / "pyproject.toml").read_text())["project"]["name"]
        editable = flags[flag] or name in os.environ.get("FAKE_UV_EDITABLE", "").split()
        info = site / f"{name}-0.3.3.dist-info"
        info.mkdir(exist_ok=True)
        dir_info = {"editable": True} if editable else {}
        (info / "direct_url.json").write_text(json.dumps({"url": path.as_uri(), "dir_info": dir_info}))
    sys.exit(0)
sys.exit(99)
'''


def _sibling(src: Path, folder: str, name: str | None = None) -> Path:
    path = src / folder
    path.mkdir(parents=True)
    (path / "pyproject.toml").write_text(
        f'[project]\nname = "{name or folder}"\nversion = "0.3.3"\n', encoding="utf-8"
    )
    return path


@pytest.fixture
def src(tmp_path: Path) -> Path:
    """A folder of clones: the five siblings, each a minimal pyproject."""
    src = tmp_path / "clones"
    for name in SIBLINGS:
        _sibling(src, name)
    return src


@pytest.fixture
def env(tmp_path: Path) -> dict[str, str]:
    """The fake uv first on PATH; its log and tool dir in tmp_path; no SRC/PYTHON leaking in."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    uv = bin_dir / "uv"
    uv.write_text(FAKE_UV.replace("PYTHON", sys.executable, 1), encoding="utf-8")
    uv.chmod(0o755)
    out = {
        k: v
        for k, v in os.environ.items()
        if k not in {"SRC", "PYTHON", "DRY_RUN", "MAKEFLAGS"}
    }
    out.update(
        PATH=f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
        FAKE_UV_LOG=str(tmp_path / "uv.log"),
        FAKE_TOOL_DIR=str(tmp_path / "tools"),
    )
    return out


def _run(
    env: dict[str, str], *args: str, cwd: Path = ROOT
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        env=env,
        cwd=cwd,
        check=False,
    )


def _uv_calls(env: dict[str, str]) -> list[list[str]]:
    log = Path(env["FAKE_UV_LOG"])
    if not log.exists():
        return []
    return [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines()]


def _printed_command(out: str) -> list[str]:
    lines = out.splitlines()
    return shlex.split(lines[lines.index("uv command:") + 1])


def _kit_python() -> str:
    return re.search(
        r"^KIT_PYTHON=(\S+)$", (ROOT / "install.sh").read_text(), re.MULTILINE
    ).group(1)


# --- the dry run: the exact command, nothing run ---------------------------------


def test_dry_run_prints_the_whole_command_and_calls_no_uv(
    src: Path, env: dict[str, str]
) -> None:
    result = _run(env, "--src", str(src), "--dry-run")
    assert result.returncode == 0, result.stderr
    argv = _printed_command(result.stdout)
    assert argv == [
        "uv", "tool", "install", "--reinstall", "--python", _kit_python(),
        "--editable", str(ROOT),
        "--with-editable", str(src / "sessionmail"),
        "--with-editable", str(src / "sessiontools"),
        "--with-editable", f"{src / 'sessionphone'}[media]",
        "--with-editable", f"{src / 'sessionvoice'}[capture]",
        "--with", str(src / "sessionview"),
    ]  # fmt: skip
    assert "--force" not in argv
    assert "dry run: nothing was installed." in result.stdout
    assert _uv_calls(env) == []
    assert not Path(env["FAKE_TOOL_DIR"]).exists()


def test_every_checkout_is_absolute_even_from_a_relative_src(
    src: Path, env: dict[str, str]
) -> None:
    # A bare name is read by uv as a package name and installed from the
    # index, so a relative SRC must still reach uv as absolute paths.
    result = _run(env, "--src", "clones", "--dry-run", cwd=src.parent)
    assert result.returncode == 0, result.stderr
    argv = _printed_command(result.stdout)
    paths = [
        argv[i + 1]
        for i, a in enumerate(argv)
        if a in {"--editable", "--with-editable", "--with"}
    ]
    assert len(paths) == 6
    for path in paths:
        assert Path(re.sub(r"\[[^\]]*\]$", "", path)).is_absolute(), path
    assert str(src / "sessionview") in paths


def test_the_extras_are_the_ones_the_kit_pyproject_names() -> None:
    assert install_dev.kit_extras() == {
        "sessionphone": "[media]",
        "sessionvoice": "[capture]",
        "settled": "[kit]",
    }


def test_python_overrides_the_kit_pin(src: Path, env: dict[str, str]) -> None:
    result = _run(env, "--src", str(src), "--python", "3.13", "--dry-run")
    assert result.returncode == 0, result.stderr
    argv = _printed_command(result.stdout)
    assert argv[argv.index("--python") + 1] == "3.13"
    assert "python:    3.13\n" in result.stdout


def test_the_default_python_is_kit_python_from_install_sh() -> None:
    assert install_dev.kit_python() == _kit_python()


# --- SRC: --src, else $SRC, else this repo's parent ----------------------------------


def test_src_from_the_environment_is_honoured(src: Path, env: dict[str, str]) -> None:
    result = _run({**env, "SRC": str(src)}, "--dry-run")
    assert result.returncode == 0, result.stderr
    assert str(src / "sessionmail") in _printed_command(result.stdout)


def test_src_defaults_to_this_repos_parent(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SRC", raising=False)
    assert install_dev.src_dir(None) == ROOT.parent.resolve()


def test_src_flag_beats_the_environment(
    src: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SRC", str(tmp_path / "elsewhere"))
    assert install_dev.src_dir(str(src)) == src.resolve()


# --- the checks: a miss is named, and uv is never called --------------------------


@pytest.mark.parametrize("dry", [True, False], ids=["dry-run", "real"])
def test_a_missing_sibling_fails_by_name_and_uv_is_not_called(
    src: Path, env: dict[str, str], dry: bool
) -> None:
    shutil.rmtree(src / "sessionphone")
    result = _run(env, "--src", str(src), *(["--dry-run"] if dry else []))
    assert result.returncode == 1
    assert f"sessionphone: no checkout at {src / 'sessionphone'}" in result.stderr
    assert "uv command:" not in result.stdout
    assert _uv_calls(env) == []


@pytest.mark.parametrize("dry", [True, False], ids=["dry-run", "real"])
def test_a_wrong_named_sibling_fails_by_name_and_uv_is_not_called(
    src: Path, env: dict[str, str], dry: bool
) -> None:
    shutil.rmtree(src / "sessionview")
    _sibling(src, "sessionview", name="sessionviewer")
    result = _run(env, "--src", str(src), *(["--dry-run"] if dry else []))
    assert result.returncode == 1
    assert (
        f"sessionview: {src / 'sessionview'} is 'sessionviewer', not sessionview"
        in result.stderr
    )
    assert _uv_calls(env) == []


def test_every_miss_is_named_not_just_the_first(src: Path, env: dict[str, str]) -> None:
    shutil.rmtree(src / "sessionmail")
    (src / "sessiontools" / "pyproject.toml").unlink()
    (src / "sessionvoice" / "pyproject.toml").write_text(
        "[project]\n", encoding="utf-8"
    )
    result = _run(env, "--src", str(src))
    assert result.returncode == 1
    assert f"sessionmail: no checkout at {src / 'sessionmail'}" in result.stderr
    assert f"sessiontools: no pyproject.toml in {src / 'sessiontools'}" in result.stderr
    assert (
        "sessionvoice: " in result.stderr
        and "no readable [project].name" in result.stderr
    )
    assert _uv_calls(env) == []


def test_a_sibling_named_with_another_spelling_of_its_name_passes(src: Path) -> None:
    # A pyproject name is compared normalised (case, and runs of - _ .), as
    # packaging tools compare it.
    (src / "sessionmail" / "pyproject.toml").write_text(
        '[project]\nname = "SessionMail"\n'
    )
    assert install_dev.check(src) == []


# --- a real run: the report is read from the env -----------------------------------


def test_a_real_run_reports_five_editable_and_sessionview_built(
    src: Path, env: dict[str, str]
) -> None:
    result = _run(env, "--src", str(src))
    assert result.returncode == 0, result.stdout + result.stderr
    calls = _uv_calls(env)
    assert calls[0] == _printed_command(result.stdout)[1:]
    assert calls[1] == ["tool", "dir"]
    rows = dict(
        re.findall(r"^  (session\w+) +0\.3\.3 +(\w+) ", result.stdout, re.MULTILINE)
    )
    assert rows == {
        "sessionkit": "editable",
        "sessionmail": "editable",
        "sessiontools": "editable",
        "sessionphone": "editable",
        "sessionvoice": "editable",
        "sessionview": "built",
    }
    assert (
        f"sessionview   0.3.3            built     {src / 'sessionview'}"
        in result.stdout
    )
    assert "a running process keeps the code it" in result.stdout
    assert (
        "Claude Code sessions" in result.stdout
        and "ears services install" in result.stdout
    )


def test_an_env_that_differs_from_the_plan_fails_and_says_so(
    src: Path, env: dict[str, str]
) -> None:
    # The fake uv installs sessionview editable: the report reads the env, so
    # it sees that, marks the row and exits 1.
    result = _run({**env, "FAKE_UV_EDITABLE": "sessionview"}, "--src", str(src))
    assert result.returncode == 1
    assert re.search(
        r"^  sessionview .* editable .*<- expected built from",
        result.stdout,
        re.MULTILINE,
    )
    assert "does not hold what was asked for" in result.stderr


def test_a_uv_failure_is_passed_on(src: Path, env: dict[str, str]) -> None:
    result = _run({**env, "FAKE_UV_EXIT": "2"}, "--src", str(src))
    assert result.returncode == 1
    assert "uv exited 2" in result.stderr
    assert "came from" not in result.stdout


@pytest.mark.parametrize("dry", [True, False], ids=["dry-run", "real"])
def test_a_python3_without_tomllib_is_refused_by_name_and_uv_is_not_called(
    src: Path, env: dict[str, str], dry: bool
) -> None:
    # The Makefile runs python3, and a stock macOS python3 is 3.9: no tomllib.
    # Simulated as the release tests do: tomllib blocked in sys.modules.
    no_tomllib = (
        "import runpy, sys; sys.modules['tomllib'] = None; "
        f"sys.argv = [{str(SCRIPT)!r}, *sys.argv[1:]]; "
        f"runpy.run_path({str(SCRIPT)!r}, run_name='__main__')"
    )
    result = subprocess.run(
        [sys.executable, "-c", no_tomllib, "--src", str(src)]
        + (["--dry-run"] if dry else []),
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    assert result.returncode == 2
    assert "install_dev: needs Python 3.11+ (tomllib)" in result.stderr
    assert "Traceback" not in result.stderr
    assert result.stdout == ""
    assert _uv_calls(env) == []


def test_came_from_reads_index_editable_built_and_missing(tmp_path: Path) -> None:
    site = tmp_path / "env" / "lib" / "python3.14" / "site-packages"
    site.mkdir(parents=True)
    (site / "sessionkit-0.3.3.dist-info").mkdir()  # no direct_url.json: the index
    for name, dir_info in (("sessionmail", {"editable": True}), ("sessionview", {})):
        info = site / f"{name}-0.3.4.dist-info"
        info.mkdir()
        url = (tmp_path / "a dir" / name).as_uri()
        (info / "direct_url.json").write_text(
            json.dumps({"url": url, "dir_info": dir_info})
        )
    rows = install_dev.came_from(tmp_path / "env")
    assert rows["sessionkit"] == ("0.3.3", "index", "")
    assert rows["sessionmail"] == (
        "0.3.4",
        "editable",
        str(tmp_path / "a dir" / "sessionmail"),
    )
    assert rows["sessionview"] == (
        "0.3.4",
        "built",
        str(tmp_path / "a dir" / "sessionview"),
    )
    assert rows["sessiontools"] == ("-", "missing", "")


# --- the Makefile -------------------------------------------------------------------

MAKE = shutil.which("make")
needs_make = pytest.mark.skipif(MAKE is None, reason="make is not installed")


def test_the_target_name_sits_on_one_makefile_line() -> None:
    lines = [
        line
        for line in (ROOT / "Makefile").read_text().splitlines()
        if "install-dev" in line
    ]
    assert len(lines) == 1
    assert lines[0].startswith("install-dev:  ## ")


def test_make_install_is_unchanged() -> None:
    text = (ROOT / "Makefile").read_text()
    recipe = re.search(r"^install:  ##[^\n]*\n((?:\t[^\n]*\n)+)", text, re.MULTILINE)
    assert recipe and recipe.group(0) == (
        "install:  ## put sessionkit on the PATH, editable (uv tool install -e .)\n"
        "\t@uv tool install -e .\n"
    )


@needs_make
def test_make_passes_src_python_and_dry_run(src: Path, env: dict[str, str]) -> None:
    result = subprocess.run(
        [
            MAKE,
            "-s",
            "-C",
            str(ROOT),
            "install-dev",
            f"SRC={src}",
            "PYTHON=3.13",
            "DRY_RUN=1",
        ],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    argv = _printed_command(result.stdout)
    assert argv[argv.index("--python") + 1] == "3.13"
    assert str(src / "sessionview") in argv
    assert _uv_calls(env) == []


@needs_make
def test_make_fails_by_name_on_a_missing_sibling(
    src: Path, env: dict[str, str]
) -> None:
    shutil.rmtree(src / "sessionvoice")
    result = subprocess.run(
        [MAKE, "-s", "-C", str(ROOT), "install-dev", f"SRC={src}"],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    assert result.returncode != 0
    assert f"sessionvoice: no checkout at {src / 'sessionvoice'}" in result.stderr
    assert _uv_calls(env) == []
