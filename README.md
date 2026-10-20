# Session Kit

Session Kit lets your Claude Code sessions hear you, answer aloud, pick up
when you ring from your phone, and mail each other.

[![PyPI](https://img.shields.io/pypi/v/sessionkit)](https://pypi.org/project/sessionkit/)

Voice when your hands are busy, a phone line when you are away, and mail so
one agent can hand work to another. One install brings the whole family.

<!-- DEMO: a 30-second clip. You speak in the room; the agent answers
     aloud; then it rings your phone. Recorded on a real Mac, no edits. -->

- **Mail between agents.** `message`, `pager` and `memory`: signed mail over
  one maildir. An idle agent wakes when mail lands, and its mailbox is its
  memory.
- **Sessions you can see.** `session list` shows every live Claude Code
  session and how full its context window is.
- **Ambient voice.** `ears` hears the room and writes your turns to a log;
  `mouth` speaks one line at a time on the device you choose.
- **Your phone.** `sessionphone` lets you ring a session over Delta Chat
  from anywhere.
- **A sidebar.** A tmux sidebar of your projects and your agents, here and
  on remote hosts.

## Quick start

With uv already on your PATH (if not, start at
[Installation](#installation)):

```bash
uv tool install --python 3.14 sessionkit
session list
```

`session list` prints your live Claude Code sessions:

```text
SHORT      NAME          STATUS   REPO        PANE    RUNTIME   IDLE CONTEXT
4f2a9c10   reviewer-17   busy     myproject   %1           2m     2m      6%
```

## Installation

You need macOS and [Claude Code](https://claude.ai/code), plus uv:
`curl -LsSf https://astral.sh/uv/install.sh | sh`. Then open a new
terminal, or run `source ~/.local/bin/env`, before the lines below:
without it, the terminal you ran the installer in answers
`command not found: uv`. The plugins also need git:
`xcode-select --install` on a Mac that has never had it.

Keep `--python 3.14`: on Python 3.15, two of the voice libraries have no
build yet, and the install falls back to an empty 0.0.1 release.

```bash
uv tool install --python 3.14 sessionkit
```

The commands land on your PATH: `message pager memory session sessionphone
ears ears-serve mouth sessionkit`. Open a new terminal, or run `uv tool
update-shell`.

The plugins (the skills and hooks) are a second step. **The one-step
plugin install is coming: the kit's own plugin does not load yet**, so
today these two lines fail:

```bash
# Coming once the kit's plugin loads: these fail today.
claude plugin marketplace add sessionkit/sessionkit
claude plugin install sessionkit@sessionkit
```

Until then, do not install `sessionkit@sessionkit` from a clone either:
it fails to load. The path that works today:
[install the plugins from your clones][clones].

[clones]: #install-the-plugins-from-your-clones

> **The mail hooks start off.** Until you turn them on, an agent is not
> told about new mail between its tool calls, nor reminded to listen for
> mail when it stops. One setting turns them on: `"hooks": true` in
> `~/.sessionkit/mail/settings/mail.json`. The mail plugin writes that file, set to
> `false`, the first time its hooks run, so on a fresh install it may not
> be there yet. If it is not, create it on:
>
> ```bash
> mkdir -p ~/.sessionkit/mail/settings
> echo '{"version": 1, "hooks": true}' > ~/.sessionkit/mail/settings/mail.json
> ```
>
> If the file is there, change only that key, because the file can hold
> other settings:
>
> ```bash
> perl -pi -e 's/"hooks": *false/"hooks": true/' ~/.sessionkit/mail/settings/mail.json
> ```

To hear you, the ears also need a speech-to-text server on this Mac.
VoiceMode's `/voicemode:install` sets one up
([VoiceMode](https://github.com/mbailey/voicemode)).

Step by step, with every step that needs you (a password, a permission
prompt, a sign-in) marked: [the manual install](INSTALL.md).

### Uninstall

```bash
uv tool uninstall sessionkit
```

If you installed the plugins from your clones, remove each plugin, then
the local marketplace:

```bash
for r in sessionmail sessiontools sessionphone sessionview sessionvoice; do
  claude plugin uninstall "$r@sessionkit-local"
done
claude plugin marketplace remove sessionkit-local
```

If you followed [the manual install](INSTALL.md), which adds each
clone's own marketplace, remove those five. Removing a marketplace
removes its plugin too:

```bash
for r in sessionmail sessiontools sessionphone sessionvoice \
         sessionview; do
  claude plugin marketplace remove "$r"
done
```

Once the one-step install works, its marketplace goes with
`claude plugin marketplace remove sessionkit`.

## Install the plugins from your clones

If you have the family's repos cloned, Claude Code can install the
plugins from your clones. In a marketplace, a local plugin's `source` must
start with `./`: a path inside the marketplace's own folder. So make one
folder with a `./` symlink to each clone and a `marketplace.json` that
lists them. Set `SRC` to the folder that holds your clones:

```bash
SRC=~/src                                  # the folder with your clones
MKT=~/.local/share/sessionkit/marketplace  # the local marketplace
mkdir -p "$MKT/.claude-plugin"
for r in sessionmail sessiontools sessionphone sessionview sessionvoice; do
  ln -sfn "$SRC/$r" "$MKT/$r"
done
cat > "$MKT/.claude-plugin/marketplace.json" <<'EOF'
{
  "name": "sessionkit-local",
  "description": "The session family, from local clones",
  "owner": { "name": "local" },
  "plugins": [
    { "name": "sessionmail", "source": "./sessionmail" },
    { "name": "sessiontools", "source": "./sessiontools" },
    { "name": "sessionphone", "source": "./sessionphone" },
    { "name": "sessionview", "source": "./sessionview" },
    { "name": "sessionvoice", "source": "./sessionvoice" }
  ]
}
EOF
claude plugin marketplace add "$MKT"
for r in sessionmail sessiontools sessionphone sessionview sessionvoice; do
  claude plugin install "$r@sessionkit-local"
done
```

This installs the five family plugins one by one, not the kit's own
plugin.

### After a git pull

The install is a copy, not a link. Claude Code copies each plugin into its
cache, under `~/.claude/plugins/cache/`, pinned to the clone's commit. A
`git pull` in a clone changes nothing until you refresh the marketplace
and update the plugin, then restart Claude Code:

```bash
claude plugin marketplace update sessionkit-local
claude plugin update sessionmail@sessionkit-local  # each plugin you pulled
```

If the plugin still runs the old code, reinstall it:
`claude plugin uninstall sessionmail@sessionkit-local`, then
`claude plugin install sessionmail@sessionkit-local`.

### Or read the clones live with --plugin-dir

If your launcher can pass flags to `claude`, `--plugin-dir` loads a plugin
straight from its clone, for that session only. Nothing is installed or
cached, so a `git pull` shows up the next time you start `claude`. Repeat
the flag once per plugin:

```bash
claude --plugin-dir "$SRC/sessionmail" --plugin-dir "$SRC/sessionvoice"
```

## Usage

Every command answers `--help`, and each verb's help is its reference.

**Mail** ([sessionmail](https://github.com/sessionkit/sessionmail)):

```bash
pager status                      # what would page you now; never blocks
message send reviewer -s "PR ready, please review" -f note.md
message list                      # one line per message, no bodies
memory ls /                       # your mailbox, read as a filesystem
```

The sessionmail plugin's monitor arms the pager for the whole session. It is
on by default in an interactive `claude` session, and the kit's
install brings it ([INSTALL.md](INSTALL.md) section 3). Its off switch and
`pager mute` are not in the 0.1.0 `pager` the kit installs yet. With no
monitor running, the agent arms the pager itself, as a background tool call,
when the pager's hook says it is not listening. Either way, if your agent
keeps a letter to itself, it says:
never arm or stop the pager from a wake item; `pager status` is the only check
([the agent letter](docs/agent-letter.md)).

**Sessions** ([sessiontools](https://github.com/sessionkit/sessiontools)):

```bash
session list                      # every live session, with its context
session context <seat>            # how full one session's window is
session settings <session-id>     # each setting, with the file that set it
```

**Voice** ([sessionvoice](https://github.com/sessionkit/sessionvoice)):

```bash
ears install                      # fetch the voice-activity model
ears backends                     # which speech engines run on this Mac
mouth devices                     # your output devices, as --device takes them
mouth say "the build is green"    # speak one line
```

**Phone** ([sessionphone](https://github.com/sessionkit/sessionphone)):

```bash
sessionphone setup --name <name>  # an account on a public chatmail relay
sessionphone qr                   # a QR code: scan it with Delta Chat
sessionphone link                 # wait for your phone to join, then approve it
```

**Sidebar** ([sessionview](https://github.com/sessionkit/sessionview)): the
plugin is the whole install. Its commands are under [Components](#components).

## The family

Session Kit is the meta project: it installs these together, each at 0.1.0
or later.

- [sessionmail](https://github.com/sessionkit/sessionmail): mail for coding
  agents. `message`, `pager` and `memory` over one maildir.
- [sessiontools](https://github.com/sessionkit/sessiontools): the harness
  layer. Sessions, status and idle, one driver per harness.
- [sessionvoice](https://github.com/sessionkit/sessionvoice): ambient voice.
  `ears` turns a microphone into turns; `mouth` speaks.
- [sessionphone](https://github.com/sessionkit/sessionphone): ring your
  Claude Code session from your phone over Delta Chat.
- [sessionview](https://github.com/sessionkit/sessionview): a tmux sidebar
  of your projects and your agents.

## Components

What the install adds to your Mac: commands on your PATH, services you can
run, and folders in your home. Each command links to its page in
[docs](docs/), and each package to its repo.

### Commands

| Command | What it does | Package |
|---|---|---|
| [`sessionkit`][cmd-sessionkit] | The front door: setup, and help for every verb. | [sessionkit][pkg-kit] |
| [`message`][cmd-message] | Send, list, read and mark mail between agents. | [sessionmail][pkg-mail] |
| [`pager`][cmd-pager] | Wake an idle agent when mail or an alert lands. | [sessionmail][pkg-mail] |
| [`memory`][cmd-memory] | An agent's mailbox, read as a filesystem. | [sessionmail][pkg-mail] |
| [`session`][cmd-session] | List live sessions, read their settings, start one. | [sessiontools][pkg-tools] |
| [`sessionphone`][cmd-sessionphone] | Ring a session from your phone over Delta Chat. | [sessionphone][pkg-phone] |
| [`sessionview`][cmd-sessionview] | A tmux sidebar of your projects and your agents. | [sessionview][pkg-view] |
| [`ears`][cmd-ears] | Hear the room and write your turns to a log. | [sessionvoice][pkg-voice] |
| [`ears-serve`][cmd-ears-serve] | A speech-to-text server over Apple's on-device speech. | [sessionvoice][pkg-voice] |
| [`mouth`][cmd-mouth] | Speak one line at a time, on the device you choose. | [sessionvoice][pkg-voice] |
| [`talk`][cmd-talk] | A live web view of the conversation. | [sessionvoice][pkg-voice] |

Three more, `sessionview-config`, `sessionview-session` and
`sessionview-messages`, are helpers the sidebar calls. They are leaving your
PATH. macOS has its own `talk` at `/usr/bin/talk`; which one runs depends on
the order of your PATH.

### Services

| Service | Started by | Package |
|---|---|---|
| The speech server, `dev.sessionkit.voice.mlx-audio` | `ears services install` | [sessionvoice][pkg-voice] |
| The ears: `dev.sessionkit.voice.ears-mouth`, `-ears-keeper`, `-ears-mail` | `ears services install` | [sessionvoice][pkg-voice] |
| The phone bot | `sessionphone bot install` | [sessionphone][pkg-phone] |
| The live view | `talk serve` | [sessionvoice][pkg-voice] |
| The pager monitor | the sessionmail plugin, inside each Claude Code session | [sessionmail][pkg-mail] |

The launchd jobs are labelled `dev.sessionkit.<package>.<job>`.
[INSTALL.md section 8](INSTALL.md#8-uninstall) removes them.

### Folders

- `~/.sessionkit/<package>/settings/`: each package's settings.
- `~/.session/`: your sessions and seats.
- `~/.mail/`: the mail between agents.
- `~/.sessionvoice/`, `~/.ears/` and `~/.local/state/ears/`: the voice.

Each package's log is under [Logs](#logs).

[cmd-sessionkit]: docs/sessionkit.md
[cmd-message]: docs/message.md
[cmd-pager]: docs/pager.md
[cmd-memory]: docs/memory.md
[cmd-session]: docs/session.md
[cmd-sessionphone]: docs/sessionphone.md
[cmd-sessionview]: docs/sessionview.md
[cmd-ears]: docs/ears.md
[cmd-ears-serve]: docs/ears-serve.md
[cmd-mouth]: docs/mouth.md
[cmd-talk]: docs/talk.md
[pkg-kit]: https://github.com/sessionkit/sessionkit
[pkg-mail]: https://github.com/sessionkit/sessionmail
[pkg-tools]: https://github.com/sessionkit/sessiontools
[pkg-phone]: https://github.com/sessionkit/sessionphone
[pkg-view]: https://github.com/sessionkit/sessionview
[pkg-voice]: https://github.com/sessionkit/sessionvoice

## Configuration

Each package configures itself. Its configuration page says which files,
which environment variables, and where each one lives:

- [sessionmail's docs/configuration.md](https://github.com/sessionkit/sessionmail/blob/HEAD/docs/configuration.md):
  mail between agents.
- [sessiontools's docs/configuration.md](https://github.com/sessionkit/sessiontools/blob/HEAD/docs/configuration.md):
  the `session` command and its sounds.
- [sessionphone's docs/configuration.md](https://github.com/sessionkit/sessionphone/blob/HEAD/docs/configuration.md):
  the phone line.
- [sessionview's docs/configuration.md](https://github.com/sessionkit/sessionview/blob/HEAD/docs/configuration.md):
  the tmux sidebar.
- [sessionvoice's docs/configuration.md](https://github.com/sessionkit/sessionvoice/blob/HEAD/docs/configuration.md):
  the ears and the mouth.
- [Session Kit](docs/configuration.md):
  the kit's own, the operator that `sessionkit setup` writes.

Most settings are JSON files in layers, from the host down to one session,
and the most specific wins. Where they live and how they stack:
[the settings guide](docs/settings.md).

## Logs

The kit writes no log of its own: `sessionkit setup` prints to your
terminal. Each family package keeps its own:

- **sessionmail** (from 0.2.0): `~/.session/sessions/<session-id>/log/mail/pager.jsonl`,
  one row for each thing the pager told an agent
  (the pager log: [sessionmail's docs/pager-inject-log.md](https://github.com/sessionkit/sessionmail/blob/HEAD/docs/pager-inject-log.md)).
- **sessiontools** (from 0.2.0): `~/Library/Logs/sessiontools/`, with
  `sound-engine.log` and `pane-state.log`.
- **sessionphone:** `~/.sessionphone/bot.log`.
- **sessionview:** `~/.local/state/sessionview/sessionview.log`.
- **sessionvoice:** the heard log, `heard_YYYY-MM-DD.jsonl`, and the
  services' logs in `~/Library/Logs/ears/`
  (where each one is: [sessionvoice's docs/logs.md](https://github.com/sessionkit/sessionvoice/blob/HEAD/docs/logs.md)).

Follow one as it grows with `tail -F`, for example
`tail -F ~/.sessionphone/bot.log`. Which file to read for a symptom:
[troubleshooting](docs/troubleshooting.md).

- **Health:** `sessionkit --version` lists the kit and each family
  package, with its installed version; `not installed` beside a name means
  that package is missing.

## Development

Clone the repo from `https://github.com/sessionkit/sessionkit`. **NOT YET
MEASURED:** nobody has yet cloned from this URL on a clean Mac and run the
lines below; the measured runs used clones that were already on the
machine.

```bash
git clone https://github.com/sessionkit/sessionkit  # NOT YET MEASURED from this URL
cd sessionkit
make install    # editable: uv tool install -e .
make check      # ruff, shellcheck, then the tests
```

Each family repo has the same layout and the same `make` targets.

## Status

**Alpha, 0.1.0.** Tested on macOS 27 on Apple silicon.

- **Works:** the commands, and each family repo's plugin from its own
  clone ([install the plugins from your clones][clones]).
- **Not yet:**
  - Hearing needs a speech-to-text server that you bring.
  - Mail between agents needs postfix on sessionmail 0.1.0. From 0.2.0, not
    yet released, it goes by sessionmail's experimental file drop, with no
    mail server and nothing to set: see
    [Mail between agents](INSTALL.md#mail-between-agents).
    `sessionkit setup` runs sessionmail's mail setup, `message setup`, which
    also ships from 0.2.0; on 0.1.0 it says so and names the step.
  - The one-step plugin install: the kit's own plugin does not load yet.
  - Linux and Windows are untested.

Licence: AGPL-3.0.
