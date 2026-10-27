# Install: from a fresh Mac to an agent that hears you and speaks

**Status: DRAFT, alpha.** Every step is tagged **MEASURED** (it ran, on the machine
and versions given), **NOT YET** (not run, or blocked), and **HUMAN** where you must type a
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

  - **HUMAN: your password** at sudo. It installs the Command Line Tools itself.
  - Then run the three lines it prints under "Next steps", as printed (two
    `echo ... >> ~/.zprofile` and one `eval ...`), so `brew` is on your PATH.
  - **MEASURED** (two fresh macOS 27 VMs): 87 to 220 seconds with the Command Line
    Tools, and a new terminal had `brew` and `git`.
- uv, about 1 second:

  ```bash
  curl -LsSf https://astral.sh/uv/install.sh | sh
  ```

  - Then open a new terminal: until you do, `uv` is not on your PATH
    (`command not found: uv`, exit 127). Or run:

    ```bash
    source ~/.zshrc
    ```
- Claude Code, Anthropic's installer, about 13 seconds:

  ```bash
  curl -fsSL https://claude.ai/install.sh | bash
  ```

  - Its "Setup notes" say `~/.local/bin is not in your PATH`? The installer does not
    change your PATH itself (Anthropic's docs). Add the folder with their two lines for
    zsh, the Mac's shell:

    ```bash
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
    source ~/.zshrc
    ```

    After the uv installer above, a new terminal already has `~/.local/bin`, and the
    installer prints no such note. **MEASURED** (a scratch home directory on macOS 27,
    Claude Code 2.1.310): run before uv, the installer printed the note and wrote no
    shell file, and a new terminal had no `claude`; after uv's installer, a new terminal
    found `~/.local/bin/claude`.
  - Then start `claude` and **HUMAN: sign in** with `/login`.
- For a call on a Mac: Homebrew, above, then ffmpeg from it. A call needs ffmpeg,
  and Homebrew is how a Mac gets it. **NOT YET** timed on a fresh Mac.

  ```bash
  brew install ffmpeg
  ```

  - Then the speech server, then link the phone (section 6).
  - A call without Homebrew is the workaround case. This guide does not cover it.
- At least 2.1 GB free disk, plus about 3.9 GB for the speech-to-text server
  (section 5): its venv, 1.2 GB, and its models, 2.7 GB.
  **MEASURED** (on the VM where Homebrew took 220 seconds): the Command Line Tools took 1.3 GB, the kit about 280 MB, Claude
  Code 230 MB, Homebrew 204 MB and uv's Python 74 MB. A fresh VM started with 9.7 GB
  free and ended with 8.7 GB.

  **On a fresh Mac, macOS takes about 8 GB of its own first.** In the first minutes
  after its first start, macOS downloads its own update and assets, before you install
  anything. Leave room for that on top of the figures here. **MEASURED** (a fresh macOS
  27.0 VM, nothing installed): 9.2 GiB free fell to 1.0 GiB within about 10 minutes,
  taken by Software Update and macOS's downloaded assets.
  **MEASURED** again on a fresh macOS 27 VM walked through section 5 at 0.2.0: the kit's
  tool folder was 230 MB, the speech server's venv 1.2 GB, the Hugging Face cache 2.7 GB
  once the server had fetched its models, and the plugins' cache 28 MB.

  **The first call is silent for about a minute.** The server fetches its models into
  the Hugging Face cache on its first request, not at install. Until they are in, your
  agent neither hears nor speaks through it: on a phone call, nothing is heard for
  about a minute. **MEASURED** (a fresh macOS 27 VM, the first phone call
  after `ears services install`): the venv 1.2 GB and the models 2.7 GB. The first
  spoken line took 65.1 seconds and the first heard speech 60.2 seconds; after that,
  a median of 0.4 seconds to speak a line and 0.3 seconds to hear a stretch of speech.
- Python 3.11 or later (uv fetches one if you have none).
- A network connection: the install is online-only. It fetches from PyPI, uv
  downloads its Python, and `ears install` downloads the voice-activity model from
  GitHub.

## 2. Install the kit

```bash
uv tool install --python 3.14 sessionkit
sessionkit setup
```

**Keep `--python 3.14`.** Without it, uv fetches Python 3.15, where the kit cannot
install: a voice library it needs (onnxruntime) has no 3.15 build yet. uv refuses,
exit 1, with `your requirements are unsatisfiable`, and installs nothing. **MEASURED**
(uv 0.13.4 with empty uv folders and only uv's own Python, as on a fresh
Mac): `uv tool install sessionkit` fetched CPython 3.15.0, then refused, exit 1, and no
tool was installed. On a Mac that already has the Command Line Tools, uv may pick their
older Python instead, which the family is not tested on (3.11 on a fresh macOS 27 VM).
Either way, keep `--python 3.14`.

**To upgrade or reinstall, keep the pin.** Each line is safe on its own:

- Upgrade:

  ```bash
  uv tool upgrade sessionkit
  ```

- Reinstall:

  ```bash
  uv tool install --python 3.14 --reinstall sessionkit
  ```

`uv tool upgrade` keeps the Python the install chose. A reinstall without
`--python 3.14` drops the pin from uv's record of the tool, and
`uv tool install --force sessionkit` builds the kit again on the Python uv finds.
**MEASURED** (uv 0.13.4, sessionkit 0.2.1 from PyPI, in an empty tool folder with an empty
uv cache, each line run on a fresh `--python 3.14` install, read in the tool's
`pyvenv.cfg` and `uv-receipt.toml`; measured on 0.2.1, not yet on 0.3.0):
- `uv tool upgrade sessionkit`, with or without `--reinstall`, and `uv tool upgrade --all`
  stayed on 3.14 with the pin kept.
- `uv tool install --python 3.14 --reinstall sessionkit` stayed on 3.14 with the pin kept.
- `uv tool install --reinstall sessionkit` stayed on 3.14 but dropped the pin.
- `uv tool install --force sessionkit` rebuilt the kit on 3.13 where that was uv's first
  Python. Where Homebrew's 3.15 was first, it refused (no 3.15 build of a voice library),
  exit 1, and left the 3.14 install as it was.
- `uv tool upgrade` has no `--refresh` on uv 0.13.4: it refuses that flag, exit 2.

**MEASURED** (read-only against PyPI): the five packages this release
needs are on PyPI, each at 0.3.0: sessionmail, sessionphone, sessiontools, sessionview
and sessionvoice. The kit asks for 0.3.0 or later of each. This line installs the kit and
its five packages, 61 packages in all, and 14 commands on your PATH:
`sessionkit message pager memory session sessionphone sessionview sessionview-config
sessionview-messages sessionview-session ears ears-serve mouth talk`. **MEASURED**
(this release's six packages at 0.3.0 installed from a folder of their
wheels, Python 3.14, an empty tool folder, an empty uv cache and a temporary home
directory): 61 packages and the 14 commands. Every `--help` tried answered but four of
`sessionview`'s, which run the verb instead: `sessionview install --help` runs its
requirements check, `sessionview autostart --help` and `sessionview from --help` do what
the verb does, and `sessionview sidebar --help` opens the sidebar.

**The install size.** **MEASURED** (the 0.2.1 install, on Apple silicon; not yet
re-measured on 0.3.0): uv downloaded about 93 MB, and the kit's tool folder is about
280 MB on disk. uv's own Python is not in that folder; section 1 counts it.

**Phone calls are installed, and walked for a session started with
`session start <name>`.** A plain `claude` session does not hear calls you make to it
yet. The kit installs sessionphone with its calls packages (its `media` extra: aiortc,
av and 8 more). They download with everything else, during `uv tool install`, with no
separate step: 10 of the 61 packages, about 21 MB of the download and about 52 MB of
the 280 MB. **MEASURED** (the 0.2.1 install, the files those 10 packages install; not yet
re-measured on 0.3.0). Setting them up is section 6, which a fresh Mac has walked for a session started with
`session start <name>`.

**On Linux** (untested), the voice package needs the system PortAudio library
(Debian and Ubuntu: `libportaudio2`). sessionvoice 0.3.0 depends on `sounddevice`,
whose Linux wheel brings no PortAudio; its macOS and Windows wheels do (read on
PyPI).

- **Then open a new terminal**, so the commands are on your PATH. Or run:

  ```bash
  uv tool update-shell
  ```

**`sessionkit setup` sets up mail on this Mac, then names you as the operator**: the
human your agents ask. It is the last line of the block, so if it stops, nothing after
it is skipped.

- The shell said `command not found: sessionkit`? Open a new terminal, and run it there:

  ```bash
  sessionkit setup
  ```

**Mail first.** It runs sessionmail's mail setup, `message setup`, which makes the mail
folder and your box and says what is left for you
([Mail between agents](#mail-between-agents), section 5, step 4). On a fresh install
your box is named for your account; with `--mailbox NAME` it makes that box too, and
your assistant's box (below), and no other. Then it writes the operator: your box, or
the address you gave with `--address`, and reads it back through `session operator`.

**On a fresh Mac it exits 4, and that is expected.** Mail setup makes your box and
its notmuch profile. notmuch is not found yet, so it leaves its two notmuch steps, the
index and the hooks, `BLOCKED`, and lists them by number (section 5, step 3). The
operator is written all the same. The last lines read like this:

```text
message setup: done what it can; 2 step(s) left for you:
  1. notmuch-index (BLOCKED): notmuch: 'notmuch' not found ($SESSIONMAIL_NOTMUCH, else PATH), so the index and hook steps are left. Once it is found, setup runs `notmuch --config=/Users/<you>/.config/notmuch/sessionkit/config new --no-hooks` once and links the hooks
  2. notmuch-hook (BLOCKED): waits on notmuch-index
then run `message setup` again.
Mail setup left steps for you (above); re-run sessionkit setup after.
Wrote /Users/<you>/.sessionkit/tools/settings/session.d/10-operator.json: the operator is address '<you>@<your-mac>'.
session operator: {"operator": "<you>@<your-mac>", "mailbox": null, "privileged": ["<you>@<your-mac>"]}
Wrote /Users/<you>/.session/agents/claude.md: the agent 'claude', not keyed.
session start --list-agents: lists 'claude'.
To hear Delta messages, start Claude with: session start
```

The last line names no agent when your agent is the default seat, `claude`:
a bare `session start` takes it (section 4).

- With `--agent NAME` naming another agent, it ends `session start NAME`.
- With a sessiontools that has no default seat (0.3.0), it ends
  `session start claude`.

**MEASURED** (this release's sessionkit, sessiontools from source with the default seat,
not yet released, a temporary home directory, run with `--address`): with no `--agent`
and with `--agent claude`, the last line was the bare form; with `--agent other`, it
ended `session start other`; with sessiontools 0.3.0, `session start claude`. Exit 4
each. **MEASURED** (this release's sessionkit's mail step, with sessionmail's mail setup
built from its source ahead of its next release, a temporary home directory, no
notmuch): the first five lines, exit 4. **MEASURED** (a fresh macOS 27 VM, sessionkit
0.2.0 and sessionmail 0.2.0 from PyPI, run with `--address`): the two operator lines
after them, exit 4; that sessionmail named one notmuch step, on one line. The last
three are this release's assistant step (below), which sessionkit 0.2.0 does not have.
**MEASURED**
(this release's sessionkit with the five 0.2.0 packages from PyPI, a
temporary home directory, run with `--address`): the last three lines, the launch
step ending `session start claude` (that sessiontools has no default seat), exit 4, and
`session start --list-agents` lists `claude`. **NOT YET** run on a fresh Mac. Without `--address` it writes your box, the one
named for your account, as the operator (read in its source). **NOT YET** on a fresh
Mac without `--address`.

**Then your assistant:** it writes `~/.session/agents/claude.md`, the agent
`session start claude` starts (section 4), and asks mail setup for its box, `claude`.

**Then the wake seat:** it makes your agent the one your voice wakes, `claude` or the
name you gave `--agent`, so you do not add it by hand in section 5 (see
[How waking works](#how-waking-works)). It prints one line just after the
`--list-agents` line:

```text
Wake seat 'claude': "hey claude" wakes it.
```

- A re-run changes nothing, and names you added to the seat stay.
- With no `ears` on the PATH, or when the ears refuse, it adds nothing. One line says
  so and names the command to run later. The exit does not change.
- With a sessiontools that has no default seat yet (0.3.0), a run without `--agent`
  adds no wake seat, and one line says so.

**MEASURED** (a temporary home directory, the kit's sessionvoice 0.3.0 and sessiontools
from source with the default seat, not yet released, run with `--address`): that line,
exit 4. A second run left the wake file byte for byte the same.

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
operator is set and mail steps are left for you, named in its output.

- Exit 4? Do the mail steps it names. Then run it again; it leaves the operator it
  wrote alone:

  ```bash
  sessionkit setup
  ```

**A dry run writes nothing, so its exit says what a real run would meet.** Mail
setup's dry run exits 4 while any of its steps is still to do, and 0 only once every
step is done. So with `--dry-run`, 4 means mail steps are still to do and the operator
check did not refuse (your box is there, or you gave `--address`, or an operator is
already set): nothing is set yet, and the real run does what it can and names the
rest. On a fresh install mail setup has not made your box, so the operator check after
it refuses too: `sessionkit setup --dry-run` exits 1 there, and the real run is what
makes the box. **MEASURED** (sessionkit setup and sessionmail 0.2.0):
`sessionkit setup --dry-run` exited 4 on a fresh macOS 27 VM with `--address`, and 1
on a fresh temporary home directory without it, and made nothing either time.

**It refused?** Run it again with one of these:

- Your own email address, in place of ADDR:

  ```bash
  sessionkit setup --address ADDR
  ```

- A box name that `message box path` finds, in place of NAME:

  ```bash
  sessionkit setup --mailbox NAME
  ```

- Add `--dry-run` to either to see the file it would write, and write nothing.

A sessionmail older than the kit asks for, with no mail setup, gets the step printed
instead: it says it has no `message setup` and names the step, and the operator half
still runs.

**MEASURED** (by the test suite, and on temporary home directories): the
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

  with `"address"` in place of `"mailbox"` if you used `--address`.
- **Changing the operator.** Either way works:
  - Edit that file.
  - Or delete it and run setup again:

    ```bash
    rm "${HOME:?}/.sessionkit/tools/settings/session.d/10-operator.json"
    sessionkit setup
    ```

- **Who is privileged.** `setup` never writes `privileged`. Then the operator alone may
  act as an administrator. This shows who is configured, under `mailbox`, `operator`
  and `privileged`:

  ```bash
  session operator
  ```

- **Adding an administrator. HUMAN (edit a file).** Three steps:
  1. Run setup first. Once any file holds an `operator` block, `setup` leaves it
     alone (below):

     ```bash
     sessionkit setup
     ```

  2. Make a file of your own, such as
     `~/.sessionkit/tools/settings/session.d/20-administrators.json`:

     ```json
     {"operator": {"privileged": ["<a seat name or address>"]}}
     ```

  3. Check it:

     ```bash
     session operator
     ```

  **The list replaces.** When two files set `privileged`, the later file's list wins
  whole, so keep every administrator in ONE list. You need not list yourself: the
  operator is always privileged. **MEASURED**
  (temporary home, `session operator` from sessiontools 0.2.0): a `20-` file's list was
  added beside the operator, and a `30-` file's list replaced the `20-` file's.
- **An environment variable never grants privilege.** `AGENT_OPERATOR_ADDR` can change
  where an agent sends a question, nothing more. `setup` ignores it, and `$USER` and
  `$MAIL` too: your account name comes from the system, not the environment. **MEASURED**
  (the same way).
- **Set an operator by hand already? `setup` leaves it alone.** If `session.json` or any
  `session.d/*.json` file holds an `operator` block, or `session operator` already
  reports one, it writes nothing, names the file or the operator, and exits 0. If one of
  those files cannot be read or is not valid JSON, it writes nothing, names the file,
  and exits 1: fix that file first.
- **Upgrading from 0.1.0.** 0.1.0 wrote the operator to
  `~/.settings/session/session.d/10-operator.json`. While that file exists and no operator
  is set in the new folder, `setup` writes nothing, prints one line naming both files, and
  exits 1, even with `--dry-run`; it never reads the old file. Do one of these:
  - Keep it: move it to `~/.sessionkit/tools/settings/session.d/10-operator.json`.

    ```bash
    mkdir -p "${HOME:?}/.sessionkit/tools/settings/session.d"
    mv "${HOME:?}/.settings/session/session.d/10-operator.json" "${HOME:?}/.sessionkit/tools/settings/session.d/10-operator.json"
    ```

  - Or drop it:

    ```bash
    rm "${HOME:?}/.settings/session/session.d/10-operator.json"
    ```

  - Then run setup again:

    ```bash
    sessionkit setup
    ```

Older notes say that `uv tool install sessionmail` or `uv tool install sessiontools`, on
its own, installs an empty placeholder. Each installs its real package now, 0.3.0 on
PyPI, and `sessionkit` brings both anyway.

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

- **Then quit Claude Code and start it again**, every window of it, before any step
  below.

This holds for the clones route too. A plugin installed from the shell loads
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
twice:

```bash
for r in sessionmail sessiontools sessionphone sessionvoice sessionview; do
  claude plugin marketplace remove "$r"
done
```

**MEASURED** (0.2.0):
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
the end of this section). The blocks below call it `$SRC`. Clone the five into it:

```bash
SRC=~/.local/share/sessionkit/src
for r in sessionmail sessiontools sessionphone sessionvoice sessionview; do
  git clone -b master "https://github.com/sessionkit/$r" "$SRC/$r"
done
```

Then add and install each one:

```bash
SRC=~/.local/share/sessionkit/src
for r in sessionmail sessiontools sessionphone sessionvoice sessionview; do
  claude plugin marketplace add "$SRC/$r" && claude plugin install "$r@$r"
done
claude plugin list
```

You should see five plugins, each `✔ enabled`, scope user, each `Read from: <SRC>/<r>`.
**MEASURED** (0.2.0, Claude Code 2.1.304, an empty Claude Code config, clones of the
public repositories made with `-b master`): five of five, all 0.2.0.

**Each plugin runs in place, from its clone.** Claude Code loads a plugin from a
marketplace you added from a local folder where it is: the clone's `bin/` and `skills/`
are what your agent gets. An edit in a clone takes effect at the next session start, or
on `/reload-plugins` in a session already open (read in Claude Code's plugin docs,
"In-place and copied plugins"). Claude Code also writes a copy to
`~/.claude/plugins/cache/<r>/<r>/<version>/`, and `installed_plugins.json` names it, but
that copy is not what runs. **MEASURED** (Claude Code 2.1.310, sessionmail 0.3.0 from a
local clone, an empty Claude Code config): `claude plugin list --json` gave the clone as
the plugin's `readFromFolder` and the cache copy as its `installPath`. **MEASURED** on a
fresh macOS 27 VM at 0.2.0: the plugin command `mouth-timeline` on the agent's PATH was
the clone's.

**The block exits 0 even when nothing installed, so read `claude plugin list`.**
**MEASURED** (in the release rehearsal): with no clones in `$SRC`, the loop printed
`✘ Path does not exist: <SRC>/sessionmail` and the like for each name, the list printed
`No plugins installed.`, and the block still exited 0.

**Fewer than five?** Set `r` to a missing one's name, `sessionmail` here:

```bash
SRC=~/.local/share/sessionkit/src
r=sessionmail
```

Then read the line the loop printed for it:

- `Path does not exist: <SRC>/<r>`: there is no clone there. Clone it:

  ```bash
  git clone -b master "https://github.com/sessionkit/$r" "$SRC/$r"
  ```

- `Marketplace file not found at <SRC>/<r>/.claude-plugin/marketplace.json`: the clone
  is there, but nothing is checked out. Delete that clone and clone it again with
  `-b master`, the branch the public repositories are on:

  ```bash
  rm -rf "${SRC:?}/${r:?}"
  git clone -b master "https://github.com/sessionkit/$r" "$SRC/$r"
  ```

  **MEASURED** (in the release rehearsal: a clone with nothing checked out gave this;
  cloned again with its branch named, it installed).

Then run the loop's line for that one:

```bash
claude plugin marketplace add "$SRC/$r" && claude plugin install "$r@$r"
```

**If a clone moves, its plugin breaks silently** (`claude plugin list` still exits 0;
**MEASURED**). The repair, also measured, drops that plugin's saved options. First name
the plugin and the folder its clone is in now. Edit both lines to yours:

```bash
r=sessionmail
new=~/src/sessionmail
```

Then:

```bash
claude plugin marketplace remove "${r:?}"
claude plugin marketplace add "${new:?}"
claude plugin install "${r:?}@${r:?}"
```

## 4. First checks

- **What is still missing.** The kit's check prints one line for each thing
  the kit needs, found or missing, and under each missing one the command
  that adds it. It installs nothing and starts nothing, and it writes no
  file of its own:

  ```bash
  sessionkit doctor
  ```

  Exit 0: nothing the kit needs is missing. Exit 1: something is.
  - Its first rows are the installer's own checks: it runs the `install.sh`
    the kit ships, with `--check`. The speech server row asks the server on
    port 8890 itself, as in [troubleshooting](docs/troubleshooting.md#ears-running-but-deaf).
  - Then three rows of its own. The mail hooks (the step below) fail it
    while they are off. The phone bot (section 6) is optional, and the
    session key is information only: neither fails it.
  - `--no-speech` leaves the speech server and the ears (section 5) out.
  - The only network it reaches itself is the speech server on port 8890,
    which it probes, and its `brew` reads download nothing. The tools it
    asks may use their own network: asked for its plugins, `claude` reaches
    Anthropic's API over HTTPS.
  - No kit yet, or `sessionkit` will not start? The installer runs the same
    check. Its address is not live yet. From a clone of this repository:

    ```bash
    bash install.sh --check
    ```

    Once the address is live:

    ```bash
    curl -fsSL https://sessionkit.ai/install.sh | bash -s -- --check
    ```

  **MEASURED** on one Mac without the kit (macOS 27, Apple silicon), in an
  empty home directory with the real tools. The check wrote nothing of its
  own. The tools it asks keep their own files, and in an empty home they
  made them:
  - `brew`: its cache, in `~/Library/Caches/Homebrew`.
  - `uv`: an empty cache, in `~/.cache/uv`.
  - `claude`: `~/.claude.json`, and a copy of it in `~/.claude/backups`.
    Asked for its plugins, it also reads its own sign-in from your login
    keychain. That is a read: the one keychain command it ran was
    `security find-generic-password`. Each of its two plugin commands also
    opened two HTTPS connections to Anthropic's API (`api.anthropic.com`).

  A second run changed nothing. On a Mac that has used these tools, the
  files are there already. Nothing outside the home directory changed, and
  `brew` downloaded nothing. **NOT YET** on a Mac with the kit:
  the `sessionkit` and `ears` rows ran only in the tests, on a stand-in Mac.
- **The ears' model.** This downloads the voice-activity model from GitHub to
  `~/.cache/ears/silero_vad.onnx`, with no sudo. **MEASURED** (in the release rehearsal).

  ```bash
  ears install
  ```

- **Start Claude** in the directory you will work from. It is the one launch step
  `sessionkit setup` ends with (section 2):

  ```text
  To hear Delta messages, start Claude with: session start
  ```

  Run it:

  ```bash
  session start
  ```

  It starts Claude as the agent `claude`, so the session hears mail to the box `claude`,
  the box your phone's Delta messages are addressed to; a bare `claude` hears only its
  own session's box. **Only one session on this Mac holds `claude`**, the default seat:
  - While one does, a second `session start claude` starts nothing. It is refused,
    exit 3, and its line names the session that holds it.
  - A bare `session start` takes `claude` when no session holds it, and starts plain
    when one does ([the README's Quick start](README.md#quick-start)).

  `claude` is Claude Code's own built-in agent, so the file setup wrote rides beside
  it: its text is added to Claude Code's own system prompt. Under any other name the
  file's text is your assistant's prompt.
  **MEASURED** (sessiontools from source with the default seat, not yet released; a
  temporary home directory; a stand-in `claude` that only waits): while one session
  held `claude`, `session start claude` printed
  `session start: claude is already held by session 4e104546 (pid 11500), live 2s -- refusing a second holder; pass --allow-second-holder to start one anyway`,
  exit 3, and launched nothing. Its dry run passed the file setup wrote as
  `--append-system-prompt-file`.
  **MEASURED** (sessiontools 0.1.0, a temporary home directory): before
  `sessionkit setup`, `session start --dry-run claude` stopped with
  `agent 'claude' not found`, exit 2; after it, the command was
  `claude --session-id <a new id> ... --agent claude`, exit 0. **MEASURED**, walked and
  passed (a fresh macOS 27 VM, this release's kit with sessionmail,
  sessionphone and sessionvoice 0.2.1): Delta messages and a phone call reached a
  session started with `session start claude`. Each turn was mailed to the box
  `claude` and woke the session, which answered aloud.
- **A second assistant** gets another name. Its name goes in place of NAME:

  ```bash
  sessionkit setup --agent NAME
  session start NAME
  ```

- **Turn the mail hooks on. HUMAN (edit a file).** The sessionmail plugin's
  hooks run clean, and your session's box under `~/.mail/agents/` is made when the session
  starts, by the plugin's start hook. **MEASURED** in part (in the release rehearsal; the
  box at session start in a temporary home directory). The hooks stay off until you set
  `"hooks": true` in `~/.sessionkit/mail/settings/mail.json`.
  Nothing on your screen says so: the plugin writes that file, with the hooks off, the
  first time your session runs a tool, and it tells your agent, not you. The README's
  step **The mail hooks start off** is one block that does either of these:
  - No file yet: make it with exactly this content:

    ```json
    {"version": 1, "hooks": true, "sendmail": "drop"}
    ```

  - The file is there: change only `"hooks": false` to `"hooks": true`, and keep its
    other keys.

  **MEASURED** (sessionmail 0.2.0 and 0.3.0 from PyPI, the plugin's start and tool-batch
  hooks run by hand on a temporary home directory): the start wrote only
  `mail.schema.json` and `mail.template.json`; the first tool batch wrote `mail.json` as
  `{"version": 1, "hooks": false, "sendmail": "drop"}`, and said so only in what it
  hands the agent. On a fresh macOS 27 VM at 0.2.0, nothing on the screen said so.
- **Claude Code asks whether you trust the folder, and "No, exit" is the answer it has
  ready.** HUMAN: on the first start in a folder, choose the yes answer before you press
  Return; Return alone quits the session. **MEASURED** (the first session on a fresh
  macOS 27 VM).
- **`pager status` and `message send` work only inside a `claude` session.** They find
  out who is asking from the session's environment, and a plain terminal has none. There
  they print this and exit 2:

  ```text
  pager status: could not look: no identity in the environment - looked for TM_AGENT_ADDRESS, CLAUDE_CODE_AGENT, CLAUDE_CODE_SESSION_ID, CLAUDE_SESSION_ID, in that order
  Error: no seat in the environment to send From - there is no --from; set an identity
  ```

  That is expected, not a broken install: run them from your agent, inside `claude`,
  which sets `CLAUDE_CODE_SESSION_ID`. **MEASURED** (a fresh macOS
  27 VM, Claude Code not signed in: both lines, exit 2). Inside a session, `pager status`
  gets past this and asks for the mailbox instead, until the pager first listens
  (**MEASURED** on the authors' Mac, not the VM).
- **Claude Code's auto mode can refuse your agent's `message send`.** From Claude Code
  2.1.283, an interactive session starts in auto mode: a second model, the classifier,
  reviews each command before it runs. Mail that asks another agent to act can be
  refused with this line:

  ```text
  Permission for this action was denied by the Claude Code auto mode classifier. Reason: [Create Unsafe Agents].
  ```

  **MEASURED** (a fresh macOS 27 VM: an agent's `message send` that asked a
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
    `⏸ manual mode on`. Further presses cycle through accept edits, plan and auto.
  - **Start every session in Manual mode.** Set this in `~/.claude/settings.json`:

    ```json
    {"permissions": {"defaultMode": "default"}}
    ```

  - **Let one refused command through.** In the session:
    1. Run `/permissions`.
    2. Open the **Recently denied** tab.
    3. Press `r` on the command.
- The sessionmail plugin's monitor arms the pager for the whole session, and it is on by
  default. Section 3 installs it: the plugin's `monitors/monitors.json` runs
  `pager listen --monitor` with the `pager` on your PATH, so you do not turn anything on.
  The sessionmail plugin section 3 installs, 0.3.0, has that `monitors/monitors.json`
  (read in its public repository); its 0.1.0 plugin had none. **MEASURED** (a fresh macOS 27 VM, sessionkit
  0.2.0 and sessionmail 0.2.0 from PyPI, the plugins installed in one step, an
  interactive `claude`): Claude Code showed `1 monitor`, and `pager status` said
  `monitor: armed (pid <n>); switch: on (the default: no switch is set)`. Claude Code runs a plugin's monitor only in an interactive session
  (never `claude -p`), with the folder trusted, and only while its own monitor gate is
  on. When it does not run it, nothing in Claude Code says so (sessionmail's
  `docs/pager-monitor.md`; the trust condition is from the README of its retired
  `plugins/pager-monitor`). sessionmail's off switch (`"monitor": false` in
  `~/.sessionkit/mail/settings/mail.json`, or `SESSIONMAIL_MONITOR=off` at launch) and
  `pager mute` / `pager unmute` ship from sessionmail 0.2.0, and the kit installs 0.3.0;
  the 0.1.0 `pager` had none of them. **MEASURED** (sessionmail 0.2.0 from
  PyPI, a temporary home directory): `pager --help` lists `mute` and `unmute`, and each
  answers its `--help`; the off switch is read in its source. **MEASURED** again on
  sessionmail 0.3.0 from PyPI: `pager --help` lists `mute` and `unmute`, and
  each answers its `--help`. With no
  monitor running, the agent arms the pager itself, as a background tool call, when the
  pager's hook says it is not listening (hooks on). Your agent's letter to itself never
  arms or stops the pager from a wake item; `pager status` is the only check
  ([the agent letter](docs/agent-letter.md)).

### Your first agent, in tmux

**NOT YET** as a whole: no fresh Mac has run these steps end to end. Each step says
what was measured.

1. **Get tmux. HUMAN (Homebrew).** The second line shows its version:

   ```bash
   brew install tmux
   tmux -V
   ```

   It uses the Homebrew from section 1. tmux brings no Python with it. The
   kit's Python is uv's (section 2), so do not `brew install python`. **MEASURED**
   (read-only, `brew deps tmux` at tmux 3.8, not on a fresh Mac): it needs
   ca-certificates, jemalloc, libevent, ncurses, openssl@4 and utf8proc, and no Python.
2. **Start tmux** in the directory you will work from. Its path goes in place of DIR:

   ```bash
   cd DIR
   tmux new-session -s agents
   ```

   This puts you inside a tmux session named `agents`.
   - To leave it running: press `Ctrl-b`, then `d`.
   - To come back to it:

     ```bash
     tmux attach -t agents
     ```

   **MEASURED** in
   part (tmux 3.8, on a tmux server of its own):
   `tmux new-session -d -s agents` made the session, and `tmux ls` listed
   `agents: 1 windows`.
3. **Start your first agent** inside it:

   ```bash
   session start claude
   ```

   It starts Claude in
   this window as the agent `claude`, the one `sessionkit setup` wrote (section 2),
   under a new session id. `sessionkit setup` ends with the bare form, which takes
   `claude` too while no session holds it:

   ```text
   To hear Delta messages, start Claude with: session start
   ```

   Only one session holds `claude` (the checks above); a second
   assistant gets its own name (the checks above, **A second assistant**).
   - To see the command and start nothing, put `--dry-run` before the name:

     ```bash
     session start --dry-run claude
     ```

   - Outside tmux: this puts the agent in a new window named `claude`, in the tmux
     session `agents`:

     ```bash
     session start --tmux-target agents claude
     ```

   Launcher flags go before the name: everything after
   it is handed to `claude` itself, so `session start claude --dry-run` refuses, names
   the right order and exits 2. With no name, `session start` takes `claude` when no
   session holds it, and starts plain when one does (the checks above). Running
   `claude` yourself works too, but that session never hears mail to the box `claude`.
   **MEASURED** as `--dry-run` (sessiontools from source with the default seat, not yet
   released, a temporary home directory): with no name and no session holding
   `claude`, the command ended `--agent claude`, and its `seat:` line read
   `claude, the default seat: a live launch takes it (box claude found; no live holder)`.
   **MEASURED** only as `--dry-run` and refusals
   (0.1.0, on a temporary home directory): with no name the command was
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
5. **Mail it.** From sessionmail 0.2.0 (the kit installs 0.3.0), `message send`
   goes by the experimental file drop with nothing to set, on this Mac only: see
   [Mail between agents](#mail-between-agents) in section 5. **MEASURED** (a fresh
   macOS 27 VM, sessionkit 0.2.0 and sessionmail 0.2.0 from PyPI, inside a
   `claude` session, no postfix): `message send admin` printed
   `sent via mail drop (no MTA)`, exit 0, and `message list admin` showed it. Send from
   your agent: in a plain terminal it refuses (the checks above). **NOT YET** as mail from
   one agent to another on a fresh Mac. The voice path in section 5 does not need mail.

## 5. Hearing and speaking ("it hears me and speaks")

None of these ran end to end in the rehearsal. Each is **NOT YET** unless a line says
otherwise.

Section 2 installs sessionvoice **0.3.0**. Steps 1 and 2 were read in sessionvoice's
source and dry-run on sessionvoice 0.2.1 from PyPI, and are not yet re-measured on 0.3.0.

**The job labels.** Every launchd job in the session family is labelled
`dev.sessionkit.<package>.<job>`. The voice's are `dev.sessionkit.voice.mlx-audio`
for the speech server and `dev.sessionkit.voice.ears-<name>` for the rest. Two
older forms are history: `com.sessionvoice.*`, which earlier copies of this guide
named, and `com.voicemode.ears-*`, which 0.1.0 loads. 0.2.1's
`ears services install` recognises a job under either old form and retires the old
form: it moves the job off before it loads the new label. **MEASURED** (sessionvoice
0.2.1 from PyPI, `ears services install --dry-run`, a temporary home
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
   (0.2.0, a temporary home directory, nothing on 8890): it would
   build that venv and load `dev.sessionkit.voice.mlx-audio`.
2. **The voice services. HUMAN (launchd, the microphone permission prompt).** Two
   commands, in this order:
   - **First the model**, even if you ran this in section 4:

     ```bash
     ears install
     ```

     It fetches the
     voice-activity model to `~/.cache/ears/silero_vad.onnx`. **MEASURED** (in
     the release rehearsal). Without that model, the ears keeper died every 4 seconds on a
     fresh Mac. **NOT YET:** that came from a field report, not the rehearsal.
     0.2.0's `ears services install` refuses without the model
     (`silero MISSING`, exit 2). **MEASURED** as `--dry-run` (0.2.0,
     a temporary home directory).
   - **Then the services**, with the kit's own `ears` from section 2 (the block
     below). `ears services install` writes four LaunchAgents and loads them:
     `dev.sessionkit.voice.mlx-audio` (the speech server, step 1), `dev.sessionkit.voice.ears-mouth`,
     `dev.sessionkit.voice.ears-keeper` and `dev.sessionkit.voice.ears-mail`. The
     keeper and ears-mail run from scripts in the sessionvoice package itself, so
     no plugin path is needed. If jobs under an old label are on this Mac (0.1.0's
     `com.voicemode.ears-*`, or `com.sessionvoice.*`), install retires the old
     form: it moves each one off before it loads the new one. **MEASURED**
     only as `--dry-run` (0.2.0, a temporary home directory): those
     four plists, with the keeper's and ears-mail's scripts in the installed
     package. A real install ran on a fresh macOS 27 VM (below), with
     no microphone: **NOT YET** on real audio.

     `sessionkit setup` has already made your agent the one your voice wakes: its
     `Wake seat 'claude'` line (section 2). So install them as they are:

     ```bash
     ears services install
     ```

     It finds the wake seat and adds none. Its `wake` line reads
     `no --agent; /Users/<you>/.sessionkit/voice/settings/wake.json already wakes claude`,
     and the keeper's notices go to the operator (section 2). **MEASURED** as
     `--dry-run` (sessionvoice 0.3.0, a temporary home directory after
     `sessionkit setup`, a stand-in file for the voice-activity model): that `wake`
     line, exit 0.

     Setup's line said `No wake seat added`? Then give `--agent` and your agent's name
     in place of NAME, `claude` unless you named another with `sessionkit setup --agent`:

     ```bash
     ears services install --agent NAME
     ```

     Without a wake seat, "hey" and your agent's name wakes no one by mail. Room mode
     (step 4) still wakes your agent: see [How waking works](#how-waking-works).
     `--agent` makes that agent the one your voice wakes (`ears wake add SEAT`), and
     sends it the keeper's notices. From sessionvoice 0.3.0, the one the kit installs,
     a bare install refuses when the wake file names no seat: it writes nothing, exits
     2, and names both ways on, `--agent NAME`, or `--no-agent` to install anyway with
     no seat for "hey" and a name until you run `ears wake add SEAT`. **MEASURED** as
     `--dry-run` (sessionvoice 0.3.0 from PyPI, a temporary home directory): bare,
     `REFUSED: no --agent NAME`, exit 2; with `--agent claude`, no such refusal, and
     `would add claude` to the wake file. **MEASURED** again as `--dry-run` (sessionvoice 0.3.0, a temporary home
     directory with no wake seat): bare,
     `REFUSED: no --agent NAME, and /Users/<you>/.sessionkit/voice/settings/wake.json names no seat`,
     exit 2.
     sessionvoice 0.2.x warned `no --agent NAME: NOBODY will be woken when you speak`
     and installed anyway. **MEASURED** (a fresh macOS 27 VM, a real install at 0.2.x):
     a bare install printed that warning. **MEASURED** as `--dry-run` (sessionvoice 0.2.1
     from PyPI, a temporary home directory): bare, the same warning; with
     `--agent claude`, `would add claude` to the wake file, and the keeper's notices to
     `claude`.

     **Warnings a Mac with no postfix can pass by.** A real install at 0.2.x, on a fresh
     macOS 27 VM with no postfix, printed three warnings:
     - `postfix has no virtual_mailbox_maps ... no agent is paged`: ignore it. It is
       about mail carried by postfix, and this Mac's mail goes by the drop.
     - `heard box MISSING, not made: ...`, which ends in a `vmailbox-gen` line: ignore
       it too. It is a postfix step for the mail path below, which this guide leaves
       for later.
     - `no --agent NAME: NOBODY will be woken when you speak`: do not ignore this one.
       `sessionkit setup` adds the wake seat (section 2), so you meet it only when
       setup's line said `No wake seat added`. Then do one of these, your agent's name
       in place of SEAT or NAME:
       - Add it to the wake file:

         ```bash
         ears wake add SEAT
         ```

       - Or install again with it:

         ```bash
         ears services install --agent NAME
         ```

     From sessionvoice 0.3.0, with mail on the drop, install checks no postfix and
     makes the heard box itself with `message setup --box heard`, and a bare install
     refuses in place of the third warning (read in its source). **NOT YET** run on a
     Mac with no postfix.

     Install ends with a `heard` line: an agent hears heard turns only once it
     subscribes to `heard+<device>` (`heard+macbook` for the built-in mic). That is
     the mail path, and this guide leaves it for later: your agent wakes on your
     voice through steps 3 and 4. The mail path is in
     [How waking works](#how-waking-works). If you take the mail path, your agent's
     `message subscription add heard+macbook` is refused, exit 2, with
     `a seat's mail is that seat's to grant`, until your agent is an administrator.
     To make it one, name it in an administrators file, as in
     [Operator and administrators](#operator-and-administrators) (section 2), for
     example `{"operator": {"privileged": ["claude"]}}`, then subscribe again.
     **MEASURED** (a fresh macOS 27 VM): the subscription was refused for
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
   macOS 14 or later, and `uv`. After the services above are running, install
   it: its own venv, the model and the job.

   ```bash
   ears services install --only speakers
   ```

   Then a person names each voice:

   ```bash
   ears speakers enrol
   ```

   Then check the speakers row:

   ```bash
   ears services status
   ```

   The install builds its own venv (mlx-audio 0.5.8) and downloads the diarizer
   model, about 190 MB, once. `ears speakers enrol` records the room while the
   keeper runs, for 180 seconds by default (Enter stops it sooner). It shows
   what each voice said and asks a person to name each one; it never guesses a
   name.
   Under launchd, macOS asks for a microphone grant for the speakers binary,
   `bin/ears-speakers`; without it, its rows say `unheard`, `no signal`.
   **MEASURED** only as `--dry-run` (0.2.0, a temporary home
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
   `<launch directory>/.claude/` (read in Claude Code's settings docs).
   - No file yet: paste this as the whole file:

     ```json
     {
       "hooks": {
         "PostToolUse":   [{"hooks": [{"type": "command", "command": "ears heard hook || exit 1", "timeout": 5}]}],
         "PostToolBatch": [{"hooks": [{"type": "command", "command": "ears heard hook || exit 1", "timeout": 5}]}]
       }
     }
     ```

   - The file is there: add these two entries to its `hooks` instead of replacing the
     file.

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
   (0.2.0, a copy of its master): the shim runs the script.

   It runs the `heard-first` waiter. In room mode it wakes your agent when you say "hey"
   and its name (or "hey everyone"), when you answer the last thing your agent said, or
   when a line your agent is speaking gets cut off (you talk over it, or the speakers
   drop); a bare mention of its name does not wake it. Run it again each time it fires.
   How this and the mail path fit together: [How waking works](#how-waking-works).
   **MEASURED** as `--dry-run` only (it prints the `heard-first` command,
   with rules for "hey" plus the name or "everyone", a reply rule and a cut rule).
   **NOT YET** as a live wake.
5. **Test the mouth. HUMAN (speakers).**

   ```bash
   mouth say "ears are up"
   ```

   With no device set, the mouth plays on your Mac's default output, wherever that is.
   **MEASURED** as the choice only (sessionvoice 0.3.0, a temporary home directory with
   no settings file): with no device given, it chose `default`, the system default
   output. **NOT MEASURED ON AUDIO.**
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

**Until step 6 passes, keep room mode and `heard-first`.** Have your agent arm room mode
(step 4), and leave the other modes and the mail path alone until your agent has woken
and answered you. **NOT YET** (advice: step 6 has not passed on any measured Mac).

### How waking works

Mail wakes your agent. The ears only hear you and write mail, and each session's
pager wakes its own session. Room mode (step 4) is the one other way: a waiter your
agent runs itself. Five parts decide which mail wakes it:

- **The session box.** Every session has its own box, named by its session id, under
  `~/.mail/agents/`. Mail to the session id lands there. The pager watches this box and
  no other. The box is made when the session starts, by the sessionmail plugin's start
  hook.
- **Subscriptions.** A session can subscribe to another box, and that box's mail is
  then copied into its session box too. The ears write each heard turn to the box
  `heard+DEVICE` (`heard+macbook` for the built-in mic), so a session hears your voice
  by mail only once it subscribes to that box. Your agent runs this once it is an
  administrator (step 2, the mail path):

  ```bash
  message subscription add heard+macbook
  ```

- **Wake or ride along.** For each mail in the session box, the pager's rules decide:
  - **Wake:** the pager pages your agent: at once when it is idle, or after 60 seconds
    when it is busy and the mail has not ridden along yet.
  - **Ride along:** the mail waits, and the mail hooks (section 4) hand it to your agent
    as a `[mail]` line on its next tool call. It never wakes an idle agent.

  To see the rules, your agent runs:

  ```bash
  pager rule list --all
  ```

- **Mail to the session id wakes, by default.** So does mail to its seat's name, such as
  `claude` for a session started with `session start claude`. Either one rides along
  instead when it is marked non-urgent. Mail from the operator wakes too. Everything
  else rides along, a subscription's copy included, unless it is a heard turn that
  calls your agent.
- **The wake seat: "hey" and a name.** The ears' mail job mails every heard turn. When a
  turn starts with "hey" and the name of a seat in the wake file, it marks the turn as a
  call to that seat. A session with that seat, subscribed to that box, wakes on the
  call. For every other session subscribed to it, the turn rides along. "Hey everyone"
  is a call to every session subscribed to that box, once the wake file names a seat.
  `sessionkit setup` puts your agent in the wake file: its `Wake seat 'claude'` line
  (section 2). To add a seat by hand, your agent's name in place of SEAT:

  ```bash
  ears wake add SEAT
  ```

  A seat that is not in the wake file is never called by name over mail. Room mode
  (step 4) still wakes it: its waiter listens for "hey" and the name itself, and reads
  no wake file. The ears' warning that `NOBODY will be woken` means only this: no call
  by mail.

**MEASURED** (sessionmail, sessiontools and sessionvoice 0.3.0 and this kit, all from
their source, a temporary home directory, mail by the drop):

- `pager -h` says
  ``By default, mail to this session's id wakes this session; other mail in its box, such as a subscription's (`message subscription add BOX`), rides along.``
- The sessionmail plugin's start hook, given a new session, made its box (`cur`, `new`
  and `tmp`) before any pager listened.
- With a session's pager listening, mail to its session id paged it at once:
  ``pager: wake by `wake to:$me` (built-in)``.
- `pager rule list --all` lists seven built-in rules. The last two are `wake to:$me` and
  `ride *`.
- The pager's rules, given mail to the seat's name `claude`, woke that seat by
  `wake to:$me`. Mail to the session id marked non-urgent rode along.
- The pager's rules, given a heard turn marked as a call to `claude`, woke the seat
  `claude` by `carry call:$me`. A turn that called nobody, or another seat, rode along by
  `ride *`, and so did a copy of mail to a subscribed box.
- The ears' mail job, given "hey claude what time is it": with no wake file, it marked
  no call; after `ears wake add claude`, a call to `claude`. "claude what time is it",
  with no "hey", called nobody. "hey everyone" called nobody with no wake file, and
  everyone after.
- The pager's rules, given a heard turn marked as a call to everyone, woke both a
  session with the seat `claude` and one with another seat, by `carry call:everyone`.
- `sessionkit setup` printed `Wake seat 'claude': "hey claude" wakes it.`, and
  `ears wake list` then printed `claude: claude`.
- `ears-arm claude room --dry-run`, with no wake file, still armed its rule for "hey"
  and `claude`.

How a seat's mail is copied into its session box was read in sessionmail's source.
**NOT YET** with a live heard turn: that needs a microphone and a running session.

### Mail between agents

From sessionmail 0.2.0, `message send` hands each message to sessionmail's file drop
by default. The drop writes the message straight into the recipient's box on this Mac,
with no mail server and no setting. Postfix is opt-in: it is how mail reaches other
Macs. The kit installs sessionmail 0.3.0 or later, so it has the drop.

**The file drop. EXPERIMENTAL.** sessionmail's own acceptance test of the drop on a bare
Mac has not run yet. Mail carried by the drop stays on this Mac. Each step below says
what was measured. The walk ran on sessionmail's code before its 0.2.0 release,
with a temporary home directory, no postfix on the PATH, no tailscale and
no mail setting. Step 1 was measured on the released 0.2.0, on a fresh Mac.

1. **Get sessionmail 0.3.0.** Section 2 installs it: the drop and mail setup (step 4)
   ship from sessionmail 0.2.0, and the kit asks for 0.3.0 or later. **MEASURED**
   (a fresh macOS 27 VM, sessionkit 0.2.0 and sessionmail 0.2.0 from PyPI,
   inside a `claude` session, no postfix): `message send admin` printed
   `sent via mail drop (no MTA)`, exit 0, and `message list admin` showed it.
2. **Nothing to set.** The drop is the default: the `sendmail` setting is `"drop"`
   unless you name another in `~/.sessionkit/mail/settings/mail.json`. A fresh install
   has no such file and needs none: the default ships with sessionmail. A Mac that
   is not on a tailnet needs nothing more: the drop delivers to this Mac's own boxes
   with no MagicDNS suffix and no tailscale. It warns that a bare sender's address is
   qualified with the short host name only. **MEASURED** (a temporary home
   directory, with no `SESSIONMAIL_SENDMAIL`, no settings file, no `MAGICDNS_SUFFIX` and
   no tailscale): sent, exit 0, by the drop, and the message was in the box's `new/`
   folder. A variable that is set beats the file: if you set
   `export SESSIONMAIL_SENDMAIL=drop` for an earlier build, it still works, and
   removing it hands the choice back to the file. **MEASURED**: mail setup
   reported the carrier as the drop "from `$SESSIONMAIL_SENDMAIL`".

   **Jobs launchd starts.** launchd reads no shell file, and the drop needs none:
   `message send` reads the carrier from the settings file, so a job with nothing in
   its environment gets the drop too (read in sessionmail's settings docs). Three mail
   senders run that way:
   - **The phone bot** (section 6).
   - **sessionvoice's mouth notices**, sent by the mouth.
   - **ears-mail's heard turns**, the mail that pages your agent when you speak.

   From sessionvoice 0.2.1 and sessionphone 0.2.1 (the kit installs 0.3.0 of each), all
   three hand their mail to `message send`, so they ride the drop, and from sessionmail
   0.2.0 a heard turn sent by the drop reads as your voice (read in their 0.2.1 source).
   Their 0.1.0 releases handed it to `/usr/sbin/sendmail` themselves. **NOT YET** walked: no launchd job has yet sent by
   the drop on a fresh Mac.
3. **Install notmuch. HUMAN (Homebrew).** `message mark` and `memory` read mail through
   notmuch. Install it before step 4:

   ```bash
   brew install notmuch
   ```

   Mail setup writes sessionmail's
   own notmuch profile, `~/.config/notmuch/sessionkit/config` (under
   `$XDG_CONFIG_HOME` when that is set), with the mail folder as its database, runs
   `notmuch new` on it once to build the index, and links sessionmail's hooks there.
   It never reads or writes a notmuch config of your own: `~/.notmuch-config` and any
   other profile are left exactly as they are, and nothing is linked into them. It
   adopts no notmuch database: if the mail folder already holds one,
   `~/.mail/.notmuch`, mail setup writes no profile, and its
   `notmuch-profile` line says `MANUAL` instead of `wrote`, and names what to do. That
   database is yours, and the uninstall leaves it (section 8). **MEASURED**
   (a temporary home directory whose mail folder held a database made by
   its own `~/.notmuch-config`): `MANUAL` on two runs, no profile written, exit 4.
   Mail setup runs the profile's first `notmuch new` itself. What its first run does
   turns on whether notmuch is found:
   - **notmuch found:** one run writes the profile, builds the index, links both hooks
     and reports every step `DONE`, exit 0.
   - **notmuch not found:** the first run writes the profile, leaves its notmuch steps
     `BLOCKED` and exits 4.
     - Install notmuch with the block above.
     - Then run setup again. It builds the index, links both hooks and reports every
       step `DONE`, exit 0:

       ```bash
       sessionkit setup
       ```

   **MEASURED** (notmuch 0.40, sessionmail's mail setup built from its source ahead of
   its next release, a temporary home directory with no notmuch config): with notmuch
   not found, the profile written, both notmuch steps `BLOCKED` and exit 4; with
   notmuch then found, the second run built the index and linked both hooks, exit 0;
   with notmuch found from the start, one run, exit 0. No hand `notmuch new` in either,
   and no `~/.notmuch-config` was made. Nothing runs `notmuch new` after setup's one
   run, in sessionmail or the kit, and setup's own `note:` line says so: until
   something does (launchd, cron, or by hand), `message mark` and `memory` read the
   index setup built, which was empty. **NOT YET:** `brew install notmuch` on a fresh
   Mac.
4. **Make the boxes: `sessionkit setup`** (section 2). It runs sessionmail's mail setup
   first, `message setup`, which makes the mail folder and your box, writes the notmuch
   profile, builds its index and links its hooks (step 3), and prints every step
   with its state (`DONE`, `TODO`, `BLOCKED` or `MANUAL`), then what is left for
   you. It is safe to run again: a
   second run reports each step `DONE` and changes nothing. It writes no mail setting.
   It makes these boxes and no others: a box named for your account, the box you
   name with `sessionkit setup --mailbox NAME`, if you give one, and your assistant's
   box, `claude` (or the name you gave `--agent`). That last box is the one a session
   started with `session start claude` hears, and your Delta messages are addressed
   to it. It makes `claude` even when you give `--agent` another name, so a session
   started as `claude`, the default seat, always has its box. The drop never makes a
   box. Mail to a box that does not exist is refused and nothing is delivered, to
   that box or any other (exit 3). A plain `claude` session's own box is made when
   its pager first listens (section 4). Make every other box that mail goes to with
   mail setup, the box's name in place of NAME:

   ```bash
   message setup --box NAME
   ```

   The sender needs no box of its own. **MEASURED** (this release's
   sessionkit with sessionmail 0.2.0 from PyPI, a temporary home directory):
   `sessionkit setup --mailbox <box>` ran the real `message setup`, which made the
   mail folder, the operator's box, that box and `claude`, and wrote the notmuch
   profile; setup then wrote the operator, exit 4 (the notmuch step left: sessionmail
   0.2.0 left it on every first run, and mail setup that builds the index itself leaves
   it only while notmuch is not found);
   `message setup --box <box>` made one more box; a re-run reported each `DONE`,
   exit 0; a plain `sessionkit setup` passed `--box claude`,
   and the real `message setup` made the box `claude` beside the account's; mail to a box it had not made was refused, exit 3; and
   `pager listen` made its session's box.
5. **Check for `jq`.** This should print a path. macOS 27 ships `/usr/bin/jq`:

   ```bash
   command -v jq
   ```

   - It printed nothing? Install it:

     ```bash
     brew install jq
     ```

   Without `jq`, mail still
   lands in the box it is addressed to, but mail to a seat's name gets no copy in that
   seat's session box, so the pager listening there is not woken by it. **MEASURED**
   (macOS 27.0.1: `/usr/bin/jq` is jq 1.7.1; with `jq` off the PATH, the
   send went through with that warning).
6. **Same Mac only.** Mail to another host is refused with "not on this host", exit 3.
   **MEASURED**.
7. **Check it, from your agent** (inside `claude`, as in section 4). A box's name goes
   in place of TO, and a file to send in place of FILE:

   ```bash
   message send TO -s test -f FILE
   ```

   It prints `sent via mail drop (no MTA)` and exits 0, and the message is in that
   box's `new/` folder. **MEASURED** (a
   temporary home directory): both ways between two named boxes, and from one
   session to another; `message list` and `message read` showed each, and a signed
   one passed `message verify`.

**Mail to other Macs: postfix, opt-in.** The drop carries mail on this Mac only. To
send through postfix instead, name its `sendmail` in
`~/.sessionkit/mail/settings/mail.json`. Make the file if there is none, or add the
`sendmail` key beside the ones already there:

```json
{"version": 1, "hooks": true, "sendmail": "/usr/sbin/sendmail"}
```

The file needs its `hooks` key: without one, sessionmail reads the file as malformed and
leaves the hooks off. It is `true` here because section 4 turned the hooks on.

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
  [its own docs](https://github.com/sessionkit/sessionphone). A call needs these, in
  this order: Homebrew, ffmpeg, the speech server on 8890, then the phone link.
  - **Homebrew first**, from section 1.
  - **Then ffmpeg**, from Homebrew:

    ```bash
    brew install ffmpeg
    ```

    - A call without Homebrew is the workaround case. This guide does not cover it.
  - **Then the speech server, before you link the phone.** A call hears you
    through the speech server, so until it is installed, no call can hear you. On a fresh
    Mac that linked the phone first, the missing hearing showed only at the
    last step (a field report).
    - Ran section 5's step 2: nothing to run. Its
      `ears services install --agent NAME` installed the speech server with the
      voice services.
    - Skipped section 5: install the speech server alone. It builds the server
      and fetches its weights, about 2.9 GB.

      ```bash
      ears services install --only speech
      ```

    - Then link the phone. Linking is sessionphone's, in its docs. The name
      people see in their chat list goes in place of NAME, and a name with a
      space needs quotes, like `"Ada Lovelace"`:

      ```bash
      sessionphone setup --name NAME
      ```

    **MEASURED** as `--dry-run` (sessionvoice 0.3.0 from PyPI, a temporary home
    directory, nothing on the port): `--only speech` would build the server's
    venv, load `dev.sessionkit.voice.mlx-audio` and fetch about 2.9 GB of
    weights. It needed neither `ears install`'s model nor `--agent`.
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
  - **MEASURED** end to end, walked and passed (a fresh macOS 27 VM,
    this release's kit with sessionphone 0.2.1, under the drop). `sessionphone bot
    install` needed no key, no registry and no seat step. The bot's mail went unsigned
    into the box `claude`, and a real call was answered aloud by a session started
    with `session start claude`. One hint was typed during the walk: the agent was
    reading an older copy of the phone guide, which asked for a signing key, and was
    pointed to the signing line above. **NOT YET:** the ears on a real microphone
    (section 5), and the uninstall (section 8). Before 0.2.1, on a fresh macOS 27 VM,
    sessionphone 0.2.0's bot would not start, because it signed its mail and a fresh
    install had no way to make it a signing identity.
- **Apple speech. HUMAN (Xcode, macOS 27).** This builds the Apple speech helper.
  **NOT YET**.

  ```bash
  ears install --apple
  ```

## 7. Known gaps you will hit

- **One plugin from two places loads twice.** Installed the five from clones before?
  Remove their marketplaces before the kit's plugin lines (section 3).
- **The mouth's default "heard" box** names the authors' own mailbox; set
  `VOICEMODE_MOUTH_HEARD_BOX` to yours.
- **Moving a clone breaks its plugin** without a word (section 3 says how to repair it).
- **Claude Code's auto mode can refuse mail between agents** (`[Create Unsafe Agents]`).
  Section 4 gives the permission rule, and how to leave auto mode.
- **`sessionview install --check` says `not ready` when only `neomutt` is missing.**
  This guide does not ask for neomutt. sessionview's check names it for its messages
  tab, in a `MISSING  neomutt` line, and that line alone makes the whole check end
  `not ready: fix the MISSING lines above, then run this again`, exit 1. The sidebar
  still draws. **MEASURED** (sessionview 0.3.0 from PyPI, a temporary home directory,
  tmux and notmuch present, no neomutt): every other requirement `PASS`, then
  `not ready`, exit 1. **MEASURED** on a fresh macOS 27 VM at 0.2.0: the same
  `not ready` from neomutt alone, and `sessionview agents` then drew its sidebar.
- **`sessionview agents` asks you one question the first time it opens**, before it
  draws: `sessionview can start an agent for you each time it opens.` When it can list
  your agents it numbers them, `claude` among them, beside `n) no agent -- never ask
  again`; when it cannot, it asks for a name, or `no`. The answer is kept. Give a name,
  and that agent is started in sessionview's session each time it opens, unless one by
  that name is already running. Give `n` or `no`, and it never asks again. To change
  the answer later, run one of these:
  - An agent each time it opens, the agent's name in place of VALUE:

    ```bash
    sessionview-config set autostart_agent VALUE
    ```

  - None:

    ```bash
    sessionview-config set autostart_agent ""
    ```

  **MEASURED** on a fresh macOS 27
  VM at 0.2.0: the question came first, and after `no` the frame drew the sidebar.
  **MEASURED** (sessionview 0.3.0 from PyPI, a temporary home directory):
  `sessionview autostart --status` printed
  `autostart_agent=ask (will ask on next open)`, and each `sessionview-config set` above
  changed it. The numbered list is read in its 0.3.0 source.

## 8. Uninstall

**NOT YET** as a whole: no rehearsal has run this page end to end. Three blocks, in
this order. The first two remove the program and keep everything you made. The third
deletes your data, and only if you choose it. Every line, why it is there, what it
leaves alone, and what was measured: [the uninstall reference][uninstall-ref].

### 1. Stop and remove the jobs

The voice jobs run from the kit's files and the phone bot from the plugins', so they
go before the plugins and the kit do.

- **Quit every `claude` session.** The steps below run in a plain terminal. In a
  session with the pager's monitor, `/exit` asks one more question, because the
  monitor is background work: answer `Exit and stop tasks`. **MEASURED** (a fresh
  macOS 27 VM at 0.2.0).
- **Look first.** This only reads. It lists the jobs the voice and the phone put
  down, and any sessiontools job you turned on:

  ```bash
  launchctl list | grep -E 'dev\.sessionkit\.|sessionvoice|voicemode\.ears|sessionphone|sessiontools'
  ```

- **The phone** (section 6). No phone: skip it. This stops the bot and removes its
  job. The account stays: it is your data.

  ```bash
  sessionphone bot uninstall
  ```

- **The voice** (section 5). First undo the ride-along hook you added by hand
  ([the voice][uninstall-voice]). Then look: this names each job it would remove,
  and changes nothing:

  ```bash
  ears services uninstall --dry-run
  ```

  Then remove them:

  ```bash
  ears services uninstall
  ```

- **A sessiontools job you turned on** (not on this path): turn it off now, with
  [its own line][uninstall-off]. It needs the `session` command that block 2 removes.
- **Check.** Wait a few seconds, then run the look again. It prints nothing once
  every job is gone:

  ```bash
  launchctl list | grep -E 'dev\.sessionkit\.|sessionvoice|voicemode\.ears|sessionphone|sessiontools'
  ```

**NOT YET** as a run, but for `/exit`. The voice's `--dry-run` was **MEASURED** on a
temporary home directory.

### 2. Remove the plugins and the tool

- **The plugins**, from the kit's marketplace (section 3's first lines). The first
  line removes its six plugins. The second deletes the copies Claude Code keeps of
  them, which the first leaves:

  ```bash
  claude plugin marketplace remove sessionkit
  rm -rf "${HOME:?}/.claude/plugins/cache/sessionkit"
  ```

  Installed them from your own clones instead: [the clones' lines][uninstall-tool].
- **The tool.** This removes the `sessionkit` command and every command it brought:

  ```bash
  uv tool uninstall sessionkit
  ```

- **What the programs left.** Program files, none of them your data: the voice model
  and run state, the speech server, the sidebar's old state, the mail cache, the image
  reader's cache, and the voice's list of audio devices. The last line removes that
  list's folder only if it is empty. Paste the lines as they are: they carry no
  comments, because in zsh a `#` typed at the prompt is not a comment.

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

  In zsh, the `imgtext-*` line prints `no matches found` when there is none: that is
  fine.

The marketplace line and the cache line were **MEASURED** on a temporary home
directory, and `uv tool uninstall sessionkit` on temporary uv tool directories. The
leftovers' lines are **NOT YET**.

### 3. Your data (opt-in)

**Only if you want it gone. This cannot be undone.** Blocks 1 and 2 kept all of it.
Each item below is one kind of data, and its lines are in the reference. Skip an item
to keep it. **NOT YET**: no walk has run these lines.

- ⚠️ **Account tokens.** `~/.sessionkit/tools/accounts/` holds the backups
  `session account` made of your tokens. Delete it, or keep it, on purpose:
  [Accounts][uninstall-accounts].
- ⚠️ **VoiceMode shares some of these files**: the mouth's mail box, and the
  transcript in `~/.voicemode`. Use VoiceMode? Skip the lines marked "No VoiceMode":
  [Mail][uninstall-mail] and [Voice][uninstall-voice-data].

Your data, in this order:

- **Mail:** every agent's box in `~/.mail/agents`, and mail setup's notmuch profile.
  [Mail][uninstall-mail].
- **Session records:** `~/.session`, `~/.sessionmail`, and the agent file
  `sessionkit setup` wrote. [Session records][uninstall-session].
- **Accounts:** above. [Accounts][uninstall-accounts].
- **The kit's home, `~/.sessionkit`:** each package's settings, logs and state, the
  phone's included. It keeps `claude-code.json`, which is yours.
  [The kit's home][uninstall-home].
- **Voice:** `~/.sessionvoice`, `~/.ears` and the voices you enrolled.
  [Voice][uninstall-voice-data].
- **Phone:** `~/.sessionphone`, the agent's chat account and its keys.
  [Phone][uninstall-phone].
- **Your clones** (section 3), only after block 2. [Your clones][uninstall-clones].

Caches and tools other programs share, each only if nothing else uses it:
[the lines][uninstall-caches].

- The speech weights, about 2.7 GB, in the shared Hugging Face cache.
- uv's cache, about 1.4 GB.
- uv's Python 3.12 (the speech server's, about 72 MB) and 3.14 (the kit's).
- Homebrew's tmux, ffmpeg, notmuch, and jq if you installed it.

**What stays.** The older logs in `~/Library/Logs`: an uninstall never deletes from
there. Homebrew, uv and Claude Code, and their folders. Never delete `~/.cache`,
`~/.local/bin` or `~/.voicemode` whole: other tools keep files there.
[What stays][uninstall-stays].

[uninstall-ref]: docs/uninstall.md
[uninstall-voice]: docs/uninstall.md#1-stop-and-remove-the-jobs
[uninstall-off]: docs/uninstall.md#1-stop-and-remove-the-jobs
[uninstall-tool]: docs/uninstall.md#2-remove-the-plugins-and-the-tool
[uninstall-accounts]: docs/uninstall.md#accounts
[uninstall-mail]: docs/uninstall.md#mail
[uninstall-session]: docs/uninstall.md#session-records
[uninstall-home]: docs/uninstall.md#the-kits-home
[uninstall-voice-data]: docs/uninstall.md#voice
[uninstall-phone]: docs/uninstall.md#phone
[uninstall-clones]: docs/uninstall.md#your-clones
[uninstall-caches]: docs/uninstall.md#4-caches-and-tools-other-programs-share-opt-in
[uninstall-stays]: docs/uninstall.md#5-what-stays
[lid]: docs/troubleshooting.md#ears-running-but-deaf
[sv-hosted]: https://github.com/sessionkit/sessionvoice/blob/HEAD/docs/models.md#a-hosted-speech-endpoint-instead
