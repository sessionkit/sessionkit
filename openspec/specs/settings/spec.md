# settings Specification

## Purpose

The settings cascade every tool of the session family reads its settings
through: where a tool's settings files live at each layer, how the layers
stack, how a command-line flag outranks them for one run, how a key is
locked, and how a launch's environment becomes a setting. Where the
directories themselves live is the tree specification
(`openspec/specs/tree/spec.md`).

Not yet specified, and so not required here:

- How two layers' values combine beyond "the lower layer wins": whether a
  map merges key by key, how a list combines, how a map whose order
  matters is written, and how mail's subscriptions combine across layers.
- The order in which a layer's `<tool>.json` and its `<tool>.d/` directory
  are read when a layer has both.
- Checking settings against a tool's schema.
- The arguments and output of the `session settings` command.
- Any layer below the session.

## Requirements

### Requirement: One settings file per tool, at every layer

A tool's settings SHALL live in a file named for the tool at each layer
that sets any: `~/.sessionkit/<package>/settings/<tool>.json` for the
host, `~/.session/seats/<seat>/settings/<tool>.json` for a seat, and
`~/.session/sessions/<session-id>/settings/<tool>.json` for a session. A
layer file SHALL hold only the keys it sets. `<package>` is the package
the tool belongs to, read from the one map the tree specification states.

#### Scenario: The mail tool at three layers

- **GIVEN** `~/.sessionkit/mail/settings/mail.json`,
  `~/.session/seats/<seat>/settings/mail.json` and
  `~/.session/sessions/<session-id>/settings/mail.json`
- **WHEN** the reader is asked for the `mail` settings of that session
- **THEN** it reads those three files, the `settings:` map in the agent
  file's front matter and the template the tool ships, and no other file

### Requirement: The layers stack, and the lowest wins

The reader SHALL merge the layers in this order: the tool's template, the
host, the agent, the seat and the session. Each layer SHALL override the
one above it, so the session has the last word. For each key, the reader
SHALL name the file that set it.

#### Scenario: A seat's value over the host's

- **GIVEN** `~/.sessionkit/voice/settings/mouth.json` with `voice: voice-a`
  and `~/.session/seats/<seat>/settings/mouth.json` with `voice: voice-b`
- **WHEN** a session of that seat asks for `mouth.voice`
- **THEN** the answer is `voice-b`, and the reader names the seat file as
  its origin

### Requirement: A command-line flag outranks every layer, for one run

A tool MAY offer a command-line flag for a setting. A value given by that flag
SHALL win over every layer, and SHALL apply to that run only. The tool SHALL NOT
write a flag's value to any layer. When a layer locks the key, the tool SHALL
refuse the run and name the file that locked it.

#### Scenario: A flag over a session file

- **GIVEN** `~/.session/sessions/<session-id>/settings/mouth.json` with
  `voice: voice-a`
- **WHEN** the tool runs once with `--voice voice-b`
- **THEN** that run uses `voice-b`, and the session file still holds
  `voice: voice-a`

#### Scenario: A lock holds against a flag

- **GIVEN** `~/.sessionkit/voice/settings/mouth.json` with `voice: voice-a` and
  `_locked: ["voice"]`
- **WHEN** the tool runs with `--voice voice-b`
- **THEN** the run is refused, and the error names the host file as the one
  that locked `voice`

### Requirement: A lock is a field, not a layer

Any layer's file MAY carry `_locked`, a list of dotted key paths. A path
locked in a layer SHALL make the reader ignore that key in every layer
below it, and `session settings` SHALL name the file that locked it. A
dotted path MAY lock one entry of a map (`rules.<name>`).

#### Scenario: A host lock holds against a session

- **GIVEN** `~/.sessionkit/mail/settings/mail.json` with `hooks: true` and
  `_locked: ["hooks"]`, and a session file with `hooks: false`
- **WHEN** the reader computes `mail` for that session
- **THEN** `hooks` is `true`, and its origin is the host file, marked
  locked

### Requirement: Agent settings are the agent file's front matter

The agent layer SHALL be an optional `settings:` map in the front matter
of the agent's Markdown file, keyed by tool. The nested form is the stored
form. A dotted key (`mouth.voice`) is shorthand that the reader SHALL
expand down to a map and never inside one, so a map key that holds a dot,
such as a seat or box name, stays whole. A file that sets one path both
ways SHALL be refused, and the error SHALL name the key.

#### Scenario: Dotted and nested say the same thing

- **GIVEN** `settings: {mouth.voice: voice-a}` in one agent file and
  `settings: {mouth: {voice: voice-a}}` in another
- **WHEN** each is read
- **THEN** both yield `mouth.voice = voice-a`

#### Scenario: Both forms at once is a refusal

- **GIVEN** `settings: {mouth.voice: a, mouth: {voice: b}}`
- **WHEN** it is read
- **THEN** the reader refuses and names `mouth.voice`

### Requirement: The agent layer is the file the launch used

A session's birth SHALL record the agent file it was launched with, as
`agent_file` in the session layer's `session.json`. The reader SHALL take
the agent layer from that file, and from `~/.session/agent/config/<name>`
when none is recorded; either way it stays the agent layer, below the
seat. No values SHALL be copied into the session: the report names the
real file.

#### Scenario: An agent launched from a plugin's file

- **GIVEN** a session launched with its agent file taken from a plugin's
  agents directory
- **WHEN** `session settings` reads that session
- **THEN** the agent layer is the plugin's file, and the report names that
  file

### Requirement: The environment is read once, at birth

A settings variable set at launch SHALL be read once, at the session's
birth, into `~/.session/sessions/<session-id>/settings/<tool>.d/50-env.json`,
and each variable SHALL be logged by name in the session's
`log/settings.jsonl`. After birth the file wins: a resumed session keeps
its file. Claude Code's and git's own variables are not settings and stay
environment.

Each tool's installed schema,
`~/.sessionkit/<package>/settings/<tool>.schema.json`, SHALL name the
tool's own variables: one `x-env` entry on the key the variable sets. The
key's `type` says how the string is read: a list of names, split on commas
and spaces, into a map of `true`; a number; or a string. The birth SHALL
walk the installed schemas. A variable that no schema names is not a
setting and SHALL NOT be read.

#### Scenario: A schema names its variable

- **GIVEN** `~/.sessionkit/mail/settings/mail.schema.json` with
  `"subscriptions": {"type": "object", "x-env": "SESSIONMAIL_SUBSCRIBE"}`
- **AND** `SESSIONMAIL_SUBSCRIBE=example+one` at launch
- **WHEN** the session is born
- **THEN** `settings/mail.d/50-env.json` holds
  `{"subscriptions": {"example+one": true}}`, and the session's
  `log/settings.jsonl` names `SESSIONMAIL_SUBSCRIBE`

#### Scenario: An unnamed variable stays environment

- **GIVEN** `EXAMPLE_LIMIT=100` at launch, named by no schema
- **WHEN** the session is born
- **THEN** no `50-env.json` carries it, and the log does not name it

#### Scenario: A subscription removed stays removed

- **GIVEN** `SESSIONMAIL_SUBSCRIBE=example+one,example+two` at launch, read
  into the session's `mail.d/50-env.json` as two map entries
- **WHEN** `message subscription remove example+one` writes
  `mail.d/70-live.json` with `subscriptions: {example+one: false}`
- **THEN** the next listen subscribes to `example+two` alone, and the
  variable is not read again

### Requirement: One file or a directory of drop-ins

A layer MAY be one file, `<tool>.json`, or a directory, `<tool>.d/*.json`,
whose files SHALL be read in name order, a later file winning; one file is
the trivial case. A drop-in splits one tool's settings by writer; it SHALL
NOT make one tool of two.

#### Scenario: Three writers, one tool

- **GIVEN** `mail.d/50-env.json` (written at birth), `mail.d/70-live.json`
  (written by `message subscription add`) and `mail.d/90-hand.json`
  (written by hand)
- **WHEN** the session layer is computed
- **THEN** the three are read in that order, and the origin of each key is
  the one file that set it

### Requirement: The reader reads new paths only, and a move ships three things

The reader SHALL read the paths in this specification and no old path.
Each tool's move to these paths SHALL ship three things together: a
one-time conversion of its old files into `<tool>.json` at the right
layers, the tool's new writer, so nothing writes the old form again, and a
symlink at the old path for readers not yet updated. A tool SHALL appear
in `session settings` only once it has moved.

#### Scenario: Before mail moves

- **GIVEN** the reader built, and the mail tool's old settings untouched
  in `~/.sessionmail/`
- **WHEN** `session settings <session-id> mail` runs
- **THEN** it reports no `mail` settings, and says the tool has not moved

#### Scenario: The hooks file, moved

- **GIVEN** the mail move has run
- **WHEN** a hook reads `hooks`
- **THEN** it reads `~/.sessionkit/mail/settings/mail.json`, and
  `~/.session/mail/settings.json` is a symlink to it
