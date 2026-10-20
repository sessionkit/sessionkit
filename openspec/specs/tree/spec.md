# tree Specification

## Purpose

Where a session's, a seat's and an agent's files live under `~/.session/`,
where each tool's host settings live, and what a package's directory under
`~/.sessionkit/` holds beside its settings. How the settings in these places
stack is the settings specification (`openspec/specs/settings/spec.md`).

Not yet specified, and so not required here:

- A `box` link in the session directory to the session's mail.
- The name and form of the record written when a seat is first launched.
- A settings log in the seat directory.
- What `home: true` in the host or template layer makes.
- Whether `home: false` and `home_dir` set in one file are refused.
- Where the host settings of a tool that the package map does not name
  live.

## Requirements

### Requirement: `~/.session/` holds `agent/`, `seats/` and `sessions/`

The tree SHALL be `~/.session/agent/`, `~/.session/seats/<seat>/` and
`~/.session/sessions/<session-id>/`. Under `agent/`, an agent's file SHALL
be `config/<name>.md`, or `config/<name>/<name>.md` beside its other files
for an agent that has any, and an agent's home SHALL be `home/<name>/`.
`agent` is the literal word, singular. `agents/` is the old name, and it
SHALL become a symlink when the `session` tool moves.

#### Scenario: A bare session has a directory

- **GIVEN** a Claude Code session with no agent and no seat
- **WHEN** it is born
- **THEN** `~/.session/sessions/<session-id>/` is its directory, and no
  `agent/` or `seats/` entry is made for it

### Requirement: The session directory, by reader

In a session directory, files read across tools SHALL go under their type:
`settings/<tool>.json`, `log/<tool>/*.jsonl` and `log/settings.jsonl`.
Files one tool reads SHALL go under that tool: `mail/` (the mail tool's
state for the session), `ears/` and `mouth/`. The session's certificates,
`session.pub` and `session.pub.sid`, `session-id`, `launch/` (with the
launcher's prompt file and agent plugin), `tmp/`, `scripts/` and `home/`
SHALL sit at the top. A directory SHALL be made only when something is
written to it.

#### Scenario: A session that never spoke has no mouth directory

- **GIVEN** a session whose mouth was never used
- **WHEN** its directory is listed at the end of the session
- **THEN** there is no `mouth/`

### Requirement: The seat holds settings, and a home if asked

A seat directory SHALL hold `settings/<tool>.json`, and `home/` only when
its settings set `home`. A session's mail state SHALL be the session's,
never the seat's. A record SHALL be written when a seat is first launched,
and kept in git.

#### Scenario: A seat with no home

- **GIVEN** `~/.session/seats/<seat>/` with `settings/mail.json` only
- **WHEN** a session takes the seat
- **THEN** the session's mail state goes to
  `~/.session/sessions/<session-id>/mail/`, and no
  `~/.session/seats/<seat>/home/` is made

### Requirement: Homes: none by default, one per session

The `session` tool SHALL have two keys: `home: true` makes a home at the
computed place, and `home_dir: PATH` sets the place and turns the home on.
The computed place is `~/.session/agent/home/<name>/`,
`~/.session/seats/<seat>/home/` or `~/.session/sessions/<session-id>/home/`,
by the layer that set `home`. The lowest layer that sets `home` SHALL win,
one home per session, so a `home: false` in a lower layer turns off a
`home_dir` set above it. `home` is the switch and `home_dir` the place: a
`home: true` in a lower layer SHALL only turn the home on, and the place
stays the `home_dir` set above it. The home SHALL reach commands as
`SESSION_HOME`, never as `$HOME`.

#### Scenario: A seat opts out of its agent's home

- **GIVEN** `settings: {session: {home_dir: ~/somewhere}}` in the agent
  layer
- **AND** `home: false` in the seat's `session.json`
- **WHEN** a session takes the seat
- **THEN** `SESSION_HOME` is unset, and no home directory is made

#### Scenario: A lower home: true is only "on"

- **GIVEN** `home_dir: ~/somewhere` in the agent layer
- **AND** `home: true` in the seat's `session.json`
- **WHEN** a session takes the seat
- **THEN** `SESSION_HOME=~/somewhere`, not `~/.session/seats/<seat>/home/`

#### Scenario: A lower home_dir turns a home back on

- **GIVEN** `home: false` in the agent layer
- **AND** `home_dir: ~/somewhere` in the seat's `session.json`
- **WHEN** a session takes the seat
- **THEN** `SESSION_HOME=~/somewhere`

#### Scenario: An agent's home

- **GIVEN** `settings: {session: {home: true}}` in
  `~/.session/agent/config/<name>/<name>.md`
- **WHEN** a session of that agent starts
- **THEN** `SESSION_HOME=~/.session/agent/home/<name>` is in its
  environment, and `$HOME` is unchanged

#### Scenario: A seat that sets no home gets none

- **GIVEN** a seat whose layers set no `home`
- **WHEN** its session starts
- **THEN** `SESSION_HOME` is unset, and no `home/` directory is made

### Requirement: The host layer is `~/.sessionkit/<package>/settings/`

Host settings for each tool the package map names SHALL live in
`~/.sessionkit/<package>/settings/<tool>.json`, beside
`<tool>.schema.json`: the package first, then `settings/`, then a file
named for the tool. A package's directory SHALL carry no `session` prefix;
the packages are `mail`, `voice`, `view`, `phone`, `tools` and `kit`. The
root SHALL be `~/.sessionkit/`, and no environment variable SHALL move it.
The reader SHALL NOT read host settings from any older location. A host
MAY keep links from an older settings location into this tree for
programs not yet updated, and the reader SHALL NOT read through them. An
app that edits settings reads and writes `~/.sessionkit/*/settings/`,
`~/.session/seats/*/settings/` and `~/.session/sessions/*/settings/`, and
asks `session settings` for merged values.

#### Scenario: The mail tool's host file

- **GIVEN** the `mail` tool
- **WHEN** the reader looks for its host settings
- **THEN** it reads `~/.sessionkit/mail/settings/mail.json`

#### Scenario: The mouth's host file moves

- **GIVEN** the mouth's host file at an older path of its own
- **WHEN** the mouth moves
- **THEN** its host file is `~/.sessionkit/voice/settings/mouth.json`, the
  old path is a symlink to it, and an app that edits settings writes the
  new one

### Requirement: A tool's package comes from one map

A reader given a tool SHALL find the tool's package through one map, kept
by the tools package, and SHALL NOT guess the package from the tool's
name. The map SHALL send `session`, `claude-code` and `sounds` to `tools`;
`mail` to `mail`; `ears` and `mouth` to `voice`; and `view` to `view`.

#### Scenario: The mouth is in the voice package

- **GIVEN** the `mouth` tool
- **WHEN** the reader resolves its package
- **THEN** the map gives `voice`, its host file is
  `~/.sessionkit/voice/settings/mouth.json`, and no `~/.sessionkit/mouth/`
  is read

### Requirement: A package keeps its state and secrets beside `settings/`

A package's directory under `~/.sessionkit/` SHALL hold `settings/` and,
beside it, the package's state and secrets: the files its tools keep that
are not settings. A package's state and secrets SHALL NOT be kept inside
`settings/`. A reader of settings, the `session settings` command and an
app that edits settings among them, SHALL read only `settings/` in a
package's directory, and SHALL NOT read the folders beside it.

#### Scenario: Settings are read from `settings/` only

- **GIVEN** `~/.sessionkit/tools/` holding `settings/` and, beside it,
  `accounts/`
- **WHEN** `session settings` lists and reads the settings of the tools in
  that package
- **THEN** it reads files under `~/.sessionkit/tools/settings/` only, and no
  file under `~/.sessionkit/tools/accounts/` is read or listed

### Requirement: The session tool's account folder

The `session` tool's account files SHALL live in one folder, `accounts/`,
in the directory of the package the package map names for the `session`
tool: `~/.sessionkit/tools/accounts/`, beside
`~/.sessionkit/tools/settings/`. The tool SHALL take the package from the
map, never from a literal name. The folder SHALL hold the account registry,
the account config (optional), the host ledger, the token-file backups, the
keychain backups, and a short-lived scratch folder for setting up a token,
removed when the setup ends. These files are secrets, and the backups hold
tokens, so the folder SHALL NOT be under `settings/`. A folder the tool
makes, the account folder, a missing parent of it or a folder inside it,
SHALL be made 0700. A folder that already exists SHALL keep its mode: the
tool SHALL NOT change it. Each file the tool writes in the folder SHALL be
made 0600. The account files' earlier location, outside `~/.sessionkit/`,
SHALL be moved into this folder only by an explicit step an operator runs,
never as a side effect of an install or an upgrade.

#### Scenario: The folder comes from the map

- **GIVEN** the package map, which sends `session` to `tools`
- **WHEN** the `session` tool finds its account folder
- **THEN** it is `~/.sessionkit/tools/accounts/`, beside
  `~/.sessionkit/tools/settings/`, and the registry is
  `~/.sessionkit/tools/accounts/accounts.json`

#### Scenario: A first write makes the folders private

- **GIVEN** a home with no `~/.sessionkit/` and no account files
- **WHEN** the `session` tool first writes the account registry
- **THEN** `~/.sessionkit/`, `~/.sessionkit/tools/` and
  `~/.sessionkit/tools/accounts/` are each made 0700, and the registry is
  0600

#### Scenario: An existing folder keeps its mode

- **GIVEN** `~/.sessionkit/tools/accounts/` already there, mode 0750, with
  no keychain backups yet
- **WHEN** the `session` tool backs up the keychain item
- **THEN** `accounts/` is still 0750, `keychain-backups/` is made 0700
  inside it, and the backup file is 0600

#### Scenario: An upgrade moves no account files

- **GIVEN** account files at their earlier location and no
  `~/.sessionkit/tools/accounts/`
- **WHEN** the tool is upgraded
- **THEN** the files stay where they are, and they reach the account
  folder only when an operator runs the move step
