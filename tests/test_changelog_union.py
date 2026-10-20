"""SK-91: CHANGELOG.md merges with ``merge=union``, and a guard catches the
damage union can do. Ported from sessionvoice EARS-356.

Every branch adds a bullet under ``## [Unreleased]``, so two branches open
at once conflict in CHANGELOG.md. On sessionkit that happened when SK-89 was
rebased over SK-76's land. ``.gitattributes`` now says
``CHANGELOG.md merge=union``: on a conflict, git keeps both sides' lines
instead of stopping.

Two kinds of test pin that:

* REPLAY. The real clash is merged again with ``git merge-tree
  --write-tree`` in a throwaway repo: once with union off, once on. Off,
  CHANGELOG.md conflicts; on, it is clean, holds no conflict marker, holds
  every line either side added and has no duplicated bullet. The clash's
  three CHANGELOG.md blobs (the merge base, ours, theirs) are vendored in
  ``tests/fixtures/changelog_union/``, because the branch side of the pair
  was rebased and is on no ref a clone fetches. Each fixture is the real
  blob's bytes with only its dates made synthetic (SK-122: the release
  heading and the born date move forward 209 whole weeks, into 2030). A test
  pins each fixture to its own blob id, so the replay runs on those bytes
  in any clone, shallow or fresh, and never skips. The attributes are set from outside: an empty
  ``attr.tree`` hides every in-tree ``.gitattributes``, and
  ``core.attributesFile`` turns union on. The checkout under test is never
  edited.

* GUARD. Union cannot conflict, so a bad merge lands silently. The guard
  reads CHANGELOG.md and fails if the same bullet's first line appears twice
  (whitespace normalised). It passes on master and catches the synthetic
  case below: two branches each reword the same two landed bullets, union
  keeps both versions of the pair and writes the unchanged bullet between
  them twice.

What the guard does NOT catch (measured with git 2.56, see
``test_guard_blind_spots``): git keeps a line two sides share out of the
conflict, so a bullet's unchanged first line is written once. When one
bullet is edited on both sides, union keeps both versions, but they differ,
so the guard sees no duplicate. When an edit sits next to an insert, the
stale text comes back as a continuation line, which the guard does not
read. A scrub of a landed bullet is such an edit: the scrubbed word can come
back. Hence the rules in AGENTS.md: never rewrite a bullet that has landed
on master, and a scrub merges alone or is re-scanned after the merge.
"""

from __future__ import annotations

import hashlib
import os
import re
import shutil
import subprocess
from collections import Counter
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CHANGELOG = "CHANGELOG.md"

FIXTURES = ROOT / "tests" / "fixtures" / "changelog_union"

# A release archive (`git archive`, the GitHub tarball) has no .git, and git
# run on ROOT there exits 128. Tests that read ROOT through git skip there.
IS_CHECKOUT = (
    shutil.which("git") is not None
    and subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--git-dir"], capture_output=True, check=False).returncode
    == 0
)

# pair -> {side: (commit, blob id of the vendored fixture)}. Each side's
# CHANGELOG.md blob at that commit is vendored as FIXTURES/<pair>/<side>.md,
# its bytes unchanged but for its dates, made synthetic (SK-122); the blob id
# pinned here is the fixture's. "clash" is the SK-89 clash.
PAIRS = {
    "clash": {
        # 019dcb3: the merge base of the pair.
        "base": (
            "019dcb300aa8fb31eb557c57af3578479015992d",
            "44d01a7d94e75f7521cdcebd8f2350e1d721a20f",
        ),
        # 4d3f965: master with SK-76 merged.
        "ours": (
            "4d3f9651c77d48dbc1a11d82db7c87f5906f02e3",
            "115ab1edb3f4632e5d80148e48ce266449824f05",
        ),
        # 78b915c: SK-89 before its rebase (it landed rebased, as 4d3973f).
        "theirs": (
            "78b915caac9c11f987e36b38aa2ccd3172c51e1c",
            "8c96e3b0848bc3f01f9f2ed0407c70e9b2ea25c3",
        ),
    },
}
SIDES = ("base", "ours", "theirs")

MARKER = re.compile(r"^(<{7}|={7}|>{7})( |$)", re.MULTILINE)
BULLET = re.compile(r"^\s*- (.*)$")
FENCE = re.compile(r"^\s*(```|~~~)")


def duplicated_bullets(text: str) -> list[str]:
    """First lines of ``- `` bullets that appear more than once.

    Whitespace is normalised. Nested bullets count; fenced code is skipped.
    """
    seen: Counter[str] = Counter()
    in_fence = False
    for line in text.splitlines():
        if FENCE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        m = BULLET.match(line)
        if m:
            seen[" ".join(m.group(1).split())] += 1
    return sorted(k for k, n in seen.items() if n > 1)


# --- a hermetic git -----------------------------------------------------------


def git_env() -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env.update(
        GIT_CONFIG_NOSYSTEM="1",
        GIT_CONFIG_GLOBAL=os.devnull,
        GIT_AUTHOR_NAME="t",
        GIT_AUTHOR_EMAIL="t@example.invalid",
        GIT_COMMITTER_NAME="t",
        GIT_COMMITTER_EMAIL="t@example.invalid",
    )
    return env


def git(repo: Path, *args: str, check: bool = True, stdin: str | None = None):
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        input=stdin,
        capture_output=True,
        text=True,
        env=git_env(),
        check=check,
    )


def merge(repo: Path, ours: str, theirs: str, union_file: Path | None):
    """``git merge-tree --write-tree``, with in-tree attributes hidden.

    Returns (exit code, conflicted paths, merged CHANGELOG.md text).
    """
    empty = git(
        repo, "hash-object", "-w", "-t", "tree", "--stdin", stdin=""
    ).stdout.strip()
    attrs = str(union_file) if union_file else os.devnull
    r = git(
        repo,
        "-c",
        f"attr.tree={empty}",
        "-c",
        f"core.attributesFile={attrs}",
        "merge-tree",
        "--write-tree",
        "--name-only",
        "--no-messages",
        ours,
        theirs,
        check=False,
    )
    assert r.returncode in (0, 1), r.stderr
    tree, *conflicted = [line for line in r.stdout.splitlines() if line]
    text = git(repo, "cat-file", "-p", f"{tree}:{CHANGELOG}").stdout
    return r.returncode, set(conflicted), text


def added_lines(repo: Path, base: str, tip: str) -> list[str]:
    diff = git(repo, "diff", "--unified=0", base, tip, "--", CHANGELOG).stdout
    return [
        line[1:]
        for line in diff.splitlines()
        if line.startswith("+") and not line.startswith("+++")
    ]


@pytest.fixture
def union_file(tmp_path: Path) -> Path:
    f = tmp_path / "union-attributes"
    f.write_text(f"{CHANGELOG} merge=union\n")
    return f


# --- the line itself -----------------------------------------------------------


def test_gitattributes_sets_union_for_changelog():
    lines = (ROOT / ".gitattributes").read_text().splitlines()
    assert f"{CHANGELOG} merge=union" in lines


@pytest.mark.skipif(not IS_CHECKOUT, reason="not a git checkout: git check-attr needs one (a release archive has no .git)")
def test_git_reads_union_for_changelog():
    r = subprocess.run(
        ["git", "-C", str(ROOT), "check-attr", "merge", "--", CHANGELOG],
        capture_output=True,
        text=True,
        check=True,
    )
    assert r.stdout.strip() == f"{CHANGELOG}: merge: union"


def test_agents_md_carries_the_rules():
    """The guard catches only some union damage; the rules cover the rest."""
    text = " ".join((ROOT / "AGENTS.md").read_text().split())
    assert (
        "Never rewrite or delete a CHANGELOG bullet that has landed on master" in text
    )
    assert "A scrub of a landed CHANGELOG bullet merges alone." in text
    assert "re-run `make scan` on the merged tree" in text


# --- REPLAY ---------------------------------------------------------------------


def blob_id(data: bytes) -> str:
    """The id git gives these bytes as a blob (SHA-1 object format)."""
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


@pytest.mark.parametrize("pair", sorted(PAIRS))
@pytest.mark.parametrize("side", SIDES)
def test_replay_fixture_is_the_real_blob(pair, side):
    """The vendored file is byte for byte the pinned blob: the real blob at
    that commit, with only its dates made synthetic (SK-122)."""
    commit, blob = PAIRS[pair][side]
    data = (FIXTURES / pair / f"{side}.md").read_bytes()
    assert blob_id(data) == blob, f"{pair} {side} is not {commit}:{CHANGELOG}"


@pytest.fixture(scope="module", params=sorted(PAIRS))
def replay_repo(request, tmp_path_factory) -> tuple[str, Path]:
    """A throwaway repo that rebuilds the clash from the fixtures.

    ``base`` holds the merge base's CHANGELOG.md; branches ``ours`` and
    ``theirs`` each grow one commit from it, holding that side's blob.
    """
    pair = request.param
    repo = tmp_path_factory.mktemp("replay") / pair
    repo.mkdir()
    git(repo, "init", "--quiet", "--initial-branch=base")
    path = repo / CHANGELOG
    for side in SIDES:
        if side != "base":
            git(repo, "switch", "--quiet", "-c", side, "base")
        path.write_bytes((FIXTURES / pair / f"{side}.md").read_bytes())
        git(repo, "add", CHANGELOG)
        git(repo, "commit", "--quiet", "-m", f"{pair} {side}")
    return pair, repo


def test_replay_conflicts_without_union(replay_repo):
    _, repo = replay_repo
    code, conflicted, _ = merge(repo, "ours", "theirs", union_file=None)
    assert code == 1
    assert CHANGELOG in conflicted


def test_replay_is_clean_with_union(replay_repo, union_file):
    pair, repo = replay_repo
    _, conflicted, text = merge(repo, "ours", "theirs", union_file)
    assert CHANGELOG not in conflicted
    assert not MARKER.search(text)
    merged = set(text.splitlines())
    for tip in ("ours", "theirs"):
        lost = [line for line in added_lines(repo, "base", tip) if line not in merged]
        assert not lost, f"{pair}: lines {tip} added are missing: {lost}"
    assert duplicated_bullets(text) == []


# --- GUARD ----------------------------------------------------------------------


def test_guard_passes_on_master():
    assert duplicated_bullets((ROOT / CHANGELOG).read_text()) == []


BASE = """\
## [Unreleased]

### Fixed

- Alpha fix (SK-1).
- Beta fix (SK-2). It
  reads the log.
- Gamma fix (SK-3).

## [0.1.0]
"""


def union_merge(tmp_path: Path, ours: str, theirs: str) -> str:
    """Merge two edits of BASE with union on, as a real merge does."""
    repo = tmp_path / "synthetic"
    repo.mkdir()
    git(repo, "init", "--quiet", "--initial-branch=main")
    (repo / ".git" / "info").mkdir(exist_ok=True)
    (repo / ".git" / "info" / "attributes").write_text(f"{CHANGELOG} merge=union\n")
    path = repo / CHANGELOG
    path.write_text(BASE)
    git(repo, "add", CHANGELOG)
    git(repo, "commit", "--quiet", "-m", "base")
    git(repo, "switch", "--quiet", "-c", "side")
    path.write_text(theirs)
    git(repo, "commit", "--quiet", "-am", "theirs")
    git(repo, "switch", "--quiet", "main")
    path.write_text(ours)
    git(repo, "commit", "--quiet", "-am", "ours")
    r = git(
        repo,
        "merge-tree",
        "--write-tree",
        "--name-only",
        "--no-messages",
        "main",
        "side",
        check=False,
    )
    assert r.returncode == 0, "union should leave nothing to resolve"
    tree = r.stdout.splitlines()[0]
    return git(repo, "cat-file", "-p", f"{tree}:{CHANGELOG}").stdout


def test_guard_catches_edit_both(tmp_path):
    """Both branches reword the landed Alpha and Gamma bullets.

    Without union this conflicts. With it, the merge is clean, both versions
    of each bullet stay, and the Beta bullet between them is written twice.
    """
    ours = BASE.replace("Alpha fix", "Alpha fix, ours").replace(
        "Gamma fix", "Gamma fix, ours"
    )
    theirs = BASE.replace("Alpha fix", "Alpha fix, theirs").replace(
        "Gamma fix", "Gamma fix, theirs"
    )
    text = union_merge(tmp_path, ours, theirs)
    assert "Alpha fix, ours" in text and "Alpha fix, theirs" in text
    assert duplicated_bullets(text) == ["Beta fix (SK-2). It"]


@pytest.mark.parametrize(
    "case,ours,theirs,silent",
    [
        (
            "one bullet edited on both sides",
            BASE.replace("Alpha fix", "Alpha fix, ours"),
            BASE.replace("Alpha fix", "Alpha fix, theirs"),
            ["- Alpha fix, ours (SK-1).", "- Alpha fix, theirs (SK-1)."],
        ),
        (
            "a continuation line edited on both sides",
            BASE.replace("reads the log.", "reads the log twice."),
            BASE.replace("reads the log.", "reads the heard log."),
            ["  reads the log twice.", "  reads the heard log."],
        ),
        (
            "an edit next to an insert brings the stale text back",
            BASE.replace("reads the log.", "reads the heard log."),
            BASE.replace("reads the log.\n", "reads the log.\n- Delta fix (SK-4).\n"),
            ["  reads the heard log.", "  reads the log.", "- Delta fix (SK-4)."],
        ),
        (
            # "Beta" stands in for a word a scrub removes; never a real term.
            "a scrub next to an insert brings the scrubbed word back",
            BASE.replace("- Beta fix (SK-2). It", "- A fix (SK-2). It"),
            BASE.replace(
                "- Beta fix (SK-2).", "- Delta fix (SK-4).\n- Beta fix (SK-2)."
            ),
            ["- A fix (SK-2). It", "- Beta fix (SK-2). It", "- Delta fix (SK-4)."],
        ),
    ],
    ids=[
        "edit-both-one-bullet",
        "edit-both-continuation",
        "stale-next-to-insert",
        "scrub-next-to-insert",
    ],
)
def test_guard_blind_spots(tmp_path, case, ours, theirs, silent):
    """What union damages and the guard cannot see: the merge is clean, the
    damage is in the file, and no bullet's first line repeats. The AGENTS.md
    rules (never rewrite a landed bullet; a scrub merges alone or is
    re-scanned on the merged tree) are the defence here, not the guard.
    """
    text = union_merge(tmp_path, ours, theirs)
    lines = text.splitlines()
    assert all(line in lines for line in silent), case
    assert duplicated_bullets(text) == [], case
