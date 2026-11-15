"""Figures INSTALL.md states, tied to the file that sets them.

- The family floor: INSTALL.md section 2 says which release of the five
  packages the kit asks for. pyproject.toml is where that is set, so a floor
  bump that leaves the doc behind fails here.
- The disk figure: INSTALL.md section 1 says how much free disk the whole
  install takes, and install.sh checks the Mac against DISK_NEED_GB. The two
  are one measurement, so they must say the same number.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

import pytest
from _ruled_deps import FAMILY
from packaging.requirements import Requirement

ROOT = Path(__file__).resolve().parent.parent
INSTALL_DOC = (ROOT / "INSTALL.md").read_text(encoding="utf-8")
INSTALL_SH = (ROOT / "install.sh").read_text(encoding="utf-8")
PYPROJECT = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))

FLOOR_SENTENCE = re.compile(
    r"The kit asks for (\d+\.\d+\.\d+) or later of each of the five packages it needs"
)
DISK_SENTENCE = re.compile(r"About (\d+) GB free disk for everything the installer lists")
DISK_NEED = re.compile(r"^DISK_NEED_GB=(\d+)$", re.MULTILINE)


def _section(n: int) -> str:
    start = INSTALL_DOC.index(f"## {n}. ")
    end = INSTALL_DOC.find(f"## {n + 1}. ", start)
    return INSTALL_DOC[start:end if end != -1 else None]


def _flat(text: str) -> str:
    return " ".join(text.split())


def family_floors(dependencies: list[str]) -> dict[str, str]:
    """Each family package's `>=` floor, as pyproject.toml writes it."""
    floors = {}
    for spec in dependencies:
        req = Requirement(spec)
        if req.name in FAMILY:
            (low,) = [s.version for s in req.specifier if s.operator == ">="]
            floors[req.name] = low
    return floors


def stated_floors(doc: str) -> list[str]:
    return FLOOR_SENTENCE.findall(_flat(doc))


def stated_disk(doc: str) -> list[str]:
    return DISK_SENTENCE.findall(_flat(doc))


def test_pyproject_floors_the_whole_family_at_one_release():
    floors = family_floors(PYPROJECT["project"]["dependencies"])
    assert sorted(floors) == sorted(FAMILY)
    assert len(set(floors.values())) == 1, floors


def test_install_states_the_family_floor_pyproject_asks_for():
    (floor,) = set(family_floors(PYPROJECT["project"]["dependencies"]).values())
    assert stated_floors(_section(2)) == [floor]
    # Once, and only in section 2: a second copy is a second place to drift.
    assert stated_floors(INSTALL_DOC) == [floor]


def next_releases(version: str) -> list[str]:
    """The next patch and the next minor after `version`."""
    major, minor, patch = (int(part) for part in version.split("."))
    return [f"{major}.{minor}.{patch + 1}", f"{major}.{minor + 1}.0"]


@pytest.mark.parametrize("step", [0, 1], ids=["patch", "minor"])
def test_the_floor_tie_fails_when_pyproject_moves_alone(step):
    # A zero is a receipt only when the same check is shown to fail. The
    # bump starts from the floor pyproject.toml holds today, so a release
    # that moves both files together leaves this test standing.
    deps = PYPROJECT["project"]["dependencies"]
    (floor,) = set(family_floors(deps).values())
    bumped = next_releases(floor)[step]
    moved = [d.replace(f">={floor}", f">={bumped}") for d in deps]
    (moved_floor,) = set(family_floors(moved).values())
    assert moved_floor == bumped
    assert stated_floors(_section(2)) != [moved_floor]


def test_next_releases_counts_up():
    assert next_releases("0.3.3") == ["0.3.4", "0.4.0"]
    assert next_releases("1.9.12") == ["1.9.13", "1.10.0"]


def test_install_sh_checks_the_disk_figure_install_states():
    (need,) = DISK_NEED.findall(INSTALL_SH)
    assert stated_disk(_section(1)) == [need]
    assert stated_disk(INSTALL_DOC) == [need]


def test_the_disk_tie_fails_when_install_sh_moves_alone():
    # Moved from today's figure, whatever it is, so a re-measure that moves
    # both files together leaves this test standing.
    (need,) = DISK_NEED.findall(INSTALL_SH)
    script = DISK_NEED.sub(f"DISK_NEED_GB={int(need) + 2}", INSTALL_SH)
    (moved,) = DISK_NEED.findall(script)
    assert moved != need
    assert stated_disk(_section(1)) != [moved]


def test_the_disk_figure_is_disk_not_memory():
    # The 9.9 GB the installer once checked against was a 16 GB Mac's
    # MEMORY in use, not disk. Neither file may state it again.
    for text in (INSTALL_SH, _section(1)):
        assert "9.9 GB" not in text
    assert "37 GiB to 29 GiB" in _flat(_section(1))
