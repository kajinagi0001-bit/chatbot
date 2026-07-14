import json
import sqlite3

from family_chatbot.family_repository import (
    FamilyRepository,
)
from family_chatbot.family_storage import (
    create_family_store,
    migrate_json_to_sqlite,
)
from family_chatbot.sqlite_family_repository import (
    SQLiteFamilyRepository,
)


def make_json_state():
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
            }
        },
        "shared": {
            "notes": [
                "ゴミ出しは火曜と金曜",
            ],
        },
        "events": [],
        "shopping_list": [
            {
                "id": "item1",
                "text": "牛乳",
                "added_by": "凪",
                "done": False,
                "created_at": "2026-07-15T00:00:00",
            }
        ],
        "messages": [],
    }


def write_json_state(path, state):
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    path.write_text(
        json.dumps(
            state,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def test_migrate_json_to_empty_sqlite(tmp_path):
    json_path = tmp_path / "family_state.json"
    database_path = tmp_path / "family.db"

    expected = make_json_state()
    write_json_state(json_path, expected)

    json_repository = FamilyRepository(json_path)
    sqlite_repository = SQLiteFamilyRepository(
        database_path
    )

    migrated = migrate_json_to_sqlite(
        json_path=json_path,
        json_repository=json_repository,
        sqlite_repository=sqlite_repository,
    )

    assert migrated is True
    assert sqlite_repository.load() == expected


def test_migration_creates_backup(tmp_path):
    json_path = tmp_path / "family_state.json"
    database_path = tmp_path / "family.db"

    expected = make_json_state()
    write_json_state(json_path, expected)

    migrate_json_to_sqlite(
        json_path=json_path,
        json_repository=FamilyRepository(json_path),
        sqlite_repository=SQLiteFamilyRepository(
            database_path
        ),
    )

    backup_path = (
        tmp_path / "family_state.pre-sqlite.json"
    )

    assert backup_path.exists()

    backup_state = json.loads(
        backup_path.read_text(
            encoding="utf-8"
        )
    )

    assert backup_state == expected


def test_original_json_is_not_deleted(tmp_path):
    json_path = tmp_path / "family_state.json"
    database_path = tmp_path / "family.db"

    write_json_state(
        json_path,
        make_json_state(),
    )

    migrate_json_to_sqlite(
        json_path=json_path,
        json_repository=FamilyRepository(json_path),
        sqlite_repository=SQLiteFamilyRepository(
            database_path
        ),
    )

    assert json_path.exists()


def test_existing_sqlite_is_not_overwritten(
    tmp_path,
):
    json_path = tmp_path / "family_state.json"
    database_path = tmp_path / "family.db"

    json_state = make_json_state()
    write_json_state(
        json_path,
        json_state,
    )

    sqlite_state = make_json_state()
    sqlite_state["shopping_list"][0][
        "text"
    ] = "パン"

    sqlite_repository = SQLiteFamilyRepository(
        database_path
    )
    sqlite_repository.save(sqlite_state)

    migrated = migrate_json_to_sqlite(
        json_path=json_path,
        json_repository=FamilyRepository(json_path),
        sqlite_repository=sqlite_repository,
    )

    assert migrated is False
    assert (
        sqlite_repository.load()[
            "shopping_list"
        ][0]["text"]
        == "パン"
    )


def test_missing_json_does_not_trigger_migration(
    tmp_path,
):
    json_path = tmp_path / "family_state.json"
    sqlite_repository = SQLiteFamilyRepository(
        tmp_path / "family.db"
    )

    migrated = migrate_json_to_sqlite(
        json_path=json_path,
        json_repository=FamilyRepository(json_path),
        sqlite_repository=sqlite_repository,
    )

    assert migrated is False
    assert sqlite_repository.is_empty() is True


def test_empty_json_does_not_trigger_migration(
    tmp_path,
):
    json_path = tmp_path / "family_state.json"
    json_path.write_text(
        "{}",
        encoding="utf-8",
    )

    sqlite_repository = SQLiteFamilyRepository(
        tmp_path / "family.db"
    )

    migrated = migrate_json_to_sqlite(
        json_path=json_path,
        json_repository=FamilyRepository(json_path),
        sqlite_repository=sqlite_repository,
    )

    assert migrated is False
    assert sqlite_repository.is_empty() is True


def test_create_family_store_uses_sqlite(
    tmp_path,
):
    json_path = tmp_path / "family_state.json"
    write_json_state(
        json_path,
        make_json_state(),
    )

    store = create_family_store(tmp_path)

    assert store.current_member == "凪"
    assert (
        store.state["shopping_list"][0]["text"]
        == "牛乳"
    )
    assert (
        isinstance(
            store.repository,
            SQLiteFamilyRepository,
        )
    )


def test_changes_are_saved_to_sqlite_after_migration(
    tmp_path,
):
    json_path = tmp_path / "family_state.json"
    write_json_state(
        json_path,
        make_json_state(),
    )

    store = create_family_store(tmp_path)

    store.handle_command(
        "買い物リストに卵を入れて"
    )

    reloaded = create_family_store(tmp_path)

    item_names = [
        item["text"]
        for item in reloaded.state[
            "shopping_list"
        ]
    ]

    assert item_names == [
        "牛乳",
        "卵",
    ]

def test_create_family_store_falls_back_to_json(
    tmp_path,
    monkeypatch,
):
    json_path = tmp_path / "family_state.json"
    expected = make_json_state()

    write_json_state(
        json_path,
        expected,
    )

    def raise_database_error(*args, **kwargs):
        raise sqlite3.OperationalError(
            "database unavailable"
        )

    monkeypatch.setattr(
        "family_chatbot.family_storage."
        "SQLiteFamilyRepository",
        raise_database_error,
    )

    store = create_family_store(tmp_path)

    assert store.current_member == "凪"
    assert (
        store.state["shopping_list"][0]["text"]
        == "牛乳"
    )
    assert isinstance(
        store.repository,
        FamilyRepository,
    )