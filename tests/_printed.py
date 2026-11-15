"""Every line install.sh can print, read from its source, at its widest.

The rule: every line install.sh prints is 76 display columns or
less, an emoji counted at its display width. tests/test_install_sh.py holds
the script to it twice: here, statically, over every `say`, every printf that
reaches the screen and the usage heredoc; and over real runs on the fake Mac.

The static read expands each string as bash would. A constant is read from the
script's own top-level assignment, and a function's `local what="..."` from
that function. What only the run knows (a version, a path, a port holder, an
error) is bounded by WORST below: the value it can take, or a stated worst
case where the value comes from outside the script. An expansion with no
bound fails the test that reads it, so a new one cannot slip past unmeasured.

Display width: an East Asian Width W or F character is 2 columns, a combining
mark or variation selector 0, anything else 1. Colour escapes count 0.
"""

from __future__ import annotations

import fnmatch
import re
import unicodedata

WIDTH = 76

ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]|\\033\[[0-9;]*[A-Za-z]|\r|\\r")


def display_width(text: str) -> int:
    text = ANSI.sub("", text)
    n = 0
    for c in text:
        if unicodedata.combining(c) or c in "︎️‍":
            continue
        n += 2 if unicodedata.east_asian_width(c) in "WF" else 1
    return n


# A version as long as any these tools print, and then some.
VERSION = "10.10.100"

# What only the run knows. A key is the expansion as the source writes it,
# or (function, expansion) where one function's value is narrower. A stated
# worst case says so in its comment.
WORST: dict[object, str] = {
    # Colour: escape codes, no columns.
    "${BOLD}": "",
    "${RESET}": "",
    "${RED}": "",
    # The checks.
    "${ver:-unknown}": "26.10.10",
    "$ARCH_WORDS": "Apple silicon",
    "$ADMIN": "yes",
    "$(version_of brew)": ", " + VERSION,
    "$(version_of uv)": ", " + VERSION,
    "$(version_of claude)": ", " + VERSION,
    # BREW_SET's longest name, and its icon.
    ("check_all", "$name"): "notmuch",
    ("check_all", "$icon"): "📨",
    ("check_all", '${out#"$name "}'): VERSION + "_10",
    "${out#sessionkit v}": VERSION,
    # The plugin versions row: one split, as the row prints each on its own line.
    ("check_plugin_versions", "$split"): (
        "sessionvoice plugin not installed, package not installed"
    ),
    ("check_plugin_versions", "$s"): "sessionvoice@sessionkit",
    ("check_plugin_versions", "$market"): "sessionkit",
    # The doctor's missing-row count.
    "$MISSING_ROWS": "14",
    # Paths. Stated worst case: ZDOTDIR unset, so ~/.zprofile; Homebrew at the
    # longer of its two prefixes.
    '$(tildify "$(zprofile_path)")': "~/.zprofile",
    '$(tildify "$f")': "~/.zprofile",
    "$(new_brew_path)": "/opt/homebrew/bin/brew",
    "$BREW": "/opt/homebrew/bin/brew",
    # uv's shell files: the two it names when ~/.zshrc exists, or all five
    # (each on its own line when there are more than two).
    "${files[0]}": "~/.zshenv",
    "${files[1]}": "~/.profile",
    "${#files[@]}": "5",
    ("list_step", "$f"): "~/.bash_profile",
    # The plan: the longest count, and the brew set at its longest.
    ("print_list", "$n"): "11",
    ("print_list", "$edits"): "No other shell file changes",
    ("print_list", "$password"): "no other password",
    ("confirm", "$q"): "Install these 11?",
    ("confirm", "$hint"): "[Y/n]",
    ("confirm", "$answer"): "yes",
    # The free disk is under DISK_NEED_GB when it is said.
    "$free_gb": "7",
    # A step's exit, and its time. Stated worst case: under 100 minutes.
    "$rc": "255",
    ("setup_failed", "$1"): "255",
    "$(duration $((SECONDS - start)))": "99 min 59 s",
    # Stated worst case: an unknown option of 30 characters.
    ("parse_args", "$1"): "--an-unknown-option-30-chars-x",
    "$2": "notmuch",
    # Why the hooks are left: the longest the script sets. Under check_hooks
    # and nothing_to_do only the checks set it, so only the no-verb words.
    "$HOOKS_WHY": "pager settings hooks on refused (exit 255)",
    ("check_hooks", "$HOOKS_WHY"): "this pager has no hooks verb yet",
    ("nothing_to_do", "$HOOKS_WHY"): "this pager has no hooks verb yet",
    # Setup's own line, passed through as it prints it: the child's to keep
    # in its width, as CHILD_OUTPUT in the tests says of every child.
    ("install_setup", "$line"): "",
    # The launch step setup names. The installer runs it with no --agent, so
    # the agent is claude: bare when that is the default seat, else named.
    "$LAUNCH_CMD": "session start claude",
}

# Functions whose output is captured, never printed as a line of its own.
HELPERS = {
    "say",
    "found",
    "missing",
    "tildify",
    "join_and",
    "duration",
    "find_tool",
    "zprofile_path",
    "version_of",
    "full_command_name",
    "new_brew_path",
    "plugin_versions",
    "plugin_version",
    "package_version",
}


class Unbounded(Exception):
    """An expansion with no value in the script and no bound in WORST."""


def _functions(src: str) -> dict[str, str]:
    out = {}
    for m in re.finditer(r"^(\w+)\(\) \{\n(.*?)^\}", src, re.MULTILINE | re.DOTALL):
        out[m.group(1)] = m.group(2)
    one_line = re.finditer(r"^(\w+)\(\) \{ (.*) \}$", src, re.MULTILINE)
    for m in one_line:
        out[m.group(1)] = m.group(2)
    return out


def _top_level(src: str) -> str:
    """The source with every function body taken out."""
    return re.sub(r"^\w+\(\) \{\n.*?^\}\n", "", src, flags=re.MULTILINE | re.DOTALL)


def _quoted(s: str, i: int) -> tuple[str, int]:
    """s[i] is a double quote: the text inside, as written, and the index
    past the closing quote. A $( ... ) inside may hold quotes of its own."""
    j, depth, out = i + 1, 0, []
    while True:
        c = s[j]
        if c == "\\":
            out.append(s[j : j + 2])
            j += 2
            continue
        if s.startswith("${", j):
            k = _balanced(s, j + 1, "{", "}")
            out.append(s[j:k])
            j = k
            continue
        if s.startswith("$(", j):
            depth += 1
            out.append("$(")
            j += 2
            continue
        if depth and c == "(":
            depth += 1
        elif depth and c == ")":
            depth -= 1
        elif depth and c == '"':
            inner, j = _quoted(s, j)
            out.append('"' + inner + '"')
            continue
        elif c == '"':
            return "".join(out), j + 1
        out.append(c)
        j += 1


def _balanced(s: str, i: int, open_: str, close: str) -> int:
    """s[i] opens; the index past its matching close."""
    depth, j = 0, i
    while j < len(s):
        if s[j] == "\\":
            j += 2
            continue
        if s[j] == '"':
            _, j = _quoted(s, j)
            continue
        if s[j] == open_:
            depth += 1
        elif s[j] == close:
            depth -= 1
            if depth == 0:
                return j + 1
        j += 1
    raise ValueError(s[i:])


class Script:
    def __init__(self, src: str):
        self.src = src
        self.funcs = _functions(src)
        self.consts: dict[str, str] = {}
        self.arrays: dict[str, list[str]] = {}
        for m in re.finditer(
            r"^([A-Z_][A-Z_0-9]*)=(.*)$", _top_level(src), re.MULTILINE
        ):
            name, raw = m.group(1), m.group(2)
            if raw.startswith("("):
                self.arrays[name] = raw.strip("()").split()
            elif raw.startswith('"'):
                self.consts[name] = _quoted(raw, 0)[0]
            elif raw.startswith("'"):
                self.consts[name] = raw[1:-1]
            else:
                self.consts[name] = raw
        self.derived = self._derived()
        self.locals: dict[str, dict[str, str]] = {}
        for f, body in self.funcs.items():
            for m in re.finditer(r'\blocal (\w+)="', body):
                self.locals.setdefault(f, {})[m.group(1)] = _quoted(body, m.end() - 1)[
                    0
                ]

    def _derived(self) -> dict[str, str]:
        """Bounds the script enforces itself, read from its constants. A port
        holder is a name ps gives, cut to HOLDER_NAME_MAX, and a 5-digit pid,
        or the script's own words for a holder lsof cannot see: the longest.
        A pager's refusal is folded to HOOKS_ERR_WIDTH, and a step setup
        left to SETUP_STEP_WIDTH."""
        named = "n" * int(self.consts["HOLDER_NAME_MAX"]) + " (pid 99999)"
        words = re.findall(r'PORT_HOLDER="([^"$]+)"', self.src)
        return {
            "$PORT_HOLDER": max([named, *words], key=display_width),
            "$errline": "e" * int(self.consts["HOOKS_ERR_WIDTH"]),
            "$stepline": "s" * int(self.consts["SETUP_STEP_WIDTH"]),
        }

    # --- expanding ------------------------------------------------------
    def _worst(self, func: str, text: str) -> str | None:
        for key in ((func, text), text):
            if key in WORST:
                return WORST[key]
        return self.derived.get(text)

    def _var(self, func: str, name: str, text: str) -> str:
        w = self._worst(func, text)
        if w is not None:
            return w
        if name in self.locals.get(func, {}):
            return self.expand(func, self.locals[func][name])
        if name in self.consts:
            return self.expand(func, self.consts[name])
        raise Unbounded(f"{func}: {text}")

    def _command(self, func: str, text: str) -> str:
        w = self._worst(func, text)
        if w is not None:
            return w
        inner = text[2:-1].strip()
        m = re.fullmatch(r"(found|missing) (.+)", inner)
        if m:
            arg = m.group(2)
            if arg.startswith('"'):
                return self.expand(func, _quoted(arg, 0)[0])
            return self.expand(func, arg)
        m = re.fullmatch(r'join_and "\$\{(\w+)\[@\]\}"', inner)
        if m and m.group(1) == "MISSING_SET":
            names = self.arrays["BREW_SET"]
            return ", ".join(names[:-1]) + " and " + names[-1]
        raise Unbounded(f"{func}: {text}")

    def expand(self, func: str, s: str) -> str:
        out, i = [], 0
        while i < len(s):
            c = s[i]
            if c == "\\" and i + 1 < len(s):
                out.append(s[i + 1])
                i += 2
            elif s.startswith("$((", i):
                j = _balanced(s, i + 1, "(", ")")
                raise Unbounded(f"{func}: {s[i:j]}")
            elif s.startswith("$(", i):
                j = _balanced(s, i + 1, "(", ")")
                out.append(self._command(func, s[i:j]))
                i = j
            elif s.startswith("${", i):
                j = _balanced(s, i + 1, "{", "}")
                text = s[i:j]
                w = self._worst(func, text)
                m = re.fullmatch(r"\$\{(\w+)\}", text)
                a = re.fullmatch(r"\$\{(\w+)\[\*\]\}", text)
                cut = re.fullmatch(r"\$\{(\w+)(%%|%|##|#)(.+)\}", text)
                if w is not None:
                    out.append(w)
                elif cut and cut.group(1) in self.consts:
                    out.append(self._cut(func, *cut.groups()))
                elif m:
                    out.append(self._var(func, m.group(1), text))
                elif a and a.group(1) == "MISSING_SET":
                    out.append(" ".join(self.arrays["BREW_SET"]))
                elif a and a.group(1) in self.arrays:
                    out.append(" ".join(self.arrays[a.group(1)]))
                else:
                    raise Unbounded(f"{func}: {text}")
                i = j
            elif (
                c == "$" and i + 1 < len(s) and (s[i + 1].isalnum() or s[i + 1] == "_")
            ):
                m = re.match(r"\$(\w+)", s[i:])
                out.append(self._var(func, m.group(1), m.group(0)))
                i += len(m.group(0))
            else:
                out.append(c)
                i += 1
        return "".join(out)

    def _cut(self, func: str, name: str, op: str, pat: str) -> str:
        """${NAME%%PAT} and its kin, on a constant: PAT a glob."""
        value = self.expand(func, self.consts[name])
        rx = fnmatch.translate(pat)[4:-3]  # the glob, unanchored
        if op.startswith("%"):
            greedy = op == "%%"
            ends = [
                i
                for i in range(len(value) + 1)
                if re.fullmatch(rx, value[i:], re.DOTALL)
            ]
            return value[: (min(ends) if greedy else max(ends))] if ends else value
        greedy = op == "##"
        starts = [
            i for i in range(len(value) + 1) if re.fullmatch(rx, value[:i], re.DOTALL)
        ]
        return value[(max(starts) if greedy else min(starts)) :] if starts else value

    # --- the printed lines ----------------------------------------------
    def _list_prefix(self) -> str:
        """print_list's `printf '%4d. '`, at the longest count."""
        m = re.search(r"printf '(%(\d+)d\. )'", self.funcs["print_list"])
        return "11. ".rjust(int(m.group(2)) + 2)

    def printed(self) -> list[tuple[int, str, str]]:
        """(source line, function, the line at its widest) for every line the
        script can print. A run_step line is expanded once per step_label."""
        rows: list[tuple[int, str, str]] = []
        labels = self._step_labels()
        indent = self.consts["INDENT"]
        prefix = self._list_prefix()
        func = None
        for m in re.finditer(r'^(\w+)\(\) \{|\bsay "', self.src, re.MULTILINE):
            if m.group(1):
                func = m.group(1)
                continue
            if func in HELPERS or func == "step_label":
                continue
            body = _quoted(self.src, m.end() - 1)[0]
            line = self.src.count("\n", 0, m.start()) + 1
            if func == "run_step":
                only = self._step_guard(m.start())
                for step, icon, name, doing, section in labels:
                    if only and step != only:
                        continue
                    s = (
                        body.replace("$icon", icon)
                        .replace("$name", name)
                        .replace("${doing}", doing)
                        .replace("$section", section)
                    )
                    rows += [(line, func, t) for t in self.expand(func, s).split("\n")]
                continue
            text = self.expand(func, body)
            if func == "list_step" and not body.startswith("${INDENT}"):
                text = prefix + text
            assert not text.startswith(indent * 2)
            rows += [(line, func, t) for t in text.split("\n")]
        rows += self._printfs()
        rows += self._heredocs()
        return rows

    def _step_labels(self) -> list[tuple[str, ...]]:
        """(step, icon, name, doing, section) for each arm of step_label."""
        out = []
        for m in re.finditer(r'(\w+)\) say "', self.funcs["step_label"]):
            body = _quoted(self.funcs["step_label"], m.end() - 1)[0]
            fields = self.expand("step_label", body).split("|")
            out.append((m.group(1), *fields))
        return out

    def _step_guard(self, at: int) -> str | None:
        """The step a run_step line at offset `at` is said for, when an
        enclosing `if [[ "$step" == STEP` holds it to one; else None."""
        head = self.src[:at]
        start = head.rfind("\nrun_step() {")
        stack: list[str | None] = []
        for line in head[start:].splitlines()[1:]:
            code = line.strip()
            if code.startswith("if "):
                g = re.search(r'"\$step" == (\w+)', code)
                stack.append(g.group(1) if g else None)
            elif code in ("else", "fi") or code.startswith("elif "):
                stack.pop()
                if code != "fi":
                    stack.append(None)
        steps = [g for g in stack if g]
        return steps[-1] if steps else None

    def _printfs(self) -> list[tuple[int, str, str]]:
        """Each printf whose format reaches the screen as a line: its %s
        filled from its arguments. print_list's number prefix is counted with
        the list's lines, so it is left out here."""
        rows = []
        for func, body in self.funcs.items():
            if func in HELPERS or func == "print_list":
                continue
            for m in re.finditer(r"printf '([^']*)'((?: \"[^\"]*\")*)", body):
                fmt, args = m.group(1), re.findall(r'"([^"]*)"', m.group(2))
                start = body[: m.start()]
                if start.endswith("$(") or "$(printf" in start[-12:]:
                    continue
                rest = body[m.end() :].split("\n", 1)[0]
                if rest.lstrip().startswith(("|", ">")):
                    continue
                vals = iter([self.expand(func, a) for a in args])
                text = re.sub(r"%[sd]", lambda _, v=vals: next(v), fmt)
                line = self.src.find(m.group(0))
                n = self.src.count("\n", 0, line) + 1
                for t in text.replace("\\n", "\n").split("\n"):
                    rows.append((n, func, t))
        return rows

    def _heredocs(self) -> list[tuple[int, str, str]]:
        rows = []
        for func, body in self.funcs.items():
            for m in re.finditer(r"<<(\w+)\n(.*?)^\1$", body, re.MULTILINE | re.DOTALL):
                start = self.src.find(m.group(2))
                n0 = self.src.count("\n", 0, start) + 1
                for k, t in enumerate(m.group(2).splitlines()):
                    rows.append((n0 + k, func, self.expand(func, t)))
        return rows
