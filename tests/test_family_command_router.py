import json
from types import SimpleNamespace

from family_chatbot.config import AppConfig
from family_chatbot.family_command_router import (
    FamilyCommandRouter,
)


def make_tool_response(
    canonical_text: str,
    category: str = "shopping",
):
    tool_call = SimpleNamespace(
        function=SimpleNamespace(
            name="normalize_family_command",
            arguments=json.dumps(
                {
                    "canonical_text": canonical_text,
                    "category": category,
                },
                ensure_ascii=False,
            ),
        )
    )

    message = SimpleNamespace(
        tool_calls=[tool_call]
    )

    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=message
            )
        ]
    )


def make_plain_response():
    message = SimpleNamespace(
        tool_calls=None
    )

    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=message
            )
        ]
    )


class FakeCompletions:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return self.response


class FakeClient:
    def __init__(self, response):
        self.chat = SimpleNamespace(
            completions=FakeCompletions(
                response
            )
        )


def test_route_shopping_expression():
    client = FakeClient(
        make_tool_response(
            "買い物リストに牛乳を入れて"
        )
    )

    router = FamilyCommandRouter(
        AppConfig(),
        client=client,
    )

    result = router.route(
        "牛乳切れそうだから次買ってきて"
    )

    assert result == (
        "買い物リストに牛乳を入れて"
    )


def test_route_schedule_expression():
    client = FakeClient(
        make_tool_response(
            "明日16時に歯医者の予定を入れて",
            category="schedule",
        )
    )

    router = FamilyCommandRouter(
        AppConfig(),
        client=client,
    )

    result = router.route(
        "明日の16時は歯医者だから覚えて"
    )

    assert result == (
        "明日16時に歯医者の予定を入れて"
    )


def test_general_conversation_returns_none():
    client = FakeClient(
        make_plain_response()
    )

    router = FamilyCommandRouter(
        AppConfig(),
        client=client,
    )

    result = router.route(
        "今日はいい天気ですね"
    )

    assert result is None


def test_empty_input_does_not_call_api():
    client = FakeClient(
        make_plain_response()
    )

    router = FamilyCommandRouter(
        AppConfig(),
        client=client,
    )

    result = router.route("   ")

    assert result is None
    assert (
        client.chat.completions.calls
        == []
    )


def test_invalid_json_returns_none():
    tool_call = SimpleNamespace(
        function=SimpleNamespace(
            name="normalize_family_command",
            arguments="{invalid",
        )
    )

    response = SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(
                    tool_calls=[tool_call]
                )
            )
        ]
    )

    router = FamilyCommandRouter(
        AppConfig(),
        client=FakeClient(response),
    )

    assert router.route(
        "牛乳をお願い"
    ) is None


def test_api_error_returns_none():
    class ErrorCompletions:
        def create(self, **kwargs):
            raise RuntimeError(
                "API unavailable"
            )

    client = SimpleNamespace(
        chat=SimpleNamespace(
            completions=ErrorCompletions()
        )
    )

    router = FamilyCommandRouter(
        AppConfig(),
        client=client,
    )

    assert router.route(
        "牛乳を買ってきて"
    ) is None

from pathlib import Path

from family_chatbot.family import FamilyStore


def test_routed_command_can_be_executed(
    tmp_path,
):
    client = FakeClient(
        make_tool_response(
            "買い物リストに牛乳を入れて"
        )
    )

    router = FamilyCommandRouter(
        AppConfig(),
        client=client,
    )

    store = FamilyStore.load(
        tmp_path / "family_state.json"
    )

    original_text = (
        "牛乳が切れそうだから"
        "次の買い物で買ってきて"
    )

    direct_result = store.handle_command(
        original_text
    )

    assert direct_result.handled is False

    canonical_text = router.route(
        original_text
    )

    routed_result = store.handle_command(
        canonical_text
    )

    assert routed_result.handled is True
    assert (
        store.state["shopping_list"][0]["text"]
        == "牛乳"
    )