from family_chatbot.family_context import (
    FamilyContextBuilder,
)


def make_builder(
    state=None,
    current_member="凪",
):
    if state is None:
        state = {
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
            "shopping_list": [],
            "messages": [],
        }

    def get_member(member_id):
        return state["members"][member_id]

    def events_for(owner=None):
        events = state["events"]

        if owner is None:
            return events

        return [
            event
            for event in events
            if event["owner"] in {
                owner,
                "家族",
            }
        ]

    def format_event(event):
        date = event.get("date", "日付未設定")
        time = event.get("time", "")
        title = event.get("title", "予定")

        if time:
            return f"{date}{time}に{title}"

        return f"{date}に{title}"

    builder = FamilyContextBuilder(
        state=state,
        current_member=current_member,
        get_member=get_member,
        events_for=events_for,
        format_event=format_event,
    )

    return builder


def test_context_contains_current_member():
    builder = make_builder()

    context = builder.build()

    assert "今話している家族: 凪" in context


def test_context_contains_personal_notes():
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
        "events": [],
        "shopping_list": [],
        "messages": [],
    }

    context = make_builder(state).build()

    assert "この人について覚えていること" in context
    assert "朝は短く話してほしい" in context


def test_context_contains_preferences():
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
        "events": [],
        "shopping_list": [],
        "messages": [],
    }

    context = make_builder(state).build()

    assert "この人の好み" in context
    assert "カレーが好き" in context


def test_context_contains_shared_notes():
    state = {
        "members": {
            "凪": {
                "display_name": "凪",
                "notes": [],
                "preferences": [],
            }
        },
        "shared": {
            "notes": [
                "ゴミ出しは火曜と金曜"
            ],
        },
        "events": [],
        "shopping_list": [],
        "messages": [],
    }

    context = make_builder(state).build()

    assert "家族共通の情報" in context
    assert "ゴミ出しは火曜と金曜" in context


def test_context_contains_schedule():
    state = {
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
        "events": [
            {
                "owner": "凪",
                "title": "歯医者",
                "date": "明日",
                "time": "16:00",
            }
        ],
        "shopping_list": [],
        "messages": [],
    }

    context = make_builder(state).build()

    assert "現在の予定" in context
    assert "明日16:00に歯医者" in context


def test_context_contains_active_shopping_items():
    state = {
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
                "text": "牛乳",
                "done": False,
            },
            {
                "text": "卵",
                "done": True,
            },
        ],
        "messages": [],
    }

    context = make_builder(state).build()

    assert "現在の買い物メモ" in context
    assert "牛乳" in context
    assert "卵" not in context


def test_pending_message_content_is_not_exposed():
    state = {
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
        "shopping_list": [],
        "messages": [
            {
                "from": "母",
                "to": "凪",
                "text": "冷蔵庫にケーキがある",
                "delivered": False,
            }
        ],
    }

    context = make_builder(state).build()

    assert "未確認の伝言がある" in context
    assert "冷蔵庫にケーキがある" not in context


def test_delivered_message_is_not_mentioned():
    state = {
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
        "shopping_list": [],
        "messages": [
            {
                "from": "母",
                "to": "凪",
                "text": "帰宅が遅くなる",
                "delivered": True,
            }
        ],
    }

    context = make_builder(state).build()

    assert "未確認の伝言がある" not in context


def test_empty_sections_are_not_output():
    context = make_builder().build()

    assert "今話している家族: 凪" in context
    assert "この人の好み" not in context
    assert "現在の予定" not in context
    assert "現在の買い物メモ" not in context