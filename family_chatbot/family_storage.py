import shutil
import sqlite3

from pathlib import Path

from .family import FamilyStore
from .family_repository import FamilyRepository
from .sqlite_family_repository import (
    SQLiteFamilyRepository,
)


def create_family_store(
    data_directory: Path = Path("data"),
) -> FamilyStore:
    """家族データ用のFamilyStoreを生成する。

    原則としてSQLiteを使用する。
    既存JSONがありSQLiteが空の場合は、一度だけ移行する。
    SQLiteを利用できない場合はJSONへフォールバックする。
    """
    json_path = data_directory / "family_state.json"
    database_path = data_directory / "family.db"

    data_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    json_repository = FamilyRepository(json_path)

    try:
        sqlite_repository = SQLiteFamilyRepository(
            database_path
        )

        migrate_json_to_sqlite(
            json_path=json_path,
            json_repository=json_repository,
            sqlite_repository=sqlite_repository,
        )

        return FamilyStore.load(
            path=database_path,
            repository=sqlite_repository,
        )

    except sqlite3.Error as error:
        print(
            "SQLiteを利用できないため、"
            "JSON保存を使用します。"
            f" 原因: {error}"
        )

        return FamilyStore.load(
            path=json_path,
            repository=json_repository,
        )


def migrate_json_to_sqlite(
    json_path: Path,
    json_repository: FamilyRepository,
    sqlite_repository: SQLiteFamilyRepository,
) -> bool:
    """既存JSONを空のSQLiteへ移行する。

    移行した場合はTrue、移行不要の場合はFalseを返す。
    """
    if not sqlite_repository.is_empty():
        return False

    if not json_path.exists():
        return False

    json_state = json_repository.load()

    if not _has_family_data(json_state):
        return False

    backup_path = _create_json_backup(json_path)

    try:
        sqlite_repository.save(json_state)
    except Exception:
        # SQLite保存に失敗しても、JSONとバックアップは残る
        raise

    print(
        "家族データをJSONからSQLiteへ移行しました。"
        f" バックアップ: {backup_path}"
    )

    return True


def _has_family_data(state: dict) -> bool:
    """初期状態以外のデータが含まれているか確認する。"""
    if not state:
        return False

    if state.get("current_member") not in {
        None,
        "",
        "guest",
    }:
        return True

    members = state.get("members", {})

    for member_id, member in members.items():
        if member_id != "guest":
            return True

        if member.get("notes"):
            return True

        if member.get("preferences"):
            return True

    return any(
        [
            state.get("shared", {}).get("notes"),
            state.get("events"),
            state.get("shopping_list"),
            state.get("messages"),
        ]
    )


def _create_json_backup(
    json_path: Path,
) -> Path:
    """移行前JSONのバックアップを作成する。"""
    backup_path = json_path.with_suffix(
        ".pre-sqlite.json"
    )

    if backup_path.exists():
        return backup_path

    shutil.copy2(
        json_path,
        backup_path,
    )

    return backup_path