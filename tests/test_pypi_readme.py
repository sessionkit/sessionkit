"""scripts/pypi_readme.py and `make pypi-dist` (SK-140, SK-289).

README.md keeps RELATIVE links so a clone can follow them, and README.md is
also the PyPI page, where relative links 404. `make pypi-dist` builds from the
release tag, pins the staged README's links to it, and checks both dists.
`tag-check` refuses unless the local tag and the public one are the same commit.

Everything here is offline: the script runs on staged trees and synthesised
dists, and the Makefile runs in a throwaway clone with a LOCAL bare repo as
PUBLIC_REMOTE. The one end-to-end case swaps `uv build` for a stub that writes
a wheel and an sdist carrying the staged README, so no backend is fetched.
"""

from __future__ import annotations

import io
import os
import re
import shutil
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "pypi_readme.py"
GIT = shutil.which("git")
MAKE = shutil.which("make")
UV = shutil.which("uv")
REF = "v9.8.7"
# Split, as tests/test_readme.py splits it: its gate fails any shipped file
# that spells the kit's own repo URL in full.
REPO = "sessionkit/session" + "kit"
BLOB = f"https://github.com/{REPO}/blob/{REF}"
TREE = f"https://github.com/{REPO}/tree/{REF}"
RAW = f"https://raw.githubusercontent.com/{REPO}/{REF}"


def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, "-I", str(SCRIPT), *args],
                          capture_output=True, text=True, timeout=60, check=False)


@pytest.fixture
def stage(tmp_path: Path) -> Path:
    """A staged release tree: the files the README's links point at."""
    st = tmp_path / "stage"
    for rel in ("INSTALL.md", "docs/components.md", "docs/img/logo.png", "my file.md", "LICENSE"):
        (st / rel).parent.mkdir(parents=True, exist_ok=True)
        (st / rel).write_text("x\n", encoding="utf-8")
    return st


def rewrite(stage: Path, text: str, name: str = "README.md") -> tuple[subprocess.CompletedProcess[str], str]:
    readme = stage / name
    readme.parent.mkdir(parents=True, exist_ok=True)
    readme.write_text(text, encoding="utf-8")
    result = run("rewrite", "--repo", REPO, "--ref", REF,
                 "--root", str(stage), str(readme))
    return result, readme.read_text(encoding="utf-8")


# --- rewrite -----------------------------------------------------------------


@pytest.mark.parametrize(("before", "after"), [
    ("[i](INSTALL.md)", f"[i]({BLOB}/INSTALL.md)"),
    ('[i](INSTALL.md "the steps")', f'[i]({BLOB}/INSTALL.md "the steps")'),
    ("[i](./INSTALL.md#mail)", f"[i]({BLOB}/INSTALL.md#mail)"),
    ("[i](INSTALL.md?plain=1#L3)", f"[i]({BLOB}/INSTALL.md?plain=1#L3)"),
    ("[d](docs/)", f"[d]({TREE}/docs)"),
    ("[d](docs)", f"[d]({TREE}/docs)"),
    ("[s](my%20file.md)", f"[s]({BLOB}/my%20file.md)"),
    ("[s](<my file.md>)", f"[s](<{BLOB}/my file.md>)"),
    ("[r](/docs/components.md)", f"[r]({BLOB}/docs/components.md)"),
    ("![logo](docs/img/logo.png)", f"![logo]({RAW}/docs/img/logo.png)"),
    ("[install]: INSTALL.md", f"[install]: {BLOB}/INSTALL.md"),
    ("[mail]: INSTALL.md#mail-between-agents", f"[mail]: {BLOB}/INSTALL.md#mail-between-agents"),
    ('[c]: docs/components.md "Components"', f'[c]: {BLOB}/docs/components.md "Components"'),
    ("[logo]: docs/img/logo.png", f"[logo]: {RAW}/docs/img/logo.png"),
    ('<a href="LICENSE">l</a>', f'<a href="{BLOB}/LICENSE">l</a>'),
    ('<img src="docs/img/logo.png">', f'<img src="{RAW}/docs/img/logo.png">'),
    ("<img src='docs/img/logo.png'>", f"<img src='{RAW}/docs/img/logo.png'>"),
])
def test_rewrite_pins_relative_links_to_the_tag(stage: Path, before: str, after: str) -> None:
    # A reference definition starts its line; anything else sits mid-sentence.
    refdef = re.match(r"\[[^\]]+\]:", before)
    result, text = rewrite(stage, f"{before}\n" if refdef else f"see {before} here\n")
    assert result.returncode == 0, result.stderr
    assert after in text
    assert "1 link(s) rewritten" in result.stdout


@pytest.mark.parametrize("line", [
    "[manual]: #installation",
    "[top](#features)",
    "[uv](https://docs.astral.sh/uv/)",
    "[pkg]: https://github.com/sessionkit/sessionmail",
    "[me](mailto:someone@example.com)",
    "[proto](//example.com/x)",
    '<a href="#logs">logs</a>',
    "a span `[i](INSTALL.md)` stays",
    "``[i](missing.md)`` stays too",
    "[^1]: a footnote, not a link",
])
def test_rewrite_leaves_anchors_absolute_and_code_alone(stage: Path, line: str) -> None:
    result, text = rewrite(stage, line + "\n")
    assert result.returncode == 0, result.stderr
    assert text == line + "\n"
    assert "0 link(s) rewritten" in result.stdout


def test_rewrite_leaves_fenced_code_alone(stage: Path) -> None:
    body = (
        "[i](INSTALL.md)\n"
        "````md\n[x](missing.md)\n```\n[y](also-missing.md)\n````\n"
        "~~~\n[z]: missing.md\n~~~\n"
        "[after](LICENSE)\n"
    )
    result, text = rewrite(stage, body)
    assert result.returncode == 0, result.stderr
    assert text == body.replace("(INSTALL.md)", f"({BLOB}/INSTALL.md)").replace(
        "(LICENSE)", f"({BLOB}/LICENSE)")


def test_rewrite_measures_code_spans_after_the_inline_pass(stage: Path) -> None:
    """A rewritten link lengthens the line; HTML in a code span after it stays code."""
    body = '[i](INSTALL.md) then `<a href="missing.md">` in code\n'
    result, text = rewrite(stage, body)
    assert result.returncode == 0, result.stderr
    assert text == body.replace("(INSTALL.md)", f"({BLOB}/INSTALL.md)")


def test_rewrite_resolves_from_the_files_own_folder(stage: Path) -> None:
    result, text = rewrite(stage, "[up](../INSTALL.md) [here](components.md)\n", "docs/guide.md")
    assert result.returncode == 0, result.stderr
    assert text == f"[up]({BLOB}/INSTALL.md) [here]({BLOB}/docs/components.md)\n"


def test_rewrite_keeps_the_kit_readmes_shape(stage: Path) -> None:
    """The kit README's own refdefs: fragments kept, the in-page anchor untouched."""
    body = (
        "the [manual steps][manual], [mail][mail], [components][components]\n\n"
        "[install]: INSTALL.md\n[manual]: #installation\n"
        "[mail]: INSTALL.md#mail-between-agents\n[components]: docs/components.md\n"
    )
    result, text = rewrite(stage, body)
    assert result.returncode == 0, result.stderr
    assert text.splitlines()[2:] == [
        f"[install]: {BLOB}/INSTALL.md",
        "[manual]: #installation",
        f"[mail]: {BLOB}/INSTALL.md#mail-between-agents",
        f"[components]: {BLOB}/docs/components.md",
    ]
    assert "3 link(s) rewritten" in result.stdout


def test_rewrite_keeps_crlf_line_endings(stage: Path) -> None:
    readme = stage / "README.md"
    readme.write_bytes(b"[install]: INSTALL.md\r\n[i](LICENSE)\r\n")
    result = run("rewrite", "--repo", REPO, "--ref", REF,
                 "--root", str(stage), str(readme))
    assert result.returncode == 0, result.stderr
    assert readme.read_bytes() == f"[install]: {BLOB}/INSTALL.md\r\n[i]({BLOB}/LICENSE)\r\n".encode()


def test_rewrite_reaches_an_image_inside_a_link(stage: Path) -> None:
    """[![alt](logo.png)](url): the outer match swallowed the image (review do-001)."""
    body = "[![logo](docs/img/logo.png)](INSTALL.md) [![x](docs/img/logo.png)](https://e.x)\n"
    result, text = rewrite(stage, body)
    assert result.returncode == 0, result.stderr
    assert text == (f"[![logo]({RAW}/docs/img/logo.png)]({BLOB}/INSTALL.md) "
                    f"[![x]({RAW}/docs/img/logo.png)](https://e.x)\n")
    assert "3 link(s) rewritten" in result.stdout


# --- rewrite refuses -----------------------------------------------------------


@pytest.mark.parametrize(("link", "why"), [
    ("[gone](NOPE.md)", "not in the release tree: NOPE.md"),
    ("[gone]: docs/nope.md#x", "not in the release tree: docs/nope.md#x"),
    ('<img src="docs/img/nope.png">', "not in the release tree: docs/img/nope.png"),
    ("[out](../outside.md)", "climbs out of the repo: ../outside.md"),
    ("[out](docs/../../outside.md)", "climbs out of the repo: docs/../../outside.md"),
    ("[out](%2e%2e/outside.md)", "climbs out of the repo: %2e%2e/outside.md"),
    # GitHub is case-sensitive; a macOS disk is not, and must not pass it (review do-001).
    ("[case](install.md)", "not in the release tree: install.md"),
    ("[case](Docs/components.md)", "not in the release tree: Docs/components.md"),
])
def test_rewrite_refuses_and_writes_nothing(stage: Path, link: str, why: str) -> None:
    (stage.parent / "outside.md").write_text("x\n", encoding="utf-8")  # exists, but outside
    body = f"[ok](INSTALL.md)\n{link}\n"
    result, text = rewrite(stage, body)
    assert result.returncode == 1
    assert why in result.stderr
    assert "nothing written" in result.stderr
    assert text == body  # untouched: not even the good link is rewritten


def test_rewrite_refuses_a_symlink_out_of_the_stage(stage: Path) -> None:
    (stage.parent / "secret.md").write_text("x\n", encoding="utf-8")
    (stage / "link.md").symlink_to(stage.parent / "secret.md")
    body = "[s](link.md)\n"
    result, text = rewrite(stage, body)
    assert result.returncode == 1
    assert "climbs out of the repo (symlink): link.md" in result.stderr
    assert text == body


def test_rewrite_refuses_a_file_outside_its_root(stage: Path, tmp_path: Path) -> None:
    other = tmp_path / "README.md"
    other.write_text("[i](INSTALL.md)\n", encoding="utf-8")
    result = run("rewrite", "--repo", REPO, "--ref", REF,
                 "--root", str(stage), str(other))
    assert result.returncode == 1
    assert "is not inside --root" in result.stderr
    assert other.read_text(encoding="utf-8") == "[i](INSTALL.md)\n"


# --- check ---------------------------------------------------------------------


def metadata(body: str) -> str:
    return ("Metadata-Version: 2.4\nName: sessionkit\nVersion: 9.8.7\n"
            "Description-Content-Type: text/markdown\n\n" + body)


def wheel(path: Path, body: str) -> Path:
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("sessionkit/__init__.py", "")
        z.writestr("sessionkit-9.8.7.dist-info/METADATA", metadata(body))
    return path


def sdist(path: Path, body: str) -> Path:
    with tarfile.open(path, "w:gz") as t:
        for name, text in (("sessionkit-9.8.7/PKG-INFO", metadata(body)),
                           ("sessionkit-9.8.7/src/sessionkit/PKG-INFO", metadata("[x](rel.md)\n"))):
            data = text.encode()
            info = tarfile.TarInfo(name)
            info.size = len(data)
            t.addfile(info, io.BytesIO(data))
    return path


CLEAN = f"[i]: {BLOB}/INSTALL.md\n[manual]: #installation\n`[x](code.md)`\n"
DIRTY = CLEAN + "[left](docs/components.md)\n"


def test_check_sees_an_image_inside_a_link(tmp_path: Path) -> None:
    w = wheel(tmp_path / "sessionkit-9.8.7-py3-none-any.whl",
              CLEAN + "[![logo](docs/img/logo.png)](https://e.x)\n")
    result = run("check", str(w))
    assert result.returncode == 1
    assert "1 relative link(s): ['docs/img/logo.png']" in result.stdout


def test_check_passes_a_clean_wheel_and_sdist(tmp_path: Path) -> None:
    w = wheel(tmp_path / "sessionkit-9.8.7-py3-none-any.whl", CLEAN)
    s = sdist(tmp_path / "sessionkit-9.8.7.tar.gz", CLEAN)
    result = run("check", str(w), str(s))
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.count(": 0 relative link(s)") == 2


@pytest.mark.parametrize("kind", ["whl", "sdist"])
def test_check_fails_a_relative_link_left(tmp_path: Path, kind: str) -> None:
    good = wheel(tmp_path / "good-py3-none-any.whl", CLEAN)
    bad = (wheel(tmp_path / "sessionkit-9.8.7-py3-none-any.whl", DIRTY) if kind == "whl"
           else sdist(tmp_path / "sessionkit-9.8.7.tar.gz", DIRTY))
    result = run("check", str(good), str(bad))
    assert result.returncode == 1
    assert f"{bad.name}: 1 relative link(s): ['docs/components.md']" in result.stdout


def test_check_fails_a_dist_with_no_description(tmp_path: Path) -> None:
    empty = tmp_path / "sessionkit-9.8.7-py3-none-any.whl"
    with zipfile.ZipFile(empty, "w") as z:
        z.writestr("sessionkit/__init__.py", "")
    result = run("check", str(empty))
    assert result.returncode == 1
    assert "cannot read the description" in result.stderr


# --- tag-check (SK-289) --------------------------------------------------------
# The public side is ALWAYS a local bare repo: nothing here touches a network host.

needs_git = pytest.mark.skipif(GIT is None, reason="git is needed")


@pytest.fixture
def tagged(tmp_path: Path) -> tuple[Path, Path, str, str]:
    """A repo with two commits, A and B, and an empty bare repo as the public one."""
    repo = tmp_path / "work"
    repo.mkdir()
    git(repo, "init", "-q")
    git(repo, "commit", "-q", "--allow-empty", "-m", "A")
    a = git(repo, "rev-parse", "HEAD").strip()
    git(repo, "commit", "-q", "--allow-empty", "-m", "B")
    b = git(repo, "rev-parse", "HEAD").strip()
    bare = tmp_path / "public.git"
    git(tmp_path, "init", "-q", "--bare", str(bare))
    return repo, bare, a, b


def tag_check(repo: Path, remote: Path | str, tag: str = REF) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, "-I", str(SCRIPT), "tag-check", "--tag", tag,
                           "--remote", str(remote)], cwd=repo, capture_output=True, text=True,
                          timeout=60, check=False)


@needs_git
@pytest.mark.parametrize("annotated", [True, False], ids=["annotated", "lightweight"])
def test_tag_check_passes_the_same_commit(tagged, annotated: bool) -> None:
    repo, bare, a, _ = tagged
    git(repo, "tag", *(["-a", "-m", "release"] if annotated else []), REF, a)
    git(repo, "push", "-q", str(bare), f"refs/tags/{REF}")
    listing = git(repo, "ls-remote", str(bare))
    # An annotated tag lists the TAG object, then the commit as ^{}: the check
    # must peel to the commit, or it would refuse every annotated release.
    assert (f"refs/tags/{REF}^{{}}" in listing) is annotated
    result = tag_check(repo, bare)
    assert result.returncode == 0, result.stderr
    assert result.stdout == f"pypi_readme tag-check: {REF} is {a} here and on {bare}\n"
    assert result.stderr == ""


@needs_git
@pytest.mark.parametrize("annotated", [True, False], ids=["annotated", "lightweight"])
def test_tag_check_refuses_a_moved_local_tag_naming_both_shas(tagged, annotated: bool) -> None:
    repo, bare, a, b = tagged
    opts = ["-a", "-m", "release"] if annotated else []
    git(repo, "tag", *opts, REF, a)
    git(repo, "push", "-q", str(bare), f"refs/tags/{REF}")
    git(repo, "tag", "-f", *opts, REF, b)  # the local tag moves; the public one does not
    result = tag_check(repo, bare)
    assert result.returncode == 1
    assert result.stdout == ""
    assert result.stderr.count("\n") == 1  # one line
    assert f"tag {REF} differs: local {b}, public {a} on {bare}" in result.stderr


@needs_git
def test_tag_check_refuses_a_missing_public_tag(tagged) -> None:
    repo, bare, a, _ = tagged
    git(repo, "tag", REF, a)
    git(repo, "push", "-q", str(bare), "HEAD:refs/heads/master")  # the branch, not the tag
    result = tag_check(repo, bare)
    assert result.returncode == 1
    assert result.stderr == (f"pypi_readme tag-check: tag {REF} is not on {bare}; "
                             "push the tag to the public repo first\n")


@needs_git
def test_tag_check_refuses_a_missing_local_tag(tagged) -> None:
    repo, bare, a, _ = tagged
    git(repo, "push", "-q", str(bare), f"{a}:refs/tags/{REF}")  # public only
    result = tag_check(repo, bare)
    assert result.returncode == 1
    assert result.stderr == f"pypi_readme tag-check: tag {REF} is not in this repo; tag the release first\n"


@needs_git
def test_tag_check_ignores_a_tag_whose_name_only_ends_the_same(tagged) -> None:
    repo, bare, a, b = tagged
    git(repo, "tag", REF, a)
    # ls-remote matches patterns by their tail, so this ref is listed too.
    git(repo, "push", "-q", str(bare), f"{b}:refs/tags/x/refs/tags/{REF}")
    result = tag_check(repo, bare)
    assert result.returncode == 1
    assert f"tag {REF} is not on {bare}" in result.stderr


@needs_git
def test_tag_check_refuses_an_unreachable_remote_with_gits_reason(tagged, tmp_path: Path) -> None:
    repo, _, a, _ = tagged
    git(repo, "tag", REF, a)
    gone = tmp_path / "no-such.git"
    result = tag_check(repo, gone)
    assert result.returncode == 1
    assert result.stderr.count("\n") == 1
    assert f"pypi_readme tag-check: cannot read {REF} from {gone}: " in result.stderr
    assert "no-such.git" in result.stderr.partition(": cannot read")[2].partition(": ")[2]


# --- the Makefile --------------------------------------------------------------


def test_publish_builds_through_pypi_dist() -> None:
    text = (ROOT / "Makefile").read_text(encoding="utf-8")
    assert re.search(r"^publish: pypi-dist\s+##", text, re.MULTILINE)
    assert re.search(r"^PUBLIC_REMOTE \?= https://github\.com/sessionkit/sessionkit\.git$", text, re.MULTILINE)
    assert re.search(r"^PYPI_README \?= python3 scripts/pypi_readme\.py$", text, re.MULTILINE)
    phony = re.search(r"^\.PHONY: (.*)$", text, re.MULTILINE)
    assert phony and "pypi-dist" in phony.group(1).split()
    assert re.search(r"^pypi-dist:.*## ", text, re.MULTILINE)


needs_tools = pytest.mark.skipif(GIT is None or MAKE is None or UV is None,
                                 reason="git, make and uv are needed")

# A stand-in for `uv build`: writes a wheel and an sdist whose long description
# is the README in the folder it runs in, as a real backend would. `uv version`
# goes to the real uv, which only reads pyproject.toml.
STUB_UV = """#!{python}
import io, os, sys, tarfile, tomllib, zipfile
args = sys.argv[1:]
if args[:1] == ["version"]:
    os.execv({uv!r}, [{uv!r}, *args])
assert args[0] == "build" and args[1] == "--out-dir", args
out = args[2]; os.makedirs(out, exist_ok=True)
v = tomllib.load(open("pyproject.toml", "rb"))["project"]["version"]
meta = "Metadata-Version: 2.4\\nName: sessionkit\\nVersion: " + v + "\\n\\n" + open("README.md").read()
with zipfile.ZipFile(os.path.join(out, f"sessionkit-{{v}}-py3-none-any.whl"), "w") as z:
    z.writestr(f"sessionkit-{{v}}.dist-info/METADATA", meta)
with tarfile.open(os.path.join(out, f"sessionkit-{{v}}.tar.gz"), "w:gz") as t:
    data = meta.encode(); info = tarfile.TarInfo(f"sessionkit-{{v}}/PKG-INFO"); info.size = len(data)
    t.addfile(info, io.BytesIO(data))
print("stub uv build:", os.getcwd())
"""


def git(cwd: Path, *args: str) -> str:
    env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.com",
           "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.com"}
    return subprocess.run([str(GIT), "-c", "commit.gpgsign=false", "-c", "tag.gpgsign=false",
                           *args], cwd=cwd, env=env, check=True, capture_output=True,
                          text=True, timeout=120).stdout


@pytest.fixture
def clone(tmp_path: Path) -> tuple[Path, Path, str]:
    """A throwaway clone carrying this working tree's Makefile and script, a tag
    for its version made locally, and an EMPTY bare repo as the public one."""
    repo = tmp_path / "clone"
    git(tmp_path, "clone", "-q", "--no-hardlinks", str(ROOT), str(repo))
    for rel in ("Makefile", "scripts/pypi_readme.py"):
        shutil.copy2(ROOT / rel, repo / rel)
    git(repo, "add", "Makefile", "scripts/pypi_readme.py")
    git(repo, "commit", "-q", "--allow-empty", "-m", "overlay: the code under test")
    version = re.search(r'^version = "([^"]+)"', (repo / "pyproject.toml").read_text(), re.MULTILINE).group(1)
    git(repo, "tag", f"v{version}")
    bare = tmp_path / "public.git"
    git(tmp_path, "init", "-q", "--bare", str(bare))
    return repo, bare, version


def make(repo: Path, bare: Path, stub: Path | None = None) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "UV_OFFLINE": "1"}
    if stub is not None:
        env["PATH"] = f"{stub}{os.pathsep}{env['PATH']}"
    return subprocess.run([str(MAKE), "-C", str(repo), "--no-print-directory", "pypi-dist",
                           f"PUBLIC_REMOTE={bare}"], env=env, capture_output=True, text=True,
                          timeout=300, check=False)


@needs_tools
def test_pypi_dist_refuses_when_the_tag_is_not_on_the_public_repo(clone) -> None:
    repo, bare, version = clone
    git(repo, "push", "-q", str(bare), "HEAD:refs/heads/master")  # the branch, not the tag
    result = make(repo, bare)
    assert result.returncode != 0
    assert (f"pypi_readme tag-check: tag v{version} is not on {bare}; "
            "push the tag to the public repo first") in result.stderr
    assert not (repo / "dist").exists()  # nothing built


@needs_tools
def test_pypi_dist_refuses_a_local_tag_moved_off_the_public_one(clone) -> None:
    repo, bare, version = clone
    tag = f"v{version}"
    git(repo, "push", "-q", str(bare), f"refs/tags/{tag}")
    public = git(repo, "rev-parse", f"{tag}^{{commit}}").strip()
    git(repo, "commit", "-q", "--allow-empty", "-m", "after the public tag")
    git(repo, "tag", "-f", tag)  # the local tag moves; the public one does not
    local = git(repo, "rev-parse", f"{tag}^{{commit}}").strip()
    result = make(repo, bare)
    assert result.returncode != 0
    assert f"tag {tag} differs: local {local}, public {public} on {bare}" in result.stderr
    assert not (repo / "dist").exists()  # nothing built


@needs_tools
def test_pypi_dist_builds_from_the_tag_and_checks_both_dists(clone, tmp_path: Path) -> None:
    repo, bare, version = clone
    git(repo, "push", "-q", str(bare), f"refs/tags/v{version}")
    stub = tmp_path / "stub"
    stub.mkdir()
    (stub / "uv").write_text(STUB_UV.format(python=sys.executable, uv=UV), encoding="utf-8")
    (stub / "uv").chmod(0o755)
    # An uncommitted edit in the checkout must not reach the dists.
    readme = repo / "README.md"
    readme.write_text(readme.read_text(encoding="utf-8") + "\nCHECKOUT-ONLY [x](nope.md)\n",
                      encoding="utf-8")
    before = readme.read_bytes()
    status = git(repo, "status", "--porcelain")

    result = make(repo, bare, stub)

    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.count(": 0 relative link(s)") == 2
    assert readme.read_bytes() == before  # the checkout's README is never rewritten
    assert git(repo, "status", "--porcelain") == status  # dist/ is ignored; nothing else moved
    whl = repo / "dist" / f"sessionkit-{version}-py3-none-any.whl"
    with zipfile.ZipFile(whl) as z:
        body = z.read(f"sessionkit-{version}.dist-info/METADATA").decode()
    blob = f"https://github.com/{REPO}/blob/v{version}"
    assert "CHECKOUT-ONLY" not in body  # built from the tag
    assert f"[install]: {blob}/INSTALL.md\n" in body
    assert f"[mail]: {blob}/INSTALL.md#mail-between-agents\n" in body
    assert f"[components]: {blob}/docs/components.md\n" in body
    assert "[manual]: #installation\n" in body
    assert (repo / "dist" / f"sessionkit-{version}.tar.gz").exists()
