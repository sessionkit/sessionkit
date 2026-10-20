# Settings

How the session family keeps its settings: in JSON files, in layers, where
the most specific layer wins. A host can set a default, and one agent, seat
or session can change it for itself.

- **Where:** under `~/.sessionkit/<package>/settings/`, in the folder of
  the package that ships the tool, with the agent, seat and session layers
  under `~/.session/` ([where](#where-settings-live)).
- **How they stack:** template, host, agent, seat, session. The lowest
  wins, a `_locked` key stops the layers below from changing it, and the
  environment is not a layer ([the cascade](#the-cascade)).
- **Who follows it:** not every package does yet. Each package's own page
  lists its keys ([each package](#each-packages-settings)).
- **The kit's own keys:** the operator's ([the kit's keys](#the-kits-own-keys)).
- **See what applies:** `session settings <session-id> [tool]` prints each
  setting with the file that set it.

Settings are JSON for now.

## Where settings live

Each tool has a short name (`mail`, `session`, `sounds`, `ears`, `mouth`,
`claude-code`), and its files are named for it. Its template and host files
live in the settings folder of the package that ships it,
`~/.sessionkit/<package>/settings/`:

| Package | Its settings folder | The tools whose files are there |
| --- | --- | --- |
| sessiontools | `~/.sessionkit/tools/settings/` | `session`, `sounds`, `claude-code` |
| sessionmail | `~/.sessionkit/mail/settings/` | `mail` |
| sessionvoice | `~/.sessionkit/voice/settings/` | `ears`, `mouth` |

| Layer | Where its files are |
| --- | --- |
| template | `~/.sessionkit/<package>/settings/<tool>.template.json`, shipped with the tool |
| host | `~/.sessionkit/<package>/settings/<tool>.json`, then `<tool>.d/*.json` beside it |
| agent | the agent's file, `~/.session/agent/config/<name>.md`, under `settings:` in its front matter |
| seat | `~/.session/seats/<seat>/settings/<tool>.json`, then `<tool>.d/*.json` |
| session | `~/.session/sessions/<session-id>/settings/<tool>.json`, then `<tool>.d/*.json` |

- **One folder for each package.** A tool reads its template and host
  files from its package's settings folder, and from no other folder. No
  variable moves that folder. A few tools also take a variable that names
  one settings file instead, such as `EARS_CONF`; their own pages say so.
- **Settings only.** A package keeps its other files, such as state and
  logs, outside its `settings/` folder.
- **Mail stays in `~/.mail`.** That folder holds the mail itself, not
  settings, and it does not move.

## The cascade

The layers stack from the most general to the most specific. Each one
overrides the one above it:

1. **template:** the defaults a tool ships.
2. **host:** yours, for everything on this machine.
3. **agent:** one agent's file, for every session that agent runs.
4. **seat:** one seat, the named place an agent works from.
5. **session:** one running session.

The rules:

- **The lowest layer wins.** A session's value beats its seat's, which
  beats its agent's, and so on up to the template.
- **Inside a layer,** `<tool>.json` is read first, then each file in
  `<tool>.d/` by name. A later file wins.
- **Maps merge key by key.** Any other value, a list included, replaces the
  one above it whole.
- **`_locked`** is a list of dotted key paths. A locked key keeps the value
  of the file that locked it: every layer below ignores it.
- **The environment is not a layer.** When a session starts, each
  environment variable a tool's settings schema names is written into that
  session's layer once, as `<tool>.d/50-env.json`. After that the files
  decide.

An example, for a made-up tool named `example`. The host sets two keys and
locks one, in `~/.sessionkit/<package>/settings/example.json`:

```json
{"_locked": ["greeting.volume"], "greeting": {"text": "hello", "volume": 40}}
```

One session changes both, in
`~/.session/sessions/<session-id>/settings/example.json`:

```json
{"greeting": {"text": "good morning", "volume": 90}}
```

That session reads `text` as `good morning`, from its own file, and
`volume` as `40`, because the host locked it.

The requirements are written down in [the settings
specification][spec-settings], which also lists what it does not yet
specify, and [the tree specification][spec-tree], for where the files live.

## Each package's settings

Each package's own settings page lists its keys: name, type, default, what
it does and which file it lives in. The last column says whether the
package reads its settings through the cascade today, so an agent, a seat
or a session can override them. It was measured from each package's code
when this page was written; the package's own page is the authority.

| Package | Its settings page | Follows the cascade today? |
| --- | --- | --- |
| sessionmail | [sessionmail's docs/settings.md][mail] | **Partly.** Some keys, such as a seat's subscriptions and whether the pager is required, are read from the host, seat and session layers. There is no agent layer yet. |
| sessiontools | [sessiontools's docs/settings.md][tools] | **Mostly.** The busy sounds and the context band read all five layers. The operator, the session list and the pane state read the template and host layers only. |
| sessionvoice | [sessionvoice's docs/settings.md][voice] | **Partly.** The mouth reads the agent, seat and session layers for its voice, its volume and how it speaks a line, over its host file. The ears read only their own file, `~/.sessionkit/voice/settings/ears.json`, or the file `EARS_CONF` names. |
| sessionphone | [sessionphone's docs/settings.md][phone] | **No.** It reads environment variables (`DC_...`) and its own folder, `~/.sessionphone`. |
| sessionview | [sessionview's docs/settings.md][view] | **No.** It has a cascade of its own: a template, `~/.sessionkit/view/settings/view.json`, then `.sessionview` files in a store and a project. |
| sessionkit | [the kit's keys](#the-kits-own-keys) | **No, by design.** The operator is read from the template and host layers only: who the human is belongs to the machine, not to one agent or session. |

## The kit's own keys

The kit has one block of keys, `operator`. They are keys of the `session`
tool, so sessiontools reads them (`session operator`), and `sessionkit
setup` writes them.

- **The file `setup` writes:** `~/.sessionkit/tools/settings/session.d/10-operator.json`.
- **Where else they may be:** any host or template file of the `session`
  tool: `session.template.json`, `session.json`, or a `session.d/*.json`.

| Key | Type | Default | What it does | Written by |
| --- | --- | --- | --- | --- |
| `operator.mailbox` | string | none | The operator's mail box: one plain box name on this machine. Other sessions send their questions there. | `sessionkit setup`, or `setup --mailbox NAME`. With no flag, your account name, if sessionmail has a box by that name. |
| `operator.address` | string | none | The operator's full mail address (`name@host`), used as written. | `sessionkit setup --address ADDR` |
| `operator.privileged` | list of strings | empty: the operator alone | The seats or addresses that may act as administrators. The operator is always one of them. A later file's list replaces an earlier one whole, so keep every name in one list. | You, by hand, in a file of your own, such as `session.d/20-administrators.json`. `setup` never writes it. |

- **Nothing is a default person.** With no `operator` block, no one is the
  operator and no one is privileged.
- **A bad file removes, never grants.** A file that is not valid JSON, or a
  `privileged` that is not a list, reads as nothing configured.
- **`AGENT_OPERATOR_ADDR`** is an environment variable that changes where
  an agent sends a question. It grants no privilege, and `setup` ignores it.

[mail]: https://github.com/sessionkit/sessionmail/blob/HEAD/docs/settings.md
[tools]: https://github.com/sessionkit/sessiontools/blob/HEAD/docs/settings.md
[voice]: https://github.com/sessionkit/sessionvoice/blob/HEAD/docs/settings.md
[phone]: https://github.com/sessionkit/sessionphone/blob/HEAD/docs/settings.md
[view]: https://github.com/sessionkit/sessionview/blob/HEAD/docs/settings.md
[spec-settings]: ../openspec/specs/settings/spec.md
[spec-tree]: ../openspec/specs/tree/spec.md
