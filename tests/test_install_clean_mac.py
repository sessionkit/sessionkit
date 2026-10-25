"""INSTALL.md's lines that a walk on a clean Mac corrected, pinned.

Each test pins one passage a stranger met on a fresh macOS 27 install that
the doc had wrong or left out: the mail hooks file and what its first run
writes, how a plugin from a local clone loads, which `ears services install`
warnings a Mac with no postfix can pass by, macOS's own share of the disk,
sessionview's `not ready` and its first question, Claude Code's folder-trust
prompt, and `/exit` with the pager's monitor running. A MEASURED tag names
what ran and on which versions; it carries no date, because a version is
the anchor a reader can check.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INSTALL = (ROOT / "INSTALL.md").read_text(encoding="utf-8")
README = (ROOT / "README.md").read_text(encoding="utf-8")

ISO_DATE = re.compile(r"\b(?:19|20)[0-9]{2}-[0-9]{2}-[0-9]{2}\b")


def _section(n: int) -> str:
    start = INSTALL.index(f"## {n}. ")
    end = INSTALL.find(f"## {n + 1}. ", start)
    return INSTALL[start:end if end != -1 else None]


def _flat(text: str) -> str:
    return " ".join(text.split())


# --- MEASURED tags carry no date -------------------------------------------

def test_the_iso_date_pattern_finds_a_date():
    # The guard below is only as good as its pattern: prove it matches.
    assert ISO_DATE.search("**MEASURED** (2001-02-03, a fresh VM)")
    assert ISO_DATE.search("read on PyPI, 2030-06-09)")
    assert not ISO_DATE.search("**MEASURED** (a fresh macOS 27 VM, Claude Code 2.1.304)")


def test_install_and_readme_carry_no_date():
    for name, text in (("INSTALL.md", INSTALL), ("README.md", README)):
        hits = [m.group(0) for m in ISO_DATE.finditer(text)]
        assert hits == [], f"{name} carries dates: {hits}"


# The agent letter and the site's notes carry MEASURED claims in prose too.
# docs/pager.md is left out on purpose: its date is front matter, not a claim.
DATED_PROSE_ELSEWHERE = ("docs/agent-letter.md", "site/README.md")


def test_the_agent_letter_and_site_notes_carry_no_date():
    for name in DATED_PROSE_ELSEWHERE:
        text = (ROOT / name).read_text(encoding="utf-8")
        hits = [m.group(0) for m in ISO_DATE.finditer(text)]
        assert hits == [], f"{name} carries dates: {hits}"


def test_the_undated_claims_keep_what_ran_and_where():
    letter = _flat((ROOT / "docs" / "agent-letter.md").read_text(encoding="utf-8"))
    assert ("(**MEASURED** on sessionmail 0.2.0 from PyPI, a temporary home "
            "directory: exit 4)") in letter
    assert "(**MEASURED** on sessionmail 0.1.0, a temporary home directory)." in letter
    assert letter.count("**MEASURED** (sessionmail 0.2.0 from PyPI, a temporary home "
                        "directory):") == 2
    site = (ROOT / "site" / "README.md").read_text(encoding="utf-8")
    assert "**No. It was measured on macOS 27.0.**" in site


def test_the_placeholder_note_names_pypi_once():
    flat = _flat(_section(2))
    assert "Each installs its real package now, 0.3.0 on PyPI, and" in flat
    assert "0.3.0 on PyPI (read on PyPI)" not in flat


def test_the_tag_legend_names_versions_not_a_date():
    head = _flat(INSTALL[:INSTALL.index("## 1. ")])
    assert "**MEASURED** (it ran, on the machine and versions given)" in head
    assert "machine and date given" not in head


# --- Section 1: macOS's own share of the disk --------------------------------

def test_section_1_counts_macos_own_first_downloads():
    s1 = _flat(_section(1))
    assert "**On a fresh Mac, macOS takes about 8 GB of its own first.**" in s1
    assert "9.2 GiB free fell to 1.0 GiB within about 10 minutes" in s1
    # The existing measured line stays: added to, not contradicted.
    assert "At least 2.1 GB free disk, plus about 3.9 GB for the speech-to-text server" in s1
    assert "the kit about 280 MB" in s1


def test_section_1_gives_the_walks_measured_sizes():
    s1 = _flat(_section(1))
    assert ("the kit's tool folder was 230 MB, the speech server's venv 1.2 GB, the Hugging "
            "Face cache 2.7 GB once the server had fetched its models, and the plugins' "
            "cache 28 MB") in s1


# --- Section 3: a plugin from a local clone loads in place -----------------

def test_section_3_clone_route_runs_in_place():
    s3 = _flat(_section(3))
    assert "**Each plugin runs in place, from its clone.**" in s3
    assert "on `/reload-plugins` in a session already open" in s3
    assert "gave the clone as the plugin's `readFromFolder` and the cache copy as its `installPath`" in s3
    assert "not from the clone" not in s3


def test_section_3_kit_route_still_runs_from_a_copy():
    s3 = _flat(_section(3))
    assert "**The plugins run from a copy.**" in s3
    assert "`~/.claude/plugins/cache/sessionkit/<name>/<version>/`, and that copy is what runs" in s3


def test_section_8_says_a_clones_copy_was_not_what_ran():
    s8 = _flat(_section(8))
    assert "the copies it wrote even though each plugin ran in place, from its clone" in s8
    assert "the cached copies its plugins ran from" not in s8


# --- Section 4: the hooks file, the folder-trust prompt --------------------

def _hooks_json_block(s4: str) -> dict:
    blocks = re.findall(r"```json\n(.*?)```", s4, re.DOTALL)
    hooks = [json.loads(b) for b in blocks if '"hooks"' in b and '"sendmail"' in b]
    assert len(hooks) == 1, hooks
    return hooks[0]


def test_section_4_no_longer_says_the_first_run_tells_you():
    assert "the first run tells you so" not in INSTALL


def test_section_4_gives_the_hooks_file_whole():
    s4 = _section(4)
    flat = _flat(s4)
    assert "**Turn the mail hooks on. HUMAN (edit a file).**" in flat
    assert "The hooks stay off until you set `\"hooks\": true` in `~/.sessionkit/mail/settings/mail.json`." in flat
    # Each path is its own labelled bullet.
    assert "- No file yet: make it with exactly this content:" in flat
    assert "- The file is there: change only" in flat
    assert "Nothing on your screen says so" in flat
    assert "it tells your agent, not you" in flat
    assert _hooks_json_block(s4) == {"version": 1, "hooks": True, "sendmail": "drop"}
    assert "change only `\"hooks\": false` to `\"hooks\": true`, and keep its other keys" in flat


def test_section_4_hooks_file_matches_the_readme():
    # INSTALL and the README write the same file when it is not there yet.
    assert '{"version": 1, "hooks": true, "sendmail": "drop"}' in README
    assert '{"version": 1, "hooks": true, "sendmail": "drop"}' in _section(4)
    assert "**The mail hooks start off.**" in README
    assert "The README's step **The mail hooks start off**" in _flat(_section(4))


def test_section_4_measured_what_the_first_run_writes():
    flat = _flat(_section(4))
    assert ("the start wrote only `mail.schema.json` and `mail.template.json`; the first tool "
            "batch wrote `mail.json` as `{\"version\": 1, \"hooks\": false, \"sendmail\": \"drop\"}`") in flat


def test_section_4_warns_of_the_folder_trust_default():
    flat = _flat(_section(4))
    assert ("**Claude Code asks whether you trust the folder, and \"No, exit\" is the answer it "
            "has ready.**") in flat
    assert "Return alone quits the session" in flat


# --- Section 5: ears services install, --agent and the warnings -------------

def test_section_5_says_a_bare_install_refuses_on_0_3_0():
    flat = _flat(_section(5))
    assert "From sessionvoice 0.3.0, the one the kit installs, a bare install refuses" in flat
    assert "bare, `REFUSED: no --agent NAME`, exit 2" in flat
    assert ('`--no-agent` to install anyway with no seat for "hey" and a name until you run '
            "`ears wake add SEAT`") in flat
    # The 0.2.x behaviour is kept as what it was, under its own release.
    assert "sessionvoice 0.2.x warned `no --agent NAME: NOBODY will be woken when you speak`" in flat
    assert "A bare install warns `no --agent NAME" not in flat


def test_section_5_names_which_warnings_a_mac_with_no_postfix_can_ignore():
    flat = _flat(_section(5))
    assert "**Warnings a Mac with no postfix can pass by.**" in flat
    assert "`postfix has no virtual_mailbox_maps ... no agent is paged`: ignore it." in flat
    assert "`heard box MISSING, not made: ...`, which ends in a `vmailbox-gen` line: ignore it too." in flat
    # SK-206: setup adds the wake seat, so the by-hand step is for a setup that added none.
    assert ("`no --agent NAME: NOBODY will be woken when you speak`: do not ignore this one. "
            "`sessionkit setup` adds the wake seat (section 2), so you meet it only when "
            "setup's line said `No wake seat added`. Then do one of these, your agent's name in "
            "place of SEAT or NAME: - Add it to the wake "
            "file: ```bash ears wake add SEAT ``` - Or install again with it: ```bash ears "
            "services install --agent NAME ```") in flat


def test_section_5_says_0_3_0_on_the_drop_checks_no_postfix():
    flat = _flat(_section(5))
    assert ("From sessionvoice 0.3.0, with mail on the drop, install checks no postfix and makes "
            "the heard box itself with `message setup --box heard`") in flat
    assert "**NOT YET** run on a Mac with no postfix." in flat


# --- Section 7: sessionview's `not ready` and first question ----------------

def test_section_7_explains_not_ready_for_neomutt_alone():
    flat = _flat(_section(7))
    assert "**`sessionview install --check` says `not ready` when only `neomutt` is missing.**" in flat
    assert "This guide does not ask for neomutt." in flat
    assert "`not ready: fix the MISSING lines above, then run this again`, exit 1" in flat


def test_section_7_does_not_class_neomutt():
    # Whether neomutt is a requirement is not this doc's to say yet: the
    # passage says what the check prints, never that neomutt is required or
    # optional.
    passage = _flat(_section(7))
    start = passage.index("**`sessionview install --check`")
    end = passage.index("**`sessionview agents`")
    for word in ("required", "optional", "brew install neomutt"):
        assert word not in passage[start:end].lower(), word


def test_section_7_documents_the_autostart_question():
    flat = _flat(_section(7))
    assert "**`sessionview agents` asks you one question the first time it opens**" in flat
    assert "`sessionview can start an agent for you each time it opens.`" in flat
    assert "`n) no agent -- never ask again`" in flat
    assert ("- An agent each time it opens, the agent's name in place of VALUE: ```bash "
            "sessionview-config set autostart_agent VALUE ```") in flat
    assert '- None: ```bash sessionview-config set autostart_agent "" ```' in flat
    assert "`autostart_agent=ask (will ask on next open)`" in flat


# --- Section 8: /exit with the monitor -------------------------------------

def test_section_8_says_exit_asks_one_more_question():
    flat = _flat(_section(8))
    assert "`/exit` asks one more question, because the monitor is background work" in flat
    assert "answer `Exit and stop tasks`" in flat
