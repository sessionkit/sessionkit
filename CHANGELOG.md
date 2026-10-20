# Changelog

All notable changes to sessionkit are documented here. The format is
[Keep a Changelog](https://keepachangelog.com/en/1.0.0/); versions follow
[Semantic Versioning](https://semver.org/spec/v2.0.0.html). The one
version lives in `pyproject.toml`; `scripts/release.py` bumps it with
`uv version`, mirrors it into `.claude-plugin/*.json` when present, and
stamps this file.

## [Unreleased]

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
