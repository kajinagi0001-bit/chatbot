import json
from pathlib import Path
from typing import Any


class FamilyRepository:
    """家族データの永続化を担当するクラス。"""

    def __init__(self, path: Path):
        self.path = path

    def load(self) -> dict[str, Any]:
        self.path.parent.mkdir(parents=True, exist_ok=True)

        if not self.path.exists():
            return {}

        try:
            return json.loads(
                self.path.read_text(encoding="utf-8")
            )
        except (
            OSError,
            UnicodeDecodeError,
            json.JSONDecodeError,
        ):
            return {}

    def save(self, state: dict[str, Any]) -> None:
        """現在の状態をJSONファイルへ保存する。"""
        self.path.parent.mkdir(parents=True, exist_ok=True)

        self.path.write_text(
            json.dumps(
                state,
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )