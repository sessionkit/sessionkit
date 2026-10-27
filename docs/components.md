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

Mail ([sessionmail][pkg-mail]), inside a Claude Code session. What would
page you now; it never blocks:

```bash
pager status
```

One line per message, no bodies:

```bash
message list
```

Your mailbox, read as a filesystem:

```bash
memory ls /
```

Sessions ([sessiontools][pkg-tools]). Every live session, with its context:

```bash
session list
```

How full one session's window is, a seat or a session id in place of SEAT:

```bash
session context SEAT
```

Each setting, with the file that set it, a session id in place of SID:

```bash
session settings SID
```

Voice ([sessionvoice][pkg-voice]). Fetch the voice-activity model:

```bash
ears install
```

Which speech engines run on this Mac:

```bash
ears backends
```

Your output devices, as `--device` takes them:

```bash
mouth devices
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
- `~/.sessionkit/<package>/log/`: the logs of sessionmail's launch
  agents, sessiontools, sessionphone, sessionview and sessionvoice
  ([logs][logs]).
- `~/.sessionkit/view/state/`: the live view's state.
- `~/.sessionkit/phone/state/`: the phone bot's root, with its Delta Chat
  account and its keys. Before 0.3.2 it was `~/.sessionphone/`. A Mac that
  has only the old one keeps using it, and nothing moves it by itself
  ([moving it][phone-root]).
- `~/.session/`: your sessions and seats.
- `~/.mail/`: the mail between agents.
- `~/.sessionvoice/`, `~/.ears/` and `~/.local/state/ears/`: the voice.

## Logs

The kit writes no log of its own: `sessionkit setup` prints to your
terminal. Each family package keeps its own:

- **sessionmail** (from 0.2.0): `~/.session/sessions/<session-id>/log/mail/pager.jsonl`,
  one row for each thing the pager told an agent
  (the pager log: [sessionmail's docs/pager-inject-log.md][mail-log]).
  Its launch agents, when you install them, log to `~/.sessionkit/mail/log/`:
  a seat agent to `seat-agent.<ADDRESS>.log`
  ([sessionmail's docs/message-seat.md][mail-seat-log]), and the puller to
  `puller.log` ([sessionmail's docs/pull.md][mail-pull-log]).
- **sessiontools:** `~/.sessionkit/tools/log/`, with `sound-engine.log`,
  `pane-state.log`, `default-model.log` and `reap.log`
  ([sessiontools' README][tools-logs]).
- **sessionphone:** each bot's own folder,
  `~/.sessionkit/phone/log/<agent>/`, with `bot.log` and `bot.launchd.log`
  ([sessionphone's README][phone-logs]).
- **sessionview:** `~/.sessionkit/view/log/sessionview.log`
  ([sessionview's README][view-logs]).
- **sessionvoice:** the heard log, `heard_YYYY-MM-DD.jsonl`, in the voice's
  home, and the services' logs in `~/.sessionkit/voice/log/`
  (where each one is: [sessionvoice's docs/logs.md][voice-logs]).

Before 0.3.2 these logs were in `~/Library/Logs/` (`sessiontools/`, `ears/`,
an older log folder from before the kit, and a seat agent's
`seat-agent.<ADDRESS>.log`), `~/.sessionphone/`
and `~/.local/state/sessionview/`; the puller's was
`<pull.state_dir>/log/puller.log`. The pager log has not moved. An upgrade
leaves the old files where they are, and nothing deletes them. A service
that an older release installed keeps writing its old log until it is
installed again:

- **A seat agent:** until it is uninstalled and installed again.
- **The puller:** until `message setup --pull` renders its plist again.

Follow a log as it grows with `tail -F`. For the phone bot, put its
agent's name in place of AGENT:

```bash
tail -F ~/.sessionkit/phone/log/AGENT/bot.log
```

Which file to read for a symptom: [troubleshooting][troubleshooting].

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
[mail-seat-log]: https://github.com/sessionkit/sessionmail/blob/HEAD/docs/message-seat.md#the-log
[mail-pull-log]: https://github.com/sessionkit/sessionmail/blob/HEAD/docs/pull.md#the-log
[voice-logs]: https://github.com/sessionkit/sessionvoice/blob/HEAD/docs/logs.md
[tools-logs]: https://github.com/sessionkit/sessiontools#logs
[phone-logs]: https://github.com/sessionkit/sessionphone#logs
[phone-root]: troubleshooting.md#the-phone-bot-still-uses-the-old-root
[view-logs]: https://github.com/sessionkit/sessionview#logs
