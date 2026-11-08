# Session Kit

Session Kit gives your Claude Code sessions a voice, a phone line and a
mailbox. From the people who brought you [VoiceMode][voicemode].

```bash
curl -fsSL https://sessionkit.ai/install.sh | bash
```

This repo is the kit's home: the installer, the [manual steps][manual]
and the docs.

<!-- Hero image goes here: Talk on a phone, mid-conversation (Mike's shot). -->

## Features

- **Voice.** Your session hears the room and answers aloud.
- **A phone line.** Text or ring your session from Delta Chat on your phone.
- **Mail.** Agents mail each other, and an idle agent wakes when mail lands
  ([mail between agents][mail]).
- **A crew.** One agent starts another and hands it the work.
- **Talk.** Watch the conversation live in a browser.

## Quick start

After the install, do what its last screen lists (sign in to Claude Code
once), then start your first session, in whatever folder you're in:

```bash
session start
```

Ask Claude to call you. It shows a QR code: scan it with your phone and
follow the steps to install Delta Chat. Then you can text or ring your
session.

## What it installs

Session Kit installs the family in one go: five packages, each with its
Claude Code plugin, and the Settings page.

- [sessionmail][pkg-mail]: mail for agent memory and communication
  ([the paper][paper]).
- [sessiontools][pkg-tools]: your live sessions, and starting new ones.
- [sessionvoice][pkg-voice]: the ears hear the room; the mouth speaks.
- [sessionphone][pkg-phone]: a phone line to your session, over Delta Chat.
- [sessionview][pkg-view]: a tmux sidebar of your projects and agents.
- [settled][settled]: the kit's settings page, on your own Mac.

Every command answers `--help`. Commands, services and folders:
[components][components].

## Requirements

- [x] macOS on Apple silicon (tested on an M5 MacBook Air, 16 GB, macOS 27)
- [ ] Linux (preliminary testing; no install steps yet)
- [ ] WSL
- [ ] Windows

You need:

- [Homebrew][brew]
- [uv][uv]
- [Claude Code][claude-code]
- About 8 GB of free disk

The installer adds any of the first three that are missing.

## Installation

The one line at the top checks your Mac, lists what it will add, and asks
before it installs anything. Rather run each step yourself? With the
requirements in place (the speech server is about 4 GB):

```bash
brew install tmux ffmpeg notmuch
uv tool install --python 3.14 sessionkit
claude plugin marketplace add sessionkit/sessionkit
claude plugin install sessionkit@sessionkit
ears install
ears services install --agent claude
sessionkit setup
pager settings hooks on
```

Then quit Claude Code, every window, so the plugins load. Check it with
`sessionkit doctor`. More detail: [step by step][install]. To remove it:
[uninstall][uninstall].

**Already using VoiceMode?** It keeps working. Use either one, or both side
by side.

## Configuration

Each package's settings: [configuration][config]. How they stack:
[settings][settings].

## Logs

Where each log is: [logs][logs]. Which to read for a symptom:
[troubleshooting][trouble]. Restarting a service: [service][service].
**Health:** `sessionkit doctor`.

## Development

`make install`, then `make check`. The rules: [AGENTS.md][agents].

## Status

Alpha, 0.3.3. A new release most Sundays. [Known gaps][gaps] · Licence
[AGPL-3.0][licence].

[voicemode]: https://voicemode.dev
[brew]: https://brew.sh
[uv]: https://docs.astral.sh/uv/
[claude-code]: https://code.claude.com/docs/en/overview
[install]: INSTALL.md
[manual]: #installation
[mail]: INSTALL.md#mail-between-agents
[gaps]: INSTALL.md#7-known-gaps-you-will-hit
[uninstall]: INSTALL.md#8-uninstall
[components]: docs/components.md
[config]: docs/configuration.md
[settings]: docs/settings.md
[service]: docs/service.md
[logs]: docs/components.md#logs
[trouble]: docs/troubleshooting.md
[agents]: AGENTS.md
[licence]: LICENSE
[pkg-mail]: https://github.com/sessionkit/sessionmail
[paper]: https://cora7.com/blog/the-mailbox-is-the-memory/
[pkg-tools]: https://github.com/sessionkit/sessiontools
[pkg-voice]: https://github.com/sessionkit/sessionvoice
[pkg-phone]: https://github.com/sessionkit/sessionphone
[pkg-view]: https://github.com/sessionkit/sessionview
[settled]: https://github.com/sessionkit/settled
