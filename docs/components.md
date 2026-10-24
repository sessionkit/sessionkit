# Components

What the install adds to your Mac: commands on your PATH, services you can
run, folders in your home, and a log for each package.

- **Commands:** eleven, each with a page here ([commands][commands]).
- **Services:** launchd jobs you start yourself, and the pager monitor
  ([services][services]).
- **Folders:** settings, sessions, mail and voice ([folders][folders]).
- **Logs:** one or more per package ([logs][logs]).

Every command answers `--help`, and each verb's help is its reference.

## Commands

| Command | What it does | Package |
|---|---|---|
| [`sessionkit`][cmd-sessionkit] | The front door: setup, and help for every verb. | [sessionkit][pkg-kit] |
| [`message`][cmd-message] | Send, list, read and mark mail between agents. | [sessionmail][pkg-mail] |
| [`pager`][cmd-pager] | Wake an idle agent when mail or an alert lands. | [sessionmail][pkg-mail] |
| [`memory`][cmd-memory] | An agent's mailbox, read as a filesystem. | [sessionmail][pkg-mail] |
| [`session`][cmd-session] | List live sessions, read their settings, start one. | [sessiontools][pkg-tools] |
| [`sessionphone`][cmd-sessionphone] | Phone calls to a session over Delta Chat; installed, and walked on a fresh Mac for a session started with `session start <name>`. | [sessionphone][pkg-phone] |
| [`sessionview`][cmd-sessionview] | A tmux sidebar of your projects and your agents. | [sessionview][pkg-view] |
| [`ears`][cmd-ears] | Hear the room and write your turns to a log. | [sessionvoice][pkg-voice] |
| [`ears-serve`][cmd-ears-serve] | A speech-to-text server over Apple's on-device speech. | [sessionvoice][pkg-voice] |
| [`mouth`][cmd-mouth] | Speak one line at a time, on the device you choose. | [sessionvoice][pkg-voice] |
| [`talk`][cmd-talk] | A live web view of the conversation. | [sessionvoice][pkg-voice] |

Three more, `sessionview-config`, `sessionview-session` and
`sessionview-messages`, are helpers the sidebar calls. They are leaving your
PATH. macOS has its own `talk` at `/usr/bin/talk`; which one runs depends on
the order of your PATH.

### First commands

Mail ([sessionmail][pkg-mail]); inside a Claude Code session:

```bash
pager status                      # what would page you now; never blocks
message list                      # one line per message, no bodies
memory ls /                       # your mailbox, read as a filesystem
```

Sessions ([sessiontools][pkg-tools]):

```bash
session list                      # every live session, with its context
session context <seat>            # how full one session's window is
session settings <session-id>     # each setting, with the file that set it
```

Voice ([sessionvoice][pkg-voice]):

```bash
ears install                      # fetch the voice-activity model
ears backends                     # which speech engines run on this Mac
mouth devices                     # your output devices, as --device takes them
```

Phone ([sessionphone][pkg-phone]): installed, and walked on a fresh Mac for a
session started with `session start <name>`: a real call reached that session
and was answered aloud. A plain `claude` session does not hear calls you make
to it yet. `sessionphone --help` lists its verbs.

The sidebar ([sessionview][pkg-view]) is its plugin: there is nothing to run
first.

## Services

| Service | Started by | Package |
|---|---|---|
| The speech server, `dev.sessionkit.voice.mlx-audio` | `ears services install` | [sessionvoice][pkg-voice] |
| The ears: `dev.sessionkit.voice.ears-mouth`, `-ears-keeper`, `-ears-mail` | `ears services install` | [sessionvoice][pkg-voice] |
| The phone bot | `sessionphone bot install` | [sessionphone][pkg-phone] |
| The live view | `talk serve` | [sessionvoice][pkg-voice] |
| The pager monitor | the sessionmail plugin, inside each Claude Code session | [sessionmail][pkg-mail] |

The launchd jobs are labelled `dev.sessionkit.<package>.<job>`. The
uninstall removes them ([uninstall][uninstall]).

## Folders

- `~/.sessionkit/<package>/settings/`: each package's settings.
- `~/.session/`: your sessions and seats.
- `~/.mail/`: the mail between agents.
- `~/.sessionvoice/`, `~/.ears/` and `~/.local/state/ears/`: the voice.

## Logs

The kit writes no log of its own: `sessionkit setup` prints to your
terminal. Each family package keeps its own:

- **sessionmail** (from 0.2.0): `~/.session/sessions/<session-id>/log/mail/pager.jsonl`,
  one row for each thing the pager told an agent
  (the pager log: [sessionmail's docs/pager-inject-log.md][mail-log]).
- **sessiontools** (from 0.2.0): `~/Library/Logs/sessiontools/`, with
  `sound-engine.log` and `pane-state.log`.
- **sessionphone:** `~/.sessionphone/bot.log`.
- **sessionview:** `~/.local/state/sessionview/sessionview.log`.
- **sessionvoice:** the heard log, `heard_YYYY-MM-DD.jsonl`, and the
  services' logs in `~/Library/Logs/ears/`
  (where each one is: [sessionvoice's docs/logs.md][voice-logs]).

Follow one as it grows with `tail -F`, for example
`tail -F ~/.sessionphone/bot.log`. Which file to read for a symptom:
[troubleshooting][troubleshooting].

- **Health:** `sessionkit --version` lists the kit and each family
  package, with its installed version; `not installed` beside a name means
  that package is missing.

[commands]: #commands
[services]: #services
[folders]: #folders
[logs]: #logs
[cmd-sessionkit]: sessionkit.md
[cmd-message]: message.md
[cmd-pager]: pager.md
[cmd-memory]: memory.md
[cmd-session]: session.md
[cmd-sessionphone]: sessionphone.md
[cmd-sessionview]: sessionview.md
[cmd-ears]: ears.md
[cmd-ears-serve]: ears-serve.md
[cmd-mouth]: mouth.md
[cmd-talk]: talk.md
[uninstall]: ../INSTALL.md#8-uninstall
[troubleshooting]: troubleshooting.md
[pkg-kit]: ../README.md
[pkg-mail]: https://github.com/sessionkit/sessionmail
[pkg-tools]: https://github.com/sessionkit/sessiontools
[pkg-phone]: https://github.com/sessionkit/sessionphone
[pkg-view]: https://github.com/sessionkit/sessionview
[pkg-voice]: https://github.com/sessionkit/sessionvoice
[mail-log]: https://github.com/sessionkit/sessionmail/blob/HEAD/docs/pager-inject-log.md
[voice-logs]: https://github.com/sessionkit/sessionvoice/blob/HEAD/docs/logs.md
