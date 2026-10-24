"""sessionkit - the front door. Help first: every verb is here before it works."""
from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

import click

from sessionkit import setup as operator_setup

CTX = {"help_option_names": ["-h", "--help"]}

# The family packages the kit installs and re-exports, in pyproject order.
# tests/test_cli.py holds this list to pyproject's [project] dependencies.
FAMILY = ("sessionmail", "sessiontools", "sessionphone", "sessionview", "sessionvoice")
NOT_INSTALLED = "not installed"


def installed_version(dist: str) -> str:
    """The INSTALLED distribution's version, never a string kept in the source."""
    try:
        return version(dist)
    except PackageNotFoundError:
        return NOT_INSTALLED


def version_lines() -> list[str]:
    """The kit's line in the family's form (`pager, version X`), then one per child."""
    width = max(len(name) for name in FAMILY)
    lines = [f"sessionkit, version {installed_version('sessionkit')}"]
    lines += [f"  {name:<{width}}  {installed_version(name)}" for name in FAMILY]
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
    help="Show the kit's version and each family package's, then exit.",
)
@click.pass_context
def main(ctx: click.Context) -> None:
    """Session Kit gives your Claude Code sessions voice, mail, a phone line and a tmux sidebar, in one install."""
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@main.command(context_settings=CTX)
def hello() -> None:
    """Say hello - the stub every verb starts as."""
    click.echo("Hello from sessionkit!")


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
    default=operator_setup.DEFAULT_AGENT,
    show_default=True,
    callback=_shape(operator_setup.check_agent_shape),
    help="Your assistant's name: setup writes its agent file and makes its "
    "mail box, so `session start NAME` starts Claude as NAME, hearing mail to NAME.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Run every check and print what would be written; write nothing.",
)
def setup(mailbox: str | None, address: str | None, agent: str, dry_run: bool) -> None:
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

    Then your assistant (--agent, default claude): it writes NAME.md where
    `session start` looks for agents (~/.session/agents, unless
    $AGENTS_DIR or ~/.session/agent/config says otherwise), not keyed, and
    asks `message setup` for the box NAME. A file already there, in either
    layout, is left as it is. It ends with the one launch step:
    `session start NAME`.

    Before that step it asks `ears backends`, read only. If the ears'
    voice-activity model is missing, it says one line naming `ears install`.
    It never runs `ears install`, and the line never changes the exit.

    Exit 0 all done, 1 refused or failed, 2 usage, 4 done what it could,
    mail steps left for you. See INSTALL.md, "Operator and administrators"
    and "Mail between agents".
    """
    if mailbox is not None and address is not None:
        raise click.UsageError("give --mailbox or --address, not both")
    outcome = operator_setup.run_setup(
        mailbox=mailbox, address=address, agent=agent, dry_run=dry_run
    )
    for line in outcome.lines:
        click.echo(line, err=outcome.code != 0)
    raise SystemExit(outcome.code)
