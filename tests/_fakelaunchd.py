"""A fake launchctl for `sessionkit service`: scripted answers, argv logged.

`FakeLaunchd(tmp)` writes an executable, `launchctl`, and a JSON state file
beside it. The CLI runs it through the SESSIONKIT_LAUNCHCTL seam
(`fake.env()`), so no test reaches the real launchd. It answers:

- `list`: the header, then one `PID Status Label` row per job in `jobs`
  (`-` for a pid or status of None). The forms copy a real Mac's: `-`, `0`,
  `3` and `-15`.
- `print gui/<uid>/<label>`: the text in `printed[label]`, else launchd's
  "Could not find service" and exit 113.
- `kickstart -k gui/<uid>/<label>`: exit `kickstart_rc[label]` (default 0),
  with `kickstart_words[label]` on stderr.
- any verb named in `rc` exits that number instead, with launchd's words for
  error 125 when the number is 125.

Every call appends its argv, one JSON list per line, to calls.log.
"""

from __future__ import annotations

import json
import stat
import sys
from pathlib import Path

SCRIPT = r"""#!{python}
import json, sys
from pathlib import Path
here = Path(__file__).resolve().parent
state = json.loads((here / "state.json").read_text())
args = sys.argv[1:]
with open(here / "calls.log", "a") as f:
    f.write(json.dumps(args) + "\n")
verb = args[0] if args else ""
rc = state.get("rc", {{}}).get(verb)
if rc is not None:
    if rc == 125:
        sys.stderr.write("Could not print domain: 125: Domain does not support specified action\n")
    else:
        sys.stderr.write(f"{{verb}} failed: {{rc}}\n")
    sys.exit(rc)
if verb == "list":
    print("PID\tStatus\tLabel")
    for pid, status, label in state.get("jobs", []):
        print(f"{{'-' if pid is None else pid}}\t{{'-' if status is None else status}}\t{{label}}")
    sys.exit(0)
label = args[-1].split("/", 2)[-1] if args else ""
if verb == "print":
    text = state.get("printed", {{}}).get(label)
    if text is None:
        sys.stderr.write(f'Could not find service "{{label}}" in domain for port\n')
        sys.exit(113)
    print(text)
    sys.exit(0)
if verb == "kickstart":
    words = state.get("kickstart_words", {{}}).get(label)
    if words:
        sys.stderr.write(words + "\n")
    sys.exit(state.get("kickstart_rc", {{}}).get(label, 0))
sys.stderr.write(f"fake launchctl: no answer for {{args}}\n")
sys.exit(64)
"""


class FakeLaunchd:
    def __init__(self, tmp: Path) -> None:
        self.dir = tmp / "fakelaunchd"
        self.dir.mkdir(parents=True, exist_ok=True)
        self.program = self.dir / "launchctl"
        self.program.write_text(SCRIPT.format(python=sys.executable), encoding="utf-8")
        self.program.chmod(self.program.stat().st_mode | stat.S_IXUSR)
        self.state: dict = {"jobs": [], "printed": {}, "kickstart_rc": {}, "rc": {}}
        self.save()

    def save(self) -> None:
        (self.dir / "state.json").write_text(json.dumps(self.state), encoding="utf-8")

    def job(
        self, label: str, pid: int | None = None, status: int | None = 0
    ) -> FakeLaunchd:
        self.state["jobs"].append([pid, status, label])
        self.save()
        return self

    def printed(self, label: str, text: str) -> FakeLaunchd:
        self.state["printed"][label] = text
        self.save()
        return self

    def fail(self, verb: str, rc: int) -> FakeLaunchd:
        self.state["rc"][verb] = rc
        self.save()
        return self

    def kickstart_fails(self, label: str, rc: int, words: str) -> FakeLaunchd:
        self.state["kickstart_rc"][label] = rc
        self.state.setdefault("kickstart_words", {})[label] = words
        self.save()
        return self

    def env(self) -> dict[str, str]:
        return {"SESSIONKIT_LAUNCHCTL": str(self.program)}

    def calls(self) -> list[list[str]]:
        log = self.dir / "calls.log"
        if not log.exists():
            return []
        return [json.loads(line) for line in log.read_text().splitlines()]

    def verbs(self, verb: str) -> list[list[str]]:
        return [c for c in self.calls() if c and c[0] == verb]
