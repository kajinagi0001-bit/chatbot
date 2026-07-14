import json

from family_chatbot.family_repository import FamilyRepository


def test_load_returns_empty_dict_when_file_does_not_exist(tmp_path):
    path = tmp_path / "family_state.json"
    repository = FamilyRepository(path)

    state = repository.load()

    assert state == {}
    assert path.parent.exists()


def test_save_and_load_state(tmp_path):
    path = tmp_path / "family_state.json"
    repository = FamilyRepository(path)

    expected = {
        "current_member": "凪",
        "shopping_list": [
            {
                "text": "牛乳",
                "done": False,
            }
        ],
    }

    repository.save(expected)
    actual = repository.load()

    assert actual == expected


def test_save_creates_parent_directory(tmp_path):
    path = tmp_path / "data" / "family_state.json"
    repository = FamilyRepository(path)

    repository.save({"current_member": "guest"})

    assert path.exists()


def test_saved_json_keeps_japanese_characters(tmp_path):
    path = tmp_path / "family_state.json"
    repository = FamilyRepository(path)

    repository.save({"message": "牛乳を買う"})

    raw_text = path.read_text(encoding="utf-8")

    assert "牛乳を買う" in raw_text
    assert "\\u725b" not in raw_text


def test_load_returns_empty_dict_for_broken_json(tmp_path):
    path = tmp_path / "family_state.json"
    path.write_text("{broken json", encoding="utf-8")

    repository = FamilyRepository(path)

    assert repository.load() == {}


def test_load_returns_empty_dict_for_invalid_encoding_data(tmp_path):
    path = tmp_path / "family_state.json"
    path.write_bytes(b"\xff\xfe\x00\x00")

    repository = FamilyRepository(path)

    assert repository.load() == {}


def test_saved_file_contains_valid_json(tmp_path):
    path = tmp_path / "family_state.json"
    repository = FamilyRepository(path)

    repository.save({"notes": ["ゴミ出しは火曜日"]})

    loaded_directly = json.loads(
        path.read_text(encoding="utf-8")
    )

    assert loaded_directly["notes"] == [
        "ゴミ出しは火曜日"
    ]