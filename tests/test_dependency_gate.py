"""The dependency gate: the kit's dependencies never drift from the ruled list.

The ruled list lives in tests/_ruled_deps.py, with the ruling beside it. This
gate holds three places to it, because each one is read by someone different:

- **pyproject.toml**: what the maintainer edits.
- **the built wheel's METADATA** (`Requires-Dist`): what a stranger's
  `pip install sessionkit` or `uv tool install sessionkit` resolves from. The
  lock never reaches a stranger, so the wheel is checked on its own.
- **uv.lock**: what `make test` and every gate run against. A lock that
  disagrees with pyproject makes every other gate measure the wrong install.

Any drift goes RED with a message naming the package and the drift: a child
missing, an extra dropped, a floor that is not the ruled one. The last test
plants each kind of drift into the ruled list and checks the gate names it, so
the gate cannot quietly lose its power.
"""

from __future__ import annotations

import shutil
import subprocess
import tomllib
import zipfile
from email.parser import Parser
from pathlib import Path

import pytest
from _ruled_deps import FAMILY, RULED, drift
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name
from packaging.version import Version

ROOT = Path(__file__).resolve().parent.parent
PYPI = "https://pypi.org/simple"


def _fail_on(problems: list[str]) -> None:
    if problems:
        pytest.fail(
            "dependencies drifted from the ruled list (tests/_ruled_deps.py):\n  "
            + "\n  ".join(problems),
            pytrace=False,
        )


def _pyproject_deps() -> list[str]:
    return tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))[
        "project"
    ]["dependencies"]


def _lock() -> dict:
    return tomllib.loads((ROOT / "uv.lock").read_text(encoding="utf-8"))


def _locked(lock: dict, name: str) -> list[dict]:
    want = canonicalize_name(name)
    return [p for p in lock.get("package", []) if canonicalize_name(p["name"]) == want]


def _lock_requires_dist(kit: dict) -> list[str]:
    """The kit's own requires-dist as uv.lock recorded it, as requirement strings."""
    out = []
    for entry in kit.get("metadata", {}).get("requires-dist", []):
        extras = entry.get("extras", [])
        spec = (
            entry["name"]
            + (f"[{','.join(extras)}]" if extras else "")
            + entry.get("specifier", "")
        )
        if entry.get("marker"):
            spec += f"; {entry['marker']}"
        out.append(spec)
    return out


# --- pyproject.toml ---------------------------------------------------------


def test_pyproject_carries_the_ruled_list() -> None:
    _fail_on(drift(_pyproject_deps(), "pyproject.toml"))


# --- the built wheel ----------------------------------------------------------


@pytest.fixture(scope="module")
def wheel_metadata(tmp_path_factory: pytest.TempPathFactory) -> str:
    """METADATA of a wheel built from this tree, as `make build` builds it."""
    uv = shutil.which("uv")
    if uv is None:
        pytest.fail(
            "uv is not on the PATH: the wheel half of the dependency gate builds the wheel with uv",
            pytrace=False,
        )
    out = tmp_path_factory.mktemp("wheel")
    run = subprocess.run(
        [uv, "build", "--wheel", "--quiet", "--out-dir", str(out), str(ROOT)],
        capture_output=True,
        text=True,
        check=False,
    )
    if run.returncode != 0:
        pytest.fail(
            f"uv build --wheel failed (exit {run.returncode}):\n{run.stderr or run.stdout}",
            pytrace=False,
        )
    wheels = sorted(out.glob("*.whl"))
    assert len(wheels) == 1, f"expected one wheel, built {[w.name for w in wheels]}"
    with zipfile.ZipFile(wheels[0]) as zf:
        (name,) = [n for n in zf.namelist() if n.endswith(".dist-info/METADATA")]
        return zf.read(name).decode("utf-8")


def test_built_wheel_requires_dist_carries_the_ruled_list(wheel_metadata: str) -> None:
    requires = (
        Parser().parsestr(wheel_metadata, headersonly=True).get_all("Requires-Dist")
        or []
    )
    _fail_on(drift(requires, "the built wheel's METADATA Requires-Dist"))


def test_built_wheel_matches_pyproject(wheel_metadata: str) -> None:
    # Every Requires-Dist line is a pyproject dependency and the reverse: the
    # build adds nothing and drops nothing.
    requires = (
        Parser().parsestr(wheel_metadata, headersonly=True).get_all("Requires-Dist")
        or []
    )
    built = {str(Requirement(r)) for r in requires}
    declared = {str(Requirement(d)) for d in _pyproject_deps()}
    assert built == declared, (
        f"wheel only: {sorted(built - declared)}; pyproject only: {sorted(declared - built)}"
    )


# --- uv.lock ------------------------------------------------------------------


def test_lock_records_the_ruled_list() -> None:
    (kit,) = _locked(_lock(), "sessionkit")
    _fail_on(drift(_lock_requires_dist(kit), "uv.lock (the kit's requires-dist)"))


def test_lock_agrees_with_pyproject() -> None:
    # uv.lock records the requires-dist it was locked against. If pyproject
    # changed since, the two differ and the lock is stale: re-run `uv lock`.
    (kit,) = _locked(_lock(), "sessionkit")
    locked = {str(Requirement(r)) for r in _lock_requires_dist(kit)}
    declared = {str(Requirement(d)) for d in _pyproject_deps()}
    assert locked == declared, (
        f"uv.lock is stale against pyproject.toml (re-run `uv lock`): "
        f"pyproject only: {sorted(declared - locked)}; uv.lock only: {sorted(locked - declared)}"
    )


def test_lock_resolves_each_child_at_a_ruled_version_from_pypi() -> None:
    lock = _lock()
    (kit,) = _locked(lock, "sessionkit")
    edges = {
        canonicalize_name(d["name"]): set(d.get("extra", []))
        for d in kit.get("dependencies", [])
    }
    problems = []
    for spec in RULED:
        ruled = Requirement(spec)
        name = canonicalize_name(ruled.name)
        if name not in edges:
            problems.append(
                f"uv.lock: the kit has no dependency edge to {ruled.name}; ruled {spec!r}"
            )
        elif edges[name] != ruled.extras:
            problems.append(
                f"uv.lock: the kit's edge to {ruled.name} has extras {sorted(edges[name])}, ruled {sorted(ruled.extras)}"
            )
        pkgs = _locked(lock, ruled.name)
        if len(pkgs) != 1:
            problems.append(
                f"uv.lock: {ruled.name} is locked {len(pkgs)} times; expected once"
            )
            continue
        version, source = pkgs[0]["version"], pkgs[0].get("source", {})
        if not ruled.specifier.contains(Version(version), prereleases=True):
            problems.append(
                f"uv.lock: {ruled.name} is locked at {version}, outside the ruled {str(ruled.specifier)!r}"
            )
        if source != {"registry": PYPI}:
            problems.append(
                f"uv.lock: {ruled.name} comes from {source}, not the public index {PYPI}"
            )
    _fail_on(problems)


# --- the gate keeps its power -------------------------------------------------


def _replace(old: str, new: str | None) -> list[str]:
    return [
        new if spec == old else spec
        for spec in RULED
        if not (spec == old and new is None)
    ]


# Each canary is built from the RULED string itself, never a copy of it, so a
# floor bump in tests/_ruled_deps.py cannot leave a canary planting nothing.
MAIL, TOOLS, PHONE, VIEW, VOICE = RULED

CANARIES = {
    "media dropped": (
        _replace(PHONE, PHONE.replace("[media]", "")),
        "sessionphone dropped the [media] extra",
    ),
    "capture dropped": (
        _replace(VOICE, VOICE.replace("[capture]", "")),
        "sessionvoice dropped the [capture] extra",
    ),
    "floor at 0.1.0": (
        _replace(MAIL, "sessionmail>=0.1.0"),
        "sessionmail is not floored as ruled: found '>=0.1.0'",
    ),
    "child removed": (_replace(VIEW, None), "sessionview is missing"),
    "no floor": (
        _replace(TOOLS, "sessiontools"),
        "sessiontools is not floored as ruled: found 'no version bound'",
    ),
    "declared twice": (
        [*RULED, "sessionmail>=0.1.0"],
        "sessionmail is declared 2 times",
    ),
    "made conditional": (
        _replace(VIEW, f"{VIEW}; sys_platform == 'darwin'"),
        "sessionview carries a marker",
    ),
}


def test_ruled_list_names_the_five_children() -> None:
    assert FAMILY == [
        "sessionmail",
        "sessiontools",
        "sessionphone",
        "sessionview",
        "sessionvoice",
    ]
    assert drift(RULED, "ruled") == []
    # Anything outside the family is not the ruled list's business.
    assert drift(["click>=8.1", *RULED], "ruled") == []


@pytest.mark.parametrize("canary", CANARIES)
def test_gate_names_each_drift(canary: str) -> None:
    declared, message = CANARIES[canary]
    problems = drift(declared, "canary")
    assert len(problems) == 1, problems
    assert problems[0].startswith(f"canary: {message}"), problems
