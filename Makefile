# sessionkit - Makefile. `make` lists the targets; each line with ## is one.

.DEFAULT_GOAL := help
SHELL := /usr/bin/env bash
BUMP ?= patch
# every tracked *.sh, and every tracked file whose FIRST line is a sh/bash shebang
SHELLSCRIPTS := $(shell { git ls-files -z | xargs -0 awk 'FNR==1 && /^\#!\/(usr\/bin\/env )?(ba)?sh/ {print FILENAME}'; git ls-files '*.sh'; } | sort -u)
.PHONY: help install test lint format check build pypi-dist release push publish docs-check docs-import

help:  ## this list
	@grep -hE '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-12s %s\n", $$1, $$2}'

install:  ## put sessionkit on the PATH, editable (uv tool install -e .)
	@uv tool install -e .

# The whole kit from your clones, by scripts/install_dev.py (its docstring says
# why each uv flag is there). SRC is the folder of your clones (default: this
# repo's parent), PYTHON the tool env's Python (default: KIT_PYTHON in
# install.sh), DRY_RUN=1 prints the uv command and changes nothing. The
# target's name is written on its own line below and nowhere else, so a rename
# is one line; that is why it is not listed in .PHONY.
install-dev:  ## the whole kit from your clones: this one and four editable, sessionview built (SRC= PYTHON= DRY_RUN=1)
	@python3 scripts/install_dev.py $(if $(SRC),--src "$(SRC)") $(if $(PYTHON),--python "$(PYTHON)") $(if $(DRY_RUN),--dry-run)

test:  ## the pytest suite
	@uv run pytest -q

lint:  ## ruff check; shellcheck on every tracked shell script (see SHELLSCRIPTS)
	@uv run ruff check .
	@if [ -n "$(SHELLSCRIPTS)" ]; then command -v shellcheck >/dev/null || { echo "shellcheck not installed (brew install shellcheck)"; exit 1; }; shellcheck $(SHELLSCRIPTS) && echo "shellcheck: $(words $(SHELLSCRIPTS)) scripts clean"; else echo "shellcheck: no shell scripts"; fi

format:  ## ruff format
	@uv run ruff format .

check: lint test  ## lint, then test
docs-check:  ## each command's docs/<command>.md against the repo that ships it (SRC=folder of your clones); exit 1 on drift
	@python3 scripts/command_docs.py check $(if $(SRC),--src $(SRC))
docs-import:  ## copy each command's page in from the repo that ships it (SRC=folder of your clones)
	@python3 scripts/command_docs.py import $(if $(SRC),--src $(SRC))

build:  ## wheel + sdist into dist/
	@uv build

# PyPI shows README.md, where the repo's RELATIVE links 404. pypi-dist
# builds from the release TAG, never the checkout: `git archive` into a scratch
# stage, pin the stage's README links to the tag (scripts/pypi_readme.py),
# `uv build` there into dist/, then check BOTH the wheel and the sdist for any
# relative link left. The links point at the PUBLIC repo's tag, and the dists are
# built from the LOCAL one, so the two must be the SAME COMMIT: it refuses unless
# `pypi_readme.py tag-check` finds the tag on PUBLIC_REMOTE at the commit the
# local tag names (a missing public tag, or a moved or stale local one, refuses).
# Both variables are overridable (`make pypi-dist PUBLIC_REMOTE=...`), so the
# other family repos can point PYPI_README at this one copy.
PUBLIC_REMOTE ?= https://github.com/sessionkit/sessionkit.git
PYPI_README ?= python3 scripts/pypi_readme.py
pypi-dist:  ## wheel + sdist from tag v<version>, README links pinned to it; the tag must be the same commit on PUBLIC_REMOTE
	@set -euo pipefail; v="v$$(uv version --short)"; \
	$(PYPI_README) tag-check --tag "$$v" --remote "$(PUBLIC_REMOTE)"; \
	stage="$$(mktemp -d)"; trap 'rm -rf "$${stage:?}"' EXIT; \
	git archive "$$v" | tar -x -C "$$stage"; \
	$(PYPI_README) rewrite --repo sessionkit/sessionkit --ref "$$v" --root "$$stage" "$$stage/README.md"; \
	(cd "$$stage" && uv build --out-dir "$(CURDIR)/dist"); \
	dist="dist/$$(echo 'sessionkit' | tr '-' '_')-$${v#v}"; \
	$(PYPI_README) check "$$dist"-*.whl "$$dist".tar.gz

# release.py is stdlib-only, so python3 runs it: a plain `uv run` would re-lock
# the project before the script starts.
release:  ## bump (BUMP=patch|minor|major) or set (VERSION=X.Y.Z), then mirror, changelog, commit, tag
	@python3 scripts/release.py $(or $(VERSION),$(BUMP))

push:  ## push the branch and the tags to origin (release never pushes; this is the line it printed)
	@git push origin HEAD && git push origin --tags

# THE TOKEN NEVER TOUCHES A COMMAND LINE. argv is readable by every process
# on the machine (`ps`); a child's environment only by its own user. So the
# token reaches uv as UV_PUBLISH_TOKEN in uv's environment, from one
# `pass show` (one touch), and what `ps` shows is `uv publish dist/...`.
# The process list must never show the token. PYPI_TOKEN_PASS_PATH names
# the pass entry, e.g.
# personal/services/pypi.org/api_tokens/x1; set it in your shell profile.
publish: pypi-dist  ## upload THIS version's wheel + sdist to PyPI; token via $$PYPI_TOKEN_PASS_PATH (pass) or $$UV_PUBLISH_TOKEN, never on a command line
	@dist="dist/$$(echo 'sessionkit' | tr '-' '_')-$$(uv version --short)"; \
	if [ -n "$$UV_PUBLISH_TOKEN" ]; then uv publish "$$dist"*; \
	elif [ -n "$$PYPI_TOKEN_PASS_PATH" ]; then UV_PUBLISH_TOKEN="$$(pass show "$$PYPI_TOKEN_PASS_PATH" | head -n1)" uv publish "$$dist"*; \
	else echo "publish: set PYPI_TOKEN_PASS_PATH to the pass entry holding your PyPI token (or UV_PUBLISH_TOKEN); the token is never put on a command line" >&2; exit 1; fi

# The pre-publish scrub check. The scanner and its word list are PRIVATE and never
# live in this repo: SESSIONKIT_SCAN names the release-scan tool (it finds its list,
# or takes SESSIONKIT_SCRUB_RULES). Unset, it falls back to release-scan on the PATH;
# a SESSIONKIT_SCAN you set (environment or `make scan SESSIONKIT_SCAN=...`) wins.
# Exits non-zero on any P0 term in HEAD's tree; exits 2 when neither finds the tool.
SESSIONKIT_SCAN ?= $(shell command -v release-scan 2>/dev/null)
.PHONY: scan scrub
scan:  ## scrub check: HEAD's tree against the private word list; fails on any P0 term
	@[ -n "$(SESSIONKIT_SCAN)" ] || { echo "scan: no release-scan tool: SESSIONKIT_SCAN is unset and release-scan is not on the PATH; set SESSIONKIT_SCAN to the tool, or put release-scan on the PATH" >&2; exit 2; }
	@"$(SESSIONKIT_SCAN)" --here --fail-on P0

scrub: scan  ## the same check, by its other name

# The strict plugin check runs on what ships, not on this checkout. The shipped
# tree is `git archive HEAD`, and .gitattributes leaves files out of it: the root
# CLAUDE.md is one, and the validator flags it, so `claude plugin validate .
# --strict` fails here on a file no user receives. This extracts HEAD's archive
# to a temp dir, validates that, and exits with claude's status. Like `make
# scan`, it reads HEAD, so commit first. The temp dir is removed on every exit.
.PHONY: validate
validate:  ## claude plugin validate --strict on what ships: HEAD's git archive, in a temp dir
	@command -v claude >/dev/null || { echo "validate: claude is not on the PATH; install Claude Code to run claude plugin validate" >&2; exit 2; }
	@set -o pipefail; \
	tmp="$${TMPDIR:-/tmp}"; dir="$$(mktemp -d "$${tmp%/}/sessionkit-validate.XXXXXX")" || { echo "validate: could not make a temp dir" >&2; exit 2; }; \
	trap 'rm -rf "$$dir"' EXIT; trap 'exit 130' INT; trap 'exit 143' TERM; \
	git archive HEAD | tar -x -C "$$dir" || { echo "validate: could not extract git archive HEAD" >&2; exit 2; }; \
	echo "validate: HEAD's git archive, in $$dir"; \
	claude plugin validate "$$dir" --strict
