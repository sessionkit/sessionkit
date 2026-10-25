# The agent letter: what it says about the pager and voice

An agent's letter is the note it writes to itself and reads each time it
wakes. A wake item is a step that runs at wake. Both live in the agent's
mailbox, not in this repo. Their shape, the labels and how items run, is
sessionmail's: see its `memory` skill,
[sessionmail's skills/memory](https://github.com/sessionkit/sessionmail/tree/HEAD/skills/memory).
This page does not repeat that shape. It gives the words about the pager, and
about voice, that every letter should carry.

**Wake items and the trust registry.** From sessionmail 0.2.0, the release the
kit installs, `memory run` is off until you opt in with
`SESSIONMAIL_MEMORY_RUN=1`. Without that it runs nothing, says so, and points
at `memory run PATH --list` (**MEASURED** on sessionmail 0.2.0 from
PyPI, a temporary home directory: exit 4). An item runs only if its signer
passes the trust check, which reads a registry: `$SESSION_REGISTRY`, else
`"registry"` in `~/.sessionkit/mail/settings/mail.json`. With neither, every item is
refused (read in its `--help`). That key names the registry's folder, which
holds an `allowed_signers` file and a `certs/` folder (read in sessionmail's
settings schema). **No command creates a registry today**,
sessionmail's or this kit's, so a fresh install has none. The registry and the
seat keys in it are described in
[sessionmail's docs/message-seat.md](https://github.com/sessionkit/sessionmail/blob/HEAD/docs/message-seat.md).
A stranger meets the registry only by following the off-state hint into
`--list`. In sessionmail 0.2.0 that refusal says what the key names, says
that sessionmail does not create a registry today, and points at that doc
(read in its source, sessionmail 0.2.0 from PyPI: an item has to
be signed to reach the registry check, and a fresh install has no key to
sign one). The `memory` in sessionmail 0.1.0, which earlier kits installed,
has no opt-in: `memory run /BOOT/WAKE` ran an item with none set
(**MEASURED** on sessionmail 0.1.0, a temporary home directory).

- **Status:** template. Copy the block below into your own letter.

## The rule

Put this in your letter, word for word:

```text
Never arm or stop the pager from a wake item; `pager status` is the only check.
The plugin's monitor arms the pager. A wake item never does.
With no monitor, I arm it from my own turn, when the pager's hook says it is
not listening: one `pager listen`, as a background tool call.
```

What that means:

- **The plugin's monitor arms the pager.** The sessionmail plugin's monitor
  runs one pager for the whole Claude Code session, from its start. It is
  on by default. On a session that has it, you do not start the
  pager, and nothing in your letter does.
- **With no monitor, the agent's own turn arms it, never a wake item.** A
  session can be without the monitor: a headless `claude -p` session, a
  Claude Code that did not start it (see the last section), a sessionmail
  plugin from before the monitor shipped (no `monitors/monitors.json`), a
  monitor turned off, or one that ended (below). Without it, sessionmail's
  hooks say so: when `"hooks": true` is set in `~/.sessionkit/mail/settings/mail.json`,
  the Stop hook and the hooks between tool calls print *pager is not
  listening -
  re-arm with the `pager listen` line ...*. The agent answers from its own
  live turn: it runs `pager listen` once, as a background tool call (Bash
  `run_in_background: true`, never a trailing `&`), and runs it again each
  time it returns. That is the agent answering its hook, not a wake item.
  With the hooks off, the default, nothing says it; mail waits in the box
  for `message list` or the next `pager listen`.
- **A wake item never arms the pager.** It does not run `pager listen`, in
  the background or otherwise.
- **A wake item never stops the pager.** It does not run `pager off` or
  `pager stop`. What they do depends on the `pager` you have:
  - **On sessionmail 0.1.0, before the kit floored it at 0.2.0:** either one
    ends the monitor for good. Claude Code does not restart a monitor whose
    command has exited, so the monitor stays down until Claude Code
    restarts. A stop is also taken as on purpose, so the hooks go quiet:
    the Stop hook says nothing and the hooks between tool calls say
    *pager is off - stopped on purpose*, with no re-arm line. Until Claude
    Code restarts, the agent's own turn runs the bare `pager listen` in the
    background without waiting for a hook to ask.
  - **The kit's `pager`, sessionmail 0.2.0 and later:**
    on the monitor, both REFUSE. They exit 4, write nothing, stop nothing,
    and name `pager mute` (it silences the monitor, which keeps running)
    and `pager stop --kill`. `--kill` is the only way to end the monitor.
    It ends it for good, as on 0.1.0, but the hooks between tool calls then
    say *this session's pager monitor was ended*, not *stopped on
    purpose*. On a hand `pager listen`, `pager off` and `pager stop` still
    stop it, as before.
    **MEASURED** (sessionmail 0.2.0 from PyPI, a temporary home
    directory): `pager mute`, `pager unmute` and `pager stop --kill` are there and
    run; with no monitor running each says so and exits 3. The refusal on a
    running monitor is read in their `--help`, not run.
- **`pager status` is the only check.** A wake item that wants to know about
  mail runs `pager status`. It never blocks, and it changes nothing. If the
  answer looks wrong, the wake item reports it, and you or your human fix it
  outside the wake.

## Why

An agent went deaf for about ten minutes after a restart. Its wake ran before
the plugin's monitor had started. The restart prompt and the agent's letter
both said to arm the pager first, so its wake item ran `pager listen` and
then `pager off` by hand. That fought the monitor, and nothing was listening
until it was noticed.

A wake runs at the one moment the monitor may not be up yet. Anything the
wake does to the pager races it. So the wake looks, and leaves arming to the
monitor, or, with no monitor, to the agent's own turn.

## Voice: mouth and ears by default

Put this in your letter too, word for word. It is the rule from sessionvoice's
ears skill:

```text
With the kit, an agent talks through the kit's own mouth and ears: it
speaks with `mouth say` and listens by arming the ears with `ears-arm`. That
is the default whenever the user asks it to talk, speak, listen or use voice,
even on a host that also has VoiceMode's `converse` tool. It uses `converse`
only when the user asks for converse by name.
```

The letter is read at every wake, so the rule is in front of the agent before
it picks a way to talk. A host with VoiceMode installed offers `converse` in
every session; this line tells the agent which path is the kit's. How to arm
the ears and speak on the user's device is in sessionvoice's ears skill.

## Restart prompts

The kit does not write a restart prompt. If you write your own, it says the
same thing as the letter: never tell an agent to arm or stop the pager when
it wakes; the plugin's monitor arms it (with no monitor, the agent's own turn
does), and `pager status` is the only check.

## The monitor itself

The monitor ships in the sessionmail plugin itself, on by default.
The plugin's `monitors/monitors.json` runs `pager listen
--monitor` with the `pager` on your PATH. The kit's install (INSTALL.md
section 3) installs that plugin, so a kit session has the monitor with
nothing to turn on. Claude Code runs a plugin's monitor only in an
interactive session (never `claude -p`), with the folder trusted, and only
while its own monitor gate is on. When it does not run it, nothing in
Claude Code says so (sessionmail's `docs/pager-monitor.md`; the trust
condition is from the README of its retired `plugins/pager-monitor`); the hooks'
*not listening* line, with `"hooks": true`, is what tells the agent.
sessionmail's old separate plugin,
`plugins/pager-monitor`, is retired: it arms nothing now, and you
do not need it.

sessionmail's off switch (`"monitor": false` in
`~/.sessionkit/mail/settings/mail.json` for the host, or `SESSIONMAIL_MONITOR=off`
at launch for one session), `pager mute` / `pager unmute`, and
`pager stop --kill` ship in sessionmail 0.2.0, the release the kit installs.
**MEASURED** (sessionmail 0.2.0 from PyPI, a temporary home
directory): the three verbs answer and run. The off switch is read in its
settings schema and its source, not run. The 0.1.0 `pager` had the `--monitor` flag the plugin runs, but none
of these.
