"""A phone NAME with a space needs quotes, and the docs say so (SK-234).

Measured from sessionphone's merged origin/master (7791377): `--name` in
src/sessionphone/cli.py is a required click option, so a NAME with a space
reaches it as one argument only when the shell keeps it whole;
displayname.py documents `sessionphone setup --name "Ada Lovelace"`. The
README and INSTALL.md both show the command in a block, never in prose.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
README = (ROOT / "README.md").read_text(encoding="utf-8")
INSTALL = (ROOT / "INSTALL.md").read_text(encoding="utf-8")

SETUP = "sessionphone setup --name NAME"
SETUP_QUOTED = 'sessionphone setup --name "Ada Lovelace"'


def _bash_blocks(text: str) -> list[str]:
    return [b.strip() for b in re.findall(r"^ *```bash\n(.*?)^ *```", text, re.MULTILINE | re.DOTALL)]


def _prose(text: str) -> str:
    return re.sub(r"^ *```.*?^ *```", "", text, flags=re.MULTILINE | re.DOTALL)


def test_readme_shows_a_quoted_name_in_a_block():
    assert SETUP in _bash_blocks(README)
    assert SETUP_QUOTED in _bash_blocks(README)
    assert "A name with a space in it needs quotes" in " ".join(README.split())


def test_install_md_phone_link_command_is_in_a_block_and_says_quotes():
    assert SETUP in _bash_blocks(INSTALL)
    assert "`sessionphone setup`" not in _prose(INSTALL)
    assert "a name with a space needs quotes" in " ".join(INSTALL.split())
