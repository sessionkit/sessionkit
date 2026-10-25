# sessionkit - Makefile. `make` lists the targets; each line with ## is one.

.DEFAULT_GOAL := help
SHELL := /usr/bin/env bash
BUMP ?= patch
# every tracked *.sh, and every tracked file whose FIRST line is a sh/bash shebang
SHELLSCRIPTS := $(shell { git ls-files -z | xargs -0 awk 'FNR==1 && /^\#!\/(usr\/bin\/env )?(ba)?sh/ {print FILENAME}'; git ls-files '*.sh'; } | sort -u)
.PHONY: help install test lint format check build release push publish docs-check docs-import

help:  ## this list
	@grep -hE '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-10s %s\n", $$1, $$2}'

install:  ## put sessionkit on the PATH, editable (uv tool install -e .)
	@uv tool install -e .

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
publish: build  ## upload THIS version's wheel + sdist to PyPI; token via $$PYPI_TOKEN_PASS_PATH (pass) or $$UV_PUBLISH_TOKEN, never on a command line
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
