import json

from pathlib import Path
from typing import Any, Protocol


class FamilyRepositoryProtocol(Protocol):
    """家族データ保存Repositoryの共通インターフェース。"""

    def load(self) -> dict[str, Any]:
        ...

    def save(
        self,
        state: dict[str, Any],
    ) -> None:
        ...


class FamilyRepository:
    """JSONファイルを使用する家族データRepository。"""

    def __init__(self, path: Path):
        self.path = path

    def load(self) -> dict[str, Any]:
        self.path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        if not self.path.exists():
            return {}

        try:
            return json.loads(
                self.path.read_text(
                    encoding="utf-8",
                )
            )
        except (
            OSError,
            UnicodeDecodeError,
            json.JSONDecodeError,
        ):
            return {}

    def save(
        self,
        state: dict[str, Any],
    ) -> None:
        self.path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.path.write_text(
            json.dumps(
                state,
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )