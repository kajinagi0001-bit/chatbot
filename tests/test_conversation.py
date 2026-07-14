import pytest

from family_chatbot.conversation import detect_style


@pytest.mark.parametrize(
    ("user_input", "expected_style"),
    [
        ("検索: 今日の天気", "search"),
        ("今日の天気を調べて", "search"),
        ("最近少し疲れています", "support"),
        ("明日の予定を確認したい", "task"),
        ("買い物について相談したい", "task"),
        ("なぜ空は青いのですか", "thinking"),
        ("今日はいい天気だね", "chat"),
    ],
)
def test_detect_style(user_input, expected_style):
    style = detect_style(user_input)

    assert style.name == expected_style


def test_search_style_has_preface():
    style = detect_style("最新ニュースを検索して")

    assert style.name == "search"
    assert style.preface == "うん、調べてみるね。"


def test_thinking_style_has_preface():
    style = detect_style("この仕組みを詳しく説明してください")

    assert style.name == "thinking"
    assert style.preface == "うん、少し考えるね。"


def test_chat_style_does_not_have_preface():
    style = detect_style("おはよう")

    assert style.name == "chat"
    assert style.preface is None


def test_search_takes_priority_over_long_question():
    user_input = (
        "今日の天気について詳しく説明してほしいので、"
        "インターネットで調べてください"
    )

    style = detect_style(user_input)

    assert style.name == "search"