"""tests/_scanlist.py, the private scan list's reader for the guard tests, on a
FAKE list of placeholder words: these run with or without the real list."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import _scanlist
import pytest

FAKE = (
    "# a comment, then a blank line\n"
    "\n"
    "vera\ts\tP0\t\\bVera\\b\n"
    "ivy-any-case\ti\tP0\tivy\n"
    "theo-dir\ts\truling\t~/\\.(theo|dave)\\b\n"
    # everything after the third TAB is the regex
    "carol-tab\ts\truling\tcarol\\tbob\n"
    "  padded  \ti\truling\t  alice  "
)


@pytest.fixture
def listfile(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    p = tmp_path / "SCRUB-RULES"
    p.write_text(FAKE + "\n")
    monkeypatch.setenv(_scanlist.ENV, str(p))
    _scanlist._cached.cache_clear()
    yield p
    _scanlist._cached.cache_clear()


def test_load_reads_the_four_fields(listfile: Path) -> None:
    rows = _scanlist.load(listfile)
    assert [(r.name, r.tier, r.lineno) for r in rows] == [
        ("vera", "P0", 3),
        ("ivy-any-case", "P0", 4),
        ("theo-dir", "ruling", 5),
        ("carol-tab", "ruling", 6),
        ("padded", "ruling", 7),
    ]
    assert rows[3].pattern.pattern == "carol\\tbob"
    # fields are stripped, as release-scan does
    assert rows[4].pattern.pattern == "alice"


def test_a_row_never_shows_its_regex_in_a_repr(listfile: Path) -> None:
    row = _scanlist.load(listfile)[0]
    assert "Vera" not in repr(row)
    assert "vera" in repr(row)  # the name is what a row is known by


def test_the_case_flag_is_honoured(listfile: Path) -> None:
    rows = _scanlist.rows()
    assert _scanlist.hits("Vera", rows) == ["vera"]
    assert _scanlist.hits("vera", rows) == []  # s: case kept
    assert _scanlist.hits("IVY", rows) == ["ivy-any-case"]  # i: case ignored


def test_hits_are_names_matched_line_by_line(listfile: Path) -> None:
    rows = _scanlist.rows()
    text = "x ~/.theo/log\nVera\nnothing\ncarol\tbob"
    assert _scanlist.hits(text, rows) == ["carol-tab", "theo-dir", "vera"]
    assert _scanlist.hits("carol\nbob", rows) == []  # no match across a line break
    assert _scanlist.hits("", rows) == []


def test_rows_picks_a_tier(listfile: Path) -> None:
    assert [r.name for r in _scanlist.rows("P0")] == ["vera", "ivy-any-case"]
    assert len(_scanlist.rows("P0", "ruling")) == 5
    with pytest.raises(ValueError):
        _scanlist.rows("P1")


def test_rows_leaves_out_the_named_rows_only(listfile: Path) -> None:
    assert [r.name for r in _scanlist.rows(but=("vera", "padded"))] == [
        "ivy-any-case",
        "theo-dir",
        "carol-tab",
    ]
    assert [r.name for r in _scanlist.rows("P0", but=("vera",))] == ["ivy-any-case"]
    # a renamed row leaves nothing out
    assert len(_scanlist.rows(but=("no-such-row",))) == 5
    with pytest.raises(TypeError):
        _scanlist.rows(but="vera")  # one string is not a list of names
    with pytest.raises(pytest.fail.Exception):
        _scanlist.rows("P0", but=("vera", "ivy-any-case"))  # nothing left to scan


def test_unset_skips_loudly_naming_the_variable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(_scanlist.ENV, raising=False)
    with pytest.raises(pytest.skip.Exception) as e:
        _scanlist.rows()
    assert str(e.value).startswith(_scanlist.SKIP_PREFIX)
    assert _scanlist.ENV in str(e.value)
    monkeypatch.setenv(_scanlist.ENV, "")  # empty is unset
    with pytest.raises(pytest.skip.Exception):
        _scanlist.rows()


def test_set_but_missing_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(_scanlist.ENV, str(tmp_path / "nowhere"))
    _scanlist._cached.cache_clear()
    with pytest.raises(pytest.fail.Exception) as e:
        _scanlist.rows()
    assert "cannot read" in str(e.value)


def test_set_but_malformed_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    p = tmp_path / "list"
    p.write_text("vera\ts\tP0\n")
    monkeypatch.setenv(_scanlist.ENV, str(p))
    _scanlist._cached.cache_clear()
    with pytest.raises(pytest.fail.Exception) as e:
        _scanlist.rows()
    assert "want 4" in str(e.value)


@pytest.mark.parametrize(
    "line, why",
    [
        ("vera\ts\tP0", "want 4"),
        ("vera\tx\tP0\tVera", "case must be"),
        ("vera\ts\tP9\tVera", "tier must be"),
        ("\ts\tP0\tVera", "empty name"),
        ("vera\ts\tP0\t ", "empty name or regex"),
        ("vera\ts\tP0\t(Vera", "bad regex"),
    ],
)
def test_a_bad_row_is_refused_by_line_never_by_its_text(
    tmp_path: Path, line: str, why: str
) -> None:
    p = tmp_path / "list"
    p.write_text(f"# ok\n{line}\n")
    with pytest.raises(_scanlist.ListError) as e:
        _scanlist.load(p)
    assert why in str(e.value) and f"{p}:2" in str(e.value)
    assert "Vera" not in str(e.value)  # the regex is never echoed


def test_an_empty_list_is_refused(tmp_path: Path) -> None:
    p = tmp_path / "list"
    p.write_text("# only comments\n\n")
    with pytest.raises(_scanlist.ListError, match="no rows"):
        _scanlist.load(p)


@pytest.mark.parametrize(
    "regex, flags",
    [
        (r"\bVera\b", ""),
        (r"ivy", "i"),
        (r"(?<![0-9a-f]{4})dave|dave(?![0-9a-f]{4})", "i"),  # lookarounds, alternation
        (r"~/\.(theo|dave)\b", ""),
        (r"\b(10\.[0-9]{1,3}\.[0-9]{1,3}|192\.168\.[0-9]{1,3})\b", ""),
        (r"(\+99[ 0-9]|\b04[0-9]{2}[ -]?[0-9]{3}\b)", ""),
        (r"\b([01][0-9]|2[0-3]):[0-5][0-9](:[0-5][0-9])? (Mon|Tue)\b", ""),
        (r"\b[a-z][a-z0-9-]*\+([a-z]+-[0-9]+\.)?(carol|bob)\b", "i"),
        (r"bob('s)?\b", ""),
        (r"[^x]vera\s+\d\W\S", ""),
        (r"theo.?ivy", ""),
        (r"(?>ivy)+", ""),  # an atomic group, a repeat
        (r"vera++", ""),  # a possessive repeat
    ],
)
def test_a_sample_is_synthesised_and_matches(regex: str, flags: str) -> None:
    pattern = re.compile(regex, re.MULTILINE | (re.IGNORECASE if flags else 0))
    row = _scanlist.Row("r", "P0", pattern, 1)
    word = _scanlist.sample(row)
    assert word and row.pattern.search(f" {word} ")


@pytest.mark.parametrize("regex", [r"(a)\1", r"^$", r"\b"])
def test_no_sample_when_the_regex_is_beyond_the_generator(regex: str) -> None:
    assert _scanlist.sample(_scanlist.Row("r", "P0", re.compile(regex), 1)) is None


def test_controls_cover_every_fake_row(listfile: Path) -> None:
    rows = _scanlist.rows()
    got = _scanlist.controls(rows)
    assert [n for n, _ in got] == [r.name for r in rows]
    for name, word in got:
        assert name in _scanlist.hits(f"x {word} x", rows)


def test_controls_fail_when_nothing_can_be_planted() -> None:
    with pytest.raises(pytest.fail.Exception):
        _scanlist.controls([_scanlist.Row("r", "P0", re.compile(r"(a)\1"), 1)])


SUMMARY_SUITE = """
import _scanlist
import pytest

def test_a():
    _scanlist.rows()

def test_b():
    _scanlist.rows("P0")

def test_c():
    pytest.skip("another reason")
"""


@pytest.mark.parametrize("listed", [False, True])
def test_the_terminal_summary_counts_the_skips(
    tmp_path: Path, listfile: Path, listed: bool
) -> None:
    """Without the list, a bare run (no -rs) says how many guards skipped and
    names the variable; with it, the guards run and the section is absent. The
    suite's own conftest.py is the one copied in, so its hook is what's tested."""
    here = Path(__file__).parent
    suite = tmp_path / "suite"
    suite.mkdir()
    for name in ("conftest.py", "_scanlist.py"):
        shutil.copy(here / name, suite / name)
    (suite / "test_guards.py").write_text(SUMMARY_SUITE)
    env = {"PATH": os.defpath}
    if listed:
        env[_scanlist.ENV] = str(listfile)
    p = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", str(suite)],
        capture_output=True,
        text=True,
        env=env,
        cwd=suite,
        timeout=60,
        check=False,
    )
    if listed:
        assert "2 passed, 1 skipped" in p.stdout, p.stdout
        assert "private scan list" not in p.stdout
    else:
        assert "3 skipped" in p.stdout, p.stdout
        assert "private scan list: 2 guard tests skipped" in p.stdout
        assert f"export {_scanlist.ENV}=" in p.stdout
