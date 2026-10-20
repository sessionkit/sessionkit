#!/usr/bin/env python3
"""Each command's page, imported from the repo that ships it; and a drift check.

    python3 scripts/command_docs.py check  [--src DIR]
    python3 scripts/command_docs.py import [--src DIR]

The commands are the kit's `[project.scripts]` in pyproject.toml. Each one's
page is `docs/<command>.md` here, so the kit's docs work offline. The source
is `<DIR>/<package>/docs/<command>.md`, in your clone of the package that
ships it. DIR is the folder that holds your clones: --src, else $SRC (as in
the README's "Install the plugins from your clones"), else this repo's parent.

`import` copies each source page here, with one comment line at its foot
naming where it came from (at the foot, so front matter and the H1 stay first). Its relative links are pointed at the package's repo on GitHub,
except a link to another command page imported here, which stays local. A command whose package has no page yet gets a short page that
says so, and is replaced on the next import once the package writes one.

`check` reads, and writes nothing. One line per command:
  same       the page here matches its source
  DRIFTED    the source changed since the import: run `import`
  missing    no page here: run `import`
  no source  the package has no docs/<command>.md yet
It exits 1 when any page is DRIFTED or missing, else 0.
"""

from __future__ import annotations

import argparse
import os
import posixpath
import re
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

#: the module a script's entry point names -> the package (repo) that ships it
PACKAGE_OF_MODULE = {
    "sessionkit": "sessionkit",
    "sessionmail": "sessionmail",
    "sessiontools": "sessiontools",
    "sessionphone": "sessionphone",
    "sessionview": "sessionview",
    "ears": "sessionvoice",
    "mouth": "sessionvoice",
    "talk": "sessionvoice",
}

#: helpers the sidebar calls; they are leaving PATH, so they get no page
NO_PAGE = {"sessionview-config", "sessionview-session", "sessionview-messages"}

FOOTER = "\n<!-- Imported from {package}'s docs/{command}.md. Edit it there, then run: python3 scripts/command_docs.py import -->\n"
STUB_MARK = "<!-- No page yet: {package} has no docs/{command}.md. -->\n"


def commands() -> dict[str, str]:
    """command -> package, for every command the kit installs that gets a page."""
    scripts = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]["scripts"]
    out = {}
    for command, target in scripts.items():
        if command in NO_PAGE:
            continue
        module = target.split(":")[0].split(".")[0]
        package = PACKAGE_OF_MODULE.get(module)
        if package is None:
            raise SystemExit(f"command_docs: {command} -> {target}: no package for module {module!r}; add it to PACKAGE_OF_MODULE")
        out[command] = package
    return out


def src_dir(arg: str | None) -> Path:
    return Path(arg or os.environ.get("SRC") or ROOT.parent).expanduser()


def page(command: str) -> Path:
    return ROOT / "docs" / f"{command}.md"


def body(text: str) -> str:
    """A page here, without the comment line import put at its foot."""
    head, sep, last = text.rstrip("\n").rpartition("\n")
    if sep and last.startswith("<!-- Imported from "):
        return head.removesuffix("\n") + "\n" if head.endswith("\n") else head + "\n"
    return text


INLINE_LINK = re.compile(r"\]\(([^)\s]+)\)")
REF_LINK = re.compile(r"^(\[[^\]]+\]:[ \t]+)(\S+)", re.MULTILINE)


def relink(text: str, package: str, here: set[str]) -> str:
    """Point the source page's relative links at its own repo on GitHub.

    A link to another command's page that is also imported here stays local,
    so it works offline; every other relative link would name a file the kit
    does not have (or a different file of the same name), so it becomes the
    package's GitHub URL for that path."""

    def target(t: str) -> str:
        if re.match(r"^[a-z][a-z0-9+.-]*:", t) or t.startswith(("#", "/")):
            return t
        path, hash_, frag = t.partition("#")
        if path in here:
            return t
        norm = posixpath.normpath(posixpath.join("docs", path))
        if norm.startswith(".."):
            return t
        return f"https://github.com/sessionkit/{package}/blob/HEAD/{norm}{hash_}{frag}"

    text = INLINE_LINK.sub(lambda m: f"]({target(m.group(1))})", text)
    return REF_LINK.sub(lambda m: m.group(1) + target(m.group(2)), text)


def imported(source: Path, package: str) -> str:
    """The body a page here should have for SOURCE: its text, relinked."""
    here = {f"{c}.md" for c, p in commands().items() if p != "sessionkit"}
    return relink(source.read_text(encoding="utf-8"), package, here)


def stub(command: str, package: str) -> str:
    return (STUB_MARK.format(package=package, command=command)
            + f"# {command}\n\nFrom [{package}](https://github.com/sessionkit/{package}).\n\n"
            + f"Not written yet: {package} has no `docs/{command}.md`. Until it does, run `{command} --help`.\n")


def do_import(src: Path) -> int:
    for command, package in commands().items():
        if package == "sessionkit":
            print(f"{command:<14} own page, not imported")
            continue
        source = src / package / "docs" / f"{command}.md"
        if source.is_file():
            page(command).write_text(imported(source, package) + FOOTER.format(package=package, command=command), encoding="utf-8")
            print(f"{command:<14} imported from {source}")
        else:
            page(command).write_text(stub(command, package), encoding="utf-8")
            print(f"{command:<14} no source at {source}: wrote a page that says so")
    return 0


def do_check(src: Path) -> int:
    bad = 0
    for command, package in commands().items():
        here = page(command)
        if package == "sessionkit":
            state = "same" if here.is_file() else "missing"
            bad += state == "missing"
            print(f"{command:<14} {state:<10} own page")
            continue
        source = src / package / "docs" / f"{command}.md"
        if not source.is_file():
            if not here.is_file():
                print(f"{command:<14} {'missing':<10} no page here: run import")
                bad += 1
                continue
            if not source.parent.is_dir():
                print(f"{command:<14} {'no clone':<10} {source.parent.parent} is not a clone here (--src DIR)")
                continue
            print(f"{command:<14} {'no source':<10} {package} has no docs/{command}.md")
            continue
        if not here.is_file() or here.read_text(encoding="utf-8").startswith("<!-- No page yet"):
            print(f"{command:<14} {'missing':<10} {package} has a page now: run import")
            bad += 1
            continue
        same = body(here.read_text(encoding="utf-8")) == imported(source, package)
        print(f"{command:<14} {'same' if same else 'DRIFTED':<10} {source}")
        bad += not same
    return 1 if bad else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("verb", choices=["check", "import"])
    parser.add_argument("--src", help="the folder that holds your clones (default $SRC, else this repo's parent)")
    args = parser.parse_args(argv)
    src = src_dir(args.src)
    return do_check(src) if args.verb == "check" else do_import(src)


if __name__ == "__main__":
    sys.exit(main())
