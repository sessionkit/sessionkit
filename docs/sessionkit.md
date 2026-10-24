# sessionkit

The kit's own command: the front door. Help first: every verb is here before
it works. Part of the [README's Components](../README.md#components).

## Verbs

- `sessionkit setup`: sets up mail on this Mac (it runs sessionmail's
  `message setup`), then writes you as the operator, the human other seats
  ask, at `~/.sessionkit/tools/settings/session.d/10-operator.json`. Then it
  writes your assistant's agent file, `~/.session/agents/claude.md`, where
  `session start` finds it (`--agent NAME` names another), asks mail setup for
  that agent's box, and ends with the one launch step:
  `To hear Delta messages, start Claude with: session start claude`. Before
  that step it asks `ears backends`, read only, and if the ears' model is
  missing it says one line naming `ears install`. It never runs `ears install`,
  and the line never changes its exit. It never
  overwrites an operator already set, or an agent file already there.
  `--dry-run` prints what it would write.
  Exit 0 all done, 1 refused or failed, 2 usage, 4 done what it could with
  mail steps left for you. See [INSTALL.md](../INSTALL.md), "Operator and
  administrators" and "Mail between agents".
- `sessionkit hello`: says hello; the stub every verb starts as.
- `sessionkit --version`: the kit's version and each family package's.

`sessionkit --help` and `sessionkit setup --help` are the full reference.
