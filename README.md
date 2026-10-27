# Session Kit

Session Kit lets your Claude Code sessions mail each other, hear you and
answer aloud. One install brings the five family packages and their Claude
Code plugins.

## Installation

You need:

- macOS.
- [Claude Code][claude-code].
  - Have Claude Code: nothing to run.
  - No Claude Code: install it with Anthropic's installer.

    ```bash
    curl -fsSL https://claude.ai/install.sh | bash
    ```

  - Its "Setup notes" say `~/.local/bin is not in your PATH`? The installer
    does not change your PATH itself. Add the folder with Anthropic's two
    lines for zsh, the Mac's shell:

    ```bash
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
    source ~/.zshrc
    ```

  - Claude Code asks you to sign in the first time you start it.
- [Homebrew][brew] or at least Apple's Command Line Tools. Homebrew
  installs the Command Line Tools for you ([prerequisites][prereqs]), and
  the kit needs two of their tools: the plugin lines clone with git, and the
  ears build a Swift helper with `swiftc`.
  - Have Homebrew: nothing to run. It installed the Command Line Tools.
  - No Homebrew: get the Command Line Tools alone.

    ```bash
    xcode-select --install
    ```

- uv.
  - Have uv: nothing to run.
  - No uv: install it.

    ```bash
    curl -LsSf https://astral.sh/uv/install.sh | sh
    ```

  - Then open a new terminal, so `uv` is on your PATH. Or run:

    ```bash
    source ~/.zshrc
    ```

- For a call on a Mac: [Homebrew][brew], then ffmpeg from it. A call needs
  ffmpeg, and Homebrew is how a Mac gets it. The Command Line Tools alone
  are not enough for a call.
  - Have Homebrew: go on to ffmpeg.
  - No Homebrew: install it with its own installer, from [brew.sh][brew].
  - Then install ffmpeg:

    ```bash
    brew install ffmpeg
    ```

  - Homebrew lists what ffmpeg needs, then asks
    `Do you want to proceed with the installation? [y/n]`. Press `y`. It
    goes on at once, with no Return.
  - Then the speech server, then link the phone: the phone bullets below.
  - A call without Homebrew is the workaround case. This guide does not
    cover it.

Then install the kit:

```bash
uv tool install --python 3.14 sessionkit
claude plugin marketplace add sessionkit/sessionkit
claude plugin install sessionkit@sessionkit
```

The first line puts the commands on your PATH. The other two install the
kit's plugin and the five family plugins it depends on.

- **Keep `--python 3.14`.** Without it, uv takes the Python it finds: 3.15,
  where a voice library has no build yet and the install fails, or the
  Command Line Tools' 3.11. The kit is tested on 3.14.
- To upgrade:

  ```bash
  uv tool upgrade sessionkit
  ```

  It keeps the Python the install chose.
- To reinstall, give the pin again:

  ```bash
  uv tool install --python 3.14 --reinstall sessionkit
  ```

  Without it, uv drops the pin from its record, or, with `--force`, builds
  the kit again on the Python it finds.
- **A dialog may ask to install the Command Line Tools.** On a Mac without
  them, the first `uv tool install` opens it. Click Install and let it
  finish: the plugin lines need the git it brings. The dialog can open
  behind the Terminal window: look for it in the Dock or with Cmd-Tab.
- **Phone calls are installed, and walked for a session started with
  `session start <name>`.** A fresh Mac took a real call and passed. A plain
  `claude` session does not hear calls you make to it yet. Whether the phone
  bot signs its mail to your Claude follows your mail carrier:
  [bot mail signing][phone-signing].
- **The speech server comes before the phone.** A call hears you through
  it, so it is installed before you link your phone.
  - No phone: nothing to run now. [Hearing and speaking][hearing]
    installs the speech server with the rest of the voice.
  - A phone: first Homebrew, then ffmpeg, as the call item under "You
    need" says.

    ```bash
    brew install ffmpeg
    ```

  - At Homebrew's `[y/n]`, press `y`.
  - Then install the speech server. It builds the server and fetches its
    weights, about 2.9 GB.

    ```bash
    ears services install --only speech
    ```

  - Then link the phone. This makes its account on a public relay and
    prints the invite link. The name people see in their chat list goes in
    place of NAME:

    ```bash
    sessionphone setup --name NAME
    ```

    A name with a space in it needs quotes, or the shell splits it in two
    and setup refuses the second word:

    ```bash
    sessionphone setup --name "Ada Lovelace"
    ```

  - The rest of linking is in [sessionphone][pkg-phone]'s docs.

- **Then quit Claude Code and start it again**, every window of it, before
  you run anything else.

A plugin installed from the shell loads only when Claude Code starts, so a
session that was already open has no plugin commands on its PATH, and no
plugin hooks.

Then set up mail. This makes the box `claude`, which your first session
needs to hear mail and calls:

```bash
sessionkit setup
```

- **On a fresh Mac it exits 4, and that is expected.** It leaves two
  notmuch steps for later: [the manual install][setup] shows its last
  lines.

The three install lines leave the ears without the model they listen
with. Fetch it once:

```bash
ears install
```

It downloads the 2.3 MB voice-activity model from GitHub (one pinned
release of Silero VAD, checked against its SHA-256) to
`~/.cache/ears/silero_vad.onnx`, with no sudo, and prints `done`. Without
it the ears cannot hear you, and `ears services install`, the step that
starts them ([hearing and speaking][hearing]), refuses with
`silero MISSING`. The Swift helper is built later, when those services start.

- **The mail hooks start off.** They tell an agent about new mail between
  its tool calls. To turn them on, set `"hooks": true` in
  `~/.sessionkit/mail/settings/mail.json`. The plugin writes that file,
  with the hooks off, the first time a Claude Code session runs a tool,
  and it holds other settings too, so change only that key. Never write
  the file over: that deletes the other keys. This works whether the file
  is there yet or not, and whether it has a `hooks` key or not:

  ```bash
  f=~/.sessionkit/mail/settings/mail.json
  if [ -f "$f" ]; then
    perl -0777 -pi -e '
      if (/"hooks"\s*:/) { s/"hooks"\s*:\s*false/"hooks": true/ }
      elsif (/\A\s*\{\s*\}\s*\z/) { s/\{\s*\}/{"hooks": true}/ }
      else { s/\{(\s*)/"{$1" . q("hooks": true,) . ($1 || " ")/e }
    ' "$f"
  else
    mkdir -p ~/.sessionkit/mail/settings
    echo '{"version": 1, "hooks": true, "sendmail": "drop"}' > "$f"
  fi
  ```

  A `"hooks": false` becomes `true`. A file with no `hooks` key gets
  `"hooks": true` as its first key, and its other keys stay as they were.
  If the file is not there yet, this writes what the plugin would have
  written, with the hooks on. The plugin never replaces a file that is
  already there.

Step by step, with every step that needs you marked: [the manual
install][install].

To see what this Mac is still missing, run the kit's check. It installs
nothing. It prints one line for each thing the kit needs, and under each
missing one, the command that adds it:

```bash
sessionkit doctor
```

It exits 0 when nothing the kit needs is missing, and 1 when something is.
The phone bot and the session key are shown, but they never fail it.

- No kit yet, or `sessionkit` will not start? The installer runs the same
  check. Its address is not live yet. From a clone of this repository,
  run `bash install.sh --check`. Once the address is live:

  ```bash
  curl -fsSL https://sessionkit.ai/install.sh | bash -s -- --check
  ```

## Quick start

```bash
sessionkit --version
```

It lists the kit and each family package, with its version. Each `X.Y.Z`
is the version you installed:

```text
sessionkit, version X.Y.Z
  sessionmail   X.Y.Z
  sessiontools  X.Y.Z
  sessionphone  X.Y.Z
  sessionview   X.Y.Z
  sessionvoice  X.Y.Z
```

Start Claude in a project folder, not in your home folder, where a new
Terminal opens. Started in the home folder, Claude Code asks macOS for
access to folders such as Desktop, Downloads, Photos and Media Library.
Make a folder, go into it, and start Claude there:

```bash
mkdir -p ~/work && cd ~/work
session start
```

- **The first session on this Mac is `claude`, and it hears Delta.** Your
  phone's Delta messages and calls go to the box `claude`, and only the
  session that holds `claude` hears them. It says so as it starts:

  ```text
  session start: this session is claude, the default seat on this host (box claude)
  ```

- **A second session starts plain.** Start another the same way while the
  first one runs, and it is a plain Claude Code session. It does not hear
  Delta, and its one line names the session that holds `claude`:

  ```text
  session start: starting plain: the default seat claude is held by session 6161d8f8-d49f-4826-9f80-095bd2e6aaed (pid 6993, live 2s), so this session will NOT hear Delta messages or calls; that one does
  ```

- **Never a bare `claude`.** Mail to your agent's box, your phone's
  included, reaches only a session started as that agent.
- **Without the box `claude`, the first session starts plain too.** The
  mail setup under Installation makes the box ([first checks][checks]).
  The line names the repair:

  ```text
  session start: starting plain: box claude is missing, so this session will NOT hear Delta messages or calls; repair: message setup --box claude
  ```

Then, from your agent inside a Claude Code session, list your live
sessions:

```bash
session list
```

Mail another agent, its box name in place of TO:

```bash
message send TO -s "PR ready" -f note.md
```

Speak one line:

```bash
mouth say "the build is green"
```

- **Mail works inside a session.** `message` and `pager` read who is asking
  from the session. A plain terminal has no session, so they refuse with
  `no seat in the environment ... set an identity` ([first checks][checks]).
  A send never makes a box: the address must have one already ([mail
  between agents][mail]).
- **The mouth plays on your Mac's default output** when no device is set.
  `mouth devices` lists the others, and `--device DEVICE` picks one.
- **To hear you**, the ears need a speech-to-text server: [hearing and
  speaking][hearing].
- **Your agent talks with the kit's mouth and ears.** sessionvoice's ears
  skill sets the default:

  > **With the kit, an agent talks through the kit's own mouth and ears: it
  > speaks with `mouth say` and listens by arming the ears with `ears-arm`. That
  > is the default whenever the user asks it to talk, speak, listen or use voice,
  > even on a host that also has VoiceMode's `converse` tool. It uses `converse`
  > only when the user asks for converse by name.**

## Requirements

- [x] macOS (tested on macOS 27, Apple silicon)
- [ ] Linux
- [ ] WSL
- [ ] Windows

What the kit depends on, what needs each one, and how to upgrade it:
[dependencies][dependencies].

## Uninstall

```bash
claude plugin marketplace remove sessionkit
uv tool uninstall sessionkit
```

Removing the marketplace removes its six plugins too, but not the copies they
ran from. Those copies, the services and your data have their own steps:
[uninstall][uninstall].

## Usage

Every command answers `--help`, and each has a page: [components][components].

## The family

Session Kit installs these together:

- [sessionmail][pkg-mail]: mail for coding agents. `message`, `pager` and
  `memory` over one maildir.
- [sessiontools][pkg-tools]: sessions, status and idle. `session`.
- [sessionvoice][pkg-voice]: ambient voice. `ears` hears; `mouth` speaks.
- [sessionphone][pkg-phone]: phone calls to a session over Delta Chat.
  Installed, and walked on a fresh Mac for a session started with
  `session start <name>`. A plain `claude` session does not hear calls you
  make to it yet.
- [sessionview][pkg-view]: a tmux sidebar of your projects and your agents.
  `sessionview` (said "session view").

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
make install
make check
```

`make install` installs the kit editable, with uv. `make check` runs ruff,
shellcheck, then the tests.

The rules for changing the kit: [AGENTS.md][agents].

## Status

Alpha, 0.3.2. Tested on macOS 27 on Apple silicon; Linux and Windows are
untested. What you may still hit: [known gaps][gaps].

Licence: [AGPL-3.0][licence].

[claude-code]: https://code.claude.com/docs/en/overview
[brew]: https://brew.sh
[install]: INSTALL.md
[prereqs]: INSTALL.md#1-prerequisites-human
[setup]: INSTALL.md#2-install-the-kit
[checks]: INSTALL.md#4-first-checks
[hearing]: INSTALL.md#5-hearing-and-speaking-it-hears-me-and-speaks
[mail]: INSTALL.md#mail-between-agents
[uninstall]: INSTALL.md#8-uninstall
[gaps]: INSTALL.md#7-known-gaps-you-will-hit
[components]: docs/components.md
[dependencies]: docs/dependencies.md
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
