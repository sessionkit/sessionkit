# Install: from a fresh Mac to an agent that hears you and speaks

**Status: DRAFT, alpha.** Every step is tagged **MEASURED** (it ran, on the machine
and date given), **NOT YET** (not run, or blocked), and **HUMAN** where you must type a
password, answer a prompt, sign in, or edit a file. The measurements come from a
rehearsal of this install, most of them on a fresh macOS 27 virtual machine.

What works today: the commands (mail, sessions, pager, memory, phone, ears,
mouth), the plugins, and the mouth (it falls back to macOS `say`). What does not
yet: hearing needs a speech server, which sessionvoice 0.2.0 installs for you
and 0.1.0 does not (section 5); agent-to-agent mail needs postfix on 0.1.0, and
from sessionmail 0.2.0, not yet released, goes by its experimental file drop with no
mail server (section 5);
the one-command kit plugin does not load (section 7).

## 1. Prerequisites (HUMAN)

**NOT YET** as a whole; each line below was timed on a fresh macOS 27 VM.

- Homebrew, the installer from <https://brew.sh>:

  ```bash
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
  ```

  **HUMAN: your password** at sudo. It installs the Command Line Tools itself. Then run
  the three lines it prints under "Next steps", as printed (two `echo ... >> ~/.zprofile`
  and one `eval ...`), so `brew` is on your PATH. **MEASURED** (2030-06-09, a
  fresh macOS 27 VM): 220 seconds with the Command Line Tools, and a new terminal had
  `brew` and `git`.
- uv: `curl -LsSf https://astral.sh/uv/install.sh | sh` (about 1 second). Then open a
  new terminal, or run `source ~/.local/bin/env`: until you do, `uv` is not on your PATH
  (`command not found: uv`, exit 127).
- Claude Code: `curl -fsSL https://claude.ai/install.sh | bash` (about 13 seconds), then
  start `claude` and **HUMAN: sign in** with `/login`.
- At least 2.1 GB free disk, plus room for a speech-to-text server (section 5).
  **MEASURED** (on the same VM): the Command Line Tools took 1.3 GB, the kit 277 MB, Claude
  Code 230 MB, Homebrew 204 MB and uv's Python 74 MB. A fresh VM started with 9.7 GB
  free and ended with 8.7 GB.
- Python 3.11 or later (uv fetches one if you have none).
- A network connection: the install is online-only. It fetches from PyPI, uv
  downloads its Python, and `ears install` downloads the voice-activity model.

## 2. Install the kit

```bash
uv tool install --python 3.14 sessionkit
sessionkit setup
```

**MEASURED** (2030-06-09, a fresh macOS 27 VM): without `--python 3.14`, uv
downloads Python 3.15, two voice libraries have no 3.15 build, and uv silently
installs the 0.0.1 placeholder instead (one `hello` verb).

**MEASURED** (2030-06-09, read-only against PyPI): 0.1.0 is on PyPI for all six
packages, and this line resolves all six at 0.1.0. On Python 3.15 it still picks the
0.0.1 placeholder, so keep `--python 3.14`. The install itself was **MEASURED** on
2030-06-07, against the same 0.1.0 files before they reached PyPI: all six at 0.1.0, and
9 commands on your PATH:
`sessionkit message pager memory session sessionphone ears ears-serve mouth`. Every
`--help` answers.

Open a new terminal (or run `uv tool update-shell`) so they are on your PATH.

**`sessionkit setup` sets up mail on this Mac, then names you as the operator**: the
human your agents ask. It is the last line of the block, so if it stops, nothing after
it is skipped. If the shell says `command not found`, open a new terminal and run it
there.

**Mail first.** It runs sessionmail's mail setup, `message setup`, which makes the mail
folder and your box and says what is left for you
([Mail between agents](#mail-between-agents), section 5, step 4). On a fresh install
your box is named for your account; with `--mailbox NAME` it makes that box too, and
no other. The sessionmail 0.1.0 this kit installs today has no mail setup: then `sessionkit setup` says so, names the
step to run once you have it, and goes on to the operator. Mail setup ships from
sessionmail 0.2.0, which is not released yet. **MEASURED** (2030-06-09, sessionmail's
unreleased code, a temporary home directory): `sessionkit setup --mailbox <box>` ran
the real mail setup, then wrote the operator.

**On a fresh install it refuses, and that is expected.** It writes a mail box name only
when sessionmail has a box by that name (by default, your account name), and a fresh
install on sessionmail 0.1.0 has none. So it writes nothing, exits 1, and tells you
what to run:

```text
Mail not set up: this sessionmail has no `message setup` (`message setup --help` exited 2).
A newer sessionmail has it. Until you have that, set mail up by hand (INSTALL.md, "Mail between agents"); once you do, run: message setup
No operator written: sessionmail has no box named '<your account name>'.
Name yourself: sessionkit setup --address YOUR-ADDRESS, or sessionkit setup --mailbox NAME (a box `message box path NAME` finds).
```

**MEASURED** (2030-06-09, sessionmail 0.1.0 from PyPI, a temporary home directory):
those four lines, exit 1, nothing written. From sessionmail 0.2.0, mail setup makes
your account's box first, so the box is there when the operator is written. **NOT YET** (read in sessionmail's unreleased code). With
`--mailbox NAME`, `sessionkit setup` asks mail setup for that box as well
(`message setup --box NAME`), so a named box on a fresh install is made before the
operator is written, and it does not refuse.

**Its exit:** 0 all done; 1 the operator was refused or a mail step failed or was
refused (it says which, and the other half still ran); 2 a flag it does not take; 4 the
operator is set and mail steps are left for you, named in its output.

**A dry run writes nothing, so its exit says what a real run would meet.** Mail
setup's dry run exits 4 while any of its steps is still to do, and 0 only once every
step is done. So with `--dry-run`, 4 means mail steps are still to do and the operator
check did not refuse (your box is there, or you gave `--address`, or an operator is
already set): nothing is set yet, and the real run does what it can and names the
rest. On a fresh install mail setup has not made your box, so the operator check after
it refuses too: `sessionkit setup --dry-run` exits 1 there, and the real run is what
makes the box. **MEASURED** (2030-06-09, sessionmail's unreleased code, temporary home
directories): mail setup's dry run exited 4 on a fresh home and 0 once every step was
done; `sessionkit setup --dry-run` exited 1 on a fresh home, 4 on a home that had the
box, and 4 on a fresh home with `--address`, and made nothing each time.

Run it again with `--address` followed by your own email address, or with `--mailbox`
followed by a box name that `message box path` finds. Add `--dry-run` to see the file it
would write, and write nothing. Until the family's operator reader ships, it ends with
"Written; not verified: `session operator` needs a newer sessiontools." The file is
written; nothing has read it back yet.

**MEASURED** (2030-06-09, by the test suite, and on a temporary home directory against a
pre-release `session operator`, never a real one): the refusal, `--address`, `--mailbox`,
a re-run that writes nothing, and the read-back. **NOT YET** on a fresh Mac.

### Operator and administrators

- **Where it lives.** `sessionkit setup` writes one file,
  `~/.sessionkit/tools/settings/session.d/10-operator.json`, in the `session` tool's settings.
  They are read in this order: `session.template.json`, `session.json`, then each
  `session.d/*.json` by name, and a later file wins. The file holds `_about` (a note
  saying what wrote it) and your operator block:

  ```json
  {"operator": {"mailbox": "NAME"}}
  ```

  with `"address"` in place of `"mailbox"` if you used `--address`. To change the
  operator, edit that file. Or delete it and run `sessionkit setup` again.
- **Who is privileged.** `setup` never writes `privileged`. Then the operator alone may
  act as an administrator. `session operator` shows who is configured, under `mailbox`,
  `operator` and `privileged`.
- **Adding an administrator. HUMAN (edit a file).** Run `sessionkit setup` first: once
  any file holds an `operator` block, `setup` leaves it alone (below). Then make a file
  of your own, such as `~/.sessionkit/tools/settings/session.d/20-administrators.json`:

  ```json
  {"operator": {"privileged": ["<a seat name or address>"]}}
  ```

  **The list replaces.** When two files set `privileged`, the later file's list wins
  whole, so keep every administrator in ONE list. You need not list yourself: the
  operator is always privileged. Check it with `session operator`. **MEASURED**
  (2030-06-09, temporary home, pre-release `session operator`): a `20-` file's list was
  added beside the operator, and a `30-` file's list replaced the `20-` file's.
- **An environment variable never grants privilege.** `AGENT_OPERATOR_ADDR` can change
  where an agent sends a question, nothing more. `setup` ignores it, and `$USER` and
  `$MAIL` too: your account name comes from the system, not the environment. **MEASURED**
  (2030-06-09, the same way).
- **Set an operator by hand already? `setup` leaves it alone.** If `session.json` or any
  `session.d/*.json` file holds an `operator` block, or `session operator` already
  reports one, it writes nothing, names the file or the operator, and exits 0. If one of
  those files cannot be read or is not valid JSON, it writes nothing, names the file,
  and exits 1: fix that file first.
- **Upgrading from 0.1.0.** 0.1.0 wrote the operator to
  `~/.settings/session/session.d/10-operator.json`. While that file exists and no operator
  is set in the new folder, `setup` writes nothing, prints one line naming both files, and
  exits 1, even with `--dry-run`; it never reads the old file. Move it to
  `~/.sessionkit/tools/settings/session.d/10-operator.json`, or remove it, then run
  `sessionkit setup` again.

Older notes say that `uv tool install sessionmail` or `uv tool install sessiontools`, on
its own, installs an empty placeholder. Since the release each installs its real 0.1.0 package
(read on PyPI, 2030-06-09), and `sessionkit` brings both anyway.

## 3. Install the plugins

**MEASURED** (in the release rehearsal, when the loop below also installed a sixth,
optional plugin): every plugin installed from its own clone's local marketplace, 6 of 6
enabled. The kit's own plugin does not load yet (section 7), so you install the five
plugins one at a time, each from its own clone.

Keep the clones in ONE directory you will not move (moving one breaks its plugin; see
the end of this section). The block below calls it `$SRC`. Clone each of the five into
it with `git clone https://github.com/sessionkit/<name> "$SRC/<name>"`, where
`<name>` is each name the loop lists. **NOT YET MEASURED:** nobody has yet
cloned from these URLs on a clean Mac and walked the rest of this guide; the measured
runs in this section used clones that were already on the machine.

```bash
SRC=~/.local/share/sessionkit/src   # clone the repos here; do NOT move them afterwards
for r in sessionmail sessiontools sessionphone sessionvoice sessionview; do
  claude plugin marketplace add "$SRC/$r" && claude plugin install "$r@$r"
done
claude plugin list
```

**The block exits 0 even when nothing installed, so read `claude plugin list`.** You
should see five plugins, each `✔ enabled`, scope user. Do **not** install
`sessionkit@sessionkit`: it does not load yet (section 7).

**MEASURED** (2030-06-09, a fresh macOS 27 VM, when the loop also installed a sixth,
optional plugin): with no clones in `$SRC`, the loop printed one line for each name,
like `✘ Path does not exist: <SRC>/sessionmail`, then `claude plugin list` printed
`No plugins installed.`, and the block still exited 0. With every clone present, the
same block gave 6 of 6 `✔ enabled` in 9 seconds, without signing in to Claude Code.

**Fewer than five?** Read the line the loop printed for each missing one:

- `Path does not exist: <SRC>/<r>`: there is no clone there. Clone it to `$SRC/<r>`.
- `Marketplace file not found at <SRC>/<r>/.claude-plugin/marketplace.json`: the clone
  is there, but nothing is checked out. Delete that clone and clone it again with
  `-b master`, the branch the public repositories are on. **MEASURED** (on the same VM,
  with clones it already had: a clone with nothing checked out gave this; cloned again
  with its branch named, `main` then, it installed). **NOT YET MEASURED** with
  `-b master`, from the public URLs or from those clones.

Then run the loop's line for that one, with `r` set to its name (`r=sessionmail`, for
example): `claude plugin marketplace add "$SRC/$r" && claude plugin install "$r@$r"`.

**`Read from` names the clone, but the plugin runs from a copy.** `claude plugin list`
says `Read from: <SRC>/<r>`. The install copies each plugin to
`~/.claude/plugins/cache/<r>/<r>/<version>/`, and that copy is what runs. Its `bin/` and
`skills/` are the paths section 5 needs. **MEASURED** (on the same VM:
`~/.claude/plugins/installed_plugins.json` gives each plugin's `installPath` there).

**If a clone moves, its plugin breaks silently** (`claude plugin list` still exits 0;
**MEASURED**). Repair, also measured: `claude plugin marketplace remove <r>`, then
`claude plugin marketplace add <new path>` and `claude plugin install <r>@<r>`. The remove
drops that plugin's saved options.

## 4. First checks

- `ears install`: fetches the voice-activity model to `~/.cache/ears/silero_vad.onnx`
  (network, no sudo). **MEASURED** (in the release rehearsal).
- Start `claude` in the directory you will work from. The sessionmail plugin's hooks run
  clean, and your mailbox under `~/.mail/agents/` is created the first time the pager
  listens. **MEASURED** in part (in the release rehearsal). The hooks stay off until you set
  `"hooks": true` in `~/.sessionkit/mail/settings/mail.json`; the first run tells you so.
- **`pager status` and `message send` work only inside a `claude` session.** They find
  out who is asking from the session's environment, and a plain terminal has none. There
  they print this and exit 2:

  ```text
  pager status: could not look: no identity in the environment - looked for TM_AGENT_ADDRESS, CLAUDE_CODE_AGENT, CLAUDE_CODE_SESSION_ID, CLAUDE_SESSION_ID, in that order
  Error: no seat in the environment to send From - there is no --from; set an identity
  ```

  That is expected, not a broken install: run them from your agent, inside `claude`,
  which sets `CLAUDE_CODE_SESSION_ID`. **MEASURED** (2030-06-09, a fresh macOS
  27 VM, Claude Code not signed in: both lines, exit 2). Inside a session, `pager status`
  gets past this and asks for the mailbox instead, until the pager first listens
  (**MEASURED** on the authors' Mac, 2030-06-09, not the VM).
- The sessionmail plugin's monitor arms the pager for the whole session, and it is on by
  default. Section 3 installs it: the plugin's `monitors/monitors.json` runs
  `pager listen --monitor` with the `pager` on your PATH, so you do not turn anything on.
  Your sessionmail clone must have that `monitors/monitors.json`; an older clone has
  none, and so no monitor. This comes from sessionmail's source: the plugin on its
  master, and the `--monitor` flag in the 0.1.0 `pager` the kit installs. **NOT YET**
  run on a fresh Mac. Claude Code runs a plugin's monitor only in an interactive session
  (never `claude -p`), with the folder trusted, and only while its own monitor gate is
  on. When it does not run it, nothing in Claude Code says so (sessionmail's
  `docs/pager-monitor.md`; the trust condition is from the README of its retired
  `plugins/pager-monitor`). sessionmail's off switch (`"monitor": false` in
  `~/.sessionkit/mail/settings/mail.json`, or `SESSIONMAIL_MONITOR=off` at launch) and
  `pager mute` / `pager unmute` are **NOT YET** for a kit install. The 0.1.0 `pager`
  from PyPI has none of them, and they wait on the next sessionmail release. With no
  monitor running, the agent arms the pager itself, as a background tool call, when the
  pager's hook says it is not listening (hooks on). Your agent's letter to itself never
  arms or stops the pager from a wake item; `pager status` is the only check
  ([the agent letter](docs/agent-letter.md)).

### Your first agent, in tmux

**NOT YET** as a whole: no fresh Mac has run these steps end to end. Each step says
what was measured.

1. **Get tmux. HUMAN (Homebrew).** Run `brew install tmux`, then `tmux -V` to see its
   version. It uses the Homebrew from section 1. tmux brings no Python with it. The
   kit's Python is uv's (section 2), so do not `brew install python`. **MEASURED**
   (2030-06-09, read-only, `brew deps tmux` at tmux 3.8, not on a fresh Mac): it needs
   ca-certificates, jemalloc, libevent, ncurses, openssl@4 and utf8proc, and no Python.
2. **Start tmux** in the directory you will work from:

   ```bash
   cd <the directory you will work from>
   tmux new-session -s agents
   ```

   This puts you inside a tmux session named `agents`. To leave it running, press
   `Ctrl-b` and then `d`. To come back, run `tmux attach -t agents`. **MEASURED** in
   part (2030-06-09, tmux 3.8, on a tmux server of its own):
   `tmux new-session -d -s agents` made the session, and `tmux ls` listed
   `agents: 1 windows`.
3. **Start your first agent** inside it: `session start`. When you name no agent, it
   starts a plain `claude` session in this window, under a new session id.
   `session start --dry-run` prints the command and starts nothing. Running `claude`
   yourself works too (as in the checks above). From outside tmux,
   `session start --tmux-target agents` puts the agent in a new window named
   `claude`. **MEASURED** only as `--dry-run` (2030-06-09, 0.1.0, on a temporary home
   directory): the command was `claude --session-id <a new id>`, exit 0. With
   `--tmux-target agents`, it gave `tmux window 'claude' in session 'agents'`. From
   outside tmux with no target, `session start --in-tmux` stopped with
   `nowhere to place the window`, exit 2.
4. **Have it listen.** Turn the mail hooks on first (`"hooks": true`, in the checks
   above). After that, the pager's hook tells your agent when it is not listening, and
   the agent starts `pager listen` itself, as a background tool call. You can also ask
   it to. The banner says whether mail reaches the agent's box. `pager status`, run by
   the agent, reads that box. **NOT YET.**
5. **Mail it: NOT YET.** On the sessionmail 0.1.0 this kit installs, sending needs
   postfix on this Mac. With none,
   `message send` refuses (**MEASURED** in the release rehearsal), and your agent
   listens but no mail can reach it. From sessionmail 0.2.0, not yet released, it goes
   by the experimental file drop with nothing to set: see
   [Mail between agents](#mail-between-agents) in section 5. The voice path in section
   5 does not need mail.

## 5. Hearing and speaking ("it hears me and speaks")

None of these ran end to end in the rehearsal. Each is **NOT YET** unless a line says
otherwise.

Steps 1 and 2 are sessionvoice **0.2.0**, which is not on PyPI yet: PyPI has
0.1.0 (2030-06-09), and that is what section 2 installs today. They were read in
sessionvoice's source, and dry-run from a 0.2.0 wheel built from its master. On
0.1.0 you bring your own speech server, and the kit's `ears` cannot run
`ears services install` (section 7). Each step says what to do on 0.1.0.

**The job labels.** Every launchd job in the session family is labelled
`dev.sessionkit.<package>.<job>`. The voice's are `dev.sessionkit.voice.mlx-audio`
for the speech server and `dev.sessionkit.voice.ears-<name>` for the rest. Two
older forms are history: `com.sessionvoice.*`, which earlier copies of this guide
named, and `com.voicemode.ears-*`, which 0.1.0 loads. 0.2.0's
`ears services install` recognises a job under either old form and retires the old
form: it moves the job off before it loads the new label. The dry runs in steps 1
and 2 were made on a build from before the rename, which wrote the same jobs under
`com.sessionvoice.*`. **NOT YET** read in a sessionvoice build that carries the new
labels.

1. **The speech server.** You do not bring one: step 2's `ears services install`
   finds it or installs it. It is mlx-audio's server on 127.0.0.1:8890, which
   runs the ears' Parakeet and the mouth's Kokoro. Install first asks what holds
   port 8890:
   - **Nothing:** it builds the server its own venv in
     `~/.local/share/ears/speech/venv` (python 3.12, mlx-audio 0.5.8; network)
     and loads it as `dev.sessionkit.voice.mlx-audio`. That needs an Apple-silicon
     Mac (arm64) on macOS 14 or later, and `uv`.
   - **A server that says it is mlx-audio** (VoiceMode's, for example): install
     uses it and starts nothing.
   - **Anything else:** install refuses, names it, and exits 2. It never
     replaces it.

   Do not run VoiceMode's installer after this one: it asks nothing, loads a
   second mlx-audio job, and one of the two crash-loops. Without a server on
   8890, nothing hears you (**MEASURED** in the release rehearsal). **MEASURED** only as `--dry-run`
   (2030-06-09, 0.2.0, a temporary home directory, nothing on 8890): it would
   build that venv and load `dev.sessionkit.voice.mlx-audio`.

   **On sessionvoice 0.1.0**, install loads no speech server, so you bring one:
   any OpenAI-compatible STT on port 8890 (Parakeet, the default) or 2022
   (whisper), for example from VoiceMode.
2. **The voice services. HUMAN (launchd, the microphone permission prompt).** Two
   commands, in this order:
   - `ears install` **first**, even if you ran it in section 4. It fetches the
     voice-activity model to `~/.cache/ears/silero_vad.onnx`. **MEASURED** (in
     the release rehearsal). Without that model, the ears keeper died every 4 seconds on a
     fresh Mac. **NOT YET:** that came from a field report, not the rehearsal.
     0.2.0's `ears services install` refuses without the model
     (`silero MISSING`, exit 2). **MEASURED** as `--dry-run` (2030-06-09, 0.2.0,
     a temporary home directory).
   - **Then** `ears services install`, the kit's own `ears` from section 2. It
     writes four LaunchAgents and loads them: `dev.sessionkit.voice.mlx-audio`
     (the speech server, step 1), `dev.sessionkit.voice.ears-mouth`,
     `dev.sessionkit.voice.ears-keeper` and `dev.sessionkit.voice.ears-mail`. The
     keeper and ears-mail run from scripts in the sessionvoice package itself, so
     no plugin path is needed. If jobs under an old label are on this Mac (0.1.0's
     `com.voicemode.ears-*`, or `com.sessionvoice.*`), install retires the old
     form: it moves each one off before it loads the new one. **MEASURED**
     only as `--dry-run` (2030-06-09, 0.2.0, a temporary home directory): those
     four plists, with the keeper's and ears-mail's scripts in the installed
     package. **NOT YET** as a real install.
   - **On sessionvoice 0.1.0** (what section 2 installs from PyPI today), the
     kit's own `ears services install` cannot find the keeper. Run it
     through the sessionvoice **plugin's** `bin/ears` instead (**MEASURED** in
     the release rehearsal). The plugin's copy is in the cache (section 3), under its
     version:

     ```bash
     ~/.claude/plugins/cache/sessionvoice/sessionvoice/0.1.0/bin/ears services install
     ```

     If your version is not 0.1.0, find it with
     `find ~/.claude/plugins/cache -path '*/bin/ears' -type f`. **MEASURED**
     (2030-06-09, a fresh macOS 27 VM, with clones made outside this guide's
     steps): that path, then two LaunchAgents loaded under 0.1.0's old labels
     (`com.voicemode.ears-mouth`, `com.voicemode.ears-keeper`), both still
     running 45 seconds later. 0.2.0's install retires the old form (the job
     labels, above). A 0.1.0 install loads the mouth and the keeper only, not
     ears-mail.
     **MEASURED** (2030-06-09, `ears services install --dry-run` on 0.1.0: two
     plists, the mouth's and the keeper's; `--only` takes `stt`, `mouth`,
     `keeper`). The plugin's `bin/ears` runs the plugin's own sessionvoice, so
     a plugin of another version does what that version does (read in its
     `bin/ears`).

   On 0.2.0, a bare `ears services install`
   loads `speech`, `mouth`, `keeper` and `mail`. `--only` takes
   `stt`, `speech`, `mouth`, `keeper`, `mail` and `speakers`: `stt` (Apple's
   speech, section 6) loads only with `--apple` or `--only stt`, and `speakers`
   only with `--only speakers` (below). ears-mail is the job that
   turns a heard turn into mail that pages your agent. On 0.2.0 it hands its mail to
   `message send` (the ears-mail of 0.1.0 handed it to `/usr/sbin/sendmail` and needed
   postfix), so with sessionmail 0.2.0 it rides the file drop in
   [Mail between agents](#mail-between-agents). With no postfix, install warns that
   `message send` needs `SESSIONMAIL_SENDMAIL=drop` and that launchd jobs do not see it,
   and loads it anyway. From sessionmail 0.2.0 neither holds: the drop is the default,
   and `message send` reads it from the settings file (read in both sources). **NOT
   YET** walked, so until it is, your agent wakes on your voice through steps 3 and 4,
   not by mail.

   **Optional: speaker names. HUMAN (a person at the mic, the microphone
   permission prompt).** The speakers service tags each heard line with who said
   it. A bare install does not load it. It needs an Apple-silicon Mac (arm64) on
   macOS 14 or later, and `uv`. After the services above are running:

   ```bash
   ears services install --only speakers   # its own venv, the model, the job
   ears speakers enrol                     # a person names each voice
   ears services status                    # the speakers row
   ```

   The install builds its own venv (mlx-audio 0.5.8) and downloads the diarizer
   model, about 190 MB, once. `ears speakers enrol` records the room while the
   keeper runs, for 180 seconds by default (Enter stops it sooner). It shows
   what each voice said and asks a person to name each one; it never guesses a
   name.
   Under launchd, macOS asks for a microphone grant for the speakers binary,
   `bin/ears-speakers`; without it, its rows say `unheard`, `no signal`.
   **MEASURED** only as `--dry-run` (2030-06-09, 0.2.0, a temporary home
   directory): it would build the venv, download
   `mlx-community/Nemotron-3-Diarization` (about 190 MB, once) and load
   `dev.sessionkit.voice.ears-speakers`. **NOT YET** as a real install or an enrol.

   **Lid shut:** the built-in mic is off in hardware; use Bluetooth buds or a USB mic.
   To check the lid, see [ears running, but deaf][lid].
3. **The ride-along hook. HUMAN (hand edit).** In your launch directory's
   `.claude/settings.local.json`, add `ears heard hook || exit 1` on PostToolUse and
   PostToolBatch (**MEASURED** in the release rehearsal). It hands your agent what you said on its next
   tool call. If the file does not exist, paste this as the whole file:

   ```json
   {
     "hooks": {
       "PostToolUse":   [{"hooks": [{"type": "command", "command": "ears heard hook || exit 1", "timeout": 5}]}],
       "PostToolBatch": [{"hooks": [{"type": "command", "command": "ears heard hook || exit 1", "timeout": 5}]}]
     }
   }
   ```

   If it exists, add these two entries to its `hooks` instead of replacing the file.
   Keep `|| exit 1`: a failing hook then shows an error and your agent carries on. `ears`
   must be on the PATH `claude` starts with; section 2 puts it there. The JSON is
   sessionvoice's own, from its README. **NOT YET** on a fresh Mac: the fresh VM could
   not sign in, so no session ran it.
4. **Wake on your voice.** Your agent runs `ears-arm <seat> room` in the
   background, where `<seat>` is the name you call your agent by. How it
   reaches `ears-arm` depends on the sessionvoice plugin's version:
   - **From sessionvoice 0.2.0** (not in 0.1.0): `ears-arm` is on the Bash
     tool's PATH by its bare name while the plugin is enabled, through the
     plugin's `bin/ears-arm`. That shim runs
     `skills/ears/scripts/ears-arm`, and the full path still works.
     **NOT YET** on PATH (read in sessionvoice's source). **MEASURED** only
     as `--help` (2030-06-09, 0.2.0, a copy of its master): the shim runs
     the script.
   - **On 0.1.0** it is not on your PATH: run it by its full
     path,
     `~/.claude/plugins/cache/sessionvoice/sessionvoice/0.1.0/skills/ears/scripts/ears-arm`
     (**MEASURED**, 2030-06-09, a fresh macOS 27 VM).

   It runs the `heard-first` waiter. In room mode it wakes your agent when you say "hey"
   and its name (or "hey everyone"), when you answer the last thing your agent said, or
   when a line your agent is speaking gets cut off (you talk over it, or the speakers
   drop); a bare mention of its name does not wake it. Run it again each time it fires.
   **MEASURED** as `--dry-run` only (2030-06-09: it prints the `heard-first` command,
   with rules for "hey" plus the name or "everyone", a reply rule and a cut rule).
   **NOT YET** as a live wake.
5. **Test the mouth. HUMAN (speakers).** `mouth say --device default "ears are up"`.
   Without a server on 8890 it speaks with macOS `say` (**MEASURED** in the release
   rehearsal). From
   sessionvoice 0.2.0 (not in 0.1.0), the mouth can speak through a hosted
   speech endpoint instead: put its URL and model in
   `~/.sessionkit/voice/settings/mouth.json`, and its key in `~/.sessionkit/voice/settings/tts.key`
   (mode 600) or `MOUTH_TTS_KEY`: see
   [sessionvoice's docs/models.md, A hosted speech endpoint instead][sv-hosted].
   **NOT YET** (read in its docs).
6. **The finish line. HUMAN (mic, speakers).** You speak; the ear writes a turn; the
   waiter wakes your agent; it answers with `mouth say`. **That is the proof: your
   agent WAKES and answers you out loud.** A heard line showing up (in the heard log, or
   handed over by the step 3 hook) is **not** the proof. It shows the ear works, not that
   your agent wakes.

**Until step 6 passes, keep room mode and `heard-first`.** Arm `ears-arm <seat> room`
(step 4), and leave the other modes and the mail path alone until your agent has woken
and answered you. **NOT YET** (advice: step 6 has not passed on any measured Mac).

### Mail between agents

From sessionmail 0.2.0, `message send` hands each message to sessionmail's file drop
by default. The drop writes the message straight into the recipient's box on this Mac,
with no mail server and no setting. Postfix is opt-in: it is how mail reaches other
Macs. The sessionmail 0.1.0 this kit installs today has no drop. It hands every message
to postfix, and with none it refuses with "Install postfix, or name the MTA in
`$SESSIONMAIL_SENDMAIL`" (**MEASURED** in the release rehearsal).

**The file drop. EXPERIMENTAL.** sessionmail's own acceptance test of the drop on a bare
Mac has not run yet. Mail carried by the drop stays on this Mac. Each step below says
what was measured. The walk ran on sessionmail's unreleased code (2030-06-09), with a
temporary home directory, no postfix on the PATH, no tailscale and no mail setting.

1. **Get sessionmail 0.2.0. NOT YET.** The drop and mail setup (step 4) ship from
   sessionmail 0.2.0, and that version is a prediction: it is not released yet. The
   0.1.0 this kit installs today has neither, so until 0.2.0 is out these steps do not
   work. **MEASURED** (2030-06-09, read-only): sessionmail 0.1.0 has no drop, and its
   `message setup` answers "No such command", exit 2; its unreleased code has both.
2. **Nothing to set.** The drop is the default: the `sendmail` setting is `"drop"`
   unless you name another in `~/.sessionkit/mail/settings/mail.json`. A fresh install
   has no such file and needs none: the default ships with sessionmail. A Mac that
   is not on a tailnet needs nothing more: the drop delivers to this Mac's own boxes
   with no MagicDNS suffix and no tailscale. It warns that a bare sender's address is
   qualified with the short host name only. **MEASURED** (2030-06-09, a temporary home
   directory, with no `SESSIONMAIL_SENDMAIL`, no settings file, no `MAGICDNS_SUFFIX` and
   no tailscale): sent, exit 0, by the drop, and the message was in the box's `new/`
   folder. A variable that is set beats the file: if you set
   `export SESSIONMAIL_SENDMAIL=drop` for an earlier build, it still works, and
   removing it hands the choice back to the file. **MEASURED** (2030-06-09): mail setup
   reported the carrier as the drop "from `$SESSIONMAIL_SENDMAIL`".

   **Jobs launchd starts.** launchd reads no shell file, and the drop needs none:
   `message send` reads the carrier from the settings file, so a job with nothing in
   its environment gets the drop too (read in sessionmail's settings docs). Three mail
   senders run that way:
   - **The phone bot** (section 6).
   - **sessionvoice's mouth notices**, sent by the mouth.
   - **ears-mail's heard turns**, the mail that pages your agent when you speak.

   In the next releases of sessionvoice and sessionphone, all three hand their mail to
   `message send`, so they ride the drop, and from sessionmail 0.2.0 a heard turn sent
   by the drop reads as your voice (read in their source). **NOT YET:** none of these
   releases is out, and in the sessionvoice and sessionphone 0.1.0 the kit installs,
   all three hand their mail to `/usr/sbin/sendmail` themselves, so on a Mac with no
   postfix they deliver nothing.
3. **Install notmuch. HUMAN (Homebrew).** `message mark` and `memory` read mail through
   notmuch. Run `brew install notmuch` before step 4. Mail setup writes sessionmail's
   own notmuch profile, `~/.config/notmuch/sessionkit/config` (under
   `$XDG_CONFIG_HOME` when that is set), with the mail folder as its database, and
   links sessionmail's hook there. It never reads or writes a notmuch config of your
   own: `~/.notmuch-config` and any other profile are left exactly as they are, and
   nothing is linked into them. It adopts no notmuch database: if the mail folder
   already holds one, `~/.mail/.notmuch`, mail setup writes no profile, and its
   `notmuch-profile` line says `MANUAL` instead of `wrote`, and names what to do. That
   database is yours, and the uninstall leaves it (section 8). **MEASURED**
   (2030-06-09, a temporary home directory whose mail folder held a database made by
   its own `~/.notmuch-config`): `MANUAL` on two runs, no profile written, exit 4.
   Until the profile's first `notmuch new`, notmuch reports no hook folder, so the
   first run of mail setup writes the profile, leaves its notmuch step `BLOCKED` and
   exits 4. Then run the line it names, once:

   ```bash
   notmuch --config="$HOME/.config/notmuch/sessionkit/config" new
   ```

   Run `sessionkit setup` again: it links both hooks and reports every step `DONE`,
   exit 0. **MEASURED** (2030-06-09, notmuch 0.40, a temporary home directory with no
   notmuch config): the profile written, `BLOCKED` and exit 4, then `notmuch new`, then
   both hooks linked and exit 0; no `~/.notmuch-config` was made. Nothing runs
   `notmuch new` after that, in sessionmail or the kit: until something does (launchd,
   cron, or by hand), `message mark` and `memory` read an empty index (read in
   sessionmail's docs). **NOT YET:** `brew install notmuch` on a fresh Mac.
4. **Make the boxes: `sessionkit setup`** (section 2). It runs sessionmail's mail setup
   first, `message setup`, which makes the mail folder and your box, writes the notmuch
   profile and links its hooks (step 3), and prints every step with its state (`DONE`,
   `TODO`, `BLOCKED` or `MANUAL`), then what is left for you. It is safe to run again: a
   second run reports each step `DONE` and changes nothing. It writes no mail setting.
   It makes these boxes and no others: a box named for your account, and the box you
   name with `sessionkit setup --mailbox NAME`, if you give one.
   The drop never makes a box. Mail to a box that does not exist is refused and
   nothing is delivered, to that box or any other (exit 3). Your agent's own box is
   made when its pager first listens (section 4). Make every other box that mail goes
   to with mail setup, for example:

   ```bash
   message setup --box <box>
   ```

   The sender needs no box of its own. **MEASURED** (2030-06-09, sessionmail's
   unreleased code, a temporary home directory): `sessionkit setup --mailbox <box>`
   ran the real `message setup`, which made the mail folder, the operator's box and
   that box and wrote the notmuch profile, and then wrote the operator, exit 4 (the
   notmuch step left); `message setup --box <box>` made one more box; a re-run reported
   each `DONE`, exit 0; mail to a box it had not made was refused, exit 3; and
   `pager listen` made its session's box.
5. **Check for `jq`.** `command -v jq` should print a path. macOS 27 ships
   `/usr/bin/jq`; if it prints nothing, run `brew install jq`. Without `jq`, mail still
   lands in the box it is addressed to, but mail to a seat's name gets no copy in that
   seat's session box, so the pager listening there is not woken by it. **MEASURED**
   (2030-06-09, macOS 27.0.1: `/usr/bin/jq` is jq 1.7.1; with `jq` off the PATH, the
   send went through with that warning).
6. **Same Mac only.** Mail to another host is refused with "not on this host", exit 3.
   **MEASURED** (2030-06-09).
7. **Check it, from your agent** (inside `claude`, as in section 4):
   `message send <a box> -s test -f <a file>` prints `sent via mail drop (no MTA)` and
   exits 0, and the message is in that box's `new/` folder. **MEASURED** (2030-06-09,
   a temporary home directory): both ways between two named boxes, and from one
   session to another; `message list` and `message read` showed each, and a signed
   one passed `message verify`.

**Mail to other Macs: postfix, opt-in.** The drop carries mail on this Mac only. To
send through postfix instead, name its `sendmail` in
`~/.sessionkit/mail/settings/mail.json`. Make the file if there is none, or add the
key beside the ones already there:

```json
{"version": 1, "sendmail": "/usr/sbin/sendmail"}
```

`SESSIONMAIL_SENDMAIL`, when it is set, beats the file. **Already have postfix
delivering agent mail?** From sessionmail 0.2.0, name it this way, or the drop carries
your mail and mail to other Macs is refused. Postfix itself is yours to set up: its
virtual mailbox and alias maps for the agent boxes need sudo, and this document does not
walk you through it (see
[sessionmail's docs/postfix-configuration.md](https://github.com/sessionkit/sessionmail/blob/HEAD/docs/postfix-configuration.md)).
Neither `sessionkit setup` nor mail setup ever edits postfix. When mail setup makes a
box on a postfix host that has sessionmail's maps, it rebuilds them once. On a host
with none, it writes none, and prints a `MANUAL` line naming `message setup
--write-maps`, which writes them only when you run it; `sessionkit setup` never passes
it. A postfix host also needs a MagicDNS suffix (the `magicdns_suffix` setting, or
`MAGICDNS_SUFFIX`) unless tailscale can be asked. Read in sessionmail's docs; **NOT
YET** walked (mail setup reads the settings file under the account's own home, so a
temporary home directory cannot point it at postfix).

## 6. Optional

- **Your phone. HUMAN (an account on a public relay, the Delta Chat app, launchd,
  Homebrew).** `sessionphone setup --name <your name>`, then scan the invite with Delta
  Chat on your phone, then `sessionphone bot install`. Calls also need `ffmpeg` from
  Homebrew and the speech server on 8890. **NOT YET** end to end.
- **Apple speech. HUMAN (Xcode, macOS 27).** `ears install --apple`. **NOT YET**.

## 7. Known gaps you will hit

- **No speech server on sessionvoice 0.1.0.** None ships with the kit; you bring one.
  0.2.0's `ears services install` finds one or installs its own (section 5 step 1).
- **The kit plugin does not load.** Install the five plugins instead (section 3).
- **The mouth's default "heard" box** names the authors' own mailbox; set
  `VOICEMODE_MOUTH_HEARD_BOX` to yours.
- **On sessionvoice 0.1.0, the kit's `ears services install` cannot find the
  keeper.** Run it through the sessionvoice plugin's `bin/ears` (section 5 step 2).
  0.2.0 ships the keeper in its package, so the kit's own `ears` runs it.
- **Mail setup needs sessionmail 0.2.0, not released yet.** On 0.1.0, `sessionkit setup`
  says it has no `message setup` and goes on to the operator. Set mail up by hand: see
  [Mail between agents](#mail-between-agents) in section 5.
- **Moving a clone breaks its plugin** without a word (section 3 says how to repair it).

## 8. Uninstall

**NOT YET** as a whole: no rehearsal has run an uninstall end to end. Each step
says what was measured. Part A removes the program and keeps everything you
made. Part B deletes your data, and only if you choose it. Keep to this order.
It is the install in reverse: the voice jobs run from the kit's files (on 0.1.0,
the plugin's) and the phone bot from the plugins', so both go before the plugins
and the kit do.

### A. Remove the program

**1. Look first.** These only read: `claude plugin list` shows the plugins,
`sessionphone bot status` the phone bot, and
`launchctl list | grep -E 'dev\.sessionkit\.|sessionvoice|voicemode\.ears|sessionphone|sessiontools'`
the launchd jobs that the voice and the phone put down, and any sessiontools job you
turned on. The pattern finds the family's labels, `dev.sessionkit.<package>.<job>`, and
the older forms a Mac may still hold. **NOT YET** as an uninstall check.

**2. Quit every `claude` session.** The pager's monitor and any `ears-arm` waiter
(section 5 step 4) run inside a session and end with it. The steps below run in a
plain terminal. **NOT YET.**

**3. The phone (section 6), if you set it up.** `sessionphone bot uninstall` stops the
bot and removes its launchd job. The account stays: it is your data (part B).
**NOT YET** as a run. Its `--help` says this (2030-06-09, 0.1.0).

**4. The voice (section 5).** Do this before step 5. The voice jobs run from the
kit's own sessionvoice package (section 2), or on 0.1.0 from the sessionvoice
plugin's files, and launchd keeps them loaded after those files are gone.

- **The ride-along hook. HUMAN (hand edit).** In your launch directory's
  `.claude/settings.local.json`, remove the two `ears heard hook || exit 1` entries and
  leave any other hooks. If you pasted the whole file in section 5 and have added
  nothing since, delete the file. **NOT YET.**
- **The voice jobs.** Run `ears services uninstall`, the kit's own `ears` that
  installed them (section 5 step 2). With no `--only` it removes every job it
  knows. 0.2.0 knows its own labels, `dev.sessionkit.voice.*`, and both old
  forms it retires: `com.sessionvoice.*`, and the older `com.voicemode.ears-*`
  that 0.1.0 used; that includes `--only speakers`, if you added it. 0.1.0
  knows the older set only, which is all it installed. The
  speech server's venv and the speakers' home, `~/.local/share/ears/speakers`,
  stay until part B. **NOT YET** as a run: read in sessionvoice 0.2.0's source
  (2030-06-09), from before the rename (the job labels, section 5).
- **On sessionvoice 0.1.0**, if you installed through the plugin's `bin/ears`
  (section 5 step 2), uninstall through that same one. Find it with
  `find ~/.claude/plugins/cache -path '*/sessionvoice/*/bin/ears' -type f`, then
  run `<that path> services uninstall`; `<that path> services status` only
  reads. Do not use the kit's 0.1.0 `ears` for this: it knows only 0.1.0's old
  form, `com.voicemode.ears-*`, which newer installs retire, so it misses the
  jobs a newer plugin installed.
  **NOT YET** as a run: read in sessionvoice's source, 0.1.0 and 0.2.0
  (2030-06-09).
- ⚠️ **On 0.1.0, `ears services uninstall` has no dry run.** It accepts
  `--dry-run` and ignores it: it boots the jobs out and deletes their plists. A
  temporary `HOME` does not make it safe either, because `launchctl` acts on
  your own user's jobs whatever `HOME` says. **MEASURED** (2030-06-09, the kit's
  0.1.0 `ears` on a temporary home directory, with no jobs installed):
  `--dry-run` printed `removed` for each job, and the source ignores the flag.
  0.2.0 honours it: it names each job it would boot out and each plist it would
  delete, and changes nothing (read in sessionvoice 0.2.0's source, not run). To
  look first on either version, run `ears services status`, which only reads.
- **Check:** `launchctl list | grep -E 'dev\.sessionkit\.voice\.|sessionvoice|voicemode\.ears'`
  prints nothing.
  Wait a few seconds before you run it. A job that is still exiting stays in the
  list for a while after the uninstall. If it prints a line, wait a few seconds and
  run it again, until it prints nothing.
  A job you rendered by hand from sessionvoice's `launchd/` templates (not on this
  path) has a label of its own. Run `launchctl bootout gui/$(id -u)/<its label>`, then
  delete its plist from `~/Library/LaunchAgents/`. **NOT YET.**
- **What you brought yourself.** The kit did not install a speech server you
  brought yourself (VoiceMode's, or any on 0.1.0; section 5 step 1), or any
  postfix setup you made for agent mail
  ([Mail between agents](#mail-between-agents), section 5). Remove them the way
  you installed them; undoing postfix needs sudo. The file drop needs no undoing: it
  is the default, and no setup step wrote a setting for it. If you named postfix in
  mail's settings file, that file goes with the settings in part B. If you set
  `SESSIONMAIL_SENDMAIL` in `~/.zshenv` for an earlier build, delete that line. If you
  installed notmuch for mail (section 5), it is yours: `brew uninstall notmuch`. Mail
  setup never touched a notmuch config or database of your own, so there is nothing
  of yours to undo; the profile it wrote goes with the mail in part B. **NOT YET.**

**Did you go off the install path?** If you ran one of these, undo it now, with its own
verb. Step 5 removes the `session` command these verbs need, and the pane-state job
runs that command, so launchd would keep it loaded on a missing file. **NOT YET**, and
each is newer than 0.1.0:

- `session pane-state agent on`: run `session pane-state agent off`.
- `session sound engine on`: run `session sound engine off --purge`. Without
  `--purge` the engine it built stays in `~/.local/share/sessiontools/sound/bin/`.
  Their logs stay in `~/Library/Logs/sessiontools/`: they are your data, so delete
  that folder by hand only if you want them gone.
- `ears services install --apple`: step 4's uninstall covers it.
- `session statusline install`: no verb removes it yet. It wrote two files in
  `~/.sessionkit/tools/settings/`: `statusline.sh` and
  `claude-code.d/50-statusline.json`. It also left a `.bak-<date>-<time>` copy beside
  each file it replaced. That copy is the file you had before, so move it back if you
  want it. Nothing runs these files once step 5 removes `session`. They are settings,
  so part B's **Settings** item deletes them, with the copies. It leaves
  `claude-code.json` alone: it is yours.
- `sessionview-install` linked sessionview's tools into `~/.local/bin`, and
  `sessionview-app-install` put an app in `~/Applications`. No verb reverses either.
  `find ~/.local/bin -type l -lname '*sessionview*'` lists the links to delete.

**5. The plugins and the kit command (sections 3 and 2).** After step 4, with no
`claude` session running, run both of these. Neither needs the other, so either order
works:

- `uv tool uninstall sessionkit`
- `claude plugin marketplace remove <r>` for each of the five (this removes the plugin
  too)

**MEASURED** (2030-06-09, Claude Code 2.1.301, one plugin, on a temporary home
directory and Claude Code config directory): `claude plugin marketplace remove`
uninstalled its plugin too (`Also uninstalled 1 plugin from this marketplace`), and
`claude plugin list` then printed `No plugins installed.` **The plugin's cached copy
stayed.** `~/.claude/plugins/cache/<r>/` was still there, marked `.orphaned_at`. This
loop removes the five copies now. **NOT YET**: the loop has not run.

```bash
for r in sessionmail sessiontools sessionphone sessionvoice sessionview; do
  rm -rf "${HOME:?}/.claude/plugins/cache/${r:?}"
done
claude plugin list
```

If `claude plugin list` still shows one of the five, `claude plugin uninstall <r>@<r>`
removes it by name. **MEASURED** (2030-06-09, uv 0.13.0, the kit from PyPI, on
temporary uv tool directories): `uv tool uninstall sessionkit` printed
`Uninstalled 9 executables` and removed the kit's tool environment.

**6. What the programs left (PROGRAM: none of it is your data).** No verb removes these
yet, so they are hand `rm` lines. **NOT YET.** In order, they delete the voice model and
the keeper's run state, the speech server's venv (which step 4 keeps), the sidebar's
state under its name and under its old one, the call listeners' run state and logs, the
cache the `memory` command keeps, and the voice's list of audio devices. The last line
removes that list's folder only if it is empty.

The lines in this section carry no comments, so paste them as they are. In zsh, the
Mac's own shell, a `#` typed at the prompt is not a comment: the words after it would
go to `rm` as more paths to delete.

```bash
rm -rf "${HOME:?}/.cache/ears"
rm -rf "${HOME:?}/.local/share/ears/speech"
rm -rf "${HOME:?}/.local/state/sessionview"
rm -rf "${HOME:?}/.local/state/herd"
rm -rf "${HOME:?}/.local/state/ears"
rm -rf "${HOME:?}/.cache/session-mail"
rm -f "${HOME:?}/.local/state/audio/devices.json"
rmdir "${HOME:?}/.local/state/audio"
```

The voice keeps a list of the Mac's audio devices in `~/.local/state/audio/devices.json`.
Other tools may read and write that file too, and the folder's name is not the kit's
own, so these lines delete only that file. The folder goes only if nothing else is in
it: if `rmdir` says `Directory not empty`, leave it.

`~/.cache/ears/silero_vad.onnx` may be a link to VoiceMode's copy of the model. If it
is, the first line removes the link, not VoiceMode's file. The kit's settings folders
also hold program files (schemas and templates), but they sit beside the choices you
made, so they go with those in part B.

The sidebar keeps its state in `~/.local/state/sessionview`. It moves the folder there from
`~/.local/state/herd`, its old name, the first time it runs, so the `herd` line finds that
folder only if the move never ran, or a sidebar started under the old name kept writing there.

**7. What stays.** Homebrew, uv, Claude Code and uv's Python 3.14 (sections 1 and 2) are
not the kit's, and other tools may use them. So are Claude Code's own folders, such as
`~/.claude` and `~/.local/state/claude`: leave them. Remove uv's Python with
`uv python uninstall 3.14` only if nothing else needs it. Never delete `~/.local/bin`,
`~/.cache`, `~/.sessionkit` or `~/.voicemode` whole: other tools keep files there. The
speech models the voice's speech server fetched stay in the Hugging Face cache, which
other tools share: `~/.cache/huggingface/hub`, unless you set `HF_HUB_CACHE` or
`HF_HOME`. Never delete it whole.
**NOT YET.**

### B. Delete your data (USER DATA, opt-in)

**Only if you want it gone. This cannot be undone.** Part A kept all of it. Each item
below deletes one kind of data: skip an item to keep that data, and copy anything you
want first. No child ships a verb for any of it yet. **NOT YET**: none of these lines
has run.

- **Mail:** every agent's mailbox, the notmuch index of them, and the mouth's queue of
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

  If you do not use VoiceMode, the mouth's box is the kit's alone: delete it with the
  lines below. If you do, keep it: VoiceMode's mouth speaks from it, and these lines
  would delete its queue. The lines sessionvoice's mouth spoke then stay in that box,
  beside VoiceMode's, until you delete it.

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
  profile for it: its first run said `wrote` on its `notmuch-profile` line, and you
  then ran section 5's `notmuch new`. If that line said `MANUAL`, the database was in
  the mail folder before the kit: it is yours, so leave it. If you cannot tell, leave
  it. The last `rmdir` then prints `Directory not empty`, and the folder stays. It
  prints the same if you kept the mouth's box.

  ```bash
  rm -rf "${HOME:?}/.mail/.notmuch"
  rmdir "${HOME:?}/.mail"
  ```

- **Session records:** what each session read, its address, its logs, the session
  list's saved state, and the older seat home. On a host that ran `session` before
  its agents folder moved, `~/.session/agents` may still hold a link for each agent.
  These lines leave it, so the `rmdir` says `Directory not empty`: look in it, and
  delete it by hand if you want it gone.

  ```bash
  for d in agent seats sessions mail state; do rm -rf "${HOME:?}/.session/${d:?}"; done
  rmdir "${HOME:?}/.session"
  rm -rf "${HOME:?}/.sessionmail"
  ```

- **Accounts:** the `session` tool's account folder, `~/.sessionkit/tools/accounts/`,
  beside its settings folder. It holds the account registry (`accounts.json`: each
  account's name, its email and where its token is kept, never the token), the account
  config (`account-config.json`), the host ledger (`host-ledger.jsonl`), and the backups
  `session account use` made of each token it replaced (`token-file-backups/` and
  `keychain-backups/`). While `session account new` sets up a token, a scratch folder sits
  there too. ⚠️ **The backups are your account tokens.** Part A leaves this folder, and
  so does the **Settings** item below, so the uninstall leaves these tokens on disk until
  you run this line. It deletes the saved accounts and every token backup, and it cannot
  be undone: to keep your accounts, skip it. It does not touch the tokens where you keep
  them (the registry's sources: a file, `pass` or `passage`), or the Keychain item or
  token file you sign in from: those are yours. The folder is there only if you used
  `session account`.

  On a host that used `session account` before the account folder moved, the older
  account folder, `~/.config/sessiontools/`, may still be there, with the same kinds of
  files in it. ⚠️ **Its backups are your account tokens too.** The kit never writes
  there, and nothing else in this section deletes it, so the second line does. Like the
  first, it cannot be undone: to keep those accounts, skip it. It leaves the rest of
  `~/.config` alone.

  ```bash
  rm -rf "${HOME:?}/.sessionkit/tools/accounts"
  rm -rf "${HOME:?}/.config/sessiontools"
  ```

- **Settings:** the operator file that `sessionkit setup` wrote (section 2), the mail
  hooks switch, your voice choices, the seats your voice wakes and the sidebar's config.
  Each package keeps its settings in `~/.sessionkit/<package>/settings/`, and its state
  and secrets beside that folder, never in it (the tree specification,
  `openspec/specs/tree/spec.md`). The voice is the one exception today: the speech keys
  you may have saved, `stt.key` and `tts.key`, are in `~/.sessionkit/voice/settings/`
  itself, so this item deletes them with your voice choices. This item removes only the
  settings. The one folder
  beside them that the kit knows is the account folder, the item above. The first loop
  removes the mail, voice and view settings folders. The next two remove only the
  `session` and `sounds` files in `~/.sessionkit/tools/settings`, the hidden schema
  copies (`.session.schema.json`, `.sounds.schema.json`) included. The next two lines
  remove what `session statusline install` wrote there, if you ran it:
  `statusline.sh`, `claude-code.d/50-statusline.json`, and the `.bak-` copies of the
  files it replaced. All of these leave `claude-code.json` there alone: `session start`
  reads it, but nothing in the kit writes it, so anything in it is yours. The `rmdir`
  lines remove a folder only if it is empty. If one says `Directory not empty`, that
  folder still holds files the kit did not write, or the account folder you kept: leave
  them. If one says
  `No such file or directory`, there was nothing there to remove: voice saves no
  settings until section 5, the sidebar makes its file only when it first runs, and
  `claude-code.d` is there only if you ran `session statusline install`.

  ```bash
  for d in mail voice view; do rm -rf "${HOME:?}/.sessionkit/${d:?}/settings"; done
  for f in session.json session.d session.template.json session.schema.json .session.schema.json; do rm -rf "${HOME:?}/.sessionkit/tools/settings/${f:?}"; done
  for f in sounds.json sounds.d sounds.template.json sounds.schema.json .sounds.schema.json; do rm -rf "${HOME:?}/.sessionkit/tools/settings/${f:?}"; done
  rm -f "${HOME:?}/.sessionkit/tools/settings/statusline.sh" "${HOME:?}/.sessionkit/tools/settings/claude-code.d/50-statusline.json"
  find "${HOME:?}/.sessionkit/tools/settings" -maxdepth 2 \( -name 'statusline.sh.bak-*' -o -name '50-statusline.json.bak-*' \) -print -delete
  rmdir "${HOME:?}/.sessionkit/tools/settings/claude-code.d"
  rmdir "${HOME:?}/.sessionkit/tools/settings"
  for d in mail voice view tools; do rmdir "${HOME:?}/.sessionkit/${d:?}"; done
  rmdir "${HOME:?}/.sessionkit"
  ```

- **Voice:** what the ears heard and the mouth said. That is the transcript of every
  turn the ears heard (`heard_*.jsonl`), who spoke each turn (`speakers_*.jsonl`), each
  session's place in that transcript, the voice's pairing token (`talk/token`), and
  every line the mouth spoke, which it keeps by default. If you turned recording on (it
  is off by default), it is also the audio the ears kept of each turn and the clips of
  replies they missed. Then the speakers' home with the voices you enrolled, and the
  service logs.

  On a fresh install all of it but the last two is in `~/.sessionvoice`, sessionvoice's
  own folder, so the first line deletes that folder whole. `~/.ears` holds the place
  `ears-arm` (section 5 step 4) keeps in the transcript.

  ```bash
  rm -rf "${HOME:?}/.sessionvoice" "${HOME:?}/.ears"
  rm -rf "${HOME:?}/.local/share/ears" "${HOME:?}/Library/Logs/ears"
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
  too. If you do not use VoiceMode, delete them with the lines below. If you do, keep
  them: these lines would delete VoiceMode's own transcript, and the places it kept
  would then point past the end of it. The turns sessionvoice heard then stay in that
  transcript, beside VoiceMode's, until you delete it.

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

- **Phone:** the agent's chat account with its keys, the invite, the callers and the
  bot's logs. Run step 3 first. The account on the public relay is not on this Mac,
  and nothing here deletes it. On your phone, delete the agent's chat in Delta Chat
  yourself.

  ```bash
  rm -rf "${HOME:?}/.sessionphone"
  ```

- **Your clones** (section 3), only after step 5: a plugin breaks when its clone goes
  (section 7). If you changed anything in them, run `git status` in each first. This deletes
  the folder section 3 clones into, `~/.local/share/sessionkit/src`, by its full name.
  If you cloned somewhere else, these lines miss those clones: delete them there by
  hand, one at a time.

  ```bash
  rm -rf "${HOME:?}/.local/share/sessionkit/src"
  rmdir "${HOME:?}/.local/share/sessionkit"
  ```

  The last line removes `~/.local/share/sessionkit` only if it is empty.

[lid]: docs/troubleshooting.md#ears-running-but-deaf
[sv-hosted]: https://github.com/sessionkit/sessionvoice/blob/HEAD/docs/models.md#a-hosted-speech-endpoint-instead
