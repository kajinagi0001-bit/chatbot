import re
from datetime import datetime

from openai import OpenAI

from .config import AppConfig
from .conversation import ConversationStyle, detect_style
from .family import FamilyStore
from .memory import ConversationMemory, summarize_conversation
from .search import WebSearch


WEEKDAYS_JA = ["月曜日", "火曜日", "水曜日", "木曜日", "金曜日", "土曜日", "日曜日"]


class ChatBrain:
    def __init__(self, config: AppConfig, memory: ConversationMemory, search: WebSearch, family: FamilyStore):
        self.config = config
        self.memory = memory
        self.search = search
        self.family = family
        self.client = OpenAI(api_key=config.openai_api_key)

    def respond(self, user_input: str) -> str:
        style = detect_style(user_input)
        search_result = self._maybe_search(user_input)
        if search_result:
            self.memory.add_user(user_input)
            response = self._complete(
                style,
                extra_instruction=(
                    '次の検索結果を根拠として使ってください。'
                    '検索を求められた場合は、多少長くなってもよいので具体的に答えてください。'
                    '結論、重要な具体情報、家庭での判断材料、次の行動の順で、5〜8文を目安に返してください。'
                    '出典名、日付、場所、価格、営業時間、持ち物、注意点、手順があれば優先して含めてください。'
                    '検索結果にないことは補わず、不明点は不明と言ってください。\n\n'
                    f"{search_result}"
                ),
                max_tokens=self.config.search_answer_tokens,
            )
        elif user_input.strip() == "続けて":
            response = self._continue_last_response(style)
        else:
            self.memory.add_user(user_input)
            response = self._complete(style)

        self.memory.add_assistant(response)
        self._save_and_summarize_if_needed()
        return response

    def preface_for(self, user_input: str) -> str | None:
        return detect_style(user_input).preface


    def _current_datetime_context(self) -> str:
        now = datetime.now()
        weekday = WEEKDAYS_JA[now.weekday()]
        return f"現在日時: {now.year}年{now.month}月{now.day}日 {weekday} {now.hour}時{now.minute:02d}分"

    def _complete(self, style: ConversationStyle, extra_instruction: str | None = None, max_tokens: int | None = None) -> str:
        messages = list(self.memory.messages)
        messages.append({"role": "system", "content": self._current_datetime_context()})
        messages.append(
            {
                "role": "system",
                "content": (
                    "以下は家族ごとの記憶です。自然に必要な範囲だけ使い、"
                    "覚えている情報を大げさに言いすぎないでください。"
                    "予定、買い物、伝言、好みが関係する場合は、具体的な確認や次の行動に使ってください。\n"
                    f"{self.family.context_for_prompt()}"
                ),
            }
        )
        messages.append({"role": "system", "content": style.instruction})
        messages.append(
            {
                "role": "system",
                "content": (
                    "出力はそのまま音声合成します。自然な会話文だけを返してください。"
                    "見出し、箇条書き、Markdown、URLは使わないでください。"
                    "ただし生活支援では、具体的な行動を必ず1つは含めてください。"
                    "曖昧な共感だけ、一般論だけの返答は禁止です。"
                ),
            }
        )
        if extra_instruction:
            messages.append({"role": "system", "content": extra_instruction})

        try:
            response = self.client.chat.completions.create(
                model=self.config.llm_model,
                messages=messages,
                max_tokens=max_tokens or self.config.max_response_tokens,
                temperature=0.8,
            )
            return response.choices[0].message.content.strip()
        except Exception as error:
            return f"返答の生成中にエラーが発生しました: {error}"

    def _continue_last_response(self, style: ConversationStyle) -> str:
        for message in reversed(self.memory.messages):
            if message.get("role") == "assistant":
                self.memory.add_user(f"次の文章の続きを自然に話してください:\n{message['content'][-160:]}")
                return self._complete(style)
        self.memory.add_user("続けて")
        return self._complete(style)

    def _maybe_search(self, user_input: str) -> str | None:
        if user_input.startswith("検索:"):
            query = user_input.replace("検索:", "", 1).strip()
            return self.search.search(query)

        match = re.search(r"(.+?)を検索して", user_input)
        if match:
            return self.search.search(match.group(1).strip())

        return None

    def _save_and_summarize_if_needed(self) -> None:
        turn_count = self.memory.turn_count()
        if turn_count % self.config.save_interval_turns == 0:
            self.memory.save()

        if turn_count >= self.config.summary_interval_turns:
            try:
                summary = summarize_conversation(self.client, self.config, self.memory.messages)
                self.memory.replace_with_summary(summary)
            except Exception as error:
                print(f"会話の要約に失敗しました: {error}")
            self.memory.save()
