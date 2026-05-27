import json
from pathlib import Path

from openai import OpenAI

from .config import AppConfig, DEFAULT_FEEDBACK


class ConversationMemory:
    def __init__(self, path: Path, system_prompt: str):
        self.path = path
        self.system_prompt = system_prompt
        self.messages = self._load()
        if not self.messages or self.messages[0].get("role") != "system":
            self.messages.insert(0, {"role": "system", "content": system_prompt})

    def add_user(self, content: str) -> None:
        self.messages.append({"role": "user", "content": content})

    def add_assistant(self, content: str) -> None:
        self.messages.append({"role": "assistant", "content": content})

    def replace_with_summary(self, summary: str) -> None:
        self.system_prompt = (
            "あなたは家庭で使われる、あたたかく落ち着いたAIチャットボットです。"
            "以下の会話要約を覚えたうえで、ユーザーを新しい家族のように支えてください。"
            f"\n会話要約: {summary}\n会話スタイル: {DEFAULT_FEEDBACK}"
        )
        self.messages = [{"role": "system", "content": self.system_prompt}]

    def turn_count(self) -> int:
        return sum(1 for message in self.messages if message.get("role") == "assistant")

    def save(self) -> None:
        self.path.write_text(json.dumps(self.messages, ensure_ascii=False, indent=2), encoding="utf-8")

    def _load(self) -> list[dict[str, str]]:
        if not self.path.exists():
            return []
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            print(f"会話履歴を読み込めませんでした: {error}")
            return []
        return data if isinstance(data, list) else []


def summarize_conversation(client: OpenAI, config: AppConfig, messages: list[dict[str, str]]) -> str:
    conversation_text = "\n".join(
        f"{message['role']}: {message['content']}"
        for message in messages
        if message.get("role") in {"user", "assistant"}
    )
    if not conversation_text:
        return "まだ会話はありません。"

    response = client.chat.completions.create(
        model=config.llm_model,
        messages=[
            {"role": "system", "content": "あなたは会話履歴を短く整理するアシスタントです。"},
            {
                "role": "user",
                "content": (
                    "家庭用チャットボットが次回以降も自然に寄り添えるよう、"
                    "好み、予定、相談内容、覚えておくべきことを簡潔に要約してください。\n\n"
                    f"{conversation_text}"
                ),
            },
        ],
        max_tokens=220,
        temperature=0.2,
    )
    return response.choices[0].message.content.strip()
