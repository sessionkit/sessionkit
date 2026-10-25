# Dependencies

Everything Session Kit depends on: what needs each one, whether you need it,
how it gets onto your Mac, and how you upgrade it. The README's
[requirements][readme-requirements] link here. The full resolved set, every
package at the version this repo is tested with, is in [`uv.lock`][uv-lock].

- **Required:** macOS, Claude Code, uv, Python 3.14, Apple's Command Line
  Tools, and jq, which macOS 27 ships. `uv tool install` brings the Python
  packages.
- **Optional:** the speech server, the ears' voice-activity model, Delta
  Chat, and a few tools single features use.
- **For calls on a Mac:** Homebrew, then ffmpeg from it, before the speech
  server ([for calls on a Mac][calls]).
- **Pending a ruling:** tmux and notmuch, and Homebrew and ffmpeg for
  anything but a call. Whether the kit requires them is not decided yet;
  their entries say what uses each one today ([pending a ruling][pending]).
- **Upgrade:** `uv tool upgrade sessionkit` for the kit and its packages,
  `claude plugin update` for the plugins ([upgrade][upgrade]).

Required means a default command fails without it. Optional means a feature
you turn on needs it, or a command still works without it but does less.

## Required

| Dependency | What needs it | How you get it | How you upgrade it |
|---|---|---|---|
| macOS | Everything. Tested on macOS 27 on Apple silicon. | Your Mac. | Software Update. |
| [Claude Code][claude-code] | The kit's plugin and the five family plugins; the sessions the kit runs in. | Its installer. | Claude Code's own update. |
| [uv][uv] | `uv tool install sessionkit`; `ears services install`, which builds the speech server with it; `session ledger`, which counts tokens through it. | The uv installer, or `brew install uv`. | `uv self update`, or `brew upgrade uv` for a Homebrew copy. |
| Python 3.14 | The kit and the five packages run on it. 3.11 to 3.14 install; 3.14 is the one tested. | `uv tool install --python 3.14` fetches it. | It stays with the kit: `uv tool upgrade sessionkit` keeps it. |
| Apple's Command Line Tools | `git`, for `claude plugin marketplace add` and `claude plugin install`, which clone the plugins. `swiftc`, which builds the ears' device watcher, the sound engine (`session sound engine`) and the phone's reader for text in pictures. | `xcode-select --install`, or Homebrew's installer, which brings them. | Software Update. |
| jq | `message send` to a seat's name: without it, that seat's pager is never woken. The mail still lands in the box it is addressed to, but the seat's session box gets no copy. | macOS 27 ships `/usr/bin/jq`. If `command -v jq` prints nothing, `brew install jq`. | Software Update, or `brew upgrade jq`. |
| The Python packages | Every command on your PATH. | `uv tool install sessionkit` brings them from PyPI. | `uv tool upgrade sessionkit`. |

The Python packages are the kit's own, and they bring their own:

- [sessionmail][pkg-mail] 0.3.1 or later: `message`, `pager`, `memory`.
- [sessiontools][pkg-tools] 0.3.1 or later: `session`.
- [sessionphone][pkg-phone] 0.3.0 or later, with its `media` extra, which
  the bot, the calls and `sessionphone web` need.
- [sessionview][pkg-view] 0.3.0 or later: `sessionview`.
- [sessionvoice][pkg-voice] 0.3.0 or later, with its `capture` extra, so the
  ears can hear the room: `ears`, `ears-serve`, `mouth`, `talk`.
- click 8.1 or later, for the `sessionkit` command itself.

## Optional

| Dependency | What needs it | Without it | How you get it | How you upgrade it |
|---|---|---|---|---|
| The speech server | Hearing you (the ears' speech-to-text), the mouth's voice and a phone call's voice. It listens on `127.0.0.1:8890`. | The ears, which hear through it by default, cannot turn speech into text; the mouth and calls speak with macOS `say`. | `ears services install` builds it with uv, at the version sessionvoice pins. | After `uv tool upgrade sessionkit`, run `ears services install` again: it re-applies the versions sessionvoice pins. |
| The voice-activity model | The ears telling speech from silence. | The ears cannot hear you, and `ears services install` refuses with `silero MISSING`. | `ears install`, 2.3 MB to `~/.cache/ears/silero_vad.onnx`. | sessionvoice pins it. `ears install` checks the copy on disk against the pin and says when it differs; to replace it, remove the file and run `ears install`. |
| [Delta Chat][delta-chat] | Phone calls: an account on a public relay, and the app on your phone. | No calls. | `sessionphone setup` makes the account; the app comes from your phone's app store ([sessionphone][pkg-phone]). | The app's own update. |

A few tools serve one feature of one package, and each package's own docs
name them: neomutt, lazygit and nvim for the sidebar's tabs
([sessionview][pkg-view]); passage or pass for secrets in agent files
([sessiontools][pkg-tools]); Tailscale for the phone's web page
([sessionphone][pkg-phone]). `session ledger` also needs tiktoken's
`cl100k_base` vocabulary on disk, which it never downloads
([sessiontools][pkg-tools]).

## For calls on a Mac

A phone call is optional. On a Mac, a call needs Homebrew, then ffmpeg from
it: Homebrew is the default way to get a call's ffmpeg.

- [Homebrew][brew], from its own installer, at [brew.sh][brew].
- Then ffmpeg:

  ```bash
  brew install ffmpeg
  ```

- Then the speech server (Optional, above), then link the phone.
- A call without Homebrew is the workaround case. This page does not cover
  it.

## Pending a ruling

Whether the kit requires these four is not decided yet, past a call on a
Mac ([for calls on a Mac][calls]), so this page gives them no class and no
install step here. Each entry says what uses it today, what
happens without it, and where it comes from today.

### [Homebrew][brew]

Status: pending a ruling, except for calls on a Mac ([for calls on a
Mac][calls]). The rest hangs on the rulings for tmux and notmuch, and for
ffmpeg's other uses, below.

- **What uses it:** no kit command runs `brew`. It is where tmux, notmuch
  and ffmpeg come from today, and its installer brings Apple's Command Line
  Tools.
- **Without it:** the Command Line Tools come from `xcode-select --install`
  instead.
- **Where it comes from today:** its installer, from its own site.

### [tmux][tmux]

Status: pending a ruling.

- **What uses it:** `session start --in-tmux` and `session start
  --tmux-target`; `session reap --yes`, to close a seat's pane; `session
  pane-state agent on`; the `sessionview` sidebar, which needs 3.7 or newer.
- **Without it:** `session start --in-tmux` stops with "tmux is not
  installed (or not on PATH)"; `session reap --yes` closes no pane; `session
  pane-state agent on` refuses and changes nothing; the sidebar does not
  run. `session list` still works.
- **Where it comes from today:** Homebrew.

### [notmuch][notmuch]

Status: pending a ruling. Whether the kit needs notmuch, and a replacement
for its search built on SQLite's full-text search, are being researched.

- **What uses it:** `memory ls`, `memory tree`, `memory cat` and `memory
  run`, and the recent threads in `memory wake`. `message mark` looks a
  message up in it. `message setup` writes its profile, runs `notmuch new`
  once to build its index and links its hooks.
- **Without it:** `memory ls` and `memory tree` stop with an error; `memory
  wake` says it could not look and goes on; `message mark` looks only in the
  seat's own boxes; `message setup` leaves its notmuch steps `BLOCKED`.
- **Where it comes from today:** Homebrew.

### [ffmpeg][ffmpeg]

Status: pending a ruling, except for calls on a Mac ([for calls on a
Mac][calls]). What else the kit needs ffmpeg for is being researched.

- **What uses it:** `mouth play` of a sound file; `mouth render` to `.mp3`
  or `.m4a`; `ears file`; measuring a voice's loudness, so the mouth can
  level it; a phone call's reply in the speech server's voice.
- **Without it:** the mouth cannot play the file or write `.mp3` or `.m4a`,
  and `ears file` fails; a voice not yet measured is not levelled; on a
  call, a line the speech server rendered is sent as chat text instead.
  With no speech server, calls speak in the Apple voice and need no ffmpeg.
- **Where it comes from today:** Homebrew.

## Upgrade

```bash
uv tool upgrade sessionkit
claude plugin marketplace update sessionkit
claude plugin update sessionkit@sessionkit
```

- **The first line** upgrades the kit, the five packages and their Python
  dependencies, and keeps the Python 3.14 the install chose. To reinstall,
  keep the pin: [install][install-upgrade].
- **The plugin lines** fetch the marketplace again, then the kit's plugin.
  The five family plugins update the same way, by name, for example
  `claude plugin update sessionmail@sessionkit`. Restart Claude Code after.

[readme-requirements]: ../README.md#requirements
[uv-lock]: ../uv.lock
[upgrade]: #upgrade
[pending]: #pending-a-ruling
[calls]: #for-calls-on-a-mac
[brew]: https://brew.sh
[install-upgrade]: ../INSTALL.md#2-install-the-kit
[claude-code]: https://code.claude.com/docs/en/overview
[uv]: https://docs.astral.sh/uv/
[tmux]: https://github.com/tmux/tmux
[notmuch]: https://notmuchmail.org
[ffmpeg]: https://ffmpeg.org
[delta-chat]: https://delta.chat
[pkg-mail]: https://github.com/sessionkit/sessionmail
[pkg-tools]: https://github.com/sessionkit/sessiontools
[pkg-phone]: https://github.com/sessionkit/sessionphone
[pkg-view]: https://github.com/sessionkit/sessionview
[pkg-voice]: https://github.com/sessionkit/sessionvoice
