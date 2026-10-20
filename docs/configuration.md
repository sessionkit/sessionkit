# Configuration

What Session Kit itself configures: which files, which environment
variables, and where each one lives. The kit configures very little of its
own. Each family package configures itself, and its own configuration page
says how: the README maps them ([the family's pages][family]).

- **The operator:** one file, written once by `sessionkit setup`:
  `~/.sessionkit/tools/settings/session.d/10-operator.json`
  ([the operator](#the-operator)).
- **Installing:** no file. `uv tool install` takes its choices as flags
  ([installing](#installing)).
- **The plugin:** two manifests inside the package. Nothing to edit
  ([the plugin](#the-plugin)).
- **Working on the kit:** environment variables that `make` and the scripts
  read ([working on the kit](#working-on-the-kit)).
- **Settings:** how the family's settings files work, and the kit's own
  keys: [the settings guide][settings].

Paths are shown under `~`, your home folder.

## The operator

The operator is the human other sessions ask: for a decision, or for a
permission. `sessionkit setup` writes you as the operator.

- **The file:** `~/.sessionkit/tools/settings/session.d/10-operator.json`. It is a
  file of the `session` tool's settings, which sessiontools reads, so
  `session operator` is what reads it back.
- **What it holds:** `_about`, a note saying what wrote it, and one
  `operator` block: `{"operator": {"mailbox": "<you>"}}`, or `"address"`
  in place of `"mailbox"` if you ran `sessionkit setup --address`.
- **When it is written:** once. `setup` writes nothing if an operator is
  already set, in that file or in any other `session` settings file. It
  also writes nothing when it cannot confirm who you are; then it says how
  to name yourself.
- **Read with it:** the `session` tool's template and host files, in this
  order: `session.template.json`, `session.json`, then each
  `session.d/*.json` by name. A later file wins.
- **Change it:** edit the file. Or delete it and run `sessionkit setup`
  again.
- **The environment:** `AGENT_OPERATOR_ADDR` can change where an agent
  sends a question, nothing more. `setup` ignores it, and takes your
  account name from the system, not from `$USER`.

Each key, its type and its default: [the kit's keys][kit-keys].

## Installing

The install has no configuration file. Its choices are flags on the
command line:

- `uv tool install --python 3.14 sessionkit` puts the kit's commands, and
  every family command it re-exports, on your PATH.
- `--python 3.14` matters: on Python 3.15, two of the voice libraries have
  no build yet.

## The plugin

The package is also a Claude Code plugin. Its two manifests are part of the
package, not files you edit:

- `.claude-plugin/plugin.json`: the plugin, and the five family plugins it
  depends on.
- `.claude-plugin/marketplace.json`: a marketplace that lists the kit's
  plugin and the five.

The kit's own plugin does not load yet. Until it does, install the five
family plugins from your clones ([the README][readme-clones]).

## Working on the kit

These are read only when you build, check or release the kit from a clone.
Each is an environment variable, or a `make` variable you can give on the
command line.

| Name | Read by | What it does |
| --- | --- | --- |
| `BUMP` | `make release` | Which part of the version to bump: `patch` (the default), `minor` or `major`. |
| `VERSION` | `make release` | Set the version outright, in place of a bump. |
| `UV_PUBLISH_TOKEN` | `make publish` | The PyPI token, in uv's environment. Never typed on a command line. |
| `PYPI_TOKEN_PASS_PATH` | `make publish` | The `pass` entry that holds the PyPI token, when `UV_PUBLISH_TOKEN` is unset. |
| `SESSIONKIT_SCAN` | `make scan` | The path of the release scan tool. Unset, `make scan` uses `release-scan` from your PATH. |
| `AGENTS_CHECK_HOSTS` | `scripts/check_agents_archive.py` | Host names to list as private, spaced or comma-separated. Adds to `--host`. |

## Settings

The family keeps most of its settings in JSON files that stack in layers:
a template, then the host, then an agent, a seat and a session. The most
specific layer wins.

- Where the files live, how the layers stack, and which packages follow
  them today: the settings guide, [docs/settings.md][settings].
- The kit's own keys, the operator's: [the kit's keys][kit-keys].

[settings]: settings.md
[kit-keys]: settings.md#the-kits-own-keys
[family]: ../README.md#configuration
[readme-clones]: ../README.md#install-the-plugins-from-your-clones
