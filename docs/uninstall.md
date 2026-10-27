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
- **[5. What stays][stays]:** the old logs in `~/Library/Logs`, which an
  uninstall never deletes, and the folders that are not the kit's.

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
  speech server's venv and the speakers' home, `~/.local/share/ears/speakers`,
  stay until step 6 and [Voice][voice]. **NOT YET** as a run.
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
  session sound engine off --purge
  ```

  Without
  `--purge` the engine it built stays in `~/.local/share/sessiontools/sound/bin/`.
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
yet, so they are hand `rm` lines. **NOT YET.** In order, they delete the voice model and
the keeper's run state, the speech server's venv (which step 4 keeps), the sidebar's
old state folder under its name and under its older one, the call listeners' run state,
the cache the `memory` command keeps, the image reader's empty cache folder, and the
voice's list of audio devices. The last line removes that list's folder only if it is
empty.

```bash
rm -rf "${HOME:?}/.cache/ears"
rm -rf "${HOME:?}/.local/share/ears/speech"
rm -rf "${HOME:?}/.local/state/sessionview"
rm -rf "${HOME:?}/.local/state/herd"
rm -rf "${HOME:?}/.local/state/ears"
rm -rf "${HOME:?}/.cache/session-mail"
rm -rf "${HOME:?}"/Library/Caches/imgtext-*
rm -f "${HOME:?}/.local/state/audio/devices.json"
rmdir "${HOME:?}/.local/state/audio"
```

The voice keeps a list of the Mac's audio devices in `~/.local/state/audio/devices.json`.
Other tools may read and write that file too, and the folder's name is not the kit's
own, so these lines delete only that file. The folder goes only if nothing else is in
it: if `rmdir` says `Directory not empty`, leave it.

`~/.cache/ears/silero_vad.onnx` may be a link to VoiceMode's copy of the model. If it
is, the first line removes the link, not VoiceMode's file.

The sidebar keeps its state in the kit's home now, `~/.sessionkit/view/state`, which
goes with [the kit's home][home]. Its older folder, `~/.local/state/sessionview`, is
there only on a Mac that ran an earlier release: an upgrade left it in place, with the
old log in it. The `herd` line finds that folder's older name, only if a move from it
never ran.

The phone bot reads the text on an image you send it with the Mac's own Vision, from
a small program it builds, `imgtext-<hash>`. macOS makes a cache folder named for that
program, `~/Library/Caches/imgtext-<hash>`; the walk found it empty. In zsh, the
Mac's own shell, the `imgtext-*` line prints `no matches found` when there is none:
that is fine.

## 3. Delete your data (USER DATA, opt-in)

**Only if you want it gone. This cannot be undone.** Steps 1 to 6 kept all of it. Each
item below deletes one kind of data: skip an item to keep that data, and copy anything
you want first. No child ships a verb for any of it yet. **NOT YET**: none of these
lines has run end to end on a fresh Mac. Run the items in this order: Accounts comes
before the kit's home, so that item's `rmdir` lines can empty the folder.

### Mail

Every agent's mailbox, the notmuch index of them, and the mouth's queue of
spoken lines. sessionmail keeps the boxes in `~/.mail/agents` unless another folder
is named by the `root` setting in `~/.sessionkit/mail/settings/mail.json`, or by the
variable `SESSIONMAIL_ROOT` or `SESSION_MAIL_ROOT`. Nothing in the kit sets any of
them, so if one is set, you set it, and these lines do not touch that folder. Look
in it first, then delete the boxes there by hand. Mail setup's notmuch profile
(section 5, step 3) keeps its config in `~/.config/notmuch/sessionkit` (under
`$XDG_CONFIG_HOME` when that is set). Your own `~/.notmuch-config` is not touched.

The mouth's queue is one of those boxes, `~/.mail/agents/mouth`, and VoiceMode uses
it too: sessionvoice's mouth and VoiceMode's both queue their lines in that one box,
and both keep every line there once it is done. So the first line deletes every box
but that one.

```bash
find "${HOME:?}/.mail/agents" -mindepth 1 -not -path "${HOME:?}/.mail/agents/mouth" -not -path "${HOME:?}/.mail/agents/mouth/*" -delete
rm -rf "${HOME:?}/.config/notmuch/sessionkit"
rmdir "${HOME:?}/.config/notmuch"
```

The last line removes `~/.config/notmuch` only if it is empty.

The mouth's box:

- You use VoiceMode: keep it. VoiceMode's mouth speaks from it, and the lines below
  would delete its queue. The lines sessionvoice's mouth spoke then stay in that box,
  beside VoiceMode's, until you delete it.
- No VoiceMode: the mouth's box is the kit's alone. Delete it:

  ```bash
  rm -rf "${HOME:?}/.mail/agents/mouth"
  rmdir "${HOME:?}/.mail/agents"
  ```

If your shell sets `MOUTH_MAILBOX` or `VOICEMODE_MOUTH_MAILBOX`, the mouth queues in
the folder it names instead. If it sets `MOUTH_DIR` or `VOICEMODE_MOUTH_DIR` to
another folder, the mouth queues in a `box` folder inside it. Nothing in the kit sets
any of them, so if one is set, you set it, and these lines miss that box: look in it,
and delete it by hand only if you do not use VoiceMode.

The profile's index is `~/.mail/.notmuch`. Delete it only if mail setup made the
profile for it. Mail setup's first run said which, on its `notmuch-profile` line:

- It said `MANUAL`: the database was in the mail folder before the kit. It is yours,
  so leave it.
- You cannot tell: leave it.
- It said `wrote`: mail setup then ran `notmuch new` once on that profile, so the
  index is the kit's. Delete it, then the mail folder:

  ```bash
  rm -rf "${HOME:?}/.mail/.notmuch"
  rmdir "${HOME:?}/.mail"
  ```

  The `rmdir` prints `Directory not empty`, and the folder stays, if you kept the
  mouth's box.

### Session records

What each session read, its address, its logs (mail's among them), the session
list's saved state, the older seat home, and the agents folder.

`sessionkit setup` (section 2) wrote one agent file, `NAME.md` for the agent you named
(`claude.md` by default), in the agents folder `session start` reads. On a fresh Mac
that folder is `~/.session/agents`. The second line deletes the agent files there,
the one setup wrote and any you wrote yourself, so copy any you want first. On a host
that ran `session` before its agents folder moved, `~/.session/agents` may also still
hold a link for each agent. That line leaves the links, so the next `rmdir` says
`Directory not empty`: look in it, and delete it by hand if you want it gone. On a host
with no `~/.session/agents`, the second and third lines print
`No such file or directory`: that is fine.

```bash
for d in agent seats sessions mail state; do rm -rf "${HOME:?}/.session/${d:?}"; done
find "${HOME:?}/.session/agents" -maxdepth 1 -type f -name '*.md' -delete
rmdir "${HOME:?}/.session/agents"
rmdir "${HOME:?}/.session"
rm -rf "${HOME:?}/.sessionmail"
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

On a host that used `session account` before the account folder moved, the older
account folder, `~/.config/sessiontools/`, may still be there, with the same kinds of
files in it. **Its backups are your account tokens too.** The kit never writes
there, and nothing else on this page deletes it, so the line below does. Like the
line above, it cannot be undone: to keep those accounts, skip it. It leaves the rest
of `~/.config` alone.

```bash
rm -rf "${HOME:?}/.config/sessiontools"
```

### The kit's home

`~/.sessionkit`, one folder per package. In each, `settings/` holds your choices,
`log/` the package's logs, and `state/` what it keeps between runs (the tree
specification, `openspec/specs/tree/spec.md`). This item deletes those three folders
for mail, voice, the sidebar (`view`) and the phone. That is the operator file that
`sessionkit setup` wrote (section 2), the mail hooks switch, your voice choices, the
seats your voice wakes, the sidebar's config and state, the phone's `phone.json`, and
every package's logs. The voice keeps the speech keys you may have saved, `stt.key` and
`tts.key`, in `~/.sessionkit/voice/settings/` itself, so this item deletes them with
your voice choices.

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
`Directory not empty`, that folder still holds files the kit did not write, or the
account folder you kept: leave them. If one says `No such file or directory`, there
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
replies they missed. Then the speakers' home with the voices you enrolled. The
services' logs are in `~/.sessionkit/voice/log/`, and go with [the kit's home][home].

On a fresh install all of it but the speakers' home is in `~/.sessionvoice`,
sessionvoice's own folder, so the first line deletes that folder whole. `~/.ears`
holds the place `ears-arm` (section 5 step 4) keeps in the transcript. The second line
deletes the speakers' home, in `~/.local/share/ears`.

```bash
rm -rf "${HOME:?}/.sessionvoice" "${HOME:?}/.ears"
rm -rf "${HOME:?}/.local/share/ears"
```

If your shell sets `SESSIONVOICE_HOME`, or VoiceMode's `VOICEMODE_BASE_DIR`,
sessionvoice keeps these files in the folder it names instead. Nothing in the kit
sets either, so if one is set, you set it. If it names `~/.voicemode`, the lines below
cover it. If it names another folder, these lines miss it: look in it, and delete
there by hand the same files the lines below delete in `~/.voicemode`.

sessionvoice also uses `~/.voicemode` when that folder already held a transcript the
first time it ran: an older sessionvoice wrote one there, or VoiceMode's `converse`
did. VoiceMode keeps its own files in `~/.voicemode` too, so never delete it whole.
These lines delete only the files there that are sessionvoice's alone: who spoke, the
`talk` folder, the missed-reply clips,
and the dated folders of kept turn audio (`audio/YYYY-MM-DD`; VoiceMode files its own
audio by year, then month). Where a line finds nothing, it deletes nothing. In zsh,
the Mac's own shell, a pattern that matches nothing prints `no matches found`: that
is fine.

```bash
rm -f "${HOME:?}"/.voicemode/logs/conversations/speakers_*.jsonl
rm -rf "${HOME:?}/.voicemode/talk" "${HOME:?}/.voicemode/state/missed-reply"
rm -rf "${HOME:?}"/.voicemode/audio/[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]
```

The rest of sessionvoice's files there are shared with VoiceMode. VoiceMode writes
the same transcript, `heard_*.jsonl` with its lock, `heard.lock`, and keeps its own
places in it in `~/.voicemode/state/heard-cursor`. Its mouth uses `~/.voicemode/mouth`
too.

- You use VoiceMode: keep them. The lines below would delete VoiceMode's own
  transcript, and the places it kept would then point past the end of it. The turns
  sessionvoice heard then stay in that transcript, beside VoiceMode's, until you
  delete it.
- No VoiceMode: delete them:

  ```bash
  rm -f "${HOME:?}"/.voicemode/logs/conversations/heard_*.jsonl
  rm -f "${HOME:?}/.voicemode/logs/conversations/heard.lock"
  rm -rf "${HOME:?}/.voicemode/mouth" "${HOME:?}/.voicemode/state/heard-cursor"
  ```

If a folder named for your agent was already in your home directory, `~/.<name>`,
`ears-arm` kept its place there as `heard.state`, instead of in `~/.ears`. Delete
that one file by hand, never the folder: `~/.claude`, for one, is Claude Code's.
If your shell sets `EARS_HOME`, `ears-arm` kept its `heard.state` in the folder it
names instead. Delete that one file there by hand too.

### Phone

The agent's chat account with its keys, the invite, the callers, and the bot's own
files. Run step 3 first. The bot's logs are in `~/.sessionkit/phone/log/`, and go with
[the kit's home][home]; an earlier release kept them in `~/.sessionphone`, so this line
deletes those too. The account on the public relay is not on this Mac, and nothing
here deletes it. On your phone, delete the agent's chat in Delta Chat yourself.

```bash
rm -rf "${HOME:?}/.sessionphone"
```

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
  Delete them by hand only if you want them gone.
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
[brew]: #homebrews-tools
[clones-route]: ../INSTALL.md#from-your-own-clones-to-work-on-the-plugins-optional
[mail-setup]: ../INSTALL.md#mail-between-agents
