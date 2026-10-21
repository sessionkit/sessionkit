# Session Kit

Session Kit lets your Claude Code sessions mail each other, hear you and
answer aloud. One install brings the five family packages and their Claude
Code plugins.

## Installation

You need macOS and [Claude Code][claude-code]. If you do not have uv yet,
install it with `curl -LsSf https://astral.sh/uv/install.sh | sh`, then open
a new terminal (or run `source ~/.local/bin/env`).

```bash
uv tool install --python 3.14 sessionkit
claude plugin marketplace add sessionkit/sessionkit
claude plugin install sessionkit@sessionkit
```

The first line puts the commands on your PATH. The other two install the
kit's plugin and the five family plugins it depends on. Start Claude Code
(or restart it) to load them.

- **Keep `--python 3.14`.** Without it, uv takes the Python it finds: 3.15,
  where a voice library has no build yet and the install fails, or the
  Command Line Tools' 3.11. The kit is tested on 3.14.
- **A dialog may ask to install the Command Line Tools.** On a Mac without
  them, the first `uv tool install` opens it. Click Install and let it
  finish: the plugin lines need the git it brings.
- **Phone calls are installed, not yet walked.** Whether the phone bot
  signs its mail to your Claude follows your mail carrier: [bot mail
  signing][phone-signing].

- **The mail hooks start off.** They tell an agent about new mail between
  its tool calls. To turn them on, set `"hooks": true` in
  `~/.sessionkit/mail/settings/mail.json`. On a fresh install the file is
  not there yet, so make it:

  ```bash
  mkdir -p ~/.sessionkit/mail/settings
  echo '{"version": 1, "hooks": true}' > ~/.sessionkit/mail/settings/mail.json
  ```

  If the file is there, change only that key, because it can hold other
  settings:

  ```bash
  perl -pi -e 's/"hooks": *false/"hooks": true/' ~/.sessionkit/mail/settings/mail.json
  ```

Step by step, with every step that needs you marked: [the manual
install][install].

## Quick start

```bash
sessionkit --version
```

It lists the kit and each family package, with its version:

```text
sessionkit, version 0.2.1
  sessionmail   0.2.1
  sessiontools  0.2.0
  sessionphone  0.2.1
  sessionview   0.2.0
  sessionvoice  0.2.1
```

Start Claude with `session start claude`, never a bare `claude`: mail to
your agent's box, your phone's included, reaches only a session started as
that agent. `sessionkit setup` makes the box and the agent first: [first
checks][checks].

Then, from your agent inside a Claude Code session:

```bash
session list                                     # your live sessions
message send <box> -s "PR ready" -f note.md      # mail another agent
mouth say --device default "the build is green"  # speak one line
```

- **Mail works inside a session.** `message` and `pager` read who is asking
  from the session. A plain terminal has no session, so they refuse with
  `no seat in the environment ... set an identity` ([first checks][checks]).
  A send never makes a box: the address must have one already ([mail
  between agents][mail]).
- **The mouth needs a device.** `--device default` is your Mac's default
  output; `mouth devices` lists the others.
- **To hear you**, the ears need a speech-to-text server: [hearing and
  speaking][hearing].

## Uninstall

```bash
claude plugin marketplace remove sessionkit
uv tool uninstall sessionkit
```

Removing the marketplace removes its six plugins too. The services and your
data have their own steps: [uninstall][uninstall].

## Usage

Every command answers `--help`, and each has a page: [components][components].

## The family

Session Kit installs these together:

- [sessionmail][pkg-mail]: mail for coding agents. `message`, `pager` and
  `memory` over one maildir.
- [sessiontools][pkg-tools]: sessions, status and idle. `session`.
- [sessionvoice][pkg-voice]: ambient voice. `ears` hears; `mouth` speaks.
- [sessionphone][pkg-phone]: phone calls to a session over Delta Chat.
  Installed, not yet walked.
- [sessionview][pkg-view]: a tmux sidebar of your projects and your agents.

## Components

The commands, services and folders the install adds, and where each
package logs: [components][components].

## Configuration

Each package configures itself: [configuration][configuration]. How the
settings files stack: [the settings guide][settings].

## Logs

Each package keeps its own log: [logs][logs]. Which one to read for a
symptom: [troubleshooting][troubleshooting].

## Development

```bash
git clone https://github.com/sessionkit/sessionkit
cd sessionkit
make install    # editable: uv tool install -e .
make check      # ruff, shellcheck, then the tests
```

The rules for changing the kit: [AGENTS.md][agents].

## Status

Alpha, 0.2.1. Tested on macOS 27 on Apple silicon; Linux and Windows are
untested. What you may still hit: [known gaps][gaps].

Licence: [AGPL-3.0][licence].

[claude-code]: https://claude.ai/code
[install]: INSTALL.md
[checks]: INSTALL.md#4-first-checks
[hearing]: INSTALL.md#5-hearing-and-speaking-it-hears-me-and-speaks
[mail]: INSTALL.md#mail-between-agents
[uninstall]: INSTALL.md#8-uninstall
[gaps]: INSTALL.md#7-known-gaps-you-will-hit
[components]: docs/components.md
[logs]: docs/components.md#logs
[configuration]: docs/configuration.md
[settings]: docs/settings.md
[troubleshooting]: docs/troubleshooting.md
[agents]: AGENTS.md
[licence]: LICENSE
[pkg-mail]: https://github.com/sessionkit/sessionmail
[pkg-tools]: https://github.com/sessionkit/sessiontools
[pkg-voice]: https://github.com/sessionkit/sessionvoice
[pkg-phone]: https://github.com/sessionkit/sessionphone
[phone-signing]: https://github.com/sessionkit/sessionphone/blob/HEAD/docs/bot-mail-signing.md
[pkg-view]: https://github.com/sessionkit/sessionview
