# Uninstall: every line, and what it keeps safe

This is the reference for [INSTALL.md section 8][short]. Section 8 is the short
page: three blocks, one line per package. This page gives every line, why it is
there, what it leaves alone, and what was measured.

- **The order is the install in reverse.** The voice jobs run from the kit's
  files and the phone bot from the plugins' files, so both go before the
  plugins and the kit do.
- **[1. Stop and remove the jobs][jobs]:** the phone bot, the voice jobs, and
  any sessiontools job you turned on. Keeps all your data.
- **[2. Remove the plugins and the tool][tool]:** the plugins, their cached
  copies, the `sessionkit` command, and what the programs left. Keeps all your
  data.
- **[3. Delete your data][data] (opt-in):** one item per kind of data. Skip an
  item to keep it. It cannot be undone.
- **[4. Caches and tools other programs share][caches] (opt-in):** the speech
  weights, uv's cache and Pythons, and Homebrew's tmux, ffmpeg and notmuch.
  Each one only if nothing else uses it.
- **[5. What stays][stays]:** the old logs in `~/Library/Logs` and the old
  folders each package used before its state moved, which an uninstall never
  deletes, and the folders that are not the kit's.

**NOT YET** as a whole: no rehearsal has run this page end to end. A walk of the
longer section 8 that came before it, on a fresh macOS 27 VM, ran every line and
found what it left behind: 2.7 GB of speech weights, 1.4 GB of uv's cache, uv's
Python 3.12, the phone's settings, the agent file setup wrote, Homebrew's tmux and
ffmpeg, and three small folders. Each of those now has a line or a sentence here.
Each step says what was measured. A line new since that walk is **NOT YET** until
a walk measures it.

The lines on this page carry no comments, so paste them as they are. In zsh, the
Mac's own shell, a `#` typed at the prompt is not a comment: the words after it
would go to `rm` as more paths to delete.

## 1. Stop and remove the jobs

**1. Look first.** These only read. The first line shows the plugins, the second the
phone bot, and the third the launchd jobs that the voice and the phone put down, and
any sessiontools job you turned on:

```bash
claude plugin list
sessionphone bot status
launchctl list | grep -E 'dev\.sessionkit\.|sessionvoice|voicemode\.ears|sessionphone|sessiontools'
```

The pattern finds the family's labels, `dev.sessionkit.<package>.<job>`, and
the older forms a Mac may still hold. **NOT YET** as an uninstall check.

**2. Quit every `claude` session.** The pager's monitor and any `ears-arm` waiter
(section 5 step 4) run inside a session and end with it. The steps below run in a
plain terminal. **NOT YET.** In a session with the pager's monitor, `/exit` asks one
more question, because the monitor is background work: answer `Exit and stop tasks`.
**MEASURED** (a fresh macOS 27 VM at 0.2.0: `Background work is running`, then
`1. Exit and stop tasks`).

**3. The phone (section 6).** Step 1's `sessionphone bot status` shows whether there
is a bot.

- No phone set up: skip this step.
- The phone set up: this stops the bot and removes its launchd job. The account
  stays: it is your data ([Phone][phone]). **NOT YET** as a run. Its `--help` says this
  (sessionphone 0.2.1).

  ```bash
  sessionphone bot uninstall
  ```

**4. The voice (section 5).** Do this before step 5. The voice jobs run from the
kit's own sessionvoice package (section 2), and launchd keeps them loaded after its
files are gone.

- **The ride-along hook. HUMAN (hand edit).** In the `.claude/settings.local.json`
  that section 5, step 3 edited, one of these. **NOT YET.**
  - You added other hooks or settings to it: remove the two
    `ears heard hook || exit 1` entries and leave the rest.
  - You pasted the whole file in section 5 and have added nothing since: delete the
    file. Its `.claude` folder is then empty, unless Claude Code or you put something
    else there. This removes it only if it is empty, the folder that holds that
    `.claude` in place of FOLDER:

    ```bash
    rmdir FOLDER/.claude
    ```

    The walk found that folder left behind, empty, in the folder it launched from.
- **Look first with `--dry-run`.** This names each
  job it would boot out and each plist it would delete, and changes nothing:

  ```bash
  ears services uninstall --dry-run
  ```

  **MEASURED** (sessionvoice 0.2.1 with this release's kit, a temporary
  home directory, no jobs installed): it named the jobs under all three forms,
  `speakers` included, printed `dry run: nothing booted out, nothing deleted`, and
  exited 0. A temporary `HOME` does not make a real run safe: `launchctl` acts on
  your own user's jobs whatever `HOME` says. `ears services status` only reads too.
- **The voice jobs.** This is the kit's own `ears`, the one that
  installed them (section 5 step 2):

  ```bash
  ears services uninstall
  ```

  With no `--only` it removes every job it
  knows. 0.3.0 knows its own labels, `dev.sessionkit.voice.*`, and both old
  forms it retires: `com.sessionvoice.*`, and the older `com.voicemode.ears-*`
  that 0.1.0 used (read in its 0.3.0 source); that includes
  `--only speakers`, if you added it. It unlinks the plists only: it deletes no
  log. The
  speech server's venv and the speakers' venv stay until step 6. **NOT YET** as a
  run.
- **Check.** Wait a few seconds before you run it: a job that is still exiting stays in the
  list for a while after the uninstall. This prints nothing once they are gone:

  ```bash
  launchctl list | grep -E 'dev\.sessionkit\.voice\.|sessionvoice|voicemode\.ears'
  ```

  - It printed a line? Wait a few seconds and run it again, until it prints nothing.
- **A job you rendered by hand** from sessionvoice's `launchd/` templates (not on this
  path) has a label of its own. **NOT YET.** Its label goes in place of LABEL:

  ```bash
  launchctl bootout "gui/$(id -u)/LABEL"
  ```

  - Then delete its plist from `~/Library/LaunchAgents/`.
- **What you brought yourself.** The kit did not install a speech server you
  brought yourself (VoiceMode's, for example; section 5 step 1), or any
  postfix setup you made for agent mail
  ([Mail between agents][mail-setup], section 5). Remove them the way
  you installed them; undoing postfix needs sudo. The file drop needs no undoing: it
  is the default, and no setup step wrote a setting for it. If you named postfix in
  mail's settings file, that file goes with [the kit's home][home]. Mail
  setup never touched a notmuch config or database of your own, so there is nothing
  of yours to undo; the profile it wrote goes with [Mail][mail]. **NOT YET.**
  - Set `SESSIONMAIL_SENDMAIL` in `~/.zshenv` for an earlier build? Delete that line.
  - Installed notmuch for mail (section 5)? It is yours: [Homebrew's tools][brew].

**Did you go off the install path?** Each line below names a command you may have run,
and how to undo it now, with its own verb. Step 5 removes the `session` command these
verbs need, and the jobs they turned on run that command, so launchd would keep them
loaded on a missing file. **NOT YET**:

- Ran `session pane-state agent on`? Undo it:

  ```bash
  session pane-state agent off
  ```

- Ran `session sound engine on`? Undo it:

  ```bash
  session sound engine off
  ```

  The engine it built stays in the folder `session path sound` names. On a fresh Mac
  that is `~/.sessionkit/tools/state/sound/bin/`, which
  [Session records][session-records] deletes. On a Mac that built it before that
  folder moved, it is in `~/.local/share/sessiontools/sound/bin/`, an old folder, and
  it stays ([What stays][stays]). `--purge` would delete it there too, so this line
  leaves it out.
- Loaded the default model's agent, `dev.sessionkit.tools.default-model`? It has no
  off verb. These boot it out and delete its plist (read in sessiontools' README):

  ```bash
  launchctl bootout "gui/$(id -u)/dev.sessionkit.tools.default-model"
  rm -f "${HOME:?}/Library/LaunchAgents/dev.sessionkit.tools.default-model.plist"
  ```

- These jobs log to `~/.sessionkit/tools/log/`, which goes with
  [the kit's home][home]. An older release logged to `~/Library/Logs/sessiontools/`:
  that folder stays ([What stays][stays]).
- Ran `message seat agent --install`? Undo it, with the address you gave it in place
  of ADDRESS. It unloads the job and removes its plist (read in sessionmail's
  docs/message-seat.md):

  ```bash
  message seat agent --uninstall ADDRESS
  ```

  Its log, `~/Library/Logs/seat-agent.ADDRESS.log`, stays ([What stays][stays]).
- Ran `ears services install --apple`? Step 4's uninstall covers it.
- `session statusline install`: no verb removes it yet. It wrote two files in
  `~/.sessionkit/tools/settings/`: `statusline.sh` and
  `claude-code.d/50-statusline.json`. It also left a `.bak-<date>-<time>` copy beside
  each file it replaced. That copy is the file you had before, so move it back if you
  want it. Nothing runs these files once step 5 removes `session`. They are settings,
  so [the kit's home][home] deletes them, with the copies. It leaves
  `claude-code.json` alone: it is yours.

## 2. Remove the plugins and the tool

**5. The plugins and the kit command (sections 3 and 2).** After step 4, with no
`claude` session running, remove the kit command and the plugins. Neither needs the
other, so either order works. The plugins' lines depend on how section 3 installed
them: from the kit's marketplace, or from your own clones. Run the lines for your
route, and both sets if you used both.

- The kit command:

  ```bash
  uv tool uninstall sessionkit
  ```

- From the kit's marketplace (section 3's first lines). This removes its six plugins
  too:

  ```bash
  claude plugin marketplace remove sessionkit
  ```

- From your own clones (section 3's
  [From your own clones][clones-route]).
  This removes each of the five marketplaces, and its plugin too:

  ```bash
  for r in sessionmail sessiontools sessionphone sessionvoice sessionview; do
    claude plugin marketplace remove "$r"
  done
  ```

**The plugins' copies stay.** Removing a marketplace does not delete the copies Claude
Code made in its plugin cache at install (section 3): from the kit's marketplace, the
copies its plugins ran from; from your own clones, the
copies it wrote even though each plugin ran in place, from its clone. Delete them by hand.

From the kit's marketplace, all six copies are in one folder,
`~/.claude/plugins/cache/sessionkit/`:

```bash
rm -rf "${HOME:?}/.claude/plugins/cache/sessionkit"
claude plugin list
```

**MEASURED** (Claude Code 2.1.307, the kit's marketplace at 0.2.1, on a
temporary home directory and Claude Code config directory): after section 3's two
lines, `claude plugin marketplace remove sessionkit` exited 0, printed `Also
uninstalled 6 plugins from this marketplace`, and removed the marketplace's own clone
in `~/.claude/plugins/marketplaces/`. `claude plugin list` then printed `No plugins
installed.` **The six copies stayed** in `~/.claude/plugins/cache/sessionkit/`, each
`<name>/<version>/` folder marked `.orphaned_at`, 28 MB in all. These two lines then
ran: the `rm` exited 0 and left `~/.claude/plugins/cache/` empty, and `claude plugin
list` still printed `No plugins installed.`

From your own clones, each plugin's copy is in a folder of its own,
`~/.claude/plugins/cache/<r>/`:

```bash
for r in sessionmail sessiontools sessionphone sessionvoice sessionview; do
  rm -rf "${HOME:?}/.claude/plugins/cache/${r:?}"
done
claude plugin list
```

**MEASURED** (Claude Code 2.1.301, one plugin, on a temporary home
directory and Claude Code config directory): `claude plugin marketplace remove`
uninstalled its plugin too (`Also uninstalled 1 plugin from this marketplace`), and
`claude plugin list` then printed `No plugins installed.` **The plugin's cached copy
stayed.** `~/.claude/plugins/cache/<r>/` was still there, marked `.orphaned_at`. This
loop removes the five copies now. **NOT YET**: the loop has not run.

- `claude plugin list` still shows one of them? Remove it by the name the list shows,
  in place of PLUGIN: `<name>@sessionkit` from the kit's marketplace, with
  `sessionkit@sessionkit` among them, and `<r>@<r>` from a clone.

  ```bash
  claude plugin uninstall PLUGIN
  ```

**MEASURED**
(uv 0.13.0, this release's kit with the five 0.2.0 packages from PyPI, on
temporary uv tool directories): `uv tool uninstall
sessionkit` printed `Uninstalled 14 executables` and removed the kit's tool environment.
Four of those are sessionview's commands, linked in `~/.local/bin` to the kit's tool
environment in uv's tool folder, `~/.local/share/uv/tools/sessionkit/`: that line
removes those links.

- **sessionview's own links and app**, only if you ran its `sessionview-install` or
  `sessionview-app-install` from a sessionview checkout (not on this path).
  `sessionview-install` linked sessionview's tools into `~/.local/bin`, and
  `sessionview-app-install` put an app in `~/Applications`. No verb reverses either.
  This lists the links to delete. It leaves out every link into uv's tool folder, so
  run before or after the kit command, it never lists the kit's own four:

  ```bash
  find ~/.local/bin -type l -lname '*sessionview*' -not -lname '*/uv/tools/*'
  ```

  **MEASURED** (a scratch folder holding the kit's four links into a
  `.local/share/uv/tools/sessionkit/bin/` and five links into a checkout's `bin/`):
  it printed the five, and none of the four. On the walk's fresh Mac, the older form
  of this line, without its `-not -lname` part, printed uv's four.

**6. What the programs left (PROGRAM: none of it is your data).** No verb removes these
yet, so they are hand `rm` lines. **NOT YET.** In order, they delete what the voice keeps
in its cache folder (its models, the keeper's run state and its helper programs), the
speech server's venv (which step 4 keeps), the speakers' venv, the music separator, the
cache the `memory` command keeps, and the image reader's empty cache folder. Each
`rmdir` line removes a folder only if it is empty.

```bash
find "${HOME:?}/.cache/ears" -mindepth 1 -not -name 'ears-mail.state.json*' -delete
rmdir "${HOME:?}/.cache/ears"
rm -rf "${HOME:?}/.local/share/ears/speech"
rm -rf "${HOME:?}/.local/share/ears/speakers/venv"
rm -rf "${HOME:?}/.local/share/ears/separator"
rmdir "${HOME:?}/.local/share/ears/speakers"
rmdir "${HOME:?}/.local/share/ears"
rm -rf "${HOME:?}/.cache/session-mail"
rm -rf "${HOME:?}"/Library/Caches/imgtext-*
```

`~/.cache/ears/silero_vad.onnx` may be a link to VoiceMode's copy of the model. If it
is, the first line removes the link, not VoiceMode's file.

**The voice's old places stay.** Two of these folders can also hold the voice's state
from before it moved into [its state folder][voice], and the lines leave it there: the
turn mail's place in the transcript, `~/.cache/ears/ears-mail.state.json`, and the
voices you enrolled, in `~/.local/share/ears/speakers`. If an `rmdir` says
`Directory not empty`, that folder holds one of them: leave it. If one says
`No such file or directory`, there was nothing there: the speakers' venv and the
separator are there only if you installed them. The other old places these lines once
deleted stay too: the call listeners' run state in `~/.local/state/ears`, the voice's
list of audio devices in `~/.local/state/audio/devices.json`, and the sidebar's old
state and log in `~/.local/state/sessionview` ([What stays][stays]).

The phone bot reads the text on an image you send it with the Mac's own Vision, from
a small program it builds, `imgtext-<hash>`. macOS makes a cache folder named for that
program, `~/Library/Caches/imgtext-<hash>`; the walk found it empty. In zsh, the
Mac's own shell, the `imgtext-*` line prints `no matches found` when there is none:
that is fine.

## 3. Delete your data (USER DATA, opt-in)

**Only if you want it gone. This cannot be undone.** Steps 1 to 6 kept all of it. Each
item below deletes one kind of data: skip an item to keep that data, and copy anything
you want first. No child ships a verb for any of it yet. **NOT YET**: none of these
lines has run end to end on a fresh Mac. Run the items in this order: Session records
and Accounts come before the kit's home, so that item's `rmdir` lines can empty the
folder.

### Mail

Every agent's mailbox, the notmuch index of them, and the mouth's queue of
spoken lines. Where they are is sessionmail's to say: while it is installed (0.3.3 or
later), `message path --root` prints the mail root and `message path --boxes` the
folder of boxes in it. Section 2 removed it, and the lines on this page delete on no
name you set, only under your home by their own names, so these name the tree
sessionmail makes by default: `~/.sessionkit/mail`, its boxes in `stores/`. If your
shell sets `SESSIONMAIL_ROOT`, or a `root` line in
`~/.sessionkit/mail/settings/mail.json` names another folder, the mail is there
instead. Nothing in the kit sets either, so if one is set, you set it, and these lines
do not touch that folder: look in it first, then delete the boxes there by hand.
(`SESSION_MAIL_ROOT` and `MAIL_ROOT`, the old names, are read by nothing.)

**The old mail tree stays.** A Mac that had mail before sessionmail 0.3.3 keeps it in
`~/.mail`, by `"root": "~/.mail"` in that file or by a symlink from
`~/.sessionkit/mail` to it. `~/.mail` is an old folder, and an uninstall never deletes
one ([What stays][stays]). It still holds what it held: `agents/`, every agent's box
from then, the mouth's among them; `.notmuch`, their notmuch index; and on a Mac where
postfix delivers, sessionmail's own `.postfix` and `.state`. The old notmuch profile,
`~/.config/notmuch/sessionkit/config`, stays too: sessionmail's notmuch settings from
before 0.3.3, with that tree as their database.

Mail setup's notmuch profile (section 5, step 3) is
`~/.sessionkit/mail/settings/notmuch/sessionkit/config` (`message path
--notmuch-config`), under the kit's settings, so it goes with [the kit's home][home].
Your own `~/.notmuch-config` is not touched.

The mouth's queue is one of those boxes, `mouth` (`message path mouth`), and
VoiceMode uses it too: sessionvoice's mouth and VoiceMode's both queue their lines in that one box,
and both keep every line there once it is done. So the first line deletes every box
but that one.

```bash
find "${HOME:?}/.sessionkit/mail/stores" -mindepth 1 -not -path "${HOME:?}/.sessionkit/mail/stores/mouth" -not -path "${HOME:?}/.sessionkit/mail/stores/mouth/*" -delete
```

On a Mac with only the old tree, it says `No such file or directory`.

The mouth's box:

- You use VoiceMode: keep it. VoiceMode's mouth speaks from it, and the lines below
  would delete its queue. The lines sessionvoice's mouth spoke then stay in that box,
  beside VoiceMode's, until you delete it.
- No VoiceMode: the mouth's box is the kit's alone. Delete it:

  ```bash
  rm -rf "${HOME:?}/.sessionkit/mail/stores/mouth"
  rmdir "${HOME:?}/.sessionkit/mail/stores"
  ```

If your shell sets `MOUTH_MAILBOX` or `VOICEMODE_MOUTH_MAILBOX`, the mouth queues in
the folder it names instead. If it sets `MOUTH_DIR` or `VOICEMODE_MOUTH_DIR` to
another folder, the mouth queues in a `box` folder inside it. Nothing in the kit sets
any of them, so if one is set, you set it, and these lines miss that box: look in it,
and delete it by hand only if you do not use VoiceMode.

The profile's index is `.notmuch` in the mail root. Delete it only if mail setup
made the profile for it. Mail setup's first run said which, on its `notmuch-profile` line:

- It said `MANUAL`: the database was in the mail folder before the kit. It is yours,
  so leave it.
- You cannot tell: leave it.
- `~/.sessionkit/mail` is a symlink to `~/.mail`: leave it. The index behind the link
  is the old tree's, and it stays.
- It said `wrote`: mail setup then ran `notmuch new` once on that profile, so the
  index is the kit's. Delete it:

  ```bash
  rm -rf "${HOME:?}/.sessionkit/mail/.notmuch"
  ```

  The mail root, `~/.sessionkit/mail`, then goes with [the kit's home][home], which
  removes it once its `settings/` folder is gone. Its `rmdir` prints
  `Directory not empty`, and the folder stays, if you kept the mouth's box.
  sessionmail's own `.postfix` and `.state`, beside the boxes on a Mac where postfix
  delivers (section 1), stay: leave them.

### Session records

What each session read, its address, its logs (mail's among them), the session
list's saved state, each agent's home, and the agents folder.

The `session` tool keeps these in its state folder, `~/.sessionkit/tools/state`.
`session path --json` names each folder in it: `sessions`, `seats`, `agent` (the
agents folder, `agent/config`, and each agent's home), `backups` and `sound` (the
busy sound's engine). The session list's saved state sits in the state folder itself.
`sessionkit setup` (section 2) wrote one agent file, `NAME.md` for the agent you named
(`claude.md` by default), in the agents folder `session start` reads: the one
`session path agent --config` names. On a fresh Mac that folder is
`~/.sessionkit/tools/state/agent/config`. The line deletes the whole state folder, the
agent files in `agent/config` with it, so copy any you want first. Everything in it is
the `session` tool's, so [the kit's home][home] can then remove `tools` and
`~/.sessionkit`.

```bash
rm -rf "${HOME:?}/.sessionkit/tools/state"
```

**The old folders stay.** An uninstall never deletes an old folder, so this page
leaves each of these alone. On a Mac that had them before the state moved, the
programs kept using them, and they still hold what they held:

- **`~/.session`:** the `session` tool's records on a Mac that ran it before its
  state moved: the sessions, seats, agent files and backups, the session list's
  state (or, once `session path migrate` ran, a link where `~/.session/state` was),
  and the older agents folder, `~/.session/agents`, where an earlier sessionkit wrote
  its agent file.
- **`~/.local/share/sessiontools/sound`:** the busy sound's engine, on a Mac that
  built it before that folder moved, or the link `session path migrate` left there.
- **`~/.sessionmail`:** mail's own folder before its state moved into
  `~/.sessionkit/mail/state`. On a Mac that had it, it holds each seat's settings and
  the seats' signing keys (`seat-keys`), the mail rules and the puller's state.

To see which of them this Mac has (each one it does not have prints
`No such file or directory`):

```bash
ls -d "${HOME:?}/.session" "${HOME:?}/.local/share/sessiontools" "${HOME:?}/.sessionmail"
```

### Accounts

The `session` tool's account folder, `~/.sessionkit/tools/accounts/`,
beside its settings folder. It holds the account registry (`accounts.json`: each
account's name, its email and where its token is kept, never the token), the account
config (`account-config.json`), the host ledger (`host-ledger.jsonl`), and the backups
`session account use` made of each token it replaced (`token-file-backups/` and
`keychain-backups/`). While `session account new` sets up a token, a scratch folder sits
there too. **The backups are your account tokens.** Steps 1 to 6 leave this folder, and
so does [the kit's home][home] below, so the uninstall leaves these tokens on disk until
you run this line. It deletes the saved accounts and every token backup, and it cannot
be undone: to keep your accounts, skip it. It does not touch the tokens where you keep
them (the registry's sources: a file, `pass` or `passage`), or the Keychain item or
token file you sign in from: those are yours. The folder is there only if you used
`session account`.

```bash
rm -rf "${HOME:?}/.sessionkit/tools/accounts"
```

**The old account folder stays.** On a host that used `session account` before the
account folder moved, the older account folder, `~/.config/sessiontools/`, may still be
there, with the same kinds of files in it. **Its backups are your account tokens
too.** The `session` tool never reads or writes it now, and an uninstall never deletes
an old folder, so this page leaves it alone, with the rest of `~/.config`.

### The kit's home

`~/.sessionkit`, one folder per package. In each, `settings/` holds your choices,
`log/` the package's logs, and `state/` what it keeps between runs (the tree
specification, `openspec/specs/tree/spec.md`). This item deletes those three folders
for mail, voice, the sidebar (`view`) and the phone. That is the operator file that
`sessionkit setup` wrote (section 2), the mail hooks switch, your voice choices, the
seats your voice wakes, the voice's state ([Voice][voice]),
the sidebar's config and state, the phone's `phone.json`, its chat account and keys
([Phone][phone]), and every package's logs. The voice keeps the speech keys you may
have saved, `stt.key` and `tts.key`, in `~/.sessionkit/voice/settings/` itself, so
this item deletes them with your voice choices.

The `session` tool's folder, `tools`, is not deleted whole. The account folder beside
its settings is the item above. Its settings folder holds a file the kit never writes,
`claude-code.json`: `session start` reads it, but nothing in the kit writes it, so
anything in it is yours. So the lines for `tools` delete its logs, then only the
`session` and `sounds` files in `~/.sessionkit/tools/settings`, the hidden schema
copies (`.session.schema.json`, `.sounds.schema.json`) included. The next two lines
remove what `session statusline install` wrote there, if you ran it:
`statusline.sh`, `claude-code.d/50-statusline.json`, and the `.bak-` copies of the
files it replaced. All of these leave `claude-code.json` there alone.

The `rmdir` lines remove a folder only if it is empty. If one says
`Directory not empty`, that folder still holds files the kit did not write, the
account folder you kept, or the `session` tool's state folder if you skipped
[Session records][session-records]: leave them. For `mail` it can also be sessionmail's
own `.postfix` and `.state`, which the Mail item above leaves in the root: leave them,
and the folder with them. On a Mac that keeps its mail at `~/.mail` by a symlink
(`~/.sessionkit/mail -> ~/.mail`), that `rmdir` says `Not a directory`: the link is
yours, and `~/.mail` behind it is the old tree the Mail item leaves, so remove the
link alone, with `rm "${HOME:?}/.sessionkit/mail"` (no `-r`, no trailing slash), or
keep it.
If one says `No such file or directory`, there
was nothing there to remove: voice saves no settings until section 5, the phone none
until section 6, and `claude-code.d` is there only if you ran
`session statusline install`.

```bash
for d in mail voice view phone; do rm -rf "${HOME:?}/.sessionkit/${d:?}/settings" "${HOME:?}/.sessionkit/${d:?}/log" "${HOME:?}/.sessionkit/${d:?}/state"; done
rm -rf "${HOME:?}/.sessionkit/tools/log"
for f in session.json session.d session.template.json session.schema.json .session.schema.json; do rm -rf "${HOME:?}/.sessionkit/tools/settings/${f:?}"; done
for f in sounds.json sounds.d sounds.template.json sounds.schema.json .sounds.schema.json; do rm -rf "${HOME:?}/.sessionkit/tools/settings/${f:?}"; done
rm -f "${HOME:?}/.sessionkit/tools/settings/statusline.sh" "${HOME:?}/.sessionkit/tools/settings/claude-code.d/50-statusline.json"
find "${HOME:?}/.sessionkit/tools/settings" -maxdepth 2 \( -name 'statusline.sh.bak-*' -o -name '50-statusline.json.bak-*' \) -print -delete
rmdir "${HOME:?}/.sessionkit/tools/settings/claude-code.d"
rmdir "${HOME:?}/.sessionkit/tools/settings"
for d in mail voice view phone tools; do rmdir "${HOME:?}/.sessionkit/${d:?}"; done
rmdir "${HOME:?}/.sessionkit"
```

The logs here are the new ones. A Mac that ran an earlier release keeps its older logs
in `~/Library/Logs`, and nothing on this page deletes from there ([What stays][stays]).

### Voice

What the ears heard and the mouth said. That is the transcript of every
turn the ears heard (`heard_*.jsonl`), who spoke each turn (`speakers_*.jsonl`), each
session's place in that transcript, the voice's pairing token (`talk/token`), and
every line the mouth spoke, which it keeps by default. If you turned recording on (it
is off by default), it is also the audio the ears kept of each turn and the clips of
replies they missed. Then the voices you enrolled. The services' logs are in
`~/.sessionkit/voice/log/`, and go with [the kit's home][home].

On a fresh Mac all of it is in the voice's state folder, `~/.sessionkit/voice/state`
(`ears home state-dir` prints it): the transcript, the mouth's folder, the pairing
token, the voices you enrolled (`speakers`), and the place `ears-arm` (section 5 step
4) keeps in the transcript for a seat with no home of its own (`seats`). That folder
is the voice's `state`, so [the kit's home][home] deletes it, with your voice choices
and its logs. This item has no line of its own.

**The old places stay.** A Mac whose voice kept its state before the move keeps using
it there, until `ears home migrate` moves it ([the step][voice-move]). An uninstall
never deletes an old place, so this page leaves each of these alone:

- **`~/.sessionvoice`:** the voice's own folder before the move, with everything
  above in it.
- **`~/.voicemode`:** the transcript and the voice's other files, on a Mac where an
  older sessionvoice, or VoiceMode's `converse`, wrote the transcript there first.
  VoiceMode keeps its own files there too.
- **`~/.ears`:** the place `ears-arm` kept in the transcript for the seats with no
  home of their own, on a Mac that had it. Nothing moves it.
- **The old places of the voice's state items:** the call listeners' run state in
  `~/.local/state/ears`, the list of audio devices in
  `~/.local/state/audio/devices.json`, the voices you enrolled in
  `~/.local/share/ears/speakers`, and the turn mail's place in
  `~/.cache/ears/ears-mail.state.json`.
- **After `ears home migrate`:** each old place is a link to its new place, and the
  original sits beside it as `<path>.pre-sessionkit`. Both stay.

To see whether this Mac still uses an old place: a second `state` row in this check
names each one.

```bash
ears services status
```

If your shell sets `SESSIONVOICE_HOME`, or VoiceMode's `VOICEMODE_BASE_DIR`,
sessionvoice keeps these files in the folder it names instead. Nothing in the kit
sets either, so if one is set, you set it, and this page does not touch that folder.

If a folder named for your agent was already in your home directory, `~/.<name>`,
`ears-arm` kept its place there as `heard.state`. Delete that one file by hand, never
the folder: `~/.claude`, for one, is Claude Code's. If your shell sets `EARS_HOME`,
`ears-arm` kept its `heard.state` in the folder it names instead. Delete that one file
there by hand too.

### Phone

The agent's chat account with its keys, the invite, the callers, and the bot's own
files. Run step 3 first. On a fresh Mac they are in the phone's state folder,
`~/.sessionkit/phone/state`. The bot's logs are in `~/.sessionkit/phone/log/`. Both go
with [the kit's home][home]: this item has no line of its own. The account on the
public relay is not on this Mac, and nothing here deletes it. On your phone, delete the
agent's chat in Delta Chat yourself.

**The old root stays.** Before 0.3.2 the phone's root was `~/.sessionphone`. A Mac
that has only the old one keeps using it, until `sessionphone bot migrate` moves it
and leaves the old path as a link to the new root
([the step][phone-move]). An uninstall
never deletes an old root, so this page leaves `~/.sessionphone` alone. On a Mac that
never moved it, it still holds the agent's Delta Chat account and its keys, and the
bot's older logs.

### Your clones

Section 3's clones, only after step 5: a plugin breaks when its clone goes
(section 7). Look first for changes of your own. This prints each clone's changed
files, and nothing for a clean one:

```bash
for r in sessionmail sessiontools sessionphone sessionvoice sessionview; do
  git -C "${HOME:?}/.local/share/sessionkit/src/${r:?}" status --short
done
```

The block below deletes the folder section 3 clones into,
`~/.local/share/sessionkit/src`, by its full name:

```bash
rm -rf "${HOME:?}/.local/share/sessionkit/src"
rmdir "${HOME:?}/.local/share/sessionkit"
```

The last line removes `~/.local/share/sessionkit` only if it is empty.

- Cloned somewhere else? These lines miss those clones: delete them there by hand,
  one at a time.

## 4. Caches and tools other programs share (opt-in)

Each of these is shared: another program may use it, and the kit cannot tell. Each
item says how to keep it and how to remove it. **NOT YET**: no walk has run these
lines.

### The speech weights, about 2.7 GB

The speech server fetched them on its first request (section 1) into the Hugging Face
cache, which other tools share. The kit's server sets no cache variable, so they are
in `~/.cache/huggingface/hub` (read in sessionvoice's docs/models.md). They come from
three repositories there: the ears' Parakeet,
`models--mlx-community--parakeet-tdt-0.6b-v3`; the mouth's Kokoro,
`models--mlx-community--Kokoro-82M-bf16`; and Kokoro's voices, which come from a third
repository, `models--prince-canuma--Kokoro-82M`. Another tool can use them too:
VoiceMode's speech server does.

Deleting those three folders is not enough. In the cache's shared layout each folder
holds only links (`models--NAME/blobs/<sha>` points to `../../blobs/<xx>/<sha256>`),
and the weights themselves sit in the cache's own `blobs` folder. The walk deleted the
three folders and found the 2.7 GB still there.

- Another tool uses them: leave them.
- Nothing else uses them? These lines follow each link in the three folders to the
  file it names in the cache's `blobs` folder, delete that file, then delete the
  folder. They delete nothing a link in another folder alone points to, and the last
  line removes only empty folders left in `blobs`:

  ```bash
  hub=$(realpath "${HOME:?}/.cache/huggingface/hub")
  for m in mlx-community--parakeet-tdt-0.6b-v3 mlx-community--Kokoro-82M-bf16 prince-canuma--Kokoro-82M; do
    find "${hub:?}/models--${m:?}" -type l -exec realpath {} + | grep "^${hub:?}/blobs/" | while read -r b; do rm -f "${b:?}"; done
    rm -rf "${hub:?}/models--${m:?}"
  done
  find "${hub:?}/blobs" -mindepth 1 -type d -empty -delete
  ```

  If another model holds the very same file, its link to it breaks too: that is the
  "another tool uses them" case above. A folder that is not there prints
  `No such file or directory`: that is fine.

Never delete the cache whole. **MEASURED** on a scratch tree only (bash and zsh, a
temporary home directory): the three folders, each with links in that shared layout
and one blob shared between the two Kokoro folders, beside another model's folder
in the same layout and one in the older layout, whose files sit in its own folder.
The lines deleted the three folders and their five blob files, and left the other two
models whole. **NOT YET** on a real cache.

### uv's cache, about 1.4 GB

uv keeps every package it downloaded, the kit's and every other tool's, in one cache,
`~/.cache/uv`. The uninstall leaves it, and step 5 does not shrink it: removing a tool
leaves its packages in the cache.

- Other uv tools or projects on this Mac: leave it. `uv cache prune` does not free the
  kit's packages. It removes only entries that nothing else in the cache points to, and
  after step 5 the kit's packages are still pointed to.
- Nothing else of yours uses uv: this empties the cache:

  ```bash
  uv cache clean
  ```

**MEASURED** on a scratch cache only (uv 0.13.5, a temporary home directory, uv cache and
tool folder): after `uv tool uninstall`, `uv cache prune` printed `No unused entries
found`, and the tool's packages stayed in the cache. **NOT YET** on a real cache.

### uv's Pythons

The speech server's venv and the speakers' venv run on uv's Python 3.12: sessionvoice
builds them with `uv venv --python 3.12` (read in its source), about 72 MB. The kit
itself runs on uv's Python 3.14 (section 2). Both are uv's, and other tools may use
them.

- Nothing else needs uv's Python 3.12? Remove it:

  ```bash
  uv python uninstall 3.12
  ```

- Nothing else needs uv's Python 3.14? Remove it:

  ```bash
  uv python uninstall 3.14
  ```

### Homebrew's tools

Sections 1 and 5 install tmux, ffmpeg (a call needs it), notmuch for mail, and jq if
your Mac had none. Each is Homebrew's, and other tools may use it.

- Nothing else uses tmux? Remove it:

  ```bash
  brew uninstall tmux
  ```

- Nothing else uses ffmpeg? Remove it:

  ```bash
  brew uninstall ffmpeg
  ```

- Nothing else uses notmuch? Remove it:

  ```bash
  brew uninstall notmuch
  ```

- Installed jq in section 5, and nothing else uses it? Remove it:

  ```bash
  brew uninstall jq
  ```

- Then the libraries they brought, and nothing else still needs. Look first, then
  remove them:

  ```bash
  brew autoremove --dry-run
  brew autoremove
  ```

## 5. What stays

- **Old logs in `~/Library/Logs`.** An uninstall never deletes from there. The kit's
  packages now log to `~/.sessionkit/<package>/log/`. A Mac that ran an earlier
  release still has their older logs, in `~/Library/Logs/ears/`,
  `~/Library/Logs/sessiontools/`, and some of the voice's in an older log folder
  from before the kit, which other programs may write to too. A mail seat
  agent still logs there today, to `~/Library/Logs/seat-agent.ADDRESS.log`. Those
  stay.
- **The old folders from before each package's state moved.** An uninstall never
  deletes one: [Session records][session-records] names `~/.session`,
  `~/.local/share/sessiontools/sound` and `~/.sessionmail`; [Accounts][accounts]
  names `~/.config/sessiontools`; [Voice][voice] names
  `~/.sessionvoice`, the voice's files in `~/.voicemode`, `~/.ears` and the old places
  of its state items; [Phone][phone] names `~/.sessionphone`; [Mail][mail] names
  `~/.mail` and `~/.config/notmuch/sessionkit`. The sidebar's old state
  folder, `~/.local/state/sessionview` (or its older name, `~/.local/state/herd`),
  stays too, with its old state and log in it. A folder a `migrate` verb moved is now a link to
  its new place, and the voice's originals sit beside theirs as
  `<path>.pre-sessionkit`: those stay as well.
- **What is not the kit's.** Homebrew, uv and Claude Code (sections 1 and 2) are not
  the kit's, and other tools may use them. So are Claude Code's own folders, such as
  `~/.claude` and `~/.local/state/claude`: leave them. Never delete `~/.local/bin`,
  `~/.cache`, `~/.sessionkit` or `~/.voicemode` whole: other tools keep files there.
- **`~/Library/LaunchAgents`.** macOS's own folder for every user job, the kit's and
  any other program's. On a fresh Mac the kit's jobs made it, and the uninstall can
  leave it empty. Leave it.

[short]: ../INSTALL.md#8-uninstall
[jobs]: #1-stop-and-remove-the-jobs
[tool]: #2-remove-the-plugins-and-the-tool
[data]: #3-delete-your-data-user-data-opt-in
[caches]: #4-caches-and-tools-other-programs-share-opt-in
[stays]: #5-what-stays
[phone]: #phone
[voice]: #voice
[home]: #the-kits-home
[mail]: #mail
[session-records]: #session-records
[accounts]: #accounts
[voice-move]: troubleshooting.md#the-voice-state-is-still-in-the-old-root
[phone-move]: troubleshooting.md#the-phone-bot-still-uses-the-old-root
[brew]: #homebrews-tools
[clones-route]: ../INSTALL.md#from-your-own-clones-to-work-on-the-plugins-optional
[mail-setup]: ../INSTALL.md#mail-between-agents
