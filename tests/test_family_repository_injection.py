from copy import deepcopy
from pathlib import Path
from typing import Any

from family_chatbot.family import FamilyStore


class InMemoryFamilyRepository:
    """ファイルを使用しないテスト用Repository。"""

    def __init__(
        self,
        initial_state: dict[str, Any] | None = None,
    ):
        self.stored_state = deepcopy(
            initial_state or {}
        )
        self.load_count = 0
        self.save_count = 0

    def load(self) -> dict[str, Any]:
        self.load_count += 1

        return deepcopy(self.stored_state)

    def save(
        self,
        state: dict[str, Any],
    ) -> None:
        self.save_count += 1
        self.stored_state = deepcopy(state)


def test_repository_is_injected():
    repository = InMemoryFamilyRepository()

    store = FamilyStore.load(
        Path("unused.json"),
        repository=repository,
    )

    assert store.repository is repository
    assert repository.load_count == 1


def test_injected_repository_is_used_for_save():
    repository = InMemoryFamilyRepository()

    store = FamilyStore.load(
        Path("unused.json"),
        repository=repository,
    )

    store.handle_command(
        "買い物リストに牛乳を入れて"
    )

    assert repository.save_count == 1
    assert (
        repository.stored_state[
            "shopping_list"
        ][0]["text"]
        == "牛乳"
    )


def test_injected_repository_restores_state():
    repository = InMemoryFamilyRepository(
        {
            "current_member": "凪",
            "members": {
                "凪": {
                    "display_name": "凪",
                    "notes": [],
                    "preferences": [],
                }
            },
            "shared": {
                "notes": [],
            },
            "events": [],
            "shopping_list": [
                {
                    "id": "item1",
                    "text": "牛乳",
                    "added_by": "凪",
                    "done": False,
                }
            ],
            "messages": [],
        }
    )

    store = FamilyStore.load(
        Path("unused.json"),
        repository=repository,
    )

    assert store.current_member == "凪"
    assert (
        store.state["shopping_list"][0]["text"]
        == "牛乳"
    )


def test_repository_receives_independent_state_copy():
    repository = InMemoryFamilyRepository()

    store = FamilyStore.load(
        Path("unused.json"),
        repository=repository,
    )

    store.handle_command(
        "買い物リストに牛乳を入れて"
    )

    store.state["shopping_list"][0][
        "text"
    ] = "変更後"

    assert (
        repository.stored_state[
            "shopping_list"
        ][0]["text"]
        == "牛乳"
    )


def test_default_json_repository_still_works(
    tmp_path,
):
    path = tmp_path / "family_state.json"

    store = FamilyStore.load(path)
    store.handle_command(
        "買い物リストに牛乳を入れて"
    )

    reloaded = FamilyStore.load(path)

    assert (
        reloaded.state["shopping_list"][0][
            "text"
        ]
        == "牛乳"
    )