#!/usr/bin/env python3
"""Install the whole kit from the checkouts beside this one.

    python3 scripts/install_dev.py [--src DIR] [--python VER] [--dry-run]

One `uv tool install` puts all six packages in the `sessionkit` tool env:

    sessionkit                                  this checkout, --editable
    sessionmail sessiontools sessionphone sessionvoice
                                                DIR/<name>, --with-editable
    sessionview                                 DIR/<name>, --with (built)

DIR is the folder that holds your clones: --src, else $SRC, else this repo's
parent (the same rule as scripts/command_docs.py). settled and click are not
checkouts; they come from the package index, as in any install.

Why each part of the command is what it is:

- sessionview is BUILT, never editable. Its commands run files from a
  `_data` folder that only a build makes, so an editable sessionview fails
  every one of them. A built copy does not follow your edits: run this again
  to pick them up.
- Every run is `--reinstall`. Without it, dropping a checkout leaves the old
  copy in place while uv's record says otherwise. `--reinstall` rebuilds in
  place; `--force` would delete the env folder, with files uv did not write,
  and take over commands another tool owns.
- Every checkout is an ABSOLUTE path. A bare name (`sessionview`) is read as
  a package name and installed from the index, with exit 0 and no warning.
- `--python` is always passed: the kit's own pin (KIT_PYTHON in install.sh)
  unless --python names another. Without it uv picks a Python itself, and
  that pick ignores the kit's requires-python.
- The extras ride on the checkout requirements exactly as the kit's
  pyproject.toml names them (`sessionphone[media]`, `sessionvoice[capture]`).

Before uv runs, each checkout is checked: the folder exists and its
pyproject.toml's [project].name is that package. Any miss is named, with the
path looked at, and uv is never called. --dry-run runs the checks, prints the
uv command, and changes nothing.

After the install, it reads the env itself and prints where each of the six
packages came from (editable, built or index, with the path), then what to
restart: a process that is already running keeps the code it started with.

Exit status: 0 done; 1 a check failed, uv failed, or the env does not hold
what was asked for; 2 usage, uv is not on the PATH, or python3 is older than
3.11 (no tomllib).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote, urlparse

# `make install-dev` runs this with python3, and a stock macOS python3 is 3.9,
# which has no tomllib. Every path here reads a pyproject.toml, so say so and
# stop, before uv runs, rather than end in a traceback.
try:
    import tomllib
except ModuleNotFoundError:
    print(
        f"install_dev: needs Python 3.11+ (tomllib); {sys.executable} is "
        f"{sys.version.split()[0]}. Put a python3 of 3.11 or newer first on the "
        "PATH and run it again; uv was not run.",
        file=sys.stderr,
    )
    sys.exit(2)

ROOT = Path(__file__).resolve().parent.parent

KIT = "sessionkit"
#: the siblings, in the order they are passed to uv, and how each is installed
SIBLINGS = {
    "sessionmail": "editable",
    "sessiontools": "editable",
    "sessionphone": "editable",
    "sessionvoice": "editable",
    # its commands need the _data folder only a build makes (see above)
    "sessionview": "built",
}
PACKAGES = [KIT, *SIBLINGS]
TOOL = KIT

RESTART_NOTE = """\
Restart what is already running: a running process keeps the code it
started with, so it does not see this install until it starts again.
  - Claude Code sessions: each one runs its own pager monitor. Restart them.
  - voice: run `ears services install` again (its service files name a
    script path that moves when sessionvoice switches between editable and
    built), then `sessionkit service restart all`.
  - phone: `sessionkit service restart all` restarts its services too.
Commands you run from now on, and Claude Code hooks, use the new code."""


def say(line: str = "") -> None:
    print(line, flush=True)


def fail(line: str) -> None:
    print(line, file=sys.stderr, flush=True)


def src_dir(arg: str | None) -> Path:
    """The folder of checkouts: --src, else $SRC, else this repo's parent; absolute."""
    return Path(arg or os.environ.get("SRC") or ROOT.parent).expanduser().resolve()


def kit_python() -> str:
    """The kit's own Python pin: KIT_PYTHON in install.sh, the one place it is set."""
    text = (ROOT / "install.sh").read_text(encoding="utf-8")
    match = re.search(r"^KIT_PYTHON=([0-9][0-9.]*)\s*$", text, re.MULTILINE)
    if not match:
        raise SystemExit(
            "install_dev: no KIT_PYTHON=<version> line in install.sh; pass --python"
        )
    return match.group(1)


def kit_extras() -> dict[str, str]:
    """package -> its extras as the kit's dependencies name them, e.g. '[media]'."""
    deps = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))[
        "project"
    ]["dependencies"]
    out = {}
    for dep in deps:
        match = re.match(r"\s*([A-Za-z0-9_.-]+)\s*(\[[^\]]*\])?", dep)
        if match and match.group(2):
            out[match.group(1).lower()] = re.sub(r"\s+", "", match.group(2))
    return out


def checkout(name: str, src: Path) -> Path:
    return ROOT if name == KIT else src / name


def project_name(path: Path) -> str | None:
    """[project].name of the pyproject.toml in PATH, or None when there is none to read."""
    try:
        return tomllib.loads((path / "pyproject.toml").read_text(encoding="utf-8"))[
            "project"
        ]["name"]
    except (OSError, tomllib.TOMLDecodeError, KeyError, TypeError):
        return None


def normal(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def check(src: Path) -> list[str]:
    """One line per checkout that is missing or is not the package it should be."""
    problems = []
    for name in PACKAGES:
        path = checkout(name, src)
        if not path.is_dir():
            problems.append(f"  {name}: no checkout at {path}")
            continue
        if not (path / "pyproject.toml").is_file():
            problems.append(f"  {name}: no pyproject.toml in {path}")
            continue
        found = project_name(path)
        if found is None:
            problems.append(
                f"  {name}: {path}/pyproject.toml has no readable [project].name"
            )
        elif normal(found) != name:
            problems.append(f"  {name}: {path} is {found!r}, not {name}")
    return problems


def command(src: Path, python: str) -> list[str]:
    """The one uv command: every checkout absolute, extras as the kit names them."""
    extras = kit_extras()
    argv = [
        "uv",
        "tool",
        "install",
        "--reinstall",
        "--python",
        python,
        "--editable",
        f"{ROOT}{extras.get(KIT, '')}",
    ]
    for name, mode in SIBLINGS.items():
        flag = "--with-editable" if mode == "editable" else "--with"
        argv += [flag, f"{checkout(name, src)}{extras.get(name, '')}"]
    return argv


def tool_env() -> Path:
    """The sessionkit tool env, where `uv tool dir` says tools live."""
    out = subprocess.run(
        ["uv", "tool", "dir"], capture_output=True, text=True, check=True
    ).stdout.strip()
    return Path(out) / TOOL


def came_from(env: Path) -> dict[str, tuple[str, str, str]]:
    """package -> (version, how, where), read from the env's own dist-info.

    how is `editable` or `built` (from a local folder), `index` (no
    direct_url.json: the package index), `url` for any other direct source,
    or `missing` when the env has no such package.
    """
    dist_infos: dict[str, Path] = {}
    for site in sorted(env.glob("lib/python*/site-packages")) + sorted(
        env.glob("Lib/site-packages")
    ):
        for info in site.glob("*.dist-info"):
            dist, _, version = info.name.removesuffix(".dist-info").partition("-")
            dist_infos.setdefault(normal(dist), info)
    out = {}
    for name in PACKAGES:
        info = dist_infos.get(name)
        if info is None:
            out[name] = ("-", "missing", "")
            continue
        version = info.name.removesuffix(".dist-info").partition("-")[2]
        direct = info / "direct_url.json"
        if not direct.is_file():
            out[name] = (version, "index", "")
            continue
        data = json.loads(direct.read_text(encoding="utf-8"))
        url = data.get("url", "")
        parsed = urlparse(url)
        where = unquote(parsed.path) if parsed.scheme == "file" else url
        if "dir_info" in data and parsed.scheme == "file":
            how = "editable" if data["dir_info"].get("editable") else "built"
        else:
            how = "url"
        out[name] = (version, how, where)
    return out


def report(env: Path, src: Path) -> bool:
    """Print where each package came from; True when each is as asked."""
    expected = {
        KIT: ("editable", ROOT),
        **{n: (m, checkout(n, src)) for n, m in SIBLINGS.items()},
    }
    rows = came_from(env)
    ok = True
    say(f"came from (read from {env}):")
    for name in PACKAGES:
        version, how, where = rows[name]
        want_how, want_path = expected[name]
        mark = ""
        if how != want_how or Path(where).resolve() != want_path.resolve():
            ok = False
            mark = f"   <- expected {want_how} from {want_path}"
        say(f"  {name:<13} {version:<16} {how:<9} {where}{mark}".rstrip())
    return ok


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--src",
        help="the folder that holds your clones (default: $SRC, else this repo's parent)",
    )
    parser.add_argument(
        "--python",
        help="the Python for the tool env (default: KIT_PYTHON in install.sh)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="run the checks and print the uv command; change nothing",
    )
    args = parser.parse_args(argv)

    src = src_dir(args.src)
    python = args.python or kit_python()
    say(f"checkouts: {src} (this kit: {ROOT})")
    say(f"python:    {python}" + ("" if args.python else " (KIT_PYTHON in install.sh)"))

    problems = check(src)
    if problems:
        fail("install_dev: these checkouts are missing or wrong, so uv was not run:")
        for line in problems:
            fail(line)
        fail("Clone each one beside this repo, or name their folder with SRC=<dir>.")
        return 1

    argv_uv = command(src, python)
    say("uv command:")
    say("  " + shlex.join(argv_uv))
    if args.dry_run:
        say("dry run: nothing was installed.")
        return 0

    if shutil.which("uv") is None:
        fail(
            "install_dev: uv is not on the PATH; install uv first (https://docs.astral.sh/uv/)"
        )
        return 2
    status = subprocess.run(argv_uv, check=False).returncode
    if status != 0:
        fail(f"install_dev: uv exited {status}; the env is as uv left it.")
        return 1

    ok = report(tool_env(), src)
    say()
    say(RESTART_NOTE)
    if not ok:
        fail(
            "install_dev: the env does not hold what was asked for (see the rows marked above)."
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
