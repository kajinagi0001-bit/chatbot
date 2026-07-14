from family_chatbot.message_service import MessageService


def make_service(
    state=None,
    current_member="guest",
):
    if state is None:
        state = {
            "members": {
                "guest": {
                    "display_name": "guest",
                }
            },
            "messages": [],
        }

    save_count = {
        "value": 0,
    }

    def save():
        save_count["value"] += 1

    def get_member(member_id):
        members = state["members"]

        if member_id not in members:
            members[member_id] = {
                "display_name": member_id,
            }

        return members[member_id]

    def normalize_member_id(name):
        return name.strip().lower().replace(
            " ",
            "_",
        )

    service = MessageService(
        state=state,
        current_member=current_member,
        save=save,
        get_member=get_member,
        normalize_member_id=normalize_member_id,
    )

    return service, state, save_count


def test_send_message():
    service, state, save_count = make_service(
        current_member="凪"
    )

    result = service.handle_command(
        "お母さんに、帰りに牛乳お願いって伝えて"
    )

    assert result.handled is True
    assert len(state["messages"]) == 1

    message = state["messages"][0]

    assert message["from"] == "凪"
    assert message["to"] == "お母さん"
    assert message["text"] == "帰りに牛乳お願い"
    assert message["delivered"] is False
    assert message["id"]
    assert message["created_at"]

    assert save_count["value"] == 1


def test_send_message_creates_recipient():
    service, state, _ = make_service()

    service.handle_command(
        "お父さんに夕食は7時って伝えて"
    )

    assert "お父さん" in state["members"]
    assert (
        state["members"]["お父さん"]["display_name"]
        == "お父さん"
    )


def test_receive_message():
    state = {
        "members": {
            "凪": {
                "display_name": "凪",
            },
            "お母さん": {
                "display_name": "お母さん",
            },
        },
        "messages": [
            {
                "id": "message1",
                "from": "凪",
                "to": "お母さん",
                "text": "帰りに牛乳お願い",
                "delivered": False,
                "created_at": "2026-07-14T10:00:00",
            }
        ],
    }

    service, _, save_count = make_service(
        state=state,
        current_member="お母さん",
    )

    result = service.handle_command(
        "伝言ある？"
    )

    assert result.handled is True
    assert "凪さんから" in result.message
    assert "帰りに牛乳お願い" in result.message

    message = state["messages"][0]

    assert message["delivered"] is True
    assert message["delivered_at"]
    assert save_count["value"] == 1


def test_delivered_message_is_not_returned_again():
    state = {
        "members": {
            "凪": {
                "display_name": "凪",
            },
            "お母さん": {
                "display_name": "お母さん",
            },
        },
        "messages": [
            {
                "id": "message1",
                "from": "凪",
                "to": "お母さん",
                "text": "帰りに牛乳お願い",
                "delivered": True,
            }
        ],
    }

    service, _, save_count = make_service(
        state=state,
        current_member="お母さん",
    )

    result = service.handle_command(
        "伝言ある？"
    )

    assert result.handled is True
    assert result.message == (
        "今のところ伝言はないよ。"
    )
    assert save_count["value"] == 0


def test_message_is_only_received_by_recipient():
    state = {
        "members": {
            "凪": {
                "display_name": "凪",
            },
            "お母さん": {
                "display_name": "お母さん",
            },
            "お父さん": {
                "display_name": "お父さん",
            },
        },
        "messages": [
            {
                "id": "message1",
                "from": "凪",
                "to": "お母さん",
                "text": "帰りに牛乳お願い",
                "delivered": False,
            }
        ],
    }

    service, _, _ = make_service(
        state=state,
        current_member="お父さん",
    )

    result = service.handle_command(
        "伝言ある？"
    )

    assert result.message == (
        "今のところ伝言はないよ。"
    )
    assert state["messages"][0]["delivered"] is False


def test_receive_multiple_messages():
    state = {
        "members": {
            "凪": {
                "display_name": "凪",
            },
            "お父さん": {
                "display_name": "お父さん",
            },
            "お母さん": {
                "display_name": "お母さん",
            },
        },
        "messages": [
            {
                "id": "message1",
                "from": "凪",
                "to": "お母さん",
                "text": "牛乳お願い",
                "delivered": False,
            },
            {
                "id": "message2",
                "from": "お父さん",
                "to": "お母さん",
                "text": "少し遅くなる",
                "delivered": False,
            },
        ],
    }

    service, _, _ = make_service(
        state=state,
        current_member="お母さん",
    )

    result = service.handle_command(
        "伝言を教えて"
    )

    assert "牛乳お願い" in result.message
    assert "少し遅くなる" in result.message

    assert all(
        message["delivered"]
        for message in state["messages"]
    )


def test_unrelated_text_is_not_handled():
    service, state, save_count = make_service()

    result = service.handle_command(
        "今日はいい天気ですね"
    )

    assert result.handled is False
    assert state["messages"] == []
    assert save_count["value"] == 0

def test_send_message_directly():
    service, state, save_count = make_service(
        current_member="凪"
    )

    result = service.send_message(
        recipient="お母さん",
        body="帰りに牛乳お願い",
    )

    assert result.handled is True
    assert state["messages"][0]["to"] == "お母さん"
    assert state["messages"][0]["text"] == (
        "帰りに牛乳お願い"
    )
    assert save_count["value"] == 1