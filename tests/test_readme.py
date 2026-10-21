"""The README's install notes, pinned to what the family's code reads.

The mail hooks note (SK-58): sessionmail writes its host settings
file with the hooks OFF on first use, by design, and only the boolean
`true` turns them on. The README must say so, at sessionmail's path and
key, measured in `sessionmail/_settings.py` (RELATIVE, `_parse`) and
`settings.template.json` at sessionmail master 83c7eff. If sessionmail
moves the file, this test is where the README's copy goes stale.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

from sessionkit import cli
from sessionkit import setup as kit_setup

ROOT = Path(__file__).resolve().parent.parent
README = (ROOT / "README.md").read_text(encoding="utf-8")

# sessionmail's settings file: the mail package's settings folder, under $HOME.
MAIL_SETTINGS = "~/.sessionkit/mail/settings/mail.json"


def _section(title: str) -> str:
    """The body of the `## title` section, up to the next `## `."""
    match = re.search(rf"^## {re.escape(title)}\n(.*?)(?=^## |\Z)", README, re.MULTILINE | re.DOTALL)
    assert match, f"README has no '## {title}' section"
    return match.group(1)


def test_installation_says_the_mail_hooks_start_off():
    install = _section("Installation")
    assert "mail hooks start off" in install
    assert MAIL_SETTINGS in install
    assert '"hooks": true' in install


def test_the_hooks_note_follows_the_install_block():
    install = _section("Installation")
    assert install.index("uv tool install") < install.index("mail hooks start off")


def test_every_hooks_command_names_sessionmails_file():
    install = _section("Installation")
    note = install[install.index("mail hooks start off"):]
    commands = re.findall(r"^ *```bash\n(.*?)^ *```", note, re.MULTILINE | re.DOTALL)
    assert len(commands) == 2, "a create-it block and an edit-it block"
    commands = ["\n".join(line.strip() for line in c.splitlines()) + "\n" for c in commands]
    create, edit = commands
    assert f"mkdir -p {MAIL_SETTINGS.rsplit('/', 1)[0]}\n" in create
    assert f"""'{{"version": 1, "hooks": true}}' > {MAIL_SETTINGS}""" in create
    assert edit.rstrip().endswith(MAIL_SETTINGS)
    assert '"hooks": true' in edit


# SK-58: uv's installer ends "restart your shell or run
# `source $HOME/.local/bin/env`". A reader who pastes the README in order,
# in the terminal they ran the installer in, must be told that BEFORE the
# first `uv` line, or that line exits 127.
UV_INSTALLER = "https://astral.sh/uv/install.sh"
UV_ENV = "source ~/.local/bin/env"


def test_installation_says_new_terminal_between_uv_installer_and_first_uv():
    install = _section("Installation")
    installer = install.index(UV_INSTALLER)
    first_uv = install.index("uv tool install")
    between = " ".join(install[installer:first_uv].split())
    assert "open a new terminal" in between and UV_ENV in between


def test_installation_is_the_first_section():
    # Progressive disclosure: the first screen gets a stranger installed.
    h2s = re.findall(r"^## (.+)$", README, re.MULTILINE)
    assert h2s[:2] == ["Installation", "Quick start"], h2s


# The install at 0.2.0, as a fresh Mac measured it: `uv tool install` pinned
# to Python 3.14, then the one-step plugin install from the kit's marketplace
# (the kit's plugin and the five it depends on). The README once said these two
# plugin lines failed and sent a reader to a folder of local clones; both
# claims are false at 0.2.0, and the clone route is gone from the README.
UV_LINE = "uv tool install --python 3.14 sessionkit"
PLUGIN_LINES = (
    "claude plugin marketplace add sessionkit/sessionkit",
    "claude plugin install sessionkit@sessionkit",
)


def _bash_blocks(text: str) -> list[str]:
    return re.findall(r"^ *```bash\n(.*?)^ *```", text, re.MULTILINE | re.DOTALL)


def test_installation_leads_with_the_pinned_install_and_the_plugin_lines():
    install = _section("Installation")
    first = _bash_blocks(install)[0].splitlines()
    assert first == [UV_LINE, *PLUGIN_LINES], first


def test_installation_says_why_the_pin_and_that_the_kit_is_tested_on_3_14():
    install = " ".join(_section("Installation").split())
    assert "**Keep `--python 3.14`.**" in install
    assert "3.15" in install and "the install fails" in install
    assert "Command Line Tools' 3.11" in install
    assert "The kit is tested on 3.14." in install


def test_installation_warns_of_the_command_line_tools_dialog_before_git_is_needed():
    install = " ".join(_section("Installation").split())
    assert "**A dialog may ask to install the Command Line Tools.**" in install
    assert "the first `uv tool install` opens it" in install
    assert "the plugin lines need the git it brings" in install


# SK-88 do-015 (DESIGN-2): sessionphone OWNS the signing paragraph, at
# docs/bot-mail-signing.md (landed on its master at cac59f5). The README's
# calls passage is ONE line and a link to it, absolute like the other child
# links, and copies none of its text. Calls are installed, not yet walked: the
# README never says they work until a fresh-Mac walk has a receipt.
PHONE_SIGNING = "https://github.com/sessionkit/sessionphone/blob/HEAD/docs/bot-mail-signing.md"
# Distinctive sentences of sessionphone's paragraph; none may be copied here.
PHONE_PARAGRAPH = (
    "Nothing on this Mac could tell a signed file from an unsigned one",
    "anything that could forge the file could also use the key",
    "the doorbell rings only for a session started as that agent",
    "A plain `claude` gets no copy of the mail, and nothing tells it so",
    "There is no switch for it",
)


def test_installation_gives_the_calls_passage_as_one_line_and_a_link():
    install = _section("Installation")
    flat = " ".join(install.split())
    bullet = ("- **Phone calls are installed, not yet walked.** Whether the phone bot signs its mail "
              "to your Claude follows your mail carrier: [bot mail signing][phone-signing].")
    assert bullet in flat
    # The 0.2.0 hand-install of the extra is gone: 0.2.1 floors sessionphone[media].
    assert "--with 'sessionphone[media]'" not in README
    assert "not yet available" not in README
    assert re.search(rf"^\[phone-signing\]: {re.escape(PHONE_SIGNING)}$", README, re.MULTILINE)
    assert not re.search(r"calls? (now )?work", flat, re.IGNORECASE)


@pytest.mark.parametrize("sentence", PHONE_PARAGRAPH)
def test_no_kit_doc_copies_sessionphones_signing_paragraph(sentence):
    for name, text in (("README.md", README), ("INSTALL.md", INSTALL_DOC), ("site/index.html", SITE)):
        assert sentence.lower() not in " ".join(text.split()).lower(), (name, sentence)


def test_quick_start_sends_the_stranger_to_session_start_and_says_why():
    quick = " ".join(_section("Quick start").split())
    assert ("Start Claude with `session start claude`, never a bare `claude`: mail to your agent's "
            "box, your phone's included, reaches only a session started as that agent.") in quick
    assert "`sessionkit setup` makes the box and the agent first: [first checks][checks]." in quick
    assert quick.index("session start claude") < quick.index("from your agent inside a Claude Code session")


# The calls are installed with the kit, never promised to work: a fresh Mac
# cannot finish their setup yet. No passage may offer to ring a session.
CALL_PROMISES = (
    r"\bring (a|your) session",
    r"\bring from",
    r"\bringing a session",
    r"pick up when you ring",
    r"calls? (now )?work",
    r"from anywhere",
)


@pytest.mark.parametrize("pattern", CALL_PROMISES)
def test_no_doc_promises_that_calls_work(pattern):
    components = (ROOT / "docs" / "components.md").read_text(encoding="utf-8")
    for name, text in (("README.md", README), ("docs/components.md", components)):
        assert not re.search(pattern, " ".join(text.split()), re.IGNORECASE), (name, pattern)


def test_every_calls_passage_says_installed_not_yet_walked():
    flat = " ".join(README.split())
    assert flat.count("not yet walked") == 2, "the Installation line, The family"
    assert "Installed, not yet walked." in " ".join(_section("The family").split())
    # One calls passage: Usage no longer repeats it, and the link is given once.
    assert "phone" not in _section("Usage").lower()
    assert flat.count("[phone-signing]") == 2, "one use, one definition"


# The setup verbs are the part a fresh Mac cannot finish yet, so the first
# commands in docs/components.md never walk a reader into them.
CALL_SETUP_VERBS = ("sessionphone setup", "sessionphone qr", "sessionphone link")


def test_components_first_commands_do_not_show_the_call_setup():
    components = (ROOT / "docs" / "components.md").read_text(encoding="utf-8")
    first = re.search(r"^### First commands\n(.*?)(?=^#{2,3} |\Z)", components, re.MULTILINE | re.DOTALL)
    assert first, "docs/components.md has no '### First commands' section"
    body = first.group(1)
    for verb in CALL_SETUP_VERBS:
        assert verb not in body, verb
    assert "installed, not yet walked on a fresh Mac" in " ".join(body.split())


FALSE_AT_0_2_0 = (
    "fail today",
    "does not load yet",
    "do not install `sessionkit@sessionkit`",
    "install the plugins from your clones",
    "sessionkit-local",
    "coming",
    "NOT YET MEASURED",
)


@pytest.mark.parametrize("claim", FALSE_AT_0_2_0)
def test_the_readme_no_longer_says_the_plugin_install_fails(claim):
    assert claim.lower() not in " ".join(README.split()).lower(), claim


def test_quick_start_shows_the_measured_version_lines():
    quick = _section("Quick start")
    [text] = re.findall(r"^```text\n(.*?)^```", quick, re.MULTILINE | re.DOTALL)
    assert text.splitlines()[0] == "sessionkit, version 0.2.1"
    # The kit's floors: sessionmail, sessionphone and sessionvoice at 0.2.1,
    # the other two at 0.2.0 (tests/_ruled_deps.py), as a fresh install prints.
    measured = {"sessionmail": "0.2.1", "sessiontools": "0.2.0", "sessionphone": "0.2.1",
                "sessionview": "0.2.0", "sessionvoice": "0.2.1"}
    assert [line.split() for line in text.splitlines()[1:]] == [
        [name, measured[name]] for name in cli.FAMILY]


def test_status_names_the_version_pyproject_ships():
    # The README's one written-down release label is the release it describes,
    # as the site's is (tests/test_site.py).
    version = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["version"]
    labels = re.findall(r"\bAlpha, ([0-9][0-9.]*[0-9])\.", _section("Status"))
    assert labels == [version], labels


def test_quick_start_says_mail_needs_a_session_and_the_mouth_a_device():
    quick = _section("Quick start")
    flat = " ".join(quick.split())
    assert "no seat in the environment ... set an identity" in flat
    assert 'mouth say --device default "the build is green"' in quick
    assert "A send never makes a box" in flat


def test_uninstall_removes_the_marketplace_then_the_commands():
    block = _bash_blocks(_section("Uninstall"))[0].splitlines()
    assert block == ["claude plugin marketplace remove sessionkit", "uv tool uninstall sessionkit"]
    assert "removes its six plugins too" in _section("Uninstall")


def test_development_clones_the_public_url():
    dev = _section("Development")
    assert "git clone https://github.com/sessionkit/sessionkit\n" in dev
    assert "make install" in dev and "make check" in dev


def test_no_doc_says_the_repos_are_not_public():
    # False on release day: the repos are named, and what is unmeasured is
    # tagged NOT YET MEASURED instead. Every shipped prose file, site/ too.
    for name in SHIPPED_PROSE:
        text = (ROOT / name).read_text(encoding="utf-8")
        flat = " ".join(text.split()).lower()
        assert "not public yet" not in flat, name
        assert "go public" not in flat, name
        assert "repos are public" not in flat, name


# INSTALL.md sections 3 and 8: section 3 installs each child from its
# clone's own marketplace, and section 8 removes those child marketplaces.
# (The README's clone-era copies of these steps are gone: at 0.2.0 it installs
# and removes the kit's own marketplace instead.)
INSTALL_DOC = (ROOT / "INSTALL.md").read_text(encoding="utf-8")


# SK-100 made the notes plugin opt-in for the kit (SK-46); SK-107 takes it
# out of the shipped docs for 0.2.0, because it is not in the release set.
# INSTALL.md section 3's install-all loop names exactly the five children, and
# the plugin count read back is five. The name is spelled in two halves here so
# that `git grep -i` for it over the shipped tree finds only CHANGELOG history.
_DROPPED = "atom" + "note"


def test_install_loop_names_exactly_the_five_children():
    section = _install_section(3)
    loops = re.findall(r"^for r in (.*?); do$", section, re.MULTILINE)
    assert len(loops) == 1, "one install-all loop in section 3"
    names = loops[0].split()
    assert sorted(names) == sorted(cli.FAMILY)
    assert len(names) == len(set(names)) == 5
    assert _DROPPED not in names


def test_the_docs_no_longer_offer_the_optional_sixth_plugin():
    assert "**Optional:" not in _install_section(3)
    for doc in (INSTALL_DOC, README):
        assert _DROPPED not in doc.lower()
    install = _section("Installation")
    assert f"marketplace remove {_DROPPED}" not in install
    assert "for each of the five (this removes the plugin" in _install_section(8)


# A release archive (`git archive`, the GitHub tarball) has no .git, so it has
# no tracked-file list to read; git run on ROOT there exits 128.
@pytest.mark.skipif(
    not shutil.which("git")
    or subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--git-dir"], capture_output=True, check=False).returncode
    != 0,
    reason="not a git checkout: git ls-files needs one (a release archive has no .git)",
)
def test_no_tracked_file_names_the_dropped_plugin_outside_changelog():
    # SK-107: the shipped tree names it nowhere but CHANGELOG.md, whose
    # landed bullets are history and are never rewritten. Reads every
    # tracked file as it is on disk, so an uncommitted edit counts too.
    tracked = subprocess.run(
        ["git", "-C", str(ROOT), "ls-files", "-z"],
        capture_output=True, check=True,
    ).stdout.decode("utf-8").split("\0")
    hits = []
    for name in filter(None, tracked):
        path = ROOT / name
        if name == "CHANGELOG.md" or not path.is_file():
            continue
        data = path.read_bytes().lower()
        if _DROPPED.encode() in data:
            hits.append(name)
    assert hits == [], hits


def test_the_plugin_count_read_back_is_six_then_five_from_clones():
    # The kit's two lines read back six (the kit's plugin and its five); the
    # optional clone route reads back the five children.
    route, clones = _install_section(3).split(CLONE_NOTE, 1)
    assert "should show six plugins" in route
    assert "should see five plugins" in clones
    assert "**Fewer than five?**" in clones
    assert "Fewer than six" not in _install_section(3)


# INSTALL.md section 3 at 0.2.0 (SK-151): the one-step route the README gives,
# measured on an empty Claude Code config (the kit's plugin and its five, all
# 0.2.0, enabled). The clone loop is only an optional note after it, for
# working on the plugins, and section 7 no longer says the kit plugin fails.
CLONE_NOTE = "### From your own clones, to work on the plugins (optional)"
INSTALL_NO_LONGER = (
    "does not load",
    "Do **not** install `sessionkit@sessionkit`",
    "Install the five plugins instead",
    "you install the five plugins one at a time",
)


def test_install_section_3_leads_with_the_one_step_route():
    section = _install_section(3)
    route, clones = section.split(CLONE_NOTE, 1)
    first = _bash_blocks(route)[0].splitlines()
    assert first[:2] == list(PLUGIN_LINES)
    assert "after the Command Line Tools" in route
    assert "marketplace add \"$SRC/$r\"" not in route
    assert "marketplace add \"$SRC/$r\"" in clones
    assert "INSTEAD of the lines above" in clones


@pytest.mark.parametrize("claim", INSTALL_NO_LONGER)
def test_install_sections_3_and_7_no_longer_say_the_kit_plugin_fails(claim):
    for n in (3, 7):
        assert claim.lower() not in " ".join(_install_section(n).split()).lower(), (n, claim)


# SK-64: the install doc after the 0.1.0 release. 0.1.0 is on PyPI for all
# six packages (measured read-only 2030-06-09), so the doc no longer tells
# a reader to wait for it (G8) or to use a folder of wheels; it keeps the
# --python 3.14 pin (on 3.15 the resolve still picks the 0.0.1
# placeholder), says the install is online-only (G10), and the
# troubleshooting hub links the phone's own call checks (PHONE-114).
TROUBLESHOOTING = (ROOT / "docs" / "troubleshooting.md").read_text(encoding="utf-8")


def _install_section(n: int) -> str:
    start = INSTALL_DOC.index(f"## {n}. ")
    end = INSTALL_DOC.find(f"## {n + 1}. ", start)
    return INSTALL_DOC[start:end if end != -1 else None]


def test_install_doc_no_longer_waits_for_the_release():
    kit = _install_section(2)
    assert "needs the 0.1.0 release" not in INSTALL_DOC
    assert "until the release" not in INSTALL_DOC.lower()
    assert "--find-links" not in INSTALL_DOC
    flat = " ".join(kit.split())
    assert "the five packages this release needs are on PyPI: sessionmail, sessionphone and sessionvoice 0.2.1, sessiontools and sessionview 0.2.0" in flat
    assert "**MEASURED** (2030-06-09, read-only against PyPI)" in kit


def test_install_doc_states_the_size_and_when_calls_download():
    # SK-88 (0.2.1): the kit installs sessionphone[media]. Section 2 states
    # the measured install size, and says the calls packages download with
    # everything else at `uv tool install`, installed but not set up.
    kit = _install_section(2)
    flat = " ".join(kit.split())
    assert "**The install size.**" in kit
    assert "uv downloaded about 93 MB, and the kit's tool folder is about 280 MB on disk" in flat
    assert "about 52 MB of the 280 MB" in flat
    assert "61 packages" in flat and "14 commands" in flat
    assert "**Phone calls are installed, not yet walked.**" in kit
    assert "They download with everything else, during `uv tool install`, with no separate step" in flat
    assert "Setting them up is section 6, and no fresh Mac has walked it yet." in flat
    # The Linux line: sessionvoice 0.2.1's base dependency sounddevice brings no
    # PortAudio on Linux.
    assert "`libportaudio2`" in kit
    optional = _install_section(6)
    assert "Phone calls are installed, not yet walked." in " ".join(optional.split())
    assert "https://github.com/sessionkit/sessionphone" in optional
    assert "not yet available" not in INSTALL_DOC


# SK-88 do-015 (the corrections measured on sessionmail 0.2.0 and the drop
# checks): section 6 says signing follows the carrier, the key a reader
# types is `sendmail` (a `carrier` key is ignored), postfix installed does not
# decide it, the signing claim is the BOT's, and the two conditions for the
# bot's mail to reach Claude: the box exists, and Claude started as the agent.
def test_section_6_says_signing_follows_the_carrier_and_links_the_phone():
    phone = _flat(_install_section(6))
    assert "**Signing follows the carrier.** From sessionphone 0.2.1, the bot's mail" in phone
    assert "Under the drop, sessionmail's default, it goes straight into your own mailbox, as you" in phone
    assert "The carrier is the `sendmail` setting (section 5, step 2), not whether postfix is installed." in phone
    assert f"[bot mail signing]({PHONE_SIGNING})" in phone


def test_section_6_names_the_two_conditions_and_the_start_line():
    phone = _flat(_install_section(6))
    assert "**Two things decide whether its mail reaches your Claude.**" in phone
    assert "the drop never makes one: `sessionkit setup` makes `claude` (section 5, step 4)" in phone
    assert "`session start claude` (section 4), never a bare `claude`" in phone
    # Not walked: the caveat stays until a fresh-Mac walk has a receipt.
    assert "**NOT YET** end to end on a fresh Mac." in phone
    assert "no fresh Mac has walked it yet" in phone


def _calls_passages() -> dict[str, str]:
    """The passages do-015 owns: the whole README and site, INSTALL's summary,
    section 2 and section 6."""
    summary = INSTALL_DOC[:INSTALL_DOC.index("## 1. ")]
    return {"README.md": README, "site/index.html": SITE, "INSTALL.md summary": summary,
            "INSTALL.md section 2": _install_section(2), "INSTALL.md section 6": _install_section(6)}


@pytest.mark.parametrize("name", ["README.md", "site/index.html", "INSTALL.md summary",
                                  "INSTALL.md section 2", "INSTALL.md section 6"])
def test_no_calls_passage_makes_no_mail_server_the_drop_condition(name):
    # Postfix is opt-in: a Mac with postfix still drops unless `sendmail` names
    # it. And the settings key is `sendmail`; a `carrier` key is never read.
    text = _flat(_calls_passages()[name])
    for wrong in ("with no mail server", "with no postfix", '"carrier":'):
        assert wrong not in text, (name, wrong)


def test_install_doc_keeps_the_python_pin():
    kit = _install_section(2)
    assert "uv tool install --python 3.14 sessionkit\n" in kit
    assert "keep `--python 3.14`" in kit


def test_install_doc_says_it_is_online_only():
    prereqs = _install_section(1)
    assert "the install is online-only." in prereqs


def test_troubleshooting_links_the_phones_call_checks():
    assert "[its call troubleshooting][phone-calls]" in TROUBLESHOOTING
    assert re.search(
        r"^\[phone-calls\]: https://github\.com/sessionkit/sessionphone#call-troubleshooting$",
        TROUBLESHOOTING, re.MULTILINE,
    )


# SK-69: the hub links sessionvoice's own mouth troubleshooting (EARS-284,
# sessionvoice master ed78bda) under a voice heading; the family repo
# owns the text, so the hub carries the link and no causes.
def test_troubleshooting_links_the_mouths_chop_checks():
    stuck = TROUBLESHOOTING[TROUBLESHOOTING.index("## Where it gets stuck"):
                            TROUBLESHOOTING.index("## More")]
    assert "### The voice chops" in stuck
    assert "[sessionvoice's docs/troubleshooting.md][sv-mouth]" in stuck
    assert re.search(
        r"^\[sv-mouth\]: https://github\.com/sessionkit/sessionvoice/blob/HEAD/"
        r"docs/troubleshooting\.md#mouth-the-voice-chops$",
        TROUBLESHOOTING, re.MULTILINE,
    )


# SK-72: case 82 (a fresh macOS 27 VM, INSTALL.md at 445ef4e) found places
# a stranger had no line to run. Each fix quotes what the VM measured. The
# clone URL is named, and tagged NOT YET MEASURED until a clean Mac clones
# from it.
HOMEBREW_INSTALLER = (
    '/bin/bash -c "$(curl -fsSL '
    'https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"'
)


def test_install_doc_names_the_homebrew_command():
    prereqs = _install_section(1)
    assert HOMEBREW_INSTALLER in prereqs
    assert "the three lines it prints" in prereqs


def test_install_doc_disk_line_matches_the_measured_install():
    prereqs = _install_section(1)
    assert "About 10 GB" not in prereqs
    assert "At least 2.1 GB free disk" in prereqs


# SK-88 (0.2.1): section 1's kit figure agrees with section 2's measured size.
def test_install_doc_disk_line_agrees_with_the_install_size():
    prereqs = " ".join(_install_section(1).split())
    kit = " ".join(_install_section(2).split())
    assert "the kit about 280 MB" in prereqs
    assert "277 MB" not in prereqs
    assert "the kit's tool folder is about 280 MB on disk" in kit


# SK-88 (0.2.1): the monitor paragraph speaks of section 3's plugin, not a clone.
def test_install_doc_monitor_names_the_installed_plugin_not_a_clone():
    checks = " ".join(_install_section(4).split())
    assert "Your sessionmail clone" not in checks
    assert "an older clone has none" not in checks
    assert "The sessionmail plugin section 3 installs, 0.2.0, has that `monitors/monitors.json`" in checks


# SK-88 (0.2.1): this INSTALL ships in 0.2.1, whose setup has the agent step:
# its three lines are measured on the 0.2.1 wheel; NOT YET says what is unrun.
def test_install_doc_setup_agent_lines_measured_on_this_release():
    kit = " ".join(_install_section(2).split())
    assert "this release's assistant step (below), which sessionkit 0.2.0 does not have" in kit
    assert "run with `--address`): the last three lines, exit 4" in kit
    assert "**NOT YET** run on a fresh Mac." in kit
    assert "and 0.2.0 has none: read in its source" not in kit


# SK-88 (0.2.1, do-010 review N1): the labels dry run names its exit 2.
def test_install_doc_labels_dry_run_names_its_refusal():
    hearing = " ".join(_install_section(5).split())
    assert "It exited 2, `silero MISSING`, because `ears install` had not fetched" in hearing


def test_install_doc_says_the_plugin_loop_exits_0_and_to_count_five():
    plugins = _install_section(3)
    assert "https://github.com/sessionkit/<name>" in plugins
    assert "stops here" not in plugins
    assert "private" not in plugins
    assert "exits 0 even when nothing installed" in plugins
    assert "`✘ Path does not exist: <SRC>/sessionmail`" in plugins
    assert "**Fewer than five?**" in plugins
    # The repair for a clone with nothing checked out is a fresh clone naming
    # its branch; a checkout in place was never run, so the doc must not say
    # it. The public repositories are on master, and at 0.2.0 a clone of each
    # made with -b master was measured to install (SK-151), so the doc no
    # longer calls that clone unmeasured.
    flat = " ".join(plugins.split())
    assert "Check out its `master` branch" not in plugins
    assert "clone it again with `-b master`, the branch the public repositories are on" in flat
    assert "clones of the public repositories made with `-b master`): five of five" in flat
    assert "NOT YET MEASURED" not in plugins


def test_install_doc_says_plugins_run_from_the_cache_copy():
    route, clones = _install_section(3).split(CLONE_NOTE, 1)
    assert "**The plugins run from a copy.**" in route
    assert "`~/.claude/plugins/cache/sessionkit/<name>/<version>/`" in route
    assert "`~/.claude/plugins/cache/<r>/<r>/<version>/`, not from the clone" in clones


def test_install_doc_quotes_the_no_identity_refusals():
    checks = _install_section(4)
    assert "work only inside a `claude` session" in checks
    assert "pager status: could not look: no identity in the environment" in checks
    assert "Error: no seat in the environment to send From" in checks


# SK-74: sessionvoice 0.2.0 ships the keeper in its package, so the kit's own
# `ears services install` runs it: no plugin bin/ears detour. The bare set and
# --only's names are services.py's at sessionvoice master (f326269).
# SK-137: every shipped launchd label is dev.sessionkit.<package>.<job>; the
# voice's are dev.sessionkit.voice.mlx-audio and dev.sessionkit.voice.ears-<name>.
VOICE_LABELS = (
    "dev.sessionkit.voice.mlx-audio",
    "dev.sessionkit.voice.ears-mouth",
    "dev.sessionkit.voice.ears-keeper",
    "dev.sessionkit.voice.ears-mail",
)
# The two old forms: the earlier docs' com.sessionvoice.*, and 0.1.0's
# com.voicemode.ears-*. INSTALL.md names them only as history.
OLD_LABEL_FORMS = ("com.sessionvoice.", "com.voicemode.ears-")


def _doc_blocks(text: str) -> list[str]:
    """Paragraphs and list items: split on blank lines, then before each item marker."""
    blocks = []
    for para in re.split(r"\n\s*\n", text):
        blocks += re.split(r"\n(?=\s*(?:-|\d+\.) )", para)
    return blocks


def test_install_doc_names_the_voice_labels_dev_sessionkit():
    # SK-137: one scheme for every shipped label; the kit names voice's.
    hearing = _install_section(5)
    assert "`dev.sessionkit.<package>.<job>`" in hearing
    assert "`dev.sessionkit.voice.ears-<name>`" in hearing
    for label in (*VOICE_LABELS, "dev.sessionkit.voice.ears-speakers"):
        assert f"`{label}`" in hearing
    assert "`dev.sessionkit.voice.*`" in _install_section(8)


def test_install_doc_names_the_old_label_forms_only_as_history():
    # SK-137: both old forms stay only beside the wording that retires them;
    # no step loads, checks or boots out a job under an old label as current.
    named = {form: 0 for form in OLD_LABEL_FORMS}
    for block in _doc_blocks(INSTALL_DOC):
        for form in OLD_LABEL_FORMS:
            if form in block:
                named[form] += 1
                assert "retire" in block, f"{form} named without retiring it: {block[:120]!r}"
    assert all(named.values()), named
    assert "retires the old\nform" in _install_section(5)


def test_install_doc_launchctl_greps_find_the_dev_sessionkit_labels():
    # SK-137: the look and the check find today's labels and the old forms.
    uninstall = _install_section(8)
    greps = re.findall(r"`launchctl list \| grep -E '([^']+)'`", uninstall)
    assert len(greps) == 2, greps
    look, check = greps
    assert look.startswith("dev\\.sessionkit\\.|")
    assert check.startswith("dev\\.sessionkit\\.voice\\.|")
    for pattern in greps:
        assert "sessionvoice" in pattern
        assert "voicemode\\.ears" in pattern


def test_install_doc_runs_the_kits_own_ears_and_gives_the_hook_json():
    hearing = _install_section(5)
    assert "`ears services install`, the kit's own `ears`" in hearing
    # SK-88 (0.2.1): the kit floors sessionvoice at 0.2.0, which ships the
    # keeper in its package, so 0.1.0's plugin bin/ears detour is gone.
    assert "**On sessionvoice 0.1.0**" not in hearing
    assert not re.search(r"bin/ears(?![-\w])", hearing)
    assert "sessionvoice/sessionvoice/0.1.0" not in hearing
    assert "com.voicemode.ears-mouth" not in hearing
    for label in VOICE_LABELS:
        assert f"`{label}`" in hearing
    assert "loads `speech`, `mouth`, `keeper` and `mail`" in hearing
    assert "`stt`, `speech`, `mouth`, `keeper`, `mail` and `speakers`" in hearing
    block = re.search(r"```json\n(.*?)\n\s*```", hearing, re.DOTALL)
    assert block, "section 5 gives the hook JSON to paste"
    hooks = json.loads(block.group(1))["hooks"]
    for event in ("PostToolUse", "PostToolBatch"):
        [group] = hooks[event]
        [hook] = group["hooks"]
        assert hook == {"type": "command", "command": "ears heard hook || exit 1", "timeout": 5}


def test_install_doc_gives_the_optional_speakers_step():
    hearing = _install_section(5)
    step = hearing[hearing.index("**Optional: speaker names.") :]
    assert hearing.index("**Then** `ears services install`") < hearing.index(
        "**Optional: speaker names."
    )
    for line in (
        "ears services install --only speakers",
        "ears speakers enrol",
        "ears services status",
    ):
        assert line in step
    assert "arm64" in step and "macOS 14" in step and "`uv`" in step
    assert "about 190 MB, once" in step
    assert "microphone grant" in step


def test_install_doc_links_the_hosted_speech_endpoint_with_no_key():
    hearing = _install_section(5)
    assert (
        "[sessionvoice's docs/models.md, A hosted speech endpoint instead][sv-hosted]"
    ) in hearing
    # SK-88 (0.2.1): the kit installs sessionvoice 0.2.0 or later, so the
    # hosted endpoint is no longer tagged against 0.1.0.
    assert re.search(r"The mouth can also speak through a hosted", hearing)
    assert "(not in 0.1.0)" not in hearing
    assert "`MOUTH_TTS_KEY`" in hearing
    assert "MOUTH_TTS_KEY=" not in INSTALL_DOC
    assert (
        "[sv-hosted]: https://github.com/sessionkit/sessionvoice/blob/HEAD/"
        "docs/models.md#a-hosted-speech-endpoint-instead"
    ) in INSTALL_DOC


def test_install_doc_puts_ears_arm_on_path_through_the_plugin():
    # SK-74: ears-arm on the Bash tool's PATH is 0.2.0's (bin/ears-arm).
    # SK-88 (0.2.1): the kit floors sessionvoice at 0.2.0, so 0.1.0's
    # full-path branch is gone.
    hearing = _install_section(5)
    assert re.search(r"`ears-arm`\s+is\s+on\s+the\s+Bash\s+tool's\s+PATH", hearing)
    assert re.search(r"the\s+plugin's\s+`bin/ears-arm`\.\s+That shim runs", hearing)
    assert "**On 0.1.0** it is not on your PATH" not in hearing
    assert "sessionvoice/sessionvoice/0.1.0/skills/ears/scripts/ears-arm" not in hearing
    assert "It is not on your PATH." not in hearing


# SK-105: "Your first agent, in tmux", the last part of INSTALL.md section 4,
# after the install. tmux comes from Homebrew, which brings no Python (the
# kit's Python is uv's); the agent starts with `session start`; it listens
# with `pager listen`; mailing it waits on the mail-server step (section 5's
# "Mail between agents"), which has no runbook, so the doc says NOT YET and
# invents none. Every kit verb and flag it names ships in the locked release
# set, read from the installed packages here, not from memory.
FIRST_AGENT_HEADING = "### Your first agent, in tmux"


def _first_agent() -> str:
    checks = _install_section(4)
    assert FIRST_AGENT_HEADING in checks, "section 4 has the first-agent part"
    return checks[checks.index(FIRST_AGENT_HEADING):]


def test_first_agent_comes_after_the_install():
    at = INSTALL_DOC.index(FIRST_AGENT_HEADING)
    assert INSTALL_DOC.index("## 3. Install the plugins") < at
    assert INSTALL_DOC.index("## 4. First checks") < at < INSTALL_DOC.index("## 5. ")
    assert INSTALL_DOC.count(FIRST_AGENT_HEADING) == 1


def test_first_agent_gets_tmux_from_homebrew_and_no_python():
    part = _first_agent()
    assert "`brew install tmux`" in part
    assert "`tmux -V`" in part
    assert "tmux brings no Python with it" in part
    assert "so do not `brew install python`" in part
    assert part.count("brew install python") == 1


def test_first_agent_starts_tmux_and_the_agent():
    part = _first_agent()
    [block] = re.findall(r"^ *```bash\n(.*?)^ *```", part, re.MULTILINE | re.DOTALL)
    assert "tmux new-session -s agents" in block
    assert "`session start`" in part
    assert "`session start --dry-run`" in part


def test_first_agent_names_only_verbs_and_flags_that_ship():
    from sessionmail.message import cli as message
    from sessionmail.pager import cli as pager
    from sessiontools.cli import VERBS

    shipped = {
        "message": set(message.commands),
        "pager": set(pager.commands),
        "session": {verb for verb, _ in VERBS},
    }
    part = _first_agent()
    named = re.findall(r"`(message|pager|session) ([a-z-]+)", part)
    assert {tool for tool, _ in named} == set(shipped)
    for tool, verb in named:
        assert verb in shipped[tool], f"`{tool} {verb}` is not in the release set"
    start_help = subprocess.run(
        [str(Path(sys.executable).parent / "session"), "start", "--help"],
        capture_output=True, text=True, check=True,
    ).stdout
    for flag in set(re.findall(r"`session start[^`]*?(--[a-z-]+)", part)):
        assert flag in start_help, f"`session start {flag}` does not ship"


def test_first_agent_mails_by_the_drop_and_points_at_the_step():
    # SK-88 (0.2.1): sessionmail 0.2.0 is the floor, so step 5 is the drop,
    # measured on a fresh VM; agent to agent stays NOT YET.
    part = _first_agent()
    flat = " ".join(part.split())
    assert part.startswith(f"{FIRST_AGENT_HEADING}\n\n**NOT YET** as a whole")
    assert "**Mail it.**" in part and "**Mail it: NOT YET.**" not in part
    assert f"[{MAIL_HEADING}]({MAIL_ANCHOR}) in section 5" in part
    assert f"\n### {MAIL_HEADING}\n" in _install_section(5)
    assert "`message send admin` printed `sent via mail drop (no MTA)`, exit 0" in flat
    assert "**NOT YET** as mail from one agent to another on a fresh Mac" in flat
    assert "sessionmail 0.1.0" not in part


# A stranger's mail path with no postfix assumed. From sessionmail
# 0.2.0 the file drop is the default carrier and postfix is opt-in (ruled by
# the owner; sessionmail's settings docs say so), so the section says so as a
# fact, never as advice ("recommended"). It labels the drop experimental,
# names the release it needs, and lists every step the walk measured. The
# intro, step 5 of the first agent, ears-mail's line, G29, the uninstall and
# the README point at it by its anchor.
MAIL_HEADING = "Mail between agents"
MAIL_ANCHOR = "#mail-between-agents"


def _mail_section() -> str:
    five = _install_section(5)
    start = five.index(f"### {MAIL_HEADING}\n")
    end = five.find("\n### ", start + 1)
    return five[start:end if end != -1 else None]


def test_mail_anchor_is_the_mail_heading():
    slug = "#" + re.sub(r"[^a-z0-9 -]", "", MAIL_HEADING.lower()).replace(" ", "-")
    assert slug == MAIL_ANCHOR
    assert INSTALL_DOC.count(f"\n### {MAIL_HEADING}\n") == 1


def test_mail_section_has_the_drop_and_postfix_opt_in_and_no_advice():
    mail = _mail_section()
    flat = " ".join(mail.split())
    assert "**The file drop. EXPERIMENTAL.**" in mail
    assert "`message send` hands each message to sessionmail's file drop by default" in flat
    assert "Postfix is opt-in" in flat
    assert "**Mail to other Macs: postfix, opt-in.**" in mail
    assert mail.index("**The file drop.") < mail.index("**Mail to other Macs:")
    # The old branch, "nothing to do", is gone: from 0.2.0 a postfix host must
    # name postfix, or the drop carries its mail.
    assert "Nothing to do." not in mail
    assert "**Already have postfix delivering agent mail?** From sessionmail 0.2.0, name it" in flat
    assert not re.search(r"recommend", mail, re.IGNORECASE)


def test_mail_section_postfix_is_named_in_the_file_and_never_edited():
    mail = _mail_section()
    flat = " ".join(mail.split())
    [opt_in] = re.findall(r"^```json\n(.*?)^```", mail, re.MULTILINE | re.DOTALL)
    assert json.loads(opt_in) == {"version": 1, "sendmail": "/usr/sbin/sendmail"}
    assert "`~/.sessionkit/mail/settings/mail.json`" in mail
    assert "Make the file if there is none" in flat
    assert "`SESSIONMAIL_SENDMAIL`, when it is set, beats the file" in flat
    assert "Neither `sessionkit setup` nor mail setup ever edits postfix" in flat
    assert "`message setup --write-maps`" in flat and "`sessionkit setup` never passes it" in flat
    assert "**NOT YET** walked" in flat


def test_mail_section_names_every_drop_step():
    mail = _mail_section()
    flat_mail = " ".join(mail.split())
    assert "sessionmail 0.2.0" in mail and "not released yet" not in mail
    assert "the kit asks for 0.2.0 or later" in flat_mail
    assert "**Get sessionmail 0.2.0.**" in mail and "**Get sessionmail 0.2.0. NOT YET.**" not in mail
    [index, boxes] = re.findall(r"^ *```bash\n(.*?)^ *```", mail, re.MULTILINE | re.DOTALL)
    # The drop is the default from sessionmail 0.2.0: no line to set, so no
    # `~/.zshenv` edit and no suffix line (measured on sessionmail 0.2.0 with
    # no variable, no settings file, no suffix and no tailscale). First boxes
    # come from mail setup, not mkdir.
    assert "**Nothing to set.**" in mail
    # A fresh install has no mail.json: the drop default is package data, so
    # the doc never sends a stranger to read it from a file that is not there.
    flat = " ".join(mail.split())
    assert "A fresh install has no such file and needs none" in flat
    assert "is `\"drop\"` unless you name another in" in flat
    assert "export SESSIONMAIL_SENDMAIL" in mail  # only as an earlier build's line
    assert "~/.zshenv" not in mail
    assert "MAGICDNS_SUFFIX=" not in mail
    assert index.strip() == 'notmuch --config="$HOME/.config/notmuch/sessionkit/config" new'
    assert boxes.strip() == "message setup --box <box>"
    assert "mkdir" not in mail
    assert "`jq`" in mail and "brew install jq" in mail
    assert "**Same Mac only.**" in mail
    assert "sent via mail drop (no MTA)" in mail
    steps = re.split(r"\n\d\. ", mail)[1:]
    assert len(steps) == 7
    for step in steps:
        assert "MEASURED" in step or "NOT YET" in step, step[:60]


def test_mail_section_uses_its_own_notmuch_profile_and_never_yours():
    mail = _mail_section()
    flat = " ".join(mail.split())
    notmuch = mail.index("**Install notmuch. HUMAN (Homebrew).**")
    setup = mail.index("**Make the boxes: `sessionkit setup`**")
    assert notmuch < setup
    assert "Run `brew install notmuch` before step 4" in flat
    assert "`~/.config/notmuch/sessionkit/config`" in flat
    assert "It never reads or writes a notmuch config of your own" in flat
    assert "`~/.notmuch-config` and any other profile are left exactly as they are" in flat
    # The profile's first `notmuch new` comes after setup's first run, which
    # writes the profile and leaves the hook BLOCKED, exit 4.
    assert "leaves its notmuch step `BLOCKED` and exits 4" in flat
    # Mail setup adopts no notmuch database: on a mail folder that already
    # holds one it writes no profile and says MANUAL (measured on the verb).
    # The doc names the line a stranger reads, so the uninstall can ask for it.
    assert "It adopts no notmuch database" in flat
    assert "`notmuch-profile` line says `MANUAL` instead of `wrote`" in flat
    assert "That database is yours, and the uninstall leaves it (section 8)" in flat
    assert "\"cannot load config file\"" not in mail
    assert "give notmuch a config" not in mail


def test_sessionkit_setup_names_mail_setup_and_its_exits():
    two = INSTALL_DOC[INSTALL_DOC.index("## 2. Install the kit"):INSTALL_DOC.index("### Operator and administrators")]
    assert "**Mail first.** It runs sessionmail's mail setup, `message setup`" in two
    # 0.2.x: the kit floors sessionmail at 0.2.0, which has mail setup, so a
    # fresh Mac meets exit 4 (notmuch BLOCKED), not 0.1.0's refusal text.
    assert "**On a fresh Mac it exits 4, and that is expected.**" in two
    assert "1 step(s) left for you: notmuch-hook (BLOCKED)" in two
    assert "On a fresh install it refuses, and that is expected." not in two
    assert "this sessionmail has no `message setup` (`message setup --help` exited 2)" not in two
    assert "**Its exit:** 0 all done; 1 " in two and "; 4 the" in two
    # A dry run on a fresh host: the verb exits 4 and makes no box, so the
    # operator check refuses and the kit exits 1 (measured on the real verb).
    flat = " ".join(two.split())
    assert "Mail setup's dry run exits 4 while any of its steps is still to do" in flat
    assert "`sessionkit setup --dry-run` exits 1 there" in flat
    # A dry run's 4 sets nothing: the exit line's "the operator is set" is a
    # real run's, so the dry-run paragraph must not say it "reads the same way".
    assert "So with `--dry-run`, 4 means mail steps are still to do and the operator check did not refuse" in flat
    assert "or you gave `--address`" in flat
    assert "nothing is set yet, and the real run does what it can" in flat
    # With --address the operator check needs no box, so a dry run's 4 does
    # not mean the box is there (measured: 4 on a fresh home with --address).
    assert "4 means your box is there" not in flat
    assert "A dry run reads the same way" not in flat


def test_mail_setup_box_claims_hold_on_the_sessionmail_measured():
    # Measured on the verb: on a fresh install the box it makes is named for
    # the account. The doc claims no more than that: an operator set later is
    # not promised to change which box mail setup makes.
    flat = " ".join(INSTALL_DOC.split())
    assert "On a fresh install your box is named for your account" in flat
    assert "It makes these boxes and no others: a box named for your account" in flat
    for claim in ("operator's box if one is set", "unless an operator box is already set",
                  "the operator's box (`operator.mailbox`, else"):
        assert claim not in flat, claim


def test_the_registry_note_says_no_command_creates_one():
    """No command creates a trust registry today: the note says so, names
    what the key points at and the doc, and promises no creating command."""
    flat = " ".join(AGENT_LETTER.split())
    assert "**No command creates a registry today**" in flat
    assert "holds an `allowed_signers` file and a `certs/` folder" in flat
    assert (
        "[sessionmail's docs/message-seat.md]"
        "(https://github.com/sessionkit/sessionmail/blob/HEAD/docs/message-seat.md)"
    ) in flat
    assert "name the command" not in flat
    assert "names the command" not in flat
    assert "the command that creates" not in flat


def test_the_registry_refusal_is_said_as_sessionmail_0_2_0s():
    """sessionmail 0.2.0, the release the kit floors, already ships the
    registry refusal that names the key, says no registry is created and
    points at the doc: the letter says so, and calls none of it unreleased."""
    flat = " ".join(AGENT_LETTER.split())
    assert "A sessionmail change, not yet released" not in flat
    assert "not yet released" not in flat
    assert (
        "In sessionmail 0.2.0 that refusal says what the key names, says that "
        "sessionmail does not create a registry today, and points at that doc "
        "(read in its source, sessionmail 0.2.0 from PyPI, 2030-06-09:"
    ) in flat


def test_mail_setup_boxes_are_measured_on_sessionmail_0_2_0():
    """INSTALL section 6 step 4's MEASURED line names the release it ran on,
    never pre-release code, and lists the agent's box `claude`."""
    flat = " ".join(INSTALL_DOC.split())
    assert "sessionmail's unreleased code" not in flat
    assert (
        "**MEASURED** (2030-06-09, this release's sessionkit with sessionmail 0.2.0 "
        "from PyPI, a temporary home directory): `sessionkit setup --mailbox <box>` "
        "ran the real `message setup`, which made the mail folder, the operator's "
        "box, that box and `claude`, and wrote the notmuch profile; setup then "
        "wrote the operator, exit 4"
    ) in flat
    assert "`claude` and wrote the notmuch profile" not in flat


# The staged placeholders (one per open setting, an HTML comment) are all
# filled: none may come back. The marker is built, so this file holds none.
PLACEHOLDER = "PICK" + "-"


@pytest.mark.parametrize("name", ["README.md", "INSTALL.md", "CHANGELOG.md",
                                  "docs/agent-letter.md", "src/sessionkit/setup.py"])
def test_no_staged_placeholder_is_left(name):
    assert PLACEHOLDER not in (ROOT / name).read_text(encoding="utf-8"), name


def test_mail_section_launchd_senders_ride_the_drop_from_their_0_2_0_releases():
    # launchd reads no shell file, and from sessionmail 0.2.0 none is needed:
    # `message send` reads the carrier from the settings file. SK-88 (0.2.1):
    # the three senders' 0.2.1 releases, which the kit installs, hand their
    # mail to `message send` (read in their 0.2.1 source); 0.1.0's
    # `/usr/sbin/sendmail` is named only as history. Not walked: NOT YET.
    mail = _mail_section()
    start = mail.index("**Jobs launchd starts.**")
    note = mail[start:mail.index("\n3. ", start)]
    flat = " ".join(note.split())
    assert "launchd reads no shell file, and the drop needs none" in flat
    assert "`message send` reads the carrier from the settings file" in flat
    for sender in ("**The phone bot**", "**sessionvoice's mouth notices**",
                   "**ears-mail's heard turns**"):
        assert sender in note
    assert "all three hand their mail to `message send`, so they ride the drop" in flat
    assert "From sessionvoice 0.2.1 and sessionphone 0.2.1, the releases the kit installs" in flat
    assert "**NOT YET:** none of these releases is out" not in flat
    assert "**NOT YET** walked" in flat
    assert "Their 0.1.0 releases, before the kit floored them at 0.2.0, handed it to `/usr/sbin/sendmail`" in flat
    assert "None of these three changes has shipped." not in note


def test_every_mail_pointer_uses_the_anchor():
    for doc in (INSTALL_DOC, README):
        assert not re.search(
            r"no (postfix )?runbook|no (mail )?setup script|needs a local postfix",
            doc, re.IGNORECASE,
        )
    assert f"\n[mail]: INSTALL.md{MAIL_ANCHOR}\n" in README
    assert INSTALL_DOC.count(f"({MAIL_ANCHOR})") >= 4


# SK-68: the pager monitor is on by default since SM-726. It ships in the root
# sessionmail plugin (monitors/monitors.json -> hooks/pager-monitor ->
# `pager listen --monitor`), and sessionmail's plugins/pager-monitor is retired.
# The off switch and mute/unmute are in sessionmail's pager from 0.2.0, the
# floor the kit installs (SK-88, 0.2.1), so the docs say so, MEASURED.
AGENT_LETTER = (ROOT / "docs" / "agent-letter.md").read_text(encoding="utf-8")
MONITOR_DOCS = {"INSTALL.md": INSTALL_DOC, "docs/agent-letter.md": AGENT_LETTER}


def test_no_doc_calls_the_pager_monitor_opt_in():
    for name, text in MONITOR_DOCS.items():
        flat = " ".join(text.split())
        assert "opt-in `plugins/pager-monitor`" not in flat, name
        assert "monitor is opt-in" not in flat, name
        assert "opt-in plugin, `plugins/pager-monitor`" not in flat, name
        assert "does not turn it on" not in flat, name
        assert "on by default" in flat, name


def test_the_monitor_off_switch_and_mute_ship_in_the_0_2_0_pager():
    for name in ("INSTALL.md", "docs/agent-letter.md"):
        flat = " ".join(MONITOR_DOCS[name].split())
        assert "SESSIONMAIL_MONITOR=off" in flat, name
        assert "0.1.0" in flat, name
    # SK-88 (0.2.1): INSTALL.md section 4 and the agent letter are both
    # MEASURED against sessionmail 0.2.0 from PyPI.
    install = " ".join(INSTALL_DOC.split())
    assert "`pager mute` / `pager unmute` are **NOT YET**" not in install
    assert ("`pager mute` / `pager unmute` ship in sessionmail 0.2.0, the release the kit "
            "installs") in install
    assert "Claude Code showed `1 monitor`" in install
    assert "the `--monitor` flag in the 0.1.0 `pager` the kit installs" not in install
    letter = " ".join(AGENT_LETTER.split())
    assert "`pager stop --kill` ship in sessionmail 0.2.0, the release the kit installs." in letter
    assert "**NOT YET** for a kit install: sessionmail's off switch" not in letter


def test_the_monitor_docs_say_claude_code_runs_it_only_when_interactive():
    # SK-68 review: Claude Code runs a plugin monitor only in an interactive,
    # trusted session with its monitor gate on (sessionmail docs/pager-monitor.md;
    # trust: the retired plugins/pager-monitor README, e47c228^),
    # so "on by default" must not read as "every session has it".
    for name in ("INSTALL.md", "docs/agent-letter.md"):
        flat = " ".join(MONITOR_DOCS[name].split())
        assert "only in an interactive session (never `claude -p`)" in flat, name
        assert "nothing in Claude Code says so" in flat, name


def test_the_agent_letter_tags_what_pager_off_and_stop_do_by_version():
    # SK-68: `pager off`/`stop` end the monitor for good on the 0.1.0
    # pager from PyPI (measured: it has no `mute` and no `stop --kill`). From
    # sessionmail 0.2.0 (SM-726, measured from PyPI) they REFUSE on the monitor
    # with exit 4, write nothing, and name `pager mute` and `pager stop --kill`;
    # a hand `pager listen` still stops as before.
    flat = " ".join(AGENT_LETTER.split())
    assert "Either one ends the monitor for good" not in flat
    assert "**On sessionmail 0.1.0, before the kit floored it at 0.2.0:** either one ends the monitor for good" in flat
    assert "**The kit's `pager`, sessionmail 0.2.0 and later:**" in flat
    assert "**NOT YET for a kit install, the next sessionmail release:**" not in flat
    assert "on the monitor, both REFUSE. They exit 4, write nothing" in flat
    assert "`--kill` is the only way to end the monitor" in flat
    # SM-726 master: after `stop --kill` the ride-along says the monitor was
    # ENDED (hook_lines.toml `monitor_ended`), not 0.1.0's "stopped on purpose".
    assert "it ends it for good, as above" not in flat
    assert "say *this session's pager monitor was ended*, not *stopped on purpose*" in flat
    assert "On a hand `pager listen`, `pager off` and `pager stop` still stop it, as before." in flat


# The user-facing prose a stranger reads names no internal tracker id and no
# code from the release rehearsal's private record: each is said in plain words
# instead (MEASURED keeps its meaning: it ran, on the machine and date given).
# Code comments and tests are not user-facing, so this reads the prose only.
SHIPPED_PROSE = (
    "README.md",
    "INSTALL.md",
    "skills/sessionkit/SKILL.md",
    "docs/agent-letter.md",
    "docs/troubleshooting.md",
    "docs/configuration.md",
    "docs/settings.md",
    "site/README.md",
    "site/index.html",
)
INTERNAL_CODE = re.compile(
    r"\b(SK|SM|EARS|PHONE|ST|SV|TM)-[0-9]+|\bJ[0-9]+\b|\bG[0-9]+\b"
    r"|record [0-9]+|case [0-9]+"
)


@pytest.mark.parametrize("name", SHIPPED_PROSE)
def test_shipped_prose_carries_no_internal_codes(name):
    text = (ROOT / name).read_text(encoding="utf-8")
    hits = [m.group(0) for m in INTERNAL_CODE.finditer(text)]
    assert not hits, f"{name}: {hits}"


def test_the_internal_code_pattern_hits():
    # A zero is a receipt only when the same pattern is shown to hit.
    for sample in ("(SM-726)", "(J6, record 21)", "G13", "case 82", "EARS-381"):
        assert INTERNAL_CODE.search(sample), sample


# Two kinds of link no shipped file may carry, tests included (each pattern
# here is built from pieces, so this file does not trip its own gate):
#
# - A branch name in a link into a family repository. In a
#   github.com/sessionkit/<repo>/(blob|tree|raw)/<ref> URL, or a
#   raw.githubusercontent.com/sessionkit/<repo>/<ref> one, <ref> may only be
#   HEAD (the repository's default branch, so a renamed branch breaks nothing)
#   or a v* release tag. Any branch fails, master too. A clone with -b or
#   --branch on main fails as well: the public repositories are on master.
# - A full URL into this repository. The kit's own links are relative, so the
#   docs read in a checkout or an editor without opening a browser. Links into
#   the other family repositories stay full, on HEAD.
#
# ONE exemption, and only from the second check: the literal
# `.../sessionkit/sessionkit/blob/HEAD/<path>` that a landed CHANGELOG bullet
# quotes, in CHANGELOG.md only. It is code text with a placeholder, not a link
# anyone can follow, and a landed bullet's words do not change. Any other full
# self-URL, in CHANGELOG.md or anywhere, and the same literal in any other
# file, still fails. The ref check exempts nothing.
#
# The walk reads the tree, not git, so the gate runs the same in a checkout,
# in a release archive and in a clone of that archive.
BRANCH = "ma" + "in"
MASTER = "mas" + "ter"
SELF_REPO = "github\\.com/sessionkit/session" + "kit"
FAMILY_REF = re.compile(
    r"github\.com/sessionkit/[A-Za-z0-9_.-]+/(?:blob|tree|raw)/([^/\s)\]>`'\"#?]+)"
    r"|raw\.githubusercontent\.com/sessionkit/[A-Za-z0-9_.-]+/"
    r"((?:refs/(?:heads|tags)/)?[^/\s)\]>`'\"#?]+)"
)
GOOD_REF = re.compile(r"HEAD|v[0-9][A-Za-z0-9_.+-]*|refs/tags/v[0-9][A-Za-z0-9_.+-]*")
WRONG_CLONE = re.compile(r"(?:-b|--branch)(?:\s+|=)[`'\"]?" + BRANCH + r"\b")
FULL_SELF_URL = re.compile(SELF_REPO + r"/(?:blob|tree|raw)/\S*")
SELF_PLACEHOLDER = "github.com/sessionkit/session" + "kit/blob/HEAD/<path>"
PLACEHOLDER_HOME = "CHANGELOG.md"
NOT_SHIPPED_DIRS = {"build", "dist", "node_modules", "__pycache__"}


def _shipped_files(root: Path = ROOT) -> list[Path]:
    """Every file under root, less git, virtualenvs, caches and build output."""
    found = []
    for path in sorted(root.rglob("*")):
        dirs = path.relative_to(root).parts[:-1]
        if any((d.startswith(".") and d != ".claude-plugin") or d in NOT_SHIPPED_DIRS
               or d.endswith(".egg-info") for d in dirs):
            continue
        if path.is_file() and not path.is_symlink():
            found.append(path)
    return found


def _wrong_branch_hits(text: str) -> list[str]:
    """Each family link whose ref is not HEAD or a v* tag, and each clone on main."""
    hits = [m.group(0) for m in FAMILY_REF.finditer(text)
            if not GOOD_REF.fullmatch(m.group(1) or m.group(2))]
    return hits + [m.group(0) for m in WRONG_CLONE.finditer(text)]


def _full_self_url_hits(text: str, placeholder_ok: bool = False) -> list[str]:
    return [m.group(0) for m in FULL_SELF_URL.finditer(text)
            if not (placeholder_ok and m.group(0).startswith(SELF_PLACEHOLDER))]


def _gate(root: Path = ROOT) -> dict[str, list[str]]:
    hits = {}
    for path in _shipped_files(root):
        name = str(path.relative_to(root))
        text = path.read_bytes().decode("utf-8", errors="ignore")
        found = _wrong_branch_hits(text) + _full_self_url_hits(
            text, placeholder_ok=name == PLACEHOLDER_HOME)
        if found:
            hits[name] = found
    return hits


def test_no_shipped_file_names_a_branch_or_a_full_self_url():
    files = _shipped_files()
    assert ROOT / "README.md" in files and ROOT / "CHANGELOG.md" in files
    assert ROOT / "tests" / "test_readme.py" in files
    assert _gate() == {}


def test_the_gate_reads_changelog_and_exempts_only_the_placeholder(tmp_path):
    self_url = "https://" + SELF_PLACEHOLDER.replace("<path>", "INSTALL.md")
    (tmp_path / "CHANGELOG.md").write_text(
        f"at `https://{SELF_PLACEHOLDER}`.\n- see {self_url}\n", encoding="utf-8")
    assert _gate(tmp_path) == {"CHANGELOG.md": [self_url.removeprefix("https://")]}
    # The placeholder on a branch is not exempt: the ref check exempts nothing.
    for branch in (BRANCH, MASTER):
        on_branch = SELF_PLACEHOLDER.replace("/HEAD/", f"/{branch}/")
        (tmp_path / "CHANGELOG.md").write_text(f"`https://{on_branch}`.\n", encoding="utf-8")
        assert on_branch.removesuffix("/<path>") in _gate(tmp_path)["CHANGELOG.md"]


def test_the_placeholder_is_exempt_in_changelog_only(tmp_path):
    (tmp_path / "CHANGELOG.md").write_text(f"`https://{SELF_PLACEHOLDER}`\n", encoding="utf-8")
    (tmp_path / "README.md").write_text(f"`https://{SELF_PLACEHOLDER}`\n", encoding="utf-8")
    assert _gate(tmp_path) == {"README.md": [SELF_PLACEHOLDER + "`"]}


SELF = "https://github.com/sessionkit/session" + "kit"
MAIL = "https://github.com/sessionkit/session" + "mail"
VOICE = "https://github.com/sessionkit/session" + "voice"
RAW = "https://raw.githubusercontent.com/sessionkit/session" + "mail"


@pytest.mark.parametrize("planted", [
    *(f"[x]({MAIL}/blob/{b}/README.md)" for b in (BRANCH, MASTER, "develop")),
    f"[x]: {MAIL}/tree/{MASTER}/skills/memory",
    f"[x]: {MAIL}/tree/{BRANCH}/skills/memory",
    f"curl {VOICE}/raw/{MASTER}/README.md",
    f"curl {VOICE}/raw/{BRANCH}/README.md",
    f"[x]({SELF}/blob/{MASTER}/INSTALL.md)",
    f"curl {RAW}/{BRANCH}/README.md",
    f"curl {RAW}/{MASTER}/README.md",
    f"curl {RAW}/refs/heads/{BRANCH}/x",
    f"curl {RAW}/refs/heads/HEAD/x",
    f"git clone -b {BRANCH} https://github.com/sessionkit/sessionmail",
    f"git clone --branch {BRANCH} https://github.com/sessionkit/sessionmail",
    f"git clone --branch={BRANCH} https://github.com/sessionkit/sessionmail",
    f"clone it again with\n  `-b {BRANCH}`, the branch",
])
def test_the_wrong_branch_guard_hits(planted):
    # A zero is a receipt only when the same guard is shown to hit.
    assert _wrong_branch_hits(planted)


@pytest.mark.parametrize("planted", [
    f"[x]({SELF}/blob/HEAD/INSTALL.md)",
    f"[x]({SELF}/tree/HEAD/docs/)",
    f"[x]: {SELF}/raw/HEAD/README.md",
    f"[x]({SELF}/blob/HEAD/INSTALL.md#mail-between-agents)",
    f"[x]({SELF}/blob/v0.2.0/INSTALL.md)",
    f"`{SELF}/blob/HEAD/<paths>`",
])
def test_the_full_self_url_guard_hits(planted):
    assert _full_self_url_hits(planted, placeholder_ok=True)


@pytest.mark.parametrize("fine", [
    "[x](https://github.com/sessionkit/sessionmail/blob/HEAD/README.md)",
    "[x](https://github.com/sessionkit/sessionmail/blob/HEAD/README.md#usage)",
    "[x]: https://github.com/sessionkit/sessionmail/tree/HEAD/skills/memory",
    "[x](https://github.com/sessionkit/sessionmail/blob/v0.2.0/README.md)",
    "curl https://raw.githubusercontent.com/sessionkit/sessionmail/HEAD/README.md",
    "curl https://raw.githubusercontent.com/sessionkit/sessionmail/refs/tags/v0.2.0/x",
    "git clone -b master https://github.com/sessionkit/sessionmail",
    f"git clone {SELF}",
    "[sv-parts]: https://github.com/sessionkit/sessionvoice#components",
    f"[x](INSTALL.md) and `https://{SELF_PLACEHOLDER}`.",
    f"@{BRANCH}.command(context_settings=CTX)",
    f"https://github.com/someone/voicemode/blob/{BRANCH}/README.md",
])
def test_the_gate_passes_head_tags_relative_links_and_other_uses(fine):
    assert _wrong_branch_hits(fine) == []
    assert _full_self_url_hits(fine, placeholder_ok=True) == []


def test_the_shipped_file_walk_skips_git_and_virtualenvs(tmp_path):
    for rel in ("README.md", ".claude-plugin/plugin.json", ".gitattributes",
                ".git/config", ".venv/lib/x.py", "dist/x.whl",
                "src/pkg/__pycache__/x.pyc", "src/pkg.egg-info/PKG-INFO"):
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / rel).write_text("x", encoding="utf-8")
    walked = {str(p.relative_to(tmp_path)) for p in _shipped_files(tmp_path)}
    assert walked == {"README.md", ".claude-plugin/plugin.json", ".gitattributes"}


# README.md links into this repository relatively, so it reads in a checkout or
# an editor without opening a browser: `](INSTALL.md)`, `](docs/settings.md)`,
# `](INSTALL.md#mail-between-agents)`. Each relative link names a file or a
# directory this tree holds, and its #anchor, if any, is a heading there. A full
# github.com/sessionkit/sessionkit/blob|tree|raw URL is not used for one: the
# gate above fails on it in any shipped file. Links into the other family
# repositories stay full, on HEAD.
NOT_IN_REPO = re.compile(r"^(?:[a-z][a-z0-9+.-]*:|//|#)", re.IGNORECASE)
LINK_TARGETS = (
    re.compile(r"\]\(\s*<?([^)\s>]*)"),                         # [x](t) and ![x](t)
    re.compile(r"^ {0,3}\[[^\]]+\]:\s*<?([^\s>]+)", re.MULTILINE),  # [x]: t
    re.compile(r"""\b(?:href|src)\s*=\s*["']([^"']*)["']""", re.IGNORECASE),
)


def _link_targets(text: str) -> list[str]:
    return [m.group(1) for pattern in LINK_TARGETS for m in pattern.finditer(text)]


def _relative_links(text: str) -> list[str]:
    """Every link target that is not a URL, a scheme or an in-page anchor."""
    return [t for t in _link_targets(text) if not NOT_IN_REPO.match(t)]


def _heading_anchors(text: str) -> set[str]:
    """GitHub's anchor for each heading: lower case, punctuation dropped,
    spaces to hyphens."""
    return {re.sub(r"[^a-z0-9 _-]", "", h.strip().lower()).replace(" ", "-")
            for h in re.findall(r"^#{1,6} (.+)$", text, re.MULTILINE)}


def _unresolved(target: str, root: Path = ROOT) -> str | None:
    """Why a relative README link does not resolve in root, else None."""
    path, _, anchor = target.partition("#")
    file = (root / path).resolve()
    if not file.is_relative_to(root.resolve()):
        return f"{target}: leaves the repository"
    if not file.exists():
        return f"{target}: names no file or directory"
    if anchor and anchor not in _heading_anchors(file.read_text(encoding="utf-8")):
        return f"{target}: names no heading there"
    return None


def test_readme_links_this_repo_relatively_and_each_link_resolves():
    links = _relative_links(README)
    assert "INSTALL.md" in links and "INSTALL.md#mail-between-agents" in links
    assert [why for why in map(_unresolved, links) if why] == []


def test_the_readme_link_check_can_fail():
    # A zero is a receipt only when the same check is shown to hit.
    assert _unresolved("NO-SUCH-FILE.md")
    assert _unresolved("INSTALL.md#no-such-heading")
    assert _unresolved("../README.md")
    assert _unresolved("INSTALL.md#mail-between-agents") is None
    assert _unresolved("docs/") is None


@pytest.mark.parametrize("planted", [
    "[the manual install](INSTALL.md)",
    "[mail](INSTALL.md#mail-between-agents)",
    "[letter](docs/agent-letter.md \"title\")",
    "[dir](./docs/)",
    "![logo](site/logo.png)",
    "[up](../README.md)",
    "[x](<docs/a b.md>)",
    "see [ref]\n\n[ref]: docs/agent-letter.md",
    '<a href="INSTALL.md">install</a>',
    '<img src="site/logo.png">',
])
def test_the_relative_link_finder_hits(planted):
    # A zero is a receipt only when the same finder is shown to hit.
    assert _relative_links(planted + "\n")


@pytest.mark.parametrize("fine", [
    "[install](#installation)",
    "[clones]: #install-the-plugins-from-your-clones",
    "[pypi](https://pypi.org/project/sessionkit/)",
    "[mail](mailto:someone@example.com)",
    "[mail](https://github.com/sessionkit/sessionmail/blob/HEAD/README.md)",
])
def test_the_relative_link_finder_passes_absolute_and_anchor_links(fine):
    assert _relative_links(fine) == []


# Every github.com URL in the README that names the kit or a sibling points at
# github.com/sessionkit/<name>, as pyproject's Homepage and Repository do.
# Clone and plain repo URLs count. Repos outside the kit (VoiceMode) are left
# as they are.
FAMILY = ("sessionkit", "sessionmail", "sessiontools", "sessionphone",
          "sessionview", "sessionvoice")
GITHUB_REPO = re.compile(r"github\.com[/:]([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)")


def _family_urls_off_the_org(text: str) -> list[str]:
    return [m.group(0) for m in GITHUB_REPO.finditer(text)
            if m.group(2).lower().removesuffix(".git") in FAMILY
            and m.group(1) != "sessionkit"]


def test_every_family_github_url_is_on_the_sessionkit_org():
    assert re.findall(r"github\.com/sessionkit/(\w+)", README), "the README names the org"
    assert _family_urls_off_the_org(README) == []


@pytest.mark.parametrize("planted", [
    "git clone https://github.com/someone/sessionkit",
    "[mail](https://github.com/someone/sessionmail/blob/master/README.md)",
    "git clone git@github.com:someone/sessionvoice.git",
])
def test_the_family_url_guard_hits(planted):
    assert _family_urls_off_the_org(planted)


@pytest.mark.parametrize("outside", [
    "https://github.com/someone/voicemode",
    "https://github.com/someone/sessionkit-extras",
])
def test_the_family_url_guard_leaves_repos_outside_the_kit(outside):
    assert _family_urls_off_the_org(outside) == []


# SK-153: a stranger's Claude hears its Delta messages by ONE launch,
# `session start claude`. INSTALL section 4 (the first check and the first
# agent's step 3) names it, with the launch sentence `sessionkit setup`
# prints, read from setup's own constant so the two cannot drift, and the
# cost: two windows started as `claude` share one box, and a second
# assistant takes another name at setup. Section 5's "Make the boxes" names
# the agent's box. Section 2's quoted refusal is setup's real output. The
# site promises no call it has not walked.
LAUNCH = kit_setup.launch_sentence(kit_setup.DEFAULT_AGENT)
SITE = (ROOT / "site" / "index.html").read_text(encoding="utf-8")


def _flat(text: str) -> str:
    return " ".join(text.split())


def test_the_launch_sentence_is_setups_and_names_session_start_claude():
    assert LAUNCH == "To hear Delta messages, start Claude with: session start claude"


def test_section_4_names_the_one_launch_and_its_sentence():
    checks = _install_section(4)
    first = checks[:checks.index(FIRST_AGENT_HEADING)]
    assert "- Start Claude with `session start claude` in the directory" in first
    assert LAUNCH in first, "the first check quotes setup's launch sentence verbatim"
    assert "Start `claude` in the directory" not in checks
    step3 = _flat(_first_agent())
    assert "3. **Start your first agent** inside it: `session start claude`." in step3
    assert LAUNCH in step3


def test_section_4_names_the_shared_box_cost_and_the_way_out():
    first = _flat(_install_section(4))
    assert "**two windows started as `claude` share one box**" in first
    assert "`sessionkit setup --agent NAME`, then `session start NAME`" in first
    # `claude` is Claude Code's built-in agent: the file's body promises nothing.
    assert "`claude` is Claude Code's own built-in agent" in first
    assert "its text does nothing" in first


def test_section_4_puts_dry_run_before_the_agent_name():
    step3 = _flat(_first_agent())
    assert "`session start --dry-run claude`" in step3
    assert "Launcher flags go before the name" in step3
    # The wrong order is named only as the refusal it is.
    assert step3.count("`session start claude --dry-run`") == 2
    assert "refuses, names the right order and exits 2" in step3


def test_section_5_make_the_boxes_names_the_agents_box():
    mail = _flat(_mail_section())
    assert "and your assistant's box, `claude` (or the name you gave `--agent`)" in mail
    assert "Your agent's own box is made when its pager first listens" not in mail


def test_section_2_quotes_setups_real_refusal_and_its_agent_lines():
    two = INSTALL_DOC[INSTALL_DOC.index("## 2. Install the kit"):INSTALL_DOC.index("### Operator and administrators")]
    [block] = re.findall(r"^```text\n(.*?)^```", two, re.MULTILINE | re.DOTALL)
    lines = block.splitlines()
    # SK-88 (0.2.1): the 0.1.0 refusal is gone; the block is 0.2.0's exit 4
    # on a fresh Mac, and SK-153's three agent lines end it.
    assert lines[0] == (
        "message setup: done what it can; 1 step(s) left for you: notmuch-hook (BLOCKED)"
    )
    assert lines[-3:] == [
        "Wrote /Users/<you>/.session/agents/claude.md: the agent 'claude', not keyed.",
        "session start --list-agents: lists 'claude'.",
        LAUNCH,
    ]
    flat = _flat(two)
    assert "the first four lines, exit 4. The last three are this release's assistant step" in flat
    assert "those seven lines" not in flat and "Mail not set up" not in two
    # The ONE line section 2 gains: what setup now writes.
    assert ("**Then your assistant:** it writes `~/.session/agents/claude.md`, the agent "
            "`session start claude` starts (section 4)") in flat


def test_docs_sessionkit_names_the_agent_file_and_the_launch():
    doc = _flat((ROOT / "docs" / "sessionkit.md").read_text(encoding="utf-8"))
    assert "`~/.session/agents/claude.md`" in doc
    assert f"`{LAUNCH}`" in doc


def test_the_site_promises_no_call_it_has_not_walked():
    for promise in ("pick up when you ring", "ring your Claude Code session"):
        assert promise not in SITE, promise
    flat = _flat(SITE)
    assert "The phone line installs, but no Delta message or call has yet been walked to a session." in flat
    # The site links nothing outside its folder and never names the install doc
    # (tests/test_site.py): it points to the README's Installation, whose calls
    # line links sessionphone's page.
    assert 'whether it signs follows the mail carrier (<a href="../README.md#installation">the README</a>)' in flat
    assert "never a bare <code>claude</code>" in flat
    assert "no Delta message or call has yet been walked to a session" in SITE
    assert "<code>session start claude</code>" in SITE
