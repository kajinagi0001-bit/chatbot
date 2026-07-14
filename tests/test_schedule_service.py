from family_chatbot.schedule_service import ScheduleService


def make_service(
    state=None,
    current_member="guest",
):
    if state is None:
        state = {
            "events": [],
            "members": {
                "guest": {
                    "display_name": "guest",
                }
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
            }

        return members[member_id]

    def normalize_member_id(name):
        return name.strip().lower().replace(
            " ",
            "_",
        )

    service = ScheduleService(
        state=state,
        current_member=current_member,
        save=save,
        get_member=get_member,
        normalize_member_id=normalize_member_id,
    )

    return service, state, save_count


def test_add_schedule():
    service, state, save_count = make_service(
        current_member="凪"
    )

    result = service.handle_command(
        "明日16時に歯医者の予定を入れて"
    )

    assert result.handled is True
    assert len(state["events"]) == 1

    event = state["events"][0]

    assert event["owner"] == "凪"
    assert event["title"] == "歯医者"
    assert event["date"] == "明日"
    assert event["time"] == "16:00"
    assert event["id"]
    assert event["created_at"]

    assert save_count["value"] == 1


def test_add_schedule_without_time():
    service, state, _ = make_service()

    result = service.handle_command(
        "明日に通院の予定を入れて"
    )

    assert result.handled is True

    event = state["events"][0]

    assert event["date"] == "明日"
    assert event["time"] == ""
    assert event["title"] == "通院"


def test_add_schedule_with_calendar_date():
    service, state, _ = make_service()

    service.handle_command(
        "7月20日10時に病院の予定を入れて"
    )

    event = state["events"][0]

    assert event["date"] == "7月20日"
    assert event["time"] == "10:00"
    assert event["title"] == "病院"


def test_add_schedule_for_family():
    service, state, _ = make_service()

    result = service.handle_command(
        "家族の予定に明日18時夕食を登録して"
    )

    assert result.handled is True
    assert state["events"][0]["owner"] == "家族"


def test_add_schedule_for_another_member():
    service, state, _ = make_service()

    result = service.handle_command(
        "お母さんの予定に明日10時病院を登録して"
    )

    assert result.handled is True
    assert state["events"][0]["owner"] == "お母さん"
    assert (
        state["members"]["お母さん"]["display_name"]
        == "お母さん"
    )


def test_show_current_member_schedule():
    state = {
        "events": [
            {
                "owner": "凪",
                "title": "歯医者",
                "date": "明日",
                "time": "16:00",
            },
            {
                "owner": "母",
                "title": "買い物",
                "date": "明日",
                "time": "10:00",
            },
        ],
        "members": {
            "凪": {
                "display_name": "凪",
            }
        },
    }

    service, _, save_count = make_service(
        state=state,
        current_member="凪",
    )

    result = service.handle_command(
        "予定を教えて"
    )

    assert result.handled is True
    assert "歯医者" in result.message
    assert "買い物" not in result.message
    assert save_count["value"] == 0


def test_family_event_is_shown_for_member():
    state = {
        "events": [
            {
                "owner": "家族",
                "title": "外食",
                "date": "明日",
                "time": "18:00",
            }
        ],
        "members": {
            "凪": {
                "display_name": "凪",
            }
        },
    }

    service, _, _ = make_service(
        state=state,
        current_member="凪",
    )

    result = service.handle_command(
        "予定を確認して"
    )

    assert result.handled is True
    assert "外食" in result.message


def test_show_all_family_schedules():
    state = {
        "events": [
            {
                "owner": "凪",
                "title": "歯医者",
                "date": "明日",
                "time": "16:00",
            },
            {
                "owner": "母",
                "title": "買い物",
                "date": "明日",
                "time": "10:00",
            },
        ],
        "members": {},
    }

    service, _, _ = make_service(
        state=state,
        current_member="凪",
    )

    result = service.handle_command(
        "家族の予定を見せて"
    )

    assert result.handled is True
    assert "歯医者" in result.message
    assert "買い物" in result.message


def test_show_empty_schedule():
    service, _, _ = make_service()

    result = service.handle_command(
        "予定を教えて"
    )

    assert result.handled is True
    assert result.message == (
        "今のところ予定は入っていないよ。"
    )


def test_events_are_sorted():
    state = {
        "events": [
            {
                "owner": "guest",
                "title": "夕食",
                "date": "明日",
                "time": "18:00",
            },
            {
                "owner": "guest",
                "title": "歯医者",
                "date": "明日",
                "time": "10:00",
            },
        ],
        "members": {
            "guest": {
                "display_name": "guest",
            }
        },
    }

    service, _, _ = make_service(state=state)

    events = service.events_for("guest")

    assert [
        event["title"]
        for event in events
    ] == [
        "歯医者",
        "夕食",
    ]


def test_unrelated_text_is_not_handled():
    service, state, save_count = make_service()

    result = service.handle_command(
        "今日はいい天気ですね"
    )

    assert result.handled is False
    assert state["events"] == []
    assert save_count["value"] == 0