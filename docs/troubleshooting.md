# Troubleshooting

A hub, not a manual: one line per symptom, a check you can paste, and a
link to the package doc that explains it. Paths are the defaults; your
environment variables move them (`EARS_LOG_DIR` moves the ears logs).

Start with the kit's check. It prints what the kit needs and what is
missing, with the command that adds each missing thing, and installs
nothing ([first checks][first-checks]):

```bash
sessionkit doctor
```

No kit yet, or `sessionkit` will not start: `bash install.sh --check`, from
a clone of the kit, runs the same check. Once the installer's address is
live, so does
`curl -fsSL https://sessionkit.ai/install.sh | bash -s -- --check`.

## The files to tail

Voice flows ears → heard log → turn mail → pager → your agent → mouth.
The usual answer is three files. Measured, there are four, and the
third is there only if turn mail runs:

1. **The heard log**: `logs/conversations/heard_YYYY-MM-DD.jsonl` in the
   voice's state root, which `ears home state-dir` prints:
   `~/.sessionkit/voice/state` on a new Mac, and `~/.sessionvoice` or
   `~/.voicemode` on a Mac that kept its log there
   ([moving it][voice-move]). What the ears
   heard (`partial`, `turn`), what the mouth said (`saying`, `said`), and
   a `heartbeat` every 15 seconds while a capture runs. Every line has a
   `seq`, which links it to the turn mail.
   (the capture: [sessionvoice's README, Components][sv-parts]; every log
   line: [sessionvoice's docs/logs.md][sv-logs])
2. **The ears logs**: `~/.sessionkit/voice/log/ears-*.log`, one for each
   launch agent (`ears-keeper.log`, `ears-mouth.log`), and the keeper's
   capture and call logs (`ears-keeper-capture.log`,
   `ears-keeper-calls.log`) in the same folder. Crashes land here: a
   capture that keeps dying, a device that went away. Before 0.3.2 they
   were in `~/Library/Logs/ears/` and an older log folder from before the kit. Those
   old files are left where they are, and a keeper an older release
   installed keeps writing there until `ears services install` runs again.
   (the keeper: [sessionvoice's README, Components][sv-parts]; every log
   file: [sessionvoice's docs/logs.md][sv-logs])
3. **The turn mail log**: `ears-mail.log`, beside the ears logs, so the
   same `*` catches it. One JSON line per heard turn it mailed: the
   `seq`, the box it went to, the subject and the Message-ID. **A kit
   install has no turn mail**: `ears services install` does not install
   it ([manual install, section 5][hear]). There, this file is missing,
   and the waiter wakes your agent instead.
4. **The pager's verdicts**: `mail/verdicts` in the agent's session
   folder, which `session path sessions <session-id>` prints
   (`~/.sessionkit/tools/state/sessions/<session-id>` on a new Mac,
   `~/.session/sessions/<session-id>` on a Mac that has `~/.session/`).
   One JSON line per mail the pager judged for that agent: `wake` or
   `ride`, and the rule that decided it. The file appears with the first mail judged.
   ([how the pager works][pager])

Paste this:

```bash
tail -F "$(ears home state-dir)"/logs/conversations/heard_$(date +%F).jsonl \
  ~/.sessionkit/voice/log/ears-*.log \
  "$(ls -t "$(session path sessions)"/*/mail/verdicts | head -1)"
```

The last line takes the agent whose pager judged a mail most recently.
With more than one agent, put its session id in the path instead: the
agent's `$CLAUDE_SESSION_ID`, or `session_id` in `session list --json`.

## Where it gets stuck

### Ears running, but deaf

You talk, but no `turn` lines appear in the heard log.

- **Services down:** `ears services status`. The `keeper` line should
  say `running`. ([install][sv-install])
- **No VAD model (Silero):** `ears backends | grep silero`. It should say
  `ok:` and the model's path; `no model` means run `ears install`.
  Without the model the keeper dies and restarts every few seconds.
  ([install][sv-install])
- **STT failing (a 500, or refused):** each line this prints names the
  STT's URL and its error.

  ```bash
  grep -ho 'whisper at[^"]*' ~/.sessionkit/voice/log/ears-*.log \
    "$(ears home state-dir)"/logs/conversations/heard_$(date +%F).jsonl | tail -3
  ```

  Then check that the server answers; this should print `200`. It is the
  default URL; yours is `final.url` in `~/.sessionkit/voice/settings/ears.json`.
  ([the speech server][sv-req])

  ```bash
  curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8890/v1/models
  ```

- **Lid shut:**
  `ioreg -r -k AppleClamshellState | grep '"AppleClamshellState"'`.
  `Yes` means the lid is shut, and a shut lid turns the built-in mic off.
  The heard log says so too: an `ears-deaf` event, `room: lid: shut`.
  With the lid shut, the keeper does not listen on the built-in mic. It
  sends one mail,
  `ears: DEAF, lid shut, built-in mic off, holding at HH:MM EOM`, and
  holds until another input becomes the Mac's default or the lid opens.
  It does not go looking for another input the Mac did not make the
  default. Use another input.

### Heard, but the agent never woke

The turn is in the heard log, but the agent did nothing.

- **No waiter (a kit install):** `pgrep -fl heard-first`. If it prints
  nothing, nothing is watching the heard log for your agent. Arm it with
  `ears-arm <seat> room` ([manual install, section 5][hear]), and arm it
  again each time it fires. (the modes:
  [sessionvoice's skills/ears/SKILL.md][sv-modes])
- **No wake name:** say "hey" and the agent's name, or "hey everyone". A
  bare mention of its name does not wake it, by design. This prints the
  last turns as the ears wrote them, as the waiter reads them.
  (the modes: [sessionvoice's skills/ears/SKILL.md][sv-modes])

  ```bash
  grep '"kind": "turn"' \
    "$(ears home state-dir)"/logs/conversations/heard_$(date +%F).jsonl | tail -3
  ```

- **No turn mail:** `tail -3 ~/.sessionkit/voice/log/ears-mail.log`. No such
  file means no heard turn became mail. A kit install has none (see the
  turn mail log above); the waiter is its wake.
- **The rule that decided:** `pager why <Message-ID>`, run in the agent's
  session, prints the action (`wake`, `carry`, `ride`) and the rule that
  gave it. From a terminal, set the session:
  `CLAUDE_SESSION_ID=<session-id> pager why <Message-ID>`. Exit 3 means
  the pager never judged that mail. ([how the pager works][pager])
- **No listener:** `pgrep -fl 'pager listen'`. A seat with no
  `pager listen` running cannot be woken by mail.
  ([how the pager works][pager])

### A call answered, but no reply

The agent picks up the call, then says nothing back. The phone's own
log, `bot.log` in `~/.sessionkit/phone/log/<agent>/`, says where each
turn was mailed, whether anyone
answered it, and why a call never connected: see
[its call troubleshooting][phone-calls].

- **The call's turns went to another box:** run `pager why <Message-ID>`
  on a call-turn mail. ``ride by `ride *` (the built-in default)`` means
  no rule of yours matched, so nothing woke the agent. Send the call's
  turns To the agent, or add a `wake` rule that matches them
  (`pager rule --help`). ([how the pager works][pager];
  [the phone][phone])
- **The call is not heard:** this counts today's call turns in the heard
  log. `0` means none, even if the call's capture started and is beating;
  look at the keeper's call log:
  `tail ~/.sessionkit/voice/log/ears-keeper-calls.log`.

  ```bash
  grep '"source": "call"' \
    "$(ears home state-dir)"/logs/conversations/heard_$(date +%F).jsonl |
    grep -c '"kind": "turn"'
  ```

### The voice chops

The agent's speech stutters or cuts out as it plays. The mouth's own
troubleshooting has the causes and the checks: see
the voice chops, in
[sessionvoice's docs/troubleshooting.md][sv-mouth].

## Steps an upgrade does not run

An upgrade replaces the programs. It does not change a server that is
already running. Each step here is done by hand, on each Mac, when you
choose to. It is a step of its own, not part of the upgrade, and nothing
runs it for you.

### The plugins are older than the kit

`sessionkit doctor` reads `🧩 Plugin versions: not at their packages'
versions` and names each plugin left behind. Upgrading the kit's package
does not update its Claude Code plugins, and a failed plugin update leaves
them where they were. Run the `→` lines under that row, then restart
Claude Code.

### A plain session hears the default seat's mail

A session you did not start as the default seat (`claude`) still hears
box `claude`. sessiontools after 0.3.1 keeps `CLAUDE_CODE_AGENT` out of
every launch and out of a tmux server it starts. Its CHANGELOG says what is
left to you: "a tmux server born inside a seat before this fix keeps the
word for every pane it makes until it is restarted, or until
`tmux set-environment -g -u CLAUDE_CODE_AGENT` is run on it." A
`session start` in such a pane drops the word; a raw `claude` typed
there keeps it. ([the default seat][session-seat])

- Check the server first. `CLAUDE_CODE_AGENT=claude` means it holds the
  word. `unknown variable: CLAUDE_CODE_AGENT` means it does not, and
  there is nothing to do.

  ```bash
  tmux show-environment -g CLAUDE_CODE_AGENT
  ```

- To keep its panes open, remove the word from the server:

  ```bash
  tmux set-environment -g -u CLAUDE_CODE_AGENT
  ```

  A pane made after this does not hold the word. A pane already open
  keeps it until you close it.
- Or restart the server: close every pane on it, then start tmux again.
  Start it from a terminal, not from inside the seat. A raw `tmux` started
  in the seat's own shell is born holding the word again.
- Run the check again. It should print
  `unknown variable: CLAUDE_CODE_AGENT`.

**MEASURED** on tmux 3.8, on a throwaway server: the check printed
`CLAUDE_CODE_AGENT=claude` on a server started with the word, and
`unknown variable: CLAUDE_CODE_AGENT` (exit 1) after the removal; a pane
opened before the removal still held the word, and a pane opened after
did not.

### Tools' state is still in the old folders

sessiontools keeps its state in `~/.sessionkit/tools/state/` on a new Mac.
A Mac that already has `~/.session/` keeps using its old folders, and
nothing moves them by itself: an upgrade never does. `session path` prints
each folder, and `session path --json` says `old` for each one still in
the old place. ([where tools keeps its state][tools-paths])

`session path migrate` moves two of them, once, on each Mac:

- **`state`:** `~/.session/state/` to `~/.sessionkit/tools/state/`.
- **`sound`:** `~/.local/share/sessiontools/sound/` to
  `~/.sessionkit/tools/state/sound/`.

It moves each by rename and leaves the old path as a link to the new
folder. Nothing deletes the old path. Your sessions, seats, agent files
and backups stay in `~/.session/`: this verb does not move them. Do not
move or delete `~/.session` by hand.
([moving tools' state][tools-migrate])

The move is a step of its own on each Mac: stop, move, check, start again.

- Check first. Its `agents` block names each tools agent and says
  `loaded` or `not loaded`. It changes nothing.

  ```bash
  session path migrate --dry-run
  ```

- Stop each agent the check shows `loaded`. A real run refuses while one
  is loaded.
  - **`pane-state agent`:**

    ```bash
    session pane-state agent off
    ```

  - **`sound engine`:**

    ```bash
    session sound engine off
    ```

  - **`default-model watch`:**

    ```bash
    launchctl bootout gui/$(id -u)/dev.sessionkit.tools.default-model
    ```

  - **`pane-state watch`:** a `session pane-state watch` you started by
    hand. Stop it in its own terminal.
- A `session default-model watch` you started by hand is not in the
  check. Stop any you started.
- Check again. Every agent should read `not loaded`, with no `would
  refuse` line and no key-like name (`id_rsa`, `*.pem`). A key-like name
  is listed, not refused: stop there and look at it first.

  ```bash
  session path migrate --dry-run
  ```

- Move:

  ```bash
  session path migrate
  ```

  When it refuses (exit 3), nothing was moved, and it names why.
- Check the move. `state` and `sound` should read `new`.

  ```bash
  session path --json
  ```

- Start again each agent you stopped:
  - **`pane-state agent`:**

    ```bash
    session pane-state agent on
    ```

  - **`sound engine`:**

    ```bash
    session sound engine on
    ```

  - **`default-model watch`:**

    ```bash
    launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/dev.sessionkit.tools.default-model.plist
    ```

- **Upgrade all six packages together.** An older copy of sessiontools
  (the one inside another package's environment, say) still writes
  `~/.session/state/` and makes the old folder real again. `session path
  --json` adds `stranded` to a folder whose new copy holds state while the
  old one is in use.

### The voice state is still in the old root

The voice keeps its state (the heard log, the mouth's folder, talk's
token, the speakers' rows) in `~/.sessionkit/voice/state` on a new Mac. A
Mac whose heard log is in `~/.sessionvoice` or `~/.voicemode` keeps using
that folder, and a state item at its old path (such as
`~/.local/state/ears/`) stays there. Nothing moves by itself. `ears
services status` then prints a second `state` row naming the old path and
`ears home migrate`. A root you set (`SESSIONVOICE_HOME`,
`VOICEMODE_BASE_DIR`) is never moved, and this step is not for it.
([the state root][voice-root])

`ears home migrate` moves it, once, on each Mac. It copies, checks each
file, and leaves each old path as a link to its new place, with the
original kept beside it as `<path>.pre-sessionkit`. It never deletes. On
`~/.voicemode` it moves only the voice's own files, never VoiceMode's.
The old shared seat home, `~/.ears`, is not moved. Do not move or delete
any of these by hand.

The move is a step of its own on each Mac: stop, move, check, start again.

- Check first. It prints the plan and every reason it would refuse, and
  writes nothing.

  ```bash
  ears home migrate --dry-run
  ```

- Stop the voice jobs. The move refuses while a voice launch agent is
  loaded or a voice writer runs, and the plan names each one.

  ```bash
  ears services uninstall
  ```

- Stop any other writer the plan names: a voice program you started by
  hand and, when the old root is `~/.voicemode`, VoiceMode's own capture
  loop or mouth player, and the phone bot.
- Move:

  ```bash
  ears home migrate
  ```

  When it refuses (exit 1), nothing was written. When it stops part-way
  (exit 3), run it again: a second run finishes the move.
- Check the move. The `state` row should name
  `~/.sessionkit/voice/state`, with no second row naming an old path.

  ```bash
  ears services status
  ```

- Re-arm each reader the move's report lists: the ones that hold the
  heard log open.
- Install the voice jobs again, before any writer starts and before your
  next login, with the same flags you installed them with. Install writes
  the new paths into each job; a job left from before still names an old
  path and makes it real again.

  ```bash
  ears services install
  ```

- Start again any other writer you stopped.

### The phone bot still uses the old root

The phone bot's root holds its Delta Chat account and its keys. From 0.3.2
the root is `~/.sessionkit/phone/state/`; before, it was `~/.sessionphone`.
A Mac that has only the old root keeps using it, and each `sessionphone`
verb says so once on stderr. Nothing moves by itself.
A root you set (`SESSIONPHONE_ROOT`, `DC_ROOT`, or the one `bot install`
keeps in `phone.json`) is never moved, and this step is not for it.

Moving the root is sessionphone's own verb, `sessionphone bot migrate`,
run once on each Mac. Do not move or delete `~/.sessionphone` by hand: the
verb moves the keys by rename and leaves the old path as a symlink to the
new root. ([moving the root][phone-migrate])

- Check first. A line that starts `sessionphone: using the old root` means
  this Mac still uses `~/.sessionphone`. No such line: there is nothing to
  do.

  ```bash
  sessionphone bot status
  ```

- Stop the bot. `migrate` refuses while a bot runs on the old root or a
  call is live.

  ```bash
  sessionphone bot uninstall
  ```

- Run it dry first. It changes nothing: it says each step it would take,
  and its `account:` line says where the account will open. Read it before
  the real run.

  ```bash
  sessionphone bot migrate --dry-run
  ```

- Move the root:

  ```bash
  sessionphone bot migrate
  ```

  When it refuses (exit 2), nothing was moved: the old root is still where
  it was, with its keys. Once the move is done, the old path is left as a
  symlink to the new root, and nothing deletes it.
- Check the move before you start the bot. It should print no
  `using the old root` line now. If it still does, the move did not
  happen: read what `migrate` said before you go on.

  ```bash
  sessionphone bot status
  ```

- Start the bot on the new path:

  ```bash
  sessionphone bot install
  ```

- Run the check again. It should print no `using the old root` line, and
  its `running:` line should name a pid.

## More

- [Install](../README.md#installation)
- [The manual install, step by step](../INSTALL.md)
- [Known gaps you will hit](../INSTALL.md#7-known-gaps-you-will-hit)

[first-checks]: ../INSTALL.md#4-first-checks
[hear]: ../INSTALL.md#5-hearing-and-speaking-it-hears-me-and-speaks
[pager]: https://github.com/sessionkit/sessionmail#how-pager-listen-works
[phone]: https://github.com/sessionkit/sessionphone#usage
[phone-calls]: https://github.com/sessionkit/sessionphone#call-troubleshooting
[phone-migrate]: https://github.com/sessionkit/sessionphone#moving-the-root-with-bot-migrate
[session-seat]: session.md#the-default-seat
[sv-install]: https://github.com/sessionkit/sessionvoice#install
[sv-logs]: https://github.com/sessionkit/sessionvoice/blob/HEAD/docs/logs.md
[sv-modes]: https://github.com/sessionkit/sessionvoice/blob/HEAD/skills/ears/SKILL.md
[sv-mouth]: https://github.com/sessionkit/sessionvoice/blob/HEAD/docs/troubleshooting.md#mouth-the-voice-chops
[sv-parts]: https://github.com/sessionkit/sessionvoice#components
[sv-req]: https://github.com/sessionkit/sessionvoice#requirements
[tools-migrate]: https://github.com/sessionkit/sessiontools/blob/HEAD/docs/tools-state-migrate.md
[tools-paths]: https://github.com/sessionkit/sessiontools/blob/HEAD/docs/tools-state-paths.md
[voice-move]: #the-voice-state-is-still-in-the-old-root
[voice-root]: https://github.com/sessionkit/sessionvoice/blob/HEAD/docs/configuration.md#the-state-root
