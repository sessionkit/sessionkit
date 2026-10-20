"""Which shape of the kit a test runs in, for the files a release leaves out.

.gitattributes export-ignores the maintainers' notes, so they reach a reader
in only one of the three shapes the kit ships in:

- a source checkout: the notes are in the tree and in HEAD;
- a release archive (`git archive`, the GitHub tarball): no notes, no .git;
- a git clone of a repo built from that archive: no notes, and a .git whose
  history never held them.

A .git alone does not tell the first shape from the third. Whether HEAD holds
the file does: a source checkout's HEAD holds it even after the file is
deleted from disk, so a lost note still fails the tests that read it, until
the deletion is committed.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


def left_out(rel: str, root: Path = ROOT) -> bool:
    """True when `rel` is absent from `root` and its git HEAD does not hold it.

    A release archive (no git) and a clone of the export (git, but the file
    was never committed there) answer True. A source checkout answers False,
    whether the file is on disk or has been deleted from it.
    """
    if (root / rel).is_file():
        return False
    if shutil.which("git") is None:
        # No git to ask: a .git directory is the only sign of a checkout.
        return not (root / ".git").exists()
    # `HEAD:./path` reads the path relative to -C, not to the repo's top.
    out = subprocess.run(
        ["git", "-C", str(root), "cat-file", "-e", f"HEAD:./{rel}"],
        capture_output=True,
        check=False,
    )
    return out.returncode != 0


def family_doc(rel: str) -> tuple[str, pytest.MarkDecorator]:
    """The text of the maintainer note `rel`, and the mark for a test that reads it.

    The mark skips where the release left the note out. In a source checkout
    it never skips, so a missing note fails: its text is then empty, and no
    item is found. The family-docs rules live one file per governed file,
    docs/family-docs-<file>.md, and each test reads the one its rule is in.
    """
    path = ROOT / rel
    mark = pytest.mark.skipif(
        left_out(rel),
        reason=f"no {rel}: .gitattributes export-ignores it, so a release archive leaves it out",
    )
    return (path.read_text(encoding="utf-8") if path.is_file() else ""), mark
