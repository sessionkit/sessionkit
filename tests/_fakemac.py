"""A fake Mac for install.sh: a scratch HOME, stub system tools and stub kit
tools, each logging its argv to calls.log.

Each test builds a Mac in a scratch folder: a HOME, stub system tools
(uname, sw_vers, id, curl, lsof, launchctl) first on PATH, and stub brew, uv, claude,
sessionkit, ears and pager put where their real installers put them. The curl stub
serves fixture installers by URL, and answers the speech server's
`127.0.0.1:8890/v1/models` with 200 when the `speech_serving` flag is set.
Every stub appends its argv to calls.log, so a test reads what the script
ran and in what order.

The pager stub fakes sessionmail's `pager settings hooks on|off` (SM-983):
its state is the real file, ~/.sessionkit/mail/settings/mail.json, so the
doctor's hooks row reads what the stub wrote. The `pager_old` flag gives the
help of a pager without the verb (install and migrate only, as measured on
an older sessionmail); `pager_on_rc` makes `on` exit with that number
and a stderr line, writing nothing.

The script has no test seam: it calls each tool by name. The one change a
test makes to its copy is the BREW_PATHS line, pointed at the scratch
folder, because Homebrew's real prefixes are outside any test's reach.
`test_the_copy_differs_only_in_brew_paths` pins that.

The script runs under /bin/bash where there is one: a fresh Mac's bash is
3.2, and the script must run there.

Shared by tests/test_install_sh.py (install.sh itself) and
tests/test_doctor.py (`sessionkit doctor`, which runs it with --check).
"""

from __future__ import annotations

import hashlib
import os
import pty
import re
import select
import shutil
import stat
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "install.sh"
SOURCE = SCRIPT.read_text(encoding="utf-8")
BASH = "/bin/bash" if Path("/bin/bash").exists() else shutil.which("bash")
SYSTEM_PATH = "/usr/bin:/bin:/usr/sbin:/sbin"


# The speech server's read-only probe: the only network install.sh --check
# reaches itself (the tools it asks, such as claude, may use their own).
SPEECH_PROBE_URL = "http://127.0.0.1:8890/v1/models"

# A line of calls.log that changes the Mac. Everything else is a probe; a curl
# of the speech server's /v1/models is a probe too.
INSTALL_VERB = re.compile(
    r"^(curl (?!.* http://127\.0\.0\.1:8890/v1/models$)|installer |brew install|uv tool install|claude plugin marketplace add|"
    r"claude plugin install|ears install|ears services install|sessionkit setup$|"
    r"pager settings hooks on$)"
)


def _exe(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


LOG = 'printf "%s\\n" "$(basename "$0") $*" >> "$STUB_CALLS"\nS=$STUB_STATE\n'

SYSTEM_STUBS = {
    "uname": LOG
    + """case "$1" in
  -s) cat "$S/os" 2>/dev/null || echo Darwin ;;
  -m) cat "$S/arch" 2>/dev/null || echo arm64 ;;
  *) echo Darwin ;;
esac
""",
    "sw_vers": LOG + "echo 27.0\n",
    "id": LOG
    + """case "$1" in
  -u) cat "$S/uid" 2>/dev/null || echo 501 ;;
  -Gn) if [ -f "$S/not_admin" ]; then echo "staff everyone"; else echo "staff everyone admin"; fi ;;
  *) /usr/bin/id "$@" ;;
esac
""",
    "lsof": LOG
    + """if [ -f "$S/port_holder" ]; then
  echo "COMMAND   PID USER   FD   TYPE DEVICE SIZE/OFF NODE NAME"
  echo "$(cat "$S/port_holder") 4242 user   7u  IPv4 0x1      0t0  TCP 127.0.0.1:8890 (LISTEN)"
fi
""",
    # The holder's whole command name, as macOS's ps gives it: a path.
    "ps": LOG
    + """[ "$*" = "-o comm= -p 4242" ] && [ -f "$S/port_holder_full" ] && cat "$S/port_holder_full"
exit 0
""",
    # A connection to the port: refused unless a test opens it.
    "nc": LOG
    + """[ -f "$S/port_open" ] && exit 0
exit 1
""",
    # launchd, read-only: `launchctl print gui/UID/LABEL` finds the phone
    # bot's job when phone_loaded is set (the doctor's phone row asks it).
    "launchctl": LOG
    + """[ "$1" = print ] || exit 1
case "$2" in
  */dev.sessionkit.phone.bot.*)
    if [ -f "$S/phone_loaded" ]; then printf '\tpid = 77\n\tlast exit code = 0\n'; exit 0; fi ;;
esac
exit 113
""",
    "curl": LOG
    + """url=""
for a in "$@"; do case "$a" in http*) url=$a ;; esac; done
case "$url" in
  *Homebrew/install*) cat "$STUB_TOOLS/homebrew-installer" ;;
  *astral.sh/uv/install.sh) cat "$STUB_TOOLS/uv-installer" ;;
  *claude.ai/install.sh) cat "$STUB_TOOLS/claude-installer" ;;
  # The speech server: as curl -o /dev/null -w '%{http_code}' prints it.
  http://127.0.0.1:8890/v1/models)
    if [ -f "$S/speech_serving" ]; then printf 200; exit 0; fi
    printf 000; exit 7 ;;
  *) exit 22 ;;
esac
""",
}

TOOL_STUBS = {
    # brew also records HOMEBREW_NO_INSTALL_FROM_API for each call, in its own
    # log: the check's read must carry it, and `brew install` must not.
    "brew": LOG
    + """printf '%s\\t%s\\n' "${HOMEBREW_NO_INSTALL_FROM_API-unset}" "$*" >> "$STUB_BREW_ENV"
case "$1" in
  --version)
    echo "Homebrew 4.6.1"
    # With the switch on, a real Homebrew prints a second line,
    # "Homebrew/homebrew-core N/A" (measured, brew 7.0.10), and `| head -1`
    # then fails the pipe with SIGPIPE under pipefail (exit 141). The stub
    # writes that line past the pipe's 64K buffer, so a reader that stops
    # at line 1 meets the same failure every time, with no race.
    if [ "${HOMEBREW_NO_INSTALL_FROM_API-}" = 1 ]; then
      i=0; while [ $i -lt 3000 ]; do echo "Homebrew/homebrew-core N/A"; i=$((i + 1)); done
    fi
    exit 0 ;;
  list)
    [ "$2" = --versions ] && name=$3 || name=$2
    if [ -f "$S/brew/$name" ]; then
      echo "$name 1.0"
      [ -f "$S/brew_list_fails" ] && exit 1
      exit 0
    fi
    exit 1 ;;
  install) shift; mkdir -p "$S/brew"; for n in "$@"; do touch "$S/brew/$n"; done ;;
  shellenv) d=$(cd "$(dirname "$0")" && pwd); echo "export PATH=\\"$d:\\$PATH\\"" ;;
esac
""",
    "uv": LOG
    + """case "$1 $2" in
  "--version "*) echo "uv 0.13.5 (stub)" ;;
  "tool list") if [ -f "$S/kit" ]; then echo "sessionkit v0.3.1"; echo "- sessionkit"; else echo "No tools installed"; fi ;;
  "tool install")
    [ -f "$S/kit_fails" ] && { echo "error: your requirements are unsatisfiable" >&2; exit 1; }
    touch "$S/kit"; mkdir -p "$HOME/.local/bin"
    cp "$STUB_TOOLS/sessionkit" "$STUB_TOOLS/ears" "$STUB_TOOLS/pager" "$HOME/.local/bin/" ;;
esac
""",
    "claude": LOG
    + """case "$*" in
  --version) echo "2.1.310 (Claude Code)" ;;
  "plugin list") [ -f "$S/plugin" ] && echo "  sessionkit@sessionkit" ;;
  "plugin marketplace list") [ -f "$S/market" ] && echo "  sessionkit" ;;
  "plugin marketplace add "*) touch "$S/market" ;;
  "plugin install "*) touch "$S/plugin" ;;
esac
exit 0
""",
    "sessionkit": LOG
    + """case "$*" in
  "setup --dry-run")
    if [ -f "$S/setup_dry_rc" ]; then echo "TODO notmuch: index the mail"; exit "$(cat "$S/setup_dry_rc")"; fi
    [ -f "$S/setup" ] && exit 0
    echo "TODO operator: make the box"; exit 1 ;;
  setup)
    printf '%s' "${PAGER-unset}" > "$S/setup_saw_pager"
    rc=$(cat "$S/setup_run_rc" 2>/dev/null || echo 0)
    echo "setup ran"
    [ "$rc" = 0 ] && touch "$S/setup"
    exit "$rc" ;;
esac
""",
    "ears": LOG
    + """case "$*" in
  backends)
    echo "nemotron  ok"
    if [ -f "$S/ears_model" ]; then echo "silero    ok: /cache/silero_vad.onnx"; else echo "silero    no model: ears install"; fi ;;
  install) touch "$S/ears_model"; echo done ;;
  "services status")
    if [ -f "$S/speech" ]; then
      printf 'mouth  running, pid 11\\nkeeper running, pid 12\\nmail   running, pid 13\\nspeech mlx-audio on :8890, pid 14\\n'
    else
      printf 'mouth  not installed\\nkeeper not installed\\nmail   not installed\\nspeech none on :8890: no listener, no mlx-audio job loaded\\n'
    fi
    # EARS-488: the stt line can say "not installed" while :8890 serves.
    [ -f "$S/stt_not_installed" ] && printf 'stt    not installed\\n'
    exit 0 ;;
  "services install "*) touch "$S/speech" ;;
esac
""",
}

# The hooks file sessionmail's verb writes; the doctor's hooks row reads it.
HOOKS_FILE = ".sessionkit/mail/settings/mail.json"
HOOKS_ON_TEXT = '{"version": 1, "hooks": true, "sendmail": "drop"}'

# The help of a pager with SM-983's verb, and of one without it (measured).
PAGER_HELP_OLD = """Usage: pager settings install | migrate [--dry-run]

  pager settings - install the mail schema; the move to ~/.session

Options:
  -h, --help  Show this message and exit.

Commands:
  install  the mail schema and template, before a launch
  migrate  [--dry-run]    a seat's old box files into its mail.json map
"""
PAGER_HELP_NEW = """Usage: pager settings install | migrate [--dry-run] | hooks [on|off]

  pager settings - install the mail schema; the move to ~/.session; hooks on|off

Options:
  -h, --help  Show this message and exit.

Commands:
  install  the mail schema and template, before a launch
  migrate  [--dry-run]    a seat's old box files into its mail.json map
  hooks    [on|off]       turn the plugin's hooks on or off; bare: say which
"""

TOOL_STUBS["pager"] = (
    LOG
    + f"""f="$HOME/{HOOKS_FILE}"
case "$*" in
  "settings --help")
    if [ -f "$S/pager_old" ]; then cat <<'HELP'
{PAGER_HELP_OLD}HELP
    else cat <<'HELP'
{PAGER_HELP_NEW}HELP
    fi
    exit 0 ;;
  "settings hooks"|"settings hooks on")
    if [ -f "$S/pager_old" ]; then
      echo "Usage: pager settings install | migrate [--dry-run]" >&2
      echo "Error: No such command 'hooks'." >&2
      exit 2
    fi ;;
esac
case "$*" in
  "settings hooks")
    if grep -q '"hooks": *true' "$f" 2>/dev/null; then
      echo "pager settings hooks: on - $f"; exit 0
    fi
    echo "pager settings hooks: off - $f"; exit 3 ;;
  "settings hooks on")
    if [ -f "$S/pager_on_rc" ]; then
      echo "pager settings hooks: refused - $f is not a JSON object; fix it by hand" >&2
      echo "a second line the installer does not show" >&2
      exit "$(cat "$S/pager_on_rc")"
    fi
    if ! grep -q '"hooks": *true' "$f" 2>/dev/null; then
      mkdir -p "$(dirname "$f")"
      echo '{HOOKS_ON_TEXT}' > "$f"
    fi
    echo "pager settings hooks: on - $f"; exit 0 ;;
esac
exit 2
"""
)

INSTALLERS = {
    "homebrew-installer": """echo "installer homebrew tty=$([ -t 0 ] && echo yes || echo no)" >> "$STUB_CALLS"
mkdir -p "$FAKE_BREW_DIR"
cp "$STUB_TOOLS/brew" "$FAKE_BREW_DIR/brew"
""",
    # Like uv's own: no shell line when ~/.local/bin is on PATH already.
    "uv-installer": """echo "installer uv PATH=$PATH" >> "$STUB_CALLS"
mkdir -p "$HOME/.local/bin"
cp "$STUB_TOOLS/uv" "$HOME/.local/bin/uv"
case ":$PATH:" in
  *":$HOME/.local/bin:"*) ;;
  *) for f in "$HOME/.zshrc" "$HOME/.profile"; do echo '. "$HOME/.local/bin/env"' >> "$f"; done ;;
esac
""",
    "claude-installer": """echo "installer claude" >> "$STUB_CALLS"
mkdir -p "$HOME/.local/bin"
cp "$STUB_TOOLS/claude" "$HOME/.local/bin/claude"
""",
}


class Result:
    def __init__(
        self, rc: int, out: str, calls: list[str], at_prompt: list[str] | None = None
    ):
        self.rc = rc
        self.out = out
        self.calls = calls
        self.at_prompt = at_prompt

    @property
    def installs(self) -> list[str]:
        return [c for c in self.calls if INSTALL_VERB.match(c)]

    def listed(self) -> list[str]:
        """The numbered list's item lines, number stripped."""
        return [
            m.group(1) for m in re.finditer(r"^ +\d+\. (.+)$", self.out, re.MULTILINE)
        ]


class FakeMac:
    def __init__(self, root: Path):
        self.root = root
        self.home = root / "home"
        self.sys = root / "sys"
        self.state = root / "state"
        self.tools = root / "tools"
        self.brew_dir = root / "opt" / "homebrew" / "bin"
        self.intel_brew_dir = root / "usr" / "local" / "bin"
        self.calls = root / "calls.log"
        self.brew_env = root / "brew-env.log"
        self.extra_env: dict[str, str] = {}
        self.brew_on_path = False
        self.local_bin_on_path = False
        for d in (self.home, self.state):
            d.mkdir(parents=True)
        for name, text in SYSTEM_STUBS.items():
            _exe(self.sys / name, "#!/bin/bash\n" + text)
        for name, text in TOOL_STUBS.items():
            _exe(self.tools / name, "#!/bin/bash\n" + text)
        for name, text in INSTALLERS.items():
            (self.tools / name).write_text(text, encoding="utf-8")
        self.script = root / "install.sh"
        self.script.write_text(
            SOURCE.replace(
                "BREW_PATHS=(/opt/homebrew/bin/brew /usr/local/bin/brew)",
                f"BREW_PATHS=({self.brew_dir}/brew {self.intel_brew_dir}/brew)",
            ),
            encoding="utf-8",
        )

    # --- what the Mac has -------------------------------------------------
    def flag(self, name: str, text: str = "") -> None:
        (self.state / name).write_text(text, encoding="utf-8")

    def with_brew(self, on_path: bool = True) -> FakeMac:
        _exe(self.brew_dir / "brew", (self.tools / "brew").read_text(encoding="utf-8"))
        self.brew_on_path = on_path
        return self

    def with_brew_set(self) -> FakeMac:
        (self.state / "brew").mkdir(exist_ok=True)
        for n in ("tmux", "ffmpeg", "notmuch"):
            (self.state / "brew" / n).touch()
        return self

    def with_local(self, *names: str) -> FakeMac:
        for n in names:
            _exe(
                self.home / ".local" / "bin" / n,
                (self.tools / n).read_text(encoding="utf-8"),
            )
        self.local_bin_on_path = True
        return self

    def with_hooks_on(self) -> FakeMac:
        p = self.home / HOOKS_FILE
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(HOOKS_ON_TEXT + "\n", encoding="utf-8")
        return self

    def hooks_on(self) -> bool:
        p = self.home / HOOKS_FILE
        return p.is_file() and '"hooks": true' in p.read_text(encoding="utf-8")

    def everything(self) -> FakeMac:
        self.with_brew().with_brew_set().with_local(
            "uv", "claude", "sessionkit", "ears", "pager"
        ).with_hooks_on()
        for f in (
            "kit",
            "setup",
            "plugin",
            "market",
            "ears_model",
            "speech",
            "speech_serving",
        ):
            self.flag(f)
        return self

    # --- running it -----------------------------------------------------
    def env(self) -> dict[str, str]:
        path = [str(self.sys)]
        if self.brew_on_path:
            path.append(str(self.brew_dir))
        if self.local_bin_on_path:
            path.append(str(self.home / ".local" / "bin"))
        path.append(SYSTEM_PATH)
        env = {
            "HOME": str(self.home),
            "PATH": ":".join(path),
            "STUB_STATE": str(self.state),
            "STUB_CALLS": str(self.calls),
            "STUB_BREW_ENV": str(self.brew_env),
            "STUB_TOOLS": str(self.tools),
            "FAKE_BREW_DIR": str(self.brew_dir),
            "NO_COLOR": "1",
            "TERM": "dumb",
            "LANG": "en_US.UTF-8",
        }
        env.update(self.extra_env)
        return env

    def brew_env_calls(self) -> list[tuple[str, str]]:
        """(HOMEBREW_NO_INSTALL_FROM_API as brew saw it, or "unset"; brew's
        args) for every brew call so far."""
        if not self.brew_env.exists():
            return []
        lines = self.brew_env.read_text(encoding="utf-8").splitlines()
        return [tuple(line.split("\t", 1)) for line in lines]

    def _calls(self) -> list[str]:
        if not self.calls.exists():
            return []
        return self.calls.read_text(encoding="utf-8").splitlines()

    def run(self, *args: str) -> Result:
        """No controlling terminal: a new session, stdin from /dev/null."""
        start = len(self._calls())
        p = subprocess.run(
            [BASH, str(self.script), *args],
            env=self.env(),
            cwd=self.root,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            start_new_session=True,
            timeout=60,
            check=False,
        )
        return Result(p.returncode, p.stdout + p.stderr, self._calls()[start:])

    def run_stdin(self, *args: str) -> Result:
        """`curl ... | bash -s -- ARGS` with no terminal at all: the script
        is bash's stdin, as under the real pipe, and /dev/tty cannot open."""
        start = len(self._calls())
        with self.script.open("rb") as stdin:
            p = subprocess.run(
                [BASH, "-s", "--", *args],
                env=self.env(),
                cwd=self.root,
                stdin=stdin,
                capture_output=True,
                start_new_session=True,
                timeout=60,
                check=False,
            )
        out = (p.stdout + p.stderr).decode("utf-8", "replace")
        return Result(p.returncode, out, self._calls()[start:])

    def tree(self) -> list[tuple[str, str, str]]:
        """The scratch root, every path but the two logs (calls.log and
        brew-env.log): its mode, and its
        symlink target or sha256. Equal before and after = nothing written."""
        rows = []
        for p in sorted(self.root.rglob("*")):
            if p in (self.calls, self.brew_env):
                continue
            rel = str(p.relative_to(self.root))
            mode = oct(p.lstat().st_mode)
            if p.is_symlink():
                rows.append((rel, mode, "-> " + os.readlink(p)))
            elif p.is_file():
                rows.append((rel, mode, hashlib.sha256(p.read_bytes()).hexdigest()))
            else:
                rows.append((rel, mode, "dir"))
        return rows

    def run_tty(self, *args: str, answers: tuple[str, ...] = ()) -> Result:
        """`cat install.sh | bash -s` on a terminal: stdin is the pipe, and
        each answer goes to the terminal when a question shows."""
        start = len(self._calls())
        pid, fd = pty.fork()
        if pid == 0:  # the child: its controlling terminal is the pty
            try:
                os.chdir(self.root)
                cmd = 'cat "$0" | "$1" -s -- "${@:2}"'
                os.execve(
                    BASH, [BASH, "-c", cmd, str(self.script), BASH, *args], self.env()
                )
            finally:
                os._exit(127)
        out = b""
        sent = 0
        at_prompt = None
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            ready, _, _ = select.select([fd], [], [], 0.1)
            if ready:
                try:
                    chunk = os.read(fd, 4096)
                except OSError:
                    break
                if not chunk:
                    break
                out += chunk
            if sent < len(answers) and out.count(b"[Y/n] ") > sent:
                if at_prompt is None:
                    at_prompt = self._calls()[start:]
                os.write(fd, answers[sent].encode() + b"\n")
                sent += 1
        os.close(fd)
        _, status = os.waitpid(pid, 0)
        text = out.decode("utf-8", "replace").replace("\r\n", "\n")
        return Result(
            os.waitstatus_to_exitcode(status), text, self._calls()[start:], at_prompt
        )
