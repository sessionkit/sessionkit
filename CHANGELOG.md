# Changelog

All notable changes to sessionkit are documented here. The format is
[Keep a Changelog](https://keepachangelog.com/en/1.0.0/); versions follow
[Semantic Versioning](https://semver.org/spec/v2.0.0.html). The one
version lives in `pyproject.toml`; `scripts/release.py` bumps it with
`uv version`, mirrors it into `.claude-plugin/*.json` when present, and
stamps this file.

## [Unreleased]

## [0.3.1] - 2026-10-25

### Added

- docs/dependencies.md lists everything the kit depends on: what needs each
  one, by command, whether you need it, where it comes from and how you
  upgrade it.
- docs/dependencies.md links `uv.lock`, the full resolved set: every package
  at the version the kit is tested with.
- `sessionkit setup` adds a wake seat, so saying "hey" and the seat's name
  wakes it on a fresh install with no step of your own. It runs
  `ears wake add NAME`, where NAME is the `--agent` you give, else the
  default seat. A re-run leaves the wake file as it was, and a seat already
  there keeps its names. With no `ears` on the PATH, or when it refuses, it
  prints one line with the step to run, and that line never changes its
  exit. It never runs `ears services install`. `--dry-run` asks
  `ears wake list`, read only, says which seat it would add, and writes
  nothing.
- `sessionkit setup` reads the default seat's name from
  `session agent default`, the same word a bare `session start` gives its
  seat. The default seat's box and its wake seat both take that name. When
  the verb does not answer, setup asks for neither and says so in one line.
- The README's Quick start starts Claude with a bare `session start`. The
  first session on a Mac is `claude`, the default seat, and it hears your
  Delta messages and calls. A second session started the same way starts
  plain, and its one line names the session that holds `claude`. The lines
  are the ones sessiontools prints. INSTALL.md section 4 says only one
  session holds `claude`. Section 2 shows setup's wake seat line, and
  section 5 installs the voice services with no `--agent`, keeping
  `--agent` and `ears wake add` for when setup added no wake seat.
- docs/sessionview.md is sessionview's own page, imported from sessionview.
  It replaces the page that said none was written yet. It lists each
  `sessionview` verb and its form, and links what an install changes.
- INSTALL.md section 5 has a short "How waking works" part. It names the
  session box, subscriptions, the pager's wake and ride-along rules, that
  mail to the session id wakes by default, and the wake seat setup makes,
  with what was measured. The waking steps link to it.

### Fixed

- INSTALL.md no longer says nobody is woken when you speak without a wake
  seat. Without one, "hey" and a name wakes no one by mail, and room mode
  still wakes your agent.
- README.md no longer says the mouth needs a device. With no device set it
  plays on the Mac's default output, so the README and INSTALL.md test lines
  pass no `--device default`.
- INSTALL.md section 4 says the session box is made when the session starts,
  by the sessionmail plugin's start hook, not the first time the pager listens.
- `sessionkit setup` asks mail setup for the default seat's box, `claude`,
  on every run, beside the operator's box and the `--mailbox` and `--agent`
  boxes. With `--agent` naming another assistant it had asked for that box
  alone, so a session started as `claude` had no box and heard no mail. The
  step it prints when sessionmail has no mail setup, and `--dry-run`, carry
  the same boxes.
- The README's Claude Code link goes to the Claude Code docs. It had gone
  to claude.ai/code, Claude on the web.
- docs/session.md says a bare `session start` takes the default seat,
  `claude`, when no other session holds it and its box is there, and starts
  plain only when one does or the box is missing. It had said a bare start
  was always a plain session.
- The README lists what you need before the install, and gives Claude
  Code's own installer. Each command sits in a block of its own, under a
  label for its path ("No Homebrew:", "No uv:"), and opening a new terminal
  after it is a bullet of its own. INSTALL.md's install steps follow the
  same rule.
- INSTALL.md section 3's blocks paste into zsh as written. The clone and
  clones-removal blocks had a `<name>` to fill in, which zsh reads as a
  redirect; they are loops over the five now. The install loop's trailing
  comment, which a fresh Mac's zsh reads as words, is gone. `r` and the
  moved clone's folder are set in blocks of their own.
- INSTALL.md section 2's `command not found` follow-up is a bullet with its
  own block, and so is `uv tool update-shell`. They had sat in sentences.
- `source ~/.local/bin/env`, after uv's installer, is a block of its own
  in the README and INSTALL.md section 1, not a clause of the "open a new
  terminal" bullet. The README's "Then quit Claude Code and start it
  again" is a bullet, as INSTALL.md's is.
- INSTALL.md sections 4 to 8, and section 2's "Operator and administrators"
  notes, follow the family command rule. Each command you run sits in a
  block of its own, under a label for its path ("No file yet:", "From your
  own clones"), and what to do after it is a bullet of its own. A value you
  type is an UPPERCASE word, named before its block. Section 8 looks with
  `--dry-run` before the voice jobs' real uninstall, and its clones route
  removes the five marketplaces with one loop. Each keep-or-delete choice in
  section 8 (the speech models, the mouth's box, the notmuch index and the
  files shared with VoiceMode) is a labelled bullet, its lines under the one
  that deletes. The two account folders each have a block of their own, so
  a reader who keeps one pastes only the other.
- The README and INSTALL.md section 6 put the speech server before the
  phone: `ears services install --only speech` comes before you link the
  phone with `sessionphone setup`. A call hears you through the speech
  server. With the phone linked first, the missing server showed only at
  the last step.
- The README, INSTALL.md and docs/dependencies.md say what a call needs on
  a Mac, in one order: Homebrew, then `brew install ffmpeg`, then the
  speech server, then the phone link. The README had said the Command Line
  Tools alone would do, and named ffmpeg nowhere; a Mac with no Homebrew
  had no way to get it. A call without Homebrew is the workaround case,
  which the docs do not cover.
- INSTALL.md section 2 gives upgrade and reinstall each its own labelled
  block. One block held both, so a paste ran both. Running the setup again
  after exit 4 is a bullet with its own block; it had sat in the paragraph
  on its exits.
- The README and INSTALL.md give the two lines that put Claude Code on your
  PATH. Its installer does not change your PATH: run before uv's, it prints
  `~/.local/bin is not in your PATH`, and a new terminal has no `claude`.
- INSTALL.md section 4 makes turning the mail hooks on a step you take, and
  gives the file to make and its content. It had said the first run tells
  you so; the plugin writes the file with the hooks off at the first tool
  call, and tells only the agent.
- INSTALL.md says a plugin installed from your own clone runs in place, from
  the clone. It had said such a plugin runs from a copy in Claude Code's
  plugin cache. The kit's own plugins still run from their copy.
- INSTALL.md section 5 says that from sessionvoice 0.3.0 a bare
  `ears services install` refuses until you give `--agent NAME` or
  `--no-agent`, and which warnings a Mac with no postfix can ignore: the two
  about postfix, never the one about `--agent`.
- INSTALL.md section 1 counts the 8 GB or so that macOS takes for itself in
  its first minutes on a fresh install, and the sizes measured on a walk.
- INSTALL.md section 7 explains why `sessionview install --check` says
  `not ready` when only `neomutt` is missing, and the question
  `sessionview agents` asks the first time it opens.
- INSTALL.md warns that Claude Code's folder-trust prompt has "No, exit"
  ready (section 4), and that `/exit` asks one more question while the
  pager's monitor runs (section 8).
- INSTALL.md's MEASURED tags no longer carry a date. Each names what ran
  and on which versions.
- The MEASURED claims in docs/agent-letter.md and site/README.md no longer
  carry a date either. Each keeps what ran, the version and the OS.
- No command the docs give you to paste ends in a `#` comment any more:
  the README's Quick start and Development blocks, INSTALL.md's speaker
  names, docs/components.md's first commands and site/README.md. In a Mac's
  zsh a pasted `#` is a word, so `session list   # your live sessions`
  ran `session list` with four more words, and a comment's apostrophe
  opened a quote that ate the lines after it. Each explanation is prose
  now, beside its command. AGENTS.md's make targets are a list.
- A value you type into a command is an UPPERCASE word now, the word the
  command's own help uses: `message send TO` in the README's Quick start,
  `--address ADDR`, `--mailbox NAME`, `--agent NAME` and `--box NAME` in
  INSTALL.md, and `SEAT` and `SID` in docs/components.md. The sentence
  before each block says what goes in its place. A `<box>` is a redirection
  in zsh and in bash, so a pasted line stopped on it and did not run.
  docs/family-docs.md's "How a command is written" names the form.
- A test reads every shell block in the docs as zsh reads a paste, and
  fails on a `#` comment, a quote left open or an unquoted `<word>`.
- `sessionkit setup --help`, the operator file it writes and its "set mail
  up by hand" line now say where INSTALL.md is: in the kit's repository,
  https://github.com/sessionkit/sessionkit. INSTALL.md is not in the wheel
  or the sdist, so "See INSTALL.md" named a file an installed kit does not
  have.
- INSTALL.md names 0.3.0 where it said which release the kit installs or
  asks for. It had named 0.2.0 or 0.2.1 for sessionmail, sessiontools,
  sessionphone, sessionview and sessionvoice. Measurements made on 0.2.x keep
  their release and say they are not yet repeated on 0.3.0.
- INSTALL.md no longer says every command answers `--help`. Four
  `sessionview` verbs run instead: `install`, `autostart`, `from` and
  `sidebar`, which opens the sidebar.
- The README's step that turns the mail hooks on no longer writes
  `~/.sessionkit/mail/settings/mail.json` over. The plugin writes that file
  itself, with `"sendmail": "drop"` beside `"hooks": false`, and the old
  `echo` deleted every key but `version` and `hooks`, a carrier set by hand
  included. The step now edits the file when it is there, and writes the
  plugin's own template with the hooks on when it is not.
- The README's mail hooks step now also turns the hooks on in a
  `mail.json` that has no `"hooks"` key, such as one made by hand with only
  a `sendmail` key. It adds `"hooks": true` as the first key and keeps the
  rest. Before, it changed only a `"hooks": false` written on one line with
  no space before the colon, so such a file, or a pretty-printed one with a
  space or a line break there, kept its hooks off. INSTALL.md's postfix
  example now carries `"hooks": true`: sessionmail reads a `mail.json` with
  no `hooks` key as malformed and leaves the hooks off. And INSTALL.md says
  `ears install` downloads the voice-activity model from GitHub, in the
  requirements and in the first checks, where it said only "network".
- A release no longer re-locks the project. `scripts/release.py` runs
  `uv version --frozen`, on a dry run too, and writes the new version onto
  uv.lock's own `sessionkit` line as text, so a release changes no other
  line of uv.lock and resolves nothing. A plain `uv version` re-locked: cut
  before the family's new releases were on PyPI, it failed, and with
  `UV_FIND_LINKS` set it wrote a lock of local paths that the release then
  committed. The script refuses a uv.lock without exactly one root
  `sessionkit` block holding one `version` line, before it writes anything.
  `make release` runs the script with `python3`, not `uv run`, which
  re-locked before the script started.

### Changed

- The README's Quick start makes and enters a project folder
  (`mkdir -p ~/work && cd ~/work`) before `session start claude`, and says
  why: started in the home folder, Claude Code asks macOS for access to
  folders such as Desktop, Downloads, Photos and Media Library.
- The README's Command Line Tools bullet says the dialog can open behind the
  Terminal window, and to look for it in the Dock or with Cmd-Tab.
- The README says `ears install` downloads its voice-activity model from
  GitHub, one pinned release of Silero VAD checked against its SHA-256,
  where it said only "network".
- `sessionkit setup`'s last line is the bare launch step,
  `To hear Delta messages, start Claude with: session start`, when its
  agent is the default seat: no `--agent`, or `--agent` naming the seat's
  word. A bare `session start` takes that seat. With `--agent` naming
  another agent the line still ends `session start NAME`, and with a
  sessiontools that has no default seat it ends `session start claude`.
  INSTALL.md sections 2 and 4 and docs/sessionkit.md quote the bare line.
- INSTALL.md follows sessionmail's mail setup, which now runs `notmuch new`
  once on its own profile to build the index. You no longer run `notmuch
  new` by hand: with notmuch found, one setup run does it all, exit 0; with
  notmuch not found, the first run leaves both notmuch steps `BLOCKED` and
  exits 4, and the run after `brew install notmuch` finishes them. Section
  2 quotes the new numbered list of steps left, section 5 step 3 drops the
  hand `notmuch new`, and the uninstall says setup made the index.
  docs/dependencies.md says the same.
- sessionphone 0.3.1 carries a security fix for the bot's caller check;
  upgrade, and read sessionphone's release notes.

## [0.3.0] - 2026-10-24

### Added

- `sessionkit setup` says when the ears cannot hear you yet. It asks
  `ears backends`, read only, with a 5 second limit, and if the ears'
  voice-activity model is missing it prints one line naming `ears install`,
  just before the launch step. It never runs `ears install`, and the line
  never changes its exit. With no `ears` on the PATH, or no answer, it says
  nothing about the model.
- INSTALL.md says how the plugins reach a session started with
  `--setting-sources ""`: pass `--settings <file>` whose `enabledPlugins`
  names all six, because the kit's plugin stays off without the five it
  depends on. It also says that a `--plugin-dir` holding a plugin of the same
  name replaces the installed one for that session.

### Changed

- The kit needs the family's 0.3.0: sessionmail, sessiontools,
  sessionphone (with its media extra), sessionview and sessionvoice (with
  its capture extra) are each floored at 0.3.0.
- The README's Installation names what the install needs besides macOS and
  Claude Code: Homebrew, or at least Apple's Command Line Tools
  (`xcode-select --install`), because the plugin lines clone with their git
  and the ears build a Swift helper with their `swiftc`. It also gives the
  `ears install` step the plugin lines leave out: it fetches the ears'
  voice-activity model, without which they cannot hear you and
  `ears services install` refuses.
- Phone calls are walked for a session started with `session start <name>`:
  a fresh Mac took a real call, its bot's mail unsigned on the mail drop, and
  Delta messages reached a session started with `session start claude`. A
  plain `claude` session does not hear calls you make to it yet. The README
  and INSTALL.md say so, and keep
  the ears on a real microphone and the uninstall marked not walked.
  INSTALL.md also counts the speech server's disk, its venv (1.2 GB) and
  its models (2.7 GB, fetched on its first request), says the first call is
  silent for about a minute while they download, gives
  `ears services install --agent <name>` (without it nobody is woken when
  you speak), and gives Homebrew's time as a range, 87 to 220 seconds.
- INSTALL.md says that Claude Code's auto mode can refuse an agent's
  `message send` to another agent (`[Create Unsafe Agents]`). It gives the
  fix, a `Bash(message send *)` permission rule, and how to leave auto mode
  (Shift+Tab). Section 5 says the mail path's
  `message subscription add heard+<device>` is refused until your agent is
  an administrator, names the administrators file that lets it through, and
  leaves that path for later.
- The README and INSTALL.md give a safe upgrade, `uv tool upgrade sessionkit`,
  which keeps the Python the install chose, and a safe reinstall,
  `uv tool install --python 3.14 --reinstall sessionkit`. Measured with uv
  0.13.4: a reinstall without the pin drops it, and `--force` without it
  builds the kit again on the Python uv finds. Restarting Claude Code after
  the plugin lines is now a step of its own, before anything that runs a
  plugin's command: a session that was already open does not have them.
  INSTALL.md says where Claude Code reads `.claude/settings.local.json`
  inside a git repository (its root), and that the speech server's models,
  about 2.7 GB, stay in the Hugging Face cache after the uninstall, with the
  lines that remove only those three folders. docs/components.md and the website say
  phone calls are walked on a fresh Mac for a session started with
  `session start <name>`.
- INSTALL.md no longer says that an install without `--python 3.14` gets
  the 0.0.1 placeholder: that placeholder is gone from PyPI. Measured with uv
  0.13.4 and empty uv folders, the install fetches Python 3.15, then refuses,
  exit 1, as unsatisfiable (a voice library has no 3.15 build), and installs
  nothing. The `--python 3.14` advice stays.
- The synthetic dates in the docs and tests fall on one of two days,
  2030-06-09 and 2030-12-08. Where the text says one came before another,
  the earlier one reads 2030-06-09 and the later one 2030-12-08, so the
  order holds. Clock times are unchanged, and release headings keep their
  real dates.
- The README and the agent letter say how your agent talks with the kit: it
  speaks with `mouth say` and listens with `ears-arm`, and uses VoiceMode's
  `converse` only when you ask for converse by name. Both quote the rule from
  sessionvoice's ears skill. The agent letter has a second block to copy into
  your letter.
- docs/session.md is sessiontools' page for `session` now, not a stub: each
  verb, its form and one example. docs/ears.md and docs/mouth.md are
  imported again from sessionvoice: `ears services install` refuses with no
  `--agent NAME` or `--no-agent`, and the mouth's queue is 0700 and every
  line picks its device in one order, ending at the system default output.
- docs/session.md is imported again from sessiontools. Its two synthetic
  dates now fall on the two days, 2030-06-09 and 2030-12-08, and
  `session settings` lists `phone` among the tools it can pick.
- The tree spec's package map names the `phone` tool, in the `phone`
  package, as sessiontools' map does. Its host file is
  `~/.sessionkit/phone/settings/phone.json`.

### Fixed

- INSTALL.md's uninstall gives the plugin lines for each install route. A
  kit install removes the one `sessionkit` marketplace, then deletes
  `~/.claude/plugins/cache/sessionkit`, where its six plugins' copies stay
  after the remove. Before, it gave only the clones route's five
  marketplaces and five cache folders, so a kit install's copies were left
  behind. The README's Uninstall says the copies stay and points at it.

## [0.2.1] - 2026-10-22

### Added

- A dependency gate in the tests. The kit's ruled dependency list (the five
  family packages floored at 0.2.0, sessionmail, sessionphone and
  sessionvoice at 0.2.1, sessionphone with its media extra and sessionvoice
  with its capture extra) lives in one place,
  `tests/_ruled_deps.py`, with the ruling beside it.
  `tests/test_dependency_gate.py` holds pyproject.toml, the built wheel's
  `Requires-Dist` and uv.lock to it, and `make test` fails, naming the
  package and the drift, when any of them departs from it.
- `sessionkit setup` defines your assistant, so its Claude hears Delta
  messages. It writes the agent file `session start` reads,
  `~/.session/agents/claude.md` (not keyed, never over one already there),
  asks mail setup for the agent's box, `claude`, and ends with the one launch
  step: "To hear Delta messages, start Claude with: session start claude".
  `--agent NAME` names another assistant; two windows started as one name
  share its box. INSTALL.md's first agent starts with `session start claude`.
  No Delta message has yet been walked to a session started this way.

### Changed

- The README is rewritten for 0.2.0, short and install first. It leads with
  `uv tool install --python 3.14 sessionkit` and the one-step plugin install,
  which works at 0.2.0; the plugins-from-your-clones route is gone from it. It
  says why the Python pin, that a Command Line Tools dialog may come first,
  how to install the calls pack on 0.2.0, that mail works inside a session,
  and that `mouth say` needs `--device`. It says phone calls are installed,
  never that they work: their setup is not yet available on a fresh Mac, and
  it links sessionphone's own docs. Everything else is one line and a
  link. The commands, services, folders and logs move to
  `docs/components.md`, and the family's configuration pages to
  `docs/configuration.md`. A new test, `tests/test_readme_links.py`, holds
  the README to reference-style links, relative for the kit's own files, no
  emoji, and labels that all resolve.
- The five family packages are floored at 0.2.0, sessionmail,
  sessionphone and sessionvoice at 0.2.1, and sessionphone comes
  with its `media` extra, so the kit's install includes the phone's calls
  packages (aiortc, av and their dependencies). Installed is not set up:
  a call's setup is not yet available on a fresh Mac, and INSTALL.md
  section 6 points to sessionphone's own docs. The version is `0.2.1` in
  `pyproject.toml`, mirrored into `.claude-plugin/plugin.json` and
  `marketplace.json`, and `uv.lock` is re-locked against the 0.2.0 and
  0.2.1 releases on PyPI. pyproject gains `readme = "README.md"`, so the
  published page has a description.
- The README's `sessionkit --version` sample and INSTALL.md's voice and
  phone lines are re-measured on the 0.2.1 children: section 5's
  `ears services install --dry-run`, section 8's
  `ears services uninstall --dry-run` and `sessionphone bot uninstall
  --help`, and the three senders read in their 0.2.1 source.
- INSTALL.md section 2 follows 0.2.x: 14 commands install, the install
  size is measured (61 packages, about 93 MB downloaded, about 280 MB on
  disk), the calls packages download with the rest at `uv tool install`,
  and a Linux line names the PortAudio library sessionvoice's
  `sounddevice` needs there. On a fresh Mac `sessionkit setup` makes your
  box, writes the operator and exits 4 while notmuch is missing; the 0.1.0
  refusal text is gone. The agent letter's pager notes (`pager mute`,
  `pager unmute`, `pager stop --kill`, the monitor's off switch) and its
  `memory run` opt-in are marked as measured on sessionmail 0.2.0.
- INSTALL.md drops what 0.1.0 needed, now that the kit floors every family
  package at 0.2.0. The intro no longer says mail needs postfix or a later
  release. Section 4: the pager monitor, its off switch and `pager mute` /
  `pager unmute` are measured on sessionmail 0.2.0, and mailing your agent
  goes by the file drop. Section 5: the steps are sessionvoice 0.2.0's, the
  job labels are measured on it (`dev.sessionkit.voice.*`, four agents
  including ears-mail), the plugin `bin/ears` and `ears-arm` detours for
  0.1.0 are gone, and the mail steps say sessionmail 0.2.0 is the release
  the kit installs. Section 7 loses its three 0.1.0 gaps.
- INSTALL.md section 8, the uninstall, drops its 0.1.0 branches: the plugin
  `bin/ears` route and the warning that `ears services uninstall` has no dry
  run are gone. Its dry run, the `sessionphone bot uninstall` help and
  `uv tool uninstall sessionkit` (14 commands) are measured on this release.
  Section 4's monitor paragraph names the sessionmail plugin section 3
  installs, not a clone; section 2's assistant step is measured on this
  release; section 1's kit size agrees with section 2's.
- The agent letter says the trust-registry refusal is sessionmail 0.2.0's:
  that release already names the key, says no registry is created and
  points at the doc (read in its source). INSTALL.md section 6's boxes line
  is measured on sessionmail 0.2.0, and names the agent's box `claude`.
- `docs/ears.md` is re-imported from sessionvoice. Its turn-mail passage no
  longer says the launch agents deliver nothing, or that a heard turn reads
  as plain mail, "until sessionmail" ships something. It says how
  sessionmail 0.2.0's mail drop delivers the turns with no mail server,
  that the `heard` box must exist first (`message setup --box heard`), and
  how to send by postfix instead.
- Phone calls are installed, not yet walked, and the words follow
  sessionphone 0.2.1: whether its bot signs follows the mail carrier, and
  under the drop it needs no key. The README's calls passage is one line
  and a link to sessionphone's own page on it, `docs/bot-mail-signing.md`,
  and its 0.2.0 hand-install of the calls pack is gone. The quick start
  sends you to `session start claude`, never a bare `claude`, and says
  why. INSTALL.md section 6 says the carrier is the `sendmail` setting,
  not whether postfix is installed, and names the two things the bot's
  mail needs to reach Claude: the agent's box, and Claude started as the
  agent. The site's Status and `docs/components.md` agree. No fresh Mac has
  walked a call yet, so nothing says calls work.

## [0.2.0] - 2026-10-21

### Added

- `sessionkit setup` sets up mail first. It runs sessionmail's mail setup
  verb, `message setup`, before it writes the operator, because that verb
  makes the operator's box. A sessionmail without the verb gets the step
  printed, and the operator half still runs. A new exit, 4: the operator is
  set and mail steps are left for you. An operator file stranded at the
  0.1.0 place stops the run before mail setup, so nothing is made. INSTALL.md's
  "Mail between agents" follows sessionmail 0.2.0: the file drop is the
  default, with nothing to set, so the `~/.zshenv` lines go; postfix is
  opt-in, named by `sendmail` in mail's settings file, and nothing in the
  kit or in mail setup edits it. Mail setup makes the boxes (instead of
  `mkdir`) and writes sessionmail's own notmuch profile; a notmuch config of
  your own is never read or written, and the one `notmuch new` runs on that
  profile after the first setup run. The phone bot, the mouth's notices and
  ears-mail ride the drop from their next releases. The uninstall removes
  the profile and its index with the mail. The agent letter notes how wake
  items meet the trust registry. All of it waits on sessionmail 0.2.0, not
  released yet.
- `sessionkit setup --mailbox NAME` asks mail setup to make NAME's box as
  well (`--box NAME`), so a named box on a fresh install is there before the
  operator is written. With no `--mailbox` it asks for no box: on a fresh
  install mail setup makes only the box named for the account. The account
  name the operator defaults to is case-folded, as mail setup folds it, so
  it names the box that was made.
- Configuration docs. `docs/configuration.md` says what the kit itself
  configures: the operator file `sessionkit setup` writes, the install's
  flags, the plugin's manifests and the variables `make` reads.
  `docs/settings.md` is the family's settings guide: where the files live
  today and where they are moving, the five layers and how they stack, a
  table of each package's settings page with whether it follows the layers
  yet, and the kit's own `operator` keys. The README gains
  `## Configuration`, one absolute link to each package's configuration
  page, and `## Logs`, where each package logs, ending on the Health line.
- The settings specification. `openspec/specs/settings/spec.md` states
  what the settings cascade requires: one file per tool at each layer, the
  order the layers stack in, a command-line flag above them for one run,
  `_locked`, the agent layer, how a launch's environment becomes a
  setting, drop-in directories and how a tool moves to the new paths.
  `openspec/specs/tree/spec.md` states where a session's, a seat's and an
  agent's files live, and the homes. Each lists what is not
  yet specified. `docs/settings.md` links both. The release archive ships
  `openspec/specs/` and leaves out `openspec/changes/`, the specs' working
  drafts (`.gitattributes`).
- The AGENTS.md archive rule. `docs/family-conventions.md` gains a
  Documentation item, beside "AGENTS.md holds the instructions": AGENTS.md
  ships in the release archive (it is never export-ignored), and stands
  alone there. Every link or repo path it names is in the archive, and it
  names no host, task id, person or agent name; notes for the maintainers'
  own machines go in CLAUDE.md, below the import.
  `scripts/check_agents_archive.py <repo>` is its check: it reads
  `git archive HEAD` and exits 1 on a missing AGENTS.md or a dead
  reference. It lists task ids, and any host the caller names with
  `--host`, for a person to read. sessionkit and sessionphone meet it. The
  "AGENTS.md holds the instructions" item is measured again: every repo but
  sessionview meets it now.
- The CHANGELOG rule. `docs/family-conventions.md` gains a Documentation
  item, beside "CHANGELOG in Keep a Changelog form": one bullet for every
  change a user would notice, fixes too (under `### Fixed`), while
  test-only, vendoring and CI changes skip it. Every `ready/` tag's message
  carries exactly one line, `Changelog: yes` or
  `Changelog: none, no user-visible change`, and the item gives the
  command that checks it. No repo meets it yet, and no tooling checks it.
- The README shape and its template. `docs/family-conventions.md` gains a
  Documentation item, "README in the family's 12-section shape": the five
  H2s every family README started from stay, Configuration and Logs are the
  must-haves, and two choices are still open (monitoring's own section, the
  name "Running"). Each of the six repos is measured against it; none meets
  it yet. `templates/README.md` is the shape as a file to copy, each section
  with a one-line comment. The five-H2 item's measure is corrected:
  sessiontools no longer has the five.
- `sessionkit --version` (and `-V`): the kit's installed version, then
  each family package's, one per line, read from the installed metadata.
  A package that is missing prints `not installed`. Before this, the flag
  did not exist (exit 2).
- `sessionkit setup [--mailbox NAME | --address ADDR] [--dry-run]`: writes
  you as the operator, the human your agents ask, in one new file,
  `~/.settings/session/session.d/10-operator.json`. It writes a mail box
  only if sessionmail has a box by that name, and otherwise refuses (exit 1)
  and says how to name yourself. It never writes `privileged`, so the
  operator alone is privileged. It never overwrites an operator already set,
  never writes past a settings file it cannot read, and no environment
  variable changes what it writes. INSTALL.md section 2 runs it last in the
  install block, and its "Operator and administrators" part says how to add
  an administrator.
- `LICENSE`: the kit is licensed AGPL-3.0-or-later, and the file is
  byte-identical to the five children's. `pyproject.toml` declares it
  (`license = "AGPL-3.0-or-later"` and `license-files = ["LICENSE"]`), so
  the wheel and the sdist carry it. Before this, the kit had no licence
  file and declared none.
- INSTALL.md section 4 gains "Your first agent, in tmux": get tmux from
  Homebrew (it brings no Python; the kit's Python stays uv's), start a tmux
  session, start a plain agent in it with `session start`, and have it run
  `pager listen`. Mailing it waits on the mail-server step, which has no
  runbook yet, and the section says so.
- The tree spec says what a package's directory under `~/.sessionkit/`
  holds beside `settings/`: the package's state and secrets, never inside
  `settings/`, and nothing that reads settings reads them. The first such
  folder is the `session` tool's account folder,
  `~/.sessionkit/tools/accounts/`, with the account registry, config, host
  ledger, token backups and a short-lived setup folder. The folders the
  tool makes there are 0700, an existing folder keeps its mode, and every
  file the tool writes is 0600. The old location moves only by an
  operator's explicit step. The item leaves the spec's "not yet specified"
  list.

### Changed

- The tests that check setup writes no private word, and that its source
  holds none, no longer carry their own word list. They read the private
  scan list `make scan` uses, from the file `SESSIONKIT_SCRUB_RULES` names,
  and test every row of it, with a planted word from each row as a positive
  control. Without the variable they skip, and the run's summary counts the
  skips and names the variable to set. A failure names a row, never a word.
- The family's conventions are split into one file per area:
  `docs/family-build.md`, `docs/family-docs.md`,
  `docs/family-file-structure.md`, `docs/family-release.md` and
  `docs/family-tests.md`, each linked from `docs/family-conventions.md`.
  The Documentation items named in the bullets above (the AGENTS.md archive
  rule, the CHANGELOG rule, the README shape) are now in one file per
  governed file, unchanged: `docs/family-docs-agents.md`,
  `docs/family-docs-changelog.md` and `docs/family-docs-readme.md`, beside
  `docs/family-docs-license.md`, with `docs/family-docs.md` as their hub.
  The tests read each rule from its own file. Like
  `docs/family-conventions.md`, the new files are maintainers' notes: the
  release archive leaves them out (`.gitattributes`).
- Settings live in `~/.sessionkit/<package>/settings/`. `sessionkit setup`
  writes the operator to
  `~/.sessionkit/tools/settings/session.d/10-operator.json`, and the docs
  name each package's settings folder: `tools`, `mail` and `voice`. No
  variable moves the folder, and nothing reads the old one: if the operator
  file an earlier release wrote is still there and none is in the new
  folder, `setup` writes nothing, names both files and exits 1. The
  uninstall steps remove only the kit's settings files there, and keep
  `claude-code.json`.
- INSTALL.md's voice steps follow sessionvoice 0.2.0. Section 5 says the
  speech server is found or installed by `ears services install` (mlx-audio
  on port 8890), which now loads four LaunchAgents, `com.sessionvoice.*`, and
  includes ears-mail. On 0.2.0 it runs from the kit's own `ears`; on 0.1.0,
  what PyPI has today, the plugin `bin/ears` step stays, tagged as 0.1.0's,
  for the install and the uninstall. Section 5 gains an optional speaker
  names step (`ears services install --only speakers`, then
  `ears speakers enrol`) and a link to sessionvoice's hosted speech endpoint
  for the mouth. The 0.1.0 differences stay in section 7's known gaps (no
  speech server, and the keeper the kit's `ears` cannot find), and section 8
  says 0.2.0's `ears services uninstall` honours `--dry-run`. Step 4 says
  0.2.0 puts `ears-arm` on the Bash tool's PATH through the plugin's
  `bin/ears-arm`, and keeps 0.1.0's full cache path for 0.1.0.
- INSTALL.md names a mail path for a Mac with no postfix (SK-95). Section
  5's "Mail between agents" is now its own heading with two branches:
  already have postfix, nothing to do; no postfix, turn on sessionmail's
  file drop, labelled experimental and needing sessionmail 0.2.0, which is
  not released yet. Its steps, each tagged as measured or not yet:
  `SESSIONMAIL_SENDMAIL=drop` and `MAGICDNS_SUFFIX` in `~/.zshenv`, each
  recipient's box made first, `jq`, same Mac only. The intro, section 4's
  "Mail it", ears-mail's line, the known gap for mail and the uninstall
  point at it, and the README's "Not yet" line links to it. ears-mail
  still needs postfix.
  The drop does not reach jobs launchd starts, and the section names all
  three that send mail: the phone bot, the mouth's notices and ears-mail's
  heard turns, with the fixes not yet released (EARS-381, SM-660, SM-847).
- `CHANGELOG.md` merges with `merge=union` (`.gitattributes`), so two
  branches that each add a bullet under `[Unreleased]` no longer conflict
  (SK-91; sessionvoice made the same change, EARS-356).
  `tests/test_changelog_union.py` replays a real conflict from this repo's
  history (SK-89) with and without it, and fails on a duplicated bullet,
  one way union damage shows. Union keeps both versions of an edited bullet
  without a conflict, and can bring a removed word back, so `AGENTS.md` says
  never to rewrite or delete a bullet that has landed on master, and that a
  change that removes words merges on its own or is scanned again.
- The package summary, the line PyPI shows under the name, now reads
  "Session Kit gives your Claude Code sessions voice, mail, a phone line
  and a tmux sidebar, in one install." It used to end "Name reserved; the
  tool follows." and left out voice. `.claude-plugin/plugin.json` and the
  kit's entry in `marketplace.json` carry the same line.
- `sessionkit --help`, the package docstring and the sessionkit skill's
  description and opening line now say the same summary line. They used to
  say "Session Kit: the session family in one install - mail, phone, view
  and tools for coding agents", which left out voice.
- The manual install no longer installs atomnote. INSTALL.md section 3's
  loop names the five children only, and `claude plugin list` should show
  five plugins. atomnote is now its own line, marked optional, for a reader
  who wants atomic notes. README's uninstall loop removes the five, and
  atomnote's marketplace if you added it.
- INSTALL.md and README no longer mention atomnote. It is not in the 0.2.0
  release set, so the optional install line in INSTALL.md section 3 and the
  uninstall lines for it, in INSTALL.md section 8 and README, are gone. The
  install and uninstall cover the five plugins only.
- Release metadata for 0.2.0. The version is `0.2.0` in `pyproject.toml`,
  mirrored into `.claude-plugin/plugin.json` and `marketplace.json`, and
  `uv.lock` is re-locked to match. The classifier is now
  `Development Status :: 3 - Alpha` (was `1 - Planning`). Every author is
  `Mike Bailey <mike@sessionkit.ai>`: in pyproject, in plugin.json, and as
  the marketplace owner and each listed plugin's author. sessionphone's
  entry named a different author before this. `[project.urls]` and plugin.json's
  `homepage` and `repository` point at
  `https://github.com/sessionkit/sessionkit`. The five family pins stay at
  `>=0.1.0` until the children's 0.2.0 releases are on PyPI.
- `.gitattributes`: `/CLAUDE.md export-ignore`. CLAUDE.md stays in the tree
  and in history, but `git archive` and the GitHub tarball leave it out, so
  `claude plugin validate --strict` passes on the shipped archive.
- `make scan` finds the scanner on the PATH: with `SESSIONKIT_SCAN` unset
  it runs `release-scan` from the PATH. A `SESSIONKIT_SCAN` you set, in the
  environment or as `make scan SESSIONKIT_SCAN=...`, still wins. With
  neither, it exits 2 and its message names both lookups. Before this,
  `make scan` exited 2 whenever `SESSIONKIT_SCAN` was unset.
- `requires-python` is now `>=3.11,<3.15` (was `>=3.11`). The kit declares
  only the Python versions it can install on. onnxruntime, which the kit
  pulls in through `sessionvoice[capture]`, ships wheels for CPython 3.11
  to 3.14 and no source distribution, so on CPython 3.15 the install
  failed. `uv.lock` is re-locked for the new range and no package version
  changed. The lock-wheel test in `tests/test_lock_wheels.py` checks the
  range against `uv.lock`, and it passes now.
- INSTALL.md section 8, Uninstall, removes everything the install put
  down, in reverse order: part A the program (the phone bot, the voice
  jobs, the plugins and their cached copies, the kit command, the
  caches), part B your data, only if you choose it. It warns that
  `ears services uninstall --dry-run` is not a dry run.
- The docs say the pager monitor is on by default (SM-726). INSTALL.md
  section 4, the README's Usage and `docs/agent-letter.md` no longer send
  you to sessionmail's retired `plugins/pager-monitor` to turn it on: the
  sessionmail plugin that section 3 installs runs `pager listen --monitor`
  itself. Its off switch and `pager mute` / `pager unmute` are marked NOT
  YET, because the 0.1.0 `pager` on PyPI has none of them.
- `docs/agent-letter.md` says what `pager off` and `pager stop` do in
  each sessionmail. With the 0.1.0 `pager` from PyPI they end the monitor
  for good. From the next release (SM-726) they refuse on the monitor
  (exit 4) and name `pager mute` and `pager stop --kill`.
- The dates the docs and tests give for a measurement or a ruling are
  synthetic now, in a year that has not come yet. Most of them read the
  same date. Where the text says one came before another, the earlier one
  is a day or two before it, so the order holds. Release headings keep
  their real dates, and no clock is faked.
- INSTALL.md names the launchd labels by the family's one scheme,
  `dev.sessionkit.<package>.<job>`: the voice's jobs are
  `dev.sessionkit.voice.mlx-audio` and `dev.sessionkit.voice.ears-<name>`.
  The old forms, `com.sessionvoice.*` and 0.1.0's `com.voicemode.ears-*`,
  stay only as history: the voice install retires the old form. The
  uninstall's `launchctl list` look and check find the new labels as well
  as the old. The kit itself still ships no launchd job.

### Fixed

- `uv tool install sessionkit` now puts every child command on the PATH.
  The kit re-declares sessionview's four commands (`sessionview`,
  `sessionview-config`, `sessionview-session`, `sessionview-messages`) and
  sessionvoice's `talk`, re-measured from each child's built wheel. The
  `pyproject.toml` comment that said sessionview declares no commands is gone.
- A convention test no longer fails on a machine with a global git
  `core.hooksPath`: the throwaway repo it commits in now ignores the
  reader's own hooks.
- The tests' throwaway git repos now ignore git config passed in the
  environment as well: each drops every `GIT_*` variable before it
  commits, so `GIT_CONFIG_COUNT` forcing `commit.gpgsign` no longer fails
  them.

- The release archive no longer ships the maintainers' notes:
  `docs/family-conventions.md`, `docs/pre-public-checklist.md` and
  `docs/release-numbering.md` are export-ignored. They stay in the tree and
  in history. AGENTS.md, `docs/troubleshooting.md` and the README template
  no longer link them, and the tests that read them skip in an archive and
  still run in a checkout.
- INSTALL.md section 3 no longer says the repositories are private and that
  a stranger stops there. It names the clone source,
  `https://github.com/sessionkit/<name>`, marked not yet measured from a
  clean Mac.
- The overview page under `site/` drops its internal `pending` notes and
  the stale "coming" marks: 0.1.0 is on PyPI, and the troubleshooting hub
  and the agent letter have landed.
- The README's links to INSTALL.md and `docs/agent-letter.md` work on
  PyPI. The README is the package's PyPI page, and PyPI cannot follow a
  relative link, so each one 404'd there. They are absolute now, at
  `https://github.com/sessionkit/sessionkit/blob/HEAD/<path>`.
- The docs name sessionview's settings where they live now,
  `~/.sessionkit/view/settings/`. `docs/settings.md` gives its home file as
  `~/.sessionkit/view/settings/view.json`, and INSTALL.md's uninstall
  removes that folder with the other packages' settings folders, no longer
  the old folder in your home directory. The `.sessionview` files in a
  store or a project keep their name. The uninstall also removes the
  sidebar's state folder by its name now, `~/.local/state/sessionview`, as
  well as by its old name.
- INSTALL.md's uninstall names the `session` tool's account folder,
  `~/.sessionkit/tools/accounts/`, instead of leaving it on disk without a
  word. Part B gains an Accounts item: what the folder holds (the account
  registry, its config, the host ledger and the backups of each token
  `session account use` replaced), that part A and the Settings item leave
  it, and the one line that deletes it, with a warning that the backups
  are account tokens, so a reader who keeps the accounts skips it. The
  Settings item says each package keeps its state and secrets beside
  `settings/`, pointing at the tree specification.
- The docs name `master`, the branch the public repositories are on. Their
  links named a branch the repositories do not have, so they 404'd.
  INSTALL.md's fresh clone for a plugin with nothing checked out says
  `-b master`, and says that line has not yet been run. The links into
  this repository, in README.md and `docs/`, are relative now, so they
  open from a checkout or an editor. This undoes the change above that
  made the README's links absolute for PyPI: on the package's PyPI page,
  the README's links into this repository do not open. The links into the
  other family repositories stay full and point at each repository's
  default branch, `HEAD`, so they name no branch, and each one's text
  names the package and the file. A test fails if a shipped file names a
  branch in a link into a family repository, clones with the old branch,
  or links into this repository by a full URL.
- INSTALL.md's uninstall deletes the transcript of what the ears heard
  where a fresh install writes it. Part B's Voice item deleted it only in
  `~/.voicemode`, but a fresh install keeps it in `~/.sessionvoice`, so it
  stayed on disk. The item now deletes `~/.sessionvoice` and `~/.ears`
  whole, and it names what they hold: the transcript, who spoke each turn,
  the pairing token, the mouth's kept lines, and the clips recording keeps
  when it is on. On a host where sessionvoice uses `~/.voicemode` (an older
  sessionvoice wrote there, or VoiceMode's converse wrote the transcript
  first), it deletes only the files there that are sessionvoice's alone. The
  transcript in `~/.voicemode`, its lock, and the two folders VoiceMode
  shares go only if you do not use VoiceMode, since VoiceMode writes the
  same transcript. The item says where to look when `SESSIONVOICE_HOME`,
  `VOICEMODE_BASE_DIR` or `EARS_HOME` names another folder. Mail deleted
  every box in `~/.mail/agents`, the mouth's queue with them, but
  VoiceMode's mouth queues in that same box, `~/.mail/agents/mouth`. Mail
  now deletes every box but that one, and the mouth's box goes only if you
  do not use VoiceMode. Part A
  deletes the call listeners' state, the memory command's cache and the
  voice's audio device list. Session records delete the session list's
  state. Accounts deletes the account folder from before the move,
  `~/.config/sessiontools/`, with the same token warning. Settings says the
  voice's speech keys are in its settings folder. The voice jobs' check
  says to wait a few seconds, since a job still exiting stays listed.

## [0.1.0] - 2026-10-10

### Added

- sessionkit, born 2030-06-09.
- The family in one install (SK-8): the package depends on sessionmail,
  sessiontools, sessionphone, sessionview and sessionvoice (unpinned in
  this release) and re-declares every child command (`message`, `pager`,
  `memory`, `session`, `sessionphone`, `ears`, `ears-serve`, `mouth`); the
  plugin depends on the five, and the marketplace lists them. Their
  sources are to be published at `github.com/sessionkit/<name>`.
