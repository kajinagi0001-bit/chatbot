from family_chatbot.shopping_service import ShoppingService


def make_service(
    state=None,
    current_member="guest",
):
    if state is None:
        state = {
            "shopping_list": [],
        }

    save_count = {
        "value": 0,
    }

    def save():
        save_count["value"] += 1

    service = ShoppingService(
        state=state,
        current_member=current_member,
        save=save,
    )

    return service, state, save_count


def test_add_shopping_item():
    service, state, save_count = make_service(
        current_member="凪"
    )

    result = service.handle_command(
        "買い物リストに牛乳を入れて"
    )

    assert result.handled is True
    assert result.message == (
        "買い物メモに「牛乳」を入れたよ。"
    )

    assert len(state["shopping_list"]) == 1

    item = state["shopping_list"][0]

    assert item["text"] == "牛乳"
    assert item["added_by"] == "凪"
    assert item["done"] is False
    assert item["id"]
    assert item["created_at"]

    assert save_count["value"] == 1


def test_show_shopping_items():
    state = {
        "shopping_list": [
            {
                "text": "牛乳",
                "done": False,
            },
            {
                "text": "卵",
                "done": False,
            },
        ]
    }

    service, _, save_count = make_service(
        state=state
    )

    result = service.handle_command(
        "買い物リストを見せて"
    )

    assert result.handled is True
    assert result.message == (
        "買い物メモは、牛乳、卵だよ。"
    )
    assert save_count["value"] == 0


def test_show_empty_shopping_list():
    service, _, _ = make_service()

    result = service.handle_command(
        "買い物リストを見せて"
    )

    assert result.handled is True
    assert result.message == (
        "買い物メモは空だよ。"
    )


def test_completed_items_are_hidden():
    state = {
        "shopping_list": [
            {
                "text": "牛乳",
                "done": True,
            },
            {
                "text": "卵",
                "done": False,
            },
        ]
    }

    service, _, _ = make_service(
        state=state
    )

    assert service.active_item_names() == [
        "卵"
    ]


def test_complete_shopping_item():
    state = {
        "shopping_list": [
            {
                "text": "牛乳",
                "done": False,
            }
        ]
    }

    service, _, save_count = make_service(
        state=state
    )

    result = service.handle_command(
        "牛乳を買った"
    )

    assert result.handled is True
    assert state["shopping_list"][0]["done"] is True
    assert state["shopping_list"][0]["done_at"]
    assert save_count["value"] == 1


def test_unknown_item_is_not_completed():
    state = {
        "shopping_list": [
            {
                "text": "牛乳",
                "done": False,
            }
        ]
    }

    service, _, save_count = make_service(
        state=state
    )

    result = service.handle_command(
        "パンを買った"
    )

    assert result.handled is False
    assert state["shopping_list"][0]["done"] is False
    assert save_count["value"] == 0


def test_unrelated_text_is_not_handled():
    service, state, save_count = make_service()

    result = service.handle_command(
        "今日はいい天気ですね"
    )

    assert result.handled is False
    assert state["shopping_list"] == []
    assert save_count["value"] == 0

def test_add_item_directly():
    service, state, save_count = make_service(
        current_member="凪"
    )

    result = service.add_item("牛乳")

    assert result.handled is True
    assert state["shopping_list"][0]["text"] == "牛乳"
    assert state["shopping_list"][0]["added_by"] == "凪"
    assert save_count["value"] == 1


def test_complete_item_directly():
    state = {
        "shopping_list": [
            {
                "id": "item1",
                "text": "牛乳",
                "done": False,
            }
        ]
    }

    service, _, save_count = make_service(
        state=state
    )

    result = service.complete_item("牛乳")

    assert result.handled is True
    assert state["shopping_list"][0]["done"] is True
    assert save_count["value"] == 1