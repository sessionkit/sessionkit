"""`sessionkit setup`: make this host's mail ready, write the operator, then
define the assistant (`run_agent`: the file `session start NAME` resolves, and
the box it hears, so a seat started that way hears mail to NAME).

Mail first. sessionmail's mail setup verb (argv in `MAIL_SETUP_ARGV`) makes
the mail root and the first boxes, the operator's box among them, and the
operator below is written only for a box that exists. The kit calls the verb
by its argv and reads its exit: 0 every step done, 4 steps are left for you,
1 a step failed, 2 refused. A sessionmail without the verb (0.1.0) gets the
exact step printed instead, and the run goes on to the operator.

The operator lives in the `session` tool's settings cascade (sessiontools'
`session operator` reads it). This step writes ONE drop-in,
`~/.sessionkit/tools/settings/session.d/10-operator.json`:

    {"_about": "...", "operator": {"mailbox": "<box>"}}     or
    {"_about": "...", "operator": {"address": "<address>"}}

Rules:

- The operator is the human at this keyboard: the OS account name (never
  `$USER`), or the box or address they name with `--mailbox` / `--address`.
  No name is ever a default here.
- A mailbox is written only if sessionmail says it EXISTS (`message box
  path NAME` exits 0). Otherwise nothing is written: refuse, exit 1, and say
  how to name yourself.
- `privileged` is never written. It defaults to the operator alone.
- An operator file left at the 0.1.0 place (`LEGACY_OPERATOR_FILE`), with
  none at the new place, stops the run: write nothing, print one line naming
  both files, exit 1. That file is only checked for existence: never opened,
  never copied, never a fallback.
- An operator already configured is never overwritten: `session operator`
  reporting one, or any host-layer settings file holding a top-level
  `operator` key, means write nothing. A host-layer file we cannot read
  means write nothing either.
- No environment variable decides what is written. `AGENT_OPERATOR_ADDR` is
  removed from `session operator`'s environment, and "configured" is read
  only from the fields settings alone fill (`mailbox`, `privileged`).
- The write is exclusive and atomic: a temp file whose name does NOT end in
  `.json` (the cascade reads every `*.json`, and one bad file there erases
  the operator for every reader), hard-linked into place, then removed.
"""

from __future__ import annotations

import json
import os
import pwd
import shutil
import subprocess
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path

# Every settings path the kit reads or writes is built by `settings_folder`
# from these names, under $HOME: `~/.sessionkit/<package>/settings/`. No
# variable or config file moves them.
SETTINGS_HOME = ".sessionkit"
SETTINGS_DIR = "settings"
# The package whose settings folder holds the `session` command's files.
SETTINGS_PACKAGE = "tools"
# The settings cascade's host layer for the `session` command (sessiontools
# `settings.sources`: `<tool>.json`, then `<tool>.d/*.json` in name order).
SETTINGS_TOOL = "session"
DROP_IN_DIR = f"{SETTINGS_TOOL}.d"
DROP_IN_NAME = "10-operator.json"
OPERATOR_KEY = "operator"
MAILBOX_KEY = "mailbox"
ADDRESS_KEY = "address"
PRIVILEGED_KEY = "privileged"
# Stranded-file detection ONLY: where sessionkit 0.1.0 wrote the operator.
# `setup` checks that this file EXISTS (a stat) and refuses while the new one
# is absent. It never opens, copies, moves or writes it, and never falls back
# to it: no value is ever read from this path.
LEGACY_OPERATOR_FILE = "~/.settings/session/session.d/10-operator.json"
ABOUT = (
    "written by `sessionkit setup`: the operator. Edit it to change it. See INSTALL.md."
)

# Sets the ask address in `session operator`, never privilege (sessiontools). It
# is removed from the child's environment so it cannot read as "configured".
ASK_ADDRESS_ENV = "AGENT_OPERATOR_ADDR"
SUBPROCESS_TIMEOUT = 10.0

# Domains reserved for examples (RFC 2606) and the docs' own placeholder: an
# address there is a pasted example, not the human, so it is refused.
PLACEHOLDER_DOMAINS = ("example", "example.com", "example.net", "example.org")
PLACEHOLDER_HOSTS = ("your-host",)

EXIT_OK = 0
EXIT_REFUSED = 1
# Done what it could; steps are left for you (the mail step: the verb said 4,
# or this sessionmail has no verb). The operator's own outcome is 0 or 1.
EXIT_STEPS_LEFT = 4

HINT = (
    "Name yourself: sessionkit setup --address YOUR-ADDRESS, or "
    "sessionkit setup --mailbox NAME (a box `message box path NAME` finds)."
)


@dataclass
class Outcome:
    """What a run did: its exit code and the lines it prints."""

    code: int
    lines: list[str] = field(default_factory=list)


class ShapeError(ValueError):
    """A flag value that can never be an operator (a usage error)."""


# --- the shapes we accept -----------------------------------------------------


def check_mailbox_shape(name: str) -> str:
    """NAME is ONE plain box name: the shape sessiontools derives an address from
    (no separator, no `@`, not `.`/`..`), with no whitespace and no leading
    `-` (it would read as a flag to `message`)."""
    if (
        not name
        or name in (".", "..")
        or "/" in name
        or "\\" in name
        or "@" in name
        or name.startswith("-")
        or any(ch.isspace() or not ch.isprintable() for ch in name)
    ):
        raise ShapeError(
            f"{name!r} is not a mail box name: one plain name, "
            "no '/', no '@', no spaces"
        )
    return name


def check_agent_shape(name: str) -> str:
    """NAME names the agent's mail box, so it is a mail box name. It names
    its file too (`<agents folder>/NAME.md`), so it may not start with `.`:
    `session start --list-agents` hides a dot-file, and a picker never offers it."""
    try:
        check_mailbox_shape(name)
    except ShapeError:
        raise ShapeError(
            f"{name!r} is not an agent name: one plain name, no '/', no '@', no spaces"
        ) from None
    if name.startswith("."):
        raise ShapeError(f"{name!r} is not an agent name: it may not start with '.'")
    return name


def check_address_shape(address: str) -> str:
    """ADDRESS is `local@domain`: exactly one `@`, both sides non-empty, no
    whitespace, and not an example domain (a pasted placeholder)."""
    local, at, domain = address.partition("@")
    if (
        not at
        or not local
        or not domain
        or "@" in domain
        or any(ch.isspace() or not ch.isprintable() for ch in address)
    ):
        raise ShapeError(f"{address!r} is not an address: name@host, one '@'")
    host = domain.lower().rstrip(".")
    if (
        host in PLACEHOLDER_DOMAINS
        or host.endswith(".example")
        or host in PLACEHOLDER_HOSTS
    ):
        raise ShapeError(f"{address!r} is an example address; give your own address")
    return address


# --- the two reads: `session operator` and the host layer ----------------------


def _child_env(environ: Mapping[str, str]) -> dict[str, str]:
    """ENVIRON without the ask-address override (never a privilege source)."""
    return {k: v for k, v in environ.items() if k != ASK_ADDRESS_ENV}


def _find(program: str, environ: Mapping[str, str]) -> str | None:
    """PROGRAM's path on ENVIRON's PATH, or None."""
    return shutil.which(program, path=environ.get("PATH", os.defpath))


def _run(argv: Sequence[str], environ: Mapping[str, str], timeout: float | None = None):
    """Run ARGV, its program found on ENVIRON's PATH. None if the program is
    absent, times out, or cannot start; else the CompletedProcess. TIMEOUT
    defaults to SUBPROCESS_TIMEOUT, read at call time."""
    program = _find(argv[0], environ)
    if program is None:
        return None
    try:
        return subprocess.run(
            [program, *argv[1:]],
            env=_child_env(environ),
            capture_output=True,
            text=True,
            timeout=SUBPROCESS_TIMEOUT if timeout is None else timeout,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None


def read_session_operator(environ: Mapping[str, str]) -> dict | None:
    """`session operator`'s one line of JSON, or None when it does not
    answer (absent, non-zero, a timeout, not a JSON object): the reader's
    fallback, "nothing configured"."""
    done = _run(["session", "operator"], environ)
    if done is None or done.returncode != 0:
        return None
    try:
        data = json.loads(done.stdout.strip().splitlines()[-1])
    except (json.JSONDecodeError, IndexError):
        return None
    return data if isinstance(data, dict) else None


def configured(answer: Mapping | None) -> bool:
    """An operator is configured: `mailbox` set, or `privileged` non-empty.
    Never `operator` alone: that field is the ask address, and the
    environment can fill it (sessiontools' operator rule 3)."""
    if not answer:
        return False
    mailbox = answer.get(MAILBOX_KEY)
    privileged = answer.get(PRIVILEGED_KEY)
    return (isinstance(mailbox, str) and bool(mailbox.strip())) or (
        isinstance(privileged, list) and bool(privileged)
    )


def host_layer_files(settings_dir: Path) -> list[Path]:
    """`session.json`, then `session.d/*.json` in name order: the files
    sessiontools reads for the host layer, the same selection."""
    out: list[Path] = []
    one = settings_dir / f"{SETTINGS_TOOL}.json"
    if one.is_file():
        out.append(one)
    drop_ins = settings_dir / DROP_IN_DIR
    if drop_ins.is_dir():
        out.extend(
            sorted(p for p in drop_ins.iterdir() if p.is_file() and p.suffix == ".json")
        )
    return out


def scan_host_layer(settings_dir: Path) -> Outcome | None:
    """None if no host-layer file holds `operator` and all read cleanly.
    Otherwise the Outcome that stops the run. This only asks "is there an
    `operator` key?"; it never decides who is privileged."""
    holders: list[Path] = []
    for path in host_layer_files(settings_dir):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError) as e:
            return _cannot_read(path, f"cannot read it ({e.__class__.__name__})")
        except json.JSONDecodeError as e:
            return _cannot_read(path, f"not JSON ({e.msg}, line {e.lineno})")
        if not isinstance(data, dict):
            return _cannot_read(path, "not a JSON object")
        if OPERATOR_KEY in data:
            holders.append(path)
    if holders:
        return Outcome(
            EXIT_OK,
            [f"An operator is already set in {holders[0]}; nothing written."],
        )
    return None


def _cannot_read(path: Path, why: str) -> Outcome:
    return Outcome(
        EXIT_REFUSED,
        [
            f"Cannot use {path}: {why}. Nothing written.",
            "Fix or remove that file, then run sessionkit setup again.",
        ],
    )


# --- the box ------------------------------------------------------------------


def account_name() -> str:
    """The OS account running this, from the password database: not $USER.

    Case-folded, as sessionmail's mail setup folds it when it makes the
    account's box: the box this names is the box the verb made."""
    return pwd.getpwuid(os.getuid()).pw_name.casefold()


def box_exists(name: str, environ: Mapping[str, str]) -> tuple[bool, str]:
    """sessionmail's own answer: `message box path NAME` exits 0 when the
    box exists. Anything else (exit 2, absent, a timeout) is "cannot
    establish it", with the reason."""
    done = _run(["message", "box", "path", name], environ)
    if done is None:
        return (
            False,
            "could not ask sessionmail (`message` not found or did not answer)",
        )
    if done.returncode == 0:
        return True, ""
    return False, f"sessionmail has no box named {name!r}"


# --- the write ----------------------------------------------------------------


def drop_in_path(settings_dir: Path) -> Path:
    return settings_dir / DROP_IN_DIR / DROP_IN_NAME


def drop_in_text(block: Mapping[str, str]) -> str:
    return json.dumps({"_about": ABOUT, OPERATOR_KEY: dict(block)}, indent=2) + "\n"


def write_exclusive(target: Path, text: str) -> str | None:
    """Create TARGET holding TEXT, only if it does not exist. None on
    success, else why not. Never a partial target and never a stray
    `*.json`: the temp's name ends in `.tmp-<pid>`, and it is removed. A
    folder that cannot be made (a file in the way, no permission) is a
    reason too, never a traceback: the caller's other halves have run, and
    their lines must still print."""
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        return f"could not make {target.parent} ({e.strerror or e.__class__.__name__})"
    temp = target.with_name(f".{target.name}.tmp-{os.getpid()}")
    try:
        # A temp by this pid's name is a dead run's leftover (no live process
        # shares the pid): clear it, so FileExistsError below means the TARGET.
        temp.unlink(missing_ok=True)
        with open(temp, "x", encoding="utf-8") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.link(temp, target)
    except FileExistsError:
        return f"{target} appeared while this ran; left it alone"
    except OSError as e:
        return f"could not write {target} ({e.strerror or e.__class__.__name__})"
    finally:
        try:
            temp.unlink()
        except FileNotFoundError:
            pass
    return None


# --- mail: sessionmail's setup verb, called by its argv -----------------------

# sessionmail's mail setup verb, `message setup` (listed on `message --help`).
# Every call and every printed step is built from this ONE constant.
MAIL_SETUP_ARGV: tuple[str, ...] = ("message", "setup")
# The verb rebuilds the maps on a postfix host; give it longer than a read.
MAIL_SETUP_TIMEOUT = 120.0

# The verb's exits (sessionmail docs/message-setup.md).
MAIL_DONE = 0
MAIL_FAILED = 1
MAIL_REFUSED = 2
MAIL_LEFT = 4

MAIL_DOC = 'INSTALL.md, "Mail between agents"'


def mail_setup_boxes(
    mailbox: str | None, address: str | None, agent: str | None
) -> tuple[str, ...]:
    """The boxes the installer asks the verb for, as `--box NAME` each.

    `--mailbox NAME` passes NAME, so a named box on a fresh install is made
    before the operator check looks for it. Then the agent's box (`--agent`,
    default `claude`): a seat started with `session start NAME` hears the
    box NAME, so the box must exist for mail to it to land. The verb's own
    floor (the operator's box, `operator.mailbox`, else the installing
    account's name) is made besides. A session's own box is made by its
    pager, never here. The verb is idempotent: a box that exists stays.
    """
    del address  # an address needs no box
    boxes = [name for name in (mailbox, agent) if name is not None]
    return tuple(dict.fromkeys(boxes))


def mail_setup_argv(boxes: Sequence[str], dry_run: bool) -> list[str]:
    """The verb's argv: MAIL_SETUP_ARGV, `--dry-run`, then `--box NAME` each."""
    argv = list(MAIL_SETUP_ARGV)
    if dry_run:
        argv.append("--dry-run")
    for box in boxes:
        argv += ["--box", box]
    return argv


def _verb() -> str:
    return " ".join(MAIL_SETUP_ARGV)


def _no_verb(why: str, boxes: Sequence[str] = ()) -> Outcome:
    """This sessionmail cannot run the verb: print the exact step instead,
    with the `--box NAME` setup would have passed (the agent's among them),
    so running it later makes the same boxes a run of the verb would."""
    step = " ".join(mail_setup_argv(boxes, dry_run=False))
    return Outcome(
        EXIT_STEPS_LEFT,
        [
            f"Mail not set up: {why}.",
            (
                f"A newer sessionmail has it. Until you have that, set mail up by "
                f"hand ({MAIL_DOC}); once you do, run: {step}"
            ),
        ],
    )


def _output_lines(done: subprocess.CompletedProcess) -> list[str]:
    return (done.stdout or "").splitlines() + (done.stderr or "").splitlines()


def run_mail_setup(
    *,
    boxes: Sequence[str] = (),
    dry_run: bool = False,
    environ: Mapping[str, str],
) -> Outcome:
    """Run sessionmail's mail setup verb and read its exit.

    First `<verb> --help`: a sessionmail without the verb (0.1.0 answers
    "No such command", exit 2) gets the exact step printed, never a guess.
    Then the verb itself, its output passed through as it is:

    - 0, every step done: EXIT_OK.
    - 4, steps left for you (the verb names them): EXIT_STEPS_LEFT. A dry
      run answers 4 while any step is still to do, and 0 only once every
      step is done.
    - 1, a step failed, or 2, refused before anything was applied, or any
      other answer: EXIT_REFUSED, with what to do.
    """
    program = MAIL_SETUP_ARGV[0]
    if _find(program, environ) is None:
        return _no_verb(f"`{program}` is not on the PATH", boxes)
    probe = _run([*MAIL_SETUP_ARGV, "--help"], environ)
    if probe is None:
        return _no_verb(f"`{_verb()} --help` did not answer", boxes)
    if probe.returncode != 0:
        return _no_verb(
            f"this sessionmail has no `{_verb()}` "
            f"(`{_verb()} --help` exited {probe.returncode})",
            boxes,
        )

    argv = mail_setup_argv(boxes, dry_run)
    done = _run(argv, environ, timeout=MAIL_SETUP_TIMEOUT)
    if done is None:
        return Outcome(
            EXIT_REFUSED,
            [
                (
                    f"Mail setup did not finish: `{' '.join(argv)}` did not answer "
                    f"within {MAIL_SETUP_TIMEOUT:g}s."
                ),
                f"Run it yourself to see where it stops: {' '.join(argv)}",
            ],
        )
    lines = _output_lines(done)
    code = done.returncode
    if code == MAIL_DONE:
        return Outcome(EXIT_OK, lines)
    if code == MAIL_LEFT:
        # A dry run applies nothing, so the verb answers 4 while any step is
        # still to do, a fresh host's included (measured); it leaves the
        # steps for the real run, not for you.
        after = (
            "Dry run: mail setup has steps still to do (above). Without "
            "--dry-run it does what it can and names the rest."
            if dry_run
            else "Mail setup left steps for you (above); re-run sessionkit setup after."
        )
        return Outcome(EXIT_STEPS_LEFT, lines + [after])
    if code == MAIL_FAILED:
        why = "a mail setup step failed; what ran before it stays"
    elif code == MAIL_REFUSED:
        why = "mail setup refused; nothing was applied"
    else:
        why = f"mail setup exited {code}, which it never does"
    return Outcome(
        EXIT_REFUSED,
        lines
        + [
            f"{why[0].upper()}{why[1:]}. Fix what it names, then run sessionkit setup again."
        ],
    )


# --- the agent: the file `session start NAME` resolves -------------------------

# The assistant setup defines when no `--agent` is given.
DEFAULT_AGENT = "claude"

# Where `session start NAME` looks for agents: sessiontools'
# `start/agents.py:agents_root`, the same rule, mirrored here so the kit does
# not import sessiontools' internals. `$AGENTS_DIR`, else
# `~/.session/agent/config` if that is a directory, else `~/.session/agents`.
# tests/test_setup.py holds this rule to the installed sessiontools'.
AGENTS_DIR_ENV = "AGENTS_DIR"
SESSION_HOME = ".session"
AGENT_CONFIG_DIR = ("agent", "config")
AGENTS_DIR_NAME = "agents"

# The reader: every agent `session start` would accept, one name a line.
LIST_AGENTS_ARGV: tuple[str, ...] = ("session", "start", "--list-agents")

# The one launch step, in sessionphone's final words: the same line its Delta
# bot prints. Spelled once: change it here only.
LAUNCH_SENTENCE = "To hear Delta messages, start Claude with: session start {agent}"

# The agent file. No `start:` keys: the seat is NOT keyed. No front matter at
# all: Claude Code (2.1.304, measured) names an agent by its file, so `name:`
# and `description:` are not needed. For any NAME but `claude` this text is
# the agent's prompt; for `claude`, Claude Code's own built-in agent of that
# name answers, and the file only has to exist for `session start` to find it.
AGENT_TEXT = """\
You are {agent}, a Claude Code assistant.

Written by `sessionkit setup`. `session start {agent}` starts Claude as
{agent}, so the session hears mail to the box {agent}. Edit this file as you
like: setup never writes over it.
"""


def agents_root(home: Path, environ: Mapping[str, str]) -> Path:
    """The agents folder `session start` reads, by sessiontools' rule."""
    named = environ.get(AGENTS_DIR_ENV)
    if named:
        return Path(os.path.expanduser(named))
    config = home / SESSION_HOME / Path(*AGENT_CONFIG_DIR)
    if config.is_dir():
        return config
    return home / SESSION_HOME / AGENTS_DIR_NAME


def agent_file(home: Path, environ: Mapping[str, str], agent: str) -> Path:
    """The file setup writes for AGENT: the flat layout, `<root>/NAME.md`."""
    return agents_root(home, environ) / f"{agent}.md"


def agent_text(agent: str) -> str:
    return AGENT_TEXT.format(agent=agent)


def launch_sentence(agent: str) -> str:
    return LAUNCH_SENTENCE.format(agent=agent)


def read_listed_agents(environ: Mapping[str, str]) -> list[str] | None:
    """`session start --list-agents`, one name a line, or None when it does
    not answer (absent, non-zero, a timeout): "not verified", never "absent"."""
    done = _run(LIST_AGENTS_ARGV, environ)
    if done is None or done.returncode != 0:
        return None
    return [line.strip() for line in done.stdout.splitlines() if line.strip()]


def run_agent(
    *,
    agent: str,
    dry_run: bool = False,
    home: Path | None = None,
    environ: Mapping[str, str] | None = None,
) -> Outcome:
    """Write AGENT's file where `session start` looks, once; then verify.

    Never clobbers: either layout `session start` reads (`<root>/NAME/NAME.md`,
    which wins, or `<root>/NAME.md`) already there means write nothing. A
    folder `<root>/NAME/` without its NAME.md, or a flat path that is not a
    file, is refused: `session start` could not start NAME from it, and
    writing beside it would not change that. AGENT is already shape-checked.
    """
    environ = os.environ if environ is None else environ
    home = Path.home() if home is None else home
    root = agents_root(home, environ)
    folder = root / agent
    flat = agent_file(home, environ, agent)
    if folder.is_dir():
        inside = folder / f"{agent}.md"
        if inside.is_file():
            return Outcome(
                EXIT_OK, [f"Agent {agent!r} is already in {inside}; left as it is."]
            )
        return Outcome(
            EXIT_REFUSED,
            [
                (
                    f"No agent file written: {folder} exists without {agent}.md "
                    f"in it, so session start cannot start {agent!r}."
                ),
                f"Put {agent}.md in that folder, or remove it, then run sessionkit setup again.",
            ],
        )
    if flat.is_file():
        return Outcome(
            EXIT_OK, [f"Agent {agent!r} is already in {flat}; left as it is."]
        )
    if os.path.lexists(flat):
        return Outcome(
            EXIT_REFUSED,
            [
                f"No agent file written: {flat} exists and is not a file session start can read.",
                "Remove it, then run sessionkit setup again.",
            ],
        )
    text = agent_text(agent)
    if dry_run:
        return Outcome(EXIT_OK, [f"Would write {flat}:", text.rstrip("\n")])

    failed = write_exclusive(flat, text)
    if failed is not None:
        return Outcome(EXIT_REFUSED, [f"No agent file written: {failed}."])
    lines = [f"Wrote {flat}: the agent {agent!r}, not keyed."]

    listed = read_listed_agents(environ)
    verb = " ".join(LIST_AGENTS_ARGV)
    if listed is None:
        lines.append(f"Written; not verified: `{verb}` did not answer.")
        return Outcome(EXIT_OK, lines)
    if agent not in listed:
        lines.append(
            f"WARNING: `{verb}` does not list {agent!r}: the `session` on your "
            "PATH looks in another agents folder ($AGENTS_DIR, or another sessiontools)."
        )
        return Outcome(EXIT_REFUSED, lines)
    lines.append(f"{verb}: lists {agent!r}.")
    return Outcome(EXIT_OK, lines)


# --- the run ------------------------------------------------------------------


def settings_folder(home: Path, package: str) -> Path:
    """The settings folder of PACKAGE under HOME. The one place the layout
    of the settings tree is written down."""
    return home / SETTINGS_HOME / package / SETTINGS_DIR


def settings_dir_for(home: Path) -> Path:
    return settings_folder(home, SETTINGS_PACKAGE)


def operator_drop_in(home: Path) -> Path:
    """The drop-in `setup` writes, under HOME."""
    return drop_in_path(settings_dir_for(home))


def legacy_operator_file(home: Path) -> Path:
    """LEGACY_OPERATOR_FILE under HOME. For the stranded check only."""
    return home / LEGACY_OPERATOR_FILE.removeprefix("~/")


def stranded(home: Path, settings_dir: Path) -> Outcome | None:
    """The refusal when an operator file is left at the 0.1.0 place and the new
    side has none; else None. The old file is only stat'ed, never read.

    The new side "has one" when the drop-in exists, or the host layer holds an
    `operator` key. A host-layer file that cannot be read also yields None:
    the run then stops on it in step 2, naming that file."""
    old = legacy_operator_file(home)
    if not os.path.lexists(old):  # a stat, never an open
        return None
    new = drop_in_path(settings_dir)
    if new.exists() or new.is_symlink():
        return None
    if scan_host_layer(settings_dir) is not None:
        return None
    line = (
        f"No operator written: found {old}, where an earlier sessionkit "
        f"wrote it, and none at {new}. Move that file to {new}, or remove "
        "it, then run sessionkit setup again."
    )
    return Outcome(EXIT_REFUSED, [line])


def run_setup(
    *,
    mailbox: str | None = None,
    address: str | None = None,
    agent: str = DEFAULT_AGENT,
    dry_run: bool = False,
    home: Path | None = None,
    environ: Mapping[str, str] | None = None,
) -> Outcome:
    """The stranded check, then mail, the operator and the agent; all print.

    An operator file stranded at the 0.1.0 place, with none at the new one,
    stops the whole run before mail: nothing is made or written, one line.
    The verb would otherwise make the operator's box from settings that
    cannot see that file. Past it, all three always run. Mail goes first
    because the operator is written only for a box that exists, and the
    mail setup verb is what makes the operator's box and the agent's. The
    exit is the worst of the three: 1 if any refused or failed, else 4 if
    mail left steps for you, else 0. With the agent defined, the run ends on
    the one launch step (LAUNCH_SENTENCE). MAILBOX / ADDRESS / AGENT are
    already shape-checked by the caller.
    """
    environ = os.environ if environ is None else environ
    resolved = Path.home() if home is None else home
    stop = stranded(resolved, settings_dir_for(resolved))
    if stop is not None:
        return stop
    # No mail setting is written, here or by the verb: the file drop is
    # sessionmail's default carrier, and postfix is the user's opt-in.
    # `--write-maps` is never passed: writing postfix maps is opt-in too.
    mail = run_mail_setup(
        boxes=mail_setup_boxes(mailbox, address, agent),
        dry_run=dry_run,
        environ=environ,
    )
    operator = run_operator(
        mailbox=mailbox, address=address, dry_run=dry_run, home=home, environ=environ
    )
    defined = run_agent(agent=agent, dry_run=dry_run, home=resolved, environ=environ)
    codes = (mail.code, operator.code, defined.code)
    if EXIT_REFUSED in codes:
        code = EXIT_REFUSED
    elif EXIT_STEPS_LEFT in codes:
        code = EXIT_STEPS_LEFT
    else:
        code = EXIT_OK
    lines = mail.lines + operator.lines + defined.lines
    if dry_run:
        lines.append(
            f"Would ask `{_verb()}` for the agent's box {agent!r} (--box {agent})."
        )
    if defined.code == EXIT_OK:
        lines.append(launch_sentence(agent))
    return Outcome(code, lines)


def run_operator(
    *,
    mailbox: str | None = None,
    address: str | None = None,
    dry_run: bool = False,
    home: Path | None = None,
    environ: Mapping[str, str] | None = None,
) -> Outcome:
    """In order: stranded? already configured? host layer? the box? write;
    verify. MAILBOX / ADDRESS are already shape-checked by the caller."""
    environ = os.environ if environ is None else environ
    home = Path.home() if home is None else home
    settings_dir = settings_dir_for(home)

    # 0. An operator file stranded at the 0.1.0 place, none at the new one:
    # first, so no reader of the old place can answer "configured" for it.
    stop = stranded(home, settings_dir)
    if stop is not None:
        return stop

    # 1. `session operator`: an operator configured in settings.
    answer = read_session_operator(environ)
    if configured(answer):
        who = answer.get(MAILBOX_KEY) or answer.get(OPERATOR_KEY) or "privileged set"
        return Outcome(
            EXIT_OK,
            [f"An operator is already configured ({who}); nothing written."],
        )

    # 2. The host layer: any `operator` key, or a file we cannot read.
    stop = scan_host_layer(settings_dir)
    if stop is not None:
        return stop

    # 3. Establish who: an address as given, or a box sessionmail confirms.
    if address is not None:
        block = {ADDRESS_KEY: address}
    else:
        box = mailbox if mailbox is not None else account_name()
        try:
            check_mailbox_shape(box)
        except ShapeError as e:
            return Outcome(EXIT_REFUSED, [f"No operator written: {e}.", HINT])
        ok, why = box_exists(box, environ)
        if not ok:
            return Outcome(EXIT_REFUSED, [f"No operator written: {why}.", HINT])
        block = {MAILBOX_KEY: box}

    target = drop_in_path(settings_dir)
    if target.exists() or target.is_symlink():
        # Ours, emptied of its `operator` by hand (step 2 found no key): never
        # write past it, and refuse here so a dry run exits as a real run does.
        return Outcome(
            EXIT_REFUSED,
            [
                f"No operator written: {target} exists and holds no operator.",
                "Add the operator to it by hand, or remove it and rerun setup.",
            ],
        )
    text = drop_in_text(block)
    if dry_run:
        return Outcome(EXIT_OK, [f"Would write {target}:", text.rstrip("\n")])

    # 4. Write it, exclusively.
    failed = write_exclusive(target, text)
    if failed is not None:
        return Outcome(EXIT_REFUSED, [f"No operator written: {failed}."])
    lines = [f"Wrote {target}: the operator is {_describe(block)}."]

    # 5. Verify through the reader.
    after = read_session_operator(environ)
    if after is None:
        lines.append(
            "Written; not verified: `session operator` needs a newer sessiontools."
        )
        return Outcome(EXIT_OK, lines)
    lines.append(f"session operator: {json.dumps(after)}")
    if not holds(after, block):
        lines.append(
            "WARNING: `session operator` does not read what was written: another "
            "settings layer, a `_locked` key or a bad settings file overrides it."
        )
        return Outcome(EXIT_REFUSED, lines)
    return Outcome(EXIT_OK, lines)


def holds(answer: Mapping, block: Mapping[str, str]) -> bool:
    """ANSWER (from `session operator`) holds what BLOCK wrote."""
    privileged = answer.get(PRIVILEGED_KEY)
    privileged = privileged if isinstance(privileged, list) else []
    if MAILBOX_KEY in block:
        name = block[MAILBOX_KEY]
        return answer.get(MAILBOX_KEY) == name and name in privileged
    name = block[ADDRESS_KEY]
    return answer.get(OPERATOR_KEY) == name and name in privileged


def _describe(block: Mapping[str, str]) -> str:
    if MAILBOX_KEY in block:
        return f"mail box {block[MAILBOX_KEY]!r}"
    return f"address {block[ADDRESS_KEY]!r}"
