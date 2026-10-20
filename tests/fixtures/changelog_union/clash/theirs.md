# Changelog

All notable changes to sessionkit are documented here. The format is
[Keep a Changelog](https://keepachangelog.com/en/1.0.0/); versions follow
[Semantic Versioning](https://semver.org/spec/v2.0.0.html). The one
version lives in `pyproject.toml`; `scripts/release.py` bumps it with
`uv version`, mirrors it into `.claude-plugin/*.json` when present, and
stamps this file.

## [Unreleased]

### Added

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

### Changed

- `make scan` finds the scanner on the PATH: with `SESSIONKIT_SCAN` unset
  it runs `release-scan` from the PATH. A `SESSIONKIT_SCAN` you set, in the
  environment or as `make scan SESSIONKIT_SCAN=...`, still wins. With
  neither, it exits 2 and its message names both lookups. Before this,
  `make scan` exited 2 whenever `SESSIONKIT_SCAN` was unset.

## [0.1.0] - 2030-10-12

### Added

- sessionkit, born 2030-10-08.
- The family in one install (SK-8): the package depends on sessionmail,
  sessiontools, sessionphone, sessionview and sessionvoice (unpinned until
  D2) and re-declares every child command (`message`, `pager`, `memory`,
  `session`, `sessionphone`, `ears`, `ears-serve`, `mouth`); the plugin
  depends on the five, and the marketplace lists them. Their sources,
  `github.com/sessionkit/<name>`, are pending D1.
