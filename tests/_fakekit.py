"""A fake ~/.sessionkit tree and ~/Library/LaunchAgents, in a scratch HOME.

`FakeKit(tmp)` makes a HOME. `service(package, name, **fields)` writes
`<package>/services/<name>.json` (`agent_dir=` puts it one folder down, as
per-agent services are); the defaults make a valid launchd service whose
label is `dev.sessionkit.<package>.<name>`. `plist(label, **keys)` writes a
plist the way an owner's install would. Tests set HOME to `kit.home`, so
nothing reads or writes the real home. Names are invented: alpha, beta.
"""

from __future__ import annotations

import json
import plistlib
from pathlib import Path

PREFIX = "dev.sessionkit."


class FakeKit:
    def __init__(self, tmp: Path) -> None:
        self.home = tmp / "home"
        self.root = self.home / ".sessionkit"
        self.agents = self.home / "Library" / "LaunchAgents"
        self.root.mkdir(parents=True)
        self.agents.mkdir(parents=True)

    def service(
        self, package: str, name: str, /, agent_dir: str | None = None, **fields
    ) -> Path:
        data = {
            "service": 1,
            "name": name,
            "label": f"{PREFIX}{package}.{name}",
            "enabled": True,
            "install": f"{package}-tool install {name}",
        }
        data.update(fields)
        for key in [k for k, v in data.items() if v is DROP]:
            del data[key]
        folder = self.root / package / "services"
        stem = name
        if agent_dir:
            folder = folder / agent_dir
            stem = data.get("agent", name.rsplit(".", 1)[-1])
        return self.raw(folder / f"{stem}.json", json.dumps(data))

    def raw(self, path: Path, text: str) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def plist(self, label: str, **keys) -> Path:
        data = {"Label": label, "ProgramArguments": ["/usr/bin/true"]}
        data.update(keys)
        path = self.agents / f"{label}.plist"
        with path.open("wb") as f:
            plistlib.dump(data, f)
        return path


DROP = object()  # a field value that removes the key
