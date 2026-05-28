import re


SYMBOL_REPLACEMENTS = {
    "OpenAI": "オープンエーアイ",
    "API": "エーピーアイ",
    "TTS": "ティーティーエス",
    "LLM": "エルエルエム",
    "Raspberry Pi": "ラズベリーパイ",
}


def prepare_for_speech(text: str) -> str:
    spoken = text.strip()
    spoken = re.sub(r"```.*?```", "コード部分は省略するね。", spoken, flags=re.DOTALL)
    spoken = re.sub(r"`([^`]+)`", r"\1", spoken)
    spoken = re.sub(r"https?://\S+", "リンク", spoken)

    for before, after in SYMBOL_REPLACEMENTS.items():
        spoken = spoken.replace(before, after)

    spoken = spoken.replace(":", "。")
    spoken = spoken.replace("：", "。")
    spoken = spoken.replace("・", "、")
    spoken = re.sub(r"^[\-\*\d]+[.)、]\s*", "", spoken, flags=re.MULTILINE)
    spoken = re.sub(r"\n+", "。", spoken)
    spoken = re.sub(r"\s+", " ", spoken)
    spoken = re.sub(r"。。+", "。", spoken)
    return spoken.strip()
