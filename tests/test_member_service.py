from family_chatbot.member_service import MemberService


def make_service(state=None):
    if state is None:
        state = {
            "current_member": "guest",
            "members": {
                "guest": {
                    "display_name": "guest",
                    "notes": [],
                    "preferences": [],
                }
            },
        }

    save_count = {
        "value": 0,
    }

    def save():
        save_count["value"] += 1

    service = MemberService(
        state=state,
        save=save,
    )

    return service, state, save_count


def test_current_member():
    service, _, _ = make_service()

    assert service.current_member == "guest"


def test_switch_member():
    service, state, save_count = make_service()

    result = service.handle_command(
        "私は凪です"
    )

    assert result.handled is True
    assert state["current_member"] == "凪"
    assert state["members"]["凪"]["display_name"] == "凪"
    assert state["members"]["凪"]["notes"] == []
    assert state["members"]["凪"]["preferences"] == []
    assert save_count["value"] == 1


def test_switch_member_with_polite_sentence():
    service, state, _ = make_service()

    result = service.handle_command(
        "わたしはお母さんです。"
    )

    assert result.handled is True
    assert state["current_member"] == "お母さん"


def test_switch_member_with_explicit_command():
    service, state, _ = make_service()

    result = service.handle_command(
        "凪として話して"
    )

    assert result.handled is True
    assert state["current_member"] == "凪"


def test_switch_member_with_change_command():
    service, state, _ = make_service()

    result = service.handle_command(
        "お父さんに切り替えて"
    )

    assert result.handled is True
    assert state["current_member"] == "お父さん"


def test_existing_member_data_is_preserved():
    state = {
        "current_member": "guest",
        "members": {
            "guest": {
                "display_name": "guest",
                "notes": [],
                "preferences": [],
            },
            "凪": {
                "display_name": "凪",
                "notes": [
                    "朝は短く話してほしい"
                ],
                "preferences": [
                    "カレーが好き"
                ],
            },
        },
    }

    service, _, _ = make_service(state)

    service.handle_command(
        "私は凪です"
    )

    assert state["members"]["凪"]["notes"] == [
        "朝は短く話してほしい"
    ]
    assert state["members"]["凪"]["preferences"] == [
        "カレーが好き"
    ]


def test_get_member_creates_missing_member():
    service, state, _ = make_service()

    member = service.get_member(
        "お母さん"
    )

    assert member["display_name"] == "お母さん"
    assert member["notes"] == []
    assert member["preferences"] == []
    assert "お母さん" in state["members"]


def test_get_member_repairs_missing_fields():
    state = {
        "current_member": "guest",
        "members": {
            "guest": {
                "display_name": "guest",
            }
        },
    }

    service, _, _ = make_service(state)

    member = service.get_member("guest")

    assert member["notes"] == []
    assert member["preferences"] == []


def test_display_name():
    state = {
        "current_member": "nagi",
        "members": {
            "nagi": {
                "display_name": "凪",
                "notes": [],
                "preferences": [],
            }
        },
    }

    service, _, _ = make_service(state)

    assert service.display_name() == "凪"
    assert service.display_name("nagi") == "凪"


def test_normalize_member_id():
    assert (
        MemberService.normalize_member_id(
            " Nagi Kajita "
        )
        == "nagi_kajita"
    )


def test_unrelated_text_is_not_handled():
    service, state, save_count = make_service()

    result = service.handle_command(
        "今日はいい天気ですね"
    )

    assert result.handled is False
    assert state["current_member"] == "guest"
    assert save_count["value"] == 0