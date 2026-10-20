"""The draft overview page under site/: static, self-contained, honest.

These pin the page's SHAPE, not its words: no script, no request that leaves
the folder, links that resolve (inside site/, and the ../ docs it reaches),
an install line that is the README's own, and no maintainers' notes in what
ships.
"""

from __future__ import annotations

import re
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
PAGES = sorted(SITE.rglob("*.html"))
TEXT_FILES = sorted(p for p in SITE.rglob("*") if p.is_file())

# The step-by-step install doc at the repo root, by its own name, so the
# check follows a rename and the name is never written out here.
INSTALL_DOCS = sorted(p.name for p in ROOT.glob("*INSTALL*.md"))


class _Links(HTMLParser):
    """Collect every href and src, and the text of #install-line."""

    def __init__(self) -> None:
        super().__init__()
        self.urls: list[str] = []
        self.scripts = 0
        self.handlers: list[str] = []
        self.install_line = ""
        self._in_install = False

    def handle_starttag(self, tag, attrs):
        if tag == "script":
            self.scripts += 1
        for name, value in attrs:
            if name in ("href", "src") and value is not None:
                self.urls.append(value)
            if name.startswith("on"):
                self.handlers.append(name)
            if name == "id" and value == "install-line":
                self._in_install = True

    def handle_endtag(self, tag):
        if tag == "code":
            self._in_install = False

    def handle_data(self, data):
        if self._in_install:
            self.install_line += data


def _parse(page: Path) -> _Links:
    parser = _Links()
    parser.feed(page.read_text())
    return parser


def _installation_section(readme: str) -> str:
    match = re.search(
        r"^## Installation\n(.*?)(?=^## |\Z)", readme, re.MULTILINE | re.DOTALL
    )
    assert match, "README has no '## Installation' section"
    return match.group(1)


def test_the_overview_page_exists():
    assert (SITE / "index.html").is_file()
    assert (SITE / "style.css").is_file()
    assert PAGES, "no HTML pages under site/"


def test_no_script_and_no_inline_handlers():
    for page in PAGES:
        links = _parse(page)
        assert links.scripts == 0, f"{page.name}: <script> found"
        assert not links.handlers, f"{page.name}: inline handlers {links.handlers}"


def test_no_absolute_or_protocol_relative_url():
    for page in PAGES:
        for url in _parse(page).urls:
            assert not re.match(r"^([a-z][a-z0-9+.-]*:|//)", url, re.IGNORECASE), (
                f"{page.name}: {url!r} leaves the folder"
            )


def test_no_url_anywhere_in_the_css():
    for css in SITE.rglob("*.css"):
        text = css.read_text()
        assert "url(" not in text, f"{css.name}: url() fetches something"
        assert "@import" not in text, f"{css.name}: @import fetches something"


def test_every_link_inside_site_resolves():
    for page in PAGES:
        for url in _parse(page).urls:
            path = url.split("#", 1)[0]
            if not path:
                continue  # in-page anchor
            target = (page.parent / path).resolve()
            if path.endswith("/"):
                target = target / "index.html"
            assert target.is_file(), f"{page.name}: {url!r} does not resolve"


def test_install_line_is_the_readmes():
    line = _parse(SITE / "index.html").install_line.strip()
    assert line.startswith("uv tool install "), line
    section = _installation_section((ROOT / "README.md").read_text())
    readme_lines = {re.sub(r"\s+#.*$", "", raw).strip() for raw in section.splitlines()}
    assert line in readme_lines, f"{line!r} is not in README's Installation"


def test_no_install_doc_filename_anywhere_in_site():
    assert INSTALL_DOCS, "no install doc at the repo root to guard against"
    for path in TEXT_FILES:
        text = path.read_text()
        for name in INSTALL_DOCS:
            assert name not in text, f"{path.relative_to(ROOT)} names {name}"
            assert name.rsplit(".", 1)[0] not in text, (
                f"{path.relative_to(ROOT)} names {name}"
            )


def test_no_internal_notes_in_what_ships():
    # The page and its README ship in the release archive. Notes for the
    # maintainers (pending-item codes, decision codes, a DRAFT label on the
    # README's title) mislead a stranger who reads them there.
    for path in TEXT_FILES:
        text = path.read_text()
        name = path.relative_to(ROOT)
        assert not re.search(r"pending P\d", text), f"{name}: a pending-item note"
        assert not re.search(r"\(D\d+\)", text), f"{name}: a decision code"
        assert "lands with its merge" not in text, f"{name}: a stale mark"
    title = (SITE / "README.md").read_text().splitlines()[0]
    assert "DRAFT" not in title, title
