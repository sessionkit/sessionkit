#!/usr/bin/env python3
"""pypi_readme: the PyPI page gets absolute links; the repo keeps relative ones.

  pypi_readme.py rewrite --repo OWNER/NAME --ref TAG --root DIR FILE
      Rewrite FILE in place (a STAGED copy, never the checkout): every relative
      link becomes an absolute GitHub URL pinned to TAG. Files -> blob/TAG/,
      directories -> tree/TAG/, images -> raw.githubusercontent.com/.../TAG/.
      Anchors (#x), absolute URLs and mailto: are left alone (PyPI renders
      in-page anchors), and so is anything in fenced code or a code span.
      A target missing from DIR, or one that climbs out of it, is an error:
      exit 1, and FILE is not written.
  pypi_readme.py check DIST...
      Read the long description out of each wheel (METADATA) and sdist
      (PKG-INFO); exit 1 if any link in it is still relative.
  pypi_readme.py tag-check --tag TAG --remote REMOTE
      Exit 0 only when TAG names the SAME COMMIT here (the cwd repo) and on
      REMOTE, the public repo the pinned links point at. The local side is
      `git rev-parse TAG^{commit}`; the public side is one `git ls-remote`,
      peeled: an annotated tag's `^{}` line, else a lightweight tag's own
      line. A tag missing on either side, a mismatch (both shas named) or an
      unreachable REMOTE is exit 1, one line on stderr.

Stdlib only, run by python3 (as scripts/release.py is). `make pypi-dist` runs
all three verbs: tag-check first, so a moved or stale local tag never builds.
"""

from __future__ import annotations

import argparse
import os
import posixpath
import re
import subprocess
import sys
import tarfile
import zipfile
from email.parser import Parser
from urllib.parse import unquote

FENCE = re.compile(r"^\s{0,3}(`{3,}|~{3,})")
CODE = re.compile(r"(`+)(?:(?!\1).)+?\1")
# [text](target "title") and ![alt](target): the title may be "", '' or ().
INLINE = re.compile(
    r"(!?)(\[(?:[^\[\]]|\[[^\]]*\])*\])"
    r"\(\s*(<[^>]*>|[^)\s]+)(\s+(?:\"[^\"]*\"|'[^']*'|\([^)]*\)))?\s*\)"
)
# [label]: target, but not a footnote ([^1]: text), whose text is no link.
REFDEF = re.compile(r"^(\s{0,3}\[(?!\^)[^\]]+\]:\s*)(<[^>]*>|\S+)(.*)$")
HTML = re.compile(r"""(\b(?:href|src)\s*=\s*)(["'])(.*?)\2""", re.IGNORECASE)
ABS = re.compile(r"^([a-zA-Z][a-zA-Z0-9+.-]*:|//|#)")
IMAGE_EXT = (".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp")


def spans(line):
    """Code-span ranges in a line, so links inside them are left alone."""
    return [m.span() for m in CODE.finditer(line)]


def outside(pos, sp):
    return all(not (a <= pos < b) for a, b in sp)


def bracket(raw, new):
    """Keep <angle brackets> round a target that had them."""
    return f"<{new}>" if raw.startswith("<") and raw.endswith(">") else new


def walk(text, fn):
    """Apply fn(kind, target) -> new target to every link outside code."""
    out, fence = [], None
    for line in text.splitlines(keepends=True):
        f = FENCE.match(line)
        if fence is None and f:
            fence = f.group(1)
            out.append(line)
            continue
        if fence is not None:
            # A fence closes on the same character, at least as long.
            if f and f.group(1)[0] == fence[0] and len(f.group(1)) >= len(fence):
                fence = None
            out.append(line)
            continue
        out.append(links(line, fn))
    return "".join(out)


def links(line, fn):
    """One line outside a fence: its reference definition, or its inline and
    HTML links, each passed through fn unless it sits in a code span."""
    m = REFDEF.match(line)
    if m and outside(0, spans(line)):
        raw = m.group(2)
        new = bracket(raw, fn("refdef", raw.strip("<>")))
        return m.group(1) + new + m.group(3) + line[m.end():]

    sp = spans(line)

    def inl(m, sp):
        if not outside(m.start(), sp):
            return m.group(0)
        raw = m.group(3)
        new = bracket(raw, fn("image" if m.group(1) else "link", raw.strip("<>")))
        # A link's text may hold an image, [![alt](logo.png)](url): the outer
        # match swallows it, so walk the text too.
        label = m.group(2)[1:-1]
        lsp = spans(label)
        label = INLINE.sub(lambda n: inl(n, lsp), label)
        return f"{m.group(1)}[{label}]({new}{m.group(4) or ''})"

    line = INLINE.sub(lambda m: inl(m, sp), line)
    sp = spans(line)  # the inline pass moved things along: measure again

    def html(m):
        if not outside(m.start(), sp):
            return m.group(0)
        kind = "image" if m.group(1).lower().startswith("src") else "link"
        return m.group(1) + m.group(2) + fn(kind, m.group(3)) + m.group(2)

    return HTML.sub(html, line)


def exists_exact(root, rel):
    """Whether rel is in root, spelled as git and GitHub spell it. A macOS disk
    ignores case, so os.path.exists would pass install.md for INSTALL.md, and
    the link would 404 on GitHub."""
    path = root
    for part in rel.split("/"):
        if part in ("", "."):
            continue
        try:
            if part not in os.listdir(path):
                return False
        except OSError:
            return False
        path = os.path.join(path, part)
    return os.path.exists(path)


def within(path, root):
    return path == root or path.startswith(root.rstrip(os.sep) + os.sep)


def rewrite(a):
    root = os.path.realpath(a.root)
    real = os.path.realpath(a.file)
    if not within(real, root):
        print(f"pypi_readme: {a.file} is not inside --root {a.root}", file=sys.stderr)
        return 1
    base = posixpath.dirname(os.path.relpath(real, root).replace(os.sep, "/"))
    errors, changed = [], []

    def fn(kind, t):
        if ABS.match(t):
            return t
        path, _, frag = t.partition("#")
        path, _, query = path.partition("?")
        # A leading / is repo-root relative, as GitHub renders it. The URL
        # keeps the link's own spelling (%20 and all); the file is looked up
        # by the decoded path.
        start = "" if path.startswith("/") else base
        url_rel = posixpath.normpath(posixpath.join(start, path.lstrip("/") or "."))
        rel = posixpath.normpath(posixpath.join(start, unquote(path).lstrip("/") or "."))
        if any(r == ".." or r.startswith(("../", "/")) for r in (rel, url_rel)):
            errors.append(f"climbs out of the repo: {t}")
            return t
        full = os.path.join(root, rel)
        if not within(os.path.realpath(full), root):
            errors.append(f"climbs out of the repo (symlink): {t}")
            return t
        if not exists_exact(root, rel):
            errors.append(f"not in the release tree: {t}")
            return t
        url_rel = "" if url_rel == "." else url_rel
        if kind == "image" or (kind == "refdef" and rel.lower().endswith(IMAGE_EXT)):
            url = f"https://raw.githubusercontent.com/{a.repo}/{a.ref}/{url_rel}"
        else:
            how = "tree" if os.path.isdir(full) else "blob"
            url = f"https://github.com/{a.repo}/{how}/{a.ref}/{url_rel}"
        new = url.rstrip("/") + (f"?{query}" if query else "") + (f"#{frag}" if frag else "")
        changed.append(t)
        return new

    with open(a.file, encoding="utf-8", newline="") as fh:
        text = fh.read()
    new = walk(text, fn)
    if errors:
        for e in errors:
            print(f"pypi_readme: {a.file}: {e}", file=sys.stderr)
        print(f"pypi_readme: {a.file}: refused, {len(errors)} bad link(s); nothing written",
              file=sys.stderr)
        return 1
    with open(a.file, "w", encoding="utf-8", newline="") as fh:
        fh.write(new)
    print(f"pypi_readme: {a.file}: {len(changed)} link(s) rewritten, pinned to {a.ref}")
    return 0


def description(dist):
    """The long description in a wheel's METADATA or an sdist's PKG-INFO."""
    if dist.endswith(".whl"):
        with zipfile.ZipFile(dist) as z:
            names = [n for n in z.namelist()
                     if n.count("/") == 1 and n.endswith(".dist-info/METADATA")]
            if not names:
                raise ValueError("no *.dist-info/METADATA in the wheel")
            raw = z.read(names[0]).decode("utf-8")
    else:
        with tarfile.open(dist) as t:
            members = [m for m in t.getmembers()
                       if m.name.count("/") == 1 and m.name.endswith("/PKG-INFO")]
            if not members:
                raise ValueError("no <name>-<version>/PKG-INFO in the sdist")
            raw = t.extractfile(members[0]).read().decode("utf-8")
    msg = Parser().parsestr(raw)
    return msg.get_payload() or msg.get("Description", "")


def relative_links(text):
    """Every link outside code that is still relative."""
    found = []

    def note(kind, t):
        if not ABS.match(t):
            found.append(t)
        return t

    walk(text, note)
    return found


def check(a):
    bad = 0
    for d in a.dist:
        name = os.path.basename(d)
        try:
            text = description(d)
        except (OSError, ValueError, KeyError, zipfile.BadZipFile, tarfile.TarError) as e:
            print(f"pypi_readme check: {name}: cannot read the description: {e}", file=sys.stderr)
            bad += 1
            continue
        found = relative_links(text)
        print(f"pypi_readme check: {name}: {len(found)} relative link(s)"
              + (f": {found[:5]}" if found else ""))
        bad += bool(found)
    return 1 if bad else 0


def git(*args):
    """Run git with an argv list, never a shell."""
    return subprocess.run(["git", *args], capture_output=True, text=True, check=False)


def public_commit(listing, tag):
    """The commit the public tag points at, from `git ls-remote` output: the
    peeled `^{}` line of an annotated tag, else a lightweight tag's own line."""
    plain = peeled = None
    for line in listing.splitlines():
        sha, _, ref = line.partition("\t")
        if ref == f"refs/tags/{tag}^{{}}":
            peeled = sha
        elif ref == f"refs/tags/{tag}":
            plain = sha
    return peeled or plain


def tag_check(a):
    tag, remote = a.tag, a.remote
    try:
        local = git("rev-parse", "--verify", "--quiet", f"refs/tags/{tag}^{{commit}}")
        public = git("ls-remote", remote, f"refs/tags/{tag}", f"refs/tags/{tag}^{{}}")
    except OSError as e:
        print(f"pypi_readme tag-check: cannot run git: {e}", file=sys.stderr)
        return 1
    if local.returncode != 0 or not local.stdout.strip():
        print(f"pypi_readme tag-check: tag {tag} is not in this repo; tag the release first",
              file=sys.stderr)
        return 1
    here = local.stdout.strip()
    if public.returncode != 0:
        why = " ".join(public.stderr.split()) or f"git ls-remote exit {public.returncode}"
        print(f"pypi_readme tag-check: cannot read {tag} from {remote}: {why}", file=sys.stderr)
        return 1
    there = public_commit(public.stdout, tag)
    if there is None:
        print(f"pypi_readme tag-check: tag {tag} is not on {remote}; "
              "push the tag to the public repo first", file=sys.stderr)
        return 1
    if here != there:
        print(f"pypi_readme tag-check: tag {tag} differs: local {here}, public {there} "
              f"on {remote}; the local tag must be the commit the public repo tagged",
              file=sys.stderr)
        return 1
    print(f"pypi_readme tag-check: {tag} is {here} here and on {remote}")
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(prog="pypi_readme.py", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    s = p.add_subparsers(dest="verb", required=True)
    r = s.add_parser("rewrite", help="pin a staged README's relative links to a tag")
    r.add_argument("--repo", required=True, help="OWNER/NAME on GitHub")
    r.add_argument("--ref", required=True, help="the release tag, e.g. v0.3.4")
    r.add_argument("--root", required=True, help="the staged tree the links resolve in")
    r.add_argument("file")
    c = s.add_parser("check", help="exit 1 if a dist's description has a relative link")
    c.add_argument("dist", nargs="+")
    t = s.add_parser("tag-check", help="exit 1 unless TAG is the same commit here and on REMOTE")
    t.add_argument("--tag", required=True, help="the release tag, e.g. v0.3.4")
    t.add_argument("--remote", required=True, help="the public repo (URL or path) the links point at")
    a = p.parse_args(argv)
    return {"rewrite": rewrite, "check": check, "tag-check": tag_check}[a.verb](a)


if __name__ == "__main__":
    sys.exit(main())
