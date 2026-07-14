import json

import pytest

from family_chatbot.family import FamilyStore


@pytest.fixture
def store(tmp_path):
    """テストごとに独立した家族データを作成する。"""
    return FamilyStore.load(tmp_path / "family_state.json")


def test_load_creates_default_state(store):
    assert store.current_member == "guest"

    assert store.state["members"]["guest"]["display_name"] == "guest"
    assert store.state["shared"]["notes"] == []
    assert store.state["events"] == []
    assert store.state["shopping_list"] == []
    assert store.state["messages"] == []


def test_load_recovers_from_broken_json(tmp_path):
    path = tmp_path / "family_state.json"
    path.write_text("{broken json", encoding="utf-8")

    store = FamilyStore.load(path)

    assert store.current_member == "guest"
    assert store.state["events"] == []


def test_switch_member_and_reload(store):
    result = store.handle_command("私は凪です")

    assert result.handled is True
    assert store.current_member == "凪"
    assert store.state["members"]["凪"]["display_name"] == "凪"

    reloaded = FamilyStore.load(store.path)

    assert reloaded.current_member == "凪"
    assert reloaded.state["members"]["凪"]["display_name"] == "凪"


def test_empty_input_is_not_handled(store):
    result = store.handle_command("   ")

    assert result.handled is False
    assert result.message is None


def test_unknown_command_is_not_handled(store):
    result = store.handle_command("今日はいい天気ですね")

    assert result.handled is False


def test_add_personal_memory(store):
    store.handle_command("私は凪です")

    result = store.handle_command("朝は短く話してほしいって覚えておいて")

    assert result.handled is True
    assert store.state["members"]["凪"]["notes"] == [
        "朝は短く話してほしい"
    ]


def test_same_memory_is_not_added_twice(store):
    store.handle_command("私は凪です")

    store.handle_command("朝は短く話してほしいって覚えておいて")
    store.handle_command("朝は短く話してほしいって覚えておいて")

    assert store.state["members"]["凪"]["notes"] == [
        "朝は短く話してほしい"
    ]


def test_add_shared_family_memory(store):
    result = store.handle_command(
        "家族のこととしてゴミ出しは火曜と金曜って覚えておいて"
    )

    assert result.handled is True
    assert store.state["shared"]["notes"] == [
        "ゴミ出しは火曜と金曜"
    ]


def test_add_preference(store):
    store.handle_command("私は凪です")

    result = store.handle_command("カレーが好き")

    assert result.handled is True
    assert store.state["members"]["凪"]["preferences"] == [
        "カレーが好き"
    ]


def test_add_shopping_item(store):
    store.handle_command("私は凪です")

    result = store.handle_command("買い物リストに牛乳を入れて")

    assert result.handled is True
    assert len(store.state["shopping_list"]) == 1

    item = store.state["shopping_list"][0]

    assert item["text"] == "牛乳"
    assert item["added_by"] == "凪"
    assert item["done"] is False
    assert item["id"]


def test_show_shopping_list(store):
    store.handle_command("買い物リストに牛乳を入れて")
    store.handle_command("買い物リストに卵を入れて")

    result = store.handle_command("買い物リストを見せて")

    assert result.handled is True
    assert "牛乳" in result.message
    assert "卵" in result.message


def test_complete_shopping_item(store):
    store.handle_command("買い物リストに牛乳を入れて")

    result = store.handle_command("牛乳を買った")

    assert result.handled is True
    assert store.state["shopping_list"][0]["done"] is True
    assert "done_at" in store.state["shopping_list"][0]


def test_completed_item_is_hidden_from_shopping_list(store):
    store.handle_command("買い物リストに牛乳を入れて")
    store.handle_command("牛乳を買った")

    result = store.handle_command("買い物リストを見せて")

    assert result.handled is True
    assert result.message == "買い物メモは空だよ。"


def test_add_schedule(store):
    store.handle_command("私は凪です")

    result = store.handle_command(
        "明日16時に歯医者の予定を入れて"
    )

    assert result.handled is True
    assert len(store.state["events"]) == 1

    event = store.state["events"][0]

    assert event["owner"] == "凪"
    assert event["title"] == "歯医者"
    assert event["date"] == "明日"
    assert event["time"] == "16:00"


def test_events_are_sorted_by_date_and_time(store):
    store.state["events"] = [
        {
            "id": "2",
            "owner": "guest",
            "title": "夕食",
            "date": "明日",
            "time": "18:00",
        },
        {
            "id": "1",
            "owner": "guest",
            "title": "歯医者",
            "date": "明日",
            "time": "10:00",
        },
    ]

    events = store.events_for("guest")

    assert [event["title"] for event in events] == [
        "歯医者",
        "夕食",
    ]


def test_send_and_receive_message(store):
    store.handle_command("私は凪です")
    send_result = store.handle_command(
        "お母さんに、帰りに牛乳お願いって伝えて"
    )

    assert send_result.handled is True
    assert len(store.state["messages"]) == 1
    assert store.state["messages"][0]["delivered"] is False

    store.handle_command("私はお母さんです")
    receive_result = store.handle_command("伝言ある？")

    assert receive_result.handled is True
    assert "凪さんから" in receive_result.message
    assert "帰りに牛乳お願い" in receive_result.message
    assert store.state["messages"][0]["delivered"] is True


def test_context_for_prompt_contains_family_information(store):
    store.handle_command("私は凪です")
    store.handle_command("カレーが好き")
    store.handle_command("朝は短く話してほしいって覚えておいて")
    store.handle_command("買い物リストに牛乳を入れて")

    context = store.context_for_prompt()

    assert "今話している家族: 凪" in context
    assert "カレーが好き" in context
    assert "朝は短く話してほしい" in context
    assert "牛乳" in context


def test_saved_file_is_valid_json(store):
    store.handle_command("買い物リストに牛乳を入れて")

    saved = json.loads(store.path.read_text(encoding="utf-8"))

    assert saved["shopping_list"][0]["text"] == "牛乳"