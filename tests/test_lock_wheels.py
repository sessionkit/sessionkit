"""Every wheel-only package in uv.lock installs on every Python the kit declares (SK-92).

The kit declares a `requires-python` range, and PyPI advertises it. A
package in the lock that ships wheels but NO sdist can only be installed
where one of its wheels fits, so the declared range is only true while
every such package has a wheel for every CPython minor version in it.
This test reads uv.lock (tomllib) and pyproject.toml and checks exactly that.

The rules:

- **Wheel-only**: the lock entry has `wheels` and no `sdist`. A package with
  an sdist can build where no wheel fits, so it is never a gap here.
- **What a wheel covers**: a `py3` (or `py2.py3`) tag covers every minor
  version; `pyXY` covers 3.Y and later. An `abi3` wheel covers its own
  minor version and every later one. Otherwise only the exact `cpXY` tag
  counts: `cp313` covers 3.13 and nothing else, and a free-threaded ABI
  (`cp313t`) does not cover a regular 3.13. Other interpreters (`pp*`) are
  not CPython and cover nothing here.
- **Which minor versions are checked**: those the declared `requires-python`
  admits. A capped range (`>=3.11,<3.15`) is finite and checked in full. An
  UNCAPPED range (`>=3.11`) is checked up to the highest CPython minor
  version that any wheel in the lock names (a `cpXY` tag), and never below
  3.15: a floor of 3.15, so an uncapped kit is always asked about the next
  CPython even when no wheel in the lock names it yet.
- **Environment markers**: the check walks the lock's dependency graph from
  the kit (its dependencies, the extras it asks for, and its dependency
  groups) once per minor version, and follows an edge only when its marker
  can hold on that version. Python markers (`python_full_version`,
  `python_version`) are evaluated exactly. Every other marker (platform,
  implementation) is tried on each of a few representative CPython
  platforms, and the edge counts when ANY of them admits it. So a
  `sys_platform == 'win32'` package is checked on the Pythons Windows
  installs: pywin32 is wheel-only with cp311-cp315 wheels, so it is not a
  gap. Wheel PLATFORM tags are not checked: this test is about the Python
  range, not about which platforms each package ships for.
- **uv's resolution-markers forks**: when the lock holds one package at
  several versions (one per fork), each version is reached only through the
  edges whose markers pick it, and is further limited to the minor versions
  its own `resolution-markers` admit. Each fork is checked only on its own
  Pythons.

A failure names each package, its version and the minor versions it has no
wheel for.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

from packaging.markers import Marker
from packaging.specifiers import SpecifierSet

ROOT = Path(__file__).resolve().parent.parent

# The floor for an uncapped range: the highest minor version checked is at
# least 3.15 (see the module docstring).
UNCAPPED_FLOOR = 15

# Representative CPython platforms. A non-Python marker holds on a minor
# version when it holds on ANY of these.
PLATFORMS = [
    {
        "sys_platform": "linux",
        "platform_system": "Linux",
        "os_name": "posix",
        "platform_machine": "x86_64",
    },
    {
        "sys_platform": "linux",
        "platform_system": "Linux",
        "os_name": "posix",
        "platform_machine": "aarch64",
    },
    {
        "sys_platform": "darwin",
        "platform_system": "Darwin",
        "os_name": "posix",
        "platform_machine": "arm64",
    },
    {
        "sys_platform": "darwin",
        "platform_system": "Darwin",
        "os_name": "posix",
        "platform_machine": "x86_64",
    },
    {
        "sys_platform": "win32",
        "platform_system": "Windows",
        "os_name": "nt",
        "platform_machine": "AMD64",
    },
]


def _environment(minor: int, platform: dict) -> dict:
    full = f"3.{minor}.0"
    return {
        "implementation_name": "cpython",
        "implementation_version": full,
        "platform_python_implementation": "CPython",
        "platform_release": "",
        "platform_version": "",
        "python_full_version": full,
        "python_version": f"3.{minor}",
        "extra": "",
        **platform,
    }


def marker_admits(marker: str | None, minor: int) -> bool:
    """True when `marker` can hold on CPython 3.<minor> on some platform."""
    if not marker:
        return True
    parsed = Marker(marker)
    return any(parsed.evaluate(_environment(minor, p)) for p in PLATFORMS)


def declared_minors(requires_python: str, lock: dict) -> list[int]:
    """The CPython 3.x minor versions `requires_python` admits (rule: docstring)."""
    spec = SpecifierSet(requires_python)

    def admits(minor: int) -> bool:
        return any(spec.contains(f"3.{minor}.{patch}") for patch in range(50))

    if admits(999):  # uncapped
        top = max([UNCAPPED_FLOOR, *named_minors(lock)])
    else:
        top = 99
    return [m for m in range(top + 1) if admits(m)]


def _wheel_tags(url: str) -> tuple[list[str], list[str]]:
    """(python tags, abi tags) from a wheel's filename."""
    name = url.rsplit("/", 1)[-1].removesuffix(".whl")
    parts = name.split("-")
    return parts[-3].split("."), parts[-2].split(".")


def named_minors(lock: dict) -> set[int]:
    """Every minor version a `cpXY` wheel tag in the lock names."""
    found = set()
    for pkg in lock.get("package", []):
        for wheel in pkg.get("wheels", []):
            for tag in _wheel_tags(wheel["url"])[0]:
                if m := re.fullmatch(r"cp3(\d+)", tag):
                    found.add(int(m.group(1)))
    return found


def wheel_covers(url: str, minor: int) -> bool:
    """True when the wheel at `url` installs on CPython 3.<minor> (rule: docstring)."""
    pys, abis = _wheel_tags(url)
    for py in pys:
        if py in ("py3", "py2.py3"):
            return True
        if (m := re.fullmatch(r"py3(\d+)", py)) and minor >= int(m.group(1)):
            return True
        if m := re.fullmatch(r"cp3(\d+)", py):
            tagged = int(m.group(1))
            if "abi3" in abis and minor >= tagged:
                return True
            if minor == tagged and any(
                a == "none" or re.fullmatch(r"cp3\d+", a) for a in abis
            ):
                return True
    return False


def _key(pkg: dict) -> tuple[str, str]:
    return pkg["name"], pkg.get("version", "")


def _root(lock: dict, name: str) -> dict:
    for pkg in lock["package"]:
        if pkg["name"] == name and set(pkg.get("source", {})) & {"editable", "virtual"}:
            return pkg
    raise AssertionError(f"uv.lock has no editable/virtual entry for {name}")


def _resolve(lock: dict, edge: dict, minor: int) -> list[dict]:
    """The lock entries an edge names, limited to those admitted on 3.<minor>."""
    hits = [
        p
        for p in lock["package"]
        if p["name"] == edge["name"]
        and ("version" not in edge or p.get("version") == edge["version"])
    ]
    return [
        p
        for p in hits
        if not p.get("resolution-markers")
        or any(marker_admits(m, minor) for m in p["resolution-markers"])
    ]


def reachable(lock: dict, root_name: str, minor: int) -> list[dict]:
    """The lock entries installed on 3.<minor>, walking from the root package."""
    root = _root(lock, root_name)
    first = list(root.get("dependencies", []))
    for group in root.get("dev-dependencies", {}).values():
        first.extend(group)
    extras_seen: dict[tuple[str, str], set[str]] = {}
    found: dict[tuple[str, str], dict] = {}
    queue: list[list[dict]] = [first]
    while queue:
        for edge in queue.pop(0):
            if not marker_admits(edge.get("marker"), minor):
                continue
            extras = set(edge.get("extra", []))
            for pkg in _resolve(lock, edge, minor):
                key = _key(pkg)
                if key in extras_seen and extras <= extras_seen[key]:
                    continue
                extras_seen[key] = extras_seen.get(key, set()) | extras
                found[key] = pkg
                edges = list(pkg.get("dependencies", []))
                for extra in extras:
                    edges.extend(pkg.get("optional-dependencies", {}).get(extra, []))
                queue.append(edges)
    return list(found.values())


def wheel_gaps(lock: dict, requires_python: str, root_name: str) -> list[str]:
    """One line per wheel-only package lacking a wheel on a declared minor version."""
    missing: dict[tuple[str, str], list[int]] = {}
    for minor in declared_minors(requires_python, lock):
        for pkg in reachable(lock, root_name, minor):
            wheels = pkg.get("wheels", [])
            if not wheels or "sdist" in pkg:
                continue
            if not any(wheel_covers(w["url"], minor) for w in wheels):
                missing.setdefault(_key(pkg), []).append(minor)
    return [
        f"{name} {version}: no wheel and no sdist for "
        + ", ".join(f"3.{m}" for m in minors)
        for (name, version), minors in sorted(missing.items())
    ]


# --- the kit's own lock ------------------------------------------------------


def test_every_wheel_only_package_covers_the_declared_range() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]
    lock = tomllib.loads((ROOT / "uv.lock").read_text())
    gaps = wheel_gaps(lock, project["requires-python"], project["name"])
    assert not gaps, (
        f"requires-python = {project['requires-python']!r} admits a Python that "
        "a wheel-only package in uv.lock cannot install on:\n  " + "\n  ".join(gaps)
    )


# --- the rules, on small hand-made locks --------------------------------------


def _wheel(name: str, tag: str) -> dict:
    return {"url": f"https://files.example/{name}-1.0-{tag}-any.whl"}


def _lock(*packages: dict, root_deps: list[dict], **root: object) -> dict:
    kit = {
        "name": "kit",
        "version": "0.1.0",
        "source": {"editable": "."},
        "dependencies": root_deps,
        **root,
    }
    return {"package": [kit, *packages]}


def _pkg(
    name: str, *tags: str, version: str = "1.0", sdist: bool = False, **extra: object
) -> dict:
    pkg = {
        "name": name,
        "version": version,
        "source": {"registry": "x"},
        "wheels": [_wheel(name, t) for t in tags],
        **extra,
    }
    if sdist:
        pkg["sdist"] = {"url": f"https://files.example/{name}-1.0.tar.gz"}
    return pkg


CP11_14 = ("cp311-cp311", "cp312-cp312", "cp313-cp313", "cp314-cp314")


def test_uncapped_range_runs_to_the_floor_then_the_highest_named_minor() -> None:
    lock = _lock(_pkg("a", *CP11_14), root_deps=[{"name": "a"}])
    assert declared_minors(">=3.11", lock) == [11, 12, 13, 14, 15]
    lock["package"].append(_pkg("b", "cp317-cp317"))
    assert declared_minors(">=3.11", lock) == [11, 12, 13, 14, 15, 16, 17]
    assert declared_minors(">=3.11,<3.15", lock) == [11, 12, 13, 14]


def test_a_cp_only_package_is_a_gap_past_its_last_wheel() -> None:
    lock = _lock(_pkg("onnx", *CP11_14), root_deps=[{"name": "onnx"}])
    assert wheel_gaps(lock, ">=3.11", "kit") == [
        "onnx 1.0: no wheel and no sdist for 3.15"
    ]
    assert wheel_gaps(lock, ">=3.11,<3.15", "kit") == []
    assert wheel_gaps(lock, ">=3.10,<3.15", "kit") == [
        "onnx 1.0: no wheel and no sdist for 3.10"
    ]


def test_py3_abi3_and_sdist_cover_and_free_threaded_does_not() -> None:
    lock = _lock(
        _pkg("pure", "py3-none"),
        _pkg("both", "py2.py3-none"),
        _pkg("stable", "cp312-abi3"),
        _pkg("built", "cp311-cp311", sdist=True),
        _pkg("ft", "cp311-cp311", "cp312-cp312", "cp313-cp313", "cp314-cp314t"),
        root_deps=[{"name": n} for n in ("pure", "both", "stable", "built", "ft")],
    )
    assert wheel_gaps(lock, ">=3.11,<3.15", "kit") == [
        "ft 1.0: no wheel and no sdist for 3.14",
        "stable 1.0: no wheel and no sdist for 3.11",
    ]


def test_a_win32_marker_is_checked_on_windows_and_pywin32_is_no_gap() -> None:
    pywin32 = _pkg("pywin32", *CP11_14, "cp315-cp315", version="312")
    lock = _lock(
        pywin32, root_deps=[{"name": "pywin32", "marker": "sys_platform == 'win32'"}]
    )
    assert wheel_gaps(lock, ">=3.11", "kit") == []
    # The marker does not hide a real gap: Windows installs 3.15 too.
    pywin32["wheels"].pop()
    assert wheel_gaps(lock, ">=3.11", "kit") == [
        "pywin32 312: no wheel and no sdist for 3.15"
    ]
    # A marker no platform admits is never followed.
    lock["package"][0]["dependencies"] = [
        {"name": "pywin32", "marker": "sys_platform == 'emscripten'"}
    ]
    assert wheel_gaps(lock, ">=3.11", "kit") == []


def test_a_python_marker_limits_the_minor_versions_checked() -> None:
    lock = _lock(
        _pkg("backport", "cp311-cp311", "cp312-cp312"),
        root_deps=[{"name": "backport", "marker": "python_full_version < '3.13'"}],
    )
    assert wheel_gaps(lock, ">=3.11", "kit") == []


def test_each_resolution_fork_is_checked_only_on_its_own_pythons() -> None:
    old = _pkg(
        "np",
        "cp311-cp311",
        version="2.4",
        **{"resolution-markers": ["python_full_version < '3.12'"]},
    )
    new = _pkg(
        "np",
        "cp312-cp312",
        "cp313-cp313",
        "cp314-cp314",
        version="2.5",
        **{"resolution-markers": ["python_full_version >= '3.12'"]},
    )
    lock = _lock(
        old,
        new,
        root_deps=[
            {"name": "np", "version": "2.4", "marker": "python_full_version < '3.12'"},
            {"name": "np", "version": "2.5", "marker": "python_full_version >= '3.12'"},
        ],
    )
    assert wheel_gaps(lock, ">=3.11,<3.15", "kit") == []
    assert wheel_gaps(lock, ">=3.11", "kit") == [
        "np 2.5: no wheel and no sdist for 3.15"
    ]
    # resolution-markers alone also bound a fork, even behind an unmarked edge.
    lock["package"][0]["dependencies"] = [{"name": "np"}]
    assert wheel_gaps(lock, ">=3.11,<3.15", "kit") == []


def test_extras_and_transitive_dependencies_are_followed() -> None:
    voice = {
        "name": "voice",
        "version": "0.1",
        "source": {"registry": "x"},
        "sdist": {"url": "u"},
        "dependencies": [{"name": "mid"}],
        "optional-dependencies": {
            "capture": [{"name": "onnx"}],
            "other": [{"name": "unused"}],
        },
    }
    mid = {
        "name": "mid",
        "version": "1",
        "source": {"registry": "x"},
        "sdist": {"url": "u"},
        "dependencies": [{"name": "deep"}],
    }
    lock = _lock(
        voice,
        mid,
        _pkg("onnx", *CP11_14),
        _pkg("deep", *CP11_14),
        _pkg("unused", "cp311-cp311"),
        root_deps=[{"name": "voice", "extra": ["capture"]}],
    )
    assert wheel_gaps(lock, ">=3.11", "kit") == [
        "deep 1.0: no wheel and no sdist for 3.15",
        "onnx 1.0: no wheel and no sdist for 3.15",
    ]


def test_dependency_groups_are_checked() -> None:
    lock = _lock(
        _pkg("tool", *CP11_14),
        root_deps=[],
        **{"dev-dependencies": {"dev": [{"name": "tool"}]}},
    )
    assert wheel_gaps(lock, ">=3.11", "kit") == [
        "tool 1.0: no wheel and no sdist for 3.15"
    ]
