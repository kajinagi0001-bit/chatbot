from family_chatbot.memory_service import MemoryService


def make_service(
    state=None,
    current_member="guest",
):
    if state is None:
        state = {
            "members": {
                "guest": {
                    "display_name": "guest",
                    "notes": [],
                    "preferences": [],
                }
            },
            "shared": {
                "notes": [],
            },
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
                "notes": [],
                "preferences": [],
            }

        return members[member_id]

    service = MemoryService(
        state=state,
        current_member=current_member,
        save=save,
        get_member=get_member,
    )

    return service, state, save_count


def test_add_personal_memory():
    service, state, save_count = make_service(
        current_member="凪"
    )

    result = service.handle_command(
        "朝は短く話してほしいって覚えておいて"
    )

    assert result.handled is True
    assert state["members"]["凪"]["notes"] == [
        "朝は短く話してほしい"
    ]
    assert save_count["value"] == 1


def test_duplicate_personal_memory_is_not_added():
    state = {
        "members": {
            "凪": {
                "display_name": "凪",
                "notes": [
                    "朝は短く話してほしい"
                ],
                "preferences": [],
            }
        },
        "shared": {
            "notes": [],
        },
    }

    service, _, save_count = make_service(
        state=state,
        current_member="凪",
    )

    result = service.handle_command(
        "朝は短く話してほしいって覚えておいて"
    )

    assert result.handled is True
    assert state["members"]["凪"]["notes"] == [
        "朝は短く話してほしい"
    ]
    assert save_count["value"] == 0


def test_add_shared_memory():
    service, state, save_count = make_service()

    result = service.handle_command(
        "家族のこととしてゴミ出しは火曜と金曜って覚えておいて"
    )

    assert result.handled is True
    assert state["shared"]["notes"] == [
        "ゴミ出しは火曜と金曜"
    ]
    assert save_count["value"] == 1


def test_duplicate_shared_memory_is_not_added():
    state = {
        "members": {
            "guest": {
                "display_name": "guest",
                "notes": [],
                "preferences": [],
            }
        },
        "shared": {
            "notes": [
                "ゴミ出しは火曜と金曜"
            ],
        },
    }

    service, _, save_count = make_service(
        state=state
    )

    result = service.handle_command(
        "家族のこととしてゴミ出しは火曜と金曜って覚えておいて"
    )

    assert result.handled is True
    assert state["shared"]["notes"] == [
        "ゴミ出しは火曜と金曜"
    ]
    assert save_count["value"] == 0


def test_add_like_preference():
    service, state, save_count = make_service(
        current_member="凪"
    )

    result = service.handle_command(
        "カレーが好き"
    )

    assert result.handled is True
    assert state["members"]["凪"]["preferences"] == [
        "カレーが好き"
    ]
    assert save_count["value"] == 1


def test_add_dislike_preference():
    service, state, _ = make_service(
        current_member="凪"
    )

    result = service.handle_command(
        "辛い料理が苦手です"
    )

    assert result.handled is True
    assert state["members"]["凪"]["preferences"] == [
        "辛い料理が苦手です"
    ]


def test_duplicate_preference_is_not_added():
    state = {
        "members": {
            "凪": {
                "display_name": "凪",
                "notes": [],
                "preferences": [
                    "カレーが好き"
                ],
            }
        },
        "shared": {
            "notes": [],
        },
    }

    service, _, save_count = make_service(
        state=state,
        current_member="凪",
    )

    result = service.handle_command(
        "カレーが好き"
    )

    assert result.handled is True
    assert state["members"]["凪"]["preferences"] == [
        "カレーが好き"
    ]
    assert save_count["value"] == 0


def test_personal_notes_returns_copy():
    service, state, _ = make_service()

    state["members"]["guest"]["notes"] = [
        "早起きする"
    ]

    notes = service.personal_notes()
    notes.append("追加")

    assert state["members"]["guest"]["notes"] == [
        "早起きする"
    ]


def test_shared_notes_returns_copy():
    service, state, _ = make_service()

    state["shared"]["notes"] = [
        "ゴミ出しは火曜"
    ]

    notes = service.shared_notes()
    notes.append("追加")

    assert state["shared"]["notes"] == [
        "ゴミ出しは火曜"
    ]


def test_unrelated_text_is_not_handled():
    service, state, save_count = make_service()

    result = service.handle_command(
        "今日はいい天気ですね"
    )

    assert result.handled is False
    assert state["members"]["guest"]["notes"] == []
    assert state["shared"]["notes"] == []
    assert save_count["value"] == 0