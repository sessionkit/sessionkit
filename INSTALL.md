# Install: from a fresh Mac to an agent that hears you and speaks

**Status: DRAFT, alpha.** Every step is tagged **MEASURED** (it ran, on the machine
and date given), **NOT YET** (not run, or blocked), and **HUMAN** where you must type a
password, answer a prompt, sign in, or edit a file. The measurements come from a
rehearsal of this install, most of them on a fresh macOS 27 virtual machine.

What works today: the commands (mail, sessions, pager, memory, phone, ears,
mouth), the plugins, and the mouth (it falls back to macOS `say`). What is still
limited: hearing needs a speech server, which sessionvoice's `ears services install`
installs for you (section 5); agent-to-agent mail goes by sessionmail's experimental
file drop, its default carrier, on this Mac only (section 5). Phone calls are
installed, and walked on a fresh Mac for a session started with `session start <name>`
(section 6). A plain `claude` session does not hear calls you make to it yet.

## 1. Prerequisites (HUMAN)

**NOT YET** as a whole; each line below was timed on a fresh macOS 27 VM.

- Homebrew, the installer from <https://brew.sh>:

  ```bash
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
  ```

  **HUMAN: your password** at sudo. It installs the Command Line Tools itself. Then run
  the three lines it prints under "Next steps", as printed (two `echo ... >> ~/.zprofile`
  and one `eval ...`), so `brew` is on your PATH. **MEASURED** (2030-06-09, two
  fresh macOS 27 VMs): 87 to 220 seconds with the Command Line Tools, and a new
  terminal had `brew` and `git`.
- uv: `curl -LsSf https://astral.sh/uv/install.sh | sh` (about 1 second). Then open a
  new terminal, or run `source ~/.local/bin/env`: until you do, `uv` is not on your PATH
  (`command not found: uv`, exit 127).
- Claude Code: `curl -fsSL https://claude.ai/install.sh | bash` (about 13 seconds), then
  start `claude` and **HUMAN: sign in** with `/login`.
- At least 2.1 GB free disk, plus about 3.9 GB for the speech-to-text server
  (section 5): its venv, 1.2 GB, and its models, 2.7 GB.
  **MEASURED** (on the VM where Homebrew took 220 seconds): the Command Line Tools took 1.3 GB, the kit about 280 MB, Claude
  Code 230 MB, Homebrew 204 MB and uv's Python 74 MB. A fresh VM started with 9.7 GB
  free and ended with 8.7 GB.

  **The first call is silent for about a minute.** The server fetches its models into
  the Hugging Face cache on its first request, not at install. Until they are in, your
  agent neither hears nor speaks through it: on a phone call, nothing is heard for
  about a minute. **MEASURED** (2030-06-09, a fresh macOS 27 VM, the first phone call
  after `ears services install`): the venv 1.2 GB and the models 2.7 GB. The first
  spoken line took 65.1 seconds and the first heard speech 60.2 seconds; after that,
  a median of 0.4 seconds to speak a line and 0.3 seconds to hear a stretch of speech.
- Python 3.11 or later (uv fetches one if you have none).
- A network connection: the install is online-only. It fetches from PyPI, uv
  downloads its Python, and `ears install` downloads the voice-activity model.

## 2. Install the kit

```bash
uv tool install --python 3.14 sessionkit
sessionkit setup
```

**Keep `--python 3.14`.** Without it, uv fetches Python 3.15, where the kit cannot
install: a voice library it needs (onnxruntime) has no 3.15 build yet. uv refuses,
exit 1, with `your requirements are unsatisfiable`, and installs nothing. **MEASURED**
(2030-06-09, uv 0.13.4 with empty uv folders and only uv's own Python, as on a fresh
Mac): `uv tool install sessionkit` fetched CPython 3.15.0, then refused, exit 1, and no
tool was installed. On a Mac that already has the Command Line Tools, uv may pick their
older Python instead, which the family is not tested on (3.11 on a fresh macOS 27 VM,
2030-06-09). Either way, keep `--python 3.14`.

**To upgrade or reinstall, keep the pin.** These two lines are safe on their own:

```bash
uv tool upgrade sessionkit
uv tool install --python 3.14 --reinstall sessionkit
```

`uv tool upgrade` keeps the Python the install chose. A reinstall without
`--python 3.14` drops the pin from uv's record of the tool, and
`uv tool install --force sessionkit` builds the kit again on the Python uv finds.
**MEASURED** (uv 0.13.4, sessionkit 0.2.1 from PyPI, in an empty tool folder with an empty
uv cache, each line run on a fresh `--python 3.14` install, read in the tool's
`pyvenv.cfg` and `uv-receipt.toml`):
- `uv tool upgrade sessionkit`, with or without `--reinstall`, and `uv tool upgrade --all`
  stayed on 3.14 with the pin kept.
- `uv tool install --python 3.14 --reinstall sessionkit` stayed on 3.14 with the pin kept.
- `uv tool install --reinstall sessionkit` stayed on 3.14 but dropped the pin.
- `uv tool install --force sessionkit` rebuilt the kit on 3.13 where that was uv's first
  Python. Where Homebrew's 3.15 was first, it refused (no 3.15 build of a voice library),
  exit 1, and left the 3.14 install as it was.
- `uv tool upgrade` has no `--refresh` on uv 0.13.4: it refuses that flag, exit 2.

**MEASURED** (2030-06-09, read-only against PyPI): the five packages this release
needs are on PyPI: sessionmail, sessionphone and sessionvoice 0.2.1, sessiontools and
sessionview 0.2.0. This line installs the kit and its five packages, 61 packages in all, and
14 commands on your PATH:
`sessionkit message pager memory session sessionphone sessionview sessionview-config
sessionview-messages sessionview-session ears ears-serve mouth talk`. **MEASURED**
(2030-06-09, the kit built from this release's source with those five packages
from PyPI, Python 3.14, an empty tool folder and an empty uv cache): 61 packages, the
14 commands, and every `--help` answers.

**The install size.** **MEASURED** (the same install, on Apple silicon): uv downloaded
about 93 MB, and the kit's tool folder is about 280 MB on disk. uv's own Python is not in
that folder; section 1 counts it.

**Phone calls are installed, and walked for a session started with
`session start <name>`.** A plain `claude` session does not hear calls you make to it
yet. The kit installs sessionphone with its calls packages (its `media` extra: aiortc,
av and 8 more). They download with everything else, during `uv tool install`, with no
separate step: 10 of the 61 packages, about 21 MB of the download and about 52 MB of
the 280 MB. **MEASURED** (the same install, the files those 10 packages install).
Setting them up is section 6, which a fresh Mac has walked for a session started with
`session start <name>`.

**On Linux** (untested), the voice package needs the system PortAudio library
(Debian and Ubuntu: `libportaudio2`). sessionvoice 0.2.1 depends on `sounddevice`,
whose Linux wheel brings no PortAudio; its macOS and Windows wheels do (read on
PyPI, 2030-06-09).

Open a new terminal (or run `uv tool update-shell`) so they are on your PATH.

**`sessionkit setup` sets up mail on this Mac, then names you as the operator**: the
human your agents ask. It is the last line of the block, so if it stops, nothing after
it is skipped. If the shell says `command not found`, open a new terminal and run it
there.

**Mail first.** It runs sessionmail's mail setup, `message setup`, which makes the mail
folder and your box and says what is left for you
([Mail between agents](#mail-between-agents), section 5, step 4). On a fresh install
your box is named for your account; with `--mailbox NAME` it makes that box too, and
your assistant's box (below), and no other. Then it writes the operator: your box, or
the address you gave with `--address`, and reads it back through `session operator`.

**On a fresh Mac it exits 4, and that is expected.** Mail setup makes your box and
its notmuch profile, and leaves its notmuch step `BLOCKED` until you install notmuch
(section 5, step 4). The operator is written all the same. The last lines read like
this:

```text
message setup: done what it can; 1 step(s) left for you: notmuch-hook (BLOCKED)
Mail setup left steps for you (above); re-run sessionkit setup after.
Wrote /Users/<you>/.sessionkit/tools/settings/session.d/10-operator.json: the operator is address '<you>@<your-mac>'.
session operator: {"operator": "<you>@<your-mac>", "mailbox": null, "privileged": ["<you>@<your-mac>"]}
Wrote /Users/<you>/.session/agents/claude.md: the agent 'claude', not keyed.
session start --list-agents: lists 'claude'.
To hear Delta messages, start Claude with: session start claude
```

**MEASURED** (2030-06-09, a fresh macOS 27 VM, sessionkit 0.2.0 and sessionmail 0.2.0
from PyPI, run with `--address`): the first four lines, exit 4. The last three are
this release's assistant step (below), which sessionkit 0.2.0 does not have. **MEASURED**
(2030-06-09, this release's sessionkit with the five 0.2.0 packages from PyPI, a
temporary home directory, run with `--address`): the last three lines, exit 4, and
`session start --list-agents` lists `claude`. **NOT YET** run on a fresh Mac. Without `--address` it writes your box, the one
named for your account, as the operator (read in its source). **NOT YET** on a fresh
Mac without `--address`.

**Then your assistant:** it writes `~/.session/agents/claude.md`, the agent
`session start claude` starts (section 4), and asks mail setup for its box, `claude`.

**Then it checks the ears' model, and only reads.** It asks `ears backends` whether the
ears' voice-activity model is there. If it is not, which is so on a fresh Mac until
`ears install` (section 4), it prints one line just before the launch step:
``The ears have no voice-activity model, so they cannot hear you: run `ears install` to fetch it.``
It never runs `ears install` itself, and the line never changes its exit. With no `ears`
on the PATH, or no answer from it within 5 seconds, it says nothing about the model.
**MEASURED** by the test suite only, against a stand-in for `ears backends` that prints
what sessionvoice 0.2.1's does.

**Its exit:** 0 all done; 1 the operator or the agent file was refused, or a mail step
failed or was refused (it says which, and the rest still ran); 2 a flag it does not take; 4 the
operator is set and mail steps are left for you, named in its output. Run it again
once you have done them: it leaves the operator it wrote alone.

**A dry run writes nothing, so its exit says what a real run would meet.** Mail
setup's dry run exits 4 while any of its steps is still to do, and 0 only once every
step is done. So with `--dry-run`, 4 means mail steps are still to do and the operator
check did not refuse (your box is there, or you gave `--address`, or an operator is
already set): nothing is set yet, and the real run does what it can and names the
rest. On a fresh install mail setup has not made your box, so the operator check after
it refuses too: `sessionkit setup --dry-run` exits 1 there, and the real run is what
makes the box. **MEASURED** (2030-06-09, sessionkit setup and sessionmail 0.2.0):
`sessionkit setup --dry-run` exited 4 on a fresh macOS 27 VM with `--address`, and 1
on a fresh temporary home directory without it, and made nothing either time.

If it refuses, run it again with `--address` followed by your own email address, or
with `--mailbox` followed by a box name that `message box path` finds. Add `--dry-run`
to see the file it would write, and write nothing. A sessionmail older than the kit
asks for, with no mail setup, gets the step printed instead: it says it has no
`message setup` and names the step, and the operator half still runs.

**MEASURED** (2030-06-09, by the test suite, and on temporary home directories): the
refusal, `--address`, `--mailbox`, a re-run that writes nothing, and the read-back.
On a fresh Mac, only the run with `--address` above.

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
  (2030-06-09, temporary home, `session operator` from sessiontools 0.2.0): a `20-` file's list was
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
its own, installs an empty placeholder. Each installs its real package now, 0.2.0 on
PyPI (read on PyPI, 2030-06-09), and `sessionkit` brings both anyway.

## 3. Install the plugins

Run these after the Command Line Tools are in (section 1): the marketplace line clones
over git.

```bash
claude plugin marketplace add sessionkit/sessionkit
claude plugin install sessionkit@sessionkit
claude plugin list
```

They install the kit's plugin and the five family plugins it depends on.
`claude plugin list` should show six plugins, each `✔ enabled`, scope user: `sessionkit`, `sessionmail`, `sessionphone`, `sessiontools`,
`sessionview` and `sessionvoice`, each `@sessionkit`.

**MEASURED** (0.2.0, Claude Code 2.1.304, an empty Claude Code config, not signed in):
both lines exited 0, and the list showed all six at 0.2.0, enabled.

**Then quit Claude Code and start it again**, every window of it, before any step
below. This holds for the clones route too. A plugin installed from the shell loads
the next time Claude Code starts (or on `/reload-plugins` in a session already open,
read in Claude Code's plugin docs). Until then, a session that was open has none of
the plugins' commands on its PATH, such as `ears-arm` (section 5), and none of their
hooks or their monitor (section 4). **NOT YET** walked as a step. On one install that
went on in the session already open, a plugin's command was not found.

**The plugins run from a copy.** The install copies each plugin to
`~/.claude/plugins/cache/sessionkit/<name>/<version>/`, and that copy is what runs. Its
`bin/` and `skills/` are the paths section 5 needs. **MEASURED**
(`~/.claude/plugins/installed_plugins.json` gives each plugin's `installPath` there).

**Installed the five from clones before?** Remove those first, or the same plugin loads
twice: `claude plugin marketplace remove <r>` for each of the five. **MEASURED** (0.2.0):
with `sessionmail@sessionmail` from a clone and `sessionmail@sessionkit` both installed,
`claude plugin list` showed both `✔ enabled`.

### A session started with `--setting-sources ""`

That session reads no settings file, so none of the six load unless you name them. The
supported way is `--settings <file>` with the six in its `enabledPlugins`:

```json
{"enabledPlugins": {"sessionkit@sessionkit": true, "sessionmail@sessionkit": true,
  "sessionphone@sessionkit": true, "sessiontools@sessionkit": true,
  "sessionview@sessionkit": true, "sessionvoice@sessionkit": true}}
```

- **Name all six.** The kit's plugin stays off unless the five it depends on are enabled
  too, and the error says `Dependency "sessionmail@sessionkit" is not installed` even
  when it is installed.
- **A `--plugin-dir` holding a plugin of the same name replaces the installed one** for
  that session, wholly. None of the installed copy's skills, commands or hooks load.
  `--plugin-dir` at the install's cache copy does load a plugin, but from a path that
  names its version.

**MEASURED** (Claude Code 2.1.309), on other installed plugins: `enabledPlugins` in
`--settings` loaded their skills, commands and hooks, and the hooks ran. With no
`--settings`, nothing loaded. A same-name `--plugin-dir` replaced the installed plugin,
and a plugin with an unlisted dependency stayed off. On the kit's own plugin,
`enabledPlugins` reached it, and it then stopped at the dependency check. **NOT YET**
walked with all six installed.

### From your own clones, to work on the plugins (optional)

Only if you are changing a family plugin. Use this INSTEAD of the lines above, not
beside them: one plugin from two places loads twice, and removing the kit's copy leaves
the kit's plugin with `Dependency "sessionmail@sessionkit" is not installed` (**MEASURED**,
0.2.0).

Keep the clones in ONE directory you will not move (moving one breaks its plugin; see
the end of this section). The block below calls it `$SRC`. Clone each of the five into
it with `git clone -b master https://github.com/sessionkit/<name> "$SRC/<name>"`, where
`<name>` is each name the loop lists.

```bash
SRC=~/.local/share/sessionkit/src   # clone the repos here; do NOT move them afterwards
for r in sessionmail sessiontools sessionphone sessionvoice sessionview; do
  claude plugin marketplace add "$SRC/$r" && claude plugin install "$r@$r"
done
claude plugin list
```

You should see five plugins, each `✔ enabled`, scope user, each `Read from: <SRC>/<r>`.
**MEASURED** (0.2.0, Claude Code 2.1.304, an empty Claude Code config, clones of the
public repositories made with `-b master`): five of five, all 0.2.0. Each runs from its
copy in `~/.claude/plugins/cache/<r>/<r>/<version>/`, not from the clone.

**The block exits 0 even when nothing installed, so read `claude plugin list`.**
**MEASURED** (in the release rehearsal): with no clones in `$SRC`, the loop printed
`✘ Path does not exist: <SRC>/sessionmail` and the like for each name, the list printed
`No plugins installed.`, and the block still exited 0.

**Fewer than five?** Read the line the loop printed for each missing one:

- `Path does not exist: <SRC>/<r>`: there is no clone there. Clone it to `$SRC/<r>`.
- `Marketplace file not found at <SRC>/<r>/.claude-plugin/marketplace.json`: the clone
  is there, but nothing is checked out. Delete that clone and clone it again with
  `-b master`, the branch the public repositories are on. **MEASURED** (in the release
  rehearsal: a clone with nothing checked out gave this; cloned again with its branch
  named, it installed).

Then run the loop's line for that one, with `r` set to its name (`r=sessionmail`, for
example): `claude plugin marketplace add "$SRC/$r" && claude plugin install "$r@$r"`.

**If a clone moves, its plugin breaks silently** (`claude plugin list` still exits 0;
**MEASURED**). Repair, also measured: `claude plugin marketplace remove <r>`, then
`claude plugin marketplace add <new path>` and `claude plugin install <r>@<r>`. The remove
drops that plugin's saved options.

## 4. First checks

- `ears install`: fetches the voice-activity model to `~/.cache/ears/silero_vad.onnx`
  (network, no sudo). **MEASURED** (in the release rehearsal).
- Start Claude with `session start claude` in the directory you will work from. It is the
  one launch step `sessionkit setup` ends with (section 2):

  ```text
  To hear Delta messages, start Claude with: session start claude
  ```

  It starts Claude as the agent `claude`, so the session hears mail to the box `claude`,
  the box your phone's Delta messages are addressed to; a bare `claude` hears only its
  own session's box. The cost: **two windows started as `claude` share one box**, so mail
  to it pages both and both may answer. For a second assistant, pick another name:
  `sessionkit setup --agent NAME`, then `session start NAME`. `claude` is Claude Code's
  own built-in agent, so the file setup wrote only lets `session start` find it, and its
  text does nothing; under any other name the file's text is your assistant's prompt.
  **MEASURED** (2030-06-09, sessiontools 0.1.0, a temporary home directory): before
  `sessionkit setup`, `session start --dry-run claude` stopped with
  `agent 'claude' not found`, exit 2; after it, the command was
  `claude --session-id <a new id> ... --agent claude`, exit 0. **MEASURED**, walked and
  passed (2030-06-09, a fresh macOS 27 VM, this release's kit with sessionmail,
  sessionphone and sessionvoice 0.2.1): Delta messages and a phone call reached a
  session started with `session start claude`. Each turn was mailed to the box
  `claude` and woke the session, which answered aloud. The sessionmail plugin's
  hooks run clean, and your mailbox under `~/.mail/agents/` is created the first time the
  pager listens. **MEASURED** in part (in the release rehearsal). The hooks stay off until you set
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
- **Claude Code's auto mode can refuse your agent's `message send`.** From Claude Code
  2.1.283, an interactive session starts in auto mode: a second model, the classifier,
  reviews each command before it runs. Mail that asks another agent to act can be
  refused with this line:

  ```text
  Permission for this action was denied by the Claude Code auto mode classifier. Reason: [Create Unsafe Agents].
  ```

  **MEASURED** (2030-06-09, a fresh macOS 27 VM: an agent's `message send` that asked a
  second agent to act). There are two fixes. Both are read in Claude Code's documentation
  on permission modes and permission rules, and neither has been walked:
  - **Allow the command.** Add this permission rule to the `.claude/settings.local.json`
    that section 5, step 3 edits (it says where that file is), beside any `hooks` there:

    ```json
    {"permissions": {"allow": ["Bash(message send *)"]}}
    ```

    In auto mode an allow rule is checked before the classifier, so a command that
    matches it runs without the classifier's review. The rule covers `message send` as a
    command of its own. If the command is joined to another one with `&&`, `;` or `|`,
    the other part needs a rule too. To allow it in every directory, put the rule in
    `~/.claude/settings.json` instead. The cost: your agent's mail then goes out with no
    review.
  - **Leave auto mode.** Press Shift+Tab. From auto mode, the first press switches to
    Manual mode, which asks you before each command, and the status bar shows
    `⏸ manual mode on`. Further presses cycle through accept edits, plan and auto. To
    start every session in Manual mode, set `{"permissions": {"defaultMode": "default"}}`
    in `~/.claude/settings.json`.

  To let one refused command through, run `/permissions`, open the **Recently denied**
  tab, and press `r` on the command.
- The sessionmail plugin's monitor arms the pager for the whole session, and it is on by
  default. Section 3 installs it: the plugin's `monitors/monitors.json` runs
  `pager listen --monitor` with the `pager` on your PATH, so you do not turn anything on.
  The sessionmail plugin section 3 installs, 0.2.0, has that `monitors/monitors.json`
  (read in its public repository, 2030-06-09); its 0.1.0 plugin had none. **MEASURED** (2030-06-09, a fresh macOS 27 VM, sessionkit
  0.2.0 and sessionmail 0.2.0 from PyPI, the plugins installed in one step, an
  interactive `claude`): Claude Code showed `1 monitor`, and `pager status` said
  `monitor: armed (pid <n>); switch: on (the default: no switch is set)`. Claude Code runs a plugin's monitor only in an interactive session
  (never `claude -p`), with the folder trusted, and only while its own monitor gate is
  on. When it does not run it, nothing in Claude Code says so (sessionmail's
  `docs/pager-monitor.md`; the trust condition is from the README of its retired
  `plugins/pager-monitor`). sessionmail's off switch (`"monitor": false` in
  `~/.sessionkit/mail/settings/mail.json`, or `SESSIONMAIL_MONITOR=off` at launch) and
  `pager mute` / `pager unmute` ship in sessionmail 0.2.0, the release the kit installs;
  the 0.1.0 `pager`, before the kit floored it at 0.2.0, had none of them. **MEASURED**
  (2030-06-09, sessionmail 0.2.0 from PyPI, a temporary home directory): `pager --help`
  lists `mute` and `unmute`, and each answers its `--help`; the off switch is read in its
  source. With no
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
3. **Start your first agent** inside it: `session start claude`. It starts Claude in
   this window as the agent `claude`, the one `sessionkit setup` wrote (section 2),
   under a new session id. To hear Delta messages, start Claude with: session start
   claude. Two windows started as `claude` share one box (the checks above); a second
   assistant gets its own name with `sessionkit setup --agent NAME`.
   `session start --dry-run` before the name (`session start --dry-run claude`) prints
   the command and starts nothing. Launcher flags go before the name: everything after
   it is handed to `claude` itself, so `session start claude --dry-run` refuses, names
   the right order and exits 2. With no name, `session start` starts a plain `claude`
   session, and running `claude` yourself works too, but neither hears mail to the box
   `claude`. From outside tmux, `session start --tmux-target agents claude` puts the
   agent in a new window named `claude`. **MEASURED** only as `--dry-run` and refusals
   (2030-06-09, 0.1.0, on a temporary home directory): with no name the command was
   `claude --session-id <a new id>`, and with `claude` it ended `--agent claude`, exit
   0 each. With `--tmux-target agents claude`, it gave
   `tmux window 'claude' in session 'agents'`. `session start claude --dry-run`
   refused, exit 2, and launched nothing. From outside tmux with no target,
   `session start --in-tmux` stopped with `nowhere to place the window`, exit 2.
4. **Have it listen.** Turn the mail hooks on first (`"hooks": true`, in the checks
   above). After that, the pager's hook tells your agent when it is not listening, and
   the agent starts `pager listen` itself, as a background tool call. You can also ask
   it to. The banner says whether mail reaches the agent's box. `pager status`, run by
   the agent, reads that box. **NOT YET.**
5. **Mail it.** From sessionmail 0.2.0, the release the kit installs, `message send`
   goes by the experimental file drop with nothing to set, on this Mac only: see
   [Mail between agents](#mail-between-agents) in section 5. **MEASURED** (2030-06-09,
   a fresh macOS 27 VM, sessionkit 0.2.0 and sessionmail 0.2.0 from PyPI, inside a
   `claude` session, no postfix): `message send admin` printed
   `sent via mail drop (no MTA)`, exit 0, and `message list admin` showed it. Send from
   your agent: in a plain terminal it refuses (the checks above). **NOT YET** as mail from
   one agent to another on a fresh Mac. The voice path in section 5 does not need mail.

## 5. Hearing and speaking ("it hears me and speaks")

None of these ran end to end in the rehearsal. Each is **NOT YET** unless a line says
otherwise.

Steps 1 and 2 are sessionvoice **0.2.1**, the release section 2 installs. They were
read in sessionvoice's source, and dry-run on sessionvoice 0.2.1 from PyPI.

**The job labels.** Every launchd job in the session family is labelled
`dev.sessionkit.<package>.<job>`. The voice's are `dev.sessionkit.voice.mlx-audio`
for the speech server and `dev.sessionkit.voice.ears-<name>` for the rest. Two
older forms are history: `com.sessionvoice.*`, which earlier copies of this guide
named, and `com.voicemode.ears-*`, which 0.1.0 loads. 0.2.1's
`ears services install` recognises a job under either old form and retires the old
form: it moves the job off before it loads the new label. **MEASURED** (2030-06-09,
sessionvoice 0.2.1 from PyPI, `ears services install --dry-run`, a temporary home
directory, nothing on 8890, `uv` on the PATH): the four plists it would write are
`dev.sessionkit.voice.mlx-audio`, `dev.sessionkit.voice.ears-mouth`,
`dev.sessionkit.voice.ears-keeper` and `dev.sessionkit.voice.ears-mail`, and it wrote
nothing. It exited 2, `silero MISSING`, because `ears install` had not fetched the
voice-activity model (step 2). The old forms are in the package only as the forms it retires (read in its
source).

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
     package. A real install ran on a fresh macOS 27 VM (2030-06-09, below), with
     no microphone: **NOT YET** on real audio.

     Give it `--agent` and your agent's name, `claude` unless you named another
     with `sessionkit setup --agent`:

     ```bash
     ears services install --agent <name>
     ```

     Without `--agent`, nobody is woken when you speak. `--agent` makes that agent
     the one your voice wakes (`ears wake add <name>`), and sends it the keeper's
     notices. A bare install warns
     `no --agent NAME: NOBODY will be woken when you speak` and installs anyway.
     **MEASURED** (2030-06-09, a fresh macOS 27 VM, a real install): a bare install
     printed that warning. **MEASURED** as `--dry-run` (2030-06-09, sessionvoice 0.2.1 from PyPI,
     a temporary home directory): bare, the same warning; with `--agent claude`,
     `would add claude` to the wake file, and the keeper's notices to `claude`.

     Install ends with a `heard` line: an agent hears heard turns only once it
     subscribes to `heard+<device>` (`heard+macbook` for the built-in mic). That is
     the mail path, and this guide leaves it for later: your agent wakes on your
     voice through steps 3 and 4. If you take the mail path, your agent's
     `message subscription add heard+macbook` is refused, exit 2, with
     `a seat's mail is that seat's to grant`, until your agent is an administrator.
     To make it one, name it in an administrators file, as in
     [Operator and administrators](#operator-and-administrators) (section 2), for
     example `{"operator": {"privileged": ["claude"]}}`, then subscribe again.
     **MEASURED** (2030-06-09, a fresh macOS 27 VM): the subscription was refused for
     the agent `claude`, exit 2. With that file in place, it went through, and the next
     heard turn reached the box `claude` and woke the session.

   On 0.2.0, a bare `ears services install`
   loads `speech`, `mouth`, `keeper` and `mail`. `--only` takes
   `stt`, `speech`, `mouth`, `keeper`, `mail` and `speakers`: `stt` (Apple's
   speech, section 6) loads only with `--apple` or `--only stt`, and `speakers`
   only with `--only speakers` (below). ears-mail is the job that
   turns a heard turn into mail that pages your agent. On 0.2.0 it hands its mail to
   `message send` (read in its source), so with sessionmail 0.2.0 it rides the file drop in
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
3. **The ride-along hook. HUMAN (hand edit).** In `.claude/settings.local.json`, add
   `ears heard hook || exit 1` on PostToolUse and PostToolBatch (**MEASURED** in the
   release rehearsal). It hands your agent what you said on its next tool call. Where
   the file is: if your launch directory is inside a git repository, Claude Code 2.1.211
   and later reads it at the repository's root, `<repository root>/.claude/`. Otherwise,
   or when that root is your home directory, it is in the launch directory itself,
   `<launch directory>/.claude/` (read in Claude Code's settings docs). If the file
   does not exist, paste this as the whole file:

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
   background, where `<seat>` is the name you call your agent by. `ears-arm` is
   on the Bash tool's PATH by its bare name while the sessionvoice plugin is
   enabled, through the plugin's `bin/ears-arm`. That shim runs
   `skills/ears/scripts/ears-arm`, and the full path still works. **NOT YET**
   on PATH (read in sessionvoice's source). **MEASURED** only as `--help`
   (2030-06-09, 0.2.0, a copy of its master): the shim runs the script.

   It runs the `heard-first` waiter. In room mode it wakes your agent when you say "hey"
   and its name (or "hey everyone"), when you answer the last thing your agent said, or
   when a line your agent is speaking gets cut off (you talk over it, or the speakers
   drop); a bare mention of its name does not wake it. Run it again each time it fires.
   **MEASURED** as `--dry-run` only (2030-06-09: it prints the `heard-first` command,
   with rules for "hey" plus the name or "everyone", a reply rule and a cut rule).
   **NOT YET** as a live wake.
5. **Test the mouth. HUMAN (speakers).** `mouth say --device default "ears are up"`.
   Without a server on 8890 it speaks with macOS `say` (**MEASURED** in the release
   rehearsal). The mouth can also speak through a hosted
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
Macs. The kit installs sessionmail 0.2.0 or later, so it has the drop.

**The file drop. EXPERIMENTAL.** sessionmail's own acceptance test of the drop on a bare
Mac has not run yet. Mail carried by the drop stays on this Mac. Each step below says
what was measured. The walk ran on sessionmail's code before its 0.2.0 release
(2030-06-09), with a temporary home directory, no postfix on the PATH, no tailscale and
no mail setting. Step 1 is the released 0.2.0, on a fresh Mac.

1. **Get sessionmail 0.2.0.** Section 2 installs it: the drop and mail setup (step 4)
   ship from sessionmail 0.2.0, and the kit asks for 0.2.0 or later. **MEASURED**
   (2030-06-09, a fresh macOS 27 VM, sessionkit 0.2.0 and sessionmail 0.2.0 from PyPI,
   inside a `claude` session, no postfix): `message send admin` printed
   `sent via mail drop (no MTA)`, exit 0, and `message list admin` showed it.
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

   From sessionvoice 0.2.1 and sessionphone 0.2.1, the releases the kit installs, all
   three hand their mail to `message send`, so they ride the drop, and from sessionmail
   0.2.0 a heard turn sent by the drop reads as your voice (read in their 0.2.1 source).
   Their 0.1.0 releases, before the kit floored them at 0.2.0, handed it to
   `/usr/sbin/sendmail` themselves. **NOT YET** walked: no launchd job has yet sent by
   the drop on a fresh Mac.
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
   It makes these boxes and no others: a box named for your account, the box you
   name with `sessionkit setup --mailbox NAME`, if you give one, and your assistant's
   box, `claude` (or the name you gave `--agent`). That last box is the one a session
   started with `session start claude` hears, and your Delta messages are addressed
   to it. The drop never makes a box. Mail to a box that does not exist is refused
   and nothing is delivered, to that box or any other (exit 3). A plain `claude`
   session's own box is made when its pager first listens (section 4). Make every
   other box that mail goes to with mail setup, for example:

   ```bash
   message setup --box <box>
   ```

   The sender needs no box of its own. **MEASURED** (2030-06-09, this release's
   sessionkit with sessionmail 0.2.0 from PyPI, a temporary home directory):
   `sessionkit setup --mailbox <box>` ran the real `message setup`, which made the
   mail folder, the operator's box, that box and `claude`, and wrote the notmuch
   profile; setup then wrote the operator, exit 4 (the notmuch step left);
   `message setup --box <box>` made one more box; a re-run reported each `DONE`,
   exit 0; a plain `sessionkit setup` passed `--box claude`,
   and the real `message setup` made the box `claude` beside the account's; mail to a box it had not made was refused, exit 3; and
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
  Homebrew).** Phone calls are installed, and walked on a fresh Mac for a session
  started with `session start <name>`. A plain `claude` session does not hear calls
  you make to it yet. Section 2's install already includes sessionphone and its calls
  packages, so there is nothing more to install from PyPI. Setting it up is sessionphone's: follow
  [its own docs](https://github.com/sessionkit/sessionphone). A call also needs
  `ffmpeg` from Homebrew and the speech server on 8890 (section 5).
  - **Signing follows the carrier.** From sessionphone 0.2.1, the bot's mail to your
    Claude is signed when the carrier sessionmail resolves for it is a mail server (an
    MTA), where it must be, or when you gave the bot a key. Under the drop,
    sessionmail's default, it goes straight into your own mailbox, as you, with no key
    to make. The carrier is the `sendmail` setting (section 5, step 2), not whether
    postfix is installed. The whole rule is sessionphone's:
    [bot mail signing](https://github.com/sessionkit/sessionphone/blob/HEAD/docs/bot-mail-signing.md).
  - **Two things decide whether its mail reaches your Claude.** The agent's box must
    exist, because the drop never makes one: `sessionkit setup` makes `claude`
    (section 5, step 4). And Claude must be started as that agent, with
    `session start claude` (section 4), never a bare `claude`, which hears only its
    own session's box.
  - **The first call is silent for about a minute** while the speech server fetches
    its models (section 1).
  - **MEASURED** end to end, walked and passed (2030-06-09, a fresh macOS 27 VM,
    this release's kit with sessionphone 0.2.1, under the drop). `sessionphone bot
    install` needed no key, no registry and no seat step. The bot's mail went unsigned
    into the box `claude`, and a real call was answered aloud by a session started
    with `session start claude`. One hint was typed during the walk: the agent was
    reading an older copy of the phone guide, which asked for a signing key, and was
    pointed to the signing line above. **NOT YET:** the ears on a real microphone
    (section 5), and the uninstall (section 8). Before 0.2.1, on a fresh macOS 27 VM,
    sessionphone 0.2.0's bot would not start, because it signed its mail and a fresh
    install had no way to make it a signing identity (2030-06-09).
- **Apple speech. HUMAN (Xcode, macOS 27).** `ears install --apple`. **NOT YET**.

## 7. Known gaps you will hit

- **One plugin from two places loads twice.** Installed the five from clones before?
  Remove their marketplaces before the kit's plugin lines (section 3).
- **The mouth's default "heard" box** names the authors' own mailbox; set
  `VOICEMODE_MOUTH_HEARD_BOX` to yours.
- **Moving a clone breaks its plugin** without a word (section 3 says how to repair it).
- **Claude Code's auto mode can refuse mail between agents** (`[Create Unsafe Agents]`).
  Section 4 gives the permission rule, and how to leave auto mode.

## 8. Uninstall

**NOT YET** as a whole: no rehearsal has run an uninstall end to end. Each step
says what was measured. Part A removes the program and keeps everything you
made. Part B deletes your data, and only if you choose it. Keep to this order.
It is the install in reverse: the voice jobs run from the kit's files and the phone
bot from the plugins', so both go before the plugins and the kit do.

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
**NOT YET** as a run. Its `--help` says this (2030-06-09, sessionphone 0.2.1).

**4. The voice (section 5).** Do this before step 5. The voice jobs run from the
kit's own sessionvoice package (section 2), and launchd keeps them loaded after its
files are gone.

- **The ride-along hook. HUMAN (hand edit).** In the `.claude/settings.local.json`
  that section 5, step 3 edited, remove the two `ears heard hook || exit 1` entries and
  leave any other hooks. If you pasted the whole file in section 5 and have added
  nothing since, delete the file. **NOT YET.**
- **The voice jobs.** Run `ears services uninstall`, the kit's own `ears` that
  installed them (section 5 step 2). With no `--only` it removes every job it
  knows. 0.2.1 knows its own labels, `dev.sessionkit.voice.*`, and both old
  forms it retires: `com.sessionvoice.*`, and the older `com.voicemode.ears-*`
  that 0.1.0 used; that includes `--only speakers`, if you added it. The
  speech server's venv and the speakers' home, `~/.local/share/ears/speakers`,
  stay until part B. **NOT YET** as a run.
- **Look first with `--dry-run`.** `ears services uninstall --dry-run` names each
  job it would boot out and each plist it would delete, and changes nothing.
  **MEASURED** (2030-06-09, sessionvoice 0.2.1 with this release's kit, a temporary
  home directory, no jobs installed): it named the jobs under all three forms,
  `speakers` included, printed `dry run: nothing booted out, nothing deleted`, and
  exited 0. A temporary `HOME` does not make a real run safe: `launchctl` acts on
  your own user's jobs whatever `HOME` says. `ears services status` only reads too.
- **Check:** `launchctl list | grep -E 'dev\.sessionkit\.voice\.|sessionvoice|voicemode\.ears'`
  prints nothing.
  Wait a few seconds before you run it. A job that is still exiting stays in the
  list for a while after the uninstall. If it prints a line, wait a few seconds and
  run it again, until it prints nothing.
  A job you rendered by hand from sessionvoice's `launchd/` templates (not on this
  path) has a label of its own. Run `launchctl bootout gui/$(id -u)/<its label>`, then
  delete its plist from `~/Library/LaunchAgents/`. **NOT YET.**
- **What you brought yourself.** The kit did not install a speech server you
  brought yourself (VoiceMode's, for example; section 5 step 1), or any
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
runs that command, so launchd would keep it loaded on a missing file. **NOT YET**:

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
`claude` session running, remove the kit command and the plugins. Neither needs the
other, so either order works. The plugins' lines depend on how section 3 installed
them: from the kit's marketplace, or from your own clones. Run the lines for your
route, and both sets if you used both.

- `uv tool uninstall sessionkit`
- `claude plugin marketplace remove sessionkit`, if you installed from the kit's
  marketplace (section 3's first lines). This removes its six plugins too.
- `claude plugin marketplace remove <r>` for each of the five (this removes the plugin
  too), if you installed them from your own clones (section 3's
  [From your own clones](#from-your-own-clones-to-work-on-the-plugins-optional)).

**The plugins' copies stay.** Removing a marketplace does not delete the cached copies
its plugins ran from (section 3, **The plugins run from a copy**). Delete them by hand.

From the kit's marketplace, all six copies are in one folder,
`~/.claude/plugins/cache/sessionkit/`:

```bash
rm -rf "${HOME:?}/.claude/plugins/cache/sessionkit"
claude plugin list
```

**MEASURED** (2030-06-09, Claude Code 2.1.307, the kit's marketplace at 0.2.1, on a
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

**MEASURED** (2030-06-09, Claude Code 2.1.301, one plugin, on a temporary home
directory and Claude Code config directory): `claude plugin marketplace remove`
uninstalled its plugin too (`Also uninstalled 1 plugin from this marketplace`), and
`claude plugin list` then printed `No plugins installed.` **The plugin's cached copy
stayed.** `~/.claude/plugins/cache/<r>/` was still there, marked `.orphaned_at`. This
loop removes the five copies now. **NOT YET**: the loop has not run.

If `claude plugin list` still shows one of them, `claude plugin uninstall` removes it by
the name the list shows: `<name>@sessionkit` from the kit's marketplace, with
`sessionkit@sessionkit` among them, and `<r>@<r>` from a clone. **MEASURED**
(2030-06-09, uv 0.13.0, this release's kit with the five 0.2.0 packages from PyPI, on
temporary uv tool directories): `uv tool uninstall
sessionkit` printed `Uninstalled 14 executables` and removed the kit's tool environment.

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
`~/.cache`, `~/.sessionkit` or `~/.voicemode` whole: other tools keep files there.

**The speech models stay behind, about 2.7 GB.** The speech server fetched them on its
first request (section 1) into the Hugging Face cache, which other tools share. The
kit's server sets no cache variable, so they are in `~/.cache/huggingface/hub` (read in
sessionvoice's docs/models.md). They are three folders there: the ears' Parakeet,
`models--mlx-community--parakeet-tdt-0.6b-v3`; the mouth's Kokoro,
`models--mlx-community--Kokoro-82M-bf16`; and Kokoro's voices, which come from a third
repository, `models--prince-canuma--Kokoro-82M`. If no other tool uses them (VoiceMode's
speech server can), remove just those three:

```bash
rm -rf "${HOME:?}/.cache/huggingface/hub/models--mlx-community--parakeet-tdt-0.6b-v3"
rm -rf "${HOME:?}/.cache/huggingface/hub/models--mlx-community--Kokoro-82M-bf16"
rm -rf "${HOME:?}/.cache/huggingface/hub/models--prince-canuma--Kokoro-82M"
```

Never delete the cache whole. **NOT YET.**

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
