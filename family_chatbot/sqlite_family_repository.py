import sqlite3

from pathlib import Path
from typing import Any


class SQLiteFamilyRepository:
    """SQLiteを使用して家族データを保存するRepository。"""

    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        self._initialize_database()

    def load(self) -> dict[str, Any]:
        """SQLite内の全データをFamilyStore形式で復元する。"""
        with self._connect() as connection:
            current_member = self._load_current_member(
                connection
            )
            members = self._load_members(connection)

            return {
                "current_member": current_member,
                "members": members,
                "shared": {
                    "notes": self._load_shared_notes(
                        connection
                    ),
                },
                "events": self._load_events(connection),
                "shopping_list": self._load_shopping_items(
                    connection
                ),
                "messages": self._load_messages(
                    connection
                ),
            }

    def save(
        self,
        state: dict[str, Any],
    ) -> None:
        """FamilyStore形式の状態をSQLiteへ保存する。

        全テーブルを1トランザクション内で更新する。
        """
        with self._connect() as connection:
            try:
                connection.execute("BEGIN")

                self._clear_all(connection)
                self._save_settings(connection, state)
                self._save_members(connection, state)
                self._save_shared_notes(connection, state)
                self._save_shopping_items(connection, state)
                self._save_events(connection, state)
                self._save_messages(connection, state)

                connection.commit()
            except Exception:
                connection.rollback()
                raise

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute(
            "PRAGMA foreign_keys = ON"
        )
        return connection

    def _initialize_database(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS members (
                    id TEXT PRIMARY KEY,
                    display_name TEXT NOT NULL,
                    created_at TEXT
                );

                CREATE TABLE IF NOT EXISTS member_notes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    member_id TEXT NOT NULL,
                    note TEXT NOT NULL,
                    position INTEGER NOT NULL,
                    FOREIGN KEY (member_id)
                        REFERENCES members(id)
                        ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS member_preferences (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    member_id TEXT NOT NULL,
                    preference TEXT NOT NULL,
                    position INTEGER NOT NULL,
                    FOREIGN KEY (member_id)
                        REFERENCES members(id)
                        ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS shared_notes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    note TEXT NOT NULL,
                    position INTEGER NOT NULL
                );

                CREATE TABLE IF NOT EXISTS shopping_items (
                    id TEXT PRIMARY KEY,
                    text TEXT NOT NULL,
                    added_by TEXT NOT NULL,
                    done INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT,
                    done_at TEXT
                );

                CREATE TABLE IF NOT EXISTS events (
                    id TEXT PRIMARY KEY,
                    owner TEXT NOT NULL,
                    title TEXT NOT NULL,
                    date TEXT,
                    time TEXT,
                    note TEXT,
                    created_at TEXT
                );

                CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY,
                    sender TEXT NOT NULL,
                    recipient TEXT NOT NULL,
                    text TEXT NOT NULL,
                    delivered INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT,
                    delivered_at TEXT
                );
                """
            )

    @staticmethod
    def _clear_all(
        connection: sqlite3.Connection,
    ) -> None:
        # 子テーブルから先に削除する
        tables = [
            "member_notes",
            "member_preferences",
            "shared_notes",
            "shopping_items",
            "events",
            "messages",
            "members",
            "settings",
        ]

        for table in tables:
            connection.execute(
                f"DELETE FROM {table}"
            )

    @staticmethod
    def _save_settings(
        connection: sqlite3.Connection,
        state: dict[str, Any],
    ) -> None:
        current_member = state.get(
            "current_member",
            "guest",
        )

        connection.execute(
            """
            INSERT INTO settings (key, value)
            VALUES (?, ?)
            """,
            ("current_member", current_member),
        )

    @staticmethod
    def _save_members(
        connection: sqlite3.Connection,
        state: dict[str, Any],
    ) -> None:
        members = state.get("members", {})

        for member_id, member in members.items():
            connection.execute(
                """
                INSERT INTO members (
                    id,
                    display_name,
                    created_at
                )
                VALUES (?, ?, ?)
                """,
                (
                    member_id,
                    member.get(
                        "display_name",
                        member_id,
                    ),
                    member.get("created_at"),
                ),
            )

            for position, note in enumerate(
                member.get("notes", [])
            ):
                connection.execute(
                    """
                    INSERT INTO member_notes (
                        member_id,
                        note,
                        position
                    )
                    VALUES (?, ?, ?)
                    """,
                    (
                        member_id,
                        note,
                        position,
                    ),
                )

            for position, preference in enumerate(
                member.get("preferences", [])
            ):
                connection.execute(
                    """
                    INSERT INTO member_preferences (
                        member_id,
                        preference,
                        position
                    )
                    VALUES (?, ?, ?)
                    """,
                    (
                        member_id,
                        preference,
                        position,
                    ),
                )

    @staticmethod
    def _save_shared_notes(
        connection: sqlite3.Connection,
        state: dict[str, Any],
    ) -> None:
        notes = state.get(
            "shared",
            {},
        ).get(
            "notes",
            [],
        )

        for position, note in enumerate(notes):
            connection.execute(
                """
                INSERT INTO shared_notes (
                    note,
                    position
                )
                VALUES (?, ?)
                """,
                (
                    note,
                    position,
                ),
            )

    @staticmethod
    def _save_shopping_items(
        connection: sqlite3.Connection,
        state: dict[str, Any],
    ) -> None:
        for item in state.get(
            "shopping_list",
            [],
        ):
            connection.execute(
                """
                INSERT INTO shopping_items (
                    id,
                    text,
                    added_by,
                    done,
                    created_at,
                    done_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    item["id"],
                    item["text"],
                    item.get("added_by", "guest"),
                    int(item.get("done", False)),
                    item.get("created_at"),
                    item.get("done_at"),
                ),
            )

    @staticmethod
    def _save_events(
        connection: sqlite3.Connection,
        state: dict[str, Any],
    ) -> None:
        for event in state.get("events", []):
            connection.execute(
                """
                INSERT INTO events (
                    id,
                    owner,
                    title,
                    date,
                    time,
                    note,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event["id"],
                    event.get("owner", "guest"),
                    event.get("title", "予定"),
                    event.get("date"),
                    event.get("time"),
                    event.get("note", ""),
                    event.get("created_at"),
                ),
            )

    @staticmethod
    def _save_messages(
        connection: sqlite3.Connection,
        state: dict[str, Any],
    ) -> None:
        for message in state.get("messages", []):
            connection.execute(
                """
                INSERT INTO messages (
                    id,
                    sender,
                    recipient,
                    text,
                    delivered,
                    created_at,
                    delivered_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    message["id"],
                    message.get("from", "guest"),
                    message["to"],
                    message["text"],
                    int(
                        message.get(
                            "delivered",
                            False,
                        )
                    ),
                    message.get("created_at"),
                    message.get("delivered_at"),
                ),
            )

    @staticmethod
    def _load_current_member(
        connection: sqlite3.Connection,
    ) -> str:
        row = connection.execute(
            """
            SELECT value
            FROM settings
            WHERE key = ?
            """,
            ("current_member",),
        ).fetchone()

        return row["value"] if row else "guest"

    @staticmethod
    def _load_members(
        connection: sqlite3.Connection,
    ) -> dict[str, dict[str, Any]]:
        rows = connection.execute(
            """
            SELECT id, display_name, created_at
            FROM members
            ORDER BY rowid
            """
        ).fetchall()

        members: dict[str, dict[str, Any]] = {}

        for row in rows:
            member_id = row["id"]

            member = {
                "display_name": row["display_name"],
                "notes": [],
                "preferences": [],
            }

            if row["created_at"] is not None:
                member["created_at"] = row[
                    "created_at"
                ]

            members[member_id] = member

        note_rows = connection.execute(
            """
            SELECT member_id, note
            FROM member_notes
            ORDER BY member_id, position
            """
        ).fetchall()

        for row in note_rows:
            member_id = row["member_id"]

            if member_id in members:
                members[member_id]["notes"].append(
                    row["note"]
                )

        preference_rows = connection.execute(
            """
            SELECT member_id, preference
            FROM member_preferences
            ORDER BY member_id, position
            """
        ).fetchall()

        for row in preference_rows:
            member_id = row["member_id"]

            if member_id in members:
                members[member_id][
                    "preferences"
                ].append(
                    row["preference"]
                )

        return members

    @staticmethod
    def _load_shared_notes(
        connection: sqlite3.Connection,
    ) -> list[str]:
        rows = connection.execute(
            """
            SELECT note
            FROM shared_notes
            ORDER BY position
            """
        ).fetchall()

        return [
            row["note"]
            for row in rows
        ]

    @staticmethod
    def _load_shopping_items(
        connection: sqlite3.Connection,
    ) -> list[dict[str, Any]]:
        rows = connection.execute(
            """
            SELECT
                id,
                text,
                added_by,
                done,
                created_at,
                done_at
            FROM shopping_items
            ORDER BY rowid
            """
        ).fetchall()

        items = []

        for row in rows:
            item = {
                "id": row["id"],
                "text": row["text"],
                "added_by": row["added_by"],
                "done": bool(row["done"]),
            }

            if row["created_at"] is not None:
                item["created_at"] = row[
                    "created_at"
                ]

            if row["done_at"] is not None:
                item["done_at"] = row["done_at"]

            items.append(item)

        return items

    @staticmethod
    def _load_events(
        connection: sqlite3.Connection,
    ) -> list[dict[str, Any]]:
        rows = connection.execute(
            """
            SELECT
                id,
                owner,
                title,
                date,
                time,
                note,
                created_at
            FROM events
            ORDER BY rowid
            """
        ).fetchall()

        events = []

        for row in rows:
            event = {
                "id": row["id"],
                "owner": row["owner"],
                "title": row["title"],
                "date": row["date"] or "",
                "time": row["time"] or "",
                "note": row["note"] or "",
            }

            if row["created_at"] is not None:
                event["created_at"] = row[
                    "created_at"
                ]

            events.append(event)

        return events

    @staticmethod
    def _load_messages(
        connection: sqlite3.Connection,
    ) -> list[dict[str, Any]]:
        rows = connection.execute(
            """
            SELECT
                id,
                sender,
                recipient,
                text,
                delivered,
                created_at,
                delivered_at
            FROM messages
            ORDER BY rowid
            """
        ).fetchall()

        messages = []

        for row in rows:
            message = {
                "id": row["id"],
                "from": row["sender"],
                "to": row["recipient"],
                "text": row["text"],
                "delivered": bool(
                    row["delivered"]
                ),
            }

            if row["created_at"] is not None:
                message["created_at"] = row[
                    "created_at"
                ]

            if row["delivered_at"] is not None:
                message["delivered_at"] = row[
                    "delivered_at"
                ]

            messages.append(message)

        return messages
    
    def is_empty(self) -> bool:
        """保存済みの家族データがないか確認する。"""
        with self._connect() as connection:
            tables = [
                "settings",
                "members",
                "member_notes",
                "member_preferences",
                "shared_notes",
                "shopping_items",
                "events",
                "messages",
            ]

            for table in tables:
                row = connection.execute(
                    f"SELECT 1 FROM {table} LIMIT 1"
                ).fetchone()

                if row is not None:
                    return False

        return True