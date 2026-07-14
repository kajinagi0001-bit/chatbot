import pytest

from family_chatbot.speech_text import prepare_for_speech


def test_remove_inline_code_marker():
    result = prepare_for_speech(
        "`python chatbot.py`を実行してください"
    )

    assert "`" not in result
    assert "python chatbot.py" in result


def test_replace_code_block():
    text = """
次のコードです。

```python
print("hello")
```

確認してください。
"""

    result = prepare_for_speech(text)

    assert "print" not in result
    assert "コード部分は省略するね。" in result

def test_replace_url():
    result = prepare_for_speech(
    "詳細はhttps://example.comを確認してください"
    )

    assert "https://" not in result
    assert "リンク" in result

@pytest.mark.parametrize(
("source", "expected"),
[
("OpenAI", "オープンエーアイ"),
("API", "エーピーアイ"),
("TTS", "ティーティーエス"),
("LLM", "エルエルエム"),
("Raspberry Pi", "ラズベリーパイ"),
],
)
def test_replace_technical_terms(source, expected):
    result = prepare_for_speech(source)

    assert result == expected

def test_replace_colons():
    result = prepare_for_speech("予定: 10時：出発")

    assert ":" not in result
    assert "：" not in result
    assert result == "予定。 10時。出発"    

def test_remove_markdown_list_markers():
    text = """
- 牛乳
* 卵
1. パン
    """

    result = prepare_for_speech(text)

    assert "- 牛乳" not in result
    assert "* 卵" not in result
    assert "1. パン" not in result

    assert "牛乳" in result
    assert "卵" in result
    assert "パン" in result

def test_normalize_line_breaks_and_spaces():
    result = prepare_for_speech(
    "今日は 晴れです。\n\n散歩できます。"
    )

    assert "   " not in result
    assert "\n" not in result
    assert "。。" not in result

def test_strip_outer_whitespace():
    result = prepare_for_speech(" おはよう ")

    assert result == "おはよう"