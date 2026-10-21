"""The kit's RULED dependency list: the one place it is written down.

The dependency gate (tests/test_dependency_gate.py) holds pyproject.toml, the
built wheel's METADATA and uv.lock to this list, and fails on any drift. Change
the ruling HERE, then change pyproject.toml and re-lock to match. Nothing else
in the repo restates the list: tests/test_family.py takes its FAMILY from here.

The ruling: a kit install is the whole family, phone calls included.

- Every family package is floored at 0.2.0. The kit needs each of them at
  0.2.0 or later, and PyPI's 0.0.1 name placeholders and the 0.1.0 alphas must
  never satisfy a kit install.
- sessionmail is floored at 0.2.1. Under the drop carrier, mail's 0.2.0
  pager banner says the doorbell is NOT COPIED even when the drop did copy
  the seat's mail into the session box, so a stranger is told seat mail will
  not arrive when it does. mail's 0.2.1 judges the doorbell by the drop.
- sessionphone and sessionvoice are floored at 0.2.1. Phone's 0.2.1 sends
  unsigned under the drop carrier, with no key and no seat step, and voice's
  0.2.1 installer sets the drop carrier. A kit on their 0.2.0 would fail the
  first call on a drop host.
- sessionphone comes WITH its media extra. Calls, the bot and
  `sessionphone web` need it, and the ruling is that calls come with the kit
  rather than as a second install.
- sessionvoice comes WITH its capture extra, so the ears can hear the room.

The strings are written exactly as pyproject.toml writes them.
"""

from __future__ import annotations

from collections.abc import Iterable

from packaging.requirements import InvalidRequirement, Requirement
from packaging.utils import canonicalize_name

RULED = (
    "sessionmail>=0.2.1",
    "sessiontools>=0.2.0",
    "sessionphone[media]>=0.2.1",
    "sessionview>=0.2.0",
    "sessionvoice[capture]>=0.2.1",
)

# The five family packages, in the ruled order (the plugin manifest's order).
FAMILY = [Requirement(spec).name for spec in RULED]


def _extras(extras: Iterable[str]) -> str:
    return ", ".join(f"[{e}]" for e in sorted(extras))


def drift(declared: Iterable[str], where: str) -> list[str]:
    """Every way `declared` (requirement strings) departs from RULED.

    Each message starts with `where` and names the package and the drift: a
    child missing, declared twice, an extra dropped or added, a floor that is
    not the ruled one, or an environment marker that makes it conditional.
    An empty list means `declared` carries the ruled list exactly. Requirements
    that are not family packages (click, say) are not this list's business.
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
