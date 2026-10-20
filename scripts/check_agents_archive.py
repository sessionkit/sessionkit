#!/usr/bin/env python3
"""Check that a repo's AGENTS.md ships in its release archive and stands alone.

    python3 scripts/check_agents_archive.py [REPO] [--ref REF] [--host NAME]... [--strict]

REPO is a git checkout (default: the current directory); REF defaults to
HEAD. The check reads `git archive REF`, which is what a release ships, so
export-ignored paths are already gone. It never writes to REPO.

It fails (exit 1) when:
- AGENTS.md is not in the archive: missing from the tree, or export-ignored;
- a relative Markdown link in AGENTS.md names a path the archive lacks;
- a backticked repo path in AGENTS.md (one with a `/` or a file suffix)
  names a path the archive lacks.

It also lists lines that look fleet-only: a task id (`ABC-123`), or a host
name the caller gives. The check ships no host names of its own: pass each
one with --host NAME (repeatable), or as a space- or comma-separated list in
$AGENTS_CHECK_HOSTS; both are used. A pattern cannot tell a task id from
`UTF-8`, so these lines are listed for a person to read, and fail only under
--strict.

Exit 0 pass, 1 rule broken, 2 usage or not a git checkout. The rule is in
the family's conventions, a maintainers' note that a checkout keeps in docs/
and the release archive leaves out.
"""

from __future__ import annotations

import argparse
import io
import os
import posixpath
import re
import subprocess
import sys
import tarfile
from urllib.parse import unquote

AGENTS = "AGENTS.md"

FENCE = re.compile(r"^\s*(```|~~~)")
INLINE_LINK = re.compile(r"\]\(\s*<?([^)\s>]+)>?(?:\s+\"[^\"]*\")?\s*\)")
REF_LINK = re.compile(r"^\s*\[[^\]]+\]:\s*<?(\S+?)>?(?:\s+\"[^\"]*\")?\s*$")
CODE_SPAN = re.compile(r"`([^`\n]+)`")
SUFFIX = re.compile(
    r"\.(md|py|toml|json|jsonl|sh|txt|ya?ml|cfg|ini|lock|js|ts|html|css)$"
)
SCHEME = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*:")
HOSTS_ENV = "AGENTS_CHECK_HOSTS"
TASK_ID = re.compile(r"\b[A-Z][A-Z0-9]*-[0-9]+\b")


def archive_listing(repo: str, ref: str) -> tuple[set[str], str | None]:
    """Every path in `git archive REF`, and AGENTS.md's text if it ships."""
    out = subprocess.run(
        ["git", "-C", repo, "archive", "--format=tar", ref],
        capture_output=True,
        check=False,
    )
    if out.returncode != 0:
        raise RuntimeError(
            out.stderr.decode(errors="replace").strip() or "git archive failed"
        )
    paths: set[str] = set()
    agents = None
    with tarfile.open(fileobj=io.BytesIO(out.stdout)) as tar:
        for member in tar.getmembers():
            name = member.name.rstrip("/")
            paths.add(name)
            if name == AGENTS and member.isfile():
                agents = (
                    tar.extractfile(member).read().decode("utf-8", errors="replace")
                )
    return paths, agents


def in_tree(repo: str, ref: str) -> bool:
    out = subprocess.run(
        ["git", "-C", repo, "cat-file", "-e", f"{ref}:{AGENTS}"],
        capture_output=True,
        check=False,
    )
    return out.returncode == 0


def exists(path: str, paths: set[str]) -> bool:
    """A file or a directory in the archive. Directories may be implicit."""
    path = path.rstrip("/")
    if path in ("", "."):
        return True
    prefix = path + "/"
    return path in paths or any(p.startswith(prefix) for p in paths)


def link_target(raw: str) -> str | None:
    """The archive path a link names, or None for a URL or an anchor."""
    if raw.startswith("#") or SCHEME.match(raw):
        return None
    return unquote(raw.split("#", 1)[0].split("?", 1)[0])


def code_path(span: str) -> str | None:
    """A backticked span that reads as a repo path, or None."""
    span = span.strip()
    if not span or any(c in span for c in " <>*{}$|=\\"):
        return None
    if span.startswith(("-", "@")) or SCHEME.match(span):
        return None
    if "/" in span or SUFFIX.search(span):
        return span
    return None


def resolve(path: str) -> str | None:
    """A relative path, normalised against the archive root; None if it leaves it."""
    if path.startswith(("/", "~")):
        return None
    norm = posixpath.normpath(path)
    if norm == ".." or norm.startswith("../"):
        return None
    return norm


def host_pattern(hosts: list[str]) -> re.Pattern[str] | None:
    """One word-bounded pattern for the caller's host names; None for none."""
    names = sorted({h for h in hosts if h}, key=len, reverse=True)
    if not names:
        return None
    return re.compile(r"(?<![\w-])(" + "|".join(map(re.escape, names)) + r")(?![\w-])")


def check(
    text: str, paths: set[str], hosts: list[str] | None = None
) -> tuple[list[str], list[str]]:
    """(dead references, fleet-looking lines), each as `line N: ...`."""
    host = host_pattern(hosts or [])
    basenames = {posixpath.basename(p) for p in paths}
    dead: list[str] = []
    fleet: list[str] = []
    fenced = False
    for n, line in enumerate(text.splitlines(), 1):
        if FENCE.match(line):
            fenced = not fenced
        if TASK_ID.search(line) or (host and host.search(line)):
            fleet.append(f"line {n}: {line.strip()}")
        if fenced or FENCE.match(line):
            continue
        targets = [m.group(1) for m in INLINE_LINK.finditer(line)]
        ref = REF_LINK.match(line)
        if ref:
            targets.append(ref.group(1))
        for raw in targets:
            target = link_target(raw)
            if target is None:
                continue
            norm = resolve(target)
            if norm is None:
                dead.append(f"line {n}: link {raw} points outside the archive")
            elif not exists(norm, paths):
                dead.append(f"line {n}: link {raw} is not in the archive")
        prose = INLINE_LINK.sub("", line)
        for span in CODE_SPAN.findall(prose):
            path = code_path(span)
            if path is None:
                continue
            norm = resolve(path)
            if norm is None:
                continue  # a home or absolute path: not a repo path
            # A bare file name ("cli.py") may live anywhere in the tree.
            if exists(norm, paths) or ("/" not in norm and norm in basenames):
                continue
            dead.append(f"line {n}: path `{span}` is not in the archive")
    return dead, fleet


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="AGENTS.md ships in the release archive and stands alone."
    )
    parser.add_argument(
        "repo", nargs="?", default=".", help="a git checkout (default: .)"
    )
    parser.add_argument(
        "--ref", default="HEAD", help="the commit to archive (default: HEAD)"
    )
    parser.add_argument(
        "--host",
        action="append",
        default=[],
        metavar="NAME",
        help=f"a host name to list as fleet-only (repeatable; also ${HOSTS_ENV})",
    )
    parser.add_argument(
        "--strict", action="store_true", help="fail on fleet-looking lines too"
    )
    args = parser.parse_args(argv)
    hosts = args.host + re.split(r"[\s,]+", os.environ.get(HOSTS_ENV, "").strip())

    try:
        paths, text = archive_listing(args.repo, args.ref)
    except (RuntimeError, OSError, tarfile.TarError) as exc:
        print(f"check_agents_archive: {args.repo}: {exc}", file=sys.stderr)
        return 2

    if text is None:
        if in_tree(args.repo, args.ref):
            print(
                f"FAIL {AGENTS} is in the tree but not in the archive: export-ignored"
            )
        else:
            print(f"FAIL no {AGENTS} at {args.ref}")
        return 1

    dead, fleet = check(text, paths, hosts)
    for item in dead:
        print(f"FAIL {item}")
    for item in fleet:
        print(f"{'FAIL' if args.strict else 'LOOK'} fleet? {item}")
    failed = bool(dead) or (args.strict and bool(fleet))
    print(
        f"{'FAIL' if failed else 'ok'}: {AGENTS} ships; "
        f"{len(dead)} dead reference(s), {len(fleet)} fleet-looking line(s)"
    )
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
