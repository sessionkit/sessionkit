"""The family install (SK-8 A1-A5): the kit's pyproject and plugin manifests.

These pin the SHAPE of the kit, not the children's code: the five children
are dependencies, held to the ruled list by tests/test_dependency_gate.py
(the list itself is tests/_ruled_deps.py); every child command is re-declared under
[project.scripts]; the plugin depends on the five; the marketplace lists the
kit plus the five, and nothing else (no voicemode: D11 is unruled).
"""
from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path

from _ruled_deps import FAMILY

ROOT = Path(__file__).resolve().parent.parent

# Each child's [project.scripts], measured from its 0.3.0 wheel, by wheel sha256:
# mail 8e4d9476, tools 8d089699, phone ac402a39, view 3942f119, voice ebc1b65c.
CHILD_SCRIPTS = {
    "message": "sessionmail.message:cli",
    "pager": "sessionmail.pager:cli",
    "memory": "sessionmail.memory:cli",
    "session": "sessiontools.cli:main",
    "sessionphone": "sessionphone.cli:main",
    "sessionview": "sessionview:main",
    "sessionview-config": "sessionview:main",
    "sessionview-session": "sessionview:main",
    "sessionview-messages": "sessionview:main",
    "ears": "ears.cli:main",
    "ears-serve": "ears.serve:main",
    "mouth": "mouth.__main__:main",
    "talk": "talk.cli:main",
}


def _pyproject() -> dict:
    return tomllib.loads((ROOT / "pyproject.toml").read_text())


def _json(name: str) -> dict:
    return json.loads((ROOT / ".claude-plugin" / name).read_text())


def test_floor_comment_sits_beside_the_dependencies() -> None:
    text = (ROOT / "pyproject.toml").read_text()
    block = text.split("dependencies = [", 1)[0].rsplit("requires-python", 1)[1]
    assert "Floored at 0.3.0" in block
    assert "0.1.0 alphas" in block


def test_pypi_page_carries_the_readme() -> None:
    # SK-88: with no readme field the metadata has no long_description, so
    # `twine check --strict` fails and the PyPI page is blank.
    project = _pyproject()["project"]
    assert project["readme"] == "README.md"
    assert (ROOT / project["readme"]).is_file()


def test_version_at_least_the_d2_alpha() -> None:
    project = _pyproject()["project"]
    # D2: alpha ships as 0.1.0; never back to the 0.0.1 name placeholder.
    version = tuple(int(part) for part in project["version"].split(".")[:3])
    assert version >= (0, 1, 0), project["version"]


# The kit's release metadata, from 0.2.0 on:
# one author and one home, the same in pyproject and in both
# plugin manifests. The version is set in pyproject and mirrored, never drifted.
AUTHOR = {"name": "Mike Bailey", "email": "mike@sessionkit.ai"}
HOME = "https://github.com/sessionkit/sessionkit"


def test_release_metadata_in_pyproject() -> None:
    project = _pyproject()["project"]
    assert project["authors"] == [AUTHOR]
    assert "Development Status :: 3 - Alpha" in project["classifiers"]
    assert not [c for c in project["classifiers"] if c.startswith("Development Status :: 1")]
    assert project["urls"] == {"Homepage": HOME, "Repository": HOME}


def test_plugin_manifests_mirror_the_pyproject_version() -> None:
    version = _pyproject()["project"]["version"]
    assert _json("plugin.json")["version"] == version
    assert _json("marketplace.json")["metadata"]["version"] == version


def test_plugin_manifests_carry_the_one_author_and_home() -> None:
    plugin = _json("plugin.json")
    assert plugin["author"] == AUTHOR
    assert plugin["homepage"] == HOME
    assert plugin["repository"] == HOME
    market = _json("marketplace.json")
    assert market["owner"] == AUTHOR
    for entry in market["plugins"]:
        assert entry["author"] == AUTHOR, entry["name"]


def test_the_one_address_is_the_only_address_in_the_release_metadata() -> None:
    # Every address these files carry is the author's; LICENSE names none of its own.
    for rel in ("pyproject.toml", ".claude-plugin/plugin.json", ".claude-plugin/marketplace.json"):
        text = (ROOT / rel).read_text(encoding="utf-8")
        found = set(re.findall(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+", text))
        assert found == {AUTHOR["email"]}, f"{rel}: {sorted(found)}"
    license_text = (ROOT / "LICENSE").read_text(encoding="utf-8")
    assert not re.findall(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+", license_text)


def test_reexports_every_child_command() -> None:
    scripts = _pyproject()["project"]["scripts"]
    for name, target in CHILD_SCRIPTS.items():
        assert scripts.get(name) == target, f"{name}: {scripts.get(name)!r} != {target!r}"


def test_kit_keeps_its_own_command_and_adds_no_other() -> None:
    scripts = _pyproject()["project"]["scripts"]
    assert scripts["sessionkit"] == "sessionkit.cli:main"
    assert set(scripts) == {"sessionkit", *CHILD_SCRIPTS}
    # `session` is sessiontools' command re-exported, never a kit implementation.
    assert not scripts["session"].startswith("sessionkit.")


def test_plugin_depends_on_the_five() -> None:
    plugin = _json("plugin.json")
    assert plugin["name"] == "sessionkit"
    # Bare names: they resolve against this plugin's own marketplace (Q1).
    assert plugin["dependencies"] == FAMILY


def test_marketplace_lists_kit_plus_the_five_and_no_voicemode() -> None:
    market = _json("marketplace.json")
    entries = {p["name"]: p for p in market["plugins"]}
    assert set(entries) == {"sessionkit", *FAMILY}
    assert "voicemode" not in entries  # D11 unruled
    assert entries["sessionkit"]["source"] == "./"


def test_family_sources_follow_d1() -> None:
    entries = {p["name"]: p for p in _json("marketplace.json")["plugins"]}
    for child in FAMILY:
        # D1: github.com/sessionkit/<name>, written as an https git url so the
        # clone is HTTPS by its form (a "github" source prefers SSH).
        assert entries[child]["source"] == {
            "source": "url",
            "url": f"https://github.com/sessionkit/{child}.git",
        }


def _sources(node: object):
    """Every "source" value anywhere in the marketplace, nested ones included."""
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "source":
                yield value
            yield from _sources(value)
    elif isinstance(node, list):
        for item in node:
            yield from _sources(item)


# A "github" source clones over SSH whenever `ssh -T git@github.com`
# answers, and an update or an in-session /plugin install never falls back to
# HTTPS, so a user with no working GitHub SSH key could not get the family.
def test_every_remote_marketplace_source_is_an_https_url() -> None:
    market = _json("marketplace.json")
    remote = [p["source"] for p in market["plugins"] if p["source"] != "./"]
    assert remote, "the family must be listed with remote sources"
    for source in remote:
        assert isinstance(source, dict) and source["source"] == "url", source
        assert source["url"].startswith("https://"), source


def test_no_marketplace_source_is_github_typed_or_ssh() -> None:
    market = _json("marketplace.json")
    for source in _sources(market):
        if isinstance(source, dict):
            assert source.get("source") != "github", source
        assert "git@" not in json.dumps(source), source


def test_every_dependency_is_listed_in_the_same_marketplace() -> None:
    # Q1: a dependency from another marketplace is not fetched ("failed to load").
    listed = {p["name"] for p in _json("marketplace.json")["plugins"]}
    for dep in _json("plugin.json")["dependencies"]:
        assert "@" not in dep and dep in listed


# SK-102: pyproject's description is the PyPI Summary, the first line a user
# reads. It was written while the name was only reserved, and said so.
def test_pyproject_says_nothing_about_a_reserved_name() -> None:
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert "name reserved" not in text.lower()


def test_description_reads_as_a_pypi_summary() -> None:
    desc = _pyproject()["project"]["description"]
    assert desc.strip(), "empty description"
    assert "\n" not in desc and desc == desc.strip()
    assert len(desc) < 160, f"{len(desc)} chars"
    assert "reserved" not in desc.lower()
    # Every part of the family it installs is named, voice included.
    for word in ("voice", "mail", "phone", "sidebar"):
        assert word in desc.lower(), word


def test_plugin_manifests_mirror_the_pyproject_description() -> None:
    desc = _pyproject()["project"]["description"]
    assert _json("plugin.json")["description"] == desc
    entries = {p["name"]: p for p in _json("marketplace.json")["plugins"]}
    assert entries["sessionkit"]["description"] == desc


# SK-103: the kit's other one-liners say the same line. `sessionkit --help`
# (the click docstring), the package docstring, and the skill's description
# and body lead each carry pyproject's description, word for word.
SKILL = ROOT / "skills" / "sessionkit" / "SKILL.md"
OLD_LEAD = "the session family in one install"


def _skill_parts() -> tuple[str, str]:
    """The skill's folded `description` (one line) and its body after the front matter."""
    _, front, body = SKILL.read_text(encoding="utf-8").split("---\n", 2)
    lines = front.splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith("description:"))
    folded = []
    for line in lines[start + 1 :]:
        if not line.startswith("  "):
            break
        folded.append(line.strip())
    return " ".join(folded), body


def test_cli_help_says_the_pyproject_description() -> None:
    from click.testing import CliRunner

    from sessionkit.cli import main

    desc = _pyproject()["project"]["description"]
    assert main.help == desc
    out = CliRunner().invoke(main, ["--help"]).output
    # Click wraps the help text; compare it unwrapped.
    assert desc in " ".join(out.split())


def test_package_docstring_says_the_pyproject_description() -> None:
    import sessionkit

    assert sessionkit.__doc__ == _pyproject()["project"]["description"]


def test_skill_description_leads_with_the_pyproject_description() -> None:
    desc = _pyproject()["project"]["description"]
    description, _ = _skill_parts()
    # The line, its full stop, then the skill's own trigger sentence.
    assert description.startswith(f"{desc} Use when "), description


def test_skill_body_leads_with_the_pyproject_description() -> None:
    _, body = _skill_parts()
    paras = [p.strip() for p in body.split("\n\n") if p.strip()]
    assert paras[0] == "# sessionkit"
    assert paras[1] == _pyproject()["project"]["description"]


def test_no_shipped_file_keeps_the_old_lead() -> None:
    for rel in ("src/sessionkit/cli.py", "src/sessionkit/__init__.py", "skills/sessionkit/SKILL.md"):
        assert OLD_LEAD not in (ROOT / rel).read_text(encoding="utf-8"), rel
