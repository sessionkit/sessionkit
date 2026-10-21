# AGENTS.md

Instructions for a coding agent working on this repo. Humans start at
[README.md](README.md).

## What this repo is

Session Kit is the meta package of the session family. It installs the five
family packages as one, and ships a small `sessionkit` command of its own.

- `pyproject.toml` lists the five as dependencies, floored at 0.2.0
  (sessionmail, sessionphone and sessionvoice at 0.2.1).
- `[project.scripts]` re-declares every child command, because `uv tool
  install` links only the commands of the package it is asked for.
- The package is also a Claude Code plugin: `.claude-plugin/` holds its
  manifests, `skills/sessionkit/` its skill.
- The CLI is `src/sessionkit/cli.py`. The tests are in `tests/`.

## Read the docs before building

Read the doc for what you are changing before you build it:

- [README.md](README.md): what the kit is, and how it installs.
- [INSTALL.md](INSTALL.md): the manual install, step by step.
- [docs/troubleshooting.md](docs/troubleshooting.md): one line per symptom,
  with a check to paste.
- [CHANGELOG.md](CHANGELOG.md): what changed in each release.

A git checkout of this repo also keeps the maintainers' notes in `docs/`:
the family's conventions, the checklist run before a release, and how
versions are numbered. The release archive leaves them out. If your copy has
them, read the one for what you are changing before you build it.

## Build and test

`make` lists the targets. You need uv.

```bash
make install   # uv tool install -e .
make test      # uv run pytest -q
make lint      # ruff check, then shellcheck on every tracked shell script
make format    # ruff format
make check     # lint, then test: run it before every commit
make build     # wheel and sdist into dist/
make scan      # the leak scan; SESSIONKIT_SCAN, else release-scan on the PATH
```

`make release`, `make push` and `make publish` are for the owner. Do not
run them.

## Rules for this repo

- **Re-declared commands follow the children.** When a family package adds,
  renames or drops a command, update `[project.scripts]` and
  `CHILD_SCRIPTS` in `tests/test_family.py` together.
- **The dependency list is ruled.** The five family packages, their floors
  and their extras are written down once, in `tests/_ruled_deps.py`, and
  `tests/test_dependency_gate.py` fails when pyproject.toml, the built wheel
  or uv.lock drift from it. Change the ruled list there first, then
  pyproject.toml, then re-lock.
- **Versions are read, never written down.** `sessionkit --version` reads
  installed metadata. Do not put a version string in the source.
- **One version, in `pyproject.toml`.** `make release` mirrors it into the
  plugin manifests and stamps the CHANGELOG. Add your change under
  `## [Unreleased]` in [CHANGELOG.md](CHANGELOG.md).
- **Never rewrite or delete a CHANGELOG bullet that has landed on master;
  add a new one.** `CHANGELOG.md` merges with `merge=union`, which keeps
  both versions of an edited bullet silently instead of conflicting.
  `tests/test_changelog_union.py` catches only some of that damage.
- **A scrub of a landed CHANGELOG bullet merges alone.** Merge it while no
  other open branch touches `CHANGELOG.md`, or re-run `make scan` on the
  merged tree after the merge. Under union, a bullet added next to it on
  another branch can bring the scrubbed word back with no conflict.
- **The tests pin the docs.** `tests/test_readme.py` checks README.md,
  INSTALL.md and docs/troubleshooting.md. Run `make test` after editing
  them.
- **No secrets in the tree.** The scanner and its word list are private and
  never live here. `make scan` checks HEAD's tree, so commit before you
  scan.
- **A token never goes on a command line.** `make publish` takes it from the
  environment.
- **No tracked symlink points outside the repo.**
- **Docs stay flat:** one topic to a file in `docs/`, linked with
  Markdown links, never wiki links.
