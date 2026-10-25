"""What a call needs on a Mac, said the same way in README.md and INSTALL.md.

Ruled by the owner: on a Mac, a call needs Homebrew by default, then
`brew install ffmpeg`, then the speech server, then the phone link. No
Homebrew is the workaround case: one neutral line, never taught. The ruling
is about calls only, so the base kit's "Homebrew or at least Apple's Command
Line Tools" item stays as it was, and tmux and notmuch are not made
requirements.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
README = (ROOT / "README.md").read_text(encoding="utf-8")
INSTALL = (ROOT / "INSTALL.md").read_text(encoding="utf-8")

FFMPEG = "brew install ffmpeg"
SPEECH = "ears services install --only speech"
WORKAROUND = "A call without Homebrew is the workaround case. This guide does not cover it."

# The base kit's Homebrew item, word for word as it stood before the ruling.
BASE_ITEM = """\
- [Homebrew][brew] or at least Apple's Command Line Tools. Homebrew
  installs the Command Line Tools for you ([prerequisites][prereqs]), and
  the kit needs two of their tools: the plugin lines clone with git, and the
  ears build a Swift helper with `swiftc`.
  - Have Homebrew: nothing to run. It installed the Command Line Tools.
  - No Homebrew: get the Command Line Tools alone.

    ```bash
    xcode-select --install
    ```
"""


def _flat(text: str) -> str:
    return " ".join(text.split())


def _blocks(text: str) -> list[tuple[int, str]]:
    """Each fenced bash block, as (offset of its fence, its stripped body)."""
    return [
        (m.start(), m.group(1).strip())
        for m in re.finditer(r"^ *```bash\n(.*?)^ *```", text, re.MULTILINE | re.DOTALL)
    ]


def _readme_section(title: str) -> str:
    match = re.search(rf"^## {re.escape(title)}\n(.*?)(?=^## |\Z)", README, re.MULTILINE | re.DOTALL)
    assert match, title
    return match.group(1)


def _install_section(n: int) -> str:
    start = INSTALL.index(f"## {n}. ")
    end = INSTALL.find(f"## {n + 1}. ", start)
    return INSTALL[start:end if end != -1 else None]


def _requirements() -> str:
    """README's "You need:" list, up to the kit's own install block."""
    install = _readme_section("Installation")
    return install[install.index("You need:"):install.index("Then install the kit:")]


def _call_item(text: str) -> str:
    """The list item that starts "- For a call on a Mac:", to the next item."""
    start = text.index("- For a call on a Mac:")
    nxt = re.search(r"^- ", text[start + 2:], re.MULTILINE)
    return text[start:start + 2 + nxt.start()] if nxt else text[start:]


def _ffmpeg_block_offsets(text: str) -> list[int]:
    return [at for at, body in _blocks(text) if body == FFMPEG]


def test_readme_and_install_each_give_brew_install_ffmpeg_in_a_block():
    for name, doc in (("README.md", README), ("INSTALL.md", INSTALL)):
        assert _ffmpeg_block_offsets(doc), name
        # Never as a command inside a sentence.
        assert f"`{FFMPEG}`" not in doc, name


def test_readme_call_item_is_in_the_list_with_homebrew_before_ffmpeg():
    req = _requirements()
    item = _call_item(req)
    # A list item after the base items, never prose.
    assert req.index("- uv.") < req.index("- For a call on a Mac:")
    assert item.index("[Homebrew][brew]") < item.index(FFMPEG)
    assert [body for _, body in _blocks(item)] == [FFMPEG]
    assert "the speech server, then link the phone" in _flat(item)
    assert _flat(item).count("workaround") == 1
    assert WORKAROUND in _flat(item)


def test_readme_phone_path_is_homebrew_then_ffmpeg_then_the_speech_server():
    install = _readme_section("Installation")
    phone = install[install.index("- **The speech server comes before the phone.**"):]
    path = phone[phone.index("  - A phone:"):phone.index("  - Then link the phone.")]
    assert path.index("Homebrew") < path.index(FFMPEG) < path.index(SPEECH)
    order = [body for _, body in _blocks(path)]
    assert order == [FFMPEG, SPEECH], order


def test_install_section_1_has_the_call_item_after_homebrew():
    prereqs = _install_section(1)
    item = _call_item(prereqs)
    assert prereqs.index("- Homebrew, the installer from") < prereqs.index("- For a call on a Mac:")
    assert [body for _, body in _blocks(item)] == [FFMPEG]
    assert "the speech server, then link the phone (section 6)" in _flat(item)
    assert WORKAROUND in _flat(item)
    # Not timed, so not labelled MEASURED.
    assert "MEASURED" not in item


def test_install_section_6_gives_the_call_steps_in_order():
    optional = _install_section(6)
    phone = optional[optional.index("- **Your phone."):optional.index("- **Apple speech.")]
    homebrew = phone.index("  - **Homebrew first**, from section 1.")
    ffmpeg = _ffmpeg_block_offsets(phone)
    speech = [at for at, body in _blocks(phone) if body == SPEECH]
    link = phone.index("    - Then link the phone.")
    assert len(ffmpeg) == 1 and len(speech) == 1
    assert homebrew < ffmpeg[0] < phone.index("  - **Then the speech server") < speech[0] < link
    # The old one-line prose form is gone.
    assert "A call also needs `ffmpeg` from Homebrew" not in phone
    assert WORKAROUND in _flat(phone)


def test_each_doc_puts_ffmpeg_after_homebrew_and_before_the_speech_server():
    for name, doc in (("README.md", README), ("INSTALL.md", INSTALL)):
        first_brew = doc.index("Homebrew")
        speech = [at for at, body in _blocks(doc) if body == SPEECH]
        for at in _ffmpeg_block_offsets(doc):
            assert first_brew < at, name
            later = [s for s in speech if s > at]
            assert later, (name, "no speech-server step after an ffmpeg block")


def test_the_base_homebrew_item_is_unchanged():
    assert BASE_ITEM in _requirements()


def test_the_call_items_name_no_tmux_or_notmuch():
    for name, item in (("README.md", _call_item(_requirements())), ("INSTALL.md", _call_item(_install_section(1)))):
        for tool in ("tmux", "notmuch"):
            assert tool not in item, (name, tool)
