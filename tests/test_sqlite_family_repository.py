import sqlite3

from family_chatbot.sqlite_family_repository import (
    SQLiteFamilyRepository,
)


def make_full_state():
    return {
        "current_member": "凪",
        "members": {
            "凪": {
                "display_name": "凪",
                "notes": [
                    "朝は短く話してほしい",
                ],
                "preferences": [
                    "カレーが好き",
                ],
                "created_at": "2026-07-14T10:00:00",
            },
            "お母さん": {
                "display_name": "お母さん",
                "notes": [],
                "preferences": [],
            },
        },
        "shared": {
            "notes": [
                "ゴミ出しは火曜と金曜",
            ],
        },
        "shopping_list": [
            {
                "id": "item1",
                "text": "牛乳",
                "added_by": "凪",
                "done": False,
                "created_at": "2026-07-14T10:00:00",
            },
            {
                "id": "item2",
                "text": "卵",
                "added_by": "凪",
                "done": True,
                "created_at": "2026-07-14T10:00:00",
                "done_at": "2026-07-14T11:00:00",
            },
        ],
        "events": [
            {
                "id": "event1",
                "owner": "凪",
                "title": "歯医者",
                "date": "明日",
                "time": "16:00",
                "note": "",
                "created_at": "2026-07-14T10:00:00",
            },
        ],
        "messages": [
            {
                "id": "message1",
                "from": "凪",
                "to": "お母さん",
                "text": "牛乳をお願いします",
                "delivered": False,
                "created_at": "2026-07-14T10:00:00",
            },
        ],
    }


def test_database_file_is_created(tmp_path):
    path = tmp_path / "family.db"

    SQLiteFamilyRepository(path)

    assert path.exists()


def test_empty_database_returns_empty_state_shape(
    tmp_path,
):
    repository = SQLiteFamilyRepository(
        tmp_path / "family.db"
    )

    state = repository.load()

    assert state["current_member"] == "guest"
    assert state["members"] == {}
    assert state["shared"]["notes"] == []
    assert state["shopping_list"] == []
    assert state["events"] == []
    assert state["messages"] == []


def test_save_and_load_full_state(tmp_path):
    repository = SQLiteFamilyRepository(
        tmp_path / "family.db"
    )

    expected = make_full_state()

    repository.save(expected)
    actual = repository.load()

    assert actual == expected


def test_japanese_text_is_preserved(tmp_path):
    repository = SQLiteFamilyRepository(
        tmp_path / "family.db"
    )

    state = make_full_state()
    repository.save(state)

    loaded = repository.load()

    assert (
        loaded["members"]["凪"]["display_name"]
        == "凪"
    )
    assert (
        loaded["shared"]["notes"][0]
        == "ゴミ出しは火曜と金曜"
    )
    assert (
        loaded["shopping_list"][0]["text"]
        == "牛乳"
    )


def test_boolean_values_are_restored(tmp_path):
    repository = SQLiteFamilyRepository(
        tmp_path / "family.db"
    )

    repository.save(make_full_state())
    loaded = repository.load()

    assert (
        loaded["shopping_list"][0]["done"]
        is False
    )
    assert (
        loaded["shopping_list"][1]["done"]
        is True
    )
    assert (
        loaded["messages"][0]["delivered"]
        is False
    )


def test_second_save_replaces_previous_state(
    tmp_path,
):
    repository = SQLiteFamilyRepository(
        tmp_path / "family.db"
    )

    first = make_full_state()
    repository.save(first)

    second = make_full_state()
    second["shopping_list"] = [
        {
            "id": "item3",
            "text": "パン",
            "added_by": "凪",
            "done": False,
            "created_at": "2026-07-14T12:00:00",
        }
    ]

    repository.save(second)
    loaded = repository.load()

    assert len(loaded["shopping_list"]) == 1
    assert (
        loaded["shopping_list"][0]["text"]
        == "パン"
    )


def test_all_expected_tables_are_created(
    tmp_path,
):
    path = tmp_path / "family.db"

    SQLiteFamilyRepository(path)

    with sqlite3.connect(path) as connection:
        rows = connection.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
            """
        ).fetchall()

    table_names = {
        row[0]
        for row in rows
    }

    expected_tables = {
        "settings",
        "members",
        "member_notes",
        "member_preferences",
        "shared_notes",
        "shopping_items",
        "events",
        "messages",
    }

    assert expected_tables <= table_names

from pathlib import Path

from family_chatbot.family import FamilyStore


def test_family_store_uses_sqlite_repository(
    tmp_path,
):
    database_path = tmp_path / "family.db"

    repository = SQLiteFamilyRepository(
        database_path
    )

    store = FamilyStore.load(
        Path("unused.json"),
        repository=repository,
    )

    store.handle_command(
        "私は凪です"
    )
    store.handle_command(
        "買い物リストに牛乳を入れて"
    )
    store.handle_command(
        "朝は短く話してほしいって覚えておいて"
    )

    reloaded = FamilyStore.load(
        Path("unused.json"),
        repository=SQLiteFamilyRepository(
            database_path
        ),
    )

    assert reloaded.current_member == "凪"
    assert (
        reloaded.state["shopping_list"][0]["text"]
        == "牛乳"
    )
    assert (
        reloaded.state["members"]["凪"]["notes"]
        == ["朝は短く話してほしい"]
    )