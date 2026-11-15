"""Every fenced shell block in the docs pastes into a Mac's zsh as written.

In zsh, the Mac's own shell, `interactivecomments` is off at the prompt, so a
pasted `#` is a WORD, not a comment:

- `session list   # your sessions` runs `session list '#' your sessions`;
- an apostrophe in a comment (`# one session's window`) opens a quote that
  eats the lines pasted after it;
- `(in ...)` in a comment is a glob, and zsh stops on it.

So a command's explanation goes in the prose, never after the command. A `#`
line belongs only in a block the reader saves and runs as a script: one that
starts with a `#!` line. And every quote a block opens, it closes.

A value the reader types is an UPPERCASE word (`message send TO`), the word the
command's own help uses, never a `<word>`. Unquoted, `<box>` is a redirection
in zsh and in bash: the paste stops with "no such file or directory: box", or
a parse error, and the line does not run.

An optional part is never shown in `[...]` in a shell block either. Unquoted,
`message list [BOX]` is a glob, and zsh stops a glob that matches nothing:
"no matches found: [BOX]", and the line does not run. Quote the word, write it
UPPERCASE with no brackets, or put a usage synopsis in the prose or a `text`
block. zsh reads `[`, `[[ ... ]]`, `$a[1]` and an assignment's value as
written, so the guard lets those through.

The guard reads each block as zsh does at the prompt, with no comments. It
covers every Markdown file in the repo (git's list when there is one, else a
walk of the tree, as in a release archive), except CHANGELOG.md, whose landed
bullets are never rewritten, and the test fixtures.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent

SHELL_FENCES = {"bash", "sh", "shell", "zsh", "console"}
SKIPPED = {"CHANGELOG.md"}
SKIPPED_DIRS = {
    ".git",
    ".venv",
    "node_modules",
    "dist",
    "build",
    ".pytest_cache",
    ".ruff_cache",
}
FIXTURES = Path("tests") / "fixtures"

FENCE = re.compile(r"^(?P<indent> *)(?P<tick>`{3,}|~{3,})\s*(?P<info>[^\s`]*)")
# A `<word>` placeholder: `<` then a letter, up to a `>` with no space before
# it. Not `<<`, `<(`, `<&`, and not `<in >out`, two real redirections.
PLACEHOLDER = re.compile(r"<[A-Za-z][^<>]*(?<!\s)>")
# `<<WORD`, `<<-WORD`, `<<'WORD'`, `<<"WORD"`; not `<<<`, a here-string.
HEREDOC = re.compile(
    r"(?<!<)<<(?!<)(?P<dash>-?)\s*(?P<q>['\"]?)(?P<word>[A-Za-z_][A-Za-z0-9_]*)(?P=q)"
)
# A parameter name, as `$NAME` reads it; one `[...]` after it is a subscript.
NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
# `NAME=`, `NAME[sub]=`, `NAME+=`: an assignment, whose value zsh does not glob.
ASSIGNMENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*(\[[^\]]*\])?\+?=")
# Words that leave the next word in command position.
LEADS = {"if", "then", "else", "elif", "while", "until", "do", "!", "time", "{", "}"}
# Commands whose `NAME=value` arguments are assignments too.
DECLARES = {"export", "local", "typeset", "declare", "readonly", "integer", "float"}


@dataclass(frozen=True)
class Block:
    path: str
    line: int  # 1-based line of the block's first content line
    info: str
    lines: tuple[str, ...]


def _doc_files() -> list[str]:
    try:
        out = subprocess.run(
            ["git", "-C", str(ROOT), "ls-files", "-z", "--", "*.md"],
            capture_output=True,
            check=True,
        ).stdout.decode()
        names = [n for n in out.split("\0") if n]
    except (OSError, subprocess.CalledProcessError):
        names = []
    if not names:
        names = [
            str(p.relative_to(ROOT))
            for p in ROOT.rglob("*.md")
            if not SKIPPED_DIRS.intersection(p.relative_to(ROOT).parts)
        ]
    return sorted(
        n
        for n in names
        if Path(n).name not in SKIPPED
        and FIXTURES not in Path(n).parents
        and (ROOT / n).is_file()
    )


def shell_blocks(text: str, path: str = "<text>") -> list[Block]:
    """Each fenced block whose info string names a shell, de-indented."""
    lines = text.split("\n")
    blocks: list[Block] = []
    i = 0
    while i < len(lines):
        m = FENCE.match(lines[i])
        if not m:
            i += 1
            continue
        indent, tick, info = len(m["indent"]), m["tick"], m["info"].lower()
        j = i + 1
        while j < len(lines) and not lines[j].lstrip().startswith(tick):
            j += 1
        if info in SHELL_FENCES:
            body = tuple(
                ln[indent:] if ln[:indent].strip() == "" else ln
                for ln in lines[i + 1 : j]
            )
            blocks.append(Block(path, i + 2, info, body))
        i = j + 1
    return blocks


def unquoted_globs(bare: str, test_open: bool) -> tuple[list[tuple[int, int]], bool]:
    """The spans of `bare` that zsh reads as a `[...]` glob, and whether a
    `[[ ... ]]` test is still open at the end of the line.

    `bare` is one line as zsh's word splitter sees it: every quoted, escaped,
    subscripted or arithmetic character is `_`, a `$(` is ` ;`, so only the
    unquoted text is left. A word that holds a `[` is a glob, except a `[` on
    its own (the test command, or a plain argument), a `[[` that starts a
    command, every word inside `[[ ... ]]`, an assignment's value, and the
    words of a `noglob` command.
    """
    spans: list[tuple[int, int]] = []
    for command in re.finditer(r"[^;&|()\n]+", bare):
        lead = True
        declares = noglob = False
        for w in re.finditer(r"[^\s<>]+", command.group()):
            word = w.group()
            span = (command.start() + w.start(), command.start() + w.end())
            if test_open:
                test_open = word != "]]"
                continue
            if lead and word in LEADS:
                continue
            if (lead or declares) and ASSIGNMENT.match(word):
                continue
            if lead:
                lead = False
                if word == "[[":
                    test_open = True
                    continue
                noglob = word == "noglob"
                declares = word in DECLARES
            if noglob or "[" not in word or word == "[":
                continue
            spans.append(span)
    return spans, test_open


def paste_problems(block: Block) -> list[str]:
    """What breaks when this block is pasted at a zsh prompt.

    A `#` that starts a word is a problem anywhere in a pasted block: after a
    command it is a trailing comment zsh runs as words; on its own line it is
    a command named `#`. Only a script block, one whose first line is `#!`,
    may carry `#` lines. A quote still open at the end of the block is the
    other problem, and an unquoted `<word>` placeholder, a redirection, the
    third. The fourth is an unquoted word that holds a `[`: zsh reads it as a
    glob, and with nothing to match the paste stops (see unquoted_globs for
    what zsh reads as written). Heredoc bodies are text, so they are not read
    for any of them.
    """
    script = bool(block.lines) and block.lines[0].startswith("#!")
    problems: list[str] = []
    # The open quoting contexts: "'" '"' "$'" "`", and the expansions "$(",
    # "$((" and "${" (each with its paren or brace depth).
    stack: list[list] = []
    heredocs: list[tuple[str, bool]] = []
    in_heredoc: tuple[str, bool] | None = None
    opened_at = 0
    test_open = False
    for n, line in enumerate(block.lines):
        where = f"{block.path}:{block.line + n}"
        if in_heredoc:
            word, dash = in_heredoc
            if (line.lstrip("\t") if dash else line) == word:
                in_heredoc = heredocs.pop(0) if heredocs else None
            continue
        if not stack:
            heredocs = [(m["word"], bool(m["dash"])) for m in HEREDOC.finditer(line)]
        # The line as zsh's word splitter sees it, for unquoted_globs.
        bare = list(line)
        comment_at = len(line)
        words_before = hashed = False
        k = 0
        while k < len(line):
            c = line[k]
            top = stack[-1][0] if stack else None
            first = k
            # What the characters read here, first..k, become in `bare`:
            # None keeps them, "_" blanks them (quoted, escaped, an expansion).
            mark: str | None = "_"
            if top == "'":
                if c == "'":
                    stack.pop()
            elif top == "$'":
                if c == "\\":
                    k += 1
                elif c == "'":
                    stack.pop()
            elif top in ('"', "`"):
                if c == "\\":
                    k += 1
                elif c == top:
                    stack.pop()
                elif c == "$" and line[k + 1 : k + 3] == "((":
                    stack.append(["$((", 2])
                    k += 2
                elif c == "$" and line[k + 1 : k + 2] == "(":
                    stack.append(["$(", 1])
                    mark = " ;"
                    k += 1
            else:
                # Unquoted: the top level, or inside a $( ... ), $(( ... )) or ${ ... }.
                if c == "\\":
                    k += 1
                elif c == "'":
                    if not stack:
                        opened_at = n
                    stack.append(["'" if line[k - 1 : k] != "$" else "$'", 0])
                elif c in ('"', "`"):
                    if not stack:
                        opened_at = n
                    stack.append([c, 0])
                elif c == "$" and line[k + 1 : k + 3] == "((":
                    if not stack:
                        opened_at = n
                    stack.append(["$((", 2])
                    k += 2
                elif c == "$" and line[k + 1 : k + 2] == "{":
                    if not stack:
                        opened_at = n
                    stack.append(["${", 1])
                    k += 1
                elif c == "$" and line[k + 1 : k + 2] == "(":
                    if not stack:
                        opened_at = n
                    stack.append(["$(", 1])
                    mark = " ;"
                    k += 1
                elif c == "$" and (name := NAME.match(line, k + 1)):
                    # `$name[1]`: the one subscript is not a glob.
                    k = name.end() - 1
                    if line[k + 1 : k + 2] == "[" and "]" in line[k + 1 :]:
                        k = line.index("]", k + 1)
                elif top in ("$(", "$((") and c == "(":
                    stack[-1][1] += 1
                    mark = None
                elif top in ("$(", "$((") and c == ")":
                    stack[-1][1] -= 1
                    mark = None
                    if stack[-1][1] == 0:
                        stack.pop()
                        if top == "$(":
                            mark = " "
                elif top == "${" and c == "{":
                    stack[-1][1] += 1
                elif top == "${" and c == "}":
                    stack[-1][1] -= 1
                    if stack[-1][1] == 0:
                        stack.pop()
                elif (
                    c == "<"
                    and line[k - 1 : k] != "<"
                    and (ph := PLACEHOLDER.match(line, k))
                ):
                    problems.append(
                        f"{where}: a <word> placeholder, a redirection: {ph.group()}"
                    )
                    words_before = True
                    k = ph.end() - 1
                elif c == "#" and (k == 0 or line[k - 1] in " \t;&|") and not hashed:
                    # zsh reads on past it, so the rest of the line still counts.
                    hashed = True
                    mark = None
                    if script:
                        # A script is run, not pasted: its `#` is a comment.
                        comment_at = k
                    if words_before:
                        problems.append(
                            f"{where}: a trailing # comment: {line.strip()}"
                        )
                    elif not script:
                        problems.append(
                            f"{where}: a # line in a block that is pasted: {line.strip()}"
                        )
                else:
                    mark = None
                    words_before = words_before or not c.isspace()
                if mark is None and any(e[0] in ("$((", "${") for e in stack):
                    mark = "_"
                words_before = words_before or c == "$"
            if mark is not None:
                last = min(k + 1, len(line))
                bare[first:last] = mark.ljust(last - first, "_")
            k += 1
        bare[comment_at:] = "_" * (len(line) - comment_at)
        spans, test_open = unquoted_globs("".join(bare), test_open)
        problems += [
            f"{where}: an unquoted [...] glob, the paste stops in zsh: {line[a:b]}"
            for a, b in spans
        ]
        if not stack and heredocs:
            in_heredoc = heredocs.pop(0)
    if stack:
        problems.append(
            f"{block.path}:{block.line + opened_at}: a quote opened here is still open"
            f" at the end of the block ({stack[0][0]})"
        )
    return problems


DOCS = _doc_files()


def _all_blocks() -> list[Block]:
    return [
        b
        for name in DOCS
        for b in shell_blocks((ROOT / name).read_text(encoding="utf-8"), name)
    ]


def test_the_guard_reads_the_public_docs():
    names = set(DOCS)
    assert {"README.md", "INSTALL.md", "AGENTS.md", "docs/components.md"} <= names
    assert "CHANGELOG.md" not in names
    assert not any(n.startswith("tests/fixtures/") for n in names)
    blocks = _all_blocks()
    assert len(blocks) > 50, len(blocks)
    assert {b.path for b in blocks} >= {"README.md", "INSTALL.md", "docs/components.md"}


def test_no_pasted_shell_line_carries_a_comment_an_open_quote_or_a_placeholder():
    problems = [p for b in _all_blocks() for p in paste_problems(b)]
    assert problems == [], "\n".join(problems)


# The canaries: the guard bites on each way a paste breaks, and on the real
# docs, and lets through what zsh reads as written.
#
# The [...] glob canaries are each measured in a real zsh below
# (test_zsh_stops_on_each_glob_the_guard_flags), so a case moves list only
# when zsh says so. Each one-liner prints `ok` when zsh runs it as written.
GLOB_BITES = [
    "message list [BOX]",
    "echo x[y]",
    "echo [a-z] [^x]",
    "echo []",
    "echo x[",
    "echo [x",
    "echo [[ -n x ]]",
    "echo --opt=[y] x=[y]",
    "echo http://[::1]:80",
    "echo {[x],y}",
    "echo $1[x]",
    "echo ${HOME}[x]",
    "a=(p q); echo $a[1][1]",
    "env a=[y] true",
    "a=(x [y])",
    "echo $(echo [x])",
    'echo "$(echo [x])"',
    "[[ -n x ]] && echo [y]",
    "true\necho [y]",
]
GLOB_READS_AS_WRITTEN = [
    "echo '[x]' \"[x]\" ok",
    "echo \\[x\\] \\[x] a\\[x] ok",
    "[[ -n x ]] && echo ok",
    "[ -n x ] && echo ok",
    "test [ = [ && echo ok",
    "[[ x == [xy] ]] && echo ok",
    "if [[ x == [xy]* ]]; then echo ok; fi",
    "echo [ ] ab] ]] [ ok",
    'a=(p q); echo ${a[1]} "${a[@]}" ${#a[@]} $a[1] x$a[2]y $((a[1] + 1)) ok',
    "a[1]=x; echo ok",
    "a=[y] b+=[z]; echo ok",
    "export a=[y]; typeset b=[y]; echo ok",
    "noglob echo [x] ok",
    "echo \"$(echo '[x]')\" ok",
]


def _one(text: str) -> Block:
    [block] = shell_blocks(f"```bash\n{text}\n```\n")
    return block


@pytest.mark.parametrize(
    ("text", "says"),
    [
        ("session list   # your live sessions", "a trailing # comment"),
        ("make check;# lint, then test", "a trailing # comment"),
        ('rm -rf "$x"   # (in the cache)', "a trailing # comment"),
        ("# one session's window\nsession list", "a # line in a block that is pasted"),
        ("session context x   # one session's window\nsession list", "still open"),
        ('message send box -s "PR ready -f note.md', "still open"),
        ("echo 'it is\nsession list", "still open"),
        ('echo "$(session list "x)"', "still open"),
        ('message send <box> -s "PR ready" -f note.md', "a <word> placeholder"),
        ("cd <the directory you will work from>", "a <word> placeholder"),
        ("sessionkit setup --address <name@host>", "a <word> placeholder"),
        ('echo "$(session context <seat>)"', "a <word> placeholder"),
        ("$EDITOR   # your editor", "a trailing # comment"),
        ("#!/bin/sh\n${EDITOR}   # your editor", "a trailing # comment"),
        ("#!/bin/sh\n$((1 + 1)) # two", "a trailing # comment"),
        ("echo ${x:-'a b}", "still open"),
    ]
    + [(text, "an unquoted [...] glob") for text in GLOB_BITES],
)
def test_the_canary_bites(text, says):
    problems = paste_problems(_one(text))
    assert any(says in p for p in problems), problems


@pytest.mark.parametrize(
    "text",
    [
        'echo "${#PATH}" $# \'a # b\' "c # d"',
        "git clone https://example.invalid/x#frag",
        "echo $'it\\'s'",
        'f="$(printf "%s" "$(date)")" && echo "$f"',
        "cat > note.md <<'EOF'\nan apostrophe's # fine in here\nEOF\necho done",
        "perl -pi -e '\n  s/\"a\"/b/\n' file",
        "#!/bin/sh\n# a script the reader saves and runs\necho ok",
        "message send TO -s 'PR ready' -f note.md",
        "sort < in.txt > out.txt",
        "sort <in >out",
        "diff <(ls a) <(ls b)",
        "exec 3<&0",
        "echo '<box>' \"<b>bold</b>\"",
        "cat <<EOF>note.md\n<box> is text in here\nEOF",
        "cat <<'EOF'\nmessage list [BOX]\nEOF",
        "#!/bin/sh\n# message list [BOX], in a comment\necho ok",
    ]
    + GLOB_READS_AS_WRITTEN,
)
def test_the_canary_lets_through_what_zsh_reads_as_written(text):
    assert paste_problems(_one(text)) == []


def test_the_canary_bites_on_the_real_readme():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "\nsession list\n" in readme
    planted = readme.replace(
        "\nsession list\n", "\nsession list   # your live sessions\n", 1
    )
    problems = [
        p for b in shell_blocks(planted, "README.md") for p in paste_problems(b)
    ]
    assert len(problems) == 1 and "README.md:" in problems[0], problems


def test_the_placeholder_canary_bites_on_the_real_readme():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "\nmessage send TO -s" in readme
    planted = readme.replace("\nmessage send TO -s", "\nmessage send <box> -s", 1)
    problems = [
        p for b in shell_blocks(planted, "README.md") for p in paste_problems(b)
    ]
    assert len(problems) == 1 and "<box>" in problems[0], problems


ZSH = shutil.which("zsh")


@pytest.mark.skipif(ZSH is None, reason="no zsh on this machine")
def test_zsh_at_the_prompt_reads_a_hash_as_a_word(tmp_path):
    # The premise, measured: an interactive zsh with no rc files.
    env = {
        "HOME": str(tmp_path),
        "ZDOTDIR": str(tmp_path),
        "PATH": os.defpath,
        "TERM": "dumb",
    }
    done = subprocess.run(
        [ZSH, "-f", "-i"],
        input="PS1=''\necho x # only if\n",
        env=env,
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert "x # only if" in done.stdout, (done.stdout, done.stderr)


def _zsh_at_the_prompt(text: str, cwd: Path) -> subprocess.CompletedProcess:
    # An interactive zsh with no rc files, in an empty directory, so a glob
    # can match nothing.
    env = {"HOME": str(cwd), "ZDOTDIR": str(cwd), "PATH": os.defpath, "TERM": "dumb"}
    return subprocess.run(
        [ZSH, "-f", "-i"],
        input=f"PS1=''\n{text}\n",
        env=env,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )


@pytest.mark.skipif(ZSH is None, reason="no zsh on this machine")
@pytest.mark.parametrize("text", GLOB_BITES)
def test_zsh_stops_on_each_glob_the_guard_flags(text, tmp_path):
    done = _zsh_at_the_prompt(text, tmp_path)
    assert re.search(r"zsh: (no matches found|bad pattern): ", done.stderr), (
        done.stdout,
        done.stderr,
    )
    assert "ok" not in done.stdout.split()


@pytest.mark.skipif(ZSH is None, reason="no zsh on this machine")
@pytest.mark.parametrize("text", GLOB_READS_AS_WRITTEN)
def test_zsh_reads_each_glob_the_guard_lets_through_as_written(text, tmp_path):
    done = _zsh_at_the_prompt(text, tmp_path)
    assert "zsh:" not in done.stderr, (done.stdout, done.stderr)
    assert "ok" in done.stdout.split(), (done.stdout, done.stderr)
