"""sessionkit - the front door. Help first: every verb is here before it works."""
from __future__ import annotations

import json
import sys
from importlib.metadata import PackageNotFoundError, version

import click

from sessionkit import doctor as kit_doctor
from sessionkit import launchd as kit_launchd
from sessionkit import services as kit_services
from sessionkit import setup as operator_setup

CTX = {"help_option_names": ["-h", "--help"]}

# The family packages the kit installs and re-exports, in pyproject order.
# tests/test_cli.py holds this list to pyproject's [project] dependencies.
FAMILY = ("sessionmail", "sessiontools", "sessionphone", "sessionview", "sessionvoice")
# The apps the kit depends on that are not family packages: each on its own
# version line, with no Claude plugin. `--version` lists them after the family.
# FAMILY stays the five: install.sh's KIT_PLUGINS is held to it.
APPS = ("settled",)
NOT_INSTALLED = "not installed"


def installed_version(dist: str) -> str:
    """The INSTALLED distribution's version, never a string kept in the source."""
    try:
        return version(dist)
    except PackageNotFoundError:
        return NOT_INSTALLED


def version_lines() -> list[str]:
    """The kit's line in the family's form (`pager, version X`), then one per
    child: the family, then the apps."""
    names = FAMILY + APPS
    width = max(len(name) for name in names)
    lines = [f"sessionkit, version {installed_version('sessionkit')}"]
    lines += [f"  {name:<{width}}  {installed_version(name)}" for name in names]
    return lines


def _print_version(ctx: click.Context, _param: click.Parameter, value: bool) -> None:
    if not value or ctx.resilient_parsing:
        return
    click.echo("\n".join(version_lines()))
    ctx.exit()


@click.group(context_settings=CTX, invoke_without_command=True)
@click.option(
    "--version",
    "-V",
    is_flag=True,
    expose_value=False,
    is_eager=True,
    callback=_print_version,
    help="Show the kit's version and that of each package it installs, then exit.",
)
@click.pass_context
def main(ctx: click.Context) -> None:
    """Session Kit gives your Claude Code sessions voice, mail, a phone line and a tmux sidebar, in one install."""
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


def _shape(check):
    """A click callback: CHECK the value's shape, a usage error if wrong."""

    def callback(_ctx: click.Context, _param: click.Parameter, value: str | None):
        if value is None:
            return None
        try:
            return check(value)
        except operator_setup.ShapeError as e:
            raise click.BadParameter(str(e)) from None

    return callback


@main.command(context_settings=CTX)
@click.option(
    "--mailbox",
    metavar="NAME",
    callback=_shape(operator_setup.check_mailbox_shape),
    help="Your mail box: a box `message box path NAME` finds. "
    "Default: your OS account name, if sessionmail has a box by that name.",
)
@click.option(
    "--address",
    metavar="ADDR",
    callback=_shape(operator_setup.check_address_shape),
    help="Your own full mail address (name@host), written as the operator "
    "instead of a mail box.",
)
@click.option(
    "--agent",
    metavar="NAME",
    default=None,
    callback=_shape(operator_setup.check_agent_shape),
    help="Your assistant's name: setup writes its agent file and makes its "
    "mail box, so `session start NAME` starts Claude as NAME, hearing mail to NAME, "
    'and adds NAME as the seat "hey NAME" wakes. '
    f"[default: {operator_setup.DEFAULT_AGENT}] "
    "The default seat's box, named by `session agent default`, is made too, "
    "whatever NAME is; with no --agent, the default seat is the one woken.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Run every check and print what would be written; write nothing.",
)
def setup(
    mailbox: str | None, address: str | None, agent: str | None, dry_run: bool
) -> None:
    """Set up mail on this Mac, write you as the operator, and define your assistant.

    Mail first: it runs sessionmail's mail setup (`message setup`), which
    makes the mail root and your box, and prints what it did and what is
    left. A sessionmail without it gets the step printed instead.

    Then the operator: it writes
    ~/.sessionkit/tools/settings/session.d/10-operator.json, once. It never
    overwrites an operator already set, never writes `privileged` (it
    defaults to the operator alone), and writes NOTHING when it cannot
    confirm who you are: then it says how to name yourself, with --address
    or --mailbox. It writes nothing, too, while the operator file an earlier
    release wrote is still in place and none is at the new path: it names
    both.

    Then your assistant (--agent, default claude): it writes NAME.md in the
    folder `session start` looks in for agents, the one `session path agent
    --config` names (on a fresh Mac ~/.sessionkit/tools/state/agent/config),
    not keyed. A sessiontools without that verb gets no agent file, and one
    line saying to run setup again once it has the verb. It
    asks `message setup` for the box NAME and for the default seat's box,
    the name `session agent default` prints, whatever NAME is. A file
    already there, in either layout, is left as it is. It ends with the one
    launch step: `session start NAME`.

    Before that step it adds the wake seat with `ears wake add`: NAME when
    --agent is given, else the default seat, so saying "hey" and its name
    wakes it. Without `ears` on the PATH, or when it refuses, it says one line
    with the step to run; that line never changes the exit. It never runs
    `ears services install`. Then it asks `ears backends`, read only. If
    the ears' voice-activity model is missing, it says one line naming
    `ears install`. It never runs `ears install`, and the line never
    changes the exit.

    Exit 0 all done, 1 refused or failed, 2 usage, 4 done what it could,
    mail steps left for you. See INSTALL.md, "Operator and administrators"
    and "Mail between agents", in https://github.com/sessionkit/sessionkit.
    """
    if mailbox is not None and address is not None:
        raise click.UsageError("give --mailbox or --address, not both")
    outcome = operator_setup.run_setup(
        mailbox=mailbox, address=address, agent=agent, dry_run=dry_run
    )
    for line in outcome.lines:
        click.echo(line, err=outcome.code != 0)
    raise SystemExit(outcome.code)


@main.command(context_settings=CTX)
@click.option(
    "--no-speech",
    is_flag=True,
    help="Leave the speech server and the ears out: their rows do not fail.",
)
def doctor(no_speech: bool) -> None:
    """Check this Mac for what the kit needs, and install nothing.

    One line per thing, found or missing, and under each missing one the
    command that adds it. The rows the installer checks come from the
    installer itself: this runs the install.sh the kit ships, with --check.
    Then four rows of its own: the mail hooks (needed), the Settings app,
    settled (needed), the phone bot (optional) and the session key
    (information only).

    It is read-only: it writes no file of its own and starts and stops
    nothing. The only network it reaches itself is the speech server on
    127.0.0.1:8890, which it probes, and its brew reads download nothing.
    The tools it asks keep their own files in your home, and may use their
    own network: in an empty home, brew, uv and claude make their caches,
    and claude, asked for its plugins, reaches Anthropic's API over HTTPS.
    INSTALL.md section 4, in
    https://github.com/sessionkit/sessionkit, names each file.

    On a Mac without the kit, or where this command will not start, the
    installer runs the same check:

    \b
        curl -fsSL https://sessionkit.ai/install.sh | bash -s -- --check

    From a clone of the kit, the same: bash install.sh --check

    Exit 0 nothing the kit needs is missing, 1 something is (each missing
    row says what to run), 2 usage, 3 this Mac cannot be checked (not macOS,
    or run as root).
    """
    raise SystemExit(kit_doctor.run(no_speech=no_speech, echo=click.echo))


# --- sessionkit service -------------------------------------------------------

# Exit codes, in the shape the kit's health check uses: 0 done, 1 a launchctl
# call failed, 2 usage or refused (an ambiguous name, an answer of no, --yes
# needed, a live call), 3 launchd cannot be reached from this shell.
SERVICE_FAILED, SERVICE_REFUSED, SERVICE_UNREACHABLE = 1, 2, 3


def _complete_names(_ctx: click.Context, _param: click.Parameter, incomplete: str):
    """TAB: the names `list` shows, the groups, and `all`. Writes nothing, and
    on any error offers nothing, never a traceback."""
    try:
        try:
            listed = kit_launchd.listed()
        except (kit_launchd.Unreachable, kit_launchd.Failed):
            listed = {}
        rows = kit_services.survey(listed=listed).rows
        return [w for w in kit_services.candidates(rows) if w.startswith(incomplete)]
    except Exception:  # noqa: BLE001 - completion must never print a traceback
        return []


def _unreachable(e: Exception) -> SystemExit:
    click.echo(
        f"sessionkit service: launchd's {kit_launchd.domain()} cannot be reached "
        f"from this shell: {e}",
        err=True,
    )
    return SystemExit(SERVICE_UNREACHABLE)


def _survey() -> kit_services.Survey:
    try:
        return kit_services.survey()
    except kit_launchd.Unreachable as e:
        raise _unreachable(e) from None
    except kit_launchd.Failed as e:
        click.echo(f"sessionkit service: launchctl list failed: {e}", err=True)
        raise SystemExit(SERVICE_FAILED) from None


def _resolve(words: tuple[str, ...], rows: list) -> list:
    try:
        return kit_services.resolve(words, rows)
    except kit_services.Unknown as e:
        click.echo(
            f"sessionkit service: no service or group named {e}; "
            "`sessionkit service list` shows them",
            err=True,
        )
    except kit_services.Ambiguous as e:
        click.echo(f"sessionkit service: {e}. Name one: <group>.<name>, or its label.", err=True)
    raise SystemExit(SERVICE_REFUSED)


def _interactive() -> bool:
    """Whether a y/N question can be asked: stdin is a terminal."""
    return sys.stdin.isatty()


def _print_list(survey: kit_services.Survey, as_json: bool) -> None:
    if as_json:
        click.echo(json.dumps(kit_services.as_json(survey.rows), indent=2))
    else:
        click.echo("\n".join(kit_services.render(survey)))


_LEGEND = "\n".join(f"  {line}" for line in kit_services.LEGEND)


@main.group(context_settings=CTX)
def service() -> None:
    """The kit's services: list them, see one, restart one or a group.

    A service is a file its package's install writes under
    ~/.sessionkit/<package>/services/; launchd says whether it runs. A word
    is a service's name (talk, bot.NAME), a group (voice, phone, mail,
    tools), <group>.<name>, a launchd label, or all.
    """


@service.command(
    name="list",
    context_settings=CTX,
    epilog="\b\nThe legend:\n" + _LEGEND,
)
@click.option("--json", "as_json", is_flag=True, help="One JSON object per service.")
def service_list(as_json: bool) -> None:
    """Every service on this Mac, by group, A to Z, and whether it runs.

    Read-only. Exit 0, 1 launchctl failed, 3 launchd cannot be reached from
    this shell.
    """
    _print_list(_survey(), as_json)


@service.command(name="status", context_settings=CTX)
@click.argument("words", nargs=-1, metavar="[NAME|GROUP|all]...", shell_complete=_complete_names)
@click.option("--json", "as_json", is_flag=True, help="One JSON object per service.")
def service_status(words: tuple[str, ...], as_json: bool) -> None:
    """The long form of a service, a group or all; bare, the same as list.

    The long form is one field per line: label, file, enabled, state, pid,
    last exit, port, plist, logs, and the owner's install command.
    Read-only. Exit 0, 1 launchctl failed, 2 no such service, 3 launchd
    cannot be reached from this shell.
    """
    survey = _survey()
    if not words:
        _print_list(survey, as_json)
        return
    rows = _resolve(words, survey.rows)
    if as_json:
        click.echo(json.dumps(kit_services.as_json(rows), indent=2))
        return
    code, blocks = 0, []
    for row in rows:
        printed = None
        if row.label and row.loaded:
            try:
                printed = kit_launchd.printed(row.label)
            except kit_launchd.Unreachable:
                code = SERVICE_UNREACHABLE
            except kit_launchd.Failed:
                pass
        blocks.append("\n".join(kit_services.long_form(row, printed)))
    click.echo("\n\n".join(blocks))
    if code:
        click.echo(
            f"launchd's {kit_launchd.domain()} cannot be reached from this shell: "
            "pid and last exit are launchctl list's.",
            err=True,
        )
    raise SystemExit(code)


def _why_not(row) -> str | None:
    """Why ROW cannot be restarted, or None when it can."""
    if row.state == kit_services.BAD:
        return f"bad file ({row.note}): {row.file}"
    if row.state == kit_services.DISABLED:
        return "disabled: its file says enabled: false, and a restart would start it"
    if not row.label:
        return "runs in the foreground; the kit never starts or restarts it"
    if not row.loaded:
        if row.installed:
            return (
                "not loaded, so there is nothing to restart. Load it with: "
                f"launchctl bootstrap {kit_launchd.domain()} {row.plist}"
            )
        install = row.data.get("install") if row.file else None
        return f"not installed: {install}" if install else "not installed"
    return None


@service.command(name="restart", context_settings=CTX)
@click.argument(
    "words", nargs=-1, required=True, metavar="NAME|GROUP|all...", shell_complete=_complete_names
)
@click.option("--yes", "-y", is_flag=True, help="Restart a group or all without asking.")
@click.option("--force", is_flag=True, help="Restart even while a phone call is live.")
def service_restart(words: tuple[str, ...], yes: bool, force: bool) -> None:
    """Restart a service, a group, or all: launchctl kickstart -k.

    It writes no file: launchd stops the job and starts it again from its
    owner's plist. One named service restarts at once. A group, all, or more
    than one name lists every job, in the order it will act, and asks y/N
    first; with no terminal it needs --yes.

    A restart can drop a live phone call. While a call is live, it refuses
    any job whose file says hazard: call, and any job with no file yet,
    unless --force.

    A job its file says is disabled, and is not running, is not started: one
    named is refused, and in a group it is named as skipped.

    Exit 0 restarted, 1 launchctl failed, 2 refused (no such service, not
    loaded, disabled, a live call, an answer of no, --yes needed), 3 launchd cannot be
    reached from this shell.
    """
    survey = _survey()
    targets = _resolve(words, survey.rows)
    names = {r.package for r in survey.rows}
    many = len(targets) > 1 or any(w == "all" or w in names for w in words)
    acting, skipped = [], []
    for row in targets:
        why = _why_not(row)
        (skipped if why else acting).append((row, why))
    if not many and skipped:
        row, why = skipped[0]
        click.echo(f"sessionkit service: {row.fullname}: {why}", err=True)
        raise SystemExit(SERVICE_REFUSED)
    acting = sorted((r for r, _ in acting), key=lambda r: (r.order, r.package, r.name))
    if not acting:
        click.echo("sessionkit service: nothing to restart:", err=True)
        for row, why in skipped:
            click.echo(f"  {row.fullname}: {why}", err=True)
        raise SystemExit(SERVICE_REFUSED)
    if not force and any(r.hazard for r in acting):
        loaded = [r.label for r in survey.rows if r.loaded and r.label]
        calls = kit_services.live_calls(loaded=loaded)
        if calls:
            guarded = ", ".join(r.fullname for r in acting if r.hazard)
            click.echo("sessionkit service: a phone call is live; nothing was restarted.", err=True)
            for line in calls:
                click.echo(f"  {line}", err=True)
            click.echo(f"A restart of {guarded} can drop it. --force restarts anyway.", err=True)
            raise SystemExit(SERVICE_REFUSED)
    if many:
        jobs = "1 job" if len(acting) == 1 else f"{len(acting)} jobs"
        click.echo(f"Restart {jobs}, in this order:")
        for row in acting:
            click.echo(f"  {row.fullname}  ({row.label})")
        for row, why in skipped:
            click.echo(f"  skipped {row.fullname}: {why}")
        if not yes:
            if not _interactive():
                click.echo(
                    "sessionkit service: no terminal to ask; give --yes to restart them.",
                    err=True,
                )
                raise SystemExit(SERVICE_REFUSED)
            if not click.confirm("Restart them?", default=False):
                click.echo("Nothing restarted.")
                raise SystemExit(SERVICE_REFUSED)
    failed = False
    for row in acting:
        try:
            ran = kit_launchd.kickstart(row.label)
        except kit_launchd.Unreachable as e:
            click.echo(f"sessionkit service: {row.fullname}: {e}", err=True)
            click.echo("This shell cannot reach launchd. From Terminal.app, run:", err=True)
            click.echo(f"  launchctl kickstart -k gui/$(id -u)/{row.label}", err=True)
            raise SystemExit(SERVICE_UNREACHABLE) from None
        except kit_launchd.Failed as e:
            ran = kit_launchd.Ran(1, str(e))
        if ran.rc == 0:
            click.echo(f"restarted {row.fullname}")
        else:
            failed = True
            click.echo(f"sessionkit service: {row.fullname}: {ran.words}", err=True)
    raise SystemExit(SERVICE_FAILED if failed else 0)


@main.command(context_settings=CTX)
@click.argument("shell", type=click.Choice(["zsh", "bash", "fish"]))
def completion(shell: str) -> None:
    """Print the shell's TAB completion script for sessionkit.

    \b
    zsh, in ~/.zshrc:
        eval "$(sessionkit completion zsh)"
    fish, in ~/.config/fish/config.fish:
        sessionkit completion fish | source

    TAB then offers the verbs, and after a service verb the names `sessionkit
    service list` shows, the groups and all. bash needs bash 4.4 or later;
    macOS's own /bin/bash is 3.2.
    """
    from click.shell_completion import get_completion_class

    cls = get_completion_class(shell)
    click.echo(cls(main, {}, "sessionkit", "_SESSIONKIT_COMPLETE").source())
