# Troubleshooting

A hub, not a manual: one line per symptom, a check you can paste, and a
link to the package doc that explains it. Paths are the defaults; your
environment variables move them (`EARS_LOG_DIR` moves the ears logs).

## The files to tail

Voice flows ears → heard log → turn mail → pager → your agent → mouth.
The usual answer is three files. Measured, there are four, and the
third is there only if turn mail runs:

1. **The heard log**:
   `~/.voicemode/logs/conversations/heard_YYYY-MM-DD.jsonl`. What the ears
   heard (`partial`, `turn`), what the mouth said (`saying`, `said`), and
   a `heartbeat` every 15 seconds while a capture runs. Every line has a
   `seq`, which links it to the turn mail.
   (the capture: [sessionvoice's README, Components][sv-parts]; every log
   line: [sessionvoice's docs/logs.md][sv-logs])
2. **The ears logs**: `~/Library/Logs/ears/ears-*.log`, one for each
   launch agent (`ears-keeper.log`, `ears-mouth.log`). The 0.1.0 keeper
   writes its capture and call logs (`ears-keeper-capture.log`,
   `ears-keeper-calls.log`) to a second folder under `~/Library/Logs/`,
   so the line below uses `*` for the folder. Crashes land here: a
   capture that keeps dying, a device that went away.
   (the keeper: [sessionvoice's README, Components][sv-parts]; every log
   file: [sessionvoice's docs/logs.md][sv-logs])
3. **The turn mail log**: `ears-mail.log`, beside the ears logs, so the
   same `*` catches it. One JSON line per heard turn it mailed: the
   `seq`, the box it went to, the subject and the Message-ID. **A kit
   install has no turn mail**: `ears services install` does not install
   it ([manual install, section 5][hear]). There, this file is missing,
   and the waiter wakes your agent instead.
4. **The pager's verdicts**:
   `~/.session/sessions/<session-id>/mail/verdicts`. One JSON line per
   mail the pager judged for that agent: `wake` or `ride`, and the rule
   that decided it. The file appears with the first mail judged.
   ([how the pager works][pager])

Paste this:

```bash
tail -F ~/.voicemode/logs/conversations/heard_$(date +%F).jsonl \
  ~/Library/Logs/*/ears-*.log \
  "$(ls -t ~/.session/sessions/*/mail/verdicts | head -1)"
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
  grep -ho 'whisper at[^"]*' ~/Library/Logs/*/ears-*.log \
    ~/.voicemode/logs/conversations/heard_$(date +%F).jsonl | tail -3
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
    ~/.voicemode/logs/conversations/heard_$(date +%F).jsonl | tail -3
  ```

- **No turn mail:** `tail -3 ~/Library/Logs/*/ears-mail.log`. No such
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
log, `bot.log`, says where each turn was mailed, whether anyone
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
  `tail ~/Library/Logs/*/ears-keeper-calls.log`.

  ```bash
  grep '"source": "call"' \
    ~/.voicemode/logs/conversations/heard_$(date +%F).jsonl |
    grep -c '"kind": "turn"'
  ```

### The voice chops

The agent's speech stutters or cuts out as it plays. The mouth's own
troubleshooting has the causes and the checks: see
the voice chops, in
[sessionvoice's docs/troubleshooting.md][sv-mouth].

## More

- [Install](../README.md#installation)
- [The manual install, step by step](../INSTALL.md)
- [Known gaps you will hit](../INSTALL.md#7-known-gaps-you-will-hit)

[hear]: ../INSTALL.md#5-hearing-and-speaking-it-hears-me-and-speaks
[pager]: https://github.com/sessionkit/sessionmail#how-pager-listen-works
[phone]: https://github.com/sessionkit/sessionphone#usage
[phone-calls]: https://github.com/sessionkit/sessionphone#call-troubleshooting
[sv-install]: https://github.com/sessionkit/sessionvoice#install
[sv-logs]: https://github.com/sessionkit/sessionvoice/blob/HEAD/docs/logs.md
[sv-modes]: https://github.com/sessionkit/sessionvoice/blob/HEAD/skills/ears/SKILL.md
[sv-mouth]: https://github.com/sessionkit/sessionvoice/blob/HEAD/docs/troubleshooting.md#mouth-the-voice-chops
[sv-parts]: https://github.com/sessionkit/sessionvoice#components
[sv-req]: https://github.com/sessionkit/sessionvoice#requirements
