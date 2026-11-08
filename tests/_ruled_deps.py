"""The kit's RULED dependency list: the one place it is written down.

The dependency gate (tests/test_dependency_gate.py) holds pyproject.toml, the
built wheel's METADATA and uv.lock to this list, and fails on any drift. Change
the ruling HERE, then change pyproject.toml and re-lock to match. Nothing else
in the repo restates the list: tests/test_family.py takes its FAMILY from here.

The ruling: a kit install is the whole family, phone calls included.

- Floored at 0.3.0: the kit is released and tested with the family's 0.3.0,
  so it needs every family package at 0.3.0 or later, and PyPI's 0.0.1 name
  placeholders and the 0.1.0 alphas must never satisfy these.
- Within the 0.3.3 floor below, `sessionkit setup` asks sessiontools for
  `session agent default`, and INSTALL.md describes sessionmail's one-run
  mail setup. Setup also asks sessiontools for the agents folder with
  `session path agent --config --json`. That verb ships in sessiontools
  0.3.3, the floor below; with a sessiontools that lacks it, setup writes
  no agent file and says so.
- All five are floored at 0.3.3: the family is released together, and an
  older copy of one package beside the others splits its state between the
  old and new folders.
- sessionphone comes WITH its media extra. Calls, the bot and
  `sessionphone web` need it, and the ruling is that calls come with the kit
  rather than as a second install.
- sessionvoice comes WITH its capture extra, so the ears can hear the room.

The second ruling: the kit also REQUIRES settled, the Settings app. It
ships with the kit, and it is a hard dependency: it goes in [project]
dependencies, never an optional extra.

- settled is required, like the family: a kit install without it is broken.
- Floored at 0.1.0, so PyPI's 0.0.1 name placeholder can never satisfy it.
- It comes WITH its kit extra. That extra brings the kit's registry
  (sessiontools.settings) and jsonschema, which validates the kit's own
  schemas. Without it settled reads only SETTINGS_ROOT, its standalone input,
  and shows none of the kit's tools. That extra asks for sessiontools 0.3.3,
  which FAMILY_RULED now floors.
- It is NOT a family package, so it is written in APPS, apart from
  FAMILY_RULED. It has its own version line (0.1.0, never the family's
  0.3.x), so a family floor bump never moves it. It ships no Claude plugin,
  so the plugin manifest and the marketplace (which follow FAMILY) leave it
  out. Its licence is AGPL-3.0-or-later, as ruled; nothing here reads it.

RULED is FAMILY_RULED + APPS: drift() and the gate hold pyproject, the built
wheel and uv.lock to all of it. The strings are written exactly as
pyproject.toml writes them.
"""

from __future__ import annotations

from collections.abc import Iterable

from packaging.requirements import InvalidRequirement, Requirement
from packaging.utils import canonicalize_name

# The family: released together, floored together, one Claude plugin each.
FAMILY_RULED = (
    "sessionmail>=0.3.3",
    "sessiontools>=0.3.3",
    "sessionphone[media]>=0.3.3",
    "sessionview>=0.3.3",
    "sessionvoice[capture]>=0.3.3",
)

# Required, but not family: each on its own version line, with no plugin.
APPS = ("settled[kit]>=0.1.0",)

# Everything the kit is ruled to require: what drift() holds a list to.
RULED = FAMILY_RULED + APPS

# The five family packages, in the ruled order (the plugin manifest's order).
FAMILY = [Requirement(spec).name for spec in FAMILY_RULED]


def _extras(extras: Iterable[str]) -> str:
    return ", ".join(f"[{e}]" for e in sorted(extras))


def drift(declared: Iterable[str], where: str) -> list[str]:
    """Every way `declared` (requirement strings) departs from RULED.

    Each message starts with `where` and names the package and the drift: a
    child missing, declared twice, an extra dropped or added, a floor that is
    not the ruled one, or an environment marker that makes it conditional.
    An empty list means `declared` carries the ruled list exactly. Requirements
    that are not ruled (click, say) are not this list's business.
    """
    problems: list[str] = []
    by_name: dict[str, list[tuple[str, Requirement]]] = {}
    for raw in declared:
        try:
            req = Requirement(raw)
        except InvalidRequirement as exc:
            problems.append(f"{where}: cannot parse {raw!r}: {exc}")
            continue
        by_name.setdefault(canonicalize_name(req.name), []).append((raw, req))

    for ruled_raw in RULED:
        ruled = Requirement(ruled_raw)
        found = by_name.get(canonicalize_name(ruled.name), [])
        if not found:
            problems.append(f"{where}: {ruled.name} is missing; ruled {ruled_raw!r}")
            continue
        if len(found) > 1:
            listed = ", ".join(repr(raw) for raw, _ in found)
            problems.append(
                f"{where}: {ruled.name} is declared {len(found)} times ({listed}); ruled once, {ruled_raw!r}"
            )
            continue
        raw, req = found[0]
        dropped = ruled.extras - req.extras
        added = req.extras - ruled.extras
        if dropped:
            problems.append(
                f"{where}: {ruled.name} dropped the {_extras(dropped)} extra: found {raw!r}, ruled {ruled_raw!r}"
            )
        if added:
            problems.append(
                f"{where}: {ruled.name} adds the unruled {_extras(added)} extra: found {raw!r}, ruled {ruled_raw!r}"
            )
        if req.specifier != ruled.specifier:
            problems.append(
                f"{where}: {ruled.name} is not floored as ruled: found {str(req.specifier) or 'no version bound'!r}"
                f" ({raw!r}), ruled {str(ruled.specifier)!r} ({ruled_raw!r})"
            )
        if req.marker is not None:
            problems.append(
                f"{where}: {ruled.name} carries a marker ({req.marker}), so not every install gets it: found {raw!r}, ruled {ruled_raw!r}"
            )
    return problems
