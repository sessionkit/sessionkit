# sessionkit service

One command over every service the kit's packages run: see them all, look
at one, restart one or a group. Part of [the kit's own command][sessionkit].

- `sessionkit service list`: every service, by group, A to Z.
- `sessionkit service status talk`: one service, the long form.
- `sessionkit service restart talk`: `launchctl kickstart -k`; writes no
  file.
- `sessionkit service restart voice`: names every job, then asks y/N.

How it works:

- **A service is a file.** Each package's install writes one JSON file per
  service under `~/.sessionkit/<package>/services/`. The kit walks that
  tree and keeps no list of its own. It writes none of these files.
- **launchd says whether it runs.** The kit reads `launchctl list` (and
  `launchctl print` for the long form) and joins it with the files.
- **A word** is a service's name (`talk`, `bot.NAME`), a group (`mail`,
  `phone`, `tools`, `voice`), `<group>.<name>`, a launchd label, or `all`.
- **A group or `all` asks first.** It names every job, in the order it will
  act, and asks y/N. With no terminal, it needs `--yes`.
- **A live phone call blocks a restart** of a job whose file says
  `"hazard": ["call"]`, and of a job with no file yet, unless `--force`.
  The check is the phone package's own, run on each bot's plist
  environment. A check that cannot run counts as a call, and so does a
  bot launchd has loaded whose plist is gone.
- **Exit codes:** 0 done, 1 a launchctl call failed, 2 usage or refused
  (no such name, not loaded, disabled, a live call, an answer of no,
  `--yes` needed), 3 launchd cannot be reached from this shell.

## The verbs

- `sessionkit service list`: every service, grouped by package, groups and
  names A to Z, in 53 columns. Each row is a glyph, the name, a state word,
  and a note only when something is worth a look. `--json` prints one
  object per service. `list -h` prints the legend.
- `sessionkit service status`: bare, the same as `list`. With a name, a
  group or `all`, the long form: one field per line, with the label, the
  file, enabled, the state, the pid, the last exit, the port and what
  listens on it, the plist, the logs and the owner's install command.
- `sessionkit service restart NAME|GROUP|all`: runs
  `launchctl kickstart -k gui/<uid>/<label>` for each job, which stops it
  and starts it again from its owner's plist. One named service restarts
  at once. A job that is not loaded is refused, and the reply says how to
  load or install it. So is a job its file says is disabled and that is
  not running, since a restart would start it. In a group, such jobs are
  named as skipped.

Read-only, apart from `restart`: `list` and `status` start, stop and write
nothing.

## The legend

| glyph and word | means |
|---|---|
| `● up` | running |
| `○ idle` | an on-demand job, waiting: its healthy state |
| `○ off` | switched off by its owner (it exits 0 and stays down) |
| `○ down` | loaded, not running, last exit 0 |
| `○ disabled` | its file says `"enabled": false` |
| `○ manual` | runs in the foreground; the kit never starts it |
| `✕ down` | not running after a non-zero exit (`exited 3`, `signal 9`), not loaded, or not installed |
| `✕ stray` | loaded, with no plist on disk |
| `✕ bad file` | a service file the kit cannot use; the note names the fault |

A word always sits beside the glyph. An up row never shows its last exit:
for a running job it describes a run that is over. `status NAME` has it.

## The service file

A package writes one file per service it offers, at one of two depths:

- `~/.sessionkit/<package>/services/<name>.json`: one service.
- `~/.sessionkit/<package>/services/<group>/<agent>.json`: one per agent,
  such as `phone/services/bots/<agent>.json`.

A deeper file, or one not ending `.json`, is not read. The folder sits
beside `settings/`, so no settings reader sees it.

```json
{"service": 1, "name": "talk", "label": "dev.sessionkit.voice.talk",
 "enabled": true, "install": "ears services install --only talk",
 "uninstall": "ears services uninstall --only talk",
 "description": "the live view in a browser",
 "port": 8780, "bind": "127.0.0.1"}
```

Required:

- `service`: the integer `1`. It marks the file as a service and gives its
  schema version. A JSON file in `services/` without it is not a service,
  and a footer line counts it.
- `name`: the short name every verb takes, the label after
  `dev.sessionkit.<package>.`. It must not be a group's name.
- `label` or `run`, never both. `label` is the launchd label, under
  `dev.sessionkit.<package>.` for the folder the file sits in. `run` is the
  command of a foreground service with no launchd job; the kit lists it and
  never starts it.
- `enabled`: `true` or `false`. The owner's install writes `true`, its
  uninstall `false`, and keeps the file.
- `install`: the owner's command that installs it.

Optional: `description`, `kind` (`daemon`, the default, or `on-demand`),
`port`, `protocol` (`tcp` or `udp`), `bind` (default `127.0.0.1`),
`health`, `hazard` (`["call"]`), `agent`, `uninstall`, `logs` (more log
paths), `order` (default 50; lower restarts first in a group) and `note`.
A key the kit does not know is ignored.

The full schema ships with the kit as [`service.schema.json`][schema]. A
file with a fault is listed as `✕ bad file`, naming the fault; it is never
skipped in silence. Two files with one name are both bad.

## Before every package writes its files

A `dev.sessionkit.*` job that no file claims yet is still listed, in its
package's group, from launchd alone. A footer counts such jobs, and
`status NAME` names the package whose install writes the file. As each
package ships its files, the footer goes away. Such a job counts as a call
hazard, so a restart of it during a live call needs `--force`.

## Shell completion

TAB offers the verbs, then after a service verb the names `list` shows, the
groups and `all`. It is click's own completion, so a file a package wrote a
minute ago is offered.

- zsh, macOS's default shell: add this line to `~/.zshrc`.

  ```bash
  eval "$(sessionkit completion zsh)"
  ```

- fish: add this line to `~/.config/fish/config.fish`.

  ```fish
  sessionkit completion fish | source
  ```

- bash: click needs bash 4.4 or later. macOS's own `/bin/bash` is 3.2, so
  install a newer bash first. Then add this line to `~/.bashrc`.

  ```bash
  eval "$(sessionkit completion bash)"
  ```

Each TAB starts sessionkit once. At TAB it writes nothing, and on any error
it offers nothing.

## When launchd cannot be reached

An ssh login, or a shell outside your login session, may not reach
`gui/<uid>`. launchctl then says error 125, and `list` and `restart` exit 3.
`restart` prints the one line to run from Terminal.app instead.

## What is not here yet

- `start`, `stop`, `logs`, `install`, `health`, `enable` and `disable`.
  Until then, each package's own install, uninstall and status verbs do
  that work.

[sessionkit]: sessionkit.md
[schema]: ../src/sessionkit/service.schema.json
