# sessionkit

The kit's own command: the front door. Help first: every verb is here before
it works. Part of the [README's Components](../README.md#components).

## Verbs

- `sessionkit setup`: sets up mail on this Mac (it runs sessionmail's
  `message setup`), then writes you as the operator, the human other seats
  ask, at `~/.sessionkit/tools/settings/session.d/10-operator.json`. Then it
  writes your assistant's agent file, `claude.md`, in the folder
  `session start` reads agents from, the one `session path agent --config`
  names (`~/.sessionkit/tools/state/agent/config/claude.md` on a fresh Mac;
  `--agent NAME` names another). A sessiontools without that verb gets no
  agent file and no launch step: one line says so, and to run setup again
  once it has the verb. It asks mail setup for
  that agent's box and for the default seat's box, `claude`, whatever the
  agent is named. It makes that agent the one your voice wakes, with
  `ears wake add`, in one line; with no `ears` on the PATH, or when the ears
  refuse, it adds none and its line says so, and the exit does not change.
  It ends with the one launch step:
  `To hear Delta messages, start Claude with: session start`, bare when the
  agent is the default seat. With `--agent` naming another agent, or with a
  sessiontools that has no default seat, the step names the agent. Before
  that step it asks `ears backends`, read only, and if the ears' model is
  missing it says one line naming `ears install`. It never runs `ears install`,
  and the line never changes its exit. It never
  overwrites an operator already set, or an agent file already there.
  `--dry-run` prints what it would write.
  Exit 0 all done, 1 refused or failed, 2 usage, 4 done what it could with
  mail steps left for you. See [INSTALL.md](../INSTALL.md), "Operator and
  administrators" and "Mail between agents".
- `sessionkit service list|status|restart`: the kit's services, found from
  the files each package's install writes under
  `~/.sessionkit/<package>/services/`, joined with launchd. `list` shows
  every one by group; `status NAME` is the long form; `restart NAME|GROUP|all`
  runs `launchctl kickstart -k`, asks first for a group or `all`, and
  refuses during a live phone call unless `--force`. See [service][service].
- `sessionkit completion zsh|bash|fish`: prints the shell's TAB completion
  script, which completes service names. See [service][service].
- `sessionkit --version`: the kit's version and each family package's.

`sessionkit --help` and `sessionkit setup --help` are the full reference.

[service]: service.md
