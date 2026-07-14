import json

from openai import OpenAI

from .config import AppConfig


FAMILY_COMMAND_TOOL = {
    "type": "function",
    "function": {
        "name": "normalize_family_command",
        "description": (
            "家族チャットボットの管理機能に該当する発話を、"
            "既存プログラムが処理できる定型文へ変換する。"
            "雑談や質問の場合は呼び出さない。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "canonical_text": {
                    "type": "string",
                    "description": (
                        "既存のFamilyStore.handle_commandで"
                        "処理できる日本語の定型コマンド"
                    ),
                },
                "category": {
                    "type": "string",
                    "enum": [
                        "member",
                        "memory",
                        "shopping",
                        "schedule",
                        "message",
                    ],
                },
            },
            "required": [
                "canonical_text",
                "category",
            ],
            "additionalProperties": False,
        },
        "strict": True,
    },
}


class FamilyCommandRouter:
    """自然な発話を既存の家族コマンドへ正規化する。"""

    def __init__(
        self,
        config: AppConfig,
        client: OpenAI | None = None,
    ):
        self.config = config
        self.client = client or OpenAI(
            api_key=config.openai_api_key
        )

    def route(self, user_input: str) -> str | None:
        """家族機能なら定型コマンドを返し、それ以外はNoneを返す。"""
        if not user_input.strip():
            return None

        try:
            response = self.client.chat.completions.create(
                model=self.config.llm_model,
                messages=[
                    {
                        "role": "system",
                        "content": self._system_instruction(),
                    },
                    {
                        "role": "user",
                        "content": user_input,
                    },
                ],
                tools=[FAMILY_COMMAND_TOOL],
                tool_choice="auto",
                temperature=0,
                max_tokens=120,
            )
        except Exception as error:
            print(
                "家族コマンドの判定に失敗しました: "
                f"{error}"
            )
            return None

        message = response.choices[0].message
        tool_calls = message.tool_calls or []

        for tool_call in tool_calls:
            if (
                tool_call.function.name
                != "normalize_family_command"
            ):
                continue

            try:
                arguments = json.loads(
                    tool_call.function.arguments
                )
            except (
                TypeError,
                json.JSONDecodeError,
            ):
                return None

            canonical_text = arguments.get(
                "canonical_text"
            )

            if not isinstance(canonical_text, str):
                return None

            canonical_text = canonical_text.strip()

            return canonical_text or None

        return None

    @staticmethod
    def _system_instruction() -> str:
        return """
あなたは家庭用チャットボットのコマンド分類器です。

発話が次の管理操作に該当する場合だけ、
normalize_family_commandを呼び出してください。

対応する操作:
- 話者の切り替え
- 個人または家族共通の記憶
- 好みの記録
- 買い物リストの追加、表示、完了
- 予定の追加、表示
- 家族への伝言、伝言の確認

雑談、相談、一般質問、検索、日時の質問では、
ツールを呼び出さないでください。

canonical_textは、次の形式に合わせてください。

話者:
- 私は凪です
- お母さんに切り替えて

記憶:
- 朝は短く話してほしいって覚えておいて
- 家族のこととしてゴミ出しは火曜って覚えておいて
- カレーが好き

買い物:
- 買い物リストに牛乳を入れて
- 買い物リストを見せて
- 牛乳を買った

予定:
- 明日16時に歯医者の予定を入れて
- 予定を教えて
- 家族の予定を見せて

伝言:
- お母さんに帰りが遅くなるって伝えて
- 伝言ある？

元の発話にない商品、日時、人名、内容を追加してはいけません。
日時が不明なら勝手に補完しないでください。
""".strip()