"""`sessionkit service`: the walk over ~/.sessionkit and the service files.

A service is a JSON file under <package>/services/, at two depths only, with
an integer "service" marker. A file the kit cannot use is a `bad file` row,
never a crash and never skipped in silence.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from _fakekit import DROP, FakeKit

from sessionkit import services


@pytest.fixture
def kit(tmp_path) -> FakeKit:
    return FakeKit(tmp_path)


def _files(kit: FakeKit) -> dict[str, services.ServiceFile]:
    return {sf.name: sf for sf in services.load_all(kit.root)}


def test_the_walk_finds_both_depths_and_nothing_else(kit):
    top = kit.service("voice", "talk")
    agent = kit.service("phone", "bot.alpha", agent_dir="bots", agent="alpha")
    kit.raw(kit.root / "voice" / "settings" / "talk.json", '{"service": 1}')
    kit.raw(kit.root / "voice" / "services" / "a" / "b" / "deep.json", '{"service": 1}')
    kit.raw(kit.root / "voice" / "services" / "notes.txt", "x")
    kit.raw(kit.root / "voice" / "talk.json", '{"service": 1}')
    assert services.walk(kit.root) == sorted([top, agent])
    assert agent.name == "alpha.json"


def test_a_missing_tree_is_no_files(tmp_path):
    assert services.walk(tmp_path / "nowhere") == []


def test_a_valid_file_has_no_problems(kit):
    kit.service("voice", "talk", port=8780, description="the live view")
    sf = _files(kit)["talk"]
    assert sf.marked and sf.problems == [] and sf.package == "voice"


def test_a_json_file_with_no_marker_is_not_a_service(kit):
    kit.raw(kit.root / "voice" / "services" / "x.json", '{"name": "x"}')
    kit.raw(kit.root / "voice" / "services" / "y.json", '{"service": true}')
    files = services.load_all(kit.root)
    assert [sf.marked for sf in files] == [False, False]


@pytest.mark.parametrize(
    ("fields", "problem"),
    [
        ({"name": DROP}, "no `name`"),
        ({"enabled": DROP}, "no `enabled`"),
        ({"install": DROP}, "no `install`"),
        ({"enabled": "yes"}, "`enabled` is not true or false"),
        ({"label": DROP}, "no `label` or `run`"),
        ({"run": ["x"]}, "both `label` and `run`"),
        (
            {"label": "dev.sessionkit.phone.talk"},
            "`label` is not under dev.sessionkit.voice.",
        ),
        ({"label": "com.example.talk"}, "`label` is not under dev.sessionkit.voice."),
        ({"name": "phone"}, "`name` is a group's name: phone"),
    ],
)
def test_each_fault_is_a_bad_file_naming_it(kit, fields, problem):
    kit.service("voice", "talk", **fields)
    (sf,) = services.load_all(kit.root)
    assert problem in sf.problems


def test_run_must_be_a_list_of_words(kit):
    kit.service("tools", "web", label=DROP, run="session web serve")
    (sf,) = services.load_all(kit.root)
    assert sf.problems == ["`run` is not a list of words"]


def test_not_json_is_a_bad_file(kit):
    kit.raw(kit.root / "voice" / "services" / "talk.json", "{not json")
    (sf,) = services.load_all(kit.root)
    assert sf.marked and sf.problems == ["not JSON"]


def test_two_files_with_one_name_are_both_bad(kit):
    a = kit.service("voice", "talk")
    b = kit.raw(
        kit.root / "voice" / "services" / "talk2.json",
        json.dumps(
            {
                "service": 1,
                "name": "talk",
                "label": "dev.sessionkit.voice.talk",
                "enabled": True,
                "install": "x",
            }
        ),
    )
    files = services.load_all(kit.root)
    assert [sf.problems for sf in files] == [
        [f"name also in {b}"],
        [f"name also in {a}"],
    ]


def test_unknown_keys_are_ignored_and_a_later_schema_is_read_with_a_note(kit):
    kit.service("voice", "talk", future_key={"x": 1}, service=2)
    (sf,) = services.load_all(kit.root)
    assert sf.problems == [] and sf.notes == ["schema 2, read as 1"]


def test_a_name_that_is_not_its_label_tail_is_shown_with_a_note(kit):
    kit.service("voice", "talk", label="dev.sessionkit.voice.talk-server")
    (sf,) = services.load_all(kit.root)
    assert sf.problems == [] and sf.notes == ["name is not its label's tail"]


def test_check_never_raises():
    for data in (None, [], "x", 3, {"service": 1, "label": 5, "run": None}):
        assert isinstance(services.check(data, "voice"), list)


SCHEMA = Path(services.__file__).with_name("service.schema.json")


def test_the_shipped_schema_matches_the_checks():
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    assert schema["required"] == list(services.REQUIRED)
    assert schema["properties"]["service"]["const"] == services.SCHEMA_VERSION
    assert schema["properties"]["kind"]["enum"] == list(services.KINDS)
    assert schema["properties"]["order"]["default"] == services.DEFAULT_ORDER
