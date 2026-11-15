"""Which re-declared commands scripts/command_docs.py wants a docs/<command>.md for.

The kit re-declares the phone's dc-* tools (dc-say, dc-answer, ...) so a kit
install puts them on PATH. sessionphone writes no docs/dc-*.md; its topic pages
document them. So `command_docs.py check` must not report seventeen pages
missing for them, and must still want a page for every other command.
"""

import importlib.util
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DC_TARGET = "sessionphone.dctools:main"


def _command_docs():
    spec = importlib.util.spec_from_file_location("command_docs", ROOT / "scripts" / "command_docs.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _scripts() -> dict:
    return tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]["scripts"]


def test_the_dc_tools_target_gets_no_page():
    assert _command_docs().NO_PAGE_TARGETS == {DC_TARGET}


def test_every_dc_tool_is_left_out_of_the_pages():
    dc = {name for name, target in _scripts().items() if target == DC_TARGET}
    assert len(dc) == 17
    assert all(name.startswith("dc-") for name in dc)
    assert not dc & set(_command_docs().commands())


def test_every_other_command_still_wants_a_page():
    docs = _command_docs()
    wanted = {name for name, target in _scripts().items()
              if target != DC_TARGET and name not in docs.NO_PAGE}
    assert set(docs.commands()) == wanted
    # the thirteen-minus-settled commands with a page, as docs/components.md says
    assert wanted == {"sessionkit", "message", "pager", "memory", "session", "sessionphone",
                      "sessionview", "ears", "ears-serve", "mouth", "talk", "sessionvoice-web"}


def test_every_command_with_a_page_has_one_here():
    for command in _command_docs().commands():
        assert (ROOT / "docs" / f"{command}.md").is_file(), command
